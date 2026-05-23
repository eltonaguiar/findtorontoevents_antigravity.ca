/**
 * Live audit dashboard: zero critical JS errors while loading and switching tabs.
 * Targets production https://findtorontoevents.ca/audit/ (override with VERIFY_REMOTE_URL).
 *
 *   npx playwright test tests/audit_remote_tabs_no_errors.spec.ts --project="Desktop Chrome"
 *
 * To skip local webServer noise, use:
 *   VERIFY_REMOTE=1 npx playwright test tests/audit_remote_tabs_no_errors.spec.ts --project="Desktop Chrome"
 */
import { test, expect } from '@playwright/test';

const REMOTE_BASE = (process.env.VERIFY_REMOTE_URL || 'https://findtorontoevents.ca').replace(
  /\/$/,
  ''
);
const AUDIT_URL = `${REMOTE_BASE}/audit/`;

const criticalPatterns = [
  'SyntaxError',
  'Unexpected token',
  'ChunkLoadError',
  'denied by modsecurity',
  'Uncaught ',
  'ReferenceError',
  'TypeError',
];

function attachCriticalListeners(page: import('@playwright/test').Page, errors: string[]) {
  page.on('pageerror', (err) => {
    if (/Minified React error #418|418.*HTML/.test(err.message)) return;
    // Benign: tab switches / in-flight fetch aborts on heavy /audit/ page (not an app bug).
    if (/aborted a request|AbortError|ERR_ABORTED/i.test(err.message)) return;
    errors.push(`PageError: ${err.message}`);
  });
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const t = msg.text();
    if (criticalPatterns.some((p) => t.includes(p))) {
      errors.push(`ConsoleError: ${t}`);
    }
  });
}

test.describe('Live /audit/ — tab navigation, no critical JS errors', () => {
  test('load + Active / Closed / Overview / Smart Picks tabs; tables render; getVerifiedTier sane', async ({
    page,
  }) => {
    test.setTimeout(180000);
    const errors: string[] = [];
    attachCriticalListeners(page, errors);

    await page.goto(AUDIT_URL, { waitUntil: 'load', timeout: 120000 });

    // Large JSON parse + render; rows exist in DOM even when Overview tab is visible.
    await page.waitForSelector('#tab-active table.data-table tbody tr', {
      state: 'attached',
      timeout: 120000,
    });

    const edgeOk = await page.evaluate(() => {
      const w = window as unknown as {
        getVerifiedTier?: (p: { strategy?: string; symbol?: string }) => unknown;
        _verifiedEdgeIndex?: Record<string, unknown> | null;
      };
      if (typeof w.getVerifiedTier !== 'function') {
        return { ok: false, reason: 'getVerifiedTier is not a function' };
      }
      const idx = w._verifiedEdgeIndex;
      if (!idx || typeof idx !== 'object') {
        return { ok: false, reason: '_verifiedEdgeIndex is null or not an object' };
      }
      try {
        const r = w.getVerifiedTier({ strategy: 'claude_gainer_1h', symbol: 'BTCUSDT' }) as {
          tier?: unknown;
        };
        if (!r || typeof r !== 'object' || !('tier' in r)) {
          return { ok: false, reason: 'getVerifiedTier returned unexpected shape' };
        }
      } catch (e) {
        return { ok: false, reason: `getVerifiedTier threw: ${e}` };
      }
      return { ok: true as const, reason: '' };
    });
    expect(edgeOk.ok, edgeOk.reason || 'verified-edge check failed').toBe(true);

    const tabSequence = ['active', 'closed', 'overview', 'smartpicks'] as const;
    for (const tab of tabSequence) {
      await page.locator(`.tab-btn[data-tab="${tab}"]`).first().click();
      await page.waitForTimeout(2500);
      expect(errors, errors.join('\n')).toHaveLength(0);
    }

    // Active again: ensure table still there after round-trip
    await page.locator('.tab-btn[data-tab="active"]').first().click();
    await page.waitForTimeout(1500);
    const activeRows = await page.locator('#tab-active table.data-table tbody tr').count();
    expect(activeRows, 'Active Picks should have at least one row on live site').toBeGreaterThan(0);

    expect(errors, errors.length ? errors.join('\n') : '').toHaveLength(0);
  });
});
