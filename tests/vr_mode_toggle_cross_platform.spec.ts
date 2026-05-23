/**
 * VR Mode Toggle Cross-Platform Test Suite
 * Tests Simple/Advanced mode toggle on:
 * - Mobile (Android/Samsung Galaxy)
 * - Meta Quest 3 (with/without controllers)
 * - Windows Desktop (Edge/Chrome)
 */

import { test, expect, devices } from '@playwright/test';

const BASE_URL = process.env.VERIFY_REMOTE === '1' 
  ? 'https://findtorontoevents.ca/vr/index.html'
  : 'http://localhost:5173/vr/index.html';

// Helper to clear localStorage after page load
async function clearVRState(page: any) {
  try {
    await page.evaluate(() => {
      try {
        localStorage.removeItem('vr-ui-mode');
        localStorage.removeItem('vr-mode-seen');
        localStorage.removeItem('vr-desktop-mode');
      } catch (e) {
        console.log('localStorage not available');
      }
    });
  } catch (e) {
    // Ignore errors
  }
}

// ==========================================
// MOBILE TESTS (Android/Samsung Galaxy)
// ==========================================
test.describe('Mobile - Samsung Galaxy S21', () => {
  test.use({
    ...devices['Samsung Galaxy S21'],
    viewport: { width: 384, height: 854 },
  });

  test('mobile: should show mode selector on first visit', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Mode selector should appear
    const selector = page.locator('#vr-mode-selector');
    await expect(selector).toBeVisible({ timeout: 5000 });

    // Both buttons should be visible
    await expect(page.locator('#vr-mode-simple-btn')).toBeVisible();
    await expect(page.locator('#vr-mode-advanced-btn')).toBeVisible();
  });

  test('mobile: should select simple mode and redirect to mobile-index', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Click Simple Mode
    const simpleBtn = page.locator('#vr-mode-simple-btn');
    await simpleBtn.click();

    // Wait for potential redirect
    await page.waitForTimeout(2000);

    // Check if redirected to mobile version
    const url = page.url();
    console.log('Mobile Simple Mode URL:', url);

    // Should show mobile page OR apply simple mode
    if (url.includes('mobile-index')) {
      expect(url).toContain('mobile-index');
    } else {
      // Check simple mode was applied via localStorage
      const mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
      expect(mode).toBe('simple');
    }
  });

  test('mobile: should select advanced mode', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Click Advanced Mode
    const advancedBtn = page.locator('#vr-mode-advanced-btn');
    await advancedBtn.click();

    await page.waitForTimeout(1000);

    // Check mode was saved
    const mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('advanced');

    // Selector should be gone
    await expect(page.locator('#vr-mode-selector')).not.toBeVisible();
  });

  test('mobile: mode toggle button should work after selection', async ({ page }) => {
    // Set initial state
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Select Advanced mode first
    await page.locator('#vr-mode-advanced-btn').click();
    await page.waitForTimeout(1000);

    // Click the mode toggle button
    const toggle = page.locator('#vr-mode-toggle');
    if (await toggle.isVisible().catch(() => false)) {
      await toggle.click();
      await page.waitForTimeout(500);

      // Mode should have toggled
      const mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
      expect(mode).toBe('simple');
    }
  });
});

// ==========================================
// DESKTOP WINDOWS - CHROME
// ==========================================
test.describe('Desktop - Chrome on Windows', () => {
  test.use({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  });

  test('desktop chrome: should show mode selector on first visit', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    const selector = page.locator('#vr-mode-selector');
    await expect(selector).toBeVisible({ timeout: 5000 });

    await expect(page.locator('#vr-mode-simple-btn')).toBeVisible();
    await expect(page.locator('#vr-mode-advanced-btn')).toBeVisible();
  });

  test('desktop chrome: clicking advanced mode should apply it', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    const advancedBtn = page.locator('#vr-mode-advanced-btn');
    await advancedBtn.click();

    await page.waitForTimeout(1000);

    // Should NOT redirect to mobile
    const url = page.url();
    expect(url).not.toContain('mobile-index');

    // Mode should be saved
    const mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('advanced');

    // Selector should close
    await expect(page.locator('#vr-mode-selector')).not.toBeVisible();

    // Toast should appear
    const bodyText = await page.locator('body').textContent();
    expect(bodyText).toContain('Advanced Mode');
  });

  test('desktop chrome: clicking simple mode should apply it', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    const simpleBtn = page.locator('#vr-mode-simple-btn');
    await simpleBtn.click();

    await page.waitForTimeout(1000);

    // Should NOT redirect to mobile
    const url = page.url();
    expect(url).not.toContain('mobile-index');

    // Mode should be saved
    const mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('simple');

    // Selector should close
    await expect(page.locator('#vr-mode-selector')).not.toBeVisible();
  });

  test('desktop chrome: refresh should stay on same page', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Select advanced mode
    await page.locator('#vr-mode-advanced-btn').click();
    await page.waitForTimeout(1000);

    // Refresh page
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Should still be on desktop VR, not mobile
    const url = page.url();
    expect(url).not.toContain('mobile-index');

    // Mode should persist
    const mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('advanced');

    // Mode selector should NOT show again (already seen)
    const selector = page.locator('#vr-mode-selector');
    await expect(selector).not.toBeVisible();
  });

  test('desktop chrome: mode toggle button at bottom should work', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Dismiss selector
    await page.locator('#vr-mode-advanced-btn').click();
    await page.waitForTimeout(1000);

    // Find and click mode toggle button
    const toggle = page.locator('#vr-mode-toggle');
    await expect(toggle).toBeVisible();

    // Click to toggle
    await toggle.click();
    await page.waitForTimeout(500);

    // Should toggle to simple
    let mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('simple');

    // Click again
    await toggle.click();
    await page.waitForTimeout(500);

    // Should toggle back to advanced
    mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('advanced');
  });
});

// ==========================================
// DESKTOP WINDOWS - EDGE
// ==========================================
test.describe('Desktop - Edge on Windows', () => {
  test.use({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
  });

  test('desktop edge: should handle mode selection', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Select simple mode
    await page.locator('#vr-mode-simple-btn').click();
    await page.waitForTimeout(1000);

    // Should stay on desktop
    const url = page.url();
    expect(url).not.toContain('mobile-index');

    // Mode saved
    const mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('simple');
  });

  test('desktop edge: refresh should not redirect to mobile', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Select mode
    await page.locator('#vr-mode-advanced-btn').click();
    await page.waitForTimeout(1000);

    // Refresh
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Verify still on desktop
    const url = page.url();
    console.log('Edge refresh URL:', url);
    expect(url).not.toContain('mobile-index');
  });
});

// ==========================================
// META QUEST 3 TESTS
// ==========================================
test.describe('Meta Quest 3 - VR Browser', () => {
  // Meta Quest 3 browser user agent
  test.use({
    viewport: { width: 1832, height: 1920 }, // Quest 3 resolution
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64; Quest 3) AppleWebKit/537.36 (KHTML, like Gecko) OculusBrowser/31.0.0.0.0.1234567 SamsungBrowser/4.0 Chrome/120.0.0.0 VR Safari/537.36',
  });

  test('quest3: should show mode selector', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    const selector = page.locator('#vr-mode-selector');
    await expect(selector).toBeVisible({ timeout: 5000 });
  });

  test('quest3: should NOT redirect to mobile-index', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Select simple mode
    await page.locator('#vr-mode-simple-btn').click();
    await page.waitForTimeout(1500);

    // Should stay in VR mode, not go to mobile
    const url = page.url();
    console.log('Quest 3 URL:', url);
    expect(url).not.toContain('mobile-index');
  });

  test('quest3 with controllers: mode toggle should work', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Dismiss selector
    await page.locator('#vr-mode-advanced-btn').click();
    await page.waitForTimeout(1000);

    // Find toggle button
    const toggle = page.locator('#vr-mode-toggle');
    await expect(toggle).toBeVisible();

    // Test toggle
    await toggle.click();
    await page.waitForTimeout(500);

    const mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('simple');
  });
});

// ==========================================
// DESKTOP WITH TOUCH SCREEN (Convertible Laptop)
// ==========================================
test.describe('Desktop with Touch (Convertible)', () => {
  test.use({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    // Simulate touch support but large screen
    hasTouch: true,
  });

  test('convertible laptop: should NOT redirect to mobile', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Should stay on desktop VR
    const url = page.url();
    console.log('Convertible URL:', url);
    expect(url).not.toContain('mobile-index');

    // Mode selector should appear for first-time
    const selector = page.locator('#vr-mode-selector');
    await expect(selector).toBeVisible({ timeout: 5000 });
  });
});

// ==========================================
// MODE PERSISTENCE TESTS
// ==========================================
test.describe('Mode Persistence Across Sessions', () => {
  test('simple mode should persist after refresh', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Select simple mode
    await page.locator('#vr-mode-simple-btn').click();
    await page.waitForTimeout(1000);

    // Refresh
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Mode should persist
    const mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('simple');

    // Selector should NOT show (already seen)
    await expect(page.locator('#vr-mode-selector')).not.toBeVisible();
  });

  test('advanced mode should persist after refresh', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Select advanced mode
    await page.locator('#vr-mode-advanced-btn').click();
    await page.waitForTimeout(1000);

    // Refresh
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Mode should persist
    const mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('advanced');
  });
});

// ==========================================
// CONSOLE ERROR CHECKS
// ==========================================
test.describe('Console Error Checks', () => {
  test('no errors when selecting modes', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    page.on('pageerror', (error) => {
      errors.push(error.message);
    });

    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Select simple mode
    await page.locator('#vr-mode-simple-btn').click();
    await page.waitForTimeout(1000);

    // Check for mode toggle related errors
    const modeErrors = errors.filter(e => 
      e.toLowerCase().includes('mode') || 
      e.toLowerCase().includes('toggle') ||
      e.toLowerCase().includes('vr-')
    );

    expect(modeErrors).toHaveLength(0);
  });
});
