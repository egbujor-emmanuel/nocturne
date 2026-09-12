"""Deep audit. Goes past 'does it run' to 'is it correct'.

audit.py checks components work. This checks the DATA is right, the DOCUMENTS
match the data, and the things that silently rot are still fresh. Written after
the fair-value anchor was found four days stale while every other check was
green.
"""
import sys, os, json, glob, re, subprocess, urllib.request
import datetime as dt
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
os.chdir(ROOT)
from session import classify, ET, DARK, WEEKEND_DARK

R = []


def chk(group, name, fn):
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, "EXC %s: %s" % (type(e).__name__, str(e)[:110])
    R.append((group, name, ok, detail))


def http(u, timeout=25):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "deep-audit"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except Exception as e:
        return getattr(e, "code", 0), b""


def site():
    return json.load(open("data/site.json"))


# ---------------- A · DATA INTEGRITY ----------------
def a_anchor_all():
    """EVERY anchor must be the most recent completed session, not just samples."""
    s = site()
    now = dt.datetime.now(ET)
    bad, ages = [], []
    for r in s["symbols"]:
        at = r.get("reference_close_at")
        if not at:
            bad.append(r["symbol"])
            continue
        t = dt.datetime.strptime(at.replace(" ET", ""), "%Y-%m-%d %H:%M").replace(tzinfo=ET)
        ages.append((now - t).total_seconds() / 3600)
    if bad:
        return False, "%d symbols have no anchor: %s" % (len(bad), bad[:5])
    return max(ages) < 96, "%d anchors, oldest %.1fh, newest %.1fh" % (
        len(ages), max(ages), min(ages))


def a_anchor_is_friday():
    """Inside a weekend window the anchor must be Friday's close, nothing later."""
    s = site()
    if s["session"] not in WEEKEND_DARK:
        return True, "not a weekend window (%s) - skipped" % s["session"]
    days = set()
    for r in s["symbols"]:
        at = r.get("reference_close_at")
        if at:
            days.add(at.split()[0])
    return len(days) == 1, "anchor dates in use: %s" % sorted(days)


def a_drift_sane():
    """Void drift should be small. Large values mean a stale or wrong anchor."""
    s = site()
    d = [abs(r["dislocation_pct"]) for r in s["symbols"] if r.get("dislocation_pct") is not None]
    if not d:
        return True, "no live drifts (scores suppressed)"
    med = st.median(d)
    return med < 3.0, "median |drift| %.2f%%, max %.2f%%" % (med, max(d))


def a_scores_spread():
    s = site()
    sc = [r["noise_score"] for r in s["symbols"] if r.get("noise_score") is not None]
    if not sc:
        return True, "scores suppressed (%s)" % s["session"]
    hi = sum(1 for x in sc if x >= 90) / len(sc)
    return hi < 0.6, "n=%d median=%d, %.0f%% at >=90" % (len(sc), st.median(sc), hi * 100)


def a_capture_gaps():
    """No gap longer than 25 min anywhere in the current void window."""
    cut = None
    s = site()
    now = dt.datetime.now(ET)
    fri = now.date() - dt.timedelta(days=(now.weekday() - 4) % 7)
    cut = dt.datetime.combine(fri, dt.time(20, 0), ET).timestamp()
    ts = set()
    for f in glob.glob("data/live/*.ndjson"):
        for line in open(f, encoding="utf8"):
            if line.strip():
                try:
                    t = json.loads(line)["t"]
                except Exception:
                    continue
                if t >= cut:
                    ts.add(t)
    ts = sorted(ts)
    if len(ts) < 3:
        return True, "void window just opened (%d cycles)" % len(ts)
    gaps = [(b - a) / 60 for a, b in zip(ts, ts[1:]) if (b - a) / 60 > 25]
    return not gaps, "%d cycles, %d gaps>25min%s" % (
        len(ts), len(gaps), (", max %.0fmin" % max(gaps)) if gaps else "")


def a_no_nulls():
    """Live rows must carry a price and a book."""
    s = site()
    noprice = [r["symbol"] for r in s["symbols"] if not r.get("last")]
    nobook = [r["symbol"] for r in s["symbols"] if r.get("buy_usd_0_5") is None]
    return (len(noprice) == 0 and len(nobook) <= 2), \
        "no price: %d, no book: %d %s" % (len(noprice), len(nobook), nobook[:3])


def a_universe_fresh():
    p = "data/weekend_universe.json"
    age = (dt.datetime.now() - dt.datetime.fromtimestamp(os.path.getmtime(p))).total_seconds() / 3600
    u = json.load(open(p))
    return age < 200, "%d of %d, file %.0fh old" % (
        u["weekend_tradeable"], u["candidates"], age)


def a_repo_size():
    out = subprocess.run(["git", "count-objects", "-vH"], capture_output=True, text=True).stdout
    m = re.search(r"size-pack: ([\d.]+) (\w+)", out)
    if not m:
        return True, "unknown"
    v, unit = float(m.group(1)), m.group(2)
    mb = v * (1024 if unit == "GiB" else 1 if unit == "MiB" else 0.001)
    return mb < 900, "pack %.0f MB (GitHub soft limit 1 GB)" % mb


# ---------------- B · DOCUMENTS MATCH THE DATA ----------------
def _docnums(path):
    return open(path, encoding="utf8").read()


def b_readme_beta():
    t = _docnums("README.md")
    return ("-1.003" in t and "-3.46" in t), "beta and t present in README"


def b_walkthrough_live():
    t = _docnums("docs/WALKTHROUGH.md")
    u = json.load(open("data/weekend_universe.json"))
    fv = json.load(open("data/fairvalue_v2.json"))
    need = [str(u["weekend_tradeable"]), "-1.003", "-3.46",
            "%.2f" % fv["large"]["MF"]["improvement_pct"]]
    missing = [n for n in need if n not in t]
    return not missing, "missing from walkthrough: %s" % missing if missing else "all key figures present"


def b_submission_live():
    t = _docnums("docs/SUBMISSION.md")
    missing = [n for n in ["-1.003", "-3.46", "9.19", "87"] if n not in t]
    return not missing, "missing: %s" % missing if missing else "all key figures present"


def b_no_stale_claims():
    """The site must not claim a figure the data no longer supports."""
    s = site()
    f = s["finding"]
    ok = abs(f["beta"] + 1.003) < 0.001 and abs(f["t"] + 3.46) < 0.01
    return ok, "site finding beta=%s t=%s" % (f["beta"], f["t"])


# ---------------- C · THE PIPELINE ----------------
# Modules the running pipeline actually imports. The analysis scripts
# (study_v2, fairvalue_v2, scan_universe...) run their whole analysis at module
# level by design and are only ever invoked as `python scripts/x.py`, so
# importing them here would execute a 699-symbol scan. They get a syntax check.
OPERATIONAL = ["session", "core", "capture", "build_state", "depth", "noise_score",
               "orchestrate", "predict", "grade", "make_post", "card", "shoot",
               "refresh_klines", "netfix", "health", "split"]


def c_scripts_import():
    bad = []
    for n in OPERATIONAL:
        if not os.path.exists(os.path.join("scripts", n + ".py")):
            bad.append(n + "(missing)")
            continue
        p = subprocess.run([sys.executable, "-c", "import %s" % n],
                           capture_output=True, text=True, timeout=60,
                           cwd=os.path.join(ROOT, "scripts"))
        if p.returncode != 0:
            bad.append(n)
    return not bad, "failed: %s" % bad if bad else "all %d operational modules import" % len(OPERATIONAL)


def c_scripts_parse():
    import ast as _ast
    bad = []
    for f in sorted(glob.glob("scripts/*.py")):
        try:
            _ast.parse(open(f, encoding="utf8").read())
        except SyntaxError:
            bad.append(os.path.basename(f))
    return not bad, "syntax errors: %s" % bad if bad else "all %d scripts parse" % len(
        glob.glob("scripts/*.py"))


def c_workflow_valid():
    p = ".github/workflows/nocturne-capture.yml"
    t = open(p, encoding="utf8").read()
    need = ["capture.py", "build_state.py", "orchestrate.py", "shoot.py", "git add -A data/"]
    missing = [n for n in need if n not in t]
    return not missing, "workflow missing: %s" % missing if missing else "all steps present"


def c_no_destructive_checkout():
    t = open("scripts/run_capture.py", encoding="utf8").read()
    bad = 'run(["git","checkout","--ours","."]' in t
    return not bad, "runner cannot clobber the working tree" if not bad else "DESTRUCTIVE CHECKOUT PRESENT"


def c_token_live():
    tok = None
    for ln in open(".env", encoding="utf8"):
        if ln.startswith("GH_DISPATCH_TOKEN="):
            tok = ln.split("=", 1)[1].strip()
    if not tok:
        return False, "no dispatch token"
    req = urllib.request.Request(
        "https://api.github.com/repos/egbujor-emmanuel/nocturne",
        headers={"Accept": "application/vnd.github+json",
                 "Authorization": "Bearer " + tok,
                 "X-GitHub-Api-Version": "2022-11-28"})
    try:
        urllib.request.urlopen(req, timeout=20)
        return True, "dispatch token valid"
    except Exception as e:
        return False, "token HTTP %s" % getattr(e, "code", "?")


def c_secrets_clean():
    pats = ["github_pat_[A-Za-z0-9_]{20,}", "gho_[A-Za-z0-9]{20,}"]
    try:
        for line in open(".env", encoding="utf8"):
            if "=" in line:
                v = line.split("=", 1)[1].strip()
                if len(v) >= 16 and not v.startswith("http"):
                    pats.append(v)
    except Exception:
        pass
    for pat in pats:
        flag = "-nIE" if pat.startswith("g") and "[" in pat else "-nIF"
        p = subprocess.run(["git", "grep", flag, pat, "HEAD"], capture_output=True, text=True)
        if p.returncode == 0:
            return False, "LEAK: %s" % p.stdout[:90]
    return True, "clean (%d patterns)" % len(pats)


# ---------------- D · WHAT THE WORLD SEES ----------------
def d_site_matches_local():
    st_, b = http("https://egbujor-emmanuel.github.io/nocturne/data/site.json")
    if st_ != 200:
        return False, "live site.json HTTP %s" % st_
    live = json.loads(b)
    loc = site()
    same_finding = live["finding"]["beta"] == loc["finding"]["beta"]
    age = "live generated %s" % live.get("generated_et")
    return same_finding, "%s, finding matches local: %s" % (age, same_finding)


def d_live_anchor_fresh():
    st_, b = http("https://egbujor-emmanuel.github.io/nocturne/data/site.json")
    if st_ != 200:
        return False, "HTTP %s" % st_
    live = json.loads(b)
    now = dt.datetime.now(ET)
    ages = []
    for r in live["symbols"]:
        at = r.get("reference_close_at")
        if at:
            t = dt.datetime.strptime(at.replace(" ET", ""), "%Y-%m-%d %H:%M").replace(tzinfo=ET)
            ages.append((now - t).total_seconds() / 3600)
    if not ages:
        return False, "no anchors live"
    return max(ages) < 96, "oldest live anchor %.1fh" % max(ages)


def d_endpoints():
    urls = ["https://egbujor-emmanuel.github.io/nocturne/",
            "https://egbujor-emmanuel.github.io/nocturne/api/v1/index.json",
            "https://egbujor-emmanuel.github.io/nocturne/api/v1/symbols/RNVDA.json"]
    bad = [u for u in urls if http(u)[0] != 200]
    return not bad, "all %d endpoints 200" % len(urls) if not bad else "down: %s" % bad


def d_prediction_integrity():
    import hashlib
    fs = [f for f in glob.glob("predictions/*.json") + glob.glob("predictions/replay/*.json")
          if not f.endswith("latest.json") and not f.endswith("_graded.json")]
    if not fs:
        return True, "no prediction published yet"
    bad = []
    for f in fs:
        body = open(f, encoding="utf8").read()
        try:
            rec = open(f.replace(".json", ".sha256"), encoding="utf8").read().split()[0]
        except Exception:
            bad.append(os.path.basename(f))
            continue
        if hashlib.sha256(body.encode()).hexdigest() != rec:
            bad.append(os.path.basename(f))
    return not bad, "%d files, hashes %s" % (len(fs), "MISMATCH: %s" % bad if bad else "all match")


for g, n, f in [
    ("A data", "every anchor is current", a_anchor_all),
    ("A data", "anchor is Friday inside a weekend", a_anchor_is_friday),
    ("A data", "void drift is plausible", a_drift_sane),
    ("A data", "scores are distributed", a_scores_spread),
    ("A data", "no capture gaps in the void", a_capture_gaps),
    ("A data", "no null prices or books", a_no_nulls),
    ("A data", "universe file fresh", a_universe_fresh),
    ("A data", "repo under the size limit", a_repo_size),
    ("B docs", "README carries the finding", b_readme_beta),
    ("B docs", "walkthrough matches the data", b_walkthrough_live),
    ("B docs", "submission matches the data", b_submission_live),
    ("B docs", "site claims match the study", b_no_stale_claims),
    ("C pipe", "operational modules import", c_scripts_import),
    ("C pipe", "every script parses", c_scripts_parse),
    ("C pipe", "workflow runs the full chain", c_workflow_valid),
    ("C pipe", "runner cannot clobber source", c_no_destructive_checkout),
    ("C pipe", "dispatch token valid", c_token_live),
    ("C pipe", "no secrets in history", c_secrets_clean),
    ("D live", "live site matches local", d_site_matches_local),
    ("D live", "live anchor is fresh", d_live_anchor_fresh),
    ("D live", "all public endpoints up", d_endpoints),
    ("D live", "prediction hashes intact", d_prediction_integrity),
]:
    chk(g, n, f)

print("=" * 86)
print("NOCTURNE DEEP AUDIT   " + dt.datetime.now(ET).strftime("%a %d %b %Y %H:%M ET") +
      "   session=" + classify())
print("=" * 86)
cur = None
for g, n, ok, d in R:
    if g != cur:
        print("\n--- %s ---" % g.upper())
        cur = g
    print("  [%s] %-34s %s" % ("PASS" if ok else "FAIL", n, d))
p = sum(1 for _, _, o, _ in R if o)
print("\n" + "=" * 86)
print("DEEP AUDIT: %d/%d passed%s" % (p, len(R), "" if p == len(R) else "    <<< FAILURES ABOVE"))
json.dump([{"group": a, "check": b, "pass": c, "detail": str(d)} for a, b, c, d in R],
          open("data/deep_audit.json", "w"), indent=2)
sys.exit(0 if p == len(R) else 1)
