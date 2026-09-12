"""Keep data/1h current.

The fair-value anchor is the last regular-session close, read from data/1h.
Those files were written once by backfill.py and never updated, so by Saturday
the anchor was Tuesday's close and "drift" was measuring four days of ordinary
trading instead of the void window. Scores saturated and the weekend prediction
would have been anchored to the wrong price.

This fetches only the recent candles for each symbol and merges them in, so the
anchor is always the most recent real close. Cheap enough to run hourly.
"""
import sys, os, json, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
try:
    import netfix  # noqa: F401  - installs the DoH resolver if DNS is hostile
except Exception:
    pass

API = "https://api.bitget.com/api/v2/spot/market/candles"
UA = {"User-Agent": "nocturne/1.0"}
LIMIT = 200          # ~8 days of hourly bars - ample overlap


def jget(u, tries=2, timeout=15):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout) as r:
                return json.load(r)
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(0.5)


def universe():
    p = os.path.join(ROOT, "data", "weekend_universe.json")
    return [r["symbol"] for r in json.load(open(p))["universe"]]


def refresh(sym):
    """Merge recent candles into the stored history. Returns (added, newest_ms)."""
    path = os.path.join(ROOT, "data", "1h", sym + ".json")
    try:
        rows = json.load(open(path))
    except Exception:
        rows = []
    have = {int(r[0]): r for r in rows}
    d = jget("%s?symbol=%s&granularity=1h&limit=%d" % (API, sym, LIMIT))
    if not d or d.get("code") != "00000":
        return 0, (max(have) if have else 0)
    added = 0
    for r in d.get("data") or []:
        t = int(r[0])
        if t not in have:
            added += 1
        have[t] = r                      # overwrite: the latest bar may be partial
    merged = [have[k] for k in sorted(have)]
    tmp = path + ".tmp"
    json.dump(merged, open(tmp, "w"))
    os.replace(tmp, path)
    return added, (max(have) if have else 0)


def main():
    syms = universe()
    total = 0
    newest = 0
    missed = []
    for s in syms:
        a, n = refresh(s)
        total += a
        newest = max(newest, n)
        if a == 0 and n == 0:
            missed.append(s)
        time.sleep(0.04)
    import datetime as dt
    from session import ET
    ts = dt.datetime.fromtimestamp(newest / 1000, ET) if newest else None
    print("refreshed %d symbols, +%d bars, newest %s%s" % (
        len(syms), total,
        ts.strftime("%a %d %b %H:%M ET") if ts else "none",
        ("  MISSED %d" % len(missed)) if missed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
