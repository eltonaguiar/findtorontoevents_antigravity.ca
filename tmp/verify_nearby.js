const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const errors = [];
  page.on('pageerror', (err) => errors.push(err.message));

  console.log('Loading...');
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(4000);
  await page.evaluate(() => { var o = document.getElementById('muteOverlay'); if (o) o.click(); });
  await page.waitForTimeout(500);

  // Test with video index 5 (close to top, should render in headless)
  const testIdx = 5;
  console.log('Testing playMovieFromBrowse(' + testIdx + ') [nearby video]...');

  // Check state before
  const before = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    return { src: iframe.src.substring(0, 80), loading: iframe.getAttribute('loading') };
  }, testIdx);
  console.log('Before:', JSON.stringify(before));

  // Call the function (simulating browse play)
  await page.evaluate((i) => { playMovieFromBrowse(i); }, testIdx);
  await page.waitForTimeout(3000);

  const after = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    return {
      src: iframe.src.substring(0, 100),
      hasAutoplay: iframe.src.includes('autoplay=1'),
      loading: iframe.getAttribute('loading'),
      contentWindow: !!iframe.contentWindow,
      width: iframe.clientWidth,
      height: iframe.clientHeight
    };
  }, testIdx);
  console.log('After:', JSON.stringify(after, null, 2));
  console.log('Page errors:', errors);
  console.log(after.hasAutoplay && after.width > 0 ? 'SUCCESS: nearby video works' : 'FAIL');

  await browser.close();
})();
