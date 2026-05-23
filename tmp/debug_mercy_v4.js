const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const allLogs = [];
  const allErrors = [];
  page.on('console', (msg) => {
    allLogs.push('[' + msg.type() + '] ' + msg.text());
  });
  page.on('pageerror', (err) => {
    allErrors.push('PAGE_ERROR: ' + err.message);
  });

  console.log('Loading...');
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(4000);
  await page.evaluate(() => { var o = document.getElementById('muteOverlay'); if (o) o.click(); });
  await page.waitForTimeout(500);

  // Find Mercy index
  const idx = await page.evaluate(() => {
    var match = filteredMovies.find(function(m) { return m.title === 'Mercy'; });
    return match ? filteredMovies.indexOf(match) : -1;
  });
  console.log('Mercy index:', idx);

  // Clear logs before calling
  allLogs.length = 0;
  allErrors.length = 0;

  // Add inline debugging to trace playMovieFromBrowse
  const result = await page.evaluate((i) => {
    var log = [];
    try {
      log.push('1. calling playMovieFromBrowse(' + i + ')');
      log.push('2. _browseScrolling type: ' + typeof _browseScrolling);
      log.push('3. filteredMovies[' + i + ']: ' + (filteredMovies[i] ? filteredMovies[i].title : 'UNDEFINED'));
      log.push('4. isMuted: ' + typeof isMuted + ' = ' + isMuted);

      // Manually trace the function
      _browseScrolling = true;
      log.push('5. _browseScrolling set to true');

      var current = document.querySelector('.video-card iframe[src*="autoplay=1"]');
      log.push('6. current autoplay iframe: ' + (current ? current.id : 'none'));

      document.getElementById('browseView').classList.remove('active');
      log.push('7. browse view closed');

      var container = document.getElementById('container');
      var targetTop = i * window.innerHeight;
      log.push('8. targetTop: ' + targetTop + ', window.innerHeight: ' + window.innerHeight);

      container.scrollTo({ top: targetTop, behavior: 'instant' });
      log.push('9. scrolled');

      var oldIframe = document.getElementById('player-' + i);
      log.push('10. oldIframe: ' + (oldIframe ? oldIframe.id : 'null'));
      if (oldIframe) {
        log.push('10a. oldIframe.src: ' + oldIframe.src.substring(0, 80));
        log.push('10b. oldIframe.parentNode: ' + (oldIframe.parentNode ? oldIframe.parentNode.className : 'null'));
      }

      if (oldIframe) {
        var wrapper = oldIframe.parentNode;
        var movie = filteredMovies[i];
        log.push('11. movie: ' + (movie ? movie.title + ' trailer=' + movie.trailer_id : 'UNDEFINED'));

        if (!movie) {
          log.push('ABORT: no movie at index');
          return { log: log };
        }

        var muted = (typeof isMuted !== 'undefined' && isMuted) ? 1 : 0;
        var newSrc = 'https://www.youtube.com/embed/' + movie.trailer_id +
            '?autoplay=1&mute=' + muted + '&controls=1&playsinline=1&loop=0&modestbranding=1&rel=0&enablejsapi=1';
        log.push('12. newSrc: ' + newSrc.substring(0, 80));

        var fresh = document.createElement('iframe');
        fresh.id = 'player-' + i;
        fresh.src = newSrc;
        fresh.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
        fresh.allowFullscreen = true;
        log.push('13. fresh iframe created');

        wrapper.replaceChild(fresh, oldIframe);
        log.push('14. replaceChild done');

        var check = document.getElementById('player-' + i);
        log.push('15. verify: new iframe src: ' + (check ? check.src.substring(0, 80) : 'null'));
        log.push('15b. verify: loading attr: ' + (check ? check.loading : 'null'));
        log.push('15c. verify: same as fresh? ' + (check === fresh));
      }

      _currentlyPlaying = String(i);
      _browseScrolling = false;
      log.push('16. done. _currentlyPlaying=' + _currentlyPlaying);

    } catch (e) {
      log.push('ERROR: ' + e.message + '\n' + e.stack);
    }
    return { log: log };
  }, idx);

  console.log('\nExecution trace:');
  result.log.forEach(l => console.log('  ' + l));

  // Wait and check final state
  await page.waitForTimeout(2000);
  const finalState = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    return {
      src: iframe ? iframe.src : 'null',
      loading: iframe ? iframe.loading : 'null',
      hasLazy: iframe ? iframe.hasAttribute('loading') : false,
      contentWindow: iframe ? !!iframe.contentWindow : false,
      width: iframe ? iframe.clientWidth : 0,
      height: iframe ? iframe.clientHeight : 0
    };
  }, idx);
  console.log('\nFinal state:', JSON.stringify(finalState, null, 2));

  console.log('\nPage errors:', allErrors);
  console.log('Console after call:', allLogs.filter(l => !l.includes('postMessage')).slice(0, 20));

  await browser.close();
})();
