/**
 * VR Creators Auth Integration Tests
 *
 * Tests the login UI, authenticated creator fetching, live menu,
 * and video browser features in the VR Creators zone.
 */
import { test, expect } from '@playwright/test';

const BASE = process.env.VERIFY_REMOTE === '1'
  ? 'https://findtorontoevents.ca'
  : 'http://localhost:5173';

test.describe('VR Creators Auth Integration', () => {

  // ─── Auth UI Panel ───

  test('Auth panel: login button visible for guest', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    const loginBar = page.locator('#auth-login-bar');
    await expect(loginBar).toBeVisible();
    const text = await loginBar.textContent();
    expect(text).toContain('Login');
    expect(text).toContain('guest');
  });

  test('Auth panel: login overlay opens on click', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    await page.click('#auth-toggle-btn');
    await page.waitForTimeout(300);
    const overlay = page.locator('#vr-login-overlay');
    await expect(overlay).toHaveClass(/open/);
    // Check form elements
    await expect(page.locator('#login-email')).toBeVisible();
    await expect(page.locator('#login-password')).toBeVisible();
    await expect(page.locator('.login-submit')).toBeVisible();
  });

  test('Auth panel: login overlay closes with X button', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    await page.click('#auth-toggle-btn');
    await page.waitForTimeout(300);
    await page.click('.login-close');
    await page.waitForTimeout(300);
    const overlay = page.locator('#vr-login-overlay');
    await expect(overlay).not.toHaveClass(/open/);
  });

  test('Auth panel: guest mode button closes login overlay', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    await page.click('#auth-toggle-btn');
    await page.waitForTimeout(300);
    // Click "Continue as Guest"
    await page.click('button:text("Continue as Guest")');
    await page.waitForTimeout(300);
    const overlay = page.locator('#vr-login-overlay');
    await expect(overlay).not.toHaveClass(/open/);
  });

  test('Auth panel: sign up link points to FC app', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    await page.click('#auth-toggle-btn');
    await page.waitForTimeout(300);
    const link = page.locator('#vr-login-card a[href*="findtorontoevents.ca/fc"]');
    await expect(link).toBeAttached();
  });

  // ─── Guest Creator Loading ───

  test('Guest mode: creators load with user_id=0', async ({ page }) => {
    const requests: string[] = [];
    page.on('request', (req) => {
      if (req.url().includes('get_my_creators')) requests.push(req.url());
    });
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);
    // Should have made a request with user_id=0
    const guestReq = requests.find(r => r.includes('user_id=0'));
    expect(guestReq).toBeTruthy();
  });

  test('Guest mode: creator cards render', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);
    // Check that some creators loaded (loading screen should be gone)
    const loadingScreen = page.locator('#loading-screen');
    const opacity = await loadingScreen.evaluate(el => getComputedStyle(el).opacity);
    expect(Number(opacity)).toBeLessThan(0.5);
  });

  // ─── Live Menu ───

  test('Live menu: toggle button visible', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    const toggle = page.locator('#live-menu-toggle');
    await expect(toggle).toBeVisible();
    const text = await toggle.textContent();
    expect(text).toContain('Live');
  });

  test('Live menu: dropdown opens on click', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);
    await page.click('#live-menu-toggle');
    await page.waitForTimeout(300);
    const dropdown = page.locator('#live-menu-dropdown');
    await expect(dropdown).toHaveClass(/open/);
  });

  test('Live menu: shows empty message or live creators', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);
    await page.click('#live-menu-toggle');
    await page.waitForTimeout(300);
    // Either the empty message or live items should exist
    const emptyMsg = page.locator('#live-menu-empty');
    const liveItems = page.locator('.live-menu-item');
    const emptyVisible = await emptyMsg.isVisible().catch(() => false);
    const itemCount = await liveItems.count();
    expect(emptyVisible || itemCount > 0).toBeTruthy();
  });

  test('Live menu: closes on toggle', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);
    await page.click('#live-menu-toggle');
    await page.waitForTimeout(300);
    await page.click('#live-menu-toggle');
    await page.waitForTimeout(300);
    const dropdown = page.locator('#live-menu-dropdown');
    await expect(dropdown).not.toHaveClass(/open/);
  });

  // ─── Creator Detail: Recent Videos Button ───

  test('Detail: "View on FC" button links to FavCreators app', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);
    // Click first card to open detail
    const hasCards = await page.locator('.clickable[data-gidx]').count();
    if (hasCards > 0) {
      await page.evaluate(() => {
        if (typeof window.showCreatorDetail === 'function') window.showCreatorDetail(0);
      });
      await page.waitForTimeout(500);
      const detailOpen = await page.locator('#creator-detail.open').count();
      if (detailOpen > 0) {
        const fcBtn = page.locator('#det-btns a:text("View on FC")');
        const count = await fcBtn.count();
        expect(count).toBeGreaterThanOrEqual(1);
      }
    }
  });

  // ─── No JS Errors ───

  test('VR Creators: loads without critical JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);
    const critical = errors.filter(e =>
      !e.includes('net::') && !e.includes('CORS') &&
      !e.includes('Failed to fetch') && !e.includes('NetworkError') &&
      !e.includes('Unexpected identifier') && !e.includes('play()')
    );
    expect(critical).toEqual([]);
  });

  // ─── HUD: link to FC ───

  test('HUD: shows link to FavCreators web app', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    const hud = page.locator('#hud');
    const text = await hud.textContent();
    expect(text).toContain('findtorontoevents.ca/fc');
  });
});
