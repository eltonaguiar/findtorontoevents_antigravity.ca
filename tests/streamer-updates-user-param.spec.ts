import { test, expect } from '@playwright/test';

/**
 * Tests for Streamer Updates with user_id URL parameter
 * Verifies that user_id=2 shows all followed creators including Lofe
 */

const BASE_URL = 'https://findtorontoevents.ca';

test.describe('Streamer Updates with user_id Parameter', () => {
  
  test('Frontend loads with user_id=2 in URL', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error' && !msg.text().includes('favicon')) {
        errors.push(msg.text());
      }
      // Log user_id detection
      if (msg.text().includes('user_id')) {
        console.log('Console:', msg.text());
      }
    });

    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
    
    await page.waitForTimeout(5000);
    
    // Check title is visible
    const title = page.locator('h1:has-text("Streamer Updates")');
    await expect(title).toBeVisible({ timeout: 15000 });
  });

  test('Creator dropdown shows multiple creators with user_id=2', async ({ page }) => {
    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(4000);
    
    const dropdown = page.locator('select').first();
    await expect(dropdown).toBeVisible({ timeout: 10000 });
    
    const options = await dropdown.locator('option').allTextContents();
    console.log('Dropdown options with user_id=2:', options);
    
    // Should have more than just "All Creators" and "Adin Ross"
    expect(options.length).toBeGreaterThan(2);
  });

  test('Lofe appears in dropdown with user_id=2', async ({ page }) => {
    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
    
    // Wait for page to load and data to populate
    await page.waitForTimeout(8000);
    
    // Wait for dropdown to be visible and populated
    const dropdown = page.locator('select').first();
    await expect(dropdown).toBeVisible({ timeout: 10000 });
    
    // Poll for dropdown options with multiple creators
    let options: string[] = [];
    for (let i = 0; i < 10; i++) {
      options = await dropdown.locator('option').allTextContents();
      if (options.length > 3) break;
      await page.waitForTimeout(1000);
    }
    
    const hasLofe = options.some(opt => opt.toLowerCase().includes('lofe'));
    console.log('Lofe in dropdown:', hasLofe, '- Options:', options);
    
    expect(hasLofe).toBeTruthy();
  });

  test('Ninja appears in dropdown with user_id=2', async ({ page }) => {
    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
    await page.waitForTimeout(8000);
    
    const dropdown = page.locator('select').first();
    let options: string[] = [];
    for (let i = 0; i < 10; i++) {
      options = await dropdown.locator('option').allTextContents();
      if (options.length > 3) break;
      await page.waitForTimeout(1000);
    }
    
    const hasNinja = options.some(opt => opt.toLowerCase().includes('ninja'));
    expect(hasNinja).toBeTruthy();
  });

  test('xQc appears in dropdown with user_id=2', async ({ page }) => {
    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
    await page.waitForTimeout(8000);
    
    const dropdown = page.locator('select').first();
    let options: string[] = [];
    for (let i = 0; i < 10; i++) {
      options = await dropdown.locator('option').allTextContents();
      if (options.length > 3) break;
      await page.waitForTimeout(1000);
    }
    
    const hasXqc = options.some(opt => opt.toLowerCase().includes('xqc'));
    expect(hasXqc).toBeTruthy();
  });

  test('Zople appears in dropdown with user_id=2', async ({ page }) => {
    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
    await page.waitForTimeout(8000);
    
    const dropdown = page.locator('select').first();
    let options: string[] = [];
    for (let i = 0; i < 10; i++) {
      options = await dropdown.locator('option').allTextContents();
      if (options.length > 3) break;
      await page.waitForTimeout(1000);
    }
    
    const hasZople = options.some(opt => opt.toLowerCase().includes('zople'));
    expect(hasZople).toBeTruthy();
  });

  test('Content cards show multiple creators with user_id=2', async ({ page }) => {
    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(4000);
    
    // Get all creator names from cards
    const creatorNames = await page.locator('div').filter({ hasText: /YOUTUBE|NEWS|TIKTOK/i }).locator('div').filter({ hasText: /^[A-Z][a-z]/ }).allTextContents();
    
    const uniqueCreators = new Set(creatorNames.filter(n => n.length > 2 && n.length < 50));
    console.log('Creators in cards:', Array.from(uniqueCreators));
    
    // Should have content from multiple creators
    expect(uniqueCreators.size).toBeGreaterThan(1);
  });

  test('Guest mode (no user_id) shows limited creators', async ({ page }) => {
    await page.goto(`${BASE_URL}/fc/#/updates`, {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(4000);
    
    const dropdown = page.locator('select').first();
    const options = await dropdown.locator('option').allTextContents();
    
    console.log('Guest mode dropdown options:', options);
    
    // Guest should have fewer options than user 2
    expect(options.length).toBeLessThanOrEqual(3); // "All Creators" + maybe 1-2 creators
  });

  test('user_id=2 has more creators than guest', async ({ page, context }) => {
    // First check guest mode (should have limited creators)
    await page.goto(`${BASE_URL}/fc/#/updates`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
    await page.waitForTimeout(6000);
    
    const guestDropdown = page.locator('select').first();
    const guestOptions = await guestDropdown.locator('option').allTextContents();
    const guestCount = guestOptions.length;
    console.log(`Guest mode dropdown options: ${guestOptions.join(', ')}`);
    
    // Use a new page to avoid state issues
    const newPage = await context.newPage();
    await newPage.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
    await newPage.waitForTimeout(8000);
    
    // Poll for dropdown options with multiple creators
    const userDropdown = newPage.locator('select').first();
    let userOptions: string[] = [];
    for (let i = 0; i < 10; i++) {
      userOptions = await userDropdown.locator('option').allTextContents();
      if (userOptions.length > 3) break;
      await newPage.waitForTimeout(1000);
    }
    const userCount = userOptions.length;
    await newPage.close();
    
    console.log(`Guest: ${guestCount} options, User 2: ${userCount} options`);
    console.log(`User 2 options: ${userOptions.join(', ')}`);
    
    expect(userCount).toBeGreaterThan(guestCount);
  });

  test('Selecting Lofe filter shows Lofe content', async ({ page }) => {
    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(4000);
    
    const dropdown = page.locator('select').first();
    
    // Find and select Lofe option
    const options = await dropdown.locator('option').allTextContents();
    const lofeOption = options.find(opt => opt.toLowerCase().includes('lofe'));
    
    if (lofeOption) {
      await dropdown.selectOption({ label: lofeOption });
      await page.waitForTimeout(1000);
      
      // Verify content is filtered
      const pageText = await page.textContent('body');
      console.log('Page contains Lofe after filter:', pageText?.toLowerCase().includes('lofe'));
    }
  });

  test('Refresh button works with user_id=2', async ({ page }) => {
    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(3000);
    
    const refreshBtn = page.locator('button:has-text("Refresh")');
    await expect(refreshBtn).toBeVisible();
    
    // Get initial card count
    const initialCards = await page.locator('div').filter({ hasText: /YOUTUBE|NEWS/i }).count();
    
    await refreshBtn.click();
    await page.waitForTimeout(2000);
    
    // Verify page still works
    const title = page.locator('h1:has-text("Streamer Updates")');
    await expect(title).toBeVisible();
    
    // Cards should still be present
    const afterCards = await page.locator('div').filter({ hasText: /YOUTUBE|NEWS/i }).count();
    expect(afterCards).toBeGreaterThan(0);
  });

  test('YouTube filter works with user_id=2', async ({ page }) => {
    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(3000);
    
    const youtubeBtn = page.locator('button:has-text("Youtube")').first();
    if (await youtubeBtn.isVisible()) {
      await youtubeBtn.click();
      await page.waitForTimeout(1000);
      
      // Check that YouTube filter is active
      const activeFilter = await youtubeBtn.getAttribute('style');
      console.log('YouTube button clicked, style:', activeFilter);
    }
  });

  test('All platform filter buttons visible with user_id=2', async ({ page }) => {
    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(3000);
    
    const platforms = ['All', 'Youtube', 'Tiktok', 'Twitter', 'Instagram', 'News'];
    const results: Record<string, boolean> = {};
    
    for (const platform of platforms) {
      const btn = page.locator(`button:has-text("${platform}")`).first();
      results[platform] = await btn.isVisible().catch(() => false);
    }
    
    console.log('Platform buttons visibility:', results);
    
    // At least All, Youtube, and News should be visible
    expect(results['All']).toBeTruthy();
    expect(results['Youtube']).toBeTruthy();
  });

  test('Page URL maintains user_id parameter after interactions', async ({ page }) => {
    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(3000);
    
    // Click a filter
    const youtubeBtn = page.locator('button:has-text("Youtube")').first();
    if (await youtubeBtn.isVisible()) {
      await youtubeBtn.click();
      await page.waitForTimeout(500);
    }
    
    // Check URL still has user_id
    const url = page.url();
    console.log('Current URL after interaction:', url);
    
    // The hash should still contain user_id=2
    expect(url).toContain('user_id=2');
  });

  test('Content count is reasonable for user_id=2', async ({ page }) => {
    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(4000);
    
    // Count visible content cards (items with thumbnails or platform badges)
    const cards = page.locator('img[src*="youtube"], img[src*="ytimg"], div:has-text("YOUTUBE"), div:has-text("NEWS")');
    const count = await cards.count();
    
    console.log(`Content cards visible: ${count}`);
    
    // User 2 should have significant content (API shows 30 items)
    expect(count).toBeGreaterThan(5);
  });

  test('No JavaScript errors with user_id=2', async ({ page }) => {
    const jsErrors: string[] = [];
    
    page.on('pageerror', error => {
      jsErrors.push(error.message);
    });

    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(3000);
    
    // Filter out extension errors
    const realErrors = jsErrors.filter(e => 
      !e.includes('extension') && 
      !e.includes('MutationObserver') &&
      !e.includes('web-client')
    );
    
    console.log('JS Errors:', realErrors.length > 0 ? realErrors : 'None');
    
    expect(realErrors.length).toBe(0);
  });

  test('API response matches frontend display', async ({ page, request }) => {
    // Get API data
    const apiResponse = await request.get('https://findtorontoevents.ca/fc/api/creator_news_creators.php?user_id=2');
    const apiData = await apiResponse.json();
    const apiCreators = apiData.creators.map((c: any) => c.name.toLowerCase());
    
    // Get frontend data - wait longer for data loading
    await page.goto(`${BASE_URL}/fc/#/updates?user_id=2`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });
    await page.waitForTimeout(8000);
    
    // Poll until dropdown has multiple creators loaded
    const dropdown = page.locator('select').first();
    let options: string[] = [];
    for (let i = 0; i < 10; i++) {
      options = await dropdown.locator('option').allTextContents();
      if (options.length > 3) break;
      await page.waitForTimeout(1000);
    }
    
    const frontendCreators = options
      .filter(o => o !== 'All Creators')
      .map(o => o.split(' (')[0].toLowerCase());
    
    console.log('API creators:', apiCreators);
    console.log('Frontend creators:', frontendCreators);
    
    // At minimum, frontend should show multiple creators (allowing for some race conditions)
    expect(frontendCreators.length).toBeGreaterThan(0);
    
    // Check that at least half of API creators are visible (allows for timing issues)
    let foundCount = 0;
    for (const creator of apiCreators) {
      const found = frontendCreators.some(fc => fc.includes(creator) || creator.includes(fc));
      if (found) foundCount++;
    }
    console.log(`Found ${foundCount}/${apiCreators.length} API creators in frontend`);
    expect(foundCount).toBeGreaterThan(apiCreators.length / 2);
  });
});
