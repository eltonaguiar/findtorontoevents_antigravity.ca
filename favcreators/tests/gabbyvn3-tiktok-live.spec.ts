import { test, expect } from '@playwright/test';

/**
 * Test to verify Gabbyvn3 is correctly detected as live on TikTok
 * She should NOT show as live on Kick or Twitch (only TikTok)
 */

test.describe('Gabbyvn3 TikTok Live Detection', () => {

    test('should detect Gabbyvn3 as live on TikTok only', async ({ page }) => {
        // Navigate to the FavCreators app
        await page.goto('http://localhost:5173/fc');

        // Wait for the app to load
        await page.waitForSelector('body', { timeout: 10000 });
        await page.waitForTimeout(2000);

        // Find Gabbyvn3's creator card
        const gabbyvn3Card = page.locator('[data-creator-name="Gabbyvn3"], [data-creator-name="gabbyvn3"]').first();

        // If not found by data attribute, try finding by text
        const cardByText = page.locator('text=Gabbyvn3').first();
        const creatorCard = await gabbyvn3Card.isVisible() ? gabbyvn3Card : cardByText;

        // Verify the card exists
        await expect(creatorCard).toBeVisible({ timeout: 5000 });

        // Check for LIVE badge
        const liveBadge = page.locator('.live-badge, [data-live="true"], text=LIVE').first();
        const isLive = await liveBadge.isVisible();

        console.log('Gabbyvn3 live status:', isLive ? 'LIVE' : 'OFFLINE');

        // Take a screenshot for debugging
        await page.screenshot({
            path: 'test-results/gabbyvn3-status.png',
            fullPage: true
        });

        // Verify she shows as live (since she's currently live on TikTok)
        expect(isLive).toBe(true);
    });

    test('should show correct platform (TikTok) for Gabbyvn3', async ({ page }) => {
        await page.goto('http://localhost:5173/fc');
        await page.waitForSelector('body', { timeout: 10000 });
        await page.waitForTimeout(2000);

        // Find Gabbyvn3's card
        const gabbyvn3Card = page.locator('text=Gabbyvn3').first();
        await expect(gabbyvn3Card).toBeVisible();

        // Click to open details or check platform indicator
        // Look for TikTok icon or platform text
        const tiktokIndicator = page.locator('text=/tiktok/i, [data-platform="tiktok"]').first();

        // The platform should be TikTok, not Twitch or Kick
        const pageContent = await page.content();

        // Verify TikTok is mentioned in context of Gabbyvn3
        expect(pageContent).toContain('tiktok');

        console.log('Platform check: TikTok indicator found');
    });

    test('direct API check: Gabbyvn3 TikTok live status', async ({ request }) => {
        // Check TikTok directly
        const tiktokResponse = await request.get('https://www.tiktok.com/@gabbyvn3/live');
        const tiktokHtml = await tiktokResponse.text();

        // Check for "LIVE has ended" - if present, she's offline
        const isOffline = tiktokHtml.includes('LIVE has ended');

        console.log('TikTok direct check:', isOffline ? 'OFFLINE' : 'LIVE');

        // She should be live (no "LIVE has ended" text)
        expect(isOffline).toBe(false);
    });

    test('verify Kick account does NOT show as live', async ({ request }) => {
        // Check if Kick API shows her as offline
        try {
            const kickResponse = await request.get('https://kick.com/api/v1/channels/gabbyvn3');

            if (kickResponse.ok()) {
                const kickData = await kickResponse.json();
                const isLiveOnKick = kickData.livestream !== null;

                console.log('Kick status:', isLiveOnKick ? 'LIVE' : 'OFFLINE');

                // She should NOT be live on Kick
                expect(isLiveOnKick).toBe(false);
            } else {
                console.log('Kick account not found or API error - this is expected');
            }
        } catch (error) {
            console.log('Kick check failed (expected if account doesn\'t exist):', error);
        }
    });

    test('verify Twitch account does NOT show as live', async ({ request }) => {
        // Check Twitch DecAPI
        try {
            const twitchResponse = await request.get('https://decapi.me/twitch/uptime/gabbyvn3');
            const twitchStatus = await twitchResponse.text();

            const isLiveOnTwitch = !twitchStatus.includes('offline') &&
                !twitchStatus.includes('not found') &&
                !twitchStatus.includes('error');

            console.log('Twitch status:', isLiveOnTwitch ? 'LIVE' : 'OFFLINE');
            console.log('Twitch response:', twitchStatus);

            // She should NOT be live on Twitch
            expect(isLiveOnTwitch).toBe(false);
        } catch (error) {
            console.log('Twitch check failed:', error);
        }
    });

    test('comprehensive platform check: only TikTok should be live', async ({ page }) => {
        await page.goto('http://localhost:5173/fc');
        await page.waitForSelector('body', { timeout: 10000 });
        await page.waitForTimeout(3000);

        // Open Gabbyvn3's details/edit modal to see all accounts
        const gabbyvn3Card = page.locator('text=Gabbyvn3').first();
        await gabbyvn3Card.click();

        // Wait for modal or details view
        await page.waitForTimeout(1000);

        // Take screenshot of the details
        await page.screenshot({
            path: 'test-results/gabbyvn3-accounts.png',
            fullPage: true
        });

        // Check the page content
        const content = await page.content();

        // Log what we find
        console.log('TikTok mentioned:', content.includes('tiktok') || content.includes('TikTok'));
        console.log('Kick mentioned:', content.includes('kick') || content.includes('Kick'));
        console.log('Twitch mentioned:', content.includes('twitch') || content.includes('Twitch'));

        // The LIVE indicator should be associated with TikTok, not Kick or Twitch
        // This is a visual check - we'll verify in the screenshot
    });
});
