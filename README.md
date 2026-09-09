# NOCTURNE

**A reference price for stocks while the stock market is closed.**

[Live dashboard](https://egbujor-emmanuel.github.io/nocturne/) ·
[Public API](https://egbujor-emmanuel.github.io/nocturne/api/v1/index.json) ·
[Methodology](docs/METHODOLOGY.md) ·
[Agent skill](skill/nocturne/SKILL.md)

---

## The problem

Bitget lists tokenized US equities (rTokens) that trade 24/7. Nasdaq does not —
it closes Friday 20:00 ET and reopens Monday 09:30 ET.

For roughly **47 hours a week these assets have no external price anywhere on
Earth.** Bitget's internal matching engine is the only source, and its own
documentation calls the quotes "indicative."

We measured what that means:

| | |
|---|---|
| rAAPL, one Friday hour (closing auction) | **$5,911,636,056** |
| All 87 weekend-tradeable rTokens, entire weekend | **$8,640,279** |
| **Ratio** | **684 : 1** |
| Median rToken, entire weekend | **$8,827** |

The price of Apple on a Saturday is set by roughly ten thousand dollars of
flow — and it is the only Apple price in the world.

## The finding — Void Drift

Across **196 observations, 37 symbols and 13 weekends**, we regressed the
re-anchor return on the void-window return.

| universe | beta | t | R² | n |
|---|---|---|---|---|
| all names pooled | -0.692 | -4.28 | 0.086 | 196 |
| **large caps only** | **-1.003** | **-3.46** | **0.131** | **81** |

A slope of **-1 means the entire weekend move reverses.** For large-cap
rTokens, essentially 100% of the price movement that happens while the US
market is shut unwinds once real liquidity returns.

The pooled figure was contaminated: 3x leveraged products (rSOXL, rSOXS,
rTQQQ) carry ~3x the volatility and dominated the variance. On a homogeneous
universe the effect is clean and complete.

## Does it beat the obvious baseline?

Walk-forward, training only on weekends before each test weekend:

| model | MAE | vs baseline | directional |
|---|---|---|---|
| baseline — "the current price is right" | 2.117% | — | — |
| **last regular close, unfitted** | **1.922%** | **+9.19%** | 57.4% |
| fitted shrinkage | 2.085% | +1.50% | 50.0% |
| fitted two-factor | 2.180% | **-3.01%** | 44.4% |

**The models we fitted lost. The unfitted one won.** With 13 weekends,
estimating coefficients cost more in noise than it bought in signal.

## What this does NOT claim

It is **not a forecast of Monday's price.** Monday is dominated by genuine
overnight news, roughly 3x larger than weekend drift. The relationship explains
13.1% of variance on large caps. The edge is real, modest, and wins **7 weekends
in 10 — not 10 in 10.**

The Noise Score **ranks** execution risk. It does not predict direction.

## Other things we found

- **The true weekend universe is 87 rTokens, not 20.** We scanned all 699
  listed rTokens against a real void window. The hackathon handbook documents
  20. Published in [`data/weekend_universe.json`](data/weekend_universe.json).
- **A measured session map.** Void A ~47h (Fri 20:00 → Sun 19:00), Partial B
  ~9h, pre-market from Mon 04:00. The volume cliff at Friday 20:00 ET is exact.
- **rSOXL is listed as weekend-tradeable but returns an empty order book.**
- **Documentation corrections:** fees are 0.10%/0.10%, not the expired 0.05%
  promo; the limit band is ±10% per the API's own `buyLimitPriceRatio`, not the
  20% stated in Bitget's guide.
- **Independent pipeline validation:** Bitget launched weekend trading on
  2026-06-12. Our study, which knew nothing of that date, found the first
  qualifying weekend was 2026-06-12.

## The public record

Every weekend the system publishes a prediction **before** the US market
reopens, with a SHA256 of the file committed to this repo. Git's commit
timestamp cannot be back-dated. It then grades itself and publishes the result —
win or lose.

Two falsifiable claims per weekend:

1. **Level** — Monday lands closer to the last regular close than to the
   weekend price
2. **Ranking** — the top-scored third moves more than the bottom third

See [`predictions/`](predictions/) and [`data/scoreboard.json`](data/scoreboard.json).
Backtested round (2026-09-04): claim 1 **lost**, claim 2 **won**. Published as-is.

## Reproduce it

```bash
python scripts/scan_universe.py     # map the weekend-tradeable universe
python scripts/backfill.py 1h       # pull hourly history for it
python scripts/study_v2.py          # the beta = -1.003 result
python scripts/fairvalue_v2.py      # walk-forward out-of-sample test
python scripts/audit.py             # 25 functional checks
```

No API key is required for any of it — Bitget's market endpoints are public.

## Layout

| path | |
|---|---|
| `scripts/` | capture, study, scoring, publishing, audit |
| `data/1h/` | hourly history, 87 symbols |
| `data/live/` | 5-minute tick + order-book capture, tagged by source |
| `api/v1/` | the public JSON API served by GitHub Pages |
| `predictions/` | hashed pre-commitments and their graded results |
| `posts/` | ready-to-paste X posts, generated automatically |
| `shots/` | hourly screenshots of the live page during dark sessions |
| `skill/` | installable agent skill |
| `docs/` | methodology, submission, video script, runbook |

## How it runs

Three independent capture sources — GitHub Actions (triggered externally,
because GitHub's own `schedule` event does not fire on this repo) and two local
scheduled lanes. Each cycle captures, rebuilds state and the API, takes an
hourly screenshot while the market is dark, and runs the orchestrator, which
publishes and grades on its own schedule.

Runtime intelligence is **Qwen** (`qwen3.8-max`), gated and cached, and it
degrades to rule-only if unavailable. **No LLM sits in the pricing path** —
fair value and depth are arithmetic on observed data.

## License

MIT — see [LICENSE](LICENSE).

*Built for Bitget AI Base Camp Hackathon S2. Track 3 — AI Trading Desk,
Execution Assistance.*
