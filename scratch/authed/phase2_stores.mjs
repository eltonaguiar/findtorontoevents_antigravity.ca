// Phase 2 — per-store availability from retailer DOM (Canada Computers, EB Games).
// Attaches to the running Chrome; reads store tables as structured rows, not
// keyword matches. Every row records where it came from.
import { chromium } from 'playwright';

const TARGETS = [
  ['Canada Computers', 'Xbox Series S 512GB', 'https://www.canadacomputers.com/en/xbox/184250/microsoft-xbox-series-s-512-gb-all-digital-console-white-rrs-00001.html'],
  ['Canada Computers', 'Xbox Series X 1TB', 'https://www.canadacomputers.com/en/xbox/184244/microsoft-xbox-series-x-1tb-black-rrt-00001.html'],
  ['EB Games', 'Xbox Series S', 'https://www.ebgames.ca/Xbox-Series-X-S/Consoles/c/xbox-series-x-s-consoles'],
];

const GTA = /(toronto|markham|richmond hill|scarborough|north york|mississauga|vaughan|etobicoke|oakville|brampton|whitby|hamilton|ajax|pickering|thornhill|unionville|downtown)/i;

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const stamp = new Date().toISOString();
const out = [];

for (const [retailer, product, url] of TARGETS) {
  const page = await ctx.newPage();
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(4000);

    // Pull table-ish rows: any element whose text names a place AND a stock word.
    const rows = await page.evaluate(() => {
      const stockWord = /(in stock|out of stock|sold out|available|unavailable|backorder|low stock|\b\d+\s*(left|in stock)\b)/i;
      const seen = new Set();
      const res = [];
      for (const el of document.querySelectorAll('tr, li, div')) {
        const t = (el.innerText || '').replace(/\s+/g, ' ').trim();
        if (!t || t.length > 160) continue;
        if (!stockWord.test(t)) continue;
        if (el.querySelector('tr, li')) continue;   // prefer leaf-ish nodes
        if (seen.has(t)) continue;
        seen.add(t);
        res.push(t);
      }
      return res.slice(0, 120);
    });

    const gta = rows.filter(r => GTA.test(r));
    out.push({ retailer, product, url, observed_at_utc: stamp,
      matched_gta_rows: gta.slice(0, 25), total_stock_rows: rows.length });

    console.log(`--- ${retailer} / ${product}`);
    console.log(`    stock-looking rows: ${rows.length}, mentioning GTA: ${gta.length}`);
    for (const g of gta.slice(0, 12)) console.log(`      ${g.slice(0, 130)}`);
    if (!gta.length) console.log(`      (none — sample) ${rows.slice(0, 4).map(r => r.slice(0, 80)).join(' | ') || '(no rows)'}`);
  } catch (e) {
    console.log(`--- ${retailer} / ${product} THROW ${String(e).split('\n')[0].slice(0, 90)}`);
  } finally {
    await page.close();
  }
}
await browser.close();
