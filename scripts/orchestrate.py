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


if __name__ == "__main__":
    sys.exit(main())
