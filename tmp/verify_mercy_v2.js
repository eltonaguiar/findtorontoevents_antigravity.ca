const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const playEvents = [];
  const errors = [];
  page.on('console', (msg) => {
    const text = msg.text();
    if (text.includes('Playing video')) playEvents.push(text);
    if (text.includes('postMessage')) errors.push('postMessage');
  });

  console.log('Loading MOVIESHOWS3...');
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(4000);
  await page.evaluate(() => { var o = document.getElementById('muteOverlay'); if (o) o.click(); });
  await page.waitForTimeout(500);

  // Open browse, search Mercy, play it
  await page.evaluate(() => { toggleBrowse(); });
  await page.waitForTimeout(500);
  await page.evaluate(() => {
    document.getElementById('browseSearchInput').value = 'Mercy';
    document.getElementById('browseSearchInput').dispatchEvent(new Event('input', { bubbles: true }));
    applyBrowseFilters();
  });
  await page.waitForTimeout(500);

  const mercyInfo = await page.evaluate(() => {
    var match = browseFilteredMovies.find(function(m) { return m.title === 'Mercy'; });
    if (!match) return null;
    var idx = filteredMovies.findIndex(function(m) { return m.id === match.id; });
    return { title: match.title, index: idx, trailer_id: match.trailer_id };
  });

  if (!mercyInfo) {
    console.log('ERROR: Mercy not found in browse results');
    await browser.close();
    return;
  }
  console.log('Found:', mercyInfo.title, 'at index', mercyInfo.index, '(trailer:', mercyInfo.trailer_id + ')');

  // Clear counters before browse play
  playEvents.length = 0;
  errors.length = 0;

  // Play from browse
  await page.evaluate((i) => { playMovieFromBrowse(i); }, mercyInfo.index);
  
  // Wait for the full sequence to complete (350ms browse close + 200ms scroll + extra)
  await page.waitForTimeout(2000);

  // Check iframe state
  const iframeState = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    if (!iframe) return { error: 'no iframe' };
    return {
      src: iframe.src,
      hasAutoplay: iframe.src.includes('autoplay=1'),
      loading: iframe.loading,
      hasLoadingAttr: iframe.hasAttribute('loading'),
      contentWindow: !!iframe.contentWindow,
      width: iframe.clientWidth,
      height: iframe.clientHeight,
      visible: iframe.getBoundingClientRect().top >= -10 && iframe.getBoundingClientRect().top < window.innerHeight
    };
  }, mercyInfo.index);

  console.log('\nIframe state:', JSON.stringify(iframeState, null, 2));
  console.log('\nPlay events after browse:', playEvents.length);
  playEvents.forEach(e => console.log(' ', e));
  console.log('postMessage errors:', errors.length);

  // Wait a bit more for load
  await page.waitForTimeout(3000);

  const finalState = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    if (!iframe) return { error: 'no iframe' };
    return {
      src: iframe.src,
      hasAutoplay: iframe.src.includes('autoplay=1'),
      contentWindow: !!iframe.contentWindow,
      width: iframe.clientWidth,
      height: iframe.clientHeight
    };
  }, mercyInfo.index);
  console.log('\nFinal state (5s total):', JSON.stringify(finalState, null, 2));

  const allOk = finalState.contentWindow && finalState.hasAutoplay && finalState.width > 0;
  console.log('\n' + (allOk ? 'SUCCESS: Mercy iframe loaded and playing' : 'FAIL: Mercy iframe still not loaded'));

  await browser.close();
})();
