const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const errors = [];
  page.on('pageerror', (err) => {
    errors.push(err.message);
    console.log('PAGE ERROR:', err.message);
  });
  
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      console.log('CONSOLE ERROR:', msg.text());
    }
  });

  console.log('=== FINAL MERCY TEST ===\n');
  
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/?_nocache=' + Date.now(), { 
    waitUntil: 'domcontentloaded',
    timeout: 60000 
  });
  await page.waitForTimeout(3000);

  // Dismiss mute overlay
  await page.evaluate(() => {
    const overlay = document.getElementById('muteOverlay');
    if (overlay) overlay.click();
  });
  await page.waitForTimeout(500);

  // Open browse
  await page.evaluate(() => { toggleBrowse(); });
  await page.waitForTimeout(500);

  // Search Mercy
  await page.evaluate(() => {
    document.getElementById('browseSearchInput').value = 'Mercy';
    document.getElementById('browseSearchInput').dispatchEvent(new Event('input', { bubbles: true }));
    applyBrowseFilters();
  });
  await page.waitForTimeout(1000);

  // Click Mercy with error catching
  console.log('\nClicking Mercy...');
  const clickResult = await page.evaluate(() => {
    try {
      const cards = document.querySelectorAll('#browseGrid .movie-card');
      for (const card of cards) {
        const titleEl = card.querySelector('.movie-card-title');
        if (titleEl && titleEl.textContent === 'Mercy') {
          const clickable = card.querySelector('[onclick*="playMovieFromBrowse"]');
          if (clickable) {
            clickable.click();
            return { success: true, onclick: clickable.getAttribute('onclick') };
          }
        }
      }
      return { success: false, reason: 'Mercy card not found' };
    } catch (e) {
      return { success: false, error: e.message };
    }
  });
  console.log('Click result:', clickResult);

  // Wait for it
  await page.waitForTimeout(2000);

  // Check state
  const state = await page.evaluate(() => {
    const overlay = document.getElementById('browse-play-overlay');
    const iframe = document.getElementById('browse-player-frame');
    return {
      overlayExists: !!overlay,
      iframeExists: !!iframe,
      iframeSize: iframe ? { w: iframe.offsetWidth, h: iframe.offsetHeight } : null,
      iframeRect: iframe ? iframe.getBoundingClientRect() : null,
      scrollTop: document.getElementById('container').scrollTop
    };
  });
  console.log('\nState after 2s:', JSON.stringify(state, null, 2));

  // Wait more
  await page.waitForTimeout(3000);
  
  const state2 = await page.evaluate(() => {
    const overlay = document.getElementById('browse-play-overlay');
    const iframe = document.getElementById('browse-player-frame');
    return {
      overlayExists: !!overlay,
      iframeExists: !!iframe,
      iframeWidth: iframe ? iframe.getBoundingClientRect().width : 0,
      iframeHeight: iframe ? iframe.getBoundingClientRect().height : 0
    };
  });
  console.log('State after 5s:', JSON.stringify(state2, null, 2));

  console.log('\n=== ERRORS ===');
  console.log(errors.length > 0 ? errors : 'No page errors');

  await page.screenshot({ path: 'tmp/mercy_final_test.png' });
  console.log('\nScreenshot: tmp/mercy_final_test.png');

  await browser.close();
})();
