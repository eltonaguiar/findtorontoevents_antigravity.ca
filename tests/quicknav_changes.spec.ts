import { test, expect } from '@playwright/test';

const BASE = process.env.BASE_URL || 'http://localhost:5173';

// Helper: open the Quick Nav drawer
async function openNav(page: any) {
  const hamburger = page.locator('button[title="Quick Navigation"]');
  await hamburger.click();
  await page.waitForTimeout(500);
}

// Helper: scope locators to the Quick Nav drawer only
function navLocator(page: any, selector: string) {
  return page.locator('.fixed.inset-0.z-\\[250\\]').locator(selector);
}

test.describe('Quick Nav Menu — Full Hierarchy', () => {
  let jsErrors: string[] = [];

  test.beforeEach(async ({ page }) => {
    jsErrors = [];
    page.on('pageerror', (error) => {
      jsErrors.push(error.message);
    });
    await page.goto(BASE, { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(3000);
  });

  test('page loads without critical JS errors', async ({ page }) => {
    const criticalErrors = jsErrors.filter(
      (e) =>
        e.includes('SyntaxError') ||
        e.includes('TypeError') ||
        e.includes('ReferenceError')
    );
    if (criticalErrors.length > 0) {
      console.log('Critical JS errors:', criticalErrors);
    }
    expect(criticalErrors).toHaveLength(0);
  });

  test('page title is correct', async ({ page }) => {
    expect(await page.title()).toContain('Toronto Events');
  });

  test('hamburger opens nav drawer', async ({ page }) => {
    await openNav(page);
    const overlay = page.locator('.fixed.inset-0.z-\\[250\\]');
    const opacity = await overlay.evaluate((el: Element) =>
      window.getComputedStyle(el).opacity
    );
    expect(parseFloat(opacity)).toBeGreaterThan(0);
  });

  test('Platform — Global Feed button', async ({ page }) => {
    await openNav(page);
    await expect(navLocator(page, 'button:has-text("Global Feed")')).toBeVisible();
  });

  test('Platform — My Collection button', async ({ page }) => {
    await openNav(page);
    await expect(navLocator(page, 'button:has-text("My Collection")')).toBeVisible();
  });

  test('gold glow header visible with gradient + animation', async ({ page }) => {
    await openNav(page);
    const goldHeader = navLocator(page, '.gold-glow-nav');
    await expect(goldHeader).toBeVisible();
    await expect(goldHeader).toContainText('OTHER STUFF');
    const bg = await goldHeader.evaluate((el: Element) =>
      window.getComputedStyle(el).backgroundImage
    );
    expect(bg).toContain('gradient');
    const anim = await goldHeader.evaluate((el: Element) =>
      window.getComputedStyle(el).animationName
    );
    expect(anim).toContain('goldShimmer');
  });

  test('Featured links visible in nav', async ({ page }) => {
    await openNav(page);
    const featured = [
      { href: '/weather/', text: 'Toronto Weather' },
      { href: '/affiliates/', text: 'Gear' },
      { href: '/updates/', text: 'Latest Updates' },
      { href: '/news/', text: 'News Aggregator' },
      { href: '/deals/', text: 'Deals' },
    ];
    for (const f of featured) {
      const link = navLocator(page, `a[href="${f.href}"]`);
      await expect(link).toBeVisible();
      await expect(link).toContainText(f.text);
    }
  });

  test('Apps & Tools expandable section exists', async ({ page }) => {
    await openNav(page);
    await expect(navLocator(page, 'summary:has-text("Apps & Tools")')).toBeVisible();
  });

  test('Investment Hub expandable submenu', async ({ page }) => {
    await openNav(page);
    // Open Apps & Tools
    await navLocator(page, 'summary:has-text("Apps & Tools")').click();
    await page.waitForTimeout(300);
    // Investment Hub should be visible
    await expect(navLocator(page, 'summary:has-text("Investment Hub")')).toBeVisible();
  });

  test('Investment Hub — Stocks category with all links', async ({ page }) => {
    await openNav(page);
    // Expand Apps & Tools → Investment Hub → Stocks
    await navLocator(page, 'summary:has-text("Apps & Tools")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("Investment Hub")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("Stocks")').click();
    await page.waitForTimeout(200);

    const stockLinks = [
      '/findstocks/',
      '/findstocks/portfolio2/dashboard.html',
      '/findstocks/portfolio2/picks.html',
      '/findstocks/portfolio2/horizon-picks.html',
      '/findstocks/portfolio2/dividends.html',
      '/findstocks/portfolio2/stats/index.html',
      '/findstocks/portfolio2/smart-learning.html',
      '/findstocks/portfolio2/stock-intel.html',
      '/findstocks/portfolio2/daytrader-sim.html',
      '/findstocks/portfolio2/penny-stocks.html',
      '/findstocks_global/',
    ];
    for (const href of stockLinks) {
      await expect(navLocator(page, `a[href="${href}"]`)).toBeVisible();
    }
  });

  test('Investment Hub — Mutual Funds category', async ({ page }) => {
    await openNav(page);
    await navLocator(page, 'summary:has-text("Apps & Tools")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("Investment Hub")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("Mutual Funds")').click();
    await page.waitForTimeout(200);

    await expect(navLocator(page, 'a[href="/findmutualfunds/portfolio1/"]')).toBeVisible();
    await expect(navLocator(page, 'a[href="/findmutualfunds2/portfolio2/"]')).toBeVisible();
  });

  test('Investment Hub — Crypto category', async ({ page }) => {
    await openNav(page);
    await navLocator(page, 'summary:has-text("Apps & Tools")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("Investment Hub")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("Crypto")').click();
    await page.waitForTimeout(200);

    await expect(navLocator(page, 'a[href="/findcryptopairs/"]')).toBeVisible();
    await expect(navLocator(page, 'a[href="/findcryptopairs/meme.html"]')).toBeVisible();
  });

  test('Investment Hub — Forex category', async ({ page }) => {
    await openNav(page);
    await navLocator(page, 'summary:has-text("Apps & Tools")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("Investment Hub")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("Forex")').click();
    await page.waitForTimeout(200);

    await expect(navLocator(page, 'a[href="/findforex2/"]')).toBeVisible();
    await expect(navLocator(page, 'a[href="/findforex2/portfolio/"]')).toBeVisible();
  });

  test('Investment Hub — Goldmines category', async ({ page }) => {
    await openNav(page);
    await navLocator(page, 'summary:has-text("Apps & Tools")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("Investment Hub")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("Goldmines")').click();
    await page.waitForTimeout(200);

    await expect(navLocator(page, 'a[href="/live-monitor/goldmine-dashboard.html"]')).toBeVisible();
    await expect(navLocator(page, 'a[href="/live-monitor/multi-dimensional.html"]')).toBeVisible();
  });

  test('Apps & Tools — standalone links (Sports, Mental Health, etc.)', async ({ page }) => {
    await openNav(page);
    await navLocator(page, 'summary:has-text("Apps & Tools")').click();
    await page.waitForTimeout(200);

    const standaloneLinks = [
      '/live-monitor/sports-betting.html',
      '/MENTALHEALTHRESOURCES/',
      '/fc/#/guest',
      '/WINDOWSFIXER/',
    ];
    for (const href of standaloneLinks) {
      await expect(navLocator(page, `a[href="${href}"]`)).toBeVisible();
    }
  });

  test('Movies & TV section with all 3 links', async ({ page }) => {
    await openNav(page);
    await navLocator(page, 'summary:has-text("Movies & TV")').click();
    await page.waitForTimeout(200);

    await expect(navLocator(page, 'a[href="/MOVIESHOWS/"]')).toBeVisible();
    await expect(navLocator(page, 'a[href="/movieshows2/"]')).toBeVisible();
    await expect(navLocator(page, 'a[href="/MOVIESHOWS3/"]')).toBeVisible();
  });

  test('Immersive section — Games & VR submenu', async ({ page }) => {
    await openNav(page);
    await navLocator(page, 'summary:has-text("Immersive")').click();
    await page.waitForTimeout(200);
    await expect(navLocator(page, 'summary:has-text("Games & VR")')).toBeVisible();
  });

  test('Games & VR — VR Experience category', async ({ page }) => {
    await openNav(page);
    await navLocator(page, 'summary:has-text("Immersive")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("Games & VR")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("VR Experience")').click();
    await page.waitForTimeout(200);

    await expect(navLocator(page, 'a[href="/vr/"]')).toBeVisible();
    await expect(navLocator(page, 'a[href="/vr/events/"]')).toBeVisible();
  });

  test('Games & VR — FPS & Shooters category', async ({ page }) => {
    await openNav(page);
    await navLocator(page, 'summary:has-text("Immersive")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("Games & VR")').click();
    await page.waitForTimeout(200);
    await navLocator(page, 'summary:has-text("FPS")').click();
    await page.waitForTimeout(200);

    await expect(navLocator(page, 'a[href="/vr/game-arena/fps-arena.html"]')).toBeVisible();
  });

  test('Drafts section with links', async ({ page }) => {
    await openNav(page);
    // Scroll down to find Drafts
    const nav = navLocator(page, 'nav.flex-1');
    await nav.evaluate((el: Element) => el.scrollTo(0, el.scrollHeight));
    await page.waitForTimeout(300);
    await navLocator(page, 'summary:has-text("Drafts")').click();
    await page.waitForTimeout(200);

    await expect(navLocator(page, 'a[href="/gotjob/"]')).toBeVisible();
  });

  test('Event System Settings button present', async ({ page }) => {
    await openNav(page);
    await expect(navLocator(page, 'button:has-text("Event System Settings")')).toBeVisible();
  });

  test('Contact Support with email present', async ({ page }) => {
    await openNav(page);
    const nav = navLocator(page, 'nav.flex-1');
    await nav.evaluate((el: Element) => el.scrollTo(0, el.scrollHeight));
    await page.waitForTimeout(300);
    await expect(navLocator(page, 'text=findtorontoevents.ca').first()).toBeVisible();
  });

  test('Data Management is REMOVED', async ({ page }) => {
    await openNav(page);
    const nav = navLocator(page, 'nav.flex-1');
    await nav.evaluate((el: Element) => el.scrollTo(0, el.scrollHeight));
    await page.waitForTimeout(300);
    await expect(navLocator(page, 'text=Data Management')).toHaveCount(0);
  });

  test('Import Collection is REMOVED', async ({ page }) => {
    await openNav(page);
    await expect(navLocator(page, 'button:has-text("Import Collection")')).toHaveCount(0);
  });

  test('goldShimmer CSS keyframes exist', async ({ page }) => {
    const hasKeyframes = await page.evaluate(() => {
      const styles = document.querySelectorAll('style');
      for (const s of styles) {
        if (s.textContent?.includes('goldShimmer')) return true;
      }
      return false;
    });
    expect(hasKeyframes).toBe(true);
  });
});
