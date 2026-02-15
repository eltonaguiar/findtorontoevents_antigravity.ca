const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 375, height: 812 } });
  await p.goto('https://findtorontoevents.ca/', { waitUntil: 'networkidle', timeout: 30000 });
  await p.waitForTimeout(8000);

  const r = await p.evaluate(function() {
    var events = window.__RAW_EVENTS__ || [];
    var feb14 = events.filter(function(e) { return e.date && e.date.startsWith('2026-02-14'); });
    var feb13 = events.filter(function(e) { return e.date && e.date.startsWith('2026-02-13'); });
    var hb = events.filter(function(e) { return e.title && e.title.indexOf('HEARTBREAK') >= 0; });
    var feb15 = events.filter(function(e) { return e.date && e.date.startsWith('2026-02-15'); });

    // Check visible cards for any past date
    var cards = document.querySelectorAll('h2, h3');
    var heartbreakCards = [];
    cards.forEach(function(t) {
      if (t.textContent.indexOf('HEARTBREAK') >= 0) {
        heartbreakCards.push(t.textContent.substring(0, 60));
      }
    });

    // Check ghost gaps
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

    return {
      total: events.length,
      feb13InData: feb13.length,
      feb14InData: feb14.length,
      feb15InData: feb15.length,
      heartbreakInData: hb.length,
      heartbreakVisible: heartbreakCards,
      ghostGaps: ghostGaps
    };
  });

  console.log('Total events loaded:', r.total);
  console.log('Feb 13 events in data:', r.feb13InData);
  console.log('Feb 14 events in data:', r.feb14InData);
  console.log('Feb 15 events in data:', r.feb15InData);
  console.log('HEARTBREAK in data:', r.heartbreakInData);
  console.log('HEARTBREAK visible cards:', r.heartbreakVisible.length);
  console.log('Ghost gaps:', r.ghostGaps);

  if (r.feb14InData > 0 || r.heartbreakInData > 0) {
    console.log('FAIL: Past events still in data!');
    process.exit(1);
  } else {
    console.log('PASS: No past events in data.');
  }

  await b.close();
})();
