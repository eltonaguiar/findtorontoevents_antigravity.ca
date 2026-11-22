import { chromium } from 'playwright';
const browser = await chromium.launch();
const ctx = await browser.newContext({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', locale: 'en-CA' });

// 1) Canada Computers: PS5 (both disc + digital) and Series S
for (const q of ['playstation 5', 'xbox series s']) {
  const page = await ctx.newPage();
  await page.goto('https://www.canadacomputers.com/en/search?s=' + encodeURIComponent(q), { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(2500);
  const links = await page.$$eval('a[href*="/en/"]', as => as.map(a => ({ h: a.href, t: (a.innerText||'').replace(/\s+/g,' ').trim() }))
    .filter(o => /playstation 5|xbox series s/i.test(o.t) && o.t.length > 12 && o.t.length < 160 && !/results$/i.test(o.t)));
  const seen = new Set(); console.log(`\n=== canadacomputers "${q}" — ${links.length} product links`);
  for (const l of links) { if (seen.has(l.h) || seen.size >= 4) continue; seen.add(l.h); console.log(`  ${l.t.slice(0,70)}\n      ${l.h}`); }
  await page.close();
}

// 2) Microsoft Store CA — Xbox
{
  const page = await ctx.newPage();
  try {
    await page.goto('https://www.microsoft.com/en-ca/store/b/xbox', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(2500);
    const text = ((await page.innerText('body')) || '').replace(/\s+/g, ' ');
    const hits = text.match(/(out of stock|in stock|sold out|add to cart|unavailable)[^.]{0,60}/gi) || [];
    console.log(`\n=== microsoft.com/en-ca/store/b/xbox  http=${(await page.title()).slice(0,40)}`);
    console.log(`  stock signals: ${[...new Set(hits.map(h => h.trim().toLowerCase()))].slice(0,6).join(' | ') || 'none found'}`);
  } catch (e) { console.log(`\n=== microsoft store THROW: ${String(e).split('\n')[0].slice(0,90)}`); }
  await page.close();
}
await browser.close();
