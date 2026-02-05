import { test, expect } from '@playwright/test';

test.describe('Creator Updates Page', () => {
  test('loads cached updates successfully', async ({ page }) => {
    // Listen for console errors
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Navigate to the creator updates page
    await page.goto('https://findtorontoevents.ca/fc/creator_updates/', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    // Wait for initial load
    await page.waitForTimeout(2000);

    // Check that the page title is correct
    await expect(page).toHaveTitle(/Creator Updates/i);

    // Check that stats section is visible (shows after loading)
    const stats = page.locator('.stats');
    await expect(stats).toBeVisible({ timeout: 10000 });

    // Check that there are update cards (from cache)
    const updateCards = page.locator('.update-card');
    const count = await updateCards.count();
    expect(count).toBeGreaterThan(0);
    console.log(`Found ${count} update cards`);

    // Check multiple platforms are represented
    const tiktokCards = page.locator('.platform-badge.tiktok');
    const youtubeCards = page.locator('.platform-badge.youtube');
    const instagramCards = page.locator('.platform-badge.instagram');
    
    const tiktokCount = await tiktokCards.count();
    const youtubeCount = await youtubeCards.count();
    const instagramCount = await instagramCards.count();
    
    console.log(`TikTok: ${tiktokCount}, YouTube: ${youtubeCount}, Instagram: ${instagramCount}`);
    
    // At least one platform should have content
    expect(tiktokCount + youtubeCount + instagramCount).toBeGreaterThan(0);

    // Check no critical JS errors (ignore network/resource issues)
    const criticalErrors = errors.filter(e => 
      !e.includes('net::') && 
      !e.includes('favicon') &&
      !e.includes('404') &&
      !e.includes('403') &&
      !e.includes('Failed to load resource')
    );
    
    if (criticalErrors.length > 0) {
      console.log('JS Errors:', criticalErrors);
    }
    expect(criticalErrors.length).toBe(0);
  });

  test('filter buttons work', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/fc/creator_updates/', {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(2000);
    
    // Click TikTok filter
    await page.click('.filter-btn[data-platform="tiktok"]');
    await page.waitForTimeout(500);
    
    // Check that TikTok filter is active
    const activeBtn = page.locator('.filter-btn.active');
    await expect(activeBtn).toHaveAttribute('data-platform', 'tiktok');
    
    // All visible cards should be TikTok
    const visibleCards = page.locator('.update-card:visible .platform-badge');
    const firstCard = visibleCards.first();
    if (await firstCard.count() > 0) {
      await expect(firstCard).toHaveClass(/tiktok/);
    }
  });

  test('profile-only cards display correctly', async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/fc/creator_updates/', {
      waitUntil: 'networkidle'
    });
    
    await page.waitForTimeout(2000);
    
    // Check for profile-only cards (TikTok/Instagram with limited data)
    const profileCards = page.locator('.update-card.profile-only');
    const profileCount = await profileCards.count();
    console.log(`Profile-only cards: ${profileCount}`);
    
    // If there are profile cards, check they have the notice
    if (profileCount > 0) {
      const notice = profileCards.first().locator('.profile-notice');
      await expect(notice).toBeVisible();
    }
  });
});
