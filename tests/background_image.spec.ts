import { test, expect } from '@playwright/test';

test('background gradient applied to entire page', async ({ page }) => {
  // Load the local HTML file directly
  const filePath = require('path').join(process.cwd(), 'findtorontoevents.ca', 'servicenow', 'javascript', 'index.html');
  await page.goto(`file://${filePath}`);
  // Wait for body to be loaded
  await page.waitForSelector('body');
  const bgImage = await page.evaluate(() => getComputedStyle(document.body).backgroundImage);
  // Verify that the background includes the radial gradients defined in the hero section
  expect(bgImage).toContain('radial-gradient');
  // Check for presence of the specific accent colors used in the hero gradient
  expect(bgImage).toContain('rgba(98,245,199,0.08)');
  expect(bgImage).toContain('rgba(122,162,255,0.08)');
});
