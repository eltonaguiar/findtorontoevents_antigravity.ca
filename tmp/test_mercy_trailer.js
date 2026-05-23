/**
 * Test script: Verify Mercy trailer plays from Browse search
 * 
 * Chromium bug fixed: iframe rendering deferred at extreme scroll positions (>500K px)
 * Fix: Scroll to video first, then enable autoplay on existing iframe (no overlay creation)
 */
const { chromium } = require('playwright');

async function testMercyTrailer() {
    console.log('=== Testing Mercy Trailer Playback ===\n');
    
    const browser = await chromium.launch({
        headless: false,  // Visible for debugging
        slowMo: 100
    });
    
    const context = await browser.newContext({
        viewport: { width: 1280, height: 720 }
    });
    
    const page = await context.newPage();
    
    // Enable console logging
    page.on('console', msg => console.log('[BROWSER]', msg.type().toUpperCase(), msg.text()));
    page.on('pageerror', err => console.log('[BROWSER ERROR]', err.message));
    
    try {
        // Navigate to MOVIESHOWS3
        console.log('1. Navigating to MOVIESHOWS3...');
        await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { 
            waitUntil: 'networkidle',
            timeout: 60000 
        });
        console.log('   Loaded successfully\n');
        
        // Wait for initial load
        await page.waitForTimeout(2000);
        
        // Open Browse view
        console.log('2. Opening Browse view...');
        // Look for the Browse button (not the heading)
        const browseBtn = await page.locator('button:has-text("Browse"), [data-view="browse"]').first();
        await browseBtn.click({ force: true });
        await page.waitForTimeout(1000);
        console.log('   Browse view opened\n');
        
        // Search for Mercy
        console.log('3. Searching for "Mercy"...');
        const searchBox = await page.locator('#browseSearchInput');
        await searchBox.fill('Mercy');
        await page.waitForTimeout(1500);  // Wait for filtering
        
        // Check if Mercy appears in results
        const mercyCard = await page.locator('.video-card:has-text("Mercy")').first();
        const mercyVisible = await mercyCard.isVisible().catch(() => false);
        
        if (!mercyVisible) {
            console.log('   ERROR: Mercy not found in search results');
            await browser.close();
            return;
        }
        console.log('   Mercy found in search results\n');
        
        // Click Play on Mercy
        console.log('4. Clicking Play on Mercy...');
        const mercyPlayBtn = mercyCard.locator('button:has-text("Play"), .play-btn, [data-action="play"]').first();
        await mercyPlayBtn.click();
        
        // Wait for scroll and autoplay to initiate
        console.log('   Waiting for scroll and autoplay (3 seconds)...');
        await page.waitForTimeout(3000);
        
        // Check for video playback
        console.log('5. Checking video playback...');
        
        // Look for iframe with autoplay
        const iframe = await page.locator('.video-card[data-index] iframe[src*="autoplay=1"]').first();
        const iframeSrc = await iframe.getAttribute('src').catch(() => null);
        
        if (iframeSrc && iframeSrc.includes('autoplay=1')) {
            console.log('   SUCCESS: iframe has autoplay=1');
            console.log('   URL:', iframeSrc.substring(0, 80) + '...\n');
        } else {
            console.log('   WARNING: iframe may not have autoplay enabled\n');
        }
        
        // Check if iframe is visible and has proper dimensions
        const bbox = await iframe.boundingBox().catch(() => null);
        if (bbox && bbox.width > 100 && bbox.height > 100) {
            console.log('   SUCCESS: iframe is visible (' + Math.round(bbox.width) + 'x' + Math.round(bbox.height) + ')');
        } else {
            console.log('   ERROR: iframe may be invisible or 0x0');
            if (bbox) {
                console.log('   Dimensions:', bbox.width + 'x' + bbox.height);
            }
        }
        
        // Screenshot for verification
        await page.screenshot({ path: 'tmp/mercy_test_result.png', fullPage: true });
        console.log('\n6. Screenshot saved: tmp/mercy_test_result.png');
        
        console.log('\n=== Test Complete ===');
        console.log('Check the browser window to see if Mercy trailer is playing.');
        console.log('Close the browser manually to end the test.');
        
        // Keep browser open for manual verification
        await new Promise(() => {});
        
    } catch (error) {
        console.error('Test error:', error);
        await browser.close();
    }
}

testMercyTrailer().catch(console.error);
