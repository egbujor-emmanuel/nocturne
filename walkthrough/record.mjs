// The demo recording: one continuous screen capture of the live product.
//
// The hackathon asks AI Trading Desk entries for "a full research-task
// walkthrough or screen recording", so nothing here is a slide. Playwright
// drives the real dashboard at egbujor-emmanuel.github.io/nocturne, clicks a
// real trade link through to Bitget's own page, and walks the public API, the
// agent skill and the Actions history.
//
// The voice is generated first (scripts/tts.py) and reports where every word
// lands, so this file never guesses a reading speed: it lights each word at the
// moment it is spoken and reports back the offset at which every line started.
// scripts/mixdown.py then drops each line of audio at exactly that offset,
// which is why the caption cannot drift off the voice.
//
// A single white frame is flashed before the first line. The mixdown finds it,
// treats it as time zero, and trims it off.
import { chromium } from "playwright-core";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const HERE = fileURLToPath(new URL(".", import.meta.url));
const SCRIPT = JSON.parse(readFileSync(HERE + "script.json", "utf8"));
const TIMING = JSON.parse(readFileSync(HERE + "audio/timing.json", "utf8"));
if (SCRIPT.length !== TIMING.length) throw new Error("script and timing disagree");

const SITE = "https://egbujor-emmanuel.github.io/nocturne/";
const API = "https://egbujor-emmanuel.github.io/nocturne/api/v1/symbols/RNVDA.json";
const SKILL = "https://github.com/egbujor-emmanuel/nocturne/blob/master/skill/nocturne/SKILL.md";
const ACTIONS = "https://github.com/egbujor-emmanuel/nocturne/actions";

const browser = await chromium.launch({ executablePath: process.env.PW_CHROME });
// 1280x720 at 2x, upscaled in the mixdown. Capturing 1920x1080 directly made
// every Playwright round-trip cost seconds and left a 40 MB file that took
// longer to flush than to record.
const ctx = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  deviceScaleFactor: 2,
  recordVideo: { dir: HERE + "final", size: { width: 1280, height: 720 } },
});
const page = await ctx.newPage();
const errs = [];
page.on("pageerror", (e) => errs.push(String(e).slice(0, 160)));

const CAP_CSS = `
#capwrap{position:fixed;left:0;right:0;bottom:0;z-index:2147483646;
  display:flex;justify-content:center;padding:52px 0 24px;pointer-events:none;
  background:linear-gradient(0deg,rgba(0,0,0,.97) 45%,rgba(0,0,0,.72) 82%,transparent)}
#cap{max-width:1020px;text-align:center;padding:0 40px}
#cap .l{display:block;font:600 25px/1.44 Inter,-apple-system,"Segoe UI",Roboto,sans-serif;
  letter-spacing:-.012em}
#cap .w{color:rgba(255,255,255,.38)}
#cap .w.read{color:#fff}
#cap .w.now{color:#4D8BFF}
#cap .n{display:block;margin-top:12px;font:700 11px/1 "JetBrains Mono",ui-monospace,Consolas,monospace;
  letter-spacing:.2em;text-transform:uppercase;color:#7c8ba6}
#flash{position:fixed;inset:0;z-index:2147483647;background:#fff;display:none}
`;

/** Re-attach the caption layer. Every navigation destroys it. */
async function dress(zoom = 1) {
  await page.addStyleTag({ content: CAP_CSS + (zoom !== 1 ? `body{zoom:${zoom}}` : "") });
  await page.evaluate(() => {
    if (!document.getElementById("capwrap")) {
      const w = document.createElement("div");
      w.id = "capwrap";
      w.innerHTML = '<div id="cap"></div>';
      document.body.appendChild(w);
    }
    if (!document.getElementById("flash")) {
      const f = document.createElement("div");
      f.id = "flash";
      document.body.appendChild(f);
    }
  });
}

const hold = (ms) => page.waitForTimeout(ms);
const to = async (sel, p = 1100, block = "center") => {
  await page.evaluate(
    ([s, b]) => document.querySelector(s)?.scrollIntoView({ block: b, behavior: "smooth" }),
    [sel, block]
  );
  await hold(p);
};
const top = async (p = 1100) => {
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
  await hold(p);
};

await page.goto(SITE, { waitUntil: "domcontentloaded", timeout: 90000 });
await dress();

// Nothing is filmed until the table has actually rendered, so no frame shows
// "loading…" while the voice is describing live prices.
for (let i = 0; i < 40; i++) {
  const n = await page.evaluate(() => document.querySelectorAll("#rows tr").length);
  const t = await page.evaluate(() => document.getElementById("rows")?.innerText || "");
  if (n > 3 && !/loading/i.test(t)) break;
  await hold(700);
}
await page.evaluate(() => window.scrollTo({ top: 0 }));
await hold(900);

// Sync anchor.
await page.evaluate(
  () =>
    new Promise((r) => {
      const f = document.getElementById("flash");
      f.style.display = "block";
      setTimeout(() => {
        f.style.display = "none";
        r();
      }, 260);
    })
);
const t0 = Date.now();
await hold(1200);

const offsets = [];
const say = async (i) => {
  const { line, tag } = SCRIPT[i];
  const t = TIMING[i];
  const at = Date.now() - t0;
  await page.evaluate(
    ([l, g, words, dur]) => {
      const parts = l.split(/\s+/);
      const cap = document.getElementById("cap");
      if (!cap) return;
      cap.innerHTML =
        `<span class="l">${parts.map((w) => `<span class="w">${w}</span>`).join(" ")}</span>` +
        (g ? `<span class="n">${g}</span>` : "");
      const spans = Array.from(cap.querySelectorAll(".w"));
      // Word boundaries come from the synthesiser. If it split the line
      // differently from a whitespace split, spread evenly rather than
      // lighting the wrong word.
      const marks =
        words.length === spans.length
          ? words.map((w) => w.at)
          : spans.map((_, k) => (dur * k) / spans.length);
      marks.forEach((ms, k) =>
        setTimeout(() => {
          if (k) spans[k - 1].className = "w read";
          spans[k].className = "w now";
        }, Math.max(0, ms))
      );
      setTimeout(() => {
        spans[spans.length - 1].className = "w read";
      }, dur);
    },
    [line, tag, t.words, t.dur]
  );
  offsets.push({ i, tag, at: Math.round(at), dur: t.dur });
  await hold(t.dur + 300);
};

// ---- the problem, on the live dashboard -------------------------------
await say(0); // the void
await say(1); // who sets the price

await to("#s-tiles", 1000);
await say(2); // the session map

await to("#s-week", 1000);
await say(3); // the trading week

await to("#s-charts", 1000);
await say(4); // the cliff
await say(5); // our own tape

// ---- the book ---------------------------------------------------------
await to("#s-book", 1100, "start");
await say(6); // the finding
await say(7); // the live book

// Push the table sideways so depth, spread and slices are the columns on
// screen while they are being described.
await page.evaluate(() => {
  const w = document.querySelector("#s-book .tw");
  if (w) w.scrollTo({ left: w.scrollWidth, behavior: "smooth" });
});
await hold(1000);
await say(8); // depth

await page.selectOption("#osize", "250000").catch(() => {});
await hold(1100);
await say(9); // order splitting

// ---- through to Bitget's own page -------------------------------------
// Clicking it for real is the point, so the link is opened in this tab
// rather than a popup - a popup would start a second recording file.
const link = await page.$("#rows tr:first-child a.go");
if (link) {
  await page.evaluate(() => {
    const a = document.querySelector("#rows tr:first-child a.go");
    if (!a) return;
    a.removeAttribute("target");
    a.style.outline = "2px solid #4D8BFF";
    a.style.outlineOffset = "3px";
    a.scrollIntoView({ block: "center" });
  });
  await hold(700);
}
await say(10); // to bitget

if (link) {
  await link.click().catch(() => {});
  await page.waitForLoadState("domcontentloaded", { timeout: 60000 }).catch(() => {});
  await hold(5200); // the exchange is heavy, and over a VPN
  await dress();
}
await say(11); // the real screen

// ---- the public record ------------------------------------------------
await page.goto(SITE, { waitUntil: "domcontentloaded", timeout: 90000 });
await dress();
for (let i = 0; i < 30; i++) {
  const t = await page.evaluate(() => document.getElementById("rounds")?.innerText || "");
  if (t.trim()) break;
  await hold(600);
}
await to("#s-record", 1200, "center");
await say(12); // the public record
await say(13); // the live round
await say(14); // the loss

// ---- the public API ---------------------------------------------------
await page.goto(API, { waitUntil: "domcontentloaded", timeout: 60000 });
await dress();
await hold(800);
await say(15); // the api

// ---- the agent skill --------------------------------------------------
await page.goto(SKILL, { waitUntil: "domcontentloaded", timeout: 90000 });
await dress();
await hold(1200);
await say(16); // the agent skill

// ---- it runs itself ---------------------------------------------------
await page.goto(ACTIONS, { waitUntil: "domcontentloaded", timeout: 90000 });
await dress();
await hold(1400);
await say(17); // autonomy

// ---- close ------------------------------------------------------------
await page.goto(SITE, { waitUntil: "domcontentloaded", timeout: 90000 });
await dress();
await hold(1400);
await top(800);
await say(18); // nocturne
await hold(2000);

writeFileSync(HERE + "audio/offsets.json", JSON.stringify(offsets, null, 1));
const last = offsets.at(-1);
console.log("  page errors:", errs.length ? errs.join(" | ") : "NONE");
console.log("  lines:", offsets.length);
console.log("  last line ends at", ((last.at + last.dur) / 1000).toFixed(1), "s");
await ctx.close();
await browser.close();
console.log("  flushed");
