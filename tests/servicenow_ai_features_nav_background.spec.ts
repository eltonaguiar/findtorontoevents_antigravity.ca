/**
 * Playwright verification for the ServiceNow AI Features page.
 * Loads the local file:// URL and checks for persistent internal ServiceNow
 * navigation plus layered animated background treatment.
 *
 * Run: npx playwright test tests/servicenow_ai_features_nav_background.spec.ts --project="Desktop Chrome"
 */

const { test, expect } = require('@playwright/test');
const { join, dirname } = require('path');

const HTML_PATH = join(
  dirname(__filename),
  '..',
  'TORONTOEVENTS_ANTIGRAVITY',
  'servicenow',
  'AIFeaturesOct2026',
  'index.html',
);

test.describe('ServiceNow AI Features — nav and animated background', () => {
  test('renders persistent training links and layered moving background without overflow', async ({ page }) => {
    const fileUrl = `file://${HTML_PATH}`;
    await page.goto(fileUrl, { waitUntil: 'domcontentloaded' });

    await expect(page.locator('h1:has-text("ServiceNow AI Features Starter Guide")')).toBeVisible();

    const heroLinks = page.locator('header.hero .actions a');
    await expect(heroLinks).toHaveCount(4);
    await expect(heroLinks.nth(0)).toHaveAttribute('href', '/');
    await expect(heroLinks.nth(1)).toHaveAttribute('href', '/servicenow/javascript/index.html');
    await expect(heroLinks.nth(2)).toHaveAttribute('href', '/servicenow/CIS-CSM/index.html');
    await expect(heroLinks.nth(3)).toHaveAttribute('href', '/servicenow/CIS-VR/index.html');

    const practicalLinks = page.locator('#nask-practical .callout a');
    await expect(practicalLinks).toHaveCount(3);
    await expect(practicalLinks.nth(0)).toHaveAttribute('href', '/servicenow/javascript/index.html');
    await expect(practicalLinks.nth(1)).toHaveAttribute('href', '/servicenow/CIS-CSM/index.html');
    await expect(practicalLinks.nth(2)).toHaveAttribute('href', '/servicenow/CIS-VR/index.html');

    const footerNav = page.locator('footer .footer-nav');
    await expect(footerNav).toBeVisible();
    await expect(footerNav.locator('a')).toHaveCount(4);

    const footerHrefs = await footerNav.locator('a').evaluateAll((links) =>
      links.map((link) => link.getAttribute('href')),
    );
    expect(footerHrefs).toEqual([
      '/servicenow/javascript/index.html',
      '/servicenow/AIFeaturesOct2026/index.html',
      '/servicenow/CIS-CSM/index.html',
      '/servicenow/CIS-VR/index.html',
    ]);

    await expect(page.locator('.bg-scene')).toBeVisible();
    await expect(page.locator('.bg-aurora')).toBeVisible();
    await expect(page.locator('.bg-orbit')).toBeVisible();

    const backgroundAnimations = await page.evaluate(() => {
      const sceneStyle = getComputedStyle(document.querySelector('.bg-scene'));
      const aurora = getComputedStyle(document.querySelector('.bg-aurora') as Element).animationName;
      const orbit = getComputedStyle(document.querySelector('.bg-orbit') as Element).animationName;
      return {
        sceneAnimation: sceneStyle.animationName,
        sceneImage: sceneStyle.backgroundImage,
        aurora,
        orbit,
      };
    });
    expect(backgroundAnimations.sceneImage).not.toBe('none');
    expect(backgroundAnimations.sceneAnimation).not.toBe('none');
    expect(backgroundAnimations.aurora).not.toBe('none');
    expect(backgroundAnimations.orbit).not.toBe('none');

    const bodyOverflow = await page.evaluate(() => {
      const body = document.body;
      return body.scrollWidth > body.clientWidth + 2;
    });
    expect(bodyOverflow).toBe(false);
  });
});
