const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const playEvents = [];
  const postMsgErrors = [];
  page.on('console', (msg) => {
    const text = msg.text();
    if (text.includes('Playing video') || text.includes('Initialized YouTube player')) playEvents.push(text);
    if (text.includes('postMessage')) postMsgErrors.push(1);
  });

  console.log('Loading MOVIESHOWS3...');
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(4000);
  await page.evaluate(() => { var o = document.getElementById('muteOverlay'); if (o) o.click(); });
  await page.waitForTimeout(500);

  // Open browse, search Mercy
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
    console.log('ERROR: Mercy not found');
    await browser.close();
    return;
  }
  console.log('Mercy:', mercyInfo.title, 'index=' + mercyInfo.index, 'trailer=' + mercyInfo.trailer_id);

  // Clear counters
  playEvents.length = 0;
  postMsgErrors.length = 0;

  // Play from browse
  console.log('\nCalling playMovieFromBrowse(' + mercyInfo.index + ')...');
  await page.evaluate((i) => { playMovieFromBrowse(i); }, mercyInfo.index);

  // Wait for the full sequence (350ms + 200ms + iframe load)
  await page.waitForTimeout(2000);

  const state2s = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    if (!iframe) return { error: 'no iframe' };
    return {
      src: iframe.src,
      hasAutoplay: iframe.src.includes('autoplay=1'),
      hasLazy: iframe.hasAttribute('loading') && iframe.loading === 'lazy',
      loading: iframe.loading || 'none',
      contentWindow: !!iframe.contentWindow,
      width: iframe.clientWidth,
      height: iframe.clientHeight,
      offsetWidth: iframe.offsetWidth,
      offsetHeight: iframe.offsetHeight,
      visible: iframe.getBoundingClientRect().top >= -10 && iframe.getBoundingClientRect().top < window.innerHeight
    };
  }, mercyInfo.index);
  console.log('\n2s after play:', JSON.stringify(state2s, null, 2));

  // Wait more for YouTube to load the embed
  await page.waitForTimeout(5000);

  const state7s = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    if (!iframe) return { error: 'no iframe' };
    return {
      src: iframe.src,
      hasAutoplay: iframe.src.includes('autoplay=1'),
      contentWindow: !!iframe.contentWindow,
      width: iframe.clientWidth,
      height: iframe.clientHeight,
      offsetWidth: iframe.offsetWidth,
      offsetHeight: iframe.offsetHeight,
      tagName: iframe.tagName
    };
  }, mercyInfo.index);
  console.log('\n7s after play:', JSON.stringify(state7s, null, 2));

  console.log('\nPlay/init events:');
  playEvents.forEach(e => console.log('  ' + e));
  console.log('postMessage errors:', postMsgErrors.length);

  // Take a screenshot to see what's on screen
  await page.screenshot({ path: 'mercy_v3_screenshot.png' });
  console.log('Screenshot: mercy_v3_screenshot.png');

  const allOk = state7s.contentWindow && state7s.hasAutoplay && state7s.width > 0;
  console.log('\n' + (allOk ? 'SUCCESS' : 'FAIL') + ': iframe ' +
    (state7s.contentWindow ? 'loaded' : 'NOT loaded') + ', ' +
    state7s.width + 'x' + state7s.height);

  await browser.close();
})();
