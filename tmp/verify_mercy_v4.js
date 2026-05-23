const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await ctx.newPage();

  const logs = [];
  page.on('console', (msg) => {
    const text = msg.text();
    if (text.startsWith('[browse]') || text.includes('Playing video') || text.includes('Initialized YouTube')) {
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

  // Wait for sequence + YouTube
  await page.waitForTimeout(10000);

  console.log('\nLogs:');
  logs.forEach(l => console.log('  ' + l));

  const state = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    if (!iframe) return { error: 'no iframe' };
    return {
      src: iframe.src.substring(0, 100),
      autoplay: iframe.src.includes('autoplay=1'),
      loading: iframe.getAttribute('loading'),
      contentWindow: !!iframe.contentWindow,
      clientW: iframe.clientWidth,
      clientH: iframe.clientHeight,
      parentW: iframe.parentNode.clientWidth,
      parentH: iframe.parentNode.clientHeight,
      computedW: getComputedStyle(iframe).width,
      computedH: getComputedStyle(iframe).height,
      computedDisplay: getComputedStyle(iframe).display
    };
  }, idx);
  console.log('\nState:', JSON.stringify(state, null, 2));

  await page.screenshot({ path: 'mercy_v4.png' });
  console.log('Screenshot: mercy_v4.png');

  await browser.close();
})();
