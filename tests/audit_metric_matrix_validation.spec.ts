import { test, expect, Page } from '@playwright/test';

const AUDIT_URL = process.env.AUDIT_URL
  ? process.env.AUDIT_URL
  : (process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true')
    ? 'https://findtorontoevents.ca/audit/'
    : '/audit_dashboard/';
const IS_REMOTE_VERIFY =
  process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true';

const ASSET_CLASSES = ['CRYPTO', 'EQUITY', 'FOREX', 'COMMODITY', 'FUTURES'];

type ExpectedSummary = {
  activeCount: number;
  closedCount: number;
  wins: number;
  losses: number;
  winRate: number;
  totalPnl: number;
  profitFactor: number;
  expectancy: number;
  systems: number;
};

async function gotoAudit(page: Page) {
  await page.goto(AUDIT_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(1500);
}

async function clearFilters(page: Page) {
  await page.locator('#btn-clear-filters').click();
  await page.waitForTimeout(400);
}

async function getSummaryMap(page: Page) {
  return page.$$eval('#summary-cards .stat-card', cards => {
    const out: Record<string, string> = {};
    for (const card of cards) {
      const label = card.querySelector('.label')?.textContent?.trim() || '';
      const value = card.querySelector('.value')?.textContent?.trim() || '';
      if (label) out[label] = value;
    }
    return out;
  });
}

function getMetricValue(summary: Record<string, string>, labelContains: string) {
  const key = Object.keys(summary).find(k => k.includes(labelContains));
  if (!key) throw new Error(`Missing summary metric containing "${labelContains}"`);
  return summary[key];
}

function parseNumeric(text: string) {
  if (text.trim() === '∞') return Number.POSITIVE_INFINITY;
  const cleaned = text.replace(/,/g, '').replace(/[^0-9.+-]/g, '');
  return cleaned ? Number(cleaned) : 0;
}

async function getHeadingCount(page: Page, selector: string) {
  const text = (await page.locator(selector).first().textContent()) || '';
  const match = text.match(/\((\d+)\)/);
  return Number(match?.[1] || 0);
}

async function getDashboardState(page: Page) {
  return page.evaluate(() => {
    const anyWindow = window as any;
    return {
      scoreTier: (document.getElementById('f-score-tier') as HTMLSelectElement | null)?.value || '',
      asset: (document.getElementById('f-asset') as HTMLSelectElement | null)?.value || '',
      hiddenFlags: {
        provenOnly: Boolean(anyWindow._provenOnlyFilter),
        scoreGate: Boolean(anyWindow._scoreGateFilter),
        showTpHits: Boolean(anyWindow._showTpHitPicks),
        tradeWorthy: Boolean(anyWindow._tradeWorthyFilter),
        leverageWorthy: Boolean(anyWindow._leverageWorthyFilter),
        smartPickActive: Boolean(anyWindow._smartPickState?.active),
      },
    };
  });
}

async function computeExpectedSummary(page: Page): Promise<ExpectedSummary> {
  return page.evaluate(() => {
    const anyWindow = window as any;
    const data = anyWindow.DASHBOARD_DATA || {};
    const summary = data.summary || {};
    const filters = typeof anyWindow.getFilters === 'function'
      ? anyWindow.getFilters()
      : {
          asset: (document.getElementById('f-asset') as HTMLSelectElement | null)?.value || '',
          system: (document.getElementById('f-system') as HTMLSelectElement | null)?.value || '',
          status: (document.getElementById('f-status') as HTMLSelectElement | null)?.value || '',
          dir: (document.getElementById('f-dir') as HTMLSelectElement | null)?.value || '',
          search: ((document.getElementById('f-search') as HTMLInputElement | null)?.value || '').toUpperCase(),
          pnl: (document.getElementById('f-pnl') as HTMLSelectElement | null)?.value || '',
          conf: (document.getElementById('f-conf') as HTMLSelectElement | null)?.value || '',
          age: (document.getElementById('f-age') as HTMLSelectElement | null)?.value || '',
          tpRem: (document.getElementById('f-tp-rem') as HTMLSelectElement | null)?.value || '',
          sort: (document.getElementById('f-sort') as HTMLSelectElement | null)?.value || '',
          conflicts: (document.getElementById('f-conflicts') as HTMLSelectElement | null)?.value || '',
          timeframe: (document.getElementById('f-timeframe') as HTMLSelectElement | null)?.value || '',
        };

    const scoreTier = (document.getElementById('f-score-tier') as HTMLSelectElement | null)?.value || '';
    const provenOnly = Boolean(anyWindow._provenOnlyFilter);
    const scoreGate = Boolean(anyWindow._scoreGateFilter);
    const showTpHits = Boolean(anyWindow._showTpHitPicks);

    const hasFilters = Boolean(
      filters.asset ||
      filters.system ||
      filters.status ||
      filters.dir ||
      filters.search ||
      filters.pnl ||
      filters.conf ||
      filters.age ||
      filters.tpRem ||
      filters.conflicts ||
      provenOnly ||
      scoreGate ||
      scoreTier
    );

    const getBaseVisibleActivePicks = anyWindow.getBaseVisibleActivePicks;
    const getBaseVisibleClosedPicks = anyWindow.getBaseVisibleClosedPicks;
    const matchFilter = anyWindow.matchFilter;
    const getTrustTier = anyWindow.getTrustTier;
    if (typeof getBaseVisibleActivePicks !== 'function' ||
        typeof getBaseVisibleClosedPicks !== 'function' ||
        typeof matchFilter !== 'function' ||
        typeof getTrustTier !== 'function') {
      throw new Error('Dashboard helper functions unavailable for audit validation');
    }

    let activePicks = getBaseVisibleActivePicks({ showTpHits });
    let closedPicks = getBaseVisibleClosedPicks();

    if (hasFilters) {
      activePicks = activePicks.filter((p: any) => matchFilter(p, filters));
      closedPicks = closedPicks.filter((p: any) => matchFilter(p, filters));
    }
    if (provenOnly) {
      activePicks = activePicks.filter((p: any) => {
        const tier = getTrustTier(p)?.tier;
        return tier === 'PROVEN' || tier === 'RELIABLE';
      });
      closedPicks = closedPicks.filter((p: any) => {
        const tier = getTrustTier(p)?.tier;
        return tier === 'PROVEN' || tier === 'RELIABLE';
      });
    }
    if (scoreGate) {
      activePicks = activePicks.filter((p: any) => (p.score || 0) >= 24);
      closedPicks = closedPicks.filter((p: any) => (p.score || 0) >= 24);
    }
    if (scoreTier === 'noise') {
      activePicks = activePicks.filter((p: any) => (p.score || 0) < 30);
      closedPicks = closedPicks.filter((p: any) => (p.score || 0) < 30);
    } else if (scoreTier === 'paper') {
      activePicks = activePicks.filter((p: any) => {
        const score = p.score || 0;
        return score >= 30 && score < 50;
      });
      closedPicks = closedPicks.filter((p: any) => {
        const score = p.score || 0;
        return score >= 30 && score < 50;
      });
    } else if (scoreTier === 'trade') {
      activePicks = activePicks.filter((p: any) => (p.score || 0) >= 50);
      closedPicks = closedPicks.filter((p: any) => (p.score || 0) >= 50);
    } else if (scoreTier === 'conviction') {
      activePicks = activePicks.filter((p: any) => (p.score || 0) >= 70);
      closedPicks = closedPicks.filter((p: any) => (p.score || 0) >= 70);
    }

    const wins = closedPicks.filter((p: any) => (p.pnl_pct || 0) > 0).length;
    const losses = closedPicks.filter((p: any) => (p.pnl_pct || 0) < 0).length;
    const resolved = wins + losses;
    const cap500 = (value: number) => Math.max(-500, Math.min(500, value || 0));
    const totalPnl = closedPicks.length > 0
      ? closedPicks.reduce((sum: number, pick: any) => sum + cap500(pick.pnl_pct), 0)
      : (hasFilters ? 0 : (summary.total_pnl_pct || 0));
    const winPnl = closedPicks
      .filter((p: any) => (p.pnl_pct || 0) > 0)
      .reduce((sum: number, pick: any) => sum + cap500(pick.pnl_pct), 0);
    const lossPnl = Math.abs(
      closedPicks
        .filter((p: any) => (p.pnl_pct || 0) < 0)
        .reduce((sum: number, pick: any) => sum + cap500(pick.pnl_pct), 0)
    );
    const profitFactor = lossPnl > 0 ? winPnl / lossPnl : (winPnl > 0 ? Number.POSITIVE_INFINITY : 0);
    const expectancy = closedPicks.length > 0 ? totalPnl / closedPicks.length : 0;
    const visibleSystems = new Set(activePicks.map((p: any) => p.source_system)).size;
    const systems = hasFilters ? visibleSystems : (summary.total_systems || 0);
    const winRate = resolved > 0 ? (wins / resolved * 100) : (hasFilters ? 0 : (summary.overall_win_rate || 0));

    return {
      activeCount: activePicks.length,
      closedCount: hasFilters ? closedPicks.length : (summary.total_closed_picks || 0),
      wins,
      losses,
      winRate,
      totalPnl,
      profitFactor,
      expectancy,
      systems,
    };
  });
}

async function assertSummaryMatchesExpected(page: Page, expected: ExpectedSummary) {
  const summary = await getSummaryMap(page);
  expect(parseNumeric(getMetricValue(summary, 'Active Picks'))).toBe(expected.activeCount);
  expect(parseNumeric(getMetricValue(summary, 'Closed Picks'))).toBe(expected.closedCount);
  expect(parseNumeric(getMetricValue(summary, 'Systems'))).toBe(expected.systems);
  expect(getMetricValue(summary, 'W / L')).toBe(`${expected.wins} / ${expected.losses}`);

  const uiWinRate = parseNumeric(getMetricValue(summary, 'Win Rate'));
  const uiTotalPnl = parseNumeric(getMetricValue(summary, 'Total PnL'));
  const uiExpectancy = parseNumeric(getMetricValue(summary, 'Expectancy'));
  const uiProfitFactor = parseNumeric(getMetricValue(summary, 'Profit Factor'));

  expect(Math.abs(uiWinRate - expected.winRate)).toBeLessThanOrEqual(0.11);
  expect(Math.abs(uiTotalPnl - expected.totalPnl)).toBeLessThanOrEqual(0.02);
  expect(Math.abs(uiExpectancy - expected.expectancy)).toBeLessThanOrEqual(0.02);

  if (!Number.isFinite(expected.profitFactor)) {
    expect(uiProfitFactor).toBe(Number.POSITIVE_INFINITY);
  } else {
    expect(Math.abs(uiProfitFactor - expected.profitFactor)).toBeLessThanOrEqual(0.02);
  }
}

test.describe('Audit Dashboard Metric Matrix Validation', () => {
  test.describe.configure({ timeout: 120000 });

  test.beforeEach(async ({ page }) => {
    if (!IS_REMOTE_VERIFY) {
      await page.route('**/*', route => {
        const url = route.request().url();
        if (
          url.startsWith('http://localhost:5173') ||
          url.startsWith('http://127.0.0.1:5173') ||
          url.startsWith('data:')
        ) {
          return route.continue();
        }
        return route.abort();
      });
    }
    await gotoAudit(page);
  });

  test('default load matches cleared filters and starts unfiltered', async ({ page }) => {
    const defaultState = await getDashboardState(page);

    expect(defaultState.scoreTier).toBe('');
    expect(defaultState.asset).toBe('');
    expect(defaultState.hiddenFlags).toEqual({
      provenOnly: false,
      scoreGate: false,
      showTpHits: false,
      tradeWorthy: false,
      leverageWorthy: false,
      smartPickActive: false,
    });

    if (IS_REMOTE_VERIFY) {
      await clearFilters(page);
      const clearedState = await getDashboardState(page);
      expect(clearedState.scoreTier).toBe('');
      expect(clearedState.asset).toBe('');
      expect(clearedState.hiddenFlags).toEqual(defaultState.hiddenFlags);

      const summary = await getSummaryMap(page);
      const summaryActive = parseNumeric(getMetricValue(summary, 'Active Picks'));
      const summarySystems = parseNumeric(getMetricValue(summary, 'Systems'));
      expect(summaryActive).toBe(await getHeadingCount(page, '#tab-active h2'));
      expect(summaryActive).toBeGreaterThan(0);
      expect(summarySystems).toBeGreaterThan(0);
      return;
    }

    const defaultSummary = await getSummaryMap(page);
    const defaultActive = parseNumeric(getMetricValue(defaultSummary, 'Active Picks'));
    const defaultSystems = parseNumeric(getMetricValue(defaultSummary, 'Systems'));

    await clearFilters(page);

    const clearedState = await getDashboardState(page);
    expect(clearedState.scoreTier).toBe('');
    expect(clearedState.asset).toBe('');
    expect(clearedState.hiddenFlags).toEqual(defaultState.hiddenFlags);

    const clearedSummary = await getSummaryMap(page);
    const clearedActive = parseNumeric(getMetricValue(clearedSummary, 'Active Picks'));
    const clearedSystems = parseNumeric(getMetricValue(clearedSummary, 'Systems'));

    expect(defaultActive).toBe(clearedActive);
    expect(defaultSystems).toBe(clearedSystems);
  });

  test('summary active card matches active tab after clear filters', async ({ page }) => {
    await clearFilters(page);
    const summary = await getSummaryMap(page);
    const summaryActive = parseNumeric(getMetricValue(summary, 'Active Picks'));
    const headingActive = await getHeadingCount(page, '#tab-active h2');
    expect(summaryActive).toBe(headingActive);
  });

  test('overview drill links reconcile to filtered tabs', async ({ page }) => {
    await clearFilters(page);
    await page.locator('button.tab-btn[data-tab="overview"]').click();
    await page.waitForTimeout(400);

    for (const asset of ASSET_CLASSES) {
      const activeLink = page.locator(`#tab-overview .drill-link[data-filter-key="f-asset"][data-filter-val="${asset}"][data-tab="active"]`).first();
      if (await activeLink.count()) {
        const linkCount = parseNumeric((await activeLink.textContent()) || '0');
        await activeLink.click();
        await page.waitForTimeout(500);
        expect(await getHeadingCount(page, '#tab-active h2')).toBe(linkCount);
        const summary = await getSummaryMap(page);
        expect(parseNumeric(getMetricValue(summary, 'Active Picks'))).toBe(linkCount);
      }

      await page.locator('button.tab-btn[data-tab="overview"]').click();
      await page.waitForTimeout(300);

      const closedLink = page.locator(`#tab-overview .drill-link[data-filter-key="f-asset"][data-filter-val="${asset}"][data-tab="closed"]`).first();
      if (await closedLink.count()) {
        const linkCount = parseNumeric((await closedLink.textContent()) || '0');
        await closedLink.click();
        await page.waitForTimeout(500);
        expect(await getHeadingCount(page, '#tab-closed h2')).toBe(linkCount);
        const summary = await getSummaryMap(page);
        expect(parseNumeric(getMetricValue(summary, 'Closed Picks'))).toBe(linkCount);
      }

      await page.locator('button.tab-btn[data-tab="overview"]').click();
      await page.waitForTimeout(300);
    }
  });

  test('asset and filter matrix summary metrics match the filtered dataset', async ({ page }) => {
    const cases: Array<{ name: string; apply: () => Promise<void> }> = [];

    for (const asset of ASSET_CLASSES) {
      cases.push({
        name: `${asset} only`,
        apply: async () => {
          await clearFilters(page);
          await page.selectOption('#f-asset', asset);
          await page.waitForTimeout(250);
        },
      });
      cases.push({
        name: `${asset} + LONG`,
        apply: async () => {
          await clearFilters(page);
          await page.selectOption('#f-asset', asset);
          await page.selectOption('#f-dir', 'LONG');
          await page.waitForTimeout(250);
        },
      });
      cases.push({
        name: `${asset} + profitable`,
        apply: async () => {
          await clearFilters(page);
          await page.selectOption('#f-asset', asset);
          await page.selectOption('#f-pnl', 'pos');
          await page.waitForTimeout(250);
        },
      });
      cases.push({
        name: `${asset} + conf>=0.65`,
        apply: async () => {
          await clearFilters(page);
          await page.selectOption('#f-asset', asset);
          await page.selectOption('#f-conf', '0.65');
          await page.waitForTimeout(250);
        },
      });
      cases.push({
        name: `${asset} + age<=48h`,
        apply: async () => {
          await clearFilters(page);
          await page.selectOption('#f-asset', asset);
          await page.selectOption('#f-age', '48');
          await page.waitForTimeout(250);
        },
      });
    }

    for (const testCase of cases) {
      await test.step(testCase.name, async () => {
        await testCase.apply();
        const expected = await computeExpectedSummary(page);
        await assertSummaryMatchesExpected(page, expected);
        expect(await getHeadingCount(page, '#tab-active h2')).toBe(expected.activeCount);
      });
    }
  });
});
