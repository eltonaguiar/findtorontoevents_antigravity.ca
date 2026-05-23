const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const errors = [];
  page.on('pageerror', (err) => errors.push(`PageError: ${err.message}`));
  page.on('console', (msg) => {
    const text = msg.text();
    if (msg.type() === 'error' && !text.includes('postMessage')) {
      errors.push(`ConsoleError: ${text}`);
    }
  });

  console.log('=== Navigating to MOVIESHOWS3 ===');
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', {
    waitUntil: 'networkidle',
    timeout: 30000
  });
  await page.waitForTimeout(3000);
  console.log('Page loaded.');

  // Dismiss mute overlay if present
  const muteOverlay = await page.$('#muteOverlay');
  if (muteOverlay) {
    await page.evaluate(() => {
      const overlay = document.getElementById('muteOverlay');
      if (overlay) overlay.style.display = 'none';
    });
    console.log('Dismissed mute overlay.');
  }

  // Extract Mercy data directly from the page's movie array
  console.log('\n=== Looking for Mercy in page data ===');
  const mercyData = await page.evaluate(() => {
    const sources = [
      typeof allMovies !== 'undefined' ? allMovies : null,
      typeof movies !== 'undefined' ? movies : null,
      typeof window.allMovies !== 'undefined' ? window.allMovies : null,
      typeof window.movies !== 'undefined' ? window.movies : null,
    ].filter(Boolean);

    if (sources.length === 0) return { error: 'No movie arrays found' };

    const movieList = sources[0];
    const matches = movieList.filter(m =>
      (m.title || '').toLowerCase().includes('mercy')
    );

    return {
      totalMovies: movieList.length,
      mercyMatches: matches.map(m => ({
        id: m.id,
        title: m.title,
        trailer_id: m.trailer_id,
        trailerUrl: m.trailerUrl,
        type: m.type,
        genre: m.genre,
        tmdb_id: m.tmdb_id,
        is_active: m.is_active
      }))
    };
  });

  console.log(JSON.stringify(mercyData, null, 2));

  // Check embeddability for each Mercy trailer
  if (mercyData.mercyMatches) {
    for (const m of mercyData.mercyMatches) {
      const ytId = m.trailer_id || (m.trailerUrl && m.trailerUrl.match(/[?&]v=([^&]+)/)?.[1]);
      if (ytId) {
        console.log(`\n=== Checking embeddability: "${m.title}" trailer: ${ytId} ===`);
        const check = await page.evaluate(async (videoId) => {
          try {
            const resp = await fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`);
            let data = null;
            if (resp.ok) {
              try { data = await resp.json(); } catch(e) {}
            }
            return { status: resp.status, ok: resp.ok, title: data ? data.title : null };
          } catch (e) {
            return { error: e.message };
          }
        }, ytId);
        console.log(`  oEmbed result:`, JSON.stringify(check));

        if (!check.ok) {
          console.log(`  >>> BROKEN! Status ${check.status} - this trailer cannot be embedded`);
        } else {
          console.log(`  >>> OK - embeddable`);
        }
      } else {
        console.log(`\n"${m.title}" has NO trailer ID!`);
      }
    }
  }

  // Also check the API directly
  console.log('\n=== Checking API for Mercy ===');
  const apiCheck = await page.evaluate(async () => {
    const urls = [
      '/MOVIESHOWS3/api/movies.php?action=search&q=Mercy',
      '/MOVIESHOWS3/api/get-movies.php?search=Mercy',
      '/MOVIESHOWS2/api/movies.php?action=search&q=Mercy',
    ];
    const results = {};
    for (const url of urls) {
      try {
        const resp = await fetch(url);
        const text = await resp.text();
        let parsed;
        try { parsed = JSON.parse(text); } catch(e) { parsed = text.substring(0, 300); }
        results[url] = { status: resp.status, data: parsed };
      } catch (e) {
        results[url] = { error: e.message };
      }
    }
    return results;
  });

  for (const [url, result] of Object.entries(apiCheck)) {
    console.log(`\n${url}:`);
    if (result.data && Array.isArray(result.data)) {
      const mercyItems = result.data.filter(r =>
        (r.title || '').toLowerCase().includes('mercy')
      );
      console.log(`  Status: ${result.status}, Total results: ${result.data.length}, Mercy matches: ${mercyItems.length}`);
      for (const item of mercyItems) {
        console.log(`  -> "${item.title}" trailer_id=${item.trailer_id} type=${item.type}`);
      }
    } else {
      console.log(`  Status: ${result.status}, Data:`, JSON.stringify(result.data).substring(0, 300));
    }
  }

  console.log('\n=== Critical errors ===');
  for (const e of errors) {
    console.log('  ', e);
  }
  if (errors.length === 0) console.log('  None.');

  await browser.close();
  console.log('\nDone.');
})();
