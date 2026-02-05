import { test, expect } from "@playwright/test";

test("Starfireara avatar is correct in guest mode", async ({ page }) => {
  // Go to your local site
  await page.goto("http://localhost:5173/FAVCREATORS/#/guest", {
    waitUntil: "domcontentloaded",
    timeout: 20000,
  });

  // Take a screenshot immediately after navigation for debugging
  try {
    await page.screenshot({ path: "test-results/guest-avatar-nav.png", fullPage: true });
  } catch (error) {
    console.warn("Unable to capture screenshot", error);
  }

  // Wait for the app to render
  await page.waitForTimeout(2000);

  // Find the creator card for Starfireara
  const card = page.locator(".creator-card:has-text('Starfireara')");
  await expect(card).toBeVisible();

  // Find the avatar image inside the card
  const avatar = card.locator("img");
  await expect(avatar).toBeVisible();
  const src = await avatar.getAttribute("src");

  // Should be a real avatar URL (Unavatar, TikTok, or local archived)
  expect(src && (
    src.includes("unavatar.io") ||
    src.includes("tiktokcdn.com") ||
    src.includes("/avatars/")
  )).toBeTruthy();

  // Optionally, check that the image loads (status 200)
  // We use a broader check since the URL might be unavatar or direct
  console.log("Avatar src found:", src);
});
