const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await ctx.newPage();

  const logs = [];
  page.on('pageerror', (err) => logs.push('PAGE_ERROR: ' + err.message));

  console.log('Loading...');
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(5000);
  await page.evaluate(() => { var o = document.getElementById('muteOverlay'); if (o) o.click(); });
  await page.waitForTimeout(1000);

  const idx = await page.evaluate(() => {
    var m = filteredMovies.find(function(x) { return x.title === 'Mercy'; });
    return m ? filteredMovies.indexOf(m) : -1;
  });
  console.log('Mercy at index:', idx);

  // Browse -> search -> play
  await page.evaluate(() => { toggleBrowse(); });
  await page.waitForTimeout(300);
  await page.evaluate(() => {
    document.getElementById('browseSearchInput').value = 'Mercy';
    document.getElementById('browseSearchInput').dispatchEvent(new Event('input', { bubbles: true }));
    applyBrowseFilters();
  });
  await page.waitForTimeout(300);

  console.log('Playing...');
  await page.evaluate((i) => { playMovieFromBrowse(i); }, idx);

  // Wait for overlay + YouTube to load
  await page.waitForTimeout(8000);

  // Check overlay state
  const overlayState = await page.evaluate(() => {
    var overlay = document.getElementById('browse-play-overlay');
    if (!overlay) return { error: 'no overlay' };
    var iframe = document.getElementById('browse-player-frame');
    return {
      overlayExists: true,
      overlayW: overlay.clientWidth,
      overlayH: overlay.clientHeight,
      iframeExists: !!iframe,
      iframeSrc: iframe ? iframe.src.substring(0, 100) : 'N/A',
      iframeW: iframe ? iframe.clientWidth : 0,
      iframeH: iframe ? iframe.clientHeight : 0,
      iframeContentWindow: iframe ? !!iframe.contentWindow : false
    };
  });
  console.log('\nOverlay state:', JSON.stringify(overlayState, null, 2));

  console.log('Errors:', logs);

  await page.screenshot({ path: 'mercy_v6.png' });
  console.log('Screenshot: mercy_v6.png');

  await browser.close();
})();
