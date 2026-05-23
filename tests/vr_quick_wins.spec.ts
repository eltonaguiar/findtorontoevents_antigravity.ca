/**
 * VR Quick Wins Tests
 *
 * Tests for:
 * QW-001: Hub Portal Live Data Badges (event count, weather, static labels)
 * QW-002: Session Timer in Nav Menu
 * QW-003: Zone Visit Tracking (localStorage visited zones)
 * QW-004: Smooth Zone Transitions (fade-in/out CSS classes)
 */
import { test, expect } from '@playwright/test';

const BASE = process.env.VERIFY_REMOTE === '1'
  ? 'https://findtorontoevents.ca'
  : 'http://localhost:5173';

test.describe('VR Quick Wins', () => {

  // ─── QW-001: Hub Portal Live Data Badges ───

  test('Hub has data badge elements for each zone', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    // Wait for A-Frame scene + badges to initialize
    await page.waitForTimeout(3000);

    // Check that data badge entities were created
    const badges = await page.locator('[id^="data-badge-"]').count();
    expect(badges).toBeGreaterThanOrEqual(4); // events, movies, weather, stocks, wellness, creators

    // Verify specific badges exist
    await expect(page.locator('#data-badge-events')).toBeAttached();
    await expect(page.locator('#data-badge-movies')).toBeAttached();
    await expect(page.locator('#data-badge-weather')).toBeAttached();
    await expect(page.locator('#data-badge-stocks')).toBeAttached();
    await expect(page.locator('#data-badge-wellness')).toBeAttached();
    await expect(page.locator('#data-badge-creators')).toBeAttached();
  });

  test('Hub movies badge shows "50+ Trailers"', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const text = await page.locator('#data-badge-movies a-text').getAttribute('value');
    expect(text).toBe('50+ Trailers');
  });

  test('Hub stocks badge shows "8 Tickers"', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const text = await page.locator('#data-badge-stocks a-text').getAttribute('value');
    expect(text).toBe('8 Tickers');
  });

  test('Hub wellness badge shows "Breathe & Relax"', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const text = await page.locator('#data-badge-wellness a-text').getAttribute('value');
    expect(text).toBe('Breathe & Relax');
  });

  // ─── QW-002: Session Timer in Nav Menu ───

  test('Nav menu contains session timer element', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    // Open the nav menu
    await page.keyboard.press('m');
    await page.waitForTimeout(500);

    // Session timer element should exist
    const session = page.locator('#vr-session');
    await expect(session).toBeVisible();

    // Should contain a time string (e.g., "0s", "1m 05s", "1h 02m")
    const text = await session.textContent();
    expect(text).toMatch(/\d+[smh]/);
  });

  test('Session timer updates over time', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    // Open the nav menu
    await page.keyboard.press('m');
    await page.waitForTimeout(500);

    const firstValue = await page.locator('#vr-session').textContent();

    // Wait for update interval (5s)
    await page.waitForTimeout(6000);

    const secondValue = await page.locator('#vr-session').textContent();
    // Timer should have changed (more seconds elapsed)
    expect(secondValue).not.toBe(firstValue);
  });

  // ─── QW-003: Zone Visit Tracking ───

  test('Visiting hub marks it as visited in localStorage', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    const visited = await page.evaluate(() => {
      try { return JSON.parse(localStorage.getItem('vr_visited_zones') || '{}'); } catch { return {}; }
    });

    expect(visited).toHaveProperty('hub');
    expect(typeof visited.hub).toBe('number');
  });

  test('Nav menu marks current zone as visited in localStorage', async ({ page }) => {
    // Visit the movies zone
    await page.goto(`${BASE}/vr/movies.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const visited = await page.evaluate(() => {
      try { return JSON.parse(localStorage.getItem('vr_visited_zones') || '{}'); } catch { return {}; }
    });

    expect(visited).toHaveProperty('movies');
    expect(typeof visited.movies).toBe('number');
  });

  test('Hub shows visited checkmarks for previously visited zones', async ({ page }) => {
    // Pre-seed localStorage with visited zones
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => {
      localStorage.setItem('vr_visited_zones', JSON.stringify({
        hub: Date.now(),
        movies: Date.now(),
        events: Date.now()
      }));
    });

    // Reload hub to pick up the seeded data
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Should have visited badge entities (green checkmarks)
    const checkmarks = await page.locator('.visited-badge').count();
    expect(checkmarks).toBeGreaterThanOrEqual(2); // movies + events at minimum
  });

  // ─── QW-004: Smooth Zone Transitions ───

  test('Page applies fade-in transition class on load', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);

    const hasClass = await page.evaluate(() =>
      document.body.classList.contains('vr-entering')
    );
    expect(hasClass).toBe(true);
  });

  test('Transition CSS keyframes are injected', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);

    const hasAnimation = await page.evaluate(() => {
      const sheets = document.styleSheets;
      for (let i = 0; i < sheets.length; i++) {
        try {
          const rules = sheets[i].cssRules;
          for (let j = 0; j < rules.length; j++) {
            if (rules[j].name === 'vr-zone-fadein') return true;
          }
        } catch { /* cross-origin */ }
      }
      return false;
    });
    expect(hasAnimation).toBe(true);
  });

  // ─── General: No JS Errors ───

  test('Hub loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    // Filter out known non-critical errors (e.g., CORS, network)
    const critical = errors.filter(e =>
      !e.includes('net::') &&
      !e.includes('CORS') &&
      !e.includes('Failed to fetch') &&
      !e.includes('NetworkError')
    );
    expect(critical).toEqual([]);
  });

  test('Movies zone loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto(`${BASE}/vr/movies.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    const critical = errors.filter(e =>
      !e.includes('net::') &&
      !e.includes('CORS') &&
      !e.includes('Failed to fetch') &&
      !e.includes('NetworkError')
    );
    expect(critical).toEqual([]);
  });
});
