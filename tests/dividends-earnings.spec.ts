import { test, expect } from '@playwright/test';

const API_BASE = 'https://findtorontoevents.ca/findstocks/portfolio2/api';
const PAGE_URL = 'https://findtorontoevents.ca/findstocks/portfolio2/dividends.html';

// ═══════════════════════════════════════════════
// Schema Tests
// ═══════════════════════════════════════════════

test.describe('Dividend & Earnings — Schema', () => {
  test('dividend_earnings_schema.php creates 3 tables', async ({ request }) => {
    const res = await request.get(`${API_BASE}/dividend_earnings_schema.php`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.actions).toHaveLength(3);
    expect(data.actions[0]).toContain('stock_dividends');
    expect(data.actions[1]).toContain('stock_earnings');
    expect(data.actions[2]).toContain('stock_fundamentals');
  });
});

// ═══════════════════════════════════════════════
// Fetch API Tests
// ═══════════════════════════════════════════════

test.describe('Dividend & Earnings — Fetch API', () => {
  test('fetch_one returns dividends, earnings, and fundamentals for AAPL', async ({ request }) => {
    const res = await request.get(`${API_BASE}/fetch_dividends_earnings.php?action=fetch_one&ticker=AAPL`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.result.ticker).toBe('AAPL');
    expect(data.result.dividends_saved).toBeGreaterThanOrEqual(0);
    expect(data.result.earnings_saved).toBeGreaterThanOrEqual(0);
    // fundamentals should be true (saved) or already cached
    expect(typeof data.result.fundamentals).toBe('boolean');
  });

  test('fetch_all processes tickers in batches of 5', async ({ request }) => {
    const res = await request.get(`${API_BASE}/fetch_dividends_earnings.php?action=fetch_all`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(typeof data.processed).toBe('number');
    expect(typeof data.remaining).toBe('number');
    expect(data.processed).toBeLessThanOrEqual(5);
    expect(Array.isArray(data.results)).toBe(true);
  });

  test('missing action returns error', async ({ request }) => {
    const res = await request.get(`${API_BASE}/fetch_dividends_earnings.php`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(false);
    expect(data.error).toContain('action');
  });
});

// ═══════════════════════════════════════════════
// Read API Tests — Dividends
// ═══════════════════════════════════════════════

test.describe('Dividend & Earnings — Dividend History', () => {
  test('get_dividends returns AAPL dividend history', async ({ request }) => {
    const res = await request.get(`${API_BASE}/fetch_dividends_earnings.php?action=get_dividends&ticker=AAPL`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.ticker).toBe('AAPL');
    expect(data.count).toBeGreaterThanOrEqual(4); // quarterly payer
    expect(Array.isArray(data.dividends)).toBe(true);
    if (data.dividends.length > 0) {
      const d = data.dividends[0];
      expect(d.ex_date).toBeDefined();
      expect(d.amount).toBeGreaterThan(0);
      expect(d.source).toBe('yahoo_v8');
    }
  });

  test('get_dividends for non-payer returns empty', async ({ request }) => {
    // BA suspended its dividend
    const res = await request.get(`${API_BASE}/fetch_dividends_earnings.php?action=get_dividends&ticker=BA`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.count).toBe(0);
  });
});

// ═══════════════════════════════════════════════
// Read API Tests — Earnings
// ═══════════════════════════════════════════════

test.describe('Dividend & Earnings — Earnings History', () => {
  test('get_earnings returns AAPL quarterly earnings', async ({ request }) => {
    const res = await request.get(`${API_BASE}/fetch_dividends_earnings.php?action=get_earnings&ticker=AAPL`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.ticker).toBe('AAPL');
    expect(data.count).toBeGreaterThanOrEqual(4);
    if (data.earnings.length > 0) {
      const e = data.earnings[0];
      expect(e.quarter_end).toBeDefined();
      expect(typeof e.eps_actual).toBe('number');
      expect(typeof e.eps_estimate).toBe('number');
      expect(e.source).toBe('yahoo_v10');
    }
  });

  test('earnings have surprise percentage', async ({ request }) => {
    const res = await request.get(`${API_BASE}/fetch_dividends_earnings.php?action=get_earnings&ticker=AAPL`);
    const data = await res.json();
    expect(data.ok).toBe(true);
    if (data.earnings.length > 0) {
      const e = data.earnings[0];
      expect(typeof e.surprise_pct).toBe('number');
    }
  });
});

// ═══════════════════════════════════════════════
// Read API Tests — Fundamentals
// ═══════════════════════════════════════════════

test.describe('Dividend & Earnings — Fundamentals', () => {
  test('get_fundamentals returns AAPL snapshot', async ({ request }) => {
    const res = await request.get(`${API_BASE}/fetch_dividends_earnings.php?action=get_fundamentals&ticker=AAPL`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.ticker).toBe('AAPL');
    const f = data.fundamentals;
    expect(f.ticker).toBe('AAPL');
    expect(typeof f.trailing_eps).toBe('number');
    expect(typeof f.trailing_pe).toBe('number');
    expect(typeof f.dividend_yield).toBe('number');
    expect(f.dividend_yield).toBeGreaterThan(0);
    expect(f.recommendation_key).toBeDefined();
    expect(f.company_name).toBeDefined();
  });

  test('get_fundamentals ticker=all returns multiple tickers', async ({ request }) => {
    const res = await request.get(`${API_BASE}/fetch_dividends_earnings.php?action=get_fundamentals&ticker=all`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.count).toBeGreaterThanOrEqual(10);
    expect(Array.isArray(data.fundamentals)).toBe(true);
    // Check structure of first entry
    const f = data.fundamentals[0];
    expect(f.ticker).toBeDefined();
    expect(f.source).toBe('yahoo_v10');
  });

  test('fundamentals for nonexistent ticker returns error', async ({ request }) => {
    const res = await request.get(`${API_BASE}/fetch_dividends_earnings.php?action=get_fundamentals&ticker=ZZZZ`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(false);
    expect(data.error).toContain('ZZZZ');
  });
});

// ═══════════════════════════════════════════════
// Upcoming Events API
// ═══════════════════════════════════════════════

test.describe('Dividend & Earnings — Upcoming Events', () => {
  test('upcoming returns dividend and earnings counts', async ({ request }) => {
    const res = await request.get(`${API_BASE}/fetch_dividends_earnings.php?action=upcoming`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(typeof data.dividend_count).toBe('number');
    expect(typeof data.earnings_count).toBe('number');
    expect(Array.isArray(data.upcoming_dividends)).toBe(true);
    expect(Array.isArray(data.upcoming_earnings)).toBe(true);
  });
});

// ═══════════════════════════════════════════════
// Dividend Leaders API
// ═══════════════════════════════════════════════

test.describe('Dividend & Earnings — Dividend Leaders', () => {
  test('dividend_leaders returns top yielders', async ({ request }) => {
    const res = await request.get(`${API_BASE}/fetch_dividends_earnings.php?action=dividend_leaders`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.count).toBeGreaterThanOrEqual(5);
    expect(Array.isArray(data.leaders)).toBe(true);
    if (data.leaders.length >= 2) {
      // Should be sorted by yield descending
      expect(data.leaders[0].dividend_yield).toBeGreaterThanOrEqual(data.leaders[1].dividend_yield);
    }
    // First leader should have meaningful yield
    const top = data.leaders[0];
    expect(top.dividend_yield).toBeGreaterThan(0.01); // >1%
    expect(top.ticker).toBeDefined();
  });
});

// ═══════════════════════════════════════════════
// Earnings Surprises API
// ═══════════════════════════════════════════════

test.describe('Dividend & Earnings — Earnings Surprises', () => {
  test('earnings_surprises returns recent beats/misses', async ({ request }) => {
    const res = await request.get(`${API_BASE}/fetch_dividends_earnings.php?action=earnings_surprises`);
    expect(res.ok()).toBe(true);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.count).toBeGreaterThanOrEqual(1);
    if (data.surprises.length > 0) {
      const s = data.surprises[0];
      expect(s.ticker).toBeDefined();
      expect(typeof s.eps_actual).toBe('number');
      expect(typeof s.eps_estimate).toBe('number');
      expect(typeof s.surprise_pct).toBe('number');
      expect(typeof s.beat).toBe('number');
      expect([0, 1]).toContain(s.beat);
    }
  });
});

// ═══════════════════════════════════════════════
// Frontend Dashboard Tests
// ═══════════════════════════════════════════════

test.describe('Dividend & Earnings — Frontend Dashboard', () => {
  test('dividends.html loads and has correct title', async ({ page }) => {
    await page.goto(PAGE_URL);
    await expect(page).toHaveTitle(/Dividends.*Earnings/);
  });

  test('dashboard shows stats cards', async ({ page }) => {
    await page.goto(PAGE_URL);
    await expect(page.locator('#stat-total')).toBeVisible();
    await expect(page.locator('#stat-payers')).toBeVisible();
    await expect(page.locator('#stat-avg-yield')).toBeVisible();
    // Wait for data to load
    await page.waitForTimeout(3000);
    const total = await page.locator('#stat-total').textContent();
    expect(parseInt(total || '0')).toBeGreaterThanOrEqual(1);
  });

  test('dashboard has 4 tabs', async ({ page }) => {
    await page.goto(PAGE_URL);
    const tabs = page.locator('.tab');
    await expect(tabs).toHaveCount(4);
    await expect(tabs.nth(0)).toContainText('Upcoming');
    await expect(tabs.nth(1)).toContainText('Dividend');
    await expect(tabs.nth(2)).toContainText('Earnings');
    await expect(tabs.nth(3)).toContainText('Fundamentals');
  });

  test('clicking Dividend Leaders tab loads data', async ({ page }) => {
    await page.goto(PAGE_URL);
    await page.locator('.tab:has-text("Dividend Leaders")').click();
    await expect(page.locator('#panel-dividends')).toBeVisible();
    // Wait for data
    await page.waitForTimeout(3000);
    const rows = page.locator('#div-leaders table tr');
    // Header + at least 1 data row
    expect(await rows.count()).toBeGreaterThanOrEqual(2);
  });

  test('clicking Fundamentals tab loads all tickers', async ({ page }) => {
    await page.goto(PAGE_URL);
    await page.locator('.tab:has-text("Fundamentals")').click();
    await expect(page.locator('#panel-fundamentals')).toBeVisible();
    await page.waitForTimeout(3000);
    const rows = page.locator('#fundamentals-table table tr');
    expect(await rows.count()).toBeGreaterThanOrEqual(5);
  });

  test('header links are present', async ({ page }) => {
    await page.goto(PAGE_URL);
    await expect(page.locator('.header-links a:has-text("Top Picks")')).toBeVisible();
    await expect(page.locator('.header-links a:has-text("Leaderboard")')).toBeVisible();
    await expect(page.locator('.header-links a:has-text("Miracle")')).toBeVisible();
  });
});
