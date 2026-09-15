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


/** Re-attach the caption layer. Every navigation destroys it.
 *
 * Styles are applied through the CSSOM rather than an injected <style> tag.
 * Bitget serves a Content-Security-Policy that drops the tag silently, and the
 * caption vanished for exactly the one shot where it mattered most - the line
 * claiming the price on screen is live. Setting properties on the element is
 * not subject to style-src, so this works everywhere.
 */
async function dress() {
  const ok = await page.evaluate(() => {
    const set = (el, css) => {
      for (const [k, v] of Object.entries(css)) el.style.setProperty(k, v, "important");
    };
    let w = document.getElementById("capwrap");
    if (!w) {
      w = document.createElement("div");
      w.id = "capwrap";
      const c = document.createElement("div");
      c.id = "cap";
      w.appendChild(c);
      document.body.appendChild(w);
    }
    set(w, {
      position: "fixed", left: "0", right: "0", bottom: "0",
      "z-index": "2147483646", display: "flex", "justify-content": "center",
      padding: "120px 0 26px", "pointer-events": "none",
      background:
        "linear-gradient(0deg,rgba(0,0,0,.99) 52%,rgba(0,0,0,.93) 70%," +
        "rgba(0,0,0,.72) 84%,transparent)",
    });
    set(document.getElementById("cap"), {
      "max-width": "1020px", "text-align": "center", padding: "0 40px",
    });
    let f = document.getElementById("flash");
    if (!f) {
      f = document.createElement("div");
      f.id = "flash";
      document.body.appendChild(f);
    }
    set(f, {
      position: "fixed", top: "0", left: "0", right: "0", bottom: "0",
      "z-index": "2147483647", background: "#fff", display: "none",
    });
    return !!document.getElementById("cap");
  });
  if (!ok) throw new Error("caption layer failed to attach");
}

const hold = (ms) => page.waitForTimeout(ms);
// A missing anchor used to resolve to null and scroll nowhere, so the first
// take narrated four charts while filming the hero and nothing anywhere said
// so. Now it stops the recording instead.
const to = async (sel, p = 1100, block = "center") => {
  const before = await page.evaluate(() => Math.round(window.scrollY));
  const ok = await page.evaluate(
    ([s, b]) => {
      const el = document.querySelector(s);
      if (!el) return false;
      el.scrollIntoView({ block: b, behavior: "smooth" });
      return true;
    },
    [sel, block]
  );
  if (!ok) throw new Error(`no such element to scroll to: ${sel}`);
  await hold(p);
  const after = await page.evaluate(() => Math.round(window.scrollY));
  if (after === before && before === 0) throw new Error(`page did not scroll for ${sel}`);
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
  // Re-attach if the layer went away. say() used to find no #cap and return
  // quietly, which is how the Bitget shot - the one shot whose whole point is
  // that the price on screen is real - ended up with no caption at all while
  // every other line had one.
  if (!(await page.evaluate(() => !!document.getElementById("cap")))) {
    console.log(`  caption layer was missing before line ${i}, re-attaching`);
    await dress();
  }
  const at = Date.now() - t0;
  await page.evaluate(
    ([l, g, words, dur]) => {
      const parts = l.split(/\s+/);
      const cap = document.getElementById("cap");
      if (!cap) return;
      // Built and coloured through the CSSOM, for the same CSP reason as the
      // wrapper. Class names alone would style nothing on Bitget's page.
      const set = (el, css) => {
        for (const [k, v] of Object.entries(css)) el.style.setProperty(k, v, "important");
      };
      cap.textContent = "";
      const lineEl = document.createElement("span");
      set(lineEl, {
        display: "block",
        font: '600 25px/1.44 Inter,-apple-system,"Segoe UI",Roboto,sans-serif',
        "letter-spacing": "-.012em",
        position: "static",
      });
      const spans = parts.map((word, k) => {
        const s = document.createElement("span");
        s.textContent = word;
        set(s, { color: "rgba(255,255,255,.38)", position: "static", display: "inline" });
        lineEl.appendChild(s);
        if (k < parts.length - 1) lineEl.appendChild(document.createTextNode(" "));
        return s;
      });
      cap.appendChild(lineEl);
      if (g) {
        const tagEl = document.createElement("span");
        tagEl.textContent = g;
        set(tagEl, {
          display: "block", "margin-top": "12px",
          font: '700 11px/1 "JetBrains Mono",ui-monospace,Consolas,monospace',
          "letter-spacing": ".2em", "text-transform": "uppercase", color: "#7c8ba6",
        });
        cap.appendChild(tagEl);
      }
      const READ = "#fff";
      const NOW = "#4D8BFF";
      // Word boundaries come from the synthesiser. If it split the line
      // differently from a whitespace split, spread evenly rather than
      // lighting the wrong word.
      const marks =
        words.length === spans.length
          ? words.map((w) => w.at)
          : spans.map((_, k) => (dur * k) / spans.length);
      marks.forEach((ms, k) =>
        setTimeout(() => {
          if (k) spans[k - 1].style.setProperty("color", READ, "important");
          spans[k].style.setProperty("color", NOW, "important");
        }, Math.max(0, ms))
      );
      setTimeout(() => {
        spans[spans.length - 1].style.setProperty("color", READ, "important");
      }, dur);
    },
    [line, tag, t.words, t.dur]
  );
  // Confirm the words actually landed on screen rather than assuming they did.
  const shown = await page
    .evaluate(() => (document.getElementById("cap")?.textContent || "").length)
    .catch(() => 0);
  if (!shown) console.log(`  WARNING: line ${i} (${tag}) rendered no caption`);
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
// Stop the dashboard reloading itself. It re-renders the table every sixty
// seconds, which puts target="_blank" back on the link and replaces the row
// out from under the click - so the click opened a popup (a second recording
// file) and this tab never moved. Everything that needed the live refresh has
// already been filmed by this point.
await page.evaluate(() => {
  const last = setTimeout(() => {}, 0);
  for (let id = 0; id <= last; id++) {
    clearInterval(id);
    clearTimeout(id);
  }
});
await hold(400);

const SEL = "#rows tr:first-child a.go";
const href = await page.evaluate((s) => {
  const a = document.querySelector(s);
  if (!a) return null;
  a.removeAttribute("target");
  a.style.outline = "2px solid #4D8BFF";
  a.style.outlineOffset = "3px";
  a.scrollIntoView({ block: "center" });
  return a.href;
}, SEL);
if (!href) throw new Error("no trade link in the table - did the book render?");
await hold(700);
await say(10); // to bitget

{
  // Re-query rather than reuse a handle taken before the line was spoken: a
  // handle to a row the page has since replaced clicks nothing at all, and
  // silently, because click() is wrapped in a catch.
  const link = await page.$(SEL);
  if (link) {
    await page.evaluate((s) => document.querySelector(s)?.removeAttribute("target"), SEL);
    await link.click({ timeout: 10000 }).catch(() => {});
  }
  // Give the click's own navigation time to land before judging it. Checking
  // the URL immediately said "did not navigate" while the tab was already on
  // its way, and the fallback goto then raced the navigation it was meant to
  // replace.
  let arrived = false;
  for (let i = 0; i < 20; i++) {
    if (/bitget\.com/i.test(page.url())) {
      arrived = true;
      break;
    }
    await hold(1000);
  }
  if (!arrived) {
    console.log("  click did not navigate, following the href directly");
    await page.goto(href, { waitUntil: "domcontentloaded", timeout: 90000 }).catch(() => {});
  }
  await page.waitForLoadState("domcontentloaded", { timeout: 60000 }).catch(() => {});
  console.log("  clicked through:", arrived, "->", page.url());

  // The exchange app is heavy and this machine reaches it over a VPN. A fixed
  // wait filmed a loading spinner while the voice said "live order book", so
  // wait for the ticker bar to actually mount. Dead time is free: the mixdown
  // compresses every gap between spoken lines.
  // Two minutes, with one reload halfway. The app usually mounts in about
  // fifteen seconds and occasionally not at all; a take that dies here costs
  // twenty-five minutes, so it is worth waiting out and worth one retry.
  const mounted = () =>
    page
      .evaluate(() => {
        const t = document.body.innerText || "";
        return /24h\s*(change|high|low|volume)/i.test(t) || /order\s*book/i.test(t);
      })
      .catch(() => false);
  let ready = false;
  for (let i = 0; i < 80; i++) {
    ready = await mounted();
    if (ready) break;
    if (i === 40) {
      console.log("  bitget still blank after 60s, reloading once");
      await page.reload({ waitUntil: "domcontentloaded", timeout: 90000 }).catch(() => {});
    }
    await hold(1500);
  }
  console.log("  bitget trading UI mounted:", ready);
  if (!ready) {
    throw new Error(
      "Bitget's app never mounted in two minutes. Check the VPN reaches " +
        "www.bitget.com, then re-run - the site itself answers in a few seconds " +
        "when it is up."
    );
  }

  // Clear the cookie dialog so it is not sitting over the order book. It can
  // appear a beat after the app mounts, so this keeps trying for a few seconds
  // rather than looking once and moving on.
  let dismissed = false;
  for (let i = 0; i < 8 && !dismissed; i++) {
    dismissed = await page
      .evaluate(() => {
        const b = [...document.querySelectorAll("button,[role=button],a")].find((el) =>
          /^\s*(accept|allow|agree|got it|ok)\b/i.test(el.textContent || "")
        );
        if (!b) return false;
        b.click();
        return true;
      })
      .catch(() => false);
    await hold(700);
  }
  console.log("  cookie dialog dismissed:", dismissed);

  // Give the price chart a short chance to draw. It usually will not:
  // TradingView wants a GPU canvas this headless build does not provide, and
  // Bitget's own code times out trying. The ticker price and the order book
  // are what the line actually claims, and both are there, so this is a brief
  // try rather than a long wait for something that is not coming.
  let charted = false;
  for (let i = 0; i < 6; i++) {
    charted = await page
      .evaluate(() => {
        const c = document.querySelector("canvas");
        return !!c && c.getBoundingClientRect().width > 300;
      })
      .catch(() => false);
    if (charted) break;
    await hold(1500);
  }
  console.log("  bitget chart drawn:", charted);
  await hold(2500);
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
