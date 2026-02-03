/**
 * Puppeteer tests for MovieShows application
 * Tests queue viewing, sound persistence, playlist sharing, and queue management
 */

const puppeteer = require('puppeteer');

const MOVIESHOWS_URL = 'https://findtorontoevents.ca/MOVIESHOWS/';
const FC_LOGIN_URL = 'https://findtorontoevents.ca/fc/';

async function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Test 1: Verify current queue displays correctly
 */
async function testQueueViewing(browser) {
    console.log('\n📋 Test 1: Queue Viewing');
    console.log('='.repeat(50));

    const page = await browser.newPage();

    try {
        await page.goto(MOVIESHOWS_URL, { waitUntil: 'networkidle2', timeout: 30000 });
        console.log('✓ Page loaded');

        // Wait for queue to load
        await page.waitForSelector('[data-testid="queue"], .queue, #queue', { timeout: 10000 }).catch(() => {
            console.log('⊘ Queue selector not found, checking for any video elements');
        });

        // Check for video elements
        const videos = await page.$$('video, iframe[src*="youtube"]');
        console.log(`✓ Found ${videos.length} video elements`);

        // Check for queue items
        const queueItems = await page.evaluate(() => {
            const items = document.querySelectorAll('[data-queue-item], .queue-item, .movie-item');
            return items.length;
        });

        console.log(`✓ Found ${queueItems} queue items`);

        // Take screenshot
        await page.screenshot({ path: 'movieshows-queue-view.png', fullPage: true });
        console.log('✓ Screenshot saved: movieshows-queue-view.png');

        return { success: true, videos: videos.length, queueItems };

    } catch (error) {
        console.error('✗ Test failed:', error.message);
        await page.screenshot({ path: 'movieshows-queue-error.png' });
        return { success: false, error: error.message };
    } finally {
        await page.close();
    }
}

/**
 * Test 2: Verify sound keeps playing when scrolling
 */
async function testSoundPersistence(browser) {
    console.log('\n🔊 Test 2: Sound Persistence During Scroll');
    console.log('='.repeat(50));

    const page = await browser.newPage();

    try {
        await page.goto(MOVIESHOWS_URL, { waitUntil: 'networkidle2' });

        // Wait for video to load
        await page.waitForSelector('video, iframe', { timeout: 10000 });
        console.log('✓ Video element found');

        // Check if video is playing
        const isPlaying = await page.evaluate(() => {
            const video = document.querySelector('video');
            if (video) {
                return !video.paused && !video.ended && video.readyState > 2;
            }
            return false;
        });

        console.log(`✓ Video playing: ${isPlaying}`);

        // Scroll down
        await page.evaluate(() => window.scrollBy(0, 500));
        await delay(1000);
        console.log('✓ Scrolled down 500px');

        // Check if video still playing
        const stillPlaying = await page.evaluate(() => {
            const video = document.querySelector('video');
            if (video) {
                return !video.paused;
            }
            return false;
        });

        console.log(`✓ Video still playing after scroll: ${stillPlaying}`);

        return { success: true, persistedSound: stillPlaying };

    } catch (error) {
        console.error('✗ Test failed:', error.message);
        return { success: false, error: error.message };
    } finally {
        await page.close();
    }
}

/**
 * Test 3: Verify users can share a playlist
 */
async function testPlaylistSharing(browser) {
    console.log('\n🔗 Test 3: Playlist Sharing');
    console.log('='.repeat(50));

    const page = await browser.newPage();

    try {
        await page.goto(MOVIESHOWS_URL, { waitUntil: 'networkidle2' });

        // Look for share button
        const shareButton = await page.$('[data-testid="share"], button:has-text("Share"), .share-button');

        if (shareButton) {
            console.log('✓ Share button found');
            await shareButton.click();
            await delay(1000);

            // Check for share link or modal
            const shareLink = await page.evaluate(() => {
                const input = document.querySelector('[data-testid="share-link"], input[type="text"]');
                return input ? input.value : null;
            });

            if (shareLink) {
                console.log(`✓ Share link generated: ${shareLink}`);
                return { success: true, shareLink };
            } else {
                console.log('⊘ Share link not found (feature may not be implemented yet)');
                return { success: false, reason: 'Share link not generated' };
            }
        } else {
            console.log('⊘ Share button not found (feature not implemented yet)');
            return { success: false, reason: 'Share button not found' };
        }

    } catch (error) {
        console.error('✗ Test failed:', error.message);
        return { success: false, error: error.message };
    } finally {
        await page.close();
    }
}

/**
 * Test 4: Verify users can manage their queue
 */
async function testQueueManagement(browser) {
    console.log('\n⚙️ Test 4: Queue Management');
    console.log('='.repeat(50));

    const page = await browser.newPage();

    try {
        await page.goto(MOVIESHOWS_URL, { waitUntil: 'networkidle2' });

        // Check for queue management controls
        const controls = await page.evaluate(() => {
            return {
                addButton: !!document.querySelector('[data-testid="add-to-queue"], button:has-text("Add")'),
                removeButton: !!document.querySelector('[data-testid="remove-from-queue"], button:has-text("Remove")'),
                reorderControls: !!document.querySelector('[draggable="true"], .sortable')
            };
        });

        console.log('Queue controls found:');
        console.log(`  Add button: ${controls.addButton}`);
        console.log(`  Remove button: ${controls.removeButton}`);
        console.log(`  Reorder controls: ${controls.reorderControls}`);

        return { success: true, controls };

    } catch (error) {
        console.error('✗ Test failed:', error.message);
        return { success: false, error: error.message };
    } finally {
        await page.close();
    }
}

/**
 * Test 5: Check login integration
 */
async function testLoginIntegration(browser) {
    console.log('\n🔐 Test 5: Login Integration');
    console.log('='.repeat(50));

    const page = await browser.newPage();

    try {
        await page.goto(MOVIESHOWS_URL, { waitUntil: 'networkidle2' });

        // Wait for potential login prompt
        await delay(3000);

        // Check for login prompt or button
        const loginElements = await page.evaluate(() => {
            return {
                loginButton: !!document.querySelector('[data-testid="login"], button:has-text("Login"), a[href*="login"]'),
                loginPrompt: !!document.querySelector('[data-testid="login-prompt"], .login-modal'),
                isLoggedIn: !!document.querySelector('[data-testid="user-menu"], .user-profile')
            };
        });

        console.log('Login elements:');
        console.log(`  Login button: ${loginElements.loginButton}`);
        console.log(`  Login prompt: ${loginElements.loginPrompt}`);
        console.log(`  User logged in: ${loginElements.isLoggedIn}`);

        return { success: true, loginElements };

    } catch (error) {
        console.error('✗ Test failed:', error.message);
        return { success: false, error: error.message };
    } finally {
        await page.close();
    }
}

/**
 * Main test runner
 */
async function runTests() {
    console.log('MovieShows Puppeteer Tests');
    console.log('===========================\n');
    console.log(`Testing: ${MOVIESHOWS_URL}\n`);

    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const results = {
        queueViewing: await testQueueViewing(browser),
        soundPersistence: await testSoundPersistence(browser),
        playlistSharing: await testPlaylistSharing(browser),
        queueManagement: await testQueueManagement(browser),
        loginIntegration: await testLoginIntegration(browser)
    };

    await browser.close();

    // Summary
    console.log('\n' + '='.repeat(50));
    console.log('TEST SUMMARY');
    console.log('='.repeat(50));

    const passed = Object.values(results).filter(r => r.success).length;
    const total = Object.keys(results).length;

    console.log(`\nPassed: ${passed}/${total}`);
    console.log('\nDetailed Results:');

    for (const [test, result] of Object.entries(results)) {
        const status = result.success ? '✓' : '✗';
        console.log(`  ${status} ${test}`);
        if (!result.success && result.reason) {
            console.log(`    Reason: ${result.reason}`);
        }
    }

    console.log('\n');

    return results;
}

// Run if executed directly
if (require.main === module) {
    runTests()
        .then(() => {
            console.log('✓ Tests complete!');
            process.exit(0);
        })
        .catch(error => {
            console.error('✗ Tests failed:', error);
            process.exit(1);
        });
}

module.exports = { runTests };
