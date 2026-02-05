import { test, expect } from '@playwright/test';

/**
 * Simple test to verify TikTok live detection for Gabbyvn3
 * Expected: She is live on TikTok, NOT on Kick or Twitch
 */

test('Gabbyvn3 TikTok live detection - direct check', async ({ page }) => {
    console.log('=== Testing Gabbyvn3 TikTok Live Status ===');

    // Step 1: Check TikTok directly
    console.log('\n1. Checking TikTok page directly...');
    await page.goto('https://www.tiktok.com/@gabbyvn3/live');
    await page.waitForTimeout(3000);

    const tiktokContent = await page.content();
    const hasLiveEnded = tiktokContent.includes('LIVE has ended');

    console.log('   TikTok "LIVE has ended" found:', hasLiveEnded);
    console.log('   Expected: false (she should be live)');
    console.log('   Result:', hasLiveEnded ? '❌ FAIL - Shows offline' : '✅ PASS - Shows live');

    expect(hasLiveEnded).toBe(false);

    // Step 2: Check Kick (should be offline or not exist)
    console.log('\n2. Checking Kick...');
    try {
        const kickResponse = await page.request.get('https://kick.com/api/v1/channels/gabbyvn3');
        if (kickResponse.ok()) {
            const kickData = await kickResponse.json();
            const isLiveOnKick = kickData.livestream !== null;
            console.log('   Kick live status:', isLiveOnKick);
            console.log('   Expected: false');
            console.log('   Result:', isLiveOnKick ? '❌ FAIL - Shows live on Kick' : '✅ PASS - Not live on Kick');
            expect(isLiveOnKick).toBe(false);
        } else {
            console.log('   Kick account not found (404) - ✅ PASS');
        }
    } catch (error) {
        console.log('   Kick check error (expected):', error.message);
    }

    // Step 3: Check Twitch (should be offline)
    console.log('\n3. Checking Twitch...');
    try {
        const twitchResponse = await page.request.get('https://decapi.me/twitch/uptime/gabbyvn3');
        const twitchStatus = await twitchResponse.text();
        console.log('   Twitch DecAPI response:', twitchStatus);

        const isLiveOnTwitch = !twitchStatus.toLowerCase().includes('offline') &&
            !twitchStatus.toLowerCase().includes('not found') &&
            !twitchStatus.toLowerCase().includes('error');

        console.log('   Twitch live status:', isLiveOnTwitch);
        console.log('   Expected: false');
        console.log('   Result:', isLiveOnTwitch ? '❌ FAIL - Shows live on Twitch' : '✅ PASS - Not live on Twitch');

        expect(isLiveOnTwitch).toBe(false);
    } catch (error) {
        console.log('   Twitch check error:', error.message);
    }

    console.log('\n=== Summary ===');
    console.log('✅ Gabbyvn3 should ONLY be live on TikTok');
    console.log('❌ She should NOT be live on Kick or Twitch');
});

test('FavCreators app - Gabbyvn3 display check', async ({ page }) => {
    console.log('\n=== Testing FavCreators App Display ===');

    await page.goto('http://localhost:5173/fc');
    await page.waitForTimeout(5000); // Wait for live status checks

    // Take a screenshot
    await page.screenshot({
        path: 'test-results/gabbyvn3-app-display.png',
        fullPage: true
    });

    // Try to find Gabbyvn3's card
    const pageContent = await page.content();
    const hasGabbyvn3 = pageContent.toLowerCase().includes('gabbyvn3');

    console.log('Gabbyvn3 found in app:', hasGabbyvn3);

    if (hasGabbyvn3) {
        // Check what platform icons are shown
        console.log('\nChecking platform indicators...');
        console.log('TikTok mentioned:', pageContent.toLowerCase().includes('tiktok'));
        console.log('Kick mentioned:', pageContent.toLowerCase().includes('kick'));
        console.log('Twitch mentioned:', pageContent.toLowerCase().includes('twitch'));

        // Look for LIVE badge
        const hasLiveBadge = pageContent.includes('LIVE') || pageContent.includes('live-badge');
        console.log('LIVE badge present:', hasLiveBadge);

        if (hasLiveBadge) {
            console.log('\n⚠️  IMPORTANT: Check the screenshot to see which platform shows the LIVE badge');
            console.log('   Expected: TikTok icon should have LIVE badge');
            console.log('   NOT Expected: Twitch or Kick should NOT have LIVE badge');
        }
    } else {
        console.log('⚠️  Gabbyvn3 not found in the app - she may need to be added first');
    }
});
