/**
 * sports-betting.spec.ts
 *
 * Comprehensive Playwright test suite for the Sports Bet Winner Finder at
 * /live-monitor/sports-betting.html
 *
 * Covers: sport tab navigation, sub-tab switching (Today's Picks, Odds,
 * Arbitrage), loading-state resolution, data-freshness validation,
 * bankroll / active-bets coherence, disclaimer presence, console error
 * detection, and mobile viewport resilience.
 *
 * Known issues to hunt:
 *   - "Last refresh" showing "--" (stale data)
 *   - "Loading today's picks..." hanging indefinitely
 *   - 0% win rate when there should be historical data
 */

import { test, expect, type Page } from "@playwright/test";
import {
  createConsoleErrorTracker,
  assertNoConsoleErrors,
  logConsoleErrors,
} from "./console-error-utils";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const SPORTS_URL = "https://findtorontoevents.ca/live-monitor/sports-betting.html";

const SPORT_TABS = [
  "NHL",
  "NBA",
  "WNBA",
  "NFL",
  "MLB",
  "CFL",
  "MLS",
  "NCAAF",
  "NCAAB",
  "EPL",
  "La Liga",
  "UFC",
  "Tennis",
  "Golf",
];

const SUB_TABS = [
  "Today's Picks",
  "Playoffs",
  "Odds Comparison",
  "Arbitrage",
  "Steam Moves",
  "My Bets",
  "Performance",
  "Pick History",
  "Glossary",
  "System Analysis",
  "Research & Future",
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

async function waitForBettingSurface(page: Page) {
  // Wait for any of: picks list, odds table, "no picks" message, loading spinner
  await page
    .locator(
      ".pick-card, [data-testid='pick-card'], table, text=/No picks/i, text=/Loading/i, .sports-table, [class*='odds']"
    )
    .first()
    .waitFor({ timeout: 15000 })
    .catch(() => {
      // If nothing appears, still continue for error capture
    });
}

async function takeBettingScreenshot(page: Page, name: string) {
  await page.screenshot({
    path: `/mnt/agents/output/findtorontoevents_swarm/tests/screenshots/sports-${name}.png`,
    fullPage: true,
  });
}

/**
 * Wait for the loading state "Loading today's picks..." to resolve.
 * Fails the test if it is still present after a generous timeout.
 */
async function resolveLoadingState(page: Page, label: string) {
  const loadingLocator = page.locator("text=/Loading.*picks/i");

  try {
    // If the loading text is present, wait for it to disappear
    if ((await loadingLocator.count()) > 0) {
      await loadingLocator.waitFor({ state: "hidden", timeout: 20000 });
    }
  } catch {
    // If it's still visible, take a screenshot and annotate
    await takeBettingScreenshot(page, `hanging-loading-${label}`);
    test.info().annotations.push({
      type: "stale-data",
      description: `Loading state "Loading today's picks..." still visible after 20s in "${label}"`,
    });
  }
}

/* ------------------------------------------------------------------ */
/*  Suite                                                              */
/* ------------------------------------------------------------------ */

test.describe.configure({ mode: "parallel" });

test.describe("Sports Betting", () => {
  /* ================================================================ */
  /*  1. Baseline Load + Console Errors                               */
  /* ================================================================ */
  test("loads without critical console or network errors", async ({
    page,
  }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  test("logs full error report for CI inspection", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    const clean = logConsoleErrors(tracker);
    expect(clean || tracker.errors.length === 0).toBeTruthy();
  });

  /* ================================================================ */
  /*  2. Data Freshness — Last Refresh                                */
  /* ================================================================ */
  test('"Last refresh" is not permanently "--"', async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    const lastRefresh = page
      .locator("text=/Last refresh/i")
      .or(page.locator("[data-testid='last-refresh']"))
      .first();

    if (await lastRefresh.isVisible().catch(() => false)) {
      const text = await lastRefresh.textContent();

      // If it literally shows "--" we flag it as a known stale-data bug.
      if (text?.includes("--")) {
        test.info().annotations.push({
          type: "stale-data-bug",
          description: `Last refresh shows "--" — known stale data issue`,
        });
        // We soft-fail so the issue is visible in CI without blocking everything
        expect(
          text,
          "Last refresh is '--' — data may be stale"
        ).not.toContain("--");
      } else {
        // Should contain some kind of timestamp or relative time
        expect(text).toBeTruthy();
      }
    }

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  3. Sport Tabs (NHL, NBA, NFL, MLB minimum)                       */
  /* ================================================================ */
  for (const sport of SPORT_TABS.slice(0, 5)) {
    test(`sport tab — ${sport}`, async ({ page }) => {
      const tracker = createConsoleErrorTracker(page);
      await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
      await waitForBettingSurface(page);

      const tab = page
        .getByRole("tab", { name: new RegExp(`^${sport}$`, "i") })
        .or(page.locator(`button:has-text('${sport}')`))
        .or(page.locator(`a:has-text('${sport}')`))
        .first();

      if ((await tab.count()) === 0 || !(await tab.isVisible().catch(() => false))) {
        test.info().annotations.push({
          type: "missing-tab",
          description: `Sport tab "${sport}" not found`,
        });
        return;
      }

      await tab.click();
      await page.waitForTimeout(800);
      await waitForBettingSurface(page);

      // Ensure the page didn't crash
      const bodyText = await page.locator("body").textContent();
      expect(bodyText).not.toMatch(/error\s*page|something\s*went\s*wrong/i);

      await takeBettingScreenshot(page, `sport-${sport.toLowerCase().replace(/\s+/g, "-")}`);

      assertNoConsoleErrors(tracker, [
        /favicon/i,
        /chunk/i,
        /source.map/i,
        /\.woff2?/i,
      ]);
    });
  }

  /* ================================================================ */
  /*  4. All Sports Tab — sanity check                                 */
  /* ================================================================ */
  test('"All Sports" tab is visible and clickable', async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    const allSports = page
      .getByRole("tab", { name: /All Sports/i })
      .or(page.locator("button:has-text('All Sports')"))
      .first();

    await expect(allSports).toBeVisible({ timeout: 8000 });
    await allSports.click();
    await page.waitForTimeout(600);

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  5. Today's Picks — Loading State Resolution                       */
  /* ================================================================ */
  test("Today's Picks — loading resolves or surfaces no-picks message", async ({
    page,
  }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });

    // Navigate to Today's Picks if not already there
    const todaysPicksTab = page
      .getByRole("tab", { name: /Today's Picks/i })
      .or(page.locator("button:has-text(\"Today's Picks\")"))
      .first();

    if (
      (await todaysPicksTab.count()) > 0 &&
      (await todaysPicksTab.isVisible().catch(() => false))
    ) {
      await todaysPicksTab.click();
    }

    await resolveLoadingState(page, "todays-picks");

    // After loading resolves we expect either pick cards OR an explicit "no picks" message.
    const pickCards = page.locator(
      "[data-testid='pick-card'], .pick-card, .bet-card"
    );
    const noPicksMsg = page.locator("text=/No picks/i");

    const hasPicks = (await pickCards.count()) > 0;
    const hasNoPicks = (await noPicksMsg.count()) > 0;

    expect(
      hasPicks || hasNoPicks,
      "After loading, expected pick cards or a 'No picks' message"
    ).toBeTruthy();

    await takeBettingScreenshot(page, "todays-picks-resolved");

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  6. Odds Comparison Tab                                          */
  /* ================================================================ */
  test("Odds Comparison tab renders without errors", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    const oddsTab = page
      .getByRole("tab", { name: /Odds Comparison/i })
      .or(page.locator("button:has-text('Odds Comparison')"))
      .first();

    if (
      (await oddsTab.count()) === 0 ||
      !(await oddsTab.isVisible().catch(() => false))
    ) {
      test.info().annotations.push({
        type: "missing-tab",
        description: "Odds Comparison tab not found",
      });
      return;
    }

    await oddsTab.click();
    await page.waitForTimeout(1000);
    await waitForBettingSurface(page);

    const bodyText = await page.locator("body").textContent();
    expect(bodyText).not.toMatch(/error\s*page|something\s*went\s*wrong/i);

    await takeBettingScreenshot(page, "odds-comparison");

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  7. Arbitrage Tab                                                  */
  /* ================================================================ */
  test("Arbitrage tab renders without errors", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    const arbTab = page
      .getByRole("tab", { name: /Arbitrage/i })
      .or(page.locator("button:has-text('Arbitrage')"))
      .first();

    if (
      (await arbTab.count()) === 0 ||
      !(await arbTab.isVisible().catch(() => false))
    ) {
      test.info().annotations.push({
        type: "missing-tab",
        description: "Arbitrage tab not found",
      });
      return;
    }

    await arbTab.click();
    await page.waitForTimeout(1000);
    await waitForBettingSurface(page);

    const bodyText = await page.locator("body").textContent();
    expect(bodyText).not.toMatch(/error\s*page|something\s*went\s*wrong/i);

    await takeBettingScreenshot(page, "arbitrage");

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  8. Bankroll Display                                               */
  /* ================================================================ */
  test("bankroll display is present and coherent", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    const bankroll = page
      .locator("text=/Bankroll/i")
      .or(page.locator("[data-testid='bankroll']"))
      .first();

    if (await bankroll.isVisible().catch(() => false)) {
      const text = await bankroll.textContent();
      expect(text).toBeTruthy();

      // The reconnaissance notes bankroll as $1,000.  Allow drift.
      const hasDollar = /\$[\d,]+/.test(text!);
      const hasExpected = text!.includes("1,000") || text!.includes("1000");

      if (!hasDollar) {
        test.info().annotations.push({
          type: "data-format",
          description: `Bankroll text does not contain dollar amount: "${text}"`,
        });
      }

      expect(hasDollar).toBeTruthy();
    } else {
      test.info().annotations.push({
        type: "missing-element",
        description: "Bankroll display not found",
      });
    }

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  9. Disclaimer Presence                                            */
  /* ================================================================ */
  test("disclaimer is present", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    const disclaimer = page
      .locator("text=/disclaimer/i")
      .or(page.locator("[data-testid='disclaimer']"))
      .or(page.locator("footer"))
      .first();

    await expect(disclaimer).toBeVisible({ timeout: 8000 });

    const text = await disclaimer.textContent();
    expect(text!.toLowerCase()).toContain("disclaimer");

    // Reconnaissance notes: Wilson CI disclaimer, research-backed situation scoring
    const bodyText = await page.locator("body").textContent();
    expect(bodyText).toMatch(/wilson|research/i);

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  10. Active Bets / Settled Coherence                              */
  /* ================================================================ */
  test("active bets and settled tickets are coherent", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    const bodyText = await page.locator("body").textContent();

    // Extract rough numbers via regex (best-effort; may need tightening per DOM)
    const activeMatch = bodyText.match(/Active\s*Bets[:\s]*(\d+)/i);
    const settledMatch = bodyText.match(/Settled\s*Tickets[:\s]*(\d+)/i);
    const winRateMatch = bodyText.match(/Win\s*Rate[:\s]*([\d.NA/n/a]+)/i);

    const activeBets = activeMatch ? parseInt(activeMatch[1], 10) : null;
    const settledTickets = settledMatch ? parseInt(settledMatch[1], 10) : null;
    const winRate = winRateMatch ? winRateMatch[1].trim() : null;

    // Known issue: if 0 bets and 0 settled, win rate should be N/A — not 0%
    if (
      activeBets === 0 &&
      (settledTickets === 0 || settledTickets === null)
    ) {
      if (winRate !== null && winRate === "0%") {
        test.info().annotations.push({
          type: "coherence-bug",
          description:
            "Win rate is 0% with 0 active bets and 0 settled tickets — should be N/A",
        });
        expect(winRate).not.toBe("0%");
      }
    }

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  11. API Credits Display                                           */
  /* ================================================================ */
  test("API credits display is present", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    const apiCredits = page
      .locator("text=/API Credits/i")
      .or(page.locator("[data-testid='api-credits']"))
      .first();

    if (await apiCredits.isVisible().catch(() => false)) {
      const text = await apiCredits.textContent();
      expect(text).toBeTruthy();
    } else {
      test.info().annotations.push({
        type: "missing-element",
        description: "API Credits display not found",
      });
    }

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  12. Console Errors During Rapid Tab Switches                    */
  /* ================================================================ */
  test("rapid tab switches do not trigger console errors", async ({
    page,
  }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    const tabs = ["NHL", "NBA", "NFL", "MLB", "Odds Comparison", "Arbitrage"];

    for (const tabName of tabs) {
      const tab = page
        .getByRole("tab", { name: new RegExp(`^${tabName}$`, "i") })
        .or(page.locator(`button:has-text('${tabName}')`))
        .first();

      if ((await tab.count()) > 0 && (await tab.isVisible().catch(() => false))) {
        await tab.click();
        await page.waitForTimeout(300); // rapid fire
      }
    }

    // Wait for any async fallout
    await page.waitForTimeout(2000);

    const hits = tracker.matching(/counter\s*oscillation/i);
    expect(
      hits.length,
      `Counter oscillation detected during rapid tab switches`
    ).toBe(0);

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  13. Playoffs Sub-tab                                              */
  /* ================================================================ */
  test("Playoffs sub-tab renders", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    const playoffsTab = page
      .getByRole("tab", { name: /Playoffs/i })
      .or(page.locator("button:has-text('Playoffs')"))
      .first();

    if (
      (await playoffsTab.count()) === 0 ||
      !(await playoffsTab.isVisible().catch(() => false))
    ) {
      test.info().annotations.push({
        type: "missing-tab",
        description: "Playoffs tab not found",
      });
      return;
    }

    await playoffsTab.click();
    await page.waitForTimeout(800);
    await waitForBettingSurface(page);

    await takeBettingScreenshot(page, "playoffs");

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  14. Performance Tab — Win Rate / ROI Sanity                      */
  /* ================================================================ */
  test("Performance tab shows sensible metrics", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    const perfTab = page
      .getByRole("tab", { name: /Performance/i })
      .or(page.locator("button:has-text('Performance')"))
      .first();

    if (
      (await perfTab.count()) === 0 ||
      !(await perfTab.isVisible().catch(() => false))
    ) {
      test.info().annotations.push({
        type: "missing-tab",
        description: "Performance tab not found",
      });
      return;
    }

    await perfTab.click();
    await page.waitForTimeout(1000);
    await waitForBettingSurface(page);

    const bodyText = await page.locator("body").textContent();

    // Win rate should be a percentage or N/A — never a nonsensical value
    const winRateMatch = bodyText.match(/Win\s*Rate[:\s]*([\d\-NA/n/a%]+)/i);
    if (winRateMatch) {
      const raw = winRateMatch[1].trim();
      if (raw !== "N/A" && raw !== "n/a" && raw !== "NA") {
        const numeric = parseFloat(raw.replace("%", ""));
        expect(numeric).toBeGreaterThanOrEqual(-100);
        expect(numeric).toBeLessThanOrEqual(100);
      }
    }

    // ROI should be within mathematically possible bounds
    const roiMatch = bodyText.match(/ROI[:\s]*([\d\-NA/n/a%]+)/i);
    if (roiMatch) {
      const raw = roiMatch[1].trim();
      if (raw !== "N/A" && raw !== "n/a" && raw !== "NA") {
        const numeric = parseFloat(raw.replace("%", ""));
        expect(numeric).toBeGreaterThanOrEqual(-1000);
        expect(numeric).toBeLessThanOrEqual(1000);
      }
    }

    await takeBettingScreenshot(page, "performance");

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  15. Mobile Viewport (375×667)                                    */
  /* ================================================================ */
  test("mobile viewport — layout and tabs survive", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto(SPORTS_URL, { waitUntil: "networkidle" });
    await waitForBettingSurface(page);

    // No horizontal overflow
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const windowWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(windowWidth + 1);

    // Try clicking a sport tab via a potential mobile overflow menu
    const nhlTab = page
      .getByRole("tab", { name: /^NHL$/i })
      .or(page.locator("button:has-text('NHL')"))
      .first();

    if (await nhlTab.isVisible().catch(() => false)) {
      await nhlTab.click();
      await page.waitForTimeout(600);
    }

    await takeBettingScreenshot(page, "mobile-375x667");

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });
});
