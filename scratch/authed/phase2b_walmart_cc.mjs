// Phase 2b — Walmart console category (Xbox Series X|S + PS5) and CC PS5 SKUs.
// The category page is already faceted to the two platforms, so every card is
// in scope; we read each card's own pickup/stock text rather than the page blob.
import { chromium } from 'playwright';

const WALMART_CAT = 'https://www.walmart.ca/en/browse/video-games/microsoft-xbox-series-x-series-s/10012_6000201024446_6000202240017?facet=pgls_pcs_video_game_platform%3AXbox+Series+X+%26+S%7C%7Cpgls_pcs_video_game_platform%3ASony+PlayStation+5';

const CC_PS5 = [
  ['PS5 Slim 1TB', 'https://www.canadacomputers.com/en/playstation-5/260297/sony-playstation-5-slim-console-1tb.html'],
];

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const stamp = new Date().toISOString();

// --- Walmart category ---
{
  const page = await ctx.newPage();
  try {
    await page.goto(WALMART_CAT, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(6000);
    const cards = await page.evaluate(() => {
      const res = [];
      const seen = new Set();
      // product cards: links containing /ip/ with a nearby text block
      for (const a of document.querySelectorAll('a[href*="/ip/"]')) {
        const href = a.href;
        if (seen.has(href)) continue;
        const box = a.closest('div') || a;
        const t = (box.innerText || '').replace(/\s+/g, ' ').trim();
        if (!t || t.length < 12) continue;
        seen.add(href);
        res.push({ href, text: t.slice(0, 200) });
      }
      return res;
    });
    console.log(`--- Walmart category: ${cards.length} product cards  (${stamp})`);
    for (const c of cards) {
      const flag = /(in stock|add to cart|out of stock|sold out|pickup|rollback|\$\d)/i.test(c.text) ? '' : '?';
      console.log(`  ${flag} ${c.text.slice(0, 120)}`);
      console.log(`      ${c.href.split('?')[0].slice(-60)}`);
    }
  } catch (e) {
    console.log(`--- Walmart category THROW ${String(e).split('\n')[0].slice(0, 90)}`);
  } finally { await page.close(); }
}

// --- CC PS5 ---
for (const [name, url] of CC_PS5) {
  const page = await ctx.newPage();
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(4000);
    const summary = await page.evaluate(() => {
      const t = (document.body.innerText || '').replace(/\s+/g, ' ');
      const pick = (re) => (t.match(re) || [])[0] || null;
      return {
        online: pick(/(Sold out online|In stock online|Delivery[^|]{0,40})/i),
        locations: pick(/(Sold Out at All Locations|Available at \d+ Locations?|In Stock at [^.]{0,40})/i),
        price: pick(/\$\s?\d{2,4}\.\d{2}/),
      };
    });
    console.log(`--- CC ${name}  (${stamp})`);
    console.log(`    ${JSON.stringify(summary)}`);
  } catch (e) {
    console.log(`--- CC ${name} THROW ${String(e).split('\n')[0].slice(0, 90)}`);
  } finally { await page.close(); }
}

await browser.close();
