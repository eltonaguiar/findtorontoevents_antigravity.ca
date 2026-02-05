import { test, expect } from '@playwright/test';

test('check what browser actually receives from API', async ({ page }) => {
    let apiData: any = null;

    // Intercept the API call
    await page.route('**/get_my_creators.php*', async (route) => {
        const response = await route.fetch();
        const text = await response.text();
        apiData = JSON.parse(text);
        console.log(`\n=== RAW API RESPONSE ===`);
        console.log(`Status: ${response.status()}`);
        console.log(`Body length: ${text.length}`);
        console.log(`Creator count: ${apiData.creators?.length || 0}`);
        console.log(`\nAll creators:`);
        apiData.creators?.forEach((c: any, i: number) => {
            console.log(`${i + 1}. ${c.name} (id: ${c.id}, avatarUrl: "${c.avatarUrl || ''}")`);
        });
        await route.continue();
    });

    await page.goto('https://findtorontoevents.ca/fc/');
    await page.waitForTimeout(5000);

    // Check what the frontend actually has
    const frontendCount = await page.evaluate(() => {
        // @ts-ignore
        return window.__REACT_DEVTOOLS_GLOBAL_HOOK__?.renderers?.size || 'unknown';
    });

    console.log(`\n=== FRONTEND STATE ===`);
    console.log(`API returned: ${apiData?.creators?.length || 0} creators`);

    // Count visible rows
    const visibleRows = await page.locator('tr[data-creator-id]').count();
    console.log(`Visible rows: ${visibleRows}`);

    // Get all visible names
    const names = await page.locator('tr[data-creator-id]').evaluateAll(rows => {
        return rows.map(r => {
            const nameCell = r.querySelector('td:nth-child(2)');
            return nameCell?.textContent?.trim() || '';
        });
    });

    console.log(`\nVisible creator names:`);
    names.forEach((name, i) => console.log(`${i + 1}. ${name}`));

    // Check if Brunitarte is in API but not visible
    const brunitarteInAPI = apiData?.creators?.some((c: any) => c.name === 'Brunitarte');
    const brunitarteVisible = names.includes('Brunitarte');

    console.log(`\n=== BRUNITARTE CHECK ===`);
    console.log(`In API response: ${brunitarteInAPI}`);
    console.log(`Visible in UI: ${brunitarteVisible}`);

    if (brunitarteInAPI && !brunitarteVisible) {
        console.log(`\n❌ PROBLEM: Brunitarte is in API but NOT rendered!`);
        const brunitarte = apiData.creators.find((c: any) => c.name === 'Brunitarte');
        console.log(`Brunitarte data:`, JSON.stringify(brunitarte, null, 2));
    }
});
