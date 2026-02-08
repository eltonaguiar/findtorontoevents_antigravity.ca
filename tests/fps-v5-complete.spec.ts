import { test, expect } from '@playwright/test';

test.describe('FPS V5 - Complete Functionality Test', () => {

    test('should load with ZERO JavaScript errors', async ({ page }) => {
        const errors: string[] = [];

        // Capture all errors
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(`CONSOLE: ${msg.text()}`);
            }
        });

        page.on('pageerror', error => {
            errors.push(`PAGE: ${error.message}`);
        });

        // Navigate
        await page.goto('file:///e:/findtorontoevents_antigravity.ca/vr/game-arena/fps-v5/index.html');

        // Wait for loading to complete
        await page.waitForSelector('#loading-screen.hidden', { timeout: 10000 });

        // Verify THREE loaded
        const threeLoaded = await page.evaluate(() => typeof THREE !== 'undefined');
        expect(threeLoaded).toBe(true);

        // Verify engine initialized
        const engineReady = await page.evaluate(() => {
            return typeof engine !== 'undefined' && engine !== null && engine.scene !== null;
        });
        expect(engineReady).toBe(true);

        // Verify player initialized
        const playerReady = await page.evaluate(() => {
            return typeof player !== 'undefined' && player !== null;
        });
        expect(playerReady).toBe(true);

        // Take screenshot of menu
        await page.screenshot({ path: 'test-results/fps-v5-menu.png', fullPage: true });

        // CRITICAL: Verify ZERO errors
        expect(errors, 'Should have ZERO JavaScript errors').toEqual([]);

        console.log('✅ Game loaded successfully with ZERO errors');
    });

    test('should start game and run at 60 FPS', async ({ page }) => {
        const errors: string[] = [];

        page.on('console', msg => {
            if (msg.type() === 'error') errors.push(msg.text());
        });

        page.on('pageerror', error => {
            errors.push(error.message);
        });

        await page.goto('file:///e:/findtorontoevents_antigravity.ca/vr/game-arena/fps-v5/index.html');
        await page.waitForSelector('#loading-screen.hidden', { timeout: 10000 });

        // Click Enter Game
        await page.click('button:has-text("Enter Game")');

        // Wait for game to start
        await page.waitForTimeout(2000);

        // Check FPS
        const fps = await page.textContent('#fps-value');
        const fpsNum = parseInt(fps || '0');

        expect(fpsNum).toBeGreaterThanOrEqual(55);

        // Verify engine is running
        const isRunning = await page.evaluate(() => engine.isRunning);
        expect(isRunning).toBe(true);

        // Take screenshot
        await page.screenshot({ path: 'test-results/fps-v5-gameplay.png', fullPage: true });

        // CRITICAL: Verify ZERO errors
        expect(errors, 'Gameplay should have ZERO errors').toEqual([]);

        console.log(`✅ Game running at ${fpsNum} FPS with ZERO errors`);
    });

    test('should handle player movement', async ({ page }) => {
        const errors: string[] = [];

        page.on('console', msg => {
            if (msg.type() === 'error') errors.push(msg.text());
        });

        page.on('pageerror', error => {
            errors.push(error.message);
        });

        await page.goto('file:///e:/findtorontoevents_antigravity.ca/vr/game-arena/fps-v5/index.html');
        await page.waitForSelector('#loading-screen.hidden', { timeout: 10000 });
        await page.click('button:has-text("Enter Game")');
        await page.waitForTimeout(1000);

        // Get initial position
        const initialPos = await page.evaluate(() => ({
            x: player.position.x,
            y: player.position.y,
            z: player.position.z
        }));

        // Simulate movement
        await page.keyboard.down('KeyW');
        await page.waitForTimeout(500);
        await page.keyboard.up('KeyW');

        // Get new position
        const newPos = await page.evaluate(() => ({
            x: player.position.x,
            y: player.position.y,
            z: player.position.z
        }));

        // Verify player moved
        const moved = newPos.x !== initialPos.x || newPos.z !== initialPos.z;
        expect(moved).toBe(true);

        // CRITICAL: Verify ZERO errors
        expect(errors, 'Movement should have ZERO errors').toEqual([]);

        console.log('✅ Player movement works with ZERO errors');
    });

    test('should render 3D scene correctly', async ({ page }) => {
        await page.goto('file:///e:/findtorontoevents_antigravity.ca/vr/game-arena/fps-v5/index.html');
        await page.waitForSelector('#loading-screen.hidden', { timeout: 10000 });

        // Verify scene has objects
        const sceneInfo = await page.evaluate(() => ({
            childrenCount: engine.scene.children.length,
            hasGround: engine.scene.children.some((c: any) => c.geometry?.type === 'PlaneGeometry'),
            hasCubes: engine.scene.children.filter((c: any) => c.geometry?.type === 'BoxGeometry').length,
            hasLights: engine.scene.children.filter((c: any) => c.isLight).length
        }));

        expect(sceneInfo.childrenCount).toBeGreaterThan(10);
        expect(sceneInfo.hasGround).toBe(true);
        expect(sceneInfo.hasCubes).toBeGreaterThanOrEqual(10);
        expect(sceneInfo.hasLights).toBeGreaterThanOrEqual(2);

        console.log('✅ 3D scene rendered correctly:', sceneInfo);
    });
});
