import { test, expect } from '@playwright/test';

const AUDIT_URL = 'https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit/';

test.describe('4-AI Battle Tab', () => {
  test('loads all 4 agents with picks data', async ({ page }) => {
    // Collect console errors
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    // Track failed network requests for our data files
    const failedRequests: string[] = [];
    page.on('response', response => {
      const url = response.url();
      if ((url.includes('grok_top_picks') || url.includes('kimi_top_3') || url.includes('claude_top_picks') || url.includes('antigravity_picks')) && response.status() >= 400) {
        failedRequests.push(`${response.status()} ${url}`);
      }
    });

    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });

    // Click the 4-AI Battle tab
    const battleTab = page.locator('button[data-tab="aibattle"]');
    await expect(battleTab).toBeVisible({ timeout: 10000 });
    await battleTab.click();

    // Wait for the battle content to render
    const battleContent = page.locator('#tab-aibattle');
    await expect(battleContent).toBeVisible({ timeout: 5000 });

    // Wait for data to load (fetches are async)
    await page.waitForTimeout(3000);

    // Check no 404s on data files
    expect(failedRequests, `Data file 404s: ${failedRequests.join(', ')}`).toHaveLength(0);

    // Check all 4 agent sections exist
    const battleHTML = await battleContent.innerHTML();
    expect(battleHTML).toContain('Claude');
    expect(battleHTML).toContain('Grok');
    expect(battleHTML).toContain('KIMI');
    expect(battleHTML).toContain('Antigravity');

    // Check Claude picks are populated (Round 2: BTC/ETH/XRP or Round 1: RENDER/TRUMP/SEI)
    const hasClaudePicks = battleHTML.includes('BTC') || battleHTML.includes('RENDER') || battleHTML.includes('TRUMP');
    expect(hasClaudePicks).toBeTruthy();

    // Check Grok picks are populated
    expect(battleHTML).toContain('BTC');
    // Grok should show SHORT direction
    expect(battleHTML.toUpperCase()).toContain('SHORT');

    // Check KIMI picks are populated
    const hasKimiPicks = battleHTML.includes('SOL') || battleHTML.includes('LINK') || battleHTML.includes('STRK');
    expect(hasKimiPicks).toBeTruthy();

    // Check leaderboard cards rendered (1st through 5th with Mercury)
    expect(battleHTML).toContain('1st');
    expect(battleHTML).toContain('2nd');
    expect(battleHTML).toContain('3rd');

    // Check table alignment - fixed layout applied
    const tables = battleContent.locator('table');
    const tableCount = await tables.count();
    expect(tableCount).toBeGreaterThanOrEqual(4); // One per agent

    // Take screenshot for visual verification
    await page.screenshot({ path: 'test-results/4ai-battle-tab.png', fullPage: false });

    // Log any console errors (non-blocking)
    if (errors.length > 0) {
      console.log('Console errors found:', errors);
    }
  });

  test('Claude Top Picks tab loads correctly', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });

    // Click Claude Top Picks tab
    const claudeTab = page.locator('button[data-tab="claudetoppicks"]');
    await expect(claudeTab).toBeVisible({ timeout: 10000 });
    await claudeTab.click();

    const claudeContent = page.locator('#tab-claudetoppicks');
    await expect(claudeContent).toBeVisible({ timeout: 5000 });
    await page.waitForTimeout(2000);

    const html = await claudeContent.innerHTML();

    // Check picks rendered (Round 2 or Round 1)
    const hasPicks = html.includes('BTC') || html.includes('RENDER') || html.includes('TRUMP');
    expect(hasPicks).toBeTruthy();

    // Check stats cards
    expect(html).toContain('Win Rate');
    expect(html).toContain('Cumulative PnL');

    await page.screenshot({ path: 'test-results/claude-top-picks-tab.png', fullPage: false });
  });

  test('table columns are aligned across all agents', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });

    const battleTab = page.locator('button[data-tab="aibattle"]');
    await battleTab.click();
    await page.waitForTimeout(3000);

    const battleContent = page.locator('#tab-aibattle');
    const tables = battleContent.locator('table');
    const tableCount = await tables.count();

    // All tables should have table-layout: fixed
    for (let i = 0; i < tableCount; i++) {
      const tableLayout = await tables.nth(i).evaluate(el => getComputedStyle(el).tableLayout);
      expect(tableLayout).toBe('fixed');
    }

    // Screenshot the full battle view
    await battleContent.screenshot({ path: 'test-results/4ai-battle-aligned.png' });
  });
});
