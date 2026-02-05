const puppeteer = require('puppeteer');

(async () => {
    console.log('\n=== COMPREHENSIVE BRUNITARTE VERIFICATION ===\n');

    const browser = await puppeteer.launch({
        headless: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Track all console messages
    const consoleLogs = [];
    page.on('console', msg => {
        const text = msg.text();
        consoleLogs.push(text);
        if (text.includes('Loaded creators from DB') || text.includes('BRUNITARTE') || text.includes('creator')) {
            console.log(`[CONSOLE] ${text}`);
        }
    });

    // Track all network requests
    const apiCalls = [];
    page.on('response', async response => {
        const url = response.url();
        if (url.includes('get_my_creators.php')) {
            try {
                const text = await response.text();
                const data = JSON.parse(text);
                apiCalls.push({
                    url,
                    status: response.status(),
                    creatorCount: data.creators?.length || 0,
                    hasBrunitarte: data.creators?.some(c => c.name === 'Brunitarte') || false,
                    creators: data.creators?.map(c => c.name) || []
                });

                console.log(`\n[API CALL] ${url}`);
                console.log(`  Status: ${response.status()}`);
                console.log(`  Creators: ${data.creators?.length || 0}`);
                console.log(`  Has Brunitarte: ${data.creators?.some(c => c.name === 'Brunitarte')}`);
            } catch (e) {
                console.log(`[API ERROR] Failed to parse response: ${e.message}`);
            }
        }
    });

    // Step 1: Navigate and clear cache
    console.log('\n[STEP 1] Navigating to site...');
    await page.goto('https://findtorontoevents.ca/fc/', { waitUntil: 'networkidle2' });

    console.log('[STEP 2] Clearing localStorage...');
    await page.evaluate(() => {
        localStorage.clear();
        sessionStorage.clear();
    });

    console.log('[STEP 3] Reloading page...');
    await page.reload({ waitUntil: 'networkidle2' });

    // Wait for page to load
    await page.waitForTimeout(8000);

    // Step 4: Check guest view
    console.log('\n[STEP 4] Checking guest view...');
    const guestCreatorCount = await page.$$eval('tr[data-creator-id]', rows => rows.length);
    console.log(`  Visible creators (guest): ${guestCreatorCount}`);

    const guestHasBrunitarte = await page.evaluate(() => {
        return document.body.textContent.includes('Brunitarte');
    });
    console.log(`  Guest has Brunitarte: ${guestHasBrunitarte}`);

    // Take screenshot
    await page.screenshot({ path: 'e:/findtorontoevents_antigravity.ca/guest-view.png', fullPage: true });

    // Step 5: Check what API calls were made
    console.log('\n[STEP 5] API Calls Summary:');
    apiCalls.forEach((call, i) => {
        console.log(`  Call ${i + 1}:`);
        console.log(`    URL: ${call.url}`);
        console.log(`    Creators: ${call.creatorCount}`);
        console.log(`    Has Brunitarte: ${call.hasBrunitarte}`);
    });

    // Step 6: Check console logs
    console.log('\n[STEP 6] Relevant Console Logs:');
    const relevantLogs = consoleLogs.filter(log =>
        log.includes('Loaded creators') ||
        log.includes('creator') ||
        log.includes('Brunitarte')
    );
    relevantLogs.forEach(log => console.log(`  ${log}`));

    // Step 7: Final summary
    console.log('\n=== SUMMARY ===');
    console.log(`Guest view creators: ${guestCreatorCount} (expected: 12)`);
    console.log(`Guest has Brunitarte: ${guestHasBrunitarte} (expected: false)`);
    console.log(`API calls made: ${apiCalls.length}`);

    if (apiCalls.length > 0) {
        const lastCall = apiCalls[apiCalls.length - 1];
        console.log(`Last API call returned: ${lastCall.creatorCount} creators`);
        console.log(`Last API call has Brunitarte: ${lastCall.hasBrunitarte}`);
    }

    console.log('\n✅ Test complete. Check guest-view.png screenshot.');
    console.log('\nPress Ctrl+C to close browser...');

    // Keep browser open for manual inspection
    await page.waitForTimeout(60000);

    await browser.close();
})();
