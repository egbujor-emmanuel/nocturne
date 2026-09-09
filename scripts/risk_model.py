"""Can we predict the MAGNITUDE of the re-anchor, rather than its direction?

Direction is unforecastable (see fairvalue.py). But for Execution Assistance
the useful question is different and much easier:

   "How far is Monday likely to move away from the price you are about to pay?"

Target: |m| (absolute re-anchor move). Features known at decision time:
   |w|        size of the void move so far
   log vq     how much money actually traded in the void window
   |mkt|,|res| market vs idiosyncratic decomposition
   vbars      how many hours actually printed

Walk-forward, same protocol as fairvalue.py. Baseline = predict the training
mean of |m| (a constant). Beating a constant means the features carry real
information about execution risk.
"""
import sys,os,json,math,statistics as st
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import observations, ROOT

MIN_TRAIN=5

def feats(r):
    return [abs(r["w"]), math.log10(max(r["vq"],1.0)), abs(r["mkt"]), abs(r["res"])]

def fit(rows):
    """Ridge-free multiple regression via Gaussian elimination (no numpy)."""
    X=[[1.0]+feats(r) for r in rows]; y=[abs(r["m"]) for r in rows]
    k=len(X[0])
    A=[[sum(X[i][a]*X[i][b] for i in range(len(X))) for b in range(k)]+
       [sum(X[i][a]*y[i] for i in range(len(X)))] for a in range(k)]
    for c in range(k):
        p=max(range(c,k),key=lambda r:abs(A[r][c]))
        if abs(A[p][c])<1e-12: return None
        A[c],A[p]=A[p],A[c]
        for r in range(k):
            if r!=c:
                f=A[r][c]/A[c][c]
                for j in range(c,k+1): A[r][j]-=f*A[c][j]
    return [A[i][k]/A[i][i] for i in range(k)]

def pred(co,r):
    return max(0.0, co[0]+sum(c*f for c,f in zip(co[1:],feats(r))))

rec=observations()
wks=sorted({r["fri"] for r in rec})
rows=[]
for i,wk in enumerate(wks):
    if i<MIN_TRAIN: continue
    tr=[r for r in rec if r["fri"]<wk]; te=[r for r in rec if r["fri"]==wk]
    co=fit(tr); base=st.mean(abs(r["m"]) for r in tr)
    if not co: continue
    for r in te:
        rows.append(dict(sym=r["sym"],fri=str(wk),actual=abs(r["m"]),
                         model=pred(co,r),base=base))

def sc(k):
    e=[r[k]-r["actual"] for r in rows]
    return st.mean(abs(x) for x in e),(st.mean(x*x for x in e))**0.5

mb,rb=sc("base"); mm,rm=sc("model")
print(f"walk-forward: {len(rows)} predictions over {len({r['fri'] for r in rows})} weekends\n")
print(f"  {'':16s} {'MAE':>9s} {'RMSE':>9s}")
print(f"  {'constant mean':16s} {mb*100:8.3f}% {rb*100:8.3f}%")
print(f"  {'feature model':16s} {mm*100:8.3f}% {rm*100:8.3f}%   ({(mb-mm)/mb*100:+.1f}% MAE)")

# does the model rank risk correctly? split predictions into terciles
rows.sort(key=lambda r:r["model"])
t=max(1,len(rows)//3)
print("\n  ranking check - actual |re-anchor| by predicted-risk tercile:")
for i,lab in enumerate(("LOW ","MED ","HIGH")):
    sub=rows[i*t:(i+1)*t] if i<2 else rows[2*t:]
    print(f"    {lab} predicted={st.mean(r['model'] for r in sub)*100:5.2f}%  "
          f"actual={st.mean(r['actual'] for r in sub)*100:5.2f}%  n={len(sub)}")
co=fit(rec)
print(f"\nfull-sample coefficients: const={co[0]:+.5f} |w|={co[1]:+.4f} "
      f"log$={co[2]:+.5f} |mkt|={co[3]:+.4f} |res|={co[4]:+.4f}")
json.dump({"mae_base":mb,"mae_model":mm,"improvement_pct":(mb-mm)/mb*100,
           "coef":co,"n":len(rows)},
          open(os.path.join(ROOT,"data","risk_model.json"),"w"),indent=1)
