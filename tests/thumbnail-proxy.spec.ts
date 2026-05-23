import { test, expect } from '@playwright/test';

/**
 * Tests for the Thumbnail Proxy API
 * Verifies thumbnail resolution and fallback behavior
 */

const API_BASE = 'https://findtorontoevents.ca/fc/api';

test.describe('Thumbnail Proxy API Tests', () => {
  
  test('resolves YouTube thumbnail from video URL', async ({ request }) => {
    const response = await request.get(`${API_BASE}/thumbnail_proxy.php?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.thumbnail_url).toBeTruthy();
    expect(data.thumbnail_url).toContain('ytimg.com');
    expect(data.video_id).toBe('dQw4w9WgXcQ');
    expect(data.method).toBeTruthy();
    
    console.log('YouTube thumbnail resolved:', data.thumbnail_url, 'via', data.method);
  });

  test('resolves YouTube thumbnail from youtu.be short URL', async ({ request }) => {
    const response = await request.get(`${API_BASE}/thumbnail_proxy.php?url=https://youtu.be/dQw4w9WgXcQ`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.thumbnail_url).toContain('ytimg.com');
    expect(data.video_id).toBe('dQw4w9WgXcQ');
  });

  test('resolves YouTube thumbnail from shorts URL', async ({ request }) => {
    // Use a real shorts video ID
    const response = await request.get(`${API_BASE}/thumbnail_proxy.php?url=https://www.youtube.com/shorts/CbKmAzp1xJ8`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    // Should find a thumbnail for shorts
    expect(data.thumbnail_url).toBeTruthy();
    expect(data.thumbnail_url).toContain('CbKmAzp1xJ8');
    console.log('Shorts thumbnail:', data.thumbnail_url, 'via', data.method);
  });

  test('handles news.google.com URLs gracefully', async ({ request }) => {
    const response = await request.get(`${API_BASE}/thumbnail_proxy.php?url=https://news.google.com/rss/articles/CBMi...`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    // News URLs may not have accessible thumbnails
    expect(data.method).toBe('news_unavailable');
    console.log('News URL result:', data);
  });

  test('handles Twitch URL with og:image', async ({ request }) => {
    const response = await request.get(`${API_BASE}/thumbnail_proxy.php?url=https://www.twitch.tv/ninja`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    // Twitch profiles should return og:image
    if (data.thumbnail_url) {
      expect(data.method).toBe('og_image');
      console.log('Twitch thumbnail:', data.thumbnail_url);
    }
  });

  test('returns usage info without URL parameter', async ({ request }) => {
    const response = await request.get(`${API_BASE}/thumbnail_proxy.php`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.error).toBe('Missing URL parameter');
    expect(data.usage).toBeTruthy();
  });

  test('fix_missing returns fix results', async ({ request }) => {
    const response = await request.get(`${API_BASE}/thumbnail_proxy.php?fix_missing=1&limit=5`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.fixed_count).toBeDefined();
    expect(data.failed_count).toBeDefined();
    expect(Array.isArray(data.fixed)).toBeTruthy();
    expect(Array.isArray(data.failed)).toBeTruthy();
    
    console.log(`Fixed: ${data.fixed_count}, Failed: ${data.failed_count}`);
  });

  test('video_id parameter works for YouTube', async ({ request }) => {
    const response = await request.get(`${API_BASE}/thumbnail_proxy.php?video_id=dQw4w9WgXcQ&platform=youtube`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.thumbnail_url).toContain('ytimg.com');
    expect(data.video_id).toBe('dQw4w9WgXcQ');
  });
});
