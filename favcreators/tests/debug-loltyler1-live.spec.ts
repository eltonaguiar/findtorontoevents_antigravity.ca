import { test, expect } from '@playwright/test';

test('Debug loltyler1 live status detection', async ({ page }) => {
    // Navigate to the app
    await page.goto('http://localhost:3000/fc/');

    // Wait for app to load
    await page.waitForTimeout(8000);

    // Get all creators from localStorage
    const creatorsData = await page.evaluate(() => {
        const stored = localStorage.getItem('fav_creators');
        if (stored) {
            const creators = JSON.parse(stored);
            const loltyler1 = creators.find((c: any) =>
                c.name.toLowerCase().includes('loltyler1') ||
                c.name.toLowerCase().includes('tyler1')
            );

            if (loltyler1) {
                return {
                    found: true,
                    name: loltyler1.name,
                    isLive: loltyler1.isLive,
                    lastChecked: loltyler1.lastChecked,
                    accounts: loltyler1.accounts.map((acc: any) => ({
                        platform: acc.platform,
                        username: acc.username,
                        isLive: acc.isLive,
                        checkLive: acc.checkLive,
                        lastChecked: acc.lastChecked
                    }))
                };
            }
        }
        return { found: false };
    });

    console.log('loltyler1 data from localStorage:', JSON.stringify(creatorsData, null, 2));

    // Now click the live check button
    await page.click('button:has-text("Check All Live Status")');

    // Wait for check to complete
    await page.waitForTimeout(10000);

    // Get data again
    const creatorsDataAfter = await page.evaluate(() => {
        const stored = localStorage.getItem('fav_creators');
        if (stored) {
            const creators = JSON.parse(stored);
            const loltyler1 = creators.find((c: any) =>
                c.name.toLowerCase().includes('loltyler1') ||
                c.name.toLowerCase().includes('tyler1')
            );

            if (loltyler1) {
                return {
                    found: true,
                    name: loltyler1.name,
                    isLive: loltyler1.isLive,
                    lastChecked: loltyler1.lastChecked,
                    accounts: loltyler1.accounts.map((acc: any) => ({
                        platform: acc.platform,
                        username: acc.username,
                        isLive: acc.isLive,
                        checkLive: acc.checkLive,
                        lastChecked: acc.lastChecked
                    }))
                };
            }
        }
        return { found: false };
    });

    console.log('loltyler1 data AFTER live check:', JSON.stringify(creatorsDataAfter, null, 2));

    // Take screenshot
    await page.screenshot({ path: 'loltyler1-debug.png', fullPage: true });
});
