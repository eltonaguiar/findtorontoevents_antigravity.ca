import { chromium } from 'playwright';
const browser = await chromium.launch();
const ctx = await browser.newContext({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', locale: 'en-CA' });
for (const url of ['https://invictusgamestation.com/', 'https://www.invictusgamestation.com/']) {
  const page = await ctx.newPage();
  try {
    const r = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const text = ((await page.innerText('body')) || '').replace(/\s+/g, ' ');
    console.log(`--- ${url}  http=${r ? r.status() : '?'}`);
    console.log(`    title: ${(await page.title()).slice(0, 70)}`);
    const hits = text.match(/(hourly[^.]{0,60}|per hour[^.]{0,50}|day pass[^.]{0,50}|per person[^.]{0,40}|\$[\d.]+ ?\/ ?h(our)?|address[^.]{0,60}|yonge[^.]{0,40})/gi) || [];
    console.log(`    ${[...new Set(hits.map(h => h.trim()))].slice(0, 8).join(' | ') || 'no pricing/address text found'}`);
  } catch (e) {
    console.log(`--- ${url}  THROW ${String(e).split('\n')[0].slice(0, 70)}`);
  }
  await page.close();
}
await browser.close();
