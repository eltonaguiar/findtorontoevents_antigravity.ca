import { chromium } from 'playwright';
const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const page = ctx.pages()[0] || await ctx.newPage();
const targets = [
  ['Best Buy PS5 Slim Disc', 'https://www.bestbuy.ca/en-ca/product/playstation-5-disc-edition-console-slim/19609594'],
  ['Best Buy Xbox Series S', 'https://www.bestbuy.ca/en-ca/product/xbox-series-s-512gb-console/19422130'],
  ['Google Shopping new PS5', 'https://www.google.com/search?q=new+ps5&udm=28'],
];
for (const [name, url] of targets) {
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(2500);
    const title = await page.title();
    const text = ((await page.innerText('body').catch(() => '')) || '').replace(/\s+/g, ' ');
    const blocked = /access denied|unusual traffic|verify you are|just a moment/i.test(text);
    const sig = text.match(/(sold out|out of stock|in stock|add to cart|only \d+ left|\$[\d,]+\.\d{2})/gi) || [];
    console.log(`--- ${name}`);
    console.log(`    http=${resp ? resp.status() : '?'} blocked=${blocked} title="${title.slice(0,50)}"`);
    console.log(`    signals: ${[...new Set(sig.map(s => s.toLowerCase()))].slice(0,8).join(', ') || '(none)'}`);
  } catch (e) {
    console.log(`--- ${name} THROW ${String(e).split('\n')[0].slice(0,70)}`);
  }
}
await browser.close();   // closes the CDP connection, not the browser
