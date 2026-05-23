/**
 * Inspect event thumbnails on torontoevent.net - count cards, check image status, report errors
 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const consoleErrors = [];
  const failedRequests = []; // 404, CORS, etc.

  page.on('console', (msg) => {
    const t = msg.type();
    const text = msg.text();
    if (t === 'error') consoleErrors.push(text);
  });

  page.on('response', (response) => {
    const status = response.status();
    const url = response.url();
    if (status >= 400) {
      failedRequests.push({ status, url });
    }
  });

  console.log('Navigating to https://torontoevent.net/index.html...');
  await page.goto('https://torontoevent.net/index.html', {
    waitUntil: 'domcontentloaded',
    timeout: 30000,
  });

  // Wait for events to appear (React may take a few seconds)
  await page.waitForSelector('[class*="glass-panel"], [class*="event-card"], [class*="EventCard"], [id="__next"]', {
    timeout: 20000,
  }).catch(() => {});

  await page.waitForTimeout(5000);

  // Scroll to trigger lazy load
  await page.evaluate(() => window.scrollTo(0, 800));
  await page.waitForTimeout(1500);
  await page.evaluate(() => window.scrollTo(0, 2000));
  await page.waitForTimeout(1500);

  const result = await page.evaluate(() => {
    const cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]');
    const visibleCards = Array.from(cards).filter((c) => !c.classList.contains('event-card-hidden'));
    const imgEls = document.querySelectorAll('.card-thumbnail, .card-thumb-placeholder, [class*="glass-panel"] img, [class*="event-card"] img');
    const imgs = Array.from(imgEls);

    const withThumb = imgs.filter((img) => img.classList && img.classList.contains('card-thumbnail'));
    const withPlaceholder = document.querySelectorAll('.card-thumb-placeholder').length;
    const imageSrcs = imgs.map((img) => img.src || img.getAttribute('src')).filter(Boolean);

    // Check which imgs are broken (naturalWidth 0 after load attempt)
    const brokenUrls = [];
    imgs.forEach((img) => {
      if (img.tagName === 'IMG' && img.src && (img.naturalWidth === 0 || img.complete === false)) {
        brokenUrls.push(img.src);
      }
    });

    const rawEvents = window.__RAW_EVENTS__ || [];
    const eventsWithImages = rawEvents.filter((e) => (e.image || e.imageUrl || e.thumbnail));
    const sampleUrls = (eventsWithImages.slice(0, 10) || []).map((e) => e.image || e.imageUrl || e.thumbnail);

    return {
      totalCards: cards.length,
      visibleCards: visibleCards.length,
      totalImgs: imgs.length,
      thumbnailsClass: withThumb.length,
      placeholders: withPlaceholder,
      imageSrcs: imageSrcs.slice(0, 20),
      brokenUrls: brokenUrls.slice(0, 20),
      rawEventsCount: rawEvents.length,
      eventsWithImageCount: eventsWithImages.length,
      sampleImageUrls: sampleUrls,
    };
  });

  console.log('\n=== EVENT THUMBNAIL REPORT ===\n');
  console.log('Visible event cards:', result.visibleCards);
  console.log('Total cards (incl. hidden):', result.totalCards);
  console.log('Raw events (__RAW_EVENTS__):', result.rawEventsCount);
  console.log('Events with image/thumbnail in data:', result.eventsWithImageCount);
  console.log('Img elements (card-thumbnail class):', result.thumbnailsClass);
  console.log('Placeholder divs (card-thumb-placeholder):', result.placeholders);

  if (result.sampleImageUrls.length) {
    console.log('\nSample image URLs from event data (first 10):');
    result.sampleImageUrls.forEach((u, i) => console.log(`  ${i + 1}. ${u}`));
  }

  if (result.brokenUrls.length) {
    console.log('\nBroken/missing image URLs (naturalWidth=0 or not loaded):');
    result.brokenUrls.forEach((u) => console.log(`  - ${u}`));
  }

  if (result.imageSrcs.length) {
    console.log('\nAll image src values (first 20):');
    result.imageSrcs.forEach((u) => console.log(`  - ${u}`));
  }

  const imageErrors = failedRequests.filter((r) =>
    /\.(jpg|jpeg|png|gif|webp|svg)/i.test(r.url) || r.url.includes('image') || r.url.includes('thumbnail')
  );
  const otherRelevant = failedRequests.filter((r) =>
    !r.url.includes('googleads') && !r.url.includes('doubleclick') && !r.url.includes('googlesyndication')
  );

  console.log('\n=== NETWORK FAILURES (non-ad) ===');
  otherRelevant.slice(0, 30).forEach((r) => console.log(`  [${r.status}] ${r.url}`));

  if (imageErrors.length) {
    console.log('\n=== IMAGE-RELATED 404s/FAILURES ===');
    imageErrors.forEach((r) => console.log(`  [${r.status}] ${r.url}`));
  }

  console.log('\n=== CONSOLE ERRORS (non-googleads) ===');
  consoleErrors
    .filter((e) => !e.includes('googleads') && !e.includes('googlesyndication'))
    .slice(0, 20)
    .forEach((e) => console.log(`  - ${e}`));

  console.log('\n=== SUMMARY ===');
  const working = result.thumbnailsClass - result.brokenUrls.length;
  const broken = result.brokenUrls.length;
  const placeholders = result.placeholders;
  console.log(`  Working thumbnails: ~${Math.max(0, working)}`);
  console.log(`  Broken/missing: ${broken}`);
  console.log(`  Colour placeholders: ${placeholders}`);

  await browser.close();
})();
