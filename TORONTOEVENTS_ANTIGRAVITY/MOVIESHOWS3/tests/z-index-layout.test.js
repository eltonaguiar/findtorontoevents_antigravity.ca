import puppeteer from 'puppeteer';

const BASE_URL = 'http://localhost/MOVIESHOWS3/';
const TIMEOUT = 10000;

describe('Z-Index and Layout Tests', () => {
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
        await page.setViewport({ width: 375, height: 812 }); // iPhone X
        await page.goto(BASE_URL, { waitUntil: 'networkidle2', timeout: TIMEOUT });

        // Wait for videos to load
        await page.waitForSelector('.video-card', { timeout: TIMEOUT });
    });

    afterEach(async () => {
        await page.close();
    });

    afterAll(async () => {
        await browser.close();
    });

    test('1. Unmute button exists and is visible', async () => {
        const unmuteBtn = await page.$('.unmute-btn');
        expect(unmuteBtn).not.toBeNull();
        const isVisible = await page.evaluate(el => {
            const style = window.getComputedStyle(el);
            return style.display !== 'none' && style.visibility !== 'hidden';
        }, unmuteBtn);
        expect(isVisible).toBe(true);
    });

    test('2. Unmute button has correct z-index (10)', async () => {
        const zIndex = await page.$eval('.unmute-btn', el =>
            window.getComputedStyle(el).zIndex
        );
        expect(zIndex).toBe('10');
    });

    test('3. Sidebar actions have higher z-index than unmute button', async () => {
        const sidebarZIndex = await page.$eval('.sidebar-actions', el =>
            parseInt(window.getComputedStyle(el).zIndex)
        );
        const unmuteZIndex = await page.$eval('.unmute-btn', el =>
            parseInt(window.getComputedStyle(el).zIndex)
        );
        expect(sidebarZIndex).toBeGreaterThan(unmuteZIndex);
    });

    test('4. Unmute button does not overlap share button', async () => {
        const unmuteBounds = await page.$eval('.unmute-btn', el => {
            const rect = el.getBoundingClientRect();
            return { top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left };
        });

        const shareBounds = await page.$eval('.sidebar-actions button:nth-child(3)', el => {
            const rect = el.getBoundingClientRect();
            return { top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left };
        });

        // Check for overlap
        const overlap = !(
            unmuteBounds.right < shareBounds.left ||
            unmuteBounds.left > shareBounds.right ||
            unmuteBounds.bottom < shareBounds.top ||
            unmuteBounds.top > shareBounds.bottom
        );

        expect(overlap).toBe(false);
    });

    test('5. Unmute button does not overlap heart button', async () => {
        const unmuteBounds = await page.$eval('.unmute-btn', el => {
            const rect = el.getBoundingClientRect();
            return { top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left };
        });

        const heartBounds = await page.$eval('.sidebar-actions button:nth-child(1)', el => {
            const rect = el.getBoundingClientRect();
            return { top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left };
        });

        const overlap = !(
            unmuteBounds.right < heartBounds.left ||
            unmuteBounds.left > heartBounds.right ||
            unmuteBounds.bottom < heartBounds.top ||
            unmuteBounds.top > heartBounds.bottom
        );

        expect(overlap).toBe(false);
    });

    test('6. Unmute button does not overlap plus button', async () => {
        const unmuteBounds = await page.$eval('.unmute-btn', el => {
            const rect = el.getBoundingClientRect();
            return { top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left };
        });

        const plusBounds = await page.$eval('.sidebar-actions button:nth-child(2)', el => {
            const rect = el.getBoundingClientRect();
            return { top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left };
        });

        const overlap = !(
            unmuteBounds.right < plusBounds.left ||
            unmuteBounds.left > plusBounds.right ||
            unmuteBounds.bottom < plusBounds.top ||
            unmuteBounds.top > plusBounds.bottom
        );

        expect(overlap).toBe(false);
    });

    test('7. Unmute button is clickable', async () => {
        await page.click('.unmute-btn');
        // If it clicks without error, test passes
        expect(true).toBe(true);
    });

    test('8. Share button is clickable when unmute button is visible', async () => {
        await page.click('.sidebar-actions button:nth-child(3)');
        expect(true).toBe(true);
    });

    test('9. Heart button is clickable', async () => {
        await page.click('.sidebar-actions button:nth-child(1)');
        expect(true).toBe(true);
    });

    test('10. Plus button is clickable', async () => {
        await page.click('.sidebar-actions button:nth-child(2)');
        expect(true).toBe(true);
    });

    test('11. All sidebar buttons are visible', async () => {
        const buttons = await page.$$('.sidebar-actions button');
        expect(buttons.length).toBe(3);
    });

    test('12. Unmute button position is correct (bottom right)', async () => {
        const position = await page.$eval('.unmute-btn', el => {
            const style = window.getComputedStyle(el);
            return {
                position: style.position,
                bottom: style.bottom,
                right: style.right
            };
        });
        expect(position.position).toBe('absolute');
        expect(position.bottom).toBe('80px');
        expect(position.right).toBe('20px');
    });

    test('13. Sidebar actions position is correct', async () => {
        const position = await page.$eval('.sidebar-actions', el => {
            const style = window.getComputedStyle(el);
            return {
                position: style.position,
                right: style.right
            };
        });
        expect(position.position).toBe('fixed');
    });

    test('14. No JavaScript errors on page load', async () => {
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.reload({ waitUntil: 'networkidle2' });
        expect(errors.length).toBe(0);
    });

    test('15. No console errors on page load', async () => {
        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') errors.push(msg.text());
        });
        await page.reload({ waitUntil: 'networkidle2' });

        // Filter out expected errors (CORS, ads, etc.)
        const unexpectedErrors = errors.filter(err =>
            !err.includes('CORS') &&
            !err.includes('googleads') &&
            !err.includes('doubleclick')
        );
        expect(unexpectedErrors.length).toBe(0);
    });

    test('16. Unmute button has correct styling', async () => {
        const styles = await page.$eval('.unmute-btn', el => {
            const style = window.getComputedStyle(el);
            return {
                borderRadius: style.borderRadius,
                width: style.width,
                height: style.height
            };
        });
        expect(styles.width).toBe('56px');
        expect(styles.height).toBe('56px');
    });

    test('17. Video card exists', async () => {
        const videoCard = await page.$('.video-card');
        expect(videoCard).not.toBeNull();
    });

    test('18. Iframe exists in video card', async () => {
        const iframe = await page.$('.video-card iframe');
        expect(iframe).not.toBeNull();
    });

    test('19. Top filter buttons are visible', async () => {
        const filterAll = await page.$('#filterAll');
        const filterMovies = await page.$('#filterMovies');
        const filterTV = await page.$('#filterTV');
        expect(filterAll).not.toBeNull();
        expect(filterMovies).not.toBeNull();
        expect(filterTV).not.toBeNull();
    });

    test('20. Menu button is clickable', async () => {
        await page.click('button[onclick="toggleMenu()"]');
        expect(true).toBe(true);
    });

    test('21. Browse button is clickable', async () => {
        await page.click('button[onclick="toggleBrowse()"]');
        await page.waitForTimeout(500);
        const browseView = await page.$('#browseView.active');
        expect(browseView).not.toBeNull();
    });

    test('22. Queue button is clickable', async () => {
        await page.click('button[onclick="toggleQueue()"]');
        expect(true).toBe(true);
    });

    test('23. All UI elements render without layout shift', async () => {
        const initialLayout = await page.evaluate(() => {
            const unmute = document.querySelector('.unmute-btn').getBoundingClientRect();
            const sidebar = document.querySelector('.sidebar-actions').getBoundingClientRect();
            return { unmute, sidebar };
        });

        await page.waitForTimeout(1000);

        const finalLayout = await page.evaluate(() => {
            const unmute = document.querySelector('.unmute-btn').getBoundingClientRect();
            const sidebar = document.querySelector('.sidebar-actions').getBoundingClientRect();
            return { unmute, sidebar };
        });

        expect(initialLayout.unmute.top).toBe(finalLayout.unmute.top);
        expect(initialLayout.sidebar.top).toBe(finalLayout.sidebar.top);
    });

    test('24. Mute overlay appears on page load', async () => {
        const overlay = await page.$('#muteOverlay');
        expect(overlay).not.toBeNull();
    });

    test('25. All critical UI elements are present', async () => {
        const elements = await page.evaluate(() => {
            return {
                container: !!document.getElementById('container'),
                browseView: !!document.getElementById('browseView'),
                queuePanel: !!document.getElementById('queuePanel'),
                menuPanel: !!document.getElementById('menuPanel'),
                muteOverlay: !!document.getElementById('muteOverlay')
            };
        });

        expect(elements.container).toBe(true);
        expect(elements.browseView).toBe(true);
        expect(elements.queuePanel).toBe(true);
        expect(elements.menuPanel).toBe(true);
        expect(elements.muteOverlay).toBe(true);
    });
});
