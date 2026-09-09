"""I5: depth, band, and order-lifecycle module.

Turns the captured book into the three execution facts the dashboard shows:

  1. what you can actually trade   - executable shares/USD before you move the
                                     price 0.5% and 2%
  2. where the walls are           - Bitget enforces buy/sellLimitPriceRatio =
                                     0.1, so limit orders outside +/-10% of the
                                     reference price cannot be placed at all
  3. what happens to your order    - unfilled weekend limit orders are cancelled
                                     when the US market reopens (Bitget docs);
                                     we show the countdown

Nothing here is modelled. Every number is observed.
"""
import sys,os,json,glob,datetime as dt
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import ROOT
from session import classify, next_reopen, ET, DARK

BAND=0.10        # buy/sellLimitPriceRatio from Bitget symbol metadata
MIN_USDT=10      # minTradeUSDT

def latest_rows():
    """Newest captured row per symbol, across every capture source."""
    best={}
    for p in sorted(glob.glob(os.path.join(ROOT,"data","live","*.ndjson"))):
        with open(p,encoding="utf8") as f:
            for line in f:
                if not line.strip(): continue
                try: r=json.loads(line)
                except Exception: continue
                s=r.get("s")
                if not s: continue
                if s not in best or r["t"]>best[s]["t"]: best[s]=r
    return best

def report(row,friday_close=None,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    sess=classify(now); reopen=next_reopen(now)
    last=row.get("last") or 0
    ref=friday_close if friday_close else last
    out={
      "symbol":row["s"],"captured":dt.datetime.fromtimestamp(row["t"],ET).strftime("%Y-%m-%d %H:%M ET"),
      "session":sess,"last":last,"bid":row.get("bid"),"ask":row.get("ask"),
      "spread_pct":row.get("spr"),
      "executable":{
        "buy_0.5pct":{"shares":row.get("aSh0.5"),"usd":row.get("aUsd0.5")},
        "sell_0.5pct":{"shares":row.get("bSh0.5"),"usd":row.get("bUsd0.5")},
        "buy_2pct":{"shares":row.get("aSh2.0"),"usd":row.get("aUsd2.0")},
        "sell_2pct":{"shares":row.get("bSh2.0"),"usd":row.get("bUsd2.0")},
      },
      "band":{"reference":round(ref,4),
              "max_buy_limit":round(ref*(1+BAND),4),
              "max_sell_limit":round(ref*(1-BAND),4),
              "pct_of_band_used":round(abs(last/ref-1)/BAND*100,1) if ref else None},
      "min_order_usdt":MIN_USDT,
      "order_lifecycle":{
        "orders_cancelled_at":reopen.strftime("%Y-%m-%d %H:%M ET"),
        "hours_until_cancel":round((reopen-now.astimezone(ET)).total_seconds()/3600,2),
        "applies_now":sess in DARK,
        "source":"Bitget: unfilled weekend limit orders are automatically cancelled when the US market reopens"},
    }
    a=row.get("aUsd0.5"); b=row.get("bUsd0.5")
    if a is not None and b is not None:
        out["liquidity_flag"]=("VERY THIN" if min(a,b)<25_000 else
                               "THIN" if min(a,b)<100_000 else "OK")
    return out

if __name__=="__main__":
    rows=latest_rows()
    print(f"symbols with a captured book: {len(rows)}")
    hdr=f"{'symbol':12s} {'last':>10s} {'spread':>7s} {'buy $ @0.5%':>13s} {'sell $ @0.5%':>13s} {'flag':>10s}"
    print("\n"+hdr); print("-"*len(hdr))
    for s in ["RNVDAUSDT","RAAPLUSDT","RTSLAUSDT","RMSFTUSDT","RAMDUSDT","RASTSUSDT"]:
        if s not in rows: continue
        r=report(rows[s])
        e=r["executable"]
        print(f"{s:12s} {r['last']:10.2f} {str(r['spread_pct']):>7s} "
              f"{(e['buy_0.5pct']['usd'] or 0):13,.0f} {(e['sell_0.5pct']['usd'] or 0):13,.0f} "
              f"{r.get('liquidity_flag',''):>10s}")
    r=report(rows["RNVDAUSDT"])
    print(f"\norder lifecycle: cancelled at {r['order_lifecycle']['orders_cancelled_at']} "
          f"(in {r['order_lifecycle']['hours_until_cancel']}h, applies_now={r['order_lifecycle']['applies_now']})")
    print(f"band: ref={r['band']['reference']} buy<={r['band']['max_buy_limit']} sell>={r['band']['max_sell_limit']}")
