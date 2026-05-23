const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { 
    waitUntil: 'domcontentloaded',
    timeout: 60000 
  });
  await page.waitForTimeout(2000);

  // Get the playMovieFromBrowse function source
  const fnSource = await page.evaluate(() => {
    return playMovieFromBrowse.toString();
  });

  console.log('=== playMovieFromBrowse function on server ===\n');
  console.log(fnSource.substring(0, 2000));
  console.log('\n...truncated...');
  
  // Check specifically for the iframe style
  const hasVwVh = fnSource.includes('100vw') || fnSource.includes('100vh');
  const hasExplicitWidth = fnSource.includes('width:100%') || fnSource.includes('width: 100%');
  
  console.log('\n=== Checks ===');
  console.log('Has 100vw/100vh:', hasVwVh);
  console.log('Has width:100%:', hasExplicitWidth);
  
  await browser.close();
})();
