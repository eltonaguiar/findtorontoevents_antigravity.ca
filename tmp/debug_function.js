const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Override function to add logging
  await page.addInitScript(() => {
    window._playMovieFromBrowseLog = [];
    const orig = window.playMovieFromBrowse;
    window.playMovieFromBrowse = function(index) {
      window._playMovieFromBrowseLog.push({ index, time: Date.now() });
      console.log('[HOOK] playMovieFromBrowse called:', index);
      return orig.call(this, index);
    };
  });

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/?_cb=' + Date.now(), { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  await page.waitForTimeout(2000);

  await page.evaluate(() => {
    document.getElementById('muteOverlay').click();
    toggleBrowse();
  });
  await page.waitForTimeout(500);
  
  await page.evaluate(() => {
    document.getElementById('browseSearchInput').value = 'Mercy';
    document.getElementById('browseSearchInput').dispatchEvent(new Event('input'));
    applyBrowseFilters();
  });
  await page.waitForTimeout(1000);

  // Click Mercy
  await page.evaluate(() => {
    const cards = document.querySelectorAll('#browseGrid .movie-card');
    for (const card of cards) {
      if (card.querySelector('.movie-card-title')?.textContent?.trim() === 'Mercy') {
        card.querySelector('[onclick*="playMovieFromBrowse"]')?.click();
        break;
      }
    }
  });
  
  await page.waitForTimeout(2000);

  // Check logs
  const logs = await page.evaluate(() => window._playMovieFromBrowseLog);
  console.log('Function calls:', JSON.stringify(logs, null, 2));

  // Check iframe
  const iframe = await page.evaluate(() => {
    const card = document.querySelector('.video-card[data-index="2158"]');
    const ifr = card?.querySelector('iframe');
    return ifr ? ifr.src : 'no iframe';
  });
  console.log('Iframe src:', iframe);

  await browser.close();
})();
