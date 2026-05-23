const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  console.log('Navigating to localhost:5173...');
  await page.goto('http://localhost:5173/', { waitUntil: 'load', timeout: 60000 });

  console.log('Waiting 20 seconds for React hydration + thumbnail enforcer...');
  await page.waitForTimeout(20000);

  const result = await page.evaluate(() => {
    const rawLen = window.__RAW_EVENTS__ ? window.__RAW_EVENTS__.length : 'NOT LOADED';
    const thumbsOn = document.body.classList.contains('thumbnails-on');
    const glassCards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');

    let cardsWithTitle = 0;
    let cardsWithThumb = 0;
    let cardsWithPlaceholder = 0;
    let cardsWithNone = 0;
    let thumbDomains = {};

    glassCards.forEach((c) => {
      const t = c.querySelector('h2, h3, [class*="title"], [class*="Title"]');
      if (t) cardsWithTitle++;
      const img = c.querySelector('.card-thumbnail');
      if (img) {
        cardsWithThumb++;
        try {
          const u = new URL(img.src);
          const d = u.hostname;
          thumbDomains[d] = (thumbDomains[d] || 0) + 1;
        } catch(e) {}
      }
      if (c.querySelector('.card-thumb-placeholder')) cardsWithPlaceholder++;
      if (!c.querySelector('.card-thumbnail') && !c.querySelector('.card-thumb-placeholder'))
        cardsWithNone++;
    });

    let eventsWithImg = 0;
    if (window.__RAW_EVENTS__) {
      eventsWithImg = window.__RAW_EVENTS__.filter(
        (e) => e.image || e.imageUrl || e.thumbnail
      ).length;
    }

    const brokenImages = [];
    document.querySelectorAll('.card-thumbnail').forEach((img) => {
      if (img.naturalWidth === 0 || img.complete === false) {
        brokenImages.push(img.src.substring(0, 100));
      }
    });

    return {
      rawEventsLoaded: rawLen,
      eventsWithImages: eventsWithImg,
      thumbnailsOn: thumbsOn,
      totalGlassCards: glassCards.length,
      cardsWithTitle,
      cardsWithThumb,
      cardsWithPlaceholder,
      cardsWithNone,
      thumbDomains,
      brokenImagesSample: brokenImages.slice(0, 5),
    };
  });

  console.log('\n=== LOCAL THUMBNAIL TEST RESULTS ===\n');
  console.log(JSON.stringify(result, null, 2));

  const success = result.cardsWithNone <= 2 && (result.cardsWithThumb + result.cardsWithPlaceholder) > 10;
  console.log(`\n${success ? '✅ PASS' : '❌ FAIL'}: ${result.cardsWithThumb} thumbnails, ${result.cardsWithPlaceholder} placeholders, ${result.cardsWithNone} unprocessed cards`);

  await browser.close();
  process.exit(success ? 0 : 1);
})();
