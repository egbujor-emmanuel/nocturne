# NOCTURNE — Build Tracker
Submit: **Mon Sep 14, 2026**. All times ET (UTC-4).

Legend: [ ] todo · [~] in progress · [x] done+verified · [!] blocked

## Hard gates
- [ ] **G1** Capture live — Fri Sep 11 20:00 ET (Sat 00:00 UTC)
- [ ] **G2** Predictions published — Sun Sep 13 ~18:00 ET
- [ ] **G3** Graded publicly — Mon Sep 14 ~10:00 ET
- [ ] **G4** Submitted — Mon Sep 14

## Phase 0 — Foundation  [COMPLETE]
- [x] F1 Public repo created; nocturne-cron-test deleted
- [x] F2 Skeleton, .gitignore, .env.example, TASKS.md
- [ ] F3 Qwen key -> GitHub Secret + local .env
- [x] F4 Universe scan — 87 of 699 rTokens trade the void window (docs say 20)
- [~] F5 Backfill history for full weekend universe (87 symbols)

## Phase 1 — Capture  [COMPLETE]
- [x] C1 capture.py — 87/87 books in 24s, source-tagged NDJSON
- [x] C2 GitHub Actions 5-min cron — bot commit verified on remote
- [x] C3 Windows Task Scheduler runner — registered, 5-min
- [x] C4 Session classifier — all boundary assertions pass
- [x] C5 Health check — dual-source staleness, fails Actions on outage

## Phase 2 — Intelligence  [COMPLETE]
- [x] I1 Void-drift study frozen + reproducible
- [x] I2 Fair value = Friday close; +9.19% MAE vs baseline out-of-sample (large caps)
- [x] I3 Noise Score 0-100 — percentile of |z| vs symbol's own history, 76 symbols calibrated
- [x] I4 Qwen judge — gated at score>=80, cached, degrades safely
- [x] I5 Depth, band, order-lifecycle module

## Phase 3 — Publishing  [COMPLETE]
- [x] P1 Dashboard — live, rebuilt around the 684:1 cliff
- [x] P2 Order-lifecycle warning
- [x] P3 predict.py — hashed, selftested 9/9 on the GitHub runner
- [x] P4 grade.py — replay-verified on a real weekend
- [x] P5 Public API (87 endpoints) + agent skill

## Phase 4 — Live run (Fri-Mon)
- [~] L1 capture live at the gate — automatic, 3 sources armed
- [~] L2 weekend monitoring — automatic + hourly screenshots
- [~] L3 footage — auto-screenshots running; optional human recording
- [~] L4 prediction publishes Sunday — automatic, verified
- [ ] L5 X post — YOU paste from posts/
- [~] L6 grading Monday — automatic, verified

## Phase 5 — Submission (Mon Sep 14)
- [x] S1 Dataset + METHODOLOGY.md + README + LICENSE
- [ ] S2 Demo video — assemble from screenshots once the void window opens
- [~] S3 Form Parts 1-6 drafted in docs/SUBMISSION.md; [LIVE] fields pending
- [ ] S4 SUBMIT — Sunday night, after the prediction publishes

## Verified facts (do not re-derive)
- Weekend session opens Fri 20:00 ET; weekend trading launched 2026-06-12
- Fees: maker 0.10% / taker 0.10% (0.05% promo expired Aug 31 2026)
- Limit band: buy/sellLimitPriceRatio = 0.1 (+/-10%), NOT 20%
- minTradeUSDT 10; pricePrecision 2; quantityPrecision 4
- rSOXL returns an EMPTY order book
- Unfilled weekend limit orders auto-cancel at Monday US reopen (Bitget docs)
