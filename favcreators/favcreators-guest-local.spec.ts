/**
 * Local test: favcreators app at /favcreators/#/guest (matches production path).
 * Run with: npx playwright test favcreators-guest-local.spec.ts
 * Requires: npm run dev (or webServer in playwright.config starts it).
 */
import { test, expect } from "@playwright/test";

const GUEST_URL = "http://localhost:5173/favcreators/#/guest";

test("favcreators guest route loads locally", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto(GUEST_URL, {
    waitUntil: "domcontentloaded",
    timeout: 15000,
  });

  // Page should load (no 500 / blank)
  await expect(page).toHaveURL(/favcreators.*#\/guest/);
  const body = await page.locator("body");
  await expect(body).toBeVisible();

  // Wait for React to mount
  await page.waitForSelector("#root", { state: "attached", timeout: 5000 });
  const root = page.locator("#root");
  await expect(root).toBeVisible({ timeout: 10000 });
});

test("favcreators guest shows main UI (Import button)", async ({ page }) => {
  await page.goto(GUEST_URL, {
    waitUntil: "domcontentloaded",
    timeout: 15000,
  });

  await expect(page.getByRole("button", { name: "📥 Import", exact: true })).toBeVisible({
    timeout: 15000,
  });
});

test("favcreators guest has category filter", async ({ page }) => {
  await page.goto(GUEST_URL, {
    waitUntil: "domcontentloaded",
    timeout: 15000,
  });

  const select = page.locator("select").first();
  await expect(select).toBeVisible({ timeout: 10000 });
});
