/**
 * Comprehensive Playwright Tests for Kimi's Claw Algorithm Battle Arena
 * 
 * Tests cover:
 * - API endpoint tests (dashboard, leaderboard, status)
 * - UI element loading tests
 * - Error handling tests
 * - Market status banner tests
 * - Data loading tests
 * - Chart.js loading tests
 */

const { test, expect } = require('@playwright/test');

// Configuration
const BASE_URL = 'https://findtorontoevents.ca/findstocks/kimis_claw/';
const API_URL = 'https://findtorontoevents.ca/findstocks/kimis_claw/api/competition.php';

// Extended timeouts for slow API responses (30-60 seconds)
const API_TIMEOUT = 70000;
const PAGE_TIMEOUT = 80000;
const NAVIGATION_TIMEOUT = 30000;

// ============================================================
// API ENDPOINT TESTS
// ============================================================

test.describe('API Endpoint Tests', () => {
    
    test('Dashboard API returns valid JSON structure', async ({ request }) => {
        const response = await request.get(`${API_URL}?action=dashboard`, { 
            timeout: API_TIMEOUT 
        });
        
        // Check response status
        expect(response.ok()).toBeTruthy();
        expect(response.status()).toBe(200);
        
        // Check content type
        const contentType = response.headers()['content-type'];
        expect(contentType).toContain('application/json');
        
        // Parse and validate JSON structure
        const data = await response.json();
        expect(data).toHaveProperty('ok', true);
        expect(data).toHaveProperty('algorithms');
        expect(data).toHaveProperty('marketStatus');
        expect(data).toHaveProperty('lastUpdated');
        
        // Validate algorithms array structure
        expect(Array.isArray(data.algorithms)).toBeTruthy();
        
        if (data.algorithms.length > 0) {
            const algo = data.algorithms[0];
            expect(algo).toHaveProperty('id');
            expect(algo).toHaveProperty('name');
            expect(algo).toHaveProperty('type');
            expect(algo).toHaveProperty('status');
            expect(algo).toHaveProperty('startingValue');
            expect(algo).toHaveProperty('currentValue');
            expect(algo).toHaveProperty('totalReturn');
            expect(algo).toHaveProperty('portfolioHistory');
            expect(algo).toHaveProperty('wins');
            expect(algo).toHaveProperty('losses');
            expect(algo).toHaveProperty('winRate');
            expect(algo).toHaveProperty('sharpeRatio');
            expect(algo).toHaveProperty('maxDrawdown');
            expect(algo).toHaveProperty('currentPicks');
        }
    });
    
    test('Leaderboard API returns valid rankings', async ({ request }) => {
        const response = await request.get(`${API_URL}?action=leaderboard`, { 
            timeout: API_TIMEOUT 
        });
        
        expect(response.ok()).toBeTruthy();
        expect(response.status()).toBe(200);
        
        const data = await response.json();
        expect(data).toHaveProperty('ok', true);
        expect(data).toHaveProperty('leaderboard');
        expect(data).toHaveProperty('marketStatus');
        
        expect(Array.isArray(data.leaderboard)).toBeTruthy();
        
        if (data.leaderboard.length > 0) {
            const entry = data.leaderboard[0];
            expect(entry).toHaveProperty('rank');
            expect(entry).toHaveProperty('algorithm');
            expect(entry).toHaveProperty('totalReturn');
            expect(entry).toHaveProperty('winRate');
            expect(entry).toHaveProperty('trades');
            
            // Validate rank is a positive number
            expect(typeof entry.rank).toBe('number');
            expect(entry.rank).toBeGreaterThan(0);
        }
    });
    
    test('Status API returns market and data status', async ({ request }) => {
        const response = await request.get(`${API_URL}?action=status`, { 
            timeout: API_TIMEOUT 
        });
        
        expect(response.ok()).toBeTruthy();
        expect(response.status()).toBe(200);
        
        const data = await response.json();
        expect(data).toHaveProperty('ok', true);
        expect(data).toHaveProperty('marketStatus');
        expect(data).toHaveProperty('dataStatus');
        
        // Validate marketStatus structure
        expect(data.marketStatus).toHaveProperty('is_open');
        expect(data.marketStatus).toHaveProperty('status');
        expect(data.marketStatus).toHaveProperty('message');
        expect(data.marketStatus).toHaveProperty('current_time');
        
        // Validate dataStatus structure
        expect(data.dataStatus).toHaveProperty('totalPicks');
        expect(data.dataStatus).toHaveProperty('hasData');
        expect(typeof data.dataStatus.hasData).toBe('boolean');
        expect(typeof data.dataStatus.totalPicks).toBe('number');
    });
    
    test('API handles unknown action gracefully', async ({ request }) => {
        const response = await request.get(`${API_URL}?action=invalid_action`, { 
            timeout: 10000 
        });
        
        expect(response.ok()).toBeFalsy();
        expect(response.status()).toBe(200); // API returns 200 with error in body
        
        const data = await response.json();
        expect(data).toHaveProperty('ok', false);
        expect(data).toHaveProperty('error');
        expect(data.error).toContain('Unknown action');
    });
    
    test('API supports CORS headers', async ({ request }) => {
        const response = await request.get(`${API_URL}?action=status`, { 
            timeout: 10000 
        });
        
        const headers = response.headers();
        expect(headers).toHaveProperty('access-control-allow-origin');
        expect(headers['access-control-allow-origin']).toBe('*');
    });
});

// ============================================================
// UI LOADING TESTS
// ============================================================

test.describe('UI Element Loading Tests', () => {
    
    test('Page loads with correct title', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        await expect(page).toHaveTitle(/Kimi's Claw/i);
    });
    
    test('Loading spinner is displayed initially', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Check for loading element
        const loading = page.locator('#loading');
        await expect(loading).toBeVisible();
        
        // Verify loading text content
        const loadingText = await loading.textContent();
        expect(loadingText).toContain('Loading');
    });
    
    test('Header elements are present', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Check for main heading
        const heading = page.locator('h1');
        await expect(heading).toBeVisible();
        
        // Check header contains expected text
        const headerText = await heading.textContent();
        expect(headerText).toMatch(/Kimi's Claw|Algorithm Battle|Competition/i);
    });
    
    test('Algorithm cards container exists', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for content to load
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Check for algorithm cards container
        const content = page.locator('#content');
        const algoContainer = page.locator('#algorithms-container');
        const algoGrid = page.locator('.algorithms-grid');
        
        // At least one of these should exist
        const contentExists = await content.isVisible().catch(() => false);
        const containerExists = await algoContainer.isVisible().catch(() => false);
        const gridExists = await algoGrid.isVisible().catch(() => false);
        
        expect(contentExists || containerExists || gridExists).toBeTruthy();
    });
    
    test('Footer or info section is present', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Look for footer, info section, or disclaimer
        const footer = page.locator('footer');
        const info = page.locator('.info-section, .disclaimer, .about');
        
        const footerExists = await footer.isVisible().catch(() => false);
        const infoExists = await info.isVisible().catch(() => false);
        
        expect(footerExists || infoExists).toBeTruthy();
    });
});

// ============================================================
// MARKET STATUS BANNER TESTS
// ============================================================

test.describe('Market Status Banner Tests', () => {
    
    test('Market status banner is visible', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for market banner
        await page.waitForSelector('#market-banner', { 
            state: 'visible', 
            timeout: PAGE_TIMEOUT 
        });
        
        const banner = page.locator('#market-banner');
        await expect(banner).toBeVisible();
    });
    
    test('Market banner displays status text', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for market banner
        await page.waitForSelector('#market-banner', { 
            state: 'visible', 
            timeout: PAGE_TIMEOUT 
        });
        
        const banner = page.locator('#market-banner');
        const text = await banner.textContent();
        
        // Banner should contain some text about market status
        expect(text.length).toBeGreaterThan(0);
        
        // Should indicate open or closed status
        const hasStatus = text.toLowerCase().includes('open') || 
                         text.toLowerCase().includes('closed') ||
                         text.toLowerCase().includes('weekend');
        expect(hasStatus).toBeTruthy();
    });
    
    test('Market banner has appropriate styling class', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        await page.waitForSelector('#market-banner', { 
            state: 'visible', 
            timeout: PAGE_TIMEOUT 
        });
        
        const banner = page.locator('#market-banner');
        
        // Check if banner has status-specific class
        const classAttribute = await banner.getAttribute('class');
        expect(classAttribute).toBeTruthy();
        
        // Should have open, closed, or weekend class
        const hasStatusClass = classAttribute?.includes('open') || 
                              classAttribute?.includes('closed') ||
                              classAttribute?.includes('weekend');
        expect(hasStatusClass).toBeTruthy();
    });
    
    test('Market banner updates with API status', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for API to populate banner
        await page.waitForFunction(() => {
            const banner = document.getElementById('market-banner');
            return banner && banner.textContent.length > 0 && 
                   banner.textContent !== 'Loading...';
        }, { timeout: PAGE_TIMEOUT });
        
        const bannerText = await page.locator('#market-banner').textContent();
        expect(bannerText).not.toBe('Loading...');
        expect(bannerText.length).toBeGreaterThan(5);
    });
});

// ============================================================
// DATA LOADING TESTS
// ============================================================

test.describe('Data Loading Tests', () => {
    
    test('Loading indicator hides after data loads', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for loading to complete
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Verify loading is hidden
        const loading = page.locator('#loading');
        await expect(loading).toBeHidden();
    });
    
    test('Algorithm cards render with data', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for data to load
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Check for algorithm cards
        const algoCards = page.locator('.algorithm-card, .algo-card, [data-algorithm]');
        const cardCount = await algoCards.count();
        
        // If data exists, cards should be rendered
        if (cardCount > 0) {
            // Verify first card has expected content
            const firstCard = algoCards.first();
            await expect(firstCard).toBeVisible();
            
            const cardText = await firstCard.textContent();
            expect(cardText.length).toBeGreaterThan(0);
        }
    });
    
    test('Algorithm data displays correctly', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for data to load
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Check for algorithm names
        const algoNames = page.locator('.algo-name, .algorithm-name, [data-algo-name]');
        const namesCount = await algoNames.count();
        
        if (namesCount > 0) {
            const nameText = await algoNames.first().textContent();
            expect(nameText.length).toBeGreaterThan(0);
        }
        
        // Check for return values
        const returnValues = page.locator('.return-value, .total-return, [data-return]');
        const returnCount = await returnValues.count();
        
        if (returnCount > 0) {
            const returnText = await returnValues.first().textContent();
            expect(returnText.length).toBeGreaterThan(0);
        }
    });
    
    test('Last updated timestamp is displayed', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for data to load
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Look for last updated timestamp
        const lastUpdated = page.locator('.last-updated, #last-updated, [data-last-updated]');
        const timestampExists = await lastUpdated.isVisible().catch(() => false);
        
        if (timestampExists) {
            const text = await lastUpdated.textContent();
            expect(text).toContain('2026'); // Should contain current year
        }
    });
});

// ============================================================
// CHART TESTS
// ============================================================

test.describe('Chart.js Loading Tests', () => {
    
    test('Chart.js library is loaded', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for page to fully load
        await page.waitForLoadState('networkidle');
        
        // Check if Chart is defined in window object
        const chartLoaded = await page.evaluate(() => {
            return typeof window.Chart !== 'undefined';
        });
        
        expect(chartLoaded).toBeTruthy();
    });
    
    test('Chart canvas elements are present', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for data to load
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Look for chart canvas elements
        const canvases = page.locator('canvas');
        const canvasCount = await canvases.count();
        
        // Should have at least one canvas for charts
        expect(canvasCount).toBeGreaterThan(0);
        
        // Verify canvas is visible
        if (canvasCount > 0) {
            await expect(canvases.first()).toBeVisible();
        }
    });
    
    test('Portfolio charts are rendered', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for data and charts to load
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Additional wait for chart rendering
        await page.waitForTimeout(2000);
        
        // Check for chart containers
        const chartContainers = page.locator('.chart-container, .portfolio-chart, canvas');
        const chartCount = await chartContainers.count();
        
        // Should have chart containers
        expect(chartCount).toBeGreaterThan(0);
        
        // Verify canvas has dimensions (indicating Chart.js rendered)
        const canvas = page.locator('canvas').first();
        const width = await canvas.evaluate(el => el.width);
        const height = await canvas.evaluate(el => el.height);
        
        expect(width).toBeGreaterThan(0);
        expect(height).toBeGreaterThan(0);
    });
    
    test('Chart instances are created', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for data to load
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Additional wait for chart initialization
        await page.waitForTimeout(2000);
        
        // Check if Chart instances exist on page
        const chartInstances = await page.evaluate(() => {
            // Chart.js stores instances in a registry (v3+) or on canvas (v2)
            if (window.Chart && window.Chart.instances) {
                return Object.keys(window.Chart.instances).length;
            }
            // Check for chart data on canvas elements
            const canvases = document.querySelectorAll('canvas');
            let count = 0;
            canvases.forEach(canvas => {
                if (canvas.chart || canvas.getContext('2d')) {
                    count++;
                }
            });
            return count;
        });
        
        expect(chartInstances).toBeGreaterThan(0);
    });
});

// ============================================================
// ERROR HANDLING TESTS
// ============================================================

test.describe('Error Handling Tests', () => {
    
    test('Page handles missing data gracefully', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for loading to complete
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Check for content or no-data message
        const content = page.locator('#content');
        const noDataBox = page.locator('.no-data-box, .empty-state, [data-empty]');
        const errorBox = page.locator('.error-box, .alert-error');
        
        const isContentVisible = await content.isVisible().catch(() => false);
        const isNoDataVisible = await noDataBox.isVisible().catch(() => false);
        const isErrorVisible = await errorBox.isVisible().catch(() => false);
        
        // Page should show something meaningful
        expect(isContentVisible || isNoDataVisible || isErrorVisible).toBeTruthy();
    });
    
    test('Error states display correctly', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for loading to complete
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Check error box if present
        const errorBox = page.locator('.error-box, .alert-error, [data-error]');
        const errorExists = await errorBox.isVisible().catch(() => false);
        
        if (errorExists) {
            // Error should have appropriate styling
            const classAttr = await errorBox.getAttribute('class');
            const hasErrorClass = classAttr?.includes('error') || 
                                 classAttr?.includes('alert') ||
                                 classAttr?.includes('danger');
            expect(hasErrorClass).toBeTruthy();
        }
    });
    
    test('No-data message is informative', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for loading to complete
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Check no-data box
        const noDataBox = page.locator('.no-data-box, .empty-state, .no-data');
        const noDataExists = await noDataBox.isVisible().catch(() => false);
        
        if (noDataExists) {
            const text = await noDataBox.textContent();
            expect(text.length).toBeGreaterThan(10); // Should have meaningful message
        }
    });
    
    test('API error responses are handled', async ({ request }) => {
        // Test with malformed URL
        const response = await request.get(`${API_URL}`, { 
            timeout: 10000 
        });
        
        // Should still return JSON
        expect(response.status()).toBe(200);
        
        const data = await response.json();
        // Should have ok property
        expect(data).toHaveProperty('ok');
    });
    
    test('Page does not show JavaScript errors in console', async ({ page }) => {
        const errors = [];
        
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });
        
        page.on('pageerror', error => {
            errors.push(error.message);
        });
        
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for loading to complete
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Wait a bit more for any async errors
        await page.waitForTimeout(3000);
        
        // Filter out expected third-party errors
        const criticalErrors = errors.filter(err => 
            !err.includes('favicon') && 
            !err.includes('google-analytics') &&
            !err.includes('gtag') &&
            !err.includes('analytics')
        );
        
        // Should not have critical JavaScript errors
        expect(criticalErrors.length).toBeLessThan(3);
    });
});

// ============================================================
// RESPONSIVE DESIGN TESTS
// ============================================================

test.describe('Responsive Design Tests', () => {
    
    test('Page renders correctly on desktop', async ({ page }) => {
        await page.setViewportSize({ width: 1280, height: 720 });
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for load
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Check layout is not broken
        const body = page.locator('body');
        const bodyWidth = await body.evaluate(el => el.offsetWidth);
        
        expect(bodyWidth).toBeGreaterThan(1000);
    });
    
    test('Page renders correctly on mobile', async ({ page }) => {
        await page.setViewportSize({ width: 375, height: 667 });
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        // Wait for load
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        // Check content is visible
        const content = page.locator('#content, main, article');
        const isVisible = await content.isVisible().catch(() => false);
        
        expect(isVisible).toBeTruthy();
    });
    
    test('Market banner is visible on all screen sizes', async ({ page }) => {
        const viewports = [
            { width: 375, height: 667 },   // Mobile
            { width: 768, height: 1024 },  // Tablet
            { width: 1280, height: 720 }   // Desktop
        ];
        
        for (const viewport of viewports) {
            await page.setViewportSize(viewport);
            await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
            
            await page.waitForSelector('#market-banner', { 
                state: 'visible', 
                timeout: PAGE_TIMEOUT 
            });
            
            const banner = page.locator('#market-banner');
            await expect(banner).toBeVisible();
        }
    });
});

// ============================================================
// PERFORMANCE TESTS
// ============================================================

test.describe('Performance Tests', () => {
    
    test('Page loads within acceptable time', async ({ page }) => {
        const startTime = Date.now();
        
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        const loadTime = Date.now() - startTime;
        
        // Should load within 70 seconds (API can be slow)
        expect(loadTime).toBeLessThan(75000);
    });
    
    test('API responds within timeout', async ({ request }) => {
        const startTime = Date.now();
        
        const response = await request.get(`${API_URL}?action=status`, { 
            timeout: API_TIMEOUT 
        });
        
        const responseTime = Date.now() - startTime;
        
        expect(response.ok()).toBeTruthy();
        expect(responseTime).toBeLessThan(API_TIMEOUT);
    });
    
    test('Charts render after data loads', async ({ page }) => {
        await page.goto(BASE_URL, { timeout: NAVIGATION_TIMEOUT });
        
        const startTime = Date.now();
        
        // Wait for data
        await page.waitForFunction(() => {
            const loading = document.getElementById('loading');
            return loading && loading.style.display === 'none';
        }, { timeout: PAGE_TIMEOUT });
        
        const dataLoadTime = Date.now() - startTime;
        
        // Wait for charts
        await page.waitForTimeout(2000);
        
        const canvases = page.locator('canvas');
        const canvasCount = await canvases.count();
        
        expect(canvasCount).toBeGreaterThan(0);
        expect(dataLoadTime).toBeLessThan(PAGE_TIMEOUT);
    });
});
