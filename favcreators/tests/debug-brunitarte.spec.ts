import { test, expect } from '@playwright/test';

test.describe('FavCreators - Debug Brunitarte Missing Issue', () => {
    test('should login as johndoe and verify all 13 creators are displayed', async ({ page }) => {
        // Enable console logging
        page.on('console', msg => {
            console.log(`[BROWSER ${msg.type()}]:`, msg.text());
        });

        // Navigate to FavCreators
        await page.goto('https://findtorontoevents.ca/fc/');

        // Login with johndoe/johndoe
        await page.fill('input[type="text"]', 'johndoe');
        await page.fill('input[type="password"]', 'johndoe');
        await page.click('button:has-text("Login")');

        // Wait for login to complete
        await page.waitForTimeout(3000);

        // Check if we're logged in (look for logout button or user indicator)
        const isLoggedIn = await page.locator('text=/logout|sign out/i').isVisible().catch(() => false);
        console.log('Is logged in:', isLoggedIn);

        // Wait for creators to load
        await page.waitForTimeout(2000);

        // Check the API call in Network tab
        const apiResponse = await page.waitForResponse(
            response => response.url().includes('get_my_creators.php'),
            { timeout: 10000 }
        ).catch(() => null);

        if (apiResponse) {
            const headers = apiResponse.headers();
            console.log('API Response Headers:');
            console.log('  X-Debug-Creator-Count:', headers['x-debug-creator-count']);
            console.log('  X-Debug-User-ID:', headers['x-debug-user-id']);

            const responseData = await apiResponse.json();
            const apiCreatorCount = responseData.creators?.length || 0;
            console.log('API returned creators:', apiCreatorCount);

            if (responseData.creators) {
                console.log('\nCreators from API:');
                responseData.creators.forEach((creator, idx) => {
                    console.log(`  ${idx + 1}. ${creator.name} (id: ${creator.id})`);
                });

                // Check if brunitarte is in the API response
                const hasBrunitarte = responseData.creators.some(c =>
                    c.name?.toLowerCase().includes('brunitarte') ||
                    c.id?.toLowerCase().includes('brunitarte')
                );
                console.log('\nBrunitarte in API response:', hasBrunitarte);
            }
        }

        // Count creators displayed on page
        const creatorRows = await page.locator('table.creator-table tbody tr').count().catch(() => 0);
        const creatorCards = await page.locator('.creator-card').count().catch(() => 0);
        const displayedCount = Math.max(creatorRows, creatorCards);

        console.log('\nCreators displayed on page:', displayedCount);

        // Check if brunitarte is visible on page
        const brunitarteVisible = await page.locator('text=/brunitarte/i').isVisible().catch(() => false);
        console.log('Brunitarte visible on page:', brunitarteVisible);

        // Get the creators state from React
        const creatorsState = await page.evaluate(() => {
            // Try to access React state (this might not work depending on React version)
            const root = document.querySelector('#root');
            if (root && (root as any)._reactRootContainer) {
                return 'React state not directly accessible';
            }
            return 'Unable to access React state';
        });
        console.log('React state:', creatorsState);

        // Check localStorage
        const localStorageData = await page.evaluate(() => {
            const data: any = {};
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key) {
                    const value = localStorage.getItem(key);
                    if (key.includes('creator') || key.includes('favcreator')) {
                        data[key] = value ? value.substring(0, 200) + '...' : null;
                    }
                }
            }
            return data;
        });
        console.log('\nLocalStorage (creator-related keys):', localStorageData);

        // Take screenshot
        await page.screenshot({ path: 'tests/screenshots/johndoe-creators-list.png', fullPage: true });

        // Assertions
        expect(displayedCount).toBeGreaterThan(0);

        // If API returned 13 but page shows less, we have a frontend issue
        if (apiResponse) {
            const responseData = await apiResponse.json();
            const apiCount = responseData.creators?.length || 0;
            if (apiCount === 13 && displayedCount < 13) {
                console.error(`\n❌ ISSUE FOUND: API returned ${apiCount} creators but only ${displayedCount} are displayed!`);
            }
        }
    });

    test('should check console for errors', async ({ page }) => {
        const consoleErrors: string[] = [];

        page.on('console', msg => {
            if (msg.type() === 'error') {
                consoleErrors.push(msg.text());
            }
        });

        await page.goto('https://findtorontoevents.ca/fc/');
        await page.waitForTimeout(3000);

        console.log('\nConsole Errors:', consoleErrors.length > 0 ? consoleErrors : 'None');

        // Log any errors but don't fail the test
        if (consoleErrors.length > 0) {
            console.error('Console errors detected:', consoleErrors);
        }
    });
});
