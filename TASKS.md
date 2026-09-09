# NOCTURNE — Build Tracker
Submit: **Mon Sep 14, 2026**. All times ET (UTC-4).

Legend: [ ] todo · [~] in progress · [x] done+verified · [!] blocked

## Hard gates
- [ ] **G1** Capture live — Fri Sep 11 20:00 ET (Sat 00:00 UTC)
- [ ] **G2** Predictions published — Sun Sep 13 ~18:00 ET
- [ ] **G3** Graded publicly — Mon Sep 14 ~10:00 ET
- [ ] **G4** Submitted — Mon Sep 14

## Phase 0 — Foundation (Wed Sep 9)
- [x] F1 Public repo created; nocturne-cron-test deleted
- [x] F2 Skeleton, .gitignore, .env.example, TASKS.md
- [ ] F3 Qwen key -> GitHub Secret + local .env
- [x] F4 Universe scan — 87 of 699 rTokens trade the void window (docs say 20)
- [~] F5 Backfill history for full weekend universe (87 symbols)

## Phase 1 — Capture (Wed-Thu, before G1)
- [ ] C1 capture.py (ticker + top-50 book, atomic append)
- [ ] C2 GitHub Actions 5-min cron, commits back
- [ ] C3 Windows Task Scheduler backup runner
- [ ] C4 Session-state classifier (RTH/AH/VoidA/PartialB/premarket)
- [ ] C5 Health check (alert if no data 30 min)

## Phase 2 — Intelligence (Thu)
- [ ] I1 Void-drift study frozen + reproducible (beta = -0.779)
- [ ] I2 Fair-value model per session state
- [ ] I3 Noise Score 0-100
- [ ] I4 Qwen news judge + threshold gate + cache
- [ ] I5 Depth & band module (+/-10% band, $10 min, 0.10% fees)

## Phase 3 — Publishing (Thu-Fri)
- [ ] P1 Dashboard on GitHub Pages
- [ ] P2 Order-lifecycle warning
- [ ] P3 predict.py (Sunday forecast + SHA256)
- [ ] P4 grade.py (Monday actual vs predicted)
- [ ] P5 Public JSON API + skill wrapper

## Phase 4 — Live run (Fri-Mon)
- [ ] L1 G1 capture live
- [ ] L2 Saturday monitoring
- [ ] L3 Demo footage during live void window
- [ ] L4 G2 predictions published
- [ ] L5 X post (#BitgetHackathon @Bitget_AI + retweet)
- [ ] L6 G3 graded publicly

## Phase 5 — Submission (Mon Sep 14)
- [ ] S1 Dataset release + methodology
- [ ] S2 Demo video (<=2 min)
- [ ] S3 Form Parts 1-6
- [ ] S4 G4 submit

## Verified facts (do not re-derive)
- Weekend session opens Fri 20:00 ET; weekend trading launched 2026-06-12
- Fees: maker 0.10% / taker 0.10% (0.05% promo expired Aug 31 2026)
- Limit band: buy/sellLimitPriceRatio = 0.1 (+/-10%), NOT 20%
- minTradeUSDT 10; pricePrecision 2; quantityPrecision 4
- rSOXL returns an EMPTY order book
- Unfilled weekend limit orders auto-cancel at Monday US reopen (Bitget docs)
