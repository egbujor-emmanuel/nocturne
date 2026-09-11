# Research task walkthrough — question to actionable insight

**Submitted as the Track 3 run record.** One complete research task, start to
finish, using only NOCTURNE and public data. Every number below is reproducible
from this repository.

---

## The question

> *It is Saturday. I hold USDT on Bitget and I want to buy rNVDA. The screen
> shows a price. Should I take it, and how much can I actually get done?*

A trader cannot answer this today. Bitget shows a price with no indication of
whether it is reliable, no view of how much size the book absorbs, and no
warning about what happens to the order on Monday.

---

## Step 1 — Is there even a market? *(the universe question)*

**Task:** establish what is genuinely tradeable during the weekend session.

**Method:** `scripts/scan_universe.py` queries all listed rTokens and tests each
against a completed void window (Fri 20:00 → Sun 19:00 ET), keeping only symbols
that actually printed trades.

**Result:**

| | |
|---|---|
| rToken pairs listed | 699 |
| **Actually traded the void window** | **87** |
| Documented in the hackathon handbook | 20 |

**Insight:** the published list is materially incomplete. 68 names trade the
weekend that no documentation mentions — rCRCL, rMSTR, rCOIN, rHOOD, rPLTR,
rORCL, rBABA, rASML among them. Conversely **rSOXL is listed as weekend-tradeable
but returns a completely empty order book.**

**Action:** trade only from the measured list, published at
`data/weekend_universe.json`.

---

## Step 2 — How much money is actually setting this price?

**Task:** quantify the liquidity behind a weekend quote.

**Method:** median turnover for each of the 168 hours of the week, computed from
our own hourly history across rAAPL, rNVDA, rTSLA and rMSFT. Figures below are
as at 2026-09-11 and are regenerated from the data on every run — the live
values always appear on the dashboard.

**Result:**

| | |
|---|---|
| Median turnover, market open | **$1,642,955,725 / hour** |
| Median turnover, inside the void | **$492 / hour** |
| **Ratio** | **3,340,020 : 1** |
| rAAPL, one Friday closing hour | $5,911,636,056 |
| All 87 rTokens, entire weekend | $8,640,279 |

**Insight:** a single Friday hour of one stock clears **684×** what every
weekend-tradeable rToken clears across an entire weekend. The median rToken
clears **$8,827** over the whole weekend. Apple's Saturday price is set by
roughly ten thousand dollars of flow — and it is the only Apple price on Earth.

**Action:** treat the weekend quote as an indicative number produced by almost
no flow, not as a market price.

---

## Step 3 — Does that price carry information?

**Task:** test whether weekend movement survives contact with real liquidity.

**Method:** for each (symbol, weekend), regress the re-anchor return on the
void-window return.

```
w = P(Sun 19:00 ET) / P(Fri 15:00 ET) − 1      the void move
m = P(Mon 10:00 ET) / P(Sun 19:00 ET) − 1      the re-anchor
```

β = −1 means the void move fully reverses; β = 0 means it persists.

**Result:**

| universe | β | t | R² | n |
|---|---|---|---|---|
| all names pooled | −0.692 | −4.28 | 0.086 | 196 |
| **large caps only** | **−1.003** | **−3.46** | **0.131** | **81** |

The pooled estimate was contaminated: 3× leveraged products (rSOXL, rSOXS,
rTQQQ) carry roughly triple the volatility and dominated the variance. On a
homogeneous universe the effect is clean.

**Insight: for large-cap rTokens essentially 100% of the price movement that
happens while the market is shut unwinds once real liquidity returns.** We call
it **Void Drift**.

**Action:** anchor fair value to the last regular-session close, not to the
weekend quote.

---

## Step 4 — Does that actually beat the obvious alternative?

**Task:** test the anchor out-of-sample before trusting it.

**Method:** walk-forward. For each weekend *k* after a five-weekend minimum
training window, fit on weekends **< k** only and predict *k*. Nothing in-sample.

**Result (large caps):**

| model | MAE | vs baseline | directional |
|---|---|---|---|
| baseline — "the current price is right" | 2.117% | — | — |
| **last regular close, unfitted** | **1.922%** | **+9.19%** | 57.4% |
| fitted shrinkage | 2.085% | +1.50% | 50.0% |
| fitted two-factor | 2.180% | **−3.01%** | 44.4% |

**Insight — and it is a negative one we report deliberately: the models we
fitted lost to the naive baseline. The unfitted one won.** With 13 weekends,
estimating coefficients cost more in noise than it bought in signal.

**Action:** ship the unfitted anchor. State plainly that it wins **7 weekends in
10**, not 10 in 10.

---

## Step 5 — How much can I actually trade?

**Task:** convert the decision into an executable size.

**Method:** `scripts/depth.py` and `scripts/split.py` read a 150-level order book
captured live and compute size available before moving the price 0.5% and 2%.

**Result (observed, during US trading hours — the weekend is thinner):**

| symbol | buy depth @0.5% |
|---|---|
| rNVDA | $631,486 |
| rAAPL | **$18,307** |
| rAMD | **$19,829** |
| rASTS | **$3,953** |

A **$50,000** order in rAAPL: the book holds ~$18k at 0.5%, so a single market
order would move the price ~1.05%. NOCTURNE returns **3 slices of $16,667**.

**Insight:** for most rTokens the binding constraint is not the price, it is that
you are the market. Fees are **0.10% each way** — the 0.05% promotion expired
2026-08-31 — which consumes roughly a fifth of the average edge.

**Action:** size to the book, slice the order, and expect the spread to cost more
than the impact on wide names.

---

## Step 6 — What happens to the order on Monday?

**Task:** check the order's lifecycle across the session boundary.

**Method:** Bitget's own documentation, plus the `buyLimitPriceRatio` /
`sellLimitPriceRatio` fields returned by their symbols endpoint.

**Result:**
- **Unfilled weekend limit orders are cancelled when the US market reopens.** A
  resting order is not queued — it is gone.
- The enforced limit band is **±10%**, per the API's own field, *not* the 20%
  stated in Bitget's written guide.

**Action:** NOCTURNE shows a live countdown to the reopen and the exact band
edges, so an order is never left resting into a cancellation.

---

## The answer

> *Should I take Saturday's price on rNVDA?*

**Only if you have checked four things NOCTURNE puts on one screen:** how far the
price has drifted from Friday's close, how unusual that drift is for this stock,
how much size the book absorbs, and how long before your order is cancelled.

The honest limit, stated on the page itself: **this is not a forecast of Monday's
price.** Monday is dominated by genuine overnight news, roughly 3× larger than
weekend drift. The edge is real, modest, and wins 7 weekends in 10.

---

## Reproduce every step

```bash
python scripts/scan_universe.py    # step 1 — the 87-name universe
python scripts/build_state.py      # step 2 — the 168-hour liquidity profile
python scripts/study_v2.py         # step 3 — beta = -1.003, t = -3.46
python scripts/fairvalue_v2.py     # step 4 — walk-forward, +9.19% MAE
python scripts/split.py RAAPL 50000 # step 5 — order slicing
python scripts/audit.py            # 25 functional checks
```

No API key is required — Bitget's market endpoints are public.

**Live record:** every weekend the system publishes a hashed prediction before
the reopen and grades itself afterwards, win or lose —
[`predictions/`](../predictions/) and
[`data/scoreboard.json`](../data/scoreboard.json).
