# Methodology

Every definition needed to reproduce or falsify the results. All times US
Eastern (UTC−4; US DST runs to 2026-11-01, covering the entire study window).

## 1. Sessions

Derived from the tape, not assumed. Turnover collapses at exactly 20:00 ET on
Friday, when US after-hours ends and Bitget's internal matching engine takes
over.

| session | window | what it is |
|---|---|---|
| `RTH` | Mon–Fri 09:30–16:00 | routed to real market liquidity |
| `AH` | Mon–Fri 16:00–20:00 | after-hours, still routed |
| `NIGHT` | Mon–Thu 20:00–04:00 | US shut overnight |
| `PRE` | Mon–Fri 04:00–09:30 | US pre-market |
| `VOID_A` | Fri 20:00 → Sun 19:00 (~47h) | **no external equity price exists anywhere** |
| `PARTIAL_B` | Sun 19:00 → Mon 04:00 (~9h) | index futures live; single names still dark |

Implemented in `scripts/session.py` with boundary assertions.

## 2. The weekend universe

A symbol is weekend-tradeable if it **printed trades inside a completed void
window.** We scanned all 699 listed rTokens against Fri 2026-09-04 20:00 →
Sun 2026-09-06 19:00 ET. 87 qualified.

This is measured, not taken from documentation — the hackathon handbook lists
20. `scripts/scan_universe.py`, output `data/weekend_universe.json`.

## 3. Anchor prices

For each (symbol, weekend):

| symbol | definition |
|---|---|
| `pf` | close of the **Fri 15:00 ET** hourly bar — the last regular-session price |
| `pv` | close of the **Sun 19:00 ET** bar — the end of the void window |
| `pm` | close of the **Mon 10:00 ET** bar — after the re-anchor has completed |

Up to 3 hours of backward slack is allowed for a missing bar. In practice the
exact bar is present in 2,413 of 2,428 cases for the Monday anchor.

Returns:

```
w = pv / pf - 1        void-window return
m = pm / pv - 1        re-anchor return
```

An observation is kept only if all three prices exist and the void window has
**at least 24 hourly bars** — so a partially-listed weekend cannot enter.

## 4. The regression

Pooled OLS of `m` on `w`. The slope is the quantity of interest:

- **β = −1** → the entire void move reverses; the weekend price carried no information
- **β = 0** → the void move persists; it was real information

Noise share is reported as `−β`.

**Universe matters.** Pooling 3x leveraged products (rSOXL, rSOXS, rTQQQ,
rSQQQ, rIQQQ, rQQQM, rQQQI, rTEM) with mega caps inflates the variance ~3x and
suppresses the estimate. Results are reported both pooled and on a homogeneous
large-cap set.

| universe | β | se | t | R² | n |
|---|---|---|---|---|---|
| pooled | −0.692 | 0.162 | −4.28 | 0.086 | 196 |
| large caps | −1.003 | 0.290 | −3.46 | 0.131 | 81 |

**Caveat we state everywhere:** the market-wide component of void drift
effectively has 13 independent observations (one per weekend), not 196. Its
confidence interval is wider than the pooled t-statistic alone suggests.

## 5. Out-of-sample protocol

Walk-forward. For each weekend *k* after a 5-weekend minimum training window,
fit on weekends **< k** only and predict *k*. Nothing reported is in-sample.

Models compared:

| id | prediction |
|---|---|
| `M0` | `m̂ = 0` — the current price is right (**baseline**) |
| `MF` | `m̂ = −w` — the void move fully reverses (**no fitted parameters**) |
| `M1` | `m̂ = a + b·w` — fitted shrinkage |
| `M2` | `m̂ = a + b₁·market + b₂·idiosyncratic` |

`MF` wins; `M1` and `M2` lose to the baseline. Reported in
`data/fairvalue_v2.json`. `scripts/fairvalue_v2.py`.

## 6. Noise Score

Not a probability. A **percentile rank**.

```
z          = (P_now / P_last_regular_close - 1) / sigma_daily
score      = percentile of |z| against that symbol's own historical
             void-window drifts, 0-100
```

`sigma_daily` is the standard deviation of that symbol's regular-session
close-to-close returns. Calibrated per symbol from every void-window hour since
weekend trading began (76 symbols have enough history).

**The score is suppressed whenever the US market is open.** During RTH/AH/PRE
orders route to real liquidity, so movement away from the last close is genuine
price discovery, not drift — and the calibration was built from void windows
only. Showing a score then would be actively misleading.

## 7. Execution figures

Directly observed, never modelled: a 150-level order book snapshot at capture
time, from which we compute shares and USD available before moving the price
0.5% and 2% on each side. The ±10% limit band comes from the API's own
`buyLimitPriceRatio` / `sellLimitPriceRatio`, the $10 minimum from
`minTradeUSDT`.

## 8. The published claims

Each weekend, before the US market reopens:

1. **Level** — Monday 10:00 ET lands closer to `predicted_monday` (the last
   regular close) than to `baseline_monday` (the weekend price), in aggregate
2. **Ranking** — the top-scored third shows a larger mean |Monday move| than
   the bottom third

The file carries a SHA256 of its own contents; the git commit timestamp is the
proof of when it existed. Grading runs Monday from 11:00 ET and publishes the
result regardless of outcome.

Historical hit rate for claim 1 is **7 weekends in 10** — stated in advance, so
a single loss is a predicted outcome rather than a surprise.

## 9. Known limitations

- 13 weekends is a small sample; weekend trading only began 2026-06-12.
- R² is 0.131 on large caps. The relationship is significant but explains a
  minority of Monday's movement.
- Per-symbol betas are not estimated; sample sizes do not support it.
- The Noise Score ranks but is not calibrated to an absolute probability.
- Fair value fails on roughly 3 weekends in 10.
- Fees (0.10% each way) consume roughly a fifth of the theoretical edge on an
  average void move.
