const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = [];

  page.on('pageerror', (err) => errors.push('PageError: ' + err.message));
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push('ConsoleError: ' + msg.text());
  });

  console.log('Loading page...');
  await page.goto('http://localhost:5173/index.html', { waitUntil: 'networkidle', timeout: 20000 });
  await page.waitForTimeout(6000); // Wait for filters to apply (2s + 4s timeouts)

  const result = await page.evaluate(() => {
    var hiddenWrappers = document.querySelectorAll('.event-wrapper-hidden');
    var hiddenCards = document.querySelectorAll('.event-card-hidden');
    var allCards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
    var ghostCheck = [];

    allCards.forEach(function(c) {
      var t = c.querySelector('h2, h3');
      if (!t) return;
      var txt = t.textContent || '';
      if (txt.indexOf('Love Me Later') >= 0 || txt.indexOf('BODY HEAT') >= 0) {
        // Walk up to find the h-[400px] wrapper (same logic as applyFilters)
        var wrapper = c.parentElement;
        var maxUp = 3;
        while (wrapper && maxUp > 0) {
          if (wrapper.className && wrapper.className.indexOf('h-[400px]') >= 0) break;
          wrapper = wrapper.parentElement;
          maxUp--;
        }
        if (!wrapper || (wrapper.className && wrapper.className.indexOf('h-[400px]') < 0)) {
          wrapper = c.parentElement;
        }
        ghostCheck.push({
          title: txt.substring(0, 80),
          cardHidden: c.classList.contains('event-card-hidden'),
          wrapperHidden: wrapper ? wrapper.classList.contains('event-wrapper-hidden') : 'no wrapper',
          cardDisplay: window.getComputedStyle(c).display,
          wrapperDisplay: wrapper ? window.getComputedStyle(wrapper).display : 'no wrapper'
        });
      }
    });

    // Also check for any empty visible wrapper gaps
    var wrappers = document.querySelectorAll('[class*="h-[400px]"]');
    var emptyGaps = 0;
    var gapDetails = [];
    wrappers.forEach(function(w) {
      var computed = window.getComputedStyle(w);
      var inner = w.querySelector('[class*="glass-panel"]');
      if (inner && inner.classList.contains('event-card-hidden')) {
        var hasWrapperHidden = w.classList.contains('event-wrapper-hidden');
        var wDisplay = computed.display;
        if (wDisplay !== 'none') {
          emptyGaps++;
          var t = inner.querySelector('h2, h3');
          gapDetails.push({
            title: t ? t.textContent.substring(0, 50) : '(no title)',
            wrapperHidden: hasWrapperHidden,
            wrapperDisplay: wDisplay,
            inStaticGrid: !!w.closest('#events-grid')
          });
        }
      }
    });

    return {
      totalCards: allCards.length,
      hiddenCards: hiddenCards.length,
      hiddenWrappers: hiddenWrappers.length,
      emptyGaps: emptyGaps,
      gapDetails: gapDetails,
      ghostCheck: ghostCheck
    };
  });

  console.log('\n=== Ghost Events Fix Test ===');
  console.log('Total event cards:', result.totalCards);
  console.log('Hidden cards (event-card-hidden):', result.hiddenCards);
  console.log('Hidden wrappers (event-wrapper-hidden):', result.hiddenWrappers);
  console.log('Empty visible gaps (wrapper visible but card hidden):', result.emptyGaps);
  if (result.gapDetails.length > 0) {
    console.log('Gap details:');
    result.gapDetails.forEach(function(g) {
      console.log('  Title:', g.title, '| inStaticGrid:', g.inStaticGrid, '| wrapperHidden:', g.wrapperHidden, '| display:', g.wrapperDisplay);
    });
  }
  console.log('\nGhost event check (Love Me Later / BODY HEAT):');
  if (result.ghostCheck.length === 0) {
    console.log('  Not found in DOM (may have been filtered by React)');
  } else {
    result.ghostCheck.forEach(function(g) {
      console.log('  Title:', g.title);
      console.log('    Card hidden:', g.cardHidden, '| Card display:', g.cardDisplay);
      console.log('    Wrapper hidden:', g.wrapperHidden, '| Wrapper display:', g.wrapperDisplay);
      var ok = g.cardHidden && g.wrapperHidden && g.cardDisplay === 'none' && g.wrapperDisplay === 'none';
      console.log('    Status:', ok ? 'PASS - properly hidden' : 'FAIL - still visible!');
    });
  }

  var jsErrors = errors.filter(function(e) {
    return e.indexOf('Minified React error #418') < 0 &&
           e.indexOf('Failed to load resource') < 0 &&
           e.indexOf('runtime.lastError') < 0 &&
           e.indexOf('CORS policy') < 0 &&
           e.indexOf('Access-Control-Allow-Origin') < 0;
  });
  console.log('\nCritical JS Errors:', jsErrors.length);
  jsErrors.forEach(function(e) { console.log('  -', e); });

  var pass = result.emptyGaps === 0 && jsErrors.length === 0;
  if (result.ghostCheck.length > 0) {
    result.ghostCheck.forEach(function(g) {
      if (!g.cardHidden || !g.wrapperHidden) pass = false;
    });
  }

  console.log('\nOverall:', pass ? 'PASS' : 'FAIL');
  await browser.close();
  process.exit(pass ? 0 : 1);
})();
