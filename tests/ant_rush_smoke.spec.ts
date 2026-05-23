/**
 * Ant Rush AR – Smoke test
 * Verifies the ant-rush page loads correctly across devices.
 */
import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';
const PAGE_URL = `${BASE}/vr/ant-rush/`;
const NAV_TIMEOUT = 30000;

const NON_CRITICAL = [
  'net::', 'CORS', 'Failed to fetch', 'NetworkError',
  'immersive-vr', 'navigator.xr', 'WebXR', 'webxr', 'XRSystem',
  'getGamepads', 'AudioContext', 'play()', 'DOMException',
  'ServiceWorker', 'ResizeObserver', 'Script error',
  'NotAllowedError', 'Permissions policy', 'Feature policy',
  'Mixed Content', 'getUserMedia', 'NotFoundError',
];

function isCritical(msg: string): boolean {
  return !NON_CRITICAL.some(p => msg.toLowerCase().includes(p.toLowerCase()));
}

test.describe('Ant Rush AR — Smoke Tests', () => {
  test('Page loads with HTTP 200', async ({ page }) => {
    const response = await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    expect(response?.status()).toBeLessThan(400);
  });

  test('Title contains Ant Rush', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    const title = await page.title();
    expect(title.toLowerCase()).toContain('ant rush');
  });

  test('No critical JS errors on load', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(3000);
    const critical = errors.filter(isCritical);
    if (critical.length > 0) console.log('Critical errors:', critical);
    expect(critical).toEqual([]);
  });

  test('Menu screen is visible on load', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    const menuScreen = page.locator('#menu-screen');
    await expect(menuScreen).toBeVisible();
  });

  test('Both game mode cards exist (Bed Challenge + Quick Mode)', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await expect(page.locator('#card-bed')).toBeVisible();
    await expect(page.locator('#card-quick')).toBeVisible();
  });

  test('Clicking Bed Challenge opens bed setup', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.click('#card-bed');
    await page.waitForTimeout(500);
    const bedSetup = page.locator('#bed-setup');
    await expect(bedSetup).toBeVisible();
    // Difficulty cards
    const diffCards = page.locator('.diff-card');
    expect(await diffCards.count()).toBe(3);
  });

  test('Clicking Quick Mode opens quick setup with upload boxes', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.click('#card-quick');
    await page.waitForTimeout(500);
    const quickSetup = page.locator('#quick-setup');
    await expect(quickSetup).toBeVisible();
    // Upload boxes
    await expect(page.locator('#box-before')).toBeVisible();
    await expect(page.locator('#box-after')).toBeVisible();
    // Time input
    await expect(page.locator('#est-time')).toBeVisible();
    // Start button should be disabled (no images uploaded)
    const startBtn = page.locator('#quick-start');
    await expect(startBtn).toBeDisabled();
  });

  test('Back buttons return to menu', async ({ page }) => {
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    // Go to bed setup, then back
    await page.click('#card-bed');
    await page.waitForTimeout(300);
    await page.click('#bed-back');
    await page.waitForTimeout(500);
    // Menu should be visible again (opacity transition)
    const menuOpacity = await page.evaluate(() => {
      const el = document.getElementById('menu-screen');
      return el ? !el.classList.contains('hidden') : false;
    });
    // After resetToMenu, hidden class is removed
    expect(menuOpacity).toBe(true);
  });

  test('Three.js CDN script loaded', async ({ page }) => {
    const js404s: string[] = [];
    page.on('response', (res) => {
      if (res.status() === 404 && res.url().includes('three')) js404s.push(res.url());
    });
    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(2000);
    expect(js404s).toEqual([]);
    const hasThree = await page.evaluate(() => typeof THREE !== 'undefined');
    expect(hasThree).toBe(true);
  });

  test('VR Hub has ant-rush zone link', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded', timeout: NAV_TIMEOUT });
    await page.waitForTimeout(3000);
    const hasZoneLink = await page.evaluate(() => {
      const els = document.querySelectorAll('[zone-link]');
      for (const el of els) {
        const attr = el.getAttribute('zone-link');
        if (attr && typeof attr === 'string' && attr.includes('ant-rush')) return true;
        // A-Frame may parse attribute into object; check innerHTML fallback
        if (el.outerHTML && el.outerHTML.includes('ant-rush')) return true;
      }
      return false;
    });
    expect(hasZoneLink).toBe(true);
  });
});
