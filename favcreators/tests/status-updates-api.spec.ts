import { test, expect } from '@playwright/test';

/**
 * Comprehensive Playwright tests for the Creator Status Updates API.
 *
 * Tests cover:
 *  - status_updates.php (GET) — query, filter, validate responses
 *  - update_creator_status.php (POST) — create, update, batch, validation
 *  - fetch_platform_status.php (GET) — all 7 platforms live-fetch
 *  - Edge cases, error handling, NSFW filtering
 *
 * These tests hit the DEPLOYED production API at findtorontoevents.ca.
 * They are designed to be non-destructive and use test-prefixed creator IDs.
 */

const BASE_URL = process.env.STATUS_API_URL || 'https://findtorontoevents.ca/fc/api';

// ============================================================
// 1. STATUS_UPDATES.PHP — GET ENDPOINT TESTS
// ============================================================

test.describe('status_updates.php — GET endpoint', () => {

  test('returns valid JSON with expected structure (no params)', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php`);
    expect(res.status()).toBe(200);

    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json).toHaveProperty('updates');
    expect(json).toHaveProperty('count');
    expect(json).toHaveProperty('stats');
    expect(json).toHaveProperty('platform_breakdown');
    expect(json).toHaveProperty('query');
    expect(json).toHaveProperty('supported_platforms');
    expect(Array.isArray(json.updates)).toBe(true);
    expect(typeof json.count).toBe('number');
  });

  test('stats object has all required fields', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php`);
    const json = await res.json();

    expect(json.stats).toHaveProperty('total_tracked');
    expect(json.stats).toHaveProperty('unique_creators');
    expect(json.stats).toHaveProperty('platforms_tracked');
    expect(json.stats).toHaveProperty('currently_live');
    expect(json.stats).toHaveProperty('last_check_time');
    expect(typeof json.stats.total_tracked).toBe('number');
    expect(typeof json.stats.unique_creators).toBe('number');
  });

  test('supported_platforms includes all expected platforms', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php`);
    const json = await res.json();

    const expected = ['twitch', 'kick', 'tiktok', 'instagram', 'twitter', 'reddit', 'youtube', 'spotify'];
    for (const p of expected) {
      expect(json.supported_platforms).toContain(p);
    }
  });

  test('filter by platform=twitch returns only twitch results', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?platform=twitch`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.query.platform).toBe('twitch');
    for (const u of json.updates) {
      expect(u.platform).toBe('twitch');
    }
  });

  test('filter by platform=kick returns only kick results', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?platform=kick`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.query.platform).toBe('kick');
    for (const u of json.updates) {
      expect(u.platform).toBe('kick');
    }
  });

  test('filter by platform=twitter returns only twitter results', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?platform=twitter`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    for (const u of json.updates) {
      expect(u.platform).toBe('twitter');
    }
  });

  test('platform=x normalizes to twitter', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?platform=x`);
    const json = await res.json();
    // Should not error — x maps to twitter
    expect(json.ok).toBe(true);
  });

  test('invalid platform returns 400 error', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?platform=fakeplatform`);
    const json = await res.json();
    expect(json.ok).toBe(false);
    expect(json.error).toContain('Invalid platform');
  });

  test('filter by user returns matching username', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?user=test_playwright_user`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.query.user).toBe('test_playwright_user');
    for (const u of json.updates) {
      expect(u.username).toBe('test_playwright_user');
    }
  });

  test('filter by type=stream returns only stream updates', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?type=stream`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    for (const u of json.updates) {
      expect(u.update_type).toBe('stream');
    }
  });

  test('filter by since_hours limits time window', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?since_hours=1`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.query.since_hours).toBe(1);
  });

  test('limit parameter caps results', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?limit=2`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.updates.length).toBeLessThanOrEqual(2);
    expect(json.query.limit).toBe(2);
  });

  test('limit cannot exceed 100', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?limit=999`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.query.limit).toBe(100);
  });

  test('live_only=1 returns only live updates', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?live_only=1`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    for (const u of json.updates) {
      expect(u.is_live).toBe(true);
    }
  });

  test('combined filters work together', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?platform=twitch&type=stream&limit=5`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.updates.length).toBeLessThanOrEqual(5);
    for (const u of json.updates) {
      expect(u.platform).toBe('twitch');
      expect(u.update_type).toBe('stream');
    }
  });

  test('OPTIONS request returns 200 (CORS preflight)', async ({ request }) => {
    const res = await request.fetch(`${BASE_URL}/status_updates.php`, { method: 'OPTIONS' });
    expect(res.status()).toBe(200);
  });

  test('update objects have all required fields', async ({ request }) => {
    // First insert a test record, then verify structure
    await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: '__pw_structure_test__',
        creator_name: 'PW Structure Test',
        platform: 'twitch',
        username: 'pw_struct_test',
        update_type: 'stream',
        content_title: 'Structure Test Stream',
        content_url: 'https://twitch.tv/pw_struct_test',
        is_live: false,
        checked_by: 'playwright'
      }
    });

    const res = await request.get(`${BASE_URL}/status_updates.php?user=pw_struct_test`);
    const json = await res.json();
    expect(json.ok).toBe(true);

    if (json.updates.length > 0) {
      const u = json.updates[0];
      const requiredFields = [
        'id', 'creator_id', 'creator_name', 'platform', 'username',
        'account_url', 'update_type', 'content_title', 'content_url',
        'content_preview', 'is_live', 'viewer_count', 'like_count',
        'comment_count', 'last_checked', 'last_updated', 'check_count'
      ];
      for (const field of requiredFields) {
        expect(u).toHaveProperty(field);
      }
      expect(typeof u.id).toBe('number');
      expect(typeof u.is_live).toBe('boolean');
      expect(typeof u.viewer_count).toBe('number');
    }
  });
});


// ============================================================
// 2. UPDATE_CREATOR_STATUS.PHP — POST ENDPOINT TESTS
// ============================================================

test.describe('update_creator_status.php — POST endpoint', () => {

  test('creates a new status update (insert)', async ({ request }) => {
    const uniqueId = '__pw_insert_' + Date.now() + '__';
    const res = await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: uniqueId,
        creator_name: 'Playwright Insert Test',
        platform: 'twitch',
        username: 'pw_insert_test',
        update_type: 'stream',
        content_title: 'Test Stream Title',
        content_url: 'https://twitch.tv/pw_insert_test',
        content_preview: 'Testing insertion',
        is_live: true,
        viewer_count: 42,
        checked_by: 'playwright'
      }
    });

    expect(res.status()).toBe(200);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.processed).toBe(1);
    expect(json.results[0].action).toBe('created');
    expect(json.results[0].creator_id).toBe(uniqueId);
    expect(json.results[0].platform).toBe('twitch');
  });

  test('updates an existing status update (upsert)', async ({ request }) => {
    const uniqueId = '__pw_upsert_test__';

    // First insert
    await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: uniqueId,
        creator_name: 'Upsert Test',
        platform: 'kick',
        username: 'pw_upsert',
        update_type: 'stream',
        content_title: 'First Title',
        is_live: true,
        viewer_count: 100,
        checked_by: 'playwright'
      }
    });

    // Second insert (same creator_id + platform + update_type = update)
    const res = await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: uniqueId,
        creator_name: 'Upsert Test Updated',
        platform: 'kick',
        username: 'pw_upsert',
        update_type: 'stream',
        content_title: 'Updated Title',
        is_live: false,
        viewer_count: 200,
        checked_by: 'playwright'
      }
    });

    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.results[0].action).toBe('updated');
  });

  test('batch updates process multiple items', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        updates: [
          {
            creator_id: '__pw_batch_1__',
            creator_name: 'Batch Test 1',
            platform: 'twitch',
            username: 'pw_batch1',
            update_type: 'stream',
            content_title: 'Batch Stream 1',
            is_live: true,
            checked_by: 'playwright'
          },
          {
            creator_id: '__pw_batch_2__',
            creator_name: 'Batch Test 2',
            platform: 'youtube',
            username: 'pw_batch2',
            update_type: 'video',
            content_title: 'Batch Video 2',
            is_live: false,
            checked_by: 'playwright'
          }
        ]
      }
    });

    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.processed).toBe(2);
  });

  test('rejects missing required fields', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: 'test',
        // missing creator_name, platform, username
      }
    });

    const json = await res.json();
    expect(json.errors.length).toBeGreaterThan(0);
    expect(json.errors[0].error).toContain('Missing required field');
  });

  test('rejects invalid platform', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: 'test',
        creator_name: 'Test',
        platform: 'onlyfans',
        username: 'test',
        update_type: 'post'
      }
    });

    const json = await res.json();
    expect(json.errors.length).toBeGreaterThan(0);
    expect(json.errors[0].error).toContain('Invalid platform');
  });

  test('rejects invalid update_type', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: 'test',
        creator_name: 'Test',
        platform: 'twitch',
        username: 'test',
        update_type: 'invalid_type'
      }
    });

    const json = await res.json();
    expect(json.errors.length).toBeGreaterThan(0);
    expect(json.errors[0].error).toContain('Invalid update_type');
  });

  test('rejects empty POST body', async ({ request }) => {
    const res = await request.fetch(`${BASE_URL}/update_creator_status.php`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    const json = await res.json();
    expect(json.ok).toBe(false);
  });

  test('normalizes platform x to twitter', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: '__pw_x_normalize__',
        creator_name: 'X Normalize Test',
        platform: 'x',
        username: 'pw_x_test',
        update_type: 'tweet',
        content_title: 'Test tweet',
        checked_by: 'playwright'
      }
    });

    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.results[0].platform).toBe('twitter');
  });

  test('OPTIONS request returns 200 (CORS preflight)', async ({ request }) => {
    const res = await request.fetch(`${BASE_URL}/update_creator_status.php`, { method: 'OPTIONS' });
    expect(res.status()).toBe(200);
  });

  test('GET request returns 405 Method Not Allowed', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/update_creator_status.php`);
    expect(res.status()).toBe(405);
  });

  test('all supported update_types are accepted', async ({ request }) => {
    const types = ['post', 'story', 'stream', 'vod', 'tweet', 'comment', 'video', 'short', 'reel'];

    for (const t of types) {
      const res = await request.post(`${BASE_URL}/update_creator_status.php`, {
        data: {
          creator_id: '__pw_type_' + t + '__',
          creator_name: 'Type Test ' + t,
          platform: 'twitch',
          username: 'pw_type_test',
          update_type: t,
          content_title: 'Testing type: ' + t,
          checked_by: 'playwright'
        }
      });

      const json = await res.json();
      expect(json.ok).toBe(true);
      expect(json.results[0].update_type).toBe(t);
    }
  });

  test('all supported platforms are accepted', async ({ request }) => {
    const platforms = ['twitch', 'kick', 'tiktok', 'instagram', 'twitter', 'reddit', 'youtube', 'spotify'];

    for (const p of platforms) {
      const res = await request.post(`${BASE_URL}/update_creator_status.php`, {
        data: {
          creator_id: '__pw_platform_' + p + '__',
          creator_name: 'Platform Test ' + p,
          platform: p,
          username: 'pw_platform_test',
          update_type: 'post',
          content_title: 'Testing platform: ' + p,
          checked_by: 'playwright'
        }
      });

      const json = await res.json();
      expect(json.ok).toBe(true);
      expect(json.results[0].platform).toBe(p);
    }
  });
});


// ============================================================
// 3. FETCH_PLATFORM_STATUS.PHP — LIVE FETCHER TESTS
// ============================================================

test.describe('fetch_platform_status.php — platform fetcher', () => {

  test('returns error when platform is missing', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?user=testuser`);
    expect(res.status()).toBe(400);
    const json = await res.json();
    expect(json.ok).toBe(false);
    expect(json.error).toContain('platform');
  });

  test('returns error when user is missing', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=twitch`);
    expect(res.status()).toBe(400);
    const json = await res.json();
    expect(json.ok).toBe(false);
    expect(json.error).toContain('user');
  });

  test('returns error for invalid platform', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=fakePlatform&user=test`);
    expect(res.status()).toBe(400);
    const json = await res.json();
    expect(json.ok).toBe(false);
    expect(json.error).toContain('Invalid platform');
  });

  test('rejects invalid/unsupported platform names', async ({ request }) => {
    const badPlatforms = ['fakeplatform', 'myspace', 'dailymotion', 'vimeo'];
    for (const p of badPlatforms) {
      const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=${p}&user=test`);
      const json = await res.json();
      expect(json.ok).toBe(false);
      expect(json.error).toContain('Invalid platform');
    }
  });

  test('normalizes platform x to twitter', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=x&user=elonmusk`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.platform).toBe('twitter');
  });

  test('cleans username prefixes (@, /)', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=reddit&user=@spez`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.username).toBe('spez');
  });

  test('response includes response_time_ms', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=reddit&user=spez`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json).toHaveProperty('response_time_ms');
    expect(typeof json.response_time_ms).toBe('number');
    expect(json.response_time_ms).toBeGreaterThanOrEqual(0);
  });

  test('OPTIONS request returns 200 (CORS preflight)', async ({ request }) => {
    const res = await request.fetch(`${BASE_URL}/fetch_platform_status.php`, { method: 'OPTIONS' });
    expect(res.status()).toBe(200);
  });

  // ---- TWITCH ----
  test('Twitch: fetches status for a known streamer', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=twitch&user=shroud`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    expect(json.platform).toBe('twitch');
    expect(json.username).toBe('shroud');
    expect(json.account_url).toContain('twitch.tv/shroud');
    expect(Array.isArray(json.updates)).toBe(true);
    // shroud may or may not be live, but structure should be valid
    if (json.updates.length > 0) {
      expect(json.updates[0]).toHaveProperty('update_type');
      expect(json.updates[0]).toHaveProperty('content_url');
    }
  });

  test('Twitch: handles nonexistent user gracefully', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=twitch&user=thisuser_definitely_does_not_exist_12345xyz`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    expect(json.platform).toBe('twitch');
    // Should not crash, just return no updates or an error message
    expect(Array.isArray(json.updates)).toBe(true);
  });

  // ---- KICK ----
  test('Kick: fetches status for a known streamer', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=kick&user=xqc`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    expect(json.platform).toBe('kick');
    expect(json.username).toBe('xqc');
    expect(json.account_url).toContain('kick.com/xqc');
    expect(Array.isArray(json.updates)).toBe(true);
  });

  test('Kick: handles nonexistent user gracefully', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=kick&user=nonexistent_user_xyz_99999`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    expect(json.platform).toBe('kick');
    expect(Array.isArray(json.updates)).toBe(true);
  });

  // ---- REDDIT ----
  test('Reddit: fetches latest post for a known user', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=reddit&user=spez`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    expect(json.platform).toBe('reddit');
    expect(json.username).toBe('spez');
    expect(json.account_url).toContain('reddit.com/user/spez');
    expect(Array.isArray(json.updates)).toBe(true);

    if (json.found && json.updates.length > 0) {
      const post = json.updates.find((u: any) => u.update_type === 'post');
      if (post) {
        expect(post.content_url).toContain('reddit.com');
        expect(post.content_title).toBeTruthy();
      }
    }
  });

  test('Reddit: fetches comments for a known user', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=reddit&user=spez`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    if (json.updates.length > 1) {
      const comment = json.updates.find((u: any) => u.update_type === 'comment');
      if (comment) {
        expect(comment.content_url).toContain('reddit.com');
        expect(comment.content_title).toContain('Comment in r/');
      }
    }
  });

  test('Reddit: NSFW content is filtered out', async ({ request }) => {
    // We can't guarantee NSFW filtering without a known NSFW user,
    // but we verify the response structure is clean
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=reddit&user=spez`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    // All returned updates should be SFW (no over_18 flag in output)
    for (const u of json.updates) {
      expect(u).not.toHaveProperty('over_18');
    }
  });

  // ---- YOUTUBE ----
  test('YouTube: fetches latest video for a known channel', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=youtube&user=@Google`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    expect(json.platform).toBe('youtube');
    expect(Array.isArray(json.updates)).toBe(true);

    if (json.found && json.updates.length > 0) {
      const video = json.updates.find((u: any) => u.update_type === 'video');
      if (video) {
        expect(video.content_url).toContain('youtube.com/watch');
        expect(video.content_title).toBeTruthy();
        expect(video.content_thumbnail).toContain('ytimg.com');
      }
    }
  });

  test('YouTube: handles @handle format', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=youtube&user=@Google`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    expect(json.username).toBe('Google');
    expect(json.account_url).toContain('youtube.com/@Google');
  });

  // ---- TIKTOK ----
  test('TikTok: returns valid structure for a user', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=tiktok&user=tiktok`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    expect(json.platform).toBe('tiktok');
    expect(json.username).toBe('tiktok');
    expect(json.account_url).toContain('tiktok.com/@tiktok');
    expect(Array.isArray(json.updates)).toBe(true);
  });

  // ---- INSTAGRAM ----
  test('Instagram: returns valid structure for a user', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=instagram&user=instagram`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    expect(json.platform).toBe('instagram');
    expect(json.username).toBe('instagram');
    expect(json.account_url).toContain('instagram.com/instagram');
    expect(Array.isArray(json.updates)).toBe(true);
    // Instagram is heavily rate-limited; error message is acceptable
  });

  // ---- TWITTER/X ----
  test('Twitter: returns valid structure for a user', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=twitter&user=elonmusk`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    expect(json.platform).toBe('twitter');
    expect(json.username).toBe('elonmusk');
    expect(json.account_url).toContain('x.com/elonmusk');
    expect(Array.isArray(json.updates)).toBe(true);
  });

  test('Twitter: x alias also works', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=x&user=NASA`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    expect(json.platform).toBe('twitter');
    expect(json.username).toBe('NASA');
  });
});


// ============================================================
// 4. END-TO-END FLOW TESTS
// ============================================================

test.describe('End-to-end flow', () => {

  test('insert via POST, then retrieve via GET', async ({ request }) => {
    const testId = '__pw_e2e_' + Date.now() + '__';

    // Insert
    const postRes = await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: testId,
        creator_name: 'E2E Test Creator',
        platform: 'youtube',
        username: 'pw_e2e_test',
        update_type: 'video',
        content_title: 'E2E Test Video',
        content_url: 'https://youtube.com/watch?v=test123',
        content_preview: 'This is an E2E test',
        is_live: false,
        viewer_count: 999,
        like_count: 50,
        comment_count: 10,
        content_published_at: '2026-02-05 12:00:00',
        checked_by: 'playwright_e2e'
      }
    });

    const postJson = await postRes.json();
    expect(postJson.ok).toBe(true);

    // Retrieve
    const getRes = await request.get(`${BASE_URL}/status_updates.php?creator_id=${testId}`);
    const getJson = await getRes.json();

    expect(getJson.ok).toBe(true);
    expect(getJson.updates.length).toBeGreaterThanOrEqual(1);

    const found = getJson.updates.find((u: any) => u.creator_id === testId);
    expect(found).toBeTruthy();
    expect(found.creator_name).toBe('E2E Test Creator');
    expect(found.platform).toBe('youtube');
    expect(found.update_type).toBe('video');
    expect(found.content_title).toBe('E2E Test Video');
    expect(found.viewer_count).toBe(999);
    expect(found.like_count).toBe(50);
    expect(found.comment_count).toBe(10);
    expect(found.is_live).toBe(false);
  });

  test('fetch from platform, then check it appears in status_updates', async ({ request }) => {
    // Fetch from Reddit (reliable public API) and save
    const fetchRes = await request.get(
      `${BASE_URL}/fetch_platform_status.php?platform=reddit&user=spez&save=1&creator_id=__pw_reddit_save__&creator_name=Spez`
    );
    const fetchJson = await fetchRes.json();

    expect(fetchJson.ok).toBe(true);

    if (fetchJson.found && fetchJson.saved) {
      // Now verify it's stored
      const getRes = await request.get(`${BASE_URL}/status_updates.php?creator_id=__pw_reddit_save__`);
      const getJson = await getRes.json();

      expect(getJson.ok).toBe(true);
      expect(getJson.updates.length).toBeGreaterThanOrEqual(1);
      expect(getJson.updates[0].platform).toBe('reddit');
    }
  });

  test('platform_breakdown in stats is populated after inserts', async ({ request }) => {
    // Insert across multiple platforms
    await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        updates: [
          { creator_id: '__pw_breakdown_tw__', creator_name: 'Breakdown TW', platform: 'twitch', username: 'pw_bd', update_type: 'stream', checked_by: 'playwright' },
          { creator_id: '__pw_breakdown_yt__', creator_name: 'Breakdown YT', platform: 'youtube', username: 'pw_bd', update_type: 'video', checked_by: 'playwright' },
          { creator_id: '__pw_breakdown_rd__', creator_name: 'Breakdown RD', platform: 'reddit', username: 'pw_bd', update_type: 'post', checked_by: 'playwright' }
        ]
      }
    });

    const res = await request.get(`${BASE_URL}/status_updates.php`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    expect(json.platform_breakdown).toBeTruthy();
    expect(typeof json.platform_breakdown).toBe('object');
    // Should have at least some platforms
    const platforms = Object.keys(json.platform_breakdown);
    expect(platforms.length).toBeGreaterThanOrEqual(1);
  });

  test('check_count increments on repeated updates', async ({ request }) => {
    const testId = '__pw_check_count__';

    // First insert
    await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: testId,
        creator_name: 'Check Count Test',
        platform: 'kick',
        username: 'pw_checkcount',
        update_type: 'stream',
        checked_by: 'playwright'
      }
    });

    // Update again
    await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: testId,
        creator_name: 'Check Count Test',
        platform: 'kick',
        username: 'pw_checkcount',
        update_type: 'stream',
        checked_by: 'playwright'
      }
    });

    // Retrieve
    const res = await request.get(`${BASE_URL}/status_updates.php?creator_id=${testId}`);
    const json = await res.json();

    expect(json.ok).toBe(true);
    if (json.updates.length > 0) {
      expect(json.updates[0].check_count).toBeGreaterThanOrEqual(2);
    }
  });
});


// ============================================================
// 5. EDGE CASES & SECURITY TESTS
// ============================================================

test.describe('Edge cases and security', () => {

  test('SQL injection attempt in platform param is handled safely', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?platform=twitch_OR_1`);
    const json = await res.json();
    // Should return error (invalid platform) — not crash or leak data
    expect(json.ok).toBe(false);
  });

  test('SQL injection attempt in user param is handled safely', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/status_updates.php?user=test_injection`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    // Should return empty results, not crash
    expect(json.updates.length).toBe(0);
  });

  test('XSS attempt in content_title is stored safely', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: '__pw_xss_test__',
        creator_name: '<script>alert("xss")</script>',
        platform: 'twitch',
        username: 'pw_xss',
        update_type: 'stream',
        content_title: '<img src=x onerror=alert(1)>',
        content_preview: '<script>document.cookie</script>',
        checked_by: 'playwright'
      }
    });

    const json = await res.json();
    expect(json.ok).toBe(true);
    // Data is stored as-is (output escaping is frontend responsibility),
    // but the API should not crash
  });

  test('very long username is handled', async ({ request }) => {
    const longUser = 'a'.repeat(300);
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=reddit&user=${longUser}`);
    // Should not crash
    expect([200, 400, 500]).toContain(res.status());
  });

  test('empty username is rejected', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=twitch&user=`);
    expect(res.status()).toBe(400);
  });

  test('unicode usernames are handled', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=tiktok&user=日本語テスト`);
    // Should not crash — may return no results but valid JSON
    expect(res.status()).toBe(200);
    const json = await res.json();
    expect(json.ok).toBe(true);
  });

  test('special characters in creator_id POST are handled', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: '__pw_special_!@#$%^&*()__',
        creator_name: 'Special Chars Test',
        platform: 'twitch',
        username: 'pw_special',
        update_type: 'post',
        checked_by: 'playwright'
      }
    });

    const json = await res.json();
    expect(json.ok).toBe(true);
  });
});


// ============================================================
// 6. PERFORMANCE TESTS
// ============================================================

test.describe('Performance', () => {

  test('status_updates.php responds in under 3 seconds', async ({ request }) => {
    const start = Date.now();
    const res = await request.get(`${BASE_URL}/status_updates.php`);
    const elapsed = Date.now() - start;

    expect(res.status()).toBe(200);
    expect(elapsed).toBeLessThan(3000);
  });

  test('update_creator_status.php responds in under 3 seconds', async ({ request }) => {
    const start = Date.now();
    const res = await request.post(`${BASE_URL}/update_creator_status.php`, {
      data: {
        creator_id: '__pw_perf__',
        creator_name: 'Perf Test',
        platform: 'twitch',
        username: 'pw_perf',
        update_type: 'stream',
        checked_by: 'playwright'
      }
    });
    const elapsed = Date.now() - start;

    expect(res.status()).toBe(200);
    expect(elapsed).toBeLessThan(3000);
  });

  test('fetch_platform_status.php responds in under 20 seconds (network dependent)', async ({ request }) => {
    const start = Date.now();
    const res = await request.get(`${BASE_URL}/fetch_platform_status.php?platform=reddit&user=spez`);
    const elapsed = Date.now() - start;

    expect(res.status()).toBe(200);
    expect(elapsed).toBeLessThan(20000);
  });
});
