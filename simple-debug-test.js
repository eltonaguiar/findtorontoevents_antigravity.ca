/**
 * Simple manual debug mode test to check console output
 */
const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: false });  // Run in non-headless to see what happens
    const page = await browser.newPage();

    console.log('\n=== Testing MOVIESHOWS3 with ?debug=1 ===\n');

    const logs = [];
    page.on('console', msg => {
        const text = msg.text();
        logs.push({ type: msg.type(), text });
        console.log(`[${msg.type().toUpperCase()}] ${text}`);
    });

    await page.goto('https://findtorontoevents_antigravity.ca/MOVIESHOWS3/?debug=1', { waitUntil: 'networkidle', timeout: 60000 });

    // Wait a bit
    await page.waitForTimeout(10000);

    // Check DEBUG_MODE
    const debugCheck = await page.evaluate(() => {
        const urlParams = new URLSearchParams(window.location.search);
        return {
            url: window.location.href,
            searchParams: window.location.search,
            debugParam: urlParams.get('debug'),
            allMoviesExists: !!window.allMovies,
            allMoviesLength: window.allMovies?.length || 0
        };
    });

    console.log('\n=== Debug Check ===');
    console.log(JSON.stringify(debugCheck, null, 2));

    console.log(`\n=== Total Console Logs: ${logs.length} ===`);

    await page.waitForTimeout(50000);  // Keep browser open for manual inspection
    await browser.close();
})();
