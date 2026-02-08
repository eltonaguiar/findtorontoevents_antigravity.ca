import { test, expect } from '@playwright/test';

const BASE = 'https://findtorontoevents.ca';

/** Wait for A-Frame scene to load */
async function waitForScene(page: any) {
  await page.waitForSelector('a-scene', { timeout: 15000 });
  await page.waitForTimeout(2000);
}

test.describe('VR Global Menu — All Features', () => {

  test('menu has clock, date, current zone, actions, music player, 7 zones', async ({ page }) => {
    await page.goto(`${BASE}/vr/index.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    // Floating button should exist
    await expect(page.locator('#vr-nav-floating-btn')).toBeAttached();

    // Open menu via keyboard
    await page.keyboard.press('m');
    await page.waitForTimeout(600);

    const menu = page.locator('#vr-nav-menu-2d');
    await expect(menu).toHaveClass(/active/);

    // Clock
    const clock = page.locator('#vr-clock');
    await expect(clock).toBeAttached();
    const clockText = await clock.textContent();
    console.log('Clock:', clockText);
    expect(clockText).toMatch(/\d+:\d+ [AP]M/);

    // Date
    const dateEl = page.locator('#vr-date');
    await expect(dateEl).toBeAttached();
    console.log('Date:', await dateEl.textContent());

    // Current zone highlighted with HERE badge
    const hereBadge = page.locator('.vr-nav-here');
    await expect(hereBadge).toBeAttached();
    expect(await hereBadge.textContent()).toBe('HERE');

    const currentZone = page.locator('.vr-nav-zone.current');
    await expect(currentZone).toBeAttached();
    const currentText = await currentZone.evaluate((el: HTMLElement) => el.querySelector('.vr-nav-name')?.textContent || '');
    console.log('Current zone:', currentText);
    expect(currentText).toContain('VR Hub');

    // All 8 zones (7 main + tutorial)
    const zones = page.locator('.vr-nav-zone');
    expect(await zones.count()).toBe(8);

    // Section actions (hub = Reset Position, Toggle Labels)
    const sectionBtns = page.locator('.vr-nav-section-btn');
    expect(await sectionBtns.count()).toBeGreaterThan(0);
    console.log('Section actions:', await sectionBtns.allTextContents());

    // Music player
    const musicToggle = page.locator('#vr-music-toggle');
    await expect(musicToggle).toBeAttached();

    // 6 stations
    const stations = page.locator('.vr-music-station');
    expect(await stations.count()).toBe(6);

    // Volume slider
    await expect(page.locator('#vr-music-vol')).toBeAttached();

    // Now-playing indicator
    await expect(page.locator('#vr-music-now')).toBeAttached();

    // SomaFM credit
    await expect(page.locator('.vr-music-credit')).toContainText('SomaFM');

    console.log('All global menu features verified!');
  });

  test('menu shows correct context actions per zone (Creators)', async ({ page }) => {
    await page.goto(`${BASE}/vr/creators.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    // Open menu
    await page.keyboard.press('m');
    await page.waitForTimeout(600);

    const sectionBtns = page.locator('.vr-nav-section-btn');
    const labels = await sectionBtns.allTextContents();
    console.log('Creators section actions:', labels);
    expect(labels).toContain('Refresh Live');
    expect(labels).toContain('Filter Platform');
    expect(labels).toContain('Next Page');

    // Current zone should be Live Creators
    const currentZone = page.locator('.vr-nav-zone.current .vr-nav-name');
    await expect(currentZone).toContainText('Live Creators');
  });

  test('menu shows correct context actions per zone (Movies)', async ({ page }) => {
    await page.goto(`${BASE}/vr/movies.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    await page.keyboard.press('m');
    await page.waitForTimeout(600);

    const sectionBtns = page.locator('.vr-nav-section-btn');
    const labels = await sectionBtns.allTextContents();
    console.log('Movies section actions:', labels);
    expect(labels).toContain('Play Trailer');
    expect(labels).toContain('Next Movie');
    expect(labels).toContain('Categories');

    const currentZone = page.locator('.vr-nav-zone.current .vr-nav-name');
    await expect(currentZone).toContainText('Movie Theater');
  });

  test('music play button is clickable in menu', async ({ page }) => {
    await page.goto(`${BASE}/vr/index.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    // Open menu
    await page.keyboard.press('m');
    await page.waitForTimeout(600);

    // Music toggle button exists and is clickable
    const toggleBtn = page.locator('#vr-music-toggle');
    await expect(toggleBtn).toBeAttached();
    await expect(toggleBtn).toBeVisible();

    // Click play (may be blocked by autoplay policy, but button should be functional)
    await toggleBtn.click();
    await page.waitForTimeout(1000);

    // Now-playing should have content
    const nowText = await page.locator('#vr-music-now').textContent();
    console.log('Now playing:', nowText);
    expect(nowText!.length).toBeGreaterThan(0);
  });

  test('Escape closes menu', async ({ page }) => {
    await page.goto(`${BASE}/vr/index.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    await page.keyboard.press('m');
    await page.waitForTimeout(400);
    await expect(page.locator('#vr-nav-menu-2d')).toHaveClass(/active/);

    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    await expect(page.locator('#vr-nav-menu-2d')).not.toHaveClass(/active/);
  });

  test('M key toggles menu open and closed', async ({ page }) => {
    await page.goto(`${BASE}/vr/index.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    // M opens
    await page.keyboard.press('m');
    await page.waitForTimeout(400);
    await expect(page.locator('#vr-nav-menu-2d')).toHaveClass(/active/);

    // M closes
    await page.keyboard.press('m');
    await page.waitForTimeout(400);
    await expect(page.locator('#vr-nav-menu-2d')).not.toHaveClass(/active/);
  });

  test('station buttons exist for all 6 stations', async ({ page }) => {
    await page.goto(`${BASE}/vr/index.html`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForScene(page);

    await page.keyboard.press('m');
    await page.waitForTimeout(600);

    const stationNames = await page.evaluate(() => {
      const btns = document.querySelectorAll('.vr-music-station');
      return Array.from(btns).map(b => ({
        name: b.querySelector('.st-name')?.textContent || '',
        genre: b.querySelector('.st-genre')?.textContent || ''
      }));
    });

    console.log('Stations:', stationNames);
    expect(stationNames.length).toBe(6);
    expect(stationNames.some(s => s.name === 'Groove Salad')).toBe(true);
    expect(stationNames.some(s => s.name === 'Space Station')).toBe(true);
    expect(stationNames.some(s => s.name === 'Drone Zone')).toBe(true);
    expect(stationNames.some(s => s.name === 'Lush')).toBe(true);
    expect(stationNames.some(s => s.name === 'Deep Space One')).toBe(true);
    expect(stationNames.some(s => s.name === 'Vaporwaves')).toBe(true);
  });
});
