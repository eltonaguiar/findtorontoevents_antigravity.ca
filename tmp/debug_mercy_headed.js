const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await ctx.newPage();

  const allLogs = [];
  page.on('console', (msg) => {
    const text = msg.text();
    if (text.startsWith('[browse]') || text.includes('Playing video') || text.includes('Initialized YouTube')) {
      allLogs.push(text);
    }
  });
  page.on('pageerror', (err) => allLogs.push('PAGE_ERROR: ' + err.message));

  console.log('Loading...');
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(5000);
  await page.evaluate(() => { var o = document.getElementById('muteOverlay'); if (o) o.click(); });
  await page.waitForTimeout(1000);

  const idx = await page.evaluate(() => {
    var match = filteredMovies.find(function(m) { return m.title === 'Mercy'; });
    return match ? filteredMovies.indexOf(match) : -1;
  });
  console.log('Mercy at index:', idx);

  // Open browse, search, play
  await page.evaluate(() => { toggleBrowse(); });
  await page.waitForTimeout(300);
  await page.evaluate(() => {
    document.getElementById('browseSearchInput').value = 'Mercy';
    document.getElementById('browseSearchInput').dispatchEvent(new Event('input', { bubbles: true }));
    applyBrowseFilters();
  });
  await page.waitForTimeout(300);

  allLogs.length = 0;
  console.log('\nCalling playMovieFromBrowse(' + idx + ')...');
  await page.evaluate((i) => { playMovieFromBrowse(i); }, idx);

  // Wait for full sequence + YouTube load
  await page.waitForTimeout(8000);

  console.log('\nAll logs:');
  allLogs.forEach(l => console.log('  ' + l));

  // Check iframe state
  const state = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    if (!iframe) return { error: 'no iframe' };
    var rect = iframe.getBoundingClientRect();
    return {
      src: iframe.src.substring(0, 100),
      hasAutoplay: iframe.src.includes('autoplay=1'),
      loading: iframe.getAttribute('loading'),
      style: iframe.getAttribute('style'),
      contentWindow: !!iframe.contentWindow,
      clientW: iframe.clientWidth,
      clientH: iframe.clientHeight,
      offsetW: iframe.offsetWidth,
      offsetH: iframe.offsetHeight,
      rectW: rect.width,
      rectH: rect.height,
      rectTop: rect.top,
      parentClass: iframe.parentNode ? iframe.parentNode.className : 'none',
      parentW: iframe.parentNode ? iframe.parentNode.clientWidth : 0,
      parentH: iframe.parentNode ? iframe.parentNode.clientHeight : 0
    };
  }, idx);
  console.log('\nIframe state:', JSON.stringify(state, null, 2));

  await page.screenshot({ path: 'mercy_headed.png' });
  console.log('Screenshot: mercy_headed.png');

  await browser.close();
})();
