import { test, expect } from '@playwright/test';

test.describe('Audit Dashboard Hydration Check', () => {
  test('should not have content disappear after hydration', async ({ page }) => {
    await page.goto('/audit/');

    // Capture DOM before hydration (or as close as possible to initial load)
    // We'll use a short timeout to ensure the initial HTML is parsed
    await page.waitForLoadState('domcontentloaded');
    const initialContent = await page.content();

    // Wait for hydration to complete (adjust timeout as needed)
    // This assumes React hydration happens within 2 seconds.
    await page.waitForTimeout(2000);

    // Capture DOM after hydration
    const hydratedContent = await page.content();

    // Compare the two contents.
    // A more robust check would involve specific elements, but for a general "disappearing content" check,
    // comparing the full content is a good start.
    // We expect the content to be largely the same, or for new content to be added,
    // but not for existing content to disappear.
    expect(hydratedContent).toContain(initialContent);

    // Further checks can be added here to specifically look for elements that are known to be
    // part of the static HTML and should persist after hydration.
    // For example, checking for specific text content in banners or headers.
    await expect(page.locator('#truth-layer-reality-banner')).toBeVisible();
    await expect(page.locator('#major-goal-banner')).toBeVisible();
    await expect(page.locator('#perf-section-header')).toBeVisible();
  });
});
