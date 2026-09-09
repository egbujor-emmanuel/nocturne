"""I2: fair-value model + honest walk-forward evaluation.

Question: given the price at the end of the void window, what will the
re-anchor produce? We predict the re-anchor return m and compare against
the only sensible baseline - "the current price is right" (m_hat = 0).

Models
  M0  random walk        m_hat = 0            (fair value = current price)
  M1  single shrinkage   m_hat = a + b*w
  M2  two-factor         m_hat = a + b1*mkt + b2*res

Walk-forward: for each weekend k (after a minimum training window), fit on
weekends < k only, predict k. Nothing in the reported numbers is in-sample.
"""
import sys,os,json,statistics as st
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import observations, ols, ols2, ROOT

MIN_TRAIN_WEEKENDS=5

def evaluate():
    rec=observations()
    wks=sorted({r["fri"] for r in rec})
    preds=[]
    for i,wk in enumerate(wks):
        if i<MIN_TRAIN_WEEKENDS: continue
        train=[r for r in rec if r["fri"]<wk]
        test=[r for r in rec if r["fri"]==wk]
        m1=ols([r["w"] for r in train],[r["m"] for r in train])
        m2=ols2(train,"mkt","res")
        for r in test:
            p={"sym":r["sym"],"fri":str(wk),"actual":r["m"],
               "M0":0.0,
               "M1":(m1["alpha"]+m1["beta"]*r["w"]) if m1 else 0.0,
               "M2":(m2["a0"]+m2["b1"]*r["mkt"]+m2["b2"]*r["res"]) if m2 else 0.0}
            preds.append(p)
    return rec,wks,preds

def score(preds,k):
    err=[p[k]-p["actual"] for p in preds]
    mae=st.mean(abs(e) for e in err)
    rmse=(st.mean(e*e for e in err))**0.5
    # directional: did we get the sign of the re-anchor right (when non-trivial)?
    nz=[p for p in preds if abs(p["actual"])>0.002 and abs(p[k])>1e-9]
    hit=sum(1 for p in nz if (p[k]>0)==(p["actual"]>0))/len(nz) if nz else float("nan")
    return mae,rmse,hit,len(nz)

if __name__=="__main__":
    rec,wks,preds=evaluate()
    print(f"observations {len(rec)}  weekends {len(wks)}  "
          f"walk-forward tested on {len({p['fri'] for p in preds})} weekends, {len(preds)} predictions")
    print(f"\n{'model':6s} {'MAE':>9s} {'RMSE':>9s} {'vs M0':>9s} {'dir.acc':>9s} {'n':>5s}")
    base=None
    out={}
    for k,label in (("M0","M0"),("M1","M1"),("M2","M2")):
        mae,rmse,hit,n=score(preds,k)
        if base is None: base=mae
        imp=(base-mae)/base*100
        out[k]=dict(mae=mae,rmse=rmse,hit=hit,n=n,improvement_pct=imp)
        print(f"{label:6s} {mae*100:8.3f}% {rmse*100:8.3f}% {imp:+8.2f}% {hit*100:8.1f}% {n:5d}")
    # full-sample coefficients for the live model
    m1=ols([r["w"] for r in rec],[r["m"] for r in rec])
    m2=ols2(rec,"mkt","res")
    print(f"\nfull-sample M1: m_hat = {m1['alpha']:+.5f} {m1['beta']:+.4f}*w   (t={m1['t']:+.2f})")
    print(f"full-sample M2: m_hat = {m2['a0']:+.5f} {m2['b1']:+.4f}*mkt {m2['b2']:+.4f}*res")
    json.dump({"walk_forward":out,
               "M1":{"alpha":m1["alpha"],"beta":m1["beta"],"t":m1["t"]},
               "M2":{"a0":m2["a0"],"b1":m2["b1"],"b2":m2["b2"]},
               "n_obs":len(rec),"n_weekends":len(wks)},
              open(os.path.join(ROOT,"data","fairvalue_model.json"),"w"),indent=1)
