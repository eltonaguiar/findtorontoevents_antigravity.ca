import { chromium } from 'playwright';
const q = 'xbox series x console';
const url = 'https://www.google.com/search?tbm=shop&q=' + encodeURIComponent(q) + '&gl=ca&hl=en';
const browser = await chromium.launch();
const ctx = await browser.newContext({
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  locale: 'en-CA', viewport: { width: 1400, height: 900 },
});
const page = await ctx.newPage();
let status = 'ERR', title = '';
try {
  const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  status = resp ? resp.status() : 'no-response';
  title = await page.title();
  await page.waitForTimeout(3000);
  const text = ((await page.innerText('body').catch(() => '')) || '').replace(/\s+/g, ' ');
  const consent = /before you continue|consent/i.test(text) && text.length < 1200;
  console.log(`http=${status}  title="${title.slice(0,70)}"`);
  console.log(`consent wall? ${consent ? 'YES — Google is asking for consent, cannot read listings' : 'no'}`);
  console.log(`textLen=${text.length}`);
  const prices = text.match(/\$[\d,]+\.\d{2}/g) || [];
  const shops = text.match(/(best buy|walmart|amazon|canada computers|gamestop|eb games|microsoft|the source|staples)/gi) || [];
  console.log(`prices seen: ${[...new Set(prices)].slice(0,10).join(', ') || 'none'}`);
  console.log(`retailers seen: ${[...new Set(shops.map(s=>s.toLowerCase()))].join(', ') || 'none'}`);
  console.log(`\nfirst 400 chars:\n${text.slice(0,400)}`);
} catch (e) {
  console.log('THROW:', String(e).split('\n')[0].slice(0,120));
}
await browser.close();
