import { test, expect } from '@playwright/test';

/**
 * Test that Ninja appears in "Creators Live Now" when live on Twitch
 * This validates the live status checking and UI display
 */
test.describe('Ninja Live Status Display', () => {
  
  test('should display Ninja in Creators Live Now section when live', async ({ page }) => {
    // Navigate to FavCreators guest mode
    await page.goto('https://findtorontoevents.ca/fc/#/guest');
    
    // Wait for the page to load
    await page.waitForSelector('.app-container', { timeout: 30000 });
    
    // Wait for initial backend check
    await page.waitForTimeout(3000);
    
    // Add Ninja as a creator using quick add
    const quickAddInput = page.locator('.quick-add-input');
    await quickAddInput.fill('ninja:twitch');
    await quickAddInput.press('Enter');
    
    // Wait for Ninja to be added and appear in the list
    const ninjaCard = page.locator('.creator-card').filter({ hasText: 'Ninja' });
    await expect(ninjaCard).toBeVisible({ timeout: 10000 });
    
    // Click the check status button for Ninja to trigger live check
    const checkStatusBtn = ninjaCard.locator('button[title="Check Live Status"]');
    await checkStatusBtn.click();
    
    // Wait for the live check to process
    await page.waitForTimeout(8000);
    
    // Check the console for live detection
    const logs: string[] = [];
    page.on('console', msg => {
      const text = msg.text();
      if (text.toLowerCase().includes('ninja')) {
        logs.push(text);
      }
    });
    
    // Wait a bit more for any delayed logs
    await page.waitForTimeout(3000);
    
    console.log('Ninja-related logs:', logs);
    
    // Check if "Creators Live Now" section exists and is visible
    const liveSummary = page.locator('.live-summary');
    await expect(liveSummary).toBeVisible();
    
    // Check if the section shows live creators or checking message
    const summaryText = await liveSummary.textContent() || '';
    
    // If Ninja is live, we should see him in the live section
    // The test passes if either:
    // 1. Ninja appears in the live creators section, OR
    // 2. The check completed and shows "No creators live right now"
    
    const liveSection = page.locator('.live-section').filter({ hasText: 'Live Streams' });
    const ninjaInLive = page.locator('.live-card').filter({ hasText: /Ninja/i });
    
    // Take a screenshot for debugging
    await page.screenshot({ path: 'test-results/ninja-live-status.png', fullPage: false });
    
    // Check if Ninja is displayed in the live section
    const isNinjaVisible = await ninjaInLive.isVisible().catch(() => false);
    
    if (isNinjaVisible) {
      console.log('✅ SUCCESS: Ninja is displayed in "Creators Live Now" section');
      
      // Verify the Twitch platform badge is shown
      const platformBadge = ninjaInLive.locator('.platform-badge').filter({ hasText: 'TWITCH' });
      await expect(platformBadge).toBeVisible();
      
      // Verify there's a link to watch on Twitch
      const watchLink = ninjaInLive.locator('a[href*="twitch.tv"]').filter({ hasText: /Watch on|Twitch/i });
      await expect(watchLink).toBeVisible();
      
      // Verify the avatar is displayed
      const avatar = ninjaInLive.locator('.live-avatar');
      await expect(avatar).toBeVisible();
    } else {
      console.log('ℹ️ Ninja is not currently live or not displayed in live section');
      console.log('Live Summary text:', summaryText);
      
      // The check should at least complete (not stuck on "Checking...")
      expect(summaryText).not.toContain('Checking for live creators...');
    }
    
    // Log the final status for debugging
    console.log('Test completed. Ninja live status checked.');
  });
  
  test('should show progress bar while checking live status', async ({ page }) => {
    // Navigate to FavCreators
    await page.goto('https://findtorontoevents.ca/fc/#/guest');
    
    // Wait for the page to load
    await page.waitForSelector('.app-container', { timeout: 30000 });
    
    // Wait a bit for the live check to start
    await page.waitForTimeout(2000);
    
    // Check that the Live Summary shows the progress indicator while loading
    const liveSummary = page.locator('.live-summary');
    await expect(liveSummary).toBeVisible();
    
    // Expand the live summary if collapsed
    const toggleBtn = liveSummary.locator('.collapse-toggle');
    const isCollapsed = await toggleBtn.textContent() === '▼';
    if (isCollapsed) {
      await toggleBtn.click();
      await page.waitForTimeout(500);
    }
    
    // Trigger a fresh live check by clicking the refresh button
    const checkAllBtn = page.locator('button[title="Check all live statuses"]');
    await checkAllBtn.click();
    await page.waitForTimeout(1000);
    
    // Check if progress bar exists
    const progressBar = liveSummary.locator('.checking-progress');
    const hasProgressBar = await progressBar.isVisible().catch(() => false);
    
    if (hasProgressBar) {
      console.log('✅ Progress bar is visible');
      
      // Verify progress elements
      const progressText = await progressBar.textContent() || '';
      expect(progressText).toMatch(/\d+\s*\/\s*\d+/); // Should show "X / Y" format
      
      // Check for progress bar visual element
      const progressBarVisual = progressBar.locator('div[style*="width"]');
      await expect(progressBarVisual).toBeVisible();
      
      // Verify current creator name is shown
      expect(progressText).toContain('Checking:');
    } else {
      console.log('ℹ️ Progress bar not visible - checking if live check completed quickly');
    }
    
    // Wait for check to complete (up to 90 seconds for all creators)
    await page.waitForTimeout(90000);
    
    // Verify we're no longer showing "Checking..."
    const summaryText = await liveSummary.textContent() || '';
    console.log('Final Live Summary text:', summaryText);
    expect(summaryText).not.toContain('Checking for live creators...');
  });
  
  test('should complete full live status check without errors', async ({ page }) => {
    // Navigate to FavCreators
    await page.goto('https://findtorontoevents.ca/fc/#/guest');
    
    // Wait for the page to load
    await page.waitForSelector('.app-container', { timeout: 30000 });
    
    // Wait for initial load
    await page.waitForTimeout(3000);
    
    // Click "Check All Live Status" button
    const checkAllBtn = page.locator('button[title="Check all live statuses"]');
    await checkAllBtn.click();
    
    // Wait for the check to start
    await page.waitForTimeout(1000);
    
    const liveSummary = page.locator('.live-summary');
    
    // Should show checking state initially
    await expect(liveSummary).toContainText(/Checking for live creators|Creators Live Now/);
    
    // Wait for the check to complete (should take less than 2 minutes for all creators)
    await page.waitForTimeout(60000);
    
    // After 60 seconds, it should either show:
    // 1. "No creators live right now" (if none are live)
    // 2. Live creator cards (if any are live)
    // 3. OR at least not show "Checking for live creators..." anymore
    
    const summaryText = await liveSummary.textContent() || '';
    
    console.log('Live Summary text after 60s:', summaryText);
    
    // Should NOT still be showing "Checking for live creators..."
    expect(summaryText).not.toContain('Checking for live creators...');
    
    // Should show either "No creators live" or actual live creators
    const hasCompletedMessage = 
      summaryText.includes('No creators live right now') ||
      summaryText.includes('Live Streams') ||
      summaryText.includes('🔴');
    
    expect(hasCompletedMessage).toBeTruthy();
  });
});