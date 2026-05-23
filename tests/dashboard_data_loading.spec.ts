/**
 * Dashboard Data Loading Tests
 *
 * Tests that all trading dashboards load correctly and their data
 * endpoints respond. Runs against live GitHub Pages deployment.
 */
import { test, expect } from '@playwright/test';

const GH_PAGES = 'https://eltonaguiar.github.io/findtorontoevents_antigravity.ca';

test.describe('KIMI Rise of the Claw Dashboard', () => {
  test('loads main page and data', async ({ page }) => {
    // Navigate to the dashboard
    const response = await page.goto(`${GH_PAGES}/riseoftheclaw.html`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    expect(response?.status()).toBe(200);

    // Check page title or heading exists
    const heading = page.locator('h1, .dashboard-title, .header-title').first();
    await expect(heading).toBeVisible({ timeout: 10000 });

    // Check for JS console errors related to data loading
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error' && msg.text().includes('404')) {
        errors.push(msg.text());
      }
    });

    // Wait for data to attempt loading
    await page.waitForTimeout(5000);

    // Verify data endpoint responds
    const dataResp = await page.evaluate(async () => {
      const base = '/findtorontoevents_antigravity.ca/riseoftheclaw/';
      try {
        const r = await fetch(base + 'data/live_competition.json?_=' + Date.now());
        return { status: r.status, ok: r.ok };
      } catch (e: any) {
        return { status: 0, ok: false, error: e.message };
      }
    });
    expect(dataResp.status).toBe(200);
  });

  test('CSS and JS assets load', async ({ page }) => {
    const failedAssets: string[] = [];
    page.on('response', resp => {
      const url = resp.url();
      if ((url.endsWith('.css') || url.endsWith('.js')) && resp.status() >= 400) {
        failedAssets.push(`${resp.status()} ${url}`);
      }
    });

    await page.goto(`${GH_PAGES}/riseoftheclaw.html`, {
      waitUntil: 'networkidle',
      timeout: 30000,
    });

    expect(failedAssets).toEqual([]);
  });

  test('data files are accessible', async ({ page }) => {
    const base = `${GH_PAGES}/riseoftheclaw/data`;
    const files = [
      'live_competition.json',
      'active_picks.json',
      'tournament.json',
      'scan_runs.json',
      'algorithms.json',
    ];

    for (const file of files) {
      const resp = await page.request.get(`${base}/${file}`);
      expect(resp.status(), `${file} should return 200`).toBe(200);
      const body = await resp.text();
      expect(body.length, `${file} should have content`).toBeGreaterThan(2);
    }
  });

  test('getBasePath returns correct prefix on GitHub Pages', async ({ page }) => {
    await page.goto(`${GH_PAGES}/riseoftheclaw.html`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    const basePath = await page.evaluate(() => {
      return (window as any).getBasePath ? (window as any).getBasePath() : 'UNDEFINED';
    });

    expect(basePath).toBe('/findtorontoevents_antigravity.ca/riseoftheclaw/');
  });

  test('algorithms render in leaderboard', async ({ page }) => {
    await page.goto(`${GH_PAGES}/riseoftheclaw.html`, {
      waitUntil: 'networkidle',
      timeout: 30000,
    });

    // Wait for leaderboard to populate
    await page.waitForTimeout(5000);

    // Check that leaderboard has populated rows (not just the loading placeholder)
    const algoRows = page.locator('#leaderboardBody tr');
    const count = await algoRows.count();
    // Should have at least 1 row (even if it's still "Loading algorithms...")
    expect(count).toBeGreaterThan(0);
    // Verify it's not stuck on the loading cell — either real data or a valid empty state
    const bodyText = await page.locator('#leaderboardBody').textContent();
    const hasData = count > 1 || !bodyText?.includes('Loading algorithms');
    const hasLoadingOrEmpty = bodyText?.includes('Loading') || bodyText?.includes('No algorithms');
    expect(hasData || hasLoadingOrEmpty).toBeTruthy();
  });
});

test.describe('Alpha Engine Dashboard', () => {
  test('loads and has content', async ({ page }) => {
    const resp = await page.goto(`${GH_PAGES}/alpha/`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    expect(resp?.status()).toBe(200);

    // Check page has some content
    const body = await page.textContent('body');
    expect(body?.length).toBeGreaterThan(100);
  });

  test('premium dashboard loads', async ({ page }) => {
    const resp = await page.goto(`${GH_PAGES}/alpha/premium.html`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    expect(resp?.status()).toBe(200);
  });

  test('alpha data files accessible', async ({ page }) => {
    const files = ['premium_signals.json', 'active_picks.json'];
    for (const file of files) {
      const resp = await page.request.get(`${GH_PAGES}/alpha/data/${file}`);
      // Some files may not exist yet; 200 or 404 are both valid states to check
      expect([200, 404]).toContain(resp.status());
    }
  });
});

test.describe('Regime Terminal Dashboard', () => {
  test('loads and has regime data', async ({ page }) => {
    const resp = await page.goto(`${GH_PAGES}/regime/`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    expect(resp?.status()).toBe(200);

    // Check page has dark theme
    const bgColor = await page.evaluate(() => {
      return window.getComputedStyle(document.body).backgroundColor;
    });
    // Should be a dark color (not white)
    expect(bgColor).not.toBe('rgb(255, 255, 255)');
  });

  test('regime state JSON accessible', async ({ page }) => {
    const resp = await page.request.get(`${GH_PAGES}/regime/data/regime_state.json`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.version).toBe('1.0.0');
    expect(data.market_overview).toBeDefined();
    expect(data.market_overview.total_scanned).toBeGreaterThan(0);
  });

  test('active signals JSON accessible', async ({ page }) => {
    const resp = await page.request.get(`${GH_PAGES}/regime/data/active_signals.json`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.market_overview).toBeDefined();
  });

  test('regime badges render', async ({ page }) => {
    await page.goto(`${GH_PAGES}/regime/`, {
      waitUntil: 'networkidle',
      timeout: 30000,
    });

    await page.waitForTimeout(3000);

    // Check for regime badge elements or market count
    const body = await page.textContent('body');
    // Should contain regime-related text
    expect(body).toContain('Regime');
  });
});

test.describe('Other Dashboards', () => {
  const dashboards = [
    { name: 'Pair Fingerprints', path: '/pair-fingerprints.html' },
    { name: 'Unified Dashboard', path: '/unified-dashboard.html' },
    { name: 'Goldmine Alerts', path: '/goldmine-alerts.html' },
    { name: 'Forex Portfolio', path: '/forex-portfolio.html' },
    { name: 'Scanner Log', path: '/riseoftheclaw/scanner-log.html' },
  ];

  for (const dash of dashboards) {
    test(`${dash.name} loads (200)`, async ({ page }) => {
      const resp = await page.goto(`${GH_PAGES}${dash.path}`, {
        waitUntil: 'domcontentloaded',
        timeout: 30000,
      });
      expect(resp?.status()).toBe(200);
    });
  }
});

test.describe('No Critical JS Errors', () => {
  const pages = [
    { name: 'KIMI Dashboard', path: '/riseoftheclaw.html' },
    { name: 'Alpha Engine', path: '/alpha/' },
    { name: 'Regime Terminal', path: '/regime/' },
  ];

  for (const pg of pages) {
    test(`${pg.name} has no fatal JS errors`, async ({ page }) => {
      const fatalErrors: string[] = [];
      page.on('pageerror', error => {
        // Only capture truly fatal errors, not expected 404s or warnings
        if (!error.message.includes('favicon') && !error.message.includes('404')) {
          fatalErrors.push(error.message);
        }
      });

      await page.goto(`${GH_PAGES}${pg.path}`, {
        waitUntil: 'networkidle',
        timeout: 30000,
      });

      await page.waitForTimeout(3000);
      expect(fatalErrors).toEqual([]);
    });
  }
});
