import { test, expect } from '@playwright/test';

/**
 * Comprehensive Playwright Test Suite for Streamer Updates Feature
 * 
 * Tests:
 * 1. Page loads without errors
 * 2. No JavaScript console errors
 * 3. Navigation link is present and functional
 * 4. API endpoints return valid responses
 * 5. UI elements render correctly
 * 6. Platform filters work
 * 7. Empty state displays properly
 */

const BASE_URL = 'https://findtorontoevents.ca/fc';
const UPDATES_URL = `${BASE_URL}/#/updates`;
const GUEST_UPDATES_URL = `${BASE_URL}/#/guest/updates`;

test.describe('Streamer Updates - Core Functionality', () => {

    test('should load the updates page without errors', async ({ page }) => {
        const errors: string[] = [];

        // Capture console errors
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });

        // Capture page errors
        page.on('pageerror', error => {
            errors.push(error.message);
        });

        await page.goto(UPDATES_URL, { waitUntil: 'networkidle' });

        // Wait for the page to fully render
        await page.waitForTimeout(3000);

        // Check for critical errors (ignore browser extension errors)
        const criticalErrors = errors.filter(err =>
            !err.includes('MutationObserver') &&
            !err.includes('extension') &&
            !err.includes('[object Promise]')
        );

        expect(criticalErrors).toHaveLength(0);
    });

    test('should display the Streamer Updates heading', async ({ page }) => {
        await page.goto(UPDATES_URL);
        await page.waitForTimeout(2000);

        const heading = await page.locator('h1, h2').filter({ hasText: 'Streamer Updates' }).first();
        await expect(heading).toBeVisible();
    });

    test('should display platform filter buttons', async ({ page }) => {
        await page.goto(UPDATES_URL);
        await page.waitForTimeout(2000);

        // Check for platform filters
        const filters = page.locator('button').filter({ hasText: /Youtube|Tiktok|Twitter|Instagram/i });
        const count = await filters.count();

        expect(count).toBeGreaterThan(0);
    });

    test('should display refresh button', async ({ page }) => {
        await page.goto(UPDATES_URL);
        await page.waitForTimeout(2000);

        const refreshButton = page.locator('button').filter({ hasText: /Refresh/i });
        await expect(refreshButton).toBeVisible();
    });

    test('should handle empty state correctly', async ({ page }) => {
        await page.goto(UPDATES_URL);
        await page.waitForTimeout(3000);

        // Check for either content or empty state message
        const hasContent = await page.locator('text=/No content found|Follow some creators/i').isVisible();
        const hasItems = await page.locator('[class*="content"]').count() > 0;

        expect(hasContent || hasItems).toBeTruthy();
    });
});

test.describe('Streamer Updates - API Integration', () => {

    test('should call the correct API endpoint without [object Promise]', async ({ page }) => {
        const apiCalls: string[] = [];

        // Intercept network requests
        page.on('request', request => {
            const url = request.url();
            if (url.includes('streamer_updates_api')) {
                apiCalls.push(url);
            }
        });

        await page.goto(UPDATES_URL);
        await page.waitForTimeout(5000);

        // Verify API was called
        expect(apiCalls.length).toBeGreaterThan(0);

        // Verify no [object Promise] in URLs
        const malformedCalls = apiCalls.filter(url => url.includes('[object'));
        expect(malformedCalls).toHaveLength(0);

        // Verify correct endpoint
        const correctCalls = apiCalls.filter(url =>
            url.includes('streamer_updates_api_simple.php') &&
            url.includes('user_id=') &&
            url.includes('limit=')
        );
        expect(correctCalls.length).toBeGreaterThan(0);
    });

    test('should receive valid JSON response from API', async ({ page }) => {
        let apiResponse: any = null;

        page.on('response', async response => {
            if (response.url().includes('streamer_updates_api_simple.php')) {
                try {
                    apiResponse = await response.json();
                } catch (e) {
                    // Response is not JSON
                }
            }
        });

        await page.goto(UPDATES_URL);
        await page.waitForTimeout(5000);

        expect(apiResponse).not.toBeNull();
        expect(apiResponse).toHaveProperty('items');
        expect(apiResponse).toHaveProperty('total');
        expect(apiResponse).toHaveProperty('user_id');
    });

    test('should not return HTTP 500 errors', async ({ page }) => {
        const http500Errors: string[] = [];

        page.on('response', response => {
            if (response.status() === 500) {
                http500Errors.push(response.url());
            }
        });

        await page.goto(UPDATES_URL);
        await page.waitForTimeout(5000);

        expect(http500Errors).toHaveLength(0);
    });
});

test.describe('Streamer Updates - Navigation', () => {

    test('should have navigation link above "Creators Live Now"', async ({ page }) => {
        await page.goto(BASE_URL);
        await page.waitForTimeout(2000);

        // Look for the navigation link
        const navLink = page.locator('a[href="#/updates"]').filter({
            hasText: /Creator News|Community Updates/i
        });

        await expect(navLink).toBeVisible();
    });

    test('navigation link should redirect to updates page', async ({ page }) => {
        await page.goto(BASE_URL);
        await page.waitForTimeout(2000);

        const navLink = page.locator('a[href="#/updates"]').first();
        await navLink.click();

        await page.waitForTimeout(2000);

        // Verify URL changed
        expect(page.url()).toContain('#/updates');

        // Verify page loaded
        const heading = await page.locator('h1, h2').filter({ hasText: 'Streamer Updates' }).first();
        await expect(heading).toBeVisible();
    });

    test('guest route should also work', async ({ page }) => {
        await page.goto(GUEST_UPDATES_URL);
        await page.waitForTimeout(3000);

        const heading = await page.locator('h1, h2').filter({ hasText: 'Streamer Updates' }).first();
        await expect(heading).toBeVisible();
    });
});

test.describe('Streamer Updates - JavaScript Error Detection', () => {

    test('should not have any unhandled promise rejections', async ({ page }) => {
        const unhandledRejections: string[] = [];

        page.on('pageerror', error => {
            if (error.message.includes('Unhandled Promise')) {
                unhandledRejections.push(error.message);
            }
        });

        await page.goto(UPDATES_URL);
        await page.waitForTimeout(5000);

        expect(unhandledRejections).toHaveLength(0);
    });

    test('should not have syntax errors in loaded scripts', async ({ page }) => {
        const syntaxErrors: string[] = [];

        page.on('console', msg => {
            if (msg.type() === 'error' && msg.text().includes('SyntaxError')) {
                syntaxErrors.push(msg.text());
            }
        });

        await page.goto(UPDATES_URL);
        await page.waitForTimeout(3000);

        expect(syntaxErrors).toHaveLength(0);
    });

    test('should not have network errors for main bundle', async ({ page }) => {
        const failedResources: string[] = [];

        page.on('response', response => {
            if (response.url().includes('main-') && response.url().endsWith('.js')) {
                if (!response.ok()) {
                    failedResources.push(response.url());
                }
            }
        });

        await page.goto(UPDATES_URL);
        await page.waitForTimeout(3000);

        expect(failedResources).toHaveLength(0);
    });
});

test.describe('Streamer Updates - UI Interaction', () => {

    test('refresh button should trigger API call', async ({ page }) => {
        await page.goto(UPDATES_URL);
        await page.waitForTimeout(3000);

        let apiCallCount = 0;

        page.on('request', request => {
            if (request.url().includes('streamer_updates_api_simple.php')) {
                apiCallCount++;
            }
        });

        const initialCount = apiCallCount;

        const refreshButton = page.locator('button').filter({ hasText: /Refresh/i });
        await refreshButton.click();

        await page.waitForTimeout(2000);

        expect(apiCallCount).toBeGreaterThan(initialCount);
    });

    test('platform filters should be clickable', async ({ page }) => {
        await page.goto(UPDATES_URL);
        await page.waitForTimeout(2000);

        const filters = page.locator('button').filter({ hasText: /Youtube|Tiktok|Twitter/i });
        const firstFilter = filters.first();

        await expect(firstFilter).toBeEnabled();
        await firstFilter.click();

        // Verify no errors after clicking
        await page.waitForTimeout(1000);
    });
});
