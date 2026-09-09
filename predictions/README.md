# Predictions

Files here are published **before** the US market reopens and are never edited
afterwards. Each carries a `.sha256` of its own contents; the git commit
timestamp is the proof of when it existed.

- `YYYY-MM-DD_HHMM.json`         - a live prediction, published during a void window
- `YYYY-MM-DD_HHMM.sha256`       - hash of that file
- `YYYY-MM-DD_HHMM_graded.json`  - how it scored once the market reopened

## replay/

`replay/` holds **backtests, not live predictions.** They reconstruct what the
model would have published on a past weekend, using only data available at that
moment, and grade it against what actually happened. They are labelled
separately so they can never be mistaken for a real-time forecast.

The first live prediction will be published during the weekend session that
opens Friday 2026-09-11 20:00 ET.
