const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('pageerror', function(e) { errors.push(e.message); });

  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(8000);

  // Click the gear button
  console.log('Opening gear panel...');
  await page.evaluate(function() {
    var gears = document.querySelectorAll('.fixed.bottom-6.right-6 button');
    if (gears.length > 0) gears[0].click();
  });
  await page.waitForTimeout(500);

  const result = await page.evaluate(function() {
    var panel = document.getElementById('theme-picker-panel');
    var thumbToggle = document.getElementById('gear-thumb-toggle');
    var thumbSlider = document.getElementById('gear-thumb-slider');
    var thumbSave = document.getElementById('gear-thumb-save');
    var thumbSaveText = document.getElementById('gear-thumb-save-text');
    var floatingBtn = document.getElementById('fte-thumb-toggle');
    var signinIsland = document.getElementById('signin-island');
    var configBtn = document.querySelector('button[title*="System Configuration"]');

    return {
      panelExists: !!panel,
      panelVisible: panel ? window.getComputedStyle(panel).display !== 'none' : false,
      thumbToggle: thumbToggle ? { exists: true, checked: thumbToggle.checked } : { exists: false },
      thumbSlider: !!thumbSlider,
      thumbSave: thumbSave ? {
        exists: true,
        disabled: thumbSave.disabled,
        text: thumbSaveText ? thumbSaveText.textContent : ''
      } : { exists: false },
      floatingBtnExists: !!floatingBtn,
      floatingBtnVisible: floatingBtn ? window.getComputedStyle(floatingBtn).display !== 'none' : false,
      alignDiff: (signinIsland && configBtn) ? Math.abs(signinIsland.getBoundingClientRect().top - configBtn.getBoundingClientRect().top) : -1,
      eventsCount: window.__RAW_EVENTS__ ? window.__RAW_EVENTS__.length : 0,
      ghostGaps: (function() {
        var g = 0;
        document.querySelectorAll('[class*="h-[400px]"]').forEach(function(w) {
          var cs = window.getComputedStyle(w);
          if (cs.display !== 'none') {
            var inner = w.querySelector('[class*="glass-panel"]');
            if (inner && (inner.classList.contains('event-card-hidden') || window.getComputedStyle(inner).display === 'none')) g++;
          }
        });
        return g;
      })()
    };
  });

  var pass = 0, fail = 0;
  function test(name, ok, detail) {
    console.log((ok ? 'PASS' : 'FAIL') + ': ' + name + (detail ? ' — ' + detail : ''));
    if (ok) pass++; else fail++;
  }

  test('Gear panel opens', result.panelExists && result.panelVisible);
  test('Thumbnail toggle in gear panel', result.thumbToggle.exists, 'checked=' + result.thumbToggle.checked);
  test('Toggle slider visual', result.thumbSlider);
  test('Save preference checkbox', result.thumbSave.exists, 'disabled=' + result.thumbSave.disabled + ' text="' + (result.thumbSave.text || '') + '"');
  test('Floating thumbnail button exists', result.floatingBtnExists && result.floatingBtnVisible);
  test('Login + gear aligned', result.alignDiff >= 0 && result.alignDiff < 5, result.alignDiff + 'px');
  test('Events loaded', result.eventsCount > 100 && result.eventsCount < 700, result.eventsCount + ' events');
  test('No ghost gaps', result.ghostGaps === 0);

  var critErrors = errors.filter(function(e) { return !e.includes('#418') && !e.includes('ads?'); });
  test('No critical JS errors', critErrors.length === 0, critErrors.length + ' errors');

  console.log('\n' + pass + '/' + (pass + fail) + ' passed');
  await browser.close();
  process.exit(fail > 0 ? 1 : 0);
})();
