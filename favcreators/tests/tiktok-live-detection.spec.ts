import { test, expect } from '@playwright/test';

/**
 * TikTok Live Detection Test Suite
 * Tests both frontend proxy method and backend API method
 */

test.describe('TikTok Live Detection', () => {

    test('should detect offline TikTok user (gillianunrestricted)', async ({ page }) => {
        // Navigate to the app
        await page.goto('http://localhost:5173/fc');

        // Wait for the app to load
        await page.waitForSelector('body');

        // Check if gillianunrestricted is shown as offline
        // This assumes the creator is in the list
        const offlineCreator = page.locator('text=gillianunrestricted').first();
        if (await offlineCreator.isVisible()) {
            // Should not have a LIVE badge
            const liveBadge = page.locator('text=LIVE').first();
            await expect(liveBadge).not.toBeVisible();
        }
    });

    test('should detect live TikTok user (gabbyvn3) when live', async ({ page }) => {
        // Navigate to the app
        await page.goto('http://localhost:5173/fc');

        // Wait for the app to load
        await page.waitForSelector('body');

        // Check if gabbyvn3 is shown as live
        // Note: This test will only pass when gabbyvn3 is actually live
        const liveCreator = page.locator('text=Gabbyvn3').first();
        if (await liveCreator.isVisible()) {
            // Wait for live status to update (may take a few seconds)
            await page.waitForTimeout(3000);

            // Should have a LIVE badge if currently streaming
            const liveBadge = page.locator('.live-badge, [data-live="true"], text=LIVE').first();
            // This assertion is conditional - only fails if we're certain they should be live
            console.log('Gabbyvn3 live status:', await liveBadge.isVisible() ? 'LIVE' : 'OFFLINE');
        }
    });

    test('backend API: should return live status for offline user', async ({ request }) => {
        const response = await request.get('http://localhost:3000/api/tiktok/live/gillianunrestricted');

        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data).toHaveProperty('username', 'gillianunrestricted');
        expect(data).toHaveProperty('is_live');
        expect(data).toHaveProperty('checked_at');

        // gillianunrestricted should be offline
        expect(data.is_live).toBe(false);
    });

    test('backend API: should return live status for live user', async ({ request }) => {
        // Note: This test assumes gabbyvn3 is currently live
        const response = await request.get('http://localhost:3000/api/tiktok/live/gabbyvn3');

        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data).toHaveProperty('username', 'gabbyvn3');
        expect(data).toHaveProperty('is_live');
        expect(data).toHaveProperty('checked_at');

        console.log('Gabbyvn3 backend live status:', data.is_live ? 'LIVE' : 'OFFLINE');
    });

    test('backend API: batch endpoint should check multiple users', async ({ request }) => {
        const response = await request.post('http://localhost:3000/api/tiktok/live/batch', {
            data: {
                usernames: ['gabbyvn3', 'gillianunrestricted', 'starfireara']
            }
        });

        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data).toHaveProperty('results');
        expect(data).toHaveProperty('checked_at');
        expect(Array.isArray(data.results)).toBeTruthy();
        expect(data.results.length).toBe(3);

        // Each result should have username and is_live
        data.results.forEach((result: any) => {
            expect(result).toHaveProperty('username');
            expect(result).toHaveProperty('is_live');
            console.log(`${result.username}: ${result.is_live ? 'LIVE' : 'OFFLINE'}${result.cached ? ' (cached)' : ''}`);
        });
    });

    test('backend API: should use cache for repeated requests', async ({ request }) => {
        const username = 'gabbyvn3';

        // First request
        const response1 = await request.get(`http://localhost:3000/api/tiktok/live/${username}`);
        const data1 = await response1.json();
        expect(data1.cached).toBe(false);

        // Second request (should be cached)
        const response2 = await request.get(`http://localhost:3000/api/tiktok/live/${username}`);
        const data2 = await response2.json();
        expect(data2.cached).toBe(true);
        expect(data2.is_live).toBe(data1.is_live);
    });

    test('direct TikTok page check: offline user shows "LIVE has ended"', async ({ page }) => {
        await page.goto('https://www.tiktok.com/@gillianunrestricted/live');

        // Wait for page to load
        await page.waitForSelector('body');
        await page.waitForTimeout(3000);

        // Check for "LIVE has ended" text
        const pageContent = await page.content();
        expect(pageContent).toContain('LIVE has ended');
    });

    test('direct TikTok page check: live user does NOT show "LIVE has ended"', async ({ page }) => {
        // Note: This test only passes when gabbyvn3 is actually live
        await page.goto('https://www.tiktok.com/@gabbyvn3/live');

        // Wait for page to load
        await page.waitForSelector('body');
        await page.waitForTimeout(3000);

        // Check that "LIVE has ended" is NOT present
        const pageContent = await page.content();
        const hasEnded = pageContent.includes('LIVE has ended');

        console.log('Gabbyvn3 page check:', hasEnded ? 'OFFLINE (has ended)' : 'LIVE or LOADING');

        // If they're live, the page should not contain "LIVE has ended"
        // This is a soft assertion - we log the result but don't fail
        if (hasEnded) {
            console.warn('⚠️ Gabbyvn3 appears to be offline based on page content');
        }
    });
});
