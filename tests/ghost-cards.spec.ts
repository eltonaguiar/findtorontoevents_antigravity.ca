import { test, expect } from '@playwright/test';

/**
 * Ghost Card Test: Validates that event card titles are visible
 * without requiring hover on patched sites.
 *
 * Root causes fixed:
 * 1. applyThumbnails() was changing card body from flex-direction:column
 *    to flex-direction:row, causing line-clamp-2 titles to collapse to zero width.
 * 2. React rendering empty <article> shells that only populate on interaction.
 *    These are now CSS-hidden via article:not(:has(button)) { display: none }.
 */

const PATCHED_SITES = [
  'https://findtorontoevents.ca/',
  'https://torontoevent.net/',
];

for (const siteUrl of PATCHED_SITES) {
  const siteName = new URL(siteUrl).hostname;

  test.describe(`Ghost Card Fix - ${siteName}`, () => {

    test('visible event cards should show titles without hover', async ({ page }) => {
      await page.goto(siteUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });

      // Wait for events to load (React hydration + events.json fetch)
      await page.waitForTimeout(10000);

      // Wait for the events-loaded class to appear on body
      await page.waitForSelector('body.events-loaded', { timeout: 20000 }).catch(() => {
        console.log('events-loaded class not found, events may still be loading');
      });

      // Find all glass-panel cards that are VISIBLE (not CSS-hidden ghost cards)
      const cards = await page.$$('[class*="glass-panel"]:not(.animate-pulse)');
      console.log(`Found ${cards.length} total event cards on ${siteName}`);
      expect(cards.length).toBeGreaterThan(0);

      let visibleTitleCount = 0;
      let checkedCount = 0;
      let hiddenByCSS = 0;
      const maxCheck = Math.min(cards.length, 12);

      for (let i = 0; i < maxCheck; i++) {
        const card = cards[i];

        // Skip cards hidden by our CSS fix (empty articles hidden via display:none)
        const isVisible = await card.isVisible();
        if (!isVisible) {
          hiddenByCSS++;
          continue;
        }

        const titleEl = await card.$('h3, h2, [class*="title"]');
        if (!titleEl) continue;

        checkedCount++;
        const titleText = await titleEl.textContent();
        const boundingBox = await titleEl.boundingBox();

        if (boundingBox && boundingBox.width > 10 && boundingBox.height > 5) {
          visibleTitleCount++;
          console.log(`  Card ${i}: Title "${titleText?.substring(0, 40)}..." visible (${boundingBox.width}x${boundingBox.height})`);
        } else {
          console.log(`  Card ${i}: Title "${titleText?.substring(0, 40)}..." GHOST (${boundingBox?.width}x${boundingBox?.height})`);
        }
      }

      console.log(`\nResults: ${visibleTitleCount}/${checkedCount} visible cards have titles (${hiddenByCSS} hidden by CSS fix)`);

      // All VISIBLE cards should have visible titles (ghost cards are CSS-hidden)
      if (checkedCount > 0) {
        const visibilityRate = visibleTitleCount / checkedCount;
        expect(visibilityRate).toBeGreaterThan(0.8);
      }
    });

    test('card body should not have flex-direction: row', async ({ page }) => {
      await page.goto(siteUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(10000);

      const brokenCards = await page.$$eval(
        '[class*="glass-panel"]:not(.animate-pulse) div[style*="flex-direction: row"]',
        (elements) => elements.length
      );

      console.log(`Cards with flex-direction:row on body: ${brokenCards}`);
      expect(brokenCards).toBe(0);
    });

    test('ghost cards should be CSS-hidden', async ({ page }) => {
      await page.goto(siteUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(10000);

      // Count empty glass-panel card containers that should be hidden
      const ghostInfo = await page.evaluate(() => {
        const cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
        let total = 0;
        let empty = 0;
        let hiddenEmpty = 0;
        cards.forEach(c => {
          total++;
          const hasTitle = c.querySelector('h3, h2');
          const hasButton = c.querySelector('button');
          if (!hasTitle && !hasButton) {
            empty++;
            const style = window.getComputedStyle(c);
            if (style.display === 'none') hiddenEmpty++;
          }
        });
        return { total, empty, hiddenEmpty };
      });

      console.log(`Cards: ${ghostInfo.total} total, ${ghostInfo.empty} empty (no h3/button), ${ghostInfo.hiddenEmpty} hidden by CSS/JS`);

      // All empty cards should be hidden (by CSS :has() or JS fixGhostCards)
      if (ghostInfo.empty > 0) {
        expect(ghostInfo.hiddenEmpty).toBe(ghostInfo.empty);
      }
    });

    test('take screenshots', async ({ page }) => {
      await page.goto(siteUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(10000);

      await page.screenshot({
        path: `test-results/ghost-cards-${siteName}-full.png`,
        fullPage: false,
      });

      const grid = await page.$('#events-grid, [class*="grid"][class*="gap"]');
      if (grid) {
        await grid.scrollIntoViewIfNeeded();
        await page.waitForTimeout(1000);
        await page.screenshot({
          path: `test-results/ghost-cards-${siteName}-grid.png`,
          fullPage: false,
        });
      }

      // Only screenshot VISIBLE cards (skip ghost cards that are display:none)
      const cards = await page.$$('[class*="glass-panel"]:not(.animate-pulse)');
      let screenshotCount = 0;
      for (let i = 0; i < Math.min(cards.length, 8) && screenshotCount < 4; i++) {
        const isVisible = await cards[i].isVisible();
        if (!isVisible) continue;
        await cards[i].screenshot({
          path: `test-results/ghost-cards-${siteName}-card-${screenshotCount}.png`,
        });
        screenshotCount++;
      }
    });
  });
}
