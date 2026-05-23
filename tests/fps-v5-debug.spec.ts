import { test, expect } from '@playwright/test';

test('FPS V5 - Simple Error Check', async ({ page }) => {
    const errors: string[] = [];

    // Capture errors
    page.on('console', msg => {
        if (msg.type() === 'error') {
            console.log('❌ CONSOLE ERROR:', msg.text());
            errors.push(msg.text());
        } else if (msg.type() === 'log' && msg.text().includes('[')) {
            console.log('📝', msg.text());
        }
    });

    page.on('pageerror', error => {
        console.log('❌ PAGE ERROR:', error.message);
        errors.push(error.message);
    });

    console.log('🚀 Loading FPS V5...');
    await page.goto('file:///e:/findtorontoevents_antigravity.ca/vr/game-arena/fps-v5/index.html');

    // Wait a bit for scripts to load
    await page.waitForTimeout(5000);

    // Check what's on the page
    const loadingVisible = await page.isVisible('#loading-screen');
    const loadingHidden = await page.evaluate(() => {
        const el = document.getElementById('loading-screen');
        return el?.classList.contains('hidden');
    });

    const loadStatus = await page.textContent('#load-status');

    console.log('📊 Page State:');
    console.log('  Loading screen visible:', loadingVisible);
    console.log('  Loading screen hidden class:', loadingHidden);
    console.log('  Load status:', loadStatus);

    // Check if THREE loaded
    const threeStatus = await page.evaluate(() => typeof THREE);
    console.log('  THREE status:', threeStatus);

    // Check if initGame exists
    const initGameExists = await page.evaluate(() => typeof initGame);
    console.log('  initGame exists:', initGameExists);

    // Check if engine exists
    const engineStatus = await page.evaluate(() => typeof engine);
    console.log('  engine status:', engineStatus);

    // Take screenshot
    await page.screenshot({ path: 'fps-v5-debug.png', fullPage: true });

    console.log('\n📋 Error Summary:');
    if (errors.length === 0) {
        console.log('✅ ZERO ERRORS!');
    } else {
        console.log(`❌ Found ${errors.length} error(s):`);
        errors.forEach((err, i) => console.log(`  ${i + 1}. ${err}`));
    }

    // Assert zero errors
    expect(errors).toEqual([]);
});
