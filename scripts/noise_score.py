"""I3: Noise Score.

Built on the validated result (see study_v2.py / fairvalue_v2.py):
  during the void window, a large-cap rToken's move away from Friday's close
  reverses essentially completely (beta = -1.003, t = -3.46), and predicting
  "Monday = Friday's close" beats "Monday = the current price" out-of-sample
  by +9.19% MAE.

So the honest quantity to show a trader is not a forecast of Monday's level.
It is: HOW FAR has this price drifted from Friday's close, measured in units
of this stock's own normal daily movement, and how unusual is that drift for
this particular stock?

  z          = (P_now / P_friday_close - 1) / sigma_daily
  percentile = rank of |z| against this symbol's own historical void drifts
  score      = that percentile, 0-100

score 90 means: "this weekend dislocation is larger than 90% of the ones this
stock has had since weekend trading began." It ranks execution risk. It does
NOT claim to know where Monday opens.
"""
import sys,os,json,glob,math,datetime as dt,statistics as st
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import load_bars, ROOT
ET=dt.timezone(dt.timedelta(hours=-4))

LARGE={"RAAPL","RMSFT","RNVDA","RGOOGL","RAMZN","RMETA","RTSLA",
       "RAMD","RAVGO","RINTC","RMU","RORCL","RPLTR","RCOIN","RBABA"}
LEVERAGED={"RSOXL","RSOXS","RTQQQ","RSQQQ","RIQQQ","RQQQM","RQQQI","RTEM"}
CAL=os.path.join(ROOT,"data","noise_calibration.json")

def build_calibration():
    """Per-symbol daily volatility + the historical distribution of |z| drifts."""
    out={}
    for p in sorted(glob.glob(os.path.join(ROOT,"data","1h","*.json"))):
        sym=os.path.basename(p)[:-9]
        try: b=load_bars(p)
        except Exception: continue
        closes={}
        for t,(c,q) in b.items():
            if t.weekday()<5 and t.hour==15: closes[t.date()]=c
        ds=sorted(closes)
        rs=[closes[y]/closes[x]-1 for x,y in zip(ds,ds[1:])
            if closes[x]>0 and abs(closes[y]/closes[x]-1)<0.5]
        if len(rs)<10: continue
        sigma=st.pstdev(rs)
        if sigma<1e-5: continue
        # historical void drifts, hour by hour, in z units
        zs=[]
        for fri in sorted({t.date() for t in b if t.weekday()==4}):
            pf=None
            for k in range(4):
                t=dt.datetime.combine(fri,dt.time(15,0),ET)-dt.timedelta(hours=k)
                if t in b: pf=b[t][0]; break
            if not pf or pf<=0: continue
            start=dt.datetime.combine(fri,dt.time(20,0),ET)
            end=dt.datetime.combine(fri+dt.timedelta(days=2),dt.time(19,0),ET)
            for t,(c,q) in b.items():
                if start<=t<end and c>0: zs.append(abs(c/pf-1)/sigma)
        if len(zs)<30: continue
        zs.sort()
        out[sym]=dict(sigma=sigma,n=len(zs),
                      grid=[round(zs[int(q*(len(zs)-1))],5) for q in
                            [i/100 for i in range(101)]])
    json.dump(out,open(CAL,"w"))
    return out

def load_calibration():
    if not os.path.exists(CAL): return build_calibration()
    return json.load(open(CAL))

def score(sym,p_now,p_fri,cal=None):
    cal=cal or load_calibration()
    c=cal.get(sym)
    if not c or not p_fri or p_fri<=0: return None
    disloc=p_now/p_fri-1
    z=disloc/c["sigma"]
    grid=c["grid"]; a=abs(z)
    pct=0
    for i,g in enumerate(grid):
        if a>=g: pct=i
        else: break
    tier="LOW" if pct<50 else ("ELEVATED" if pct<80 else "HIGH")
    return dict(symbol=sym,price=p_now,friday_close=p_fri,
                dislocation_pct=round(disloc*100,3),
                sigma_daily_pct=round(c["sigma"]*100,3),
                z=round(z,2),score=pct,tier=tier,
                expected_reversion_pct=round(-disloc*100,3),
                fair_value=round(p_fri,4),
                basis="large-cap" if sym in LARGE else
                      ("leveraged - excluded from the study" if sym in LEVERAGED else "other"))

if __name__=="__main__":
    cal=build_calibration()
    print(f"calibrated {len(cal)} symbols")
    demo=[("RNVDA",1.012),("RAAPL",0.995),("RTSLA",1.03),("RMU",1.001)]
    print(f"\n{'symbol':8s} {'drift':>8s} {'sigma':>7s} {'z':>6s} {'score':>6s} {'tier':>9s} {'exp.rev':>8s}")
    for sym,mult in demo:
        c=cal.get(sym)
        if not c: continue
        pf=100.0; pn=pf*mult
        s=score(sym,pn,pf,cal)
        print(f"{sym:8s} {s['dislocation_pct']:+7.2f}% {s['sigma_daily_pct']:6.2f}% "
              f"{s['z']:+6.2f} {s['score']:6d} {s['tier']:>9s} {s['expected_reversion_pct']:+7.2f}%")
