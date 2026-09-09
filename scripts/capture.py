"""C1: one capture cycle.

Writes one compact NDJSON row per symbol to data/live/YYYY-MM-DD.ndjson.
Depth is computed at capture time (the raw book is too big to keep every
5 minutes); a full top-20 book snapshot is kept once per hour as evidence.

Designed to be run by cron/Actions. Idempotent, append-only, never rewrites.
"""
import json,os,sys,time,datetime as dt,urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from session import classify, next_reopen, ET

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA={"User-Agent":"nocturne/1.0"}
API="https://api.bitget.com/api/v2/spot/market"
BAND=0.10          # buy/sellLimitPriceRatio from the symbol metadata
DEPTH_PCTS=(0.5,2.0)

def jget(u,tries=3,timeout=20):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=timeout) as r:
                return json.load(r)
        except Exception:
            if i==tries-1: return None
            time.sleep(0.6*(i+1))

def universe():
    p=os.path.join(ROOT,"data","weekend_universe.json")
    return [r["symbol"] for r in json.load(open(p))["universe"]]

def depth(levels,ref,side,pct):
    """shares available within pct% of ref on one side"""
    lim=ref*(1+pct/100) if side=="ask" else ref*(1-pct/100)
    tot=0.0; usd=0.0
    for p,q in levels:
        p=float(p); q=float(q)
        if (side=="ask" and p<=lim) or (side=="bid" and p>=lim):
            tot+=q; usd+=p*q
        else: break
    return round(tot,4),round(usd,2)

def book(sym):
    d=jget(f"{API}/orderbook?symbol={sym}&type=step0&limit=150")
    if not d or d.get("code")!="00000": return sym,None
    return sym,d["data"]

def main():
    ts=dt.datetime.now(dt.timezone.utc)
    et=ts.astimezone(ET)
    sess=classify(ts)

    # cadence gate: 5-min while the US market is shut (what we actually study),
    # 15-min otherwise. Halves repo growth without losing the void window.
    from session import DARK
    if sess not in DARK and et.minute % 15 >= 5 and "--force" not in sys.argv:
        print(f"{et:%H:%M ET} sess={sess} skip (off-cadence)"); return

    syms=universe()

    tk=jget(f"{API}/tickers")
    tmap={}
    if tk and tk.get("code")=="00000":
        tmap={r["symbol"]:r for r in tk["data"]}

    books={}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for s,b in ex.map(book,syms): books[s]=b

    outdir=os.path.join(ROOT,"data","live"); os.makedirs(outdir,exist_ok=True)
    src=os.environ.get("NOCTURNE_SOURCE","local")
    path=os.path.join(outdir,f"{et:%Y-%m-%d}.{src}.ndjson")
    reopen=next_reopen(ts)
    rows=[]; ok=0
    for s in syms:
        t=tmap.get(s); b=books.get(s)
        if not t: continue
        try: last=float(t.get("lastPr") or 0)
        except: last=0.0
        row={"t":int(ts.timestamp()),"src":src,"s":s,"sess":sess,"last":last,
             "bid":float(t.get("bidPr") or 0),"ask":float(t.get("askPr") or 0),
             "bidSz":float(t.get("bidSz") or 0),"askSz":float(t.get("askSz") or 0),
             "v24":float(t.get("usdtVolume") or 0)}
        if b and b.get("asks") and b.get("bids"):
            a0=float(b["asks"][0][0]); b0=float(b["bids"][0][0])
            row["spr"]=round((a0-b0)/b0*100,4) if b0 else None
            for pct in DEPTH_PCTS:
                sh,usd=depth(b["asks"],a0,"ask",pct)
                row[f"aSh{pct}"]=sh; row[f"aUsd{pct}"]=usd
                sh,usd=depth(b["bids"],b0,"bid",pct)
                row[f"bSh{pct}"]=sh; row[f"bUsd{pct}"]=usd
            row["lvls"]=[len(b["asks"]),len(b["bids"])]
            ok+=1
        else:
            row["book"]=None
        rows.append(row)

    tmp=path+".tmp"
    with open(tmp,"w",encoding="utf8") as f:
        for r in rows: f.write(json.dumps(r,separators=(",",":"))+"\n")
    with open(path,"a",encoding="utf8") as f, open(tmp,encoding="utf8") as g:
        f.write(g.read())
    os.remove(tmp)

    # hourly full-book snapshot as evidence
    if et.minute<5:
        snapdir=os.path.join(ROOT,"data","books",f"{et:%Y-%m-%d}")
        os.makedirs(snapdir,exist_ok=True)
        snap={s:{"asks":(b["asks"][:20] if b else None),"bids":(b["bids"][:20] if b else None)}
              for s,b in books.items()}
        json.dump({"t":int(ts.timestamp()),"src":src,"sess":sess,"books":snap},
                  open(os.path.join(snapdir,f"{et:%H%M}.json"),"w"),separators=(",",":"))

    status={"last_run":ts.isoformat(),"src":src,"session":sess,"symbols":len(syms),
            "rows":len(rows),"with_book":ok,
            "next_reopen":reopen.isoformat(),"file":os.path.basename(path)}
    json.dump(status,open(os.path.join(ROOT,"data",f"status.{src}.json"),"w"),indent=1)
    print(f"{et:%Y-%m-%d %H:%M ET} sess={sess} rows={len(rows)} books={ok}/{len(syms)} -> {os.path.basename(path)}")

if __name__=="__main__": main()
