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
  
  // Wait longer for iframe to load
  await page.waitForTimeout(3000);

  // Check dimensions
  const dims = await page.evaluate(() => {
    const iframe = document.getElementById('browse-player-frame');
    const overlay = document.getElementById('browse-play-overlay');
    if (!iframe || !overlay) return { error: 'Not found' };
    
    return {
      overlay: {
        offsetWidth: overlay.offsetWidth,
        offsetHeight: overlay.offsetHeight,
        clientWidth: overlay.clientWidth,
        clientHeight: overlay.clientHeight
      },
      iframe: {
        offsetWidth: iframe.offsetWidth,
        offsetHeight: iframe.offsetHeight,
        clientWidth: iframe.clientWidth,
        clientHeight: iframe.clientHeight,
        widthAttr: iframe.getAttribute('width'),
        heightAttr: iframe.getAttribute('height')
      },
      rect: iframe.getBoundingClientRect()
    };
  });
  
  console.log('Dimensions:', JSON.stringify(dims, null, 2));

  await browser.close();
})();
