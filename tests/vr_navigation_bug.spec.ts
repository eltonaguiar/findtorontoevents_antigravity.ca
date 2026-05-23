import { test, expect, Page } from '@playwright/test';

/**
 * VR Navigation Bug Test
 * Verifies that clicking Events goes to Events, not Cinema/Movies
 */

async function waitForScene(page: Page, timeout = 5000) {
  await page.waitForSelector('a-scene', { timeout });
  await page.waitForTimeout(2000); // Let scene fully load
}

test.describe('VR Navigation Bug Fix', () => {
  test('Events portal navigates to /vr/events/', async ({ page }) => {
    // Track navigation
    let navigatedUrl = '';
    page.on('framenavigated', frame => {
      if (frame === page.mainFrame()) {
        navigatedUrl = frame.url();
        console.log('Navigation:', navigatedUrl);
      }
    });

    await page.goto('/vr/', { waitUntil: 'domcontentloaded' });
    await waitForScene(page);

    // Find the Events zone and click it
    // The Events zone is at position -6 0 -8 with zone-link to /vr/events/
    const eventsZone = await page.locator('[zone-link="url: /vr/events/"]').first();
    
    // Verify the zone exists and has correct URL
    const zoneUrl = await eventsZone.evaluate(el => el.getAttribute('zone-link'));
    console.log('Events zone-link attribute:', zoneUrl);
    expect(zoneUrl).toContain('/vr/events/');

    // Click the events zone
    await eventsZone.click();
    
    // Wait for navigation
    await page.waitForTimeout(1000);
    
    // Verify we navigated to events, NOT movies
    console.log('Final URL:', page.url());
    expect(page.url()).toContain('/vr/events');
    expect(page.url()).not.toContain('/vr/movies');
  });

  test('Movies portal navigates to /vr/movies.html', async ({ page }) => {
    await page.goto('/vr/', { waitUntil: 'domcontentloaded' });
    await waitForScene(page);

    const moviesZone = await page.locator('[zone-link="url: /vr/movies.html"]').first();
    
    const zoneUrl = await moviesZone.evaluate(el => el.getAttribute('zone-link'));
    console.log('Movies zone-link attribute:', zoneUrl);
    expect(zoneUrl).toContain('/vr/movies.html');
  });

  test('All zone portals have correct URLs', async ({ page }) => {
    await page.goto('/vr/', { waitUntil: 'domcontentloaded' });
    await waitForScene(page);

    const expectedZones = [
      { name: 'Events', url: '/vr/events/' },
      { name: 'Movies', url: '/vr/movies.html' },
      { name: 'Creators', url: '/vr/creators.html' },
      { name: 'Stocks', url: '/vr/stocks-zone.html' },
      { name: 'Wellness', url: '/vr/wellness/' },
      { name: 'Weather', url: '/vr/weather-zone.html' },
      { name: 'Tutorial', url: '/vr/tutorial/' },
    ];

    for (const zone of expectedZones) {
      const zoneElements = await page.locator(`[zone-link="url: ${zone.url}"]`).count();
      console.log(`${zone.name}: found ${zoneElements} elements with URL ${zone.url}`);
      expect(zoneElements).toBeGreaterThan(0);
    }
  });
});

test.describe('VR Simple/Advanced Mode', () => {
  test('Simple mode toggle exists', async ({ page }) => {
    await page.goto('/vr/', { waitUntil: 'domcontentloaded' });
    await waitForScene(page);

    // Check for mode toggle button
    const modeToggle = await page.locator('#vr-mode-toggle, [data-mode-toggle]').first();
    expect(await modeToggle.isVisible()).toBeTruthy();
  });

  test('Switching to Simple mode hides advanced buttons', async ({ page }) => {
    await page.goto('/vr/', { waitUntil: 'domcontentloaded' });
    await waitForScene(page);

    // Get initial button count
    const initialButtons = await page.locator('button').count();
    console.log('Initial button count:', initialButtons);

    // Click simple mode
    await page.locator('#vr-mode-simple').click();
    await page.waitForTimeout(500);

    // Get simple mode button count
    const simpleButtons = await page.locator('button').count();
    console.log('Simple mode button count:', simpleButtons);

    // Simple mode should have fewer buttons
    expect(simpleButtons).toBeLessThan(initialButtons);
  });
});
