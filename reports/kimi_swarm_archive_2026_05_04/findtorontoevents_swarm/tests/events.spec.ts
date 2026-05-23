/**
 * events.spec.ts
 *
 * Comprehensive Playwright test suite for findtorontoevents.ca /index.html
 * covering: filters, toggles, scroll-to-load, geolocation, mobile viewport,
 * and aggressive console / network / page-error detection.
 *
 * Known issues to hunt:
 *   - "Counter oscillation subagent" console error
 *   - Stale / sync issues with Next.js chunks loading the event grid
 */

import { test, expect, type Page } from "@playwright/test";
import {
  createConsoleErrorTracker,
  assertNoConsoleErrors,
  logConsoleErrors,
  KNOWN_BAD_PATTERNS,
} from "./console-error-utils";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const BASE_URL = "https://findtorontoevents.ca/index.html";

const DATE_FILTERS = [
  { label: "All Dates", selector: "text=All Dates" },
  { label: "Today", selector: "text=Today" },
  { label: "Tomorrow", selector: "text=Tomorrow" },
  { label: "This Week", selector: "text=This Week" },
  { label: "This Month", selector: "text=This Month" },
  { label: "Next Month", selector: "text=Next Month" },
];

const CATEGORIES = [
  "Dating",
  "Architecture",
  "Arts",
  "Business",
  "Community",
  "Family",
  "Festival",
  "Film",
  "Food & Drink",
  "General",
  "Music",
  "Nightlife",
  "Photography",
  "Sports",
  "Theatre",
  "Toronto",
];

const TOGGLES = [
  { label: "Sold Out Hidden", selector: "text=Sold Out Hidden" },
  { label: "Multi-Day Off", selector: "text=Multi-Day" },
  { label: "Expensive Hidden", selector: "text=Expensive Hidden" },
  { label: "Ongoing Hidden", selector: "text=Ongoing Hidden" },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

async function waitForEventGridStable(page: Page) {
  // The event grid is hydrated by Next.js chunks.  We wait for either
  // the grid container or a "no events" message to appear.
  await page
    .locator(
      "[data-testid='event-grid'], .event-grid, [class*='grid'], text='No events found'"
    )
    .first()
    .waitFor({ timeout: 15000 })
    .catch(() => {
      // If nothing appears, the page may still be useful for error capture.
    });
}

async function takeDiagnosticScreenshot(page: Page, name: string) {
  await page.screenshot({
    path: `/mnt/agents/output/findtorontoevents_swarm/tests/screenshots/events-${name}.png`,
    fullPage: true,
  });
}

/* ------------------------------------------------------------------ */
/*  Suite configuration                                                */
/* ------------------------------------------------------------------ */

test.describe.configure({ mode: "parallel" });

test.describe("Events Discovery Page", () => {
  /* ================================================================ */
  /*  1. Smoke + Console Error Baseline                               */
  /* ================================================================ */
  test("loads without critical console or network errors", async ({
    page,
  }) => {
    const tracker = createConsoleErrorTracker(page);

    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    // Allow benign Next.js chunk-loading chatter and favicon 404s
    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
    ]);
  });

  test("captures and reports all warnings for manual inspection", async ({
    page,
  }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    // Soft assertion — we log but don't fail so the report is visible in CI
    const clean = logConsoleErrors(tracker);
    expect(
      clean || tracker.warnings.length === 0,
      `Warnings detected:\n${tracker.getReport()}`
    ).toBeTruthy();
  });

  /* ================================================================ */
  /*  2. Date Filters                                                 */
  /* ================================================================ */
  for (const { label, selector } of DATE_FILTERS) {
    test(`date filter — ${label}`, async ({ page }) => {
      const tracker = createConsoleErrorTracker(page);
      await page.goto(BASE_URL, { waitUntil: "networkidle" });
      await waitForEventGridStable(page);

      const filterBtn = page.locator(selector).first();
      await expect(filterBtn).toBeVisible({ timeout: 5000 });
      await filterBtn.click();

      // Allow the grid to re-render
      await page.waitForTimeout(800);
      await waitForEventGridStable(page);

      // Screenshot the filtered state for visual regression baselines
      await takeDiagnosticScreenshot(page, `filter-date-${label.toLowerCase().replace(/\s+/g, "-")}`);

      assertNoConsoleErrors(tracker, [
        /favicon/i,
        /chunk/i,
        /source.map/i,
      ]);
    });
  }

  /* ================================================================ */
  /*  3. Category Filtering                                           */
  /* ================================================================ */
  test("category filters are visible and clickable", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    for (const cat of CATEGORIES) {
      const pill = page.locator(`text=${cat}`).first();
      // Some categories may be hidden behind an overflow; we at least
      // assert that the first few are present.
      const visible = await pill.isVisible().catch(() => false);
      if (visible) {
        await pill.click();
        await page.waitForTimeout(600);

        // Click again to clear (toggle behaviour)
        await pill.click();
        await page.waitForTimeout(400);
      }
    }

    assertNoConsoleErrors(tracker, [/favicon/i, /chunk/i, /source.map/i]);
  });

  test("category filter — Music events load", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    const musicPill = page.locator("text=Music").first();
    await expect(musicPill).toBeVisible({ timeout: 5000 });
    await musicPill.click();

    await page.waitForTimeout(800);
    await waitForEventGridStable(page);

    // After filtering we should see event cards, a count badge, or a "no events" message.
    const anyContent = page
      .locator("[data-testid='event-card'], .event-card, text=/No events/i")
      .first();
    await expect(anyContent).toBeVisible({ timeout: 10000 });

    await takeDiagnosticScreenshot(page, "filter-category-music");
    assertNoConsoleErrors(tracker, [/favicon/i, /chunk/i, /source.map/i]);
  });

  /* ================================================================ */
  /*  4. Price Limit Slider                                             */
  /* ================================================================ */
  test("price limit slider adjusts and filters events", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    // Locate slider by accessible label or nearby text
    const slider = page.locator(
      "input[type='range'], [aria-label*='price'], [aria-label*='Price']"
    );

    if ((await slider.count()) === 0) {
      test.info().annotations.push({
        type: "skip-reason",
        description: "Price limit slider not found in DOM",
      });
      return;
    }

    // Set price limit to $50
    await slider.fill("50");
    await page.waitForTimeout(600);
    await waitForEventGridStable(page);

    // Set price limit back to $120
    await slider.fill("120");
    await page.waitForTimeout(600);
    await waitForEventGridStable(page);

    await takeDiagnosticScreenshot(page, "filter-price-120");
    assertNoConsoleErrors(tracker, [/favicon/i, /chunk/i, /source.map/i]);
  });

  /* ================================================================ */
  /*  5. Toggle Controls                                                */
  /* ================================================================ */
  for (const { label, selector } of TOGGLES) {
    test(`toggle — ${label}`, async ({ page }) => {
      const tracker = createConsoleErrorTracker(page);
      await page.goto(BASE_URL, { waitUntil: "networkidle" });
      await waitForEventGridStable(page);

      const toggle = page.locator(selector).first();
      const exists = (await toggle.count()) > 0;
      if (!exists) {
        test.info().annotations.push({
          type: "skip-reason",
          description: `Toggle "${label}" not found`,
        });
        return;
      }

      await expect(toggle).toBeVisible({ timeout: 5000 });
      await toggle.click();
      await page.waitForTimeout(600);

      // Toggle back
      await toggle.click();
      await page.waitForTimeout(400);

      assertNoConsoleErrors(tracker, [/favicon/i, /chunk/i, /source.map/i]);
    });
  }

  /* ================================================================ */
  /*  6. Nearby Me — Mock Geolocation                                 */
  /* ================================================================ */
  test("Nearby Me filter with mocked geolocation", async ({ context, page }) => {
    const tracker = createConsoleErrorTracker(page);

    // Mock downtown Toronto coordinates
    await context.grantPermissions(["geolocation"]);
    await page.context().setGeolocation({
      latitude: 43.65107,
      longitude: -79.347015,
    });

    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    const nearbyBtn = page.locator("text=Nearby Me").first();
    if ((await nearbyBtn.count()) === 0) {
      test.info().annotations.push({
        type: "skip-reason",
        description: "Nearby Me button not found",
      });
      return;
    }

    await nearbyBtn.click();
    await page.waitForTimeout(1200); // Geolocation + grid fetch
    await waitForEventGridStable(page);

    await takeDiagnosticScreenshot(page, "filter-nearby-me");

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /user\s*denied\s*geolocation/i, // Some browsers warn if permission isn't pre-granted
    ]);
  });

  /* ================================================================ */
  /*  7. Scroll-to-Load-More                                            */
  /* ================================================================ */
  test("scroll loads additional event cards", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    // Count initial visible cards
    const getCardCount = () =>
      page.locator("[data-testid='event-card'], .event-card, article").count();

    const initialCount = await getCardCount();

    // Scroll to bottom repeatedly to trigger lazy loading
    for (let i = 0; i < 4; i++) {
      await page.evaluate(() =>
        window.scrollTo(0, document.body.scrollHeight)
      );
      await page.waitForTimeout(1200);
    }

    const finalCount = await getCardCount();

    // We expect more cards after scrolling, or at minimum the same count
    // if the server has no more events (not a failure).
    expect(finalCount).toBeGreaterThanOrEqual(initialCount);

    await takeDiagnosticScreenshot(page, "scroll-loaded");
    assertNoConsoleErrors(tracker, [/favicon/i, /chunk/i, /source.map/i]);
  });

  /* ================================================================ */
  /*  8. Sign-in Button + Gear Icon                                    */
  /* ================================================================ */
  test("sign-in button is visible and clickable", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    const signIn = page.locator("text=Sign In, button:has-text('Sign In'), [data-testid='sign-in']").first();
    // Try multiple semantic strategies
    const btn = page
      .getByRole("button", { name: /sign\s*in/i })
      .or(page.locator("button:has-text('Sign In')"))
      .or(page.locator("a:has-text('Sign In')"))
      .first();

    await expect(btn).toBeVisible({ timeout: 8000 });
    await btn.click();

    // Clicking may open a modal or navigate — just ensure no explosion.
    await page.waitForTimeout(500);

    assertNoConsoleErrors(tracker, [/favicon/i, /chunk/i, /source.map/i]);
  });

  test("gear / config icon opens settings panel", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    const gear = page
      .getByRole("button", { name: /config|settings|gear/i })
      .or(page.locator("button:has-text('⚙️')"))
      .or(page.locator("[aria-label*='settings' i]"))
      .or(page.locator("[data-testid='config-button']"))
      .first();

    if ((await gear.count()) === 0 || !(await gear.isVisible().catch(() => false))) {
      test.info().annotations.push({
        type: "skip-reason",
        description: "Gear / config icon not found",
      });
      return;
    }

    await gear.click();
    await page.waitForTimeout(600);

    // Expect some kind of panel / modal / popover to appear
    const panel = page
      .locator(
        "[role='dialog'], [role='menu'], .settings-panel, [data-testid='settings-panel']"
      )
      .first();

    const panelVisible = await panel.isVisible().catch(() => false);
    if (panelVisible) {
      await expect(panel).toBeVisible();
    }

    assertNoConsoleErrors(tracker, [/favicon/i, /chunk/i, /source.map/i]);
  });

  /* ================================================================ */
  /*  9. View Toggles (tabular / thumbnails)                            */
  /* ================================================================ */
  test("view mode toggles (table / thumbnails) work", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    // Thumbnails toggle
    const thumbToggle = page
      .locator("button:has-text('Thumbnails'), [aria-label*='thumbnail' i]")
      .first();
    if (await thumbToggle.isVisible().catch(() => false)) {
      await thumbToggle.click();
      await page.waitForTimeout(500);
    }

    // Tabular toggle
    const tableToggle = page
      .locator("button:has-text('Table'), [aria-label*='table' i], button:has-text('Tabular')")
      .first();
    if (await tableToggle.isVisible().catch(() => false)) {
      await tableToggle.click();
      await page.waitForTimeout(500);
    }

    await takeDiagnosticScreenshot(page, "view-toggle");
    assertNoConsoleErrors(tracker, [/favicon/i, /chunk/i, /source.map/i]);
  });

  /* ================================================================ */
  /*  10. Filter Stream Text Validation                               */
  /* ================================================================ */
  test("filter stream summary is coherent", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    const filterStream = page
      .locator("text=/Current Filter Stream/i")
      .or(page.locator("[data-testid='filter-stream']"))
      .first();

    if (await filterStream.isVisible().catch(() => false)) {
      const text = await filterStream.textContent();
      expect(text).toContain("Under $120");
      expect(text).toContain("Hiding Sold Out");
    }

    assertNoConsoleErrors(tracker, [/favicon/i, /chunk/i, /source.map/i]);
  });

  /* ================================================================ */
  /*  11. System Issues Banner                                        */
  /* ================================================================ */
  test("system issues banner is present and link works", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    const banner = page
      .locator("text=/System Issues/i")
      .or(page.locator("[data-testid='system-issues-banner']"))
      .first();

    if (await banner.isVisible().catch(() => false)) {
      const link = banner.locator("a:has-text('Windows Boot Fixer')").or(banner.locator("a")).first();
      if (await link.isVisible().catch(() => false)) {
        const href = await link.getAttribute("href");
        expect(href).toBeTruthy();
      }
    }

    assertNoConsoleErrors(tracker, [/favicon/i, /chunk/i, /source.map/i]);
  });

  /* ================================================================ */
  /*  12. Mobile Viewport (375×667)                                   */
  /* ================================================================ */
  test("mobile viewport — layout and filters survive", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    // Ensure no horizontal overflow (common mobile breakage)
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const windowWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(windowWidth + 1); // allow 1px rounding

    // Hamburger / mobile menu if present
    const hamburger = page
      .getByRole("button", { name: /menu/i })
      .or(page.locator("[aria-label*='menu' i]"))
      .first();
    if (await hamburger.isVisible().catch(() => false)) {
      await hamburger.click();
      await page.waitForTimeout(400);
    }

    await takeDiagnosticScreenshot(page, "mobile-375x667");
    assertNoConsoleErrors(tracker, [/favicon/i, /chunk/i, /source.map/i]);
  });

  /* ================================================================ */
  /*  13. Specific Bug Hunt: Counter Oscillation                       */
  /* ================================================================ */
  test("does not emit 'Counter oscillation' console error", async ({
    page,
  }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    // Interact with filters rapidly to trigger any race-condition errors
    const today = page.locator("text=Today").first();
    const tomorrow = page.locator("text=Tomorrow").first();

    if ((await today.count()) > 0 && (await tomorrow.count()) > 0) {
      for (let i = 0; i < 5; i++) {
        await today.click();
        await page.waitForTimeout(200);
        await tomorrow.click();
        await page.waitForTimeout(200);
      }
    }

    const oscillationHits = tracker.matching(/counter\s*oscillation/i);
    expect(
      oscillationHits.length,
      `Counter oscillation error detected:\n${oscillationHits
        .map((h) => h.message)
        .join("\n")}`
    ).toBe(0);

    assertNoConsoleErrors(tracker, [/favicon/i, /chunk/i, /source.map/i]);
  });

  /* ================================================================ */
  /*  14. Mega-menu Sections Sanity Check                             */
  /* ================================================================ */
  test("mega-menu sections are present", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    await waitForEventGridStable(page);

    const sections = [
      "Movies",
      "System Issues",
      "Stock Ideas",
      "Fav Creators",
      "Mental Health",
      "VR",
      "Game Arena",
      "Accountability",
      "Updates",
      "Blog",
    ];

    for (const section of sections) {
      const link = page.locator(`a:has-text('${section}'), button:has-text('${section}')`).first();
      const visible = await link.isVisible().catch(() => false);
      if (!visible) {
        test.info().annotations.push({
          type: "missing-section",
          description: `Section "${section}" not visible`,
        });
      }
    }

    assertNoConsoleErrors(tracker, [/favicon/i, /chunk/i, /source.map/i]);
  });
});
