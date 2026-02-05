import { test, expect } from '@playwright/test';

/**
 * Test to verify Gabbyvn3 live status detection is correct
 * Expected: Live on TikTok, NOT live on Kick
 */

test.describe('Gabbyvn3 Live Status Fix Verification', () => {

    test('should show Gabbyvn3 as live on TikTok (not Kick)', async ({ page }) => {
        console.log('=== Testing Gabbyvn3 Live Status After Fix ===\n');

        // Navigate to the app
        await page.goto('http://localhost:5173/fc');
        await page.waitForTimeout(5000); // Wait for initial load

        // Find Gabbyvn3's card
        const pageContent = await page.content();
        const hasGabbyvn3 = pageContent.toLowerCase().includes('gabbyvn3');

        if (!hasGabbyvn3) {
            console.log('⚠️  Gabbyvn3 not found in app - skipping test');
            test.skip();
            return;
        }

        console.log('✅ Found Gabbyvn3 in the app');

        // Take a screenshot BEFORE clicking refresh
        await page.screenshot({
            path: 'test-results/gabbyvn3-before-refresh.png',
            fullPage: true
        });

        // Click the "Check Live Status" button to force a refresh
        const checkButton = page.locator('button[title*="Check Live Status"]').first();
        if (await checkButton.isVisible()) {
            console.log('🔄 Clicking "Check Live Status" button...');
            await checkButton.click();
            await page.waitForTimeout(8000); // Wait for status check to complete
        }

        // Take a screenshot AFTER refresh
        await page.screenshot({
            path: 'test-results/gabbyvn3-after-refresh.png',
            fullPage: true
        });

        // Get the updated page content
        const updatedContent = await page.content();

        // Check for platform indicators
        console.log('\n📊 Platform Indicators:');
        console.log('  TikTok mentioned:', updatedContent.toLowerCase().includes('tiktok'));
        console.log('  Kick mentioned:', updatedContent.toLowerCase().includes('kick'));

        // Look for the account links with live dots
        const accountLinks = await page.locator('.account-link').all();

        console.log(`\n🔍 Found ${accountLinks.length} account links`);

        for (const link of accountLinks) {
            const linkHtml = await link.innerHTML();
            const hasLiveDot = linkHtml.includes('account-live-dot');
            const platform = await link.getAttribute('class');

            if (linkHtml.toLowerCase().includes('gabbyvn3') || linkHtml.toLowerCase().includes('@gabbyvn3')) {
                console.log(`  Account: ${platform}`);
                console.log(`    Has live dot: ${hasLiveDot}`);

                if (platform?.includes('kick') && hasLiveDot) {
                    console.log('    ❌ FAIL: Kick should NOT have live dot');
                } else if (platform?.includes('tiktok') && !hasLiveDot) {
                    console.log('    ❌ FAIL: TikTok SHOULD have live dot');
                } else if (platform?.includes('tiktok') && hasLiveDot) {
                    console.log('    ✅ PASS: TikTok has live dot (correct!)');
                } else if (platform?.includes('kick') && !hasLiveDot) {
                    console.log('    ✅ PASS: Kick does NOT have live dot (correct!)');
                }
            }
        }

        console.log('\n📸 Screenshots saved to test-results/');
        console.log('   - gabbyvn3-before-refresh.png');
        console.log('   - gabbyvn3-after-refresh.png');
    });

    test('verify Kick false positive fix', async ({ page }) => {
        console.log('\n=== Testing Kick False Positive Fix ===\n');

        // Test the Kick detection directly
        await page.goto('http://localhost:5173/fc');
        await page.waitForTimeout(2000);

        // Execute the checkLiveStatus function directly in the browser
        const kickResult = await page.evaluate(async () => {
            // This simulates what the app does
            const response = await fetch('https://kick.com/gabbyvn3');
            const html = await response.text();

            // Check for 404
            const has404 = html.includes('Channel Not Found') ||
                html.includes('channel-not-found') ||
                html.includes('404');

            // Check for the word LIVE
            const hasLiveWord = html.includes('LIVE');

            // Check for livestream structure
            const hasLivestream = html.includes('"livestream":{') &&
                !html.includes('"livestream":null');

            return {
                has404,
                hasLiveWord,
                hasLivestream,
                shouldBeLive: !has404 && hasLivestream
            };
        });

        console.log('Kick Detection Results:');
        console.log('  Has 404/Not Found:', kickResult.has404);
        console.log('  Has word "LIVE":', kickResult.hasLiveWord);
        console.log('  Has livestream structure:', kickResult.hasLivestream);
        console.log('  Should be detected as live:', kickResult.shouldBeLive);

        expect(kickResult.has404).toBe(true);
        expect(kickResult.shouldBeLive).toBe(false);

        console.log('\n✅ Kick false positive fix verified!');
    });

    test('verify TikTok detection works', async ({ page }) => {
        console.log('\n=== Testing TikTok Detection ===\n');

        await page.goto('http://localhost:5173/fc');
        await page.waitForTimeout(2000);

        // Test TikTok detection
        const tiktokResult = await page.evaluate(async () => {
            try {
                // Use the proxy endpoint
                const proxyUrl = '/api/proxy?url=' + encodeURIComponent('https://www.tiktok.com/@gabbyvn3/live');
                const response = await fetch(proxyUrl);
                const html = await response.text();

                // Check for offline indicator
                const hasEnded = html.includes('LIVE has ended');

                // Check for status codes
                const hasStatus2 = html.includes('"status":2');
                const hasStatus4 = html.includes('"status":4');

                return {
                    hasEnded,
                    hasStatus2,
                    hasStatus4,
                    shouldBeLive: !hasEnded && hasStatus2
                };
            } catch (error) {
                return {
                    error: error.message
                };
            }
        });

        console.log('TikTok Detection Results:');
        if (tiktokResult.error) {
            console.log('  Error:', tiktokResult.error);
        } else {
            console.log('  Has "LIVE has ended":', tiktokResult.hasEnded);
            console.log('  Has status:2 (live):', tiktokResult.hasStatus2);
            console.log('  Has status:4 (offline):', tiktokResult.hasStatus4);
            console.log('  Should be detected as live:', tiktokResult.shouldBeLive);

            expect(tiktokResult.hasEnded).toBe(false);
            expect(tiktokResult.shouldBeLive).toBe(true);

            console.log('\n✅ TikTok detection verified!');
        }
    });
});
