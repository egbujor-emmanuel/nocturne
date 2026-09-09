"""Shared feature extraction for the void-drift work."""
import json,glob,os,datetime as dt,statistics as st
ET=dt.timezone(dt.timedelta(hours=-4))
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_bars(p):
    return {dt.datetime.fromtimestamp(int(r[0])/1000,ET):(float(r[4]),float(r[6]))
            for r in json.load(open(p))}

def near(b,day,hour,slack=3):
    for k in range(slack+1):
        t=dt.datetime.combine(day,dt.time(hour,0),ET)-dt.timedelta(hours=k)
        if t in b: return b[t][0]

def observations(min_void_bars=24):
    """One record per (symbol, weekend) with the three anchor prices."""
    rec=[]
    for p in sorted(glob.glob(os.path.join(ROOT,"data","1h","*.json"))):
        sym=os.path.basename(p)[:-9]
        try: b=load_bars(p)
        except Exception: continue
        for fri in sorted({t.date() for t in b if t.weekday()==4}):
            sun=fri+dt.timedelta(days=2); mon=fri+dt.timedelta(days=3)
            pf,pv,pm=near(b,fri,15),near(b,sun,19),near(b,mon,10)
            if not all((pf,pv,pm)) or min(pf,pv,pm)<=0: continue
            vq=[q for t,(c,q) in b.items()
                if dt.datetime.combine(fri,dt.time(20,0),ET)<=t
                <dt.datetime.combine(sun,dt.time(19,0),ET)]
            if len(vq)<min_void_bars: continue
            rec.append(dict(sym=sym,fri=fri,pf=pf,pv=pv,pm=pm,
                            w=pv/pf-1,m=pm/pv-1,vq=sum(vq),vbars=len(vq)))
    add_peer_features(rec)
    return rec

def add_peer_features(rec):
    bywk={}
    for r in rec: bywk.setdefault(r["fri"],[]).append(r)
    for wk,rs in bywk.items():
        for r in rs:
            others=[x["w"] for x in rs if x["sym"]!=r["sym"]]
            r["mkt"]=st.median(others) if len(others)>=3 else 0.0
            r["res"]=r["w"]-r["mkt"]
            r["npeers"]=len(others)

def ols(xs,ys):
    n=len(xs)
    if n<3: return None
    mx,my=sum(xs)/n,sum(ys)/n
    sxx=sum((x-mx)**2 for x in xs)
    if sxx==0: return None
    beta=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sxx
    alpha=my-beta*mx
    sse=sum((y-(alpha+beta*x))**2 for x,y in zip(xs,ys))
    sst=sum((y-my)**2 for y in ys)
    se=(sse/(n-2)/sxx)**0.5 if n>2 else float("nan")
    return dict(n=n,alpha=alpha,beta=beta,se=se,t=beta/se if se else float("nan"),
                r2=1-sse/sst if sst else 0)

def ols2(rows,k1,k2,ykey="m"):
    """Two-regressor OLS via normal equations (no numpy)."""
    n=len(rows)
    x1=[r[k1] for r in rows]; x2=[r[k2] for r in rows]; y=[r[ykey] for r in rows]
    m1,m2,my=sum(x1)/n,sum(x2)/n,sum(y)/n
    a=sum((p-m1)**2 for p in x1); b=sum((p-m1)*(q-m2) for p,q in zip(x1,x2))
    c=b; d=sum((q-m2)**2 for q in x2)
    e=sum((p-m1)*(z-my) for p,z in zip(x1,y)); f=sum((q-m2)*(z-my) for q,z in zip(x2,y))
    det=a*d-b*c
    if abs(det)<1e-18: return None
    b1=(e*d-b*f)/det; b2=(a*f-c*e)/det
    a0=my-b1*m1-b2*m2
    return dict(n=n,a0=a0,b1=b1,b2=b2)
