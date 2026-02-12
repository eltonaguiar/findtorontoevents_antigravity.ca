import { test, expect, Page, BrowserContext } from '@playwright/test';

/**
 * Auth Persistence Tests — Mobile User Agents
 *
 * Reproduces the bug: user signs in, refreshes the page,
 * and still sees "Sign In" / "Guest mode" instead of their username.
 *
 * Tests with multiple mobile user agents to verify if it's a
 * mobile-specific issue, caching issue, or session persistence issue.
 */

const APP_URL = 'https://findtorontoevents.ca/fc/';
const API_BASE = 'https://findtorontoevents.ca/fc/api';

// Mobile user agents to test
const MOBILE_USER_AGENTS = {
  'iPhone Safari': {
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
    viewport: { width: 390, height: 844 },
  },
  'Android Chrome': {
    userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
    viewport: { width: 412, height: 915 },
  },
  'Samsung Internet': {
    userAgent: 'Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/122.0.0.0 Mobile Safari/537.36',
    viewport: { width: 412, height: 915 },
  },
  'iPad Safari': {
    userAgent: 'Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
    viewport: { width: 820, height: 1180 },
  },
  'Desktop Chrome': {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 720 },
  },
};

// Helper: perform login with admin credentials via the UI
async function loginViaUI(page: Page) {
  // Wait for the app to load and the auth panel to appear
  await page.waitForTimeout(3000);

  // Click the Login button to expand the login form (in guest mode)
  const loginBtn = page.locator('button:has-text("Login")');
  if (await loginBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
    await loginBtn.click();
    await page.waitForTimeout(500);
  }

  // Fill email and password
  const emailInputs = page.locator('input[type="email"]');
  const passwordInputs = page.locator('input[type="password"]');

  // Find the first visible email input in the auth panel
  const emailInput = emailInputs.first();
  const passwordInput = passwordInputs.first();

  await emailInput.fill('admin');
  await passwordInput.fill('adminelton2016');

  // Click the email login button
  const emailLoginBtn = page.locator('button:has-text("Email login")');
  await emailLoginBtn.click();

  // Wait for the auth state to update
  await page.waitForTimeout(3000);
}

// Helper: check if user appears logged in
async function isLoggedIn(page: Page): Promise<{ loggedIn: boolean; displayText: string }> {
  // Check for auth-user section (shown when logged in)
  const authUserName = page.locator('.auth-user__name');
  const signOutBtn = page.locator('button:has-text("Sign out")');
  const guestModeLabel = page.locator('.auth-status:has-text("Guest mode")');
  const loginBtn = page.locator('button:has-text("Login")');

  const hasUserName = await authUserName.isVisible({ timeout: 3000 }).catch(() => false);
  const hasSignOut = await signOutBtn.isVisible({ timeout: 1000 }).catch(() => false);
  const hasGuestMode = await guestModeLabel.isVisible({ timeout: 1000 }).catch(() => false);
  const hasLoginBtn = await loginBtn.isVisible({ timeout: 1000 }).catch(() => false);

  let displayText = '';
  if (hasUserName) {
    displayText = await authUserName.textContent() || '';
  } else if (hasGuestMode) {
    displayText = 'Guest mode';
  } else if (hasLoginBtn) {
    displayText = 'Login button visible';
  }

  return {
    loggedIn: hasUserName && hasSignOut,
    displayText,
  };
}

// ============================================================
// 1. API-LEVEL TESTS — Verify session and cookie behavior
// ============================================================

test.describe('Auth API Session Tests', () => {
  test('login.php sets session cookie and returns user', async ({ request }) => {
    const res = await request.post(`${API_BASE}/login.php`, {
      data: { email: 'admin', password: 'adminelton2016' },
    });
    expect(res.status()).toBe(200);

    const json = await res.json();
    console.log('Login response:', JSON.stringify(json));

    expect(json.user).toBeDefined();
    expect(json.user.email).toBe('admin');
    expect(json.user.provider).toBe('admin');

    // Check that a session cookie was set
    const cookies = await res.headers()['set-cookie'];
    console.log('Set-Cookie header:', cookies);
    if (cookies) {
      expect(cookies).toContain('PHPSESSID');
    }
  });

  test('get_me.php returns user when session is valid', async ({ request }) => {
    // First login to establish session
    const loginRes = await request.post(`${API_BASE}/login.php`, {
      data: { email: 'admin', password: 'adminelton2016' },
    });
    expect(loginRes.status()).toBe(200);

    // Now check get_me.php (should use the session cookie from login)
    const meRes = await request.get(`${API_BASE}/get_me.php`);
    expect(meRes.status()).toBe(200);

    const meJson = await meRes.json();
    console.log('get_me.php response:', JSON.stringify(meJson));

    expect(meJson.user).toBeDefined();
    expect(meJson.user).not.toBeNull();
    expect(meJson.user.email).toBe('admin');
  });

  test('get_me.php returns null when no session (simulating expired session)', async ({ request }) => {
    // Call get_me.php without logging in first (no session cookie)
    const meRes = await request.get(`${API_BASE}/get_me.php`);
    expect(meRes.status()).toBe(200);

    const meJson = await meRes.json();
    console.log('get_me.php without session:', JSON.stringify(meJson));

    // Should return null user
    expect(meJson.user).toBeNull();
  });

  test('get_me.php has correct CORS and cache headers', async ({ request }) => {
    const res = await request.get(`${API_BASE}/get_me.php`);
    const headers = res.headers();

    console.log('get_me.php headers:', JSON.stringify(headers, null, 2));

    // Check Cache-Control
    expect(headers['cache-control']).toContain('no-cache');

    // BUG CHECK: get_me.php should have CORS headers for credentials
    // Missing Access-Control-Allow-Origin is a potential issue
    const hasCors = !!headers['access-control-allow-origin'];
    console.log('Has CORS header:', hasCors);
    if (!hasCors) {
      console.warn('WARNING: get_me.php is missing Access-Control-Allow-Origin header');
    }
  });

  test('session cookie SameSite attribute check', async ({ request }) => {
    const loginRes = await request.post(`${API_BASE}/login.php`, {
      data: { email: 'admin', password: 'adminelton2016' },
    });

    const setCookie = loginRes.headers()['set-cookie'] || '';
    console.log('Full Set-Cookie:', setCookie);

    // Check SameSite
    const hasSameSite = /samesite/i.test(setCookie);
    console.log('Has SameSite:', hasSameSite);
    if (!hasSameSite) {
      console.warn('WARNING: Session cookie missing SameSite attribute. Mobile browsers may default to Lax.');
    }

    // Check Secure
    const hasSecure = /secure/i.test(setCookie);
    console.log('Has Secure flag:', hasSecure);

    // Check HttpOnly
    const hasHttpOnly = /httponly/i.test(setCookie);
    console.log('Has HttpOnly flag:', hasHttpOnly);
  });
});

// ============================================================
// 2. BROWSER-LEVEL TESTS — Login + Refresh with mobile UAs
// ============================================================

for (const [deviceName, config] of Object.entries(MOBILE_USER_AGENTS)) {
  test.describe(`Auth Persistence — ${deviceName}`, () => {
    test(`login and verify username is displayed on ${deviceName}`, async ({ browser }) => {
      const context = await browser.newContext({
        userAgent: config.userAgent,
        viewport: config.viewport,
      });
      const page = await context.newPage();

      // Intercept and log auth-related network requests
      const authRequests: string[] = [];
      page.on('request', (req) => {
        const url = req.url();
        if (url.includes('login.php') || url.includes('get_me.php') || url.includes('auth')) {
          authRequests.push(`${req.method()} ${url}`);
        }
      });
      page.on('response', (res) => {
        const url = res.url();
        if (url.includes('login.php') || url.includes('get_me.php') || url.includes('auth')) {
          console.log(`[${deviceName}] Response: ${res.status()} ${url}`);
        }
      });

      // Navigate to the app (use 'load' not 'networkidle' — app has continuous polling)
      await page.goto(APP_URL, { waitUntil: 'load' });
      await page.waitForTimeout(5000);

      // Check initial state - should be guest mode
      const beforeLogin = await isLoggedIn(page);
      console.log(`[${deviceName}] Before login: loggedIn=${beforeLogin.loggedIn}, display="${beforeLogin.displayText}"`);
      expect(beforeLogin.loggedIn).toBe(false);

      // Perform login
      await loginViaUI(page);

      // Verify login succeeded
      const afterLogin = await isLoggedIn(page);
      console.log(`[${deviceName}] After login: loggedIn=${afterLogin.loggedIn}, display="${afterLogin.displayText}"`);

      // Check localStorage
      const localStorageAuth = await page.evaluate(() => {
        return localStorage.getItem('fav_creators_auth_user');
      });
      console.log(`[${deviceName}] localStorage auth after login:`, localStorageAuth);

      // Take screenshot
      await page.screenshot({
        path: `e:/findtorontoevents_antigravity.ca/favcreators/test-results/auth-${deviceName.replace(/\s/g, '-')}-after-login.png`,
        fullPage: false,
      });

      expect(afterLogin.loggedIn).toBe(true);
      expect(afterLogin.displayText).toContain('Admin');

      await context.close();
    });

    test(`login persists after refresh on ${deviceName}`, async ({ browser }) => {
      const context = await browser.newContext({
        userAgent: config.userAgent,
        viewport: config.viewport,
      });
      const page = await context.newPage();

      // Log network requests for debugging
      const responses: { url: string; status: number; body?: string }[] = [];
      page.on('response', async (res) => {
        const url = res.url();
        if (url.includes('get_me.php') || url.includes('login.php')) {
          let body = '';
          try {
            body = await res.text();
          } catch { }
          responses.push({ url, status: res.status(), body });
          console.log(`[${deviceName}] Network: ${res.status()} ${url} → ${body.substring(0, 200)}`);
        }
      });

      // Step 1: Navigate and login
      await page.goto(APP_URL, { waitUntil: 'load' });
      await page.waitForTimeout(2000);
      await loginViaUI(page);

      const afterLogin = await isLoggedIn(page);
      console.log(`[${deviceName}] After login: loggedIn=${afterLogin.loggedIn}, display="${afterLogin.displayText}"`);

      // Verify localStorage is set
      const lsBefore = await page.evaluate(() => localStorage.getItem('fav_creators_auth_user'));
      console.log(`[${deviceName}] localStorage before refresh:`, lsBefore);
      expect(lsBefore).not.toBeNull();

      // Step 2: Refresh the page
      console.log(`[${deviceName}] --- REFRESHING PAGE ---`);
      await page.reload({ waitUntil: 'load' });
      await page.waitForTimeout(4000);

      // Step 3: Check if still logged in
      const afterRefresh = await isLoggedIn(page);
      console.log(`[${deviceName}] After refresh: loggedIn=${afterRefresh.loggedIn}, display="${afterRefresh.displayText}"`);

      // Check localStorage after refresh
      const lsAfter = await page.evaluate(() => localStorage.getItem('fav_creators_auth_user'));
      console.log(`[${deviceName}] localStorage after refresh:`, lsAfter);

      // Check cookies
      const cookies = await context.cookies();
      const sessionCookie = cookies.find(c => c.name === 'PHPSESSID');
      console.log(`[${deviceName}] PHPSESSID cookie after refresh:`, sessionCookie ? `value=${sessionCookie.value}, secure=${sessionCookie.secure}, sameSite=${sessionCookie.sameSite}` : 'NOT FOUND');

      // Take screenshot
      await page.screenshot({
        path: `e:/findtorontoevents_antigravity.ca/favcreators/test-results/auth-${deviceName.replace(/\s/g, '-')}-after-refresh.png`,
        fullPage: false,
      });

      // Log all get_me.php responses
      const getMeResponses = responses.filter(r => r.url.includes('get_me.php'));
      console.log(`[${deviceName}] get_me.php calls: ${getMeResponses.length}`);
      getMeResponses.forEach((r, i) => {
        console.log(`  [${i}] ${r.status}: ${r.body?.substring(0, 200)}`);
      });

      // THE KEY ASSERTION: user should still be logged in after refresh
      if (!afterRefresh.loggedIn) {
        console.error(`BUG CONFIRMED on ${deviceName}: User is NOT logged in after refresh!`);
        console.error(`  localStorage: ${lsAfter}`);
        console.error(`  Session cookie: ${sessionCookie ? 'present' : 'missing'}`);
        console.error(`  Display text: "${afterRefresh.displayText}"`);
      }

      expect(afterRefresh.loggedIn).toBe(true);
      expect(afterRefresh.displayText).toContain('Admin');

      await context.close();
    });

    test(`login persists after navigation away and back on ${deviceName}`, async ({ browser }) => {
      const context = await browser.newContext({
        userAgent: config.userAgent,
        viewport: config.viewport,
      });
      const page = await context.newPage();

      // Login
      await page.goto(APP_URL, { waitUntil: 'load' });
      await page.waitForTimeout(2000);
      await loginViaUI(page);

      const afterLogin = await isLoggedIn(page);
      expect(afterLogin.loggedIn).toBe(true);

      // Navigate away
      await page.goto('https://findtorontoevents.ca/', { waitUntil: 'load' });
      await page.waitForTimeout(1000);

      // Navigate back
      await page.goto(APP_URL, { waitUntil: 'load' });
      await page.waitForTimeout(4000);

      const afterNavBack = await isLoggedIn(page);
      console.log(`[${deviceName}] After nav away & back: loggedIn=${afterNavBack.loggedIn}, display="${afterNavBack.displayText}"`);

      // Check if localStorage survived navigation
      const ls = await page.evaluate(() => localStorage.getItem('fav_creators_auth_user'));
      console.log(`[${deviceName}] localStorage after nav back:`, ls);

      await page.screenshot({
        path: `e:/findtorontoevents_antigravity.ca/favcreators/test-results/auth-${deviceName.replace(/\s/g, '-')}-after-nav-back.png`,
        fullPage: false,
      });

      if (!afterNavBack.loggedIn) {
        console.error(`BUG CONFIRMED on ${deviceName}: User lost login after navigating away and back!`);
      }

      expect(afterNavBack.loggedIn).toBe(true);

      await context.close();
    });
  });
}

// ============================================================
// 3. DIAGNOSTIC TESTS — Isolate the root cause
// ============================================================

test.describe('Auth Persistence Diagnostics', () => {
  test('diagnose: does get_me.php clear localStorage when session expires?', async ({ browser }) => {
    const context = await browser.newContext({
      userAgent: MOBILE_USER_AGENTS['iPhone Safari'].userAgent,
      viewport: MOBILE_USER_AGENTS['iPhone Safari'].viewport,
    });
    const page = await context.newPage();

    // Manually set localStorage as if user was logged in before
    await page.goto(APP_URL, { waitUntil: 'load' });
    await page.waitForTimeout(2000);

    // Inject a fake cached auth user (non-admin provider to test the dangerous code path)
    await page.evaluate(() => {
      localStorage.setItem('fav_creators_auth_user', JSON.stringify({
        id: 999,
        email: 'test@test.com',
        display_name: 'TestUser',
        provider: 'local',
      }));
    });

    const lsBefore = await page.evaluate(() => localStorage.getItem('fav_creators_auth_user'));
    console.log('localStorage BEFORE reload (fake local user):', lsBefore);

    // Reload — the app will call get_me.php, session won't exist, get_me returns null
    // This will trigger: localStorage.removeItem('fav_creators_auth_user')
    await page.reload({ waitUntil: 'load' });
    await page.waitForTimeout(4000);

    const lsAfter = await page.evaluate(() => localStorage.getItem('fav_creators_auth_user'));
    console.log('localStorage AFTER reload (no valid session):', lsAfter);

    if (lsAfter === null) {
      console.error('BUG CONFIRMED: localStorage was CLEARED because get_me.php returned null!');
      console.error('This is the cascading failure: expired session destroys the local cache too.');
    } else {
      console.log('localStorage preserved (catch block fallback worked).');
    }

    await context.close();
  });

  test('diagnose: admin provider uses localStorage cache directly (bypass get_me)', async ({ browser }) => {
    const context = await browser.newContext({
      userAgent: MOBILE_USER_AGENTS['iPhone Safari'].userAgent,
      viewport: MOBILE_USER_AGENTS['iPhone Safari'].viewport,
    });
    const page = await context.newPage();

    let getMeCalled = false;
    page.on('request', (req) => {
      if (req.url().includes('get_me.php')) {
        getMeCalled = true;
      }
    });

    // Navigate and set admin user in localStorage
    await page.goto(APP_URL, { waitUntil: 'load' });
    await page.waitForTimeout(2000);

    await page.evaluate(() => {
      localStorage.setItem('fav_creators_auth_user', JSON.stringify({
        id: 0,
        email: 'admin',
        display_name: 'Admin',
        provider: 'admin',
        role: 'admin',
      }));
    });

    // Reload — should use cached admin directly without calling get_me.php
    getMeCalled = false;
    await page.reload({ waitUntil: 'load' });
    await page.waitForTimeout(4000);

    const authState = await isLoggedIn(page);
    console.log('Admin cache test: loggedIn=', authState.loggedIn, 'display=', authState.displayText);
    console.log('get_me.php was called:', getMeCalled);

    // For admin, get_me.php should NOT be called (early return from cache)
    if (getMeCalled) {
      console.warn('NOTE: get_me.php was called even for admin provider. This could cause issues if session expired.');
    }

    const ls = await page.evaluate(() => localStorage.getItem('fav_creators_auth_user'));
    console.log('localStorage after admin reload:', ls);

    expect(authState.loggedIn).toBe(true);
    expect(ls).not.toBeNull();

    await context.close();
  });

  test('diagnose: get_me.php network failure preserves localStorage (catch path)', async ({ browser }) => {
    const context = await browser.newContext({
      userAgent: MOBILE_USER_AGENTS['Android Chrome'].userAgent,
      viewport: MOBILE_USER_AGENTS['Android Chrome'].viewport,
    });
    const page = await context.newPage();

    // Navigate and set a local user in localStorage
    await page.goto(APP_URL, { waitUntil: 'load' });
    await page.waitForTimeout(2000);

    await page.evaluate(() => {
      localStorage.setItem('fav_creators_auth_user', JSON.stringify({
        id: 42,
        email: 'user@example.com',
        display_name: 'CachedUser',
        provider: 'local',
      }));
    });

    // Block get_me.php to simulate network failure
    await page.route('**/get_me.php**', (route) => {
      console.log('Intercepted get_me.php — aborting to simulate network error');
      route.abort('connectionfailed');
    });

    await page.reload({ waitUntil: 'load' });
    await page.waitForTimeout(4000);

    const ls = await page.evaluate(() => localStorage.getItem('fav_creators_auth_user'));
    console.log('localStorage after network failure:', ls);

    // The catch block should preserve the cached user
    if (ls) {
      console.log('GOOD: localStorage preserved on network failure (catch block worked).');
    } else {
      console.error('BUG: localStorage was cleared even on network failure!');
    }

    const authState = await isLoggedIn(page);
    console.log('Auth state after network failure:', authState);

    // Cached user should be restored via catch block
    expect(ls).not.toBeNull();

    await context.close();
  });

  test('regression: expired session should NOT clear localStorage cache', async ({ browser }) => {
    const context = await browser.newContext({
      userAgent: MOBILE_USER_AGENTS['Android Chrome'].userAgent,
      viewport: MOBILE_USER_AGENTS['Android Chrome'].viewport,
    });
    const page = await context.newPage();

    // Navigate and set a local user in localStorage
    await page.goto(APP_URL, { waitUntil: 'load' });
    await page.waitForTimeout(2000);

    await page.evaluate(() => {
      localStorage.setItem('fav_creators_auth_user', JSON.stringify({
        id: 42,
        email: 'user@example.com',
        display_name: 'CachedUser',
        provider: 'local',
      }));
    });

    // Mock get_me.php to return null user (expired session scenario)
    await page.route('**/get_me.php**', (route) => {
      console.log('Intercepted get_me.php — returning null user (expired session)');
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ user: null, debug_log_enabled: false }),
      });
    });

    await page.reload({ waitUntil: 'load' });
    await page.waitForTimeout(4000);

    const ls = await page.evaluate(() => localStorage.getItem('fav_creators_auth_user'));
    console.log('localStorage after get_me returns null:', ls);

    // AFTER FIX: localStorage should be preserved even when session expires
    // The cached user should remain so the user stays "logged in" until explicit logout
    expect(ls).not.toBeNull();
    if (ls) {
      console.log('PASS: localStorage preserved when session expired (fix working)');
    }

    await context.close();
  });

  test('diagnose: measure time between login and session loss', async ({ browser }) => {
    const context = await browser.newContext({
      userAgent: MOBILE_USER_AGENTS['iPhone Safari'].userAgent,
      viewport: MOBILE_USER_AGENTS['iPhone Safari'].viewport,
    });
    const page = await context.newPage();

    // Login
    await page.goto(APP_URL, { waitUntil: 'load' });
    await page.waitForTimeout(2000);
    await loginViaUI(page);

    const afterLogin = await isLoggedIn(page);
    console.log('Logged in:', afterLogin.loggedIn);

    if (!afterLogin.loggedIn) {
      console.log('Could not login — skipping timing test');
      await context.close();
      return;
    }

    // Rapid refresh cycle to see if session persists
    for (let i = 1; i <= 3; i++) {
      await page.waitForTimeout(2000);
      console.log(`\n--- Refresh #${i} (${i * 2}s after login) ---`);

      await page.reload({ waitUntil: 'load' });
      await page.waitForTimeout(3000);

      const state = await isLoggedIn(page);
      const ls = await page.evaluate(() => localStorage.getItem('fav_creators_auth_user'));

      console.log(`  loggedIn: ${state.loggedIn}`);
      console.log(`  display: "${state.displayText}"`);
      console.log(`  localStorage: ${ls ? 'present' : 'CLEARED'}`);

      if (!state.loggedIn) {
        console.error(`  Session lost after ${i * 2} seconds and ${i} refreshes!`);
        break;
      }
    }

    await context.close();
  });
});
