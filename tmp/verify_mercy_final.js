const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const events = [];
  const errors = [];
  page.on('console', (msg) => {
    const text = msg.text();
    if (text.includes('Playing video') || text.includes('Initialized YouTube')) events.push(text);
    if (text.includes('postMessage')) errors.push('postMessage');
  });
  page.on('pageerror', (err) => {
    errors.push('PAGE_ERROR: ' + err.message);
  });

  console.log('Loading MOVIESHOWS3...');
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(4000);
  await page.evaluate(() => { var o = document.getElementById('muteOverlay'); if (o) o.click(); });
  await page.waitForTimeout(500);

  // Open browse, search Mercy, find exact match
  await page.evaluate(() => { toggleBrowse(); });
  await page.waitForTimeout(500);
  await page.evaluate(() => {
    document.getElementById('browseSearchInput').value = 'Mercy';
    document.getElementById('browseSearchInput').dispatchEvent(new Event('input', { bubbles: true }));
    applyBrowseFilters();
  });
  await page.waitForTimeout(500);

  const idx = await page.evaluate(() => {
    var match = browseFilteredMovies.find(function(m) { return m.title === 'Mercy'; });
    if (!match) return -1;
    return filteredMovies.findIndex(function(m) { return m.id === match.id; });
  });
  console.log('Mercy at index:', idx);
  if (idx < 0) { console.log('NOT FOUND'); await browser.close(); return; }

  // Clear counters
  events.length = 0;
  errors.length = 0;

  // Call the ACTUAL function on the live page
  console.log('Calling playMovieFromBrowse(' + idx + ')...');
  await page.evaluate((i) => { playMovieFromBrowse(i); }, idx);

  // Wait for the full sequence: 350ms browse close + 200ms scroll + iframe load
  await page.waitForTimeout(3000);

  const state = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    if (!iframe) return { error: 'no iframe found' };
    return {
      src: iframe.src.substring(0, 100),
      hasAutoplay: iframe.src.includes('autoplay=1'),
      loading: iframe.getAttribute('loading'),
      contentWindow: !!iframe.contentWindow,
      width: iframe.clientWidth,
      height: iframe.clientHeight,
      offsetW: iframe.offsetWidth,
      offsetH: iframe.offsetHeight
    };
  }, idx);
  console.log('\nIframe state (3s):', JSON.stringify(state, null, 2));

  // Wait more for YouTube to fully load
  await page.waitForTimeout(5000);

  const finalState = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    if (!iframe) return { error: 'no iframe found' };
    return {
      src: iframe.src.substring(0, 100),
      hasAutoplay: iframe.src.includes('autoplay=1'),
      contentWindow: !!iframe.contentWindow,
      width: iframe.clientWidth,
      height: iframe.clientHeight
    };
  }, idx);
  console.log('\nFinal state (8s):', JSON.stringify(finalState, null, 2));

  console.log('\nEvents:', events);
  console.log('Errors:', errors.length, errors.filter(e => e.startsWith('PAGE_ERROR')));

  const ok = finalState.hasAutoplay && finalState.width > 0;
  console.log('\n' + (ok ? 'SUCCESS: Mercy iframe has autoplay=1 and is rendered' : 'FAIL'));

  await browser.close();
})();
