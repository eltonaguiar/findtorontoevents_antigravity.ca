import { test, expect } from '@playwright/test';

/**
 * Verify that Lofe (a creator followed by user_id=2) shows up correctly
 * in the Creator Updates page and underlying APIs.
 *
 * This validates the fix for the bug where only Pokimane appeared in updates.
 */

const REMOTE_BASE = 'https://findtorontoevents.ca';

test.describe('Lofe Creator Updates Validation (user_id=2)', () => {

  test('API: creator_news_creators returns Lofe with content for user_id=2', async ({ request }) => {
    const response = await request.get(
      `${REMOTE_BASE}/fc/api/creator_news_creators.php?user_id=2`
    );
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.creators).toBeDefined();
    expect(data.total).toBeGreaterThan(1); // Must have more than just Pokimane

    // Find Lofe
    const lofe = data.creators.find(
      (c: any) => c.name && c.name.toLowerCase().includes('lofe')
    );
    expect(lofe).toBeDefined();
    expect(lofe.contentCount).toBeGreaterThan(0);

    console.log(`✅ Lofe found in creator_news_creators: id=${lofe.id}, contentCount=${lofe.contentCount}`);
    console.log(`   Total creators with content: ${data.total}`);
  });

  test('API: creator_news_api returns Lofe content items for user_id=2', async ({ request }) => {
    const response = await request.get(
      `${REMOTE_BASE}/fc/api/creator_news_api.php?user_id=2&limit=100`
    );
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.items).toBeDefined();
    expect(data.total).toBeGreaterThan(5); // Should have many items from many creators

    // Find Lofe items
    const lofeItems = data.items.filter(
      (item: any) => item.creator && item.creator.name && item.creator.name.toLowerCase().includes('lofe')
    );
    expect(lofeItems.length).toBeGreaterThan(0);

    console.log(`✅ Lofe has ${lofeItems.length} content items in feed`);
    for (const item of lofeItems) {
      console.log(`   - [${item.platform}] ${item.title?.substring(0, 60)}`);
    }
    console.log(`   Total feed items: ${data.total}`);
  });

  test('API: get_cached_updates returns Lofe updates for user_id=2', async ({ request }) => {
    const response = await request.get(
      `${REMOTE_BASE}/fc/api/get_cached_updates.php?user_id=2`
    );
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.ok).toBe(true);
    expect(data.updates).toBeDefined();
    expect(data.updates.length).toBeGreaterThan(10);

    // Find Lofe updates (check both creator.name and creator_name)
    const lofeUpdates = data.updates.filter((u: any) => {
      const creatorName = u.creator?.name || u.creator_name || '';
      return creatorName.toLowerCase().includes('lofe');
    });
    expect(lofeUpdates.length).toBeGreaterThan(0);

    // Verify Lofe updates have proper creator.id for filter matching
    for (const u of lofeUpdates) {
      expect(u.creator).toBeDefined();
      expect(u.creator.id).toBeDefined();
      expect(String(u.creator.id)).toBeTruthy(); // Must have a non-empty ID
    }

    console.log(`✅ Lofe has ${lofeUpdates.length} cached updates`);
    for (const u of lofeUpdates) {
      console.log(`   - [${u.platform}] creator.id=${u.creator?.id}, title=${u.content_title?.substring(0, 50)}`);
    }
    console.log(`   Total cached updates: ${data.updates.length}`);
    console.log(`   Unique creators: ${data.creators_count}`);
  });

  test('Page: creator_updates loads for user_id=2 with Lofe in dropdown', async ({ page }) => {
    // Listen for JS errors
    const errors: string[] = [];
    page.on('pageerror', (err) => {
      errors.push(`PageError: ${err.message}`);
    });
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Filter out known non-critical errors (network issues, favicon, etc.)
        if (!text.includes('net::') && !text.includes('favicon') && !text.includes('404') &&
            !text.includes('403') && !text.includes('Failed to load resource')) {
          errors.push(`ConsoleError: ${text}`);
        }
      }
    });

    // Navigate with user_id=2 override
    await page.goto(`${REMOTE_BASE}/fc/creator_updates/?user_id=2`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000
    });

    // Wait for the page to load and show stats
    await page.waitForSelector('.stats', { state: 'visible', timeout: 30000 });

    // Wait for updates to load
    await page.waitForTimeout(3000);

    // Check the creator dropdown is populated
    const creatorSelect = page.locator('#creatorSelect');
    await expect(creatorSelect).toBeVisible();

    // Get all options from the dropdown
    const options = await creatorSelect.locator('option').allTextContents();
    console.log(`Dropdown has ${options.length} options`);

    // Find Lofe in the dropdown
    const lofeOption = options.find(opt => opt.toLowerCase().includes('lofe'));
    expect(lofeOption).toBeDefined();
    console.log(`✅ Lofe found in dropdown: "${lofeOption}"`);

    // Select Lofe from the dropdown
    const lofeValue = await creatorSelect.locator('option', { hasText: /lofe/i }).getAttribute('value');
    expect(lofeValue).toBeTruthy();
    await creatorSelect.selectOption(lofeValue!);

    // Wait for filter to apply
    await page.waitForTimeout(1000);

    // Check that updates are shown (not "No updates found")
    const emptyState = page.locator('.empty-state');
    const updateCards = page.locator('.update-card');

    const isEmpty = await emptyState.isVisible().catch(() => false);
    const cardCount = await updateCards.count();

    console.log(`After selecting Lofe: isEmpty=${isEmpty}, cardCount=${cardCount}`);

    // Lofe MUST have at least one update card
    expect(cardCount).toBeGreaterThan(0);
    console.log(`✅ Lofe shows ${cardCount} update cards when filtered`);

    // Verify no critical JS errors
    if (errors.length > 0) {
      console.log('JS Errors:', errors);
    }
    expect(errors.length).toBe(0);
  });

  test('API: Multiple creators have content (not just Pokimane)', async ({ request }) => {
    const response = await request.get(
      `${REMOTE_BASE}/fc/api/creator_news_creators.php?user_id=2`
    );
    const data = await response.json();

    // Must have significantly more than 1 creator
    expect(data.total).toBeGreaterThan(10);

    // Get creator names
    const names = data.creators.map((c: any) => c.name);
    console.log(`✅ ${data.total} creators with content: ${names.slice(0, 15).join(', ')}...`);

    // Pokimane should still be there
    const hasPokimane = names.some((n: string) => n.toLowerCase().includes('pokimane'));
    expect(hasPokimane).toBe(true);

    // But there should be many more
    expect(data.total).toBeGreaterThan(10);
  });
});
