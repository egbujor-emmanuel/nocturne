"""Page Bitget spot history-candles back to listing for the weekend rToken cohort."""
import json,urllib.request,datetime as dt,time,os,sys

WEEKEND20=["RNVDA","RAAPL","RAMZN","RGOOGL","RMSFT","RMETA","RTSLA","RAMD","RAVGO",
           "RINTC","RMU","RMRVL","RSNDK","RSOXL","RDRAM","RLITE","RNOK","RAAOI","RRKLB","RASTS"]
BASE="https://api.bitget.com/api/v2/spot/market/history-candles"

def get(url,tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url,timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if i==tries-1: return {"err":str(e)}
            time.sleep(1.5*(i+1))
    return {}

def fetch_all(sym,gran="1h",pages=6):
    """Walk backwards from now until the exchange stops returning rows."""
    end=int(time.time()*1000); out={}
    for _ in range(pages):
        r=get(f"{BASE}?symbol={sym}&granularity={gran}&endTime={end}&limit=200")
        rows=r.get("data") or []
        if not rows: break
        for x in rows: out[int(x[0])]=x
        oldest=min(int(x[0]) for x in rows)
        if oldest>=end: break
        end=oldest
        time.sleep(0.12)
    return [out[k] for k in sorted(out)]

if __name__=="__main__":
    gran=sys.argv[1] if len(sys.argv)>1 else "1h"
    pages=int(sys.argv[2]) if len(sys.argv)>2 else 20
    os.makedirs(f"data/{gran}",exist_ok=True)
    for t in WEEKEND20:
        sym=t+"USDT"
        rows=fetch_all(sym,gran,pages)
        if not rows:
            print(f"{sym:12s} NO DATA"); continue
        json.dump(rows,open(f"data/{gran}/{sym}.json","w"))
        a=dt.datetime.utcfromtimestamp(int(rows[0][0])/1000)
        b=dt.datetime.utcfromtimestamp(int(rows[-1][0])/1000)
        print(f"{sym:12s} {len(rows):6d} bars  {a:%Y-%m-%d} -> {b:%Y-%m-%d}")
