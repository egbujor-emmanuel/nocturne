"""F4: Empirically map the TRUE weekend-tradeable rToken universe.

The hackathon handbook says 20 names. Bitget has since announced +22 and +14.
Nobody has published the actual list. We detect it from the tape: a symbol is
weekend-tradeable if it printed trades inside the last completed void window.
"""
import json,urllib.request,datetime as dt,time,sys
import os as _os, sys as _sys
_sys.path.insert(0,_os.path.dirname(_os.path.abspath(__file__)))
import netfix  # DNS fallback; no-op on a healthy network

ET=dt.timezone(dt.timedelta(hours=-4))
UA={"User-Agent":"Mozilla/5.0"}
def jget(u,tries=3):
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=25))
        except Exception as e:
            if i==tries-1: raise
            time.sleep(1+i)

# last completed void window: Fri 20:00 ET -> Sun 19:00 ET
today=dt.datetime.now(ET).date()
fri=today-dt.timedelta(days=(today.weekday()-4)%7 or 7)
VOID_A=dt.datetime.combine(fri,dt.time(20,0),ET)
VOID_B=dt.datetime.combine(fri+dt.timedelta(days=2),dt.time(19,0),ET)
print(f"void window under test: {VOID_A:%a %Y-%m-%d %H:%M} -> {VOID_B:%a %Y-%m-%d %H:%M} ET",flush=True)

syms=[s["symbol"] for s in jget("https://api.bitget.com/api/v2/spot/public/symbols")["data"]
      if s["symbol"].startswith("R") and s["symbol"].endswith("USDT")
      and s.get("baseCoin","").startswith("r") and s.get("status")=="online"]
print(f"candidate rToken symbols: {len(syms)}",flush=True)

res=[]
for i,s in enumerate(syms,1):
    try:
        d=jget(f"https://api.bitget.com/api/v2/spot/market/candles?symbol={s}&granularity=1h&limit=200")["data"]
    except Exception as e:
        res.append(dict(symbol=s,error=str(e)[:60])); continue
    bars=0; vol=0.0; trades=0
    for r in d:
        t=dt.datetime.fromtimestamp(int(r[0])/1000,ET)
        if VOID_A<=t<VOID_B:
            bars+=1; q=float(r[6]); vol+=q
            if q>0: trades+=1
    res.append(dict(symbol=s,base=s[:-4],void_bars=bars,void_bars_traded=trades,void_usd=round(vol,2)))
    if i%75==0: print(f"  scanned {i}/{len(syms)}",flush=True)
    time.sleep(0.06)

live=[r for r in res if r.get("void_bars_traded",0)>0]
live.sort(key=lambda r:-r["void_usd"])
out=dict(generated=dt.datetime.now(dt.timezone.utc).isoformat(),
         void_window=[VOID_A.isoformat(),VOID_B.isoformat()],
         candidates=len(syms),weekend_tradeable=len(live),
         universe=live,all_results=res)
json.dump(out,open("data/weekend_universe.json","w"),indent=1)
print(f"\n=== WEEKEND-TRADEABLE: {len(live)} of {len(syms)} ===",flush=True)
for r in live[:70]:
    print(f"  {r['base']:10s} bars={r['void_bars']:3d} traded={r['void_bars_traded']:3d} ${r['void_usd']:>12,.0f}")
