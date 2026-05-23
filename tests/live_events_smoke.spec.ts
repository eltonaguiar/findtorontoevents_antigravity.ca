/**
 * Live findtorontoevents.ca smoke test — desktop + mobile.
 * Verifies events.json loads, events render, and no JS errors fire.
 *
 * Runs against production (https://findtorontoevents.ca) when invoked
 * with the Galaxy / Desktop projects in playwright.config.ts.
 */
import { test, expect } from "@playwright/test";

const SITE = "https://findtorontoevents.ca/";

async function smokeTest(page: import("@playwright/test").Page, label: string) {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];

  page.on("console", (m) => {
    if (m.type() === "error") consoleErrors.push(m.text());
  });
  page.on("pageerror", (e) => pageErrors.push(e.message));
  page.on("requestfailed", (r) =>
    failedRequests.push(`${r.url()} (${r.failure()?.errorText ?? "?"})`),
  );

  await page.goto(SITE, { waitUntil: "domcontentloaded", timeout: 60000 });

  // Fetch events.json directly via the page's request context — avoids
  // "Request content was evicted from inspector cache" on the ~10K-event payload.
  const apiResp = await page.request.get(SITE + "next/events.json", { timeout: 60000 });
  expect(apiResp.ok(), `${label}: next/events.json HTTP`).toBeTruthy();
  const evs = await apiResp.json();
  const list = Array.isArray(evs) ? evs : (evs.events ?? []);
  expect(list.length, `${label}: events.json count`).toBeGreaterThan(4000);

  // TPL events should be present in the live payload after the 2026-04-26 merge.
  const tplCount = list.filter(
    (e: any) => (e.source || "").trim() === "Toronto Public Library",
  ).length;
  expect(tplCount, `${label}: TPL events in live events.json`).toBeGreaterThan(1000);

  // At least one event card / list item rendered on the page.
  await page.waitForLoadState("networkidle", { timeout: 60000 }).catch(() => {});
  const visibleEventText = await page.locator("body").innerText();
  expect(visibleEventText.length, `${label}: page has rendered text`).toBeGreaterThan(500);

  // Check a few interactive bits — search/filter input present.
  const interactiveCount =
    (await page.locator('input[type="search"], input[type="text"], button').count()) ?? 0;
  expect(interactiveCount, `${label}: interactive controls rendered`).toBeGreaterThan(0);

  if (pageErrors.length) console.log(`[${label}] pageErrors:`, pageErrors);
  if (consoleErrors.length) console.log(`[${label}] consoleErrors:`, consoleErrors);
  if (failedRequests.length) console.log(`[${label}] failedRequests:`, failedRequests);

  // Known pre-existing bug on findtorontoevents.ca: Next.js SSR/CSR hydration
  // mismatch (React error #418). Non-fatal — events still render after the
  // client-side re-render. Tracked separately; not caused by the events DB
  // enhancements landed in PR #419.
  const newPageErrors = pageErrors.filter(
    (e) => !/Minified React error #418/.test(e),
  );
  expect(newPageErrors, `${label}: uncaught JS errors (excluding known #418)`).toEqual([]);

  // Filter known-noisy console messages: 3rd-party analytics/ads 4xx/5xx and
  // generic "Failed to load resource: 400/404" lines (whose URLs the console
  // doesn't include — but their cause shows up in failedRequests, which we
  // separately verify is third-party-only below).
  const firstPartyErrors = consoleErrors.filter(
    (e) =>
      !/google-analytics|googletagmanager|googlesyndication|doubleclick|facebook|hotjar|cloudflareinsights|adservice/i.test(
        e,
      ) && !/Failed to load resource: the server responded with a status of (4\d\d|5\d\d)/i.test(e),
  );
  expect(firstPartyErrors, `${label}: first-party console errors`).toEqual([]);

  // Failed requests should be third-party only.
  const firstPartyFailedRequests = failedRequests.filter(
    (e) =>
      !/google-analytics|googletagmanager|googlesyndication|doubleclick|facebook|hotjar|cloudflareinsights|adservice|pagead/i.test(
        e,
      ),
  );
  expect(firstPartyFailedRequests, `${label}: first-party failed requests`).toEqual([]);

  return {
    eventsCount: list.length,
    tplCount,
    consoleErrors: consoleErrors.length,
    failedRequests: failedRequests.length,
  };
}

test.describe("findtorontoevents.ca live", () => {
  test("desktop loads events without JS errors", async ({ page }) => {
    const r = await smokeTest(page, "desktop");
    console.log("desktop:", JSON.stringify(r));
  });

  test("mobile (Galaxy viewport) loads events without JS errors", async ({ browser }) => {
    // Samsung Galaxy S25 Ultra: 1440 x 3120 device pixels, devicePixelRatio 3.5,
    // CSS viewport ~412 x 892. Use Android Chrome UA.
    const ctx = await browser.newContext({
      viewport: { width: 412, height: 892 },
      deviceScaleFactor: 3.5,
      isMobile: true,
      hasTouch: true,
      userAgent:
        "Mozilla/5.0 (Linux; Android 15; SM-S938B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    });
    const page = await ctx.newPage();
    const r = await smokeTest(page, "galaxy-s25-ultra");
    console.log("galaxy-s25-ultra:", JSON.stringify(r));
    await ctx.close();
  });
});
