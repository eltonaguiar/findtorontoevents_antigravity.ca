const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('pageerror', function(e) { errors.push(e.message); });

  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(8000);

  const result = await page.evaluate(function() {
    var thumbToggle = document.getElementById('fte-thumb-toggle');
    var floatingControls = document.getElementById('custom-filter-controls');
    var nearMeToggle = document.getElementById('near-me-toggle');
    var multiDayToggle = document.getElementById('multiday-toggle');
    var htmlHasThumbClass = document.documentElement.classList.contains('fte-thumbnails-on');
    var thumbWrappers = document.querySelectorAll('.fte-thumb-wrap');
    var visibleThumbs = 0;
    thumbWrappers.forEach(function(w) {
      if (window.getComputedStyle(w).display !== 'none') visibleThumbs++;
    });

    // Ghost gaps
    var ghostGaps = 0;
    document.querySelectorAll('[class*="h-[400px]"]').forEach(function(w) {
      var cs = window.getComputedStyle(w);
      if (cs.display !== 'none') {
        var inner = w.querySelector('[class*="glass-panel"]');
        if (inner && (inner.classList.contains('event-card-hidden') || window.getComputedStyle(inner).display === 'none')) {
          ghostGaps++;
        }
      }
    });

    // Alignment
    var si = document.getElementById('signin-island');
    var cb = document.querySelector('button[title*="System Configuration"]');
    var alignDiff = (si && cb) ? Math.abs(si.getBoundingClientRect().top - cb.getBoundingClientRect().top) : -1;

    return {
      thumbToggleExists: !!thumbToggle,
      thumbToggleVisible: thumbToggle ? window.getComputedStyle(thumbToggle).display !== 'none' : false,
      floatingControlsExists: !!floatingControls,
      nearMeToggleExists: !!nearMeToggle,
      multiDayToggleExists: !!multiDayToggle,
      thumbnailsOn: htmlHasThumbClass,
      visibleThumbnails: visibleThumbs,
      totalThumbWrappers: thumbWrappers.length,
      ghostGaps: ghostGaps,
      alignDiff: alignDiff,
      eventsCount: window.__RAW_EVENTS__ ? window.__RAW_EVENTS__.length : 0
    };
  });

  var pass = 0, fail = 0;
  function test(name, ok, detail) {
    console.log((ok ? 'PASS' : 'FAIL') + ': ' + name + (detail ? ' — ' + detail : ''));
    if (ok) pass++; else fail++;
  }

  test('Thumbnail toggle visible', result.thumbToggleExists && result.thumbToggleVisible);
  test('No floating "Near Me" button', !result.nearMeToggleExists);
  test('No floating "Multi-Day" button', !result.multiDayToggleExists);
  test('No floating controls container', !result.floatingControlsExists);
  test('Thumbnails ON by default', result.thumbnailsOn, result.visibleThumbnails + '/' + result.totalThumbWrappers + ' visible');
  test('No ghost gaps', result.ghostGaps === 0, result.ghostGaps + ' gaps');
  test('Login + gear aligned', result.alignDiff >= 0 && result.alignDiff < 5, result.alignDiff + 'px diff');
  test('Events count < 700', result.eventsCount > 100 && result.eventsCount < 700, result.eventsCount + ' events');
  
  var critErrors = errors.filter(function(e) { return !e.includes('#418') && !e.includes('ads?'); });
  test('No critical JS errors', critErrors.length === 0, critErrors.length + ' errors');

  console.log('\n' + pass + '/' + (pass + fail) + ' passed');
  await browser.close();
  process.exit(fail > 0 ? 1 : 0);
})();
