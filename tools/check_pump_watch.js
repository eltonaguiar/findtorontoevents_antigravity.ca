const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  console.log('Navigating to pump-watch.html...');
  await page.goto('https://findtorontoevents.ca/findcryptopairs/pump-watch.html', {
    waitUntil: 'networkidle',
    timeout: 30000
  });
  
  // Wait for data to load
  await page.waitForTimeout(5000);
  
  // Take initial screenshot
  await page.screenshot({ path: 'pump-watch-main.png', fullPage: true });
  console.log('✓ Main view screenshot saved');
  
  // Get last scan time
  const lastScan = await page.locator('#lastScan').textContent().catch(() => 'Not found');
  console.log(`\n📅 Last Scan: ${lastScan}`);
  
  // Get stats
  const stats = {
    total: await page.locator('#sTotal').textContent().catch(() => '--'),
    high: await page.locator('#sHigh').textContent().catch(() => '--'),
    extreme: await page.locator('#sExtreme').textContent().catch(() => '--'),
    winRate: await page.locator('#sWinRate').textContent().catch(() => '--'),
    avgPnl: await page.locator('#sAvgPnl').textContent().catch(() => '--'),
    resolved: await page.locator('#sResolved').textContent().catch(() => '--'),
  };
  
  console.log('\n📊 Stats:');
  console.log(`  Total Scanned: ${stats.total}`);
  console.log(`  High (45+): ${stats.high}`);
  console.log(`  Extreme (60+): ${stats.extreme}`);
  console.log(`  Win Rate: ${stats.winRate}`);
  console.log(`  Avg P&L: ${stats.avgPnl}`);
  console.log(`  Resolved: ${stats.resolved}`);
  
  // Get pump candidates
  const picksContainer = await page.locator('#picksContainer').textContent();
  console.log(`\n🎯 Pump Candidates Tab:`);
  
  const pickCards = await page.locator('.pick-card').all();
  if (pickCards.length === 0) {
    console.log('  ' + picksContainer.trim());
  } else {
    console.log(`  Found ${pickCards.length} candidates:`);
    for (let i = 0; i < pickCards.length; i++) {
      const card = pickCards[i];
      const pair = await card.locator('.pick-pair').textContent().catch(() => '');
      const score = await card.locator('.pick-score').textContent().catch(() => '');
      const badge = await card.locator('.badge').textContent().catch(() => '');
      console.log(`  ${i + 1}. ${pair} - Score: ${score} [${badge}]`);
    }
  }
  
  // Click on Audit Log tab
  console.log('\n🔍 Switching to Audit Log tab...');
  await page.locator('.tab').filter({ hasText: 'Audit Log' }).click();
  await page.waitForTimeout(2000);
  
  // Take audit log screenshot
  await page.screenshot({ path: 'pump-watch-audit.png', fullPage: true });
  console.log('✓ Audit Log screenshot saved');
  
  // Get audit log content
  const auditContent = await page.locator('#auditContainer').textContent();
  console.log(`\n📋 Audit Log:`);
  
  const auditEntries = await page.locator('.audit-entry').all();
  if (auditEntries.length === 0) {
    console.log('  ' + auditContent.trim());
  } else {
    console.log(`  Found ${auditEntries.length} entries (showing first 15):`);
    for (let i = 0; i < Math.min(auditEntries.length, 15); i++) {
      const entry = auditEntries[i];
      const text = await entry.textContent();
      console.log(`  ${i + 1}. ${text.trim()}`);
    }
  }
  
  // Check for EST timezone indicators
  const bodyText = await page.locator('body').textContent();
  const hasEST = bodyText.includes('EST') || bodyText.includes('Eastern') || bodyText.includes('AM ') || bodyText.includes('PM ');
  console.log(`\n⏰ Timezone: ${hasEST ? 'Times appear to be in EST format (AM/PM)' : 'No clear timezone indicator'}`);
  
  await browser.close();
  console.log('\n✓ Done!');
})();
