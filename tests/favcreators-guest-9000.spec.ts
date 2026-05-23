import { test, expect } from '@playwright/test';

const GUEST_URL = (process.env.BASE_URL || 'http://localhost:5173') + '/fc/#/guest';

test.describe('FavCreators guest at /fc/#/guest', () => {
  test('guest page loads (built app from docs)', async ({ page }) => {
    const res = await page.goto(GUEST_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
    expect(res?.status()).toBe(200);
    const html = await res!.text();
    // Built index has /fc/assets/... not /src/main.tsx
    expect(html).toMatch(/fc\/assets\/index-.*\.js/);
    expect(html).not.toMatch(/src\/main\.tsx/);
    await expect(page.locator('#root')).toBeVisible({ timeout: 10000 });
  });

  test('guest page shows FavCreators UI (Import or search)', async ({ page }) => {
    await page.goto(GUEST_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await expect(
      page.getByRole('button', { name: /Import/i }).or(page.getByPlaceholder(/search/i)).or(page.getByText('FavCreators'))
    ).toBeVisible({ timeout: 15000 });
  });
});
