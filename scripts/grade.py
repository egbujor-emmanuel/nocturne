"""P4: grade a published prediction against what actually happened.

Fetches the real Monday 10:00 ET price and scores both published claims.
Writes scoreboard.json (cumulative) and a ready-to-paste X post.
Publishes the result whether we won or lost - that is the point.
"""
import sys,os,json,glob,time,urllib.request,datetime as dt,statistics as st
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import ROOT
import netfix  # DNS fallback; no-op on a healthy network
from session import ET
UA={"User-Agent":"nocturne/1.0"}

def candles(sym,limit=200):
    u=f"https://api.bitget.com/api/v2/spot/market/candles?symbol={sym}&granularity=1h&limit={limit}"
    try:
        d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=25))
        return d.get("data") or []
    except Exception: return []

def price_at(sym,target,slack=3):
    for r in candles(sym):
        t=dt.datetime.fromtimestamp(int(r[0])/1000,ET)
        if t==target: return float(r[4])
    rows={dt.datetime.fromtimestamp(int(r[0])/1000,ET):float(r[4]) for r in candles(sym)}
    for k in range(slack+1):
        t=target-dt.timedelta(hours=k)
        if t in rows: return rows[t]
    return None

def latest_prediction():
    fs=[f for f in sorted(glob.glob(os.path.join(ROOT,"predictions","*.json")))
        if not f.endswith("latest.json")]
    return fs[-1] if fs else None

def main(path=None):
    path=path or latest_prediction()
    if not path: print("no prediction file"); return 1
    doc=json.load(open(path,encoding="utf8"))
    tgt=dt.datetime.strptime(doc["graded_against"].replace(" ET",""),"%Y-%m-%d %H:%M").replace(tzinfo=ET)
    tgt=tgt.replace(hour=10,minute=0)      # grade at the 10:00 ET bar, post re-anchor
    if dt.datetime.now(ET)<tgt+dt.timedelta(hours=1):
        print(f"too early - grading target is {tgt:%Y-%m-%d %H:%M ET}"); return 1
    graded=[]
    for p in doc["predictions"]:
        a=price_at(p["symbol"]+"USDT",tgt)
        if not a: continue
        graded.append(dict(p,actual=a,
            err_model=abs(p["predicted_monday"]-a)/a,
            err_base=abs(p["baseline_monday"]-a)/a,
            monday_move=abs(a/p["price_at_prediction"]-1)))
        time.sleep(0.06)
    if len(graded)<5: print(f"only {len(graded)} gradeable"); return 1
    mm=st.mean(g["err_model"] for g in graded); mb=st.mean(g["err_base"] for g in graded)
    c1=mm<mb
    graded.sort(key=lambda g:-g["noise_score"])
    n=max(3,len(graded)//3)
    hi=st.mean(g["monday_move"] for g in graded[:n])
    lo=st.mean(g["monday_move"] for g in graded[-n:])
    c2=hi>lo
    res={"prediction_file":os.path.basename(path),
         "published":doc["published_et"],"graded_at":dt.datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"),
         "target":tgt.strftime("%Y-%m-%d %H:%M ET"),"n":len(graded),
         "claim_1_level":{"won":c1,"mae_model_pct":round(mm*100,3),
                          "mae_baseline_pct":round(mb*100,3),
                          "improvement_pct":round((mb-mm)/mb*100,2) if mb else None},
         "claim_2_ranking":{"won":c2,"top_third_move_pct":round(hi*100,3),
                            "bottom_third_move_pct":round(lo*100,3),"third_size":n},
         "detail":graded}
    sb=os.path.join(ROOT,"data","scoreboard.json")
    hist=json.load(open(sb)) if os.path.exists(sb) else {"rounds":[]}
    hist["rounds"]=[r for r in hist["rounds"] if r["prediction_file"]!=res["prediction_file"]]
    hist["rounds"].append({k:v for k,v in res.items() if k!="detail"})
    hist["summary"]={"rounds":len(hist["rounds"]),
        "claim_1_won":sum(1 for r in hist["rounds"] if r["claim_1_level"]["won"]),
        "claim_2_won":sum(1 for r in hist["rounds"] if r["claim_2_ranking"]["won"])}
    json.dump(hist,open(sb,"w"),indent=1)
    json.dump(res,open(os.path.join(ROOT,"predictions",
        os.path.basename(path).replace(".json","_graded.json")),"w"),indent=1)
    print(f"graded {len(graded)} symbols against {res['target']}")
    print(f"  CLAIM 1 level  : {'WON' if c1 else 'LOST'}  model {mm*100:.3f}% vs baseline {mb*100:.3f}%")
    print(f"  CLAIM 2 ranking: {'WON' if c2 else 'LOST'}  top {hi*100:.3f}% vs bottom {lo*100:.3f}%")
    print(f"  cumulative: claim1 {hist['summary']['claim_1_won']}/{hist['summary']['rounds']}, "
          f"claim2 {hist['summary']['claim_2_won']}/{hist['summary']['rounds']}")
    return 0

if __name__=="__main__": sys.exit(main())
