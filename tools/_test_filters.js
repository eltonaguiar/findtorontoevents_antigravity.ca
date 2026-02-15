/**
 * Comprehensive filter test — checks time tabs, ghost events, and card visibility.
 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = [];
  let passed = 0, failed = 0;

  page.on('pageerror', (err) => errors.push('PageError: ' + err.message));

  function assert(label, condition) {
    if (condition) { console.log('  PASS:', label); passed++; }
    else { console.log('  FAIL:', label); failed++; }
  }

  console.log('Loading page...');
  await page.goto('http://localhost:5173/index.html', { waitUntil: 'networkidle', timeout: 25000 });
  await page.waitForTimeout(6000); // Wait for React + filters to apply

  // ── Test 1: Find React time-period filter tabs ──
  console.log('\n=== Test 1: Time-Period Filter Tabs ===');
  const tabInfo = await page.evaluate(() => {
    // Look for typical React time filter buttons
    var buttons = document.querySelectorAll('button');
    var filterTabs = [];
    for (var i = 0; i < buttons.length; i++) {
      var txt = buttons[i].textContent.trim().toLowerCase();
      if (txt === 'today' || txt === 'this week' || txt === 'this weekend' ||
          txt === 'this month' || txt === 'all' || txt === 'tomorrow') {
        filterTabs.push({
          text: buttons[i].textContent.trim(),
          visible: window.getComputedStyle(buttons[i]).display !== 'none'
        });
      }
    }
    return filterTabs;
  });
  console.log('  Found time tabs:', tabInfo.length > 0 ? tabInfo.map(t => t.text).join(', ') : 'NONE');

  // ── Test 2: Count visible event cards in default view ──
  console.log('\n=== Test 2: Default View Card Count ===');
  const defaultCards = await page.evaluate(() => {
    var cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
    var visible = 0, hidden = 0, wrapperHidden = 0;
    cards.forEach(function(c) {
      var title = c.querySelector('h2, h3');
      if (!title) return;
      var cardHidden = c.classList.contains('event-card-hidden');
      var wrapper = c.parentElement;
      var mx = 3;
      while (wrapper && mx > 0) {
        if (wrapper.className && wrapper.className.indexOf('h-[400px]') >= 0) break;
        wrapper = wrapper.parentElement;
        mx--;
      }
      var wHidden = wrapper && wrapper.classList.contains('event-wrapper-hidden');
      if (cardHidden || wHidden) { hidden++; if (wHidden) wrapperHidden++; }
      else visible++;
    });
    return { visible: visible, hidden: hidden, wrapperHidden: wrapperHidden };
  });
  console.log('  Visible cards:', defaultCards.visible, '| Hidden:', defaultCards.hidden, '| Wrappers hidden:', defaultCards.wrapperHidden);
  assert('At least 10 visible cards in default view', defaultCards.visible >= 10);
  assert('Hidden wrappers match hidden cards', defaultCards.wrapperHidden >= defaultCards.hidden - 2);

  // ── Test 3: Ghost events check ──
  console.log('\n=== Test 3: Ghost Events (Empty Visible Gaps) ===');
  const ghostCheck = await page.evaluate(() => {
    var wrappers = document.querySelectorAll('[class*="h-[400px]"]');
    var gaps = [];
    wrappers.forEach(function(w) {
      var comp = window.getComputedStyle(w);
      if (comp.display !== 'none' && comp.visibility !== 'hidden') {
        var inner = w.querySelector('[class*="glass-panel"]');
        if (inner) {
          var innerComp = window.getComputedStyle(inner);
          if (innerComp.display === 'none' || inner.classList.contains('event-card-hidden')) {
            var t = inner.querySelector('h2, h3');
            gaps.push({
              title: t ? t.textContent.substring(0, 60) : '(no title)',
              wrapperDisplay: comp.display,
              cardHidden: inner.classList.contains('event-card-hidden')
            });
          }
        }
      }
    });
    return gaps;
  });
  console.log('  Empty visible gaps:', ghostCheck.length);
  if (ghostCheck.length > 0) {
    ghostCheck.forEach(g => console.log('    Gap:', g.title, '| wrapper:', g.wrapperDisplay));
  }
  assert('Zero ghost events (empty visible gaps)', ghostCheck.length === 0);

  // ── Test 4: Click "This Week" tab (if exists) and check ──
  console.log('\n=== Test 4: "This Week" Filter ===');
  const weekTabExists = await page.evaluate(() => {
    var buttons = document.querySelectorAll('button');
    for (var i = 0; i < buttons.length; i++) {
      var txt = buttons[i].textContent.trim().toLowerCase();
      if (txt === 'this week') return true;
    }
    return false;
  });

  if (weekTabExists) {
    await page.click('button:has-text("This Week")');
    await page.waitForTimeout(3000); // Wait for React re-render + filters

    const weekCards = await page.evaluate(() => {
      var cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
      var visible = 0, hidden = 0;
      var visibleDates = {};
      cards.forEach(function(c) {
        var title = c.querySelector('h2, h3');
        if (!title) return;
        if (c.classList.contains('event-card-hidden')) { hidden++; return; }
        var wrapper = c.parentElement;
        var mx = 3;
        while (wrapper && mx > 0) {
          if (wrapper.className && wrapper.className.indexOf('h-[400px]') >= 0) break;
          wrapper = wrapper.parentElement;
          mx--;
        }
        if (wrapper && wrapper.classList.contains('event-wrapper-hidden')) { hidden++; return; }

        visible++;
        // Try to extract date from the card
        var dateSpan = c.querySelector('[class*="date"], time, [datetime]');
        var allText = c.textContent;
        var dateMatch = allText.match(/(?:FEB|Feb|feb)\s*(\d{1,2})/);
        if (dateMatch) {
          var d = 'Feb ' + dateMatch[1];
          visibleDates[d] = (visibleDates[d] || 0) + 1;
        }
      });
      return { visible: visible, hidden: hidden, visibleDates: visibleDates };
    });
    console.log('  After clicking "This Week":');
    console.log('    Visible cards:', weekCards.visible, '| Hidden:', weekCards.hidden);
    console.log('    Visible dates:', JSON.stringify(weekCards.visibleDates));
    assert('This Week shows at least 15 cards', weekCards.visible >= 15);
    assert('This Week shows events beyond just today', Object.keys(weekCards.visibleDates).length > 1);
  } else {
    console.log('  No "This Week" button found — checking alternative time filters...');
    // Try to find any time-period tabs
    const altTabs = await page.evaluate(() => {
      var els = document.querySelectorAll('button, [role="tab"], a');
      var found = [];
      for (var i = 0; i < els.length; i++) {
        var t = els[i].textContent.trim();
        if (/week|today|month|weekend/i.test(t) && t.length < 30) {
          found.push(t);
        }
      }
      return found;
    });
    console.log('  Alternative time-related tabs:', altTabs.join(', ') || 'none');
  }

  // ── Test 5: Click "Today" tab (if exists) and check ──
  console.log('\n=== Test 5: "Today" Filter ===');
  const todayTabExists = await page.evaluate(() => {
    var buttons = document.querySelectorAll('button');
    for (var i = 0; i < buttons.length; i++) {
      if (buttons[i].textContent.trim().toLowerCase() === 'today') return true;
    }
    return false;
  });

  if (todayTabExists) {
    await page.click('button:has-text("Today")');
    await page.waitForTimeout(3000);

    const todayCards = await page.evaluate(() => {
      var now = new Date();
      var todayStr = 'Feb ' + now.getDate();
      var cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
      var visible = 0, hidden = 0, todayCount = 0, otherDates = 0;
      cards.forEach(function(c) {
        if (c.classList.contains('event-card-hidden')) { hidden++; return; }
        var wrapper = c.parentElement;
        var mx = 3;
        while (wrapper && mx > 0) {
          if (wrapper.className && wrapper.className.indexOf('h-[400px]') >= 0) break;
          wrapper = wrapper.parentElement;
          mx--;
        }
        if (wrapper && wrapper.classList.contains('event-wrapper-hidden')) { hidden++; return; }
        visible++;
        var allText = c.textContent;
        var dateMatch = allText.match(/(?:FEB|Feb|feb)\s*(\d{1,2})/);
        if (dateMatch && dateMatch[0].toLowerCase() === todayStr.toLowerCase()) todayCount++;
        else otherDates++;
      });
      return { visible: visible, hidden: hidden, todayCount: todayCount, otherDates: otherDates };
    });
    console.log('  After clicking "Today":');
    console.log('    Visible:', todayCards.visible, '| Today dates:', todayCards.todayCount, '| Other dates:', todayCards.otherDates);
    assert('Today filter shows some cards', todayCards.visible > 0);
  } else {
    console.log('  No "Today" button found');
  }

  // ── Test 6: Multi-day filter toggle ──
  console.log('\n=== Test 6: Multi-Day Filter Toggle ===');
  const multiDayToggle = await page.evaluate(() => {
    var labels = document.querySelectorAll('label, button, [class*="toggle"]');
    for (var i = 0; i < labels.length; i++) {
      var t = labels[i].textContent.trim().toLowerCase();
      if (t.indexOf('multi-day') >= 0 || t.indexOf('multi day') >= 0) {
        return { found: true, text: labels[i].textContent.trim() };
      }
    }
    return { found: false };
  });
  console.log('  Multi-day toggle found:', multiDayToggle.found, multiDayToggle.text || '');

  // ── Test 7: Check which events are hidden by our custom filters ──
  console.log('\n=== Test 7: Hidden Events Analysis ===');

  // Go back to default view
  if (weekTabExists) {
    await page.click('button:has-text("This Week")');
    await page.waitForTimeout(3000);
  }

  const hiddenAnalysis = await page.evaluate(() => {
    var cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
    var result = { total: 0, visible: 0, hiddenByFilter: [], hiddenByWrapper: [] };
    cards.forEach(function(c) {
      var title = c.querySelector('h2, h3');
      if (!title) return;
      result.total++;
      var cardHidden = c.classList.contains('event-card-hidden');
      var wrapper = c.parentElement;
      var mx = 3;
      while (wrapper && mx > 0) {
        if (wrapper.className && wrapper.className.indexOf('h-[400px]') >= 0) break;
        wrapper = wrapper.parentElement;
        mx--;
      }
      var wHidden = wrapper && wrapper.classList.contains('event-wrapper-hidden');
      if (cardHidden) {
        result.hiddenByFilter.push(title.textContent.substring(0, 60));
      } else if (wHidden) {
        result.hiddenByWrapper.push(title.textContent.substring(0, 60));
      } else {
        result.visible++;
      }
    });
    return result;
  });
  console.log('  Total cards:', hiddenAnalysis.total);
  console.log('  Visible:', hiddenAnalysis.visible);
  console.log('  Hidden by event-card-hidden (' + hiddenAnalysis.hiddenByFilter.length + '):');
  hiddenAnalysis.hiddenByFilter.forEach(t => console.log('    -', t));
  console.log('  Hidden by wrapper only (' + hiddenAnalysis.hiddenByWrapper.length + '):');
  hiddenAnalysis.hiddenByWrapper.forEach(t => console.log('    -', t));

  // ── Test 8: Filter console log check ──
  console.log('\n=== Test 8: Filter Console Logs ===');
  const filterLogs = await page.evaluate(() => {
    // Check if window.__RAW_EVENTS__ is populated
    return {
      hasRawEvents: !!window.__RAW_EVENTS__,
      rawEventsCount: window.__RAW_EVENTS__ ? window.__RAW_EVENTS__.length : 0
    };
  });
  console.log('  __RAW_EVENTS__ loaded:', filterLogs.hasRawEvents, '| count:', filterLogs.rawEventsCount);
  assert('__RAW_EVENTS__ is populated', filterLogs.rawEventsCount > 0);

  // ── Summary ──
  var jsErrors = errors.filter(e =>
    !e.includes('Minified React error #418') &&
    !e.includes('Failed to load resource') &&
    !e.includes('runtime.lastError') &&
    !e.includes('CORS policy') &&
    !e.includes('Access-Control')
  );

  console.log('\n=== Summary ===');
  console.log('Passed:', passed, '| Failed:', failed);
  console.log('Critical JS Errors:', jsErrors.length);
  jsErrors.forEach(e => console.log('  -', e));

  console.log('\nOverall:', failed === 0 && jsErrors.length === 0 ? 'PASS' : 'FAIL');
  await browser.close();
  process.exit(failed === 0 && jsErrors.length === 0 ? 0 : 1);
})();
