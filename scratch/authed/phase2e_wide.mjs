// Wide sweep — premium consoles across many sources.
// Each source is recorded with its own outcome: hit / negative / unknown.
// Unknowns are never folded into negatives.
import { chromium } from 'playwright';

const SOURCES = [
  // Walmart search pages (the category grid was identity-walled; search may not be)
  ['Walmart search', 'xbox series x', 'https://www.walmart.ca/en/search?q=xbox+series+x'],
  ['Walmart search', 'ps5 pro', 'https://www.walmart.ca/en/search?q=ps5+pro'],
  ['Walmart search', 'playstation 5 console', 'https://www.walmart.ca/en/search?q=playstation+5+console'],
  // Microsoft Store — first party, we already saw two OOS premium XSKUs
  ['Microsoft', 'Xbox Series X 1TB', 'https://www.microsoft.com/en-ca/d/xbox-series-x-1tb/8r2v1hbtl1tg'],
  ['Microsoft', 'Xbox Series S 1TB', 'https://www.microsoft.com/en-ca/d/xbox-series-s-1tb-white/8r02lkf9q26r'],
  // Staples / Toys R Us — GTA stores, product pages
  ['Staples', 'Xbox Series X search', 'https://www.staples.ca/search?query=xbox%20series%20x'],
  ['Toys R Us', 'PS5 search', 'https://www.toysrus.ca/en/search?q=ps5'],
  // GameStop / EB product-style listing
  ['EB Games', 'PS5 consoles', 'https://www.ebgames.ca/PlayStation-5/Consoles/c/playstation-5-consoles'],
];

const CONSOLE = /(xbox series [xs]|playstation\s*5|ps5)/i;
const STOCK = /(in stock|out of stock|sold out|add to cart|available|unavailable|pickup|pre-?order|only \d+ left)/i;
const GTA = /(toronto|markham|richmond hill|scarborough|north york|mississauga|vaughan|etobicoke|oakville|brampton|whitby|hamilton|ajax|pickering|thornhill)/i;

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];

for (const [retailer, label, url] of SOURCES) {
  const page = await ctx.newPage();
  const stamp = new Date().toISOString();
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => null);
    await page.waitForTimeout(5000);
    const r = await page.evaluate(({ consoleSrc, stockSrc, gtaSrc }) => {
      const cRe = new RegExp(consoleSrc, 'i'), sRe = new RegExp(stockSrc, 'i'), gRe = new RegExp(gtaSrc, 'i');
      const text = (document.body.innerText || '').replace(/[ \t]+/g, ' ');
      const walled = /verify your identity|unusual traffic|robot check|access denied|just a moment|are you a human/i.test(text);
      const lines = text.split('\n').map(s => s.trim()).filter(Boolean);
      const rows = [];
      for (let i = 0; i < lines.length; i++) {
        const l = lines[i];
        if (l.length > 150) continue;
        if (!cRe.test(l)) continue;
        const window = lines.slice(i, i + 5).join(' | ');
        if (!sRe.test(window)) continue;
        rows.push(window.slice(0, 200));
      }
      const gtaRows = rows.filter(x => gRe.test(x));
      const price = (text.match(/\$\s?\d{3,4}\.\d{2}/g) || []).slice(0, 6);
      return { title: document.title, walled, rows: [...new Set(rows)].slice(0, 12),
               gtaRows: [...new Set(gtaRows)].slice(0, 8), prices: [...new Set(price)] };
    }, { consoleSrc: CONSOLE.source, stockSrc: STOCK.source, gtaSrc: GTA.source });

    const verdict = r.walled ? 'UNKNOWN (bot-walled)' : (r.rows.length ? `${r.rows.length} console rows` : 'NO console rows');
    console.log(`--- [${retailer}] ${label}  ${resp ? 'http=' + resp.status() : 'http=?'}  ${verdict}  (${stamp})`);
    if (r.prices.length) console.log(`    prices seen: ${r.prices.join('  ')}`);
    for (const row of r.rows) console.log(`    ${row}`);
    if (r.gtaRows.length) { console.log('    GTA store mentions:'); for (const g of r.gtaRows) console.log(`      ${g}`); }
  } catch (e) {
    console.log(`--- [${retailer}] ${label} THROW ${String(e).split('\n')[0].slice(0, 80)}`);
  } finally { await page.close(); }
}
await browser.close();
