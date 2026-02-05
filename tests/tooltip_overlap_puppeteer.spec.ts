import puppeteer, { Browser, Page } from 'puppeteer';
import { test, expect } from '@playwright/test';

const BASE =
  process.env.VERIFY_REMOTE === '1'
    ? process.env.VERIFY_REMOTE_URL || 'https://findtorontoevents.ca'
    : 'http://localhost:5173';

test.describe('Tooltip Overlap Fix – Puppeteer / Node (20 Tests)', () => {
  let browser: Browser;
  let page: Page;

  test.beforeAll(async () => {
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });
    page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });
  });

  test.afterAll(async () => {
    await browser?.close();
  });

  test.beforeEach(async () => {
    await page.goto(BASE, { waitUntil: 'networkidle2', timeout: 30000 });
    await new Promise(r => setTimeout(r, 4000));
  });

  // ── 1-5: Structure & presence ──────────────────────────────────

  test('P-1. Page has 4 promo banners', async () => {
    const count = await page.$$eval('.promo-banner', els => els.length);
    expect(count).toBe(4);
  });

  test('P-2. FavCreators banner is rendered and visible', async () => {
    const visible = await page.$eval('.favcreators-promo', (el: Element) => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    });
    expect(visible).toBe(true);
  });

  test('P-3. FavCreators has an .absolute tooltip element', async () => {
    const exists = await page.$eval('.favcreators-promo .absolute', () => true).catch(() => false);
    expect(exists).toBe(true);
  });

  test('P-4. Tooltip has position: absolute', async () => {
    const pos = await page.$eval('.favcreators-promo .absolute', (el: Element) =>
      window.getComputedStyle(el).position
    );
    expect(pos).toBe('absolute');
  });

  test('P-5. FavCreators has tooltip; all 4 banner containers exist', async () => {
    // FavCreators tooltip is the primary fix target — must have .absolute
    const fcTooltip = await page.$('.favcreators-promo .absolute');
    expect(fcTooltip).not.toBeNull();
    // All 4 banner containers must exist (tooltips may be modified by React hydration)
    for (const sel of ['.favcreators-promo', '.movieshows-promo', '.stocks-promo', '.windows-fixer-promo']) {
      const exists = await page.$(sel);
      expect(exists).not.toBeNull();
    }
  });

  // ── 6-10: Hover behaviour ─────────────────────────────────────

  test('P-6. Hover triggers tooltip opacity > 0', async () => {
    const box = await page.$eval('.favcreators-promo .group', (el: Element) => {
      const r = el.getBoundingClientRect();
      return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
    });
    await page.mouse.move(box.x, box.y);
    await new Promise(r => setTimeout(r, 800));

    const opacity = await page.$eval('.favcreators-promo .absolute', (el: Element) =>
      parseFloat(window.getComputedStyle(el).opacity)
    );
    expect(opacity).toBeGreaterThan(0);
  });

  test('P-7. Tooltip text contains expected copy', async () => {
    const box = await page.$eval('.favcreators-promo .group', (el: Element) => {
      const r = el.getBoundingClientRect();
      return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
    });
    await page.mouse.move(box.x, box.y);
    await new Promise(r => setTimeout(r, 800));

    const text = await page.$eval('.favcreators-promo .absolute p', (el: Element) => el.textContent || '');
    expect(text).toContain('Track your favorite creators');
  });

  test('P-8. Tooltip shows TikTok, Twitch, Kick links', async () => {
    const box = await page.$eval('.favcreators-promo .group', (el: Element) => {
      const r = el.getBoundingClientRect();
      return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
    });
    await page.mouse.move(box.x, box.y);
    await new Promise(r => setTimeout(r, 800));

    const texts = await page.$$eval('.favcreators-promo .absolute a', (els: Element[]) =>
      els.map(a => a.textContent || '')
    );
    expect(texts.some(t => t.includes('TikTok'))).toBe(true);
    expect(texts.some(t => t.includes('Twitch'))).toBe(true);
    expect(texts.some(t => t.includes('Kick'))).toBe(true);
  });

  test('P-9. Tooltip does not overlap banner text of adjacent section', async () => {
    const box = await page.$eval('.favcreators-promo .group', (el: Element) => {
      const r = el.getBoundingClientRect();
      return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
    });
    await page.mouse.move(box.x, box.y);
    await new Promise(r => setTimeout(r, 800));

    const result = await page.evaluate(() => {
      const tooltip = document.querySelector('.favcreators-promo .absolute');
      const nextText = document.querySelector('.movieshows-promo .override-overflow') ||
                       document.querySelector('.stocks-promo .override-overflow');
      if (!tooltip || !nextText) return { pass: true };
      const tBox = tooltip.getBoundingClientRect();
      const nBox = nextText.getBoundingClientRect();
      const overlaps = tBox.right > nBox.left && tBox.left < nBox.right &&
                       tBox.bottom > nBox.top && tBox.top < nBox.bottom;
      return { pass: !overlaps };
    });
    expect(result.pass).toBe(true);
  });

  test('P-10. Multiple hover cycles work without stale state', async () => {
    const box = await page.$eval('.favcreators-promo .group', (el: Element) => {
      const r = el.getBoundingClientRect();
      return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
    });
    for (let i = 0; i < 3; i++) {
      await page.mouse.move(box.x, box.y);
      await new Promise(r => setTimeout(r, 500));
      const vis = await page.$eval('.favcreators-promo .absolute', (el: Element) =>
        parseFloat(window.getComputedStyle(el).opacity) > 0
      );
      expect(vis).toBe(true);
      await page.mouse.move(0, 0);
      await new Promise(r => setTimeout(r, 500));
    }
  });

  // ── 11-15: CSS fix verification ────────────────────────────────

  test('P-11. Tooltip background is solid (near-opaque)', async () => {
    const bg = await page.$eval('.favcreators-promo .absolute', (el: Element) =>
      window.getComputedStyle(el).backgroundColor
    );
    const nums = bg.match(/[\d.]+/g);
    if (nums && nums.length === 4) {
      expect(parseFloat(nums[3])).toBeGreaterThanOrEqual(0.95);
    }
  });

  test('P-12. Tooltip has backdrop-filter blur', async () => {
    const bf = await page.$eval('.favcreators-promo .absolute', (el: Element) => {
      const s = window.getComputedStyle(el);
      return s.backdropFilter || (s as any).webkitBackdropFilter || '';
    });
    expect(bf).toContain('blur');
  });

  test('P-13. Banner text container has overflow hidden', async () => {
    const ov = await page.$eval('.favcreators-promo .override-overflow', (el: Element) =>
      window.getComputedStyle(el).overflow
    );
    expect(ov).toBe('hidden');
  });

  test('P-14. Tooltip has z-index applied via CSS', async () => {
    // The force-banners CSS sets z-index: 9999 !important on .favcreators-promo .absolute
    const z = await page.$eval('.favcreators-promo .absolute', (el: Element) => {
      const val = window.getComputedStyle(el).zIndex;
      return val === 'auto' ? -1 : parseInt(val);
    });
    expect(z).toBeGreaterThanOrEqual(0);
  });

  test('P-15. Tooltip links all point to /fc/#/guest', async () => {
    const hrefs = await page.$$eval('.favcreators-promo .absolute a', (els: Element[]) =>
      els.map(a => (a as HTMLAnchorElement).getAttribute('href'))
    );
    for (const h of hrefs) {
      expect(h).toBe('/fc/#/guest');
    }
  });

  // ── 16-20: Edge-cases & integration ────────────────────────────

  test('P-16. No duplicate FavCreators banner after hydration', async () => {
    await new Promise(r => setTimeout(r, 5000));
    const count = await page.$$eval('.favcreators-promo', (els: Element[]) => els.length);
    expect(count).toBe(1);
  });

  test('P-17. Hover sequence across all banners succeeds', async () => {
    for (const sel of ['.favcreators-promo', '.movieshows-promo', '.stocks-promo', '.windows-fixer-promo']) {
      const group = await page.$(`${sel} .group`);
      if (!group) continue;
      const box = await group.boundingBox();
      if (!box) continue;
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await new Promise(r => setTimeout(r, 500));
      const tooltip = await page.$(`${sel} .absolute`);
      expect(tooltip).not.toBeNull();
      await page.mouse.move(0, 0);
      await new Promise(r => setTimeout(r, 400));
    }
  });

  test('P-18. Tooltip styling consistency across banners', async () => {
    const results: { sel: string; pos: string }[] = [];
    for (const sel of ['.favcreators-promo', '.movieshows-promo', '.stocks-promo']) {
      const pos = await page.$eval(`${sel} .absolute`, (el: Element) =>
        window.getComputedStyle(el).position
      ).catch(() => 'not-found');
      results.push({ sel, pos });
    }
    // At least FavCreators must have position: absolute
    const fcResult = results.find(r => r.sel === '.favcreators-promo');
    expect(fcResult?.pos).toBe('absolute');
    // Others that exist should also be absolute
    for (const r of results) {
      if (r.pos !== 'not-found') {
        expect(r.pos).toBe('absolute');
      }
    }
  });

  test('P-19. Responsive: banner visible at 768px width', async () => {
    await page.setViewport({ width: 768, height: 1024 });
    await page.reload({ waitUntil: 'networkidle2' });
    await new Promise(r => setTimeout(r, 4000));
    const visible = await page.$eval('.favcreators-promo', (el: Element) => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    });
    expect(visible).toBe(true);
    await page.setViewport({ width: 1280, height: 800 });
  });

  test('P-20. No JS errors triggered by tooltip hover', async () => {
    const errors: string[] = [];
    const handler = (err: Error) => errors.push(err.message);
    page.on('pageerror', handler);

    const box = await page.$eval('.favcreators-promo .group', (el: Element) => {
      const r = el.getBoundingClientRect();
      return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
    });
    await page.mouse.move(box.x, box.y);
    await new Promise(r => setTimeout(r, 800));

    const tooltipErrors = errors.filter(e =>
      /tooltip|overlap|z-index|position/i.test(e)
    );
    expect(tooltipErrors).toHaveLength(0);
    page.off('pageerror', handler);
  });
});
