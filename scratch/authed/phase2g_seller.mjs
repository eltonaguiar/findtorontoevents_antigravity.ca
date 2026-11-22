// Phase 2g — for each pickup-today console, capture WHO sells it and its
// condition. A marketplace seller at 2x MSRP is not the same claim as
// first-party Walmart stock, so the two must never share a table row style.
import { chromium } from 'playwright';

const TARGETS = [
  ['Xbox Series X - 1TB SSD - Carbon Black (with Disk)', 'https://www.walmart.ca/en/search?q=xbox+series+x', /Xbox Series X - 1TB SSD - Carbon Black/i],
  ['Xbox Series X Console [Certified Microsoft Refurbished]', 'https://www.walmart.ca/en/search?q=xbox+series+x', /Certified Microsoft Refurbished/i],
  ['Xbox Series X Gaming Console - 1TB SSD Black', 'https://www.walmart.ca/en/search?q=xbox+series+x', /Xbox Series X Gaming Console - 1TB SSD Black/i],
  ['Sony PlayStation 5 Pro Console', 'https://www.walmart.ca/en/search?q=ps5', /PlayStation 5 Pro Console \(PS5 Pro\)/i],
  ['PS5 Disc Console Slim - White (Refurbished)', 'https://www.walmart.ca/en/search?q=ps5', /Disc Console Slim - White \(Refurbished\)/i],
];

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];

for (const [label, searchUrl, re] of TARGETS) {
  const sp = await ctx.newPage();
  let href = null;
  try {
    await sp.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await sp.waitForTimeout(4500);
    href = await sp.evaluate((src) => {
      const r = new RegExp(src.slice(1, src.lastIndexOf('/')), 'i');
      for (const a of document.querySelectorAll('a[href*="/ip/"]')) {
        const box = a.closest('div') || a;
        const t = (box.innerText || '').replace(/\s+/g, ' ');
        if (r.test(t)) return a.href;
      }
      return null;
    }, re.toString());
  } catch (e) { console.log(`--- ${label} SEARCH THROW`); }
  finally { await sp.close(); }

  if (!href) { console.log(`--- ${label}: no matching product link`); continue; }

  const p = await ctx.newPage();
  const stamp = new Date().toISOString();
  try {
    await p.goto(href, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await p.waitForTimeout(5000);
    const r = await p.evaluate(() => {
      const t = (document.body.innerText || '').replace(/[ \t]+/g, ' ');
      const one = (re) => { const m = t.match(re); return m ? m[0].replace(/\s+/g, ' ').trim().slice(0, 100) : null; };
      return {
        seller: one(/Sold (?:and shipped )?by\s+[^\n|]{2,40}/i),
        condition: one(/\b(Refurbished|Certified Refurbished|Open Box|Pre-owned|Used|Brand New|New)\b/i),
        pickup: one(/free pickup[^\n]{0,50}|Pickup today/i),
        price: one(/\$\s?\d{3,4}\.\d{2}/),
      };
    });
    const firstParty = r.seller && /Walmart/i.test(r.seller);
    console.log(`--- ${label}  (${stamp})`);
    console.log(`    price=${r.price} seller="${r.seller ?? '—'}" condition="${r.condition ?? '—'}" pickup="${r.pickup ?? '—'}"`);
    console.log(`    => ${firstParty ? 'FIRST-PARTY' : 'MARKETPLACE / third-party'}`);
  } catch (e) {
    console.log(`--- ${label} THROW ${String(e).split('\n')[0].slice(0, 70)}`);
  } finally { await p.close(); }
}
await browser.close();
