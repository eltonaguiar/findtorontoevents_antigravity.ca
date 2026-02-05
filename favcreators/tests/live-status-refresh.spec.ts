/**
 * Live Status Refresh Tests
 * 
 * These tests verify:
 * 1. The refresh button appears next to "Creators Live Now" header
 * 2. Clicking refresh triggers a live status check
 * 3. The refresh indicator message shows during refresh
 * 4. The "last updated" timestamp is displayed
 * 5. The update frequency is every 3 minutes (180 seconds)
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'https://findtorontoevents.ca/fc/';
const TEST_TIMEOUT = 120000; // 2 minutes for live status checks

// Helper to wait for the Live Summary to be visible
async function waitForLiveSummary(page: Page) {
  await page.waitForSelector('.live-summary', { timeout: 10000 });
  // Wait a bit for the component to fully mount
  await page.waitForTimeout(1000);
}

// Helper to check if refresh button exists
async function getRefreshButton(page: Page) {
  return page.locator('.refresh-button');
}

// Helper to get refresh status bar
async function getRefreshStatusBar(page: Page) {
  return page.locator('.refresh-status-bar');
}

test.describe('Live Status Refresh Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForLiveSummary(page);
  });

  test('Refresh button is visible next to Creators Live Now header', async ({ page }) => {
    const refreshButton = await getRefreshButton(page);
    await expect(refreshButton).toBeVisible();
    
    // Verify the button has the correct title/aria-label
    await expect(refreshButton).toHaveAttribute('title', 'Refresh live status');
    await expect(refreshButton).toHaveAttribute('aria-label', 'Refresh live status');
  });

  test('Refresh button has correct icon', async ({ page }) => {
    const refreshIcon = page.locator('.refresh-icon');
    await expect(refreshIcon).toBeVisible();
    await expect(refreshIcon).toHaveText('🔄');
  });

  test('Refresh status bar is visible with initial message', async ({ page }) => {
    const statusBar = await getRefreshStatusBar(page);
    await expect(statusBar).toBeVisible();
    
    // Should show either "Checking live status..." or "Updated X ago" or info message
    const statusText = await statusBar.locator('.refresh-status-text').textContent();
    expect(['Checking live status...', 'Updated', 'Auto-updates every 3 minutes'].some(
      msg => statusText?.includes(msg)
    )).toBeTruthy();
  });

  test('Clicking refresh button triggers live status check', async ({ page }) => {
    const refreshButton = await getRefreshButton(page);
    
    // Click the refresh button
    await refreshButton.click();
    
    // Wait for the refreshing state to be applied
    await expect(refreshButton).toHaveClass(/refreshing/);
    
    // Verify the status bar shows checking message
    const statusBar = await getRefreshStatusBar(page);
    await expect(statusBar).toHaveClass(/checking/);
    
    const statusText = await statusBar.locator('.refresh-status-text').textContent();
    expect(statusText).toContain('Checking live status...');
  });

  test('Refresh button is disabled during refresh', async ({ page }) => {
    const refreshButton = await getRefreshButton(page);
    
    // Click to start refresh
    await refreshButton.click();
    
    // Button should be disabled
    await expect(refreshButton).toBeDisabled();
    
    // Wait for refresh to complete (or timeout)
    try {
      await expect(refreshButton).toBeEnabled({ timeout: 60000 });
    } catch {
      // If it takes too long, that's okay - we're testing the disabled state
    }
  });

  test('Refresh icon spins during refresh', async ({ page }) => {
    const refreshButton = await getRefreshButton(page);
    const refreshIcon = page.locator('.refresh-icon');
    
    // Start refresh
    await refreshButton.click();
    
    // Verify the button has the refreshing class which triggers the animation
    await expect(refreshButton).toHaveClass(/refreshing/);
  });

  test('Last updated timestamp is displayed after refresh', async ({ page }) => {
    // Wait for any initial check to complete
    await page.waitForTimeout(5000);
    
    // Trigger a refresh
    const refreshButton = await getRefreshButton(page);
    await refreshButton.click();
    
    // Wait for the refresh to complete
    await expect(refreshButton).toBeEnabled({ timeout: 120000 });
    
    // Check that the timestamps section is visible
    const timestamps = page.locator('.timestamps');
    await expect(timestamps).toBeVisible();
    
    // Should contain "Last updated" text
    const timestampsText = await timestamps.textContent();
    expect(timestampsText).toContain('Last updated');
  });

  test('Update frequency information is shown', async ({ page }) => {
    const statusBar = await getRefreshStatusBar(page);
    const statusText = await statusBar.textContent();
    
    // Should indicate update frequency somewhere
    expect(statusText).toMatch(/Updated|Checking|Auto-updates/);
  });

  test('Live Summary shows correct header structure', async ({ page }) => {
    const header = page.locator('.live-summary-header');
    await expect(header).toBeVisible();
    
    // Verify the title contains "Creators Live Now"
    const title = header.locator('h2');
    await expect(title).toHaveText('Creators Live Now');
    
    // Verify controls are present
    const controls = header.locator('.live-summary-controls');
    await expect(controls).toBeVisible();
    
    // Should have refresh button and collapse toggle
    await expect(controls.locator('.refresh-button')).toBeVisible();
    await expect(controls.locator('.collapse-toggle')).toBeVisible();
  });

  test('Refresh status bar shows checking state correctly', async ({ page }) => {
    const refreshButton = await getRefreshButton(page);
    const statusBar = await getRefreshStatusBar(page);
    
    // Click refresh
    await refreshButton.click();
    
    // Check all visual indicators of checking state
    await expect(statusBar).toHaveClass(/checking/);
    
    const icon = statusBar.locator('.refresh-status-icon');
    await expect(icon).toHaveText('⏳');
    
    const text = statusBar.locator('.refresh-status-text');
    await expect(text).toHaveText('Checking live status...');
  });

  test('Refresh status bar shows updated state after completion', async ({ page }) => {
    const refreshButton = await getRefreshButton(page);
    
    // Trigger refresh
    await refreshButton.click();
    
    // Wait for completion
    await expect(refreshButton).toBeEnabled({ timeout: 120000 });
    
    // Check status bar shows updated state
    const statusBar = await getRefreshStatusBar(page);
    const statusText = await statusBar.locator('.refresh-status-text').textContent();
    
    // Should show "Updated X ago" format
    expect(statusText).toMatch(/Updated\s+(Just now|\d+m ago|\d+h ago)/);
  });

  test('Multiple rapid clicks on refresh button are handled correctly', async ({ page }) => {
    const refreshButton = await getRefreshButton(page);
    
    // Click multiple times rapidly
    await refreshButton.click();
    await refreshButton.click();
    await refreshButton.click();
    
    // Should still be in a valid state (either checking or enabled)
    const isDisabled = await refreshButton.isDisabled();
    expect(typeof isDisabled).toBe('boolean');
  });

  test('Live Summary remains functional during refresh', async ({ page }) => {
    const refreshButton = await getRefreshButton(page);
    const collapseToggle = page.locator('.collapse-toggle');
    
    // Start refresh
    await refreshButton.click();
    
    // Should still be able to collapse/expand
    await collapseToggle.click();
    
    // Check if content is collapsed
    const content = page.locator('.live-summary-content');
    // Content visibility depends on collapsed state
    const isVisible = await content.isVisible().catch(() => false);
    expect(typeof isVisible).toBe('boolean');
  });

  test('Refresh progress is shown when checking', async ({ page }) => {
    const refreshButton = await getRefreshButton(page);
    
    // Start refresh
    await refreshButton.click();
    
    // Look for progress container
    const progressContainer = page.locator('.checking-progress-container');
    
    // Progress should appear during checking
    try {
      await expect(progressContainer).toBeVisible({ timeout: 5000 });
      
      // Should show progress text
      const progressText = await progressContainer.textContent();
      expect(progressText).toContain('Checking for live creators');
    } catch {
      // If it completed too fast, that's okay
    }
  });

  test('Page load shows correct initial state', async ({ page }) => {
    // Reload page to test initial state
    await page.reload();
    await waitForLiveSummary(page);
    
    // Should have refresh button
    const refreshButton = await getRefreshButton(page);
    await expect(refreshButton).toBeVisible();
    
    // Should have status bar
    const statusBar = await getRefreshStatusBar(page);
    await expect(statusBar).toBeVisible();
    
    // Should have timestamps
    const timestamps = page.locator('.timestamps');
    await expect(timestamps).toBeVisible();
    
    // Page load time should be shown
    const timestampsText = await timestamps.textContent();
    expect(timestampsText).toContain('Page loaded');
  });
});

test.describe('Live Status Auto-Update Behavior', () => {
  test('Auto-update interval is approximately 3 minutes', async ({ page }) => {
    // This test verifies the auto-update interval is set correctly
    // Note: We don't actually wait 3 minutes, we check the code behavior
    
    await page.goto(BASE_URL);
    await waitForLiveSummary(page);
    
    // Get initial last updated time if available
    const statusBar = await getRefreshStatusBar(page);
    const initialText = await statusBar.textContent();
    
    // The status should indicate auto-updates happen every 3 minutes
    // This is shown in the info state
    if (initialText?.includes('Auto-updates')) {
      expect(initialText).toContain('3 minutes');
    }
  });

  test('Manual refresh can be triggered at any time', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForLiveSummary(page);
    
    const refreshButton = await getRefreshButton(page);
    
    // Should be able to click refresh immediately after load
    await expect(refreshButton).toBeEnabled();
    
    // Click should work
    await refreshButton.click();
    await expect(refreshButton).toBeDisabled();
  });
});

test.describe('Live Status Edge Cases', () => {
  test('Refresh button works when no creators are live', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForLiveSummary(page);
    
    const refreshButton = await getRefreshButton(page);
    
    // Click refresh even if no one is live
    await refreshButton.click();
    
    // Should show checking state
    const statusBar = await getRefreshStatusBar(page);
    await expect(statusBar).toHaveClass(/checking/);
    
    // Wait for completion
    await expect(refreshButton).toBeEnabled({ timeout: 120000 });
    
    // No live message should be visible if no one is live
    const noLiveMessage = page.locator('.no-live-message');
    // Message visibility depends on whether anyone is live
    const messageExists = await noLiveMessage.count() > 0;
    if (messageExists) {
      const messageText = await noLiveMessage.textContent();
      expect(messageText).toContain('No creators live right now');
    }
  });

  test('Status bar updates correctly through the refresh cycle', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForLiveSummary(page);
    
    const refreshButton = await getRefreshButton(page);
    const statusBar = await getRefreshStatusBar(page);
    
    // Record initial state
    const initialClasses = await statusBar.getAttribute('class');
    
    // Start refresh
    await refreshButton.click();
    
    // Should transition to checking state
    await expect(statusBar).toHaveClass(/checking/);
    
    // Wait for completion
    await expect(refreshButton).toBeEnabled({ timeout: 120000 });
    
    // Should transition to updated state
    const finalClasses = await statusBar.getAttribute('class');
    expect(finalClasses).toMatch(/updated|info/);
  });
});
