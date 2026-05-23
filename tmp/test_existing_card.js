const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/?_cb=' + Date.now(), { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  await page.waitForTimeout(2000);

  // Trigger Mercy
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
  
  // Wait for scroll and play
  await page.waitForTimeout(2000);

  // Check the video card at index 2158
  const info = await page.evaluate(() => {
    const card = document.querySelector('.video-card[data-index="2158"]');
    if (!card) return { error: 'Card not found' };
    
    const iframe = card.querySelector('iframe');
    return {
      cardExists: true,
      cardInViewport: card.getBoundingClientRect().top >= 0 && card.getBoundingClientRect().top < window.innerHeight,
      iframeExists: !!iframe,
      iframeSrc: iframe ? iframe.src : 'none',
      iframeRect: iframe ? iframe.getBoundingClientRect() : null,
      hasAutoplay: iframe ? iframe.src.includes('autoplay=1') : false
    };
  });
  
  console.log('Card 2158 after click:', JSON.stringify(info, null, 2));

  await browser.close();
})();
