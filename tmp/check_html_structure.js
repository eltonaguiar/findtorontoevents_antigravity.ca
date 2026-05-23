const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/?_cb=' + Date.now(), { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  await page.waitForTimeout(2000);

  // Trigger Mercy playback
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
  
  await page.evaluate(() => {
    document.querySelector('#browseGrid .movie-card [onclick*="playMovieFromBrowse"]').click();
  });
  
  // Wait
  await page.waitForTimeout(3000);

  // Check HTML structure
  const html = await page.evaluate(() => {
    const ov = document.getElementById('browse-play-overlay');
    if (!ov) return 'Overlay not found';
    
    return {
      outerHTML: ov.outerHTML.substring(0, 500),
      childCount: ov.childNodes.length,
      firstChild: ov.firstChild ? ov.firstChild.tagName : 'none'
    };
  });
  
  console.log('HTML structure:', JSON.stringify(html, null, 2));

  await browser.close();
})();
