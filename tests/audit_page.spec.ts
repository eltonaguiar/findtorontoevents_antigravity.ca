/**
 * /audit page smoke test — JS errors, console errors, asset 404s, content checks.
 *
 * Loads TORONTOEVENTS_ANTIGRAVITY/audit/index.html via file:// (no server needed)
 * and asserts the page renders cleanly.
 */
import { test, expect } from "@playwright/test";
import { pathToFileURL } from "url";
import path from "path";

const auditHtml = path.resolve(
  __dirname,
  "..",
  "TORONTOEVENTS_ANTIGRAVITY",
  "audit",
  "index.html",
);
const auditUrl = pathToFileURL(auditHtml).toString();

test.describe("/audit page", () => {
  test("loads without JS errors, console errors, or asset 404s", async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    const failedRequests: string[] = [];

    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => pageErrors.push(err.message));
    page.on("requestfailed", (req) =>
      failedRequests.push(`${req.url()} (${req.failure()?.errorText ?? "unknown"})`),
    );
    page.on("response", (res) => {
      if (res.status() >= 400) {
        failedRequests.push(`${res.url()} -> HTTP ${res.status()}`);
      }
    });

    await page.goto(auditUrl, { waitUntil: "networkidle" });

    expect(pageErrors, "uncaught JS errors").toEqual([]);
    expect(consoleErrors, "console errors").toEqual([]);
    expect(failedRequests, "failed asset loads").toEqual([]);
  });

  test("renders the headline content sections", async ({ page }) => {
    await page.goto(auditUrl, { waitUntil: "domcontentloaded" });

    await expect(page).toHaveTitle(/Toronto Events Database Audit/i);
    await expect(page.locator("h1")).toContainText("Toronto Events Database Audit");

    const sectionIds = ["summary", "critical", "quality", "coverage", "festivals", "actions", "progress"];
    for (const id of sectionIds) {
      await expect(page.locator(`section#${id}`), `section #${id}`).toBeVisible();
    }

    // Stat tiles render
    await expect(page.locator(".stat .num").first()).toBeVisible();
    expect(await page.locator(".stat").count()).toBeGreaterThanOrEqual(4);

    // All four charts load with real intrinsic sizes (i.e. the PNGs are present, not broken).
    const imgs = page.locator("figure img");
    const count = await imgs.count();
    expect(count).toBeGreaterThanOrEqual(4);
    for (let i = 0; i < count; i++) {
      const img = imgs.nth(i);
      await expect(img).toBeVisible();
      const naturalWidth = await img.evaluate((el: HTMLImageElement) => el.naturalWidth);
      expect(naturalWidth, `image #${i} naturalWidth`).toBeGreaterThan(0);
    }

    // Download link to the .docx report present
    const docxLink = page.locator('a[href$="Toronto_Events_Database_Audit.docx"]').first();
    await expect(docxLink).toBeVisible();
  });

  test("table-of-contents anchors all resolve to a section", async ({ page }) => {
    await page.goto(auditUrl, { waitUntil: "domcontentloaded" });
    const tocLinks = await page.locator("nav.toc a").all();
    expect(tocLinks.length).toBeGreaterThan(0);
    for (const a of tocLinks) {
      const href = await a.getAttribute("href");
      expect(href).toMatch(/^#/);
      const targetId = href!.replace("#", "");
      await expect(page.locator(`#${targetId}`), `target ${href}`).toHaveCount(1);
    }
  });
});
