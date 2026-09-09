# Dataset

Open data from this study. No API key needed to reproduce any of it — Bitget's
market endpoints are public.

| path | contents |
|---|---|
| `1h/<SYMBOL>USDT.json` | hourly OHLCV, ~4,000 bars per symbol, 87 symbols. Raw Bitget format: `[ts_ms, open, high, low, close, base_vol, quote_vol, usdt_vol]` |
| `live/<date>.<source>.ndjson` | 5-minute capture: last/bid/ask/sizes/spread plus executable depth at ±0.5% and ±2%, one JSON object per line. `source` is `gh`, `local` or `local2` — three independent capture lanes |
| `books/<date>/<HHMM>.json` | hourly top-20 order book snapshots, kept as evidence |
| `weekend_universe.json` | the 87 weekend-tradeable rTokens, with the void-window evidence for each, plus all 699 scanned |
| `fairvalue_v2.json` | walk-forward out-of-sample model comparison |
| `scoreboard.json` | cumulative record of every published claim, won or lost |
| `volume_cliff.json` | rAAPL hourly turnover across the Friday 20:00 ET boundary |
| `noise_calibration.json` | per-symbol daily volatility and void-drift percentile grid |

Timestamps in `live/` are unix seconds UTC. Hourly bars are labelled by open
time. Sessions are US Eastern; see `docs/METHODOLOGY.md`.
