import { test, expect } from '@playwright/test';

test.describe('Index page promo sections and tooltips', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/index.html');
    // Wait for page to load and React hydration to settle
    await page.waitForLoadState('networkidle');
    // Wait extra time for forceBanners to win against React
    await page.waitForTimeout(4000);
  });

  test('should have horizontal promo container with all 4 sections', async ({ page }) => {
    const container = page.locator('#injected-promos');
    await expect(container).toBeVisible({ timeout: 10000 });
    
    // Verify all 4 promo sections exist within the container
    await expect(container.locator('.windows-fixer-promo')).toBeVisible();
    await expect(container.locator('.movieshows-promo')).toBeVisible();
    await expect(container.locator('.favcreators-promo')).toBeVisible();
    await expect(container.locator('.stocks-promo')).toBeVisible();
  });

  test('should show Movie/TV Show Trailers title', async ({ page }) => {
    const container = page.locator('#injected-promos');
    await expect(container).toBeVisible({ timeout: 10000 });
    
    // Check for the updated title
    const movieTitle = container.locator('text=Movie/TV Show Trailers');
    await expect(movieTitle).toBeVisible();
  });

  test('should show updated subtitle - Swipe through trailers', async ({ page }) => {
    const container = page.locator('#injected-promos');
    await expect(container).toBeVisible({ timeout: 10000 });
    
    const subtitle = container.locator('text=Swipe through trailers');
    await expect(subtitle).toBeVisible();
  });

  test('should have V1, V2, V3 buttons for Movie Trailers', async ({ page }) => {
    const container = page.locator('#injected-promos');
    await expect(container).toBeVisible({ timeout: 10000 });
    
    const movieSection = container.locator('.movieshows-promo');
    
    const v1Button = movieSection.locator('a:has-text("V1")');
    const v2Button = movieSection.locator('a:has-text("V2")');
    const v3Button = movieSection.locator('a:has-text("V3")');
    
    await expect(v1Button).toBeVisible();
    await expect(v2Button).toBeVisible();
    await expect(v3Button).toBeVisible();
    
    // Verify hrefs
    await expect(v1Button).toHaveAttribute('href', '/MOVIESHOWS/');
    await expect(v2Button).toHaveAttribute('href', '/movieshows2/');
    await expect(v3Button).toHaveAttribute('href', '/MOVIESHOWS3');
  });

  test('should show Fav Creators with updated subtitle', async ({ page }) => {
    const container = page.locator('#injected-promos');
    await expect(container).toBeVisible({ timeout: 10000 });
    
    const favSection = container.locator('.favcreators-promo');
    const subtitle = favSection.locator('text=Never miss when your favorites go live');
    await expect(subtitle).toBeVisible();
  });

  test('should show Stock Ideas with updated subtitle', async ({ page }) => {
    const container = page.locator('#injected-promos');
    await expect(container).toBeVisible({ timeout: 10000 });
    
    const stockSection = container.locator('.stocks-promo');
    const subtitle = stockSection.locator('text=AI-validated picks');
    await expect(subtitle).toBeVisible();
  });

  test('should have info tooltip icons for all 3 feature sections', async ({ page }) => {
    const container = page.locator('#injected-promos');
    await expect(container).toBeVisible({ timeout: 10000 });
    
    // Check for group/info elements in each section (the tooltip wrapper)
    const movieInfo = container.locator('.movieshows-promo .group\\/info');
    const favInfo = container.locator('.favcreators-promo .group\\/info');
    const stockInfo = container.locator('.stocks-promo .group\\/info');
    
    await expect(movieInfo).toBeVisible();
    await expect(favInfo).toBeVisible();
    await expect(stockInfo).toBeVisible();
  });

  test('should show tooltip content on hover for Movie Trailers', async ({ page }) => {
    const container = page.locator('#injected-promos');
    await expect(container).toBeVisible({ timeout: 10000 });
    
    const movieSection = container.locator('.movieshows-promo');
    const infoWrapper = movieSection.locator('.group\\/info').first();
    const tooltipContent = infoWrapper.locator('div[class*="absolute"]');
    
    // Verify tooltip exists but is hidden initially
    await expect(tooltipContent).toBeAttached();
    
    // Hover over the info icon
    await infoWrapper.hover();
    await page.waitForTimeout(500);
    
    // Check tooltip content is now visible
    await expect(tooltipContent).toBeVisible();
    
    // Verify content mentions V1, V2, V3
    const text = await tooltipContent.textContent();
    expect(text).toContain('V1');
    expect(text).toContain('V2');
    expect(text).toContain('V3');
  });

  test('should show tooltip content on hover for Fav Creators', async ({ page }) => {
    const container = page.locator('#injected-promos');
    await expect(container).toBeVisible({ timeout: 10000 });
    
    const favSection = container.locator('.favcreators-promo');
    const infoWrapper = favSection.locator('.group\\/info').first();
    const tooltipContent = infoWrapper.locator('div[class*="absolute"]');
    
    await expect(tooltipContent).toBeAttached();
    
    await infoWrapper.hover();
    await page.waitForTimeout(500);
    
    await expect(tooltipContent).toBeVisible();
    
    const text = await tooltipContent.textContent();
    expect(text).toContain('Live status');
  });

  test('should show tooltip content on hover for Stock Ideas', async ({ page }) => {
    const container = page.locator('#injected-promos');
    await expect(container).toBeVisible({ timeout: 10000 });
    
    const stockSection = container.locator('.stocks-promo');
    const infoWrapper = stockSection.locator('.group\\/info').first();
    const tooltipContent = infoWrapper.locator('div[class*="absolute"]');
    
    await expect(tooltipContent).toBeAttached();
    
    await infoWrapper.hover();
    await page.waitForTimeout(500);
    
    await expect(tooltipContent).toBeVisible();
    
    const text = await tooltipContent.textContent();
    expect(text).toContain('Daily picks');
  });
});
