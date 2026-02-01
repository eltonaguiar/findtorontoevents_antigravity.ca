import { test, expect } from '@playwright/test';

test('verify sidebar navigation links', async ({ page }) => {
    console.log('Navigating to site...');
    await page.goto('https://findtorontoevents.ca/', { waitUntil: 'networkidle' });

    // Click Quick Nav button to open sidebar
    await page.getByTitle("Quick Navigation").click();

    // Wait for sidebar
    await page.waitForTimeout(1000);

    // Check FavCreators Link
    const favLink = page.getByRole('link', { name: 'FAVCREATORS' });
    const isFavVisible = await favLink.isVisible();
    if (isFavVisible) {
        const href = await favLink.getAttribute('href');
        console.log('FavCreators HREF:', href);
        if (href !== '/favcreators/#/guest') {
            console.error('FAIL: FavCreators link is ' + href + ', expected /favcreators/#/guest');
        } else {
            console.log('PASS: FavCreators link is correct.');
        }
    } else {
        console.error('FAIL: FAVCREATORS link not visible');
    }

    // Check New Link "are your favorite creators live?"
    const liveLink = page.getByText("are your favorite creators live?");
    const isLiveVisible = await liveLink.isVisible();

    if (isLiveVisible) {
        console.log('PASS: New link FOUND.');
    } else {
        console.log('FAIL: New link NOT FOUND.');
    }

    // Scan ALL links to debug Hero Button
    console.log('--- SCANNING ALL LINKS ---');
    const allLinks = await page.getByRole('link').all();
    for (const link of allLinks) {
        const href = await link.getAttribute('href');
        const text = await link.innerText();
        if (href && (href.toLowerCase().includes('favcreators') || text.includes('App') || text.includes('Open'))) {
            console.log(`Found Link: Text='${text}', Href='${href}'`);
        }
    }
    console.log('--- END SCAN ---');

    await page.screenshot({ path: 'nav_check.png' });
});
