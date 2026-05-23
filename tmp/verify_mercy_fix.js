const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const logs = [];
  const errors = [];
  
  page.on('console', (msg) => {
    const text = msg.text();
    logs.push(`[${msg.type()}] ${text}`);
    if (msg.type() === 'error') errors.push(text);
  });
  
  page.on('pageerror', (err) => errors.push(`PageError: ${err.message}`));

  console.log('=== Testing Mercy Trailer Playback Fix ===\n');
  
  // Load the LOCAL fixed version
  const filePath = require('path').resolve(__dirname, 'fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html');
  await page.goto('file://' + filePath, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);

  console.log('Step 1: Check if playMovieFromBrowse has the fix');
  
  const functionCheck = await page.evaluate(() => {
    const fnSrc = playMovieFromBrowse.toString();
    return {
      hasLoadingEager: fnSrc.includes('loading="eager"'),
      hasEagerAttribute: fnSrc.includes('setAttribute("loading", "eager")'),
      hasOffsetHeight: fnSrc.includes('offsetHeight'),
      hasEarlyValidation: fnSrc.includes('!movie || !movie.trailer_id'),
      functionLength: fnSrc.length
    };
  });
  
  console.log('Fix verification:', JSON.stringify(functionCheck, null, 2));

  if (!functionCheck.hasLoadingEager && !functionCheck.hasEagerAttribute) {
    console.log('❌ Fix NOT applied - loading="eager" not found');
    await browser.close();
    return;
  }

  console.log('\nStep 2: Load movies and test Mercy playback');
  
  // Load movies from API
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { waitUntil: 'networkidle', timeout: 30000 });
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

  // Get Mercy info
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

  console.log('Mercy info:', mercyInfo);

  if (mercyInfo.error) {
    console.log('❌', mercyInfo.error);
    await browser.close();
    return;
  }

  console.log('\nStep 3: Click Mercy and check overlay creation');
  
  // Click on Mercy card
  await page.evaluate(() => {
    const cards = document.querySelectorAll('#browseGrid .movie-card');
    for (const card of cards) {
      const titleEl = card.querySelector('.movie-card-title');
      if (titleEl && titleEl.textContent === 'Mercy') {
        const clickable = card.querySelector('[onclick*="playMovieFromBrowse"]');
        if (clickable) clickable.click();
        return { clicked: true };
      }
    }
    return { clicked: false };
  });

  // Wait for overlay to be created
  await page.waitForTimeout(500);

  // Check overlay state
  const overlayCheck = await page.evaluate(() => {
    const overlay = document.getElementById('browse-play-overlay');
    const iframe = document.getElementById('browse-player-frame');
    
    if (!overlay || !iframe) {
      return { error: 'Overlay or iframe not found', overlayExists: !!overlay, iframeExists: !!iframe };
    }

    // Check computed styles
    const overlayStyles = window.getComputedStyle(overlay);
    const iframeStyles = window.getComputedStyle(iframe);
    
    return {
      overlayExists: true,
      iframeExists: true,
      iframeSrc: iframe.src,
      iframeLoadingAttr: iframe.getAttribute('loading'),
      overlayOpacity: overlayStyles.opacity,
      overlayVisibility: overlayStyles.visibility,
      iframeOpacity: iframeStyles.opacity,
      iframeVisibility: iframeStyles.visibility,
      overlayZIndex: overlayStyles.zIndex,
      hasAutoplay: iframe.src.includes('autoplay=1'),
      hasTrailerId: iframe.src.includes('JUADqWkJiiE')
    };
  });

  console.log('Overlay check:', JSON.stringify(overlayCheck, null, 2));

  console.log('\nStep 4: Wait for iframe to load and verify playback');
  
  // Wait longer for iframe to fully initialize
  await page.waitForTimeout(3000);

  const finalCheck = await page.evaluate(() => {
    const iframe = document.getElementById('browse-player-frame');
    if (!iframe) return { error: 'Iframe disappeared' };

    // Check if iframe has content
    const rect = iframe.getBoundingClientRect();
    const hasSize = rect.width > 100 && rect.height > 100;
    
    // Check if scroll position is correct
    const container = document.getElementById('container');
    const expectedScroll = Math.floor(2158 * window.innerHeight);
    const actualScroll = Math.floor(container.scrollTop);
    const scrollCorrect = Math.abs(actualScroll - expectedScroll) < 10;

    return {
      iframeExists: true,
      iframeWidth: rect.width,
      iframeHeight: rect.height,
      hasSize,
      expectedScroll,
      actualScroll,
      scrollCorrect,
      iframeSrc: iframe.src.substring(0, 100)
    };
  });

  console.log('Final check:', JSON.stringify(finalCheck, null, 2));

  // Summary
  console.log('\n=== TEST SUMMARY ===');
  
  if (functionCheck.hasLoadingEager || functionCheck.hasEagerAttribute) {
    console.log('✅ Fix applied: loading="eager" attribute added');
  } else {
    console.log('❌ Fix NOT applied');
  }

  if (overlayCheck.overlayExists && overlayCheck.iframeExists) {
    console.log('✅ Overlay and iframe created successfully');
  } else {
    console.log('❌ Overlay/iframe creation failed');
  }

  if (overlayCheck.iframeLoadingAttr === 'eager') {
    console.log('✅ Iframe has loading="eager" attribute');
  } else {
    console.log('⚠️ Iframe missing loading="eager" attribute');
  }

  if (finalCheck.hasSize) {
    console.log('✅ Iframe has proper dimensions');
  } else {
    console.log('❌ Iframe has incorrect dimensions');
  }

  if (finalCheck.scrollCorrect) {
    console.log('✅ Scroll position is correct');
  } else {
    console.log('⚠️ Scroll position may be off');
  }

  if (errors.length > 0) {
    console.log('\n⚠️ Console errors:', errors);
  }

  await browser.close();
  console.log('\n=== Verification Complete ===');
})();
