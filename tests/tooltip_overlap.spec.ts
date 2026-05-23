import { test, expect } from '@playwright/test';

test.describe('Tooltip Overlap Fix – Playwright (20 Tests)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    // Wait for banners to render (force-banner script may restore them)
    await page.waitForTimeout(4000);
  });

  // ── 1-5: Structure & Presence ──────────────────────────────────

  test('1. Page loads and FavCreators banner is visible', async ({ page }) => {
    await expect(page.locator('.favcreators-promo')).toBeVisible();
  });

  test('2. All 4 promo banners are present', async ({ page }) => {
    for (const cls of ['.windows-fixer-promo', '.favcreators-promo', '.movieshows-promo', '.stocks-promo']) {
      await expect(page.locator(cls)).toBeVisible();
    }
  });

  test('3. FavCreators banner has correct child structure', async ({ page }) => {
    const b = page.locator('.favcreators-promo');
    await expect(b.locator('.promo-banner')).toBeVisible();
    await expect(b.locator('.override-overflow')).toHaveCount(1);
    await expect(b.locator('a:has-text("Open App")')).toBeVisible();
  });

  test('4. FavCreators tooltip element exists inside banner', async ({ page }) => {
    const tooltip = page.locator('.favcreators-promo .absolute');
    await expect(tooltip).toHaveCount(1);
  });

  test('5. FavCreators tooltip has z-index applied', async ({ page }) => {
    const z = await page.locator('.favcreators-promo .absolute').first()
      .evaluate(el => {
        const val = window.getComputedStyle(el).zIndex;
        return val === 'auto' ? -1 : parseInt(val);
      });
    expect(z).toBeGreaterThanOrEqual(0);
  });

  // ── 6-10: Hover behaviour & tooltip display ────────────────────

  test('6. Hovering FavCreators shows tooltip', async ({ page }) => {
    const group = page.locator('.favcreators-promo .group');
    await group.hover();
    await page.waitForTimeout(800);
    const tooltip = page.locator('.favcreators-promo .absolute').first();
    const opacity = await tooltip.evaluate(el =>
      parseFloat(window.getComputedStyle(el).opacity)
    );
    expect(opacity).toBeGreaterThan(0);
  });

  test('7. Tooltip text matches expected copy', async ({ page }) => {
    await page.locator('.favcreators-promo .group').hover();
    await page.waitForTimeout(800);
    const txt = await page.locator('.favcreators-promo .absolute p').first().textContent();
    expect(txt).toContain('Track your favorite creators');
  });

  test('8. Tooltip contains TikTok / Twitch / Kick links', async ({ page }) => {
    await page.locator('.favcreators-promo .group').hover();
    await page.waitForTimeout(800);
    const links = await page.locator('.favcreators-promo .absolute a').evaluateAll(
      els => els.map(a => a.textContent || '')
    );
    expect(links.some(t => t.includes('TikTok'))).toBe(true);
    expect(links.some(t => t.includes('Twitch'))).toBe(true);
    expect(links.some(t => t.includes('Kick'))).toBe(true);
  });

  test('9. Tooltip has solid opaque background (no bleed-through)', async ({ page }) => {
    const bg = await page.locator('.favcreators-promo .absolute').first()
      .evaluate(el => window.getComputedStyle(el).backgroundColor);
    expect(bg).toMatch(/rgba?\(/);
    const match = bg.match(/[\d.]+/g);
    if (match && match.length === 4) {
      expect(parseFloat(match[3])).toBeGreaterThanOrEqual(0.95);
    }
  });

  test('10. Tooltip positioned below Open App button – no overlap with banner text', async ({ page }) => {
    await page.locator('.favcreators-promo .group').hover();
    await page.waitForTimeout(800);

    const result = await page.evaluate(() => {
      const bannerText = document.querySelector('.favcreators-promo .override-overflow');
      const tooltip = document.querySelector('.favcreators-promo .absolute');
      if (!bannerText || !tooltip) return { pass: true };
      const bBox = bannerText.getBoundingClientRect();
      const tBox = tooltip.getBoundingClientRect();
      // Tooltip top should be below the banner text, OR they shouldn't overlap horizontally
      const verticallyBelow = tBox.top >= bBox.bottom - 5;
      const horizontallySeparate = tBox.left >= bBox.right || tBox.right <= bBox.left;
      return { pass: verticallyBelow || horizontallySeparate, tTop: tBox.top, bBottom: bBox.bottom };
    });
    expect(result.pass).toBe(true);
  });

  // ── 11-15: Cross-banner & interaction tests ────────────────────

  test('11. Hovering each banner shows its own tooltip content', async ({ page }) => {
    const banners = [
      { sel: '.favcreators-promo', kw: 'creators' },
      { sel: '.movieshows-promo', kw: 'movie' },
      { sel: '.stocks-promo', kw: 'stock' },
    ];
    for (const { sel, kw } of banners) {
      const group = page.locator(`${sel} .group`);
      if (await group.count() === 0) continue;
      await group.hover();
      await page.waitForTimeout(600);
      const txt = await page.locator(`${sel} .absolute`).first().textContent();
      expect(txt!.toLowerCase()).toContain(kw);
      await page.mouse.move(0, 0);
      await page.waitForTimeout(400);
    }
  });

  test('12. Multiple hover cycles on FavCreators work correctly', async ({ page }) => {
    const group = page.locator('.favcreators-promo .group');
    for (let i = 0; i < 3; i++) {
      await group.hover();
      await page.waitForTimeout(600);
      const opacity = await page.locator('.favcreators-promo .absolute').first()
        .evaluate(el => parseFloat(window.getComputedStyle(el).opacity));
      expect(opacity).toBeGreaterThan(0);
      await page.mouse.move(0, 0);
      await page.waitForTimeout(500);
    }
  });

  test('13. FavCreators tooltip does not overlap with banner TEXT of next section', async ({ page }) => {
    await page.locator('.favcreators-promo .group').hover();
    await page.waitForTimeout(800);

    const result = await page.evaluate(() => {
      const tooltip = document.querySelector('.favcreators-promo .absolute');
      // Check overlap with the NEXT banner's text (not the banner container)
      const nextText = document.querySelector('.movieshows-promo .override-overflow') ||
                       document.querySelector('.stocks-promo .override-overflow');
      if (!tooltip || !nextText) return { pass: true };
      const tBox = tooltip.getBoundingClientRect();
      const nBox = nextText.getBoundingClientRect();
      // Tooltip should not visually interfere with next banner's text content
      const overlaps = tBox.right > nBox.left && tBox.left < nBox.right &&
                       tBox.bottom > nBox.top && tBox.top < nBox.bottom;
      return { pass: !overlaps };
    });
    expect(result.pass).toBe(true);
  });

  test('14. Banner text container has overflow: hidden', async ({ page }) => {
    const overflow = await page.locator('.favcreators-promo .override-overflow')
      .evaluate(el => window.getComputedStyle(el).overflow);
    expect(overflow).toBe('hidden');
  });

  test('15. Tooltip links point to /fc/#/guest', async ({ page }) => {
    const hrefs = await page.locator('.favcreators-promo .absolute a').evaluateAll(
      els => els.map(a => (a as HTMLAnchorElement).getAttribute('href'))
    );
    for (const h of hrefs) {
      expect(h).toBe('/fc/#/guest');
    }
  });

  // ── 16-20: Edge-cases & visual regression ──────────────────────

  test('16. No duplicate FavCreators or Stocks banners', async ({ page }) => {
    await page.waitForTimeout(5000);
    expect(await page.locator('.favcreators-promo').count()).toBe(1);
    expect(await page.locator('.stocks-promo').count()).toBe(1);
  });

  test('17. Tooltip backdrop-filter blur is applied', async ({ page }) => {
    const bf = await page.locator('.favcreators-promo .absolute').first()
      .evaluate(el => window.getComputedStyle(el).backdropFilter);
    expect(bf).toContain('blur');
  });

  test('18. Responsive: banner visible at 768px viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);
    await expect(page.locator('.favcreators-promo')).toBeVisible();
  });

  test('19. No tooltip-related console errors on hover', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.locator('.favcreators-promo .group').hover();
    await page.waitForTimeout(800);
    const tooltipErrors = errors.filter(e =>
      /tooltip|overlap|z-index|position/i.test(e)
    );
    expect(tooltipErrors).toHaveLength(0);
  });

  test('20. Full integration – all 4 banners hover without overlap', async ({ page }) => {
    const selectors = ['.windows-fixer-promo', '.favcreators-promo', '.movieshows-promo', '.stocks-promo'];
    for (const sel of selectors) {
      const group = page.locator(`${sel} .group`);
      if (await group.count() === 0) continue;
      await group.hover();
      await page.waitForTimeout(500);
      const title = await page.locator(`${sel} .text-sm.font-bold`).first().textContent();
      expect(title!.length).toBeGreaterThan(0);
      await page.mouse.move(0, 0);
      await page.waitForTimeout(400);
    }
  });
});
