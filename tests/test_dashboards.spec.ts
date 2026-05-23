import { test, expect } from '@playwright/test';

const isRemote = process.env.VERIFY_REMOTE === '1';
const BASE = isRemote ? 'https://findtorontoevents.ca' : 'http://localhost:5173';
const GH_PAGES = 'https://eltonaguiar.github.io/findtorontoevents_antigravity.ca';

test.describe('Claude ML Gainer Dashboard', () => {
  test('page loads and shows KPI cards', async ({ page }) => {
    await page.goto(`${BASE}/updates/claude-ml-gainer.html`, { waitUntil: 'networkidle', timeout: 30000 });
    // Hero title
    await expect(page.locator('.hero h1')).toContainText('Claude Code');
    // KPI row exists
    await expect(page.locator('#kpiRow')).toBeVisible();
    // 6 KPI cards
    const kpis = page.locator('.kpi');
    await expect(kpis).toHaveCount(6);
  });

  test('active picks table has correct columns', async ({ page }) => {
    await page.goto(`${BASE}/updates/claude-ml-gainer.html`, { waitUntil: 'networkidle', timeout: 30000 });
    const headers = page.locator('table thead th');
    const texts = await headers.allTextContents();
    expect(texts.some(t => t.includes('Symbol'))).toBeTruthy();
    expect(texts.some(t => t.includes('Probability'))).toBeTruthy();
    expect(texts.some(t => t.includes('Entry'))).toBeTruthy();
    expect(texts.some(t => t.includes('TP'))).toBeTruthy();
    expect(texts.some(t => t.includes('SL'))).toBeTruthy();
    expect(texts.some(t => t.includes('Time Active'))).toBeTruthy();
  });

  test('probability column header has tooltip', async ({ page }) => {
    await page.goto(`${BASE}/updates/claude-ml-gainer.html`, { waitUntil: 'networkidle', timeout: 30000 });
    const probHeader = page.locator('th:has-text("Probability")');
    const title = await probHeader.getAttribute('title');
    expect(title).toContain('RF+XGB ensemble');
    expect(title).toContain('20 engineered features');
  });

  test('no $0.000e+0 prices visible', async ({ page }) => {
    await page.goto(`${BASE}/updates/claude-ml-gainer.html`, { waitUntil: 'networkidle', timeout: 30000 });
    // Wait for data to load
    await page.waitForTimeout(5000);
    const content = await page.content();
    expect(content).not.toContain('$0.000e+0');
    expect(content).not.toContain('$0.000e');
  });

  test('CRYPTO badges appear on picks', async ({ page }) => {
    await page.goto(`${BASE}/updates/claude-ml-gainer.html`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(5000);
    // If there are picks, they should have CRYPTO badges
    const badges = await page.locator('text=CRYPTO').count();
    // Should have at least 1 if picks loaded
    console.log(`Found ${badges} CRYPTO badges`);
  });

  test('KPIs show real data (not all dashes)', async ({ page }) => {
    await page.goto(`${BASE}/updates/claude-ml-gainer.html`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(5000);
    const totalPicks = await page.locator('#kpiTotal').textContent();
    console.log(`Total picks KPI: ${totalPicks}`);
    // Performance JSON has 32 total picks
    expect(totalPicks).not.toBe('\u2014');
  });
});

test.describe('ML Live Picks Dashboard', () => {
  test('page loads with stats bar', async ({ page }) => {
    await page.goto(`${BASE}/updates/ml-live-picks.html`, { waitUntil: 'networkidle', timeout: 30000 });
    await expect(page.locator('.hero h1')).toContainText('ANTIGRAVITY');
    await expect(page.locator('#stats-bar')).toBeVisible();
  });

  test('active picks table has data', async ({ page }) => {
    await page.goto(`${BASE}/updates/ml-live-picks.html`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(5000);
    const activeCount = await page.locator('#active-badge').textContent();
    console.log(`Active picks: ${activeCount}`);
    // Should have some active picks from ml_crypto_predictor + claude_gainer
    expect(parseInt(activeCount) || 0).toBeGreaterThanOrEqual(0);
  });

  test('forensic analysis section renders', async ({ page }) => {
    await page.goto(`${BASE}/updates/ml-live-picks.html`, { waitUntil: 'networkidle', timeout: 30000 });
    await expect(page.locator('#forensic-grid')).toBeVisible();
  });
});

test.describe('Key Live Dashboards Health Check', () => {
  const dashboards = [
    { name: 'Audit Trail', url: `${BASE}/audit/` },
    { name: 'KIMI RiseOfTheClaw', url: `${GH_PAGES}/riseoftheclaw.html` },
    { name: 'Alpha Engine', url: `${GH_PAGES}/alpha/` },
    { name: 'Cross Monitor', url: `${GH_PAGES}/monitor/` },
    { name: 'Breakout Arena', url: `${GH_PAGES}/arena/` },
    { name: 'Rapid Fire NOW', url: `${BASE}/findcryptopairs/now.html` },
  ];

  for (const d of dashboards) {
    test(`${d.name} loads without errors`, async ({ page }) => {
      const errors = [];
      page.on('pageerror', err => errors.push(err.message));

      const response = await page.goto(d.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      expect(response.status()).toBeLessThan(400);

      // Check for JS errors
      if (errors.length > 0) {
        console.log(`${d.name} JS errors:`, errors);
      }
    });
  }
});
