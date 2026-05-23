const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/?_cb=' + Date.now(), { 
    waitUntil: 'networkidle', timeout: 60000 
  });
  await page.waitForTimeout(2000);

  // Setup monitoring
  await page.evaluate(() => {
    window._overlayLogs = [];
    const originalGet = document.getElementById;
    document.getElementById = function(id) {
      if (id === 'browse-play-overlay') {
        window._overlayLogs.push('getElementById(' + id + ') at ' + Date.now());
      }
      return originalGet.call(document, id);
    };
  });

  // Click mute
  await page.evaluate(() => {
    const m = document.getElementById('muteOverlay');
    if (m) m.click();
  });
  await page.waitForTimeout(500);

  // Toggle browse
  await page.evaluate(() => toggleBrowse());
  await page.waitForTimeout(500);

  // Search
  await page.evaluate(() => {
    document.getElementById('browseSearchInput').value = 'Mercy';
    document.getElementById('browseSearchInput').dispatchEvent(new Event('input'));
    applyBrowseFilters();
  });
  await page.waitForTimeout(1000);

  // Click Mercy
  console.log('Clicking Mercy...');
  await page.evaluate(() => {
    const cards = document.querySelectorAll('#browseGrid .movie-card');
    for (const card of cards) {
      const title = card.querySelector('.movie-card-title');
      if (title && title.textContent === 'Mercy') {
        const clickable = card.querySelector('[onclick*="playMovieFromBrowse"]');
        if (clickable) clickable.click();
      }
    }
  });

  // Check immediately and after delay
  for (let i = 0; i < 10; i++) {
    await page.waitForTimeout(500);
    const state = await page.evaluate(() => {
      const ov = document.getElementById('browse-play-overlay');
      return {
        exists: !!ov,
        logs: window._overlayLogs || []
      };
    });
    console.log(`Time ${(i+1)*500}ms: overlay exists =`, state.exists);
    if (state.logs.length > 0) {
      console.log('  Logs:', state.logs);
    }
  }

  await browser.close();
})();
