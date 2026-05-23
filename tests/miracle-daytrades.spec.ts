import { test, expect } from '@playwright/test';

const API_BASE = 'https://findtorontoevents.ca/findstocks2_global/api';
const PAGE_URL = 'https://findtorontoevents.ca/findstocks2_global/miracle.html';

// ═══════════════════════════════════════════════
// Schema & Setup Tests
// ═══════════════════════════════════════════════

test.describe('DayTrades Miracle Claude — Schema', () => {
  test('setup_schema2.php creates all tables and seeds data', async ({ request }) => {
    const res = await request.get(`${API_BASE}/setup_schema2.php`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.actions).toBeDefined();

    // Check all 6 tables created
    const tableNames = ['miracle_strategies2', 'miracle_picks2', 'miracle_portfolios2', 'miracle_results2', 'miracle_watchlist2', 'miracle_audit2'];
    for (const tbl of tableNames) {
      const found = data.actions.some((a: string) => a.includes(tbl));
      expect(found).toBe(true);
    }

    // Check seeding
    const stratSeed = data.actions.find((a: string) => a.includes('miracle strategies'));
    expect(stratSeed).toBeDefined();
    const portSeed = data.actions.find((a: string) => a.includes('miracle portfolios'));
    expect(portSeed).toBeDefined();
    const watchSeed = data.actions.find((a: string) => a.includes('watchlist tickers'));
    expect(watchSeed).toBeDefined();
  });
});

// ═══════════════════════════════════════════════
// Dashboard API Tests
// ═══════════════════════════════════════════════

test.describe('DayTrades Miracle Claude — Dashboard API', () => {
  test('dashboard summary returns correct structure', async ({ request }) => {
    const res = await request.get(`${API_BASE}/dashboard2.php?action=summary`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.summary).toBeDefined();
    expect(typeof data.summary.total_picks).toBe('number');
    expect(typeof data.summary.winners).toBe('number');
    expect(typeof data.summary.losers).toBe('number');
    expect(typeof data.summary.pending).toBe('number');
    expect(typeof data.summary.win_rate).toBe('number');
    expect(typeof data.summary.profit_factor).toBe('number');
    expect(typeof data.summary.expectancy).toBe('number');
    expect(typeof data.summary.cdr_win_rate).toBe('number');
  });

  test('dashboard leaderboard returns strategy data', async ({ request }) => {
    const res = await request.get(`${API_BASE}/dashboard2.php?action=leaderboard`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.leaderboard).toBeDefined();
    expect(Array.isArray(data.leaderboard)).toBe(true);
  });

  test('dashboard portfolios returns portfolio list', async ({ request }) => {
    const res = await request.get(`${API_BASE}/dashboard2.php?action=portfolios`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.portfolios).toBeDefined();
    expect(data.portfolios.length).toBeGreaterThanOrEqual(8);
    // Check portfolio structure
    const p = data.portfolios[0];
    expect(p.name).toBeDefined();
    expect(p.initial_capital).toBeDefined();
    expect(p.position_size_pct).toBeDefined();
    expect(p.max_positions).toBeDefined();
    expect(p.fee_model).toBeDefined();
  });

  test('dashboard watchlist returns tickers', async ({ request }) => {
    const res = await request.get(`${API_BASE}/dashboard2.php?action=watchlist`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.watchlist).toBeDefined();
    expect(data.watchlist.length).toBeGreaterThanOrEqual(60);

    // Check CDR tickers are in the watchlist
    const cdrTickers = data.watchlist.filter((w: any) => w.is_cdr === '1' || w.is_cdr === 1);
    expect(cdrTickers.length).toBeGreaterThanOrEqual(35);

    // Check NVDA is in watchlist
    const nvda = data.watchlist.find((w: any) => w.ticker === 'NVDA');
    expect(nvda).toBeDefined();
    expect(nvda.company_name).toContain('NVIDIA');
  });

  test('dashboard strategies returns all 8 strategies', async ({ request }) => {
    const res = await request.get(`${API_BASE}/dashboard2.php?action=strategies`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.strategies).toBeDefined();
    expect(data.strategies.length).toBe(8);

    // Check strategy names
    const names = data.strategies.map((s: any) => s.name);
    expect(names).toContain('Gap Up Momentum');
    expect(names).toContain('Volume Surge Breakout');
    expect(names).toContain('Oversold Bounce');
    expect(names).toContain('Momentum Continuation');
    expect(names).toContain('Earnings Catalyst Runner');
    expect(names).toContain('CDR Zero-Fee Play');
    expect(names).toContain('Sector Momentum Leader');
    expect(names).toContain('Mean Reversion Sniper');
  });

  test('dashboard full action returns all sections', async ({ request }) => {
    const res = await request.get(`${API_BASE}/dashboard2.php?action=full`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.summary).toBeDefined();
    expect(data.leaderboard).toBeDefined();
    expect(data.portfolios).toBeDefined();
    expect(data.recent).toBeDefined();
    expect(data.best_picks).toBeDefined();
    expect(data.worst_picks).toBeDefined();
    expect(data.streaks).toBeDefined();
  });

  test('dashboard streaks returns streak data', async ({ request }) => {
    const res = await request.get(`${API_BASE}/dashboard2.php?action=streaks`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.streaks).toBeDefined();
    expect(typeof data.streaks.current_count).toBe('number');
    expect(typeof data.streaks.max_win_streak).toBe('number');
    expect(typeof data.streaks.max_loss_streak).toBe('number');
  });
});

// ═══════════════════════════════════════════════
// Picks API Tests
// ═══════════════════════════════════════════════

test.describe('DayTrades Miracle Claude — Picks API', () => {
  test('picks2.php returns today picks with correct structure', async ({ request }) => {
    const res = await request.get(`${API_BASE}/picks2.php`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.total).toBeDefined();
    expect(data.summary).toBeDefined();
    expect(data.picks).toBeDefined();
    expect(Array.isArray(data.picks)).toBe(true);

    if (data.picks.length > 0) {
      const pick = data.picks[0];
      expect(pick.ticker).toBeDefined();
      expect(pick.strategy_name).toBeDefined();
      expect(pick.entry_price).toBeDefined();
      expect(pick.stop_loss_price).toBeDefined();
      expect(pick.take_profit_price).toBeDefined();
      expect(pick.score).toBeDefined();
      expect(pick.confidence).toBeDefined();
      expect(pick.is_cdr).toBeDefined();
      expect(pick.questrade_fee).toBeDefined();
      expect(pick.net_profit_if_tp).toBeDefined();
      expect(pick.risk_reward_ratio).toBeDefined();
      expect(pick.outcome).toBe('pending');
    }
  });

  test('picks2.php CDR filter works', async ({ request }) => {
    const res = await request.get(`${API_BASE}/picks2.php?cdr_only=1`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    // All returned picks should be CDR
    for (const pick of data.picks) {
      expect(pick.is_cdr == 1 || pick.is_cdr === '1').toBe(true);
    }
  });

  test('picks2.php confidence filter works', async ({ request }) => {
    const res = await request.get(`${API_BASE}/picks2.php?confidence=high`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    for (const pick of data.picks) {
      expect(pick.confidence).toBe('high');
    }
  });

  test('picks2.php sort by risk_reward works', async ({ request }) => {
    const res = await request.get(`${API_BASE}/picks2.php?sort=risk_reward_ratio`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    if (data.picks.length >= 2) {
      const first = parseFloat(data.picks[0].risk_reward_ratio);
      const second = parseFloat(data.picks[1].risk_reward_ratio);
      expect(first).toBeGreaterThanOrEqual(second);
    }
  });

  test('picks2.php days filter works', async ({ request }) => {
    const res = await request.get(`${API_BASE}/picks2.php?days=7`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.total).toBeGreaterThanOrEqual(0);
  });

  test('picks2.php ticker filter works', async ({ request }) => {
    const res = await request.get(`${API_BASE}/picks2.php?ticker=AMZN&days=30`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    for (const pick of data.picks) {
      expect(pick.ticker).toBe('AMZN');
    }
  });

  test('picks2.php strategy filter works', async ({ request }) => {
    const res = await request.get(`${API_BASE}/picks2.php?strategy=CDR+Zero-Fee+Play&days=30`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    for (const pick of data.picks) {
      expect(pick.strategy_name).toBe('CDR Zero-Fee Play');
    }
  });
});

// ═══════════════════════════════════════════════
// Scanner API Tests
// ═══════════════════════════════════════════════

test.describe('DayTrades Miracle Claude — Scanner API', () => {
  test('scanner2.php dry run returns picks without saving', async ({ request }) => {
    const res = await request.get(`${API_BASE}/scanner2.php?dry_run=1&top=5`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.scanned).toBeGreaterThan(0);
    expect(data.saved).toBe(0); // dry_run should not save
    expect(data.scan_time).toBeDefined();
    expect(Array.isArray(data.picks)).toBe(true);
  }, 120000);

  test('scanner picks have valid price levels', async ({ request }) => {
    const res = await request.get(`${API_BASE}/scanner2.php?dry_run=1&top=5`);
    expect(res.ok()).toBe(true);
    const data = await res.json();

    for (const pick of data.picks) {
      const entry = parseFloat(pick.entry_price);
      const sl = parseFloat(pick.stop_loss_price);
      const tp = parseFloat(pick.take_profit_price);
      // Stop loss should be below entry
      expect(sl).toBeLessThan(entry);
      // Take profit should be above entry
      expect(tp).toBeGreaterThan(entry);
      // Score should be 0-100
      expect(pick.score).toBeGreaterThanOrEqual(0);
      expect(pick.score).toBeLessThanOrEqual(100);
      // Risk/reward should be positive
      expect(parseFloat(pick.risk_reward)).toBeGreaterThan(0);
    }
  }, 120000);

  test('scanner single ticker mode works', async ({ request }) => {
    const res = await request.get(`${API_BASE}/scanner2.php?ticker=NVDA&dry_run=1`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.scanned).toBe(1);
    // All picks should be for NVDA
    for (const pick of data.picks) {
      expect(pick.ticker).toBe('NVDA');
    }
  }, 60000);
});

// ═══════════════════════════════════════════════
// Learning API Tests
// ═══════════════════════════════════════════════

test.describe('DayTrades Miracle Claude — Learning API', () => {
  test('learning report returns correct structure', async ({ request }) => {
    const res = await request.get(`${API_BASE}/learning2.php?action=report`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.action).toBe('report');
    expect(data.strategy_analysis).toBeDefined();
    expect(data.score_calibration).toBeDefined();
    expect(data.cdr_vs_noncdr).toBeDefined();
    expect(data.day_of_week).toBeDefined();
    expect(data.confidence_accuracy).toBeDefined();
    expect(data.adjustments).toBeDefined();
    expect(data.score_history).toBeDefined();
    expect(data.ticker_performance).toBeDefined();
    expect(data.recommendations).toBeDefined();
  });

  test('learning analyze returns strategy grades', async ({ request }) => {
    const res = await request.get(`${API_BASE}/learning2.php?action=analyze`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.strategy_analysis).toBeDefined();
    expect(data.score_calibration).toBeDefined();
    expect(Array.isArray(data.score_calibration)).toBe(true);
    // Score calibration should have 5 bands
    expect(data.score_calibration.length).toBe(5);
  });

  test('learning score_history returns date-based data', async ({ request }) => {
    const res = await request.get(`${API_BASE}/learning2.php?action=score_history`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.score_history).toBeDefined();
    expect(Array.isArray(data.score_history)).toBe(true);
  });

  test('learning recommendations returns array', async ({ request }) => {
    const res = await request.get(`${API_BASE}/learning2.php?action=recommendations`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.recommendations).toBeDefined();
    expect(Array.isArray(data.recommendations)).toBe(true);
  });

  test('learning ticker_performance returns data', async ({ request }) => {
    const res = await request.get(`${API_BASE}/learning2.php?action=ticker_performance`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.ticker_performance).toBeDefined();
    expect(Array.isArray(data.ticker_performance)).toBe(true);
  });
});

// ═══════════════════════════════════════════════
// Resolve Picks API Tests
// ═══════════════════════════════════════════════

test.describe('DayTrades Miracle Claude — Resolve API', () => {
  test('resolve_picks2.php returns correct structure', async ({ request }) => {
    const res = await request.get(`${API_BASE}/resolve_picks2.php?days=1`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(typeof data.resolved).toBe('number');
    expect(typeof data.winners).toBe('number');
    expect(typeof data.losers).toBe('number');
    expect(typeof data.expired).toBe('number');
    expect(typeof data.still_pending).toBe('number');
  }, 120000);
});

// ═══════════════════════════════════════════════
// Daily Scan Orchestrator Tests
// ═══════════════════════════════════════════════

test.describe('DayTrades Miracle Claude — Daily Scan', () => {
  test('daily_scan2.php requires auth key', async ({ request }) => {
    const res = await request.get(`${API_BASE}/daily_scan2.php`);
    const data = await res.json();
    expect(data.ok).toBe(false);
    expect(data.error).toContain('Invalid key');
  });

  test('daily_scan2.php rejects wrong key', async ({ request }) => {
    const res = await request.get(`${API_BASE}/daily_scan2.php?key=wrongkey`);
    const data = await res.json();
    expect(data.ok).toBe(false);
  });
});

// ═══════════════════════════════════════════════
// Frontend Page Tests
// ═══════════════════════════════════════════════

test.describe('DayTrades Miracle Claude — Frontend', () => {
  test('miracle.html loads with correct title', async ({ page }) => {
    await page.goto(PAGE_URL);
    await expect(page).toHaveTitle(/DayTrades Miracle Claude/);
  });

  test('miracle.html has all navigation tabs', async ({ page }) => {
    await page.goto(PAGE_URL);
    const tabs = ['Overview', "Today's Picks", 'Strategy Leaderboard', 'Self-Learning AI', 'Pick History', 'Portfolios', 'Watchlist'];
    for (const tab of tabs) {
      await expect(page.locator(`.tab:has-text("${tab}")`)).toBeVisible();
    }
  });

  test('miracle.html overview loads stats', async ({ page }) => {
    await page.goto(PAGE_URL);
    // Wait for dashboard to load
    await page.waitForTimeout(3000);
    // Should show stat cards (not loading spinner)
    const statCards = page.locator('.stat-card');
    await expect(statCards.first()).toBeVisible({ timeout: 10000 });
  });

  test('miracle.html tab switching works', async ({ page }) => {
    await page.goto(PAGE_URL);
    // Click Portfolios tab
    await page.locator('.tab:has-text("Portfolios")').click();
    // Portfolio panel should be visible
    await expect(page.locator('#panel-portfolios')).toBeVisible();
    // Wait for content to load
    await page.waitForTimeout(3000);
    // Should show strategy cards
    const cards = page.locator('.strategy-card');
    await expect(cards.first()).toBeVisible({ timeout: 10000 });
  });

  test('miracle.html has disclaimer', async ({ page }) => {
    await page.goto(PAGE_URL);
    await expect(page.locator('.disclaimer')).toBeVisible();
    await expect(page.locator('.disclaimer')).toContainText('Not financial advice');
  });
});

// ═══════════════════════════════════════════════
// Data Integrity Tests
// ═══════════════════════════════════════════════

test.describe('DayTrades Miracle Claude — Data Integrity', () => {
  test('all 8 strategy scan_types are valid', async ({ request }) => {
    const res = await request.get(`${API_BASE}/dashboard2.php?action=strategies`);
    const data = await res.json();
    const validTypes = ['gap_scanner', 'volume_scanner', 'reversal', 'trend_pullback', 'earnings', 'cdr_filter', 'sector_scan', 'zscore_reversal'];
    for (const strat of data.strategies) {
      expect(validTypes).toContain(strat.scan_type);
    }
  });

  test('all strategies have valid TP/SL defaults', async ({ request }) => {
    const res = await request.get(`${API_BASE}/dashboard2.php?action=strategies`);
    const data = await res.json();
    for (const strat of data.strategies) {
      const tp = parseFloat(strat.default_tp_pct);
      const sl = parseFloat(strat.default_sl_pct);
      expect(tp).toBeGreaterThan(0);
      expect(sl).toBeGreaterThan(0);
      expect(tp).toBeGreaterThan(sl); // TP should always exceed SL
    }
  });

  test('watchlist has both CDR and non-CDR tickers', async ({ request }) => {
    const res = await request.get(`${API_BASE}/dashboard2.php?action=watchlist`);
    const data = await res.json();
    const cdr = data.watchlist.filter((w: any) => w.is_cdr == 1);
    const nonCdr = data.watchlist.filter((w: any) => w.is_cdr == 0);
    expect(cdr.length).toBeGreaterThan(30);
    expect(nonCdr.length).toBeGreaterThan(20);
  });

  test('watchlist includes sector ETFs', async ({ request }) => {
    const res = await request.get(`${API_BASE}/dashboard2.php?action=watchlist`);
    const data = await res.json();
    const etfs = data.watchlist.filter((w: any) => w.sector === 'ETF');
    expect(etfs.length).toBeGreaterThanOrEqual(11);
    const etfTickers = etfs.map((e: any) => e.ticker);
    expect(etfTickers).toContain('XLK');
    expect(etfTickers).toContain('SPY');
  });

  test('portfolio templates have correct fee model', async ({ request }) => {
    const res = await request.get(`${API_BASE}/dashboard2.php?action=portfolios`);
    const data = await res.json();
    for (const p of data.portfolios) {
      expect(p.fee_model).toBe('questrade');
    }
  });
});

// ═══════════════════════════════════════════════
// Budget Pick API Tests
// ═══════════════════════════════════════════════

test.describe('DayTrades Miracle Claude — Budget Picks', () => {
  test('budget_pick2.php requires a budget parameter', async ({ request }) => {
    const res = await request.get(`${API_BASE}/budget_pick2.php`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(false);
    expect(data.error).toContain('budget');
  });

  test('budget_pick2.php returns picks for $250', async ({ request }) => {
    const res = await request.get(`${API_BASE}/budget_pick2.php?budget=250`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.budget).toBe(250);
    expect(data.affordable).toBeGreaterThanOrEqual(0);
    expect(data.cdr_affordable).toBeGreaterThanOrEqual(0);
    expect(typeof data.avg_fee_drag).toBe('number');
    expect(data.recommendation).toBeDefined();
    expect(Array.isArray(data.picks)).toBe(true);
  });

  test('budget picks have correct structure', async ({ request }) => {
    const res = await request.get(`${API_BASE}/budget_pick2.php?budget=1000&top=3`);
    const data = await res.json();
    expect(data.ok).toBe(true);
    if (data.picks.length > 0) {
      const p = data.picks[0];
      expect(p.rank).toBe(1);
      expect(p.ticker).toBeDefined();
      expect(p.shares).toBeGreaterThanOrEqual(1);
      expect(p.invested).toBeGreaterThan(0);
      expect(p.invested).toBeLessThanOrEqual(1000);
      expect(p.entry_price).toBeGreaterThan(0);
      expect(p.tp_price).toBeGreaterThan(p.entry_price);
      expect(p.sl_price).toBeLessThan(p.entry_price);
      expect(p.net_profit).toBeGreaterThan(0);
      expect(p.net_loss).toBeLessThan(0);
      expect(typeof p.fee_drag_pct).toBe('number');
      expect(typeof p.breakeven_pct).toBe('number');
      expect(typeof p.risk_reward).toBe('number');
      expect(typeof p.budget_score).toBe('number');
      expect(p.confidence).toBeDefined();
    }
  });

  test('budget picks respect CDR filter', async ({ request }) => {
    const res = await request.get(`${API_BASE}/budget_pick2.php?budget=500&cdr_only=1`);
    const data = await res.json();
    expect(data.ok).toBe(true);
    for (const p of data.picks) {
      expect(p.is_cdr).toBe(1);
    }
  });

  test('budget picks: invested never exceeds budget', async ({ request }) => {
    const res = await request.get(`${API_BASE}/budget_pick2.php?budget=100&top=10`);
    const data = await res.json();
    expect(data.ok).toBe(true);
    for (const p of data.picks) {
      expect(p.invested).toBeLessThanOrEqual(100);
      expect(p.shares).toBeGreaterThanOrEqual(1);
    }
  });

  test('budget picks: CDR stocks have zero fees', async ({ request }) => {
    const res = await request.get(`${API_BASE}/budget_pick2.php?budget=5000&cdr_only=1`);
    const data = await res.json();
    expect(data.ok).toBe(true);
    for (const p of data.picks) {
      if (p.is_cdr === 1) {
        expect(p.total_fees).toBe(0);
        expect(p.fee_drag_pct).toBe(0);
        expect(p.breakeven_pct).toBe(0);
      }
    }
  });

  test('budget picks: recommendation text is non-empty for valid budget', async ({ request }) => {
    const res = await request.get(`${API_BASE}/budget_pick2.php?budget=500`);
    const data = await res.json();
    expect(data.ok).toBe(true);
    if (data.picks.length > 0) {
      expect(data.recommendation.length).toBeGreaterThan(50);
      expect(data.recommendation).toContain('buy');
      expect(data.recommendation).toContain('stop-loss');
      expect(data.recommendation).toContain('take-profit');
    }
  });

  test('miracle.html budget tab exists and works', async ({ page }) => {
    await page.goto(PAGE_URL);
    await page.locator('.tab:has-text("My Budget")').click();
    await expect(page.locator('#panel-budget')).toBeVisible();
    await expect(page.locator('#budget-amount')).toBeVisible();
    // Budget presets should be visible
    await expect(page.locator('.budget-presets button').first()).toBeVisible();
  });

  test('miracle.html has trading style selector with all 5 options', async ({ page }) => {
    await page.goto(PAGE_URL);
    await page.locator('.tab:has-text("My Budget")').click();
    await expect(page.locator('#panel-budget')).toBeVisible();
    const pills = page.locator('.style-pills button');
    await expect(pills).toHaveCount(5);
    // Check labels
    await expect(pills.nth(0)).toContainText('All Styles');
    await expect(pills.nth(1)).toContainText('Day Trade');
    await expect(pills.nth(2)).toContainText('Overnight');
    await expect(pills.nth(3)).toContainText('Swing Trade');
    await expect(pills.nth(4)).toContainText('Buy');
  });

  test('budget_pick2.php style=intraday adjusts TP/SL', async ({ request }) => {
    const [noStyle, intraday] = await Promise.all([
      request.get(`${API_BASE}/budget_pick2.php?budget=500`).then(r => r.json()),
      request.get(`${API_BASE}/budget_pick2.php?budget=500&style=intraday`).then(r => r.json()),
    ]);
    expect(noStyle.ok).toBe(true);
    expect(intraday.ok).toBe(true);
    expect(intraday.style).toBe('intraday');
    expect(intraday.style_label).toBe('Day Trade (Today)');
    if (noStyle.picks.length > 0 && intraday.picks.length > 0) {
      // Find matching ticker in both
      const ns = noStyle.picks[0];
      const id = intraday.picks.find((p: any) => p.ticker === ns.ticker);
      if (id) {
        // Intraday TP should be tighter (closer to entry)
        expect(Math.abs(id.tp_price - id.entry_price)).toBeLessThanOrEqual(
          Math.abs(ns.tp_price - ns.entry_price) + 0.01
        );
      }
    }
  });

  test('budget_pick2.php style=longterm widens TP/SL', async ({ request }) => {
    const [noStyle, longterm] = await Promise.all([
      request.get(`${API_BASE}/budget_pick2.php?budget=500`).then(r => r.json()),
      request.get(`${API_BASE}/budget_pick2.php?budget=500&style=longterm`).then(r => r.json()),
    ]);
    expect(longterm.ok).toBe(true);
    expect(longterm.style).toBe('longterm');
    expect(longterm.style_label).toBe('Buy & Hold (Weeks/Months)');
    if (noStyle.picks.length > 0 && longterm.picks.length > 0) {
      const ns = noStyle.picks[0];
      const lt = longterm.picks.find((p: any) => p.ticker === ns.ticker);
      if (lt) {
        // Longterm TP should be wider (further from entry)
        expect(Math.abs(lt.tp_price - lt.entry_price)).toBeGreaterThanOrEqual(
          Math.abs(ns.tp_price - ns.entry_price) - 0.01
        );
        expect(lt.hold_period).toBe('30+ days');
      }
    }
  });

  test('budget_pick2.php style=swing returns valid data', async ({ request }) => {
    const res = await request.get(`${API_BASE}/budget_pick2.php?budget=1000&style=swing`);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.style).toBe('swing');
    expect(data.style_label).toBe('Swing Trade (Up to 1 Week)');
    for (const p of data.picks) {
      expect(p.hold_period).toBe('5-7 days');
      expect(p.tp_price).toBeGreaterThan(p.entry_price);
      expect(p.sl_price).toBeLessThan(p.entry_price);
    }
  });

  test('budget_pick2.php invalid style is ignored', async ({ request }) => {
    const res = await request.get(`${API_BASE}/budget_pick2.php?budget=250&style=invalid`);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.style).toBe('invalid');
    expect(data.style_label).toBe('');
    // Should still return picks with no hold_period
    for (const p of data.picks) {
      expect(p.hold_period).toBe('');
    }
  });
});
