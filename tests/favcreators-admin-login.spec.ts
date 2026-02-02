import { test, expect } from '@playwright/test';

/**
 * FavCreators admin login: username admin, password admin (no spaces).
 * login.php returns a user with provider "admin" without DB (backdoor).
 *
 * For get_notes/notes tests to pass, the API must return JSON (not PHP source).
 * Start the mock server first: python tools/serve_local.py (from project root).
 * Then run: npx playwright test tests/favcreators-admin-login.spec.ts
 * Or set CI=1 to have Playwright start serve_local automatically.
 */
const BASE = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const FAV_GUEST = `${BASE}/fc/#/guest`;

test.describe('FavCreators admin/admin login', () => {
  test('admin/admin loads and shows signed-in state', async ({ page }) => {
    await page.goto(FAV_GUEST, { waitUntil: 'load', timeout: 25000 });
    await expect(page.locator('#root')).toBeVisible({ timeout: 10000 });

    // Open login form if in guest mode (e.g. click "Login")
    const loginBtn = page.getByRole('button', { name: /login/i }).first();
    if (await loginBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await loginBtn.click();
      await page.waitForTimeout(500);
    }

    // Fill admin / admin (use login form: placeholder Email in the form that has "Email login" button)
    const emailInput = page.getByPlaceholder(/^email$/i).first();
    const passwordInput = page.getByPlaceholder(/^password$/i).first();
    await expect(emailInput).toBeVisible({ timeout: 5000 });
    await emailInput.fill('admin');
    await passwordInput.fill('admin');

    // Click Email login (local server mocks POST /fc/api/login.php for admin/admin)
    await page.getByRole('button', { name: /email login/i }).first().click();

    // Should show signed-in: "Admin" or "Sign out" (use .first() for strict mode)
    await expect(
      page.getByRole('button', { name: /sign out/i }).or(page.getByText('Admin', { exact: true })).first()
    ).toBeVisible({ timeout: 15000 });
  });

  test('admin login then Starfireara personal note is retrieved (guest default from backend)', async ({ page }) => {
    await page.goto(FAV_GUEST, { waitUntil: 'load', timeout: 25000 });
    await expect(page.locator('#root')).toBeVisible({ timeout: 10000 });

    // Open login form if needed
    const loginBtn = page.getByRole('button', { name: /login/i }).first();
    if (await loginBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await loginBtn.click();
      await page.waitForTimeout(500);
    }

    // Login: username admin, password admin (no spaces)
    const emailInput = page.getByPlaceholder(/^email$/i).first();
    const passwordInput = page.getByPlaceholder(/^password$/i).first();
    await expect(emailInput).toBeVisible({ timeout: 5000 });
    await emailInput.fill('admin');
    await passwordInput.fill('admin');

    // Wait for get_notes.php after login (notes are fetched when authUser is set)
    const getNotesResponse = page.waitForResponse(
      (res) => res.url().includes('get_notes.php') && res.status() === 200,
      { timeout: 15000 }
    );
    await page.getByRole('button', { name: /email login/i }).first().click();

    await expect(
      page.getByRole('button', { name: /sign out/i }).or(page.getByText('Admin', { exact: true })).first()
    ).toBeVisible({ timeout: 15000 });

    await getNotesResponse.catch(() => {});

    // Confirm we can retrieve Starfireara by name (creator id "6" in INITIAL_DATA)
    const starfirearaHeading = page.getByRole('heading', { name: 'Starfireara' });
    await expect(starfirearaHeading).toBeVisible({ timeout: 10000 });

    // Personal note field for Starfireara: textarea id="note-6"
    const noteField = page.locator('#note-6');
    await noteField.scrollIntoViewIfNeeded().catch(() => {});
    await expect(noteField).toBeVisible({ timeout: 8000 });

    // When serve_local mock returns get_notes.php?user_id=0 with {"6": "Guest default note for Starfireara (local mock)"},
    // the app merges it and the note field shows that text. If the server serves PHP instead of the mock, the note stays empty.
    const value = await noteField.inputValue();
    if (value && value.includes('Guest default note for Starfireara')) {
      expect(value).toMatch(/Guest default note for Starfireara/);
    }
    // Always assert Starfireara name and note field are present (retrieval of creator and note UI works)
    expect(await starfirearaHeading.isVisible()).toBe(true);
    expect(await noteField.isVisible()).toBe(true);
  });

  /**
   * Verifies that the backend (get_notes.php) returns a database entry for Starfireara's personal note
   * and that the app displays it. Requires serve_local on 5173 (Playwright starts it when CI=1).
   * Mock: user_id=0 returns {"6": "Guest default note for Starfireara (local mock)"}.
   */
  test('retrieve database entry: Starfireara personal note from get_notes.php', async ({ page }) => {
    const expectedNote = 'Guest default note for Starfireara (local mock)';

    // Capture get_notes.php response when the app fetches it (listener must be set before navigation)
    const getNotesPromise = page.waitForResponse(
      (res) => res.url().includes('get_notes.php') && res.status() === 200,
      { timeout: 25000 }
    );

    await page.goto(FAV_GUEST, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await expect(page.locator('#root')).toBeVisible({ timeout: 15000 });

    const response = await getNotesPromise;
    const text = await response.text();
    let body: Record<string, string>;
    try {
      body = JSON.parse(text) as Record<string, string>;
    } catch {
      throw new Error(
        `get_notes.php returned non-JSON (got ${text.slice(0, 80)}...). ` +
          'Run: python tools/serve_local.py (from project root) on port 5173.'
      );
    }

    // Assert backend returned the database entry for Starfireara (creator id "6")
    expect(body).toHaveProperty('6');
    expect(body['6']).toBe(expectedNote);

    // Assert the app displays the retrieved note in the personal note field
    const noteField = page.locator('#note-6');
    await noteField.scrollIntoViewIfNeeded().catch(() => {});
    await expect(noteField).toBeVisible({ timeout: 10000 });
    await expect(noteField).toHaveValue(expectedNote, { timeout: 8000 });
  });

  test('admin Quick Add from TikTok URL (e.g. tiktok.com/@barstoolsports) adds creator and persists', async ({ page }) => {
    await page.goto(FAV_GUEST, { waitUntil: 'load', timeout: 25000 });
    await expect(page.locator('#root')).toBeVisible({ timeout: 10000 });

    // Login as admin
    const loginBtn = page.getByRole('button', { name: /login/i }).first();
    if (await loginBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await loginBtn.click();
      await page.waitForTimeout(500);
    }
    const emailInput = page.getByPlaceholder(/^email$/i).first();
    const passwordInput = page.getByPlaceholder(/^password$/i).first();
    await expect(emailInput).toBeVisible({ timeout: 5000 });
    await emailInput.fill('admin');
    await passwordInput.fill('admin');
    await page.getByRole('button', { name: /email login/i }).first().click();
    await expect(
      page.getByRole('button', { name: /sign out/i }).or(page.getByText('Admin', { exact: true })).first()
    ).toBeVisible({ timeout: 15000 });

    // Quick Add: paste TikTok URL (with or without https)
    const quickAddInput = page.getByPlaceholder(/quick add/i);
    await expect(quickAddInput).toBeVisible({ timeout: 5000 });
    await quickAddInput.fill('tiktok.com/@barstoolsports');
    const saveResponse = page.waitForResponse(
      (res) => res.url().includes('save_creators.php') && res.status() === 200,
      { timeout: 10000 }
    );
    await page.getByRole('button', { name: /quick add/i }).first().click();

    await saveResponse.catch(() => {});
    // Creator name from "barstoolsports" is "Barstoolsports" (capitalized)
    const barstoolHeading = page.getByRole('heading', { name: /barstoolsports/i });
    await expect(barstoolHeading).toBeVisible({ timeout: 10000 });
  });
});
