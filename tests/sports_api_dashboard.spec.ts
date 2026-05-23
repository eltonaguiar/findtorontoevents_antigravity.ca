/**
 * Public sports dashboard JSON (no auth). Catches regressions in stale-pending + core metrics keys.
 * Run: npx playwright test tests/sports_api_dashboard.spec.ts
 * Override: SPORTS_DASHBOARD_URL=https://...
 */
import { test, expect } from '@playwright/test';

const DASHBOARD_URL =
  process.env.SPORTS_DASHBOARD_URL ||
  'https://findtorontoevents.ca/live-monitor/api/sports_bets.php?action=dashboard';

test('sports_bets dashboard JSON has required keys', async ({ request }) => {
  const res = await request.get(DASHBOARD_URL);
  expect(res.ok(), `dashboard HTTP ${res.status()} for ${DASHBOARD_URL}`).toBe(true);
  const d = await res.json();
  expect(d.ok, 'dashboard ok field').toBe(true);

  for (const k of [
    'bankroll',
    'clv_quadrants',
    'by_market',
    'pending_exposure_by_sport',
    'risk_budget',
    'by_sport',
    'pending_stale_14d_count',
    'pending_stale_14d_stake',
    'oldest_stale_pending_commence',
    'stale_pending_hint',
    'win_rate_quality',
    'cohort_guardrail_v1',
    'since_policy_fix',
  ]) {
    expect(d, `missing ${k}`).toHaveProperty(k);
  }

  expect(typeof d.pending_stale_14d_count).toBe('number');
  expect(typeof d.pending_stale_14d_stake).toBe('number');

  const wq = d.win_rate_quality as Record<string, unknown>;
  for (const k of ['wilson_95_low_pct', 'wilson_95_high_pct', 'directional_n', 'small_sample']) {
    expect(wq, `win_rate_quality.${k}`).toHaveProperty(k);
  }
  const cg = d.cohort_guardrail_v1 as Record<string, unknown>;
  for (const k of [
    'cohort',
    'algorithm',
    'directional_n',
    'wins',
    'losses',
    'pushes',
    'voids',
    'win_rate_pct',
    'wilson_95_low_pct',
    'wilson_95_high_pct',
    'total_pnl',
    'roi_pct',
  ]) {
    expect(cg, `cohort_guardrail_v1.${k}`).toHaveProperty(k);
  }

  const spf = d.since_policy_fix as Record<string, unknown>;
  for (const k of [
    'cohort',
    'settled_tickets',
    'wins',
    'losses',
    'pushes',
    'voids',
    'directional_n',
    'win_rate_pct',
    'total_pnl',
    'roi_pct',
    'caption',
  ]) {
    expect(spf, `since_policy_fix.${k}`).toHaveProperty(k);
  }
  const wrq2 = spf.win_rate_quality as Record<string, unknown>;
  for (const k of ['wilson_95_low_pct', 'wilson_95_high_pct', 'directional_n', 'small_sample']) {
    expect(wrq2, `since_policy_fix.win_rate_quality.${k}`).toHaveProperty(k);
  }
});
