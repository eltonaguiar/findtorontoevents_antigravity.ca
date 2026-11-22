// Phase 2f — the method that actually worked: for console products found in
// Walmart search, open each product page and read its OWN pickup line.
// Caps the number of products per query so this stays a sweep, not a scrape storm.
import { chromium } from 'playwright';

const QUERIES = [
  ['xbox series x', 'https://www.walmart.ca/en/search?q=xbox+series+x'],
  ['ps5', 'https://www.walmart.ca/en/search?q=ps5'],
];
const CONSOLE = /(xbox series [xs]|playstation\s*5|ps5)\s*(console)?/i;
const ACCESSORY = /(controller|stand|cover|case|charging|headset|gift card|cable|skin|bundle plate|dock|mount|screen)/i;
const MAX_PER_QUERY = 5;

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const results = [];

for (const [q, url] of QUERIES) {
  const page = await ctx.newPage();
  const cards = [];
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    const raw = await page.evaluate(() => {
      const out = [], seen = new Set();
      for (const a of document.querySelectorAll('a[href*="/ip/"]')) {
        const href = a.href.split('?')[0];
        if (seen.has(href)) continue;
        const box = a.closest('div') || a;
        const t = (box.innerText || '').replace(/\s+/g, ' ').trim();
        if (t.length < 10) continue;
        seen.add(href);
        out.push({ href, text: t.slice(0, 120) });
      }
      return out;
    });
    for (const c of raw) {
      if (!CONSOLE.test(c.text) || ACCESSORY.test(c.text)) continue;
      cards.push(c);
      if (cards.length >= MAX_PER_QUERY) break;
    }
    console.log(`--- search "${q}": ${raw.length} cards, ${cards.length} console candidates`);
  } catch (e) {
    console.log(`--- search "${q}" THROW ${String(e).split('\n')[0].slice(0, 80)}`);
  } finally { await page.close(); }

  for (const c of cards) {
    const p = await ctx.newPage();
    const stamp = new Date().toISOString();
    try {
      await p.goto(c.href, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await p.waitForTimeout(5000);
      const r = await p.evaluate(() => {
        const t = (document.body.innerText || '').replace(/[ \t]+/g, ' ');
        const one = (re) => { const m = t.match(re); return m ? m[0].replace(/\s+/g, ' ').trim().slice(0, 110) : null; };
        const ld = [...document.querySelectorAll('script[type="application/ld+json"]')]
          .map(s => { try { return JSON.parse(s.textContent); } catch { return null; } }).flat().filter(Boolean);
        let price = null;
        for (const o of ld) {
          const off = o.offers || (Array.isArray(o) ? o.map(x => x.offers).flat().filter(Boolean) : []);
          const pr = Array.isArray(off) ? off[0]?.price : off?.price;
          if (pr) { price = pr; break; }
        }
        return {
          title: (document.title || '').split('|')[0].trim().slice(0, 80),
          price,
          pickup: one(/free pickup[^\n]{0,60}/i) || one(/pickup[^\n]{0,40}(today|tomorrow|unavailable)[^\n]{0,20}/i),
          cart: one(/add to cart|out of stock|sold out online/i),
          store: one(/at\s+([A-Z][A-Za-z ]{4,30}?)(?=\s*$|\s*\|)/m),
        };
      });
      const kind = r.pickup && /today/i.test(r.pickup) ? 'PICKUP-TODAY' : (r.cart && /add to cart/i.test(r.cart) ? 'buyable' : 'unavailable');
      console.log(`    [${kind}] ${r.title}`);
      console.log(`        price=${r.price ?? '?'} pickup="${r.pickup ?? '—'}" cart="${r.cart ?? '—'}"`);
      results.push({ q, ...r, kind, href: c.href, observed_at_utc: stamp });
    } catch (e) {
      console.log(`    THROW ${String(e).split('\n')[0].slice(0, 70)}  ${c.href.slice(-40)}`);
    } finally { await p.close(); }
  }
}

await browser.close();
console.log('\n=== summary ===');
for (const r of results.filter(r => r.kind === 'PICKUP-TODAY')) console.log(`PICKUP TODAY: ${r.title} — ${r.pickup}`);
