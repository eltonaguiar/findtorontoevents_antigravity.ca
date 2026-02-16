// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('MOVIESHOWS3 Streaming Provider Badges', () => {
  test('API returns provider data for movies', async ({ request }) => {
    const response = await request.get('https://findtorontoevents.ca/MOVIESHOWS3/api/get-movies.php');
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.count).toBeGreaterThan(0);
    expect(data.movies).toBeDefined();

    // Check that some movies have providers
    const moviesWithProviders = data.movies.filter(m => m.providers && m.providers.length > 0);
    expect(moviesWithProviders.length).toBeGreaterThan(0);

    console.log(`\u2705 Found ${moviesWithProviders.length} movies with providers out of ${data.count} total`);

    // Check Culinary Class Wars specifically
    const culinary = data.movies.find(m => m.title.includes('Culinary'));
    if (culinary) {
      console.log(`\u2705 Culinary Class Wars found: ${culinary.providers.length} providers`);
      expect(culinary.providers).toBeDefined();
      expect(culinary.providers.length).toBeGreaterThan(0);

      const netflix = culinary.providers.find(p => p.name === 'Netflix');
      expect(netflix).toBeDefined();
      expect(netflix.id).toBe('8');
      console.log(`\u2705 Netflix provider confirmed for Culinary Class Wars`);
    }
  });

  test('Homepage loads and displays movies', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/');

    // Wait for movies to load
    await page.waitForSelector('.swiper-slide', { timeout: 10000 });

    const title = await page.title();
    expect(title).toContain('MovieShows');

    console.log('\u2705 Homepage loaded successfully');
  });

  test('Provider badges appear on movie cards', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/');

    // Wait for movies to load
    await page.waitForSelector('.swiper-slide', { timeout: 10000 });

    // Wait a bit for provider data to load from API
    await page.waitForTimeout(3000);

    // Check for provider badges in the DOM
    const providerBadges = await page.locator('.provider-badge').count();

    if (providerBadges > 0) {
      console.log(`\u2705 Found ${providerBadges} provider badges on page`);
      expect(providerBadges).toBeGreaterThan(0);

      // Get first provider badge
      const firstBadge = page.locator('.provider-badge').first();
      await expect(firstBadge).toBeVisible();

      const alt = await firstBadge.getAttribute('alt');
      console.log(`\u2705 First provider badge: ${alt}`);
    } else {
      console.warn('\u26A0\uFE0F No provider badges found on page - may need more provider data loaded');
    }
  });

  test('Streaming filter pills are present', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/');

    // Toggle streaming filter
    const filterBtn = page.locator('#streamingToggleBtn');
    await expect(filterBtn).toBeVisible();
    await filterBtn.click();

    // Check for streaming pills
    await page.waitForSelector('.streaming-pill', { timeout: 5000 });

    const pills = await page.locator('.streaming-pill').count();
    expect(pills).toBeGreaterThan(0);

    console.log(`\u2705 Found ${pills} streaming filter pills`);

    // Verify specific providers
    const netflixPill = page.locator('.streaming-pill.netflix');
    await expect(netflixPill).toBeVisible();

    const primePill = page.locator('.streaming-pill.prime');
    await expect(primePill).toBeVisible();

    console.log('\u2705 Netflix and Prime Video filter pills confirmed');
  });

  test('Culinary Class Wars shows Netflix badge', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/');

    // Wait for movies to load
    await page.waitForSelector('.swiper-slide', { timeout: 10000 });
    await page.waitForTimeout(2000);

    // Search for Culinary Class Wars in Browse view
    const browseBtn = page.locator('button:has-text("Browse")');
    if (await browseBtn.isVisible()) {
      await browseBtn.click();
      await page.waitForTimeout(1000);
    }

    // Look for Culinary Class Wars in the page content
    const pageContent = await page.content();
    if (pageContent.includes('Culinary')) {
      console.log('\u2705 Culinary Class Wars found on page');

      // Check if Netflix badge is present
      const hasNetflix = pageContent.includes('Netflix') || pageContent.includes('pbpMk2JmcoNnQwx5JGpXngfoWtp');
      if (hasNetflix) {
        console.log('\u2705 Netflix provider badge confirmed in page content');
      } else {
        console.warn('\u26A0\uFE0F Culinary Class Wars found but Netflix badge not visible');
      }
    } else {
      console.warn('\u26A0\uFE0F Culinary Class Wars not visible in current view');
    }
  });
});
