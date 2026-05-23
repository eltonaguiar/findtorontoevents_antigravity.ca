/**
 * Debug Mode Performance & Data Quality Test
 * Tests MOVIESHOWS2 and MOVIESHOWS3 with and without ?debug=1 parameter
 */

const { chromium } = require('playwright');
const fs = require('fs');

const MOVIESHOWS2_URL = 'https://findtorontoevents.ca/MOVIESHOWS2/';
const MOVIESHOWS3_URL = 'https://findtorontoevents.ca/MOVIESHOWS3/';
const REPORT_PATH = 'e:/findtorontoevents_antigravity.ca/movieshows_performance_test.txt';

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
 * Collect comprehensive metrics for a given URL
 */
async function collectMetrics(page, appName, mode, url) {
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

        if (msg.type() === 'error') {
            consoleErrors.push({
                text: msg.text(),
                timestamp: Date.now()
            });
        }
    });

    // Capture JavaScript errors
    page.on('pageerror', error => {
        jsErrors.push({
            message: error.message,
            stack: error.stack,
            timestamp: Date.now()
        });
    });

    console.log(`\n🧪 Testing ${appName} - ${mode.toUpperCase()} mode`);
    console.log(`   URL: ${url}`);

    // Navigate to page
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });

    // Wait for movies to load
    try {
        await page.waitForFunction(() => {
            return window.allMovies && window.allMovies.length > 0;
        }, { timeout: 30000 });
    } catch (e) {
        console.log(`   ⚠️  Warning: Movies didn't load within timeout`);
    }

    // Additional wait for rendering
    await page.waitForTimeout(5000);

    const loadTime = Date.now() - startTime;

    // Check for specific console log patterns
    const debugLogs = consoleLogs.filter(log =>
        log.text.includes('DEBUG:') ||
        log.text.includes('DEBUG MODE ENABLED') ||
        log.text.includes('Provider') ||
        log.text.includes('Loading') ||
        log.text.includes('Movies loaded')
    );

    // Debug mode is active if we see the debug mode message
    const debugModeMessage = consoleLogs.find(log => log.text.includes('DEBUG MODE ENABLED'));

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

    console.log(`   ✓ Total movies: ${dataMetrics.totalMovies}`);
    console.log(`   ✓ Movies with providers: ${dataMetrics.moviesWithProviders}`);
    console.log(`   ✓ Provider badges rendered: ${dataMetrics.providerBadgesInDOM}`);
    console.log(`   ✓ Console logs: ${consoleLogs.length} (debug logs: ${debugLogs.length})`);
    console.log(`   ✓ Debug mode active: ${!!debugModeMessage}`);
    console.log(`   ✓ Load time: ${loadTime}ms`);
    console.log(`   ✓ JS Errors: ${jsErrors.length}`);
    if (dataMetrics.memoryInfo) {
        console.log(`   ✓ Memory used: ${dataMetrics.memoryInfo.usedJSHeapSize}MB`);
    }

    // Show console log samples for debugging
    if (mode === 'debug' && consoleLogs.length > 0) {
        console.log(`\n   Console Log Samples (first 5):`);
        consoleLogs.slice(0, 5).forEach((log, idx) => {
            console.log(`     ${idx + 1}. [${log.type}] ${log.text.substring(0, 80)}`);
        });
    }

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
            debugModeActive: !!debugModeMessage,
            providerDetails: providerDetails
        }
    };
}

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

/**
 * Main test execution
 */
(async () => {
    console.log('\n═══════════════════════════════════════════════════════════════════════════');
    console.log('            DEBUG MODE PERFORMANCE & DATA QUALITY TEST');
    console.log('═══════════════════════════════════════════════════════════════════════════\n');

    const browser = await chromium.launch({
        headless: true,
        args: ['--enable-precise-memory-info']  // Enable memory profiling
    });

    try {
        // Test MOVIESHOWS2 - Normal Mode
        let context = await browser.newContext();
        let page = await context.newPage();
        testResults.movieshows2.normal = await collectMetrics(page, 'MOVIESHOWS2', 'normal', MOVIESHOWS2_URL);
        await context.close();

        // Test MOVIESHOWS2 - Debug Mode
        context = await browser.newContext();
        page = await context.newPage();
        testResults.movieshows2.debug = await collectMetrics(page, 'MOVIESHOWS2', 'debug', MOVIESHOWS2_URL + '?debug=1');
        await context.close();

        // Test MOVIESHOWS3 - Normal Mode
        context = await browser.newContext();
        page = await context.newPage();
        testResults.movieshows3.normal = await collectMetrics(page, 'MOVIESHOWS3', 'normal', MOVIESHOWS3_URL);
        await context.close();

        // Test MOVIESHOWS3 - Debug Mode
        context = await browser.newContext();
        page = await context.newPage();
        testResults.movieshows3.debug = await collectMetrics(page, 'MOVIESHOWS3', 'debug', MOVIESHOWS3_URL + '?debug=1');
        await context.close();

        // Generate and save report
        console.log('\n\n📊 Generating Performance Report...\n');
        const report = generateReport(testResults);

        fs.writeFileSync(REPORT_PATH, report, 'utf8');
        console.log(`✅ Report saved to: ${REPORT_PATH}\n`);

        // Print summary to console
        console.log('\n' + report);

    } catch (error) {
        console.error('❌ Test failed:', error);
    } finally {
        await browser.close();
    }

    console.log('\n✅ All tests completed!\n');
})();
