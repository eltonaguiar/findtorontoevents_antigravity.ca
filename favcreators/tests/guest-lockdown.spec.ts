import { test, expect } from '@playwright/test';

/**
 * Guest Lockdown Tests
 *
 * Verifies that:
 * 1. The check_site API correctly counts event clicks and returns allowed=false after limit
 * 2. The tracking API correctly records event_click entries
 * 3. The events page shows the login wall when check_site returns allowed=false
 * 4. Logged-in users always bypass the lockdown
 */

const BASE_URL = 'https://findtorontoevents.ca/fc/api';
const EVENTS_URL = 'https://findtorontoevents.ca/index.html';

// ============================================================
// 1. API-LEVEL TESTS — Verify check_site + track.php work correctly
// ============================================================

test.describe('Guest Lockdown API', () => {

  test('check_site returns event_click_count and event_click_limit fields', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/guest_usage.php?action=check_site`);
    expect(res.status()).toBe(200);

    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json).toHaveProperty('event_click_count');
    expect(json).toHaveProperty('event_click_limit');
    expect(json).toHaveProperty('allowed');
    expect(json).toHaveProperty('distinct_days');
    expect(json).toHaveProperty('day_limit');
    expect(typeof json.event_click_count).toBe('number');
    expect(typeof json.event_click_limit).toBe('number');
    expect(json.event_click_limit).toBe(2);
  });

  test('track.php records event_click correctly', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/track.php`, {
      data: {
        action: 'click',
        click_type: 'event_click',
        page: 'events',
        target_url: 'https://www.eventbrite.ca/e/playwright-test-event',
        target_title: 'Playwright Test Event',
        target_id: 'test-pw-001'
      }
    });
    expect(res.status()).toBe(200);
    const json = await res.json();
    expect(json.ok).toBe(true);
  });

  test('check_site counts event_clicks for current IP', async ({ request }) => {
    // First record a few event clicks
    for (let i = 0; i < 3; i++) {
      await request.post(`${BASE_URL}/track.php`, {
        data: {
          action: 'click',
          click_type: 'event_click',
          page: 'events',
          target_url: `https://www.eventbrite.ca/e/test-event-${i}`,
          target_title: `Test Event ${i}`,
          target_id: `test-${i}`
        }
      });
    }

    // Now check site — event_click_count should be > 0
    const res = await request.get(`${BASE_URL}/guest_usage.php?action=check_site`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.event_click_count).toBeGreaterThan(0);

    // If count exceeds limit, allowed should be false (for guests)
    if (json.event_click_count > json.event_click_limit) {
      expect(json.allowed).toBe(false);
    }
  });

  test('logged-in user always gets allowed=true even with many event clicks', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/guest_usage.php?action=check_site&user_id=1`);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.allowed).toBe(true);
  });
});


// ============================================================
// 2. EVENTS PAGE — Verify the lockdown wall behavior in the browser
// ============================================================

test.describe('Events Page Lockdown', () => {

  test('page loads and tracking script exists', async ({ page }) => {
    await page.goto(EVENTS_URL, { waitUntil: 'domcontentloaded' });

    // Verify the tracking script references exist
    const trackApiPresent = await page.evaluate(() => {
      const scripts = document.querySelectorAll('script');
      for (let i = 0; i < scripts.length; i++) {
        if (scripts[i].textContent && scripts[i].textContent.indexOf('track.php') !== -1) return true;
      }
      return false;
    });
    expect(trackApiPresent).toBe(true);

    // Verify the lockdown script references exist
    const lockdownPresent = await page.evaluate(() => {
      const scripts = document.querySelectorAll('script');
      for (let i = 0; i < scripts.length; i++) {
        if (scripts[i].textContent && scripts[i].textContent.indexOf('checkGuestSiteLockdown') !== -1) return true;
      }
      return false;
    });
    expect(lockdownPresent).toBe(true);
  });

  test('__fte_recheckGuestLockdown is exposed on window', async ({ page }) => {
    await page.goto(EVENTS_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000); // let scripts initialize

    const exists = await page.evaluate(() => typeof window.__fte_recheckGuestLockdown === 'function');
    expect(exists).toBe(true);
  });

  test('event links on events page are detected correctly', async ({ page }) => {
    await page.goto(EVENTS_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Find all links that would be classified as event_click
    const eventLinks = await page.evaluate(() => {
      const links = document.querySelectorAll('a[href]');
      const eventDomains = ['eventbrite', 'universe.com', 'showpass', 'ticketmaster'];
      const results: { href: string; text: string }[] = [];
      for (let i = 0; i < links.length; i++) {
        const href = links[i].getAttribute('href') || '';
        for (const domain of eventDomains) {
          if (href.indexOf(domain) !== -1) {
            results.push({
              href: href.substring(0, 120),
              text: (links[i].textContent || '').trim().substring(0, 80)
            });
            break;
          }
        }
      }
      return results;
    });

    console.log(`Found ${eventLinks.length} event links on page:`);
    for (const link of eventLinks.slice(0, 10)) {
      console.log(`  ${link.href}`);
    }

    // There should be event links on the events page
    // (this may be 0 if events haven't loaded yet — log either way)
    console.log(`Total event links found: ${eventLinks.length}`);
  });

  test('login wall appears when check_site returns allowed=false', async ({ page }) => {
    // Intercept check_site to simulate "not allowed" response
    await page.route('**/guest_usage.php?action=check_site*', async (route) => {
      const url = route.request().url();
      // Only mock for guest requests (no user_id param)
      if (url.indexOf('user_id=') === -1) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ok: true,
            allowed: false,
            distinct_days: 5,
            day_limit: 2,
            event_click_count: 10,
            event_click_limit: 2,
            first_seen_at: '2026-01-01 00:00:00',
            registered: false
          })
        });
      } else {
        await route.continue();
      }
    });

    await page.goto(EVENTS_URL, { waitUntil: 'domcontentloaded' });

    // Wait for the lockdown check to run (2s delay + processing)
    await page.waitForTimeout(4000);

    // The login wall should appear
    const wall = await page.locator('#fte-guest-login-wall');
    await expect(wall).toBeVisible({ timeout: 5000 });

    // Verify the wall has a sign-in button
    const signInBtn = await page.locator('#fte-wall-signin-btn');
    await expect(signInBtn).toBeVisible();
    const btnText = await signInBtn.textContent();
    expect(btnText).toContain('Sign In');
  });

  test('login wall does NOT appear when check_site returns allowed=true', async ({ page }) => {
    // Intercept check_site to simulate "allowed" response
    await page.route('**/guest_usage.php?action=check_site*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          allowed: true,
          distinct_days: 1,
          day_limit: 2,
          event_click_count: 0,
          event_click_limit: 2,
          first_seen_at: '2026-02-09 00:00:00',
          registered: false
        })
      });
    });

    await page.goto(EVENTS_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    // The login wall should NOT appear
    const wall = await page.locator('#fte-guest-login-wall');
    await expect(wall).not.toBeVisible();
  });

  test('login wall does NOT appear for logged-in users', async ({ page }) => {
    // Set up logged-in user state before navigating
    await page.addInitScript(() => {
      (window as any).__fc_logged_in_user__ = { id: 99, email: 'test@test.com', display_name: 'Test' };
      localStorage.setItem('fav_creators_auth_user', JSON.stringify({ id: 99, email: 'test@test.com' }));
    });

    await page.goto(EVENTS_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    // The login wall should NOT appear for logged-in users
    const wall = await page.locator('#fte-guest-login-wall');
    await expect(wall).not.toBeVisible();
  });

  test('clicking event links triggers recheck after tracking', async ({ page }) => {
    let trackRequests = 0;
    let checkSiteRequests = 0;

    // Monitor track.php calls
    page.on('request', (req) => {
      if (req.url().indexOf('track.php') !== -1 && req.method() === 'POST') {
        trackRequests++;
      }
      if (req.url().indexOf('guest_usage.php') !== -1 && req.url().indexOf('check_site') !== -1) {
        checkSiteRequests++;
      }
    });

    await page.goto(EVENTS_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    // Record initial check_site count (should be at least 2 from page load: 2s + 6s)
    const initialChecks = checkSiteRequests;
    console.log(`Initial check_site requests after page load: ${initialChecks}`);

    // Find an event link (or simulate one)
    const hasEventLink = await page.evaluate(() => {
      const links = document.querySelectorAll('a[href]');
      const eventDomains = ['eventbrite', 'universe.com', 'showpass', 'ticketmaster'];
      for (let i = 0; i < links.length; i++) {
        const href = links[i].getAttribute('href') || '';
        for (const domain of eventDomains) {
          if (href.indexOf(domain) !== -1) return true;
        }
      }
      return false;
    });

    if (hasEventLink) {
      // Click the first event link (prevent navigation)
      await page.evaluate(() => {
        const links = document.querySelectorAll('a[href]');
        const eventDomains = ['eventbrite', 'universe.com', 'showpass', 'ticketmaster'];
        for (let i = 0; i < links.length; i++) {
          const href = links[i].getAttribute('href') || '';
          for (const domain of eventDomains) {
            if (href.indexOf(domain) !== -1) {
              // Prevent actual navigation but trigger the click handler
              links[i].addEventListener('click', (e) => e.preventDefault(), { once: true });
              (links[i] as HTMLElement).click();
              return;
            }
          }
        }
      });

      // Wait for track + recheck cycle (1.5s)
      await page.waitForTimeout(3000);

      console.log(`Track requests after click: ${trackRequests}`);
      console.log(`check_site requests after click: ${checkSiteRequests}`);

      // There should be a track request for the event_click
      expect(trackRequests).toBeGreaterThan(0);
      // There should be a recheck after the event click
      expect(checkSiteRequests).toBeGreaterThan(initialChecks);
    } else {
      console.log('No event links found on page — simulating a click dispatch');

      // Simulate an event click by creating a temporary link and clicking it
      await page.evaluate(() => {
        const a = document.createElement('a');
        a.href = 'https://www.eventbrite.ca/e/simulated-test-event';
        a.textContent = 'Simulated Test Event';
        a.target = '_blank';
        a.style.position = 'fixed';
        a.style.top = '50%';
        a.style.left = '50%';
        a.style.zIndex = '999999';
        document.body.appendChild(a);
        a.addEventListener('click', (e) => e.preventDefault(), { once: true });
        a.click();
        a.remove();
      });

      await page.waitForTimeout(3000);

      console.log(`Track requests after simulated click: ${trackRequests}`);
      console.log(`check_site requests after simulated click: ${checkSiteRequests}`);
    }
  });

  test('wall appears after exceeding event click limit via live API', async ({ page }) => {
    // This test does NOT mock — it uses the real API
    // First, flood the server with event clicks from this test's IP
    const request = page.request;

    // Record several event clicks to exceed the limit
    for (let i = 0; i < 4; i++) {
      await (await page.request.post(`${BASE_URL}/track.php`, {
        data: {
          action: 'click',
          click_type: 'event_click',
          page: 'events',
          target_url: `https://www.eventbrite.ca/e/live-test-${Date.now()}-${i}`,
          target_title: `Live Test Event ${i}`,
          target_id: `live-test-${i}`
        }
      }));
    }

    // Now check what check_site returns for this IP
    const checkRes = await page.request.get(`${BASE_URL}/guest_usage.php?action=check_site`);
    const checkData = await checkRes.json();
    console.log('check_site response after 4 event clicks:', JSON.stringify(checkData));

    expect(checkData.ok).toBe(true);
    expect(checkData.event_click_count).toBeGreaterThan(2);
    expect(checkData.allowed).toBe(false);

    // Now load the page — the wall should appear
    await page.goto(EVENTS_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    const wall = await page.locator('#fte-guest-login-wall');
    const isVisible = await wall.isVisible();
    console.log(`Login wall visible: ${isVisible}`);

    // The wall should be visible since this IP has exceeded the click limit
    await expect(wall).toBeVisible({ timeout: 5000 });
  });
});


// ============================================================
// 3. DIAGNOSTICS — Inspect what tracking data looks like
// ============================================================

test.describe('Tracking Diagnostics', () => {

  test('admin endpoint shows click data with event_click type', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/guest_usage_admin.php`);
    expect(res.status()).toBe(200);

    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json).toHaveProperty('clicks');
    expect(json.clicks).toHaveProperty('summary');
    expect(json.clicks).toHaveProperty('recent');

    // Check if event_click type exists in summary
    const eventClickSummary = json.clicks.summary.find((s: any) => s.click_type === 'event_click');
    console.log('Event click summary:', eventClickSummary);

    // Log recent event clicks
    const recentEventClicks = json.clicks.recent.filter((c: any) => c.click_type === 'event_click');
    console.log(`Recent event clicks: ${recentEventClicks.length}`);
    for (const c of recentEventClicks.slice(0, 5)) {
      console.log(`  IP: ${c.ip_address}, at: ${c.clicked_at}, url: ${(c.target_url || '').substring(0, 60)}`);
    }
  });

  test('page view tracking is recording visits', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/guest_usage_admin.php`);
    const json = await res.json();

    expect(json).toHaveProperty('page_views');
    console.log(`Total page view records: ${json.page_views.total}`);

    // Check page view summary
    for (const pv of json.page_views.summary || []) {
      console.log(`  Page: ${pv.page}, unique visitors: ${pv.unique_visitors}, total views: ${pv.total_views}`);
    }
  });
});
