const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await ctx.newPage();

  const logs = [];
  page.on('console', (msg) => {
    const text = msg.text();
    if (text.startsWith('[browse]') || text.includes('Playing video') || text.includes('Initialized YouTube') || text.includes('YT player')) {
      logs.push(text);
    }
  });
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

  await page.evaluate(() => { toggleBrowse(); });
  await page.waitForTimeout(300);
  await page.evaluate(() => {
    document.getElementById('browseSearchInput').value = 'Mercy';
    document.getElementById('browseSearchInput').dispatchEvent(new Event('input', { bubbles: true }));
    applyBrowseFilters();
  });
  await page.waitForTimeout(300);

  logs.length = 0;
  console.log('Calling playMovieFromBrowse(' + idx + ')...');
  await page.evaluate((i) => { playMovieFromBrowse(i); }, idx);

  // Wait for YT API to create and load player
  await page.waitForTimeout(10000);

  console.log('\nLogs:');
  logs.forEach(l => console.log('  ' + l));

  // Check what's at the player position now
  const state = await page.evaluate((i) => {
    var el = document.getElementById('player-' + i);
    if (!el) return { error: 'no element with id player-' + i };
    return {
      tagName: el.tagName,
      clientW: el.clientWidth,
      clientH: el.clientHeight,
      src: el.tagName === 'IFRAME' ? el.src.substring(0, 100) : 'N/A',
      parentW: el.parentNode.clientWidth,
      parentH: el.parentNode.clientHeight,
      innerHTML: el.innerHTML ? el.innerHTML.substring(0, 200) : 'empty'
    };
  }, idx);
  console.log('\nPlayer state:', JSON.stringify(state, null, 2));

  // Also check if YT.Player was created
  const ytState = await page.evaluate((i) => {
    if (!window.ytPlayers) return 'ytPlayers not defined';
    var p = window.ytPlayers[i];
    if (!p) return 'no player at index ' + i;
    return {
      exists: true,
      getPlayerState: typeof p.getPlayerState === 'function' ? p.getPlayerState() : 'N/A',
      getVideoUrl: typeof p.getVideoUrl === 'function' ? p.getVideoUrl() : 'N/A'
    };
  }, idx);
  console.log('\nYT Player:', JSON.stringify(ytState, null, 2));

  await page.screenshot({ path: 'mercy_v5.png' });
  console.log('Screenshot: mercy_v5.png');

  await browser.close();
})();
