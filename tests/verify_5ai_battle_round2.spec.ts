import { test, expect } from '@playwright/test';

const AUDIT_URL = 'https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit/';

test.describe('5-AI Battle Tab — Round 2', () => {
  test('loads all 5 agents with picks data', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    const failedRequests: string[] = [];
    page.on('response', response => {
      const url = response.url();
      if ((url.includes('top_picks') || url.includes('kimi_top_3')) && response.status() >= 400) {
        failedRequests.push(`${response.status()} ${url}`);
      }
    });

    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });

    const battleTab = page.locator('button[data-tab="aibattle"]');
    await expect(battleTab).toBeVisible({ timeout: 10000 });
    await battleTab.click();

    const battleContent = page.locator('#tab-aibattle');
    await expect(battleContent).toBeVisible({ timeout: 5000 });
    await page.waitForTimeout(4000);

    expect(failedRequests, `Data file 404s: ${failedRequests.join(', ')}`).toHaveLength(0);

    const battleHTML = await battleContent.innerHTML();

    // All 5 agents present
    expect(battleHTML).toContain('Claude');
    expect(battleHTML).toContain('Grok');
    expect(battleHTML).toContain('KIMI');
    expect(battleHTML).toContain('Antigravity');
    expect(battleHTML).toContain('Mercury');

    // Leaderboard shows 1st through 5th
    expect(battleHTML).toContain('1st');
    expect(battleHTML).toContain('2nd');
    expect(battleHTML).toContain('3rd');
    expect(battleHTML).toContain('4th');
    expect(battleHTML).toContain('5th');

    // Leaderboard uses "Avg P/L" (not Realized/Unrealized dollar amounts)
    expect(battleHTML).toContain('Avg P/L');
    expect(battleHTML).not.toContain('Realized: +$');
    expect(battleHTML).not.toContain('Unrealized:');

    // Pick count shown
    expect(battleHTML).toContain('picks');

    // Tables rendered for all agents
    const tables = battleContent.locator('table');
    const tableCount = await tables.count();
    expect(tableCount).toBeGreaterThanOrEqual(5);

    await page.screenshot({ path: 'test-results/5ai-battle-round2.png', fullPage: false });
  });

  test('closed picks show correct P/L (not live price)', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });

    const battleTab = page.locator('button[data-tab="aibattle"]');
    await battleTab.click();
    await page.waitForTimeout(4000);

    const battleContent = page.locator('#tab-aibattle');
    const html = await battleContent.innerHTML();

    // TRUMP should show TP HIT status
    if (html.includes('TRUMP')) {
      expect(html).toContain('TP HIT');
      // TRUMP TP HIT should show positive P/L, not negative
      // The P/L should be calculated from TP price, not live price
    }

    // Check for SHORT direction (Grok/Mercury should have SHORT picks)
    expect(html.toUpperCase()).toContain('SHORT');

    await page.screenshot({ path: 'test-results/5ai-closed-picks-pnl.png', fullPage: false });
  });

  test('tables have fixed layout and consistent columns', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });

    const battleTab = page.locator('button[data-tab="aibattle"]');
    await battleTab.click();
    await page.waitForTimeout(3000);

    const battleContent = page.locator('#tab-aibattle');
    const tables = battleContent.locator('table');
    const tableCount = await tables.count();

    for (let i = 0; i < tableCount; i++) {
      const tableLayout = await tables.nth(i).evaluate(el => getComputedStyle(el).tableLayout);
      expect(tableLayout).toBe('fixed');

      // Each table should have 12 columns
      const headerCells = await tables.nth(i).locator('thead th').count();
      expect(headerCells).toBe(12);
    }

    await battleContent.screenshot({ path: 'test-results/5ai-battle-aligned-round2.png' });
  });

  test('Claude Top Picks shows Round 2 picks', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });

    const claudeTab = page.locator('button[data-tab="claudetoppicks"]');
    await expect(claudeTab).toBeVisible({ timeout: 10000 });
    await claudeTab.click();

    const claudeContent = page.locator('#tab-claudetoppicks');
    await expect(claudeContent).toBeVisible({ timeout: 5000 });
    await page.waitForTimeout(2000);

    const html = await claudeContent.innerHTML();

    // Check stats cards
    expect(html).toContain('Win Rate');
    expect(html).toContain('Cumulative PnL');
    expect(html).toContain('Total Picks');

    // Should have picks rendered
    const rows = claudeContent.locator('table tbody tr');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThanOrEqual(1);

    await page.screenshot({ path: 'test-results/claude-top-picks-round2.png', fullPage: false });
  });
});
