import { chromium } from 'playwright';
const browser = await chromium.launch();
const ctx = await browser.newContext({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', locale: 'en-CA' });
for (const q of ['playstation 5 console', 'xbox series x console']) {
  const page = await ctx.newPage();
  await page.goto('https://www.canadacomputers.com/en/search?s=' + encodeURIComponent(q), { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(2500);
  const items = await page.$$eval('a[href*="/en/"]', as => as
    .map(a => ({ href: a.href, text: (a.innerText || '').replace(/\s+/g, ' ').trim() }))
    .filter(o => /playstation 5|xbox series [xs]/i.test(o.text) && o.text.length > 12 && o.text.length < 200));
  const seen = new Set();
  console.log(`\n=== ${q} — ${items.length} candidate links on canadacomputers.com`);
  for (const it of items) {
    if (seen.has(it.href)) continue;
    seen.add(it.href);
    const soldOut = /sold out|out of stock/i.test(it.text);
    console.log(`  [${soldOut ? 'SOLD OUT?' : 'listed'}] ${it.text.slice(0, 80)}`);
    console.log(`      ${it.href}`);
    if (seen.size >= 5) break;
  }
  await page.close();
}
await browser.close();
