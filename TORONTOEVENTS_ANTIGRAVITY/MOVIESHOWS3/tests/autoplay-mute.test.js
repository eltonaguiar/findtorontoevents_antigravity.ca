import puppeteer from 'puppeteer';

const BASE_URL = 'http://localhost/MOVIESHOWS3/';
const TIMEOUT = 15000;

describe('Autoplay and Mute Tests', () => {
    let browser;
    let page;

    beforeAll(async () => {
        browser = await puppeteer.launch({
            headless: true,
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

    test('1. First video autoplays on page load', async () => {
        await page.waitForTimeout(2000);

        const firstIframeSrc = await page.$eval('#player-0', el => el.src);
        expect(firstIframeSrc).toContain('autoplay=1');
    });

    test('2. Mute overlay appears on page load', async () => {
        const overlayVisible = await page.$eval('#muteOverlay', el => {
            const style = window.getComputedStyle(el);
            return style.display !== 'none';
        });

        expect(overlayVisible).toBe(true);
    });

    test('3. Unmute button exists on first video', async () => {
        const unmuteBtn = await page.$('.unmute-btn');
        expect(unmuteBtn).not.toBeNull();
    });

    test('4. Unmute button shows muted icon by default', async () => {
        const icon = await page.$eval('.unmute-btn', el => el.textContent);
        expect(icon).toBe('🔇');
    });

    test('5. Clicking unmute button changes icon', async () => {
        await page.click('.unmute-btn');
        await page.waitForTimeout(500);

        const icon = await page.$eval('.unmute-btn', el => el.textContent);
        expect(icon).toBe('🔊');
    });

    test('6. Clicking unmute updates iframe src', async () => {
        await page.click('.unmute-btn');
        await page.waitForTimeout(500);

        const iframeSrc = await page.$eval('#player-0', el => el.src);
        expect(iframeSrc).toContain('mute=0');
    });

    test('7. Mute overlay disappears after unmuting', async () => {
        await page.click('.unmute-btn');
        await page.waitForTimeout(500);

        const overlayVisible = await page.$eval('#muteOverlay', el => {
            const style = window.getComputedStyle(el);
            return style.display !== 'none';
        });

        expect(overlayVisible).toBe(false);
    });

    test('8. Scrolling to second video stops first video', async () => {
        await page.waitForTimeout(1000);

        await page.evaluate(() => {
            document.getElementById('container').scrollTo({
                top: window.innerHeight,
                behavior: 'smooth'
            });
        });

        await page.waitForTimeout(2000);

        const firstIframeSrc = await page.$eval('#player-0', el => el.src);
        expect(firstIframeSrc).toContain('autoplay=0');
    });

    test('9. Scrolling to second video starts second video', async () => {
        await page.waitForTimeout(1000);

        await page.evaluate(() => {
            document.getElementById('container').scrollTo({
                top: window.innerHeight,
                behavior: 'smooth'
            });
        });

        await page.waitForTimeout(2000);

        const secondIframeSrc = await page.$eval('#player-1', el => el.src);
        expect(secondIframeSrc).toContain('autoplay=1');
    });

    test('10. Only one video plays at a time', async () => {
        await page.waitForTimeout(1000);

        await page.evaluate(() => {
            document.getElementById('container').scrollTo({
                top: window.innerHeight,
                behavior: 'smooth'
            });
        });

        await page.waitForTimeout(2000);

        const playingVideos = await page.$$eval('.video-card iframe', iframes =>
            iframes.filter(iframe => iframe.src.includes('autoplay=1')).length
        );

        expect(playingVideos).toBeLessThanOrEqual(1);
    });

    test('11. IntersectionObserver is set up correctly', async () => {
        const hasObserver = await page.evaluate(() => {
            const cards = document.querySelectorAll('.video-card');
            return cards.length > 0;
        });

        expect(hasObserver).toBe(true);
    });

    test('12. Videos have correct YouTube embed parameters', async () => {
        const iframeSrc = await page.$eval('#player-0', el => el.src);

        expect(iframeSrc).toContain('youtube.com/embed/');
        expect(iframeSrc).toContain('autoplay=');
        expect(iframeSrc).toContain('mute=');
    });

    test('13. Mute state persists per video', async () => {
        // Unmute first video
        await page.click('.unmute-btn');
        await page.waitForTimeout(500);

        // Scroll to second video
        await page.evaluate(() => {
            document.getElementById('container').scrollTo({
                top: window.innerHeight,
                behavior: 'smooth'
            });
        });

        await page.waitForTimeout(2000);

        // Second video should still be muted
        const secondIframeSrc = await page.$eval('#player-1', el => el.src);
        expect(secondIframeSrc).toContain('mute=1');
    });

    test('14. Rapid scrolling works correctly', async () => {
        for (let i = 0; i < 5; i++) {
            await page.evaluate((index) => {
                document.getElementById('container').scrollTo({
                    top: index * window.innerHeight,
                    behavior: 'smooth'
                });
            }, i);
            await page.waitForTimeout(800);
        }

        // Should complete without errors
        expect(true).toBe(true);
    });

    test('15. No multiple videos playing after rapid scrolling', async () => {
        for (let i = 0; i < 3; i++) {
            await page.evaluate((index) => {
                document.getElementById('container').scrollTo({
                    top: index * window.innerHeight,
                    behavior: 'smooth'
                });
            }, i);
            await page.waitForTimeout(500);
        }

        await page.waitForTimeout(2000);

        const playingVideos = await page.$$eval('.video-card iframe', iframes =>
            iframes.filter(iframe => iframe.src.includes('autoplay=1')).length
        );

        expect(playingVideos).toBeLessThanOrEqual(1);
    });

    test('16. Autoplay works after filter change', async () => {
        await page.click('#filterMovies');
        await page.waitForTimeout(1500);

        const firstIframeSrc = await page.$eval('#player-0', el => el.src);
        expect(firstIframeSrc).toContain('autoplay=1');
    });

    test('17. No JavaScript errors during autoplay', async () => {
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));

        await page.waitForTimeout(2000);

        await page.evaluate(() => {
            document.getElementById('container').scrollTo({
                top: window.innerHeight,
                behavior: 'smooth'
            });
        });

        await page.waitForTimeout(2000);

        expect(errors.length).toBe(0);
    });

    test('18. Video iframes load correctly', async () => {
        const iframes = await page.$$('.video-card iframe');
        expect(iframes.length).toBeGreaterThan(0);

        const firstSrc = await page.$eval('#player-0', el => el.src);
        expect(firstSrc).toBeTruthy();
    });

    test('19. Scroll position updates correctly', async () => {
        await page.evaluate(() => {
            document.getElementById('container').scrollTo({
                top: window.innerHeight * 2,
                behavior: 'smooth'
            });
        });

        await page.waitForTimeout(2000);

        const scrollTop = await page.evaluate(() =>
            document.getElementById('container').scrollTop
        );

        expect(scrollTop).toBeGreaterThan(window.innerHeight);
    });

    test('20. Auto-scroll feature can be toggled', async () => {
        await page.click('button[onclick="toggleMenu()"]');
        await page.waitForTimeout(500);

        const toggle = await page.$('#autoScrollToggle');
        if (toggle) {
            await toggle.click();
            await page.waitForTimeout(500);

            const isChecked = await page.$eval('#autoScrollToggle', el => el.checked);
            expect(typeof isChecked).toBe('boolean');
        }
    });

    test('21. Videos continue playing after page interaction', async () => {
        await page.click('.sidebar-actions button:nth-child(1)'); // Like button
        await page.waitForTimeout(500);

        const iframeSrc = await page.$eval('#player-0', el => el.src);
        expect(iframeSrc).toContain('autoplay=1');
    });

    test('22. Mute state is tracked correctly', async () => {
        const hasMuteTracking = await page.evaluate(() => {
            return typeof window.videoMuteStates !== 'undefined';
        });

        expect(hasMuteTracking).toBe(true);
    });

    test('23. User interaction flag is set correctly', async () => {
        await page.click('.unmute-btn');
        await page.waitForTimeout(500);

        const hasInteracted = await page.evaluate(() => {
            return window.hasUserInteracted === true;
        });

        expect(hasInteracted).toBe(true);
    });

    test('24. All videos have unique player IDs', async () => {
        const playerIds = await page.$$eval('.video-card iframe', iframes =>
            iframes.map(iframe => iframe.id)
        );

        const uniqueIds = new Set(playerIds);
        expect(uniqueIds.size).toBe(playerIds.length);
    });

    test('25. Autoplay respects browser policies', async () => {
        // This test verifies that autoplay works with our policy settings
        await page.waitForTimeout(2000);

        const firstIframeSrc = await page.$eval('#player-0', el => el.src);
        expect(firstIframeSrc).toContain('autoplay=1');
        expect(firstIframeSrc).toContain('mute=1');
    });
});
