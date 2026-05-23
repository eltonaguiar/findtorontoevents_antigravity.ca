import { test, expect } from '@playwright/test';

const BASE = 'https://findtorontoevents.ca';

test.describe('VR Tutorial Zone', () => {
  test('tutorial page loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', e => errors.push(e.message));

    await page.goto(`${BASE}/vr/tutorial/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForSelector('a-scene', { timeout: 15000 });
    await page.waitForTimeout(3000);

    console.log('JS errors:', errors.length);
    expect(errors.length).toBe(0);
  });

  test('tutorial has step UI and progress dots', async ({ page }) => {
    await page.goto(`${BASE}/vr/tutorial/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForSelector('a-scene', { timeout: 15000 });
    await page.waitForTimeout(2000);

    // Step 1 title
    const title = await page.locator('#step-title').textContent();
    console.log('Step title:', title);
    expect(title).toContain('Look Around');

    // 7 progress dots
    const dots = await page.locator('.step-dot').count();
    expect(dots).toBe(7);

    // Active dot = first one
    const activeDot = page.locator('.step-dot.active');
    expect(await activeDot.count()).toBe(1);
  });

  test('tutorial has look targets (step 1)', async ({ page }) => {
    await page.goto(`${BASE}/vr/tutorial/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForSelector('a-scene', { timeout: 15000 });
    await page.waitForTimeout(2000);

    const lookTargets = await page.evaluate(() => {
      return document.querySelectorAll('.look-target').length;
    });
    expect(lookTargets).toBe(3);
  });

  test('tutorial has camera rig and controller support', async ({ page }) => {
    await page.goto(`${BASE}/vr/tutorial/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForSelector('a-scene', { timeout: 15000 });
    await page.waitForTimeout(3000);

    const rigInfo = await page.evaluate(() => {
      const rig = document.getElementById('rig');
      if (!rig) return null;
      return {
        hasCamera: rig.querySelector('a-camera') !== null,
        hasLeftHand: rig.querySelector('#left-hand') !== null,
        hasRightHand: rig.querySelector('#right-hand') !== null,
      };
    });

    console.log('Rig info:', rigInfo);
    expect(rigInfo).not.toBeNull();
    expect(rigInfo!.hasCamera).toBe(true);
  });

  test('tutorial has input status display', async ({ page }) => {
    await page.goto(`${BASE}/vr/tutorial/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForSelector('a-scene', { timeout: 15000 });
    await page.waitForTimeout(2000);

    const kbStatus = await page.locator('#kb-status').textContent();
    console.log('Keyboard status:', kbStatus);
    expect(kbStatus).toContain('Keyboard');
  });

  test('hub has tutorial portal', async ({ page }) => {
    await page.goto(`${BASE}/vr/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForSelector('a-scene', { timeout: 15000 });
    await page.waitForTimeout(2000);

    // Check for tutorial zone link
    const hasTutorial = await page.evaluate(() => {
      const els = document.querySelectorAll('[zone-link]');
      for (let i = 0; i < els.length; i++) {
        const attr = els[i].getAttribute('zone-link');
        if (attr && String(attr).indexOf('tutorial') !== -1) return true;
        // A-Frame may parse the attribute into an object with url property
        if (attr && typeof attr === 'object' && (attr as any).url && String((attr as any).url).indexOf('tutorial') !== -1) return true;
      }
      return false;
    });

    console.log('Hub has tutorial portal:', hasTutorial);
    expect(hasTutorial).toBe(true);
  });

  test('nav menu includes tutorial', async ({ page }) => {
    await page.goto(`${BASE}/vr/tutorial/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForSelector('a-scene', { timeout: 15000 });
    await page.waitForTimeout(2000);

    // Open menu
    await page.keyboard.press('m');
    await page.waitForTimeout(500);

    // Current zone should be Tutorial with HERE badge
    const currentZone = page.locator('.vr-nav-zone.current .vr-nav-name');
    await expect(currentZone).toContainText('Tutorial');
  });
});
