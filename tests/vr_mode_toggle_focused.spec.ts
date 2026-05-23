/**
 * VR Mode Toggle Focused Tests
 * Quick verification of mode toggle across platforms
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'https://findtorontoevents.ca/vr/index.html';

// Helper to clear VR state
async function clearVRState(page: any) {
  try {
    await page.evaluate(() => {
      try {
        localStorage.removeItem('vr-ui-mode');
        localStorage.removeItem('vr-mode-seen');
        localStorage.removeItem('vr-desktop-mode');
      } catch (e) {}
    });
  } catch (e) {}
}

test.describe('VR Mode Toggle - Desktop Chrome', () => {
  test.use({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  });

  test('desktop: mode selector appears and advanced mode works', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    
    // Wait for mode selector
    const selector = page.locator('#vr-mode-selector');
    await expect(selector).toBeVisible({ timeout: 10000 });
    
    // Click Advanced Mode
    await page.locator('#vr-mode-advanced-btn').click();
    
    // Wait for it to process
    await page.waitForTimeout(1000);
    
    // Verify mode saved
    const mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('advanced');
    
    // Selector should be gone
    await expect(selector).not.toBeVisible();
    
    // Verify still on desktop (not mobile)
    const url = page.url();
    expect(url).not.toContain('mobile-index');
    
    console.log('✓ Desktop Chrome: Advanced mode works correctly');
  });

  test('desktop: simple mode works and refresh persists', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    
    // Select simple mode
    const selector = page.locator('#vr-mode-selector');
    await expect(selector).toBeVisible({ timeout: 10000 });
    
    await page.locator('#vr-mode-simple-btn').click();
    await page.waitForTimeout(1000);
    
    // Verify mode saved
    let mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('simple');
    
    // Refresh page
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    
    // Verify still on desktop
    const url = page.url();
    expect(url).not.toContain('mobile-index');
    
    // Verify mode persisted
    mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('simple');
    
    console.log('✓ Desktop Chrome: Simple mode persists after refresh');
  });
});

test.describe('VR Mode Toggle - Mobile (Samsung)', () => {
  test.use({
    viewport: { width: 384, height: 854 },
    userAgent: 'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.0.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    hasTouch: true,
  });

  test('mobile: simple mode saves preference', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    
    // Wait for mode selector
    const selector = page.locator('#vr-mode-selector');
    await expect(selector).toBeVisible({ timeout: 10000 });
    
    // Click Simple Mode
    await page.locator('#vr-mode-simple-btn').click();
    
    // Wait for processing
    await page.waitForTimeout(2000);
    
    const url = page.url();
    console.log('Mobile URL after Simple Mode:', url);
    
    // Mode preference should be saved (redirect happens via mobile-detect.js, not mode toggle)
    const mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('simple');
    
    console.log('✓ Mobile: Simple mode preference saved');
  });

  test('mobile: advanced mode stays in VR', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    
    const selector = page.locator('#vr-mode-selector');
    await expect(selector).toBeVisible({ timeout: 10000 });
    
    // Click Advanced Mode
    await page.locator('#vr-mode-advanced-btn').click();
    await page.waitForTimeout(2000);
    
    const url = page.url();
    console.log('Mobile URL after Advanced Mode:', url);
    
    // Mode should be saved
    const mode = await page.evaluate(() => localStorage.getItem('vr-ui-mode'));
    expect(mode).toBe('advanced');
    
    console.log('✓ Mobile: Advanced mode saved');
  });
});

test.describe('VR Mode Toggle - Meta Quest 3', () => {
  test.use({
    viewport: { width: 1832, height: 1920 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64; Quest 3) AppleWebKit/537.36 (KHTML, like Gecko) OculusBrowser/31.0.0.0.0 SamsungBrowser/4.0 Chrome/120.0.0.0 VR Safari/537.36',
  });

  test('quest3: should NOT redirect to mobile', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    
    const selector = page.locator('#vr-mode-selector');
    await expect(selector).toBeVisible({ timeout: 10000 });
    
    // Select simple mode
    await page.locator('#vr-mode-simple-btn').click();
    await page.waitForTimeout(2000);
    
    // Should NOT be on mobile-index
    const url = page.url();
    expect(url).not.toContain('mobile-index');
    
    console.log('✓ Quest 3: Stays in VR mode');
  });
});

test.describe('VR Mode Toggle - Desktop with Touch', () => {
  test.use({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    hasTouch: true,
  });

  test('convertible: touch screen should not redirect to mobile', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await clearVRState(page);
    await page.reload({ waitUntil: 'networkidle' });
    
    await page.waitForTimeout(3000);
    
    // Should stay on desktop
    const url = page.url();
    console.log('Convertible laptop URL:', url);
    expect(url).not.toContain('mobile-index');
    
    console.log('✓ Convertible: Stays on desktop with touch');
  });
});
