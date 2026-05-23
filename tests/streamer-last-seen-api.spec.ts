import { test, expect } from '@playwright/test';

/**
 * Tests for the Streamer Last Seen API endpoints
 * These endpoints cache live status to reduce API calls and enable quick loading
 */

const API_BASE = 'https://findtorontoevents.ca/fc/api';

test.describe('Streamer Last Seen API', () => {
  
  const testCreator = {
    creator_id: `test_creator_${Date.now()}`,
    creator_name: 'Test Creator',
    platform: 'twitch',
    username: 'testuser',
    is_live: true,
    stream_title: 'Test Stream',
    viewer_count: 100
  };

  test('GET get_streamer_last_seen.php - should return empty array initially', async ({ request }) => {
    const response = await request.get(`${API_BASE}/get_streamer_last_seen.php`, {
      params: { creator_id: 'nonexistent', platform: 'twitch' }
    });
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok).toBe(true);
    expect(Array.isArray(data.streamers)).toBe(true);
    expect(data.streamers.length).toBe(0);
    expect(data.stats.total_tracked).toBeGreaterThanOrEqual(0);
  });

  test('POST update_streamer_last_seen.php - should create new record', async ({ request }) => {
    const response = await request.post(`${API_BASE}/update_streamer_last_seen.php`, {
      data: testCreator
    });
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok).toBe(true);
    expect(data.action).toBe('created');
    expect(data.creator_id).toBe(testCreator.creator_id);
    expect(data.platform).toBe(testCreator.platform);
    expect(data.is_live).toBe(true);
    expect(data.record_id).toBeGreaterThan(0);
  });

  test('GET get_streamer_last_seen.php - should return created record', async ({ request }) => {
    const response = await request.get(`${API_BASE}/get_streamer_last_seen.php`, {
      params: { creator_id: testCreator.creator_id, platform: testCreator.platform }
    });
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok).toBe(true);
    expect(data.streamers.length).toBe(1);
    
    const record = data.streamers[0];
    expect(record.creator_id).toBe(testCreator.creator_id);
    expect(record.creator_name).toBe(testCreator.creator_name);
    expect(record.platform).toBe(testCreator.platform);
    expect(record.username).toBe(testCreator.username);
    expect(record.is_live).toBe(true);
    expect(record.stream_title).toBe(testCreator.stream_title);
    expect(record.viewer_count).toBe(testCreator.viewer_count);
  });

  test('GET get_streamer_last_seen.php - live_only filter should work', async ({ request }) => {
    // First create an offline record
    const offlineCreator = {
      ...testCreator,
      creator_id: `offline_${Date.now()}`,
      is_live: false
    };
    
    await request.post(`${API_BASE}/update_streamer_last_seen.php`, {
      data: offlineCreator
    });
    
    // Query with live_only=1
    const response = await request.get(`${API_BASE}/get_streamer_last_seen.php`, {
      params: { live_only: '1' }
    });
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok).toBe(true);
    
    // Should only include live creators
    const liveCreators = data.streamers.filter((s: any) => s.is_live);
    const offlineCreators = data.streamers.filter((s: any) => !s.is_live);
    
    expect(offlineCreators.length).toBe(0);
    expect(liveCreators.length).toBeGreaterThanOrEqual(1);
  });

  test('POST update_streamer_last_seen.php - should update existing record', async ({ request }) => {
    const updatedData = {
      ...testCreator,
      is_live: false,
      stream_title: 'Stream Ended',
      viewer_count: 0
    };
    
    const response = await request.post(`${API_BASE}/update_streamer_last_seen.php`, {
      data: updatedData
    });
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok).toBe(true);
    expect(data.action).toBe('updated');
    expect(data.is_live).toBe(false);
  });

  test('GET get_streamer_last_seen.php - since_minutes filter should work', async ({ request }) => {
    const response = await request.get(`${API_BASE}/get_streamer_last_seen.php`, {
      params: { since_minutes: '60' }
    });
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok).toBe(true);
    expect(data.query.since_minutes).toBe(60);
    expect(Array.isArray(data.streamers)).toBe(true);
  });
});

test.describe('Live Status Cache API', () => {
  
  const testCacheData = {
    creators: [{
      id: `cache_test_${Date.now()}`,
      name: 'Cache Test Creator',
      avatarUrl: 'https://example.com/avatar.jpg',
      accounts: [{
        platform: 'twitch',
        username: 'cachetest',
        isLive: true,
        streamTitle: 'Cached Stream',
        viewerCount: 500,
        startedAt: new Date().toISOString(),
        checkMethod: 'api',
        nextCheckDate: Date.now() + 60000
      }]
    }]
  };

  test('GET get_live_cached.php - should return empty initially', async ({ request }) => {
    const response = await request.get(`${API_BASE}/get_live_cached.php`);
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok).toBe(true);
    expect(Array.isArray(data.liveNow)).toBe(true);
    expect(Array.isArray(data.recentlyLive)).toBe(true);
    expect(data.cached).toBe(true);
  });

  test('POST sync_live_status.php - should sync creator status', async ({ request }) => {
    const response = await request.post(`${API_BASE}/sync_live_status.php`, {
      data: testCacheData
    });
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok).toBe(true);
    expect(data.updated).toBeGreaterThan(0);
    expect(data.timestamp).toBeDefined();
  });

  test('GET get_live_cached.php - should return cached live creators', async ({ request }) => {
    const response = await request.get(`${API_BASE}/get_live_cached.php`, {
      params: { since_minutes: '60' }
    });
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok).toBe(true);
    expect(data.liveNow.length).toBeGreaterThan(0);
    
    // Find our test creator
    const testCreator = data.liveNow.find((c: any) => c.id === testCacheData.creators[0].id);
    expect(testCreator).toBeDefined();
    expect(testCreator.name).toBe(testCacheData.creators[0].name);
    expect(testCreator.platforms.length).toBeGreaterThan(0);
    
    const platform = testCreator.platforms[0];
    expect(platform.platform).toBe('twitch');
    expect(platform.isLive).toBe(true);
    expect(platform.streamTitle).toBe('Cached Stream');
  });

  test('GET get_live_cached.php - stats should be accurate', async ({ request }) => {
    const response = await request.get(`${API_BASE}/get_live_cached.php`);
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok).toBe(true);
    expect(data.stats).toBeDefined();
    expect(typeof data.stats.totalCached).toBe('number');
    expect(typeof data.stats.liveCount).toBe('number');
    expect(data.stats.sinceMinutes).toBe(60);
    expect(data.timestamp).toBeDefined();
  });
});

test.describe('Frontend Integration with Last Seen API', () => {
  
  test('frontend should load cached live status on page load', async ({ page, request }) => {
    // First, create a cached live entry
    const cacheData = {
      creators: [{
        id: 'frontend_test_123',
        name: 'Frontend Test Creator',
        avatarUrl: 'https://example.com/avatar.jpg',
        accounts: [{
          platform: 'twitch',
          username: 'frontendtest',
          isLive: true,
          streamTitle: 'Integration Test Stream',
          viewerCount: 1000,
          startedAt: new Date().toISOString(),
          checkMethod: 'api',
          nextCheckDate: Date.now() + 60000
        }]
      }]
    };
    
    await request.post(`${API_BASE}/sync_live_status.php`, {
      data: cacheData
    });
    
    // Now load the frontend
    await page.goto('https://findtorontoevents.ca/fc/#/guest');
    await page.waitForSelector('.app-container', { timeout: 30000 });
    await page.waitForTimeout(5000);
    
    // Check console for cache loading messages
    const logs: string[] = [];
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('Live Cache') || text.includes('get_live_cached')) {
        logs.push(text);
      }
    });
    
    await page.waitForTimeout(2000);
    
    console.log('Live cache related logs:', logs);
    
    // The live summary should be visible
    const liveSummary = page.locator('.live-summary');
    await expect(liveSummary).toBeVisible();
    
    // Take screenshot for debugging
    await page.screenshot({ 
      path: 'test-results/live-cache-integration.png', 
      fullPage: false 
    });
  });

  test('last seen endpoints should not return 500 errors', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        const text = msg.text();
        if (text.includes('get_streamer_last_seen') || 
            text.includes('update_streamer_last_seen') ||
            text.includes('get_live_cached') ||
            text.includes('sync_live_status')) {
          errors.push(text);
        }
      }
    });
    
    page.on('response', response => {
      const url = response.url();
      if (url.includes('get_streamer_last_seen.php') || 
          url.includes('update_streamer_last_seen.php') ||
          url.includes('get_live_cached.php') ||
          url.includes('sync_live_status.php')) {
        if (!response.ok()) {
          errors.push(`API Error ${response.status()}: ${url}`);
        }
      }
    });
    
    await page.goto('https://findtorontoevents.ca/fc/#/guest');
    await page.waitForSelector('.app-container', { timeout: 30000 });
    await page.waitForTimeout(10000); // Wait for API calls
    
    // Check for live status check to trigger API calls
    const checkAllBtn = page.locator('button[title="Check all live statuses"]').first();
    if (await checkAllBtn.isVisible().catch(() => false)) {
      await checkAllBtn.click();
      await page.waitForTimeout(5000);
    }
    
    console.log('API errors found:', errors);
    expect(errors.length).toBe(0);
  });
});
