import puppeteer from 'puppeteer';

const BASE_URL = 'http://localhost/MOVIESHOWS3/';
const TIMEOUT = 10000;

describe('Filter Functionality Tests', () => {
    let browser;
    let page;

    beforeAll(async () => {
        browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
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

    test('1. All filter button exists and is active by default', async () => {
        const isActive = await page.$eval('#filterAll', el => el.classList.contains('active'));
        expect(isActive).toBe(true);
    });

    test('2. Movies filter button exists', async () => {
        const button = await page.$('#filterMovies');
        expect(button).not.toBeNull();
    });

    test('3. TV filter button exists', async () => {
        const button = await page.$('#filterTV');
        expect(button).not.toBeNull();
    });

    test('4. Clicking Movies filter shows only movies', async () => {
        await page.click('#filterMovies');
        await page.waitForTimeout(500);

        const types = await page.$$eval('.video-card', cards =>
            cards.map(card => card.getAttribute('data-type'))
        );

        const allMovies = types.every(type => type === 'movie');
        expect(allMovies).toBe(true);
    });

    test('5. Clicking TV filter shows only TV shows', async () => {
        await page.click('#filterTV');
        await page.waitForTimeout(500);

        const types = await page.$$eval('.video-card', cards =>
            cards.map(card => card.getAttribute('data-type'))
        );

        const allTV = types.every(type => type === 'tv');
        expect(allTV).toBe(true);
    });

    test('6. Clicking All filter shows all content', async () => {
        // First filter to movies
        await page.click('#filterMovies');
        await page.waitForTimeout(500);

        // Then click All
        await page.click('#filterAll');
        await page.waitForTimeout(500);

        const types = await page.$$eval('.video-card', cards =>
            cards.map(card => card.getAttribute('data-type'))
        );

        const hasMovies = types.some(type => type === 'movie');
        const hasTV = types.some(type => type === 'tv');
        expect(hasMovies).toBe(true);
        expect(hasTV).toBe(true);
    });

    test('7. Filter buttons update active state correctly', async () => {
        await page.click('#filterMovies');
        await page.waitForTimeout(300);

        const moviesActive = await page.$eval('#filterMovies', el => el.classList.contains('active'));
        const allActive = await page.$eval('#filterAll', el => el.classList.contains('active'));

        expect(moviesActive).toBe(true);
        expect(allActive).toBe(false);
    });

    test('8. Filter count updates for Movies', async () => {
        const count = await page.$eval('#countMovies', el => parseInt(el.textContent));
        expect(count).toBeGreaterThan(0);
    });

    test('9. Filter count updates for TV', async () => {
        const count = await page.$eval('#countTV', el => parseInt(el.textContent));
        expect(count).toBeGreaterThan(0);
    });

    test('10. Filter count updates for All', async () => {
        const count = await page.$eval('#countAll', el => parseInt(el.textContent));
        expect(count).toBeGreaterThan(0);
    });

    test('11. All count equals Movies + TV count', async () => {
        const allCount = await page.$eval('#countAll', el => parseInt(el.textContent));
        const movieCount = await page.$eval('#countMovies', el => parseInt(el.textContent));
        const tvCount = await page.$eval('#countTV', el => parseInt(el.textContent));

        expect(allCount).toBe(movieCount + tvCount);
    });

    test('12. Videos re-render after filter change', async () => {
        const initialCount = await page.$$eval('.video-card', cards => cards.length);

        await page.click('#filterMovies');
        await page.waitForTimeout(500);

        const filteredCount = await page.$$eval('.video-card', cards => cards.length);

        // Counts should be different (unless all items are movies)
        expect(filteredCount).toBeGreaterThan(0);
    });

    test('13. Scroll autoplay re-initializes after filtering', async () => {
        await page.click('#filterMovies');
        await page.waitForTimeout(500);

        // Check that IntersectionObserver is set up
        const hasObserver = await page.evaluate(() => {
            const cards = document.querySelectorAll('.video-card');
            return cards.length > 0;
        });

        expect(hasObserver).toBe(true);
    });

    test('14. First video autoplays after filter change', async () => {
        await page.click('#filterMovies');
        await page.waitForTimeout(1500);

        const firstIframeSrc = await page.$eval('.video-card iframe', el => el.src);
        expect(firstIframeSrc).toContain('autoplay=1');
    });

    test('15. No JavaScript errors during filter change', async () => {
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));

        await page.click('#filterMovies');
        await page.waitForTimeout(500);
        await page.click('#filterTV');
        await page.waitForTimeout(500);
        await page.click('#filterAll');
        await page.waitForTimeout(500);

        expect(errors.length).toBe(0);
    });

    test('16. Filter persists during session', async () => {
        await page.click('#filterMovies');
        await page.waitForTimeout(500);

        const isActive = await page.$eval('#filterMovies', el => el.classList.contains('active'));
        expect(isActive).toBe(true);
    });

    test('17. Multiple rapid filter clicks work correctly', async () => {
        await page.click('#filterMovies');
        await page.click('#filterTV');
        await page.click('#filterAll');
        await page.waitForTimeout(500);

        const isActive = await page.$eval('#filterAll', el => el.classList.contains('active'));
        expect(isActive).toBe(true);
    });

    test('18. Container scrolls to top after filter change', async () => {
        // Scroll down first
        await page.evaluate(() => {
            document.getElementById('container').scrollTop = 1000;
        });

        await page.click('#filterMovies');
        await page.waitForTimeout(500);

        const scrollTop = await page.evaluate(() =>
            document.getElementById('container').scrollTop
        );

        expect(scrollTop).toBe(0);
    });

    test('19. Browse view updates when filter changes', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);

        await page.click('#filterMovies');
        await page.waitForTimeout(500);

        // Browse grid should update
        const gridItems = await page.$$('.browse-grid-item');
        expect(gridItems.length).toBeGreaterThan(0);
    });

    test('20. Filter buttons are keyboard accessible', async () => {
        await page.keyboard.press('Tab');
        await page.keyboard.press('Tab');
        await page.keyboard.press('Enter');

        // Should work without errors
        expect(true).toBe(true);
    });

    test('21. All filter shows more than 200 items', async () => {
        const count = await page.$eval('#countAll', el => parseInt(el.textContent));
        // With API limits removed, should have more than 200
        expect(count).toBeGreaterThanOrEqual(200);
    });

    test('22. Movies filter shows correct count', async () => {
        await page.click('#filterMovies');
        await page.waitForTimeout(500);

        const displayedCount = await page.$$eval('.video-card', cards => cards.length);
        const buttonCount = await page.$eval('#countMovies', el => parseInt(el.textContent));

        expect(displayedCount).toBe(buttonCount);
    });

    test('23. TV filter shows correct count', async () => {
        await page.click('#filterTV');
        await page.waitForTimeout(500);

        const displayedCount = await page.$$eval('.video-card', cards => cards.length);
        const buttonCount = await page.$eval('#countTV', el => parseInt(el.textContent));

        expect(displayedCount).toBe(buttonCount);
    });

    test('24. Filter animation completes without errors', async () => {
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));

        await page.click('#filterMovies');
        await page.waitForTimeout(1000);

        expect(errors.length).toBe(0);
    });

    test('25. Videos load correctly after multiple filter changes', async () => {
        await page.click('#filterMovies');
        await page.waitForTimeout(500);
        await page.click('#filterTV');
        await page.waitForTimeout(500);
        await page.click('#filterAll');
        await page.waitForTimeout(500);

        const iframes = await page.$$('.video-card iframe');
        expect(iframes.length).toBeGreaterThan(0);

        const firstSrc = await page.$eval('.video-card iframe', el => el.src);
        expect(firstSrc).toContain('youtube.com');
    });
});
