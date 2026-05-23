import { test, expect } from '@playwright/test';

test('Shadow Arena game page loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => {
        errors.push(`PageError: ${err.message}`);
    });
    page.on('console', (msg) => {
        if (msg.type() === 'error') {
            errors.push(`ConsoleError: ${msg.text()}`);
        }
    });

    await page.goto('http://localhost:5173/FIGHTGAME/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Title should be visible
    const title = await page.locator('.game-title').textContent();
    expect(title).toContain('SHADOW');

    // FIGHT button should exist
    const fightBtn = page.locator('#btn-play');
    await expect(fightBtn).toBeVisible();

    // Check that character data loaded (no script errors)
    const charCount = await page.evaluate(() => {
        return (window as any).CHARACTERS ? (window as any).CHARACTERS.length : 0;
    });
    expect(charCount).toBe(6);

    // Check no JS errors
    expect(errors).toHaveLength(0);
});

test('Shadow Arena character select screen works', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => {
        errors.push(`PageError: ${err.message}`);
    });

    await page.goto('http://localhost:5173/FIGHTGAME/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Click FIGHT
    await page.click('#btn-play');
    await page.waitForTimeout(500);

    // Mode screen should be visible
    const modeScreen = page.locator('#mode-screen');
    await expect(modeScreen).toHaveClass(/active/);

    // Click VS AI
    await page.click('#btn-mode-arcade');
    await page.waitForTimeout(500);

    // Character select should be visible
    const charScreen = page.locator('#char-select-screen');
    await expect(charScreen).toHaveClass(/active/);

    // Character cards should be rendered
    const cards = page.locator('.char-card');
    expect(await cards.count()).toBe(6);

    expect(errors).toHaveLength(0);
});

test('Shadow Arena game canvas starts without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => {
        errors.push(`PageError: ${err.message}`);
    });

    await page.goto('http://localhost:5173/FIGHTGAME/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);

    // Navigate to game: FIGHT -> VS AI -> Confirm char -> Confirm weapon -> Confirm stage
    await page.click('#btn-play');
    await page.waitForTimeout(300);
    await page.click('#btn-mode-arcade');
    await page.waitForTimeout(300);
    await page.click('#btn-char-confirm');
    await page.waitForTimeout(300);
    await page.click('#btn-weapon-confirm');
    await page.waitForTimeout(300);
    await page.click('#btn-stage-confirm');
    await page.waitForTimeout(2000);

    // Game screen should be active
    const gameScreen = page.locator('#game-screen');
    await expect(gameScreen).toHaveClass(/active/);

    // Canvas should exist and have dimensions
    const canvasSize = await page.evaluate(() => {
        const c = document.getElementById('gameCanvas') as HTMLCanvasElement;
        return c ? { w: c.width, h: c.height } : null;
    });
    expect(canvasSize).not.toBeNull();
    expect(canvasSize!.w).toBe(1280);
    expect(canvasSize!.h).toBe(720);

    expect(errors).toHaveLength(0);
});
