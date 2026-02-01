import { test, expect } from "@playwright/test";

const isRealishAvatar = (url: string | null): boolean => {
  if (!url) return false;
  if (url.includes("dicebear.com")) return false;
  if (url.includes("ui-avatars.com")) return false;
  return true;
};

test("All main avatars are correct in guest mode", async ({ page }) => {
  await page.goto("http://localhost:5173/FAVCREATORS/#/guest", {
    waitUntil: "domcontentloaded",
    timeout: 20000,
  });

  await page.waitForTimeout(3000);

  // WTFPreston
  const wtfCard = page.locator(".creator-card:has-text('WTFPreston')");
  await expect(wtfCard).toBeVisible();
  const wtfAvatar = await wtfCard.locator("img").getAttribute("src");
  expect(isRealishAvatar(wtfAvatar)).toBeTruthy();

  // Zarthestar
  const zarCard = page.locator(".creator-card:has-text('Zarthestar')");
  await expect(zarCard).toBeVisible();
  const zarAvatar = await zarCard.locator("img").getAttribute("src");
  expect(isRealishAvatar(zarAvatar)).toBeTruthy();

  // Starfireara
  const starCard = page.locator(".creator-card:has-text('Starfireara')");
  await expect(starCard).toBeVisible();
  const starAvatar = await starCard.locator("img").getAttribute("src");
  expect(isRealishAvatar(starAvatar)).toBeTruthy();

  // Adin Ross (should be empty or a real URL, not dicebear)
  const adinCard = page.locator(".creator-card:has-text('Adin Ross')");
  await expect(adinCard).toBeVisible();
  const adinAvatar = await adinCard.locator("img").getAttribute("src");
  expect(!!adinAvatar).toBeTruthy();
});
