"""Does PEER CONFIRMATION separate signal from noise?

Decompose each void move into a market component and an idiosyncratic residual:
  market_t   = mean void move of all OTHER symbols that weekend
  beta_i     = 1 (equal-weight proxy; sample too small to estimate per name)
  resid_i    = w_i - market_t

Hypothesis: the market component reflects genuine overnight risk sentiment and
should PERSIST; the idiosyncratic residual is one name moving on ~$8k of flow
and should UNWIND. If so, regressing the re-anchor on both gives a much more
negative slope on resid than on market -> a real, usable feature.
"""
import json,glob,os,datetime as dt,statistics as st
ET=dt.timezone(dt.timedelta(hours=-4))

def load(p): return {dt.datetime.fromtimestamp(int(r[0])/1000,ET):(float(r[4]),float(r[6]))
                     for r in json.load(open(p))}
def near(b,d,h,slack=3):
    for k in range(slack+1):
        t=dt.datetime.combine(d,dt.time(h,0),ET)-dt.timedelta(hours=k)
        if t in b: return b[t][0]
rec=[]
for p in sorted(glob.glob("data/1h/*.json")):
    sym=os.path.basename(p)[:-9]; b=load(p)
    for fri in sorted({t.date() for t in b if t.weekday()==4}):
        sun=fri+dt.timedelta(days=2); mon=fri+dt.timedelta(days=3)
        pf,pv,pm=near(b,fri,15),near(b,sun,19),near(b,mon,10)
        if not all((pf,pv,pm)) or min(pf,pv,pm)<=0: continue
        vq=[q for t,(c,q) in b.items()
            if dt.datetime.combine(fri,dt.time(20,0),ET)<=t<dt.datetime.combine(sun,dt.time(19,0),ET)]
        if len(vq)<24: continue
        rec.append(dict(sym=sym,fri=fri,w=pv/pf-1,m=pm/pv-1,vq=sum(vq)))

bywk={}
for r in rec: bywk.setdefault(r["fri"],[]).append(r)
for wk,rs in bywk.items():
    if len(rs)<4: continue
    for r in rs:
        others=[x["w"] for x in rs if x["sym"]!=r["sym"]]
        r["mkt"]=st.median(others)
        r["res"]=r["w"]-r["mkt"]

use=[r for r in rec if "mkt" in r]
def ols2(rows,xk):
    xs=[r[xk] for r in rows]; ys=[r["m"] for r in rows]; n=len(xs)
    mx,my=sum(xs)/n,sum(ys)/n
    sxx=sum((x-mx)**2 for x in xs)
    beta=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sxx; alpha=my-beta*mx
    sse=sum((y-(alpha+beta*x))**2 for x,y in zip(xs,ys)); sst=sum((y-my)**2 for y in ys)
    se=(sse/(n-2)/sxx)**0.5
    return n,beta,se,beta/se,1-sse/sst

print(f"observations with peers: {len(use)}  weekends: {len(bywk)}")
for k,label in (("w","raw void move  "),("mkt","MARKET component"),("res","IDIOSYNCRATIC  ")):
    n,b,se,t,r2=ols2(use,k)
    print(f"  {label}  beta={b:+.3f}  se={se:.3f}  t={t:+.2f}  R2={r2:.3f}  noise={-b*100:6.1f}%")
