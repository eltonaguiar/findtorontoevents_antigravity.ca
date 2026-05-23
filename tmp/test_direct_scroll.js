const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/?_cb=' + Date.now(), { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  await page.waitForTimeout(2000);

  await page.evaluate(() => {
    document.getElementById('muteOverlay').click();
  });
  await page.waitForTimeout(500);

  // Call playMovieFromBrowse directly with index 2158
  const result = await page.evaluate((idx) => {
    console.log('Calling playMovieFromBrowse with index:', idx);
    console.log('Expected scroll:', idx * window.innerHeight);
    
    playMovieFromBrowse(idx);
    
    return {
      called: true,
      scrollImmediatelyAfter: document.getElementById('container').scrollTop
    };
  }, 2158);
  
  console.log('Result:', result);

  // Check scroll after delays
  for (let i = 0; i < 5; i++) {
    await page.waitForTimeout(500);
    const scroll = await page.evaluate(() => ({
      scrollTop: document.getElementById('container').scrollTop,
      expected: 2158 * window.innerHeight
    }));
    console.log(`Time ${(i+1)*500}ms:`, scroll);
  }

  await browser.close();
})();
