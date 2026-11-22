// Phase 2c — retry the two failed probes honestly.
// Walmart category: wait for hydration + scroll, then collect console cards by
// product NAME (not by /ip/ anchors, which may be rendered late or as buttons).
// CC PS5: search the site instead of guessing a product URL.
import { chromium } from 'playwright';

const WALMART_CAT = 'https://www.walmart.ca/en/browse/video-games/microsoft-xbox-series-x-series-s/10012_6000201024446_6000202240017?facet=pgls_pcs_video_game_platform%3AXbox+Series+X+%26+S%7C%7Cpgls_pcs_video_game_platform%3ASony+PlayStation+5';
const CONSOLE = /(xbox series [xs]|playstation\s*5|ps5)/i;

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const stamp = new Date().toISOString();

{
  const page = await ctx.newPage();
  try {
    await page.goto(WALMART_CAT, { waitUntil: 'load', timeout: 90000 }).catch(() => {});
    await page.waitForTimeout(8000);
    for (let i = 0; i < 3; i++) { await page.mouse.wheel(0, 1600); await page.waitForTimeout(2500); }

    const info = await page.evaluate((src) => {
      const re = new RegExp(src, 'i');
      const body = (document.body.innerText || '').replace(/[ \t]+/g, ' ');
      const lines = body.split('\n').map(s => s.trim()).filter(Boolean);
      const hits = [];
      for (let i = 0; i < lines.length; i++) {
        if (re.test(lines[i]) && lines[i].length < 160) {
          // keep the line and the next few short lines (price / stock usually follow)
          hits.push(lines.slice(i, i + 4).join(' | ').slice(0, 190));
        }
      }
      const anchors = [...document.querySelectorAll('a')].map(a => a.href).filter(h => h.includes('/ip/'));
      return { title: document.title, blockCount: document.querySelectorAll('[data-testid],[class*="product"]').length,
               ipAnchors: [...new Set(anchors)].length, hits: [...new Set(hits)].slice(0, 40) };
    }, CONSOLE.source);

    console.log(`--- Walmart category retry (${stamp})`);
    console.log(`    title="${info.title.slice(0, 70)}" ipAnchors=${info.ipAnchors} productishNodes=${info.blockCount}`);
    if (!info.hits.length) console.log('    no console lines found — page likely not hydrated or bot-walled');
    for (const h of info.hits) console.log(`    ${h}`);
  } catch (e) {
    console.log(`--- Walmart category retry THROW ${String(e).split('\n')[0].slice(0, 90)}`);
  } finally { await page.close(); }
}

{
  const page = await ctx.newPage();
  try {
    await page.goto('https://www.canadacomputers.com/en/search?s=playstation%205%20console', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    const r = await page.evaluate(() => {
      const out = [];
      for (const a of document.querySelectorAll('a[href*="/en/"]')) {
        const t = (a.innerText || '').replace(/\s+/g, ' ').trim();
        if (/playstation|ps5/i.test(t) && t.length < 120) out.push(`${t} -> ${a.href}`);
      }
      return [...new Set(out)].slice(0, 15);
    });
    console.log(`--- CC search "playstation 5 console" (${stamp})`);
    if (!r.length) console.log('    no product links matched');
    for (const x of r) console.log(`    ${x}`);
  } catch (e) {
    console.log(`--- CC search THROW ${String(e).split('\n')[0].slice(0, 90)}`);
  } finally { await page.close(); }
}

await browser.close();
