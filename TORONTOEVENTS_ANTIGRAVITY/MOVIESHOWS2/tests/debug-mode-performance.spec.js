// @ts-check
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

/**
 * Performance & Data Quality Test for MOVIESHOWS2 and MOVIESHOWS3
 * Testing console logging behavior with ?debug=1 parameter
 */

const MOVIESHOWS2_URL = 'https://findtorontoevents.ca/MOVIESHOWS2/';
const MOVIESHOWS3_URL = 'https://findtorontoevents.ca/MOVIESHOWS3/';

const REPORT_PATH = 'e:/findtorontoevents_antigravity.ca/movieshows_performance_test.txt';

test.describe('Debug Mode Performance Tests', () => {

    // Test results storage
    const testResults = {
        timestamp: new Date().toISOString(),
        movieshows2: {
            normal: null,
            debug: null
        },
        movieshows3: {
            normal: null,
            debug: null
        }
    };

    /**
     * Helper function to collect comprehensive metrics
     */
    async function collectMetrics(page, appName, mode) {
        const startTime = Date.now();
        const consoleLogs = [];
        const consoleErrors = [];
        const jsErrors = [];

        // Capture console messages
        page.on('console', msg => {
            const text = msg.text();
            consoleLogs.push({
                type: msg.type(),
                text: text,
                timestamp: Date.now()
            });
        });

        // Capture JavaScript errors
        page.on('pageerror', error => {
            jsErrors.push({
                message: error.message,
                stack: error.stack,
                timestamp: Date.now()
            });
        });

        // Capture console errors specifically
        page.on('console', msg => {
            if (msg.type() === 'error') {
                consoleErrors.push({
                    text: msg.text(),
                    timestamp: Date.now()
                });
            }
        });

        // Navigate to page
        const url = mode === 'debug'
            ? (appName === 'MOVIESHOWS2' ? MOVIESHOWS2_URL + '?debug=1' : MOVIESHOWS3_URL + '?debug=1')
            : (appName === 'MOVIESHOWS2' ? MOVIESHOWS2_URL : MOVIESHOWS3_URL);

        await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });

        // Wait for movies to load
        await page.waitForFunction(() => {
            return window.allMovies && window.allMovies.length > 0;
        }, { timeout: 30000 });

        // Additional wait for rendering
        await page.waitForTimeout(5000);

        const loadTime = Date.now() - startTime;

        // Collect data quality metrics
        const dataMetrics = await page.evaluate(() => {
            const movies = window.allMovies || [];
            const moviesWithProviders = movies.filter(m =>
                (m.providers && m.providers.length > 0) ||
                (m._providers && m._providers.length > 0)
            );

            // Check provider badges in DOM
            const providerBadges = document.querySelectorAll('.provider-badge');
            const videoCards = document.querySelectorAll('.video-card');

            // Check if debug mode is active
            const debugActive = window.DEBUG_MODE === true;

            // Memory usage (if available)
            let memoryInfo = null;
            if (performance.memory) {
                memoryInfo = {
                    usedJSHeapSize: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024 * 100) / 100,
                    totalJSHeapSize: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024 * 100) / 100,
                    jsHeapSizeLimit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024 * 100) / 100
                };
            }

            // Performance metrics
            const perf = performance.getEntriesByType('navigation')[0];
            const resources = performance.getEntriesByType('resource');

            return {
                totalMovies: movies.length,
                moviesWithProviders: moviesWithProviders.length,
                providerBadgesInDOM: providerBadges.length,
                videoCardsInDOM: videoCards.length,
                debugModeActive: debugActive,
                memoryInfo: memoryInfo,
                performance: {
                    domContentLoaded: Math.round(perf?.domContentLoadedEventEnd || 0),
                    loadEvent: Math.round(perf?.loadEventEnd || 0),
                    totalResources: resources.length,
                    domNodes: document.querySelectorAll('*').length
                }
            };
        });

        // Check specific provider data for first few movies
        const providerDetails = await page.evaluate(() => {
            const movies = window.allMovies || [];
            return movies.slice(0, 5).map(m => ({
                title: m.title,
                id: m.id,
                hasProviders: (m.providers && m.providers.length > 0) || (m._providers && m._providers.length > 0),
                providerCount: (m.providers?.length || m._providers?.length || 0)
            }));
        });

        // Check for specific console log patterns
        const debugLogs = consoleLogs.filter(log =>
            log.text.includes('DEBUG:') ||
            log.text.includes('Provider') ||
            log.text.includes('Loading') ||
            log.text.includes('Movies loaded')
        );

        return {
            url: url,
            loadTime: loadTime,
            consoleLogs: {
                total: consoleLogs.length,
                debug: debugLogs.length,
                errors: consoleErrors.length,
                byType: {
                    log: consoleLogs.filter(l => l.type === 'log').length,
                    info: consoleLogs.filter(l => l.type === 'info').length,
                    warn: consoleLogs.filter(l => l.type === 'warning').length,
                    error: consoleLogs.filter(l => l.type === 'error').length
                },
                samples: consoleLogs.slice(0, 10).map(l => l.text)
            },
            jsErrors: {
                total: jsErrors.length,
                details: jsErrors.slice(0, 5)
            },
            dataQuality: {
                ...dataMetrics,
                providerDetails: providerDetails
            }
        };
    }

    /**
     * Test MOVIESHOWS2 - Normal Mode (no debug parameter)
     */
    test('MOVIESHOWS2 - Normal Mode (console logs disabled)', async ({ page }) => {
        console.log('\n🧪 Testing MOVIESHOWS2 - Normal Mode');
        const metrics = await collectMetrics(page, 'MOVIESHOWS2', 'normal');
        testResults.movieshows2.normal = metrics;

        // Assertions
        expect(metrics.dataQuality.totalMovies).toBeGreaterThan(0);
        expect(metrics.dataQuality.debugModeActive).toBe(false);

        // In normal mode, console logs should be minimal
        console.log(`   ✓ Total movies: ${metrics.dataQuality.totalMovies}`);
        console.log(`   ✓ Movies with providers: ${metrics.dataQuality.moviesWithProviders}`);
        console.log(`   ✓ Provider badges rendered: ${metrics.dataQuality.providerBadgesInDOM}`);
        console.log(`   ✓ Console logs: ${metrics.consoleLogs.total} (should be minimal)`);
        console.log(`   ✓ Debug mode active: ${metrics.dataQuality.debugModeActive}`);
        console.log(`   ✓ Load time: ${metrics.loadTime}ms`);
        console.log(`   ✓ JS Errors: ${metrics.jsErrors.total}`);
    });

    /**
     * Test MOVIESHOWS2 - Debug Mode (?debug=1)
     */
    test('MOVIESHOWS2 - Debug Mode (console logs enabled)', async ({ page }) => {
        console.log('\n🧪 Testing MOVIESHOWS2 - Debug Mode');
        const metrics = await collectMetrics(page, 'MOVIESHOWS2', 'debug');
        testResults.movieshows2.debug = metrics;

        // Assertions
        expect(metrics.dataQuality.totalMovies).toBeGreaterThan(0);
        expect(metrics.dataQuality.debugModeActive).toBe(true);

        // In debug mode, console logs should be present
        expect(metrics.consoleLogs.total).toBeGreaterThan(0);

        console.log(`   ✓ Total movies: ${metrics.dataQuality.totalMovies}`);
        console.log(`   ✓ Movies with providers: ${metrics.dataQuality.moviesWithProviders}`);
        console.log(`   ✓ Provider badges rendered: ${metrics.dataQuality.providerBadgesInDOM}`);
        console.log(`   ✓ Console logs: ${metrics.consoleLogs.total} (should be verbose)`);
        console.log(`   ✓ Debug mode active: ${metrics.dataQuality.debugModeActive}`);
        console.log(`   ✓ Load time: ${metrics.loadTime}ms`);
        console.log(`   ✓ JS Errors: ${metrics.jsErrors.total}`);
    });

    /**
     * Test MOVIESHOWS3 - Normal Mode (no debug parameter)
     */
    test('MOVIESHOWS3 - Normal Mode (console logs disabled)', async ({ page }) => {
        console.log('\n🧪 Testing MOVIESHOWS3 - Normal Mode');
        const metrics = await collectMetrics(page, 'MOVIESHOWS3', 'normal');
        testResults.movieshows3.normal = metrics;

        // Assertions
        expect(metrics.dataQuality.totalMovies).toBeGreaterThan(0);
        expect(metrics.dataQuality.debugModeActive).toBe(false);

        console.log(`   ✓ Total movies: ${metrics.dataQuality.totalMovies}`);
        console.log(`   ✓ Movies with providers: ${metrics.dataQuality.moviesWithProviders}`);
        console.log(`   ✓ Provider badges rendered: ${metrics.dataQuality.providerBadgesInDOM}`);
        console.log(`   ✓ Console logs: ${metrics.consoleLogs.total} (should be minimal)`);
        console.log(`   ✓ Debug mode active: ${metrics.dataQuality.debugModeActive}`);
        console.log(`   ✓ Load time: ${metrics.loadTime}ms`);
        console.log(`   ✓ JS Errors: ${metrics.jsErrors.total}`);
    });

    /**
     * Test MOVIESHOWS3 - Debug Mode (?debug=1)
     */
    test('MOVIESHOWS3 - Debug Mode (console logs enabled)', async ({ page }) => {
        console.log('\n🧪 Testing MOVIESHOWS3 - Debug Mode');
        const metrics = await collectMetrics(page, 'MOVIESHOWS3', 'debug');
        testResults.movieshows3.debug = metrics;

        // Assertions
        expect(metrics.dataQuality.totalMovies).toBeGreaterThan(0);
        expect(metrics.dataQuality.debugModeActive).toBe(true);

        // In debug mode, console logs should be present
        expect(metrics.consoleLogs.total).toBeGreaterThan(0);

        console.log(`   ✓ Total movies: ${metrics.dataQuality.totalMovies}`);
        console.log(`   ✓ Movies with providers: ${metrics.dataQuality.moviesWithProviders}`);
        console.log(`   ✓ Provider badges rendered: ${metrics.dataQuality.providerBadgesInDOM}`);
        console.log(`   ✓ Console logs: ${metrics.consoleLogs.total} (should be verbose)`);
        console.log(`   ✓ Debug mode active: ${metrics.dataQuality.debugModeActive}`);
        console.log(`   ✓ Load time: ${metrics.loadTime}ms`);
        console.log(`   ✓ JS Errors: ${metrics.jsErrors.total}`);
    });
    /**
     * Generate comprehensive report after all tests
     */
    test.afterAll(async () => {
        console.log('\n📊 Generating Performance Report...\n');

        const report = generateReport(testResults);

        // Write to file
        fs.writeFileSync(REPORT_PATH, report, 'utf8');
        console.log(`✅ Report saved to: ${REPORT_PATH}\n`);

        // Print summary to console
        console.log(report);
    });
});

/**
 * Generate detailed performance report
 */
function generateReport(results) {
    const lines = [];

    lines.push('═══════════════════════════════════════════════════════════════════════════');
    lines.push('                  MOVIESHOWS PERFORMANCE & DEBUG MODE TEST REPORT');
    lines.push('═══════════════════════════════════════════════════════════════════════════');
    lines.push('');
    lines.push(`Test Date: ${new Date(results.timestamp).toLocaleString()}`);
    lines.push('');
    lines.push('PURPOSE: Test debug mode functionality and performance impact');
    lines.push('  - Console logging should be OFF by default (normal mode)');
    lines.push('  - Console logging should be ON with ?debug=1 parameter');
    lines.push('  - Data integrity should be maintained in both modes');
    lines.push('  - Provider badges should render correctly in both modes');
    lines.push('');
    lines.push('═══════════════════════════════════════════════════════════════════════════');
    lines.push('                              MOVIESHOWS2 RESULTS');
    lines.push('═══════════════════════════════════════════════════════════════════════════');
    lines.push('');

    // MOVIESHOWS2 comparison
    if (results.movieshows2.normal && results.movieshows2.debug) {
        const normal = results.movieshows2.normal;
        const debug = results.movieshows2.debug;

        lines.push('┌─────────────────────────────────────────────────────────────────────────┐');
        lines.push('│ CONSOLE LOGGING BEHAVIOR                                                │');
        lines.push('├─────────────────────────────────────────────────────────────────────────┤');
        lines.push(`│ Normal Mode (no ?debug):                                                │`);
        lines.push(`│   Total console logs:     ${String(normal.consoleLogs.total).padEnd(47)}│`);
        lines.push(`│   Debug logs:             ${String(normal.consoleLogs.debug).padEnd(47)}│`);
        lines.push(`│   Debug mode active:      ${String(normal.dataQuality.debugModeActive).padEnd(47)}│`);
        lines.push(`│   Result:                 ${(normal.consoleLogs.total < 10 ? '✅ MINIMAL (as expected)' : '⚠️  EXCESSIVE').padEnd(47)}│`);
        lines.push(`│                                                                         │`);
        lines.push(`│ Debug Mode (?debug=1):                                                  │`);
        lines.push(`│   Total console logs:     ${String(debug.consoleLogs.total).padEnd(47)}│`);
        lines.push(`│   Debug logs:             ${String(debug.consoleLogs.debug).padEnd(47)}│`);
        lines.push(`│   Debug mode active:      ${String(debug.dataQuality.debugModeActive).padEnd(47)}│`);
        lines.push(`│   Result:                 ${(debug.consoleLogs.total > normal.consoleLogs.total ? '✅ VERBOSE (as expected)' : '❌ NOT WORKING').padEnd(47)}│`);
        lines.push('└─────────────────────────────────────────────────────────────────────────┘');
        lines.push('');

        lines.push('┌─────────────────────────────────────────────────────────────────────────┐');
        lines.push('│ PERFORMANCE METRICS                                                     │');
        lines.push('├─────────────────────────────────────────────────────────────────────────┤');
        lines.push(`│                           Normal Mode    Debug Mode    Difference       │`);
        lines.push(`│ Page Load Time:           ${String(normal.loadTime).padEnd(12)} ${String(debug.loadTime).padEnd(11)} ${String(debug.loadTime - normal.loadTime > 0 ? '+' : '')}${debug.loadTime - normal.loadTime}ms │`);
        lines.push(`│ DOM Nodes:                ${String(normal.dataQuality.performance.domNodes).padEnd(12)} ${String(debug.dataQuality.performance.domNodes).padEnd(11)} ${String(debug.dataQuality.performance.domNodes - normal.dataQuality.performance.domNodes).padEnd(13)}│`);
        lines.push(`│ Total Resources:          ${String(normal.dataQuality.performance.totalResources).padEnd(12)} ${String(debug.dataQuality.performance.totalResources).padEnd(11)} ${String(debug.dataQuality.performance.totalResources - normal.dataQuality.performance.totalResources).padEnd(13)}│`);
        lines.push(`│ JS Errors:                ${String(normal.jsErrors.total).padEnd(12)} ${String(debug.jsErrors.total).padEnd(11)} ${String(debug.jsErrors.total - normal.jsErrors.total).padEnd(13)}│`);
        lines.push('└─────────────────────────────────────────────────────────────────────────┘');
        lines.push('');

        lines.push('┌─────────────────────────────────────────────────────────────────────────┐');
        lines.push('│ DATA QUALITY                                                            │');
        lines.push('├─────────────────────────────────────────────────────────────────────────┤');
        lines.push(`│                           Normal Mode    Debug Mode    Status           │`);
        lines.push(`│ Total Movies:             ${String(normal.dataQuality.totalMovies).padEnd(12)} ${String(debug.dataQuality.totalMovies).padEnd(11)} ${(normal.dataQuality.totalMovies === debug.dataQuality.totalMovies ? '✅ Match' : '❌ Mismatch').padEnd(13)}│`);
        lines.push(`│ Movies w/ Providers:      ${String(normal.dataQuality.moviesWithProviders).padEnd(12)} ${String(debug.dataQuality.moviesWithProviders).padEnd(11)} ${(normal.dataQuality.moviesWithProviders === debug.dataQuality.moviesWithProviders ? '✅ Match' : '❌ Mismatch').padEnd(13)}│`);
        lines.push(`│ Provider Badges Rendered: ${String(normal.dataQuality.providerBadgesInDOM).padEnd(12)} ${String(debug.dataQuality.providerBadgesInDOM).padEnd(11)} ${(normal.dataQuality.providerBadgesInDOM === debug.dataQuality.providerBadgesInDOM ? '✅ Match' : '❌ Mismatch').padEnd(13)}│`);
        lines.push(`│ Video Cards:              ${String(normal.dataQuality.videoCardsInDOM).padEnd(12)} ${String(debug.dataQuality.videoCardsInDOM).padEnd(11)} ${(normal.dataQuality.videoCardsInDOM === debug.dataQuality.videoCardsInDOM ? '✅ Match' : '❌ Mismatch').padEnd(13)}│`);
        lines.push('└─────────────────────────────────────────────────────────────────────────┘');
        lines.push('');

        // Memory info if available
        if (normal.dataQuality.memoryInfo && debug.dataQuality.memoryInfo) {
            lines.push('┌─────────────────────────────────────────────────────────────────────────┐');
            lines.push('│ MEMORY USAGE (MB)                                                       │');
            lines.push('├─────────────────────────────────────────────────────────────────────────┤');
            lines.push(`│                           Normal Mode    Debug Mode    Difference       │`);
            lines.push(`│ Used JS Heap:             ${String(normal.dataQuality.memoryInfo.usedJSHeapSize).padEnd(12)} ${String(debug.dataQuality.memoryInfo.usedJSHeapSize).padEnd(11)} ${String(debug.dataQuality.memoryInfo.usedJSHeapSize - normal.dataQuality.memoryInfo.usedJSHeapSize > 0 ? '+' : '')}${(debug.dataQuality.memoryInfo.usedJSHeapSize - normal.dataQuality.memoryInfo.usedJSHeapSize).toFixed(2)}MB │`);
            lines.push(`│ Total JS Heap:            ${String(normal.dataQuality.memoryInfo.totalJSHeapSize).padEnd(12)} ${String(debug.dataQuality.memoryInfo.totalJSHeapSize).padEnd(11)} ${String(debug.dataQuality.memoryInfo.totalJSHeapSize - normal.dataQuality.memoryInfo.totalJSHeapSize > 0 ? '+' : '')}${(debug.dataQuality.memoryInfo.totalJSHeapSize - normal.dataQuality.memoryInfo.totalJSHeapSize).toFixed(2)}MB │`);
            lines.push('└─────────────────────────────────────────────────────────────────────────┘');
            lines.push('');
        }

        // Sample provider details
        lines.push('┌─────────────────────────────────────────────────────────────────────────┐');
        lines.push('│ PROVIDER DATA SAMPLE (First 5 Movies - Normal Mode)                    │');
        lines.push('├─────────────────────────────────────────────────────────────────────────┤');
        normal.dataQuality.providerDetails.forEach((movie, idx) => {
            const title = movie.title.substring(0, 40).padEnd(40);
            const providers = String(movie.providerCount).padStart(2);
            const status = movie.hasProviders ? '✅' : '❌';
            lines.push(`│ ${idx + 1}. ${title} Providers: ${providers} ${status}  │`);
        });
        lines.push('└─────────────────────────────────────────────────────────────────────────┘');
        lines.push('');
    }

    lines.push('═══════════════════════════════════════════════════════════════════════════');
    lines.push('                              MOVIESHOWS3 RESULTS');
    lines.push('═══════════════════════════════════════════════════════════════════════════');
    lines.push('');

    // MOVIESHOWS3 comparison
    if (results.movieshows3.normal && results.movieshows3.debug) {
        const normal = results.movieshows3.normal;
        const debug = results.movieshows3.debug;

        lines.push('┌─────────────────────────────────────────────────────────────────────────┐');
        lines.push('│ CONSOLE LOGGING BEHAVIOR                                                │');
        lines.push('├─────────────────────────────────────────────────────────────────────────┤');
        lines.push(`│ Normal Mode (no ?debug):                                                │`);
        lines.push(`│   Total console logs:     ${String(normal.consoleLogs.total).padEnd(47)}│`);
        lines.push(`│   Debug logs:             ${String(normal.consoleLogs.debug).padEnd(47)}│`);
        lines.push(`│   Debug mode active:      ${String(normal.dataQuality.debugModeActive).padEnd(47)}│`);
        lines.push(`│   Result:                 ${(normal.consoleLogs.total < 10 ? '✅ MINIMAL (as expected)' : '⚠️  EXCESSIVE').padEnd(47)}│`);
        lines.push(`│                                                                         │`);
        lines.push(`│ Debug Mode (?debug=1):                                                  │`);
        lines.push(`│   Total console logs:     ${String(debug.consoleLogs.total).padEnd(47)}│`);
        lines.push(`│   Debug logs:             ${String(debug.consoleLogs.debug).padEnd(47)}│`);
        lines.push(`│   Debug mode active:      ${String(debug.dataQuality.debugModeActive).padEnd(47)}│`);
        lines.push(`│   Result:                 ${(debug.consoleLogs.total > normal.consoleLogs.total ? '✅ VERBOSE (as expected)' : '❌ NOT WORKING').padEnd(47)}│`);
        lines.push('└─────────────────────────────────────────────────────────────────────────┘');
        lines.push('');

        lines.push('┌─────────────────────────────────────────────────────────────────────────┐');
        lines.push('│ PERFORMANCE METRICS                                                     │');
        lines.push('├─────────────────────────────────────────────────────────────────────────┤');
        lines.push(`│                           Normal Mode    Debug Mode    Difference       │`);
        lines.push(`│ Page Load Time:           ${String(normal.loadTime).padEnd(12)} ${String(debug.loadTime).padEnd(11)} ${String(debug.loadTime - normal.loadTime > 0 ? '+' : '')}${debug.loadTime - normal.loadTime}ms │`);
        lines.push(`│ DOM Nodes:                ${String(normal.dataQuality.performance.domNodes).padEnd(12)} ${String(debug.dataQuality.performance.domNodes).padEnd(11)} ${String(debug.dataQuality.performance.domNodes - normal.dataQuality.performance.domNodes).padEnd(13)}│`);
        lines.push(`│ Total Resources:          ${String(normal.dataQuality.performance.totalResources).padEnd(12)} ${String(debug.dataQuality.performance.totalResources).padEnd(11)} ${String(debug.dataQuality.performance.totalResources - normal.dataQuality.performance.totalResources).padEnd(13)}│`);
        lines.push(`│ JS Errors:                ${String(normal.jsErrors.total).padEnd(12)} ${String(debug.jsErrors.total).padEnd(11)} ${String(debug.jsErrors.total - normal.jsErrors.total).padEnd(13)}│`);
        lines.push('└─────────────────────────────────────────────────────────────────────────┘');
        lines.push('');

        lines.push('┌─────────────────────────────────────────────────────────────────────────┐');
        lines.push('│ DATA QUALITY                                                            │');
        lines.push('├─────────────────────────────────────────────────────────────────────────┤');
        lines.push(`│                           Normal Mode    Debug Mode    Status           │`);
        lines.push(`│ Total Movies:             ${String(normal.dataQuality.totalMovies).padEnd(12)} ${String(debug.dataQuality.totalMovies).padEnd(11)} ${(normal.dataQuality.totalMovies === debug.dataQuality.totalMovies ? '✅ Match' : '❌ Mismatch').padEnd(13)}│`);
        lines.push(`│ Movies w/ Providers:      ${String(normal.dataQuality.moviesWithProviders).padEnd(12)} ${String(debug.dataQuality.moviesWithProviders).padEnd(11)} ${(normal.dataQuality.moviesWithProviders === debug.dataQuality.moviesWithProviders ? '✅ Match' : '❌ Mismatch').padEnd(13)}│`);
        lines.push(`│ Provider Badges Rendered: ${String(normal.dataQuality.providerBadgesInDOM).padEnd(12)} ${String(debug.dataQuality.providerBadgesInDOM).padEnd(11)} ${(normal.dataQuality.providerBadgesInDOM === debug.dataQuality.providerBadgesInDOM ? '✅ Match' : '❌ Mismatch').padEnd(13)}│`);
        lines.push(`│ Video Cards:              ${String(normal.dataQuality.videoCardsInDOM).padEnd(12)} ${String(debug.dataQuality.videoCardsInDOM).padEnd(11)} ${(normal.dataQuality.videoCardsInDOM === debug.dataQuality.videoCardsInDOM ? '✅ Match' : '❌ Mismatch').padEnd(13)}│`);
        lines.push('└─────────────────────────────────────────────────────────────────────────┘');
        lines.push('');

        // Memory info if available
        if (normal.dataQuality.memoryInfo && debug.dataQuality.memoryInfo) {
            lines.push('┌─────────────────────────────────────────────────────────────────────────┐');
            lines.push('│ MEMORY USAGE (MB)                                                       │');
            lines.push('├─────────────────────────────────────────────────────────────────────────┤');
            lines.push(`│                           Normal Mode    Debug Mode    Difference       │`);
            lines.push(`│ Used JS Heap:             ${String(normal.dataQuality.memoryInfo.usedJSHeapSize).padEnd(12)} ${String(debug.dataQuality.memoryInfo.usedJSHeapSize).padEnd(11)} ${String(debug.dataQuality.memoryInfo.usedJSHeapSize - normal.dataQuality.memoryInfo.usedJSHeapSize > 0 ? '+' : '')}${(debug.dataQuality.memoryInfo.usedJSHeapSize - normal.dataQuality.memoryInfo.usedJSHeapSize).toFixed(2)}MB │`);
            lines.push(`│ Total JS Heap:            ${String(normal.dataQuality.memoryInfo.totalJSHeapSize).padEnd(12)} ${String(debug.dataQuality.memoryInfo.totalJSHeapSize).padEnd(11)} ${String(debug.dataQuality.memoryInfo.totalJSHeapSize - normal.dataQuality.memoryInfo.totalJSHeapSize > 0 ? '+' : '')}${(debug.dataQuality.memoryInfo.totalJSHeapSize - normal.dataQuality.memoryInfo.totalJSHeapSize).toFixed(2)}MB │`);
            lines.push('└─────────────────────────────────────────────────────────────────────────┘');
            lines.push('');
        }

        // Sample provider details
        lines.push('┌─────────────────────────────────────────────────────────────────────────┐');
        lines.push('│ PROVIDER DATA SAMPLE (First 5 Movies - Normal Mode)                    │');
        lines.push('├─────────────────────────────────────────────────────────────────────────┤');
        normal.dataQuality.providerDetails.forEach((movie, idx) => {
            const title = movie.title.substring(0, 40).padEnd(40);
            const providers = String(movie.providerCount).padStart(2);
            const status = movie.hasProviders ? '✅' : '❌';
            lines.push(`│ ${idx + 1}. ${title} Providers: ${providers} ${status}  │`);
        });
        lines.push('└─────────────────────────────────────────────────────────────────────────┘');
        lines.push('');
    }

    lines.push('═══════════════════════════════════════════════════════════════════════════');
    lines.push('                                  SUMMARY');
    lines.push('═══════════════════════════════════════════════════════════════════════════');
    lines.push('');

    // Overall summary
    const ms2Normal = results.movieshows2.normal;
    const ms2Debug = results.movieshows2.debug;
    const ms3Normal = results.movieshows3.normal;
    const ms3Debug = results.movieshows3.debug;

    lines.push('CONSOLE LOGGING:');
    lines.push(`  MOVIESHOWS2 Normal:  ${ms2Normal?.consoleLogs.total < 10 ? '✅ Minimal logs (as expected)' : '⚠️  Excessive logs'}`);
    lines.push(`  MOVIESHOWS2 Debug:   ${ms2Debug?.consoleLogs.total > ms2Normal?.consoleLogs.total ? '✅ Verbose logs (as expected)' : '❌ Debug mode not working'}`);
    lines.push(`  MOVIESHOWS3 Normal:  ${ms3Normal?.consoleLogs.total < 10 ? '✅ Minimal logs (as expected)' : '⚠️  Excessive logs'}`);
    lines.push(`  MOVIESHOWS3 Debug:   ${ms3Debug?.consoleLogs.total > ms3Normal?.consoleLogs.total ? '✅ Verbose logs (as expected)' : '❌ Debug mode not working'}`);
    lines.push('');

    lines.push('DATA INTEGRITY:');
    lines.push(`  MOVIESHOWS2:  ${ms2Normal?.dataQuality.totalMovies === ms2Debug?.dataQuality.totalMovies ? '✅ Data consistent between modes' : '❌ Data mismatch'}`);
    lines.push(`  MOVIESHOWS3:  ${ms3Normal?.dataQuality.totalMovies === ms3Debug?.dataQuality.totalMovies ? '✅ Data consistent between modes' : '❌ Data mismatch'}`);
    lines.push('');

    lines.push('PROVIDER BADGES:');
    lines.push(`  MOVIESHOWS2:  ${ms2Normal?.dataQuality.providerBadgesInDOM > 0 ? '✅ Rendering correctly' : '❌ Not rendering'}`);
    lines.push(`  MOVIESHOWS3:  ${ms3Normal?.dataQuality.providerBadgesInDOM > 0 ? '✅ Rendering correctly' : '❌ Not rendering'}`);
    lines.push('');

    lines.push('JAVASCRIPT ERRORS:');
    lines.push(`  MOVIESHOWS2 Normal:  ${ms2Normal?.jsErrors.total === 0 ? '✅ No errors' : `⚠️  ${ms2Normal?.jsErrors.total} error(s)`}`);
    lines.push(`  MOVIESHOWS2 Debug:   ${ms2Debug?.jsErrors.total === 0 ? '✅ No errors' : `⚠️  ${ms2Debug?.jsErrors.total} error(s)`}`);
    lines.push(`  MOVIESHOWS3 Normal:  ${ms3Normal?.jsErrors.total === 0 ? '✅ No errors' : `⚠️  ${ms3Normal?.jsErrors.total} error(s)`}`);
    lines.push(`  MOVIESHOWS3 Debug:   ${ms3Debug?.jsErrors.total === 0 ? '✅ No errors' : `⚠️  ${ms3Debug?.jsErrors.total} error(s)`}`);
    lines.push('');

    lines.push('PERFORMANCE IMPACT:');
    const ms2LoadDiff = ms2Debug?.loadTime - ms2Normal?.loadTime;
    const ms3LoadDiff = ms3Debug?.loadTime - ms3Normal?.loadTime;
    lines.push(`  MOVIESHOWS2:  Debug mode adds ${ms2LoadDiff > 0 ? '+' : ''}${ms2LoadDiff}ms to load time`);
    lines.push(`  MOVIESHOWS3:  Debug mode adds ${ms3LoadDiff > 0 ? '+' : ''}${ms3LoadDiff}ms to load time`);
    lines.push('');

    lines.push('═══════════════════════════════════════════════════════════════════════════');
    lines.push('                              END OF REPORT');
    lines.push('═══════════════════════════════════════════════════════════════════════════');

    return lines.join('\n');
}
