import { test, expect } from '@playwright/test';

test.describe('Movie Trailers (Item #3) Overlap Diagnostics', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    // Wait for banners to render
    await page.waitForTimeout(4000);
  });

  test('Movie Trailers banner is visible', async ({ page }) => {
    await expect(page.locator('.movieshows-promo')).toBeVisible();
  });

  test('Movie Trailers tooltip does NOT overlap with banner text on hover', async ({ page }) => {
    // Hover over the Movie Trailers banner
    const group = page.locator('.movieshows-promo .group');
    await group.hover();
    await page.waitForTimeout(800);

    // Take a screenshot for visual inspection
    await page.screenshot({ path: 'test-results/movieshows-hover.png', fullPage: false });

    // Check for overlap using bounding rectangles
    const overlapCheck = await page.evaluate(() => {
      const bannerText = document.querySelector('.movieshows-promo .override-overflow');
      const tooltip = document.querySelector('.movieshows-promo .absolute');
      
      if (!bannerText || !tooltip) {
        return { error: 'Elements not found', bannerText: !!bannerText, tooltip: !!tooltip };
      }

      const textRect = bannerText.getBoundingClientRect();
      const tooltipRect = tooltip.getBoundingClientRect();

      // Check if they overlap
      const overlaps = !(
        textRect.right < tooltipRect.left ||
        textRect.left > tooltipRect.right ||
        textRect.bottom < tooltipRect.top ||
        textRect.top > tooltipRect.bottom
      );

      return {
        overlaps,
        textRect: { top: textRect.top, bottom: textRect.bottom, left: textRect.left, right: textRect.right, height: textRect.height },
        tooltipRect: { top: tooltipRect.top, bottom: tooltipRect.bottom, left: tooltipRect.left, right: tooltipRect.right, height: tooltipRect.height },
        verticalGap: tooltipRect.top - textRect.bottom
      };
    });

    console.log('Overlap check result:', overlapCheck);

    // The tooltip should be positioned below the banner text with no overlap
    expect(overlapCheck.overlaps).toBe(false);
    
    // There should be a positive vertical gap (tooltip below text)
    if (overlapCheck.verticalGap !== undefined) {
      expect(overlapCheck.verticalGap).toBeGreaterThanOrEqual(-2); // Allow small margin
    }
  });

  test('Movie Trailers tooltip has solid background', async ({ page }) => {
    const bg = await page.locator('.movieshows-promo .absolute').first()
      .evaluate(el => window.getComputedStyle(el).backgroundColor);
    
    console.log('Movie Trailers tooltip background:', bg);
    
    // Should be semi-opaque or opaque
    expect(bg).toMatch(/rgba?\(/);
    const match = bg.match(/[\d.]+/g);
    if (match && match.length === 4) {
      const alpha = parseFloat(match[3]);
      console.log('Background alpha:', alpha);
      expect(alpha).toBeGreaterThanOrEqual(0.9);
    }
  });

  test('Movie Trailers tooltip position analysis', async ({ page }) => {
    await page.locator('.movieshows-promo .group').hover();
    await page.waitForTimeout(800);

    const position = await page.evaluate(() => {
      const tooltip = document.querySelector('.movieshows-promo .absolute');
      const button = document.querySelector('.movieshows-promo a:has-text("Open App")');
      
      if (!tooltip || !button) return { error: 'Elements not found' };

      const tooltipRect = tooltip.getBoundingClientRect();
      const buttonRect = button.getBoundingClientRect();

      return {
        tooltipTop: tooltipRect.top,
        buttonBottom: buttonRect.bottom,
        distanceFromButton: tooltipRect.top - buttonRect.bottom,
        tooltipZIndex: window.getComputedStyle(tooltip).zIndex,
        tooltipPosition: window.getComputedStyle(tooltip).position
      };
    });

    console.log('Position analysis:', position);
    
    // Tooltip should be positioned below the button
    if (position.distanceFromButton !== undefined) {
      expect(position.distanceFromButton).toBeGreaterThanOrEqual(0);
    }
  });

  test('All 4 banners hover without overlap', async ({ page }) => {
    const banners = [
      { name: 'Windows Fixer', selector: '.windows-fixer-promo' },
      { name: 'FavCreators', selector: '.favcreators-promo' },
      { name: 'Movie Trailers', selector: '.movieshows-promo' },
      { name: 'Stock Ideas', selector: '.stocks-promo' }
    ];

    const results = [];

    for (const banner of banners) {
      const group = page.locator(`${banner.selector} .group`);
      if (await group.count() === 0) continue;

      await group.hover();
      await page.waitForTimeout(600);

      const overlapCheck = await page.evaluate((sel) => {
        const bannerText = document.querySelector(`${sel} .override-overflow`);
        const tooltip = document.querySelector(`${sel} .absolute`);
        
        if (!bannerText || !tooltip) return { error: 'Elements not found' };

        const textRect = bannerText.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();

        const overlaps = !(
          textRect.right < tooltipRect.left ||
          textRect.left > tooltipRect.right ||
          textRect.bottom < tooltipRect.top ||
          textRect.top > tooltipRect.bottom
        );

        return {
          overlaps,
          textHeight: textRect.height,
          tooltipTop: tooltipRect.top,
          textBottom: textRect.bottom
        };
      }, banner.selector);

      results.push({ name: banner.name, ...overlapCheck });
      
      await page.mouse.move(0, 0);
      await page.waitForTimeout(400);
    }

    console.log('All banners overlap check:', results);
    
    // All banners should have no overlap
    for (const result of results) {
      expect(result.overlaps).toBe(false);
    }
  });
});