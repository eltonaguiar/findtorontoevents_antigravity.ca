// Phase 0 — verify the Walmart Stockyards pickup lead.
// Attaches to the already-running Chrome (CDP 9222) so we inherit cookies
// and a real rendering engine; never launches, so no EGL/GPU init.
import { chromium } from 'playwright';

const URL = 'https://www.walmart.ca/en/ip/XBOX-Series-S-All-Digital-Gaming-Console-512GB-SSD-Includes-XBOX-Wireless-Controller-120FPS-Robot-White/7IY33NVWJOKP?selectedSellerId=0';

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();          // my own tab, so I never disturb the user's

try {
  const resp = await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(6000);
  const title = await page.title();
  const text = ((await page.innerText('body').catch(() => '')) || '').replace(/[ \t]+/g, ' ');

  const blocked = /access denied|unusual traffic|verify you are|robot check|just a moment|something went wrong/i.test(text);

  console.log(`http=${resp ? resp.status() : '?'}  blocked=${blocked}`);
  console.log(`title="${title.slice(0, 90)}"`);

  // price — first CAD figure on the page
  const price = text.match(/\$\s?([\d,]+\.\d{2})/);
  console.log(`price=${price ? '$' + price[1] : '(none)'}`);

  // fulfilment words near the top matter most; print any line mentioning them
  const KEYS = /(pickup|pick up|delivery|ship|in stock|out of stock|sold out|add to cart|stockyards|st\.? clair)/i;
  const lines = text.split(/\n|(?<=\.)\s+/).map(s => s.trim()).filter(Boolean);
  const hits = lines.filter(l => KEYS.test(l)).slice(0, 40);
  console.log('--- fulfilment lines ---');
  for (const l of hits) console.log('  ' + l.slice(0, 160));

  // any store name + address pattern
  const stores = [...text.matchAll(/([A-Z][A-Za-z0-9 .'&\-]{3,40})\s*[,\u2013-]\s*(\d{2,5}\s+[A-Za-z0-9 .'\-]{3,45}(?:Ave|St|Street|Blvd|Rd|Road|Dr|Way|Pkwy)[^,\n]{0,20})/g)]
    .map(m => `${m[1].trim()} — ${m[2].trim()}`);
  if (stores.length) {
    console.log('--- store/address candidates ---');
    for (const s of [...new Set(stores)].slice(0, 20)) console.log('  ' + s);
  }
} catch (e) {
  console.log('THROW ' + String(e).split('\n')[0].slice(0, 120));
} finally {
  await page.close();
  await browser.close();   // closes the CDP connection, not the browser
}
