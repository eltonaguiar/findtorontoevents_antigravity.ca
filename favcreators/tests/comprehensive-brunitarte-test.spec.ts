import { test, expect } from '@playwright/test';

test.describe('Comprehensive Brunitarte Testing', () => {
    test('verify API returns 13 creators with Brunitarte', async ({ page }) => {
        let apiData: any = null;

        page.on('response', async (response) => {
            if (response.url().includes('get_my_creators.php?user_id=2')) {
                const text = await response.text();
                apiData = JSON.parse(text);
            }
        });

        // Direct API test first
        const apiResponse = await page.request.get('https://findtorontoevents.ca/fc/api/get_my_creators.php?user_id=2');
        const apiJson = await apiResponse.json();

        console.log(`\n=== DIRECT API TEST ===`);
        console.log(`Status: ${apiResponse.status()}`);
        console.log(`Creator count: ${apiJson.creators.length}`);

        const hasBrunitarte = apiJson.creators.some((c: any) => c.name === 'Brunitarte');
        console.log(`Has Brunitarte: ${hasBrunitarte}`);

        if (!hasBrunitarte) {
            console.log(`\n❌ FAIL: API does not return Brunitarte!`);
            console.log(`All creators:`);
            apiJson.creators.forEach((c: any, i: number) => {
                console.log(`  ${i + 1}. ${c.name}`);
            });
        }

        expect(apiJson.creators.length).toBe(13);
        expect(hasBrunitarte).toBe(true);

        console.log(`\n✅ API test passed`);
    });

    test('verify guest view shows 12 creators', async ({ page }) => {
        await page.goto('https://findtorontoevents.ca/fc/');

        // Clear storage
        await page.evaluate(() => {
            localStorage.clear();
            sessionStorage.clear();
        });

        await page.reload();
        await page.waitForTimeout(8000);

        const count = await page.locator('tr[data-creator-id]').count();
        console.log(`\n=== GUEST VIEW ===`);
        console.log(`Visible creators: ${count}`);

        await page.screenshot({
            path: 'e:/findtorontoevents_antigravity.ca/favcreators/test-results/guest-view.png',
            fullPage: true
        });

        expect(count).toBe(12); // Guest should see 12
    });

    test('check database directly', async ({ page }) => {
        const response = await page.request.get('https://findtorontoevents.ca/fc/api/emergency_check.php');
        const text = await response.text();

        console.log(`\n=== DATABASE CHECK ===`);
        console.log(text);

        expect(text).toContain('Total creators in DB: 13');
        expect(text).toContain('FOUND! Brunitarte');
    });
});
