import { chromium } from 'playwright';
const urls = [
  ['Series S 512GB White', 'https://www.canadacomputers.com/en/xbox/184250/microsoft-xbox-series-s-512-gb-all-digital-console-white-rrs-00001.html'],
  ['Series S 1TB Robot White', 'https://www.canadacomputers.com/en/xbox/264253/microsoft-xbox-series-s-1tb-console-robot-white-ep2-00634.html'],
];
const browser = await chromium.launch();
const ctx = await browser.newContext({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', locale: 'en-CA' });
for (const [name, url] of urls) {
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(3000);
  const text = ((await page.innerText('body')) || '').replace(/\s+/g, ' ');
  const avail = text.match(/(sold out[^.]{0,70}|in stock[^.]{0,50}|out of stock[^.]{0,50}|add to cart[^.]{0,30})/gi) || [];
  console.log(`\n--- ${name}`);
  console.log(`    ${url}`);
  console.log(`    ${[...new Set(avail.map(a => a.trim().toLowerCase()))].slice(0, 4).join('\n    ') || 'no availability text found'}`);
  await page.close();
}
await browser.close();
