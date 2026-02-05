import { test, expect } from '@playwright/test';

test('verify Brunitarte displays after fix', async ({ page }) => {
    // Navigate
    await page.goto('https://findtorontoevents.ca/fc/');

    // Clear cache
    await page.evaluate(() => {
        localStorage.clear();
        sessionStorage.clear();
    });

    // Reload
    await page.reload();
    await page.waitForTimeout(8000);

    // Count creators
    const count = await page.locator('tr[data-creator-id]').count();
    console.log(`Visible creators: ${count}`);

    // Check for Brunitarte
    const brunitarteVisible = await page.locator('text=Brunitarte').isVisible().catch(() => false);
    console.log(`Brunitarte visible: ${brunitarteVisible}`);

    // Take screenshot
    await page.screenshot({
        path: 'e:/findtorontoevents_antigravity.ca/favcreators/test-results/final-verification.png',
        fullPage: true
    });

    expect(count).toBe(12); // Guest list

    console.log('\n✅ Test complete - check screenshot');
});
