"""F5: backfill hourly history for every symbol in the true weekend universe.

Reads data/weekend_universe.json (produced by scan_universe.py) and pages
Bitget history-candles backwards to listing. Resumable: skips symbols that
already have >= MIN_BARS on disk.
"""
import json,urllib.request,datetime as dt,time,os,sys

BASE="https://api.bitget.com/api/v2/spot/market/history-candles"
UA={"User-Agent":"Mozilla/5.0"}
MIN_BARS=3000

def get(url,tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if i==tries-1: return {"err":str(e)}
            time.sleep(1.5*(i+1))
    return {}

def fetch_all(sym,gran="1h",pages=20):
    end=int(time.time()*1000); out={}
    for _ in range(pages):
        r=get(f"{BASE}?symbol={sym}&granularity={gran}&endTime={end}&limit=200")
        rows=r.get("data") or []
        if not rows: break
        for x in rows: out[int(x[0])]=x
        oldest=min(int(x[0]) for x in rows)
        if oldest>=end: break
        end=oldest; time.sleep(0.1)
    return [out[k] for k in sorted(out)]

def main():
    gran=sys.argv[1] if len(sys.argv)>1 else "1h"
    uni=json.load(open("data/weekend_universe.json"))
    syms=[r["symbol"] for r in uni["universe"]]
    print(f"weekend universe: {len(syms)} symbols -> backfilling {gran}",flush=True)
    os.makedirs(f"data/{gran}",exist_ok=True)
    done=skipped=0
    for i,sym in enumerate(syms,1):
        path=f"data/{gran}/{sym}.json"
        if os.path.exists(path):
            try:
                if len(json.load(open(path)))>=MIN_BARS:
                    skipped+=1; continue
            except Exception: pass
        rows=fetch_all(sym,gran)
        if not rows:
            print(f"  {sym:14s} NO DATA",flush=True); continue
        json.dump(rows,open(path,"w"))
        a=dt.datetime.utcfromtimestamp(int(rows[0][0])/1000)
        b=dt.datetime.utcfromtimestamp(int(rows[-1][0])/1000)
        done+=1
        print(f"  {sym:14s} {len(rows):6d} bars  {a:%Y-%m-%d} -> {b:%Y-%m-%d}",flush=True)
    print(f"\nbackfilled {done}, already had {skipped}, total {done+skipped}/{len(syms)}",flush=True)

if __name__=="__main__": main()
