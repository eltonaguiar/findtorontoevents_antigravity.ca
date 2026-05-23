import { test, expect } from '@playwright/test';

/**
 * Live /audit/ quant snapshot: DASHBOARD_DATA PnL distribution + anomaly counts.
 * Plan: audit_dashboard_quant_review — instrumented audit against production.
 */

const AUDIT_URL = 'https://findtorontoevents.ca/audit/';

test.describe('Live audit /audit/ — DASHBOARD_DATA quant snapshot', () => {
  test('loads with zero page/console errors and reports PnL histogram signals', async ({
    page,
  }) => {
    const errors: string[] = [];
    const critical = (s: string) =>
      /SyntaxError|ChunkLoadError|modsecurity|Unexpected token/i.test(s) ||
      /denied by modsecurity/i.test(s);

    page.on('pageerror', (err) => {
      const s = `PageError: ${err.message}`;
      if (critical(s)) errors.push(s);
    });
    page.on('console', (msg) => {
      if (msg.type() !== 'error') return;
      const t = msg.text();
      if (/Failed to load resource.*404|favicon|net::ERR/i.test(t)) return;
      if (critical(t)) errors.push(`ConsoleError: ${t}`);
    });

    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 120000 });
    await page
      .waitForFunction(
        () => {
          const W = window as Window & { DASHBOARD_DATA?: { picks?: { active?: unknown[] } } };
          return (
            !!W.DASHBOARD_DATA &&
            !!W.DASHBOARD_DATA.picks &&
            Array.isArray(W.DASHBOARD_DATA.picks.active)
          );
        },
        { timeout: 90000 }
      )
      .catch(() => {});
    await page.waitForTimeout(2500);

    const snapshot = await page.evaluate(() => {
      function summarizePnls(rows: Array<Record<string, unknown>>) {
        let zero = 0;
        let nullish = 0;
        let over50 = 0;
        let over500 = 0;
        let min = Infinity;
        let max = -Infinity;
        for (const p of rows) {
          const raw = p.net_pnl_pct ?? p.pnl_pct;
          if (raw === null || raw === undefined || raw === '') {
            nullish++;
            continue;
          }
          const v = typeof raw === 'number' ? raw : parseFloat(String(raw));
          if (!Number.isFinite(v)) {
            nullish++;
            continue;
          }
          if (Math.abs(v) < 1e-9) zero++;
          if (Math.abs(v) > 50) over50++;
          if (Math.abs(v) > 500) over500++;
          min = Math.min(min, v);
          max = Math.max(max, v);
        }
        return {
          n: rows.length,
          zero,
          nullish,
          over50,
          over500,
          min: Number.isFinite(min) ? min : 0,
          max: Number.isFinite(max) ? max : 0,
        };
      }

      const W = window as Window &
        typeof globalThis & { DASHBOARD_DATA?: Record<string, unknown> };
      const D = W.DASHBOARD_DATA;
      if (!D || typeof D !== 'object')
        return { ok: false as const, reason: 'DASHBOARD_DATA missing' };
      const picks = (D.picks || {}) as {
        active?: unknown[];
        recent_closed?: unknown[];
      };
      const active = Array.isArray(picks.active) ? picks.active : [];
      const closed = Array.isArray(picks.recent_closed) ? picks.recent_closed : [];
      const summary = (D.summary || {}) as Record<string, unknown>;
      const nc = summary.non_crypto_performance as
        | { categories?: Record<string, { closed?: number }>; aggregate?: { closed?: number } }
        | undefined;

      function clientNcKey(p: Record<string, unknown>): string | null {
        const ac = String(p.asset_class || '').toUpperCase();
        const cat = String(p.category || '').toUpperCase();
        const sym = String(p.symbol || '').toUpperCase();
        if (ac === 'FOREX' || cat === 'FOREX' || sym.includes('=X')) return 'FOREX';
        if (
          ac === 'EQUITY' ||
          ac === 'STOCK' ||
          cat === 'EQUITY' ||
          cat === 'STOCK' ||
          cat === 'STOCKS'
        )
          return 'EQUITY';
        if (
          ac === 'COMMODITY' ||
          cat === 'COMMODITY' ||
          cat === 'COMMODITIES' ||
          sym.startsWith('XAG') ||
          sym.startsWith('XAU')
        )
          return 'COMMODITY';
        if (ac === 'FUTURES' || cat === 'FUTURES' || cat === 'FUTURE') return 'FUTURES';
        if (ac === 'ETF' || cat === 'ETF') return 'ETF';
        return null;
      }

      const closedRows = closed.filter((x) => x && typeof x === 'object') as Record<
        string,
        unknown
      >[];
      const byClient: Record<string, number> = {};
      for (const p of closedRows) {
        const k = clientNcKey(p);
        if (k) byClient[k] = (byClient[k] || 0) + 1;
      }

      return {
        ok: true as const,
        activeCount: active.length,
        closedCount: closed.length,
        summaryKeys: Object.keys(summary).slice(0, 30),
        smartPct: summary.quality_stats,
        closedPnl: summarizePnls(closedRows),
        activePnl: summarizePnls(
          active.filter((x) => x && typeof x === 'object') as Record<string, unknown>[]
        ),
        ncCategories: nc?.categories
          ? Object.fromEntries(
              Object.entries(nc.categories).map(([k, v]) => [k, (v as { closed?: number }).closed ?? 0])
            )
          : null,
        ncClientClosedByKey: byClient,
      };
    });

    expect(errors, errors.join('\n')).toHaveLength(0);
    expect(snapshot.ok, JSON.stringify(snapshot)).toBe(true);
    if (snapshot.ok) {
      // eslint-disable-next-line no-console
      console.log('[audit quant snapshot]', JSON.stringify(snapshot, null, 2));
      expect(snapshot.closedCount).toBeGreaterThan(0);
      expect(snapshot.activeCount).toBeGreaterThan(0);
    }
  });
});
