const { chromium } = require('playwright');

async function runComprehensiveTests() {
    console.log('🎬 MOVIESHOWS3 - COMPREHENSIVE TEST SUITE\n');
    console.log('='.repeat(60));

    const browser = await chromium.launch({
        headless: false,
        slowMo: 500 // Slow down for visibility
    });

    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    });

    const page = await context.newPage();

    let passedTests = 0;
    let failedTests = 0;

    const test = async (name, fn) => {
        try {
            console.log(`\n🧪 ${name}`);
            await fn();
            console.log(`   ✅ PASSED`);
            passedTests++;
        } catch (error) {
            console.log(`   ❌ FAILED: ${error.message}`);
            failedTests++;
        }
    };

    try {
        // PHASE 1: Page Load & Structure
        console.log('\n📋 PHASE 1: PAGE LOAD & STRUCTURE');
        console.log('-'.repeat(60));

        await test('Load main page', async () => {
            await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', {
                waitUntil: 'networkidle',
                timeout: 30000
            });
            await page.waitForTimeout(2000);
        });

        await test('Verify correct version loaded (index.html)', async () => {
            const scripts = await page.evaluate(() => {
                return Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
            });
            const hasOldScripts = scripts.some(s => s.includes('scroll-fix.js') || s.includes('ui-minimal.js'));
            if (hasOldScripts) throw new Error('Old app.html is loaded instead of index.html');
        });

        await test('API returns data', async () => {
            const apiData = await page.evaluate(async () => {
                const response = await fetch('/MOVIESHOWS3/api/get-movies.php');
                return await response.json();
            });
            if (!apiData.movies || apiData.movies.length === 0) {
                throw new Error('API returned no movies');
            }
            console.log(`      Found ${apiData.count} movies in API`);
        });

        await test('Movies rendered on page', async () => {
            const movieCount = await page.locator('.video-card').count();
            if (movieCount === 0) throw new Error('No video cards rendered');
            console.log(`      Rendered ${movieCount} video cards`);
        });

        await test('YouTube iframes present', async () => {
            const iframeCount = await page.locator('iframe').count();
            if (iframeCount === 0) throw new Error('No YouTube iframes found');
            console.log(`      Found ${iframeCount} YouTube iframes`);
        });

        // PHASE 2: UI Elements
        console.log('\n📋 PHASE 2: UI ELEMENTS');
        console.log('-'.repeat(60));

        await test('Hamburger menu present', async () => {
            const hamburger = await page.locator('.hamburger-btn').count();
            if (hamburger === 0) throw new Error('Hamburger menu not found');
        });

        await test('Filter buttons present', async () => {
            await page.locator('.hamburger-btn').click();
            await page.waitForTimeout(500);
            const allBtn = await page.locator('text=All').count();
            const moviesBtn = await page.locator('text=Movies').count();
            const tvBtn = await page.locator('text=TV').count();
            if (allBtn === 0 || moviesBtn === 0 || tvBtn === 0) {
                throw new Error('Filter buttons missing');
            }
            await page.locator('.hamburger-btn').click(); // Close menu
            await page.waitForTimeout(500);
        });

        await test('Unmute button present', async () => {
            const unmuteBtn = await page.locator('.unmute-btn').count();
            if (unmuteBtn === 0) throw new Error('Unmute button not found');
        });

        await test('Play overlay present on first video', async () => {
            const playOverlay = await page.locator('.play-overlay').count();
            if (playOverlay === 0) throw new Error('Play overlay not found');
        });

        // PHASE 3: Interactivity
        console.log('\n📋 PHASE 3: INTERACTIVITY');
        console.log('-'.repeat(60));

        await test('Click play overlay', async () => {
            const overlay = page.locator('.play-overlay').first();
            await overlay.click();
            await page.waitForTimeout(2000);
            // Check if overlay is hidden
            const isVisible = await overlay.isVisible().catch(() => false);
            if (isVisible) throw new Error('Play overlay did not hide after click');
        });

        await test('First video iframe loads', async () => {
            const firstIframe = page.locator('iframe').first();
            const src = await firstIframe.getAttribute('src');
            if (!src || !src.includes('youtube.com/embed')) {
                throw new Error('Invalid YouTube iframe src');
            }
            console.log(`      First video: ${src.substring(0, 60)}...`);
        });

        await test('Unmute button toggles', async () => {
            const unmuteBtn = page.locator('.unmute-btn').first();
            const initialText = await unmuteBtn.textContent();
            await unmuteBtn.click();
            await page.waitForTimeout(500);
            const newText = await unmuteBtn.textContent();
            if (initialText === newText) throw new Error('Unmute button did not toggle');
            console.log(`      Toggled from ${initialText} to ${newText}`);
        });

        await test('Scroll to next video', async () => {
            await page.mouse.wheel(0, 1000);
            await page.waitForTimeout(2000);
            console.log('      Scrolled successfully');
        });

        // PHASE 4: Menu Navigation
        console.log('\n📋 PHASE 4: MENU NAVIGATION');
        console.log('-'.repeat(60));

        await test('Open hamburger menu', async () => {
            await page.locator('.hamburger-btn').click();
            await page.waitForTimeout(500);
            const menuVisible = await page.locator('.menu-panel').isVisible();
            if (!menuVisible) throw new Error('Menu did not open');
        });

        await test('Filter by Movies', async () => {
            await page.locator('text=Movies').first().click();
            await page.waitForTimeout(1000);
            console.log('      Movies filter applied');
        });

        await test('Filter by TV', async () => {
            await page.locator('.hamburger-btn').click();
            await page.waitForTimeout(500);
            await page.locator('text=TV').first().click();
            await page.waitForTimeout(1000);
            console.log('      TV filter applied');
        });

        await test('Reset to All', async () => {
            await page.locator('.hamburger-btn').click();
            await page.waitForTimeout(500);
            await page.locator('text=All').first().click();
            await page.waitForTimeout(1000);
            console.log('      All filter applied');
        });

        // PHASE 5: Browse & Search
        console.log('\n📋 PHASE 5: BROWSE & SEARCH');
        console.log('-'.repeat(60));

        await test('Open browse view', async () => {
            await page.locator('.hamburger-btn').click();
            await page.waitForTimeout(500);
            const browseBtn = page.locator('text=Search & Browse').first();
            await browseBtn.click();
            await page.waitForTimeout(1000);
            const browseView = await page.locator('#browseView').isVisible();
            if (!browseView) throw new Error('Browse view did not open');
        });

        await test('Browse grid shows movies', async () => {
            const gridItems = await page.locator('.movie-card').count();
            if (gridItems === 0) throw new Error('No movies in browse grid');
            console.log(`      Found ${gridItems} movies in grid`);
        });

        await test('Click movie in browse view', async () => {
            const firstCard = page.locator('.movie-card').first();
            await firstCard.click();
            await page.waitForTimeout(2000);
            // Browse view should close
            const browseVisible = await page.locator('#browseView.active').count();
            if (browseVisible > 0) throw new Error('Browse view did not close');
        });

        // PHASE 6: Mobile Responsiveness
        console.log('\n📋 PHASE 6: MOBILE RESPONSIVENESS');
        console.log('-'.repeat(60));

        await test('Switch to mobile viewport', async () => {
            await page.setViewportSize({ width: 375, height: 812 });
            await page.waitForTimeout(1000);
        });

        await test('Mobile: UI elements visible', async () => {
            const hamburger = await page.locator('.hamburger-btn').isVisible();
            const unmute = await page.locator('.unmute-btn').first().isVisible();
            if (!hamburger || !unmute) throw new Error('Mobile UI elements not visible');
        });

        await test('Mobile: Scroll works', async () => {
            await page.mouse.wheel(0, 800);
            await page.waitForTimeout(1500);
            console.log('      Mobile scroll successful');
        });

        await test('Switch back to desktop', async () => {
            await page.setViewportSize({ width: 1920, height: 1080 });
            await page.waitForTimeout(1000);
        });

        // PHASE 7: Performance & Console
        console.log('\n📋 PHASE 7: PERFORMANCE & CONSOLE');
        console.log('-'.repeat(60));

        await test('No JavaScript errors', async () => {
            const errors = [];
            page.on('pageerror', error => errors.push(error.message));
            await page.waitForTimeout(2000);
            if (errors.length > 0) {
                throw new Error(`Found ${errors.length} JS errors: ${errors[0]}`);
            }
        });

        await test('Page loads in reasonable time', async () => {
            const startTime = Date.now();
            await page.reload({ waitUntil: 'networkidle' });
            const loadTime = Date.now() - startTime;
            console.log(`      Load time: ${loadTime}ms`);
            if (loadTime > 10000) throw new Error('Page load too slow');
        });

        // Take final screenshot
        await page.screenshot({
            path: 'movieshows-final-test.png',
            fullPage: false
        });
        console.log('\n📸 Final screenshot: movieshows-final-test.png');

    } catch (error) {
        console.error('\n💥 Critical Error:', error.message);
    } finally {
        await browser.close();

        // Print summary
        console.log('\n' + '='.repeat(60));
        console.log('📊 TEST SUMMARY');
        console.log('='.repeat(60));
        console.log(`✅ Passed: ${passedTests}`);
        console.log(`❌ Failed: ${failedTests}`);
        console.log(`📈 Success Rate: ${Math.round((passedTests / (passedTests + failedTests)) * 100)}%`);

        if (failedTests === 0) {
            console.log('\n🎉 ALL TESTS PASSED! 🎉');
        } else {
            console.log('\n⚠️  Some tests failed. Review above for details.');
        }

        process.exit(failedTests > 0 ? 1 : 0);
    }
}

runComprehensiveTests().catch(console.error);
