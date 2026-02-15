const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const results = { passed: 0, failed: 0, tests: [] };

  function test(name, ok, detail) {
    results.tests.push({ name: name, ok: ok, detail: detail || '' });
    if (ok) results.passed++;
    else results.failed++;
    console.log((ok ? 'PASS' : 'FAIL') + ': ' + name + (detail ? ' — ' + detail : ''));
  }

  // Desktop test
  console.log('\n=== Desktop (1280x800) ===');
  var page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  var errors = [];
  page.on('pageerror', function(e) { errors.push(e.message); });
  page.on('console', function(m) { if (m.type() === 'error' && !m.text().includes('418') && !m.text().includes('ads?') && !m.text().includes('lastError')) errors.push(m.text()); });

  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(8000);

  // 1. Thumbnail toggle exists and visible
  var thumb = await page.evaluate(function() {
    var el = document.getElementById('fte-thumb-toggle');
    if (!el) return null;
    var cs = window.getComputedStyle(el);
    return { display: cs.display, visible: cs.visibility === 'visible' && cs.opacity !== '0' };
  });
  test('Thumbnail toggle visible (desktop)', thumb && thumb.visible, thumb ? 'display=' + thumb.display : 'NOT FOUND');

  // 2. No ghost gaps
  var ghosts = await page.evaluate(function() {
    var gaps = 0;
    document.querySelectorAll('[class*="h-[400px]"]').forEach(function(w) {
      var cs = window.getComputedStyle(w);
      if (cs.display !== 'none') {
        var inner = w.querySelector('[class*="glass-panel"]');
        if (inner && (inner.classList.contains('event-card-hidden') || window.getComputedStyle(inner).display === 'none')) {
          gaps++;
        }
      }
    });
    return gaps;
  });
  test('No ghost gaps (desktop)', ghosts === 0, ghosts + ' ghost gaps');

  // 3. Login + gear aligned
  var align = await page.evaluate(function() {
    var si = document.getElementById('signin-island');
    var cb = document.querySelector('button[title*="System Configuration"]');
    if (!si || !cb) return null;
    return { diff: Math.abs(si.getBoundingClientRect().top - cb.getBoundingClientRect().top) };
  });
  test('Login + gear aligned (desktop)', align && align.diff < 5, align ? 'diff=' + align.diff + 'px' : 'elements missing');

  // 4. Events loaded (reasonable count)
  var evCount = await page.evaluate(function() {
    return window.__RAW_EVENTS__ ? window.__RAW_EVENTS__.length : 0;
  });
  test('Events loaded < 800', evCount > 100 && evCount < 800, evCount + ' events');

  // 5. No hidden events showing as visible gaps  
  var hiddenCount = await page.evaluate(function() {
    var count = 0;
    document.querySelectorAll('.event-card-hidden').forEach(function() { count++; });
    return count;
  });
  test('No filter-hidden events visible as gaps', ghosts === 0, hiddenCount + ' cards hidden, ' + ghosts + ' gaps');

  // 6. No critical JS errors
  var critErrors = errors.filter(function(e) { return !e.includes('ERR_') && !e.includes('net::'); });
  test('No critical JS errors (desktop)', critErrors.length === 0, critErrors.length + ' errors' + (critErrors.length ? ': ' + critErrors[0].substring(0, 100) : ''));

  await page.close();

  // Mobile test
  console.log('\n=== Mobile (375x812) ===');
  page = await browser.newPage({ viewport: { width: 375, height: 812 } });
  errors = [];
  page.on('pageerror', function(e) { errors.push(e.message); });

  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(8000);

  // Thumbnail on mobile
  var thumbMobile = await page.evaluate(function() {
    var el = document.getElementById('fte-thumb-toggle');
    if (!el) return null;
    var r = el.getBoundingClientRect();
    var cs = window.getComputedStyle(el);
    return { visible: cs.visibility === 'visible' && cs.display !== 'none', bottom: Math.round(window.innerHeight - r.bottom), width: r.width };
  });
  test('Thumbnail toggle visible (mobile)', thumbMobile && thumbMobile.visible, thumbMobile ? 'bottom=' + thumbMobile.bottom + 'px' : 'NOT FOUND');

  // Mobile alignment
  var alignMobile = await page.evaluate(function() {
    var si = document.getElementById('signin-island');
    var cb = document.querySelector('button[title*="System Configuration"]');
    if (!si || !cb) return null;
    return { diff: Math.abs(si.getBoundingClientRect().top - cb.getBoundingClientRect().top) };
  });
  test('Login + gear aligned (mobile)', alignMobile && alignMobile.diff < 5, alignMobile ? 'diff=' + alignMobile.diff + 'px' : 'elements missing');

  // Mobile ghost gaps
  var ghostsMobile = await page.evaluate(function() {
    var gaps = 0;
    document.querySelectorAll('[class*="h-[400px]"]').forEach(function(w) {
      var cs = window.getComputedStyle(w);
      if (cs.display !== 'none') {
        var inner = w.querySelector('[class*="glass-panel"]');
        if (inner && (inner.classList.contains('event-card-hidden') || window.getComputedStyle(inner).display === 'none')) {
          gaps++;
        }
      }
    });
    return gaps;
  });
  test('No ghost gaps (mobile)', ghostsMobile === 0, ghostsMobile + ' ghost gaps');

  await page.close();
  await browser.close();

  console.log('\n=== Summary ===');
  console.log(results.passed + '/' + (results.passed + results.failed) + ' tests passed');
  if (results.failed > 0) {
    console.log('FAILURES:');
    results.tests.filter(function(t) { return !t.ok; }).forEach(function(t) { console.log('  - ' + t.name + ': ' + t.detail); });
    process.exit(1);
  }
})();
