import { chromium } from 'playwright';
const urls = [
  ['PS5 Slim Disc', 'https://www.bestbuy.ca/en-ca/product/playstation-5-disc-edition-console-slim/19609594'],
  ['PS5 Pro 2TB (open box)', 'https://www.bestbuy.ca/en-ca/product/playstation-5-pro-console-with-2tb-ssd-ai-enhanced-4k-resolution-playstation-spectral-super-resolution-open-box/20351327'],
];
const browser = await chromium.launch();
const ctx = await browser.newContext({
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
  locale: 'en-CA', viewport: { width: 1440, height: 900 },
  extraHTTPHeaders: { 'accept-language': 'en-CA,en;q=0.9' },
});
for (const [name, url] of urls) {
  const page = await ctx.newPage();
  let status = 'ERR', title = '', verdict = '';
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    status = resp ? resp.status() : 'no-response';
    title = await page.title();
    const text = ((await page.innerText('body').catch(() => '')) || '').replace(/\s+/g, ' ');
    const m = text.match(/(sold out|out of stock|in stock|add to cart|available (?:online|in store)|not available|coming soon)[^.]{0,60}/i);
    verdict = m ? m[0].trim() : (text.slice(0, 120) || '(no body text)');
  } catch (e) { status = 'THROW: ' + String(e).split('\n')[0].slice(0, 70); }
  console.log(`\n--- ${name}`);
  console.log(`    http=${status}  title="${title.slice(0, 60)}"`);
  console.log(`    ${verdict}`);
  await page.close();
}
await browser.close();
