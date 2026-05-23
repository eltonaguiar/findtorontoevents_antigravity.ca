/**
 * Investigate event thumbnails on findtorontoevents.ca
 * Run: node tools/investigate_thumbnails.js
 */
const { chromium } = require('playwright');

const URL = 'https://findtorontoevents.ca/index.html';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  const consoleLogs = [];
  const imageErrors = [];
  const failedRequests = [];
  const badResponses = [];

  page.on('response', (res) => {
    const status = res.status();
    if (status >= 400) {
      badResponses.push({ url: res.url(), status });
    }
  });

  page.on('console', (msg) => {
    const type = msg.type();
    const text = msg.text();
    consoleLogs.push({ type, text });
    if (type === 'error' && (text.includes('404') || text.includes('img') || text.includes('image') || text.includes('failed') || text.includes('load'))) {
      imageErrors.push(text);
    }
  });

  page.on('requestfailed', (req) => {
    const url = req.url();
    if (url.match(/\.(jpg|jpeg|png|gif|webp|avif)/i) || url.includes('thumbnail') || url.includes('image')) {
      failedRequests.push({ url, failure: req.failure()?.errorText || 'unknown' });
    }
  });

  console.log('Navigating to', URL);
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(6000);

  // Scroll down to load more events (infinite scroll)
  for (let i = 0; i < 5; i++) {
    await page.evaluate(() => window.scrollBy(0, 600));
    await page.waitForTimeout(2000);
  }

  // Find event cards / tiles
  const eventData = await page.evaluate(() => {
    const cards = [];
    // Common selectors for event cards
    const selectors = [
      '[data-testid="event-card"]',
      '[class*="event"] [class*="card"]',
      'a[href*="/event"]',
      'article',
      '[class*="EventCard"]',
      '.event-card',
      '[class*="event-card"]',
    ];
    let els = document.querySelectorAll('img');
    const seen = new Set();
    els.forEach((img) => {
      const src = img.getAttribute('src');
      if (!src || seen.has(src)) return;
      seen.add(src);
      const card = img.closest('a, article, [class*="card"], [class*="tile"], [class*="event"]') || img.parentElement;
      const rect = img.getBoundingClientRect();
      const naturalWidth = img.naturalWidth || 0;
      const naturalHeight = img.naturalHeight || 0;
      const complete = img.complete;
      cards.push({
        src,
        parentTag: card ? card.tagName : null,
        parentClass: card && card.className ? String(card.className).slice(0, 80) : null,
        width: rect.width,
        height: rect.height,
        naturalWidth,
        naturalHeight,
        complete,
        alt: img.alt || null,
      });
    });
    return cards;
  });

  console.log('\n=== EVENT IMAGE ANALYSIS ===\n');
  console.log('Total unique img elements found:', eventData.length);

  const working = eventData.filter((e) => e.naturalWidth > 0 && e.complete);
  const broken = eventData.filter((e) => e.complete && (e.naturalWidth === 0 || e.naturalHeight === 0));
  const pending = eventData.filter((e) => !e.complete);

  console.log('Working thumbnails (naturalWidth > 0):', working.length);
  console.log('Broken thumbnails (complete but 0x0):', broken.length);
  console.log('Still loading:', pending.length);

  if (broken.length > 0) {
    console.log('\n--- Broken image URLs ---');
    broken.forEach((b, i) => {
      console.log(`${i + 1}. ${b.src}`);
    });
  }

  if (working.length > 0) {
    console.log('\n--- Sample working URLs ---');
    working.slice(0, 3).forEach((w, i) => {
      console.log(`${i + 1}. ${w.src}`);
    });
  }

  // Console errors
  const errLogs = consoleLogs.filter((l) => l.type === 'error');
  console.log('\n=== CONSOLE ERRORS (all) ===');
  if (errLogs.length === 0) {
    console.log('None');
  } else {
    errLogs.slice(0, 15).forEach((e, i) => console.log(`${i + 1}. ${e.text}`));
  }

  console.log('\n=== Image-related console errors ===');
  if (imageErrors.length === 0) {
    console.log('None');
  } else {
    imageErrors.forEach((e, i) => console.log(`${i + 1}. ${e}`));
  }

  console.log('\n=== Failed network requests (images) ===');
  if (failedRequests.length === 0) {
    console.log('None');
  } else {
    failedRequests.forEach((f, i) => console.log(`${i + 1}. ${f.url}\n   Reason: ${f.failure}`));
  }

  // Count event cards / links
  const cardCount = await page.evaluate(() => {
    const links = document.querySelectorAll('a[href*="event"], a[href*="events"]');
    const articles = document.querySelectorAll('article');
    return { linkCount: links.length, articleCount: articles.length };
  });
  console.log('\n=== Page structure ===');
  console.log('Links with event/events in href:', cardCount.linkCount);
  console.log('Article elements:', cardCount.articleCount);

  console.log('\n=== HTTP 4xx/5xx responses ===');
  if (badResponses.length === 0) {
    console.log('None');
  } else {
    badResponses.forEach((r, i) => console.log(`${i + 1}. [${r.status}] ${r.url}`));
  }

  // Event-card-specific: find cards with event/ticket links
  const eventCardAnalysis = await page.evaluate(() => {
    const eventLinks = document.querySelectorAll('a[href*="eventbrite"], a[href*="allevents"], a[href*="event"], a[href*="ticketmaster"], a[href*="universe.com"], a[href*="showpass"]');
    const cards = [];
    const seen = new Set();
    eventLinks.forEach((a) => {
      const card = a.closest('[class*="card"], [class*="Card"], [class*="tile"], [class*="Tile"], article, div[role="button"]') || a.parentElement?.parentElement;
      if (!card || seen.has(card)) return;
      seen.add(card);
      const img = card.querySelector('img');
      const src = img ? (img.getAttribute('src') || img.src || '') : '';
      const nw = img ? (img.naturalWidth || 0) : 0;
      const nh = img ? (img.naturalHeight || 0) : 0;
      const complete = img ? img.complete : false;
      const title = (card.textContent || '').slice(0, 60).trim();
      cards.push({
        hasImg: !!img,
        src: src ? src.slice(0, 150) : '',
        nw,
        nh,
        complete,
        working: complete && nw > 0,
        broken: complete && (nw === 0 || nh === 0) && src && !src.startsWith('data:'),
        title,
      });
    });
    return {
      totalEventCards: cards.length,
      withImg: cards.filter((c) => c.hasImg).length,
      working: cards.filter((c) => c.working).length,
      broken: cards.filter((c) => c.broken).length,
      noImg: cards.filter((c) => !c.hasImg).length,
      stillLoading: cards.filter((c) => c.hasImg && !c.complete).length,
      brokenUrls: cards.filter((c) => c.broken).map((c) => c.src),
      sampleCards: cards.slice(0, 8),
    };
  });

  console.log('\n=== EVENT CARD ANALYSIS (cards with event/ticket links) ===');
  console.log('Total event cards found:', eventCardAnalysis.totalEventCards);
  console.log('With img element:', eventCardAnalysis.withImg);
  console.log('Working thumbnails:', eventCardAnalysis.working);
  console.log('Broken thumbnails:', eventCardAnalysis.broken);
  console.log('No image:', eventCardAnalysis.noImg);
  console.log('Still loading:', eventCardAnalysis.stillLoading);
  if (eventCardAnalysis.brokenUrls.length > 0) {
    console.log('\nBroken image URLs:');
    eventCardAnalysis.brokenUrls.forEach((u, i) => console.log(`  ${i + 1}. ${u}`));
  }
  if (eventCardAnalysis.sampleCards.length > 0) {
    console.log('\nSample cards:');
    eventCardAnalysis.sampleCards.forEach((c, i) => {
      console.log(`  ${i + 1}. img=${c.hasImg} working=${c.working} broken=${c.broken} | ${c.title}`);
    });
  }

  // Per-card analysis: count event tiles and their images
  const cardAnalysis = await page.evaluate(() => {
    const tiles = document.querySelectorAll('[class*="tile"], [class*="Tile"], [class*="card"], [class*="Card"], article');
    const results = { total: 0, withImg: 0, imgWorking: 0, imgBroken: 0, imgEmpty: 0, noImg: 0, sampleSrcs: [] };
    const seenSrc = new Set();
    tiles.forEach((el) => {
      const img = el.querySelector('img');
      if (!img) {
        results.noImg++;
        return;
      }
      results.withImg++;
      const src = img.getAttribute('src') || '';
      const nw = img.naturalWidth || 0;
      const nh = img.naturalHeight || 0;
      const complete = img.complete;
      if (src && !src.startsWith('data:')) {
        if (!seenSrc.has(src)) {
          seenSrc.add(src);
          results.sampleSrcs.push({ src: src.slice(0, 120) + '...', nw, nh, complete });
        }
        if (complete && nw > 0) results.imgWorking++;
        else if (complete && (nw === 0 || nh === 0)) results.imgBroken++;
        else results.imgEmpty++;
      }
    });
    results.total = tiles.length;
    return results;
  });
  console.log('\n=== Event tile/card analysis ===');
  console.log('Total tiles/cards found:', cardAnalysis.total);
  console.log('With img element:', cardAnalysis.withImg);
  console.log('Images working (loaded, naturalWidth>0):', cardAnalysis.imgWorking);
  console.log('Images broken (complete but 0x0):', cardAnalysis.imgBroken);
  console.log('Images loading/empty:', cardAnalysis.imgEmpty);
  console.log('Tiles without img:', cardAnalysis.noImg);

  await browser.close();
})();
