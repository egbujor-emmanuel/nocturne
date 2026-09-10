"""P1 core: assemble the current product state into data/site.json.

One file that the dashboard renders and the public API serves. Everything in
it is either directly observed or derived from the validated result:
  fair value during a dark session = the last regular-session close.
"""
import sys,os,json,glob,datetime as dt
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import ROOT, load_bars
from session import classify, next_reopen, ET, DARK
from depth import latest_rows, report as depth_report, BAND
from noise_score import load_calibration, score as noise_of, LARGE, LEVERAGED

NAMES={"RNVDA":"Nvidia","RAAPL":"Apple","RTSLA":"Tesla","RMSFT":"Microsoft",
 "RGOOGL":"Alphabet","RAMZN":"Amazon","RMETA":"Meta","RAMD":"AMD","RAVGO":"Broadcom",
 "RINTC":"Intel","RMU":"Micron","RORCL":"Oracle","RPLTR":"Palantir","RCOIN":"Coinbase",
 "RBABA":"Alibaba","RMSTR":"Strategy","RCRCL":"Circle","RHOOD":"Robinhood",
 "RSNDK":"SanDisk","RMRVL":"Marvell","RASTS":"AST SpaceMobile","RRKLB":"Rocket Lab"}

def ref_close(sym,now):
    """Last regular-session (15:00 ET bar) close before the current dark window."""
    p=os.path.join(ROOT,"data","1h",sym+"USDT.json")
    if not os.path.exists(p): return None,None
    try: b=load_bars(p)
    except Exception: return None,None
    cands=sorted((t for t in b if t.weekday()<5 and t.hour==15 and t<=now.astimezone(ET)),
                 reverse=True)
    if not cands: return None,None
    return b[cands[0]][0], cands[0]

def last_void_snapshot(cal):
    """What the score showed at the end of the most recent completed void window.

    When the US market is open the live score is suppressed by design - but a
    visitor arriving mid-week would then see four empty columns and conclude the
    product is broken. So we surface the last real void window instead, clearly
    labelled as historical.
    """
    from core import load_bars
    out={}; window=None
    for path in glob.glob(os.path.join(ROOT,"data","1h","*.json")):
        sym=os.path.basename(path)[:-9]
        try: b=load_bars(path)
        except Exception: continue
        fris=sorted({t.date() for t in b if t.weekday()==4})
        if not fris: continue
        for fri in reversed(fris):
            sun=fri+dt.timedelta(days=2)
            pf=pv=None
            for k in range(4):
                t=dt.datetime.combine(fri,dt.time(15,0),ET)-dt.timedelta(hours=k)
                if t in b: pf=b[t][0]; break
            for k in range(4):
                t=dt.datetime.combine(sun,dt.time(18,0),ET)-dt.timedelta(hours=k)
                if t in b: pv=b[t][0]; break
            if pf and pv and pf>0:
                ns=noise_of(sym,pv,pf,cal)
                if ns:
                    out[sym]=dict(drift=ns["dislocation_pct"],score=ns["score"],
                                  tier=ns["tier"],fair=round(pf,4),last=round(pv,4))
                    window=window or (fri.isoformat(),sun.isoformat())
                break
    return out,window


def build():
    now=dt.datetime.now(dt.timezone.utc)
    sess=classify(now); cal=load_calibration(); rows=latest_rows()
    out=[]
    for sym_pair,row in rows.items():
        sym=sym_pair[:-4]
        pf,pf_t=ref_close(sym,now)
        last=row.get("last") or 0
        if not last: continue
        d=depth_report(row,friday_close=pf,now=now)
        # The Noise Score is only meaningful while the US market is SHUT.
        # During RTH/PRE/AH the book is routed to real market liquidity and a
        # move away from the last close is genuine price discovery, not drift.
        # The calibration was also built from void windows only.
        ns=noise_of(sym,last,pf,cal) if (pf and sess in DARK) else None
        e=d["executable"]
        out.append({
          "symbol":sym,"pair":sym_pair,"name":NAMES.get(sym,sym.lstrip("R")),
          "last":last,"bid":row.get("bid"),"ask":row.get("ask"),
          "spread_pct":row.get("spr"),
          "reference_close":pf,
          "reference_close_at":pf_t.strftime("%Y-%m-%d %H:%M ET") if pf_t else None,
          "fair_value":pf if sess in DARK else None,
          "score_applies":sess in DARK,
          "score_suppressed_reason":None if sess in DARK else
              f"US market is open ({sess}) - orders route to real liquidity, "
              "so movement away from the last close is genuine price discovery",
          "dislocation_pct":ns["dislocation_pct"] if ns else None,
          "noise_score":ns["score"] if ns else None,
          "tier":ns["tier"] if ns else None,
          "sigma_daily_pct":ns["sigma_daily_pct"] if ns else None,
          "z":ns["z"] if ns else None,
          "buy_usd_0_5":e["buy_0.5pct"]["usd"],"sell_usd_0_5":e["sell_0.5pct"]["usd"],
          "buy_shares_0_5":e["buy_0.5pct"]["shares"],
          "liquidity":d.get("liquidity_flag"),
          "band_max_buy":d["band"]["max_buy_limit"],"band_max_sell":d["band"]["max_sell_limit"],
          "class":"large-cap" if sym in LARGE else ("leveraged" if sym in LEVERAGED else "other"),
          "captured":d["captured"],
        })
    lv,lvwin=({},None)
    if sess not in DARK:
        lv,lvwin=last_void_snapshot(cal)
        for r in out:
            h=lv.get(r["symbol"])
            if h:
                r["last_void"]=h
    out.sort(key=lambda r:(-(r["noise_score"] or (lv.get(r["symbol"],{}).get("score") or -1)),
                           -(r["buy_usd_0_5"] or 0)))
    fv=json.load(open(os.path.join(ROOT,"data","fairvalue_v2.json")))
    uni=json.load(open(os.path.join(ROOT,"data","weekend_universe.json")))
    reopen=next_reopen(now)
    state={
      "generated":now.isoformat(),
      "generated_et":now.astimezone(ET).strftime("%Y-%m-%d %H:%M ET"),
      "session":sess,"is_dark":sess in DARK,
      "next_reopen_et":reopen.strftime("%Y-%m-%d %H:%M ET"),
      "hours_to_reopen":round((reopen-now.astimezone(ET)).total_seconds()/3600,2),
      "band_pct":BAND*100,
      "last_void_window":lvwin,
      "universe":{"weekend_tradeable":uni["weekend_tradeable"],"scanned":uni["candidates"]},
      "finding":{
        "noise_share_large_cap_pct":100.3,"beta":-1.003,"t":-3.46,
        "oos_improvement_pct":round(fv["large"]["MF"]["improvement_pct"],2),
        "oos_direction_pct":round(fv["large"]["MF"]["hit"]*100,1),
        "observations":196,"weekends":13},
      "symbols":out}
    json.dump(state,open(os.path.join(ROOT,"data","site.json"),"w"),indent=1)
    # public API: stable versioned paths served by GitHub Pages
    api=os.path.join(ROOT,"api","v1"); os.makedirs(os.path.join(api,"symbols"),exist_ok=True)
    json.dump(state,open(os.path.join(api,"state.json"),"w"),indent=1)
    json.dump({"generated":state["generated_et"],"session":state["session"],
               "is_dark":state["is_dark"],"next_reopen_et":state["next_reopen_et"],
               "finding":state["finding"],
               "symbols":[r["symbol"] for r in state["symbols"]]},
              open(os.path.join(api,"index.json"),"w"),indent=1)
    for r in state["symbols"]:
        json.dump(r,open(os.path.join(api,"symbols",r["symbol"]+".json"),"w"),indent=1)
    return state

if __name__=="__main__":
    s=build()
    print(f"session={s['session']} dark={s['is_dark']} symbols={len(s['symbols'])}")
    print(f"reopen in {s['hours_to_reopen']}h")
    print(f"\n{'sym':8s} {'name':14s} {'last':>9s} {'ref':>9s} {'disloc':>8s} {'score':>5s} {'buy$0.5%':>10s} {'liq':>10s}")
    for r in s["symbols"][:10]:
        print(f"{r['symbol']:8s} {r['name'][:14]:14s} {r['last']:9.2f} "
              f"{(r['reference_close'] or 0):9.2f} {(r['dislocation_pct'] or 0):+7.2f}% "
              f"{str(r['noise_score']):>5s} {(r['buy_usd_0_5'] or 0):10,.0f} {str(r['liquidity']):>10s}")
