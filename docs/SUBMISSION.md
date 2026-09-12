# NOCTURNE — submission, field by field

Matches the actual Google Form. `[YOU]` = only you can supply it.
`[LIVE]` = final number lands after Monday's grading.

---

## Identity

| Field | Answer |
|---|---|
| Team Name | `[YOU]` |
| Team Lead Bitget UID | `[YOU]` — numbers only |
| Team Lead Email | `[YOU]` |
| Team Lead Contact | `[YOU]` — Telegram handle preferred |
| Member Background | `[YOU]` — Student / Developer / Researcher / Trader / Entrepreneur |
| University Name | `[YOU]` — leave blank unless entering the University Special Award |
| Apply for Demo Day | **Yes** |
| How did you hear about this event? | `[YOU]` |
| Did this team participate in S1? | **Yes** |
| Kimi K3 Token Credits (30U) | **Yes** |
| Open to Playbook Review | **Yes** |

## Track

**Competition Track:** AI Trading Desk
**Competition Sub-theme:** Execution Assistance

## Project Name

**NOCTURNE**

## One-line Project Summary *(140 char max)*

> A reference price for tokenized US stocks while the stock market is closed — and how much you can actually trade before Monday.

*(127 characters)*

---

## Project Description

### Part 1 · Thesis

Bitget lists tokenized US equities that trade 24/7. Nasdaq does not — it closes
Friday 20:00 ET and reopens Monday 09:30. **For roughly 47 hours a week these
assets have no external price anywhere on Earth.** Bitget's own documentation
says an internal matching engine takes over and quotes are "indicative."

We measured what that means. One hour of rAAPL on a Friday clears
**$5,911,636,056**. The entire following weekend, across all 87
weekend-tradeable rTokens combined, clears **$8,640,279** — a ratio of
**684 : 1**. Median turnover per hour is **$1.6bn** while the market is open and
**$492** inside the void, a factor of 3.3 million. The median rToken clears
**$8,827** across an entire weekend.

So we asked whether those prices carry information. Across 196 observations, 37
symbols and 13 weekends we regressed the re-anchor return on the void-window
return:

| universe | β | t | R² | n |
|---|---|---|---|---|
| all names pooled | −0.692 | −4.28 | 0.086 | 196 |
| **large caps only** | **−1.003** | **−3.46** | **0.131** | **81** |

A slope of −1 means the entire weekend move reverses. **For large-cap rTokens,
essentially 100% of the price movement while the US market is shut unwinds once
real liquidity returns.** We call it **Void Drift**.

**Why existing solutions fall short.** Bloomberg does not quote weekend rNVDA.
TradingView does not chart it. Bitget's own screen shows the price but never
indicates it may be unreliable, never shows how much size the book absorbs, and
never warns that unfilled weekend limit orders are cancelled at the reopen.
Bitget's Agent Hub ships five research skills and every one is crypto-only —
there is no equity perception layer at all. This is the first tool for a market
that is three months old.

### Part 2 · Target user and product value

**Who.** Retail and semi-professional crypto-native traders holding USDT on
Bitget, capital roughly $1k–$250k, who trade rTokens **during the weekend
session**. Moderate-to-high risk appetite, episodic rather than high-frequency —
they trade on a headline, not a schedule. Primary market: tokenized US equities
on Bitget spot. Specific use case: news breaks on a Saturday, or they hold
rToken collateral through the weekend, and they must decide whether the screen
price is worth taking.

**Why they need it.** Their reference price is produced by almost no flow, and
they cannot see that. Our order-book capture shows **rAAPL holding $18,307
within half a percent during US trading hours** — thinner still on a weekend —
and rSPMO holding **$2,323**. A $50,000 order in rAAPL moves the price ~1.05% as
a single fill. They are the market and do not know it.

**What existing solutions still fail to solve:** nobody publishes a weekend
reference price, executable depth, or an order-lifecycle warning for these
instruments. Not Bitget, not the data vendors.

### Part 3 · Validation data and key metrics

All figures **observed** unless labelled otherwise. Walk-forward or directly
measured; nothing in-sample.

**Out-of-sample forecast test** — walk-forward, train on weekends < k, test on k:

| model | MAE | vs baseline | directional |
|---|---|---|---|
| baseline — "the current price is right" | 2.117% | — | — |
| **last regular close, unfitted** | **1.922%** | **+9.19%** | 57.4% |
| fitted shrinkage | 2.085% | +1.50% | 50.0% |
| fitted two-factor | 2.180% | **−3.01%** | 44.4% |

**The models we fitted lost to the naive baseline. The unfitted one won.** We
report that plainly. Full universe: +5.32% MAE, 62.8% directional.

**Execution-risk ranking** (observed, tercile means of actual Monday move):
low 2.64% · middle 2.91% · high 3.28% — monotonic.

**Costs, observed:** fees 0.10% each way (the 0.05% promotion expired
2026-08-31), consuming roughly a fifth of the average edge. Limit band ±10% from
the API's own `buyLimitPriceRatio` — not the 20% in Bitget's written guide.

**Original artifacts:** the true weekend universe is **87 of 699 rTokens**,
measured from the tape — the handbook documents 20. A measured session map
(Void A ~47h, Partial B ~9h, pre-market from 04:00). Independent pipeline
validation: Bitget launched weekend trading 2026-06-12, and our study, blind to
that date, found the first qualifying weekend was 2026-06-12.

**Live public record `[LIVE]`.** Every weekend the system publishes two
falsifiable claims **before** the US market reopens, with a SHA256 committed to a
public repo — a git timestamp cannot be back-dated — then grades itself and
publishes the result. Backtested round (2026-09-04): claim 1 **lost**
(0.974% vs 0.808%), claim 2 **won** (0.819% vs 0.670%). Published as-is.

**Distribution and effectiveness — targeted, stated honestly.** We have no users
yet. Our proof is a public, timestamped, self-grading record rather than a usage
claim: predictions hashed before the outcome, graded after, win or lose, running
autonomously through judging. Measurable now: uptime of the live reference price
(observed — capture from three independent sources, zero gaps in the current
void window), and cumulative claim accuracy (observed, published).

**What we do not claim.** We cannot forecast Monday's price for an individual
stock. Monday is dominated by genuine overnight news, roughly 3× larger than
weekend drift. The edge is real, modest, and wins **7 weekends in 10** — not 10
in 10.

### Part 4 · Progress

**Built and verified** — 26 functional checks plus a 22-check data audit:
capture from three independent sources (GitHub Actions via external cron, two
local lanes); a six-state session classifier derived from the tape; the
void-drift study; the fair-value anchor; a Noise Score calibrated across 76
symbols; a Qwen news judge, gated and cached; depth, order-splitting and
order-lifecycle modules; a live dashboard; an 87-endpoint public JSON API;
hashed prediction publishing; automated grading; an installable agent skill.

**Problems hit and solved.** GitHub's own `schedule` event never fired on this
repo despite every documented fix — we route around it with an external cron
hitting `workflow_dispatch`. Our ISP refuses TCP to `www.bitget.com` at the
connection layer, so capture resolves via DNS-over-HTTPS. The capture runner was
executing `git checkout --ours .` on merge conflict and silently reverting source
edits. And the one that mattered most: the fair-value anchor was reading a stale
archive and reporting four days of ordinary trading as weekend drift — every
component check was green throughout, which is why we now audit the data rather
than the code paths.

**Not built:** live order placement (deliberate — NOCTURNE is read-only and never
holds a key), per-symbol betas (sample sizes do not support it), and a collateral
liquidation monitor (next).

**Stack:** Python standard library only, no dependencies. Bitget public spot
market endpoints (symbols, candles, tickers, orderbook — no API key required).
Qwen `qwen3.8-max` via the hackathon endpoint. GitHub Actions and Pages.

### Part 5 · Your take on AI Trading

The useful lesson from this build is negative. We fitted two models to predict
the re-anchor and both lost to a naive baseline out of sample. What won had no
fitted parameters at all: assume the drift reverses, because theory and a
significant β say it should. With 13 weekends, estimating coefficients cost more
in noise than it bought in signal.

AI earned its place here in **perception** — mapping the tradeable universe,
classifying sessions, reading news, ranking risk — not in prediction. We
deliberately kept the LLM out of the pricing path: fair value and depth are
arithmetic on observed data, and a model that hallucinates a price would be worse
than no product. We think that is the honest boundary for AI in trading today,
and we would rather show our own model failing than present a backtest without an
out-of-sample split.

---

## Submission Material Links

```
Project (live demo)   https://egbujor-emmanuel.github.io/nocturne/
Source + dataset      https://github.com/egbujor-emmanuel/nocturne
Run record            https://github.com/egbujor-emmanuel/nocturne/blob/master/docs/WALKTHROUGH.md
Methodology           https://github.com/egbujor-emmanuel/nocturne/blob/master/docs/METHODOLOGY.md
Public API (no key)   https://egbujor-emmanuel.github.io/nocturne/api/v1/index.json
Prediction record     https://github.com/egbujor-emmanuel/nocturne/tree/master/predictions
Scoreboard            https://github.com/egbujor-emmanuel/nocturne/blob/master/data/scoreboard.json
Agent skill           https://github.com/egbujor-emmanuel/nocturne/blob/master/skill/nocturne/SKILL.md
Demo video            [LIVE]
```

Repo is public with a complete README. No login required anywhere.

## Role of the LLM / AI in Your Project

**Qwen `qwen3.8-max`**, via the Bitget hackathon endpoint, is the product's
runtime intelligence. It performs **event and sentiment analysis**: given a
void-window price move and the headlines around it, it returns structured JSON
judging whether real news plausibly justifies a move of that size. It is gated to
fire only above Noise Score 80, cached per symbol-hour, and degrades to
rule-only if unavailable — so the product never depends on it being up.

**Deliberately, no LLM sits in the pricing path.** Fair value, depth, order
splitting and the band are arithmetic on observed market data.

**Claude (Opus)** was used for coding assistance during development. It is not
part of the running system: the product has no dependency on it and continues
publishing and grading itself autonomously.

## X Project Post URL

`[YOU]` — the **launch post**, generated to `posts/*_launch_short.txt`. Post it
Monday quoting Sunday's prediction post, with the demo video attached.

## Material Additions Since S1

S1 was a different project entirely. NOCTURNE shares no code, data, thesis or
architecture with it. New since S1: the Void Drift finding itself (β = −1.003,
t = −3.46, 196 observations) and the walk-forward validation behind it; the
measured 87-name weekend universe against a documented 20; the six-state session
map derived from the tape; a live reference-price product with depth,
order-splitting and order-lifecycle modelling; a three-source capture
architecture; a hashed, self-grading public prediction record; an 87-endpoint
public API and an installable agent skill; and an open dataset. This is not a
rename or an edit of an S1 entry.

---

## Pre-submit checklist

- [ ] Deep audit 22/22 and audit 26/26 green (`python scripts/deep_audit.py`)
- [ ] Monday's grading has run — scoreboard shows the live round
- [ ] Demo video ≤3 min, public (X post or YouTube)
- [ ] Sunday prediction post published
- [ ] Launch post published, quoting Sunday, with the video
- [ ] `[LIVE]` fields filled from the graded result
- [ ] Every material link opens from a logged-out browser
