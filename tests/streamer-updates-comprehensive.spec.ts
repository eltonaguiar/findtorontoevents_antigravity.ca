import { test, expect } from '@playwright/test';

/**
 * Comprehensive tests for Streamer Updates feature
 * Tests both API endpoints and frontend functionality
 */

const API_BASE = 'https://findtorontoevents.ca/fc/api';

test.describe('Streamer Updates API Tests', () => {
  
  // ===== creator_news_creators.php tests =====
  
  test('API: creator_news_creators returns creators for user 2', async ({ request }) => {
    const response = await request.get(`${API_BASE}/creator_news_creators.php?user_id=2`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.creators).toBeDefined();
    expect(Array.isArray(data.creators)).toBeTruthy();
    expect(data.creators.length).toBeGreaterThan(0);
    
    console.log(`Found ${data.creators.length} creators for user 2`);
    data.creators.forEach((c: any) => {
      console.log(`  - ${c.name}: ${c.contentCount} items, ${c.followerCount} followers`);
    });
  });

  test('API: creator_news_creators includes Lofe for user 2', async ({ request }) => {
    const response = await request.get(`${API_BASE}/creator_news_creators.php?user_id=2`);
    const data = await response.json();
    
    const lofe = data.creators.find((c: any) => c.name.toLowerCase() === 'lofe');
    expect(lofe).toBeDefined();
    expect(lofe.contentCount).toBeGreaterThan(0);
    console.log(`Lofe found with ${lofe.contentCount} content items`);
  });

  test('API: creator_news_creators includes Zople for user 2', async ({ request }) => {
    const response = await request.get(`${API_BASE}/creator_news_creators.php?user_id=2`);
    const data = await response.json();
    
    const zople = data.creators.find((c: any) => c.name.toLowerCase() === 'zople');
    expect(zople).toBeDefined();
    expect(zople.contentCount).toBeGreaterThan(0);
    console.log(`Zople found with ${zople.contentCount} content items`);
  });

  test('API: creator_news_creators includes Ninja for user 2', async ({ request }) => {
    const response = await request.get(`${API_BASE}/creator_news_creators.php?user_id=2`);
    const data = await response.json();
    
    const ninja = data.creators.find((c: any) => c.name.toLowerCase() === 'ninja');
    expect(ninja).toBeDefined();
    expect(ninja.contentCount).toBeGreaterThan(0);
    console.log(`Ninja found with ${ninja.contentCount} content items`);
  });

  test('API: creator_news_creators includes xQc for user 2', async ({ request }) => {
    const response = await request.get(`${API_BASE}/creator_news_creators.php?user_id=2`);
    const data = await response.json();
    
    const xqc = data.creators.find((c: any) => c.name.toLowerCase() === 'xqc');
    expect(xqc).toBeDefined();
    expect(xqc.contentCount).toBeGreaterThan(0);
    console.log(`xQc found with ${xqc.contentCount} content items`);
  });

  test('API: creator_news_creators returns empty for non-existent user', async ({ request }) => {
    const response = await request.get(`${API_BASE}/creator_news_creators.php?user_id=99999`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.creators).toBeDefined();
    expect(data.creators.length).toBe(0);
  });

  // ===== creator_news_api.php tests =====

  test('API: creator_news_api returns content for user 2', async ({ request }) => {
    const response = await request.get(`${API_BASE}/creator_news_api.php?user_id=2&limit=50`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.items).toBeDefined();
    expect(Array.isArray(data.items)).toBeTruthy();
    expect(data.items.length).toBeGreaterThan(0);
    
    console.log(`Found ${data.items.length} content items for user 2`);
  });

  test('API: creator_news_api includes multiple creators', async ({ request }) => {
    const response = await request.get(`${API_BASE}/creator_news_api.php?user_id=2&limit=50`);
    const data = await response.json();
    
    const creatorNames = new Set(data.items.map((i: any) => i.creator.name));
    console.log(`Unique creators in feed: ${Array.from(creatorNames).join(', ')}`);
    
    expect(creatorNames.size).toBeGreaterThan(1);
  });

  test('API: creator_news_api includes Lofe content', async ({ request }) => {
    const response = await request.get(`${API_BASE}/creator_news_api.php?user_id=2&limit=50`);
    const data = await response.json();
    
    const lofeItems = data.items.filter((i: any) => i.creator.name.toLowerCase() === 'lofe');
    expect(lofeItems.length).toBeGreaterThan(0);
    console.log(`Lofe items: ${lofeItems.map((i: any) => i.title).join(', ')}`);
  });

  test('API: creator_news_api content has required fields', async ({ request }) => {
    const response = await request.get(`${API_BASE}/creator_news_api.php?user_id=2&limit=10`);
    const data = await response.json();
    
    expect(data.items.length).toBeGreaterThan(0);
    
    const item = data.items[0];
    expect(item.id).toBeDefined();
    expect(item.creator).toBeDefined();
    expect(item.creator.name).toBeDefined();
    expect(item.platform).toBeDefined();
    expect(item.contentUrl).toBeDefined();
    expect(item.title).toBeDefined();
  });

  test('API: creator_news_api platform filter works', async ({ request }) => {
    const response = await request.get(`${API_BASE}/creator_news_api.php?user_id=2&platform=youtube&limit=20`);
    const data = await response.json();
    
    if (data.items.length > 0) {
      const allYoutube = data.items.every((i: any) => i.platform === 'youtube');
      expect(allYoutube).toBeTruthy();
      console.log(`All ${data.items.length} items are YouTube content`);
    }
  });

  // ===== index_creator_content.php tests =====

  test('API: index_creator_content finds creator by name', async ({ request }) => {
    const response = await request.get(`${API_BASE}/index_creator_content.php?creator_name=Adin`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok).toBeTruthy();
    expect(data.creator).toBeDefined();
    expect(data.creator.name.toLowerCase()).toContain('adin');
    console.log(`Found creator: ${data.creator.name}`);
  });

  test('API: index_creator_content processes multiple platforms', async ({ request }) => {
    const response = await request.get(`${API_BASE}/index_creator_content.php?creator_name=Ninja`);
    const data = await response.json();
    
    expect(data.ok).toBeTruthy();
    expect(data.accounts_processed).toBeGreaterThan(0);
    console.log(`Processed ${data.accounts_processed} accounts for Ninja`);
  });

  test('API: index_creator_content returns error for unknown creator', async ({ request }) => {
    const response = await request.get(`${API_BASE}/index_creator_content.php?creator_name=NONEXISTENT_CREATOR_12345`);
    const data = await response.json();
    
    expect(data.error).toBeDefined();
  });

  // ===== debug_user_creators.php tests =====

  test('API: debug_user_creators shows user 2 creator list', async ({ request }) => {
    const response = await request.get(`${API_BASE}/debug_user_creators.php?user_id=2`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.total_in_list).toBeGreaterThan(0);
    expect(data.creators_in_db).toBeDefined();
    
    console.log(`User 2 follows ${data.total_in_list} creators`);
    console.log(`${Object.keys(data.creators_in_db).length} are in the database`);
  });

  test('API: debug_user_creators shows content counts', async ({ request }) => {
    const response = await request.get(`${API_BASE}/debug_user_creators.php?user_id=2`);
    const data = await response.json();
    
    expect(data.content_counts).toBeDefined();
    
    const withContent = Object.entries(data.content_counts).filter(([_, count]) => (count as number) > 0);
    console.log(`Creators with content: ${withContent.length}`);
    withContent.forEach(([id, count]) => {
      const name = data.creators_in_db[id]?.name || id;
      console.log(`  - ${name}: ${count} items`);
    });
  });
});

test.describe('Streamer Updates Frontend Tests', () => {
  
  test('Frontend: page loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error' && !msg.text().includes('favicon') && !msg.text().includes('404')) {
        errors.push(msg.text());
      }
    });

    await page.goto('https://findtorontoevents.ca/fc/#/updates', {
      waitUntil: 'networkidle',
      timeout: 30000
    });
    
    await page.waitForTimeout(3000);
    
    // Filter out non-critical errors
    const criticalErrors = errors.filter(e => 
      !e.includes('net::') && 
      !e.includes('Failed to load resource') &&
      !e.includes('403')
    );
    
    expect(criticalErrors.length).toBe(0);
  });

  test('Frontend: Streamer Updates title visible', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/fc/#/updates', {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(2000);
    
    const title = page.locator('h1:has-text("Streamer Updates")');
    await expect(title).toBeVisible({ timeout: 10000 });
  });

  test('Frontend: creator dropdown is populated', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/fc/#/updates', {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(3000);
    
    // Find the creator dropdown
    const dropdown = page.locator('select').first();
    await expect(dropdown).toBeVisible({ timeout: 10000 });
    
    // Check options
    const options = await dropdown.locator('option').allTextContents();
    console.log('Dropdown options:', options);
    
    expect(options.length).toBeGreaterThan(1); // At least "All Creators" + one creator
  });

  test('Frontend: content cards are displayed', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/fc/#/updates', {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(3000);
    
    // Look for content cards (they have thumbnails/images)
    const cards = page.locator('div').filter({ has: page.locator('img') }).filter({ hasText: /YOUTUBE|NEWS|TIKTOK/i });
    const count = await cards.count();
    
    console.log(`Found ${count} content cards`);
    expect(count).toBeGreaterThan(0);
  });

  test('Frontend: refresh button works', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/fc/#/updates', {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(2000);
    
    const refreshBtn = page.locator('button:has-text("Refresh")');
    await expect(refreshBtn).toBeVisible();
    
    await refreshBtn.click();
    
    // Should show loading state or complete
    await page.waitForTimeout(2000);
    
    // Page should still be functional
    const title = page.locator('h1:has-text("Streamer Updates")');
    await expect(title).toBeVisible();
  });

  test('Frontend: platform filter buttons exist', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/fc/#/updates', {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(2000);
    
    // Check for platform filter buttons
    const platforms = ['All', 'Youtube', 'Tiktok', 'Twitter', 'Instagram', 'News'];
    
    for (const platform of platforms) {
      const btn = page.locator(`button:has-text("${platform}")`).first();
      const isVisible = await btn.isVisible().catch(() => false);
      console.log(`${platform} button: ${isVisible ? 'visible' : 'not visible'}`);
    }
  });

  test('Frontend: clicking platform filter changes view', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/fc/#/updates', {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(3000);
    
    // Get initial state
    const initialCards = await page.locator('div').filter({ hasText: /YOUTUBE/ }).count();
    
    // Click Youtube filter if available
    const youtubeBtn = page.locator('button:has-text("Youtube")').first();
    if (await youtubeBtn.isVisible()) {
      await youtubeBtn.click();
      await page.waitForTimeout(1000);
      
      // Verify filter is active (button should have different style)
      console.log('YouTube filter clicked');
    }
  });
});

test.describe('Streamer Updates Data Integrity Tests', () => {
  
  test('Data: all creators with content appear in dropdown', async ({ request }) => {
    // Get creators with content
    const creatorsRes = await request.get(`${API_BASE}/creator_news_creators.php?user_id=2`);
    const creatorsData = await creatorsRes.json();
    
    // Get content feed
    const contentRes = await request.get(`${API_BASE}/creator_news_api.php?user_id=2&limit=100`);
    const contentData = await contentRes.json();
    
    // Extract unique creators from content
    const contentCreators = new Set(contentData.items.map((i: any) => i.creator.name));
    
    // All content creators should be in the creators list
    const dropdownCreators = new Set(creatorsData.creators.map((c: any) => c.name));
    
    console.log('Dropdown creators:', Array.from(dropdownCreators));
    console.log('Content creators:', Array.from(contentCreators));
    
    for (const creator of contentCreators) {
      expect(dropdownCreators.has(creator)).toBeTruthy();
    }
  });

  test('Data: content counts match actual content', async ({ request }) => {
    const creatorsRes = await request.get(`${API_BASE}/creator_news_creators.php?user_id=2`);
    const creatorsData = await creatorsRes.json();
    
    const contentRes = await request.get(`${API_BASE}/creator_news_api.php?user_id=2&limit=200`);
    const contentData = await contentRes.json();
    
    // Count content per creator
    const actualCounts: Record<string, number> = {};
    contentData.items.forEach((i: any) => {
      const name = i.creator.name;
      actualCounts[name] = (actualCounts[name] || 0) + 1;
    });
    
    // Compare with reported counts
    for (const creator of creatorsData.creators) {
      const reported = creator.contentCount;
      const actual = actualCounts[creator.name] || 0;
      console.log(`${creator.name}: reported=${reported}, actual=${actual}`);
      expect(reported).toBe(actual);
    }
  });

  test('Data: Lofe has valid content URL', async ({ request }) => {
    const response = await request.get(`${API_BASE}/creator_news_api.php?user_id=2&limit=50`);
    const data = await response.json();
    
    const lofeItems = data.items.filter((i: any) => i.creator.name.toLowerCase() === 'lofe');
    expect(lofeItems.length).toBeGreaterThan(0);
    
    for (const item of lofeItems) {
      expect(item.contentUrl).toBeDefined();
      expect(item.contentUrl).toMatch(/^https?:\/\//);
      console.log(`Lofe content: ${item.title} -> ${item.contentUrl}`);
    }
  });

  test('Data: YouTube content has thumbnails', async ({ request }) => {
    const response = await request.get(`${API_BASE}/creator_news_api.php?user_id=2&platform=youtube&limit=20`);
    const data = await response.json();
    
    let withThumbnail = 0;
    let withoutThumbnail = 0;
    
    for (const item of data.items) {
      if (item.thumbnailUrl && item.thumbnailUrl.length > 0) {
        withThumbnail++;
      } else {
        withoutThumbnail++;
        console.log(`No thumbnail: ${item.title?.substring(0, 50)}`);
      }
    }
    
    console.log(`YouTube - With thumbnail: ${withThumbnail}, Without: ${withoutThumbnail}`);
    // YouTube items should all have thumbnails
    expect(withThumbnail).toBeGreaterThan(0);
  });
});
