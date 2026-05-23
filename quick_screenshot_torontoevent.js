const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  const consoleMessages = [];
  const jsErrors = [];
  const networkErrors = [];

  // Capture console messages
  page.on('console', msg => {
    consoleMessages.push({ type: msg.type(), text: msg.text() });
  });

  // Capture JS errors
  page.on('pageerror', error => {
    jsErrors.push(error.message);
  });

  // Capture network failures
  page.on('response', response => {
    if (!response.ok() && response.status() !== 304) {
      networkErrors.push({ url: response.url(), status: response.status() });
    }
  });

  console.log('Navigating to https://torontoevent.net/index.html...');

  try {
    await page.goto('https://torontoevent.net/index.html', {
      waitUntil: 'domcontentloaded',
      timeout: 15000
    });

    // Wait for events to load
    await page.waitForTimeout(5000);

    console.log('Taking screenshots...');

    // Screenshot 1: Full page
    await page.screenshot({
      path: 'torontoevent_net_fullpage.png',
      fullPage: true
    });
    console.log('✅ Saved: torontoevent_net_fullpage.png');

    // Screenshot 2: Main viewport
    await page.screenshot({
      path: 'torontoevent_net_viewport.png'
    });
    console.log('✅ Saved: torontoevent_net_viewport.png');

    // Scroll to bottom for gear icon
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);

    // Screenshot 3: Bottom-right area
    await page.screenshot({
      path: 'torontoevent_net_bottomright.png',
      clip: { x: 1600, y: 800, width: 320, height: 280 }
    });
    console.log('✅ Saved: torontoevent_net_bottomright.png');

    // Check for event cards
    const eventCards = await page.locator('.event-card, [class*="event"], article').count();
    console.log(`\nEvent cards found: ${eventCards}`);

    // Check for images
    const eventImages = await page.locator('.event-card img, [class*="event"] img, article img, img[alt*="event" i]').count();
    console.log(`Event images found: ${eventImages}`);

    // Check for gear icon
    const gearElements = await page.evaluate(() => {
      const selectors = [
        '.gear-icon',
        '[class*="settings"]',
        '[class*="gear"]',
        'button[title*="settings" i]',
        'a[title*="settings" i]',
        'svg[class*="gear"]',
        'i[class*="gear"]'
      ];
      let found = [];
      selectors.forEach(sel => {
        const els = document.querySelectorAll(sel);
        if (els.length > 0) {
          found.push({ selector: sel, count: els.length });
        }
      });
      
      // Also check for fixed positioned elements in bottom-right
      const allElements = Array.from(document.querySelectorAll('*'));
      const bottomRight = allElements.filter(el => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return (style.position === 'fixed' || style.position === 'absolute') &&
               rect.bottom > window.innerHeight - 100 &&
               rect.right > window.innerWidth - 100;
      }).map(el => ({
        tag: el.tagName,
        class: el.className,
        id: el.id,
        innerHTML: el.innerHTML.substring(0, 100)
      }));
      
      return { gearSelectors: found, bottomRightElements: bottomRight };
    });
    
    console.log('\nGear icon check:', JSON.stringify(gearElements, null, 2));

    // Summary
    console.log('\n=== SUMMARY ===');
    console.log(`Console Errors: ${consoleMessages.filter(m => m.type === 'error').length}`);
    console.log(`Page Errors: ${jsErrors.length}`);
    console.log(`Network Errors: ${networkErrors.length}`);
    
    console.log('\n=== JS ERRORS ===');
    jsErrors.forEach(e => console.log(`  - ${e}`));
    
    console.log('\n=== CRITICAL CONSOLE ERRORS ===');
    consoleMessages
      .filter(m => m.type === 'error' && !m.text.includes('googleads'))
      .forEach(m => console.log(`  - ${m.text}`));
    
    console.log('\n=== NETWORK ERRORS (non-ad) ===');
    networkErrors
      .filter(e => !e.url.includes('googleads') && !e.url.includes('doubleclick'))
      .forEach(e => console.log(`  - [${e.status}] ${e.url}`));

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    console.log('\nKeeping browser open. Press Ctrl+C to close.');
  }
})();
