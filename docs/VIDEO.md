# NOCTURNE — demo video script

**Target: 90 seconds.** A judge watching 200 submissions decides in the first
ten. Lead with the number, not the product tour.

Times are ET, with your local (WAT = ET + 5) alongside.

---

## The opening line — say this over shot 1

> "One hour of Apple on a Friday trades five point nine billion dollars.
> The entire following weekend, across all 87 tokenised US stocks on Bitget,
> trades eight point six million.
> That's six hundred and eighty four to one.
> And the price still moves."

Then, two beats later:

> "We measured what happens to those weekend moves. For large caps,
> a hundred percent of them reverse by Monday. We call it Void Drift."

---

## Shot list

### Shot 1 — the dead market (30s)
**Sat 08:00–14:00 ET · Sat 13:00–19:00 your time**

Screen: the dashboard, live, during the void window.

- The banner reading **US market is CLOSED (VOID_A)**
- The depth column — scroll to the VERY THIN rows. rAAPL, rAMD, rASTS
- One Noise Score in the 90s next to a drift of a fraction of a percent
- The countdown: "orders cancelled in N hours"

**This is the most important footage of the weekend.** It is the only shot that
cannot be reconstructed later, and it is the entire argument.

### Shot 2 — the pre-commitment (15s)
**Sun 17:00–19:00 ET · Sun 22:00–00:00 your time**

Screen: the GitHub commit for the prediction file.

- The `predictions/` file and its `.sha256`
- GitHub's own commit timestamp, clearly before Monday's open
- Say: *"Published before the market opened. Hashed. We can't edit it after."*

### Shot 3 — liquidity returns (10s, optional)
**Sun 19:00–20:00 ET · Mon 00:00–01:00 your time**

Screen: session flips VOID_A -> PARTIAL_B, depth numbers visibly rebuild.

Say: *"Sunday evening, index futures reopen and liquidity comes back. Nobody
charts this boundary because you have to know it exists."*

Skip if you're not up. Nice-to-have.

### Shot 4 — the re-anchor and the grade (25s)
**Mon 09:30–11:30 ET · Mon 14:30–16:30 your time**

Screen: prices snap back, then the scoreboard.

- Both claims scored, **including any loss**
- Say: *"We said Monday would land closer to Friday's close. Here's how we did.
  Claim one wins seven weekends in ten — we said that before, not after."*

### Shot 5 — the close (10s)

Screen: the skill installed in Claude or Cursor, answering
*"what is rNVDA worth right now?"* from the public API.

> "No API key. Eighty-seven stocks. It'll still be running while you judge."

---

## Rules

- **Never say "predicts."** Say *reference price*, *ranks execution risk*.
- **Show a loss on screen.** It is the most persuasive thing in the video.
- Real cursor movement on the live site. No mockups, no slides.
- Screen-record at 1080p+. Face optional; voice matters more.
- If a number on screen disagrees with the script, **read the screen.**

---

## Recording checklist

- [ ] Dashboard open, session shows a DARK state
- [ ] Browser zoom ~110% so depth figures are legible
- [ ] Terminal ready with the skill client
- [ ] GitHub commit history open in a second tab
- [ ] Test 10s of audio first
- [ ] Shot 1 captured — everything else is upside
