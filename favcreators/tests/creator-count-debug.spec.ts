/**
 * Creator Count Debug Test
 * 
 * This test investigates why only ~11 creators are being checked for live status
 * when the user follows ~42 creators.
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'https://findtorontoevents.ca/fc/';

test.describe('Creator Count Debug', () => {
  test('Debug: Log creator counts at various stages', async ({ page }) => {
    // Collect console logs
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      const text = msg.text();
      consoleLogs.push(text);
      console.log(`[BROWSER] ${text}`);
    });

    // Collect network responses
    const apiResponses: Record<string, any> = {};
    page.on('response', async response => {
      const url = response.url();
      if (url.includes('get_my_creators.php') || url.includes('get_live_cached.php')) {
        try {
          const data = await response.json();
          apiResponses[url] = {
            status: response.status(),
            headers: await response.allHeaders(),
            data: data
          };
          console.log(`[API] ${url} - ${response.status()}`);
          if (data.creators) {
            console.log(`[API] Creators count from API: ${data.creators.length}`);
          }
        } catch (e) {
          console.log(`[API] ${url} - Could not parse JSON`);
        }
      }
    });

    // Navigate to the page
    await page.goto(BASE_URL);
    
    // Wait for the Live Summary to appear
    await page.waitForSelector('.live-summary', { timeout: 30000 });
    
    // Wait for any initial loading to complete
    await page.waitForTimeout(5000);

    // Check if user is logged in
    const authInfo = await page.evaluate(() => {
      const authUser = localStorage.getItem('fav_creators_auth_user');
      return {
        hasAuth: !!authUser,
        authData: authUser ? JSON.parse(authUser) : null
      };
    });
    
    console.log('[TEST] Auth info:', authInfo);

    // Get creators from localStorage
    const localData = await page.evaluate(() => {
      const creators = localStorage.getItem('fav_creators');
      return {
        hasCreators: !!creators,
        count: creators ? JSON.parse(creators).length : 0,
        creators: creators ? JSON.parse(creators) : []
      };
    });
    
    console.log(`[TEST] Creators in localStorage: ${localData.count}`);
    
    // Log all creator names
    if (localData.creators.length > 0) {
      console.log('[TEST] Creator names in localStorage:');
      localData.creators.forEach((c: any, i: number) => {
        console.log(`  ${i + 1}. ${c.name} (id: ${c.id})`);
      });
    }

    // Wait for live check to start
    await page.waitForFunction(() => {
      const progress = document.querySelector('.checking-progress-container');
      return progress !== null;
    }, { timeout: 60000 });

    // Get the progress text to see total count
    const progressText = await page.locator('.checking-progress div').first().textContent();
    console.log(`[TEST] Progress text: ${progressText}`);

    // Extract total from progress (e.g., "6 / 11 (55%)")
    const match = progressText?.match(/\d+\s+\/\s+(\d+)/);
    if (match) {
      const totalChecking = parseInt(match[1]);
      console.log(`[TEST] Total creators being checked: ${totalChecking}`);
      console.log(`[TEST] Creators in localStorage: ${localData.count}`);
      
      // This is the key assertion
      if (totalChecking < localData.count) {
        console.error(`[TEST] BUG DETECTED: Only checking ${totalChecking} of ${localData.count} creators!`);
      }
    }

    // Wait for checking to complete or timeout
    try {
      await page.waitForFunction(() => {
        const refreshButton = document.querySelector('.refresh-button');
        return refreshButton && !(refreshButton as HTMLButtonElement).disabled;
      }, { timeout: 120000 });
    } catch {
      console.log('[TEST] Live check timed out or still in progress');
    }

    // Get final stats
    const finalStatus = await page.locator('.refresh-status-bar').textContent();
    console.log(`[TEST] Final status: ${finalStatus}`);

    // Log all console messages for debugging
    console.log('[TEST] All console logs:');
    consoleLogs.forEach((log, i) => {
      if (log.includes('Loaded creators from DB') || 
          log.includes('creators') || 
          log.includes('get_my_creators') ||
          log.includes('Loaded')) {
        console.log(`  ${i}: ${log}`);
      }
    });

    // Log API responses
    console.log('[TEST] API Responses summary:');
    Object.entries(apiResponses).forEach(([url, response]: [string, any]) => {
      console.log(`  ${url}:`);
      console.log(`    Status: ${response.status}`);
      console.log(`    X-Creator-Count header: ${response.headers['x-creator-count'] || 'N/A'}`);
      if (response.data?.creators) {
        console.log(`    Creators in response: ${response.data.creators.length}`);
      }
    });
  });

  test('Debug: Check API response directly', async ({ request }) => {
    // This test makes a direct API call to check the creator count
    const apiUrl = `${BASE_URL}api/get_my_creators.php?user_id=2`;
    
    console.log(`[TEST] Calling API: ${apiUrl}`);
    
    const response = await request.get(apiUrl);
    const status = response.status();
    const headers = response.headers();
    const data = await response.json();
    
    console.log(`[TEST] API Status: ${status}`);
    console.log(`[TEST] X-Creator-Count header: ${headers['x-creator-count'] || 'N/A'}`);
    console.log(`[TEST] X-Source header: ${headers['x-source'] || 'N/A'}`);
    
    if (data.creators) {
      console.log(`[TEST] Creators in API response: ${data.creators.length}`);
      
      // List all creators
      console.log('[TEST] Creator names from API:');
      data.creators.forEach((c: any, i: number) => {
        console.log(`  ${i + 1}. ${c.name} (id: ${c.id})`);
      });
      
      // Check for duplicates by name
      const names = data.creators.map((c: any) => c.name?.toLowerCase()?.trim());
      const uniqueNames = new Set(names);
      if (names.length !== uniqueNames.size) {
        console.warn(`[TEST] WARNING: Found ${names.length - uniqueNames.size} duplicate name(s)`);
      }
    } else {
      console.log('[TEST] No creators array in response');
      console.log('[TEST] Response:', JSON.stringify(data, null, 2));
    }
  });

  test('Debug: Check localStorage vs API mismatch', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('.live-summary', { timeout: 30000 });
    await page.waitForTimeout(3000);

    // Get API response through page
    const apiInfo = await page.evaluate(async () => {
      // Get auth user ID
      const authUser = localStorage.getItem('fav_creators_auth_user');
      const userId = authUser ? JSON.parse(authUser).id : 0;
      
      // Make API call
      const baseUrl = window.location.origin + '/fc/';
      const response = await fetch(`${baseUrl}api/get_my_creators.php?user_id=${userId}`);
      const data = await response.json();
      
      return {
        userId,
        apiCreatorsCount: data.creators?.length || 0,
        apiCreators: data.creators?.map((c: any) => ({ name: c.name, id: c.id })) || []
      };
    });

    // Get localStorage creators
    const localInfo = await page.evaluate(() => {
      const creators = localStorage.getItem('fav_creators');
      const parsed = creators ? JSON.parse(creators) : [];
      return {
        localCreatorsCount: parsed.length,
        localCreators: parsed.map((c: any) => ({ name: c.name, id: c.id }))
      };
    });

    console.log('[TEST] API vs LocalStorage comparison:');
    console.log(`  API creators: ${apiInfo.apiCreatorsCount}`);
    console.log(`  LocalStorage creators: ${localInfo.localCreatorsCount}`);
    
    // Find missing creators
    const apiIds = new Set(apiInfo.apiCreators.map((c: any) => c.id));
    const localIds = new Set(localInfo.localCreators.map((c: any) => c.id));
    
    const inApiButNotLocal = apiInfo.apiCreators.filter((c: any) => !localIds.has(c.id));
    const inLocalButNotApi = localInfo.localCreators.filter((c: any) => !apiIds.has(c.id));
    
    if (inApiButNotLocal.length > 0) {
      console.log('[TEST] Creators in API but not in localStorage:');
      inApiButNotLocal.forEach((c: any) => console.log(`  - ${c.name}`));
    }
    
    if (inLocalButNotApi.length > 0) {
      console.log('[TEST] Creators in localStorage but not in API:');
      inLocalButNotApi.forEach((c: any) => console.log(`  - ${c.name}`));
    }

    // The API count should match localStorage after initial load
    expect(localInfo.localCreatorsCount).toBe(apiInfo.apiCreatorsCount);
  });
});
