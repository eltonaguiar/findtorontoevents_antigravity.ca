var playwright = require('playwright');
(async function() {
  var browser = await playwright.chromium.launch({ headless: true });
  var page = await browser.newPage();

  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(5000);

  console.log('=== Test 1: Open theme picker ===');
  await page.locator('div.fixed.bottom-6.right-6 button').click();
  await page.waitForTimeout(500);

  var panelOpen = await page.evaluate(function() {
    var panel = document.getElementById('theme-picker-panel');
    return panel && panel.style.display === 'flex';
  });
  console.log('Picker opened:', panelOpen ? 'PASS' : 'FAIL');

  console.log('\n=== Test 2: Category tabs ===');
  var tabs = await page.evaluate(function() {
    return Array.from(document.querySelectorAll('[data-category-tab]')).map(function(t) { return t.textContent; });
  });
  console.log('Categories:', tabs.join(', '));

  console.log('\n=== Test 3: Apply a theme (Matrix Rain) ===');
  // Search for Matrix Rain
  await page.fill('#theme-picker-search', 'Matrix');
  await page.waitForTimeout(300);

  var searchResults = await page.evaluate(function() {
    return document.querySelectorAll('[data-theme-id]').length;
  });
  console.log('Search results for "Matrix":', searchResults);

  // Click Apply on first result
  var applyBtn = page.locator('[data-theme-id] [data-action="apply"]').first();
  if (await applyBtn.isVisible()) {
    await applyBtn.click();
    await page.waitForTimeout(500);

    var themeApplied = await page.evaluate(function() {
      var root = document.documentElement;
      var cs = getComputedStyle(root);
      var saved = localStorage.getItem('toronto-events-settings');
      return {
        pk500: cs.getPropertyValue('--pk-500').trim(),
        bodyBg: getComputedStyle(document.body).backgroundColor,
        savedTheme: saved ? JSON.parse(saved).selectedTheme : 'NONE',
        overrideStyle: !!document.getElementById('theme-override'),
      };
    });
    console.log('Theme applied:', JSON.stringify(themeApplied, null, 2));
    console.log('Apply:', themeApplied.savedTheme && themeApplied.overrideStyle ? 'PASS' : 'FAIL');
  }

  console.log('\n=== Test 4: Reset theme ===');
  await page.fill('#theme-picker-search', '');
  await page.waitForTimeout(100);
  await page.click('#theme-picker-reset');
  await page.waitForTimeout(500);

  var afterReset = await page.evaluate(function() {
    var saved = localStorage.getItem('toronto-events-settings');
    return {
      overrideStyleGone: !document.getElementById('theme-override'),
      savedTheme: saved ? JSON.parse(saved).selectedTheme : 'NONE',
    };
  });
  console.log('After reset:', JSON.stringify(afterReset));
  console.log('Reset:', afterReset.overrideStyleGone && !afterReset.savedTheme ? 'PASS' : 'FAIL');

  console.log('\n=== Test 5: Close with ESC ===');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);
  var afterEsc = await page.evaluate(function() {
    var panel = document.getElementById('theme-picker-panel');
    return panel ? panel.style.display : 'GONE';
  });
  console.log('Panel after ESC:', afterEsc);
  console.log('ESC close:', afterEsc === 'none' ? 'PASS' : 'FAIL');

  console.log('\n=== Test 6: Theme persists after reload ===');
  // Apply theme, reload, check
  await page.locator('div.fixed.bottom-6.right-6 button').click();
  await page.waitForTimeout(500);
  await page.locator('[data-theme-id="blog101"] [data-action="apply"]').click();
  await page.waitForTimeout(500);

  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  var afterReload = await page.evaluate(function() {
    var saved = localStorage.getItem('toronto-events-settings');
    return {
      savedTheme: saved ? JSON.parse(saved).selectedTheme : 'NONE',
      overrideActive: !!document.getElementById('theme-override'),
      pk500: getComputedStyle(document.documentElement).getPropertyValue('--pk-500').trim(),
    };
  });
  console.log('After reload:', JSON.stringify(afterReload));
  console.log('Persistence:', afterReload.savedTheme === 'blog101' && afterReload.overrideActive ? 'PASS' : 'FAIL');

  await browser.close();
})().catch(function(err) { console.error('Script error:', err.message); });
