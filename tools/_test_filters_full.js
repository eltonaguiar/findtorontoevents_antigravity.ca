/**
 * Full filter test with scrolling and all time tabs
 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  let passed = 0, failed = 0;
  const jsErrors = [];

  page.on('pageerror', (err) => {
    if (!err.message.includes('Minified React error #418')) {
      jsErrors.push(err.message);
    }
  });

  function assert(label, condition) {
    if (condition) { console.log('  PASS:', label); passed++; }
    else { console.log('  FAIL:', label); failed++; }
  }

  console.log('Loading page...');
  await page.goto('http://localhost:5173/index.html', { waitUntil: 'networkidle', timeout: 25000 });
  await page.waitForTimeout(6000);

  // ── Test 1: Default view ──
  console.log('\n=== Test 1: Default View ===');
  let counts = await getVisibleCardCounts(page);
  console.log('  Visible:', counts.visible, '| Hidden:', counts.hidden, '| Dates:', JSON.stringify(counts.dates));
  assert('At least 10 visible cards', counts.visible >= 10);
  assert('Zero ghost gaps', counts.gaps === 0);

  // ── Test 2: Click "This Week" ──
  console.log('\n=== Test 2: This Week Tab ===');
  await clickTab(page, 'This Week');
  await page.waitForTimeout(3000);
  counts = await getVisibleCardCounts(page);
  console.log('  Visible:', counts.visible, '| Hidden:', counts.hidden, '| Dates:', JSON.stringify(counts.dates));
  assert('This Week: at least 15 visible', counts.visible >= 15);
  assert('This Week: zero ghost gaps', counts.gaps === 0);

  // ── Test 3: Scroll down in "This Week" to load more events ──
  console.log('\n=== Test 3: Scroll Down (This Week) ===');
  for (let i = 0; i < 5; i++) {
    await page.evaluate(() => window.scrollBy(0, 1500));
    await page.waitForTimeout(1000);
  }
  await page.waitForTimeout(2000); // Wait for filters to reapply
  counts = await getVisibleCardCounts(page);
  console.log('  After scrolling 5x:');
  console.log('  Visible:', counts.visible, '| Hidden:', counts.hidden, '| Dates:', JSON.stringify(counts.dates));
  const datesAfterScroll = Object.keys(counts.dates).length;
  assert('After scroll: more events loaded', counts.visible >= 20);
  assert('After scroll: events from multiple dates visible', datesAfterScroll >= 2);
  assert('After scroll: zero ghost gaps', counts.gaps === 0);

  // ── Test 4: Click "Tomorrow" ──
  console.log('\n=== Test 4: Tomorrow Tab ===');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  const tomorrowClicked = await clickTab(page, 'Tomorrow');
  if (tomorrowClicked) {
    await page.waitForTimeout(4000);
    counts = await getVisibleCardCounts(page);
    console.log('  Visible:', counts.visible, '| Hidden:', counts.hidden, '| Dates:', JSON.stringify(counts.dates));
    assert('Tomorrow: shows some cards', counts.visible > 0);
    assert('Tomorrow: zero ghost gaps', counts.gaps === 0);
    // Check that Feb 15 events appear
    const hasFeb15 = counts.dates['Feb 15'] > 0;
    assert('Tomorrow: shows Feb 15 events', hasFeb15);
  } else {
    console.log('  No "Tomorrow" tab found');
  }

  // ── Test 5: Click "This Month" ──
  console.log('\n=== Test 5: This Month Tab ===');
  const monthClicked = await clickTab(page, 'This Month');
  if (monthClicked) {
    await page.waitForTimeout(4000);
    counts = await getVisibleCardCounts(page);
    console.log('  Visible:', counts.visible, '| Hidden:', counts.hidden, '| Dates:', JSON.stringify(counts.dates));
    assert('This Month: shows cards', counts.visible > 0);
    assert('This Month: zero ghost gaps', counts.gaps === 0);
  } else {
    console.log('  No "This Month" tab found');
  }

  // ── Test 6: Ghost events specific check ──
  console.log('\n=== Test 6: Ghost Events Deep Check ===');
  // Navigate to default and check for ghost-specific events
  await page.evaluate(() => window.scrollTo(0, 0));
  const ghostSpecific = await page.evaluate(() => {
    var wrappers = document.querySelectorAll('[class*="h-[400px]"]');
    var problems = [];
    wrappers.forEach(function(w) {
      var comp = window.getComputedStyle(w);
      if (comp.display !== 'none' && comp.visibility !== 'hidden') {
        // Wrapper is visible — check if inner card is hidden
        var inner = w.querySelector('[class*="glass-panel"]');
        if (inner) {
          var innerComp = window.getComputedStyle(inner);
          if (innerComp.display === 'none' || inner.classList.contains('event-card-hidden')) {
            var t = inner.querySelector('h2, h3');
            problems.push(t ? t.textContent.substring(0, 60) : '(no title)');
          }
          // Check for invisible cards (opacity 0, visibility hidden)
          if (parseFloat(innerComp.opacity) === 0 || innerComp.visibility === 'hidden') {
            var t2 = inner.querySelector('h2, h3');
            problems.push('INVISIBLE: ' + (t2 ? t2.textContent.substring(0, 60) : '(no title)'));
          }
        }
      }
    });
    return problems;
  });
  console.log('  Ghost problems found:', ghostSpecific.length);
  ghostSpecific.forEach(p => console.log('    -', p));
  assert('No ghost rendering issues', ghostSpecific.length === 0);

  // ── Summary ──
  console.log('\n=== Summary ===');
  console.log('Passed:', passed, '| Failed:', failed);
  console.log('Critical JS Errors:', jsErrors.length);
  jsErrors.forEach(e => console.log('  -', e));
  console.log('Overall:', failed === 0 && jsErrors.length === 0 ? 'PASS' : 'FAIL');

  await browser.close();
  process.exit(failed === 0 ? 0 : 1);
})();

async function clickTab(page, text) {
  try {
    const btn = await page.$('button:has-text("' + text + '")');
    if (btn) { await btn.click(); return true; }
  } catch (e) {}
  return false;
}

async function getVisibleCardCounts(page) {
  return await page.evaluate(() => {
    var cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
    var visible = 0, hidden = 0, dates = {}, gaps = 0;
    var wrappers = document.querySelectorAll('[class*="h-[400px]"]');

    // Count ghost gaps
    wrappers.forEach(function(w) {
      var comp = window.getComputedStyle(w);
      if (comp.display !== 'none' && comp.visibility !== 'hidden') {
        var inner = w.querySelector('[class*="glass-panel"]');
        if (inner && (inner.classList.contains('event-card-hidden') || window.getComputedStyle(inner).display === 'none')) {
          gaps++;
        }
      }
    });

    cards.forEach(function(c) {
      var t = c.querySelector('h2, h3');
      if (!t) return;
      var isHidden = c.classList.contains('event-card-hidden');
      if (!isHidden) {
        var wrapper = c.parentElement;
        var mx = 3;
        while (wrapper && mx > 0) {
          if (wrapper.className && wrapper.className.indexOf('h-[400px]') >= 0) break;
          wrapper = wrapper.parentElement;
          mx--;
        }
        if (wrapper && wrapper.classList.contains('event-wrapper-hidden')) isHidden = true;
      }
      if (isHidden) { hidden++; return; }
      visible++;
      var m = c.textContent.match(/(?:FEB|Feb|feb)\s*(\d{1,2})/);
      if (m) { var d = 'Feb ' + m[1]; dates[d] = (dates[d] || 0) + 1; }
    });
    return { visible: visible, hidden: hidden, dates: dates, gaps: gaps };
  });
}
