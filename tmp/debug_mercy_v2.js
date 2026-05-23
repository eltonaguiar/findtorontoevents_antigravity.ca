const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const events = [];
  page.on('console', (msg) => {
    const text = msg.text();
    if (text.includes('Playing video') || text.includes('Mercy') || text.includes('playMovieFromBrowse')) {
      events.push(text);
    }
  });

  console.log('Loading MOVIESHOWS3...');
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(3000);
  await page.evaluate(() => { var o = document.getElementById('muteOverlay'); if (o) o.click(); });
  await page.waitForTimeout(500);

  // Open browse and search for EXACTLY "Mercy" the movie
  await page.evaluate(() => { toggleBrowse(); });
  await page.waitForTimeout(500);
  await page.evaluate(() => {
    document.getElementById('browseSearchInput').value = 'Mercy';
    document.getElementById('browseSearchInput').dispatchEvent(new Event('input', { bubbles: true }));
    applyBrowseFilters();
  });
  await page.waitForTimeout(500);

  // Find the exact Mercy movie and its index
  const mercyInfo = await page.evaluate(() => {
    var match = browseFilteredMovies.find(function(m) { return m.title === 'Mercy'; });
    if (!match) return { error: 'No exact Mercy match' };
    var idx = filteredMovies.findIndex(function(m) { return m.id === match.id; });
    return {
      title: match.title,
      id: match.id,
      trailer_id: match.trailer_id,
      tmdb_id: match.tmdb_id,
      filteredIndex: idx,
      totalFiltered: filteredMovies.length
    };
  });
  console.log('Mercy info:', JSON.stringify(mercyInfo, null, 2));

  if (mercyInfo.error) {
    console.log('Could not find Mercy. Exiting.');
    await browser.close();
    return;
  }

  const idx = mercyInfo.filteredIndex;

  // Check iframe state BEFORE playing
  const beforePlay = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    var card = document.querySelector('.video-card[data-index="' + i + '"]');
    return {
      iframeExists: !!iframe,
      iframeSrc: iframe ? iframe.src : 'N/A',
      iframeLoading: iframe ? iframe.loading : 'N/A',
      iframeComplete: iframe ? iframe.complete : 'N/A',
      cardExists: !!card,
      cardTop: card ? card.getBoundingClientRect().top : 'N/A'
    };
  }, idx);
  console.log('\nBefore play:', JSON.stringify(beforePlay, null, 2));

  // Now play from browse
  console.log('\nCalling playMovieFromBrowse(' + idx + ')...');
  await page.evaluate((i) => { playMovieFromBrowse(i); }, idx);
  await page.waitForTimeout(1000);

  // Check iframe state 1s after
  const after1s = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    var card = document.querySelector('.video-card[data-index="' + i + '"]');
    return {
      iframeSrc: iframe ? iframe.src : 'N/A',
      iframeLoading: iframe ? iframe.loading : 'N/A',
      hasAutoplay: iframe ? iframe.src.includes('autoplay=1') : false,
      cardInViewport: card ? (card.getBoundingClientRect().top >= -10 && card.getBoundingClientRect().top < window.innerHeight) : false,
      cardTop: card ? card.getBoundingClientRect().top : 'N/A',
      scrollTop: document.getElementById('container') ? document.getElementById('container').scrollTop : document.documentElement.scrollTop,
      expectedScroll: i * window.innerHeight,
      windowHeight: window.innerHeight
    };
  }, idx);
  console.log('\n1s after play:', JSON.stringify(after1s, null, 2));

  // Wait more and check again
  await page.waitForTimeout(3000);
  const after4s = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    return {
      iframeSrc: iframe ? iframe.src : 'N/A',
      hasAutoplay: iframe ? iframe.src.includes('autoplay=1') : false,
      contentWindow: iframe ? !!iframe.contentWindow : false,
      naturalWidth: iframe ? iframe.clientWidth : 0,
      naturalHeight: iframe ? iframe.clientHeight : 0
    };
  }, idx);
  console.log('\n4s after play:', JSON.stringify(after4s, null, 2));

  // Check if YouTube embed actually responded
  const embedCheck = await page.evaluate(async (trailerId) => {
    try {
      var resp = await fetch('https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=' + trailerId + '&format=json');
      return { status: resp.status, ok: resp.ok };
    } catch(e) { return { error: e.message }; }
  }, mercyInfo.trailer_id);
  console.log('\noEmbed check:', JSON.stringify(embedCheck));

  console.log('\nEvents:', events);

  await browser.close();
  console.log('Done.');
})();
