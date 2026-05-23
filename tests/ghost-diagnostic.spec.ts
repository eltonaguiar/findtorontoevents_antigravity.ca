import { test, expect } from '@playwright/test';

/**
 * Diagnostic test: Inspect every card and its PARENT wrapper
 * to understand why ghost cards still show as blank spaces.
 */

test('diagnose ghost cards - parent wrapper analysis', async ({ page }) => {
  await page.goto('https://findtorontoevents.ca/', {
    waitUntil: 'domcontentloaded',
    timeout: 45000,
  });

  await page.waitForTimeout(12000);

  // Take screenshots at different scroll positions
  await page.screenshot({ path: 'test-results/ghost-diag-top.png', fullPage: false });

  const analysis = await page.evaluate(() => {
    const cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
    const results: Array<{
      index: number;
      // Card info
      cardTag: string;
      cardDisplay: string;
      cardWidth: number;
      cardHeight: number;
      hasH3: boolean;
      h3Text: string;
      hasButton: boolean;
      // Parent info
      parentTag: string;
      parentClass: string;
      parentDisplay: string;
      parentWidth: number;
      parentHeight: number;
      parentVisible: boolean;
      // Grandparent info
      gpTag: string;
      gpClass: string;
      gpDisplay: string;
      // Is this card a "blank space" problem?
      isBlankSpace: boolean;
    }> = [];

    cards.forEach((card, i) => {
      const el = card as HTMLElement;
      const cardStyle = window.getComputedStyle(el);
      const parent = el.parentElement as HTMLElement;
      const gp = parent?.parentElement as HTMLElement;
      const h3 = el.querySelector('h3');

      const parentStyle = parent ? window.getComputedStyle(parent) : null;
      const gpStyle = gp ? window.getComputedStyle(gp) : null;

      const cardHidden = cardStyle.display === 'none' || el.offsetWidth === 0;
      const parentVisible = parent ? (parentStyle!.display !== 'none' && parent.offsetWidth > 0) : false;

      results.push({
        index: i,
        cardTag: el.tagName,
        cardDisplay: cardStyle.display,
        cardWidth: el.offsetWidth,
        cardHeight: el.offsetHeight,
        hasH3: !!h3,
        h3Text: h3 ? (h3.textContent || '').trim().substring(0, 40) : '',
        hasButton: !!el.querySelector('button'),
        parentTag: parent?.tagName || '',
        parentClass: (parent?.className || '').substring(0, 80),
        parentDisplay: parentStyle?.display || '',
        parentWidth: parent?.offsetWidth || 0,
        parentHeight: parent?.offsetHeight || 0,
        parentVisible,
        gpTag: gp?.tagName || '',
        gpClass: (gp?.className || '').substring(0, 80),
        gpDisplay: gpStyle?.display || '',
        // BLANK SPACE = card is hidden but parent wrapper is still visible
        isBlankSpace: cardHidden && parentVisible,
      });
    });
    return results;
  });

  console.log(`\n=== GHOST CARD PARENT ANALYSIS ===`);
  console.log(`Total cards: ${analysis.length}\n`);

  let blankSpaceCount = 0;

  for (const c of analysis) {
    if (c.isBlankSpace || c.index < 10) {
      const status = c.isBlankSpace
        ? '🔴 BLANK SPACE (card hidden, parent visible)'
        : c.cardDisplay === 'none'
        ? '🟡 Hidden (card + parent both hidden)'
        : '🟢 Visible card';

      console.log(`Card ${c.index}: ${status}`);
      console.log(`  CARD: ${c.cardTag} display=${c.cardDisplay} size=${c.cardWidth}x${c.cardHeight} hasH3=${c.hasH3} title="${c.h3Text}"`);
      console.log(`  PARENT: ${c.parentTag} display=${c.parentDisplay} size=${c.parentWidth}x${c.parentHeight} visible=${c.parentVisible}`);
      console.log(`  PARENT class="${c.parentClass}"`);
      console.log(`  GRANDPARENT: ${c.gpTag} display=${c.gpDisplay}`);
      console.log(`  GP class="${c.gpClass}"`);
      console.log('');

      if (c.isBlankSpace) blankSpaceCount++;
    }
  }

  console.log(`\n=== BLANK SPACE SUMMARY ===`);
  console.log(`Blank spaces (card hidden, parent visible): ${blankSpaceCount}`);
  console.log(`Total cards: ${analysis.length}`);
  console.log(`Cards with display=none: ${analysis.filter(c => c.cardDisplay === 'none').length}`);
  console.log(`Cards with display=flex: ${analysis.filter(c => c.cardDisplay === 'flex').length}`);

  // Scroll and take more screenshots
  await page.evaluate(() => window.scrollBy(0, 600));
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'test-results/ghost-diag-scroll1.png', fullPage: false });

  await page.evaluate(() => window.scrollBy(0, 600));
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'test-results/ghost-diag-scroll2.png', fullPage: false });

  expect(analysis.length).toBeGreaterThan(0);
});
