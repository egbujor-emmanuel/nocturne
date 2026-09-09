"""Order splitting — the part of Execution Assistance we were missing.

Given an order size and the live book, work out whether it can be filled at
all, what it would cost as a single market order, and how to break it up.

Everything here is arithmetic on the captured book. Nothing is modelled.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import ROOT
from depth import latest_rows
from session import classify, next_reopen, ET, DARK
import datetime as dt

MIN_USDT = 10
BAND = 0.10


def plan(row, usd, side="buy"):
    """Return an execution plan for `usd` notional of one symbol."""
    last = row.get("last") or 0
    if not last:
        return None
    d05 = row.get("aUsd0.5" if side == "buy" else "bUsd0.5") or 0
    d20 = row.get("aUsd2.0" if side == "buy" else "bUsd2.0") or 0
    spread = row.get("spr")

    # how far into the book does this order reach?
    if usd <= d05:
        impact, reach = "under 0.5%", "inside the top of book"
    elif usd <= d20:
        # linear interpolation between the two measured rungs
        frac = (usd - d05) / max(d20 - d05, 1e-9)
        impact, reach = "~%.2f%%" % (0.5 + frac * 1.5), "into the 2% band"
    else:
        impact, reach = "beyond 2%", "deeper than the book we can see"

    # slice so each child order sits inside the half-percent rung
    slices = 1 if usd <= d05 else max(2, min(20, int(usd / max(d05, 1)) + 1))
    per = usd / slices

    return {
        "symbol": row["s"][:-4],
        "side": side,
        "order_usd": round(usd, 2),
        "last": last,
        "spread_pct": spread,
        "depth_0_5_usd": round(d05, 2),
        "depth_2_0_usd": round(d20, 2),
        "fillable_now": usd <= d20,
        "est_impact": impact,
        "reach": reach,
        "suggested_slices": slices,
        "usd_per_slice": round(per, 2),
        "min_order_usdt": MIN_USDT,
        "band_max_buy": round(last * (1 + BAND), 4),
        "band_max_sell": round(last * (1 - BAND), 4),
    }


def advise(plan_, now=None):
    """Plain-language guidance a trader can act on."""
    if not plan_:
        return ["no live book for this symbol"]
    now = now or dt.datetime.now(dt.timezone.utc)
    sess = classify(now)
    out = []
    if not plan_["fillable_now"]:
        out.append("This order is larger than the visible book. You would be the market — "
                   "expect to move the price against yourself.")
    elif plan_["suggested_slices"] > 1:
        out.append("Split into %d slices of about $%s. One market order would move the "
                   "price %s." % (plan_["suggested_slices"],
                                  format(plan_["usd_per_slice"], ",.0f"),
                                  plan_["est_impact"]))
    else:
        out.append("Fits inside the top of the book. A single order should fill "
                   "under 0.5%% impact.")
    if sess in DARK:
        r = next_reopen(now)
        out.append("The US market is shut. Unfilled limit orders are cancelled at %s — "
                   "slices resting past that are lost, not queued."
                   % r.strftime("%Y-%m-%d %H:%M ET"))
    if plan_["spread_pct"] and plan_["spread_pct"] > 0.3:
        out.append("Spread is %.2f%% — wide. Crossing it costs more than the impact "
                   "of the order itself." % plan_["spread_pct"])
    return out


if __name__ == "__main__":
    sym = (sys.argv[1] if len(sys.argv) > 1 else "RAAPL").upper()
    usd = float(sys.argv[2]) if len(sys.argv) > 2 else 50000
    rows = latest_rows()
    key = sym + "USDT" if not sym.endswith("USDT") else sym
    if key not in rows:
        print("no book for", key); sys.exit(1)
    p = plan(rows[key], usd)
    print(json.dumps(p, indent=1))
    print()
    for line in advise(p):
        print(" *", line)
