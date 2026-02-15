const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('pageerror', function(e) { errors.push(e.message); });

  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(6000);

  // Click the gear button to open the picker
  console.log('Opening gear panel...');
  const gearClicked = await page.evaluate(function() {
    // Find the bottom-right gear area
    var gears = document.querySelectorAll('.fixed.bottom-6.right-6 button');
    if (gears.length > 0) {
      gears[0].click();
      return true;
    }
    // Fallback: find any settings button
    var btn = document.querySelector('button[aria-label="Open Settings"]');
    if (btn) { btn.click(); return true; }
    return false;
  });
  console.log('Gear clicked:', gearClicked);

  await page.waitForTimeout(500);

  // Check if the theme picker panel opened
  const panelInfo = await page.evaluate(function() {
    var panel = document.getElementById('theme-picker-panel');
    if (!panel) return { exists: false };

    var thumbToggle = document.getElementById('gear-thumb-toggle');
    var thumbSlider = document.getElementById('gear-thumb-slider');
    var thumbSave = document.getElementById('gear-thumb-save');
    var thumbSaveText = document.getElementById('gear-thumb-save-text');
    var permTheme = document.getElementById('perm-theme-check');
    var autoApply = document.getElementById('theme-auto-apply');

    return {
      exists: true,
      display: window.getComputedStyle(panel).display,
      thumbToggle: {
        exists: !!thumbToggle,
        checked: thumbToggle ? thumbToggle.checked : null
      },
      thumbSlider: !!thumbSlider,
      thumbSave: {
        exists: !!thumbSave,
        checked: thumbSave ? thumbSave.checked : null,
        disabled: thumbSave ? thumbSave.disabled : null,
        text: thumbSaveText ? thumbSaveText.textContent : null
      },
      permTheme: !!permTheme,
      autoApply: !!autoApply
    };
  });

  console.log('\n=== Gear Panel Results ===');
  console.log('Panel exists:', panelInfo.exists);
  console.log('Panel display:', panelInfo.display);
  console.log('Thumbnail toggle:', JSON.stringify(panelInfo.thumbToggle));
  console.log('Thumbnail slider:', panelInfo.thumbSlider);
  console.log('Thumbnail save:', JSON.stringify(panelInfo.thumbSave));
  console.log('Permanent theme checkbox:', panelInfo.permTheme);
  console.log('Auto-apply checkbox:', panelInfo.autoApply);

  // Test toggling the thumbnail switch
  if (panelInfo.thumbToggle.exists) {
    console.log('\nTesting toggle...');
    var wasBefore = panelInfo.thumbToggle.checked;
    // Click the slider (visible part of toggle), not the hidden checkbox
    await page.evaluate(function() {
      var cb = document.getElementById('gear-thumb-toggle');
      if (cb) { cb.checked = !cb.checked; cb.dispatchEvent(new Event('change')); }
    });
    await page.waitForTimeout(300);

    var afterToggle = await page.evaluate(function() {
      var cb = document.getElementById('gear-thumb-toggle');
      var hasClass = document.documentElement.classList.contains('fte-thumbnails-on');
      var floatingBtn = document.getElementById('fte-thumb-toggle');
      return {
        checked: cb ? cb.checked : null,
        htmlHasThumbClass: hasClass,
        floatingBtnActive: floatingBtn ? floatingBtn.classList.contains('active') : null
      };
    });
    console.log('After toggle:', JSON.stringify(afterToggle));
    console.log('Toggle synced to page:', afterToggle.checked === afterToggle.htmlHasThumbClass ? 'PASS' : 'FAIL');
    console.log('Floating button synced:', afterToggle.checked === afterToggle.floatingBtnActive ? 'PASS' : 'FAIL');
  }

  var critErrors = errors.filter(function(e) { return !e.includes('#418') && !e.includes('ads?'); });
  console.log('\nJS errors:', critErrors.length, critErrors.length === 0 ? 'PASS' : 'FAIL');
  critErrors.forEach(function(e) { console.log('  -', e.substring(0, 100)); });

  await browser.close();
})();
