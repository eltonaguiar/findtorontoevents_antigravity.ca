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

  await page.goto('/weather/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(9000);

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

test('reset look button clears cached bad theme (glass) and restores defaults', async ({ page }) => {
  await page.goto('/weather/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  // simulate the user who picked Glass, got unreadable text, and couldn't recover
  await page.evaluate(() => localStorage.setItem('weather-theme', 'glass'));
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  expect(await page.evaluate(() => document.body.classList.contains('theme-glass'))).toBe(true);

  // the emergency reset button must be visible even under a broken theme
  await expect(page.locator('#look-reset')).toBeVisible();
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
    page.click('#look-reset'),
  ]);
  await page.waitForTimeout(1000);

  // note: after reload the page re-caches the default theme ('auto'), so the key
  // is 'auto' rather than null — null only right after removeItem, pre-reload
  const theme = await page.evaluate(() => localStorage.getItem('weather-theme'));
  expect(theme).toBe('auto');
  expect(await page.evaluate(() => document.body.classList.contains('theme-glass'))).toBe(false);
  // after reset, page defaults to Auto (weather-driven) theme
  const activeBtn = await page.locator('.theme-btn.active[data-theme]').first().getAttribute('data-theme');
  expect(activeBtn).toBe('auto');
});

test('self-dev books widget renders rotated Goodreads picks', async ({ page }) => {
  await page.goto('/weather/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForSelector('#side-books li a', { timeout: 25000 });
  const count = await page.locator('#side-books li a').count();
  console.log('Books rendered:', count);
  expect(count).toBe(5);
});

test('failed refresh KEEPS last good weather data (no wipe) and shows a stale notice', async ({ page }) => {
  // Regression for the 2026-10-19 report "all items missing": the 10-min
  // auto-refresh used to hide #content on any failed fetch, wiping a good
  // render. A failed refresh must keep the old data + show a Retry notice.
  await page.goto('/weather/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(9000);

  const tempBefore = await page.locator('#cur-temp').textContent();
  const fcBefore = await page.locator('.fc-day').count();
  expect(tempBefore).not.toMatch(/--/);
  expect(fcBefore).toBeGreaterThanOrEqual(5);

  // now break the weather API and trigger a refresh (same path as the
  // auto-refresh / Retry button). Regex matcher: the built URL contains
  // &timezone=America/Toronto, and a glob `*` does not cross `/`.
  await page.route(/api\.open-meteo\.com\/v1\/forecast/, (route) => route.abort());
  await page.evaluate(() => (window as any).retryWeather());
  await page.waitForTimeout(6000);

  // last good render must still be on screen
  expect(await page.locator('#content').isVisible()).toBe(true);
  const tempAfter = await page.locator('#cur-temp').textContent();
  expect(tempAfter).not.toMatch(/--/);
  expect(await page.locator('.fc-day').count()).toBeGreaterThanOrEqual(5);
  expect(await page.locator('.h-item').count()).toBeGreaterThanOrEqual(10);

  // and the stale notice must be visible with a Retry control
  expect(await page.locator('#wx-stale').isVisible()).toBe(true);
  expect(await page.locator('#wx-stale-retry').isVisible()).toBe(true);
});

test('initial fetch failure shows a VISIBLE error + Retry button, and Retry recovers', async ({ page }) => {
  // Regression: previously the error was written into the hidden #loading
  // box after #content was already hidden — the user saw a blank page with
  // no error and no way to retry (3 failed attempts were also fatal).
  await page.route(/api\.open-meteo\.com\/v1\/forecast/, (route) => route.abort());
  await page.goto('/weather/', { waitUntil: 'domcontentloaded', timeout: 30000 });

  // retries: 3 attempts with 500ms/1500ms backoff, all aborting fast
  await expect(page.locator('#wx-retry')).toBeVisible({ timeout: 15000 });
  // content must NOT be shown as an empty skeleton
  expect(await page.locator('#content').isVisible()).toBe(false);

  // API works again → Retry must recover
  await page.unroute(/api\.open-meteo\.com\/v1\/forecast/);
  await page.click('#wx-retry');
  await page.waitForTimeout(9000);

  expect(await page.locator('#content').isVisible()).toBe(true);
  expect(await page.locator('.fc-day').count()).toBeGreaterThanOrEqual(5);
  const verdict = await page.locator('#v-title').textContent();
  expect(verdict).not.toBe('Loading…');
});

test('partial API payload shows an error, never an empty skeleton', async ({ page }) => {
  // Regression: a 200 response missing daily/hourly made render() throw
  // AFTER the content flip → every card showed "--" / "Loading…" with the
  // error invisible. This is the exact "all items missing" symptom.
  await page.route(/api\.open-meteo\.com\/v1\/forecast/, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        latitude: 43.65,
        longitude: -79.38,
        timezone: 'America/Toronto',
        current: { time: '2026-10-19T12:00', temperature_2m: 11 },
        // daily + hourly deliberately omitted
      }),
    }),
  );
  await page.goto('/weather/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(4000);

  // no empty skeleton: content hidden, verdict never visible
  expect(await page.locator('#content').isVisible()).toBe(false);
  expect(await page.locator('#v-title').isVisible()).toBe(false);
  expect(await page.locator('.fc-day').count()).toBe(0);

  // visible error + Retry control
  expect(await page.locator('#wx-retry')).toBeVisible();
  const errText = await page.locator('#loading').textContent();
  expect(errText).toContain('Could not load weather');
});

test('postal code lookup works', async ({ page }) => {
  // domcontentloaded instead of networkidle: the Windy map iframe + players keep
  // network activity alive, which makes networkidle flaky on this page
  await page.goto('/weather/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(4000);

  // enter a Toronto postal code
  await page.fill('#postal-input', 'M5V 3A8');
  await page.click('.loc-form button:has-text("Go")');
  await page.waitForTimeout(5000);

  const area = await page.locator('#area-label').textContent();
  console.log('Area after lookup:', area);
  expect(area).toContain('M5V');
});
