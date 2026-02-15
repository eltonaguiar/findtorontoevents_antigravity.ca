const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
  const consoleLogs = [];
  const errors = [];

  page.on('pageerror', (err) => errors.push('PageError: ' + err.message));
  page.on('console', (msg) => {
    var t = msg.text();
    if (t.includes('[THUMBNAILS]') || t.includes('[FILTERS]') || t.includes('[PREFS]') || t.includes('SyntaxError')) {
      consoleLogs.push(msg.type() + ': ' + t);
    }
  });

  console.log('Loading live site...');
  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(8000);

  // 1. Thumbnail toggle
  console.log('\n=== Thumbnail Toggle ===');
  const thumbInfo = await page.evaluate(() => {
    var el = document.getElementById('fte-thumb-toggle');
    if (!el) return { exists: false };
    var r = el.getBoundingClientRect();
    var cs = window.getComputedStyle(el);
    return {
      exists: true,
      display: cs.display,
      visibility: cs.visibility,
      opacity: cs.opacity,
      zIndex: cs.zIndex,
      width: r.width,
      height: r.height,
      top: Math.round(r.top),
      bottom: Math.round(window.innerHeight - r.bottom),
      innerHTML: el.innerHTML.substring(0, 100)
    };
  });
  if (!thumbInfo.exists) {
    console.log('  MISSING! #fte-thumb-toggle not found in DOM');
  } else {
    console.log('  Found:', JSON.stringify(thumbInfo, null, 2));
  }

  // 2. Ghost events / hidden events
  console.log('\n=== Ghost / Hidden Events ===');
  const ghostInfo = await page.evaluate(() => {
    var cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
    var visible = 0, hidden = 0, ghostGaps = 0;
    var hiddenTitles = [];
    var ghostTitles = [];

    cards.forEach(function(c) {
      var t = c.querySelector('h2, h3');
      var title = t ? t.textContent.substring(0, 60) : '(no title)';
      if (c.classList.contains('event-card-hidden')) {
        hidden++;
        hiddenTitles.push(title);
      } else {
        visible++;
      }
    });

    // Check for ghost gaps (wrapper visible, card hidden)
    document.querySelectorAll('[class*="h-[400px]"]').forEach(function(w) {
      var cs = window.getComputedStyle(w);
      if (cs.display !== 'none') {
        var inner = w.querySelector('[class*="glass-panel"]');
        if (inner && (inner.classList.contains('event-card-hidden') || window.getComputedStyle(inner).display === 'none')) {
          ghostGaps++;
          var t = inner.querySelector('h2, h3');
          ghostTitles.push(t ? t.textContent.substring(0, 60) : '(no title)');
        }
      }
    });

    return { visible: visible, hidden: hidden, ghostGaps: ghostGaps, hiddenTitles: hiddenTitles, ghostTitles: ghostTitles };
  });
  console.log('  Visible:', ghostInfo.visible, '| Hidden:', ghostInfo.hidden, '| Ghost gaps:', ghostInfo.ghostGaps);
  if (ghostInfo.hiddenTitles.length) {
    console.log('  Hidden events:');
    ghostInfo.hiddenTitles.forEach(t => console.log('    -', t));
  }
  if (ghostInfo.ghostTitles.length) {
    console.log('  Ghost gap events:');
    ghostInfo.ghostTitles.forEach(t => console.log('    -', t));
  }

  // 3. Login icon + gear icon alignment
  console.log('\n=== Login + Gear Alignment ===');
  const alignInfo = await page.evaluate(() => {
    var signIn = document.getElementById('signin-island');
    var configBtn = document.querySelector('button[title*="System Configuration"]');
    if (!signIn || !configBtn) {
      return { signIn: !!signIn, configBtn: !!configBtn, aligned: false };
    }
    var sr = signIn.getBoundingClientRect();
    var cr = configBtn.getBoundingClientRect();
    return {
      signIn: true,
      configBtn: true,
      signInTop: Math.round(sr.top),
      configTop: Math.round(cr.top),
      signInRight: Math.round(sr.right),
      configRight: Math.round(cr.right),
      verticalDiff: Math.abs(Math.round(sr.top) - Math.round(cr.top)),
      aligned: Math.abs(sr.top - cr.top) < 10
    };
  });
  console.log('  Sign-in island:', alignInfo.signIn ? 'found' : 'NOT FOUND');
  console.log('  Config button:', alignInfo.configBtn ? 'found' : 'NOT FOUND');
  if (alignInfo.signIn && alignInfo.configBtn) {
    console.log('  Sign-in top:', alignInfo.signInTop, '| Config top:', alignInfo.configTop);
    console.log('  Vertical diff:', alignInfo.verticalDiff + 'px', '|', alignInfo.aligned ? 'ALIGNED' : 'NOT ALIGNED');
  }

  // 4. Events.json stats
  console.log('\n=== Events Data ===');
  const eventsStats = await page.evaluate(() => {
    return {
      rawEventsLoaded: !!window.__RAW_EVENTS__,
      rawEventsCount: window.__RAW_EVENTS__ ? window.__RAW_EVENTS__.length : 0
    };
  });
  console.log('  __RAW_EVENTS__:', eventsStats.rawEventsLoaded ? eventsStats.rawEventsCount + ' events' : 'NOT LOADED');

  // 5. Console logs
  console.log('\n=== Relevant Console Logs ===');
  consoleLogs.forEach(l => console.log('  ' + l));

  console.log('\n=== JS Errors ===');
  var criticalErrors = errors.filter(e => !e.includes('#418') && !e.includes('Failed to load') && !e.includes('lastError'));
  console.log('  Critical:', criticalErrors.length);
  criticalErrors.forEach(e => console.log('  -', e));

  await browser.close();
})();
