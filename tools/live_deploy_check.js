// Post-deploy check: NO page.route injection — this loads the real deployed HTML.
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  // Same wait strategy as verify_thumbnail_fix.js: the React bundle hydrates
  // and injects the cards well after networkidle, so wait a flat 15s.
  const resp = await page.goto('https://findtorontoevents.ca/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(15000);
  // Freshness comes from the SERVED document, not the hydrated DOM: React
  // hydration rebuilds the hidden <p data-version> footer and drops the
  // attribute, so the stamp is only reliable in the raw response body.
  const servedHtml = await resp.text();
  const stampMatch = servedHtml.match(/2026-\d{2}-\d{2}-[a-f0-9]{7,10}/);
  const deployStamp = stampMatch ? stampMatch[0] : null;
  const r = await page.evaluate(() => {
    const imgs = [...document.querySelectorAll('img.card-thumbnail')];
    let wide = 0, wideRight = 0, normal = 0, normalCentered = 0;
    for (const img of imgs) {
      if (!img.naturalWidth) continue;
      const isWide = img.naturalWidth / img.naturalHeight >= 2.2 && img.naturalWidth >= 320;
      const pos = getComputedStyle(img).objectPosition;
      if (isWide) { wide++; if (pos === '100% 50%') wideRight++; }
      else { normal++; if (pos === '50% 50%') normalCentered++; }
    }
    return { total: imgs.length, wide, wideRight, normal, normalCentered };
  });
  r.deployStamp = deployStamp;
  console.log(JSON.stringify(r, null, 2));
  // Deploy stamp must carry today's UTC date — proves the live HTML is the
  // current deploy, not a stale copy. Reusable for future deploys.
  const today = new Date().toISOString().slice(0, 10);
  const stampOk = (deployStamp || '').startsWith(today);
  console.log(`expected stamp date: ${today}`);
  const pass = r.wide > 0 && r.wide === r.wideRight && r.normal === r.normalCentered && stampOk;
  console.log(pass ? 'LIVE-DEPLOY PASS' : 'LIVE-DEPLOY FAIL');
  await browser.close();
  process.exit(pass ? 0 : 1);
})();
