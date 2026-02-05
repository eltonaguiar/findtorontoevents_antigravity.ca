import { test, expect } from '@playwright/test';

/**
 * Live Indicator Accuracy Test
 * 
 * Tests that red dot live indicators show on the CORRECT platform only.
 * Specifically verifies the bug fix where creators were incorrectly showing
 * as live on Kick when they were actually live on TikTok.
 * 
 * Test Case: @ggbabes88 is currently live on TikTok (verified manually)
 * Expected: Red dot on TikTok only, NO red dot on Kick
 */

test.describe('Live Indicator Accuracy', () => {
    test('should show live indicator on correct platform only for @ggbabes88', async ({ page }) => {
        // Navigate to local dev instance
        await page.goto('http://localhost:3000/fc/');

        // Wait for page to load
        await page.waitForLoadState('networkidle');

        // Add ggbabes88 with both TikTok and Kick platforms
        const quickAddInput = page.locator('.quick-add-input');
        await quickAddInput.fill('ggbabes88:tiktok,kick');

        const quickAddButton = page.locator('button:has-text("Quick Add")');
        await quickAddButton.click();

        // Wait for creator to be added
        await page.waitForTimeout(2000);

        // Trigger live status check
        const liveCheckButton = page.locator('button:has-text("Live check")');
        await liveCheckButton.click();

        // Wait for live checks to complete (8 seconds timeout per platform)
        await page.waitForTimeout(20000);

        // Search for the creator to isolate their card
        const searchInput = page.locator('input[placeholder*="Search"]');
        await searchInput.fill('ggbabes88');
        await page.waitForTimeout(1000);

        // Get the creator card
        const creatorCard = page.locator('.creator-card').filter({ hasText: 'Ggbabes88' });
        await expect(creatorCard).toBeVisible();

        // Check TikTok account - should have live dot
        const tiktokAccount = creatorCard.locator('.account-link.tiktok');
        await expect(tiktokAccount).toBeVisible();

        const tiktokLiveDot = tiktokAccount.locator('.account-live-dot');
        await expect(tiktokLiveDot).toBeVisible({ timeout: 5000 });

        console.log('✅ TikTok shows live indicator (CORRECT)');

        // Check Kick account - should NOT have live dot
        const kickAccount = creatorCard.locator('.account-link.kick');
        await expect(kickAccount).toBeVisible();

        const kickLiveDot = kickAccount.locator('.account-live-dot');
        await expect(kickLiveDot).not.toBeVisible();

        console.log('✅ Kick does NOT show live indicator (CORRECT)');

        // Verify TLC.php responses directly
        const tiktokResponse = await page.request.get(
            'https://findtorontoevents.ca/fc/TLC.php?user=ggbabes88&platform=tiktok&debug=1'
        );
        const tiktokData = await tiktokResponse.json();

        expect(tiktokData.live).toBe(true);
        expect(tiktokData.platform).toBe('tiktok');
        console.log(`✅ TikTok TLC.php: live=${tiktokData.live}, method=${tiktokData.method}`);

        const kickResponse = await page.request.get(
            'https://findtorontoevents.ca/fc/TLC.php?user=ggbabes88&platform=kick&debug=1'
        );
        const kickData = await kickResponse.json();

        // Kick should return false or null (both mean "not live")
        expect(kickData.live).not.toBe(true);
        expect(kickData.platform).toBe('kick');
        console.log(`✅ Kick TLC.php: live=${kickData.live}, method=${kickData.method}`);

        // Take screenshot for visual verification
        await page.screenshot({ path: 'live-indicator-accuracy-test.png', fullPage: true });
    });

    test('should verify TLC.php backend accuracy for multiple platforms', async ({ page }) => {
        // Test TikTok (should be live)
        const tiktokResponse = await page.request.get(
            'https://findtorontoevents.ca/fc/TLC.php?user=ggbabes88&platform=tiktok&debug=1'
        );
        const tiktokData = await tiktokResponse.json();

        console.log('TikTok Response:', JSON.stringify(tiktokData, null, 2));
        expect(tiktokData.user).toBe('ggbabes88');
        expect(tiktokData.platform).toBe('tiktok');
        expect(tiktokData.live).toBe(true);
        expect(tiktokData.method).toContain('sigi'); // Should use SIGI detection method

        // Test Kick (should NOT be live or undetermined)
        const kickResponse = await page.request.get(
            'https://findtorontoevents.ca/fc/TLC.php?user=ggbabes88&platform=kick&debug=1'
        );
        const kickData = await kickResponse.json();

        console.log('Kick Response:', JSON.stringify(kickData, null, 2));
        expect(kickData.user).toBe('ggbabes88');
        expect(kickData.platform).toBe('kick');
        // Kick should return null (undetermined) or false (not live), but NOT true
        expect(kickData.live).not.toBe(true);

        // Test Twitch (should NOT be live or undetermined)
        const twitchResponse = await page.request.get(
            'https://findtorontoevents.ca/fc/TLC.php?user=ggbabes88&platform=twitch&debug=1'
        );
        const twitchData = await twitchResponse.json();

        console.log('Twitch Response:', JSON.stringify(twitchData, null, 2));
        expect(twitchData.user).toBe('ggbabes88');
        expect(twitchData.platform).toBe('twitch');
        expect(twitchData.live).not.toBe(true);

        // Test YouTube (should NOT be live or undetermined)
        const youtubeResponse = await page.request.get(
            'https://findtorontoevents.ca/fc/TLC.php?user=ggbabes88&platform=youtube&debug=1'
        );
        const youtubeData = await youtubeResponse.json();

        console.log('YouTube Response:', JSON.stringify(youtubeData, null, 2));
        expect(youtubeData.user).toBe('ggbabes88');
        expect(youtubeData.platform).toBe('youtube');
        expect(youtubeData.live).not.toBe(true);
    });
});
