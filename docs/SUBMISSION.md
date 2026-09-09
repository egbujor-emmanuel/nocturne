# NOCTURNE — Bitget AI Base Camp S2 submission

**Track 3 — AI Trading Desk · Sub-theme: Execution Assistance**

Fields marked `[LIVE]` get their final numbers after Monday's grading.
Every other number here is measured and reproducible from this repo.

---

## Part 1 — Thesis: the problem and why existing tools fail

Bitget lists tokenized US equities (rTokens) that trade 24/7. Nasdaq does not.
It closes Friday 20:00 ET and does not reopen until Monday 09:30 ET.

For roughly **47 hours every week these assets have no external price anywhere
on Earth.** Bitget's own documentation is explicit: on weekends an internal
matching engine takes over and quotes are "indicative." We measured what that
means in practice.

**One hour of rAAPL on a Friday clears $5,911,636,056. The entire following
weekend, across all 87 weekend-tradeable rTokens combined, clears $8,640,279.**
A ratio of **684 to 1**. The median rToken clears **$8,827** across an entire
weekend. Apple's price on a Saturday is set by roughly ten thousand dollars of
flow, and that price is the only Apple price in the world.

We then measured whether those weekend prices carry information. Across 196
observations, 37 symbols and 13 weekends we regressed the re-anchor return on
the void-window return. For a homogeneous large-cap universe:

| metric | value |
|---|---|
| slope (beta) | **-1.003** |
| t-statistic | **-3.46** |
| R-squared | 0.131 |
| observations | 81 (13 symbols x 13 weekends) |

**A slope of -1 means the entire weekend move reverses.** For large-cap
rTokens, essentially 100% of the price movement that happens while the US
market is shut unwinds once real liquidity returns. We call it **Void Drift**.

**Why existing tools fail.** Bloomberg does not quote weekend rNVDA.
TradingView does not chart it. Bitget's own interface shows the price but never
indicates it may be unreliable, never shows how much size the book can absorb,
and never warns that unfilled weekend limit orders are cancelled at the reopen.
Bitget's Agent Hub ships five research skills and **every one is crypto-only** —
there is no equity perception layer at all. This is not a better version of an
existing tool. It is the first tool for a market that is three months old.

---

## Part 2 — Target user and product value

**Who.** A crypto-native trader holding USDT who trades rTokens during the
weekend session — the person who sees news on a Saturday and wants to act on it,
or who is holding rToken collateral through the weekend. Narrow and specific,
not "all traders."

**What they get, four things on one screen:**

1. **A reference price.** Fair value during a dark session is the last regular
   session close — validated, not asserted (Part 3).
2. **What they can actually trade.** Executable size in shares and dollars
   before moving the price 0.5% and 2%, computed from a 150-level book at
   capture time. **rAAPL holds $18,307 within half a percent during US trading
   hours.** On a weekend it is far thinner. rSOXL — a documented
   weekend-tradeable name — returns a completely empty book.
3. **Order splitting.** Pick an order size and NOCTURNE shows how many slices it
   would take to fill without moving the price more than half a percent — computed
   from the live book, not modelled. A $50,000 order in rAAPL needs 3 slices; a
   single market order would move the price ~1.05%.
4. **An order-lifecycle warning.** A live countdown to the Monday reopen, when
   Bitget cancels every unfilled weekend limit order. This is one line in
   Bitget's documentation with real money consequences.
5. **A Noise Score.** How far this price has drifted from the last close, in
   units of that symbol's own daily volatility, ranked against its own history.
   It ranks execution risk. It does not predict direction.

**Value:** it stops a bad fill and tells the user when the number on screen is
not to be trusted. It is not a signal service.

---

## Part 3 — Validation data and key metrics

Everything below is walk-forward or directly observed. Nothing is in-sample.

### The core finding

| universe | beta | t | R2 | n |
|---|---|---|---|---|
| all names pooled | -0.692 | -4.28 | 0.086 | 196 |
| **large caps only** | **-1.003** | **-3.46** | **0.131** | **81** |

The pooled figure was contaminated: 3x leveraged products (rSOXL, rSOXS,
rTQQQ) carry roughly triple the volatility and dominated the variance. On a
homogeneous universe the effect is clean and complete.

### Out-of-sample forecast test (walk-forward, train on weekends < k, test on k)

| model | MAE | vs baseline | directional |
|---|---|---|---|
| baseline — "current price is right" | 2.117% | — | — |
| **last close, unfitted** | **1.922%** | **+9.19%** | 57.4% |
| fitted shrinkage | 2.085% | +1.50% | 50.0% |
| fitted two-factor | 2.180% | **-3.01%** | 44.4% |

**The models we fitted lost. The unfitted one won.** We report that plainly.
On the full universe the same unfitted model is +5.32% MAE with 62.8%
directional accuracy.

### Execution-risk ranking (the Noise Score)

| predicted-risk tercile | actual Monday move |
|---|---|
| low | 2.64% |
| middle | 2.91% |
| high | 3.28% |

Monotonic. The ranking works; the magnitude prediction does not (+0.9% over a
constant, which is nothing).

### Original artifacts

- **The true weekend universe: 87 of 699 rTokens**, measured from the tape.
  The hackathon handbook documents 20. Published as `data/weekend_universe.json`.
- **A measured session map.** Void A ~47h (Fri 20:00 -> Sun 19:00), Partial B
  ~9h, pre-market from Mon 04:00. The volume cliff at Friday 20:00 ET is exact.
- **Corrections to the documentation**: fees are 0.10%/0.10%, not the expired
  0.05% promo; the limit band is +/-10% per the API's own
  `buyLimitPriceRatio`, not the 20% stated in Bitget's guide.
- **Independent validation of our pipeline**: Bitget launched weekend trading
  on 2026-06-12. Our study, which knew nothing of that date, found the first
  qualifying weekend was 2026-06-12.

### Live public record

`[LIVE]` Predictions for the 2026-09-11 weekend were published during the void
window with a SHA256 committed to a public repo before the US market opened,
then graded against real reopen prices. Two falsifiable claims, both scored,
win or lose. Historical hit rate for claim 1 is 7 weekends in 10 — stated in
advance so a single loss is a predicted outcome, not a surprise.

Backtested round (2026-09-04 weekend, full replay): claim 1 **lost**
(0.974% vs 0.808%), claim 2 **won** (0.819% vs 0.670%). Published as-is.

### What we do not claim

We cannot forecast Monday's price for an individual stock. Monday is dominated
by genuine overnight news, roughly 3x larger than weekend drift. The
relationship explains 8.6% of variance pooled, 13.1% on large caps. The edge is
real, modest, and wins 7 weekends in 10 — not 10 in 10.

---

## Part 4 — Progress

**Built and verified** (25/25 functional audit, `scripts/audit.py`):
capture from three independent sources; four-regime session classifier; the
void-drift study; fair value; Noise Score across 76 calibrated symbols; a
Qwen news judge, gated and cached; depth/band/order-lifecycle; a live
dashboard; an 87-endpoint public API; hashed prediction publishing; automated
grading; an installable agent skill.

**Known limitations:** 13 weekends is a small sample. The market component of
void drift effectively has 13 independent observations, not 196, so its
confidence interval is wider than the t-statistic alone suggests. The Noise
Score ranks but does not calibrate. Fair value fails on roughly 3 weekends in
10.

**Next:** more weekends; per-symbol betas once samples allow; a collateral
liquidation-distance monitor, since rTokens are accepted as margin at up to 95%
while being priced by this market.

---

## Part 5 — Deliverables

| | |
|---|---|
| Live dashboard | https://egbujor-emmanuel.github.io/nocturne/ |
| Public API (no key) | https://egbujor-emmanuel.github.io/nocturne/api/v1/index.json |
| Source, data and study | https://github.com/egbujor-emmanuel/nocturne |
| Agent skill | `skill/nocturne/SKILL.md` |
| Prediction record | `predictions/` with SHA256 per file |
| Scoreboard | `data/scoreboard.json` |
| Dataset | `data/1h/` (87 symbols), `data/live/` (tick capture) |
| Demo video | `[LIVE]` |

---

## Part 6 — On AI in trading

The useful lesson from this build is negative. We fitted two models to predict
the re-anchor and both lost to a naive baseline out of sample. What won had no
fitted parameters at all: assume the drift fully reverses, because theory and a
significant beta say it should.

With 13 weekends, estimating coefficients cost more in noise than it bought in
signal. AI earned its place here in perception — mapping the tradeable universe,
classifying sessions, reading news, ranking risk — not in prediction. We think
that is the honest boundary for AI in trading today, and we would rather show a
model of ours failing than present a backtest without an out-of-sample split.

---

## Role of the LLM

**Qwen (`qwen3.8-max`) via the hackathon endpoint** is the product's runtime
intelligence. It judges whether news plausibly justifies a void-window move and
returns structured JSON. It is gated to fire only above Noise Score 80, cached
per symbol-hour, and degrades to rule-only if unavailable — so the product never
depends on it being up, and the token budget survives the judging window.

Deliberately: **no LLM sits in the pricing path.** Fair value and depth are
arithmetic on observed data. An LLM that hallucinates a price would be worse
than no product at all.

---

## Form checklist

- [ ] Track 3 -> Execution Assistance
- [ ] Parts 1-6 pasted
- [ ] Role of the LLM
- [ ] Materials link
- [ ] X post link (`#BitgetHackathon` + `@Bitget_AI` + retweet official post)
- [ ] Demo Day checkbox
- [ ] Qwen subsidy checkbox
- [ ] University field — decide deliberately; it opens a separate 10 x 500 USDT pool
