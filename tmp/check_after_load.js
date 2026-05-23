const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/?_cb=' + Date.now(), { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  await page.waitForTimeout(2000);

  // Click and trigger Mercy
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
  
  // Wait for iframe to load
  console.log('Waiting for iframe to load...');
  await page.waitForTimeout(5000);

  // Check if iframe has content
  const result = await page.evaluate(() => {
    const iframe = document.getElementById('browse-player-frame');
    if (!iframe) return { error: 'No iframe' };
    
    // Try to access iframe content
    let hasContent = false;
    try {
      hasContent = !!iframe.contentWindow;
    } catch(e) {}
    
    return {
      src: iframe.src,
      rect: iframe.getBoundingClientRect(),
      offsetWidth: iframe.offsetWidth,
      offsetHeight: iframe.offsetHeight,
      hasContentWindow: hasContent,
      readyState: iframe.readyState
    };
  });
  
  console.log('Result:', JSON.stringify(result, null, 2));

  await browser.close();
})();
