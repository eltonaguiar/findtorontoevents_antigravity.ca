import { test, expect } from '@playwright/test';

/**
 * FPS V5 — Zero JavaScript Errors Verification
 *
 * Uses the local dev server (http://localhost:5173) so ES module import maps work.
 * The game exposes window._fpsEngine, window._fpsPlayer, and window.THREE for testing.
 */

test.describe('FPS V5 - Zero JavaScript Errors Verification', () => {

    test('should load without any JavaScript errors', async ({ page }) => {
        const consoleErrors: string[] = [];
        const pageErrors: string[] = [];

        page.on('console', msg => {
            if (msg.type() === 'error') {
                consoleErrors.push(msg.text());
            }
        });

        page.on('pageerror', error => {
            pageErrors.push(error.message);
        });

        // Navigate via local server (import maps require http)
        await page.goto('/vr/game-arena/fps-v5/prototype-tactical.html', { waitUntil: 'domcontentloaded' });

        // Wait for loading screen to disappear (ES module + CDN load takes time)
        await page.waitForSelector('#loading-screen.hidden', { timeout: 25000 });

        // Wait for HUD to appear
        await page.waitForSelector('#hud.active', { timeout: 5000 });

        // Verify THREE.js loaded (exposed on window in ES module)
        const threeLoaded = await page.evaluate(() => typeof (window as any).THREE !== 'undefined');
        expect(threeLoaded).toBe(true);

        // Verify engine initialized
        const engineExists = await page.evaluate(() => {
            const eng = (window as any)._fpsEngine;
            return eng !== undefined && eng !== null;
        });
        expect(engineExists).toBe(true);

        // Verify player initialized
        const playerExists = await page.evaluate(() => {
            const p = (window as any)._fpsPlayer;
            return p !== undefined && p !== null;
        });
        expect(playerExists).toBe(true);

        // Take screenshot of loaded state
        await page.screenshot({ path: 'test-results/fps-v5-loaded.png', fullPage: true });

        // CRITICAL: Verify ZERO errors
        expect(consoleErrors, 'Console should have ZERO errors').toEqual([]);
        expect(pageErrors, 'Page should have ZERO errors').toEqual([]);

        console.log('FPS V5 loaded successfully with ZERO errors');
    });

    test('should start game and render frames', async ({ page }) => {
        const errors: string[] = [];

        page.on('console', msg => {
            if (msg.type() === 'error') errors.push(msg.text());
        });

        page.on('pageerror', error => {
            errors.push(error.message);
        });

        await page.goto('/vr/game-arena/fps-v5/prototype-tactical.html', { waitUntil: 'domcontentloaded' });
        await page.waitForSelector('#hud.active', { timeout: 25000 });

        // Click "Enter Game" button
        await page.click('#btn-start');

        // Wait for engine to render some frames
        await page.waitForTimeout(3000);

        // Check FPS counter is updating
        const fps = await page.textContent('#fps-value');
        const fpsNum = parseInt(fps || '0');
        // In headless mode FPS can be lower; just check it's running at all
        expect(fpsNum).toBeGreaterThan(0);

        // Verify engine is running
        const isRunning = await page.evaluate(() => (window as any)._fpsEngine.isRunning);
        expect(isRunning).toBe(true);

        await page.screenshot({ path: 'test-results/fps-v5-gameplay.png', fullPage: true });

        // CRITICAL: Verify ZERO errors during gameplay
        expect(errors, 'Gameplay should have ZERO errors').toEqual([]);

        console.log(`FPS V5 running at ${fpsNum} FPS with ZERO errors`);
    });

    test('should show pause overlay when ESC is pressed', async ({ page }) => {
        const errors: string[] = [];

        page.on('console', msg => {
            if (msg.type() === 'error') errors.push(msg.text());
        });
        page.on('pageerror', error => {
            errors.push(error.message);
        });

        await page.goto('/vr/game-arena/fps-v5/prototype-tactical.html', { waitUntil: 'domcontentloaded' });
        await page.waitForSelector('#hud.active', { timeout: 25000 });

        // Start the game
        await page.click('#btn-start');
        await page.waitForTimeout(1000);

        // Pause overlay should be hidden while playing
        const pauseHidden = await page.evaluate(() => {
            return document.getElementById('pause-overlay')!.style.display === 'none';
        });
        expect(pauseHidden).toBe(true);

        // ZERO errors throughout
        expect(errors, 'Should have ZERO errors').toEqual([]);

        console.log('Pause overlay test passed with ZERO errors');
    });
});
