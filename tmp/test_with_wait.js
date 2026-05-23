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
  
  // Click Mercy
  await page.evaluate(() => {
    document.querySelector('#browseGrid .movie-card [onclick*="playMovieFromBrowse"]').click();
  });
  
  // Wait and check multiple times
  for (let i = 0; i < 10; i++) {
    await page.waitForTimeout(500);
    const info = await page.evaluate(() => {
      const card = document.querySelector('.video-card[data-index="2158"]');
      const iframe = card ? card.querySelector('iframe') : null;
      return {
        cardExists: !!card,
        cardInViewport: card ? (card.getBoundingClientRect().top >= -100 && card.getBoundingClientRect().top < window.innerHeight + 100) : false,
        cardRect: card ? card.getBoundingClientRect() : null,
        iframeSrc: iframe ? iframe.src : 'none',
        hasAutoplay: iframe ? iframe.src.includes('autoplay=1') : false
      };
    });
    console.log(`Time ${(i+1)*500}ms:`, JSON.stringify(info, null, 2));
  }

  await browser.close();
})();
