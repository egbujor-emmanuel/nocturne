"""Void Drift study across the FULL weekend universe.

Beyond the pooled beta, this answers the question the Noise Score depends on:
does the noise share vary with how thin the weekend market was?
If thin weekends unwind more than liquid ones, thinness is a usable feature.
"""
import json,glob,os,datetime as dt,statistics as st

ET=dt.timezone(dt.timedelta(hours=-4))

def load(p):
    return {dt.datetime.fromtimestamp(int(r[0])/1000,ET):(float(r[4]),float(r[6]))
            for r in json.load(open(p))}

def near(b,day,hour,slack=3):
    for k in range(slack+1):
        t=dt.datetime.combine(day,dt.time(hour,0),ET)-dt.timedelta(hours=k)
        if t in b: return b[t][0]

def study(p):
    sym=os.path.basename(p)[:-9]; b=load(p); rec=[]
    for fri in sorted({t.date() for t in b if t.weekday()==4}):
        sun=fri+dt.timedelta(days=2); mon=fri+dt.timedelta(days=3)
        pf,pv,pm=near(b,fri,15),near(b,sun,19),near(b,mon,10)
        if not all((pf,pv,pm)) or min(pf,pv,pm)<=0: continue
        vq=[q for t,(c,q) in b.items()
            if dt.datetime.combine(fri,dt.time(20,0),ET)<=t<dt.datetime.combine(sun,dt.time(19,0),ET)]
        if len(vq)<24: continue
        rec.append(dict(sym=sym,fri=fri,w=pv/pf-1,m=pm/pv-1,vq=sum(vq),bars=len(vq)))
    return rec

def ols(xs,ys):
    n=len(xs)
    if n<5: return None
    mx,my=sum(xs)/n,sum(ys)/n
    sxx=sum((x-mx)**2 for x in xs)
    if sxx==0: return None
    beta=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sxx; alpha=my-beta*mx
    sse=sum((y-(alpha+beta*x))**2 for x,y in zip(xs,ys)); sst=sum((y-my)**2 for y in ys)
    se=(sse/(n-2)/sxx)**0.5 if n>2 else float("nan")
    return dict(n=n,beta=beta,r2=1-sse/sst if sst else 0,se=se,t=beta/se if se else float("nan"))

rec=[]
for p in sorted(glob.glob("data/1h/*.json")): rec+=study(p)
print(f"symbols with data : {len({r['sym'] for r in rec})}")
print(f"observations      : {len(rec)}")
print(f"weekends          : {len({r['fri'] for r in rec})}")
res=ols([r["w"] for r in rec],[r["m"] for r in rec])
print(f"\nPOOLED  beta={res['beta']:+.3f}  se={res['se']:.3f}  t={res['t']:+.2f}  R2={res['r2']:.3f}")
print(f"        NOISE SHARE = {-res['beta']*100:.1f}%")

# --- the Noise Score feasibility test: beta by weekend-liquidity quartile ---
rec.sort(key=lambda r:r["vq"])
q=max(1,len(rec)//4)
print("\nbeta by void-window liquidity quartile (thinnest first):")
print(f"  {'bucket':8s} {'n':>4s} {'median $vol':>13s} {'beta':>8s} {'noise':>8s} {'t':>7s}")
for i in range(4):
    sub=rec[i*q:(i+1)*q] if i<3 else rec[3*q:]
    rr=ols([r["w"] for r in sub],[r["m"] for r in sub])
    if rr:
        mv=st.median([r["vq"] for r in sub])
        print(f"  Q{i+1:<7d} {rr['n']:4d} ${mv:>12,.0f} {rr['beta']:+8.3f} {-rr['beta']*100:7.1f}% {rr['t']:+7.2f}")

# --- and by size of the void move ---
rec.sort(key=lambda r:abs(r["w"]))
print("\nbeta by |void move| quartile (smallest first):")
for i in range(4):
    sub=rec[i*q:(i+1)*q] if i<3 else rec[3*q:]
    rr=ols([r["w"] for r in sub],[r["m"] for r in sub])
    if rr:
        mm=st.median([abs(r["w"]) for r in sub])*100
        print(f"  Q{i+1:<7d} {rr['n']:4d} {mm:>12.2f}% {rr['beta']:+8.3f} {-rr['beta']*100:7.1f}% {rr['t']:+7.2f}")
json.dump(dict(pooled=res,n=len(rec)),open("data/void_drift_extended.json","w"),indent=1,default=str)
