import { chromium } from 'playwright';
const skus = [
  ['Series X 1TB Black', 'https://www.canadacomputers.com/en/xbox/184244/microsoft-xbox-series-x-1tb-black-rrt-00001.html'],
  ['Series S 512GB White', 'https://www.canadacomputers.com/en/xbox/184250/microsoft-xbox-series-s-512-gb-all-digital-console-white-rrs-00001.html'],
];
const browser = await chromium.launch();
const ctx = await browser.newContext({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', locale: 'en-CA' });
for (const [name, url] of skus) {
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(3500);
  const text = ((await page.innerText('body')) || '').replace(/[ \t]+/g, ' ');
  // store names appear near availability; grab any GTA city mention with nearby stock words
  const cities = ['Toronto Downtown','Markham','Richmond Hill','Scarborough','North York','Mississauga','Vaughan','Etobicoke','Oakville','Brampton','Whitby','Hamilton','Unionville'];
  console.log(`\n--- ${name}`);
  for (const c of cities) {
    const re = new RegExp(c.replace(/ /g, '\\s+') + '[^\\n]{0,90}', 'i');
    const m = text.match(re);
    if (m) console.log(`  ${m[0].replace(/\s+/g,' ').trim().slice(0,110)}`);
  }
  const summary = text.match(/(sold out[^.\n]{0,60}|in stock[^.\n]{0,40}|available[^.\n]{0,40})/i);
  console.log(`  overall: ${summary ? summary[0].trim() : 'no summary found'}`);
  await page.close();
}
await browser.close();
