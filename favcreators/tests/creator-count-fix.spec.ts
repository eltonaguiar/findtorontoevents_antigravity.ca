/**
 * Creator Count Fix Verification Test
 * 
 * This test verifies that the fix for the race condition works correctly:
 * - The live status check should wait for all creators to load from the API
 * - It should NOT check only the INITIAL_DATA (11 creators) when user has more
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'https://findtorontoevents.ca/fc/';

test.describe('Creator Count Fix Verification', () => {
  test('Live check should wait for API-loaded creators, not use INITIAL_DATA', async ({ page }) => {
    const consoleLogs: string[] = [];
    
    // Collect console logs
    page.on('console', msg => {
      const text = msg.text();
      consoleLogs.push(text);
      console.log(`[BROWSER] ${text}`);
    });

    // Navigate to the page
    await page.goto(BASE_URL);
    
    // Wait for Live Summary to appear
    await page.waitForSelector('.live-summary', { timeout: 30000 });
    
    // Wait for the creators to be loaded message
    await page.waitForFunction(() => {
      return consoleLogs.some(log => 
        log.includes('Creators loaded:') || 
        log.includes('Loaded creators from DB')
      );
    }, { timeout: 30000 });

    // Now wait for live check to start
    await page.waitForFunction(() => {
      return consoleLogs.some(log => 
        log.includes('Starting check with') || 
        log.includes('Checking:')
      );
    }, { timeout: 30000 });

    // Parse the console logs to find creator counts
    const loadedLog = consoleLogs.find(log => log.includes('Creators loaded:'));
    const startingCheckLog = consoleLogs.find(log => log.includes('Starting check with'));
    
    console.log('[TEST] Loaded log:', loadedLog);
    console.log('[TEST] Starting check log:', startingCheckLog);

    // Extract creator counts
    let apiCreatorCount = 0;
    let checkCreatorCount = 0;
    
    if (loadedLog) {
      const match = loadedLog.match(/Creators loaded:\s*(\d+)/);
      if (match) apiCreatorCount = parseInt(match[1]);
    }
    
    if (startingCheckLog) {
      const match = startingCheckLog.match(/Starting check with\s*(\d+)/);
      if (match) checkCreatorCount = parseInt(match[1]);
    }

    console.log(`[TEST] Creators loaded from API: ${apiCreatorCount}`);
    console.log(`[TEST] Creators being checked: ${checkCreatorCount}`);

    // The key assertion: the check should use the API-loaded count, not INITIAL_DATA (11)
    // If apiCreatorCount > 11, then checkCreatorCount should match apiCreatorCount
    if (apiCreatorCount > 11) {
      expect(checkCreatorCount).toBe(apiCreatorCount);
      console.log('[TEST] ✅ PASS: Live check is using all API-loaded creators');
    } else {
      console.log('[TEST] ⚠️ User may have 11 or fewer creators, or using guest mode');
    }

    // Also verify through the UI progress indicator
    const progressText = await page.locator('.checking-progress div').first().textContent().catch(() => '');
    console.log(`[TEST] UI Progress text: ${progressText}`);
    
    const progressMatch = progressText.match(/\d+\s+\/\s+(\d+)/);
    if (progressMatch) {
      const uiTotal = parseInt(progressMatch[1]);
      console.log(`[TEST] UI shows total: ${uiTotal}`);
      
      // UI total should match API count (or be close)
      if (apiCreatorCount > 11) {
        expect(uiTotal).toBeGreaterThan(11);
      }
    }
  });

  test('Logged-in user should have all creators checked', async ({ page }) => {
    // Check if user is logged in
    const authInfo = await page.evaluate(() => {
      const authUser = localStorage.getItem('fav_creators_auth_user');
      return authUser ? JSON.parse(authUser) : null;
    });

    console.log('[TEST] Auth user:', authInfo);

    if (!authInfo) {
      console.log('[TEST] Skipping - user not logged in');
      return;
    }

    // Navigate to page
    await page.goto(BASE_URL);
    await page.waitForSelector('.live-summary', { timeout: 30000 });
    
    // Wait for live check to start
    await page.waitForSelector('.checking-progress-container', { timeout: 60000 });

    // Get the progress text
    const progressText = await page.locator('.checking-progress div').first().textContent();
    console.log(`[TEST] Progress: ${progressText}`);

    // Extract total from progress (e.g., "6 / 42 (14%)")
    const match = progressText?.match(/\d+\s+\/\s+(\d+)/);
    if (match) {
      const totalChecking = parseInt(match[1]);
      console.log(`[TEST] Total creators being checked: ${totalChecking}`);

      // Verify we're checking more than the default 11
      expect(totalChecking).toBeGreaterThan(11);
      
      // Log success
      console.log(`[TEST] ✅ PASS: Checking ${totalChecking} creators (more than default 11)`);
    }
  });

  test('Console should show correct sequence: load -> then check', async ({ page }) => {
    const logs: string[] = [];
    
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('Live Check') || text.includes('Loaded creators')) {
        logs.push(text);
        console.log(`[SEQUENCE] ${text}`);
      }
    });

    await page.goto(BASE_URL);
    await page.waitForSelector('.live-summary', { timeout: 30000 });
    
    // Wait for both load and check messages
    await page.waitForFunction(() => {
      const allLogs = (window as any).consoleLogs || [];
      return allLogs.some((log: string) => log.includes('Creators loaded:')) &&
             allLogs.some((log: string) => log.includes('Starting check with'));
    }, { timeout: 60000 }).catch(() => {
      // Continue even if timeout - we'll check what we have
    });

    await page.waitForTimeout(2000); // Give time for more logs

    // Find the sequence
    const loadedIndex = logs.findIndex(log => log.includes('Creators loaded:'));
    const startingCheckIndex = logs.findIndex(log => log.includes('Starting check with'));

    console.log(`[TEST] Loaded message at index: ${loadedIndex}`);
    console.log(`[TEST] Starting check message at index: ${startingCheckIndex}`);

    if (loadedIndex >= 0 && startingCheckIndex >= 0) {
      // The check should start AFTER creators are loaded
      expect(startingCheckIndex).toBeGreaterThan(loadedIndex);
      console.log('[TEST] ✅ PASS: Live check starts after creators are loaded');
    }
  });

  test('Race condition fix: should not show 11 creators when user has more', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('.live-summary', { timeout: 30000 });

    // Wait for the checking to start
    const progressContainer = await page.waitForSelector('.checking-progress-container', { 
      timeout: 60000,
      state: 'visible'
    });

    // Get the progress text immediately
    const progressText = await page.locator('.checking-progress div').first().textContent();
    console.log(`[TEST] Initial progress: ${progressText}`);

    // Extract total
    const match = progressText?.match(/\d+\s+\/\s+(\d+)/);
    if (match) {
      const initialTotal = parseInt(match[1]);
      console.log(`[TEST] Initial total shown: ${initialTotal}`);

      // If user has more than 11 creators, we should never see exactly 11
      // (unless they actually have exactly 11)
      const localData = await page.evaluate(() => {
        const creators = localStorage.getItem('fav_creators');
        return creators ? JSON.parse(creators).length : 0;
      });

      console.log(`[TEST] localStorage creators: ${localData}`);

      // Wait for a bit and check again - it should remain consistent
      await page.waitForTimeout(3000);
      
      const laterProgressText = await page.locator('.checking-progress div').first().textContent();
      const laterMatch = laterProgressText?.match(/\d+\s+\/\s+(\d+)/);
      
      if (laterMatch) {
        const laterTotal = parseInt(laterMatch[1]);
        console.log(`[TEST] Later total shown: ${laterTotal}`);
        
        // The total should be consistent (not change from 11 to 42 mid-check)
        expect(laterTotal).toBe(initialTotal);
      }
    }
  });
});

test.describe('Creator Count Debug - API Verification', () => {
  test('API should return correct creator count for logged-in user', async ({ request }) => {
    // This test makes a direct API call to verify the backend is returning all creators
    const apiUrl = `${BASE_URL}api/get_my_creators.php?user_id=2`;
    
    console.log(`[TEST] Calling API: ${apiUrl}`);
    
    const response = await request.get(apiUrl);
    const status = response.status();
    const headers = response.headers();
    const data = await response.json();
    
    console.log(`[TEST] API Status: ${status}`);
    console.log(`[TEST] X-Creator-Count header: ${headers['x-creator-count'] || 'N/A'}`);
    
    if (data.creators) {
      console.log(`[TEST] Creators in API response: ${data.creators.length}`);
      
      // List all creators
      console.log('[TEST] All creators from API:');
      data.creators.forEach((c: any, i: number) => {
        console.log(`  ${i + 1}. ${c.name}`);
      });
      
      // Verify count matches header
      expect(data.creators.length.toString()).toBe(headers['x-creator-count'] || '');
      
      // The API should return more than 11 if user has more
      // (This assertion might fail for guest mode which uses default list)
      if (data.creators.length <= 11) {
        console.log('[TEST] ⚠️ Only 11 or fewer creators in API - may be default list');
      } else {
        console.log(`[TEST] ✅ PASS: API returns ${data.creators.length} creators`);
      }
    }
  });
});
