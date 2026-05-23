const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    bypassCSP: true,
    ignoreHTTPSErrors: true
  });
  const page = await context.newPage();

  // Block cache
  await page.route('**/*', route => {
    route.continue({
      headers: {
        ...route.request().headers(),
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    });
  });

  // Load with cache-busting query param
  const url = 'https://findtorontoevents.ca/MOVIESHOWS3/?_cb=' + Date.now();
  console.log('Loading:', url);
  
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(2000);

  // Get function source
  const fnSource = await page.evaluate(() => playMovieFromBrowse.toString());
  
  console.log('\n=== Checking for fix ===');
  console.log('Has 100vw/100vh:', fnSource.includes('100vw') && fnSource.includes('100vh'));
  console.log('Has inset:0:', fnSource.includes('inset:0'));
  
  // Show first 1000 chars
  console.log('\nFunction start:');
  console.log(fnSource.substring(0, 1000));

  await browser.close();
})();
