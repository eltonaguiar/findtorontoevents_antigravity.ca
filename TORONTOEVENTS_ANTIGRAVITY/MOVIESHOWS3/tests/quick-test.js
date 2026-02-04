const puppeteer = require('puppeteer');

/**
 * SIMPLE FOCUSED TEST - MOVIESHOWS3
 * Quick validation of core functionality
 */

async function runSimpleTest() {
    console.log('🚀 MOVIESHOWS3 - Quick Validation Test\n');

    const results = {
        passed: 0,
        failed: 0,
        tests: []
    };

    const browser = await puppeteer.launch({
        headless: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1920, height: 1080 });

        const consoleErrors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                consoleErrors.push(msg.text());
            }
        });

        // TEST 1: Page loads
        console.log('TEST 1: Page Load...');
        await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', {
            waitUntil: 'domcontentloaded',
            timeout: 15000
        });
        results.tests.push({ name: 'Page loads', passed: true });
        results.passed++;
        console.log('✅ Page loaded\n');

        // TEST 2: Videos exist
        console.log('TEST 2: Video Cards Exist...');
        await page.waitForSelector('.video-card', { timeout: 10000 });
        const videoCount = await page.$$eval('.video-card', cards => cards.length);
        console.log(`Found ${videoCount} video cards`);
        if (videoCount > 0) {
            results.tests.push({ name: `${videoCount} videos loaded`, passed: true });
            results.passed++;
            console.log('✅ Videos loaded\n');
        }

        // TEST 3: Browse button works
        console.log('TEST 3: Browse Modal...');
        await page.click('button[title="Browse All"]');
        await new Promise(r => setTimeout(r, 1000));
        const browseVisible = await page.$eval('#browseView', el => el.classList.contains('active'));
        if (browseVisible) {
            results.tests.push({ name: 'Browse modal opens', passed: true });
            results.passed++;
            console.log('✅ Browse modal opens\n');

            // TEST 4: Search exists
            console.log('TEST 4: Search Input...');
            const searchExists = await page.$('#browseSearchInput');
            if (searchExists) {
                results.tests.push({ name: 'Search input exists', passed: true });
                results.passed++;
                console.log('✅ Search input found\n');

                // TEST 5: Search works
                console.log('TEST 5: Search Functionality...');
                await page.type('#browseSearchInput', 'test');
                await new Promise(r => setTimeout(r, 500));
                const resultsText = await page.$eval('#browseResultsCount', el => el.textContent);
                if (resultsText.includes('result')) {
                    results.tests.push({ name: 'Search filters results', passed: true });
                    results.passed++;
                    console.log(`✅ Search works: ${resultsText}\n`);
                }
            }

            // TEST 6: Close button works
            console.log('TEST 6: Close Button...');
            await page.click('.browse-close');
            await new Promise(r => setTimeout(r, 500));
            const browseClosed = await page.$eval('#browseView', el => !el.classList.contains('active'));
            if (browseClosed) {
                results.tests.push({ name: 'Browse modal closes', passed: true });
                results.passed++;
                console.log('✅ Close button works\n');
            }
        }

        // TEST 7: Queue button works
        console.log('TEST 7: Queue Panel...');
        await page.click('button[title="My Queue"]');
        await new Promise(r => setTimeout(r, 1000));
        const queueVisible = await page.$eval('#queuePanel', el => el.classList.contains('active'));
        if (queueVisible) {
            results.tests.push({ name: 'Queue panel opens', passed: true });
            results.passed++;
            console.log('✅ Queue panel opens\n');

            // Close queue
            await page.click('.queue-close');
            await new Promise(r => setTimeout(r, 500));
        }

        // TEST 8: Sidebar actions visible
        console.log('TEST 8: Sidebar Actions...');
        const actionButtons = await page.$$('.action-btn');
        if (actionButtons.length === 3) {
            results.tests.push({ name: '3 sidebar action buttons exist', passed: true });
            results.passed++;
            console.log('✅ Sidebar actions present\n');
        }

        // TEST 9: Check for console errors
        console.log('TEST 9: JavaScript Errors...');
        if (consoleErrors.length === 0) {
            results.tests.push({ name: 'No JavaScript errors', passed: true });
            results.passed++;
            console.log('✅ No JS errors\n');
        } else {
            results.tests.push({ name: `${consoleErrors.length} JS errors found`, passed: false });
            results.failed++;
            console.log(`❌ Found ${consoleErrors.length} JS errors\n`);
            consoleErrors.slice(0, 5).forEach(err => console.log(`  - ${err}`));
        }

    } catch (error) {
        results.tests.push({ name: 'Test execution', passed: false, error: error.message });
        results.failed++;
        console.error('❌ Test failed:', error.message);
    }

    await browser.close();

    // SUMMARY
    console.log('\n' + '='.repeat(60));
    console.log('📊 TEST SUMMARY');
    console.log('='.repeat(60));
    console.log(`✅ Passed: ${results.passed}`);
    console.log(`❌ Failed: ${results.failed}`);
    console.log(`📊 Total: ${results.tests.length}`);
    console.log('='.repeat(60) + '\n');

    results.tests.forEach(test => {
        const icon = test.passed ? '✅' : '❌';
        console.log(`${icon} ${test.name}`);
    });

    console.log('\n');

    return results;
}

runSimpleTest()
    .then(results => {
        process.exit(results.failed > 0 ? 1 : 0);
    })
    .catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
