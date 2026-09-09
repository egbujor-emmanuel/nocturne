"""Walk-forward fair value, restricted to a homogeneous large-cap universe."""
import sys,os,json,statistics as st
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import observations, ols, ols2, ROOT

LARGE={"RAAPL","RMSFT","RNVDA","RGOOGL","RAMZN","RMETA","RTSLA",
       "RAMD","RAVGO","RINTC","RMU","RORCL","RPLTR","RCOIN","RBABA"}
MIN_TRAIN=5

def evaluate(universe,label):
    rec=[r for r in observations() if r["sym"] in universe] if universe else observations()
    wks=sorted({r["fri"] for r in rec}); preds=[]
    for i,wk in enumerate(wks):
        if i<MIN_TRAIN: continue
        tr=[r for r in rec if r["fri"]<wk]; te=[r for r in rec if r["fri"]==wk]
        if len(tr)<20: continue
        m1=ols([r["w"] for r in tr],[r["m"] for r in tr])
        m2=ols2(tr,"mkt","res")
        for r in te:
            preds.append({"sym":r["sym"],"fri":str(wk),"actual":r["m"],"M0":0.0,
                          "M1":(m1["alpha"]+m1["beta"]*r["w"]) if m1 else 0.0,
                          "M2":(m2["a0"]+m2["b1"]*r["mkt"]+m2["b2"]*r["res"]) if m2 else 0.0,
                          "MF":-r["w"]})   # MF = full fade (beta fixed at -1, no fitting)
    if not preds: print(f"{label}: no predictions"); return None
    def sc(k):
        e=[p[k]-p["actual"] for p in preds]
        mae=st.mean(abs(x) for x in e); rmse=(st.mean(x*x for x in e))**0.5
        nz=[p for p in preds if abs(p["actual"])>0.002 and abs(p[k])>1e-9]
        hit=sum(1 for p in nz if (p[k]>0)==(p["actual"]>0))/len(nz) if nz else float("nan")
        return mae,rmse,hit,len(nz)
    print(f"\n=== {label} ===")
    print(f"{len(preds)} predictions over {len({p['fri'] for p in preds})} weekends, "
          f"{len({p['sym'] for p in preds})} symbols")
    print(f"  {'model':22s} {'MAE':>9s} {'RMSE':>9s} {'vs M0':>9s} {'dir':>8s} {'n':>5s}")
    base=None; out={}
    for k,lab in (("M0","M0 current price"),("MF","MF full fade (b=-1)"),
                  ("M1","M1 fitted shrink"),("M2","M2 two-factor")):
        mae,rmse,hit,n=sc(k)
        if base is None: base=mae
        imp=(base-mae)/base*100
        out[k]=dict(mae=mae,rmse=rmse,hit=hit,improvement_pct=imp)
        flag=" <<<" if imp>0.5 else ""
        print(f"  {lab:22s} {mae*100:8.3f}% {rmse*100:8.3f}% {imp:+8.2f}% {hit*100:7.1f}% {n:5d}{flag}")
    return out

a=evaluate(None,"FULL UNIVERSE (as before)")
b=evaluate(LARGE,"LARGE CAPS ONLY")
json.dump({"full":a,"large":b,"large_universe":sorted(LARGE)},
          open(os.path.join(ROOT,"data","fairvalue_v2.json"),"w"),indent=1)
