"""Keep the fair-value anchor current, without rewriting the archive.

The anchor is the last regular-session (15:00 ET) close. It was being read from
data/1h, which backfill wrote once and never updated - so by Saturday the anchor
was Tuesday's close and "drift" reported four days of ordinary trading as
weekend movement.

The obvious fix - refresh data/1h hourly - would rewrite 38 MB of tracked files
every hour, roughly 1.8 GB of git objects over a weekend, past GitHub's 1 GB
soft limit. So this writes a small hot file instead:

    data/anchors.json   {symbol: {"close": float, "at": "YYYY-MM-DD HH:MM ET"}}

a few KB, refreshed hourly. data/1h stays the cold archive the study reads, and
is refreshed rarely by backfill.py.
"""
import sys, os, json, time, urllib.request, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
try:
    import netfix  # noqa: F401 - installs the DoH resolver if DNS is hostile
except Exception:
    pass
from session import ET

API = "https://api.bitget.com/api/v2/spot/market/candles"
UA = {"User-Agent": "nocturne/1.0"}
OUT = os.path.join(ROOT, "data", "anchors.json")
LIMIT = 200          # ~8 days of hourly bars


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


def last_regular_close(sym):
    """Close of the most recent completed 15:00 ET bar - the last real session price."""
    d = jget("%s?symbol=%s&granularity=1h&limit=%d" % (API, sym, LIMIT))
    if not d or d.get("code") != "00000":
        return None
    best = None
    for r in d.get("data") or []:
        t = dt.datetime.fromtimestamp(int(r[0]) / 1000, ET)
        if t.weekday() < 5 and t.hour == 15:
            if best is None or t > best[0]:
                best = (t, float(r[4]))
    return best


def main():
    syms = universe()
    out = {}
    missed = []
    for s in syms:
        got = last_regular_close(s)
        if got:
            out[s[:-4]] = {"close": got[1], "at": got[0].strftime("%Y-%m-%d %H:%M ET"),
                           "ts": int(got[0].timestamp())}
        else:
            missed.append(s)
        time.sleep(0.04)
    if not out:
        print("refresh failed: no anchors fetched")
        return 1
    payload = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(),
               "generated_et": dt.datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"),
               "anchors": out}
    tmp = OUT + ".tmp"
    json.dump(payload, open(tmp, "w"), indent=1)
    os.replace(tmp, OUT)
    newest = max(v["ts"] for v in out.values())
    print("anchors: %d symbols, newest %s%s, %d bytes" % (
        len(out), dt.datetime.fromtimestamp(newest, ET).strftime("%a %d %b %H:%M ET"),
        ("  MISSED %d" % len(missed)) if missed else "", os.path.getsize(OUT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
