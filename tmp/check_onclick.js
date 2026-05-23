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
    toggleBrowse();
  });
  await page.waitForTimeout(500);
  
  await page.evaluate(() => {
    document.getElementById('browseSearchInput').value = 'Mercy';
    document.getElementById('browseSearchInput').dispatchEvent(new Event('input'));
    applyBrowseFilters();
  });
  await page.waitForTimeout(1000);

  // Get onclick attribute
  const onclickInfo = await page.evaluate(() => {
    const el = document.querySelector('#browseGrid .movie-card [onclick*="playMovieFromBrowse"]');
    return {
      onclick: el ? el.getAttribute('onclick') : 'not found',
      text: el ? el.textContent : 'not found'
    };
  });
  console.log('Onclick info:', onclickInfo);

  await browser.close();
})();
