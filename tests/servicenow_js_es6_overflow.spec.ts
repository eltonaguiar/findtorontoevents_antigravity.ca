/**
 * Playwright verification for ServiceNow JavaScript reference page.
 * Loads the local file:// URL and checks the ES6 examples section for overflow.
 *
 * Run: npx playwright test tests/servicenow_js_es6_overflow.spec.ts --project="Desktop Chrome"
 */

import { test, expect } from '@playwright/test';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const HTML_PATH = join(__dirname, '..', 'findtorontoevents.ca', 'servicenow', 'javascript', 'index.html');

test.describe('ServiceNow JS Reference — ES6 Examples Overflow Check', () => {
  test('loads local file and renders ES6 section without horizontal overflow', async ({ page }) => {
    const fileUrl = `file://${HTML_PATH}`;
    await page.goto(fileUrl, { waitUntil: 'domcontentloaded' });

    // Verify the new heading exists (proves we're not seeing the old Animal/Dog version)
    await expect(page.locator('h3:has-text("Production-Grade ServiceNow Examples")')).toBeVisible();

    // Verify the single-column ES6 grid exists
    const es6Grid = page.locator('.api-grid.es6-examples');
    await expect(es6Grid).toBeVisible();

    // Count the 5 production-grade example cards
    const cards = es6Grid.locator('.api-card');
    await expect(cards).toHaveCount(5);

    // Verify none of the old Animal/Dog code is present in the ES6 section
    const es6SectionText = await es6Grid.innerText();
    expect(es6SectionText).not.toContain('var Animal = Class.create()');
    expect(es6SectionText).not.toContain('Dog.prototype = Object.extendsObject');

    // Check for horizontal overflow: compare scrollWidth vs clientWidth on the grid
    const gridOverflow = await es6Grid.evaluate((el: HTMLElement) => {
      return {
        scrollWidth: el.scrollWidth,
        clientWidth: el.clientWidth,
        hasOverflow: el.scrollWidth > el.clientWidth + 2, // 2px tolerance
      };
    });

    console.log(`[ES6 Grid] scrollWidth=${gridOverflow.scrollWidth}, clientWidth=${gridOverflow.clientWidth}, overflow=${gridOverflow.hasOverflow}`);
    expect(gridOverflow.hasOverflow).toBe(false);

    // Check each card's pre block for overflow
    for (let i = 0; i < 5; i++) {
      const pre = cards.nth(i).locator('pre');
      const preOverflow = await pre.evaluate((el: HTMLElement) => {
        return {
          scrollWidth: el.scrollWidth,
          clientWidth: el.clientWidth,
          hasOverflow: el.scrollWidth > el.clientWidth + 2,
        };
      });
      console.log(`[Card ${i + 1} pre] scrollWidth=${preOverflow.scrollWidth}, clientWidth=${preOverflow.clientWidth}, overflow=${preOverflow.hasOverflow}`);
      // Note: pre blocks are allowed to scroll horizontally (overflow-x:auto), so we don't assert false here.
      // The key check is that the grid itself doesn't force the page to scroll horizontally.
    }

    // Final sanity: page body should not have horizontal scroll
    const bodyOverflow = await page.evaluate(() => {
      const body = document.body;
      return body.scrollWidth > body.clientWidth + 2;
    });
    console.log(`[Body] has horizontal overflow: ${bodyOverflow}`);
    expect(bodyOverflow).toBe(false);
  });
});
