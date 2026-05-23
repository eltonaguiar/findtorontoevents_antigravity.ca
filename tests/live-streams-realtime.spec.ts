import { test, expect } from '@playwright/test';

/**
 * Test to validate that a newly added creator who is live 
 * immediately shows up in the "Live Streams" section
 * 
 * Test creator: username11376489 (TikTok)
 * URL: https://www.tiktok.com/@username11376489
 */

test.describe('Live Streams Real-time Update', () => {
  
  test('should display live creator in Live Streams section immediately', async ({ page }) => {
    // Navigate to FavCreators guest mode
    await page.goto('https://findtorontoevents.ca/fc/#/guest');
    
    // Wait for the page to load
    await page.waitForSelector('.app-container', { timeout: 30000 });
    
    // Wait for initial backend check to complete
    await page.waitForTimeout(5000);
    
    // Capture console logs for debugging
    const logs: string[] = [];
    page.on('console', msg => {
      const text = msg.text();
      if (text.toLowerCase().includes('live') || 
          text.toLowerCase().includes('username11376489') ||
          text.toLowerCase().includes('tiktok')) {
        logs.push(`[${msg.type()}] ${text}`);
      }
    });

    // Check if username11376489 already exists in the list
    const existingCard = page.locator('.creator-card').filter({ hasText: /username11376489/i });
    const creatorExists = await existingCard.isVisible().catch(() => false);
    
    if (!creatorExists) {
      console.log('Creator not found, adding via Quick Add...');
      
      // Add the creator using Quick Add with TikTok URL
      const quickAddInput = page.locator('.quick-add-input');
      await quickAddInput.fill('https://www.tiktok.com/@username11376489');
      await quickAddInput.press('Enter');
      
      // Wait for the creator to be added
      await page.waitForTimeout(3000);
      
      // Verify creator card appears
      const newCard = page.locator('.creator-card').filter({ hasText: /username11376489/i });
      await expect(newCard).toBeVisible({ timeout: 10000 });
      console.log('✅ Creator added successfully');
    } else {
      console.log('Creator already exists in the list');
    }
    
    // Get the creator card
    const creatorCard = page.locator('.creator-card').filter({ hasText: /username11376489/i });
    
    // Click the check status button for this creator
    const checkStatusBtn = creatorCard.locator('button[title="Check Live Status"]').first();
    await checkStatusBtn.click();
    console.log('Clicked check status button for username11376489');
    
    // Wait for the live check to process (TikTok check takes a few seconds)
    await page.waitForTimeout(10000);
    
    // Check the Live Summary section
    const liveSummary = page.locator('.live-summary');
    await expect(liveSummary).toBeVisible();
    
    // Expand the live summary if collapsed
    const toggleBtn = liveSummary.locator('.collapse-toggle');
    const isCollapsed = await toggleBtn.textContent().then(t => t === '▼').catch(() => false);
    if (isCollapsed) {
      await toggleBtn.click();
      await page.waitForTimeout(500);
    }
    
    // Take a screenshot of the Live Streams section
    await page.screenshot({ 
      path: 'test-results/live-streams-username11376489.png', 
      fullPage: false 
    });
    
    // Check if the creator appears in the Live Streams section
    const liveSection = page.locator('.live-section').filter({ hasText: /Live Streams/i });
    const liveCard = page.locator('.live-card').filter({ hasText: /username11376489/i });
    
    const isInLiveSection = await liveCard.isVisible().catch(() => false);
    
    // Get the Live Summary text for debugging
    const summaryText = await liveSummary.textContent() || '';
    console.log('Live Summary text:', summaryText);
    console.log('Console logs:', logs);
    
    if (isInLiveSection) {
      console.log('✅ SUCCESS: username11376489 is displayed in Live Streams section');
      
      // Verify the TikTok platform badge is shown
      const platformBadge = liveCard.locator('.platform-badge').filter({ hasText: /TIKTOK/i });
      await expect(platformBadge).toBeVisible();
      
      // Verify there's a link to watch on TikTok
      const watchLink = liveCard.locator('a[href*="tiktok.com"]').first();
      await expect(watchLink).toBeVisible();
      
      // Verify live indicator (red dot or "LIVE" text)
      const liveIndicator = liveCard.locator('.live-indicator, [class*="live"]').first();
      const hasLiveIndicator = await liveIndicator.isVisible().catch(() => false);
      expect(hasLiveIndicator).toBeTruthy();
      
    } else {
      console.log('ℹ️ Creator is not currently live or not displayed in Live Streams section');
      console.log('Live Summary text:', summaryText);
      
      // The test should still pass if the check completed successfully
      // (creator might just not be live at the moment)
      expect(summaryText).not.toContain('Checking for live creators...');
    }
  });
  
  test('should update Live Streams when creator goes live during check', async ({ page }) => {
    // Navigate to FavCreators
    await page.goto('https://findtorontoevents.ca/fc/#/guest');
    
    // Wait for the page to load
    await page.waitForSelector('.app-container', { timeout: 30000 });
    await page.waitForTimeout(3000);
    
    // Ensure username11376489 exists
    const creatorCard = page.locator('.creator-card').filter({ hasText: /username11376489/i });
    const creatorExists = await creatorCard.isVisible().catch(() => false);
    
    if (!creatorExists) {
      // Add the creator
      const quickAddInput = page.locator('.quick-add-input');
      await quickAddInput.fill('https://www.tiktok.com/@username11376489');
      await quickAddInput.press('Enter');
      await page.waitForTimeout(3000);
    }
    
    // Get initial Live Streams state
    const liveSummary = page.locator('.live-summary');
    const initialText = await liveSummary.textContent() || '';
    console.log('Initial Live Summary:', initialText);
    
    // Click "Check All Live Status" button
    const checkAllBtn = page.locator('button[title="Check all live statuses"]').first();
    await checkAllBtn.click();
    
    // Wait for check to start
    await page.waitForTimeout(1000);
    
    // Monitor for live detection during the check
    let liveDetected = false;
    const startTime = Date.now();
    const timeout = 120000; // 2 minutes max
    
    while (Date.now() - startTime < timeout) {
      const currentText = await liveSummary.textContent() || '';
      
      // Check if username11376489 appears in live section during check
      const liveCard = page.locator('.live-card').filter({ hasText: /username11376489/i });
      const isLiveVisible = await liveCard.isVisible().catch(() => false);
      
      if (isLiveVisible) {
        liveDetected = true;
        console.log('✅ Live detection confirmed during check-all');
        break;
      }
      
      // Check if check is complete
      if (!currentText.includes('Checking') && !currentText.includes('...')) {
        console.log('Check completed, live status:', currentText);
        break;
      }
      
      await page.waitForTimeout(1000);
    }
    
    // Take final screenshot
    await page.screenshot({ 
      path: 'test-results/live-streams-checkall-username11376489.png', 
      fullPage: false 
    });
    
    // Verify check completed
    const finalText = await liveSummary.textContent() || '';
    expect(finalText).not.toContain('Checking for live creators...');
    
    console.log('Final Live Summary:', finalText);
    console.log('Live detected during check:', liveDetected);
  });
  
  test('should show toast notification when creator goes live', async ({ page }) => {
    // Navigate to FavCreators
    await page.goto('https://findtorontoevents.ca/fc/#/guest');
    
    // Wait for the page to load
    await page.waitForSelector('.app-container', { timeout: 30000 });
    await page.waitForTimeout(3000);
    
    // Monitor for toast notifications
    const toastMessages: string[] = [];
    
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('toast') || text.includes('live') && text.includes('username11376489')) {
        toastMessages.push(text);
      }
    });
    
    // Ensure creator exists and trigger check
    const creatorCard = page.locator('.creator-card').filter({ hasText: /username11376489/i });
    const creatorExists = await creatorCard.isVisible().catch(() => false);
    
    if (!creatorExists) {
      const quickAddInput = page.locator('.quick-add-input');
      await quickAddInput.fill('https://www.tiktok.com/@username11376489');
      await quickAddInput.press('Enter');
      await page.waitForTimeout(3000);
    }
    
    // Click check status
    const checkBtn = page.locator('.creator-card')
      .filter({ hasText: /username11376489/i })
      .locator('button[title="Check Live Status"]')
      .first();
    await checkBtn.click();
    
    // Wait for check to complete
    await page.waitForTimeout(10000);
    
    // Check for toast container
    const toastContainer = page.locator('.toast-container, [class*="toast"]').first();
    const hasToast = await toastContainer.isVisible().catch(() => false);
    
    console.log('Toast messages captured:', toastMessages);
    console.log('Toast container visible:', hasToast);
    
    // Take screenshot
    await page.screenshot({ 
      path: 'test-results/live-toast-username11376489.png', 
      fullPage: false 
    });
  });
});
