const { chromium } = require('playwright');

const sites = [
  { name: 'findtorontoevents.ca', url: 'https://findtorontoevents.ca' },
  { name: 'torontoevent.net', url: 'https://torontoevent.net' },
  { name: 'tdotevent.ca', url: 'https://tdotevent.ca' },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  
  for (const site of sites) {
    console.log(`\n=== ${site.name} ===`);
    const page = await browser.newPage();
    const errors = [];
    
    page.on('pageerror', (err) => {
      if (/Minified React error #418/.test(err.message)) return;
      errors.push(`PageError: ${err.message.substring(0, 100)}`);
    });
    
    // Test 1: Homepage loads
    try {
      const resp = await page.goto(site.url + '/index.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
      console.log(`  [1] Homepage: HTTP ${resp.status()}`);
    } catch (e) {
      console.log(`  [1] Homepage: FAIL - ${e.message.substring(0, 80)}`);
    }
    
    await page.waitForTimeout(6000);
    
    // Test 2: Ghost card check
    const ghostResult = await page.evaluate(() => {
      const hidden = document.querySelectorAll('.event-card-hidden');
      let ghostCount = 0;
      for (const h of hidden) {
        const g = h.closest('.group');
        if (g && window.getComputedStyle(g).display !== 'none') ghostCount++;
      }
      const visible = document.querySelectorAll('[role="button"][aria-label*="View details"]:not(.event-card-hidden)');
      return { hidden: hidden.length, ghosts: ghostCount, visible: visible.length };
    });
    console.log(`  [2] Ghost cards: ${ghostResult.ghosts === 0 ? 'PASS' : 'FAIL'} (visible=${ghostResult.visible}, hidden=${ghostResult.hidden}, ghosts=${ghostResult.ghosts})`);
    
    // Test 3: CSS fix present
    const hasCSSFix = await page.evaluate(() => {
      return document.documentElement.innerHTML.includes('group:has');
    });
    console.log(`  [3] CSS :has() fix: ${hasCSSFix ? 'PRESENT' : 'MISSING'}`);
    
    // Test 4: JS fix present
    const hasJSFix = await page.evaluate(() => {
      return document.documentElement.innerHTML.includes('gridItem.style.display');
    });
    console.log(`  [4] JS grid fix: ${hasJSFix ? 'PRESENT' : 'MISSING'}`);
    
    // Test 5: JS errors
    console.log(`  [5] JS errors: ${errors.length === 0 ? 'PASS (0 errors)' : `FAIL (${errors.length} errors)`}`);
    errors.forEach(e => console.log(`       - ${e}`));
    
    // Test 6: Updates page
    try {
      const updResp = await page.goto(site.url + '/updates/', { waitUntil: 'domcontentloaded', timeout: 20000 });
      await page.waitForTimeout(1000);
      
      const hasGhostDoc = await page.evaluate(() => {
        return document.body.innerText.includes('Ghost Event Cards');
      });
      const hasThumbnailDoc = await page.evaluate(() => {
        return document.body.innerText.includes('Full-Width Event Thumbnails');
      });
      console.log(`  [6] Updates page: HTTP ${updResp.status()}`);
      console.log(`       Ghost card doc: ${hasGhostDoc ? 'PRESENT' : 'MISSING'}`);
      console.log(`       Thumbnail doc: ${hasThumbnailDoc ? 'PRESENT' : 'MISSING'}`);
    } catch (e) {
      console.log(`  [6] Updates page: FAIL - ${e.message.substring(0, 80)}`);
    }
    
    const passed = ghostResult.ghosts === 0 && hasCSSFix && hasJSFix && errors.length === 0;
    results.push({ site: site.name, passed });
    
    await page.close();
  }
  
  await browser.close();
  
  console.log('\n' + '='.repeat(50));
  console.log('FINAL RESULTS');
  console.log('='.repeat(50));
  results.forEach(r => {
    console.log(`  ${r.site}: ${r.passed ? 'ALL PASS' : 'ISSUES FOUND'}`);
  });
  
  const allPassed = results.every(r => r.passed);
  process.exit(allPassed ? 0 : 1);
})();
