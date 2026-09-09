# Weekend runbook — what to do and when

All times shown as **your local (WAT)**, with ET alongside. Everything marked
AUTOMATIC needs nobody.

## Friday
| Your time | ET | |
|---|---|---|
| Sat 01:00 | Fri 20:00 | **Void window opens.** Capture switches to every-5-min on all three sources. AUTOMATIC |

## Saturday — the one thing that needs you
| Your time | ET | |
|---|---|---|
| 13:00–19:00 | 08:00–14:00 | **Record shot 1.** Dashboard live, market dark, depth collapsed. See docs/VIDEO.md |

This is the only irreplaceable task of the weekend.

## Sunday — publish and submit
| Your time | ET | |
|---|---|---|
| 22:00–00:00 | 17:00–19:00 | **Prediction publishes**, hashed and pushed. AUTOMATIC |
| after that | | 1. Confirm it landed (ask Claude, or check `predictions/` on GitHub) |
| | | 2. Copy `posts/<date>_predict_short.txt` → post on X |
| | | 3. Retweet Bitget's official hackathon post |
| | | 4. Fill the Google Form from `docs/SUBMISSION.md` |
| | | 5. Paste the X link into the form. Tick Demo Day, Qwen subsidy, **University** |

The X post MUST contain `#BitgetHackathon` and `@Bitget_AI` — both are already
in the generated file.

## Monday — the grade lands
| Your time | ET | |
|---|---|---|
| 14:30 | 09:30 | US market reopens, prices re-anchor |
| 16:00 | 11:00 | **Grading runs**, scoreboard updates, results post written. AUTOMATIC |
| after | | Optional: post `posts/<date>_grade_short.txt`. Judges see the resolved claim either way |

Submitting Sunday does not stop Monday's grading. The system keeps running and
the public scoreboard resolves before judging opens on Sep 22.

## If something looks wrong
- `python scripts/audit.py` — 25 functional checks
- `python scripts/health.py` — is capture alive on each source
- `python scripts/netfix.py` — is DNS reaching Bitget
- `logs/runner.local.log`, `logs/runner.local2.log`, `logs/orchestrator.log`

## Facts worth not re-deriving
- Deadline Sep 21 (UTC+8). Judging Sep 22 – Oct 7. Public vote Sep 22–28.
- University prize is a **fallback, not a trade-off**: you only lose it if you
  win a main-track prize. Always tick it.
- Only the highest judge prize counts (Grand > Theme/Open > Best Spread).
  Fan Favorite stacks with everything.
