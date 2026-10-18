import { test, expect } from '@playwright/test';

test('weather page loads with jacket verdict and no JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (err) => {
    errors.push(`PageError: ${err.message}`);
  });
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      if (text.includes('#418') || text.includes('favicon')) return;
      errors.push(`ConsoleError: ${text}`);
    }
  });

  await page.goto('/weather/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(5000);

  const title = await page.title();
  expect(title).toContain('Toronto Weather');

  // jacket verdict loaded
  const verdictTitle = await page.locator('#v-title').textContent();
  console.log('Verdict:', verdictTitle);
  expect(verdictTitle).not.toBe('Loading…');
  expect(verdictTitle!.length).toBeGreaterThan(3);

  // reason text
  const reason = await page.locator('#v-reason').textContent();
  expect(reason!.length).toBeGreaterThan(20);

  // last updated present
  const updated = await page.locator('#last-updated').textContent();
  expect(updated).not.toBe('--');

  // area label present
  const area = await page.locator('#area-label').textContent();
  expect(area).toContain('Area:');

  // rain probability card
  const rainProb = await page.locator('#rain-prob').textContent();
  console.log('Rain prob:', rainProb);
  expect(rainProb).toMatch(/%$/);

  // sunset visible
  const sunset = await page.locator('#sunset').textContent();
  console.log('Sunset:', sunset);
  expect(sunset).not.toBe('--');

  // sunrise visible
  const sunrise = await page.locator('#sunrise').textContent();
  expect(sunrise).not.toBe('--');

  // sunny verdict
  const sunny = await page.locator('#sunny-verdict').textContent();
  expect(sunny).not.toBe('—');

  // forecast days
  const fcDays = await page.locator('.fc-day').count();
  console.log('Forecast days:', fcDays);
  expect(fcDays).toBeGreaterThanOrEqual(5);

  // hourly items
  const hourly = await page.locator('.h-item').count();
  console.log('Hourly items:', hourly);
  expect(hourly).toBeGreaterThanOrEqual(10);

  // postal input exists
  const postalInput = page.locator('#postal-input');
  expect(await postalInput.isVisible()).toBe(true);

  // back link
  expect(await page.locator('.back').isVisible()).toBe(true);

  console.log('JS errors:', errors.length);
  errors.forEach(e => console.log('  -', e));
  expect(errors).toHaveLength(0);
});

test('jacket page redirects to weather', async ({ page }) => {
  await page.goto('/jacket/', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(2000);
  expect(page.url()).toContain('/weather/');
});

test('doineedajacket page redirects to weather', async ({ page }) => {
  await page.goto('/doineedajacket/', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(2000);
  expect(page.url()).toContain('/weather/');
});

test('postal code lookup works', async ({ page }) => {
  await page.goto('/weather/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(4000);

  // enter a Toronto postal code
  await page.fill('#postal-input', 'M5V 3A8');
  await page.click('.loc-form button:has-text("Go")');
  await page.waitForTimeout(5000);

  const area = await page.locator('#area-label').textContent();
  console.log('Area after lookup:', area);
  expect(area).toContain('M5V');
});
