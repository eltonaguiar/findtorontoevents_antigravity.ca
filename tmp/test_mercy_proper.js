const { chromium } = require('playwright');

(async () => {
  console.log('=== PROPER MERCY TEST ===\n');
  
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Capture all console logs
  const logs = [];
  page.on('console', (msg) => {
    const text = `[${msg.type()}] ${msg.text()}`;
    logs.push(text);
    console.log(text);
  });

  try {
    // 1. Load page
    console.log('\n1. Loading page...');
    await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { 
      waitUntil: 'domcontentloaded',
      timeout: 60000 
    });
    await page.waitForTimeout(3000);

    // 2. Dismiss mute overlay
    console.log('\n2. Dismissing mute overlay...');
    await page.evaluate(() => {
      const overlay = document.getElementById('muteOverlay');
      if (overlay) {
        overlay.click();
        console.log('[TEST] Mute overlay clicked');
      }
    });
    await page.waitForTimeout(1000);

    // 3. Wait for video to start playing
    console.log('\n3. Waiting for initial video to play...');
    await page.waitForTimeout(2000);

    // 4. Check current state
    const stateBefore = await page.evaluate(() => {
      const playingIframe = document.querySelector('.video-card iframe[src*="autoplay=1"]');
      return {
        hasPlayingVideo: !!playingIframe,
        playingVideoSrc: playingIframe ? playingIframe.src.substring(0, 80) : 'none',
        scrollTop: document.getElementById('container').scrollTop
      };
    });
    console.log('State before opening browse:', stateBefore);

    // 5. OPEN BROWSE (this is what user does)
    console.log('\n4. Opening browse/search...');
    await page.evaluate(() => {
      console.log('[TEST] Calling toggleBrowse()');
      toggleBrowse();
    });
    await page.waitForTimeout(1000);

    // 6. Check if browse is open
    const browseState = await page.evaluate(() => {
      const browseView = document.getElementById('browseView');
      const searchInput = document.getElementById('browseSearchInput');
      return {
        browseIsActive: browseView ? browseView.classList.contains('active') : false,
        searchInputExists: !!searchInput,
        videoStillPlaying: !!document.querySelector('.video-card iframe[src*="autoplay=1"]')
      };
    });
    console.log('Browse state:', browseState);

    // 7. SEARCH FOR MERCY
    console.log('\n5. Searching for Mercy...');
    await page.evaluate(() => {
      const input = document.getElementById('browseSearchInput');
      if (input) {
        input.value = 'Mercy';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        console.log('[TEST] Search input set to Mercy');
      }
    });
    
    // Trigger search
    await page.evaluate(() => {
      if (typeof applyBrowseFilters === 'function') {
        applyBrowseFilters();
        console.log('[TEST] applyBrowseFilters() called');
      }
    });
    await page.waitForTimeout(1500);

    // 8. Check search results
    const searchResults = await page.evaluate(() => {
      const cards = document.querySelectorAll('#browseGrid .movie-card');
      const mercyCards = [];
      cards.forEach(card => {
        const title = card.querySelector('.movie-card-title');
        if (title && title.textContent.toLowerCase().includes('mercy')) {
          const clickable = card.querySelector('[onclick*="playMovieFromBrowse"]');
          mercyCards.push({
            title: title.textContent,
            hasClickHandler: !!clickable,
            onclickAttr: clickable ? clickable.getAttribute('onclick') : null
          });
        }
      });
      return {
        totalCards: cards.length,
        mercyCards: mercyCards
      };
    });
    console.log('Search results:', searchResults);

    // 9. CLICK ON MERCY
    console.log('\n6. Clicking on Mercy card...');
    const clickResult = await page.evaluate(() => {
      const cards = document.querySelectorAll('#browseGrid .movie-card');
      for (const card of cards) {
        const title = card.querySelector('.movie-card-title');
        if (title && title.textContent === 'Mercy') {
          const clickable = card.querySelector('[onclick*="playMovieFromBrowse"]');
          if (clickable) {
            console.log('[TEST] Clicking Mercy with onclick:', clickable.getAttribute('onclick'));
            clickable.click();
            return { clicked: true, onclick: clickable.getAttribute('onclick') };
          }
        }
      }
      return { clicked: false };
    });
    console.log('Click result:', clickResult);

    // 10. Wait and check what happens
    console.log('\n7. Waiting for playback...');
    await page.waitForTimeout(3000);

    const playbackState = await page.evaluate(() => {
      const overlay = document.getElementById('browse-play-overlay');
      const iframe = document.getElementById('browse-player-frame');
      const browseView = document.getElementById('browseView');
      
      return {
        overlayExists: !!overlay,
        iframeExists: !!iframe,
        browseViewActive: browseView ? browseView.classList.contains('active') : false,
        iframeSrc: iframe ? iframe.src : 'N/A',
        iframeWidth: iframe ? iframe.getBoundingClientRect().width : 0,
        iframeHeight: iframe ? iframe.getBoundingClientRect().height : 0,
        scrollTop: document.getElementById('container').scrollTop,
        expectedScroll: 2158 * window.innerHeight
      };
    });
    console.log('\nPlayback state:', JSON.stringify(playbackState, null, 2));

    // 11. Screenshot
    await page.screenshot({ path: 'tmp/mercy_test_result.png' });
    console.log('\nScreenshot saved: tmp/mercy_test_result.png');

    // Summary
    console.log('\n=== TEST SUMMARY ===');
    if (playbackState.overlayExists && playbackState.iframeExists && playbackState.iframeWidth > 100) {
      console.log('✅ PASS: Overlay and iframe created with proper dimensions');
    } else {
      console.log('❌ FAIL: Overlay/iframe issue');
      console.log('   - Overlay exists:', playbackState.overlayExists);
      console.log('   - Iframe exists:', playbackState.iframeExists);
      console.log('   - Iframe size:', playbackState.iframeWidth + 'x' + playbackState.iframeHeight);
    }

  } catch (err) {
    console.error('Test error:', err.message);
  } finally {
    await browser.close();
  }
})();
