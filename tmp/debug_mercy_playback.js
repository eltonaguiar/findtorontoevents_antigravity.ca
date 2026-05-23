const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const errors = [];
  const ytEvents = [];

  page.on('pageerror', (err) => errors.push(`PageError: ${err.message}`));
  page.on('console', (msg) => {
    const text = msg.text();
    if (msg.type() === 'error' && !text.includes('postMessage')) {
      errors.push(`ConsoleError: ${text}`);
    }
    if (text.includes('Mercy') || text.includes('mercy') || text.includes('JUADqWkJiiE')) {
      ytEvents.push(`[${msg.type()}] ${text}`);
    }
    if (text.includes('Playing video') || text.includes('Initialized YouTube') || text.includes('search') || text.includes('filter')) {
      ytEvents.push(`[${msg.type()}] ${text}`);
    }
  });

  console.log('=== Navigating to MOVIESHOWS3 ===');
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', {
    waitUntil: 'networkidle',
    timeout: 30000
  });
  await page.waitForTimeout(3000);

  // Dismiss mute overlay
  await page.evaluate(() => {
    const overlay = document.getElementById('muteOverlay');
    if (overlay) overlay.click();
  });
  await page.waitForTimeout(1000);

  // Find the search input and search for Mercy
  console.log('\n=== Searching for Mercy ===');

  const searchResult = await page.evaluate(() => {
    const input = document.getElementById('browseSearchInput');
    if (!input) return { error: 'browseSearchInput not found' };

    input.value = 'Mercy';
    input.dispatchEvent(new Event('input', { bubbles: true }));

    const applyBtn = document.querySelector('.apply-filters-btn') ||
                     document.querySelector('[onclick*="applyBrowseFilters"]') ||
                     document.querySelector('button.apply');

    return {
      inputFound: true,
      inputValue: input.value,
      applyBtn: applyBtn ? applyBtn.textContent.trim() : 'not found'
    };
  });

  console.log('Search setup:', JSON.stringify(searchResult));

  // Try to trigger the search/filter
  await page.evaluate(() => {
    if (typeof applyBrowseFilters === 'function') {
      applyBrowseFilters();
    }
  });
  await page.waitForTimeout(2000);

  // Check what's visible after search
  const afterSearch = await page.evaluate(() => {
    const cards = document.querySelectorAll('.video-card, .movie-card');
    const visibleCards = [];
    cards.forEach(card => {
      const style = window.getComputedStyle(card);
      if (style.display !== 'none' && style.visibility !== 'hidden') {
        const title = card.querySelector('.movie-title, .title, h3, h4');
        const iframe = card.querySelector('iframe');
        visibleCards.push({
          title: title ? title.textContent.trim() : 'no title',
          iframeSrc: iframe ? (iframe.src || iframe.dataset.src) : 'no iframe',
          display: style.display
        });
      }
    });
    return { totalCards: cards.length, visibleCards: visibleCards.slice(0, 10) };
  });

  console.log('\nAfter search:', JSON.stringify(afterSearch, null, 2));

  // Check for Mercy specifically
  const mercyCard = await page.evaluate(() => {
    const cards = document.querySelectorAll('.video-card, .movie-card');
    for (const card of cards) {
      const titleEl = card.querySelector('.movie-title, .title, h3, h4');
      if (titleEl && titleEl.textContent.toLowerCase().includes('mercy')) {
        const iframe = card.querySelector('iframe');
        const playBtn = card.querySelector('.play-overlay, .play-btn, [data-action="play"]');
        const index = card.dataset.index || card.dataset.movieIndex;

        return {
          found: true,
          title: titleEl.textContent.trim(),
          display: window.getComputedStyle(card).display,
          iframeSrc: iframe ? iframe.src : 'none',
          iframeDataSrc: iframe ? iframe.dataset.src : 'none',
          hasPlayOverlay: !!playBtn,
          cardIndex: index,
          cardRect: card.getBoundingClientRect(),
          cardClasses: card.className
        };
      }
    }
    return { found: false };
  });

  console.log('\nMercy card:', JSON.stringify(mercyCard, null, 2));

  if (mercyCard.found) {
    // Try to click play on the Mercy card
    console.log('\n=== Attempting to play Mercy trailer ===');

    const playResult = await page.evaluate(() => {
      const cards = document.querySelectorAll('.video-card, .movie-card');
      for (const card of cards) {
        const titleEl = card.querySelector('.movie-title, .title, h3, h4');
        if (titleEl && titleEl.textContent.toLowerCase().includes('mercy')) {
          card.scrollIntoView({ behavior: 'instant', block: 'center' });

          const iframe = card.querySelector('iframe');
          const playOverlay = card.querySelector('.play-overlay');

          if (playOverlay) {
            playOverlay.click();
            return { action: 'clicked play overlay' };
          }

          if (iframe) {
            const currentSrc = iframe.src;
            const dataSrc = iframe.dataset.src;
            if (!currentSrc && dataSrc) {
              iframe.src = dataSrc;
              return { action: 'set iframe src from data-src', src: dataSrc };
            }
            if (currentSrc) {
              return { action: 'iframe already has src', src: currentSrc };
            }
          }

          const idx = card.dataset.index || card.dataset.movieIndex;
          if (idx && typeof startPlayback === 'function') {
            startPlayback(parseInt(idx));
            return { action: 'called startPlayback', index: idx };
          }

          return { action: 'no playback method found', cardHTML: card.innerHTML.substring(0, 500) };
        }
      }
      return { action: 'mercy card not found after search' };
    });

    console.log('Play result:', JSON.stringify(playResult, null, 2));

    await page.waitForTimeout(3000);

    // Check iframe state after play attempt
    const afterPlay = await page.evaluate(() => {
      const cards = document.querySelectorAll('.video-card, .movie-card');
      for (const card of cards) {
        const titleEl = card.querySelector('.movie-title, .title, h3, h4');
        if (titleEl && titleEl.textContent.toLowerCase().includes('mercy')) {
          const iframe = card.querySelector('iframe');
          const ytPlayer = card.querySelector('[id^="player-"]');
          return {
            iframeSrc: iframe ? iframe.src : 'none',
            iframeLoaded: iframe ? (iframe.src && iframe.src.length > 10) : false,
            ytPlayerId: ytPlayer ? ytPlayer.id : 'none',
            cardInnerHTML: card.innerHTML.substring(0, 800)
          };
        }
      }
      return { error: 'mercy card gone' };
    });

    console.log('\nAfter play attempt:', JSON.stringify(afterPlay, null, 2));
  }

  console.log('\n=== YouTube-related events ===');
  for (const e of ytEvents) {
    console.log('  ', e);
  }

  console.log('\n=== Critical errors ===');
  for (const e of errors) {
    console.log('  ', e);
  }
  if (errors.length === 0) console.log('  None.');

  await browser.close();
  console.log('\nDone.');
})();
