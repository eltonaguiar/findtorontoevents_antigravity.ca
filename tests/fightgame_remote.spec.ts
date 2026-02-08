import { test, expect } from '@playwright/test';

const BASE = 'https://findtorontoevents.ca';

test('Shadow Arena loads on remote site without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => {
        errors.push(`PageError: ${err.message}`);
    });
    page.on('console', (msg) => {
        if (msg.type() === 'error') {
            errors.push(`ConsoleError: ${msg.text()}`);
        }
    });

    await page.goto(BASE + '/FIGHTGAME/', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    // Title should be visible
    const title = await page.locator('.game-title').textContent();
    expect(title).toContain('SHADOW');

    // FIGHT button
    const fightBtn = page.locator('#btn-play');
    await expect(fightBtn).toBeVisible();

    // 6 characters loaded
    const charCount = await page.evaluate(() => {
        return (window as any).CHARACTERS ? (window as any).CHARACTERS.length : 0;
    });
    expect(charCount).toBe(6);

    // No JS errors
    expect(errors).toHaveLength(0);
});
