const puppeteer = require('puppeteer');

/**
 * PUPPETEER DEEP TESTING - MOVIESHOWS3
 * Complementary to Playwright tests
 * Focuses on JavaScript console errors and performance
 */

async function runPuppeteerTests() {
    console.log('🔍 Starting Puppeteer Deep Testing...\n');

    const browser = await puppeteer.launch({
        headless: false,
        devtools: true,
        args: ['--start-maximized']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });

    const testResults = {
        passed: [],
        failed: [],
        warnings: [],
        consoleErrors: [],
        networkErrors: [],
        performanceMetrics: {}
    };

    // Monitor console
    page.on('console', msg => {
        const type = msg.type();
        const text = msg.text();

        if (type === 'error') {
            testResults.consoleErrors.push(text);
            console.log(`❌ [CONSOLE ERROR] ${text}`);
        } else if (type === 'warning') {
            console.log(`⚠️  [CONSOLE WARN] ${text}`);
        } else {
            console.log(`ℹ️  [CONSOLE ${type}] ${text}`);
        }
    });

    // Monitor network failures
    page.on('requestfailed', request => {
        const failure = `${request.url()} - ${request.failure().errorText}`;
        testResults.networkErrors.push(failure);
        console.log(`🌐 [NETWORK FAIL] ${failure}`);
    });

    // Monitor page errors
    page.on('pageerror', error => {
        testResults.consoleErrors.push(error.message);
        console.log(`💥 [PAGE ERROR] ${error.message}`);
    });

    try {
        console.log('📋 TEST: Loading page and measuring performance...');

        // Start performance measurement
        const startTime = Date.now();

        await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', {
            waitUntil: 'networkidle2',
            timeout: 30000
        });

        const loadTime = Date.now() - startTime;
        testResults.performanceMetrics.pageLoad = loadTime;
        console.log(`⏱️  Page loaded in ${loadTime}ms`);

        if (loadTime < 5000) {
            testResults.passed.push(`Page load time excellent: ${loadTime}ms`);
        } else if (loadTime < 10000) {
            testResults.warnings.push(`Page load time acceptable: ${loadTime}ms`);
        } else {
            testResults.failed.push(`Page load time slow: ${loadTime}ms`);
        }

        // Wait for content
        await page.waitForSelector('.video-card', { timeout: 10000 });

        console.log('\n📋 TEST: Checking for JavaScript errors...');
        await page.waitForTimeout(3000);

        // Test browse modal interactions
        console.log('\n📋 TEST: Browse modal stress test...');
        for (let i = 0; i < 3; i++) {
            await page.click('button[onclick="toggleBrowse()"]');
            await page.waitForTimeout(500);
            await page.click('.browse-close');
            await page.waitForTimeout(500);
        }
        testResults.passed.push('Browse modal open/close stress test passed');

        // Test search input
        console.log('\n📋 TEST: Search input performance...');
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        const searchInput = await page.$('#browseSearchInput');
        await searchInput.type('action', { delay: 100 });
        await page.waitForTimeout(1000);

        const resultsText = await page.$eval('#browseResultsCount', el => el.textContent);
        console.log(`Search results: ${resultsText}`);

        if (resultsText.includes('result')) {
            testResults.passed.push('Search updates results in real-time');
        }

        // Test filter combinations
        console.log('\n📋 TEST: Filter combination stress test...');
        await page.click('[data-type="movie"]');
        await page.waitForTimeout(500);

        const genreButtons = await page.$$('[data-genre]');
        if (genreButtons.length > 1) {
            await genreButtons[1].click();
            await page.waitForTimeout(500);
        }

        await page.type('#yearFrom', '2020');
        await page.type('#yearTo', '2023');
        await page.waitForTimeout(1000);

        testResults.passed.push('Multiple filters applied without errors');

        // Close browse
        await page.click('.browse-close');
        await page.waitForTimeout(500);

        // Test queue operations
        console.log('\n📋 TEST: Queue operations...');
        await page.click('button[onclick="toggleQueue()"]');
        await page.waitForTimeout(500);
        await page.click('.queue-close');
        await page.waitForTimeout(500);

        testResults.passed.push('Queue panel operations successful');

        // Test scroll behavior
        console.log('\n📋 TEST: Scroll behavior...');
        await page.evaluate(() => {
            document.getElementById('container').scrollTo({
                top: window.innerHeight * 2,
                behavior: 'smooth'
            });
        });
        await page.waitForTimeout(2000);

        testResults.passed.push('Scroll navigation successful');

        // Get performance metrics
        const metrics = await page.metrics();
        testResults.performanceMetrics.jsHeapSize = Math.round(metrics.JSHeapUsedSize / 1024 / 1024);
        testResults.performanceMetrics.domNodes = metrics.Nodes;
        testResults.performanceMetrics.jsEventListeners = metrics.JSEventListeners;

        console.log(`\n📊 Performance Metrics:`);
        console.log(`  - JS Heap Size: ${testResults.performanceMetrics.jsHeapSize} MB`);
        console.log(`  - DOM Nodes: ${testResults.performanceMetrics.domNodes}`);
        console.log(`  - Event Listeners: ${testResults.performanceMetrics.jsEventListeners}`);

        // Check for memory leaks
        if (testResults.performanceMetrics.jsHeapSize > 100) {
            testResults.warnings.push(`High memory usage: ${testResults.performanceMetrics.jsHeapSize} MB`);
        } else {
            testResults.passed.push(`Memory usage acceptable: ${testResults.performanceMetrics.jsHeapSize} MB`);
        }

        // Test rapid interactions
        console.log('\n📋 TEST: Rapid interaction stress test...');
        for (let i = 0; i < 5; i++) {
            await page.click('button[onclick="toggleBrowse()"]');
            await page.waitForTimeout(100);
            await page.click('.browse-close');
            await page.waitForTimeout(100);
        }
        testResults.passed.push('Rapid interaction test passed');

        // Final wait to catch delayed errors
        await page.waitForTimeout(2000);

    } catch (error) {
        testResults.failed.push(`Critical error: ${error.message}`);
        console.error('❌ Test error:', error);
    }

    // FINAL REPORT
    console.log('\n\n' + '='.repeat(80));
    console.log('🔍 PUPPETEER DEEP TEST RESULTS');
    console.log('='.repeat(80));

    console.log(`\n✅ PASSED (${testResults.passed.length}):`);
    testResults.passed.forEach(test => console.log(`  ✓ ${test}`));

    if (testResults.warnings.length > 0) {
        console.log(`\n⚠️  WARNINGS (${testResults.warnings.length}):`);
        testResults.warnings.forEach(test => console.log(`  ⚠ ${test}`));
    }

    if (testResults.failed.length > 0) {
        console.log(`\n❌ FAILED (${testResults.failed.length}):`);
        testResults.failed.forEach(test => console.log(`  ✗ ${test}`));
    }

    console.log(`\n💥 JavaScript/Page Errors: ${testResults.consoleErrors.length}`);
    if (testResults.consoleErrors.length > 0) {
        const uniqueErrors = [...new Set(testResults.consoleErrors)];
        uniqueErrors.forEach(error => console.log(`  ⚠️  ${error}`));
    }

    console.log(`\n🌐 Network Errors: ${testResults.networkErrors.length}`);
    if (testResults.networkErrors.length > 0) {
        const uniqueNetworkErrors = [...new Set(testResults.networkErrors)];
        uniqueNetworkErrors.forEach(error => console.log(`  ⚠️  ${error}`));
    }

    console.log('\n' + '='.repeat(80));
    console.log(`OVERALL: ${testResults.passed.length} passed, ${testResults.failed.length} failed, ${testResults.warnings.length} warnings`);
    console.log(`JS Errors: ${testResults.consoleErrors.length}, Network Errors: ${testResults.networkErrors.length}`);
    console.log('='.repeat(80) + '\n');

    await browser.close();

    return testResults;
}

// Run tests
runPuppeteerTests()
    .then(results => {
        console.log('\n✅ Puppeteer testing complete!');
        process.exit(results.failed.length > 0 || results.consoleErrors.length > 0 ? 1 : 0);
    })
    .catch(error => {
        console.error('❌ Puppeteer testing failed:', error);
        process.exit(1);
    });
