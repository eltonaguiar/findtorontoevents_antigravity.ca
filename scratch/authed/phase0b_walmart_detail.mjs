// Phase 0b — Walmart detail: real price, store address, and whether
// a downtown-core store also has pickup. Never disturbs the user's tabs.
import { chromium } from 'playwright';

const URL = 'https://www.walmart.ca/en/ip/XBOX-Series-S-All-Digital-Gaming-Console-512GB-SSD-Includes-XBOX-Wireless-Controller-120FPS-Robot-White/7IY33NVWJOKP?selectedSellerId=0';

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const now = new Date().toISOString();
try {
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(6000);

  // Price: prefer structured data / meta, fall back to the buy-box text.
  const price = await page.evaluate(() => {
    const ld = [...document.querySelectorAll('script[type="application/ld+json"]')]
      .map(s => { try { return JSON.parse(s.textContent); } catch { return null; } })
      .flat().filter(Boolean);
    for (const o of ld) {
      const off = o.offers || (Array.isArray(o) ? o.map(x => x.offers).flat().filter(Boolean) : []);
      const p = Array.isArray(off) ? off[0]?.price : off?.price;
      if (p) return { price: p, currency: (Array.isArray(off) ? off[0]?.priceCurrency : off?.priceCurrency) || 'CAD', src: 'json-ld' };
    }
    const og = document.querySelector('meta[property="product:price:amount"]');
    if (og) return { price: og.content, currency: 'CAD', src: 'og' };
    const m = (document.body.innerText || '').match(/\$\s?(\d{2,4}\.\d{2})/);
    return m ? { price: m[1], currency: 'CAD', src: 'text-match' } : null;
  });

  // Store identity: whatever the page itself says about the pickup store.
  const store = await page.evaluate(() => {
    const t = document.body.innerText || '';
    const m = t.match(/pickup[^\n]{0,30}?at\s+([A-Z][A-Za-z0-9 .'\-&]{3,40})/i);
    const addr = t.match(/(\d{2,5})\s+([A-Za-z0-9 .'\-]{3,45}?(?:Ave|St|Street|Blvd|Rd|Road|Dr|Way|Pkwy)[A-Za-z0-9 .,'\-]{0,25})/);
    return { store: m ? m[1].trim() : null, address: addr ? `${addr[1]} ${addr[2]}`.trim() : null };
  });

  const avail = await page.evaluate(() => {
    const t = document.body.innerText || '';
    const pick = /(free pickup[^\n]{0,60})/i.exec(t);
    const deliv = /(free delivery[^\n]{0,70})/i.exec(t);
    const cart = /(add to cart|out of stock|sold out)/i.exec(t);
    return { pickup: pick?.[1] || null, delivery: deliv?.[1] || null, cart: cart?.[1] || null };
  });

  console.log(JSON.stringify({ observed_at_utc: now, url: URL, price, store, avail,
    title: await page.title() }, null, 2));
} catch (e) {
  console.log('THROW ' + String(e).split('\n')[0].slice(0, 120));
} finally {
  await page.close();
  await browser.close();
}
