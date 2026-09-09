# NOCTURNE

**A reference price for stocks while the stock market is closed.**

Bitget lists tokenized US equities (rTokens) that trade 24/7. But Nasdaq closes
Friday 20:00 ET and does not reopen until Monday 09:30 ET. For ~47 hours a week
there is no external price for these assets anywhere on Earth — Bitget's internal
matching engine is the sole price source, and it clears almost no volume.

## The finding

Across 19 tickers and 13 weekends (121 observations), we regressed the re-anchor
return on the void-window return:

| metric | value |
|---|---|
| slope (beta) | **-0.779** |
| t-statistic | **-3.83** |
| observations | 121 |
| **noise share** | **77.9%** |

**About 78% of price movement that happens while the market is closed unwinds
once real liquidity returns.** We call this **Void Drift**.

## Status
Build in progress. See `TASKS.md`.
