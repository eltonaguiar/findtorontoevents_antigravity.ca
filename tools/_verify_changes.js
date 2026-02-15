const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('pageerror', function(e) { errors.push(e.message); });

  // Clear localStorage to test fresh default
  await page.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.evaluate(function() { localStorage.removeItem('fte_view_mode'); });

  // Reload to test default
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(6000);

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

    return {
      thumbToggleExists: !!thumbToggle,
      thumbToggleVisible: thumbToggle ? window.getComputedStyle(thumbToggle).display !== 'none' : false,
      floatingControlsExists: !!floatingControls,
      nearMeToggleExists: !!nearMeToggle,
      multiDayToggleExists: !!multiDayToggle,
      thumbnailsOnByDefault: htmlHasThumbClass,
      visibleThumbnails: visibleThumbs,
      totalThumbWrappers: thumbWrappers.length
    };
  });

  console.log('=== Verification Results ===');
  console.log('Thumbnail toggle exists:', result.thumbToggleExists);
  console.log('Thumbnail toggle visible:', result.thumbToggleVisible);
  console.log('Floating controls container exists:', result.floatingControlsExists, result.floatingControlsExists ? 'FAIL - should be removed' : 'PASS');
  console.log('Near Me floating button exists:', result.nearMeToggleExists, result.nearMeToggleExists ? 'FAIL - should be removed' : 'PASS');
  console.log('Multi-Day floating button exists:', result.multiDayToggleExists, result.multiDayToggleExists ? 'FAIL - should be removed' : 'PASS');
  console.log('Thumbnails ON by default:', result.thumbnailsOnByDefault, result.thumbnailsOnByDefault ? 'PASS' : 'FAIL');
  console.log('Visible thumbnails:', result.visibleThumbnails, 'of', result.totalThumbWrappers);

  var critErrors = errors.filter(function(e) { return !e.includes('#418') && !e.includes('ads?'); });
  console.log('Critical JS errors:', critErrors.length, critErrors.length === 0 ? 'PASS' : 'FAIL');
  critErrors.forEach(function(e) { console.log('  -', e.substring(0, 120)); });

  await browser.close();
  var passed = result.thumbToggleExists && result.thumbToggleVisible && !result.floatingControlsExists && !result.nearMeToggleExists && !result.multiDayToggleExists && result.thumbnailsOnByDefault;
  process.exit(passed ? 0 : 1);
})();
