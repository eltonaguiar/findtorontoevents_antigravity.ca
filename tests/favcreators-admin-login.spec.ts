import { test, expect } from '@playwright/test';

/**
 * FavCreators admin login: username admin, password admin.
 * login.php returns a user with provider "admin" without DB (backdoor).
 */
const BASE = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:9000';
const FAV_GUEST = `${BASE}/fc/#/guest`;

test.describe('FavCreators admin/admin login', () => {
  test('admin/admin loads and shows signed-in state', async ({ page }) => {
    await page.goto(FAV_GUEST, { waitUntil: 'domcontentloaded', timeout: 15000 });
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
});
