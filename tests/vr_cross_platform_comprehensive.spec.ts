/**
 * VR Cross-Platform Comprehensive Test Suite
 * 
 * Tests both VR URLs across desktop, mobile, and tablet viewports
 * - https://findtorontoevents.ca/vr/ (main VR hub)
 * - https://findtorontoevents.ca/vr/mobile-index.html (mobile VR)
 * 
 * Checks for:
 * - JavaScript errors
 * - Correct page loading
 * - Redirection behavior
 * - Console warnings/errors
 * - WebXR availability
 */

import { test, expect, devices } from '@playwright/test';

const BASE_URL = 'https://findtorontoevents.ca';
const VR_URL = `${BASE_URL}/vr/`;
const MOBILE_VR_URL = `${BASE_URL}/vr/mobile-index.html`;

// Collect console errors and warnings
interface ConsoleLog {
  type: string;
  text: string;
  location?: string;
}

// Device configurations
const deviceConfigs = {
  desktop: {
    name: 'Desktop Chrome',
    viewport: { width: 1280, height: 720 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  },
  mobile_iPhone: {
    name: 'iPhone 14',
    viewport: { width: 390, height: 844 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
  },
  mobile_Android: {
    name: 'Android Pixel 7',
    viewport: { width: 412, height: 915 },
    userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
  },
  tablet: {
    name: 'iPad Pro',
    viewport: { width: 1024, height: 1366 },
    userAgent: 'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
  },
  vr_headset: {
    name: 'Meta Quest 3',
    viewport: { width: 1832, height: 1920 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) OculusBrowser/32.0.0.0.0 SamsungBrowser/4.0 Chrome/120.0.0.0 VR Safari/537.36'
  }
};

test.describe('VR Cross-Platform Tests', () => {
  let consoleLogs: ConsoleLog[] = [];
  let pageErrors: Error[] = [];

  // Reset collectors before each test
  test.beforeEach(() => {
    consoleLogs = [];
    pageErrors = [];
  });

  // Helper to setup console/error listeners
  async function setupListeners(page: any) {
    page.on('console', (msg: any) => {
      const log: ConsoleLog = {
        type: msg.type(),
        text: msg.text(),
        location: msg.location()?.url
      };
      consoleLogs.push(log);
      
      // Log to test output for debugging
      if (msg.type() === 'error' || msg.type() === 'warning') {
        console.log(`[${msg.type().toUpperCase()}] ${msg.text()}`);
      }
    });

    page.on('pageerror', (error: Error) => {
      pageErrors.push(error);
      console.log(`[PAGE ERROR] ${error.message}`);
    });
  }

  // Helper to check for critical JS errors
  function getCriticalErrors(): ConsoleLog[] {
    const criticalPatterns = [
      'Uncaught',
      'undefined is not',
      'null is not',
      'Cannot read',
      'Cannot set',
      'is not a function',
      'is not defined',
      'SyntaxError',
      'ReferenceError',
      'TypeError',
      'A-Frame',
      'aframe',
      'THREE.',
      'WebXR',
      'webxr',
      'XR',
      'vr-mode',
      'enter-vr',
      'exit-vr'
    ];
    
    return consoleLogs.filter(log => 
      log.type === 'error' && 
      criticalPatterns.some(pattern => log.text.includes(pattern))
    );
  }

  // Helper to analyze test results
  function analyzeResults(testName: string) {
    const criticalErrors = getCriticalErrors();
    
    console.log('\n=== Test Results: ' + testName + ' ===');
    console.log('Total console logs:', consoleLogs.length);
    console.log('Page errors:', pageErrors.length);
    console.log('Critical JS errors:', criticalErrors.length);
    
    if (criticalErrors.length > 0) {
      console.log('\nCritical Errors:');
      criticalErrors.forEach((err, i) => {
        console.log(`  ${i + 1}. [${err.type}] ${err.text.substring(0, 200)}`);
      });
    }
    
    return {
      hasCriticalErrors: criticalErrors.length > 0,
      totalErrors: consoleLogs.filter(l => l.type === 'error').length,
      totalWarnings: consoleLogs.filter(l => l.type === 'warning').length,
      pageErrorCount: pageErrors.length
    };
  }

  // ============================================
  // TEST 1: Desktop access to /vr/
  // ============================================
  test('Desktop - Main VR Hub loads without errors', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: deviceConfigs.desktop.viewport,
      userAgent: deviceConfigs.desktop.userAgent
    });
    
    const page = await context.newPage();
    await setupListeners(page);
    
    // Navigate to main VR hub
    const response = await page.goto(VR_URL, {
      waitUntil: 'networkidle',
      timeout: 60000
    });
    
    expect(response?.status()).toBe(200);
    expect(page.url()).toBe(VR_URL); // Should NOT redirect
    
    // Wait for A-Frame to initialize
    await page.waitForTimeout(3000);
    
    // Check page title
    await expect(page).toHaveTitle(/VR|Virtual Reality|Hub/i);
    
    // Check for A-Frame scene
    const hasAFrame = await page.locator('a-scene').count() > 0;
    expect(hasAFrame, 'A-Frame scene should be present').toBe(true);
    
    // Analyze results
    const results = analyzeResults('Desktop VR Hub');
    expect(results.hasCriticalErrors, 'Should have no critical JS errors').toBe(false);
    expect(results.pageErrorCount, 'Should have no page errors').toBe(0);
    
    await context.close();
  });

  // ============================================
  // TEST 2: Desktop access to mobile-index (should work but show mobile UI)
  // ============================================
  test('Desktop - Mobile VR page loads without errors', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: deviceConfigs.desktop.viewport,
      userAgent: deviceConfigs.desktop.userAgent
    });
    
    const page = await context.newPage();
    await setupListeners(page);
    
    const response = await page.goto(MOBILE_VR_URL, {
      waitUntil: 'networkidle',
      timeout: 60000
    });
    
    expect(response?.status()).toBe(200);
    
    // Wait for scripts to load
    await page.waitForTimeout(3000);
    
    // Analyze results
    const results = analyzeResults('Desktop Mobile VR');
    expect(results.hasCriticalErrors, 'Should have no critical JS errors').toBe(false);
    
    await context.close();
  });

  // ============================================
  // TEST 3: Mobile access to /vr/ (redirection test)
  // ============================================
  test('Mobile iPhone - Should redirect or handle mobile gracefully', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: deviceConfigs.mobile_iPhone.viewport,
      userAgent: deviceConfigs.mobile_iPhone.userAgent,
      isMobile: true,
      hasTouch: true
    });
    
    const page = await context.newPage();
    await setupListeners(page);
    
    // Monitor navigation events
    let finalUrl = '';
    page.on('framenavigated', (frame: any) => {
      if (frame === page.mainFrame()) {
        finalUrl = frame.url();
      }
    });
    
    const response = await page.goto(VR_URL, {
      waitUntil: 'networkidle',
      timeout: 60000
    });
    
    // Wait for any redirects to complete
    await page.waitForTimeout(2000);
    
    console.log('Initial URL:', VR_URL);
    console.log('Final URL:', finalUrl || page.url());
    
    // Check if redirected to mobile page
    const currentUrl = page.url();
    const wasRedirected = currentUrl.includes('mobile-index');
    
    if (wasRedirected) {
      console.log('✓ Mobile user was redirected to mobile-index.html');
      expect(currentUrl).toContain('mobile-index');
    } else {
      console.log('✓ Mobile user stayed on main VR page');
      // If not redirected, the page should still work
      const hasAFrame = await page.locator('a-scene').count() > 0;
      expect(hasAFrame || currentUrl.includes('mobile'), 'Should have A-Frame or be mobile page').toBe(true);
    }
    
    // Analyze results
    const results = analyzeResults('Mobile iPhone VR');
    expect(results.hasCriticalErrors, 'Should have no critical JS errors on mobile').toBe(false);
    
    await context.close();
  });

  // ============================================
  // TEST 4: Mobile Android - Direct mobile page access
  // ============================================
  test('Mobile Android - Mobile VR page loads correctly', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: deviceConfigs.mobile_Android.viewport,
      userAgent: deviceConfigs.mobile_Android.userAgent,
      isMobile: true,
      hasTouch: true
    });
    
    const page = await context.newPage();
    await setupListeners(page);
    
    const response = await page.goto(MOBILE_VR_URL, {
      waitUntil: 'networkidle',
      timeout: 60000
    });
    
    expect(response?.status()).toBe(200);
    
    // Check for mobile-specific elements
    await page.waitForTimeout(2000);
    
    // Mobile page should have touch-friendly UI
    const bodyClass = await page.evaluate(() => document.body.className);
    console.log('Body classes:', bodyClass);
    
    // Analyze results
    const results = analyzeResults('Mobile Android VR');
    expect(results.hasCriticalErrors, 'Should have no critical JS errors on Android').toBe(false);
    
    await context.close();
  });

  // ============================================
  // TEST 5: Tablet access
  // ============================================
  test('Tablet iPad - VR page loads correctly', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: deviceConfigs.tablet.viewport,
      userAgent: deviceConfigs.tablet.userAgent,
      isMobile: true, // iPad often reports as mobile
      hasTouch: true
    });
    
    const page = await context.newPage();
    await setupListeners(page);
    
    const response = await page.goto(VR_URL, {
      waitUntil: 'networkidle',
      timeout: 60000
    });
    
    expect(response?.status()).toBe(200);
    
    // Wait for load
    await page.waitForTimeout(3000);
    
    // Analyze results
    const results = analyzeResults('Tablet iPad VR');
    expect(results.hasCriticalErrors, 'Should have no critical JS errors on tablet').toBe(false);
    
    await context.close();
  });

  // ============================================
  // TEST 6: VR Headset (Meta Quest) simulation
  // ============================================
  test('VR Headset - Quest browser simulation', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: deviceConfigs.vr_headset.viewport,
      userAgent: deviceConfigs.vr_headset.userAgent
    });
    
    const page = await context.newPage();
    await setupListeners(page);
    
    const response = await page.goto(VR_URL, {
      waitUntil: 'networkidle',
      timeout: 60000
    });
    
    expect(response?.status()).toBe(200);
    
    // Check for WebXR availability
    const webXRSupport = await page.evaluate(() => {
      return {
        isSecureContext: window.isSecureContext,
        hasNavigatorXR: 'xr' in navigator,
        hasWebXRPolyfill: typeof (window as any).WebXRPolyfill !== 'undefined',
        hasAFrame: typeof (window as any).AFRAME !== 'undefined',
        aframeVersion: (window as any).AFRAME?.version || 'not loaded'
      };
    });
    
    console.log('WebXR Support:', webXRSupport);
    
    // Wait for A-Frame
    await page.waitForTimeout(3000);
    
    // Check if A-Frame scene initialized
    const aframeStatus = await page.evaluate(() => {
      const scene = document.querySelector('a-scene') as any;
      return {
        hasScene: !!scene,
        isVRMode: scene?.is?.('vr-mode') || false,
        renderer: !!scene?.renderer
      };
    });
    
    console.log('A-Frame Status:', aframeStatus);
    
    // Analyze results
    const results = analyzeResults('VR Headset');
    expect(results.hasCriticalErrors, 'Should have no critical JS errors in VR mode').toBe(false);
    
    await context.close();
  });

  // ============================================
  // TEST 7: JavaScript Error Sweep - All URLs
  // ============================================
  test('JS Error Sweep - All VR pages', async ({ browser }) => {
    const urls = [VR_URL, MOBILE_VR_URL];
    const devices = [
      deviceConfigs.desktop,
      deviceConfigs.mobile_iPhone,
      deviceConfigs.mobile_Android
    ];
    
    let totalErrors = 0;
    let totalWarnings = 0;
    
    for (const url of urls) {
      for (const device of devices) {
        console.log(`\nTesting ${url} on ${device.name}`);
        
        const context = await browser.newContext({
          viewport: device.viewport,
          userAgent: device.userAgent,
          isMobile: device.name.includes('Mobile'),
          hasTouch: device.name.includes('Mobile') || device.name.includes('Tablet')
        });
        
        const page = await context.newPage();
        
        // Collect errors
        const errors: ConsoleLog[] = [];
        page.on('console', (msg: any) => {
          if (msg.type() === 'error' || msg.type() === 'warning') {
            errors.push({ type: msg.type(), text: msg.text() });
          }
        });
        
        try {
          await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
          await page.waitForTimeout(2000);
        } catch (e) {
          console.log('Navigation error:', (e as Error).message);
        }
        
        const criticalErrors = errors.filter(e => 
          e.type === 'error' && 
          (e.text.includes('Uncaught') || 
           e.text.includes('undefined') || 
           e.text.includes('null') ||
           e.text.includes('A-Frame') ||
           e.text.includes('aframe'))
        );
        
        if (criticalErrors.length > 0) {
          console.log(`  ⚠ ${criticalErrors.length} critical errors found`);
          criticalErrors.forEach((err, i) => {
            console.log(`    ${i + 1}. ${err.text.substring(0, 100)}`);
          });
        } else {
          console.log(`  ✓ No critical errors`);
        }
        
        totalErrors += errors.filter(e => e.type === 'error').length;
        totalWarnings += errors.filter(e => e.type === 'warning').length;
        
        await context.close();
      }
    }
    
    console.log(`\n=== Final JS Error Sweep Results ===`);
    console.log(`Total errors across all tests: ${totalErrors}`);
    console.log(`Total warnings across all tests: ${totalWarnings}`);
    
    // Expect reasonable error count (some non-critical errors are acceptable)
    expect(totalErrors, 'Should have minimal JS errors').toBeLessThan(10);
  });

  // ============================================
  // TEST 8: Specific redirection behavior
  // ============================================
  test('Redirection - Desktop should NOT be redirected to mobile', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: deviceConfigs.desktop.viewport,
      userAgent: deviceConfigs.desktop.userAgent
    });
    
    const page = await context.newPage();
    
    // Track all navigation
    const navigations: string[] = [];
    page.on('framenavigated', (frame: any) => {
      if (frame === page.mainFrame()) {
        navigations.push(frame.url());
      }
    });
    
    await page.goto(VR_URL, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(2000);
    
    const finalUrl = page.url();
    
    console.log('Navigation chain:', navigations);
    console.log('Final URL:', finalUrl);
    
    // Desktop should stay on main VR page, not be forced to mobile
    const wasForcedToMobile = finalUrl.includes('mobile-index') && 
                              !finalUrl.includes('?mobile=') && 
                              !finalUrl.includes('#mobile');
    
    if (wasForcedToMobile) {
      console.error('❌ Desktop user was incorrectly redirected to mobile page!');
    } else {
      console.log('✓ Desktop user stayed on appropriate page');
    }
    
    expect(wasForcedToMobile, 'Desktop should not be forced to mobile page').toBe(false);
    
    await context.close();
  });

  // ============================================
  // TEST 9: Check all VR feature scripts load
  // ============================================
  test('VR Feature Scripts - All load without errors', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: deviceConfigs.desktop.viewport,
      userAgent: deviceConfigs.desktop.userAgent
    });
    
    const page = await context.newPage();
    
    const failedRequests: string[] = [];
    page.on('requestfailed', (request: any) => {
      failedRequests.push(request.url());
      console.log('Failed request:', request.url(), request.failure()?.errorText);
    });
    
    await page.goto(VR_URL, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    // Check for common VR script failures
    const vrScripts = [
      'quick-wins',
      'presence',
      'nav-menu',
      'controller-support',
      'area-guide',
      'comfort',
      'audio',
      'mobile'
    ];
    
    const scriptElements = await page.locator('script[src]').all();
    const loadedScripts = await Promise.all(
      scriptElements.map(async (el) => await el.getAttribute('src'))
    );
    
    console.log('Loaded scripts count:', loadedScripts.length);
    
    // Filter for VR-specific scripts
    const vrLoadedScripts = loadedScripts.filter(src => 
      src && vrScripts.some(vr => src.includes(vr))
    );
    
    console.log('VR scripts found:', vrLoadedScripts);
    
    // Check for 404s in VR scripts
    const failedVRScripts = failedRequests.filter(url => 
      vrScripts.some(vr => url.includes(vr))
    );
    
    if (failedVRScripts.length > 0) {
      console.error('Failed VR scripts:', failedVRScripts);
    }
    
    expect(failedVRScripts.length, 'VR scripts should load without 404s').toBe(0);
    
    await context.close();
  });
});