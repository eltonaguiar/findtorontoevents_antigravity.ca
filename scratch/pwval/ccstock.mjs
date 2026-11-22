import { chromium } from 'playwright';
const urls = [
  'https://www.canadacomputers.com/en/xbox/184244/microsoft-xbox-series-x-1tb-black-rrt-00001.html',
  'https://www.canadacomputers.com/en/xbox/264257/xbox-series-x-1tb-digital-console-robot-white-ep2-00692.html',
];
const browser = await chromium.launch();
const ctx = await browser.newContext({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', locale: 'en-CA' });
for (const url of urls) {
  const page = await ctx.newPage();
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(3000);
    const title = await page.title();
    const text = ((await page.innerText('body').catch(() => '')) || '').replace(/\s+/g, ' ');
    const stockBits = text.match(/(in stock|out of stock|sold out|available|pickup|ship)[^.]{0,80}/gi) || [];
    const downtown = text.match(/Toronto Downt?own[^.]{0,120}/gi) || [];
    console.log(`\n--- ${title.slice(0, 70)}`);
    console.log(`    url=${url}`);
    console.log(`    stock signals: ${[...new Set(stockBits.map(s => s.trim().toLowerCase()))].slice(0, 6).join(' | ') || 'none found'}`);
    console.log(`    downtown mentions: ${downtown.slice(0, 3).join(' || ') || 'none'}`);
  } catch (e) {
    console.log(`\n--- THROW ${url}: ${String(e).split('\n')[0].slice(0, 100)}`);
  }
  await page.close();
}
await browser.close();
