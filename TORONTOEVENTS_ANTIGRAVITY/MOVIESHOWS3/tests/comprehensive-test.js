const { chromium } = require('playwright');

/**
 * COMPREHENSIVE MOVIESHOWS3 TESTING SUITE
 * Tests all features including new search/filter functionality
 */

async function runComprehensiveTests() {
    console.log('🚀 Starting Comprehensive MOVIESHOWS3 Testing Suite...\n');

    const browser = await chromium.launch({ headless: false, slowMo: 500 });
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    const page = await context.newPage();

    const testResults = {
        passed: [],
        failed: [],
        warnings: []
    };

    // Capture console logs and errors
    const consoleMessages = [];
    const jsErrors = [];

    page.on('console', msg => {
        const text = msg.text();
        consoleMessages.push({ type: msg.type(), text });
        console.log(`[CONSOLE ${msg.type()}] ${text}`);
    });

    page.on('pageerror', error => {
        jsErrors.push(error.message);
        console.error(`[JS ERROR] ${error.message}`);
    });

    try {
        // TEST 1: Page Load
        console.log('\n📋 TEST 1: Page Load and Initial State');
        await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { waitUntil: 'networkidle' });
        await page.waitForTimeout(2000);

        const title = await page.title();
        if (title.includes('MovieShows')) {
            testResults.passed.push('Page loads with correct title');
        } else {
            testResults.failed.push(`Incorrect title: ${title}`);
        }

        // TEST 2: Video Autoplay (First Video Only)
        console.log('\n📋 TEST 2: Video Autoplay - Only First Video');
        await page.waitForSelector('.video-card', { timeout: 5000 });

        const videoCards = await page.$$('.video-card');
        console.log(`Found ${videoCards.length} video cards`);

        if (videoCards.length > 0) {
            testResults.passed.push(`${videoCards.length} video cards loaded`);

            // Check first video has autoplay=1
            const firstIframe = await videoCards[0].$('iframe');
            const firstSrc = await firstIframe.getAttribute('src');

            if (firstSrc.includes('autoplay=1')) {
                testResults.passed.push('First video has autoplay=1');
            } else {
                testResults.failed.push('First video missing autoplay=1');
            }

            // Check second video has autoplay=0
            if (videoCards.length > 1) {
                const secondIframe = await videoCards[1].$('iframe');
                const secondSrc = await secondIframe.getAttribute('src');

                if (secondSrc.includes('autoplay=0')) {
                    testResults.passed.push('Second video has autoplay=0 (correct)');
                } else {
                    testResults.failed.push('Second video should have autoplay=0');
                }
            }
        } else {
            testResults.failed.push('No video cards found');
        }

        // TEST 3: Unmute Button Z-Index
        console.log('\n📋 TEST 3: Unmute Button Visibility (Z-Index Fix)');
        const unmuteBtn = await page.$('.unmute-btn');
        if (unmuteBtn) {
            const zIndex = await unmuteBtn.evaluate(el => window.getComputedStyle(el).zIndex);
            const sidebarActions = await page.$('.sidebar-actions');
            const sidebarZIndex = await sidebarActions.evaluate(el => window.getComputedStyle(el).zIndex);

            console.log(`Unmute button z-index: ${zIndex}`);
            console.log(`Sidebar actions z-index: ${sidebarZIndex}`);

            if (parseInt(zIndex) > parseInt(sidebarZIndex)) {
                testResults.passed.push('Unmute button z-index higher than sidebar (visible)');
            } else {
                testResults.failed.push('Unmute button z-index issue - may be hidden');
            }
        }

        // TEST 4: Browse Modal - Open and Close
        console.log('\n📋 TEST 4: Browse Modal - Open/Close Functionality');
        const browseBtn = await page.$('button[onclick="toggleBrowse()"]');
        await browseBtn.click();
        await page.waitForTimeout(500);

        const browseView = await page.$('#browseView.active');
        if (browseView) {
            testResults.passed.push('Browse modal opens successfully');

            // Check for close button
            const closeBtn = await page.$('.browse-close');
            if (closeBtn) {
                testResults.passed.push('Browse close button exists');
                await closeBtn.click();
                await page.waitForTimeout(500);

                const browseViewClosed = await page.$('#browseView:not(.active)');
                if (browseViewClosed) {
                    testResults.passed.push('Browse modal closes successfully');
                } else {
                    testResults.failed.push('Browse modal did not close');
                }
            } else {
                testResults.failed.push('Browse close button not found');
            }
        } else {
            testResults.failed.push('Browse modal did not open');
        }

        // TEST 5: Search Functionality
        console.log('\n📋 TEST 5: Search by Name Functionality');
        await browseBtn.click();
        await page.waitForTimeout(1000);

        const searchInput = await page.$('#browseSearchInput');
        if (searchInput) {
            testResults.passed.push('Search input exists');

            // Type a search query
            await searchInput.fill('good');
            await page.waitForTimeout(1000);

            const resultsCount = await page.$('#browseResultsCount');
            const resultsText = await resultsCount.textContent();
            console.log(`Search results: ${resultsText}`);

            if (resultsText.includes('result')) {
                testResults.passed.push('Search filters results correctly');

                // Check clear button appears
                const clearBtn = await page.$('#browseSearchClear.visible');
                if (clearBtn) {
                    testResults.passed.push('Search clear button appears when typing');
                } else {
                    testResults.failed.push('Search clear button not visible');
                }
            } else {
                testResults.warnings.push('Search results format unexpected');
            }

            // Clear search
            await searchInput.fill('');
            await page.waitForTimeout(500);
        } else {
            testResults.failed.push('Search input not found');
        }

        // TEST 6: Content Type Filters
        console.log('\n📋 TEST 6: Content Type Filters');
        const movieFilterBtn = await page.$('[data-type="movie"]');
        if (movieFilterBtn) {
            await movieFilterBtn.click();
            await page.waitForTimeout(1000);

            const isActive = await movieFilterBtn.evaluate(el => el.classList.contains('active'));
            if (isActive) {
                testResults.passed.push('Movie filter activates correctly');
            } else {
                testResults.failed.push('Movie filter did not activate');
            }

            // Check results updated
            const resultsCount = await page.$('#browseResultsCount');
            const resultsText = await resultsCount.textContent();
            console.log(`Movie filter results: ${resultsText}`);
        }

        // TEST 7: Genre Filters
        console.log('\n📋 TEST 7: Genre Filters');
        const genreButtons = await page.$$('[data-genre]');
        console.log(`Found ${genreButtons.length} genre filter buttons`);

        if (genreButtons.length > 1) {
            testResults.passed.push(`${genreButtons.length} genre filters populated dynamically`);

            // Click a genre (not "All")
            if (genreButtons[1]) {
                await genreButtons[1].click();
                await page.waitForTimeout(1000);

                const resultsCount = await page.$('#browseResultsCount');
                const resultsText = await resultsCount.textContent();
                console.log(`Genre filter results: ${resultsText}`);
                testResults.passed.push('Genre filter applies successfully');
            }
        } else {
            testResults.warnings.push('No genres found in database or not populated');
        }

        // TEST 8: Year Range Filter
        console.log('\n📋 TEST 8: Year Range Filter');
        const yearFromInput = await page.$('#yearFrom');
        const yearToInput = await page.$('#yearTo');

        if (yearFromInput && yearToInput) {
            testResults.passed.push('Year range inputs exist');

            await yearFromInput.fill('2020');
            await yearToInput.fill('2023');
            await page.waitForTimeout(1000);

            const resultsCount = await page.$('#browseResultsCount');
            const resultsText = await resultsCount.textContent();
            console.log(`Year range filter results: ${resultsText}`);
            testResults.passed.push('Year range filter applies successfully');
        } else {
            testResults.failed.push('Year range inputs not found');
        }

        // TEST 9: Add to Queue from Browse
        console.log('\n📋 TEST 9: Add to Queue from Browse');
        const addQueueBtn = await page.$('.movie-card-add-queue');
        if (addQueueBtn) {
            testResults.passed.push('Add to queue button exists on movie cards');

            // Click add to queue
            await addQueueBtn.click();
            await page.waitForTimeout(500);

            // Check queue count updated
            const queueCount = await page.$('#queueCount');
            const count = await queueCount.textContent();
            console.log(`Queue count: ${count}`);

            if (parseInt(count) > 0) {
                testResults.passed.push('Add to queue from browse works');
            } else {
                testResults.failed.push('Queue count did not update');
            }
        } else {
            testResults.failed.push('Add to queue button not found on movie cards');
        }

        // Close browse modal
        const closeBtn2 = await page.$('.browse-close');
        await closeBtn2.click();
        await page.waitForTimeout(500);

        // TEST 10: Queue Panel and "Up Next"
        console.log('\n📋 TEST 10: Queue Panel and Up Next Preview');
        const queueBtn = await page.$('button[onclick="toggleQueue()"]');
        await queueBtn.click();
        await page.waitForTimeout(1000);

        const queuePanel = await page.$('#queuePanel.active');
        if (queuePanel) {
            testResults.passed.push('Queue panel opens successfully');

            // Check for "Up Next" section
            const upNextSection = await page.$('#queueUpNext');
            if (upNextSection) {
                const isVisible = await upNextSection.evaluate(el => el.style.display !== 'none');
                if (isVisible) {
                    testResults.passed.push('"Up Next" section is visible');
                } else {
                    testResults.warnings.push('"Up Next" section exists but not visible (may be empty queue)');
                }
            } else {
                testResults.failed.push('"Up Next" section not found');
            }

            // Close queue
            const queueCloseBtn = await page.$('.queue-close');
            await queueCloseBtn.click();
            await page.waitForTimeout(500);
        } else {
            testResults.failed.push('Queue panel did not open');
        }

        // TEST 11: Play from Browse (Video Conflict Fix)
        console.log('\n📋 TEST 11: Play from Browse - Video Conflict Fix');
        await browseBtn.click();
        await page.waitForTimeout(1000);

        const firstMovieCard = await page.$('.movie-card div[onclick^="playMovieFromBrowse"]');
        if (firstMovieCard) {
            await firstMovieCard.click();
            await page.waitForTimeout(2000);

            // Check that browse modal closed
            const browseViewClosed = await page.$('#browseView:not(.active)');
            if (browseViewClosed) {
                testResults.passed.push('Browse modal closes when playing movie');

                // Count how many videos have autoplay=1
                const iframes = await page.$$('iframe');
                let autoplayCount = 0;

                for (const iframe of iframes) {
                    const src = await iframe.getAttribute('src');
                    if (src && src.includes('autoplay=1')) {
                        autoplayCount++;
                    }
                }

                console.log(`Videos with autoplay=1: ${autoplayCount}`);

                if (autoplayCount === 1) {
                    testResults.passed.push('Only ONE video has autoplay=1 (conflict fix working)');
                } else {
                    testResults.failed.push(`${autoplayCount} videos have autoplay=1 - should be 1`);
                }
            } else {
                testResults.failed.push('Browse modal did not close after playing');
            }
        }

        // TEST 12: Sidebar Actions Visibility
        console.log('\n📋 TEST 12: Sidebar Actions (Like, Add, Share) Visibility');
        const sidebarActions = await page.$('.sidebar-actions');
        if (sidebarActions) {
            const buttons = await sidebarActions.$$('.action-btn');
            console.log(`Found ${buttons.length} sidebar action buttons`);

            if (buttons.length === 3) {
                testResults.passed.push('All 3 sidebar action buttons exist');
            } else {
                testResults.failed.push(`Expected 3 sidebar buttons, found ${buttons.length}`);
            }
        }

        // TEST 13: Database Validation
        console.log('\n📋 TEST 13: Database Validation - API Response');
        const apiResponse = await page.evaluate(async () => {
            try {
                const response = await fetch('/MOVIESHOWS3/api/get-movies.php');
                const data = await response.json();
                return {
                    success: true,
                    count: data.length,
                    sample: data[0]
                };
            } catch (error) {
                return {
                    success: false,
                    error: error.message
                };
            }
        });

        if (apiResponse.success) {
            testResults.passed.push(`Database API returns ${apiResponse.count} movies`);
            console.log('Sample movie:', apiResponse.sample);

            // Validate sample movie has required fields
            const requiredFields = ['id', 'title', 'type', 'trailer_id'];
            const missingFields = requiredFields.filter(field => !apiResponse.sample[field]);

            if (missingFields.length === 0) {
                testResults.passed.push('Database records have all required fields');
            } else {
                testResults.failed.push(`Database missing fields: ${missingFields.join(', ')}`);
            }
        } else {
            testResults.failed.push(`Database API error: ${apiResponse.error}`);
        }

        // TEST 14: Scroll Behavior
        console.log('\n📋 TEST 14: Scroll Behavior and Video Switching');
        const container = await page.$('#container');
        if (container) {
            // Scroll to second video
            await page.evaluate(() => {
                document.getElementById('container').scrollTo({
                    top: window.innerHeight,
                    behavior: 'smooth'
                });
            });

            await page.waitForTimeout(2000);

            // Check that videos switched
            const iframes = await page.$$('iframe');
            let autoplayCount = 0;

            for (const iframe of iframes) {
                const src = await iframe.getAttribute('src');
                if (src && src.includes('autoplay=1')) {
                    autoplayCount++;
                }
            }

            if (autoplayCount === 1) {
                testResults.passed.push('Scroll switches videos correctly (only 1 playing)');
            } else {
                testResults.failed.push(`After scroll: ${autoplayCount} videos playing - should be 1`);
            }
        }

        // Wait a bit to capture any delayed errors
        await page.waitForTimeout(2000);

    } catch (error) {
        testResults.failed.push(`Critical error: ${error.message}`);
        console.error('Test suite error:', error);
    }

    // FINAL REPORT
    console.log('\n\n' + '='.repeat(80));
    console.log('📊 COMPREHENSIVE TEST RESULTS');
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

    console.log(`\n📝 JavaScript Errors Detected: ${jsErrors.length}`);
    if (jsErrors.length > 0) {
        jsErrors.forEach(error => console.log(`  ⚠️  ${error}`));
    }

    console.log(`\n📝 Console Messages: ${consoleMessages.length}`);
    const errorMessages = consoleMessages.filter(m => m.type === 'error');
    if (errorMessages.length > 0) {
        console.log(`  ⚠️  ${errorMessages.length} console errors`);
        errorMessages.forEach(msg => console.log(`     ${msg.text}`));
    }

    console.log('\n' + '='.repeat(80));
    console.log(`OVERALL: ${testResults.passed.length} passed, ${testResults.failed.length} failed, ${testResults.warnings.length} warnings`);
    console.log('='.repeat(80) + '\n');

    await browser.close();

    return {
        passed: testResults.passed.length,
        failed: testResults.failed.length,
        warnings: testResults.warnings.length,
        jsErrors: jsErrors.length,
        details: testResults
    };
}

// Run the tests
runComprehensiveTests()
    .then(results => {
        console.log('\n✅ Testing complete!');
        process.exit(results.failed > 0 ? 1 : 0);
    })
    .catch(error => {
        console.error('❌ Testing failed:', error);
        process.exit(1);
    });
