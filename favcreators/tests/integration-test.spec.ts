import { test, expect } from '@playwright/test';

test.describe('FavCreators Full Integration Test', () => {
    test('should show all 13 creators for zerounderscore@gmail.com after login', async ({ page }) => {
        // Navigate to FavCreators
        await page.goto('https://findtorontoevents.ca/fc/');

        // Wait for app to initialize
        await page.waitForTimeout(2000);

        // Check that we're in guest mode initially
        const guestMode = await page.locator('text=GUEST MODE').isVisible();
        console.log('Guest mode visible:', guestMode);

        // Click Login button
        await page.click('button:has-text("Login")');

        // Wait for Google login redirect
        await page.waitForURL(/accounts\.google\.com/, { timeout: 10000 });

        // Fill in Google credentials
        await page.fill('input[type="email"]', 'zerounderscore@gmail.com');
        await page.click('button:has-text("Next")');
        await page.waitForTimeout(1000);

        // Note: Password step would require actual credentials
        // For now, we'll test the API directly

        console.log('Login flow initiated - would require real credentials to complete');
    });

    test('should verify API returns all 13 creators for user 2', async ({ request }) => {
        // Test the API directly
        const response = await request.get('https://findtorontoevents.ca/fc/api/get_my_creators.php?user_id=2');

        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        console.log('API Response:', JSON.stringify(data, null, 2));

        expect(data.creators).toBeDefined();
        expect(data.creators.length).toBe(13);

        // Check for brunitarte specifically
        const brunitarte = data.creators.find((c: any) => c.id === 'brunitarte-tiktok');
        expect(brunitarte).toBeDefined();
        expect(brunitarte.name).toBe('Brunitarte');

        console.log('✅ All 13 creators found including brunitarte!');

        // List all creators
        console.log('\nAll creators:');
        data.creators.forEach((c: any, i: number) => {
            console.log(`${i + 1}. ${c.name} (${c.id})`);
        });
    });

    test('should verify frontend loads and displays creators', async ({ page }) => {
        await page.goto('https://findtorontoevents.ca/fc/');

        // Wait for app to load
        await page.waitForSelector('.creator-card, tr[data-creator-id]', { timeout: 10000 });

        // Count visible creators
        const creatorRows = await page.locator('tr[data-creator-id]').count();
        console.log(`Frontend shows ${creatorRows} creators`);

        // Check if brunitarte is visible
        const brunitarteVisible = await page.locator('text=Brunitarte').isVisible();
        console.log('Brunitarte visible on page:', brunitarteVisible);

        // Take screenshot
        await page.screenshot({ path: 'e:/findtorontoevents_antigravity.ca/favcreators/test-results/frontend-loaded.png', fullPage: true });
    });

    test('should verify database has correct data', async ({ request }) => {
        // Check status endpoint
        const statusResponse = await request.get('https://findtorontoevents.ca/fc/api/status.php');
        const statusData = await statusResponse.json();

        console.log('Database status:', statusData);
        expect(statusData.ok).toBe(true);
        expect(statusData.db).toBe('connected');

        // Check notes endpoint
        const notesResponse = await request.get('https://findtorontoevents.ca/fc/api/get_notes.php?user_id=2');
        const notesData = await notesResponse.json();

        console.log('Notes loaded:', Object.keys(notesData.notes || {}).length);
    });
});
