# NOCTURNE — the demo video

The hackathon asks AI Trading Desk entries for **"a full research-task
walkthrough or screen recording"**, and a demo video of **3 minutes or less**.
So the video is not a slide deck. It is one continuous screen recording of the
live product, driven by Playwright, narrated, with a word-synchronised caption.

Output: `media/nocturne-demo.mp4`, 1920×1080.

---

## What it shows, in order

Every part of the build is touched once and then left. Nothing is dwelt on.

| # | section | on screen |
|---|---|---|
| 1 | the void | the live dashboard, hero |
| 2 | who sets the price | — |
| 3 | the session map | the six-state session tile |
| 4 | the trading week | 168 hourly bars, void highlighted, log axis |
| 5 | the cliff | rAAPL turnover, $2.38bn → $63 at 20:00 ET |
| 6 | our own tape | the live-capture sparkline, our own ticks |
| 7 | the finding | arriving at the book |
| 8 | the live book | last, fair value, drift, noise score, tier |
| 9 | depth | the table scrolled to buy/sell depth and spread |
| 10 | order splitting | order size raised to $250,000, slices change |
| 11 | to Bitget | a real `trade →` link, highlighted, clicked |
| 12 | **the real screen** | **Bitget's own live page for that pair** |
| 13 | the public record | the hashed-prediction section |
| 14 | the live round | Sunday's round, graded |
| 15 | the loss | the level claim losing, on the front page |
| 16 | the API | a live JSON endpoint in the browser |
| 17 | the agent skill | `skill/nocturne/SKILL.md` |
| 18 | autonomy | the GitHub Actions run history |
| 19 | close | back to the dashboard |

## How it is built

Four steps, all reproducible.

```bash
# 1. the words
#    walkthrough/script.json — one line per beat

# 2. the voice, and where every word lands
python scripts/tts.py --voice en-US-AndrewNeural --rate "+8%"
#    -> walkthrough/audio/NN.mp3 + timing.json

# 3. drive the live product and film it
cd walkthrough && PW_CHROME=<chromium> node record.mjs
#    -> walkthrough/final/*.webm + audio/offsets.json

# 4. cut it to the narration and lay the voice on
python scripts/mixdown.py
#    -> media/nocturne-demo.mp4
```

**Why the caption cannot drift.** The voice is synthesised *first*, and the
synthesiser reports the millisecond at which every word is spoken. The recorder
lights each word from those marks, and reports back the offset at which each
line began. The mixdown places each line of audio at exactly that offset.
Nothing is estimated from an assumed reading speed, so the highlight stays on
the voice for the whole run.

**Why the transitions run fast.** Headless Chromium drives the page far slower
than a person does — a scroll and a settle that read as one second cost twenty
in the capture — so the raw take runs about seven minutes. The mixdown keeps
every narrated passage at real speed and compresses only the dead time between
them. The transitions are the same frames, run fast. Nothing is dropped and no
frame is synthetic.

## Bitget's own page

Shot 12 is the one that makes the rest count: the dashboard alone only *claims*
a price is thin, and the dashboard next to Bitget showing that same price is
what proves it. The recorder strips `target="_blank"` from a real `trade →`
link so it opens in the same tab, keeping one continuous recording.

**A VPN is required on this machine.** The ISP refuses TCP to `www.bitget.com`
at the connection layer — DNS resolves fine, port 443 returns
ConnectionRefused. It is not a DNS problem and no browser setting fixes it.
`api.bitget.com` is unaffected, which is why data capture never needed one.
Confirm the page loads before recording, not mid-take.

## Dependencies

Build-time only; nothing in the running product imports any of them.

- `edge-tts` — narration and word timings
- `playwright-core` + Chromium — driving and filming the live site
- `ffmpeg` / `ffprobe` — cutting and mixing
