import { test, expect } from '@playwright/test';

test('clear all caches and check API', async ({ context, page }) => {
    // Clear all caches
    await context.clearCookies();
    await page.goto('https://findtorontoevents.ca/fc/');

    // Clear localStorage and service workers
    await page.evaluate(async () => {
        localStorage.clear();
        sessionStorage.clear();

        // Unregister service workers
        const registrations = await navigator.serviceWorker.getRegistrations();
        for (const registration of registrations) {
            await registration.unregister();
        }
    });

    // Hard reload
    await page.reload({ waitUntil: 'networkidle' });

    // Now intercept API call
    let apiResponse: any = null;
    page.on('response', async (response) => {
        if (response.url().includes('get_my_creators.php?user_id=2')) {
            const text = await response.text();
            apiResponse = JSON.parse(text);
            console.log(`\n=== API RESPONSE (after cache clear) ===`);
            console.log(`Creator count: ${apiResponse.creators.length}`);
            console.log(`\nAll creators:`);
            apiResponse.creators.forEach((c: any, i: number) => {
                console.log(`${i + 1}. ${c.name}`);
            });

            const hasBrunitarte = apiResponse.creators.some((c: any) => c.name === 'Brunitarte');
            console.log(`\nHas Brunitarte: ${hasBrunitarte}`);
        }
    });

    await page.waitForTimeout(8000);

    // Take screenshot
    await page.screenshot({
        path: 'e:/findtorontoevents_antigravity.ca/favcreators/test-results/after-cache-clear.png',
        fullPage: true
    });
});
