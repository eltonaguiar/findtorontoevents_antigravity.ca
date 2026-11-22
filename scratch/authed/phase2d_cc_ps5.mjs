// Phase 2d — CC PS5 product pages (real URLs from the site's own search).
// CC prints "Sold Out at All Locations" or a per-store table; capture both.
import { chromium } from 'playwright';

const TARGETS = [
  ['PS5 Slim Console', 'https://www.canadacomputers.com/en/playstation/247956/sony-playstation-5-slim-console-1000039655-1000049888.html'],
  ['PS5 Slim Digital Edition', 'https://www.canadacomputers.com/en/playstation/247955/sony-playstation-5-slim-console-digital-edition-1000039669-1000049898.html'],
  ['PS5 Pro Digital Edition', 'https://www.canadacomputers.com/en/playstation/263621/sony-playstation-5-pro-digital-edition-1000046547-1000050805.html'],
];

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const stamp = new Date().toISOString();

for (const [name, url] of TARGETS) {
  const page = await ctx.newPage();
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(4500);
    const r = await page.evaluate(() => {
      const t = (document.body.innerText || '').replace(/[ \t]+/g, ' ');
      const one = (re) => { const m = t.match(re); return m ? m[0].replace(/\s+/g, ' ').trim().slice(0, 90) : null; };
      // store rows: a location name followed by a qty/status
      const storeRows = [];
      for (const line of t.split('\n').map(s => s.trim()).filter(Boolean)) {
        if (/(Toronto|Markham|Richmond Hill|Scarborough|North York|Mississauga|Vaughan|Etobicoke|Oakville|Brampton|Whitby|Hamilton|Ajax|Pickering|Thornhill)/i.test(line)
            && line.length < 120 && /(stock|\d+\s*(unit|in stock)|out of stock|available)/i.test(line)) {
          storeRows.push(line);
        }
      }
      return {
        price: one(/\$\s?\d{2,4}\.\d{2}/),
        online: one(/(Sold out online|In stock online|Add to cart)/i),
        locations: one(/(Sold Out at All Locations|Available at \d+ Locations?|In Stock at [^|\n]{0,40})/i),
        storeRows: [...new Set(storeRows)].slice(0, 20),
      };
    });
    console.log(`--- CC ${name}  (${stamp})`);
    console.log(`    price=${r.price} online=${r.online} locations=${r.locations}`);
    for (const s of r.storeRows) console.log(`      ${s}`);
    if (!r.storeRows.length) console.log('      (no per-store rows rendered)');
  } catch (e) {
    console.log(`--- CC ${name} THROW ${String(e).split('\n')[0].slice(0, 90)}`);
  } finally { await page.close(); }
}
await browser.close();
