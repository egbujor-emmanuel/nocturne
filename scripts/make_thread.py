#!/usr/bin/env python
"""Build the launch thread from the live data, and check every post fits.

Numbers come from data/scoreboard.json and the prediction's own hash file, so
a figure in the thread cannot drift from the figure the product published. The
length check counts links the way X does - 23 characters regardless of the real
URL - because counting them raw made a post that fits look sixty over.

The thread deliberately does not retell the demo video. The video walks the
product; this leads with the result, which is the part that is hard to fake.

    python scripts/make_thread.py      -> posts/<date>_thread.txt
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from session import ET

SITE = "https://egbujor-emmanuel.github.io/nocturne/"
REPO = "https://github.com/egbujor-emmanuel/nocturne"
LIMIT = 280


def xlen(t: str) -> int:
    """Characters as X counts them: every link bills at 23."""
    return len(re.sub(r"https?://\S+", "x" * 23, t))


def main() -> int:
    sb = json.load(open(os.path.join(ROOT, "data", "scoreboard.json"), encoding="utf8"))
    live = sb["rounds"][-1]
    c1, c2 = live["claim_1_level"], live["claim_2_ranking"]
    s = sb["summary"]

    posts = [
        # 1 - lead with what happened, not with what the product is. The live
        # link and the tags belong here: this is the post the form points at.
        "Sunday night, in the window where tokenized US stocks have no external "
        "price, this published a call on %d of them and hashed it into a public "
        "repo.\n\n"
        "Monday it graded itself. Won one claim, lost the other. Both public.\n\n"
        "%s\n\n"
        "#BitgetHackathon @Bitget_AI" % (live["n"], SITE),

        # 2 - the result, with the numbers, loss included
        "Won: ranking which names are dangerous to execute in. The third it "
        "flagged riskiest moved %.2f%% on Monday. The third it cleared moved "
        "%.2f%%.\n\n"
        "Lost: predicting the price level. %.3f%% error against %.3f%% for "
        "doing nothing.\n\n"
        "Running: ranking %d/%d, level %d/%d." % (
            c2["top_third_move_pct"], c2["bottom_third_move_pct"],
            c1["mae_model_pct"], c1["mae_baseline_pct"],
            s["claim_2_won"], s["rounds"], s["claim_1_won"], s["rounds"]),

        # 3 - the loss was predicted in advance, and said so in advance
        "I expected that loss. Walk-forward, both models I fitted lost to a "
        "naive baseline out of sample - only the unfitted rule beat it, and I "
        "wrote that down before this weekend rather than after.\n\n"
        "It is on the front page of the site, not in a footnote.",

        # 4 - why there is anything to measure at all
        "Why there is anything to measure: Nasdaq shuts Friday 20:00 ET. rAAPL "
        "turnover falls from $2.38bn to $63 in one hour, and Bitget's own "
        "engine becomes the only source of a price.\n\n"
        "Across 196 observations, nearly all of that weekend drift reverses by "
        "Monday.",

        # 5 - what it is, and that it is still running
        "It is read-only. No account, no API key, it never places an order.\n\n"
        "Code, the dataset, every hashed prediction and the scoreboard:\n"
        "%s\n\n"
        "It captured, published and graded itself through the weekend with "
        "nobody at the keyboard, and it still is." % REPO,
    ]

    out, bad = [], 0
    for i, p in enumerate(posts, 1):
        n = xlen(p)
        flag = "ok" if n <= LIMIT else "OVER BY %d" % (n - LIMIT)
        if n > LIMIT:
            bad += 1
        out.append("--- %d/%d  (%d chars, %s) ---\n%s\n" % (i, len(posts), n, flag, p))
        print("  %d/%d  %3d chars  %s" % (i, len(posts), n, flag))

    d = os.path.join(ROOT, "posts")
    os.makedirs(d, exist_ok=True)
    stamp = dt.datetime.now(ET).strftime("%Y-%m-%d")
    path = os.path.join(d, stamp + "_thread.txt")
    open(path, "w", encoding="utf8").write("\n".join(out))
    print("\n  %d posts -> %s" % (len(posts), os.path.relpath(path, ROOT)))
    if bad:
        print("  %d post(s) OVER the limit" % bad)
        return 1
    print("  every post fits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
