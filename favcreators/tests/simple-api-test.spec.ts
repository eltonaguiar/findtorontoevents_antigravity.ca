import { test, expect } from '@playwright/test';

test('direct API interception test', async ({ page }) => {
    let guestApiData: any = null;
    let user2ApiData: any = null;

    // Intercept API calls
    page.on('response', async (response) => {
        const url = response.url();

        if (url.includes('get_my_creators.php')) {
            const text = await response.text();
            const data = JSON.parse(text);

            if (url.includes('user_id=0')) {
                guestApiData = data;
                console.log(`\n>>> GUEST API: ${data.creators.length} creators`);
            } else if (url.includes('user_id=2')) {
                user2ApiData = data;
                console.log(`\n>>> USER 2 API: ${data.creators.length} creators`);
                console.log(`>>> Has Brunitarte: ${data.creators.some((c: any) => c.name === 'Brunitarte')}`);

                console.log(`\n>>> All creators from API:`);
                data.creators.forEach((c: any, i: number) => {
                    console.log(`  ${i + 1}. ${c.name}`);
                });
            }
        }
    });

    await page.goto('https://findtorontoevents.ca/fc/');
    await page.waitForTimeout(10000);

    const visibleCount = await page.locator('tr[data-creator-id]').count();
    console.log(`\n>>> Visible in UI: ${visibleCount}`);

    if (guestApiData) {
        console.log(`\n========== RESULT ==========`);
        console.log(`Guest API returned: ${guestApiData.creators.length}`);
        console.log(`UI shows: ${visibleCount}`);
        console.log(`Match: ${guestApiData.creators.length === visibleCount}`);
    }
});
