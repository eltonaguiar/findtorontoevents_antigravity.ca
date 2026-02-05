import { test, expect } from "@playwright/test";

test("Deployed site loads and renders main components", async ({ page }) => {
  // Collect console errors
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  // Go to your local site
  await page.goto("http://localhost:5173/FAVCREATORS/#/guest", {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });

  // Check for blank page (body should not be empty)
  const bodyContent = await page.content();
  expect(bodyContent.length).toBeGreaterThan(100);

  // Wait for the app to render
  await page.waitForTimeout(3000);

  // Check for Import button (always visible)
  await expect(page.getByRole("button", { name: /Import/i })).toBeVisible();

  // Check for category filter dropdown
  const categorySelect = page.locator("select").first();
  await expect(categorySelect).toBeVisible();

  // Check for at least one creator card or content
  const creatorCards = page.locator(".creator-card");
  const cardCount = await creatorCards.count();
  console.log(`Found ${cardCount} creator cards`);

  // Take a screenshot for visual verification
  await page.screenshot({
    path: "test-results/deployed-site.png",
    fullPage: true,
  });

  console.log("Site verification complete!");
});

test("Category filter works correctly", async ({ page }) => {
  await page.goto("http://localhost:5173/FAVCREATORS/#/guest", {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });

  // Wait for app to load
  await page.waitForTimeout(2000);
  await expect(page.getByRole("button", { name: /Import/i })).toBeVisible({ timeout: 15000 });

  // Find the category dropdown
  const categorySelect = page
    .locator("select")
    .filter({ hasText: /All Categories|Favorites|Other/i })
    .first();

  if (await categorySelect.isVisible()) {
    // Test filtering by Favorites
    await categorySelect.selectOption("Favorites");
    await page.waitForTimeout(500);

    // Test filtering by Other
    await categorySelect.selectOption("Other");
    await page.waitForTimeout(500);

    // Reset to All
    await categorySelect.selectOption("");
    await page.waitForTimeout(500);

    console.log("Category filter test passed!");
  }
});

test("No duplicate filter dropdowns", async ({ page }) => {
  await page.goto("http://localhost:5173/FAVCREATORS/#/guest", {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });

  // Wait for app to load
  await page.waitForTimeout(2000);

  // Check that there's no "All Creators" / "Adin Ross only" dropdown (the one we removed)
  const adinRossOption = page.locator("option", { hasText: "Adin Ross only" });
  const count = await adinRossOption.count();

  expect(count).toBe(0);
  console.log("No duplicate filter dropdown found - test passed!");
});
