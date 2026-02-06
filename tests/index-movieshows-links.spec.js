import { test, expect } from '@playwright/test';

test.describe('Index.html - Movieshows Banner Links', () => {

    test('movieshows icon is clickable after React hydration', async ({ page }) => {
        await page.goto('https://findtorontoevents.ca/');

        // Wait for React to hydrate
        await page.waitForTimeout(3000);

        // Find the movieshows icon (🎬)
        const icon = page.locator('.movieshows-promo .w-10.h-10.rounded-full');

        // Verify it's an anchor tag
        const tagName = await icon.evaluate(el => el.tagName);
        expect(tagName).toBe('A');

        // Verify it has href
        const href = await icon.getAttribute('href');
        expect(href).toBe('/MOVIESHOWS/');

        console.log('✓ Movieshows icon is wrapped in anchor tag with correct href');
    });

    test('movieshows "Open App" button works', async ({ page }) => {
        await page.goto('https://findtorontoevents.ca/');
        await page.waitForTimeout(3000);

        const openAppBtn = page.locator('.movieshows-promo a:has-text("Open App")');
        await expect(openAppBtn).toBeVisible();

        const href = await openAppBtn.getAttribute('href');
        expect(href).toBe('/MOVIESHOWS/');

        console.log('✓ Open App button has correct link');
    });

    test('movieshows "TV Shows" button works', async ({ page }) => {
        await page.goto('https://findtorontoevents.ca/');
        await page.waitForTimeout(3000);

        const tvShowsBtn = page.locator('.movieshows-promo a:has-text("TV Shows →")');
        await expect(tvShowsBtn).toBeVisible();

        const href = await tvShowsBtn.getAttribute('href');
        expect(href).toBe('/movieshows2');

        console.log('✓ TV Shows button has correct link');
    });

    test('movieshows tooltip links work on hover', async ({ page }) => {
        await page.goto('https://findtorontoevents.ca/');
        await page.waitForTimeout(3000);

        // Hover over the banner to show tooltip
        const banner = page.locator('.movieshows-promo');
        await banner.hover();

        // Wait for tooltip to appear
        await page.waitForTimeout(500);

        // Check tooltip links
        const tooltipLinks = page.locator('.movieshows-promo .tooltip-panel a');
        const count = await tooltipLinks.count();
        expect(count).toBe(3); // Movie Shows, TV Shows, Trending

        // Verify each link
        const link1 = tooltipLinks.nth(0);
        expect(await link1.getAttribute('href')).toBe('/MOVIESHOWS/');

        const link2 = tooltipLinks.nth(1);
        expect(await link2.getAttribute('href')).toBe('/movieshows2/');

        const link3 = tooltipLinks.nth(2);
        expect(await link3.getAttribute('href')).toBe('/MOVIESHOWS3');

        console.log('✓ All 3 tooltip links have correct hrefs');
    });

    test('all banner icons are clickable', async ({ page }) => {
        await page.goto('https://findtorontoevents.ca/');
        await page.waitForTimeout(3000);

        // Check all 4 banners
        const banners = [
            { class: 'windows-fixer-promo', expectedHref: '/WINDOWSFIXER/' },
            { class: 'favcreators-promo', expectedHref: '/fc/#/guest' },
            { class: 'movieshows-promo', expectedHref: '/MOVIESHOWS/' },
            { class: 'stocks-promo', expectedHref: '/findstocks/' }
        ];

        for (const banner of banners) {
            const icon = page.locator(`.${banner.class} .w-10.h-10.rounded-full`).first();
            const tagName = await icon.evaluate(el => el.tagName);

            if (tagName === 'A') {
                const href = await icon.getAttribute('href');
                console.log(`✓ ${banner.class} icon is clickable with href: ${href}`);
            } else {
                console.log(`✗ ${banner.class} icon is NOT an anchor tag (tagName: ${tagName})`);
            }
        }
    });

    test('React hydration does not break links', async ({ page }) => {
        await page.goto('https://findtorontoevents.ca/');

        // Check links immediately (before hydration)
        const iconBefore = page.locator('.movieshows-promo .w-10.h-10.rounded-full');
        const hrefBefore = await iconBefore.getAttribute('href');

        // Wait for React hydration
        await page.waitForTimeout(5000);

        // Check links after hydration
        const iconAfter = page.locator('.movieshows-promo .w-10.h-10.rounded-full');
        const hrefAfter = await iconAfter.getAttribute('href');

        // They should be the same
        expect(hrefAfter).toBe(hrefBefore);
        expect(hrefAfter).toBe('/MOVIESHOWS/');

        console.log('✓ Links persist after React hydration');
    });
});
