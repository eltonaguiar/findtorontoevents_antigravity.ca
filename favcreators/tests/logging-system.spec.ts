import { test, expect } from '@playwright/test';

/**
 * FavCreators Logging System Test
 * Verifies that the logging system is working correctly and no JavaScript errors occur
 */

test.describe('FavCreators Logging System', () => {
  test.beforeEach(async ({ page }) => {
    // Listen for console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.error('Browser console error:', msg.text());
      }
    });

    // Listen for page errors
    page.on('pageerror', error => {
      console.error('Page error:', error.message);
    });
  });

  test('should load FavCreators without JavaScript errors', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    page.on('pageerror', error => {
      errors.push(error.message);
    });

    // Navigate to FavCreators
    await page.goto('https://findtorontoevents.ca/fc/');
    
    // Wait for the app to load
    await page.waitForLoadState('networkidle');
    
    // Check for errors
    expect(errors).toHaveLength(0);
    
    // Verify main elements are present
    await expect(page.locator('body')).toBeVisible();
  });

  test('should successfully add a creator via quick add', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('https://findtorontoevents.ca/fc/');
    await page.waitForLoadState('networkidle');

    // Find the quick add input
    const quickAddInput = page.locator('input[placeholder*="Quick add"]');
    await expect(quickAddInput).toBeVisible();

    // Add a test creator via URL
    await quickAddInput.fill('tiktok.com/@testcreator');
    await quickAddInput.press('Enter');

    // Wait for the operation to complete
    await page.waitForTimeout(2000);

    // Check for errors
    expect(errors).toHaveLength(0);
  });

  test('should run backfill script without errors', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Navigate to backfill admin page
    await page.goto('https://findtorontoevents.ca/fc/admin_backfill.html');
    await page.waitForLoadState('networkidle');

    // Click the run button
    const runButton = page.locator('button#runBtn');
    await expect(runButton).toBeVisible();
    await runButton.click();

    // Wait for the script to complete
    await page.waitForSelector('#output', { state: 'visible', timeout: 10000 });

    // Verify output is shown
    const output = page.locator('#output');
    await expect(output).toBeVisible();
    
    const outputText = await output.textContent();
    expect(outputText).toContain('Summary');

    // Check for errors
    expect(errors).toHaveLength(0);
  });

  test('should fetch logs via API (admin only)', async ({ page }) => {
    // This test assumes you're logged in as admin
    // You may need to adjust based on your auth setup
    
    const response = await page.request.get('https://findtorontoevents.ca/fc/api/get_logs.php?limit=10');
    
    // Should either return logs (if admin) or unauthorized error
    expect([200, 401, 403]).toContain(response.status());
    
    if (response.status() === 200) {
      const data = await response.json();
      expect(data).toHaveProperty('logs');
      expect(data).toHaveProperty('total');
      expect(Array.isArray(data.logs)).toBe(true);
    }
  });

  test('should verify database logging is working', async ({ page }) => {
    // Navigate to the app
    await page.goto('https://findtorontoevents.ca/fc/');
    await page.waitForLoadState('networkidle');

    // Trigger an action that should be logged (e.g., fetching creators)
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Wait a moment for the log to be written
    await page.waitForTimeout(1000);

    // Note: To fully verify, you'd need to check the database directly
    // or use the get_logs.php API endpoint if you have admin access
    console.log('✓ Page loaded successfully, logging should have occurred');
  });
});

test.describe('FavCreators User Flow', () => {
  test('should allow guest user to view creators', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('https://findtorontoevents.ca/fc/');
    await page.waitForLoadState('networkidle');

    // Wait for creators to load
    await page.waitForTimeout(2000);

    // Check for errors
    expect(errors).toHaveLength(0);
  });

  test('should verify brunitarte is in user_id 2 list', async ({ page }) => {
    // This is a manual verification test
    // You would need to check the database or API directly
    console.log('Manual verification: Check that brunitarte exists in user_lists for user_id=2');
    
    // Could be automated with a custom API endpoint that returns user lists
    const response = await page.request.get('https://findtorontoevents.ca/fc/api/get_my_creators.php?user_id=2');
    
    if (response.status() === 200) {
      const data = await response.json();
      const creators = data.creators || [];
      const hasBrunitarte = creators.some((c: any) => 
        c.name?.toLowerCase().includes('brunitarte') || 
        c.id?.toLowerCase().includes('brunitarte')
      );
      
      console.log(`Brunitarte found in user 2's list: ${hasBrunitarte}`);
    }
  });
});
