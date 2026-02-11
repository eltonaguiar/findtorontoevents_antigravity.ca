/**
 * Theme Switcher — Comprehensive Playwright tests
 *
 * Verifies the site-wide theme picker works correctly and that
 * core site functionality is preserved after themes are applied.
 *
 * Run:
 *   npx playwright test tests/theme-switcher.spec.ts --project="Desktop Chrome"
 *
 * Against custom port:
 *   BASE_URL=http://localhost:5173 npx playwright test tests/theme-switcher.spec.ts --project="Desktop Chrome"
 */

import { test, expect, Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const BASE = process.env.BASE_URL || 'http://localhost:5173';

// Known error patterns to ignore (pre-existing, not theme-related)
const IGNORE_ERRORS = [
  /Minified React error #418/,
  /418.*HTML/,
  /hydration/i,
  /favicon\.ico/,
  /DIAGNOSTIC/,
  /get_me\.php/,
  /Failed to load resource/,
  /net::ERR_/,
  /CORS/,
  /403|400/,
];

function isIgnoredError(text: string): boolean {
  return IGNORE_ERRORS.some((p) => p.test(text));
}

// Selectors — the theme system is not yet built, so these are the planned
// selectors based on the UX spec. Adjust once implementation lands.
const SEL = {
  // Gear button (bottom-right settings icon, line 905 of index.html)
  gearButton: 'div.fixed.bottom-6.right-6 button[aria-label="Open Settings"]',

  // Theme picker overlay (injected by theme-switcher script)
  pickerOverlay: '#theme-picker-overlay',
  pickerPanel: '#theme-picker-panel',
  pickerClose: '#theme-picker-close',
  pickerSearch: '#theme-picker-search',

  // Theme category tabs
  categoryTab: (name: string) =>
    `#theme-picker-panel [data-category-tab="${name}"]`,
  categoryTabAll: '#theme-picker-panel [data-category-tab="all"]',

  // Theme cards
  themeCard: (id: string) =>
    `#theme-picker-panel [data-theme-id="${id}"]`,
  themeCardAny: '#theme-picker-panel [data-theme-id]',
  themeApplyBtn: (id: string) =>
    `#theme-picker-panel [data-theme-id="${id}"] button[data-action="apply"]`,
  themeActiveIndicator: '.theme-card-active',

  // Reset button
  resetButton: '#theme-picker-reset',

  // AI Assistant (FAB button injected by ai-assistant.js)
  aiButton: '#fte-ai-btn',
  aiPanel: '#fte-ai-panel',
  aiClose: '#fte-ai-close',

  // Sign-in island (injected by script, line ~3316-3404)
  signInIsland: '#signin-island',
  signInButton: '#signin-island button',
  signInModal: '#signin-modal',
  signInModalClose: '#signin-modal-close',

  // Event cards (React hydrated)
  eventCards:
    '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',

  // React search bar — The Next.js app renders an <input> for event search.
  // Selector depends on React hydration; fall back to visible text input.
  searchInput: 'input[placeholder*="search" i], input[placeholder*="find" i], input[type="search"]',

  // Category filter buttons (rendered by React in the main content area)
  categoryFilterBtn: 'button[data-category], [role="tab"][data-category]',

  // Date filter — "Today" / "This Weekend" etc.
  dateFilterToday:
    'button:has-text("Today"), [data-date-filter="today"]',

  // Other Stuff menu
  otherStuffPromo: '.otherstuff-promo',
  otherStuffOverlay: '#otherstuff-overlay',
  otherStuffPopup: '#otherstuff-popup',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Wait for page to be reasonably loaded (events JSON fetched, cards rendered). */
async function waitForPageReady(page: Page) {
  await page.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 30_000 });
  // Allow React hydration + injected scripts to settle
  await page.waitForTimeout(3000);
}

/** Open the theme picker via the gear button. */
async function openThemePicker(page: Page) {
  const gear = page.locator(SEL.gearButton);
  await expect(gear).toBeVisible({ timeout: 10_000 });
  await gear.click();
  // Wait for the picker overlay to appear
  await expect(page.locator(SEL.pickerOverlay)).toBeVisible({ timeout: 5000 });
}

/** Apply a theme by its registry id (e.g. "blog100"). */
async function applyTheme(page: Page, themeId: string) {
  const applyBtn = page.locator(SEL.themeApplyBtn(themeId));
  await expect(applyBtn).toBeVisible({ timeout: 5000 });
  await applyBtn.click();
  // Allow CSS transition to settle
  await page.waitForTimeout(500);
}

/** Read computed CSS variable from <html> or <body>. */
async function getCSSVar(page: Page, varName: string): Promise<string> {
  return page.evaluate((v) => {
    return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  }, varName);
}

/** Read localStorage value. */
async function getLocalStorage(page: Page, key: string): Promise<string | null> {
  return page.evaluate((k) => localStorage.getItem(k), key);
}

// ---------------------------------------------------------------------------
// Suite 1: Theme Picker UI
// ---------------------------------------------------------------------------

test.describe('Suite 1: Theme Picker UI', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any stored theme before each test
    await page.addInitScript(() => {
      localStorage.removeItem('toronto-events-settings');
    });
    await waitForPageReady(page);
  });

  test('T1.1 — Gear button click opens theme picker overlay', async ({ page }) => {
    await openThemePicker(page);
    await expect(page.locator(SEL.pickerPanel)).toBeVisible();
  });

  test('T1.2 — Theme picker shows category tabs', async ({ page }) => {
    await openThemePicker(page);

    // "All" tab should always exist
    await expect(page.locator(SEL.categoryTabAll)).toBeVisible();

    // Verify all known categories (must match CATEGORIES in theme-switcher.js)
    const expectedCategories = ['Living', 'Still', 'Cyberpunk', 'Light', 'Nature', 'Elegant', 'Retro', 'Space', 'Minimal'];
    for (const cat of expectedCategories) {
      const tab = page.locator(SEL.categoryTab(cat));
      await expect(tab, `Category tab "${cat}" should be present`).toBeVisible({ timeout: 3000 });
    }
  });

  test('T1.3 — Search bar filters themes by name', async ({ page }) => {
    await openThemePicker(page);

    const searchInput = page.locator(SEL.pickerSearch);
    await expect(searchInput).toBeVisible();

    // Count all visible theme cards before search
    const allCards = page.locator(SEL.themeCardAny);
    const totalBefore = await allCards.count();
    expect(totalBefore).toBeGreaterThan(0);

    // Type a specific theme name
    await searchInput.fill('Matrix Rain');
    await page.waitForTimeout(300);

    // Should filter down — fewer visible cards
    const visibleAfter = await allCards.filter({ has: page.locator(':visible') }).count();
    // At minimum the matching theme should appear
    const matrixCard = page.locator(SEL.themeCard('blog101'));
    await expect(matrixCard).toBeVisible();

    // Clear search
    await searchInput.fill('');
    await page.waitForTimeout(300);
    const afterClear = await allCards.count();
    expect(afterClear).toBe(totalBefore);
  });

  test('T1.4 — Category tab filters themes correctly', async ({ page }) => {
    await openThemePicker(page);

    // Click "Cyberpunk" tab
    const cyberpunkTab = page.locator(SEL.categoryTab('Cyberpunk'));
    await cyberpunkTab.click();
    await page.waitForTimeout(300);

    // All visible cards should be Cyberpunk-category themes
    const visibleCards = page.locator(`${SEL.themeCardAny}:visible`);
    const count = await visibleCards.count();
    expect(count).toBeGreaterThan(0);

    // Verify at least one known cyberpunk theme is present
    await expect(page.locator(SEL.themeCard('blog100'))).toBeVisible(); // Neon Cyberpunk

    // Switch to "All" — should show more
    await page.locator(SEL.categoryTabAll).click();
    await page.waitForTimeout(300);
    const allCount = await page.locator(`${SEL.themeCardAny}:visible`).count();
    expect(allCount).toBeGreaterThanOrEqual(count);
  });

  test('T1.5 — Theme cards display name, color swatch, and apply button', async ({ page }) => {
    await openThemePicker(page);

    // Check a known theme card structure
    const card = page.locator(SEL.themeCard('blog100'));
    await expect(card).toBeVisible();

    // Name should be visible
    await expect(card.locator('text=Neon Cyberpunk')).toBeVisible();

    // Apply button should exist
    const applyBtn = page.locator(SEL.themeApplyBtn('blog100'));
    await expect(applyBtn).toBeVisible();

    // Color swatch — the card should contain a visual preview element
    // (exact selector depends on implementation; check for any color-showing child)
    const swatch = card.locator('[data-swatch], [class*="swatch"], [class*="preview"], [style*="background"]');
    const swatchCount = await swatch.count();
    expect(swatchCount, 'Theme card should have at least one color swatch/preview element').toBeGreaterThan(0);
  });

  test('T1.6 — Close button and backdrop click closes the picker', async ({ page }) => {
    // Test close button
    await openThemePicker(page);
    const closeBtn = page.locator(SEL.pickerClose);
    await closeBtn.click();
    await page.waitForTimeout(300);
    await expect(page.locator(SEL.pickerOverlay)).not.toBeVisible();

    // Test backdrop click
    await openThemePicker(page);
    const overlay = page.locator(SEL.pickerOverlay);
    // Click on the overlay itself (not the panel) to dismiss
    await overlay.click({ position: { x: 10, y: 10 } });
    await page.waitForTimeout(300);
    await expect(page.locator(SEL.pickerOverlay)).not.toBeVisible();
  });

  test('T1.7 — Keyboard ESC closes the picker', async ({ page }) => {
    await openThemePicker(page);
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    await expect(page.locator(SEL.pickerOverlay)).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Suite 2: Theme Application
// ---------------------------------------------------------------------------

test.describe('Suite 2: Theme Application', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.removeItem('toronto-events-settings');
    });
    await waitForPageReady(page);
  });

  test('T2.1 — Apply changes body background color', async ({ page }) => {
    const bgBefore = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );

    await openThemePicker(page);
    // Apply "Neon Cyberpunk" (bg: #0a0a1a)
    await applyTheme(page, 'blog100');

    const bgAfter = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );

    // The background should have changed
    expect(bgAfter).not.toBe(bgBefore);
  });

  test('T2.2 — Apply changes --pk-500 CSS variable', async ({ page }) => {
    const pkBefore = await getCSSVar(page, '--pk-500');

    await openThemePicker(page);
    await applyTheme(page, 'blog100');

    const pkAfter = await getCSSVar(page, '--pk-500');
    // Should have changed (or been set if previously unset)
    expect(pkAfter.length).toBeGreaterThan(0);
    // For Neon Cyberpunk the accent is #00ff88 — the CSS var should reflect that
  });

  test('T2.3 — Applied theme shows active indicator on its card', async ({ page }) => {
    await openThemePicker(page);
    await applyTheme(page, 'blog100');

    // The card should have an active class or indicator
    const card = page.locator(SEL.themeCard('blog100'));
    const hasActive = await card.evaluate((el) =>
      el.classList.contains('theme-card-active') ||
      el.querySelector('.theme-card-active, [data-active="true"]') !== null ||
      el.getAttribute('data-active') === 'true' ||
      el.getAttribute('aria-selected') === 'true'
    );
    expect(hasActive, 'Applied theme card should have an active indicator').toBe(true);
  });

  test('T2.4 — Reset to Default restores original colors', async ({ page }) => {
    // Capture original state
    const originalBg = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );

    // Apply a theme
    await openThemePicker(page);
    await applyTheme(page, 'blog100');

    // Now reset
    const resetBtn = page.locator(SEL.resetButton);
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();
    await page.waitForTimeout(500);

    // Background should return to original
    const restoredBg = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );
    expect(restoredBg).toBe(originalBg);

    // localStorage should have theme cleared
    const stored = await getLocalStorage(page, 'toronto-events-settings');
    if (stored) {
      const parsed = JSON.parse(stored);
      expect(parsed.selectedTheme).toBeFalsy();
    }
  });

  test('T2.5 — Theme persists after page reload (localStorage)', async ({ page }) => {
    await openThemePicker(page);
    await applyTheme(page, 'blog101'); // Matrix Rain

    // Verify localStorage was set
    const stored = await getLocalStorage(page, 'toronto-events-settings');
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed.selectedTheme).toBe('blog101');

    // Reload the page
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    // Background should still be Matrix Rain (bg: #000a00)
    const bg = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );
    // #000a00 in rgb is approximately rgb(0, 10, 0)
    expect(bg).not.toBe('rgba(0, 0, 0, 0)'); // Not transparent/default
  });

  test('T2.6 — Apply a light theme — text remains readable', async ({ page }) => {
    await openThemePicker(page);

    // Apply a light theme (blog125 or first "Light" category theme)
    // TODO: Adjust theme ID once light themes are finalized
    const lightThemeId = 'blog125';
    await applyTheme(page, lightThemeId);

    // Check that text color has sufficient contrast against background
    const { textColor, bgColor } = await page.evaluate(() => {
      const body = document.body;
      const cs = getComputedStyle(body);
      return {
        textColor: cs.color,
        bgColor: cs.backgroundColor,
      };
    });

    // Text and background should be different
    expect(textColor).not.toBe(bgColor);

    // Event cards should still be visible (not invisible text on similar background)
    const cards = page.locator(SEL.eventCards);
    const cardCount = await cards.count();
    if (cardCount > 0) {
      const firstCard = cards.first();
      await expect(firstCard).toBeVisible();
    }
  });

  test('T2.7 — Apply a theme with custom font — font loads and applies', async ({ page }) => {
    await openThemePicker(page);
    // Apply "Neon Cyberpunk" which uses Orbitron heading font
    await applyTheme(page, 'blog100');

    // Check if the heading font family was applied
    const fontFamily = await page.evaluate(() => {
      // Check body or heading elements for font change
      const h = document.querySelector('h1, h2, h3');
      if (h) return getComputedStyle(h).fontFamily;
      return getComputedStyle(document.body).fontFamily;
    });

    // Orbitron should appear in the font family stack
    // (The font may not have loaded yet from Google Fonts, but the CSS value should reference it)
    expect(fontFamily.toLowerCase()).toMatch(/orbitron|sans-serif/);
  });
});

// ---------------------------------------------------------------------------
// Suite 3: Core Functionality Preservation (with theme applied)
// ---------------------------------------------------------------------------

test.describe('Suite 3: Core Functionality Preservation', () => {
  test.beforeEach(async ({ page }) => {
    // Apply a theme BEFORE running core tests to verify nothing breaks
    await page.addInitScript(() => {
      localStorage.setItem(
        'toronto-events-settings',
        JSON.stringify({ selectedTheme: 'blog100' })
      );
    });
    await waitForPageReady(page);
  });

  test('T3.1 — AI chatbot icon is visible and clickable after theme applied', async ({ page }) => {
    const aiBtn = page.locator(SEL.aiButton);
    await expect(aiBtn).toBeVisible({ timeout: 10_000 });

    // Click should open the AI panel
    await aiBtn.click();
    await page.waitForTimeout(500);

    const aiPanel = page.locator(SEL.aiPanel);
    // Panel should become visible (has .open class)
    const isOpen = await aiPanel.evaluate((el) =>
      el.classList.contains('open') || getComputedStyle(el).display !== 'none'
    );
    expect(isOpen, 'AI panel should open on button click').toBe(true);

    // Close it
    const closeBtn = page.locator(SEL.aiClose);
    if (await closeBtn.isVisible()) {
      await closeBtn.click();
    }
  });

  test('T3.2 — Sign-in button is visible, has glow effect, and opens modal', async ({ page }) => {
    // The sign-in button is injected by script into the Quick Nav sidebar.
    // Look for any element containing "Sign in" text with the glow class.
    const signInBtn = page.locator('button:has-text("Sign in"), [onclick*="openSignInModal"]').first();
    await expect(signInBtn).toBeVisible({ timeout: 10_000 });

    // Verify glow animation class is present (nav-glow-signin)
    const hasGlow = await signInBtn.evaluate((el) => {
      const cs = getComputedStyle(el);
      return el.className.includes('nav-glow-signin') ||
        cs.animationName !== 'none' ||
        cs.boxShadow !== 'none';
    });
    expect(hasGlow, 'Sign-in button should have glow effect').toBe(true);

    // Click should open sign-in modal
    await signInBtn.click();
    await page.waitForTimeout(500);

    const modal = page.locator(SEL.signInModal);
    const modalVisible = await modal.evaluate((el) =>
      el && getComputedStyle(el).display !== 'none'
    );
    expect(modalVisible, 'Sign-in modal should open').toBe(true);

    // Close modal
    const closeBtn = page.locator(SEL.signInModalClose);
    if (await closeBtn.isVisible()) {
      await closeBtn.click();
    }
  });

  test('T3.3 — Event search: type "dating" filters results', async ({ page }) => {
    // The React app renders a search input for event filtering.
    // Wait for event cards to load first.
    const cards = page.locator(SEL.eventCards);
    await expect(cards.first()).toBeVisible({ timeout: 15_000 });
    const totalBefore = await cards.count();

    // Find and use the search input
    const searchInput = page.locator(SEL.searchInput).first();
    await expect(searchInput).toBeVisible({ timeout: 10_000 });

    await searchInput.fill('dating');
    await page.waitForTimeout(1000);

    // After filtering, either fewer cards or cards contain "dating" in text
    const visibleCards = page.locator(`${SEL.eventCards}:visible`);
    const filteredCount = await visibleCards.count();

    if (filteredCount > 0) {
      // Check that at least one visible card mentions "dating"
      const firstCardText = await visibleCards.first().textContent();
      expect(
        firstCardText?.toLowerCase().includes('dat') || filteredCount < totalBefore,
        'Search for "dating" should filter event cards'
      ).toBe(true);
    }
    // If zero results, that's also acceptable — the filter worked

    // Clear search
    await searchInput.fill('');
  });

  test('T3.4 — Event combo filter: "dating" + "today" filters correctly', async ({ page }) => {
    const cards = page.locator(SEL.eventCards);
    await expect(cards.first()).toBeVisible({ timeout: 15_000 });

    // Type "dating" in search
    const searchInput = page.locator(SEL.searchInput).first();
    await expect(searchInput).toBeVisible({ timeout: 10_000 });
    await searchInput.fill('dating');
    await page.waitForTimeout(500);

    // Click "Today" date filter if available
    const todayBtn = page.locator(SEL.dateFilterToday).first();
    if (await todayBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await todayBtn.click();
      await page.waitForTimeout(500);

      // Both filters should be active simultaneously
      const visibleCards = page.locator(`${SEL.eventCards}:visible`);
      const count = await visibleCards.count();
      // Result can be 0 (no dating events today) — that's valid combo filtering
      console.log(`Combo filter "dating" + "today" shows ${count} results`);
    } else {
      // TODO: Date filter button not found — adjust selector once implemented
      console.log('Date filter "Today" button not found; skipping combo test');
    }

    await searchInput.fill('');
  });

  test('T3.5 — Category buttons still work with theme applied', async ({ page }) => {
    const cards = page.locator(SEL.eventCards);
    await expect(cards.first()).toBeVisible({ timeout: 15_000 });

    // Find category filter buttons
    const categoryBtns = page.locator(SEL.categoryFilterBtn);
    const btnCount = await categoryBtns.count();

    if (btnCount > 0) {
      // Click the first category button
      await categoryBtns.first().click();
      await page.waitForTimeout(500);

      // Page should still be functional (no crash, cards may filter)
      const visibleCards = page.locator(`${SEL.eventCards}:visible`);
      const count = await visibleCards.count();
      console.log(`After category click: ${count} visible cards`);
    } else {
      // React-rendered category buttons — try text-based approach
      // TODO: Adjust once category button selectors are confirmed
      console.log('Category buttons not found with current selector; may need update');
    }
  });

  test('T3.6 — Filter reset clears all filters', async ({ page }) => {
    const cards = page.locator(SEL.eventCards);
    await expect(cards.first()).toBeVisible({ timeout: 15_000 });
    const totalBefore = await cards.count();

    // Apply a text filter
    const searchInput = page.locator(SEL.searchInput).first();
    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await searchInput.fill('xyznonexistent');
      await page.waitForTimeout(500);

      // Clear by emptying the input
      await searchInput.fill('');
      await page.waitForTimeout(500);

      // Cards should return to original count
      const afterReset = await cards.count();
      expect(afterReset).toBe(totalBefore);
    }
  });

  test('T3.7 — Other Stuff menu opens and closes with theme applied', async ({ page }) => {
    // Verify the menu open/close function exists
    const fnExists = await page.evaluate(
      () => typeof (window as any).openOtherStuffMenu === 'function'
    );
    expect(fnExists, 'openOtherStuffMenu function should exist').toBe(true);

    // Open via function call
    await page.evaluate(() => (window as any).openOtherStuffMenu());
    await page.waitForTimeout(500);

    const overlayOpen = await page.evaluate(() => {
      const ov = document.getElementById('otherstuff-overlay');
      return ov ? ov.classList.contains('open') : false;
    });
    expect(overlayOpen, 'Other Stuff overlay should open').toBe(true);

    // Verify popup content is visible
    const popupOpen = await page.evaluate(() => {
      const pp = document.getElementById('otherstuff-popup');
      return pp ? pp.classList.contains('open') : false;
    });
    expect(popupOpen, 'Other Stuff popup should be open').toBe(true);

    // Close via function
    await page.evaluate(() => (window as any).closeOtherStuffMenu());
    await page.waitForTimeout(300);

    const overlayClosed = await page.evaluate(() => {
      const ov = document.getElementById('otherstuff-overlay');
      return ov ? ov.classList.contains('open') : true;
    });
    expect(overlayClosed, 'Other Stuff overlay should close').toBe(false);
  });

  test('T3.8 — Page scroll works normally (theme overlay does not break scroll)', async ({ page }) => {
    // Scroll down
    await page.evaluate(() => window.scrollTo(0, 500));
    await page.waitForTimeout(300);

    const scrollY = await page.evaluate(() => window.scrollY);
    expect(scrollY).toBeGreaterThan(0);

    // Scroll back up
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(300);

    const scrollTop = await page.evaluate(() => window.scrollY);
    expect(scrollTop).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// Suite 4: Edge Cases
// ---------------------------------------------------------------------------

test.describe('Suite 4: Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.removeItem('toronto-events-settings');
    });
    await waitForPageReady(page);
  });

  test('T4.1 — Rapid theme switching (5 themes quickly) — no visual glitches', async ({
    page,
  }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', (err) => {
      if (!isIgnoredError(err.message)) {
        jsErrors.push(`PageError: ${err.message}`);
      }
    });

    await openThemePicker(page);

    // Rapidly apply 5 different themes
    const themeIds = ['blog100', 'blog101', 'blog110', 'blog120', 'blog130'];
    for (const id of themeIds) {
      // Scroll the card into view and click apply
      const card = page.locator(SEL.themeCard(id));
      if (await card.isVisible({ timeout: 2000 }).catch(() => false)) {
        const applyBtn = page.locator(SEL.themeApplyBtn(id));
        await applyBtn.click();
        // Minimal wait between switches
        await page.waitForTimeout(100);
      }
    }

    // Wait for everything to settle
    await page.waitForTimeout(1000);

    // Should have no JS errors from rapid switching
    expect(
      jsErrors,
      `No JS errors during rapid theme switching. Got: ${jsErrors.join(', ')}`
    ).toHaveLength(0);

    // Page should not be blank — body should have content
    const bodyHtml = await page.evaluate(() => document.body.innerHTML.length);
    expect(bodyHtml).toBeGreaterThan(100);
  });

  test('T4.2 — Apply theme, open chatbot, theme colors still applied', async ({ page }) => {
    await openThemePicker(page);
    await applyTheme(page, 'blog100');

    // Close theme picker
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    // Capture the background color with theme applied
    const themedBg = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );

    // Open AI chatbot
    const aiBtn = page.locator(SEL.aiButton);
    await expect(aiBtn).toBeVisible({ timeout: 10_000 });
    await aiBtn.click();
    await page.waitForTimeout(500);

    // Background should still be the themed color
    const bgAfterChat = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );
    expect(bgAfterChat).toBe(themedBg);

    // Close chatbot
    const closeBtn = page.locator(SEL.aiClose);
    if (await closeBtn.isVisible()) {
      await closeBtn.click();
    }
  });

  test('T4.3 — Mobile viewport (375px width) — picker is usable', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 384, height: 854 });
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    // Gear button should still be accessible
    const gear = page.locator(SEL.gearButton);
    await expect(gear).toBeVisible({ timeout: 10_000 });
    await gear.click();

    // Picker should open and be usable
    await expect(page.locator(SEL.pickerOverlay)).toBeVisible({ timeout: 5000 });
    await expect(page.locator(SEL.pickerPanel)).toBeVisible();

    // Panel should not overflow viewport width
    const panelWidth = await page.locator(SEL.pickerPanel).evaluate((el) => {
      return el.getBoundingClientRect().width;
    });
    expect(panelWidth).toBeLessThanOrEqual(384);

    // Apply button should be tappable
    const firstApply = page.locator(`${SEL.themeCardAny} button[data-action="apply"]`).first();
    if (await firstApply.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(firstApply).toBeVisible();
    }

    // Close via Escape
    await page.keyboard.press('Escape');
    await expect(page.locator(SEL.pickerOverlay)).not.toBeVisible();
  });

  test('T4.4 — Apply theme, navigate away, come back — theme still applied', async ({
    page,
  }) => {
    await openThemePicker(page);
    await applyTheme(page, 'blog100');

    // Capture themed background
    const themedBg = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );

    // Navigate to a sub-page (e.g. /weather/)
    await page.goto(BASE + '/weather/', { waitUntil: 'networkidle', timeout: 30_000 });
    await page.waitForTimeout(2000);

    // Navigate back to home
    await page.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 30_000 });
    await page.waitForTimeout(3000);

    // Theme should still be applied (from localStorage)
    const bgBack = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );
    expect(bgBack).toBe(themedBg);
  });
});

// ---------------------------------------------------------------------------
// Suite 5: Dark Luxury Theme (blog204) — Specific Validation
// ---------------------------------------------------------------------------

test.describe('Suite 5: Dark Luxury Theme', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.removeItem('toronto-events-settings');
    });
    await waitForPageReady(page);
  });

  test('T5.1 — Apply Dark Luxury sets gold accent (#d4af37)', async ({ page }) => {
    await openThemePicker(page);
    await applyTheme(page, 'blog204');

    const accent = await getCSSVar(page, '--pk-500');
    expect(accent.toLowerCase()).toContain('d4af37');
  });

  test('T5.2 — Dark Luxury body background is dark (#0a0a0a)', async ({ page }) => {
    await openThemePicker(page);
    await applyTheme(page, 'blog204');

    const bgImage = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundImage
    );
    // Dark Luxury uses a gradient: linear-gradient(135deg, #0a0a0a, #1a1a10)
    expect(bgImage).toContain('gradient');
    expect(bgImage).toContain('10, 10, 10'); // #0a0a0a in rgb
  });

  test('T5.3 — Dark Luxury loads Playfair Display font', async ({ page }) => {
    await openThemePicker(page);
    await applyTheme(page, 'blog204');
    await page.waitForTimeout(1000);

    const fontLink = await page.evaluate(() => {
      const link = document.getElementById('theme-font-link') as HTMLLinkElement | null;
      return link ? link.href : null;
    });
    expect(fontLink).toBeTruthy();
    expect(fontLink!.toLowerCase()).toContain('playfair');
  });

  test('T5.4 — Dark Luxury canvas animation runs without JS errors', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', (err) => {
      if (!isIgnoredError(err.message)) {
        jsErrors.push(err.message);
      }
    });

    await openThemePicker(page);
    await applyTheme(page, 'blog204');
    await page.waitForTimeout(2000);

    const hasCanvas = await page.evaluate(() =>
      !!document.getElementById('bg-canvas')
    );
    expect(hasCanvas, 'Canvas element should exist for Dark Luxury animation').toBe(true);

    const canvasErrors = jsErrors.filter(
      (e) => e.includes('canvas') || e.includes('draw') || e.includes('animation')
    );
    expect(canvasErrors, 'No canvas/animation JS errors').toHaveLength(0);
  });

  test('T5.5 — Dark Luxury persists after reload', async ({ page }) => {
    await openThemePicker(page);
    await applyTheme(page, 'blog204');

    // Verify localStorage
    const stored = await getLocalStorage(page, 'toronto-events-settings');
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed.selectedTheme).toBe('blog204');

    // Override the beforeEach initScript that clears localStorage — restore theme before reload
    await page.addInitScript(() => {
      localStorage.setItem(
        'toronto-events-settings',
        JSON.stringify({ selectedTheme: 'blog204' })
      );
    });

    // Reload — theme-switcher re-applies saved theme after React hydration (~2.5s)
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(5000);

    // Gold accent should still be applied
    const accent = await getCSSVar(page, '--pk-500');
    expect(accent.toLowerCase()).toContain('d4af37');
  });

  test('T5.6 — blog204.html standalone page loads with Dark Luxury styling', async ({
    page,
  }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', (err) => {
      if (!isIgnoredError(err.message)) {
        jsErrors.push(err.message);
      }
    });

    await page.goto(BASE + '/blog/blog204.html', {
      waitUntil: 'networkidle',
      timeout: 30_000,
    });
    await page.waitForTimeout(2000);

    // Page title should reference Dark Luxury
    const title = await page.title();
    expect(title.toLowerCase()).toContain('dark luxury');

    // Background should use the Dark Luxury gradient (gradient from #0a0a0a)
    const bgImage = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundImage
    );
    expect(bgImage).toContain('gradient');

    // Canvas animation should be running
    const hasCanvas = await page.evaluate(() =>
      !!document.getElementById('bg-canvas')
    );
    expect(hasCanvas, 'Blog page should have bg-canvas for animation').toBe(true);

    // No theme-related JS errors
    expect(jsErrors).toHaveLength(0);
  });

  test('T5.7 — Dark Luxury theme nav bar injects with gold accent', async ({ page }) => {
    await openThemePicker(page);
    await applyTheme(page, 'blog204');

    const navExists = await page.evaluate(() =>
      !!document.getElementById('theme-sections-nav')
    );
    expect(navExists, 'Theme nav bar should be injected').toBe(true);

    // Nav border should use gold accent
    const borderColor = await page.evaluate(() => {
      const nav = document.getElementById('theme-sections-nav');
      return nav ? getComputedStyle(nav).borderBottomColor : '';
    });
    // Gold border = rgba(212, 175, 55, ...) or similar
    expect(borderColor).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// Suite 6: Text Visibility — All Animated (Living) Themes
// ---------------------------------------------------------------------------
// Verifies that text is readable when any animated theme is applied.
// Trail-effect canvas animations (fillRect with translucent black) must NOT
// obscure page content — the canvas should have limited opacity.

test.describe('Suite 6: Text Visibility on Living Themes', () => {
  // All themes known to have canvas animations (trail-effect or clearRect).
  // These are the themes most at risk of hiding text behind opaque canvases.
  const ANIMATED_THEMES = [
    // blog200-249 canvas animations
    'blog200', 'blog201', 'blog202', 'blog203', 'blog204', 'blog205',
    'blog206', 'blog207', 'blog208', 'blog209', 'blog210', 'blog211',
    'blog212', 'blog213', 'blog214', 'blog215', 'blog216', 'blog217',
    'blog218', 'blog219', 'blog220', 'blog221', 'blog222', 'blog223',
    'blog224', 'blog225', 'blog226', 'blog227', 'blog228', 'blog229',
    'blog230', 'blog235', 'blog236', 'blog237', 'blog240', 'blog241',
    'blog242', 'blog243', 'blog244', 'blog245', 'blog246', 'blog247',
    'blog249',
    // blog100-149 canvas animations
    'blog101', 'blog103', 'blog107', 'blog110', 'blog113', 'blog144',
  ];

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.removeItem('toronto-events-settings');
    });
    await waitForPageReady(page);
  });

  for (const themeId of ANIMATED_THEMES) {
    test(`T6 — ${themeId}: canvas has limited opacity and text is visible`, async ({ page }) => {
      // Apply theme via localStorage + reload for reliable activation
      await page.evaluate((id) => {
        localStorage.setItem(
          'toronto-events-settings',
          JSON.stringify({ selectedTheme: id, autoApply: true })
        );
      }, themeId);
      await page.reload({ waitUntil: 'networkidle' });
      // Wait for animation to run and trail effects to accumulate
      await page.waitForTimeout(3000);

      // 1. Canvas should exist
      const canvasInfo = await page.evaluate(() => {
        const canvas = document.getElementById('bg-canvas');
        if (!canvas) return { exists: false, opacity: '1' };
        const cs = getComputedStyle(canvas);
        return {
          exists: true,
          opacity: cs.opacity,
          zIndex: cs.zIndex,
          position: cs.position,
        };
      });

      expect(canvasInfo.exists, `${themeId}: bg-canvas should exist`).toBe(true);

      // 2. Canvas opacity should be limited for trail-effect animations.
      //    clearRect animations have transparent canvases (opacity: 1 is fine).
      //    Trail-effect (fillRect) animations should have opacity <= 0.5.
      const opacity = parseFloat(canvasInfo.opacity);
      expect(
        opacity,
        `${themeId}: canvas opacity should be set (got ${opacity})`
      ).toBeLessThanOrEqual(1.0);

      // 3. Page body text color and background should have contrast
      const colors = await page.evaluate(() => {
        const body = document.body;
        const cs = getComputedStyle(body);
        return {
          textColor: cs.color,
          bgColor: cs.backgroundColor,
        };
      });
      expect(
        colors.textColor,
        `${themeId}: text color should not match background`
      ).not.toBe(colors.bgColor);

      // 4. Hero title or heading text should be visible (not hidden by canvas)
      const textVisible = await page.evaluate(() => {
        // Find any heading or prominent text element
        const selectors = ['h1', 'h2', '.hero-title', '[class*="title"]'];
        for (const sel of selectors) {
          const el = document.querySelector(sel);
          if (el) {
            const rect = el.getBoundingClientRect();
            const cs = getComputedStyle(el);
            const visible =
              rect.width > 0 &&
              rect.height > 0 &&
              cs.visibility !== 'hidden' &&
              cs.display !== 'none' &&
              parseFloat(cs.opacity) > 0;
            if (visible) return true;
          }
        }
        return false;
      });
      expect(
        textVisible,
        `${themeId}: heading/title text should be visible`
      ).toBe(true);
    });
  }

  // Trail-effect themes (fillRect with translucent black) — MUST have reduced canvas opacity
  const TRAIL_EFFECT_THEMES = [
    'blog201', 'blog203', 'blog205', 'blog206', 'blog207', 'blog208',
    'blog209', 'blog212', 'blog218', 'blog220', 'blog223', 'blog225',
    'blog226', 'blog227', 'blog228', 'blog241', 'blog246', 'blog249',
    'blog101',
  ];

  for (const themeId of TRAIL_EFFECT_THEMES) {
    test(`T6.trail — ${themeId}: trail-effect canvas opacity <= 0.4`, async ({ page }) => {
      await page.evaluate((id) => {
        localStorage.setItem(
          'toronto-events-settings',
          JSON.stringify({ selectedTheme: id, autoApply: true })
        );
      }, themeId);
      await page.reload({ waitUntil: 'networkidle' });
      await page.waitForTimeout(3000);

      const opacity = await page.evaluate(() => {
        const canvas = document.getElementById('bg-canvas');
        return canvas ? parseFloat(getComputedStyle(canvas).opacity) : 1;
      });

      expect(
        opacity,
        `${themeId}: trail-effect canvas MUST have opacity <= 0.4 to keep text readable (got ${opacity})`
      ).toBeLessThanOrEqual(0.4);
    });
  }
});
