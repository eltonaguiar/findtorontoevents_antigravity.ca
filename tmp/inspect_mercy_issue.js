const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const logs = [];
  const errors = [];
  
  page.on('console', (msg) => {
    const text = msg.text();
    logs.push(`[${msg.type()}] ${text}`);
    if (msg.type() === 'error') {
      errors.push(text);
    }
  });
  
  page.on('pageerror', (err) => {
    errors.push(`PageError: ${err.message}`);
  });

  console.log('=== Step 1: Navigate to MOVIESHOWS3 ===');
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

  console.log('\n=== Step 2: Open Browse and Search for Mercy ===');
  await page.evaluate(() => { toggleBrowse(); });
  await page.waitForTimeout(500);

  // Search for Mercy
  await page.evaluate(() => {
    const input = document.getElementById('browseSearchInput');
    input.value = 'Mercy';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    applyBrowseFilters();
  });
  await page.waitForTimeout(1000);

  // Check Mercy data and index
  const mercyData = await page.evaluate(() => {
    // Find in browse filtered results
    const browseMatch = browseFilteredMovies.find(m => 
      m.title.toLowerCase().includes('mercy')
    );
    
    if (!browseMatch) {
      return { error: 'Mercy not found in browseFilteredMovies' };
    }

    // Find index in filteredMovies
    const filteredIndex = filteredMovies.findIndex(m => m.id === browseMatch.id);
    
    // Find index in allMovies
    const allMoviesIndex = allMovies.findIndex(m => m.id === browseMatch.id);

    return {
      title: browseMatch.title,
      id: browseMatch.id,
      trailer_id: browseMatch.trailer_id,
      type: browseMatch.type,
      filteredIndex: filteredIndex,
      allMoviesIndex: allMoviesIndex,
      totalFilteredMovies: filteredMovies.length,
      totalBrowseFiltered: browseFilteredMovies.length,
      browseMatches: browseFilteredMovies.filter(m => 
        m.title.toLowerCase().includes('mercy')
      ).map(m => ({ title: m.title, id: m.id, trailer_id: m.trailer_id }))
    };
  });

  console.log('Mercy Data:', JSON.stringify(mercyData, null, 2));

  if (mercyData.error) {
    console.log('ERROR:', mercyData.error);
    await browser.close();
    return;
  }

  console.log('\n=== Step 3: Check Card Click Handler ===');
  
  // Inspect the Mercy card in browse grid
  const cardInspection = await page.evaluate(() => {
    const cards = document.querySelectorAll('#browseGrid .movie-card');
    for (const card of cards) {
      const titleEl = card.querySelector('.movie-card-title');
      if (titleEl && titleEl.textContent.toLowerCase().includes('mercy')) {
        const clickableDiv = card.querySelector('[onclick*="playMovieFromBrowse"]');
        const hasClickHandler = !!clickableDiv;
        const onclickAttr = clickableDiv ? clickableDiv.getAttribute('onclick') : 'NONE';
        
        return {
          cardFound: true,
          title: titleEl.textContent,
          hasClickHandler,
          onclickAttr,
          cardHTML: card.outerHTML.substring(0, 500)
        };
      }
    }
    return { cardFound: false, cardsCount: cards.length };
  });

  console.log('Card Inspection:', JSON.stringify(cardInspection, null, 2));

  console.log('\n=== Step 4: Attempt to Play Mercy ===');
  
  // Click on the Mercy card
  const playResult = await page.evaluate(() => {
    const cards = document.querySelectorAll('#browseGrid .movie-card');
    for (const card of cards) {
      const titleEl = card.querySelector('.movie-card-title');
      if (titleEl && titleEl.textContent.toLowerCase().includes('mercy')) {
        const clickableDiv = card.querySelector('[onclick*="playMovieFromBrowse"]');
        if (clickableDiv) {
          clickableDiv.click();
          return { clicked: true, onclick: clickableDiv.getAttribute('onclick') };
        }
        // Try clicking the card itself
        card.click();
        return { clicked: 'card', cardHTML: card.outerHTML.substring(0, 200) };
      }
    }
    return { clicked: false };
  });

  console.log('Play Result:', JSON.stringify(playResult, null, 2));

  // Wait for playback to attempt
  await page.waitForTimeout(2000);

  console.log('\n=== Step 5: Check Playback State ===');
  
  const playbackState = await page.evaluate(() => {
    // Check for browse play overlay
    const overlay = document.getElementById('browse-play-overlay');
    const iframe = document.getElementById('browse-player-frame');
    
    // Check if browse view is still active
    const browseView = document.getElementById('browseView');
    const isBrowseActive = browseView ? browseView.classList.contains('active') : 'not found';
    
    // Check scroll position
    const container = document.getElementById('container');
    const scrollTop = container ? container.scrollTop : 'N/A';
    
    // Check for any iframes with autoplay
    const autoplayIframes = document.querySelectorAll('iframe[src*="autoplay=1"]');
    
    return {
      overlayExists: !!overlay,
      overlayIframeExists: !!iframe,
      iframeSrc: iframe ? iframe.src : 'N/A',
      isBrowseActive,
      scrollTop,
      autoplayIframeCount: autoplayIframes.length,
      autoplayIframeSrcs: Array.from(autoplayIframes).map(f => f.src.substring(0, 100))
    };
  });

  console.log('Playback State:', JSON.stringify(playbackState, null, 2));

  console.log('\n=== Step 6: Check for Errors ===');
  console.log('Console Errors:', errors.length > 0 ? errors : 'None');
  
  // Filter logs for relevant entries
  const relevantLogs = logs.filter(l => 
    l.toLowerCase().includes('mercy') || 
    l.toLowerCase().includes('play') || 
    l.toLowerCase().includes('trailer') ||
    l.toLowerCase().includes('error')
  );
  console.log('Relevant Logs:', relevantLogs.length > 0 ? relevantLogs : 'None');

  await browser.close();
  console.log('\n=== Inspection Complete ===');
})();
