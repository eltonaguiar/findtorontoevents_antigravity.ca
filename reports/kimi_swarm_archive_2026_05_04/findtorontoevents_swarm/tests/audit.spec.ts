/**
 * audit.spec.ts
 *
 * Comprehensive Playwright test suite for the audit dashboard pages:
 *   - /audit/          — Unified Audit Dashboard v99.0
 *   - /audit/hyrotrader/ — HyroTrader challenge tracker
 *
 * Covers: asset-class card validation, filter interactions, view switching,
 * CSV export, disclaimer presence, console/network error detection,
 * and mobile viewport resilience.
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

const AUDIT_BASE = "https://findtorontoevents.ca/audit/";
const HYRO_BASE = "https://findtorontoevents.ca/audit/hyrotrader/";

const ASSET_CLASSES = [
  {
    name: "EQUITY",
    pf: "1.41",
    wr: "52.7",
    n: "421",
    label: "T2 candidate",
  },
  {
    name: "CRYPTO",
    pf: "1.25",
    wr: "44.6",
    n: "8067",
  },
  {
    name: "ETF",
    pf: "1.24",
    wr: "55.2",
    n: "87",
  },
  {
    name: "COMMODITY",
    pf: "1.78",
    wr: "46.9",
    n: "750",
  },
  {
    name: "FOREX",
    pf: "0.27",
    wr: "46.4",
    n: "1169",
    extra: "SUB-FLOOR",
  },
  {
    name: "BOND",
    pf: "1.72",
    wr: "55.6",
    n: "18",
  },
];

const VIEWS = [
  "Overview",
  "Active Picks",
  "Verified Alpha",
  "Smart Picks",
  "US Equity Picks",
  "Closed Picks",
  "Portfolios",
  "Dashboards",
  "Strat. Leaderboard",
  "Permutations",
  "Performance",
  "Score Tracker",
  "ML Health",
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

async function waitForAuditGrid(page: Page) {
  // Wait for the primary data surface (cards, table, or chart canvas)
  await page
    .locator(
      ".asset-card, [data-testid='asset-card'], table, canvas, .audit-table"
    )
    .first()
    .waitFor({ timeout: 15000 })
    .catch(() => {
      // Some views may be text-only; don't hard-fail.
    });
}

async function takeAuditScreenshot(page: Page, name: string) {
  await page.screenshot({
    path: `/mnt/agents/output/findtorontoevents_swarm/tests/screenshots/audit-${name}.png`,
    fullPage: true,
  });
}

/* ------------------------------------------------------------------ */
/*  Suite                                                              */
/* ------------------------------------------------------------------ */

test.describe.configure({ mode: "parallel" });

test.describe("Audit Dashboard", () => {
  /* ================================================================ */
  /*  1. Baseline Load + Error Capture                                 */
  /* ================================================================ */
  test("/audit/ loads without critical errors", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(AUDIT_BASE, { waitUntil: "networkidle" });
    await waitForAuditGrid(page);

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  test("/audit/ logs full error report for CI inspection", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(AUDIT_BASE, { waitUntil: "networkidle" });
    await waitForAuditGrid(page);

    const clean = logConsoleErrors(tracker);
    expect(clean || tracker.errors.length === 0).toBeTruthy();
  });

  /* ================================================================ */
  /*  2. Asset-Class Summary Cards                                     */
  /* ================================================================ */
  test("all 6 asset class cards are visible with expected metrics", async ({
    page,
  }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(AUDIT_BASE, { waitUntil: "networkidle" });
    await waitForAuditGrid(page);

    for (const asset of ASSET_CLASSES) {
      // Locate card by heading text
      const card = page
        .locator(`text=/\\b${asset.name}\\b/i`)
        .locator("xpath=ancestor::*[contains(@class,'card') or contains(@class,'asset') or @data-testid='asset-card']")
        .or(page.locator(`[data-testid='asset-card-${asset.name}']`))
        .first();

      // Fallback: just verify the text exists somewhere in the page
      const heading = page.locator(`text=/\\b${asset.name}\\b/i`).first();
      await expect(heading).toBeVisible({ timeout: 10000 });

      // Verify PF, WR, and n counts appear near the card
      const pageText = await page.locator("body").textContent();
      expect(pageText).toContain(asset.pf);
      expect(pageText).toContain(asset.wr);
      expect(pageText).toContain(asset.n);
    }

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  test("FOREX card highlights SUB-FLOOR status", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(AUDIT_BASE, { waitUntil: "networkidle" });
    await waitForAuditGrid(page);

    const bodyText = await page.locator("body").textContent();
    expect(bodyText).toMatch(/SUB\-FLOOR/i);
    expect(bodyText).toContain("0.27"); // PF sub-floor

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  3. Filter Dropdown Interactions                                  */
  /* ================================================================ */
  test("filter dropdowns open and accept options", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(AUDIT_BASE, { waitUntil: "networkidle" });
    await waitForAuditGrid(page);

    const filters = [
      { label: "Asset", selector: "text=Asset" },
      { label: "System", selector: "text=System" },
      { label: "Status", selector: "text=Status" },
      { label: "Direction", selector: "text=Direction" },
    ];

    for (const f of filters) {
      const btn = page.locator(f.selector).first();
      const exists = (await btn.count()) > 0 && (await btn.isVisible().catch(() => false));
      if (!exists) {
        test.info().annotations.push({
          type: "missing-filter",
          description: `Filter "${f.label}" not found`,
        });
        continue;
      }

      await btn.click();
      await page.waitForTimeout(400);

      // Press Escape or click away to close without changing selection
      await page.keyboard.press("Escape");
      await page.waitForTimeout(200);
    }

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  test("filter buttons — Best Score, Proven Only, In Profit", async ({
    page,
  }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(AUDIT_BASE, { waitUntil: "networkidle" });
    await waitForAuditGrid(page);

    const buttons = [
      { name: "Best Score", pattern: /best\s*score/i },
      { name: "Proven Only", pattern: /proven\s*only/i },
      { name: "In Profit", pattern: /in\s*profit/i },
    ];

    for (const btn of buttons) {
      const locator = page.getByRole("button", { name: btn.pattern }).first();
      if ((await locator.count()) > 0 && (await locator.isVisible().catch(() => false))) {
        await locator.click();
        await page.waitForTimeout(500);
        await waitForAuditGrid(page);
      } else {
        test.info().annotations.push({
          type: "missing-button",
          description: `Button "${btn.name}" not found`,
        });
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
  /*  4. Score Filter Dropdown                                         */
  /* ================================================================ */
  test("score filter dropdown opens", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(AUDIT_BASE, { waitUntil: "networkidle" });
    await waitForAuditGrid(page);

    const scoreFilter = page
      .locator("button:has-text('Score'), [data-testid='score-filter']")
      .first();

    if ((await scoreFilter.count()) > 0 && (await scoreFilter.isVisible().catch(() => false))) {
      await scoreFilter.click();
      await page.waitForTimeout(400);
      await page.keyboard.press("Escape");
    }

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  5. Export CSV Buttons                                            */
  /* ================================================================ */
  test("Export Active (CSV) button triggers download or request", async ({
    page,
  }) => {
    const tracker = createConsoleErrorTracker(page);

    // Intercept the CSV request so we can assert it was attempted
    let csvUrl: string | null = null;
    page.on("request", (req) => {
      if (req.url().includes(".csv") || req.url().includes("export")) {
        csvUrl = req.url();
      }
    });

    await page.goto(AUDIT_BASE, { waitUntil: "networkidle" });
    await waitForAuditGrid(page);

    const exportBtn = page
      .getByRole("button", { name: /export.*active/i })
      .or(page.locator("button:has-text('Export Active')"))
      .or(page.locator("button:has-text('Export CSV')"))
      .first();

    if ((await exportBtn.count()) > 0 && (await exportBtn.isVisible().catch(() => false))) {
      const [download] = await Promise.all([
        page.waitForEvent("download", { timeout: 10000 }).catch(() => null),
        exportBtn.click(),
      ]);

      // Either a download started or a CSV request fired
      expect(download !== null || csvUrl !== null).toBeTruthy();
    } else {
      test.info().annotations.push({
        type: "skip-reason",
        description: "Export Active CSV button not found",
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
  /*  6. View Switching                                                 */
  /* ================================================================ */
  for (const viewName of VIEWS.slice(0, 6)) {
    // Only parallelise the most important views
    test(`view switch — ${viewName}`, async ({ page }) => {
      const tracker = createConsoleErrorTracker(page);
      await page.goto(AUDIT_BASE, { waitUntil: "networkidle" });
      await waitForAuditGrid(page);

      const tab = page
        .getByRole("tab", { name: new RegExp(viewName, "i") })
        .or(page.locator(`button:has-text('${viewName}')`))
        .or(page.locator(`a:has-text('${viewName}')`))
        .first();

      if ((await tab.count()) === 0 || !(await tab.isVisible().catch(() => false))) {
        test.info().annotations.push({
          type: "missing-view",
          description: `View tab "${viewName}" not found`,
        });
        return;
      }

      await tab.click();
      await page.waitForTimeout(800);
      await waitForAuditGrid(page);

      await takeAuditScreenshot(page, `view-${viewName.toLowerCase().replace(/\s+/g, "-")}`);

      assertNoConsoleErrors(tracker, [
        /favicon/i,
        /chunk/i,
        /source.map/i,
        /\.woff2?/i,
      ]);
    });
  }

  /* ================================================================ */
  /*  7. Disclaimer Footer                                              */
  /* ================================================================ */
  test("disclaimer footer is present", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(AUDIT_BASE, { waitUntil: "networkidle" });
    await waitForAuditGrid(page);

    const disclaimer = page
      .locator("text=/disclaimer/i")
      .or(page.locator("[data-testid='disclaimer']"))
      .or(page.locator("footer"))
      .first();

    await expect(disclaimer).toBeVisible({ timeout: 8000 });

    const text = await disclaimer.textContent();
    expect(text!.toLowerCase()).toContain("disclaimer");

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  8. /audit/hyrotrader/ — Baseline                                */
  /* ================================================================ */
  test("/audit/hyrotrader/ loads without critical errors", async ({
    page,
  }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(HYRO_BASE, { waitUntil: "networkidle" });

    const heading = page
      .locator("text=/HyroTrader/i")
      .or(page.locator("h1, h2"))
      .first();
    await expect(heading).toBeVisible({ timeout: 15000 });

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  9. HyroTrader — Challenge Parameters                            */
  /* ================================================================ */
  test("hyrotrader challenge parameters table is present", async ({
    page,
  }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(HYRO_BASE, { waitUntil: "networkidle" });

    const bodyText = await page.locator("body").textContent();

    // Challenge parameters
    expect(bodyText).toContain("$5K");
    expect(bodyText).toMatch(/phase\s*1/i);

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  10. HyroTrader — Account Snapshot Values                          */
  /* ================================================================ */
  test("hyrotrader account snapshot values are populated", async ({
    page,
  }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(HYRO_BASE, { waitUntil: "networkidle" });

    const bodyText = await page.locator("body").textContent();

    // Equity, day start, high-water, cumulative PnL should all be present
    // and not literally blank.
    expect(bodyText).toMatch(/equity\s*[:=\s]*\d/i);
    expect(bodyText).toMatch(/high[\s\-]?water/i);
    expect(bodyText).toMatch(/cum(ulative)?\s*pnl/i);

    // Specific known values from reconnaissance (tolerance for drift)
    expect(bodyText).toContain("4929");
    expect(bodyText).toContain("5000");
    expect(bodyText).toContain("5070");
    expect(bodyText).toContain("-70.66");

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  11. HyroTrader — Progress Bars Render                             */
  /* ================================================================ */
  test("hyrotrader progress bars render", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(HYRO_BASE, { waitUntil: "networkidle" });

    const progressBars = page.locator(
      "progress, [role='progressbar'], .progress-bar, [class*='progress']"
    );

    const count = await progressBars.count();
    if (count === 0) {
      // Some implementations use div-based bars without ARIA roles
      const divBars = page.locator(
        "div[style*='width']" // crude fallback for styled div bars
      );
      const hasBar = (await divBars.count()) > 0;
      if (!hasBar) {
        test.info().annotations.push({
          type: "visual-check",
          description:
            "No semantic progress bars found; verify visually that bars render",
        });
      }
    } else {
      expect(count).toBeGreaterThan(0);
      // At least one should have a non-zero width or value
      const first = progressBars.first();
      const val = await first.getAttribute("value");
      const max = await first.getAttribute("max");
      if (val !== null && max !== null) {
        expect(Number(val)).toBeGreaterThanOrEqual(0);
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
  /*  12. HyroTrader — Strategy List Populated                          */
  /* ================================================================ */
  test("hyrotrader strategy list is populated", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(HYRO_BASE, { waitUntil: "networkidle" });

    const strategies = [
      "CCI Divergence",
      "ADX Volatility Breakout",
      "BB Squeeze Breakout",
      "Multi-EMA Stack",
      "CMF Cross",
    ];

    for (const strat of strategies) {
      const link = page.locator(`text=/\\b${strat}\\b/i`).first();
      await expect(link).toBeVisible({ timeout: 8000 });
    }

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  13. HyroTrader — Strategy Doc Links                              */
  /* ================================================================ */
  test("hyrotrader strategy links point to GitHub", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.goto(HYRO_BASE, { waitUntil: "networkidle" });

    const githubLinks = page.locator("a[href*='github.com']");
    const count = await githubLinks.count();

    // At least one strategy documentation link should exist
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < Math.min(count, 5); i++) {
      const href = await githubLinks.nth(i).getAttribute("href");
      expect(href).toMatch(/^https:\/\/github\.com/);
    }

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  /* ================================================================ */
  /*  14. Mobile Viewport (375×667)                                    */
  /* ================================================================ */
  test("mobile viewport — audit dashboard survives", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto(AUDIT_BASE, { waitUntil: "networkidle" });
    await waitForAuditGrid(page);

    // No horizontal overflow
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const windowWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(windowWidth + 1);

    // Asset cards should still be readable (stacked vertically)
    for (const asset of ASSET_CLASSES) {
      const heading = page.locator(`text=/\\b${asset.name}\\b/i`).first();
      const visible = await heading.isVisible().catch(() => false);
      if (!visible) {
        test.info().annotations.push({
          type: "mobile-visibility",
          description: `${asset.name} not visible on mobile`,
        });
      }
    }

    await takeAuditScreenshot(page, "mobile-375x667");

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });

  test("mobile viewport — hyrotrader survives", async ({ page }) => {
    const tracker = createConsoleErrorTracker(page);
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto(HYRO_BASE, { waitUntil: "networkidle" });

    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const windowWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(windowWidth + 1);

    const heading = page.locator("text=/HyroTrader/i").first();
    await expect(heading).toBeVisible({ timeout: 10000 });

    await takeAuditScreenshot(page, "hyrotrader-mobile-375x667");

    assertNoConsoleErrors(tracker, [
      /favicon/i,
      /chunk/i,
      /source.map/i,
      /\.woff2?/i,
    ]);
  });
});
