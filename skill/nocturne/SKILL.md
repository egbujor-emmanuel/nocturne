---
name: nocturne
description: Check whether a tokenized US stock (rToken) price on Bitget is trustworthy right now. Use when the US market is closed - weekends, overnight, pre-market - and someone asks what an rToken is really worth, how much they can actually trade, whether a weekend move is real, or what happens to their order on Monday. Covers 87 weekend-tradeable rTokens including rNVDA, rAAPL, rTSLA, rMSFT, rMU, rCRCL, rMSTR, rCOIN.
---

# NOCTURNE

A reference price for tokenized US stocks while the US stock market is shut.

## Why this exists

Bitget lists rTokens that trade 24/7, but Nasdaq closes Friday 20:00 ET and
reopens Monday 09:30 ET. For ~47 hours a week there is no external price for
these assets anywhere on Earth. Bitget's internal matching engine is the only
source, and across an entire weekend all 87 weekend-tradeable rTokens combined
clear roughly $8.6M - about 1/684th of what rAAPL alone does in one Friday hour.

Measured across 196 observations and 13 weekends: for large-cap rTokens,
**essentially 100% of the price movement that happens while the market is shut
reverses once real liquidity returns** (beta = -1.003, t = -3.46).

## No API key. No auth. Just fetch.

Everything is static JSON on GitHub Pages.

```
Base: https://egbujor-emmanuel.github.io/nocturne/api/v1
```

| Endpoint | Returns |
|---|---|
| `/index.json` | session state, the headline finding, list of covered symbols |
| `/state.json` | full state for all 87 symbols |
| `/symbols/RNVDA.json` | one symbol (use the rToken symbol, uppercase, no USDT) |

## How to answer questions with it

**"Is this weekend price on rNVDA real?"**
Fetch `/symbols/RNVDA.json`. Read `dislocation_pct` (how far from the last
regular-session close) and `noise_score` (0-100 percentile of that drift against
this symbol's own history). Above 80 means an unusually large drift for this
stock. Report `fair_value` as the reference, not as a forecast.

**"How much can I actually buy?"**
Read `buy_usd_0_5` / `buy_shares_0_5` - the size available before you move the
price half a percent. Many rTokens hold under $25,000 even during US hours.
`liquidity` flags VERY THIN below $25k.

**"What happens to my order?"**
Read `next_reopen_et` from `/index.json`. Bitget cancels all unfilled weekend
limit orders when the US market reopens. Also check `band_max_buy` /
`band_max_sell` - Bitget rejects limit orders outside +/-10% of the reference.

## Reading the fields honestly

- `fair_value` is the last regular-session close. It is a reference point, not
  a prediction of Monday's open.
- `noise_score` **ranks** execution risk. It does not predict direction.
- When `score_applies` is false the US market is open, orders route to real
  market liquidity, and drift from the last close is genuine price discovery.
  Do not describe it as noise in that state.

## What this deliberately does not do

It does not forecast Monday's price. Fitted forecasting models were built and
tested walk-forward; they lost to the naive baseline. Only the unfitted
"assume the drift fully reverses" model wins, and only by about 9% MAE on large
caps, winning 7 weekends in 10. Never present it as more than that.

Source, dataset and the full study: https://github.com/egbujor-emmanuel/nocturne
