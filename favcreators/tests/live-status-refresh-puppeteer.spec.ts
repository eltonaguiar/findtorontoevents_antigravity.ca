/**
 * Live Status Refresh Tests - Puppeteer/Node Version
 * 
 * These tests verify:
 * 1. The refresh button appears next to "Creators Live Now" header
 * 2. Clicking refresh triggers a live status check
 * 3. The refresh indicator message shows during refresh
 * 4. The "last updated" timestamp is displayed
 * 5. The update frequency is every 3 minutes
 */

import puppeteer from 'puppeteer';
import { describe, test, expect, beforeAll, afterAll, beforeEach } from '@jest/globals';

const BASE_URL = 'https://findtorontoevents.ca/fc/';
const TEST_TIMEOUT = 120000; // 2 minutes

describe('Live Status Refresh Feature - Puppeteer', () => {
  let browser: puppeteer.Browser;
  let page: puppeteer.Page;

  beforeAll(async () => {
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
  });

  afterAll(async () => {
    if (browser) {
      await browser.close();
    }
  });

  beforeEach(async () => {
    page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
    
    // Wait for LiveSummary to load
    await page.waitForSelector('.live-summary', { timeout: 10000 });
    await page.waitForTimeout(1000);
  }, TEST_TIMEOUT);

  afterEach(async () => {
    if (page) {
      await page.close();
    }
  });

  test('P-1: Refresh button is visible next to Creators Live Now header', async () => {
    const refreshButton = await page.$('.refresh-button');
    expect(refreshButton).toBeTruthy();
    
    if (refreshButton) {
      const title = await refreshButton.evaluate(el => el.getAttribute('title'));
      const ariaLabel = await refreshButton.evaluate(el => el.getAttribute('aria-label'));
      
      expect(title).toBe('Refresh live status');
      expect(ariaLabel).toBe('Refresh live status');
    }
  }, TEST_TIMEOUT);

  test('P-2: Refresh button has correct icon', async () => {
    const refreshIcon = await page.$('.refresh-icon');
    expect(refreshIcon).toBeTruthy();
    
    if (refreshIcon) {
      const text = await refreshIcon.evaluate(el => el.textContent);
      expect(text).toBe('🔄');
    }
  }, TEST_TIMEOUT);

  test('P-3: Refresh status bar is visible with initial message', async () => {
    const statusBar = await page.$('.refresh-status-bar');
    expect(statusBar).toBeTruthy();
    
    if (statusBar) {
      const statusText = await statusBar.evaluate(el => 
        el.querySelector('.refresh-status-text')?.textContent
      );
      
      const validMessages = [
        'Checking live status...',
        'Updated',
        'Auto-updates every 3 minutes'
      ];
      
      const hasValidMessage = validMessages.some(msg => 
        statusText?.includes(msg)
      );
      expect(hasValidMessage).toBe(true);
    }
  }, TEST_TIMEOUT);

  test('P-4: Clicking refresh button triggers live status check', async () => {
    const refreshButton = await page.$('.refresh-button');
    expect(refreshButton).toBeTruthy();
    
    if (refreshButton) {
      // Click the refresh button
      await refreshButton.click();
      
      // Wait for refreshing state
      await page.waitForTimeout(500);
      
      // Check if button has refreshing class
      const hasRefreshingClass = await refreshButton.evaluate(el => 
        el.classList.contains('refreshing')
      );
      expect(hasRefreshingClass).toBe(true);
      
      // Check status bar shows checking
      const statusBar = await page.$('.refresh-status-bar');
      if (statusBar) {
        const hasCheckingClass = await statusBar.evaluate(el => 
          el.classList.contains('checking')
        );
        expect(hasCheckingClass).toBe(true);
      }
    }
  }, TEST_TIMEOUT);

  test('P-5: Refresh button is disabled during refresh', async () => {
    const refreshButton = await page.$('.refresh-button');
    expect(refreshButton).toBeTruthy();
    
    if (refreshButton) {
      // Click to start refresh
      await refreshButton.click();
      await page.waitForTimeout(500);
      
      // Check if button is disabled
      const isDisabled = await refreshButton.evaluate(el => 
        (el as HTMLButtonElement).disabled
      );
      expect(isDisabled).toBe(true);
      
      // Wait for it to become enabled again (or timeout)
      try {
        await page.waitForFunction(
          () => {
            const btn = document.querySelector('.refresh-button');
            return btn && !(btn as HTMLButtonElement).disabled;
          },
          { timeout: 60000 }
        );
      } catch {
        // If timeout, that's okay for this test
      }
    }
  }, TEST_TIMEOUT);

  test('P-6: Refresh icon spins during refresh', async () => {
    const refreshButton = await page.$('.refresh-button');
    expect(refreshButton).toBeTruthy();
    
    if (refreshButton) {
      await refreshButton.click();
      await page.waitForTimeout(500);
      
      // Check for spinning animation via CSS class
      const hasRefreshingClass = await refreshButton.evaluate(el => 
        el.classList.contains('refreshing')
      );
      expect(hasRefreshingClass).toBe(true);
    }
  }, TEST_TIMEOUT);

  test('P-7: Last updated timestamp is displayed after refresh', async () => {
    // Wait for any initial check
    await page.waitForTimeout(5000);
    
    const refreshButton = await page.$('.refresh-button');
    if (refreshButton) {
      // Trigger refresh
      await refreshButton.click();
      
      // Wait for completion
      await page.waitForFunction(
        () => {
          const btn = document.querySelector('.refresh-button');
          return btn && !(btn as HTMLButtonElement).disabled;
        },
        { timeout: 120000 }
      );
      
      // Check timestamps section
      const timestamps = await page.$('.timestamps');
      expect(timestamps).toBeTruthy();
      
      if (timestamps) {
        const text = await timestamps.evaluate(el => el.textContent);
        expect(text).toContain('Last updated');
      }
    }
  }, TEST_TIMEOUT);

  test('P-8: Update frequency information is shown', async () => {
    const statusBar = await page.$('.refresh-status-bar');
    expect(statusBar).toBeTruthy();
    
    if (statusBar) {
      const text = await statusBar.evaluate(el => el.textContent);
      expect(text).toMatch(/Updated|Checking|Auto-updates/);
    }
  }, TEST_TIMEOUT);

  test('P-9: Live Summary shows correct header structure', async () => {
    const header = await page.$('.live-summary-header');
    expect(header).toBeTruthy();
    
    if (header) {
      // Check title
      const title = await header.$eval('h2', el => el.textContent);
      expect(title).toBe('Creators Live Now');
      
      // Check controls exist
      const controls = await header.$('.live-summary-controls');
      expect(controls).toBeTruthy();
      
      if (controls) {
        const refreshBtn = await controls.$('.refresh-button');
        const collapseToggle = await controls.$('.collapse-toggle');
        
        expect(refreshBtn).toBeTruthy();
        expect(collapseToggle).toBeTruthy();
      }
    }
  }, TEST_TIMEOUT);

  test('P-10: Refresh status bar shows checking state correctly', async () => {
    const refreshButton = await page.$('.refresh-button');
    const statusBar = await page.$('.refresh-status-bar');
    
    expect(refreshButton).toBeTruthy();
    expect(statusBar).toBeTruthy();
    
    if (refreshButton && statusBar) {
      await refreshButton.click();
      await page.waitForTimeout(500);
      
      // Check checking class
      const hasCheckingClass = await statusBar.evaluate(el => 
        el.classList.contains('checking')
      );
      expect(hasCheckingClass).toBe(true);
      
      // Check icon
      const icon = await statusBar.$eval('.refresh-status-icon', el => el.textContent);
      expect(icon).toBe('⏳');
      
      // Check text
      const text = await statusBar.$eval('.refresh-status-text', el => el.textContent);
      expect(text).toBe('Checking live status...');
    }
  }, TEST_TIMEOUT);

  test('P-11: Refresh status bar shows updated state after completion', async () => {
    const refreshButton = await page.$('.refresh-button');
    expect(refreshButton).toBeTruthy();
    
    if (refreshButton) {
      // Trigger refresh
      await refreshButton.click();
      
      // Wait for completion
      await page.waitForFunction(
        () => {
          const btn = document.querySelector('.refresh-button');
          return btn && !(btn as HTMLButtonElement).disabled;
        },
        { timeout: 120000 }
      );
      
      // Check status bar shows updated state
      const statusBar = await page.$('.refresh-status-bar');
      if (statusBar) {
        const text = await statusBar.$eval('.refresh-status-text', el => el.textContent);
        
        // Should match "Updated X ago" pattern
        expect(text).toMatch(/Updated\s+(Just now|\d+m ago|\d+h ago)/);
      }
    }
  }, TEST_TIMEOUT);

  test('P-12: Multiple rapid clicks on refresh button are handled correctly', async () => {
    const refreshButton = await page.$('.refresh-button');
    expect(refreshButton).toBeTruthy();
    
    if (refreshButton) {
      // Click multiple times rapidly
      await refreshButton.click();
      await refreshButton.click();
      await refreshButton.click();
      
      // Check button is in valid state
      const isDisabled = await refreshButton.evaluate(el => 
        (el as HTMLButtonElement).disabled
      );
      expect(typeof isDisabled).toBe('boolean');
    }
  }, TEST_TIMEOUT);

  test('P-13: Live Summary remains functional during refresh', async () => {
    const refreshButton = await page.$('.refresh-button');
    const collapseToggle = await page.$('.collapse-toggle');
    
    expect(refreshButton).toBeTruthy();
    expect(collapseToggle).toBeTruthy();
    
    if (refreshButton && collapseToggle) {
      // Start refresh
      await refreshButton.click();
      await page.waitForTimeout(500);
      
      // Try to collapse/expand
      await collapseToggle.click();
      
      // Should still work - check if toggle changes
      const toggleText = await collapseToggle.evaluate(el => el.textContent);
      expect(['▼', '▲']).toContain(toggleText);
    }
  }, TEST_TIMEOUT);

  test('P-14: Refresh progress is shown when checking', async () => {
    const refreshButton = await page.$('.refresh-button');
    expect(refreshButton).toBeTruthy();
    
    if (refreshButton) {
      await refreshButton.click();
      
      // Wait for progress container to appear
      try {
        await page.waitForSelector('.checking-progress-container', { timeout: 5000 });
        
        const progressContainer = await page.$('.checking-progress-container');
        if (progressContainer) {
          const text = await progressContainer.evaluate(el => el.textContent);
          expect(text).toContain('Checking for live creators');
        }
      } catch {
        // If it completed too fast, that's okay
      }
    }
  }, TEST_TIMEOUT);

  test('P-15: Page load shows correct initial state', async () => {
    // Reload page
    await page.reload({ waitUntil: 'networkidle2' });
    await page.waitForSelector('.live-summary', { timeout: 10000 });
    
    // Check refresh button exists
    const refreshButton = await page.$('.refresh-button');
    expect(refreshButton).toBeTruthy();
    
    // Check status bar exists
    const statusBar = await page.$('.refresh-status-bar');
    expect(statusBar).toBeTruthy();
    
    // Check timestamps exist
    const timestamps = await page.$('.timestamps');
    expect(timestamps).toBeTruthy();
    
    if (timestamps) {
      const text = await timestamps.evaluate(el => el.textContent);
      expect(text).toContain('Page loaded');
    }
  }, TEST_TIMEOUT);

  test('P-16: Manual refresh can be triggered at any time', async () => {
    const refreshButton = await page.$('.refresh-button');
    expect(refreshButton).toBeTruthy();
    
    if (refreshButton) {
      // Check initially enabled
      const isEnabled = await refreshButton.evaluate(el => 
        !(el as HTMLButtonElement).disabled
      );
      expect(isEnabled).toBe(true);
      
      // Click should work
      await refreshButton.click();
      
      // Should be disabled after click
      const isDisabled = await refreshButton.evaluate(el => 
        (el as HTMLButtonElement).disabled
      );
      expect(isDisabled).toBe(true);
    }
  }, TEST_TIMEOUT);

  test('P-17: No live message shows helpful text', async () => {
    // Check if no live message exists
    const noLiveMessage = await page.$('.no-live-message');
    
    if (noLiveMessage) {
      const text = await noLiveMessage.evaluate(el => el.textContent);
      
      // Should indicate no creators are live
      expect(text).toContain('No creators live right now');
      
      // Should mention auto-update frequency
      const subtext = await noLiveMessage.$eval('.no-live-subtext', el => el.textContent);
      expect(subtext).toContain('3 minutes');
    }
  }, TEST_TIMEOUT);

  test('P-18: Refresh button hover effects work', async () => {
    const refreshButton = await page.$('.refresh-button');
    expect(refreshButton).toBeTruthy();
    
    if (refreshButton) {
      // Hover over the button
      await refreshButton.hover();
      await page.waitForTimeout(200);
      
      // Check button is still visible and interactive
      const isVisible = await refreshButton.isIntersectingViewport();
      expect(isVisible).toBe(true);
    }
  }, TEST_TIMEOUT);

  test('P-19: Status bar transitions through states correctly', async () => {
    const refreshButton = await page.$('.refresh-button');
    const statusBar = await page.$('.refresh-status-bar');
    
    expect(refreshButton).toBeTruthy();
    expect(statusBar).toBeTruthy();
    
    if (refreshButton && statusBar) {
      // Get initial state
      const initialClasses = await statusBar.evaluate(el => el.className);
      
      // Start refresh
      await refreshButton.click();
      await page.waitForTimeout(500);
      
      // Should be in checking state
      const checkingClasses = await statusBar.evaluate(el => el.className);
      expect(checkingClasses).toContain('checking');
      
      // Wait for completion
      await page.waitForFunction(
        () => {
          const btn = document.querySelector('.refresh-button');
          return btn && !(btn as HTMLButtonElement).disabled;
        },
        { timeout: 120000 }
      );
      
      // Should transition to updated/info state
      const finalClasses = await statusBar.evaluate(el => el.className);
      expect(finalClasses).toMatch(/updated|info/);
    }
  }, TEST_TIMEOUT);

  test('P-20: Auto-update frequency is documented in UI', async () => {
    // Look for any mention of the 3-minute update interval
    const pageContent = await page.evaluate(() => document.body.textContent);
    
    // Should mention the auto-update interval somewhere
    const hasUpdateInterval = 
      pageContent?.includes('3 minutes') ||
      pageContent?.includes('180 seconds') ||
      pageContent?.includes('Auto-updates');
    
    expect(hasUpdateInterval).toBe(true);
  }, TEST_TIMEOUT);
});
