import { test, expect } from '@playwright/test';

/**
 * active_picks_count — smoke test for the post-2026-04-18 filter-chain tightening.
 *
 * Thresholds (adjust as filter behavior evolves):
 *  - MIN_ACTIVE_PICKS: 20 is the conservative lower bound we expect AFTER retiring
 *    3 dead strategies + blocking MATIC + freshness-gating 48 stale sources.
 *    Below 20 => regression or over-pruning by another agent.
 *  - MIN_RAW_PICKS: 200 — the unfiltered pool should always be deep; if raw drops
 *    that low the scanners themselves have stopped, not just the filter.
 *  - MAX_ATTRITION_PCT: 90 — filtering more than 90% of raw->active suggests
 *    a filter mis-configuration rather than healthy quality gating.
 *
 * Run: npx playwright test tests/active_picks_count.spec.ts
 */

const SITE = 'https://findtorontoevents.ca/audit/';
const DATA = 'https://findtorontoevents.ca/audit/data/dashboard_data.json';
const MIN_ACTIVE_PICKS = 20;
const MIN_RAW_PICKS = 200;
const MAX_ATTRITION_PCT = 90;

test('dashboard JSON has healthy active-pick count', async ({ request }) => {
  const res = await request.get(DATA);
  expect(res.ok(), 'dashboard_data.json must be reachable').toBeTruthy();
  const data = await res.json();

  const active = (data?.picks?.active ?? []) as any[];
  const raw    = (data?.picks?.active_raw ?? []) as any[];
  const genAt  = data?.generated_at;

  console.log(`[active_picks_count] generated_at=${genAt}`);
  console.log(`[active_picks_count] active=${active.length} raw=${raw.length}`);

  expect(raw.length, `raw pool too shallow (<${MIN_RAW_PICKS}) — scanner pipeline may be failing`).toBeGreaterThanOrEqual(MIN_RAW_PICKS);
  expect(active.length, `active picks too few (<${MIN_ACTIVE_PICKS}) — filter over-pruned?`).toBeGreaterThanOrEqual(MIN_ACTIVE_PICKS);

  const attrition = 100 * (1 - active.length / raw.length);
  console.log(`[active_picks_count] attrition=${attrition.toFixed(1)}%`);
  expect(attrition, `attrition ${attrition.toFixed(1)}% > ${MAX_ATTRITION_PCT}% — filter mis-configured`).toBeLessThanOrEqual(MAX_ATTRITION_PCT);
});

test('dashboard HTML renders Active Picks without crashing', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('pageerror', err => consoleErrors.push(`pageerror: ${err.message}`));
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(`console.error: ${msg.text()}`);
  });

  await page.goto(SITE, { waitUntil: 'domcontentloaded' });
  // Wait for the Active Picks table header or its count badge to appear.
  await page.waitForSelector('text=/Active Picks/i', { timeout: 30000 });

  // Extract the displayed count from the label "Active Picks (N)".
  const label = await page.locator('text=/Active Picks \\(\\d+\\)/i').first().textContent();
  console.log(`[active_picks_count] UI label="${label}"`);
  const m = label?.match(/\((\d+)\)/);
  expect(m, 'Active Picks (N) badge missing').toBeTruthy();
  const displayedCount = parseInt(m![1], 10);
  console.log(`[active_picks_count] displayed count=${displayedCount}`);
  expect(displayedCount, `UI displayed only ${displayedCount} active picks (<${MIN_ACTIVE_PICKS})`).toBeGreaterThanOrEqual(MIN_ACTIVE_PICKS);

  expect(consoleErrors, `page errors: ${consoleErrors.join(' | ')}`).toEqual([]);
});
