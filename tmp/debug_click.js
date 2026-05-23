const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Monitor playMovieFromBrowse calls
  await page.addInitScript(() => {
    window._playMovieFromBrowseCalls = [];
    const original = window.playMovieFromBrowse;
    window.playMovieFromBrowse = function(index) {
      window._playMovieFromBrowseCalls.push({
        index: index,
        time: Date.now(),
        scrollBefore: document.getElementById('container').scrollTop
      });
      console.log('[HOOK] playMovieFromBrowse called with index:', index);
      return original.apply(this, arguments);
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

  // Get Mercy info
  const mercyInfo = await page.evaluate(() => {
    const m = browseFilteredMovies.find(x => x.title === 'Mercy');
    return {
      browseIndex: browseFilteredMovies.indexOf(m),
      filteredIndex: filteredMovies.findIndex(f => f.id === m.id)
    };
  });
  console.log('Mercy indices:', mercyInfo);

  // Click Mercy
  await page.evaluate(() => {
    document.querySelector('#browseGrid .movie-card [onclick*="playMovieFromBrowse"]').click();
  });
  
  await page.waitForTimeout(1000);

  // Check what was called
  const calls = await page.evaluate(() => window._playMovieFromBrowseCalls);
  console.log('playMovieFromBrowse calls:', JSON.stringify(calls, null, 2));

  await browser.close();
})();
