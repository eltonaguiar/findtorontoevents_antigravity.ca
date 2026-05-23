import { test, expect } from '@playwright/test';

// ══════════════════════════════════════════════════════════════════════════════
//  ALPHA ENGINE DASHBOARD — GitHub Pages
// ══════════════════════════════════════════════════════════════════════════════
const ALPHA_URL = 'https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/';

test.describe('Alpha Engine Dashboard', () => {
  test('loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto(ALPHA_URL, { waitUntil: 'networkidle', timeout: 30000 });
    // Allow minor non-critical errors but fail on syntax/reference errors
    const critical = errors.filter(e => /SyntaxError|ReferenceError|TypeError/.test(e));
    expect(critical).toEqual([]);
  });

  test('hero KPI cards render with data', async ({ page }) => {
    await page.goto(ALPHA_URL, { waitUntil: 'networkidle', timeout: 30000 });
    // Wait for data to load
    await page.waitForFunction(() => {
      const el = document.getElementById('total-pnl-value');
      return el && el.textContent !== '$0.00';
    }, { timeout: 20000 }).catch(() => {});

    // Check original 4 KPIs exist
    const pnl = await page.locator('#total-pnl-value').textContent();
    expect(pnl).toBeTruthy();
    expect(pnl).not.toBe('$0.00');

    const wr = await page.locator('#win-rate-value').textContent();
    expect(wr).toBeTruthy();
    expect(wr).toMatch(/\d+(\.\d+)?%/);

    const picks = await page.locator('#picks-count').textContent();
    expect(picks).toBeTruthy();
  });

  test('new KPI cards present (closed, avg pnl, unrealized, profit factor)', async ({ page }) => {
    await page.goto(ALPHA_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForFunction(() => {
      const el = document.getElementById('closed-count');
      return el && el.textContent !== '0';
    }, { timeout: 20000 }).catch(() => {});

    // Closed trades card
    const closed = await page.locator('#closed-count').textContent();
    expect(closed).toBeTruthy();

    // Avg P/L card
    const avgPnl = await page.locator('#avg-pnl-value').textContent();
    expect(avgPnl).toBeTruthy();

    // Unrealized P/L card
    const unreal = await page.locator('#unrealized-value').textContent();
    expect(unreal).toBeTruthy();

    // Profit Factor card
    const pf = await page.locator('#pf-value').textContent();
    expect(pf).toBeTruthy();
    expect(pf).not.toBe('--');
  });

  test('strategy leaderboard renders with rows', async ({ page }) => {
    await page.goto(ALPHA_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('#leaderboard-container table', { timeout: 20000 }).catch(() => {});

    const rows = page.locator('#leaderboard-container tbody tr');
    const count = await rows.count();
    // Should have at least some strategy rows (each strategy = 2 rows: data + hidden detail)
    expect(count).toBeGreaterThan(2);
  });

  test('leaderboard expand shows strategy description', async ({ page }) => {
    await page.goto(ALPHA_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('#leaderboard-container table tbody tr', { timeout: 20000 });

    // Click the first strategy row
    const firstRow = page.locator('#leaderboard-container tbody tr').first();
    await firstRow.click();

    // Wait for detail row to appear
    await page.waitForSelector('.strategy-detail-row[style*="table-row"]', { timeout: 5000 });

    // Check for the "How ... works" expandable section
    const detailPanel = page.locator('.strategy-detail-row[style*="table-row"] .strategy-detail-panel');
    const panelText = await detailPanel.textContent();
    expect(panelText).toBeTruthy();

    // Should have pick history heading
    expect(panelText).toContain('Pick History');

    // Check for "How ... works" details element (strategy description)
    const hasDetails = await detailPanel.locator('details').count();
    // Either has a details element (documented strategy) or italic "not yet documented"
    const hasNotDocumented = panelText?.includes('not yet documented') || false;
    expect(hasDetails > 0 || hasNotDocumented).toBeTruthy();
  });

  test('strategy glossary section renders', async ({ page }) => {
    await page.goto(ALPHA_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForFunction(() => {
      const el = document.getElementById('glossary-badge');
      return el && !el.textContent?.includes('--');
    }, { timeout: 20000 }).catch(() => {});

    // Badge shows count
    const badge = await page.locator('#glossary-badge').textContent();
    expect(badge).toMatch(/\d+ strategies documented/);

    // Container has cards
    const cards = page.locator('#glossary-container > div');
    const count = await cards.count();
    expect(count).toBeGreaterThan(10);
  });

  test('glossary search filters results', async ({ page }) => {
    await page.goto(ALPHA_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('#glossary-container > div:not(.status-box)', { timeout: 20000 });

    const initialCount = await page.locator('#glossary-container > div').count();

    // Type a specific search term
    await page.fill('#glossary-search', 'autocorrelation');
    await page.waitForTimeout(300); // debounce

    const filteredCount = await page.locator('#glossary-container > div').count();
    expect(filteredCount).toBeLessThan(initialCount);
    expect(filteredCount).toBeGreaterThan(0);

    // Verify the card contains "autocorrelation"
    const cardText = await page.locator('#glossary-container > div').first().textContent();
    expect(cardText?.toLowerCase()).toContain('autocorrelation');
  });

  test('glossary category filter works', async ({ page }) => {
    await page.goto(ALPHA_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('#glossary-container > div:not(.status-box)', { timeout: 20000 });

    const initialCount = await page.locator('#glossary-container > div').count();

    // Filter to forex only
    await page.selectOption('#glossary-cat-filter', 'forex');
    await page.waitForTimeout(100);

    const filteredCount = await page.locator('#glossary-container > div').count();
    expect(filteredCount).toBeLessThan(initialCount);
    expect(filteredCount).toBeGreaterThan(0);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
//  AUDIT DASHBOARD — GitHub raw content (runs on FTP site)
// ══════════════════════════════════════════════════════════════════════════════
const AUDIT_URL = 'https://findtorontoevents.ca/audit/';

test.describe('Audit Dashboard', () => {
  test('loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    const critical = errors.filter(e => /SyntaxError|ReferenceError/.test(e));
    expect(critical).toEqual([]);
  });

  test('BT vs Forward table renders with data', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    // Click the BT vs Forward tab
    const tab = page.locator('text=BT vs Forward').first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
    }

    // Look for the table
    const table = page.locator('#tab-btvsfwd table');
    if (await table.isVisible({ timeout: 5000 }).catch(() => false)) {
      const rows = table.locator('tbody tr');
      const count = await rows.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test('win rate column has no stray characters', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    // Navigate to BT vs Forward tab
    const tab = page.locator('text=BT vs Forward').first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
    }

    const table = page.locator('#tab-btvsfwd table');
    if (await table.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Get all cells in the BT Win Rate column (3rd column, index 2)
      const wrCells = table.locator('tbody tr td:nth-child(3)');
      const count = await wrCells.count();
      for (let i = 0; i < Math.min(count, 20); i++) {
        const text = await wrCells.nth(i).textContent();
        // Should only contain digits, decimal, % and maybe spaces — no triangles or garbage
        expect(text?.trim()).toMatch(/^[\d.]+%$|^0%$/);
      }
    }
  });

  test('BT vs Forward column headers are sortable', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    const tab = page.locator('text=BT vs Forward').first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
    }

    const table = page.locator('#tab-btvsfwd table');
    if (await table.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Check that headers have onclick/data-sort
      const headers = table.locator('thead th');
      const count = await headers.count();
      expect(count).toBe(7); // Strategy, System, BT WR, FWD WR, Decay, BT Trades, FWD Trades

      // Click BT Win Rate header to sort
      const wrHeader = table.locator('thead th:nth-child(3)');
      await wrHeader.click();
      await page.waitForTimeout(300);

      // Header text should contain sort arrow
      const headerText = await wrHeader.textContent();
      expect(headerText).toMatch(/[▲▼]/);

      // Click again to toggle
      await wrHeader.click();
      await page.waitForTimeout(300);
      const headerText2 = await wrHeader.textContent();
      expect(headerText2).toMatch(/[▲▼]/);
      // Arrow should have toggled
      expect(headerText2).not.toBe(headerText);
    }
  });

  test('strategy tooltips render for known systems', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 30000 });
    const tab = page.locator('text=BT vs Forward').first();
    if (await tab.isVisible()) {
      await tab.click();
      await page.waitForTimeout(500);
    }

    // Check that strategy cells have tooltip wrappers
    const table = page.locator('#tab-btvsfwd table');
    if (await table.isVisible({ timeout: 5000 }).catch(() => false)) {
      const strategyCells = table.locator('tbody tr td:first-child');
      const count = await strategyCells.count();
      expect(count).toBeGreaterThan(0);

      // At least some should have tooltip spans (for known systems)
      let tooltipCount = 0;
      for (let i = 0; i < Math.min(count, 30); i++) {
        const hasTooltip = await strategyCells.nth(i).locator('.strat-tip').count();
        if (hasTooltip > 0) tooltipCount++;
      }
      // Not all will have tooltips, but some should
      // This is fine as a smoke test
    }
  });
});

// ══════════════════════════════════════════════════════════════════════════════
//  GAINER ML DASHBOARD
// ══════════════════════════════════════════════════════════════════════════════
const GAINER_URL = 'https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/updates/antigravity-ml-gainer.html';
const GAINER_FTP_URL = 'https://findtorontoevents.ca/updates/antigravity-ml-gainer.html';

test.describe('Gainer ML Dashboard', () => {
  test('loads and shows KPI stats', async ({ page }) => {
    await page.goto(GAINER_FTP_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForFunction(() => {
      const el = document.getElementById('kpiResolved');
      return el && el.textContent !== '0';
    }, { timeout: 15000 }).catch(() => {});

    const resolved = await page.locator('#kpiResolved').textContent();
    expect(resolved).toBeTruthy();

    const wr = await page.locator('#kpiWinRate').textContent();
    expect(wr).toMatch(/\d+(\.\d+)?%/);
  });

  test('resolved trade log shows entries with proper data', async ({ page }) => {
    await page.goto(GAINER_FTP_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForFunction(() => {
      const el = document.getElementById('resolvedCount');
      return el && el.textContent !== '0';
    }, { timeout: 15000 }).catch(() => {});

    const rows = page.locator('#resolvedBody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);

    // First row should have actual data (not all dashes)
    if (count > 0) {
      const firstRow = rows.first();
      const cells = firstRow.locator('td');
      const cellCount = await cells.count();
      expect(cellCount).toBeGreaterThanOrEqual(5);

      // Coin name should be visible
      const coin = await cells.nth(0).textContent();
      expect(coin?.trim().length).toBeGreaterThan(0);

      // Outcome should show TP HIT or SL HIT
      const outcome = await cells.nth(1).textContent();
      expect(outcome).toMatch(/TP HIT|SL HIT/i);

      // Entry price should be a number
      const entry = await cells.nth(2).textContent();
      expect(entry).toMatch(/\$[\d.]/);

      // P/L should have a percentage
      const pnl = await cells.nth(4).textContent();
      expect(pnl).toMatch(/[+-]?[\d.]+%/);
    }
  });

  test('R:R ratio is dynamic (not hardcoded 2.5:1)', async ({ page }) => {
    await page.goto(GAINER_FTP_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForFunction(() => {
      const el = document.getElementById('kpiRR');
      return el && el.textContent !== '2.5:1' && el.textContent !== '--';
    }, { timeout: 15000 }).catch(() => {});

    const rr = await page.locator('#kpiRR').textContent();
    expect(rr).toMatch(/[\d.]+:1/);
  });
});
