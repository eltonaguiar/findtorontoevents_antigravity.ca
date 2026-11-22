import { chromium } from 'playwright';
const targets = [
  ['GTA5TORONTOTRACKER repo', 'https://github.com/eltonaguiar/GTA5TORONTOTRACKER'],
  ['BestBuy PS5 search', 'https://www.bestbuy.ca/en-ca/search?search=playstation+5+console'],
  ['CanadaComputers PS5', 'https://www.canadacomputers.com/en/search?s=playstation%205'],
];
const browser = await chromium.launch();
for (const [name, url] of targets) {
  const ctx = await browser.newContext({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', locale: 'en-CA' });
  const page = await ctx.newPage();
  let status = 'ERR', title = '', bodyLen = 0, snippet = '';
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    status = resp ? resp.status() : 'no-response';
    title = await page.title();
    const text = (await page.innerText('body').catch(() => '')) || '';
    bodyLen = text.length;
    snippet = text.replace(/\s+/g, ' ').slice(0, 220);
  } catch (e) {
    status = 'THROW: ' + String(e).split('\n')[0].slice(0, 90);
  }
  console.log(`--- ${name}`);
  console.log(`    url=${url}`);
  console.log(`    http=${status}  title="${title}"  textLen=${bodyLen}`);
  console.log(`    first: ${snippet}`);
  await ctx.close();
}
await browser.close();
