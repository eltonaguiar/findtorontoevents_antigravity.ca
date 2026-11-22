import { chromium } from 'playwright';
// Reuse the profile you logged into over VNC, so the session persists.
const ctx = await chromium.launchPersistentContext('/home/eaguiar2015/.coms-vnc-profile', {
  headless: false,          // needs the display; set DISPLAY=:1
  viewport: { width: 1280, height: 860 },
  locale: 'en-CA',
});
const page = ctx.pages()[0] || await ctx.newPage();
const targets = [
  ['Best Buy PS5 Slim Disc', 'https://www.bestbuy.ca/en-ca/product/playstation-5-disc-edition-console-slim/19609594'],
  ['Google Shopping new PS5', 'https://www.google.com/search?q=new+ps5&udm=28'],
];
for (const [name, url] of targets) {
  let status = 'ERR', verdict = '', title = '';
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    status = resp ? resp.status() : '?';
    title = await page.title();
    await page.waitForTimeout(2500);
    const text = ((await page.innerText('body').catch(() => '')) || '').replace(/\s+/g, ' ');
    const m = text.match(/(sold out|out of stock|in stock|add to cart|available (?:online|in store)|not available|\$[\d,]+\.\d{2})/gi) || [];
    verdict = [...new Set(m.map(s => s.toLowerCase()))].slice(0, 8).join(', ');
    const blocked = /access denied|unusual traffic|verify you are|just a moment/i.test(text);
    console.log(`--- ${name}`);
    console.log(`    http=${status} title="${title.slice(0,55)}" blocked=${blocked}`);
    console.log(`    signals: ${verdict || '(none)'}  textLen=${text.length}`);
  } catch (e) {
    console.log(`--- ${name}  THROW ${String(e).split('\n')[0].slice(0,80)}`);
  }
}
await ctx.close();
