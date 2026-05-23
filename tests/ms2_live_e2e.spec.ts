import { test, expect, Page } from '@playwright/test';

const MS2_URL = 'https://findtorontoevents.ca/MOVIESHOWS2/app.html';

// Helper: wait for MS2 to fully load (database loaded + initial videos populated)
async function waitForMS2Ready(page: Page, timeoutMs = 45000) {
  // Wait for the scroll container with video slides
  await page.waitForSelector('.snap-center', { timeout: timeoutMs });
  // Wait for at least one iframe to appear (video loaded)
  await page.waitForSelector('iframe', { timeout: timeoutMs });
  // Give time for initial video population
  await page.waitForTimeout(2000);
}

// Helper: collect console errors/warnings
function collectConsoleLogs(page: Page) {
  const errors: string[] = [];
  const warnings: string[] = [];
  const logs: string[] = [];
  page.on('console', msg => {
    const text = msg.text();
    if (msg.type() === 'error') errors.push(text);
    else if (msg.type() === 'warning') warnings.push(text);
    else logs.push(text);
  });
  page.on('pageerror', err => {
    errors.push(`PAGE ERROR: ${err.message}`);
  });
  return { errors, warnings, logs };
}

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS2 Page Load & Basic Structure
// ═══════════════════════════════════════════════════════════

test.describe('MS2 Live - Page Load', () => {
  test('page loads successfully with 200 status', async ({ page }) => {
    const response = await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    expect(response?.status()).toBe(200);
  });

  test('essential scripts load', async ({ page }) => {
    const scriptLoads: Record<string, boolean> = {};
    page.on('response', resp => {
      const url = resp.url();
      if (url.includes('scroll-fix.js')) scriptLoads['scroll-fix'] = resp.status() === 200;
      if (url.includes('ms2-enhancer.js')) scriptLoads['ms2-enhancer'] = resp.status() === 200;
      if (url.includes('db-connector.js')) scriptLoads['db-connector'] = resp.status() === 200;
      if (url.includes('ui-minimal.js')) scriptLoads['ui-minimal'] = resp.status() === 200;
    });
    await page.goto(MS2_URL, { waitUntil: 'networkidle', timeout: 45000 });
    expect(scriptLoads['scroll-fix']).toBe(true);
    expect(scriptLoads['ms2-enhancer']).toBe(true);
  });

  test('database loads movies successfully', async ({ page }) => {
    const { logs } = collectConsoleLogs(page);
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    const dbLoaded = logs.some(l => l.includes('SUCCESS: Loaded') && l.includes('items from Database'));
    expect(dbLoaded).toBe(true);
  });

  test('initial video slides are populated', async ({ page }) => {
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    const slideCount = await page.locator('.snap-center').count();
    expect(slideCount).toBeGreaterThanOrEqual(5);
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS2 JavaScript Errors
// ═══════════════════════════════════════════════════════════

test.describe('MS2 Live - JS Errors', () => {
  test('no critical JS errors on load', async ({ page }) => {
    const { errors } = collectConsoleLogs(page);
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    // Filter out known non-critical errors (browser extensions, 3rd-party)
    const criticalErrors = errors.filter(e =>
      !e.includes('web-client-content-script') &&
      !e.includes('net::ERR_') &&
      !e.includes('favicon.ico') &&
      !e.includes('ResizeObserver') &&
      !e.includes('www-widgetapi')
    );

    // Report all errors found
    if (criticalErrors.length > 0) {
      console.log('=== CRITICAL JS ERRORS ===');
      criticalErrors.forEach(e => console.log('  ERROR:', e));
    }

    // Check specifically for the known updateMuteControl error
    const muteControlError = errors.some(e => e.includes('updateMuteControl'));
    if (muteControlError) {
      console.log('  *** CONFIRMED BUG: updateMuteControl is not defined ***');
    }

    expect(criticalErrors.length).toBe(0);
  });

  test('no updateMuteControl error during video selection', async ({ page }) => {
    const { errors } = collectConsoleLogs(page);
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    // Scroll to trigger video changes
    const container = page.locator('.snap-center').first().locator('..');
    for (let i = 0; i < 3; i++) {
      await container.evaluate(el => el.scrollBy(0, window.innerHeight));
      await page.waitForTimeout(500);
    }

    const muteError = errors.some(e => e.includes('updateMuteControl'));
    if (muteError) {
      console.log('  *** BUG CONFIRMED: updateMuteControl is not defined during scroll ***');
    }
    expect(muteError).toBe(false);
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS2 Settings / Gear Icon
// ═══════════════════════════════════════════════════════════

test.describe('MS2 Live - Settings Panel', () => {
  test('settings panel default state (collapsed or expanded)', async ({ page }) => {
    // Clear localStorage to simulate fresh user
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.evaluate(() => localStorage.removeItem('movieshows-settings-collapsed'));
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    const settingsToggle = page.locator('#settings-toggle');
    const playerSizeControl = page.locator('#player-size-control');

    const toggleExists = await settingsToggle.count() > 0;
    if (toggleExists) {
      const toggleText = await settingsToggle.textContent();
      const controlVisible = await playerSizeControl.isVisible().catch(() => false);

      console.log(`  Settings toggle text: "${toggleText}"`);
      console.log(`  Player size control visible: ${controlVisible}`);

      // Per bug report: user wants settings COLLAPSED by default
      if (controlVisible) {
        console.log('  *** BUG: Settings overlay is OPEN by default (should be closed) ***');
      }
    } else {
      console.log('  Settings toggle not found');
    }
  });

  test('gear icon shows filter badge when filters active', async ({ page }) => {
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    // Check if gear icon has any badge indicator mechanism
    const settingsToggle = page.locator('#settings-toggle');
    const hasBadge = await page.locator('#settings-toggle .filter-badge, #settings-toggle [data-filter-count]').count();
    console.log(`  Filter badge element exists: ${hasBadge > 0}`);
    if (hasBadge === 0) {
      console.log('  *** MISSING FEATURE: No filter badge on gear icon ***');
    }
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS2 Filters
// ═══════════════════════════════════════════════════════════

test.describe('MS2 Live - Year Filter', () => {
  test('apply 2026 year filter and verify feed content', async ({ page }) => {
    const { logs } = collectConsoleLogs(page);
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    // Open filter panel via the Filters button in the nav
    const filterBtn = page.locator('button:has-text("Filters"), [data-action="filters"]').first();
    const filterBtnExists = await filterBtn.count() > 0;

    if (!filterBtnExists) {
      console.log('  Filters button not found directly, trying nav buttons...');
      // Try clicking the filters nav button
      const navBtns = page.locator('nav button, .nav-btn, [class*="filter"]');
      const count = await navBtns.count();
      console.log(`  Found ${count} potential nav/filter buttons`);
      for (let i = 0; i < Math.min(count, 10); i++) {
        const text = await navBtns.nth(i).textContent();
        console.log(`    Button ${i}: "${text?.trim()}"`);
      }
      return;
    }

    await filterBtn.click();
    await page.waitForTimeout(500);

    // Click 2026 year filter button
    const yearBtn = page.locator('button[data-year="2026"], .filter-btn:has-text("2026")').first();
    if (await yearBtn.count() > 0) {
      await yearBtn.click();
      console.log('  Clicked 2026 year filter');

      // Click Apply Filters
      const applyBtn = page.locator('#apply-filters, button:has-text("Apply")').first();
      if (await applyBtn.count() > 0) {
        await applyBtn.click();
        await page.waitForTimeout(2000);

        // Check feed repopulation log
        const repopulated = logs.some(l => l.includes('Repopulating feed') || l.includes('Found') && l.includes('items'));
        console.log(`  Feed repopulated: ${repopulated}`);

        // Check what movies are in the feed now
        const slides = page.locator('.snap-center');
        const slideCount = await slides.count();
        console.log(`  Slides after filter: ${slideCount}`);

        // Check first few slide titles for year info
        for (let i = 0; i < Math.min(slideCount, 5); i++) {
          const titleEl = slides.nth(i).locator('h2, [data-movie-title]').first();
          const title = await titleEl.textContent().catch(() => 'N/A');
          const yearBadge = await slides.nth(i).locator('[class*="year"], [class*="badge"]').first().textContent().catch(() => 'N/A');
          console.log(`  Slide ${i}: "${title?.trim()}" | badge: "${yearBadge?.trim()}"`);
        }
      } else {
        console.log('  *** Apply Filters button not found ***');
      }
    } else {
      console.log('  *** 2026 year filter button not found ***');
    }
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS2 Scroll & Playback
// ═══════════════════════════════════════════════════════════

test.describe('MS2 Live - Scroll Playback', () => {
  test('only one video plays at a time during scroll', async ({ page }) => {
    const { logs, errors } = collectConsoleLogs(page);
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    // Scroll through 5 videos
    const container = page.locator('.snap-center').first().locator('..');
    for (let i = 0; i < 5; i++) {
      await container.evaluate(el => el.scrollBy(0, window.innerHeight));
      await page.waitForTimeout(800);
    }

    // Check for "Playing ONLY:" log messages — each should appear once per scroll
    const playOnlyLogs = logs.filter(l => l.includes('Playing ONLY:'));
    const playLogs = logs.filter(l => l.includes('Playing:') && l.includes('muted='));

    console.log(`  "Playing ONLY" log count: ${playOnlyLogs.length}`);
    console.log(`  "Playing" log count: ${playLogs.length}`);

    // Check if multiple videos were stopped/started simultaneously
    // Look for patterns where multiple plays happen in quick succession
    let multiplePlayCount = 0;
    for (let i = 1; i < playOnlyLogs.length; i++) {
      // If the same video appears in consecutive logs, something is wrong
      if (playOnlyLogs[i] === playOnlyLogs[i-1]) {
        multiplePlayCount++;
      }
    }

    if (multiplePlayCount > 0) {
      console.log(`  *** BUG: ${multiplePlayCount} duplicate consecutive play events ***`);
    }

    // Count how many YouTube iframes are actively playing (src contains youtube.com)
    const activeIframes = await page.evaluate(() => {
      const iframes = document.querySelectorAll('iframe');
      let active = 0;
      iframes.forEach(f => {
        if (f.src && f.src.includes('youtube.com') && f.src.includes('autoplay=1')) {
          active++;
        }
      });
      return active;
    });

    console.log(`  Active YouTube iframes after scrolling: ${activeIframes}`);

    // Only 1 should be active
    if (activeIframes > 1) {
      console.log(`  *** BUG: Multiple videos playing simultaneously (${activeIframes} active) ***`);
    }
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS2 Top 50 Section
// ═══════════════════════════════════════════════════════════

test.describe('MS2 Live - Top 50 Section', () => {
  test('Top 50 panel loads with content', async ({ page }) => {
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    // Look for the Top 50 panel or button
    const topPanel = page.locator('#ms2-top-panel');
    const topPanelExists = await topPanel.count() > 0;
    console.log(`  Top 50 panel element exists: ${topPanelExists}`);

    // Look for Top section cards
    const topCards = page.locator('.top-card');
    const topCardCount = await topCards.count();
    console.log(`  Top cards found: ${topCardCount}`);

    // Check sections
    const topSections = page.locator('.ms2-top-section');
    const sectionCount = await topSections.count();
    console.log(`  Top sections found: ${sectionCount}`);

    if (sectionCount > 0) {
      for (let i = 0; i < sectionCount; i++) {
        const header = await topSections.nth(i).locator('.top-header, .top-title').first().textContent().catch(() => 'N/A');
        const cardCount = await topSections.nth(i).locator('.top-card').count();
        console.log(`    Section ${i}: "${header?.trim()}" (${cardCount} cards)`);
      }
    }
  });

  test('clicking Top 50 card triggers play in feed', async ({ page }) => {
    const { logs } = collectConsoleLogs(page);
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    // Open Top 50 panel
    const topBtn = page.locator('#ms2-top-panel-toggle, button:has-text("Top 50"), button:has-text("Top")').first();
    if (await topBtn.count() === 0) {
      console.log('  Top 50 button not found, checking enhancer overlay buttons...');
      // The ms2-enhancer creates the top panel. Look for it.
      const enhancerBtns = page.locator('[class*="ms2-top"], [id*="ms2-top"]');
      console.log(`  Enhancer top elements: ${await enhancerBtns.count()}`);
      return;
    }

    // Find and click the first playable top card
    const topCards = page.locator('.top-card');
    if (await topCards.count() > 0) {
      const firstCard = topCards.first();
      const cardTitle = await firstCard.locator('.top-card-title').textContent().catch(() => 'unknown');
      console.log(`  Clicking first top card: "${cardTitle}"`);

      await firstCard.click();
      await page.waitForTimeout(3000);

      // Check if prompt appeared
      const topPrompt = page.locator('#ms2-top-prompt');
      const promptVisible = await topPrompt.isVisible().catch(() => false);
      console.log(`  Top auto-play prompt visible: ${promptVisible}`);

      if (promptVisible) {
        const promptText = await topPrompt.textContent();
        console.log(`  Prompt text: "${promptText?.trim()}"`);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS2 Freestyle Search
// ═══════════════════════════════════════════════════════════

test.describe('MS2 Live - Freestyle Search', () => {
  test('freestyle overlay opens and search works', async ({ page }) => {
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    // Open freestyle overlay
    const freestyleBtn = page.locator('#ms2-freestyle-btn, [class*="freestyle"]').first();
    if (await freestyleBtn.count() === 0) {
      // Try the Search & Browse button which may toggle freestyle
      const searchBtn = page.locator('button:has-text("Search"), button:has-text("Browse")').first();
      if (await searchBtn.count() > 0) {
        await searchBtn.click();
        await page.waitForTimeout(500);
      }
    }

    const freestyleOverlay = page.locator('#ms2-freestyle-overlay');
    const overlayExists = await freestyleOverlay.count() > 0;
    console.log(`  Freestyle overlay exists: ${overlayExists}`);

    if (overlayExists) {
      const isActive = await freestyleOverlay.evaluate(el => el.classList.contains('active'));
      console.log(`  Freestyle overlay active: ${isActive}`);

      if (!isActive) {
        // Try to find and click the freestyle button within the UI
        const fsToggle = page.locator('[class*="freestyle"] button, .ms2-freestyle-btn').first();
        if (await fsToggle.count() > 0) {
          await fsToggle.click();
          await page.waitForTimeout(500);
        }
      }

      // Try performing a search
      const searchInput = page.locator('#ms2-freestyle-input, input[placeholder*="search" i], input[placeholder*="freestyle" i]').first();
      if (await searchInput.count() > 0) {
        await searchInput.fill('how to get a girlfriend');
        await searchInput.press('Enter');
        await page.waitForTimeout(3000);

        // Check for results
        const results = page.locator('.fs-result, [class*="freestyle-result"]');
        const resultCount = await results.count();
        console.log(`  Freestyle results for "how to get a girlfriend": ${resultCount}`);

        // Check if there's a queue/add button
        const queueBtns = page.locator('.fs-queue-btn, button:has-text("Queue"), button:has-text("+")');
        const queueBtnCount = await queueBtns.count();
        console.log(`  Queue buttons in freestyle results: ${queueBtnCount}`);
        if (queueBtnCount === 0) {
          console.log('  *** MISSING FEATURE: No queue button in freestyle results ***');
        }
      } else {
        console.log('  Freestyle search input not found');
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS2 Navigation & UI Elements
// ═══════════════════════════════════════════════════════════

test.describe('MS2 Live - Navigation', () => {
  test('all nav buttons exist and are clickable', async ({ page }) => {
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    // Check for key navigation elements
    const navElements = {
      'Filters': 'button:has-text("Filters")',
      'Search/Browse': 'button:has-text("Search"), button:has-text("Browse")',
      'Queue': 'button:has-text("Queue")',
      'Now Playing': 'button:has-text("Now Playing"), button:has-text("now playing")',
      'Hamburger': '.hamburger, [class*="hamburger"]',
    };

    for (const [name, selector] of Object.entries(navElements)) {
      const el = page.locator(selector).first();
      const exists = await el.count() > 0;
      const visible = exists ? await el.isVisible().catch(() => false) : false;
      console.log(`  ${name}: exists=${exists}, visible=${visible}`);
    }
  });

  test('hamburger menu opens and has items', async ({ page }) => {
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    const hamburger = page.locator('.hamburger, [class*="hamburger"]').first();
    if (await hamburger.count() > 0) {
      await hamburger.click();
      await page.waitForTimeout(500);

      const drawer = page.locator('.drawer, [class*="drawer"]').first();
      const drawerVisible = await drawer.isVisible().catch(() => false);
      console.log(`  Hamburger drawer visible: ${drawerVisible}`);
    }
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS2 Enhancer Features Check
// ═══════════════════════════════════════════════════════════

test.describe('MS2 Live - Enhancer Features', () => {
  test('ms2-enhancer version and initialization', async ({ page }) => {
    const { logs } = collectConsoleLogs(page);
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    const enhancerInit = logs.find(l => l.includes('MS2 Enhancer'));
    console.log(`  Enhancer init log: "${enhancerInit || 'NOT FOUND'}"`);

    // Check enhancer version from cache bust
    const enhancerVersion = await page.evaluate(() => {
      const scripts = document.querySelectorAll('script[src*="ms2-enhancer"]');
      return scripts.length > 0 ? scripts[0].getAttribute('src') : 'not found';
    });
    console.log(`  Enhancer script src: ${enhancerVersion}`);
  });

  test('top section renders from JSON', async ({ page }) => {
    const { logs } = collectConsoleLogs(page);
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS2Ready(page);

    const topLoaded = logs.some(l => l.includes('Top section loaded'));
    console.log(`  Top section loaded from JSON: ${topLoaded}`);

    // Check for top section DOM
    const topSections = await page.locator('.ms2-top-section').count();
    const topCards = await page.locator('.top-card').count();
    console.log(`  Top sections: ${topSections}, Top cards: ${topCards}`);
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS2 Cache Bust Verification
// ═══════════════════════════════════════════════════════════

test.describe('MS2 Live - Deployment Verification', () => {
  test('latest cache bust version deployed', async ({ page }) => {
    await page.goto(MS2_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });

    const scriptVersions = await page.evaluate(() => {
      const scripts = Array.from(document.querySelectorAll('script[src]'));
      return scripts.map(s => s.getAttribute('src')).filter(s => s && (s.includes('scroll-fix') || s.includes('ms2-enhancer') || s.includes('db-connector') || s.includes('ui-minimal')));
    });

    console.log('  Deployed script versions:');
    scriptVersions.forEach(s => console.log(`    ${s}`));

    // Check if the latest enhancer version is deployed
    const enhancerSrc = scriptVersions.find(s => s?.includes('ms2-enhancer'));
    if (enhancerSrc) {
      const match = enhancerSrc.match(/v=(\w+)/);
      console.log(`  Enhancer cache bust: ${match ? match[1] : 'none'}`);
    }
  });
});
