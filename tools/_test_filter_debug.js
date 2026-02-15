/**
 * Debug test - logs exactly why each hidden event is hidden
 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Capture console logs from the page
  const consoleLogs = [];
  page.on('console', (msg) => {
    if (msg.text().includes('[FILTERS]') || msg.text().includes('[FILTER-DEBUG]')) {
      consoleLogs.push(msg.text());
    }
  });

  console.log('Loading page...');
  await page.goto('http://localhost:5173/index.html', { waitUntil: 'networkidle', timeout: 25000 });
  await page.waitForTimeout(3000);

  // Inject debug version of applyFilters that logs reasons
  await page.evaluate(() => {
    var cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]');
    cards.forEach(function(card) {
      if (!card.classList.contains('event-card-hidden')) return;

      var titleEl = card.querySelector('h2, h3, [class*="title"], [class*="Title"]');
      if (!titleEl) return;
      var rawTitle = titleEl.textContent || '';
      var title = rawTitle.replace(/📅\s*Multi-Day/g, '').replace(/📍\s*[\d.]+\s*km/g, '').trim();

      // Try to find matching event
      var eventData = null;
      if (window.__RAW_EVENTS__) {
        eventData = window.__RAW_EVENTS__.find(function(e) {
          var eTitle = (e.title || '').toLowerCase();
          var cardTitle = title.toLowerCase();
          return eTitle === cardTitle ||
                 eTitle.includes(cardTitle.substring(0, 20)) ||
                 cardTitle.includes(eTitle.substring(0, 20));
        });
      }

      var reason = 'unknown';
      if (eventData) {
        var eventEnd = eventData.endDate ? new Date(eventData.endDate) : new Date(eventData.date);
        var now = new Date();
        var todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());

        if (eventEnd < todayStart) {
          reason = 'past-event (endDate ' + eventEnd.toISOString() + ' < todayStart ' + todayStart.toISOString() + ')';
        } else {
          // Check multi-day
          var isMulti = false;
          if (eventData.is_multi_day || eventData.isMultiDay) isMulti = true;
          if (eventData.endDate) {
            var dur = (new Date(eventData.endDate) - new Date(eventData.date)) / 3600000;
            if (dur >= 18) isMulti = true;
          }
          var t = (eventData.title || '').toLowerCase();
          if (['festival','exhibition','exhibit','runs until','conference'].some(function(k){return t.includes(k)})) isMulti = true;

          if (isMulti) {
            reason = 'multi-day (duration ' + ((eventData.endDate ? (new Date(eventData.endDate) - new Date(eventData.date)) / 3600000 : 0).toFixed(1)) + 'h)';
          } else {
            reason = 'NOT filtered by date or multi-day logic (eventData found but shouldShow=true) — something else hiding it';
          }
        }
      } else {
        reason = 'NO eventData match found in __RAW_EVENTS__ (title matching failed)';
      }

      console.log('[FILTER-DEBUG] HIDDEN: "' + title.substring(0, 60) + '" | Reason: ' + reason +
        (eventData ? ' | date: ' + eventData.date + ' | endDate: ' + (eventData.endDate || 'none') : ''));
    });
  });

  await page.waitForTimeout(500);

  console.log('\n=== Filter Debug Output ===');
  consoleLogs.filter(l => l.includes('[FILTER-DEBUG]')).forEach(l => console.log(l));

  // Also check: what events does React actually render for "This Week"?
  console.log('\n=== Clicking "This Week" ===');
  const weekBtn = await page.$('button:has-text("This Week")');
  if (weekBtn) {
    await weekBtn.click();
    await page.waitForTimeout(4000);

    // Re-check hidden
    const hidden2 = await page.evaluate(() => {
      var cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
      var results = [];
      cards.forEach(function(c) {
        var t = c.querySelector('h2, h3');
        if (!t) return;
        var isHidden = c.classList.contains('event-card-hidden');
        var wrapper = c.parentElement;
        var mx = 3;
        while (wrapper && mx > 0) {
          if (wrapper.className && wrapper.className.indexOf('h-[400px]') >= 0) break;
          wrapper = wrapper.parentElement;
          mx--;
        }
        var wHidden = wrapper && wrapper.classList.contains('event-wrapper-hidden');
        if (isHidden || wHidden) {
          results.push(t.textContent.substring(0, 60));
        }
      });
      return results;
    });
    console.log('Hidden after "This Week" click:', hidden2.length);
    hidden2.forEach(t => console.log('  -', t));

    // Count by date
    const dateCounts = await page.evaluate(() => {
      var cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
      var counts = { visible: {}, hidden: {} };
      cards.forEach(function(c) {
        var isHidden = c.classList.contains('event-card-hidden');
        var m = c.textContent.match(/(?:FEB|Feb|feb)\s*(\d{1,2})/);
        var d = m ? 'Feb ' + m[1] : 'unknown';
        var bucket = isHidden ? 'hidden' : 'visible';
        counts[bucket][d] = (counts[bucket][d] || 0) + 1;
      });
      return counts;
    });
    console.log('\nVisible by date:', JSON.stringify(dateCounts.visible));
    console.log('Hidden by date:', JSON.stringify(dateCounts.hidden));
  }

  await browser.close();
})();
