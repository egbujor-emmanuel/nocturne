"""Render a 1200x675 social card for the X posts.

A text-only post gets far less reach, and the Sunday post is the one carrying
the pre-commitment. This builds a purpose-made image from live data - not a
crop of the dashboard, which is tall and unreadable at timeline size.

  python scripts/card.py            -> posts/card_<date>.png  (current state)
  python scripts/card.py predict    -> the weekend prediction card
  python scripts/card.py grade      -> the result card
"""
import sys, os, json, subprocess, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from session import ET

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/bin/chromium",
]

TPL = """<!doctype html><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0}
body{width:1200px;height:675px;background:#070B14;color:#EAF0FA;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;position:relative}
.g1,.g2{position:absolute;border-radius:50%;filter:blur(100px)}
.g1{width:760px;height:760px;left:-200px;top:-300px;background:radial-gradient(circle,#1652E8,transparent 70%);opacity:.55}
.g2{width:620px;height:620px;right:-170px;bottom:-240px;background:radial-gradient(circle,#0C7CD5,transparent 70%);opacity:.45}
.grid{position:absolute;inset:0;opacity:.4;
  background-image:linear-gradient(rgba(88,120,190,.07) 1px,transparent 1px),
    linear-gradient(90deg,rgba(88,120,190,.07) 1px,transparent 1px);background-size:54px 54px}
.in{position:relative;padding:52px 60px;height:100%;display:flex;flex-direction:column}
.top{display:flex;align-items:center;gap:14px}
.lg{font-size:17px;letter-spacing:.32em;font-weight:800;
  background:linear-gradient(95deg,#fff,#8FB6FF);-webkit-background-clip:text;color:transparent}
.tag{margin-left:auto;font-family:'JetBrains Mono';font-size:13px;color:#61708C;letter-spacing:.05em}
h1{font-size:57px;line-height:1.04;font-weight:900;letter-spacing:-.035em;margin-top:28px;max-width:19ch}
h1 em{font-style:normal;background:linear-gradient(95deg,#4D8BFF,#7FD8FF);
  -webkit-background-clip:text;color:transparent}
.sub{margin-top:18px;font-size:19px;color:#93A3BE;max-width:56ch;line-height:1.45}
.sub b{color:#EAF0FA}
.row{margin-top:auto;display:flex;gap:16px}
.st{flex:1;background:rgba(18,27,45,.8);border:1px solid rgba(88,120,190,.24);
  border-radius:14px;padding:17px 19px}
.st .k{font-size:11px;letter-spacing:.13em;text-transform:uppercase;color:#61708C;font-weight:700}
.st .v{font-size:33px;font-weight:800;margin-top:7px;font-family:'JetBrains Mono';letter-spacing:-.02em}
.st .v.b{background:linear-gradient(95deg,#4D8BFF,#7FD8FF);-webkit-background-clip:text;color:transparent}
.st .v.r{color:#FF5C4D}.st .v.g{color:#2BD48A}
.st .n{font-size:11.5px;color:#61708C;margin-top:5px}
.foot{margin-top:20px;font-family:'JetBrains Mono';font-size:14px;color:#4D8BFF}
</style>
<div class="g1"></div><div class="g2"></div><div class="grid"></div>
<div class="in">
  <div class="top"><span class="lg">NOCTURNE</span><span class="tag">__TAG__</span></div>
  <h1>__H1__</h1>
  <div class="sub">__SUB__</div>
  <div class="row">__TILES__</div>
  <div class="foot">egbujor-emmanuel.github.io/nocturne</div>
</div>"""


def tile(k, v, n, cls=""):
    return ('<div class="st"><div class="k">%s</div><div class="v %s">%s</div>'
            '<div class="n">%s</div></div>' % (k, cls, v, n))


def browser():
    for b in BROWSERS:
        if os.path.exists(b):
            return b
    return None


def render(html, out):
    tmp = os.path.join(ROOT, "scratch", "_card.html")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, "w", encoding="utf8").write(html)
    b = browser()
    if not b:
        return False, "no browser"
    try:
        subprocess.run([b, "--headless", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
                        "--no-first-run", "--no-default-browser-check",
                        "--virtual-time-budget=7000", "--window-size=1200,675",
                        "--screenshot=%s" % out, "file:///" + tmp.replace("\\", "/")],
                       capture_output=True, timeout=120, creationflags=CREATE_NO_WINDOW)
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, str(e)[:60])
    if os.path.exists(out) and os.path.getsize(out) > 20000:
        return True, "%d bytes" % os.path.getsize(out)
    return False, "no image written"


def build(kind="finding"):
    site = json.load(open(os.path.join(ROOT, "data", "site.json")))
    uni = site["universe"]["weekend_tradeable"]
    now = dt.datetime.now(ET)
    tag = now.strftime("%d %b %Y").upper()

    if kind == "predict":
        tr = site.get("track_record", {}) or {}
        p = tr.get("pending") or {}
        n = p.get("n", "—")
        h1 = "This weekend's call, <em>published before the open</em>."
        sub = ("%s tokenized US stocks scored inside the void window and hashed to a public "
               "repo. Graded Monday — <b>win or lose</b>." % n)
        tiles = (tile("Scored", str(n), "rTokens in the void") +
                 tile("Void drift reverses", "100%", "large caps · t = −3.46", "b") +
                 tile("Graded", "MON", str(p.get("graded_against", "at the reopen"))))
    elif kind == "grade":
        tr = site.get("track_record", {}) or {}
        rs = tr.get("rounds") or []
        r = rs[-1] if rs else {}
        lw = "WON" if r.get("level_won") else "LOST"
        rw = "WON" if r.get("rank_won") else "LOST"
        h1 = "We said it first. <em>Here is how it scored.</em>"
        sub = ("Predictions were hashed and committed before the US market reopened. "
               "Nothing edited after. <b>We publish either way.</b>")
        tiles = (tile("Claim 1 · level", lw, "%s%% vs %s%% baseline" % (
                     r.get("level_model", "—"), r.get("level_base", "—")),
                     "g" if r.get("level_won") else "r") +
                 tile("Claim 2 · ranking", rw, "%s%% vs %s%%" % (
                     r.get("rank_top", "—"), r.get("rank_bottom", "—")),
                     "g" if r.get("rank_won") else "r") +
                 tile("Graded", str(r.get("n", "—")), "tokenized US stocks"))
    else:
        h1 = "For 47 hours a week these stocks have <em>no price</em>."
        sub = ("Tokenized US stocks trade 24/7. Nasdaq does not. In between, an internal "
               "matching engine is the only source of a price — and it clears almost nothing.")
        tiles = (tile("Void drift reverses", "100%", "large caps · β −1.003 · t −3.46", "b") +
                 tile("Weekend market", "$8.64m", "all %d rTokens, whole weekend" % uni, "r") +
                 tile("One Friday hour", "$5.9bn", "rAAPL alone — 684× more"))

    html = (TPL.replace("__TAG__", tag).replace("__H1__", h1)
               .replace("__SUB__", sub).replace("__TILES__", tiles))
    d = os.path.join(ROOT, "posts")
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, "card_%s_%s.png" % (now.strftime("%Y-%m-%d"), kind))
    ok, detail = render(html, out)
    print("%s %s  %s" % ("card" if ok else "FAILED", os.path.relpath(out, ROOT), detail))
    return out if ok else None


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "finding")
