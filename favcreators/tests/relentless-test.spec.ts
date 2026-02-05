import { test, expect } from '@playwright/test';

test.describe('RELENTLESS API Testing', () => {
    test('intercept EXACT API response browser receives', async ({ page }) => {
        let apiCallMade = false;
        let apiData: any = null;
        let apiUrl = '';

        // Intercept ALL network requests
        await page.route('**/*', async (route) => {
            const url = route.request().url();

            // Let the request go through
            const response = await route.fetch();

            // Capture get_my_creators API calls
            if (url.includes('get_my_creators.php')) {
                apiCallMade = true;
                apiUrl = url;
                const text = await response.text();

                console.log(`\n========== API INTERCEPTED ==========`);
                console.log(`URL: ${url}`);
                console.log(`Status: ${response.status()}`);
                console.log(`Response length: ${text.length} bytes`);

                try {
                    apiData = JSON.parse(text);
                    console.log(`\nParsed successfully`);
                    console.log(`Creator count: ${apiData.creators?.length || 0}`);

                    if (apiData.creators) {
                        console.log(`\nAll ${apiData.creators.length} creators:`);
                        apiData.creators.forEach((c: any, i: number) => {
                            console.log(`  ${i + 1}. ${c.name} (id: ${c.id})`);
                        });

                        const hasBrunitarte = apiData.creators.some((c: any) => c.name === 'Brunitarte');
                        console.log(`\n>>> Brunitarte in API response: ${hasBrunitarte}`);
                    }
                } catch (e) {
                    console.log(`Failed to parse JSON: ${e}`);
                    console.log(`Raw response: ${text.substring(0, 500)}`);
                }
                console.log(`=====================================\n`);
            }

            await route.fulfill({ response });
        });

        // Navigate and wait
        console.log('\nNavigating to https://findtorontoevents.ca/fc/');
        await page.goto('https://findtorontoevents.ca/fc/');

        // Wait for app to initialize
        await page.waitForTimeout(8000);

        // Check console logs
        const logs: string[] = [];
        page.on('console', (msg) => {
            const text = msg.text();
            logs.push(text);
            if (text.includes('Loaded creators from DB')) {
                console.log(`\n>>> CONSOLE: ${text}`);
            }
        });

        // Count visible creators
        const visibleCount = await page.locator('tr[data-creator-id]').count();
        console.log(`\n>>> Visible creators in UI: ${visibleCount}`);

        // Check if Brunitarte is visible
        const brunitarteVisible = await page.locator('text=Brunitarte').isVisible().catch(() => false);
        console.log(`>>> Brunitarte visible in UI: ${brunitarteVisible}`);

        // Get all visible names
        const names = await page.locator('tr[data-creator-id]').evaluateAll(rows => {
            return rows.map(r => {
                const cell = r.querySelector('td:nth-child(2)');
                return cell?.textContent?.trim() || '';
            });
        });

        console.log(`\n>>> Visible creator names (${names.length}):`);
        names.forEach((name, i) => console.log(`  ${i + 1}. ${name}`));

        // Final summary
        console.log(`\n========== SUMMARY ==========`);
        console.log(`API call made: ${apiCallMade}`);
        console.log(`API URL: ${apiUrl}`);
        console.log(`API returned: ${apiData?.creators?.length || 0} creators`);
        console.log(`UI shows: ${visibleCount} creators`);
        console.log(`Brunitarte in API: ${apiData?.creators?.some((c: any) => c.name === 'Brunitarte') || false}`);
        console.log(`Brunitarte in UI: ${brunitarteVisible}`);
        console.log(`============================\n`);

        // Take screenshot
        await page.screenshot({
            path: 'e:/findtorontoevents_antigravity.ca/favcreators/test-results/api-test-screenshot.png',
            fullPage: true
        });

        // Assertions
        expect(apiCallMade).toBe(true);
        if (apiData) {
            console.log(`\n>>> CRITICAL: API returned ${apiData.creators.length} but UI shows ${visibleCount}`);
            if (apiData.creators.length !== visibleCount) {
                throw new Error(`MISMATCH: API has ${apiData.creators.length} creators but UI shows ${visibleCount}`);
            }
        }
    });

    test('test with cache cleared', async ({ context, page }) => {
        // Clear everything
        await context.clearCookies();
        await context.clearPermissions();

        await page.goto('https://findtorontoevents.ca/fc/');

        // Clear storage
        await page.evaluate(() => {
            localStorage.clear();
            sessionStorage.clear();
        });

        // Hard reload
        await page.reload({ waitUntil: 'networkidle' });

        // Capture API response
        let apiResponse: any = null;
        page.on('response', async (response) => {
            if (response.url().includes('get_my_creators.php?user_id=0')) {
                const text = await response.text();
                apiResponse = JSON.parse(text);
                console.log(`\n>>> Guest API returned: ${apiResponse.creators.length} creators`);
            }
        });

        await page.waitForTimeout(5000);

        const visibleCount = await page.locator('tr[data-creator-id]').count();
        console.log(`>>> Guest UI shows: ${visibleCount} creators`);
    });
});
