import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// Validate the exact GitHub Pages artifact served from docs/bestiejob.
const DATA_PATH = path.resolve(process.cwd(), 'docs/bestiejob/data/verified_leads.json');
const PUBLISHED = JSON.parse(fs.readFileSync(DATA_PATH, 'utf-8')) as Array<any>;

test.describe('BESTIEJOB GitHub Pages', () => {
  test('loads with correct title and header', async ({ page }) => {
    await page.goto('./');
    await expect(page).toHaveTitle(/BestieJob/i);
    await expect(page.locator('h1')).toContainText(/SN\/SF Developer Leads/i);
  });

  test('renders every published lead from the JSON feed', async ({ page }) => {
    await page.goto('./');
    const rows = page.locator('#rows tr');
    await expect(rows).toHaveCount(PUBLISHED.length, { timeout: 10000 });
    await expect(page.locator('#count')).toContainText(`${PUBLISHED.length} of ${PUBLISHED.length}`);
  });

  test('published feed is rights-gated and live', async () => {
    expect(PUBLISHED.length).toBeGreaterThan(0);
    for (const r of PUBLISHED) {
      expect(r.redistribute, `${r.title} must be redistributable`).toBe(true);
      expect(r.live, `${r.title} must be live`).toBe(true);
      expect(String(r.url)).toMatch(/^https?:\/\//);
    }
    // LinkedIn/Workday are never publicly redistributable
    const sources = new Set(PUBLISHED.map(r => String(r.source).toLowerCase()));
    expect(sources.has('linkedin')).toBe(false);
    expect(sources.has('workday')).toBe(false);
  });

  test('track filter narrows to a single track', async ({ page }) => {
    const snCount = PUBLISHED.filter(r => r.track === 'servicenow').length;
    const sfCount = PUBLISHED.filter(r => r.track === 'salesforce').length;
    await page.goto('./');

    await page.locator('#track').selectOption('servicenow');
    const snBadges = page.locator('#rows tr td:nth-child(5) .badge');
    await expect(snBadges).toHaveCount(snCount);
    for (let i = 0; i < snCount; i++) {
      await expect(snBadges.nth(i)).toHaveText(/ServiceNow/i);
    }
    await expect(page.locator('#count')).toContainText(`${snCount} of ${PUBLISHED.length}`);

    await page.locator('#track').selectOption('salesforce');
    await expect(page.locator('#rows tr')).toHaveCount(sfCount);

    await page.locator('#track').selectOption('');
    await expect(page.locator('#rows tr')).toHaveCount(PUBLISHED.length);
  });

  test('text search filters rows', async ({ page }) => {
    await page.goto('./');
    const term = String(PUBLISHED[0].company || PUBLISHED[0].title).split(' ')[0];
    await page.locator('#q').fill(term);
    const rows = page.locator('#rows tr');
    const n = await rows.count();
    expect(n).toBeGreaterThan(0);
    expect(n).toBeLessThanOrEqual(PUBLISHED.length);
    const first = (await rows.first().innerText()).toLowerCase();
    expect(first).toContain(term.toLowerCase());
  });

  test('every row link is a safe external link', async ({ page }) => {
    await page.goto('./');
    const links = page.locator('#rows tr a');
    const n = await links.count();
    expect(n).toBe(PUBLISHED.length);
    for (let i = 0; i < Math.min(n, 10); i++) {
      const a = links.nth(i);
      await expect(a).toHaveAttribute('href', /^https?:\/\//);
      await expect(a).toHaveAttribute('target', '_blank');
      await expect(a).toHaveAttribute('rel', /noopener/);
    }
  });

  test('no console errors or uncaught page errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto('./');
    await expect(page.locator('#rows tr').first()).toBeVisible({ timeout: 10000 });
    expect(errors, errors.join('\n')).toEqual([]);
  });

  test('mobile viewport renders without horizontal page overflow', async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    await page.goto('./');
    await expect(page.locator('#rows tr').first()).toBeVisible({ timeout: 10000 });
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth - document.documentElement.clientWidth);
    // table scrolls inside .wrap; the page itself must not overflow by more than a hair
    expect(overflow).toBeLessThanOrEqual(2);
    await ctx.close();
  });
});
