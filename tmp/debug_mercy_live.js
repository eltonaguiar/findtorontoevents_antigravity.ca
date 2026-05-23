const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const logs = [];
  const errors = [];
  
  page.on('console', (msg) => {
    const text = msg.text();
    logs.push(`[${msg.type()}] ${text}`);
    console.log(`[${msg.type()}] ${text}`);
    if (msg.type() === 'error') errors.push(text);
  });
  
  page.on('pageerror', (err) => {
    errors.push(`PageError: ${err.message}`);
    console.log(`PageError: ${err.message}`);
  });

  console.log('=== Testing Mercy on LIVE site ===\n');
  
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { 
    waitUntil: 'networkidle', 
    timeout: 30000 
  });
  await page.waitForTimeout(3000);

  // Dismiss mute overlay
  await page.evaluate(() => {
    const overlay = document.getElementById('muteOverlay');
    if (overlay) overlay.click();
  });
  await page.waitForTimeout(500);

  // Open browse and search for Mercy
  await page.evaluate(() => { toggleBrowse(); });
  await page.waitForTimeout(500);

  await page.evaluate(() => {
    document.getElementById('browseSearchInput').value = 'Mercy';
    document.getElementById('browseSearchInput').dispatchEvent(new Event('input', { bubbles: true }));
    applyBrowseFilters();
  });
  await page.waitForTimeout(1000);

  // Get Mercy index
  const mercyInfo = await page.evaluate(() => {
    const browseMatch = browseFilteredMovies.find(m => m.title === 'Mercy');
    if (!browseMatch) return { error: 'Mercy not found' };
    const filteredIndex = filteredMovies.findIndex(m => m.id === browseMatch.id);
    return {
      title: browseMatch.title,
      id: browseMatch.id,
      trailer_id: browseMatch.trailer_id,
      filteredIndex,
      targetScroll: filteredIndex * window.innerHeight
    };
  });

  console.log('\nMercy info:', mercyInfo);

  // Click Mercy
  console.log('\n=== Clicking Mercy ===');
  await page.evaluate(() => {
    const cards = document.querySelectorAll('#browseGrid .movie-card');
    for (const card of cards) {
      const titleEl = card.querySelector('.movie-card-title');
      if (titleEl && titleEl.textContent === 'Mercy') {
        const clickable = card.querySelector('[onclick*="playMovieFromBrowse"]');
        if (clickable) {
          console.log('Clicking element with onclick:', clickable.getAttribute('onclick'));
          clickable.click();
          return { clicked: true };
        }
      }
    }
    return { clicked: false };
  });

  // Wait and check overlay state
  await page.waitForTimeout(1000);

  console.log('\n=== Checking overlay state (1s after click) ===');
  const state1 = await page.evaluate(() => {
    const overlay = document.getElementById('browse-play-overlay');
    const iframe = document.getElementById('browse-player-frame');
    
    if (!overlay || !iframe) {
      return { error: 'Overlay or iframe not found' };
    }

    // Check if iframe is actually loaded
    const rect = iframe.getBoundingClientRect();
    
    return {
      overlayExists: true,
      iframeExists: true,
      iframeSrc: iframe.src,
      iframeLoading: iframe.getAttribute('loading'),
      iframeWidth: rect.width,
      iframeHeight: rect.height,
      iframeTop: rect.top,
      iframeLeft: rect.left,
      iframeComputedDisplay: window.getComputedStyle(iframe).display,
      iframeComputedVisibility: window.getComputedStyle(iframe).visibility,
      iframeComputedOpacity: window.getComputedStyle(iframe).opacity,
      overlayComputedZIndex: window.getComputedStyle(overlay).zIndex,
      contentWindowExists: !!iframe.contentWindow,
      scrollTop: document.getElementById('container').scrollTop
    };
  });
  console.log('State:', JSON.stringify(state1, null, 2));

  // Wait more
  await page.waitForTimeout(3000);

  console.log('\n=== Checking overlay state (4s after click) ===');
  const state2 = await page.evaluate(() => {
    const overlay = document.getElementById('browse-play-overlay');
    const iframe = document.getElementById('browse-player-frame');
    
    if (!overlay || !iframe) {
      return { error: 'Overlay or iframe not found after 4s' };
    }

    // Check iframe content
    let iframeDoc = null;
    let iframeBody = null;
    try {
      iframeDoc = iframe.contentDocument;
      iframeBody = iframeDoc ? iframeDoc.body : null;
    } catch(e) {}

    return {
      overlayExists: true,
      iframeExists: true,
      iframeSrc: iframe.src,
      iframeReadyState: iframe.readyState,
      contentWindowExists: !!iframe.contentWindow,
      canAccessContentDocument: !!iframeDoc,
      iframeBodyExists: !!iframeBody,
      iframeBodyInnerHTML: iframeBody ? iframeBody.innerHTML.substring(0, 200) : 'N/A'
    };
  });
  console.log('State:', JSON.stringify(state2, null, 2));

  // Take screenshot
  await page.screenshot({ path: 'tmp/mercy_debug_screenshot.png', fullPage: true });
  console.log('\nScreenshot saved: tmp/mercy_debug_screenshot.png');

  console.log('\n=== Errors ===');
  console.log(errors.length > 0 ? errors : 'No errors');

  await browser.close();
})();
