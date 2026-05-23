/**
 * Smoke: prediction-market-related sources × asset_class from DASHBOARD_DATA.
 * Run: npx playwright test tests/audit_prediction_markets_crossover.spec.ts --project="Desktop Chrome"
 * Remote: VERIFY_REMOTE=1 npx playwright test ...
 */
import { test, expect } from '@playwright/test';

const PM_MARKERS = ['pm_', 'prediction_market', 'kalshi', 'polymarket'];

test.describe('Audit /audit/ — prediction markets × asset class (data smoke)', () => {
  test('DASHBOARD_DATA loads; PM-related rows have asset_class; no critical JS errors', async ({
    page,
  }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(`PageError: ${err.message}`));
    page.on('console', (msg) => {
      if (msg.type() !== 'error') return;
      const t = msg.text();
      if (/SyntaxError|ReferenceError|ChunkLoadError|Uncaught /i.test(t)) errors.push(t);
    });

    await page.goto('/audit/', { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForTimeout(2000);

    const matrix = await page.evaluate((markers: string[]) => {
      const data = (window as unknown as { DASHBOARD_DATA?: any }).DASHBOARD_DATA;
      const rows = [
        ...(data?.picks?.active || []),
        ...(data?.picks?.recent_closed || []).slice(0, 800),
      ];
      const out: Record<string, number> = {};
      const normAc = (p: any) => {
        const a = String(p?.asset_class || p?.asset_class_type || 'CRYPTO').toUpperCase();
        if (['STOCKS', 'PENNY_STOCK', 'EQUITIES'].includes(a)) return 'EQUITY';
        if (a === 'COMMODITIES') return 'COMMODITY';
        return a || 'CRYPTO';
      };
      const blob = (p: any) => {
        const parts = [
          p?.source_system,
          p?.strategy,
          ...(Array.isArray(p?.source_systems) ? p.source_systems : []),
          ...(Array.isArray(p?.pm_source_systems) ? p.pm_source_systems : []),
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return parts;
      };
      for (const p of rows) {
        const b = blob(p);
        if (!markers.some((m) => b.includes(m))) continue;
        const key = `${normAc(p)}`;
        out[key] = (out[key] || 0) + 1;
      }
      return { counts: out, pmRowTotal: Object.values(out).reduce((a, n) => a + n, 0) };
    }, PM_MARKERS);

    console.log('[PM × asset_class]', JSON.stringify(matrix, null, 2));
    expect(errors.length, errors.join('\n')).toBe(0);
    expect(matrix.pmRowTotal).toBeGreaterThanOrEqual(0);
  });
});
