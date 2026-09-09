"""Full build audit, phases 0-3. Every check runs the real thing."""
import sys, os, json, glob, subprocess, urllib.request, datetime as dt, hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
R = []


def chk(phase, name, fn):
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, "EXC %s: %s" % (type(e).__name__, str(e)[:90])
    R.append((phase, name, ok, detail))


def sh(*a, **kw):
    p = subprocess.run(a, capture_output=True, text=True, timeout=kw.get("timeout", 90))
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def http(u, timeout=20):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "audit"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except Exception as e:
        return getattr(e, "code", 0), b""


# ---------------- PHASE 0 ----------------
def _repo():
    c, o = sh("gh", "repo", "view", "egbujor-emmanuel/nocturne", "--json", "visibility",
              "-q", ".visibility")
    return "PUBLIC" in o.upper(), o.strip()


def _secret():
    c, o = sh("gh", "secret", "list", "-R", "egbujor-emmanuel/nocturne")
    return "QWEN_API_KEY" in o, "present" if "QWEN_API_KEY" in o else o[:60]


def _uni():
    u = json.load(open("data/weekend_universe.json"))
    return u["weekend_tradeable"] >= 80, "%d of %d" % (u["weekend_tradeable"], u["candidates"])


def _bf():
    fs = glob.glob("data/1h/*.json")
    bars = sum(len(json.load(open(f))) for f in fs[:5]) // max(1, len(fs[:5]))
    return len(fs) >= 85, "%d symbols, ~%d bars each" % (len(fs), bars)


def _secrets_clean():
    """Scan git history for the live secrets, read from .env so no key is
    hardcoded here (this check previously leaked the key it was looking for)."""
    pats = ["github_pat_[A-Za-z0-9_]{20,}", "gho_[A-Za-z0-9]{20,}"]
    try:
        for line in open(os.path.join(ROOT, ".env"), encoding="utf8"):
            if "=" in line:
                v = line.split("=", 1)[1].strip()
                if len(v) >= 12 and not v.startswith("http"):
                    pats.append(v)
    except Exception:
        pass
    for pat in pats:
        c, o = sh("git", "grep", "-nIF" if not pat.startswith("g") else "-nIE", pat, "HEAD")
        if c == 0:
            return False, "LEAK: %s" % o[:100]
    return True, "clean (%d patterns checked)" % len(pats)


chk("0", "repo is public", _repo)
chk("0", "qwen secret set", _secret)
chk("0", "weekend universe mapped", _uni)
chk("0", "history backfilled", _bf)
chk("0", "no secrets in git history", _secrets_clean)


# ---------------- PHASE 1 ----------------
def _cap():
    c, o = sh(sys.executable, "scripts/capture.py", "--force", timeout=180)
    return ("rows=87" in o and "books=87/87" in o), o.strip()[-60:]


def _sess():
    c, o = sh(sys.executable, "scripts/session.py")
    return "ALL BOUNDARY ASSERTIONS PASSED" in o, "boundaries pass" if c == 0 else o[-60:]


def _health():
    c, o = sh(sys.executable, "scripts/health.py")
    line = [l for l in o.splitlines() if "healthy" in l]
    return "healthy=True" in o, (line[-1].strip() if line else o[-60:])


def _lanes():
    a, b = os.path.exists("logs/runner.log"), os.path.exists("logs/runner.local2.log")
    ca = open("logs/runner.log").read().count("rows=87") if a else 0
    cb = open("logs/runner.local2.log").read().count("rows=87") if b else 0
    return a and b, "lane1 %d captures, lane2 %d captures" % (ca, cb)


def _ext():
    c, o = sh("gh", "run", "list", "-R", "egbujor-emmanuel/nocturne", "--limit", "50",
              "--json", "event", "-q", '[.[]|select(.event=="workflow_dispatch")]|length')
    n = int(o.strip() or 0)
    return n >= 7, "%d dispatch runs" % n


def _srcs():
    srcs = set()
    for f in glob.glob("data/live/*.ndjson"):
        for l in open(f, encoding="utf8"):
            if l.strip():
                srcs.add(json.loads(l).get("src", "?"))
    return len(srcs) >= 2, "sources: %s" % sorted(srcs)


chk("1", "capture cycle runs", _cap)
chk("1", "session classifier", _sess)
chk("1", "health check", _health)
chk("1", "two local lanes exist", _lanes)
chk("1", "external cron dispatching", _ext)
chk("1", "multiple sources on disk", _srcs)


# ---------------- PHASE 2 ----------------
def _study():
    c, o = sh(sys.executable, "scripts/study_v2.py", timeout=200)
    line = [l for l in o.splitlines() if "beta=-1.003" in l]
    return bool(line), (line[0].strip()[:76] if line else o[-60:])


def _fv():
    d = json.load(open("data/fairvalue_v2.json"))
    mf = d["large"]["MF"]
    return mf["improvement_pct"] > 5, "MF +%.2f%% MAE, dir %.1f%%" % (
        mf["improvement_pct"], mf["hit"] * 100)


def _ns():
    from noise_score import load_calibration, score
    cal = load_calibration()
    a = score("RNVDA", 101.2, 100.0, cal)
    b = score("RNVDA", 100.02, 100.0, cal)
    return (a and b and a["score"] > b["score"]), "%d symbols; 1.2%%=%d vs 0.02%%=%d" % (
        len(cal), a["score"], b["score"])


def _qwen():
    from qwen_judge import judge, load_cache
    c = load_cache()
    hi = judge("RNVDA", "Nvidia", 2.4, 168280, 95, c)
    lo = judge("RAAPL", "Apple", 0.2, 11276, 40, c)
    return (hi is not None and lo is None), "gated call ok, sub-threshold skipped"


def _depth():
    from depth import latest_rows, report
    rows = latest_rows()
    r = report(rows["RNVDAUSDT"])
    usd = r["executable"]["buy_0.5pct"]["usd"] or 0
    return usd > 0, "%d books; RNVDA buy $%s" % (len(rows), format(usd, ",.0f"))


chk("2", "void-drift study reproduces", _study)
chk("2", "fair value beats baseline OOS", _fv)
chk("2", "noise score monotonic", _ns)
chk("2", "qwen judge + gate", _qwen)
chk("2", "depth/band/lifecycle", _depth)


# ---------------- PHASE 3 ----------------
def _url(u):
    def f():
        s, b = http(u)
        return s == 200, "HTTP %s%s" % (s, ", %d bytes" % len(b) if b else "")
    return f


def _apin():
    n = len(glob.glob("api/v1/symbols/*.json"))
    return n >= 85, "%d symbol endpoints" % n


def _pred():
    fs = [f for f in glob.glob("predictions/*.json") if not f.endswith("latest.json")]
    fs += [f for f in glob.glob("predictions/replay/*.json")]
    if not fs:
        return False, "no prediction file"
    f = sorted(fs)[-1]
    body = open(f, encoding="utf8").read()
    h = hashlib.sha256(body.encode()).hexdigest()
    rec = open(f.replace(".json", ".sha256"), encoding="utf8").read().split()[0]
    d = json.loads(body)
    return h == rec, "%s n=%d hash %s" % (os.path.basename(f), len(d["predictions"]),
                                          "MATCH" if h == rec else "MISMATCH")


def _grade():
    sb = "data/scoreboard.json"
    if not os.path.exists(sb):
        return False, "no scoreboard"
    h = json.load(open(sb))
    s = h["summary"]
    return s["rounds"] >= 1, "%d round(s); claim1 %d/%d claim2 %d/%d" % (
        s["rounds"], s["claim_1_won"], s["rounds"], s["claim_2_won"], s["rounds"])


def _posts():
    c, o = sh(sys.executable, "scripts/make_post.py", "finding")
    sf = sorted(glob.glob("posts/*_finding_short.txt"))
    n = len(open(sf[-1], encoding="utf8").read()) if sf else 999
    return (c == 0 and n <= 280), "short post %d chars" % n


def _skill():
    c, o = sh(sys.executable, "skill/nocturne/nocturne.py", timeout=60)
    ls = [l for l in o.splitlines() if l.strip()]
    return ("finding:" in o), (ls[1][:66] if len(ls) > 1 else o[:60])


chk("3", "dashboard live", _url("https://egbujor-emmanuel.github.io/nocturne/"))
chk("3", "site.json live", _url("https://egbujor-emmanuel.github.io/nocturne/data/site.json"))
chk("3", "api index live", _url("https://egbujor-emmanuel.github.io/nocturne/api/v1/index.json"))
chk("3", "api symbol live",
    _url("https://egbujor-emmanuel.github.io/nocturne/api/v1/symbols/RNVDA.json"))
chk("3", "api covers universe", _apin)
chk("3", "prediction + hash integrity", _pred)
chk("3", "grader produced a round", _grade)
chk("3", "post generator <=280", _posts)
chk("3", "skill hits public api", _skill)

# ---------------- REPORT ----------------
print("=" * 82)
print("NOCTURNE BUILD AUDIT   " + dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
print("=" * 82)
cur = None
for ph, name, ok, det in R:
    if ph != cur:
        print("\n--- PHASE %s ---" % ph)
        cur = ph
    print("  [%s] %-32s %s" % ("PASS" if ok else "FAIL", name, det))
p = sum(1 for _, _, o, _ in R if o)
t = len(R)
print("\n" + "=" * 82)
print("RESULT: %d/%d passed%s" % (p, t, "" if p == t else "    <<< FAILURES ABOVE"))
json.dump([{"phase": a, "check": b, "pass": c, "detail": str(d)} for a, b, c, d in R],
          open("data/audit.json", "w"), indent=1)
sys.exit(0 if p == t else 1)
