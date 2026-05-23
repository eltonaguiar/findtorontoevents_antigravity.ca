import { test, expect } from '@playwright/test';
import { AxeBuilder } from '@axe-core/playwright';

test.describe('Find Toronto Events Page Test Suite', () => {
  let consoleErrors: string[] = [];

  test.beforeEach(async ({ page }) => {
    consoleErrors = [];
    // Capture console errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    // Navigate to target page
    await page.goto('https://findtorontoevents.ca');
    await page.waitForLoadState('networkidle');
  });

  test('Initial page load has no console errors', async () => {
    expect(consoleErrors.length).toBe(0);
  });

  test('Initial page passes basic accessibility checks', async ({ page }) => {
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toHaveLength(0);
  });

  // Test all date filters
  const dateFilters = ['today', 'tomorrow', 'this week', 'this month', 'next month'];
  for (const filter of dateFilters) {
    test(`Date filter "${filter}" works correctly`, async ({ page }) => {
      const filterBtn = page.getByText(filter, { exact: true });
      await expect(filterBtn).toBeVisible();
      await filterBtn.click();
      await page.waitForLoadState('networkidle');

      // Verify no console errors after filter
      expect(consoleErrors.length).toBe(0);
      // Verify filter is active (common pattern for toggle buttons)
      await expect(filterBtn).toHaveAttribute('aria-pressed', 'true');
      // Accessibility check after filter
      const a11yResults = await new AxeBuilder({ page }).analyze();
      expect(a11yResults.violations).toHaveLength(0);
    });
  }

  test('Gear icon settings panel opens and supports persistence', async ({ page }) => {
    const gearBtn = page.getByRole('button', { name: /settings|gear/i });
    await expect(gearBtn).toBeVisible();
    await gearBtn.click();

    // Verify settings panel opens
    const settingsPanel = page.getByRole('dialog', { name: /settings/i }).or(page.getByTestId('settings-panel'));
    await expect(settingsPanel).toBeVisible();

    // Test max 3 events per provider toggle (if available)
    const maxEventsToggle = page.getByLabel(/max 3 events per day per provider/i);
    if (await maxEventsToggle.isVisible()) {
      await maxEventsToggle.click();
      // Verify localStorage persistence
      const stored = await page.evaluate(() => localStorage.getItem('eventSettings'));
      expect(stored).not.toBeNull();
    }

    // Test Eventbrite exemption toggle
    const eventbriteExempt = page.getByLabel(/eventbrite exemption/i);
    if (await eventbriteExempt.isVisible()) {
      await eventbriteExempt.click();
    }

    // Close settings
    await settingsPanel.getByRole('button', { name: /close|cancel/i }).click();
    await expect(settingsPanel).not.toBeVisible();
  });

  test('Full user journey: filter → adjust settings → view event', async ({ page }) => {
    // Apply today filter
    await page.getByText('today', { exact: true }).click();
    await page.waitForLoadState('networkidle');

    // Open settings and adjust
    await page.getByRole('button', { name: /gear/i }).click();
    const settingsPanel = page.getByRole('dialog', { name: /settings/i });
    await expect(settingsPanel).toBeVisible();

    // Toggle a setting if available
    const distanceSetting = page.getByLabel(/distance radius/i);
    if (await distanceSetting.isVisible()) {
      await distanceSetting.fill('10');
    }
    await settingsPanel.getByRole('button', { name: /save|close/i }).click();

    // Click first event card if available
    const firstEvent = page.getByTestId('event-card').first();
    if (await firstEvent.isVisible()) {
      await firstEvent.click();
      await expect(page).toHaveURL(/event/);
    }

    // Verify no console errors throughout journey
    expect(consoleErrors.length).toBe(0);
  });
});
