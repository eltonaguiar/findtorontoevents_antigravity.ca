import { chromium } from 'playwright';
const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const targets = [
  ['Microsoft', 'https://www.microsoft.com/en-ca/store/b/xboxconsoles'],
  ['EB Games', 'https://www.ebgames.ca/shop/category/games-xbox-series-x-s-195'],
  ['Walmart', 'https://www.walmart.ca/en/browse/video-games/microsoft-xbox-series-x-series-s/10012_6000201024446'],
  ['Best Buy cat', 'https://www.bestbuy.ca/en-ca/category/xbox-series-x-s/17582854'],
  ['Amazon', 'https://www.amazon.ca/s?k=xbox+series+x'],
];
for (const [name, url] of targets) {
  const page = await ctx.newPage();
  try {
    const r = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(2500);
    const text = ((await page.innerText('body').catch(() => '')) || '').replace(/\s+/g, ' ');
    const blocked = /access denied|unusual traffic|verify you are|just a moment|something went wrong|robot|captcha/i.test(text);
    const consoleLines = (text.match(/[^.]{0,70}(series [xs]|console)[^.]{0,70}/gi) || [])
      .filter(l => /\$[\d,]+\.\d{2}|in stock|out of stock|sold out|add to cart/i.test(l));
    const prices = [...new Set(consoleLines.flatMap(l => l.match(/\$[\d,]+\.\d{2}/g) || []))].slice(0, 5);
    console.log(`\n--- ${name}  http=${r ? r.status() : '?'}  blocked=${blocked}`);
    console.log(`    console prices: ${prices.join(', ') || '-'}`);
    consoleLines.slice(0, 2).forEach(l => console.log(`    > ${l.trim().slice(0, 115)}`));
  } catch (e) { console.log(`\n--- ${name} THROW ${String(e).split('\n')[0].slice(0, 70)}`); }
  await page.close();   // close only the tab I opened
}
await browser.close();
