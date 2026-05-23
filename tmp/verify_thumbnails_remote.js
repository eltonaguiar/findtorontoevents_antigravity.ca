const { chromium } = require('playwright');

const SITES = [
  'https://findtorontoevents.ca/index.html',
  'https://torontoevent.net/index.html',
  'https://tdotevent.ca/index.html',
];

(async () => {
  const browser = await chromium.launch();

  for (const url of SITES) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`Testing: ${url}`);
    console.log('='.repeat(60));

    const page = await browser.newPage();
    try {
      await page.goto(url, { waitUntil: 'load', timeout: 30000 });
    } catch (e) {
      console.log(`  ERROR loading page: ${e.message}`);
      await page.close();
      continue;
    }

    console.log('  Waiting 25 seconds for thumbnails...');
    await page.waitForTimeout(25000);

    const result = await page.evaluate(() => {
      const rawLen = window.__RAW_EVENTS__ ? window.__RAW_EVENTS__.length : 'NOT LOADED';
      const thumbsOn = document.body.classList.contains('thumbnails-on');
      const cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');

      let withThumb = 0, withPlaceholder = 0, withNeither = 0, withTitle = 0;
      let thumbDomains = {};
      let broken = [];

      cards.forEach(c => {
        const t = c.querySelector('h2, h3, [class*="title"], [class*="Title"]');
        if (t) withTitle++;
        const img = c.querySelector('.card-thumbnail');
        if (img) {
          withThumb++;
          try {
            const d = new URL(img.src).hostname;
            thumbDomains[d] = (thumbDomains[d] || 0) + 1;
          } catch(e) {}
          if (img.naturalWidth === 0) broken.push(img.src.substring(0, 80));
        } else if (c.querySelector('.card-thumb-placeholder')) {
          withPlaceholder++;
        } else {
          withNeither++;
        }
      });

      let evWithImg = 0;
      if (window.__RAW_EVENTS__) {
        evWithImg = window.__RAW_EVENTS__.filter(e => e.image || e.imageUrl || e.thumbnail).length;
      }

      return { rawLen, evWithImg, thumbsOn, total: cards.length, withTitle, withThumb, withPlaceholder, withNeither, thumbDomains, broken: broken.slice(0, 3) };
    });

    console.log(`  Events loaded: ${result.rawLen} (${result.evWithImg} with images)`);
    console.log(`  Thumbnails ON: ${result.thumbsOn}`);
    console.log(`  Cards: ${result.total} total, ${result.withTitle} with titles`);
    console.log(`  Thumbnails: ${result.withThumb} images, ${result.withPlaceholder} placeholders, ${result.withNeither} empty`);
    console.log(`  Image domains: ${JSON.stringify(result.thumbDomains)}`);
    if (result.broken.length > 0) {
      console.log(`  Broken images: ${result.broken.join(', ')}`);
    }

    const ok = result.withThumb + result.withPlaceholder > 10 && result.withNeither <= 2;
    console.log(`\n  ${ok ? 'PASS' : 'FAIL'}`);

    await page.close();
  }

  await browser.close();
})();
