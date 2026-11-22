import { chromium } from 'playwright';
const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const page = ctx.pages()[0] || await ctx.newPage();
const skus = [
  ['Series X 1TB Black', 184244],
];
const targets = [
  ['Best Buy Xbox Series X 1TB', 'https://www.bestbuy.ca/en-ca/product/xbox-series-x-1tb-console/18986002'],
  ['Best Buy Xbox landing', 'https://www.bestbuy.ca/en-ca/brand/xbox'],
  ['Microsoft Store Xbox', 'https://www.microsoft.com/en-ca/store/b/xbox'],
  ['Google Shopping xbox series x', 'https://www.google.com/search?q=xbox+series+x+console&udm=28'],
  ['Canada Computers Series X', 'https://www.canadacomputers.com/en/xbox/184244/microsoft-xbox-series-x-1tb-black-rrt-00001.html'],
];
for (const [name, url] of targets) {
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(2500);
    const title = await page.title();
    const text = ((await page.innerText('body').catch(() => '')) || '').replace(/\s+/g, ' ');
    const blocked = /access denied|unusual traffic|verify you are|just a moment/i.test(text);
    const prices = [...new Set((text.match(/\$[\d,]+\.\d{2}/g) || []))].slice(0, 6);
    const stock = [...new Set((text.match(/(in stock|out of stock|sold out|add to cart|only \d+ left|unavailable)/gi) || []).map(s => s.toLowerCase()))];
    console.log(`--- ${name}`);
    console.log(`    http=${resp ? resp.status() : '?'} blocked=${blocked} "${title.slice(0,45)}"`);
    console.log(`    prices: ${prices.join(', ') || '-'}   stock words: ${stock.join(', ') || '-'}`);
  } catch (e) {
    console.log(`--- ${name} THROW ${String(e).split('\n')[0].slice(0,70)}`);
  }
}
await browser.close();
