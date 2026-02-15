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
  await page.screenshot({ path: 'pump-watch-ordi-check-1-main.png', fullPage: true });
  console.log('✓ Screenshot 1: Main view saved\n');
  
  // ==========================================
  // CHECK 1: Look for ORDI/USDT in candidates
  // ==========================================
  console.log('🔍 CHECK 1: Looking for ORDI/USDT in pump candidates...\n');
  
  // First check "Data as of" timestamp
  const dataAsOfElement = await page.locator('text=/Data as of:/i').count();
  if (dataAsOfElement > 0) {
    const dataAsOfText = await page.locator('text=/Data as of:/i').first().textContent();
    console.log(`📅 Data as of: "${dataAsOfText.trim()}"`);
    const hasEST = dataAsOfText.includes('EST');
    console.log(`   EST timezone? ${hasEST ? '✅ YES' : '❌ NO'}\n`);
  }
  
  // Look for ORDI in the candidates
  const pickCards = await page.locator('.pick-card').all();
  console.log(`📊 Total pump candidates found: ${pickCards.length}\n`);
  
  let ordiFound = false;
  let ordiInfo = {};
  
  for (let i = 0; i < pickCards.length; i++) {
    const card = pickCards[i];
    const cardText = await card.textContent();
    const pairElement = await card.locator('.pick-pair').count();
    
    if (pairElement > 0) {
      const pair = await card.locator('.pick-pair').textContent();
      
      // Check for ORDI
      if (pair.includes('ORDI')) {
        ordiFound = true;
        const score = await card.locator('.pick-score').textContent().catch(() => 'N/A');
        const badge = await card.locator('.badge').textContent().catch(() => '');
        
        ordiInfo = {
          position: i + 1,
          pair: pair.trim(),
          score: score.trim(),
          badge: badge.trim()
        };
        
        console.log(`✅ ORDI FOUND at position #${i + 1}!`);
        console.log(`   Pair: ${ordiInfo.pair}`);
        console.log(`   Score: ${ordiInfo.score}`);
        console.log(`   Badge: ${ordiInfo.badge}`);
        
        // Get more details from the card
        const thesis = await card.locator('.thesis').textContent().catch(() => '');
        if (thesis) {
          console.log(`   Thesis: ${thesis.trim().substring(0, 150)}...`);
        }
        console.log();
      }
    }
  }
  
  if (!ordiFound) {
    console.log('❌ ORDI/USDT NOT FOUND in the current pump candidates list\n');
    // List top 10 candidates instead
    console.log('📋 Top 10 candidates currently shown:');
    for (let i = 0; i < Math.min(10, pickCards.length); i++) {
      const card = pickCards[i];
      const pair = await card.locator('.pick-pair').textContent().catch(() => 'Unknown');
      const score = await card.locator('.pick-score').textContent().catch(() => 'N/A');
      console.log(`   ${i + 1}. ${pair.trim()} - Score: ${score.trim()}`);
    }
    console.log();
  }
  
  // ==========================================
  // CHECK 2: Click Audit Log and look for KuCoin entries
  // ==========================================
  console.log('🔍 CHECK 2: Clicking "Audit Log" tab to check for KuCoin entries...\n');
  
  const auditTab = page.locator('.tab').filter({ hasText: 'Audit Log' });
  const auditTabCount = await auditTab.count();
  
  if (auditTabCount > 0) {
    await auditTab.click();
    await page.waitForTimeout(2000);
    
    // Take screenshot of audit log
    await page.screenshot({ path: 'pump-watch-ordi-check-2-audit.png', fullPage: true });
    console.log('✓ Screenshot 2: Audit Log view saved\n');
    
    // Check for EST note
    const estNote = await page.locator('text=/All times shown in Eastern Standard Time/i').count();
    console.log(`📅 "All times shown in Eastern Standard Time (EST)" note? ${estNote > 0 ? '✅ YES' : '❌ NO'}\n`);
    
    // Get all audit log text to search for KuCoin-related entries
    const auditContent = await page.locator('#auditContainer').textContent();
    
    // Search for EXTRA_SCAN and EXTRA_DONE
    const hasExtraScan = auditContent.includes('EXTRA_SCAN');
    const hasExtraDone = auditContent.includes('EXTRA_DONE');
    const hasKuCoin = auditContent.includes('KuCoin') || auditContent.includes('kucoin') || auditContent.includes('KUCOIN');
    const hasORDI = auditContent.includes('ORDI');
    
    console.log('🔎 Searching audit log for KuCoin-related entries:');
    console.log(`   Contains "EXTRA_SCAN"? ${hasExtraScan ? '✅ YES' : '❌ NO'}`);
    console.log(`   Contains "EXTRA_DONE"? ${hasExtraDone ? '✅ YES' : '❌ NO'}`);
    console.log(`   Contains "KuCoin"? ${hasKuCoin ? '✅ YES' : '❌ NO'}`);
    console.log(`   Contains "ORDI"? ${hasORDI ? '✅ YES' : '❌ NO'}\n`);
    
    // Extract specific entries
    const auditEntries = await page.locator('.audit-entry').all();
    console.log(`📋 Total audit log entries: ${auditEntries.length}\n`);
    
    if (hasExtraScan || hasExtraDone || hasKuCoin || hasORDI) {
      console.log('🎯 KuCoin/ORDI-related audit log entries:\n');
      
      let foundCount = 0;
      for (let i = 0; i < auditEntries.length; i++) {
        const entry = auditEntries[i];
        const text = await entry.textContent();
        
        if (text.includes('EXTRA_SCAN') || text.includes('EXTRA_DONE') || 
            text.includes('KuCoin') || text.includes('kucoin') || 
            text.includes('ORDI')) {
          foundCount++;
          console.log(`   Entry ${i + 1}: ${text.trim()}`);
          
          if (foundCount >= 20) {
            console.log(`   ... (showing first 20 matches, more may exist)\n`);
            break;
          }
        }
      }
      
      if (foundCount === 0) {
        console.log('   (Keywords found in audit log text but no matching entries extracted - may be in combined text)\n');
      } else {
        console.log();
      }
    } else {
      console.log('ℹ️  No EXTRA_SCAN, EXTRA_DONE, KuCoin, or ORDI entries found in audit log\n');
      console.log('📋 Showing first 5 recent audit entries instead:\n');
      for (let i = 0; i < Math.min(5, auditEntries.length); i++) {
        const entry = auditEntries[i];
        const text = await entry.textContent();
        console.log(`   ${i + 1}. ${text.trim()}`);
      }
      console.log();
    }
    
    // Check timestamps in audit log for EST
    if (auditEntries.length > 0) {
      const sampleEntry = await auditEntries[0].textContent();
      const hasESTInEntry = sampleEntry.includes('EST');
      console.log(`📅 First audit entry contains "EST"? ${hasESTInEntry ? '✅ YES' : '❌ NO'}`);
      if (hasESTInEntry) {
        console.log(`   Sample: ${sampleEntry.trim().substring(0, 100)}...\n`);
      }
    }
  } else {
    console.log('❌ Audit Log tab not found\n');
  }
  
  // ==========================================
  // CHECK 3: List other potential KuCoin pairs
  // ==========================================
  console.log('🔍 CHECK 3: Looking for other potential KuCoin-sourced pairs...\n');
  
  // Go back to candidates tab
  const candidatesTab = page.locator('.tab').filter({ hasText: 'Pump Candidates' });
  if (await candidatesTab.count() > 0) {
    await candidatesTab.click();
    await page.waitForTimeout(1000);
  }
  
  // List all pairs to identify potential KuCoin pairs
  const allPairs = [];
  for (let i = 0; i < Math.min(20, pickCards.length); i++) {
    const card = pickCards[i];
    const pair = await card.locator('.pick-pair').textContent().catch(() => '');
    const score = await card.locator('.pick-score').textContent().catch(() => '');
    if (pair) {
      allPairs.push(`${pair.trim()} (${score.trim()})`);
    }
  }
  
  console.log('📊 Top 20 pump candidates (potential KuCoin pairs highlighted):\n');
  allPairs.forEach((pair, idx) => {
    // Highlight ORDI and other potential KuCoin-exclusive pairs
    const isKuCoinLikely = pair.includes('ORDI') || pair.includes('STABLE') || 
                           pair.includes('TGBP') || pair.includes('EURC');
    const marker = isKuCoinLikely ? '⭐' : '  ';
    console.log(`   ${marker} ${idx + 1}. ${pair}`);
  });
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
