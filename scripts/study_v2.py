"""Void drift, corrected for a heterogeneous universe.

The pooled regression mixed 3x leveraged ETFs (rSOXL, rSOXS, rTQQQ) with
mega caps. Leveraged names carry ~3x the volatility and dominate the variance,
destroying signal-to-noise for everyone else.

Two corrections:
  1. exclude structurally leveraged/inverse products
  2. express every return in units of that symbol's OWN volatility (z-scores),
     so one observation from Apple counts the same as one from SOXL
"""
import sys,os,json,math,statistics as st,glob,datetime as dt
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import observations, ols, ols2, load_bars, ROOT
ET=dt.timezone(dt.timedelta(hours=-4))

LEVERAGED={"RSOXL","RSOXS","RTQQQ","RSQQQ","RIQQQ","RQQQM","RQQQI","RTEM"}

def daily_vol(sym):
    """stdev of RTH close-to-close returns, per symbol, from hourly bars"""
    try: b=load_bars(os.path.join(ROOT,"data","1h",sym+"USDT.json"))
    except Exception: return None
    closes={}
    for t,(c,q) in b.items():
        if t.weekday()<5 and t.hour==15: closes[t.date()]=c
    ds=sorted(closes)
    rs=[closes[b_]/closes[a]-1 for a,b_ in zip(ds,ds[1:])
        if closes[a]>0 and abs(closes[b_]/closes[a]-1)<0.5]
    return st.pstdev(rs) if len(rs)>10 else None

def run(rec,label):
    if len(rec)<20: print(f"{label}: too few obs ({len(rec)})"); return
    r1=ols([r["w"] for r in rec],[r["m"] for r in rec])
    print(f"\n{label}")
    nsym=len({r["sym"] for r in rec})
    print(f"  n={r1['n']:4d} symbols={nsym:3d}  beta={r1['beta']:+.3f} se={r1['se']:.3f} "
          f"t={r1['t']:+.2f} R2={r1['r2']:.3f}  noise={-r1['beta']*100:.1f}%")
    return r1

rec=observations()
vol={s:daily_vol(s) for s in {r["sym"] for r in rec}}
ok={s:v for s,v in vol.items() if v and v>1e-5}

run(rec,"ALL NAMES (original)")
clean=[r for r in rec if r["sym"] not in LEVERAGED]
run(clean,"EX-LEVERAGED")
mega=[r for r in rec if r["sym"] in {"RAAPL","RMSFT","RNVDA","RGOOGL","RAMZN","RMETA","RTSLA",
                                     "RAMD","RAVGO","RINTC","RMU","RORCL","RPLTR","RCOIN","RBABA"}]
run(mega,"LARGE CAPS ONLY")

# volatility-normalised: z = return / own daily vol
z=[]
for r in clean:
    v=ok.get(r["sym"])
    if not v: continue
    z.append(dict(r,w=r["w"]/v,m=r["m"]/v))
run(z,"EX-LEVERAGED, VOL-NORMALISED (z units)")

zl=[r for r in z if abs(r["w"])>0.5]
run(zl,"VOL-NORMALISED, |void move| > 0.5 sigma")
json.dump({"leveraged_excluded":sorted(LEVERAGED)},open(os.path.join(ROOT,"data","study_v2.json"),"w"),indent=1)
