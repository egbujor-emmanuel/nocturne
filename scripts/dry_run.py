"""Full weekend dry run.

Exercises the entire Friday-to-Monday chain before the real gate:

  1. capture           - live Bitget data, clock pinned inside a void window
  2. build_state       - scores populate (they are suppressed during RTH)
  3. predict           - hashed, timestamped prediction file
  4. make_post predict - ready-to-paste X post
  5. grade             - against REAL historical Monday prices
  6. make_post grade    - results post
  7. health            - capture still healthy afterwards

Everything it creates is written under a dryrun/ prefix and removed at the end,
so the public record is untouched.
"""
import sys, os, json, glob, shutil, importlib, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
os.chdir(ROOT)

import session as S

FAKE = dt.datetime(2026, 9, 6, 18, 0, tzinfo=S.ET)   # Sunday, deep in the void window
_orig_classify = S.classify
_orig_reopen = S.next_reopen

STEPS = []


def step(n, ok, detail):
    STEPS.append((n, ok, detail))
    print("  [%s] %-28s %s" % ("PASS" if ok else "FAIL", n, detail))


def pin():
    S.classify = lambda t=None: _orig_classify(FAKE)
    S.next_reopen = lambda t=None: _orig_reopen(FAKE)


def unpin():
    S.classify = _orig_classify
    S.next_reopen = _orig_reopen


def snapshot():
    return set(glob.glob("predictions/**/*", recursive=True)) | set(glob.glob("posts/*"))


print("=" * 78)
print("NOCTURNE FULL DRY RUN   simulated clock: %s" % FAKE.strftime("%a %Y-%m-%d %H:%M ET"))
print("=" * 78)
before = snapshot()
sb_path = "data/scoreboard.json"
sb_backup = json.load(open(sb_path)) if os.path.exists(sb_path) else None

pin()
try:
    # 1. capture (live data, void session)
    import capture
    capture.classify = S.classify
    capture.next_reopen = S.next_reopen
    os.environ["NOCTURNE_SOURCE"] = "dryrun"
    sys.argv = ["capture.py", "--force"]
    capture.main()
    rows = glob.glob("data/live/*.dryrun.ndjson")
    n = sum(1 for f in rows for l in open(f, encoding="utf8") if l.strip())
    step("1 capture", n >= 80, "%d rows written" % n)

    # 2. build_state with scores active
    import build_state as B
    B.classify = S.classify
    B.next_reopen = S.next_reopen
    st = B.build()
    scored = sum(1 for r in st["symbols"] if r["noise_score"] is not None)
    step("2 build_state", st["is_dark"] and scored >= 50,
         "session=%s dark=%s scored=%d/%d" % (st["session"], st["is_dark"], scored,
                                              len(st["symbols"])))

    # 3. predict
    import predict as P
    P.classify = S.classify
    P.next_reopen = S.next_reopen
    P.build = B.build
    rc = P.main(force=False)
    fs = sorted(f for f in glob.glob("predictions/*.json") if not f.endswith("latest.json"))
    pf = fs[-1] if fs else None
    import hashlib
    okhash = False
    npred = 0
    if pf:
        body = open(pf, encoding="utf8").read()
        rec = open(pf.replace(".json", ".sha256"), encoding="utf8").read().split()[0]
        okhash = hashlib.sha256(body.encode()).hexdigest() == rec
        npred = len(json.loads(body)["predictions"])
    step("3 predict", rc == 0 and okhash and npred >= 50,
         "%s n=%d hash=%s" % (os.path.basename(pf or "-"), npred,
                              "MATCH" if okhash else "MISMATCH"))

    # 4. prediction post
    import make_post as M
    M.predict()
    sp = sorted(glob.glob("posts/*_predict_short.txt"))
    ln = len(open(sp[-1], encoding="utf8").read()) if sp else 999
    step("4 post predict", ln <= 280, "short post %d chars" % ln)

    # 5. grade against REAL historical Monday prices
    unpin()
    import grade as G
    # never pick a *_graded.json results file - it is not a prediction doc
    replay = sorted(f for f in glob.glob("predictions/replay/*.json")
                    if not f.endswith("_graded.json"))
    rc = G.main(replay[-1]) if replay else 1
    sb = json.load(open(sb_path)) if os.path.exists(sb_path) else {"summary": {}}
    r = sb["rounds"][-1] if sb.get("rounds") else {}
    step("5 grade", rc == 0 and bool(r),
         "n=%s claim1=%s claim2=%s" % (r.get("n"),
                                       "WON" if r.get("claim_1_level", {}).get("won") else "LOST",
                                       "WON" if r.get("claim_2_ranking", {}).get("won") else "LOST"))

    # 6. results post
    M.grade()
    sg = sorted(glob.glob("posts/*_grade_short.txt"))
    lg = len(open(sg[-1], encoding="utf8").read()) if sg else 999
    step("6 post grade", lg <= 280, "short post %d chars" % lg)

    # 7. health after the whole run
    import health
    importlib.reload(health)
    rc = health.main()
    step("7 health", rc == 0, "capture healthy after full chain")

finally:
    unpin()
    # remove everything this run created
    after = snapshot()
    made = sorted(after - before)
    for f in made:
        if os.path.isfile(f):
            os.remove(f)
    for f in glob.glob("data/live/*.dryrun.ndjson"):
        os.remove(f)
    if os.path.exists("data/status.dryrun.json"):
        os.remove("data/status.dryrun.json")
    if sb_backup is not None:
        json.dump(sb_backup, open(sb_path, "w"), indent=1)
    # rebuild real state so nothing is left pinned to the fake clock
    import build_state as B2
    B2.classify = _orig_classify
    B2.next_reopen = _orig_reopen
    B2.build()
    print("\n  cleanup: removed %d dry-run artifacts, scoreboard restored, state rebuilt"
          % len(made))

p = sum(1 for _, o, _ in STEPS if o)
print("\n" + "=" * 78)
print("DRY RUN: %d/%d steps passed%s" % (p, len(STEPS), "" if p == len(STEPS) else "  <<< SEE ABOVE"))
sys.exit(0 if p == len(STEPS) else 1)
