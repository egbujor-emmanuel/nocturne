"""Generate ready-to-paste X posts. No Claude required - this is what keeps the
public record going after the build window closes.

  python scripts/make_post.py finding   -> post the research finding
  python scripts/make_post.py predict   -> post the weekend's predictions
  python scripts/make_post.py grade     -> post how they scored

Writes posts/YYYY-MM-DD_<kind>.txt (long) and _short.txt (<=280 chars).
Open it, copy it, post it. Every post carries the hashtags the hackathon requires.
"""
import sys, os, json, glob, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import ROOT
from session import ET

TAGS = "#BitgetHackathon @Bitget_AI"
SITE = "https://egbujor-emmanuel.github.io/nocturne/"
REPO = "https://github.com/egbujor-emmanuel/nocturne"
NL = "\n"


def w(kind, text, short=None):
    """Write a long version and, for accounts without X Premium, a <=280 char one."""
    d = os.path.join(ROOT, "posts")
    os.makedirs(d, exist_ok=True)
    stamp = dt.datetime.now(ET).strftime("%Y-%m-%d")
    p = os.path.join(d, stamp + "_" + kind + ".txt")
    open(p, "w", encoding="utf8").write(text)
    print(text)
    print(NL + "--- " + os.path.relpath(p, ROOT) + "  (" + str(len(text)) +
          " chars - needs X Premium) ---")
    if short:
        ps = os.path.join(d, stamp + "_" + kind + "_short.txt")
        open(ps, "w", encoding="utf8").write(short)
        flag = "OK" if len(short) <= 280 else "STILL TOO LONG"
        print(NL + "SHORT (" + str(len(short)) + " chars - " + flag + "):")
        print(short)
        print("--- " + os.path.relpath(ps, ROOT) + " ---")
    return p


def latest_prediction():
    fs = [f for f in sorted(glob.glob(os.path.join(ROOT, "predictions", "*.json")))
          if not f.endswith("latest.json")]
    return fs[-1] if fs else None


def finding():
    uni = json.load(open(os.path.join(ROOT, "data", "weekend_universe.json")))
    n = uni["weekend_tradeable"]
    long_ = (
        "Bitget lists tokenized US stocks that trade 24/7." + NL * 2 +
        "But Nasdaq shuts Friday 20:00 ET and reopens Monday 09:30." + NL * 2 +
        "For ~47 hours a week there is no external price for these assets anywhere." + NL * 2 +
        "I measured that window across " + str(n) + " rTokens." + NL * 2 +
        "For large caps, ~100% of the price movement while the market is shut reverses "
        "once real liquidity returns. beta = -1.003, t = -3.46, 196 observations." + NL * 2 +
        "I call it Void Drift." + NL * 2 +
        "Live: " + SITE + NL + "Data + code: " + REPO + NL * 2 + TAGS)
    short = (
        "Tokenized US stocks trade 24/7. Nasdaq doesn't." + NL * 2 +
        "For ~47h/week they have no external price anywhere." + NL * 2 +
        "Across " + str(n) + " rTokens: for large caps ~100% of that movement "
        "reverses by Monday. t = -3.46." + NL * 2 +
        "Void Drift." + NL * 2 + SITE + NL + TAGS)
    return w("finding", long_, short)


def predict():
    p = latest_prediction()
    if not p:
        print("no prediction file yet")
        return
    d = json.load(open(p, encoding="utf8"))
    sha = open(p.replace(".json", ".sha256"), encoding="utf8").read().split()[0]
    n = len(d["predictions"])
    long_ = (
        "NOCTURNE - weekend predictions, published before the US market opens." + NL * 2 +
        str(n) + " tokenized US stocks scored during the void window (" +
        d["published_et"] + ")." + NL * 2 +
        "Highest execution risk into Monday:" + NL +
        ", ".join(d["top_risk"][:6]) + NL * 2 +
        "Two claims, graded " + d["graded_against"] + ":" + NL +
        "1. Monday lands closer to Friday's close than to the weekend price" + NL +
        "2. Our top-scored third moves more than our bottom third" + NL * 2 +
        "Claim 1 historically wins 7 weekends in 10. We publish either way." + NL * 2 +
        "SHA256 " + sha[:24] + "..." + NL + SITE + NL * 2 + TAGS)
    short = (
        "NOCTURNE: " + str(n) + " tokenized US stocks scored during this weekend's "
        "void window. Published before the open, hashed." + NL * 2 +
        "Highest execution risk:" + NL + ", ".join(d["top_risk"][:4]) + NL * 2 +
        "Graded " + d["graded_against"] + ". Win or lose." + NL * 2 +
        SITE + NL + TAGS)
    return w("predict", long_, short)


def grade():
    sb = os.path.join(ROOT, "data", "scoreboard.json")
    if not os.path.exists(sb):
        print("no scoreboard yet")
        return
    h = json.load(open(sb))
    r = h["rounds"][-1]
    s = h["summary"]
    c1, c2 = r["claim_1_level"], r["claim_2_ranking"]
    w1 = "WON" if c1["won"] else "LOST"
    w2 = "WON" if c2["won"] else "LOST"
    rec = (str(s["claim_1_won"]) + "/" + str(s["rounds"]) + " and " +
           str(s["claim_2_won"]) + "/" + str(s["rounds"]))
    long_ = (
        "NOCTURNE - how last weekend's predictions actually scored." + NL * 2 +
        "Graded " + str(r["n"]) + " tokenized US stocks against the real " +
        r["target"] + " prices." + NL * 2 +
        "CLAIM 1 (level): " + w1 + NL + "  our error " + str(c1["mae_model_pct"]) +
        "% vs baseline " + str(c1["mae_baseline_pct"]) + "%" + NL * 2 +
        "CLAIM 2 (ranking): " + w2 + NL + "  top third moved " +
        str(c2["top_third_move_pct"]) + "% vs bottom third " +
        str(c2["bottom_third_move_pct"]) + "%" + NL * 2 +
        "Running record: " + rec + NL * 2 +
        "Predictions were hashed and committed before the open. Nothing edited after." +
        NL + SITE + NL * 2 + TAGS)
    short = (
        "NOCTURNE weekend results, " + str(r["n"]) + " tokenized US stocks:" + NL * 2 +
        "CLAIM 1 level: " + w1 + " (" + str(c1["mae_model_pct"]) + "% vs " +
        str(c1["mae_baseline_pct"]) + "%)" + NL +
        "CLAIM 2 ranking: " + w2 + " (" + str(c2["top_third_move_pct"]) + "% vs " +
        str(c2["bottom_third_move_pct"]) + "%)" + NL * 2 +
        "Record: " + rec + ". Hashed before the open." + NL * 2 + SITE + NL + TAGS)
    return w("grade", long_, short)


def launch():
    """The submission post: introduces the product, states the finding, and
    carries the graded result if there is one. This is the URL that goes in the
    hackathon form - Sunday's and Monday's posts both assume the reader already
    knows what NOCTURNE is."""
    uni = json.load(open(os.path.join(ROOT, "data", "weekend_universe.json")))
    n = uni["weekend_tradeable"]
    res = ""
    short_res = ""
    sb = os.path.join(ROOT, "data", "scoreboard.json")
    if os.path.exists(sb):
        try:
            h = json.load(open(sb))
            r = h["rounds"][-1]
            c1, c2 = r["claim_1_level"], r["claim_2_ranking"]
            res = (NL * 2 + "We published this weekend's call before the open, hashed. Result: " +
                   "level " + ("WON" if c1["won"] else "LOST") + ", ranking " +
                   ("WON" if c2["won"] else "LOST") + ". We publish either way.")
            short_res = NL * 2 + "Weekend call published before the open, hashed. Graded " +                         ("WON" if c1["won"] else "LOST") + "/" +                         ("WON" if c2["won"] else "LOST") + "."
        except Exception:
            pass
    long_ = (
        "Introducing NOCTURNE - a reference price for stocks while the stock market "
        "is closed." + NL * 2 +
        "Bitget lists tokenized US equities that trade 24/7. Nasdaq shuts Friday 20:00 ET "
        "and reopens Monday 09:30. For ~47 hours a week these assets have no external "
        "price anywhere on Earth." + NL * 2 +
        "I measured that window across " + str(n) + " rTokens. For large caps, ~100% of the "
        "price movement while the market is shut reverses once real liquidity returns. "
        "beta = -1.003, t = -3.46, 196 observations." + NL * 2 +
        "I call it Void Drift." + NL * 2 +
        "NOCTURNE shows you how far a weekend price has drifted, how much size the book "
        "can actually absorb, and that Bitget cancels your unfilled order at the reopen. "
        "Read-only: no account, no wallet, no API key." + res + NL * 2 +
        "Live: " + SITE + NL + "Code, data and study: " + REPO + NL * 2 + TAGS)
    # the free X limit is 280; the graded result lives in the long version
    short = (
        "NOCTURNE - a reference price for stocks while the market is closed." + NL * 2 +
        "~47h a week, tokenized US stocks have no external price anywhere." + NL * 2 +
        "Across " + str(n) + " rTokens: ~100% of that drift reverses by Monday." + NL * 2 +
        SITE + NL + TAGS)
    return w("launch", long_, short)


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "finding"
    {"finding": finding, "predict": predict, "grade": grade, "launch": launch}.get(kind, finding)()
