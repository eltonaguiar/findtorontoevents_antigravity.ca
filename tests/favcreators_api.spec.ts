import { test, expect } from '@playwright/test';

const API_BASE = 'https://findtorontoevents.ca/fc';

test.describe('FavCreators API Tests', () => {
  
  test('API health check - TLC.php responds', async ({ request }) => {
    const response = await request.get(`${API_BASE}/TLC.php?platform=tiktok&user=test`);
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('live');
    expect(data).toHaveProperty('method');
  });

  test('get_my_creators.php returns creators for user_id=0', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/get_my_creators.php?user_id=0`);
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('creators');
    expect(Array.isArray(data.creators)).toBe(true);
    expect(data.creators.length).toBeGreaterThan(0);
    
    // Check structure of first creator
    const firstCreator = data.creators[0];
    expect(firstCreator).toHaveProperty('id');
    expect(firstCreator).toHaveProperty('name');
    expect(firstCreator).toHaveProperty('accounts');
  });

  test('get_my_creators.php returns creators for user_id=2', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/get_my_creators.php?user_id=2`);
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('creators');
  });

  test('get_streamer_last_seen.php returns data', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/get_streamer_last_seen.php`);
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('ok');
    expect(data.ok).toBe(true);
    expect(data).toHaveProperty('streamers');
    expect(data).toHaveProperty('stats');
  });

  test('update_streamer_last_seen.php accepts POST data', async ({ request }) => {
    const payload = {
      creator_id: 'test-creator-' + Date.now(),
      creator_name: 'Test Creator',
      platform: 'tiktok',
      username: 'testuser',
      is_live: false,
      checked_by: 'test@example.com'
    };
    
    const response = await request.post(`${API_BASE}/api/update_streamer_last_seen.php`, {
      data: payload
    });
    
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('ok');
    expect(data.ok).toBe(true);
  });

  test('db_connect.php is accessible', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/test_db.php`);
    expect(response.status()).toBe(200);
  });

  test('All API endpoints return valid JSON', async ({ request }) => {
    const endpoints = [
      '/api/get_my_creators.php?user_id=0',
      '/api/get_streamer_last_seen.php',
      '/TLC.php?platform=tiktok&user=wtfpreston'
    ];
    
    for (const endpoint of endpoints) {
      const response = await request.get(`${API_BASE}${endpoint}`);
      expect(response.status()).toBe(200);
      
      const contentType = response.headers()['content-type'];
      expect(contentType).toContain('json');
      
      // Verify it's valid JSON
      const text = await response.text();
      expect(() => JSON.parse(text)).not.toThrow();
    }
  });
});