// Dump every rendered card's text content so we can see what date format is actually used.
import { chromium } from "playwright";
import fs from "node:fs";

const patched = fs.readFileSync("e:/findtorontoevents_antigravity.ca/next/events.json", "utf-8");
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1400, height: 1000 }, locale: "en-CA", timezoneId: "America/Toronto" });
const page = await ctx.newPage();

await page.route((u) => u.pathname.endsWith("/events.json"), (r) =>
  r.fulfill({ status: 200, headers: { "Content-Type": "application/json" }, body: patched }),
);

await page.goto("https://findtorontoevents.ca/", { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(3500);

for (const s of ["button:has-text('Today')", "text=/^Today$/"]) {
  const loc = page.locator(s).first();
  if (await loc.count()) { await loc.click().catch(()=>{}); break; }
}
await page.waitForTimeout(3000);

// Scroll very aggressively to trigger pagination / "sync more" loading.
for (let i = 0; i < 80; i++) {
  await page.evaluate(() => window.scrollBy(0, 5000));
  await page.waitForTimeout(400);
}
// Click any "sync more" style trigger, then scroll again.
for (const sel of ["button:has-text('Sync')", "button:has-text('Show All')", "button:has-text('Load more')", "button:has-text('More')"]) {
  const loc = page.locator(sel).first();
  if (await loc.count()) await loc.click().catch(()=>{});
}
await page.waitForTimeout(2000);
for (let i = 0; i < 30; i++) { await page.evaluate(() => window.scrollBy(0, 5000)); await page.waitForTimeout(400); }

// Dump every likely-card node's text + a hint about date chip.
const cards = await page.evaluate(() => {
  const out = [];
  // Find all elements that contain a title tag + short visible text
  const titleNodes = Array.from(document.querySelectorAll("h2, h3, h4, h5"));
  for (const titleEl of titleNodes) {
    let card = titleEl.closest("article, [data-event-id], .group, [class*='card' i], [class*='event' i]");
    if (!card) card = titleEl.parentElement?.parentElement;
    if (!card) continue;
    const text = (card.textContent || "").replace(/\s+/g, " ").trim();
    if (text.length < 30 || text.length > 2500) continue;
    const title = (titleEl.textContent || "").trim().slice(0, 80);
    // first 60 chars of card text - where the date chip usually sits
    out.push({ title, lead: text.slice(0, 60) });
  }
  // dedupe by title
  const seen = new Set();
  return out.filter((c) => {
    if (seen.has(c.title)) return false;
    seen.add(c.title);
    return true;
  });
});

console.log(`Unique cards: ${cards.length}`);
const byMonth = {};
// Note: /\b(Feb)\s*(\d{1,2})\b/ fails on "Feb21Free" because `\b` needs a
// non-word char between digits and the next letter — so match greedily instead.
const monthRe = /(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*(\d{1,2})/i;
for (const c of cards) {
  const m = c.lead.match(monthRe);
  if (m) {
    const key = `${m[1]} ${m[2]}`;
    byMonth[key] = (byMonth[key] || 0) + 1;
  }
}
console.log("\nDate chip counts across rendered cards:");
for (const [k, v] of Object.entries(byMonth).sort((a, b) => b[1] - a[1])) {
  console.log(`  ${k.padEnd(10)} ${v}`);
}

console.log("\nSample cards (first 12):");
for (const c of cards.slice(0, 12)) {
  console.log(`  • ${c.title} — lead: "${c.lead}"`);
}

// Specifically look for the Hottest Singles Mixer
const match = cards.find((c) => /Hottest Singles Mixer/i.test(c.title) || /Hottest/i.test(c.lead));
console.log(`\nHottest Singles Mixer card: ${match ? JSON.stringify(match) : "NOT FOUND in rendered cards"}`);

await browser.close();
