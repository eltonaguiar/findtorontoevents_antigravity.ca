import { test, expect } from '@playwright/test';

test('inspect FavCreators link behavior', async ({ page }) => {
    console.log('=== FAVCREATORS LINK INSPECTION ===');
    
    // Navigate to site
    console.log('Navigating to https://findtorontoevents.ca/...');
    await page.goto('https://findtorontoevents.ca/', { waitUntil: 'networkidle' });
    
    // Wait for page to fully load
    await page.waitForTimeout(2000);
    
    // Find all links containing "favcreators" or "FAVCREATORS"
    console.log('\n--- Finding all FavCreators links ---');
    const allLinks = await page.locator('a').all();
    const favLinks: Array<{text: string, href: string, visible: boolean}> = [];
    
    for (const link of allLinks) {
        const href = await link.getAttribute('href');
        const text = await link.innerText().catch(() => '');
        const isVisible = await link.isVisible().catch(() => false);
        
        if (href && (href.toLowerCase().includes('favcreators') || text.toLowerCase().includes('favcreator'))) {
            favLinks.push({ text: text.trim(), href, visible: isVisible });
            console.log(`Found: text="${text.trim()}", href="${href}", visible=${isVisible}`);
        }
    }
    
    console.log(`\nTotal FavCreators links found: ${favLinks.length}`);
    
    // Check the main menu link specifically
    console.log('\n--- Checking main menu link ---');
    try {
        // Try to find by role and name
        const mainMenuLink = page.getByRole('link', { name: /FAVCREATORS/i });
        const count = await mainMenuLink.count();
        console.log(`Links with role="link" and name containing "FAVCREATORS": ${count}`);
        
        if (count > 0) {
            for (let i = 0; i < count; i++) {
                const link = mainMenuLink.nth(i);
                const href = await link.getAttribute('href');
                const text = await link.innerText();
                const isVisible = await link.isVisible();
                console.log(`Link ${i + 1}: text="${text}", href="${href}", visible=${isVisible}`);
            }
        }
    } catch (e) {
        console.log('Could not find link by role:', e);
    }
    
    // Try to find by text content
    console.log('\n--- Searching by text content ---');
    const textLinks = await page.locator('a:has-text("FAVCREATORS")').all();
    console.log(`Links with text "FAVCREATORS": ${textLinks.length}`);
    for (let i = 0; i < textLinks.length; i++) {
        const link = textLinks[i];
        const href = await link.getAttribute('href');
        const text = await link.innerText();
        const isVisible = await link.isVisible();
        console.log(`Link ${i + 1}: text="${text}", href="${href}", visible=${isVisible}`);
    }
    
    // Open the navigation menu if it exists
    console.log('\n--- Opening navigation menu ---');
    try {
        const navButton = page.getByTitle('Quick Navigation');
        if (await navButton.isVisible()) {
            await navButton.click();
            await page.waitForTimeout(1000);
            console.log('Navigation menu opened');
            
            // Check links in the navigation
            const navLinks = await page.locator('nav a, [class*="nav"] a').all();
            console.log(`Links in navigation: ${navLinks.length}`);
            for (const link of navLinks) {
                const href = await link.getAttribute('href');
                const text = await link.innerText();
                if (href && href.toLowerCase().includes('favcreators')) {
                    console.log(`Nav link: text="${text}", href="${href}"`);
                }
            }
        }
    } catch (e) {
        console.log('Could not open navigation menu:', e);
    }
    
    // Check the actual JavaScript chunk content
    console.log('\n--- Checking JavaScript chunk content ---');
    const response = await page.goto('https://findtorontoevents.ca/next/_next/static/chunks/a2ac3a6616d60872.js');
    if (response) {
        const jsContent = await response.text();
        const wrongUrlMatches = jsContent.match(/href:"\/favcreators\/"/g);
        const correctUrlMatches = jsContent.match(/href:"\/favcreators\/#\/guest"/g);
        console.log(`Wrong URL matches (href:"/favcreators/"): ${wrongUrlMatches ? wrongUrlMatches.length : 0}`);
        console.log(`Correct URL matches (href:"/favcreators/#/guest"): ${correctUrlMatches ? correctUrlMatches.length : 0}`);
        
        if (wrongUrlMatches && wrongUrlMatches.length > 0) {
            console.error('❌ FOUND WRONG URL IN JS CHUNK!');
            // Find context around the wrong URL
            const wrongIndex = jsContent.indexOf('href:"/favcreators/"');
            if (wrongIndex > -1) {
                const context = jsContent.substring(Math.max(0, wrongIndex - 100), Math.min(jsContent.length, wrongIndex + 200));
                console.log('Context:', context);
            }
        }
    }
    
    // Try clicking a link and see where it goes
    console.log('\n--- Testing link click behavior ---');
    try {
        const clickableLink = page.locator('a[href*="favcreators"]').first();
        if (await clickableLink.isVisible()) {
            const hrefBefore = await clickableLink.getAttribute('href');
            console.log(`Link href before click: ${hrefBefore}`);
            
            // Set up navigation listener
            const navigationPromise = page.waitForURL('**/favcreators/**', { timeout: 5000 }).catch(() => null);
            await clickableLink.click();
            const finalUrl = await navigationPromise;
            
            if (finalUrl) {
                console.log(`Final URL after click: ${finalUrl}`);
            } else {
                const currentUrl = page.url();
                console.log(`Current URL after click: ${currentUrl}`);
            }
        }
    } catch (e) {
        console.log('Could not test link click:', e);
    }
    
    // Take screenshot
    await page.screenshot({ path: 'favcreators_link_inspection.png', fullPage: true });
    console.log('\n=== INSPECTION COMPLETE ===');
});
