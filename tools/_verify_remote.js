const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
  const errors = [];
  page.on('pageerror', (err) => {
    if (!err.message.includes('#418')) errors.push(err.message);
  });

  console.log('Loading live site (mobile)...');
  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(6000);

  const result = await page.evaluate(() => {
    var thumb = document.getElementById('fte-thumb-toggle');
    var thumbBottom = null;
    if (thumb) {
      thumbBottom = Math.round(window.innerHeight - thumb.getBoundingClientRect().bottom);
    }
    // Ghost gaps
    var gaps = 0;
    var wrappers = document.querySelectorAll('[class*="h-[400px]"]');
    wrappers.forEach(function(w) {
      var c = window.getComputedStyle(w);
      if (c.display !== 'none') {
        var inner = w.querySelector('[class*="glass-panel"]');
        if (inner && inner.classList.contains('event-card-hidden')) gaps++;
      }
    });
    // Dating filter
    var datingBtns = 0;
    document.querySelectorAll('button').forEach(function(b) {
      if (b.textContent.trim() === '💘Dating') datingBtns++;
    });
    // Card counts
    var visible = 0, hidden = 0;
    document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)').forEach(function(c) {
      if (c.classList.contains('event-card-hidden')) hidden++;
      else visible++;
    });
    return { thumbBottom: thumbBottom, gaps: gaps, datingBtns: datingBtns, visible: visible, hidden: hidden };
  });

  console.log('Results:');
  console.log('  Thumb toggle bottom:', result.thumbBottom !== null ? result.thumbBottom + 'px' : 'NOT FOUND');
  console.log('  Ghost gaps:', result.gaps);
  console.log('  Dating buttons:', result.datingBtns);
  console.log('  Visible cards:', result.visible);
  console.log('  Hidden cards:', result.hidden);
  console.log('  JS errors:', errors.length);
  errors.forEach(e => console.log('  -', e));

  var pass = result.gaps === 0 && errors.length === 0;
  console.log('\nOverall:', pass ? 'PASS' : 'FAIL');
  await browser.close();
  process.exit(pass ? 0 : 1);
})();
