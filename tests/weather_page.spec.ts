import { test, expect } from '@playwright/test';

test('weather page loads with no JS errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (err) => {
    errors.push(`PageError: ${err.message}`);
  });
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      // Ignore known non-critical errors
      if (text.includes('#418') || text.includes('favicon')) return;
      errors.push(`ConsoleError: ${text}`);
    }
  });

  await page.goto('/weather/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(4000);

  // Check title
  const title = await page.title();
  expect(title).toContain('Toronto Weather');

  // Check weather data loaded
  const heroTemp = await page.locator('#hero-temp').textContent();
  console.log('Hero temp:', heroTemp);
  expect(heroTemp).not.toBe('--°');

  // Check hero condition
  const heroCondition = await page.locator('#hero-condition').textContent();
  console.log('Condition:', heroCondition);
  expect(heroCondition).not.toBe('Loading...');

  // Check feels like loaded
  const feelsValue = await page.locator('#feels-value').textContent();
  console.log('Feels like:', feelsValue);
  expect(feelsValue).not.toBe('--°');

  // Check forecast strip has items
  const forecastDays = await page.locator('.forecast-day').count();
  console.log('Forecast days:', forecastDays);
  expect(forecastDays).toBeGreaterThanOrEqual(5);

  // Check hourly scroll has items
  const hourlyItems = await page.locator('.hour-item').count();
  console.log('Hourly items:', hourlyItems);
  expect(hourlyItems).toBeGreaterThanOrEqual(10);

  // Check AI assistant script is included
  const aiScript = await page.evaluate(() => {
    const scripts = Array.from(document.querySelectorAll('script[src]'));
    return scripts.some(s => (s as HTMLScriptElement).src.includes('ai-assistant'));
  });
  console.log('AI assistant script included:', aiScript);
  expect(aiScript).toBe(true);

  // Check back link exists
  const backLink = await page.locator('.back-link').isVisible();
  expect(backLink).toBe(true);

  // Check VR link exists
  const vrLink = await page.locator('.vr-link').isVisible();
  expect(vrLink).toBe(true);

  // Report errors
  console.log('JS errors found:', errors.length);
  errors.forEach(e => console.log('  -', e));
  expect(errors).toHaveLength(0);
});

test('weather page clothing advice renders', async ({ page }) => {
  await page.goto('/weather/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(4000);

  const adviceText = await page.locator('#advice-text').textContent();
  console.log('Advice:', adviceText);
  expect(adviceText).not.toBe('Loading advice...');
  expect(adviceText!.length).toBeGreaterThan(10);
});
