const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/?_cb=' + Date.now(), { 
    waitUntil: 'networkidle', timeout: 60000 
  });
  await page.waitForTimeout(2000);

  // Click mute overlay
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

  // Get Mercy index
  const idx = await page.evaluate(() => {
    const m = browseFilteredMovies.find(x => x.title === 'Mercy');
    return m ? filteredMovies.findIndex(f => f.id === m.id) : -1;
  });
  console.log('Mercy index:', idx);

  // Call playMovieFromBrowse directly and capture return
  const result = await page.evaluate((i) => {
    try {
      playMovieFromBrowse(i);
      return { called: true };
    } catch(e) {
      return { called: false, error: e.message, stack: e.stack };
    }
  }, idx);
  console.log('Function result:', result);

  await page.waitForTimeout(2000);

  // Check
  const check = await page.evaluate(() => ({
    overlay: !!document.getElementById('browse-play-overlay'),
    iframe: !!document.getElementById('browse-player-frame'),
    bodyHTML: document.body.innerHTML.includes('browse-play-overlay')
  }));
  console.log('Check:', check);

  // Get function source to verify
  const fnSrc = await page.evaluate(() => playMovieFromBrowse.toString());
  console.log('\nFunction has createElement:', fnSrc.includes("createElement('div')"));
  console.log('Function has browse-play-overlay:', fnSrc.includes("browse-play-overlay"));
  console.log('Function has 100vw:', fnSrc.includes('100vw'));

  await browser.close();
})();
