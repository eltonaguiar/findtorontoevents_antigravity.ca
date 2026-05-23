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

  // Click specifically the Mercy card
  await page.evaluate(() => {
    const cards = document.querySelectorAll('#browseGrid .movie-card');
    for (const card of cards) {
      const title = card.querySelector('.movie-card-title')?.textContent?.trim();
      if (title === 'Mercy') {
        const clickable = card.querySelector('[onclick*="playMovieFromBrowse"]');
        if (clickable) {
          console.log('Clicking Mercy with onclick:', clickable.getAttribute('onclick'));
          clickable.click();
          break;
        }
      }
    }
  });
  
  // Wait
  await page.waitForTimeout(3000);

  // Check result
  const result = await page.evaluate(() => {
    const card = document.querySelector('.video-card[data-index="2158"]');
    const iframe = card?.querySelector('iframe');
    return {
      scrollTop: document.getElementById('container').scrollTop,
      expectedScroll: 2158 * window.innerHeight,
      cardInViewport: card ? (card.getBoundingClientRect().top >= 0 && card.getBoundingClientRect().top < window.innerHeight) : false,
      iframeSrc: iframe ? iframe.src : 'none',
      hasAutoplay: iframe ? iframe.src.includes('autoplay=1') : false
    };
  });
  
  console.log('Result:', JSON.stringify(result, null, 2));

  await browser.close();
})();
