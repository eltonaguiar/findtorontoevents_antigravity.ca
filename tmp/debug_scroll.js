const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/?_cb=' + Date.now(), { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  await page.waitForTimeout(2000);

  const before = await page.evaluate(() => ({
    scrollTop: document.getElementById('container').scrollTop,
    windowHeight: window.innerHeight
  }));
  console.log('Before:', before);

  // Click Mercy
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
  
  // Get Mercy index
  const mercyInfo = await page.evaluate(() => {
    const m = browseFilteredMovies.find(x => x.title === 'Mercy');
    const idx = m ? filteredMovies.findIndex(f => f.id === m.id) : -1;
    return { index: idx, expectedScroll: idx * window.innerHeight };
  });
  console.log('Mercy info:', mercyInfo);

  // Click and monitor scroll
  await page.evaluate(() => {
    document.querySelector('#browseGrid .movie-card [onclick*="playMovieFromBrowse"]').click();
  });

  // Check scroll immediately and after delay
  for (let i = 0; i < 5; i++) {
    await page.waitForTimeout(300);
    const scroll = await page.evaluate(() => ({
      scrollTop: document.getElementById('container').scrollTop,
      expected: 2158 * window.innerHeight
    }));
    console.log(`Time ${(i+1)*300}ms scroll:`, scroll);
  }

  await browser.close();
})();
