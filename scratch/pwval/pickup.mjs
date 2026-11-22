import { chromium } from 'playwright';
const url = 'https://www.canadacomputers.com/en/xbox/184244/microsoft-xbox-series-x-1tb-black-rrt-00001.html';
const browser = await chromium.launch();
const ctx = await browser.newContext({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', locale: 'en-CA' });
const page = await ctx.newPage();
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(4000);
// The pickup widget lists stores; each row carries a store name and a stock state.
const rows = await page.evaluate(() => {
  const out = [];
  const els = document.querySelectorAll('[class*="store"], [class*="pickup"], li, tr');
  for (const el of els) {
    const t = (el.innerText || '').replace(/\s+/g, ' ').trim();
    if (!t || t.length > 160) continue;
    if (!/(Toronto|Markham|Scarborough|Mississauga|Vaughan|Richmond Hill|North York|Etobicoke)/i.test(t)) continue;
    out.push(t);
  }
  return [...new Set(out)];
});
console.log(`=== per-store rows found: ${rows.length} ===`);
for (const r of rows) console.log('  ' + r);
await browser.close();
