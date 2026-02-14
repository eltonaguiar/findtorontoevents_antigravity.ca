const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Capture console errors
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  
  // Capture JS errors
  const jsErrors = [];
  page.on('pageerror', err => {
    jsErrors.push(err.message);
  });
  
  console.log('🌐 Navigating to pump-watch.html...\n');
  await page.goto('https://findtorontoevents.ca/findcryptopairs/pump-watch.html', {
    waitUntil: 'networkidle',
    timeout: 30000
  });
  
  // Wait for content to load
  await page.waitForTimeout(5000);
  
  // Take initial screenshot
  await page.screenshot({ path: 'pump-watch-check-1-main.png', fullPage: true });
  console.log('✓ Screenshot 1: Main view saved\n');
  
  // ==========================================
  // CHECK 1: "Data as of: [datetime] EST" bar
  // ==========================================
  console.log('📋 CHECK 1: Looking for "Data as of: [datetime] EST" bar near top...');
  const dataAsOfBar = await page.locator('text=/Data as of:/i').count();
  if (dataAsOfBar > 0) {
    const dataAsOfText = await page.locator('text=/Data as of:/i').first().textContent();
    console.log(`  ✅ FOUND: "${dataAsOfText.trim()}"`);
  } else {
    console.log('  ❌ NOT FOUND: No "Data as of:" bar visible');
  }
  console.log();
  
  // ==========================================
  // CHECK 2: "Last scan" line in header with EST
  // ==========================================
  console.log('📋 CHECK 2: Checking "Last scan" line in header...');
  const lastScanElement = await page.locator('#lastScan').count();
  if (lastScanElement > 0) {
    const lastScanText = await page.locator('#lastScan').textContent();
    const hasEST = lastScanText.includes('EST');
    const hasFullDate = /\d{4}-\d{2}-\d{2}/.test(lastScanText);
    console.log(`  Text: "${lastScanText.trim()}"`);
    console.log(`  ✓ Has full date (YYYY-MM-DD)? ${hasFullDate ? 'YES' : 'NO'}`);
    console.log(`  ✓ Contains "EST"? ${hasEST ? 'YES' : 'NO'}`);
  } else {
    // Check for any element containing "last scan"
    const altLastScan = await page.locator('text=/last scan/i').count();
    if (altLastScan > 0) {
      const text = await page.locator('text=/last scan/i').first().textContent();
      console.log(`  Found: "${text.trim()}"`);
    } else {
      console.log('  ❌ NOT FOUND: No "Last scan" element');
    }
  }
  console.log();
  
  // ==========================================
  // CHECK 3: Pump candidate cards show dates with EST
  // ==========================================
  console.log('📋 CHECK 3: Checking pump candidate cards for dates with EST...');
  const pickCards = await page.locator('.pick-card').count();
  if (pickCards > 0) {
    console.log(`  Found ${pickCards} candidate cards`);
    // Check first 3 cards for date/time information
    for (let i = 0; i < Math.min(3, pickCards); i++) {
      const card = page.locator('.pick-card').nth(i);
      const cardText = await card.textContent();
      const pair = await card.locator('.pick-pair').textContent().catch(() => 'Unknown');
      const hasEST = cardText.includes('EST');
      const hasDate = /\d{4}-\d{2}-\d{2}/.test(cardText) || /\w{3}\s+\d+/.test(cardText);
      console.log(`  Card ${i + 1} (${pair}): Date? ${hasDate ? 'YES' : 'NO'}, EST? ${hasEST ? 'YES' : 'NO'}`);
      if (hasDate || hasEST) {
        // Extract the date/time portion
        const dateMatch = cardText.match(/(\d{4}-\d{2}-\d{2}[^|]*)/);
        if (dateMatch) console.log(`    → "${dateMatch[1].trim()}"`);
      }
    }
  } else {
    console.log('  ❌ No candidate cards found');
  }
  console.log();
  
  // ==========================================
  // CHECK 4: "Scan ORDI + Extras" button
  // ==========================================
  console.log('📋 CHECK 4: Looking for "Scan ORDI + Extras" button...');
  const ordiButton = await page.locator('button:has-text("Scan ORDI + Extras")').count();
  if (ordiButton > 0) {
    console.log('  ✅ FOUND: "Scan ORDI + Extras" button exists');
  } else {
    // Check for any button containing "ORDI"
    const anyOrdiButton = await page.locator('button:has-text("ORDI")').count();
    if (anyOrdiButton > 0) {
      const btnText = await page.locator('button:has-text("ORDI")').first().textContent();
      console.log(`  ⚠️  Found button with ORDI: "${btnText.trim()}"`);
    } else {
      console.log('  ❌ NOT FOUND: No "Scan ORDI + Extras" button');
    }
  }
  console.log();
  
  // ==========================================
  // CHECK 5: Click Audit Log tab and check timestamps
  // ==========================================
  console.log('📋 CHECK 5: Clicking "Audit Log" tab...');
  const auditTab = page.locator('.tab').filter({ hasText: 'Audit Log' });
  const auditTabCount = await auditTab.count();
  
  if (auditTabCount > 0) {
    await auditTab.click();
    await page.waitForTimeout(2000);
    
    // Take screenshot of audit log
    await page.screenshot({ path: 'pump-watch-check-2-audit.png', fullPage: true });
    console.log('  ✓ Screenshot 2: Audit Log view saved');
    
    // Check for EST note
    const estNote = await page.locator('text=/All times shown in Eastern Standard Time/i').count();
    console.log(`  ✓ "All times shown in Eastern Standard Time (EST)" note? ${estNote > 0 ? 'YES ✅' : 'NO ❌'}`);
    
    // Check audit log entries for EST format
    const auditEntries = await page.locator('.audit-entry').count();
    if (auditEntries > 0) {
      console.log(`  Found ${auditEntries} audit log entries`);
      // Check first 3 entries
      for (let i = 0; i < Math.min(3, auditEntries); i++) {
        const entry = page.locator('.audit-entry').nth(i);
        const text = await entry.textContent();
        const hasEST = text.includes('EST');
        const hasFullDate = /\d{4}-\d{2}-\d{2}/.test(text);
        console.log(`  Entry ${i + 1}:`);
        console.log(`    Full date? ${hasFullDate ? 'YES' : 'NO'}, EST? ${hasEST ? 'YES' : 'NO'}`);
        console.log(`    → "${text.trim().substring(0, 100)}..."`);
      }
    } else {
      const auditContent = await page.locator('#auditContainer').textContent();
      console.log(`  Audit log content: "${auditContent.trim().substring(0, 150)}"`);
    }
  } else {
    console.log('  ❌ Audit Log tab not found');
  }
  console.log();
  
  // ==========================================
  // JS/Console Errors Summary
  // ==========================================
  console.log('🐛 JAVASCRIPT ERRORS CHECK:');
  if (jsErrors.length > 0) {
    console.log(`  ❌ Found ${jsErrors.length} JS error(s):`);
    jsErrors.forEach((err, i) => console.log(`    ${i + 1}. ${err}`));
  } else {
    console.log('  ✅ No JS errors detected');
  }
  console.log();
  
  console.log('📢 CONSOLE ERRORS CHECK:');
  if (consoleErrors.length > 0) {
    console.log(`  ⚠️  Found ${consoleErrors.length} console error(s):`);
    consoleErrors.forEach((err, i) => console.log(`    ${i + 1}. ${err}`));
  } else {
    console.log('  ✅ No console errors detected');
  }
  
  await browser.close();
  console.log('\n✅ All checks complete!');
})();
