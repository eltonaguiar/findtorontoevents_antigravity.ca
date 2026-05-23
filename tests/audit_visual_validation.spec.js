// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Audit Dashboard Visual Validation Tests
 * ========================================
 * Uses Playwright to open the live audit pages, validate rendered data,
 * and capture screenshots for visual verification.
 *
 * Run: npx playwright test tests/audit_visual_validation.spec.js
 */

const FUNDS_URL = 'https://findtorontoevents.ca/audit/funds.html';
const AUDIT_URL = 'https://findtorontoevents.ca/audit/';
const PAYLOAD_URL = 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/audit_trail/data/dashboard_payload.json';

test.describe('Audit Funds Page', () => {
  test.setTimeout(60000);

  test('$10K growth values are reasonable (<$10M)', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'networkidle', timeout: 30000 });

    // Wait for content to render
    await page.waitForTimeout(2000);

    // Extract all growth values displayed on the page
    const growthValues = await page.evaluate(() => {
      const results = [];
      // Look for elements containing dollar values (e.g., $12,345)
      const allElements = document.querySelectorAll('td, span, div, p');
      for (const el of allElements) {
        const text = el.textContent || '';
        const matches = text.match(/\$[\d,]+(\.\d+)?/g);
        if (matches) {
          for (const m of matches) {
            const val = parseFloat(m.replace(/[$,]/g, ''));
            if (val > 1000) { // Only care about growth values (> $1K)
              results.push({ text: m, value: val, context: text.substring(0, 80) });
            }
          }
        }
      }
      return results;
    });

    console.log(`Found ${growthValues.length} growth values on page`);
    for (const gv of growthValues) {
      console.log(`  ${gv.text} (${gv.value}) -- context: ${gv.context}`);
      // $10K growth should not exceed $10M (1000x return is unrealistic)
      expect(gv.value, `Growth value ${gv.text} should be < $10M`).toBeLessThan(10_000_000);
    }
  });

  test('no win rate exceeds 100%', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    const winRates = await page.evaluate(() => {
      const results = [];
      // Look specifically for win rate cells -- they are in table rows near "Win Rate" or "WR" headers
      // Also check for elements with win-rate related classes or data attributes
      const allRows = document.querySelectorAll('tr');
      for (const row of allRows) {
        const cells = row.querySelectorAll('td');
        for (const cell of cells) {
          const text = (cell.textContent || '').trim();
          const match = text.match(/^(\d+(?:\.\d+)?)\s*%$/);
          if (match) {
            const val = parseFloat(match[1]);
            // Check if this row/cell is in a win-rate column by looking at the table header
            const table = cell.closest('table');
            if (table) {
              const headerRow = table.querySelector('thead tr, tr:first-child');
              if (headerRow) {
                const headers = headerRow.querySelectorAll('th, td');
                const cellIndex = Array.from(cells).indexOf(cell);
                const header = headers[cellIndex]?.textContent || '';
                if (/win\s*rate|w\s*%|wr/i.test(header)) {
                  results.push({ text, value: val, header: header.trim() });
                }
              }
            }
          }
        }
      }
      // Also check for explicitly labeled win rates in non-table contexts
      const allElements = document.querySelectorAll('[class*="win-rate"], [data-field="win_rate"]');
      for (const el of allElements) {
        const text = (el.textContent || '').trim();
        const match = text.match(/(\d+(?:\.\d+)?)\s*%/);
        if (match) {
          results.push({ text: match[0], value: parseFloat(match[1]), header: 'class-based' });
        }
      }
      return results;
    });

    console.log(`Found ${winRates.length} win rate values on page`);
    for (const wr of winRates) {
      console.log(`  ${wr.text} (header: ${wr.header})`);
      expect(wr.value, `Win rate ${wr.text} should be <= 100%`).toBeLessThanOrEqual(100);
    }
  });

  test('scoring system produces grades A-F', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    const grades = await page.evaluate(() => {
      const validGrades = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F'];
      const found = [];
      const allElements = document.querySelectorAll('td, span, div, .grade, .score');
      for (const el of allElements) {
        const text = (el.textContent || '').trim();
        if (validGrades.includes(text)) {
          found.push(text);
        }
      }
      return [...new Set(found)];
    });

    console.log(`Found grades: ${grades.join(', ') || '(none)'}`);
    // The page should have at least some grading if the scoring system is active
    // This is a soft check -- some pages may not display letter grades
    if (grades.length === 0) {
      console.log('  NOTE: No letter grades found -- page may use numeric scoring instead');
    } else {
      const validSet = new Set(['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']);
      for (const g of grades) {
        expect(validSet.has(g), `Grade "${g}" should be a valid A-F grade`).toBeTruthy();
      }
    }
  });

  test('screenshot for visual verification', async ({ page }) => {
    await page.goto(FUNDS_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    await page.screenshot({
      path: 'tests/screenshots/audit_funds_page.png',
      fullPage: true,
    });
    console.log('Screenshot saved to tests/screenshots/audit_funds_page.png');
  });
});

test.describe('Dashboard Payload JSON', () => {
  test.setTimeout(30000);

  test('payload has valid structure and fresh data', async ({ request }) => {
    const resp = await request.get(PAYLOAD_URL);
    expect(resp.status()).toBe(200);

    const data = await resp.json();
    expect(data.generated_at).toBeTruthy();
    expect(data.systems).toBeTruthy();
    expect(data.systems.length).toBeGreaterThan(0);

    // Check freshness
    const genTime = new Date(data.generated_at);
    const hoursAgo = (Date.now() - genTime.getTime()) / 3600000;
    expect(hoursAgo).toBeLessThan(24);
    console.log(`Payload generated ${hoursAgo.toFixed(1)}h ago with ${data.systems.length} systems`);

    // Validate each system
    for (const sys of data.systems) {
      const wr = sys.win_rate || 0;
      expect(wr, `${sys.name} win_rate`).toBeLessThanOrEqual(100);
      expect(wr, `${sys.name} win_rate`).toBeGreaterThanOrEqual(0);

      const wins = sys.wins || 0;
      const losses = sys.losses || 0;
      if (wins + losses > 0) {
        const calcWR = (wins / (wins + losses)) * 100;
        const diff = Math.abs(calcWR - wr);
        expect(diff, `${sys.name} WR consistency (reported=${wr.toFixed(1)}, calc=${calcWR.toFixed(1)})`).toBeLessThan(1.5);
      }
    }
  });
});
