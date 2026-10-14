/**
 * Playwright verification for the "JavaScript for Coding Interviews" cheat sheet
 * (js-interview.html) — section 5, the eleven iconic problems and the reusable
 * concept each one drills.
 *
 * Run: npx playwright test tests/js-interview-iconic.spec.ts --project="Desktop Chrome"
 */

import { test, expect } from '@playwright/test';
import { join } from 'path';

// Tests run from the project root; avoid import.meta (keeps the spec CJS).
const HTML_PATH = join(process.cwd(), 'findtorontoevents.ca', 'servicenow', 'javascript', 'js-interview.html');

test.describe('js-interview.html — section 5 iconic problems', () => {
  test('renders the 5 groups, 12 code samples, and no console errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
    page.on('pageerror', (err) => consoleErrors.push(String(err)));

    await page.goto(`file://${HTML_PATH}`, { waitUntil: 'domcontentloaded' });

    // Section 5 exists with its five grouped subsections
    const section5 = page.locator('h2#iconic');
    await expect(section5).toBeVisible();
    await expect(section5).toContainText('Iconic problems');
    for (const id of ['iconic-arrays', 'iconic-trees', 'iconic-graphs', 'iconic-design', 'iconic-dp']) {
      await expect(page.locator(`h3#${id}`)).toBeVisible();
    }

    // 12 published code samples (1 pre-existing frequency block + 11 iconic functions)
    const codeBlocks = page.locator('pre code');
    await expect(codeBlocks).toHaveCount(12);

    // Every iconic function is actually on the page (exactly one copy of each)
    for (const fn of ['twoSum', 'maxProfit', 'lengthOfLongestSubstring', 'threeSum',
                      'invertTree', 'isValidBST', 'numIslands', 'canFinish',
                      'LRUCache', 'rob(nums)', 'coinChange']) {
      await expect(codeBlocks.filter({ hasText: fn })).toHaveCount(1);
    }

    // Section 5 summary table: 11 problems + header row
    const summaryBody = page.locator('h2#iconic ~ .table-wrap').first().locator('tbody tr');
    await expect(summaryBody).toHaveCount(11);

    // Section 4 pattern table now has 7 original + 3 new rows
    const patternRows = page.locator('h2#patterns + .table-wrap tbody tr');
    await expect(patternRows).toHaveCount(10);

    // Entities decode to real characters (no literal markup leaking into text)
    const firstBlock = await codeBlocks.first().innerText();
    expect(firstBlock).toContain('count[c]');

    const arraysHeading = await page.locator('h3#iconic-arrays').innerText();
    expect(arraysHeading).toContain('Arrays');

    const goodBox = await page.locator('#iconic-arrays ~ .good').first().innerText();
    expect(goodBox).toContain('while (l < r && nums[l] === nums[l + 1]) l++;');

    // The prose table cell that carries markup must render as plain text:
    // the em-dash arrows in headings/entities are decoded, never shown literally.
    const cardText = await page.locator('.card').innerText();
    expect(cardText).not.toContain('<code>');
    expect(cardText).not.toContain('<pre>');
    expect(cardText).not.toContain('4. Which building block each medium pattern needs'.slice(0, 0) + '<h2');

    // No horizontal page overflow
    const overflow = await page.evaluate(
      () => document.body.scrollWidth > document.documentElement.clientWidth + 2
    );
    expect(overflow).toBe(false);

    expect(consoleErrors, `console errors: ${consoleErrors.join(' | ')}`).toHaveLength(0);
  });
});
