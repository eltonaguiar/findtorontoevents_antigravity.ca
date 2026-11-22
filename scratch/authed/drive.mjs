import { chromium } from 'playwright';
const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const targets = [
  ['Microsoft Xbox consoles', 'https://www.microsoft.com/en-ca/store/b/xboxconsoles'],
  ['EB Games X|S', 'https://www.ebgames.ca/shop/category/games-xbox-series-x-s-195'],
  ['EB Games PS5', 'https://www.ebgames.ca/shop/category/games-playstation-5-196'],
  ['Walmart Xbox', 'https://www.walmart.ca/en/browse/video-games/microsoft-xbox-series-x-series-s/10012_6000201024446'],
  ['Best Buy PS5 cat', 'https://www.bestbuy.ca/en-ca/category/playstation-5/28331218'],
  ['Amazon Xbox', 'https://www.amazon.ca/s?k=xbox+series+x'],
  ['Amazon PS5', 'https://www.amazon.ca/s?k=playstation+5'],
];
const rows = [];
for (const [name, url] of targets) {
  const page = await ctx.newPage();
  let status = 'ERR', blocked = null, found = [];
  try {
    const r = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    status = r ? r.status() : '?';
    await page.waitForTimeout(2500);
    const text = ((await page.innerText('body').catch(() => '')) || '').replace(/\s+/g, ' ');
    blocked = /access denied|unusual traffic|verify you are|just a moment|robot|captcha|something went wrong/i.test(text);
    // price immediately adjacent to a CONSOLE name — not a game, not an accessory
    const re = /((?:xbox series [xs]|playstation ?5|ps5)[^$]{0,40}?console[^$]{0,30}?)\s*(?:CAD\s*)?\$([\d,]+\.\d{2})/gi;
    let m;
    while ((m = re.exec(text)) && found.length < 4) found.push(`${m[1].trim().slice(0, 45)} — $${m[2]}`);
    if (!found.length) {
      const oos = text.match(/out of stock[^.]{0,60}/i);
      if (oos) found.push(`(${oos[0].trim().slice(0, 60)})`);
    }
  } catch (e) { status = 'THROW ' + String(e).split('\n')[0].slice(0, 50); }
  rows.push([name, status, blocked, found]);
  await page.close();
}
for (const [n, s, b, f] of rows) {
  console.log(`\n--- ${n}  http=${s}  blocked=${b}`);
  f.length ? f.forEach(x => console.log(`    ${x}`)) : console.log('    (no console-level price found)');
}
await browser.close();
