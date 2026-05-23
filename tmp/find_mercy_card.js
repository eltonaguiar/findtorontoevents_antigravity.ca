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

  // Get ALL cards
  const cards = await page.evaluate(() => {
    const allCards = document.querySelectorAll('#browseGrid .movie-card');
    return Array.from(allCards).map(card => {
      const title = card.querySelector('.movie-card-title')?.textContent?.trim();
      const clickable = card.querySelector('[onclick*="playMovieFromBrowse"]');
      return {
        title: title,
        onclick: clickable ? clickable.getAttribute('onclick') : 'none'
      };
    });
  });
  
  console.log('All cards:', JSON.stringify(cards, null, 2));

  await browser.close();
})();
