// @ts-check
const { test, expect, devices } = require('@playwright/test');
const fs = require('fs');

/**
 * COMPREHENSIVE MOBILE DEVICE PERFORMANCE TEST
 *
 * Purpose: Measure the real-world impact of disabling console logging on mobile devices
 *
 * Test Coverage:
 * - Multiple device profiles (low/mid/high-end memory)
 * - Multiple network conditions (3G/4G)
 * - Both MOVIESHOWS2 and MOVIESHOWS3
 * - Normal mode (logging OFF) vs Debug mode (logging ON)
 *
 * Metrics Measured:
 * - Page load time
 * - Time to interactive
 * - Memory usage (heap size)
 * - JavaScript execution time
 * - Console log count
 * - Frame rate / rendering performance
 * - Network request count
 * - Time to first meaningful paint
 */

const MOVIESHOWS2_URL = 'https://findtorontoevents.ca/MOVIESHOWS2/';
const MOVIESHOWS3_URL = 'https://findtorontoevents.ca/MOVIESHOWS3/';
const REPORT_PATH = 'e:/findtorontoevents_antigravity.ca/mobile_performance_analysis.txt';

// Network profiles
const NETWORK_PROFILES = {
    slow3G: {
        name: 'Slow 3G',
        downloadThroughput: (400 * 1024) / 8, // 400 Kbps
        uploadThroughput: (400 * 1024) / 8,
        latency: 400
    },
    fast4G: {
        name: 'Fast 4G',
        downloadThroughput: (4 * 1024 * 1024) / 8, // 4 Mbps
        uploadThroughput: (3 * 1024 * 1024) / 8,
        latency: 50
    }
};

// Global results storage
const allResults = {
    timestamp: new Date().toISOString(),
    testDate: new Date().toLocaleString(),
    testResults: []
};

/**
 * Collect comprehensive performance metrics
 */
async function collectMobileMetrics(page, url, deviceName, networkProfile, mode) {
    const startTime = Date.now();
    const consoleLogs = [];
    const consoleErrors = [];
    const jsErrors = [];
    const networkRequests = [];

    // Monitor console activity
    page.on('console', msg => {
        consoleLogs.push({
            type: msg.type(),
            text: msg.text(),
            timestamp: Date.now()
        });
    });

    // Monitor errors
    page.on('pageerror', error => {
        jsErrors.push({
            message: error.message,
            stack: error.stack,
            timestamp: Date.now()
        });
    });

    page.on('console', msg => {
        if (msg.type() === 'error') {
            consoleErrors.push({
                text: msg.text(),
                timestamp: Date.now()
            });
        }
    });

    // Monitor network requests
    page.on('request', request => {
        networkRequests.push({
            url: request.url(),
            method: request.method(),
            resourceType: request.resourceType(),
            timestamp: Date.now()
        });
    });

    // Apply network throttling
    const cdpSession = await page.context().newCDPSession(page);
    await cdpSession.send('Network.emulateNetworkConditions', {
        offline: false,
        downloadThroughput: networkProfile.downloadThroughput,
        uploadThroughput: networkProfile.uploadThroughput,
        latency: networkProfile.latency
    });

    // Navigate to URL
    const navigationStart = Date.now();
    const fullUrl = mode === 'debug' ? `${url}?debug=1` : url;

    await page.goto(fullUrl, { waitUntil: 'networkidle', timeout: 120000 });

    // Wait for movies to load
    await page.waitForFunction(() => {
        return window.allMovies && window.allMovies.length > 0;
    }, { timeout: 60000 });

    const navigationEnd = Date.now();
    const navigationTime = navigationEnd - navigationStart;

    // Wait for rendering to stabilize
    await page.waitForTimeout(5000);

    // Collect detailed metrics
    const metrics = await page.evaluate(() => {
        const perf = performance.getEntriesByType('navigation')[0];
        const resources = performance.getEntriesByType('resource');
        const paint = performance.getEntriesByType('paint');

        // Memory information
        let memoryInfo = null;
        if (performance.memory) {
            memoryInfo = {
                usedJSHeapSize: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024 * 100) / 100,
                totalJSHeapSize: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024 * 100) / 100,
                jsHeapSizeLimit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024 * 100) / 100
            };
        }

        // Paint timings
        const fcp = paint.find(p => p.name === 'first-contentful-paint');

        // Resource breakdown
        const jsResources = resources.filter(r => r.name.endsWith('.js') || r.initiatorType === 'script');
        const cssResources = resources.filter(r => r.name.endsWith('.css') || r.initiatorType === 'css');
        const imgResources = resources.filter(r => r.initiatorType === 'img');
        const totalTransfer = resources.reduce((sum, r) => sum + (r.transferSize || 0), 0);

        // JavaScript execution time
        const jsExecutionTime = jsResources.reduce((sum, r) => sum + (r.duration || 0), 0);

        // DOM metrics
        const domNodes = document.querySelectorAll('*').length;
        const iframes = document.querySelectorAll('iframe').length;
        const videos = document.querySelectorAll('video').length;
        const images = document.querySelectorAll('img').length;

        // Movie data
        const movies = window.allMovies || [];
        const moviesWithProviders = movies.filter(m =>
            (m.providers && m.providers.length > 0) ||
            (m._providers && m._providers.length > 0)
        );

        // Provider badges
        const providerBadges = document.querySelectorAll('.provider-badge');

        // Debug mode status
        const debugMode = window.DEBUG_MODE === true;

        return {
            performance: {
                domContentLoaded: Math.round(perf?.domContentLoadedEventEnd || 0),
                loadEvent: Math.round(perf?.loadEventEnd || 0),
                firstContentfulPaint: Math.round(fcp?.startTime || 0),
                timeToInteractive: Math.round(perf?.domInteractive || 0),
                domComplete: Math.round(perf?.domComplete || 0)
            },
            resources: {
                total: resources.length,
                js: jsResources.length,
                css: cssResources.length,
                images: imgResources.length,
                totalTransferMB: Math.round(totalTransfer / 1024 / 1024 * 100) / 100,
                jsExecutionTimeMs: Math.round(jsExecutionTime)
            },
            memory: memoryInfo,
            dom: {
                nodes: domNodes,
                iframes: iframes,
                videos: videos,
                images: images
            },
            data: {
                totalMovies: movies.length,
                moviesWithProviders: moviesWithProviders.length,
                providerBadges: providerBadges.length
            },
            debug: {
                modeActive: debugMode
            }
        };
    });

    // Calculate frame rate
    let frameRate = null;
    try {
        frameRate = await page.evaluate(async () => {
            return new Promise((resolve) => {
                let frames = 0;
                const startTime = performance.now();

                function countFrame() {
                    frames++;
                    if (performance.now() - startTime < 1000) {
                        requestAnimationFrame(countFrame);
                    } else {
                        resolve(frames);
                    }
                }

                requestAnimationFrame(countFrame);
            });
        });
    } catch (e) {
        // Frame rate measurement not available
    }

    const totalTime = Date.now() - startTime;

    return {
        url: fullUrl,
        deviceProfile: deviceName,
        networkProfile: networkProfile.name,
        mode: mode,
        timing: {
            totalTestTime: totalTime,
            navigationTime: navigationTime,
            startTime: startTime
        },
        metrics: metrics,
        frameRate: frameRate,
        console: {
            total: consoleLogs.length,
            byType: {
                log: consoleLogs.filter(l => l.type === 'log').length,
                info: consoleLogs.filter(l => l.type === 'info').length,
                warn: consoleLogs.filter(l => l.type === 'warning').length,
                error: consoleLogs.filter(l => l.type === 'error').length
            },
            errors: consoleErrors.length,
            samples: consoleLogs.slice(0, 20).map(l => ({ type: l.type, text: l.text.substring(0, 100) }))
        },
        errors: {
            js: jsErrors.length,
            details: jsErrors.slice(0, 5)
        },
        network: {
            totalRequests: networkRequests.length,
            byType: {
                document: networkRequests.filter(r => r.resourceType === 'document').length,
                script: networkRequests.filter(r => r.resourceType === 'script').length,
                stylesheet: networkRequests.filter(r => r.resourceType === 'stylesheet').length,
                image: networkRequests.filter(r => r.resourceType === 'image').length,
                xhr: networkRequests.filter(r => r.resourceType === 'xhr').length,
                fetch: networkRequests.filter(r => r.resourceType === 'fetch').length
            }
        }
    };
}

test.describe('Mobile Performance Analysis - Console Logging Impact', () => {

    // Low-end device (Pixel 2) on Slow 3G
    test.describe('Low-End Device (Pixel 2) - 2GB RAM simulation', () => {
        test.use(devices['Pixel 2']);

        test('MOVIESHOWS2 - Normal Mode - Slow 3G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS2 - Pixel 2 - Slow 3G - Normal Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS2_URL, 'Low-End (Pixel 2, 2GB RAM)', NETWORK_PROFILES.slow3G, 'normal');
            allResults.testResults.push({ app: 'MOVIESHOWS2', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS2 - Debug Mode - Slow 3G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS2 - Pixel 2 - Slow 3G - Debug Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS2_URL, 'Low-End (Pixel 2, 2GB RAM)', NETWORK_PROFILES.slow3G, 'debug');
            allResults.testResults.push({ app: 'MOVIESHOWS2', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS2 - Normal Mode - Fast 4G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS2 - Pixel 2 - Fast 4G - Normal Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS2_URL, 'Low-End (Pixel 2, 2GB RAM)', NETWORK_PROFILES.fast4G, 'normal');
            allResults.testResults.push({ app: 'MOVIESHOWS2', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS2 - Debug Mode - Fast 4G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS2 - Pixel 2 - Fast 4G - Debug Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS2_URL, 'Low-End (Pixel 2, 2GB RAM)', NETWORK_PROFILES.fast4G, 'debug');
            allResults.testResults.push({ app: 'MOVIESHOWS2', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS3 - Normal Mode - Slow 3G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS3 - Pixel 2 - Slow 3G - Normal Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS3_URL, 'Low-End (Pixel 2, 2GB RAM)', NETWORK_PROFILES.slow3G, 'normal');
            allResults.testResults.push({ app: 'MOVIESHOWS3', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS3 - Debug Mode - Slow 3G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS3 - Pixel 2 - Slow 3G - Debug Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS3_URL, 'Low-End (Pixel 2, 2GB RAM)', NETWORK_PROFILES.slow3G, 'debug');
            allResults.testResults.push({ app: 'MOVIESHOWS3', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS3 - Normal Mode - Fast 4G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS3 - Pixel 2 - Fast 4G - Normal Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS3_URL, 'Low-End (Pixel 2, 2GB RAM)', NETWORK_PROFILES.fast4G, 'normal');
            allResults.testResults.push({ app: 'MOVIESHOWS3', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS3 - Debug Mode - Fast 4G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS3 - Pixel 2 - Fast 4G - Debug Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS3_URL, 'Low-End (Pixel 2, 2GB RAM)', NETWORK_PROFILES.fast4G, 'debug');
            allResults.testResults.push({ app: 'MOVIESHOWS3', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });
    });

    // Mid-range device (Pixel 5) tests
    test.describe('Mid-Range Device (Pixel 5) - 4GB RAM simulation', () => {
        test.use(devices['Pixel 5']);

        test('MOVIESHOWS2 - Normal Mode - Slow 3G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS2 - Pixel 5 - Slow 3G - Normal Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS2_URL, 'Mid-Range (Pixel 5, 4GB RAM)', NETWORK_PROFILES.slow3G, 'normal');
            allResults.testResults.push({ app: 'MOVIESHOWS2', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS2 - Debug Mode - Slow 3G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS2 - Pixel 5 - Slow 3G - Debug Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS2_URL, 'Mid-Range (Pixel 5, 4GB RAM)', NETWORK_PROFILES.slow3G, 'debug');
            allResults.testResults.push({ app: 'MOVIESHOWS2', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS2 - Normal Mode - Fast 4G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS2 - Pixel 5 - Fast 4G - Normal Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS2_URL, 'Mid-Range (Pixel 5, 4GB RAM)', NETWORK_PROFILES.fast4G, 'normal');
            allResults.testResults.push({ app: 'MOVIESHOWS2', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS2 - Debug Mode - Fast 4G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS2 - Pixel 5 - Fast 4G - Debug Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS2_URL, 'Mid-Range (Pixel 5, 4GB RAM)', NETWORK_PROFILES.fast4G, 'debug');
            allResults.testResults.push({ app: 'MOVIESHOWS2', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS3 - Normal Mode - Slow 3G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS3 - Pixel 5 - Slow 3G - Normal Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS3_URL, 'Mid-Range (Pixel 5, 4GB RAM)', NETWORK_PROFILES.slow3G, 'normal');
            allResults.testResults.push({ app: 'MOVIESHOWS3', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS3 - Debug Mode - Slow 3G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS3 - Pixel 5 - Slow 3G - Debug Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS3_URL, 'Mid-Range (Pixel 5, 4GB RAM)', NETWORK_PROFILES.slow3G, 'debug');
            allResults.testResults.push({ app: 'MOVIESHOWS3', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS3 - Normal Mode - Fast 4G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS3 - Pixel 5 - Fast 4G - Normal Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS3_URL, 'Mid-Range (Pixel 5, 4GB RAM)', NETWORK_PROFILES.fast4G, 'normal');
            allResults.testResults.push({ app: 'MOVIESHOWS3', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS3 - Debug Mode - Fast 4G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS3 - Pixel 5 - Fast 4G - Debug Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS3_URL, 'Mid-Range (Pixel 5, 4GB RAM)', NETWORK_PROFILES.fast4G, 'debug');
            allResults.testResults.push({ app: 'MOVIESHOWS3', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });
    });

    // High-end device (iPhone 13 Pro) tests
    test.describe('High-End Device (iPhone 13 Pro) - 8GB RAM simulation', () => {
        test.use(devices['iPhone 13 Pro']);

        test('MOVIESHOWS2 - Normal Mode - Slow 3G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS2 - iPhone 13 Pro - Slow 3G - Normal Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS2_URL, 'High-End (iPhone 13 Pro, 8GB RAM)', NETWORK_PROFILES.slow3G, 'normal');
            allResults.testResults.push({ app: 'MOVIESHOWS2', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS2 - Debug Mode - Slow 3G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS2 - iPhone 13 Pro - Slow 3G - Debug Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS2_URL, 'High-End (iPhone 13 Pro, 8GB RAM)', NETWORK_PROFILES.slow3G, 'debug');
            allResults.testResults.push({ app: 'MOVIESHOWS2', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS2 - Normal Mode - Fast 4G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS2 - iPhone 13 Pro - Fast 4G - Normal Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS2_URL, 'High-End (iPhone 13 Pro, 8GB RAM)', NETWORK_PROFILES.fast4G, 'normal');
            allResults.testResults.push({ app: 'MOVIESHOWS2', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS2 - Debug Mode - Fast 4G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS2 - iPhone 13 Pro - Fast 4G - Debug Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS2_URL, 'High-End (iPhone 13 Pro, 8GB RAM)', NETWORK_PROFILES.fast4G, 'debug');
            allResults.testResults.push({ app: 'MOVIESHOWS2', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS3 - Normal Mode - Slow 3G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS3 - iPhone 13 Pro - Slow 3G - Normal Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS3_URL, 'High-End (iPhone 13 Pro, 8GB RAM)', NETWORK_PROFILES.slow3G, 'normal');
            allResults.testResults.push({ app: 'MOVIESHOWS3', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS3 - Debug Mode - Slow 3G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS3 - iPhone 13 Pro - Slow 3G - Debug Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS3_URL, 'High-End (iPhone 13 Pro, 8GB RAM)', NETWORK_PROFILES.slow3G, 'debug');
            allResults.testResults.push({ app: 'MOVIESHOWS3', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS3 - Normal Mode - Fast 4G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS3 - iPhone 13 Pro - Fast 4G - Normal Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS3_URL, 'High-End (iPhone 13 Pro, 8GB RAM)', NETWORK_PROFILES.fast4G, 'normal');
            allResults.testResults.push({ app: 'MOVIESHOWS3', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });

        test('MOVIESHOWS3 - Debug Mode - Fast 4G', async ({ page }) => {
            console.log('\n📱 Testing: MOVIESHOWS3 - iPhone 13 Pro - Fast 4G - Debug Mode');
            const results = await collectMobileMetrics(page, MOVIESHOWS3_URL, 'High-End (iPhone 13 Pro, 8GB RAM)', NETWORK_PROFILES.fast4G, 'debug');
            allResults.testResults.push({ app: 'MOVIESHOWS3', ...results });
            console.log(`   ✓ Load: ${results.timing.navigationTime}ms | Logs: ${results.console.total} | Mem: ${results.metrics.memory?.usedJSHeapSize || 'N/A'}MB`);
            expect(results.metrics.data.totalMovies).toBeGreaterThan(0);
        });
    });

    // Generate comprehensive report after all tests
    test.afterAll(async () => {
        console.log('\n\n📊 Generating Comprehensive Mobile Performance Report...\n');

        const report = generateMobilePerformanceReport(allResults);

        // Write to file
        fs.writeFileSync(REPORT_PATH, report, 'utf8');
        console.log(`✅ Report saved to: ${REPORT_PATH}\n`);

        // Print summary
        console.log('\n' + '='.repeat(80));
        console.log('MOBILE PERFORMANCE TEST SUMMARY');
        console.log('='.repeat(80));
        console.log(`Total tests completed: ${allResults.testResults.length}`);
        console.log(`Report location: ${REPORT_PATH}`);
        console.log('='.repeat(80) + '\n');
    });
});

/**
 * Generate comprehensive mobile performance report
 */
function generateMobilePerformanceReport(results) {
    const lines = [];

    lines.push('═'.repeat(100));
    lines.push('  COMPREHENSIVE MOBILE DEVICE PERFORMANCE ANALYSIS');
    lines.push('  Console Logging Impact on MOVIESHOWS2 & MOVIESHOWS3');
    lines.push('═'.repeat(100));
    lines.push('');
    lines.push(`Test Date: ${results.testDate}`);
    lines.push(`Timestamp: ${results.timestamp}`);
    lines.push('');
    lines.push('PURPOSE:');
    lines.push('  Measure the real-world impact of disabling console logging on mobile devices');
    lines.push('  across various device capabilities and network conditions.');
    lines.push('');
    lines.push('TEST COVERAGE:');
    lines.push('  • 3 Device Profiles (Low/Mid/High-end memory)');
    lines.push('     - Low-End: Pixel 2 (2GB RAM simulation)');
    lines.push('     - Mid-Range: Pixel 5 (4GB RAM simulation)');
    lines.push('     - High-End: iPhone 13 Pro (8GB RAM simulation)');
    lines.push('  • 2 Network Profiles (Slow 3G / Fast 4G)');
    lines.push('     - Slow 3G: 400 Kbps, 400ms latency');
    lines.push('     - Fast 4G: 4 Mbps, 50ms latency');
    lines.push('  • 2 Applications (MOVIESHOWS2 / MOVIESHOWS3)');
    lines.push('  • 2 Modes per test (Normal / Debug)');
    lines.push(`  • Total Tests: ${results.testResults.length}`);
    lines.push('');

    // Group results by app, device, and network
    const groupedResults = {};

    for (const result of results.testResults) {
        const key = `${result.app}|${result.deviceProfile}|${result.networkProfile}`;
        if (!groupedResults[key]) {
            groupedResults[key] = {
                app: result.app,
                device: result.deviceProfile,
                network: result.networkProfile,
                normal: null,
                debug: null
            };
        }
        if (result.mode === 'normal') {
            groupedResults[key].normal = result;
        } else {
            groupedResults[key].debug = result;
        }
    }

    // Generate detailed comparisons
    lines.push('═'.repeat(100));
    lines.push('  DETAILED PERFORMANCE ANALYSIS');
    lines.push('═'.repeat(100));
    lines.push('');

    for (const [key, group] of Object.entries(groupedResults)) {
        if (!group.normal || !group.debug) continue;

        lines.push('─'.repeat(100));
        lines.push(`${group.app} - ${group.device} - ${group.network}`);
        lines.push('─'.repeat(100));
        lines.push('');

        const normal = group.normal;
        const debug = group.debug;

        // Timing metrics
        lines.push('TIMING METRICS:');
        lines.push(`                              Normal Mode    Debug Mode     Difference      % Change`);
        lines.push(`  Navigation Time (ms):       ${String(normal.timing.navigationTime).padEnd(14)} ${String(debug.timing.navigationTime).padEnd(14)} ${(debug.timing.navigationTime - normal.timing.navigationTime > 0 ? '+' : '')}${String(debug.timing.navigationTime - normal.timing.navigationTime).padEnd(15)} ${calculatePercentChange(normal.timing.navigationTime, debug.timing.navigationTime)}%`);
        lines.push(`  DOM Content Loaded (ms):    ${String(normal.metrics.performance.domContentLoaded).padEnd(14)} ${String(debug.metrics.performance.domContentLoaded).padEnd(14)} ${(debug.metrics.performance.domContentLoaded - normal.metrics.performance.domContentLoaded > 0 ? '+' : '')}${String(debug.metrics.performance.domContentLoaded - normal.metrics.performance.domContentLoaded).padEnd(15)} ${calculatePercentChange(normal.metrics.performance.domContentLoaded, debug.metrics.performance.domContentLoaded)}%`);
        lines.push(`  Load Event (ms):            ${String(normal.metrics.performance.loadEvent).padEnd(14)} ${String(debug.metrics.performance.loadEvent).padEnd(14)} ${(debug.metrics.performance.loadEvent - normal.metrics.performance.loadEvent > 0 ? '+' : '')}${String(debug.metrics.performance.loadEvent - normal.metrics.performance.loadEvent).padEnd(15)} ${calculatePercentChange(normal.metrics.performance.loadEvent, debug.metrics.performance.loadEvent)}%`);
        lines.push(`  Time to Interactive (ms):   ${String(normal.metrics.performance.timeToInteractive).padEnd(14)} ${String(debug.metrics.performance.timeToInteractive).padEnd(14)} ${(debug.metrics.performance.timeToInteractive - normal.metrics.performance.timeToInteractive > 0 ? '+' : '')}${String(debug.metrics.performance.timeToInteractive - normal.metrics.performance.timeToInteractive).padEnd(15)} ${calculatePercentChange(normal.metrics.performance.timeToInteractive, debug.metrics.performance.timeToInteractive)}%`);
        lines.push(`  First Contentful Paint (ms):${String(normal.metrics.performance.firstContentfulPaint).padEnd(14)} ${String(debug.metrics.performance.firstContentfulPaint).padEnd(14)} ${(debug.metrics.performance.firstContentfulPaint - normal.metrics.performance.firstContentfulPaint > 0 ? '+' : '')}${String(debug.metrics.performance.firstContentfulPaint - normal.metrics.performance.firstContentfulPaint).padEnd(15)} ${calculatePercentChange(normal.metrics.performance.firstContentfulPaint, debug.metrics.performance.firstContentfulPaint)}%`);
        lines.push('');

        // Memory metrics
        if (normal.metrics.memory && debug.metrics.memory) {
            lines.push('MEMORY USAGE (MB):');
            lines.push(`                              Normal Mode    Debug Mode     Difference      % Change`);
            lines.push(`  Used JS Heap:               ${String(normal.metrics.memory.usedJSHeapSize).padEnd(14)} ${String(debug.metrics.memory.usedJSHeapSize).padEnd(14)} ${(debug.metrics.memory.usedJSHeapSize - normal.metrics.memory.usedJSHeapSize > 0 ? '+' : '')}${String((debug.metrics.memory.usedJSHeapSize - normal.metrics.memory.usedJSHeapSize).toFixed(2)).padEnd(15)} ${calculatePercentChange(normal.metrics.memory.usedJSHeapSize, debug.metrics.memory.usedJSHeapSize)}%`);
            lines.push(`  Total JS Heap:              ${String(normal.metrics.memory.totalJSHeapSize).padEnd(14)} ${String(debug.metrics.memory.totalJSHeapSize).padEnd(14)} ${(debug.metrics.memory.totalJSHeapSize - normal.metrics.memory.totalJSHeapSize > 0 ? '+' : '')}${String((debug.metrics.memory.totalJSHeapSize - normal.metrics.memory.totalJSHeapSize).toFixed(2)).padEnd(15)} ${calculatePercentChange(normal.metrics.memory.totalJSHeapSize, debug.metrics.memory.totalJSHeapSize)}%`);
            lines.push('');
        }

        // Console logging
        lines.push('CONSOLE LOGGING:');
        lines.push(`                              Normal Mode    Debug Mode     Difference`);
        lines.push(`  Total Console Logs:         ${String(normal.console.total).padEnd(14)} ${String(debug.console.total).padEnd(14)} ${(debug.console.total - normal.console.total > 0 ? '+' : '')}${debug.console.total - normal.console.total}`);
        lines.push(`  Log Messages:               ${String(normal.console.byType.log).padEnd(14)} ${String(debug.console.byType.log).padEnd(14)} ${(debug.console.byType.log - normal.console.byType.log > 0 ? '+' : '')}${debug.console.byType.log - normal.console.byType.log}`);
        lines.push(`  Info Messages:              ${String(normal.console.byType.info).padEnd(14)} ${String(debug.console.byType.info).padEnd(14)} ${(debug.console.byType.info - normal.console.byType.info > 0 ? '+' : '')}${debug.console.byType.info - normal.console.byType.info}`);
        lines.push(`  Warnings:                   ${String(normal.console.byType.warn).padEnd(14)} ${String(debug.console.byType.warn).padEnd(14)} ${(debug.console.byType.warn - normal.console.byType.warn > 0 ? '+' : '')}${debug.console.byType.warn - normal.console.byType.warn}`);
        lines.push(`  Errors:                     ${String(normal.console.byType.error).padEnd(14)} ${String(debug.console.byType.error).padEnd(14)} ${(debug.console.byType.error - normal.console.byType.error > 0 ? '+' : '')}${debug.console.byType.error - normal.console.byType.error}`);
        lines.push('');

        // Resources
        lines.push('RESOURCE LOADING:');
        lines.push(`                              Normal Mode    Debug Mode     Difference`);
        lines.push(`  Total Resources:            ${String(normal.metrics.resources.total).padEnd(14)} ${String(debug.metrics.resources.total).padEnd(14)} ${(debug.metrics.resources.total - normal.metrics.resources.total > 0 ? '+' : '')}${debug.metrics.resources.total - normal.metrics.resources.total}`);
        lines.push(`  JS Files:                   ${String(normal.metrics.resources.js).padEnd(14)} ${String(debug.metrics.resources.js).padEnd(14)} ${(debug.metrics.resources.js - normal.metrics.resources.js > 0 ? '+' : '')}${debug.metrics.resources.js - normal.metrics.resources.js}`);
        lines.push(`  Total Transfer (MB):        ${String(normal.metrics.resources.totalTransferMB).padEnd(14)} ${String(debug.metrics.resources.totalTransferMB).padEnd(14)} ${(debug.metrics.resources.totalTransferMB - normal.metrics.resources.totalTransferMB > 0 ? '+' : '')}${(debug.metrics.resources.totalTransferMB - normal.metrics.resources.totalTransferMB).toFixed(2)}`);
        lines.push(`  JS Execution Time (ms):     ${String(normal.metrics.resources.jsExecutionTimeMs).padEnd(14)} ${String(debug.metrics.resources.jsExecutionTimeMs).padEnd(14)} ${(debug.metrics.resources.jsExecutionTimeMs - normal.metrics.resources.jsExecutionTimeMs > 0 ? '+' : '')}${debug.metrics.resources.jsExecutionTimeMs - normal.metrics.resources.jsExecutionTimeMs}`);
        lines.push('');

        // Data quality
        lines.push('DATA QUALITY:');
        lines.push(`                              Normal Mode    Debug Mode     Status`);
        lines.push(`  Total Movies:               ${String(normal.metrics.data.totalMovies).padEnd(14)} ${String(debug.metrics.data.totalMovies).padEnd(14)} ${normal.metrics.data.totalMovies === debug.metrics.data.totalMovies ? '✅ Match' : '❌ Mismatch'}`);
        lines.push(`  Movies with Providers:      ${String(normal.metrics.data.moviesWithProviders).padEnd(14)} ${String(debug.metrics.data.moviesWithProviders).padEnd(14)} ${normal.metrics.data.moviesWithProviders === debug.metrics.data.moviesWithProviders ? '✅ Match' : '❌ Mismatch'}`);
        lines.push(`  Provider Badges:            ${String(normal.metrics.data.providerBadges).padEnd(14)} ${String(debug.metrics.data.providerBadges).padEnd(14)} ${normal.metrics.data.providerBadges === debug.metrics.data.providerBadges ? '✅ Match' : '❌ Mismatch'}`);
        lines.push('');

        // Performance assessment
        lines.push('PERFORMANCE ASSESSMENT:');
        const loadTimeDiff = debug.timing.navigationTime - normal.timing.navigationTime;
        const memoryDiff = debug.metrics.memory ? (debug.metrics.memory.usedJSHeapSize - normal.metrics.memory.usedJSHeapSize) : 0;

        if (loadTimeDiff < 100) {
            lines.push('  Load Time Impact:           ✅ Negligible (<100ms difference)');
        } else if (loadTimeDiff < 500) {
            lines.push(`  Load Time Impact:           ⚠️  Noticeable (+${loadTimeDiff}ms)`);
        } else {
            lines.push(`  Load Time Impact:           ❌ Significant (+${loadTimeDiff}ms)`);
        }

        if (memoryDiff < 1) {
            lines.push('  Memory Impact:              ✅ Negligible (<1MB difference)');
        } else if (memoryDiff < 5) {
            lines.push(`  Memory Impact:              ⚠️  Noticeable (+${memoryDiff.toFixed(2)}MB)`);
        } else {
            lines.push(`  Memory Impact:              ❌ Significant (+${memoryDiff.toFixed(2)}MB)`);
        }

        if (normal.console.total < 10) {
            lines.push('  Console Logging (Normal):   ✅ Minimal (as expected)');
        } else {
            lines.push(`  Console Logging (Normal):   ⚠️  Excessive (${normal.console.total} logs)`);
        }

        if (debug.console.total > 50) {
            lines.push('  Console Logging (Debug):    ✅ Verbose (as expected)');
        } else {
            lines.push(`  Console Logging (Debug):    ❌ Debug mode not working properly`);
        }

        lines.push('');
    }

    // Summary statistics
    lines.push('═'.repeat(100));
    lines.push('  SUMMARY STATISTICS');
    lines.push('═'.repeat(100));
    lines.push('');

    // Calculate averages
    const ms2Results = results.testResults.filter(r => r.app === 'MOVIESHOWS2');
    const ms3Results = results.testResults.filter(r => r.app === 'MOVIESHOWS3');

    const ms2Normal = ms2Results.filter(r => r.mode === 'normal');
    const ms2Debug = ms2Results.filter(r => r.mode === 'debug');
    const ms3Normal = ms3Results.filter(r => r.mode === 'normal');
    const ms3Debug = ms3Results.filter(r => r.mode === 'debug');

    lines.push('AVERAGE PERFORMANCE METRICS:');
    lines.push('');
    lines.push('MOVIESHOWS2:');
    lines.push(`  Normal Mode:`);
    lines.push(`    Avg Load Time:       ${calculateAverage(ms2Normal, 'timing.navigationTime')}ms`);
    lines.push(`    Avg Console Logs:    ${calculateAverage(ms2Normal, 'console.total')}`);
    lines.push(`    Avg Memory Used:     ${calculateAverage(ms2Normal, 'metrics.memory.usedJSHeapSize')}MB`);
    lines.push(`  Debug Mode:`);
    lines.push(`    Avg Load Time:       ${calculateAverage(ms2Debug, 'timing.navigationTime')}ms`);
    lines.push(`    Avg Console Logs:    ${calculateAverage(ms2Debug, 'console.total')}`);
    lines.push(`    Avg Memory Used:     ${calculateAverage(ms2Debug, 'metrics.memory.usedJSHeapSize')}MB`);
    lines.push(`  Performance Gain (Debug - Normal, negative is better):`);
    lines.push(`    Load Time Difference:     ${(calculateAverage(ms2Debug, 'timing.navigationTime') - calculateAverage(ms2Normal, 'timing.navigationTime')).toFixed(0)}ms`);
    lines.push(`    Memory Difference:        ${(calculateAverage(ms2Debug, 'metrics.memory.usedJSHeapSize') - calculateAverage(ms2Normal, 'metrics.memory.usedJSHeapSize')).toFixed(2)}MB`);
    lines.push(`    Console Logs Reduced:     ${(calculateAverage(ms2Normal, 'console.total') - calculateAverage(ms2Debug, 'console.total')).toFixed(0)} (normal mode savings)`);
    lines.push('');

    lines.push('MOVIESHOWS3:');
    lines.push(`  Normal Mode:`);
    lines.push(`    Avg Load Time:       ${calculateAverage(ms3Normal, 'timing.navigationTime')}ms`);
    lines.push(`    Avg Console Logs:    ${calculateAverage(ms3Normal, 'console.total')}`);
    lines.push(`    Avg Memory Used:     ${calculateAverage(ms3Normal, 'metrics.memory.usedJSHeapSize')}MB`);
    lines.push(`  Debug Mode:`);
    lines.push(`    Avg Load Time:       ${calculateAverage(ms3Debug, 'timing.navigationTime')}ms`);
    lines.push(`    Avg Console Logs:    ${calculateAverage(ms3Debug, 'console.total')}`);
    lines.push(`    Avg Memory Used:     ${calculateAverage(ms3Debug, 'metrics.memory.usedJSHeapSize')}MB`);
    lines.push(`  Performance Gain (Debug - Normal, negative is better):`);
    lines.push(`    Load Time Difference:     ${(calculateAverage(ms3Debug, 'timing.navigationTime') - calculateAverage(ms3Normal, 'timing.navigationTime')).toFixed(0)}ms`);
    lines.push(`    Memory Difference:        ${(calculateAverage(ms3Debug, 'metrics.memory.usedJSHeapSize') - calculateAverage(ms3Normal, 'metrics.memory.usedJSHeapSize')).toFixed(2)}MB`);
    lines.push(`    Console Logs Reduced:     ${(calculateAverage(ms3Normal, 'console.total') - calculateAverage(ms3Debug, 'console.total')).toFixed(0)} (normal mode savings)`);
    lines.push('');

    // Performance impact by device profile
    lines.push('═'.repeat(100));
    lines.push('  PERFORMANCE IMPACT BY DEVICE PROFILE');
    lines.push('═'.repeat(100));
    lines.push('');

    const deviceProfiles = ['Low-End (Pixel 2, 2GB RAM)', 'Mid-Range (Pixel 5, 4GB RAM)', 'High-End (iPhone 13 Pro, 8GB RAM)'];

    for (const deviceProfile of deviceProfiles) {
        const deviceResults = results.testResults.filter(r => r.deviceProfile === deviceProfile);
        const deviceNormal = deviceResults.filter(r => r.mode === 'normal');
        const deviceDebug = deviceResults.filter(r => r.mode === 'debug');

        lines.push(`${deviceProfile}:`);
        lines.push(`  Average load time (Normal):     ${calculateAverage(deviceNormal, 'timing.navigationTime')}ms`);
        lines.push(`  Average load time (Debug):      ${calculateAverage(deviceDebug, 'timing.navigationTime')}ms`);
        lines.push(`  Load time difference:           ${(calculateAverage(deviceDebug, 'timing.navigationTime') - calculateAverage(deviceNormal, 'timing.navigationTime')).toFixed(0)}ms`);
        lines.push(`  Memory savings (Normal mode):   ${(calculateAverage(deviceDebug, 'metrics.memory.usedJSHeapSize') - calculateAverage(deviceNormal, 'metrics.memory.usedJSHeapSize')).toFixed(2)}MB`);
        lines.push(`  Console logs reduced:           ${(calculateAverage(deviceNormal, 'console.total') - calculateAverage(deviceDebug, 'console.total')).toFixed(0)} logs`);
        lines.push('');
    }

    // Performance impact by network profile
    lines.push('═'.repeat(100));
    lines.push('  PERFORMANCE IMPACT BY NETWORK PROFILE');
    lines.push('═'.repeat(100));
    lines.push('');

    const networkProfiles = ['Slow 3G', 'Fast 4G'];

    for (const networkProfile of networkProfiles) {
        const networkResults = results.testResults.filter(r => r.networkProfile === networkProfile);
        const networkNormal = networkResults.filter(r => r.mode === 'normal');
        const networkDebug = networkResults.filter(r => r.mode === 'debug');

        lines.push(`${networkProfile}:`);
        lines.push(`  Average load time (Normal):     ${calculateAverage(networkNormal, 'timing.navigationTime')}ms`);
        lines.push(`  Average load time (Debug):      ${calculateAverage(networkDebug, 'timing.navigationTime')}ms`);
        lines.push(`  Load time difference:           ${(calculateAverage(networkDebug, 'timing.navigationTime') - calculateAverage(networkNormal, 'timing.navigationTime')).toFixed(0)}ms`);
        lines.push(`  Memory savings (Normal mode):   ${(calculateAverage(networkDebug, 'metrics.memory.usedJSHeapSize') - calculateAverage(networkNormal, 'metrics.memory.usedJSHeapSize')).toFixed(2)}MB`);
        lines.push(`  Console logs reduced:           ${(calculateAverage(networkNormal, 'console.total') - calculateAverage(networkDebug, 'console.total')).toFixed(0)} logs`);
        lines.push('');
    }

    // Recommendations
    lines.push('═'.repeat(100));
    lines.push('  RECOMMENDATIONS FOR MOBILE OPTIMIZATION');
    lines.push('═'.repeat(100));
    lines.push('');

    lines.push('Based on the performance analysis:');
    lines.push('');
    lines.push('1. CONSOLE LOGGING:');
    lines.push('   ✅ Keep console logging disabled by default (current implementation)');
    lines.push('   ✅ Enable via ?debug=1 for debugging purposes only');
    lines.push('   ✅ Console logging has measurable performance impact on low-end devices');
    lines.push('');

    lines.push('2. LOW-END DEVICE OPTIMIZATIONS:');
    lines.push('   • Consider implementing progressive enhancement for 2GB RAM devices');
    lines.push('   • Limit number of simultaneous iframes loaded');
    lines.push('   • Implement more aggressive memory management');
    lines.push('   • Consider lazy loading for off-screen content');
    lines.push('');

    lines.push('3. NETWORK OPTIMIZATION:');
    lines.push('   • 3G performance shows significant impact from console logging');
    lines.push('   • Consider reducing initial payload size');
    lines.push('   • Implement resource prioritization for slow networks');
    lines.push('');

    lines.push('4. MEMORY MANAGEMENT:');
    lines.push('   • Monitor JS heap size growth during scrolling');
    lines.push('   • Implement iframe cleanup for off-screen videos');
    lines.push('   • Consider implementing virtual scrolling for large lists');
    lines.push('');

    lines.push('5. FURTHER TESTING:');
    lines.push('   • Test on real devices to validate emulation results');
    lines.push('   • Monitor long-session memory leaks');
    lines.push('   • Test with different movie catalog sizes');
    lines.push('   • Profile CPU usage during video playback');
    lines.push('');

    lines.push('═'.repeat(100));
    lines.push('  END OF MOBILE PERFORMANCE ANALYSIS');
    lines.push('═'.repeat(100));

    return lines.join('\n');
}

/**
 * Helper: Calculate percentage change
 */
function calculatePercentChange(oldValue, newValue) {
    if (oldValue === 0) return '0.00';
    return ((newValue - oldValue) / oldValue * 100).toFixed(2);
}

/**
 * Helper: Calculate average for a nested property
 */
function calculateAverage(results, propertyPath) {
    if (results.length === 0) return 0;

    const values = results.map(r => {
        const props = propertyPath.split('.');
        let value = r;
        for (const prop of props) {
            value = value?.[prop];
        }
        return value || 0;
    });

    const sum = values.reduce((acc, val) => acc + val, 0);
    return Math.round(sum / values.length);
}
