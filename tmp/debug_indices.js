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

  const debug = await page.evaluate(() => {
    const mercy = browseFilteredMovies.find(m => m.title === 'Mercy');
    const mercyInFiltered = filteredMovies.find(m => m.id === mercy.id);
    const mercyInFilteredIndex = filteredMovies.findIndex(m => m.id === mercy.id);
    
    return {
      browseFilteredMoviesLength: browseFilteredMovies.length,
      filteredMoviesLength: filteredMovies.length,
      mercyFoundInBrowse: !!mercy,
      mercyFoundInFiltered: !!mercyInFiltered,
      mercyIndexInFiltered: mercyInFilteredIndex,
      firstFewBrowseMovies: browseFilteredMovies.slice(0, 3).map(m => ({ title: m.title, id: m.id })),
      firstFewFilteredMovies: filteredMovies.slice(0, 3).map(m => ({ title: m.title, id: m.id }))
    };
  });
  
  console.log(JSON.stringify(debug, null, 2));

  await browser.close();
})();
