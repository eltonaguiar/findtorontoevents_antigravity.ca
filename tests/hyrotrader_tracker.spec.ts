/**
 * HyroTrader tracker: local /audit/hyrotrader/ loads JSON, renders rules + picks, no JS errors.
 * Run: npx playwright test tests/hyrotrader_tracker.spec.ts --project="Desktop Chrome"
 * Requires: python tools/serve_local.py (or Playwright webServer in playwright.config.ts)
 */
import { test, expect } from '@playwright/test';

const PICKS_URL = '/audit/data/hyrotrader_picks.json';
const JOURNAL_URL = '/audit/data/hyrotrader_journal.json';

test.describe('HyroTrader tracker — data quality & UI', () => {
  test('hyrotrader_picks.json is valid and matches UI expectations', async ({ request }) => {
    const res = await request.get(PICKS_URL);
    expect(res.ok(), `GET ${PICKS_URL} must be 200 (got ${res.status()})`).toBe(true);
    const data = (await res.json()) as Record<string, unknown>;
    const ch = data.challenge as Record<string, unknown> | undefined;
    expect(ch, 'challenge block required').toBeTruthy();
    expect(ch!.account_size_usdt, 'account_size_usdt').toBe(5000);
    expect(ch!.phase1_profit_target_usdt, 'P1 target USDT').toBe(500);
    expect(ch!.phase2_profit_target_usdt, 'P2 target USDT').toBe(250);
    expect(ch!.max_daily_loss_usdt, 'daily loss cap').toBe(250);
    expect(ch!.hyro_max_risk_per_trade_usdt, 'Hyro max risk').toBe(150);

    const picks = data.picks as unknown[];
    expect(picks.length, 'at least one planned pick').toBeGreaterThanOrEqual(1);
    expect(picks.length, 'expected 7 high-quality picks (v2 proven strategies)').toBe(7);

    for (let i = 0; i < picks.length; i++) {
      const p = picks[i] as Record<string, unknown>;
      expect(p.label, `pick[${i}].label`).toBeTruthy();
      expect(p.direction, `pick[${i}].direction`).toBeTruthy();
      expect(p.rank, `pick[${i}].rank`).toBeTruthy();
      expect(typeof p.stop_plan === 'string' && (p.stop_plan as string).length > 10, `pick[${i}].stop_plan`).toBe(true);
      expect(
        typeof p.take_profit_plan === 'string' && (p.take_profit_plan as string).length > 10,
        `pick[${i}].take_profit_plan`
      ).toBe(true);
      expect(['planned', 'active', 'open', 'closed'].includes(String(p.status || 'planned')), `pick[${i}].status`).toBe(true);
      const ep = p.entry_price;
      if ((p.status || 'planned') === 'planned' || p.status === 'active') {
        expect(ep == null, `pick[${i}]: planned/active picks must not invent entry_price`).toBe(true);
      }
    }
  });

  test('hyrotrader_journal.json is valid', async ({ request }) => {
    const res = await request.get(JOURNAL_URL);
    expect(res.ok(), `GET ${JOURNAL_URL} must be 200`).toBe(true);
    const j = (await res.json()) as { trades?: unknown[]; version?: number };
    expect(Array.isArray(j.trades)).toBe(true);
  });

  test('page loads with zero critical JS errors and shows data', async ({ page }) => {
    const errors: string[] = [];
    const critical = ['SyntaxError', 'Unexpected token', 'ReferenceError', 'TypeError', 'ChunkLoadError'];

    page.on('pageerror', (err) => {
      errors.push(`PageError: ${err.message}`);
    });
    page.on('console', (msg) => {
      if (msg.type() === 'error' && critical.some((c) => msg.text().includes(c))) {
        errors.push(`ConsoleError: ${msg.text()}`);
      }
    });

    await page.goto('/audit/hyrotrader/', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1500);

    await expect(page.locator('#load-err')).not.toBeVisible();

    const rules = page.locator('#challenge-rules');
    await expect(rules).toContainText('Phase 1');
    await expect(rules).toContainText('500 USDT');
    await expect(page.getByRole('heading', { name: /HyroTrader challenge tracker/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Live playbook signals/i })).toBeVisible();

    const pickRows = page.locator('#pick-rows tr');
    await expect(pickRows).toHaveCount(7);

    const firstRow = pickRows.first();
    await expect(firstRow).toContainText(/Bitcoin|BTC|LONG|SHORT|BOTH|CCI/i);
    await expect(page.locator('#pick-rows')).toContainText('SL');
    await expect(page.getByRole('heading', { name: /Progress & limits/i })).toBeVisible();

    await expect(page.getByRole('heading', { name: /Position size \(Hyro cap\)/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Budget snapshot/i })).toBeVisible();

    const journalEmpty = page.locator('#journal-empty');
    const journalWrap = page.locator('#journal-wrap');
    const emptyVisible = await journalEmpty.isVisible();
    const wrapVisible = await journalWrap.isVisible();
    expect(emptyVisible || wrapVisible, 'journal section: empty message or table').toBe(true);

    expect(errors, errors.join('\n')).toHaveLength(0);
  });
});
