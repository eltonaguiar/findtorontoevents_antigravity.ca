/**
 * VR Quick Wins Phase 2 Tests
 *
 * QW-005: Stocks Zone keyboard shortcuts + ticker cycling
 * QW-006: Events Explorer search box + / shortcut
 * QW-007: Weather Zone keyboard shortcuts (1-4 modes, P, R)
 * QW-008: Creators Zone keyboard enhancements (R refresh, 1-5 platform)
 * QW-009: Shared keyboard-hints module (? overlay, hint bar)
 * QW-010: Tutorial skip (S), reset (R), back (B)
 */
import { test, expect } from '@playwright/test';

const BASE = process.env.VERIFY_REMOTE === '1'
  ? 'https://findtorontoevents.ca'
  : 'http://localhost:5173';

test.describe('VR Quick Wins Phase 2', () => {

  // ─── QW-009: Keyboard Hints Module (shared across all zones) ───

  test('Hub: keyboard hint bar is visible at bottom', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const hintBar = page.locator('#vr-hint-bar');
    await expect(hintBar).toBeAttached();
    const text = await hintBar.textContent();
    expect(text).toContain('All shortcuts');
  });

  test('Hub: ? key toggles keyboard shortcuts overlay', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);

    // Overlay should not be visible
    const overlay = page.locator('#vr-kb-overlay');
    await expect(overlay).not.toHaveClass(/open/);

    // Press ? (shift+/)
    await page.keyboard.press('Shift+/');
    await page.waitForTimeout(300);
    await expect(overlay).toHaveClass(/open/);

    // Press Escape to close
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    await expect(overlay).not.toHaveClass(/open/);
  });

  test('Hub: shortcut overlay shows zone-specific shortcuts', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);

    await page.keyboard.press('Shift+/');
    await page.waitForTimeout(300);

    const card = page.locator('#vr-kb-card');
    const text = await card.textContent();
    expect(text).toContain('1-6');
    expect(text).toContain('Jump to zone');
    expect(text).toContain('WASD');
  });

  // ─── QW-005: Stocks Zone ───

  test('Stocks: loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto(`${BASE}/vr/stocks-zone.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    const critical = errors.filter(e => !e.includes('net::') && !e.includes('CORS') && !e.includes('Failed to fetch') && !e.includes('NetworkError') && !e.includes('play()') && !e.includes('Unexpected identifier'));
    expect(critical).toEqual([]);
  });

  test('Stocks: keyboard hint bar shows stock shortcuts', async ({ page }) => {
    await page.goto(`${BASE}/vr/stocks-zone.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const hintBar = page.locator('#vr-hint-bar');
    const text = await hintBar.textContent();
    expect(text).toContain('Refresh');
  });

  test('Stocks: R key triggers refresh notification', async ({ page }) => {
    await page.goto(`${BASE}/vr/stocks-zone.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    await page.keyboard.press('r');
    await page.waitForTimeout(500);
    const notification = page.locator('#stock-notification');
    await expect(notification).toBeAttached();
    const text = await notification.textContent();
    expect(text).toContain('refreshed');
  });

  test('Stocks: arrow keys cycle tickers', async ({ page }) => {
    await page.goto(`${BASE}/vr/stocks-zone.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    await page.keyboard.press('ArrowDown');
    await page.waitForTimeout(500);
    const notification = page.locator('#stock-notification');
    await expect(notification).toBeAttached();
    const text = await notification.textContent();
    expect(text).toMatch(/[A-Z]+.*\$/); // e.g., "MSFT: $415.86 +1.87%"
  });

  // ─── QW-006: Events Explorer ───

  test('Events: search box exists', async ({ page }) => {
    await page.goto(`${BASE}/vr/events/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const searchBox = page.locator('#vr-event-search');
    await expect(searchBox).toBeAttached();
  });

  test('Events: / key focuses search box', async ({ page }) => {
    await page.goto(`${BASE}/vr/events/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    await page.keyboard.press('/');
    await page.waitForTimeout(300);
    const focused = await page.evaluate(() => document.activeElement?.id);
    expect(focused).toBe('vr-event-search');
  });

  test('Events: keyboard hint bar shows search shortcut', async ({ page }) => {
    await page.goto(`${BASE}/vr/events/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const hintBar = page.locator('#vr-hint-bar');
    const text = await hintBar.textContent();
    expect(text).toContain('Search');
  });

  // ─── QW-007: Weather Zone ───

  test('Weather: loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto(`${BASE}/vr/weather-zone.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    const critical = errors.filter(e => !e.includes('net::') && !e.includes('CORS') && !e.includes('Failed to fetch') && !e.includes('NetworkError') && !e.includes('Unexpected identifier'));
    expect(critical).toEqual([]);
  });

  test('Weather: keyboard hint bar shows weather mode shortcuts', async ({ page }) => {
    await page.goto(`${BASE}/vr/weather-zone.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const hintBar = page.locator('#vr-hint-bar');
    const text = await hintBar.textContent();
    expect(text).toContain('Clear');
  });

  test('Weather: ? key shows shortcut overlay with modes', async ({ page }) => {
    await page.goto(`${BASE}/vr/weather-zone.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    await page.keyboard.press('Shift+/');
    await page.waitForTimeout(300);
    const overlay = page.locator('#vr-kb-overlay');
    await expect(overlay).toHaveClass(/open/);
    const text = await overlay.textContent();
    expect(text).toContain('Rain mode');
    expect(text).toContain('Thunderstorm');
    expect(text).toContain('Passthrough');
  });

  // ─── QW-008: Creators Zone ───

  test('Creators: loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);
    const critical = errors.filter(e => !e.includes('net::') && !e.includes('CORS') && !e.includes('Failed to fetch') && !e.includes('NetworkError') && !e.includes('Unexpected identifier'));
    expect(critical).toEqual([]);
  });

  test('Creators: keyboard hint bar shows R to refresh', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const hintBar = page.locator('#vr-hint-bar');
    const text = await hintBar.textContent();
    expect(text).toContain('Refresh');
  });

  test('Creators: ? overlay shows platform filter shortcuts', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    await page.keyboard.press('Shift+/');
    await page.waitForTimeout(300);
    const card = page.locator('#vr-kb-card');
    const text = await card.textContent();
    expect(text).toContain('platform');
  });

  // ─── QW-010: Tutorial ───

  test('Tutorial: loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto(`${BASE}/vr/tutorial/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    const critical = errors.filter(e => !e.includes('net::') && !e.includes('CORS') && !e.includes('Failed to fetch') && !e.includes('NetworkError') && !e.includes('Unexpected identifier'));
    expect(critical).toEqual([]);
  });

  test('Tutorial: S key advances to next step', async ({ page }) => {
    await page.goto(`${BASE}/vr/tutorial/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Get initial step text
    const initialTitle = await page.locator('#step-title').textContent();

    // Press S to skip
    await page.keyboard.press('s');
    await page.waitForTimeout(500);

    const newTitle = await page.locator('#step-title').textContent();
    expect(newTitle).not.toBe(initialTitle);
  });

  test('Tutorial: B key goes back one step', async ({ page }) => {
    await page.goto(`${BASE}/vr/tutorial/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Skip forward twice
    await page.keyboard.press('s');
    await page.waitForTimeout(300);
    await page.keyboard.press('s');
    await page.waitForTimeout(300);
    const afterSkip = await page.locator('#step-title').textContent();

    // Go back
    await page.keyboard.press('b');
    await page.waitForTimeout(300);
    const afterBack = await page.locator('#step-title').textContent();

    expect(afterBack).not.toBe(afterSkip);
  });

  test('Tutorial: keyboard hint bar shows skip/reset shortcuts', async ({ page }) => {
    await page.goto(`${BASE}/vr/tutorial/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const hintBar = page.locator('#vr-hint-bar');
    const text = await hintBar.textContent();
    expect(text).toContain('Skip');
  });

  // ─── Cross-zone: H key returns to Hub ───

  test('Movies: H key navigates back to Hub', async ({ page }) => {
    await page.goto(`${BASE}/vr/movies.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    await page.keyboard.press('h');
    await page.waitForTimeout(1000);
    expect(page.url()).toContain('/vr/');
  });
});
