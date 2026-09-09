"""
NOCTURNE core study.

How much of a weekend rToken price move is NOISE that unwinds once real
liquidity returns?

Windows (all US Eastern, DST):
  Fri 15:00 bar close  -> last regular-session price (the "reference close")
  Sun 19:00 bar close  -> end of Void A, the dead window with no external price
  Mon 10:00 bar close  -> after the re-anchor has completed

  w = void return      = P(Sun 19:00) / P(Fri 15:00) - 1
  m = re-anchor return = P(Mon 10:00) / P(Sun 19:00) - 1

Pooled OLS of m on w. Slope beta:
  beta = -1  every void move fully unwinds  -> weekend price is pure noise
  beta =  0  void moves persist             -> weekend price is real information
Noise share = -beta.
"""
import json,glob,os,datetime as dt,statistics as st

ET=dt.timezone(dt.timedelta(hours=-4))

def load(p):
    out={}
    for r in json.load(open(p)):
        t=dt.datetime.fromtimestamp(int(r[0])/1000,ET)
        out[t]=dict(c=float(r[4]),q=float(r[6]))
    return out

def near(b,day,hour,slack=3):
    """closest bar at/just before target hour, tolerating missing bars"""
    for k in range(slack+1):
        t=dt.datetime.combine(day,dt.time(hour,0),ET)-dt.timedelta(hours=k)
        if t in b: return b[t]["c"]
    return None

def study(p):
    sym=os.path.basename(p)[:-9]
    b=load(p); rec=[]
    for fri in sorted({t.date() for t in b if t.weekday()==4}):
        sun=fri+dt.timedelta(days=2); mon=fri+dt.timedelta(days=3)
        pf=near(b,fri,15); pv=near(b,sun,19); pm=near(b,mon,10)
        if not all((pf,pv,pm)) or min(pf,pv,pm)<=0: continue
        void=[v["q"] for t,v in b.items()
              if dt.datetime.combine(fri,dt.time(20,0),ET)<=t<dt.datetime.combine(sun,dt.time(19,0),ET)]
        if len(void)<24: continue            # require a genuinely covered weekend
        rec.append(dict(sym=sym,fri=fri,w=pv/pf-1,m=pm/pv-1,net=pm/pf-1,
                        vq=sum(void),vbars=len(void)))
    return rec

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
    return dict(n=n,beta=beta,r2=1-sse/sst if sst else 0,se=se,
                t=beta/se if se else float("nan"))

rec=[]
for p in sorted(glob.glob("data/1h/*.json")): rec+=study(p)
if not rec: print("NO QUALIFYING WEEKENDS"); raise SystemExit
xs=[r["w"] for r in rec]; ys=[r["m"] for r in rec]
res=ols(xs,ys)
wks=sorted({r["fri"] for r in rec}); syms=sorted({r["sym"] for r in rec})
print(f"observations : {len(rec)}  ({len(syms)} tickers x {len(wks)} weekends)")
print(f"weekends     : {wks[0]} .. {wks[-1]}")
print(f"median void $ volume per name per weekend : ${st.median([r['vq'] for r in rec]):,.0f}")
print()
print(f"  beta (re-anchor on void) = {res['beta']:+.3f}  (se {res['se']:.3f}, t {res['t']:+.2f}, n={res['n']})")
print(f"  >>> NOISE SHARE = {-res['beta']*100:.1f}%  of void-window movement unwinds")
print(f"  R^2 = {res['r2']:.3f}")
print()
opp=sum(1 for r in rec if r['w']*r['m']<0)
print(f"  re-anchor moves AGAINST the void move : {opp}/{len(rec)} = {opp/len(rec)*100:.1f}% of the time")
print(f"  mean |void move|      = {st.mean([abs(r['w']) for r in rec])*100:.2f}%")
print(f"  mean |re-anchor move| = {st.mean([abs(r['m']) for r in rec])*100:.2f}%")
print()
print("per-weekend:")
for wk in wks:
    s=[r for r in rec if r["fri"]==wk]
    rr=ols([r["w"] for r in s],[r["m"] for r in s])
    if rr: print(f"  {wk}  n={rr['n']:2d}  beta={rr['beta']:+.3f}  noise={-rr['beta']*100:6.1f}%  R2={rr['r2']:.2f}")
