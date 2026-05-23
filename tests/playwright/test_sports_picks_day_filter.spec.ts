import { test, expect } from '@playwright/test';

const URL = 'https://findtorontoevents.ca/live-monitor/sports-betting.html';

test.describe('sports-betting day filter', () => {
  test('renders day-filter buttons + no JS errors + picks visible', async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', (err) => pageErrors.push(String(err)));

    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });

    // Wait for picks API to render. Day-filter bar is inserted before picks render.
    await page.waitForFunction(
      () => {
        const bar = document.getElementById('day-filter-bar');
        return bar && (bar as HTMLElement).style.display !== 'none';
      },
      { timeout: 30000 },
    );

    // Confirm 4 day-filter buttons exist with counts.
    const dayBtns = page.locator('#day-filter-bar .day-filter-btn');
    await expect(dayBtns).toHaveCount(4);

    const labels = ['ALL', 'TODAY', 'TOMORROW', 'LATER'];
    for (const k of labels) {
      const btn = page.locator(`#day-filter-bar .day-filter-btn[data-day="${k}"]`);
      await expect(btn).toBeVisible();
      const txt = (await btn.textContent()) || '';
      // each button shows label + (count). Counts may be (0).
      expect(txt).toMatch(/\(\d+\)/);
    }

    // Default-pressed button: TODAY if today has picks, else TOMORROW, else ALL.
    const pressed = await page.locator('#day-filter-bar .day-filter-btn[aria-pressed="true"]').first();
    await expect(pressed).toBeVisible();

    // Click TOMORROW and confirm grid renders > 0 cards (we know live has 10 picks today, all tomorrow).
    const tomorrowBtn = page.locator('#day-filter-bar .day-filter-btn[data-day="TOMORROW"]');
    await tomorrowBtn.click();
    await page.waitForTimeout(1500);
    const tomorrowCount = parseInt((await tomorrowBtn.locator('span').textContent() || '(0)').replace(/[^\d]/g, ''), 10);
    if (tomorrowCount > 0) {
      const cards = await page.locator('#value-bets-grid .pick-card-enhanced').count();
      expect(cards).toBeGreaterThan(0);
    }

    // Switch to TODAY — either renders cards or empty-state copy.
    const todayBtn = page.locator('#day-filter-bar .day-filter-btn[data-day="TODAY"]');
    await todayBtn.click();
    await page.waitForTimeout(1500);
    const todayBody = await page.locator('#value-bets-grid').innerHTML();
    expect(todayBody.length).toBeGreaterThan(20);

    // No JS errors caused by our changes.
    const ourErrors = pageErrors.filter((e) => !/sports_failover_proxy|favicon/.test(e));
    expect(ourErrors).toEqual([]);

    // Console errors: ignore the known 503 from sports_failover_proxy stub.
    const ourConsoleErrors = consoleErrors.filter(
      (msg) => !/sports_failover_proxy|503|Failed to load resource|favicon/.test(msg),
    );
    expect(ourConsoleErrors).toEqual([]);
  });
});
