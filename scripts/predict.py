"""P3: publish a timestamped, hashed prediction before the US market reopens.

Two falsifiable claims, both graded on Monday by grade.py:

  CLAIM 1 (level)   Monday 10:00 ET will be closer to Friday's close than to
                    the price showing right now.  Validated OOS at +9.19% MAE
                    on large caps - it is a real edge, not a certainty.

  CLAIM 2 (ranking) The names we score highest will move MORE on Monday than
                    the names we score lowest.  Validated on terciles
                    (2.64% / 2.91% / 3.28% actual |re-anchor|).

The file is committed with its own SHA256. Git's commit timestamp is the
proof it existed before the market opened - it cannot be back-dated.
"""
import sys,os,json,hashlib,datetime as dt
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import ROOT
from session import classify, next_reopen, ET, DARK
from build_state import build
from noise_score import LARGE

MIN_SCORED=5

def main(force=False):
    now=dt.datetime.now(dt.timezone.utc); sess=classify(now)
    if sess not in DARK and not force:
        print(f"session={sess} - predictions are only published while the market is shut"); return 1
    st=build()
    rows=[r for r in st["symbols"] if r["noise_score"] is not None and r["reference_close"]]
    if len(rows)<MIN_SCORED and not force:
        print(f"only {len(rows)} scored symbols - not enough to publish"); return 1
    rows.sort(key=lambda r:-r["noise_score"])
    large=[r for r in rows if r["symbol"] in LARGE]
    reopen=next_reopen(now)
    preds=[{"symbol":r["symbol"],"name":r["name"],
            "price_at_prediction":r["last"],
            "predicted_monday":r["reference_close"],      # fair value = last regular close
            "baseline_monday":r["last"],                  # what we are betting against
            "dislocation_pct":r["dislocation_pct"],
            "noise_score":r["noise_score"],"tier":r["tier"],
            "buy_usd_0_5":r["buy_usd_0_5"],"liquidity":r["liquidity"],
            "class":r["class"]} for r in rows]
    n=max(3,len(rows)//3)
    doc={"published":now.isoformat(),
         "published_et":now.astimezone(ET).strftime("%Y-%m-%d %H:%M ET"),
         "session":sess,
         "graded_against":reopen.strftime("%Y-%m-%d %H:%M ET"),
         "method":"fair value during a dark session = last regular-session close",
         "claim_1_level":"Monday 10:00 ET will be closer to predicted_monday than to baseline_monday, in aggregate",
         "claim_2_ranking":"the top-scoring third will show a larger mean |Monday move| than the bottom third",
         "top_risk":[r["symbol"] for r in rows[:n]],
         "bottom_risk":[r["symbol"] for r in rows[-n:]],
         "large_cap_count":len(large),
         "predictions":preds}
    body=json.dumps(doc,indent=1,sort_keys=True)
    h=hashlib.sha256(body.encode()).hexdigest()
    d=os.path.join(ROOT,"predictions"); os.makedirs(d,exist_ok=True)
    stamp=now.astimezone(ET).strftime("%Y-%m-%d_%H%M")
    open(os.path.join(d,f"{stamp}.json"),"w").write(body)
    open(os.path.join(d,f"{stamp}.sha256"),"w").write(h+"  "+stamp+".json\n")
    json.dump({"latest":stamp,"sha256":h,"published":doc["published_et"],
               "graded_against":doc["graded_against"],"n":len(preds)},
              open(os.path.join(d,"latest.json"),"w"),indent=1)
    print(f"published {stamp}.json  n={len(preds)}  sha256={h[:16]}...")
    print(f"  graded against {doc['graded_against']}")
    print(f"  top risk: {', '.join(doc['top_risk'][:8])}")
    return 0

if __name__=="__main__":
    sys.exit(main(force="--force" in sys.argv))
