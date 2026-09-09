"""C5: capture health check.

Reads every live NDJSON file, finds the newest row per source, and reports
staleness. Exits non-zero if BOTH capture systems are stale, which makes the
GitHub Actions run go red and sends an email — free alerting.

One stale source is a warning (the other is covering). Both stale is an outage.
"""
import json,glob,os,sys,datetime as dt
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from session import classify, ET

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# how stale is too stale, by session (minutes). Dark = 5-min cadence, else 15.
LIMIT_DARK, LIMIT_LIT = 30, 45

def newest_per_source():
    out={}
    for p in glob.glob(os.path.join(ROOT,"data","live","*.ndjson")):
        src=os.path.basename(p).split(".")[-2]
        last=None
        with open(p,encoding="utf8") as f:
            for line in f:
                if line.strip(): last=line
        if not last: continue
        try: t=json.loads(last).get("t")
        except Exception: continue
        if t and t>out.get(src,0): out[src]=t
    return out

def main():
    now=dt.datetime.now(dt.timezone.utc)
    sess=classify(now)
    limit=LIMIT_DARK if sess in {"VOID_A","PARTIAL_B","NIGHT"} else LIMIT_LIT
    src=newest_per_source()
    report={"checked":now.isoformat(),"session":sess,"limit_min":limit,"sources":{}}
    stale=[]
    for s in ("gh","local"):
        t=src.get(s)
        if not t:
            report["sources"][s]={"age_min":None,"state":"MISSING"}; stale.append(s); continue
        age=(now.timestamp()-t)/60
        state="OK" if age<=limit else "STALE"
        report["sources"][s]={"age_min":round(age,1),
                             "last":dt.datetime.fromtimestamp(t,ET).strftime("%Y-%m-%d %H:%M ET"),
                             "state":state}
        if state=="STALE": stale.append(s)
    report["healthy"]=len(stale)<2
    json.dump(report,open(os.path.join(ROOT,"data","health.json"),"w"),indent=1)
    for s,v in report["sources"].items():
        print(f"  {s:6s} age={str(v['age_min']):>7s}m  {v['state']}  {v.get('last','-')}")
    print(f"session={sess} limit={limit}m healthy={report['healthy']}")
    if not report["healthy"]:
        print("CAPTURE OUTAGE: both sources stale"); return 1
    if stale: print(f"WARNING: {stale} stale, other source covering")
    return 0

if __name__=="__main__": sys.exit(main())
