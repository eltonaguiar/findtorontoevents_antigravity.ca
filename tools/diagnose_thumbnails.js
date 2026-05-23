/**
 * Diagnose why thumbnails are not being injected on findtorontoevents.ca
 * Run: node tools/diagnose_thumbnails.js
 */
const { chromium } = require('playwright');

const URL = 'https://findtorontoevents.ca/index.html';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  console.log('Navigating to', URL);
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 30000 });

  console.log('Waiting 15 seconds for React to hydrate and events to render...');
  await page.waitForTimeout(15000);

  const result = await page.evaluate(() => {
    const rawLen = window.__RAW_EVENTS__ ? window.__RAW_EVENTS__.length : 'NOT LOADED';

    const thumbsOn = document.body.classList.contains('thumbnails-on');

    const glassCards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
    const eventCards = document.querySelectorAll('[class*="event-card"], [class*="EventCard"]');

    let cardsWithTitle = 0;
    let cardsWithThumb = 0;
    let cardsWithPlaceholder = 0;
    let cardsWithNone = 0;
    glassCards.forEach((c) => {
      const t = c.querySelector('h2, h3, [class*="title"], [class*="Title"]');
      if (t) cardsWithTitle++;
      if (c.querySelector('.card-thumbnail')) cardsWithThumb++;
      if (c.querySelector('.card-thumb-placeholder')) cardsWithPlaceholder++;
      if (!c.querySelector('.card-thumbnail') && !c.querySelector('.card-thumb-placeholder'))
        cardsWithNone++;
    });

    const sampleCard = glassCards[0];
    const sampleHTML = sampleCard ? sampleCard.outerHTML.substring(0, 800) : 'NO CARDS';

    // First 15 card titles (to see if they're section names vs event names)
    const titleTexts = [];
    glassCards.forEach((c, i) => {
      if (i >= 15) return;
      const t = c.querySelector('h2, h3, [class*="title"], [class*="Title"]');
      if (t) titleTexts.push((t.textContent || '').trim().substring(0, 60));
    });

    // Full HTML of a card that has NO thumb (typical event card structure)
    let noThumbCardHTML = '';
    for (let i = 0; i < glassCards.length; i++) {
      const c = glassCards[i];
      if (!c.querySelector('.card-thumbnail') && !c.querySelector('.card-thumb-placeholder')) {
        const t = c.querySelector('h2, h3, [class*="title"], [class*="Title"]');
        const txt = t ? (t.textContent || '').trim() : '';
        if (txt.length > 5 && !txt.match(/^(Global Feed|Filter|VR Hub)/i)) {
          noThumbCardHTML = c.outerHTML.substring(0, 1500);
          break;
        }
      }
    }

    let eventsWithImg = 0;
    if (window.__RAW_EVENTS__) {
      eventsWithImg = window.__RAW_EVENTS__.filter(
        (e) => e.image || e.imageUrl || e.thumbnail
      ).length;
    }

    return {
      rawEventsLoaded: rawLen,
      eventsWithImages: eventsWithImg,
      thumbnailsOn: thumbsOn,
      glassCards: glassCards.length,
      eventCards: eventCards.length,
      cardsWithTitle,
      cardsWithThumb,
      cardsWithPlaceholder,
      cardsWithNone,
      sampleCardHTML: sampleHTML,
      first15TitleTexts: titleTexts,
      noThumbCardHTML: noThumbCardHTML,
    };
  });

  console.log('\n=== DIAGNOSTIC RESULTS ===\n');
  console.log(JSON.stringify(result, null, 2));

  // Additional: check for cards that DON'T match glass-panel but are event cards
  const altCardAnalysis = await page.evaluate(() => {
    const eventLinks = document.querySelectorAll(
      'a[href*="eventbrite"], a[href*="allevents"], a[href*="ticketmaster"], a[href*="universe.com"]'
    );
    const classCounts = {};
    const sampleClasses = [];
    eventLinks.forEach((a, i) => {
      const card = a.closest('[class*="card"], [class*="Card"], [class*="tile"], [class*="tile"], article, [class*="glass"], div[role="button"], div');
      if (card && i < 5) {
        sampleClasses.push({
          tag: card.tagName,
          className: card.className,
          hasGlassPanel: (card.className || '').includes('glass-panel'),
        });
      }
      const cn = (card && card.className) ? String(card.className).split(/\s+/).filter(Boolean)[0] || 'none' : 'no-parent';
      classCounts[cn] = (classCounts[cn] || 0) + 1;
    });
    return { classCounts, sampleClasses };
  });

  console.log('\n=== ALTERNATIVE CARD SELECTORS (event links parent classes) ===\n');
  console.log(JSON.stringify(altCardAnalysis, null, 2));

  // Check ALL elements that might be event cards (broader selector)
  const broaderAnalysis = await page.evaluate(() => {
    const candidates = [
      { sel: '[class*="glass-panel"]', count: document.querySelectorAll('[class*="glass-panel"]').length },
      { sel: '[class*="glass"]', count: document.querySelectorAll('[class*="glass"]').length },
      { sel: '[class*="event"]', count: document.querySelectorAll('[class*="event"]').length },
      { sel: '[class*="card"]', count: document.querySelectorAll('[class*="card"]').length },
      { sel: '[class*="tile"]', count: document.querySelectorAll('[class*="tile"]').length },
      { sel: 'article', count: document.querySelectorAll('article').length },
    ];
    return candidates;
  });

  console.log('\n=== BROADER SELECTOR COUNTS ===\n');
  broaderAnalysis.forEach((r) => console.log(`  ${r.sel}: ${r.count}`));

  await browser.close();
})();
