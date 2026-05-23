import { test, expect } from '@playwright/test';

test.describe('FPS V5 - Zero Errors Test', () => {
    test('should load without JavaScript errors', async ({ page }) => {
        const errors: string[] = [];

        // Capture console errors
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });

        // Capture page errors
        page.on('pageerror', error => {
            errors.push(error.message);
        });

        // Navigate to the game
        await page.goto('file:///e:/findtorontoevents_antigravity.ca/vr/game-arena/fps-v5/index.html');

        // Wait for loading to complete
        await page.waitForSelector('#loading-screen.hidden', { timeout: 10000 });

        // Wait for HUD to appear
        await page.waitForSelector('#hud.active', { timeout: 5000 });

        // Check for THREE.js
        const threeLoaded = await page.evaluate(() => typeof THREE !== 'undefined');
        expect(threeLoaded).toBe(true);

        // Check for engine
        const engineLoaded = await page.evaluate(() => typeof engine !== 'undefined');
        expect(engineLoaded).toBe(true);

        // Check for player
        const playerLoaded = await page.evaluate(() => typeof player !== 'undefined');
        expect(playerLoaded).toBe(true);

        // Verify no errors
        expect(errors).toEqual([]);

        // Take screenshot
        await page.screenshot({ path: 'fps-v5-loaded.png' });
    });

    test('should start game and run at 60 FPS', async ({ page }) => {
        await page.goto('file:///e:/findtorontoevents_antigravity.ca/vr/game-arena/fps-v5/index.html');

        // Wait for game to load
        await page.waitForSelector('#hud.active', { timeout: 10000 });

        // Click Enter Game button
        await page.click('button:has-text("Enter Game")');

        // Wait for game to start
        await page.waitForTimeout(1000);

        // Check FPS
        const fps = await page.textContent('#fps-value');
        const fpsNum = parseInt(fps || '0');

        expect(fpsNum).toBeGreaterThanOrEqual(55);

        // Take screenshot of gameplay
        await page.screenshot({ path: 'fps-v5-gameplay.png' });
    });
});
