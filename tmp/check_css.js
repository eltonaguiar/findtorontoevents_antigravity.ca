const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/?_cb=' + Date.now(), { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  await page.waitForTimeout(2000);

  // Click and trigger
  await page.evaluate(() => {
    const m = document.getElementById('muteOverlay');
    if (m) m.click();
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
    const cards = document.querySelectorAll('#browseGrid .movie-card');
    for (const card of cards) {
      const title = card.querySelector('.movie-card-title');
      if (title && title.textContent === 'Mercy') {
        const clickable = card.querySelector('[onclick*="playMovieFromBrowse"]');
        if (clickable) clickable.click();
      }
    }
  });
  await page.waitForTimeout(1500);

  // Check computed styles
  const styles = await page.evaluate(() => {
    const overlay = document.getElementById('browse-play-overlay');
    const iframe = document.getElementById('browse-player-frame');
    if (!overlay || !iframe) return { error: 'Not found' };
    
    const ovStyle = window.getComputedStyle(overlay);
    const ifStyle = window.getComputedStyle(iframe);
    
    return {
      overlay: {
        position: ovStyle.position,
        top: ovStyle.top,
        left: ovStyle.left,
        width: ovStyle.width,
        height: ovStyle.height,
        zIndex: ovStyle.zIndex
      },
      iframe: {
        position: ifStyle.position,
        top: ifStyle.top,
        left: ifStyle.left,
        width: ifStyle.width,
        height: ifStyle.height
      }
    };
  });
  
  console.log('Computed styles:', JSON.stringify(styles, null, 2));

  await browser.close();
})();
