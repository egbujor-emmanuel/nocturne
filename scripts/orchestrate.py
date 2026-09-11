"""Phase 4 autopilot: decides what the weekend needs and does it.

Called on every capture cycle by both the Actions workflow and the local
runners. Idempotent - safe to call every few minutes, all weekend.

  Sunday 17:00 ET -> Monday 04:00 ET   publish the hashed prediction (once)
  Monday  11:00 ET onward              grade it against the real reopen (once)

Both steps also write a ready-to-paste X post. Nothing here needs Claude, a
human, or GitHub's scheduler - only that some capture cycle fires.
"""
import sys, os, json, glob, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from session import classify, ET, DARK

PRED_DIR = os.path.join(ROOT, "predictions")
STATE = os.path.join(ROOT, "data", "orchestrator.json")


def log(m):
    line = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + " " + m
    try:
        os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
        open(os.path.join(ROOT, "logs", "orchestrator.log"), "a", encoding="utf8").write(line + "\n")
    except Exception:
        pass
    print(line)


def weekend_id(now):
    """The Friday date of the void window we are in or just came out of."""
    d = now.astimezone(ET)
    back = (d.weekday() - 4) % 7
    fri = d.date() - dt.timedelta(days=back)
    # before Friday 20:00 the current window is still the PREVIOUS weekend
    if d.weekday() == 4 and d.hour < 20:
        fri = fri - dt.timedelta(days=7)
    return fri.isoformat()


def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {"published": {}, "graded": {}}


def save_state(s):
    json.dump(s, open(STATE, "w"), indent=1)


def in_publish_window(now):
    d = now.astimezone(ET)
    if classify(now) not in DARK:
        return False
    # Sunday from 17:00, or Monday before 04:00 as a catch-up.
    # The catch-up cannot run later than that: from 04:00 ET the session is
    # PRE, noise scores are suppressed by design, and predict would have
    # nothing to publish.
    if d.weekday() == 6 and d.hour >= 17:
        return True
    if d.weekday() == 0 and d.hour < 4:
        return True
    return False


def in_grade_window(now):
    d = now.astimezone(ET)
    return d.weekday() == 0 and d.hour >= 11


def prediction_for(wid):
    """A live prediction file published for this weekend, if any."""
    for f in sorted(glob.glob(os.path.join(PRED_DIR, "*.json"))):
        if f.endswith("latest.json"):
            continue
        try:
            d = json.load(open(f, encoding="utf8"))
        except Exception:
            continue
        if d.get("weekend_id") == wid:
            return f
    return None


def main():
    now = dt.datetime.now(dt.timezone.utc)
    wid = weekend_id(now)
    st = load_state()
    sess = classify(now)
    did = []

    # ---- publish ----
    if in_publish_window(now) and st["published"].get(wid) is None:
        import predict as P
        rc = P.main(force=False)
        if rc == 0:
            fs = [f for f in sorted(glob.glob(os.path.join(PRED_DIR, "*.json")))
                  if not f.endswith("latest.json")]
            if fs:
                f = fs[-1]
                d = json.load(open(f, encoding="utf8"))
                d["weekend_id"] = wid
                # rewrite with the tag, then re-hash so the file and hash still agree
                import hashlib
                body = json.dumps(d, indent=1, sort_keys=True)
                open(f, "w", encoding="utf8").write(body)
                open(f.replace(".json", ".sha256"), "w", encoding="utf8").write(
                    hashlib.sha256(body.encode()).hexdigest() + "  " + os.path.basename(f) + "\n")
                st["published"][wid] = os.path.basename(f)
                save_state(st)
                try:
                    import make_post as M
                    M.predict()
                    try:
                        import card as C
                        C.build("predict")
                    except Exception as e2:
                        log("card predict failed: %s" % str(e2)[:70])
                except Exception as e:
                    log("post predict failed: %s" % str(e)[:80])
                did.append("PUBLISHED " + os.path.basename(f))
        else:
            log("predict declined (rc=%s) session=%s" % (rc, sess))

    # ---- grade ----
    if in_grade_window(now) and st["published"].get(wid) and st["graded"].get(wid) is None:
        f = os.path.join(PRED_DIR, st["published"][wid])
        if os.path.exists(f):
            import grade as G
            rc = G.main(f)
            if rc == 0:
                st["graded"][wid] = True
                save_state(st)
                try:
                    import make_post as M
                    M.grade()
                    try:
                        import card as C
                        C.build("grade")
                    except Exception as e2:
                        log("card grade failed: %s" % str(e2)[:70])
                except Exception as e:
                    log("post grade failed: %s" % str(e)[:80])
                did.append("GRADED " + os.path.basename(f))
            else:
                log("grade declined (rc=%s)" % rc)

    if did:
        log("weekend=%s session=%s -> %s" % (wid, sess, "; ".join(did)))
    else:
        log("weekend=%s session=%s nothing due (published=%s graded=%s)" % (
            wid, sess, bool(st["published"].get(wid)), bool(st["graded"].get(wid))))
    return 0


def selftest():
    """Run the REAL publish path against a pinned clock, then remove what it made.

    Proves post generation works end to end on whatever machine this runs on -
    including the GitHub runner, which is the path that must survive without a
    laptop or an assistant present.
    """
    import hashlib
    import session as S, build_state as B, predict as P, make_post as M

    before = set(glob.glob(os.path.join(PRED_DIR, "*"))) |              set(glob.glob(os.path.join(ROOT, "posts", "*")))
    fake = dt.datetime(2026, 9, 6, 18, 0, tzinfo=S.ET)   # a real past void window
    oc, orr = S.classify, S.next_reopen
    R = []
    try:
        S.classify = lambda t=None: oc(fake)
        S.next_reopen = lambda t=None: orr(fake)
        for mod in (B, P, M):
            if hasattr(mod, "classify"): mod.classify = S.classify
            if hasattr(mod, "next_reopen"): mod.next_reopen = S.next_reopen
        P.build = B.build

        rc = P.main(force=False)
        fs = sorted(f for f in glob.glob(os.path.join(PRED_DIR, "*.json"))
                    if not f.endswith("latest.json") and not f.endswith("_graded.json"))
        newest = fs[-1] if fs else None
        R.append(("predict ran", rc == 0 and newest is not None,
                  os.path.basename(newest) if newest else "no file"))
        if newest:
            body = open(newest, encoding="utf8").read()
            rec = open(newest.replace(".json", ".sha256"), encoding="utf8").read().split()[0]
            n = len(json.loads(body)["predictions"])
            R.append(("hash matches file", hashlib.sha256(body.encode()).hexdigest() == rec,
                      "n=%d" % n))
            R.append(("enough symbols scored", n >= 40, "%d scored" % n))
            M.predict()
            sp = sorted(glob.glob(os.path.join(ROOT, "posts", "*_predict_short.txt")))
            if sp:
                txt = open(sp[-1], encoding="utf8").read()
                R.append(("post written", True, os.path.basename(sp[-1])))
                R.append(("post <= 280 chars", len(txt) <= 280, "%d chars" % len(txt)))
                R.append(("has #BitgetHackathon", "#BitgetHackathon" in txt, ""))
                R.append(("has @Bitget_AI", "@Bitget_AI" in txt, ""))
                R.append(("has live URL", "egbujor-emmanuel.github.io" in txt, ""))
                R.append(("names top risk", "risk" in txt.lower(), ""))
            else:
                R.append(("post written", False, "no post file"))
    finally:
        S.classify, S.next_reopen = oc, orr
        after = set(glob.glob(os.path.join(PRED_DIR, "*"))) |                 set(glob.glob(os.path.join(ROOT, "posts", "*")))
        removed = 0
        for f in sorted(after - before):
            try:
                os.remove(f); removed += 1
            except Exception:
                pass

    print("ORCHESTRATOR SELFTEST")
    for name, ok, det in R:
        print("  [%s] %-24s %s" % ("PASS" if ok else "FAIL", name, det))
    p_ = sum(1 for _, o, _ in R if o)
    print("  %d/%d passed, %d test artifacts removed" % (p_, len(R), removed))
    return 0 if R and p_ == len(R) else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
