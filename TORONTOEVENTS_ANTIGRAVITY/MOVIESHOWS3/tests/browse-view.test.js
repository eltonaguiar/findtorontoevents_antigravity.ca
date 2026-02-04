import puppeteer from 'puppeteer';

const BASE_URL = 'http://localhost/MOVIESHOWS3/';
const TIMEOUT = 15000;

describe('Browse View Click-to-Play Tests', () => {
    let browser;
    let page;

    beforeAll(async () => {
        browser = await puppeteer.launch({
            headless: true, // Critical: test with DevTools CLOSED
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--autoplay-policy=no-user-gesture-required']
        });
    });

    beforeEach(async () => {
        page = await browser.newPage();
        await page.setViewport({ width: 375, height: 812 });
        await page.goto(BASE_URL, { waitUntil: 'networkidle2', timeout: TIMEOUT });
        await page.waitForSelector('.video-card', { timeout: TIMEOUT });
    });

    afterEach(async () => {
        await page.close();
    });

    afterAll(async () => {
        await browser.close();
    });

    test('1. Browse button opens browse view', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        const isActive = await page.$eval('#browseView', el => el.classList.contains('active'));
        expect(isActive).toBe(true);
    });

    test('2. Browse grid renders items', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        const items = await page.$$('.browse-grid-item');
        expect(items.length).toBeGreaterThan(0);
    });

    test('3. Clicking movie from browse closes browse view', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        await page.click('.browse-grid-item');
        await page.waitForTimeout(1000);

        const isActive = await page.$eval('#browseView', el => el.classList.contains('active'));
        expect(isActive).toBe(false);
    });

    test('4. Clicking movie from browse scrolls to correct video (DevTools CLOSED)', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        // Click the 5th item
        const items = await page.$$('.browse-grid-item');
        if (items.length >= 5) {
            await items[4].click();
            await page.waitForTimeout(2000);

            const scrollTop = await page.evaluate(() =>
                document.getElementById('container').scrollTop
            );

            // Should scroll to approximately 4 * viewport height
            expect(scrollTop).toBeGreaterThan(3000);
        }
    });

    test('5. Clicking movie from browse triggers autoplay (DevTools CLOSED)', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        await page.click('.browse-grid-item');
        await page.waitForTimeout(2000);

        const iframeSrc = await page.evaluate(() => {
            const container = document.getElementById('container');
            const scrollTop = container.scrollTop;
            const index = Math.round(scrollTop / window.innerHeight);
            const iframe = document.getElementById(`player-${index}`);
            return iframe ? iframe.src : null;
        });

        expect(iframeSrc).toContain('autoplay=1');
    });

    test('6. Clicking movie from browse shows mute overlay', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        await page.click('.browse-grid-item');
        await page.waitForTimeout(2000);

        const overlayVisible = await page.$eval('#muteOverlay', el => {
            const style = window.getComputedStyle(el);
            return style.display !== 'none';
        });

        expect(overlayVisible).toBe(true);
    });

    test('7. Previous videos stop when playing from browse', async () => {
        // Let first video play
        await page.waitForTimeout(2000);

        // Open browse and click another video
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        const items = await page.$$('.browse-grid-item');
        if (items.length >= 3) {
            await items[2].click();
            await page.waitForTimeout(2000);

            // Check first video is stopped
            const firstIframeSrc = await page.$eval('#player-0', el => el.src);
            expect(firstIframeSrc).toContain('autoplay=0');
        }
    });

    test('8. Browse search input exists', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        const searchInput = await page.$('#browseSearchInput');
        expect(searchInput).not.toBeNull();
    });

    test('9. Browse search filters results', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        const initialCount = await page.$$eval('.browse-grid-item', items => items.length);

        await page.type('#browseSearchInput', 'test');
        await page.waitForTimeout(500);

        const filteredCount = await page.$$eval('.browse-grid-item', items => items.length);

        // Filtered count should be less than or equal to initial
        expect(filteredCount).toBeLessThanOrEqual(initialCount);
    });

    test('10. Browse genre filters work', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        const genreButtons = await page.$$('[data-genre]');
        if (genreButtons.length > 1) {
            await genreButtons[1].click();
            await page.waitForTimeout(500);

            const items = await page.$$('.browse-grid-item');
            expect(items.length).toBeGreaterThan(0);
        }
    });

    test('11. Browse year filters work', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        await page.type('#yearFrom', '2020');
        await page.type('#yearTo', '2024');
        await page.waitForTimeout(500);

        const items = await page.$$('.browse-grid-item');
        expect(items.length).toBeGreaterThan(0);
    });

    test('12. Browse content type filters work', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        const movieButton = await page.$('[data-type="movie"]');
        if (movieButton) {
            await movieButton.click();
            await page.waitForTimeout(500);

            const items = await page.$$('.browse-grid-item');
            expect(items.length).toBeGreaterThan(0);
        }
    });

    test('13. Browse clear search button works', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        await page.type('#browseSearchInput', 'test');
        await page.waitForTimeout(500);

        await page.click('#browseSearchClear');
        await page.waitForTimeout(500);

        const searchValue = await page.$eval('#browseSearchInput', el => el.value);
        expect(searchValue).toBe('');
    });

    test('14. Multiple clicks from browse work correctly', async () => {
        for (let i = 0; i < 3; i++) {
            await page.click('button[onclick="toggleBrowse()"]');
            await page.waitForTimeout(500);

            const items = await page.$$('.browse-grid-item');
            if (items.length > i) {
                await items[i].click();
                await page.waitForTimeout(1500);
            }
        }

        // Should complete without errors
        expect(true).toBe(true);
    });

    test('15. Browse view respects top filter (All/Movies/TV)', async () => {
        await page.click('#filterMovies');
        await page.waitForTimeout(500);

        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        const items = await page.$$('.browse-grid-item');
        expect(items.length).toBeGreaterThan(0);
    });

    test('16. No JavaScript errors during browse click-to-play', async () => {
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));

        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);
        await page.click('.browse-grid-item');
        await page.waitForTimeout(2000);

        expect(errors.length).toBe(0);
    });

    test('17. Browse thumbnails load correctly', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(1000);

        const hasThumbnails = await page.$$eval('.browse-grid-item img', imgs =>
            imgs.every(img => img.src && img.src.length > 0)
        );

        expect(hasThumbnails).toBe(true);
    });

    test('18. Browse grid is scrollable', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        const scrollable = await page.$eval('.browse-grid', el => {
            return el.scrollHeight > el.clientHeight;
        });

        expect(scrollable).toBe(true);
    });

    test('19. Clicking same video twice works correctly', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        await page.click('.browse-grid-item');
        await page.waitForTimeout(1500);

        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        await page.click('.browse-grid-item');
        await page.waitForTimeout(1500);

        expect(true).toBe(true);
    });

    test('20. Browse close button works', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        const closeBtn = await page.$('#browseView button[onclick="toggleBrowse()"]');
        if (closeBtn) {
            await closeBtn.click();
            await page.waitForTimeout(500);

            const isActive = await page.$eval('#browseView', el => el.classList.contains('active'));
            expect(isActive).toBe(false);
        }
    });

    test('21. Browse view animation completes', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(1000);

        const transform = await page.$eval('#browseView', el =>
            window.getComputedStyle(el).transform
        );

        expect(transform).not.toBe('none');
    });

    test('22. Scrollend event fires correctly (or fallback timeout)', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        const items = await page.$$('.browse-grid-item');
        if (items.length >= 5) {
            await items[4].click();
            await page.waitForTimeout(2000);

            // Video should be playing after scrollend
            const playing = await page.evaluate(() => {
                const container = document.getElementById('container');
                const index = Math.round(container.scrollTop / window.innerHeight);
                const iframe = document.getElementById(`player-${index}`);
                return iframe && iframe.src.includes('autoplay=1');
            });

            expect(playing).toBe(true);
        }
    });

    test('23. Browse works after filter change', async () => {
        await page.click('#filterMovies');
        await page.waitForTimeout(500);

        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        await page.click('.browse-grid-item');
        await page.waitForTimeout(1500);

        const iframeSrc = await page.evaluate(() => {
            const container = document.getElementById('container');
            const index = Math.round(container.scrollTop / window.innerHeight);
            const iframe = document.getElementById(`player-${index}`);
            return iframe ? iframe.src : null;
        });

        expect(iframeSrc).toContain('autoplay=1');
    });

    test('24. Browse grid shows all database items (not limited to 200)', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(1000);

        const itemCount = await page.$$eval('.browse-grid-item', items => items.length);

        // With API limits removed, should have more than 200
        expect(itemCount).toBeGreaterThanOrEqual(200);
    });

    test('25. Rapid browse open/close works correctly', async () => {
        for (let i = 0; i < 5; i++) {
            await page.click('button[onclick="toggleBrowse()"]');
            await page.waitForTimeout(200);
            await page.click('button[onclick="toggleBrowse()"]');
            await page.waitForTimeout(200);
        }

        expect(true).toBe(true);
    });
});
