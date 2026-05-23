// Final proof: route-intercept live findtorontoevents.ca with repo's next/events.json
// and screenshot Apr 17 events rendering under Today filter.
import { chromium } from "playwright";
import fs from "node:fs";

const patched = fs.readFileSync("e:/findtorontoevents_antigravity.ca/next/events.json", "utf-8");
const patchedEvents = JSON.parse(patched);
console.log(`[data] patched next/events.json has ${patchedEvents.length} events`);

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({
  viewport: { width: 1400, height: 1000 },
  locale: "en-CA",
  timezoneId: "America/Toronto",
});
const page = await ctx.newPage();

await page.route((u) => u.pathname.endsWith("/events.json"), async (r) =>
  r.fulfill({
    status: 200,
    headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
    body: patched,
  }),
);

const logs = [];
page.on("console", (m) => {
  const t = m.text();
  if (/\[Filter|\[validEvents|\[EventFeed|EMERGENCY|\[DIAGNOSTIC/.test(t)) logs.push(t);
});

console.log("[step] Navigate to live site…");
await page.goto("https://findtorontoevents.ca/", { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(3000);

console.log("[step] Click Today filter…");
for (const s of ["button:has-text('Today')", "text=/^Today$/"]) {
  const loc = page.locator(s).first();
  if (await loc.count()) {
    await loc.click().catch(() => {});
    break;
  }
}
await page.waitForTimeout(3500);

// Aggressive scroll to force render of all paginated Today cards (react virtualizes at 50).
// Scroll to bottom, wait for more to load, repeat until height stabilizes.
let prevHeight = 0;
for (let i = 0; i < 25; i++) {
  const h = await page.evaluate(() => document.body.scrollHeight);
  if (h === prevHeight) break;
  prevHeight = h;
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(700);
}
// Click any "Load more" / "Sync more" button if present
for (const s of ["button:has-text('Sync')", "button:has-text('Load')", "text=/Scroll down to sync/i"]) {
  const loc = page.locator(s).first();
  if (await loc.count()) await loc.click().catch(()=>{});
}
await page.waitForTimeout(1500);
await page.evaluate(() => window.scrollTo(0, 0));
await page.waitForTimeout(800);

await page.screenshot({ path: "tests/artifacts/apr17_final_proof.png", fullPage: true });

// Pull per-card data from the DOM to confirm Apr 17 events render.
const cards = await page.evaluate(() => {
  const out = [];
  const candidates = Array.from(document.querySelectorAll("[data-event-id], article, .group"));
  for (const n of candidates) {
    const text = (n.textContent || "").replace(/\s+/g, " ").trim();
    if (text.length < 30 || text.length > 3000) continue;
    // Card pattern: "Apr17" or "Apr 17" date badge at top
    const m = text.match(/\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s?(\d{1,2})\b/);
    if (!m) continue;
    const titleEl = n.querySelector("h1, h2, h3, h4");
    const title = (titleEl?.textContent || "").replace(/\s+/g, " ").trim().slice(0, 100);
    out.push({ dateChip: `${m[1]} ${m[2]}`, title, snippet: text.slice(0, 140) });
    if (out.length >= 60) break;
  }
  return out;
});

const apr17Cards = cards.filter((c) => /^Apr\s?17$/.test(c.dateChip));
const apr18Cards = cards.filter((c) => /^Apr\s?18$/.test(c.dateChip));

const body = await page.evaluate(() => document.body.innerText || "");
const banner = (body.match(/\d+\s*Events?\s*Found/i) || [])[0] || "(no banner)";
const tbdBanner = (body.match(/\d+\s+with\s+date\s+unavailable/i) || [])[0] || "(no TBD banner)";
const tbdCards = (body.match(/Date\s*TBD/gi) || []).length;

console.log("\n=== RESULT ===");
console.log(`Events banner: ${banner}`);
console.log(`TBD banner:    ${tbdBanner}`);
console.log(`TBD cards:     ${tbdCards}`);
console.log(`Apr 17 cards visible: ${apr17Cards.length}`);
console.log(`Apr 18 cards visible: ${apr18Cards.length}`);
console.log("\nFirst 10 Apr 17 cards:");
for (const c of apr17Cards.slice(0, 10)) {
  console.log(`  • [${c.dateChip}] ${c.title || c.snippet.slice(0, 80)}`);
}

// Targeted searches for known Apr 17 events
const hasSinglesMixer = body.includes("Hottest Singles Mixer") || body.includes("Hottest\u00a0Singles\u00a0Mixer");
console.log(`\n'Toronto's Hottest Singles Mixer' present: ${hasSinglesMixer}`);

console.log("\n=== FILTER TAIL ===");
for (const l of logs.slice(-5)) console.log(l);

console.log(`\nScreenshot saved: tests/artifacts/apr17_final_proof.png`);

const PASS = apr17Cards.length >= 5 && tbdCards === 0;
console.log(`\n${PASS ? "✅ PASS" : "❌ FAIL"}: Apr 17 cards=${apr17Cards.length}, TBD cards=${tbdCards}`);

await browser.close();
process.exit(PASS ? 0 : 1);
