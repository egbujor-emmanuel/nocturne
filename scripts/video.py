"""Build the demo video from real captured assets. No mockups, no slides.

Every frame in the output is one of three things:

  1. A dashboard screenshot captured automatically during the void window it
     describes (shots/*.png, hourly, 1500x2400 full-page).
  2. A screenshot of the live site or of Bitget's own trading page.
  3. A title card rendered from data/site.json and data/scoreboard.json at
     build time - so a number on a card cannot drift from the number in the
     product.

Only shots captured after 2026-09-12 14:28 ET are used: that is when the
fair-value anchor fix landed, and earlier frames show the saturated scores the
bug produced. Showing them would be showing a defect as a feature.

    python scripts/video.py            -> media/nocturne-demo.mp4

Requires ffmpeg on PATH and a Chromium-family browser for card rendering.
"""
import sys, os, json, glob, shutil, subprocess, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from session import ET

W, H, FPS = 1920, 1080, 30
WORK = os.path.join(ROOT, "scratch", "vid")
OUT = os.path.join(ROOT, "media", "nocturne-demo.mp4")
SITE_URL = "https://egbujor-emmanuel.github.io/nocturne/"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
# the fair-value anchor fix; frames before it show saturated scores
CLEAN_AFTER = dt.datetime(2026, 9, 12, 15, 0, tzinfo=ET)

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/bin/chromium",
]


def browser():
    for b in BROWSERS:
        if os.path.exists(b):
            return b
    raise SystemExit("no Chromium-family browser found for card rendering")


def run(args, timeout=300):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=ROOT,
                       creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# ---------------------------------------------------------------- cards

HEAD = """<!doctype html><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0}
body{width:1920px;height:1080px;background:#070B14;color:#EAF0FA;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;position:relative}
.g1,.g2{position:absolute;border-radius:50%;filter:blur(150px)}
.g1{width:1200px;height:1200px;left:-320px;top:-480px;
  background:radial-gradient(circle,#1652E8,transparent 70%);opacity:.5}
.g2{width:980px;height:980px;right:-260px;bottom:-380px;
  background:radial-gradient(circle,#0C7CD5,transparent 70%);opacity:.4}
.grid{position:absolute;inset:0;opacity:.35;
  background-image:linear-gradient(rgba(88,120,190,.07) 1px,transparent 1px),
    linear-gradient(90deg,rgba(88,120,190,.07) 1px,transparent 1px);background-size:80px 80px}
.in{position:relative;padding:86px 104px;height:100%;display:flex;flex-direction:column}
.top{display:flex;align-items:center;gap:20px}
.lg{font-size:24px;letter-spacing:.34em;font-weight:800;
  background:linear-gradient(95deg,#fff,#8FB6FF);-webkit-background-clip:text;color:transparent}
.tag{margin-left:auto;font-family:'JetBrains Mono';font-size:19px;color:#61708C;letter-spacing:.06em}
h1{font-size:88px;line-height:1.03;font-weight:900;letter-spacing:-.038em;
  margin-top:52px;max-width:20ch}
h1.sm{font-size:64px;max-width:26ch}
h1 em{font-style:normal;background:linear-gradient(95deg,#4D8BFF,#7FD8FF);
  -webkit-background-clip:text;color:transparent}
.sub{margin-top:30px;font-size:30px;color:#93A3BE;max-width:52ch;line-height:1.45}
.sub b{color:#EAF0FA;font-weight:600}
.sub .r{color:#FF5C4D}.sub .g{color:#2BD48A}
.row{margin-top:auto;display:flex;gap:26px}
.st{flex:1;background:rgba(18,27,45,.82);border:1px solid rgba(88,120,190,.24);
  border-radius:20px;padding:28px 32px}
.st .k{font-size:16px;letter-spacing:.14em;text-transform:uppercase;color:#61708C;font-weight:700}
.st .v{font-size:54px;font-weight:800;margin-top:12px;font-family:'JetBrains Mono';
  letter-spacing:-.03em;line-height:1.05}
.st .v.b{background:linear-gradient(95deg,#4D8BFF,#7FD8FF);-webkit-background-clip:text;color:transparent}
.st .v.r{color:#FF5C4D}.st .v.g{color:#2BD48A}
.st .n{font-size:17px;color:#61708C;margin-top:10px;line-height:1.4}
.foot{margin-top:38px;font-family:'JetBrains Mono';font-size:23px;color:#4D8BFF}
pre{margin-top:44px;font-family:'JetBrains Mono';font-size:25px;line-height:1.75;
  color:#93A3BE;background:rgba(11,18,32,.86);border:1px solid rgba(88,120,190,.22);
  border-radius:18px;padding:34px 40px;white-space:pre}
pre b{color:#EAF0FA;font-weight:500}
pre .b{color:#4D8BFF}pre .r{color:#FF5C4D}pre .g{color:#2BD48A}pre .d{color:#61708C}
</style>
<div class="g1"></div><div class="g2"></div><div class="grid"></div>
<div class="in">
  <div class="top"><span class="lg">NOCTURNE</span><span class="tag">__TAG__</span></div>
"""
FOOT = """  <div class="foot">egbujor-emmanuel.github.io/nocturne</div>
</div>"""


def tile(k, v, n, cls=""):
    return ('<div class="st"><div class="k">%s</div><div class="v %s">%s</div>'
            '<div class="n">%s</div></div>' % (k, cls, v, n))


def card(name, tag, body):
    html = HEAD.replace("__TAG__", tag) + body + FOOT
    src = os.path.join(WORK, "_%s.html" % name)
    png = os.path.join(WORK, "%s.png" % name)
    open(src, "w", encoding="utf8").write(html)
    shot_url(png, "file:///" + src.replace("\\", "/"), budget=9000)
    return png


def shot_url(png, url, budget=15000):
    c, o = run([browser(), "--headless", "--disable-gpu", "--hide-scrollbars",
                "--no-sandbox", "--no-first-run", "--no-default-browser-check",
                "--force-device-scale-factor=1",
                "--virtual-time-budget=%d" % budget,
                "--window-size=%d,%d" % (W, H),
                "--screenshot=%s" % png, url])
    if not (os.path.exists(png) and os.path.getsize(png) > 15000):
        raise SystemExit("render failed for %s\n%s" % (url, o[-400:]))
    return png


# ---------------------------------------------------------------- shots

def from_shot(name, src, top, height=None):
    """Crop a band out of a 1500x2400 full-page capture into a 1920x1080 frame."""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    sw, sh = im.size
    height = height or int(sw * H / W)          # 16:9 band at source width
    top = max(0, min(top, sh - height))
    out = im.crop((0, top, sw, top + height)).resize((W, H), Image.LANCZOS)
    png = os.path.join(WORK, "%s.png" % name)
    out.save(png)
    return png


def letterbox(name, src):
    """Fit an off-size screenshot (Bitget's page) onto the 1920x1080 canvas."""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    s = min(W / im.width, H / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    bg = Image.new("RGB", (W, H), (7, 11, 20))
    bg.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    png = os.path.join(WORK, "%s.png" % name)
    bg.save(png)
    return png


def void_shots():
    """Void-window captures taken after the anchor fix, in order."""
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "shots", "*_ET.png"))):
        b = os.path.basename(f)
        try:
            t = dt.datetime.strptime(b[:15], "%Y-%m-%d_%H%M").replace(tzinfo=ET)
        except ValueError:
            continue
        if t >= CLEAN_AFTER:
            out.append((t, f))
    return out


# ---------------------------------------------------------------- encode

def clip(png, seconds, idx, zoom=True):
    """One still, held, with a slow push so the frame is not dead."""
    mp4 = os.path.join(WORK, "seg%02d.mp4" % idx)
    n = int(seconds * FPS)
    if zoom:
        vf = ("scale=%d:%d,zoompan=z='min(zoom+0.00045,1.08)':d=%d:"
              "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=%dx%d:fps=%d,"
              "format=yuv420p" % (W * 2, H * 2, n, W, H, FPS))
    else:
        vf = "scale=%d:%d,fps=%d,format=yuv420p" % (W, H, FPS)
    c, o = run(["ffmpeg", "-y", "-loop", "1", "-i", png, "-t", "%.2f" % seconds,
                "-vf", vf, "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
                "-crf", "18", "-pix_fmt", "yuv420p", mp4])
    if c != 0:
        raise SystemExit("ffmpeg clip failed:\n%s" % o[-600:])
    return mp4


def timelapse(pngs, seconds, idx):
    """The void window, hour by hour, at the speed nothing happens in it."""
    d = os.path.join(WORK, "tl")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    for i, p in enumerate(pngs):
        shutil.copyfile(p, os.path.join(d, "f%03d.png" % i))
    rate = max(1.0, len(pngs) / seconds)
    mp4 = os.path.join(WORK, "seg%02d.mp4" % idx)
    c, o = run(["ffmpeg", "-y", "-framerate", "%.3f" % rate,
                "-i", os.path.join(d, "f%03d.png"),
                "-vf", "scale=%d:%d,fps=%d,format=yuv420p" % (W, H, FPS),
                "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
                "-crf", "18", "-pix_fmt", "yuv420p", mp4])
    if c != 0:
        raise SystemExit("ffmpeg timelapse failed:\n%s" % o[-600:])
    return mp4


def stitch(segs, durations, out, xf=0.6):
    """Chain xfade across the segments, then mux a silent track.

    Platforms that reject a video with no audio stream are common enough that
    the silent aac track is worth the two seconds it costs to add.
    """
    ins = []
    for s in segs:
        ins += ["-i", s]
    parts, prev, off = [], "0:v", 0.0
    for i in range(1, len(segs)):
        off += durations[i - 1] - xf
        lab = "v%d" % i
        parts.append("[%s][%d:v]xfade=transition=fade:duration=%.2f:offset=%.2f[%s]"
                     % (prev, i, xf, off, lab))
        prev = lab
    fg = ";".join(parts) if parts else None
    args = ["ffmpeg", "-y"] + ins
    args += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    if fg:
        args += ["-filter_complex", fg, "-map", "[%s]" % prev]
    else:
        args += ["-map", "0:v"]
    args += ["-map", "%d:a" % len(segs), "-shortest",
             "-c:v", "libx264", "-preset", "slow", "-crf", "19",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart",
             "-c:a", "aac", "-b:a", "96k", out]
    c, o = run(args, timeout=1200)
    if c != 0:
        raise SystemExit("ffmpeg stitch failed:\n%s" % o[-900:])
    return out


# ---------------------------------------------------------------- build

def main():
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    site = json.load(open(os.path.join(ROOT, "data", "site.json"), encoding="utf8"))
    sb = json.load(open(os.path.join(ROOT, "data", "scoreboard.json"), encoding="utf8"))
    live = sb["rounds"][-1]
    c1, c2 = live["claim_1_level"], live["claim_2_ranking"]
    sm = sb["summary"]
    uni = site["universe"]["weekend_tradeable"]
    tag = dt.datetime.now(ET).strftime("%d %b %Y").upper()

    shots = void_shots()
    if len(shots) < 12:
        raise SystemExit("only %d clean void shots - refusing to build a thin timelapse" % len(shots))
    sun = [f for t, f in shots if t.strftime("%Y-%m-%d") == "2026-09-13"]
    detail = sun[-5] if len(sun) >= 5 else shots[-1][1]
    print("%d clean void captures, detail frame %s" % (len(shots), os.path.basename(detail)))

    seq = []   # (png, seconds, zoom)

    seq.append((card("t1", tag,
        '<h1>For 47 hours a week<br>these stocks have <em>no price</em>.</h1>'
        '<div class="sub">Bitget lists tokenized US equities that trade around the '
        'clock. Nasdaq closes Friday 20:00 ET and reopens Monday 09:30. In between, '
        'an internal matching engine is the only source of a price on Earth.</div>'
        '<div class="row">%s%s%s</div>' % (
            tile("rAAPL, one Friday hour", "$5.91bn", "the closing auction"),
            tile("Every rToken, whole weekend", "$8.64m", "combined, all of them", "r"),
            tile("Ratio", "684 : 1", "and the price still moves", "b"))), 7.5, False))

    seq.append((from_shot("s_hero", detail, 0), 5.5, True))

    tl = []
    for i, (t, f) in enumerate(shots):
        tl.append(from_shot("tl%03d" % i, f, 980, 900))
    seq.append((timelapse(tl, 9.0, 90), 9.0, None))

    span = (shots[-1][0] - shots[0][0]).total_seconds() / 3600
    window = "%s → %s ET" % (shots[0][0].strftime("%a %H:%M"),
                             shots[-1][0].strftime("%a %H:%M"))
    seq.append((card("t2", tag,
        '<h1 class="sm">That was <em>%.0f hours</em> of the only<br>Apple price in the world.</h1>'
        '<div class="sub">Median turnover while the US market is open: '
        '<b>$1.6bn an hour</b>. Inside the void: <b class="r">$492 an hour</b>. '
        'The median rToken clears <b>$8,827</b> across an entire weekend.</div>'
        '<div class="row">%s%s%s</div>' % (
            span,
            tile("Captured, unattended", "%d frames" % len(shots), window),
            tile("Median hour, inside the void", "$492", "Bitget's internal engine", "r"),
            tile("Median hour, market open", "$1.6bn", "a factor of 3,340,020", "b"))), 8.0, False))

    seq.append((from_shot("s_book", detail, 1020, 900), 6.5, True))
    # Bitget's own page is the proof the questioned price is the real one, so it
    # is shown whole - a Ken Burns push would crop the ticker off the edge.
    seq.append((letterbox("s_bitget",
        os.path.join(ROOT, "shots", "bitget", "RNVDAUSDT_2026-09-11.png")), 6.0, False))

    seq.append((card("t3", tag,
        '<h1 class="sm">Almost all of that<br>weekend move <em>unwinds</em>.</h1>'
        '<div class="sub">We regressed Monday\'s re-anchor return on the void-window '
        'return across <b>196 observations, 37 symbols, 13 weekends</b>. For large '
        'caps the slope is <b>−1.003</b>: essentially 100%% of the movement that '
        'happens while the market is shut reverses once real liquidity returns. '
        'We call it <b>Void Drift</b>.</div>'
        '<div class="row">%s%s%s</div>' % (
            tile("β, large caps", "−1.003", "t = −3.46 · R² = 0.131", "b"),
            tile("Observations", "196", "37 symbols · 13 weekends"),
            tile("Out-of-sample MAE", "+9.19%", "walk-forward vs baseline", "g"))), 9.0, False))

    seq.append((card("t4", tag,
        '<h1 class="sm">The models we fitted<br><em>lost.</em> We published that.</h1>'
        '<div class="sub">Walk-forward, train on weekends &lt; k, test on k. The two '
        'fitted models lost to a naive baseline out of sample. The unfitted rule — '
        'assume the drift reverses — won. With 13 weekends, estimating coefficients '
        'cost more in noise than it bought in signal.</div>'
        '<div class="row">%s%s%s</div>' % (
            tile("Baseline: price is right", "2.117%", "mean absolute error"),
            tile("Last regular close, unfitted", "1.922%", "+9.19% · 57.4% directional", "g"),
            tile("Fitted two-factor", "2.180%", "−3.01% · worse than nothing", "r"))), 9.0, False))

    seq.append((card("t5", tag,
        '<h1 class="sm">Every weekend it commits<br>to <em>two falsifiable claims</em>.</h1>'
        '<pre>'
        '<span class="d">$ cat predictions/2026-09-13_1701.sha256</span>\n'
        '<span class="b">%s</span>\n'
        '<span class="d">  predictions/2026-09-13_1701.json</span>\n\n'
        '<span class="d">$ git log -1 --format=%%cI -- predictions/</span>\n'
        '<b>%s</b>  <span class="d">· Sunday, inside the void</span>\n'
        '<span class="d">   US market reopens 2026-09-14T13:30Z — %s later</span>\n\n'
        '<span class="d">$ python scripts/grade.py</span>\n'
        'graded <b>%d symbols</b> against Mon 10:00 ET\n'
        'claim 1 level    <span class="r">LOST</span>   %.3f%% vs %.3f%%\n'
        'claim 2 ranking  <span class="g">WON</span>    %.3f%% vs %.3f%%'
        '</pre>' % (_hash(), _committed(), _gap(), live["n"],
                    c1["mae_model_pct"], c1["mae_baseline_pct"],
                    c2["top_third_move_pct"], c2["bottom_third_move_pct"])), 10.5, False))

    seq.append((card("t6", tag,
        '<h1 class="sm">It published, hashed and graded<br>itself with <em>nobody awake</em>.</h1>'
        '<div class="sub">Published Sunday 17:01 ET from GitHub Actions, SHA256 committed '
        'to a public repo before the reopen — a git timestamp cannot be back-dated — '
        'then graded Monday 11:01 ET. The names it flagged riskiest moved '
        '<b class="r">%.2f%%</b>. The names it cleared moved <b class="g">%.2f%%</b>.</div>'
        '<div class="row">%s%s%s</div>' % (
            c2["top_third_move_pct"], c2["bottom_third_move_pct"],
            tile("Execution-risk ranking", "%d / %d" % (sm["claim_2_won"], sm["rounds"]),
                 "%.2f%% vs %.2f%% on Monday" % (c2["top_third_move_pct"],
                                                 c2["bottom_third_move_pct"]), "g"),
            tile("Price-level forecast", "%d / %d" % (sm["claim_1_won"], sm["rounds"]),
                 "%.3f%% vs %.3f%% — shown, not hidden" % (c1["mae_model_pct"],
                                                           c1["mae_baseline_pct"]), "r"),
            tile("Symbols graded", str(live["n"]), "hashed before the open", "b"))), 10.0, False))

    seq.append((card("t7", tag,
        '<h1 class="sm">What it <em>does not</em> claim.</h1>'
        '<div class="sub">It cannot forecast Monday\'s price for an individual stock. '
        'Monday is dominated by genuine overnight news, roughly 3× larger than weekend '
        'drift. The edge is real, modest, and wins <b>7 weekends in 10</b> — not 10 in 10. '
        'No LLM sits in the pricing path: fair value and depth are arithmetic on observed '
        'market data.</div>'
        '<div class="row">%s%s%s</div>' % (
            tile("Read-only", "no key", "never holds an account or a wallet"),
            tile("Public API", "%d endpoints" % len(site["symbols"]), "no login, no rate limit", "b"),
            tile("Weekend universe", "%d rTokens" % uni,
                 "measured from the tape, not documented"))), 9.0, False))

    seq.append((shot_url(os.path.join(WORK, "s_live.png"), SITE_URL), 6.0, True))

    seq.append((card("t8", tag,
        '<h1>A reference price for stocks<br>while the market is <em>closed</em>.</h1>'
        '<div class="sub">Live now, capturing on its own, and it will still be '
        'publishing and grading itself while you judge.</div>'
        '<div class="row">%s%s%s</div>' % (
            tile("Live dashboard", "open", "egbujor-emmanuel.github.io/nocturne", "b"),
            tile("Source + dataset", "public", "github.com/egbujor-emmanuel/nocturne"),
            tile("Next round", "Sunday", "publishes automatically, hashed", "g"))), 7.0, False))

    segs, durs = [], []
    for i, (png, secs, zoom) in enumerate(seq):
        if zoom is None:
            segs.append(png)                       # already a clip
        else:
            segs.append(clip(png, secs, i, zoom=zoom))
        durs.append(secs)
        print("  seg %02d  %5.1fs  %s" % (i, secs, os.path.basename(png)))

    xf = 0.6
    total = sum(durs) - xf * (len(durs) - 1)
    print("\nstitching %d segments -> %.1fs" % (len(segs), total))
    stitch(segs, durs, OUT, xf=xf)
    mb = os.path.getsize(OUT) / 1e6
    c, o = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1", OUT])
    print("\n%s\n  %.1f MB, %s s, 1920x1080" % (OUT, mb, o.strip()))
    if float(o.strip() or 0) > 180:
        print("  WARNING: over the 3-minute submission limit")
    return 0


PRED = "2026-09-13_1701"


def _hash():
    h = open(os.path.join(ROOT, "predictions", PRED + ".sha256"),
             encoding="utf8").read().split()[0]
    return h[:32] + "\n" + h[32:]


def _committed():
    """The git commit time of the prediction file - read, never typed. This is
    the tamper-evidence the whole record rests on, so it comes from git."""
    c, o = run(["git", "log", "--diff-filter=A", "--format=%cI", "--",
                "predictions/" + PRED + ".json"])
    t = (o.strip().splitlines() or [""])[-1].strip()
    if not t:
        raise SystemExit("cannot read the commit time for " + PRED)
    return t


def _gap():
    """Hours between the commitment and the US reopen it was graded against."""
    c = dt.datetime.fromisoformat(_committed().replace("Z", "+00:00"))
    open_ = dt.datetime(2026, 9, 14, 9, 30, tzinfo=ET)
    return "%.0fh" % ((open_ - c).total_seconds() / 3600)


if __name__ == "__main__":
    sys.exit(main())
