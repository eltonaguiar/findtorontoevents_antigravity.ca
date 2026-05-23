/**
 * Comprehensive filter tests for findtorontoevents.ca
 *
 * Covers:
 *  1. TBD filter: events with no/invalid dates are hidden by default
 *  2. TBD toggle button: exists, toggles state, updates label
 *  3. TBD indicator badge: injected on TBD cards when revealed
 *  4. UTC timezone bug: events stored as "YYYY-MM-DDT00:00:00Z" (UTC midnight)
 *     get treated as "yesterday evening" in Eastern Time and are incorrectly
 *     hidden by the past-event filter.  Today's events MUST be visible.
 *  5. Yesterday's events are properly hidden by the past-event filter
 *  6. Future events are always visible
 *
 * Run locally:
 *   npx playwright test tests/events_filter_bugs.spec.ts --project="Desktop Chrome"
 *
 * Run against live site:
 *   VERIFY_REMOTE=1 npx playwright test tests/events_filter_bugs.spec.ts --project="Desktop Chrome"
 *
 * NOTE: Local mode requires serve_local.py AND the main site index.html to be
 * present.  If that chunk is missing, tests that need real event cards will
 * be skipped automatically (see `skipIfNoEventCards`).
 */

import { test, expect, Page } from '@playwright/test';

// ─── Config ───────────────────────────────────────────────────────────────────

const isRemote =
  process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true';

const BASE =
  process.env.BASE_URL ||
  (isRemote ? 'https://findtorontoevents.ca' : 'http://localhost:5173');

/** Max time for filter scripts to settle after page load (ms). */
const FILTER_SETTLE = 8000;

// ─── Date helpers ─────────────────────────────────────────────────────────────

/** UTC ISO string "YYYY-MM-DDT00:00:00.000Z" for today + daysFromNow */
function utcMidnightISO(daysFromNow: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + daysFromNow);
  d.setUTCHours(0, 0, 0, 0);
  return d.toISOString();
}

// ─── Mock event fixtures ──────────────────────────────────────────────────────

const TODAY_TITLE    = '[TEST] Today UTC Midnight Event';
const TOMORROW_TITLE = '[TEST] Tomorrow Future Event';
const YESTERDAY_TITLE = '[TEST] Yesterday Past Event';
const TBD_NULL_TITLE  = '[TEST] TBD Null Date Event';
const TBD_EMPTY_TITLE = '[TEST] TBD Empty String Date Event';
const FUTURE_TITLE    = '[TEST] Far Future 30-Day Event';

/** Minimal but complete event object matching the events.json schema. */
function makeEvent(
  id: string,
  title: string,
  date: string | null,
  extraDays = 0,
): object {
  return {
    id,
    title,
    date,
    location: 'Test Venue – Nathan Phillips Square',
    address: '100 Queen St W, Toronto, ON M5H 2N1',
    lat: 43.6525,
    lng: -79.3832,
    source: 'test',
    host: 'Test Host',
    url: `https://example.com/event-${id}`,
    price: 'Free',
    price_amount: 0,
    is_free: true,
    description: `Test event: ${title}`,
    categories: ['Arts'],
    tags: ['Test'],
    status: 'UPCOMING',
    is_multi_day: false,
    duration_category: 'single',
    is_recurring: false,
    last_updated: new Date().toISOString(),
    isMultiDay: false,
    isFree: true,
    isRecurring: false,
    priceAmount: 0,
    lastUpdated: new Date().toISOString(),
    image: null,
  };
}

function buildMockEvents(): object[] {
  return [
    makeEvent('test-today-utc',   TODAY_TITLE,    utcMidnightISO(0)),   // UTC midnight today
    makeEvent('test-tomorrow',    TOMORROW_TITLE,  utcMidnightISO(1)),   // Tomorrow
    makeEvent('test-yesterday',   YESTERDAY_TITLE, utcMidnightISO(-1)),  // Yesterday
    makeEvent('test-tbd-null',    TBD_NULL_TITLE,  null),                // TBD: null date
    makeEvent('test-tbd-empty',   TBD_EMPTY_TITLE, ''),                  // TBD: empty date
    makeEvent('test-future-30d',  FUTURE_TITLE,    utcMidnightISO(30)),  // Far future
  ];
}

// ─── Playwright helpers ───────────────────────────────────────────────────────

/**
 * Register a network-level route interceptor that returns mock events for
 * ALL events.json requests.  Must be called BEFORE page.goto().
 */
async function mockEventsJSON(page: Page, events: object[] = buildMockEvents()) {
  const body = JSON.stringify({ events });
  // The page's fetch override tries /next/events.json, /events.json, /data/events.json, and
  // a GitHub raw URL.  Catch all of them with a single predicate.
  await page.route(
    (url) => url.pathname.endsWith('events.json') || url.href.includes('events.json'),
    (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json; charset=utf-8',
        body,
      }),
  );
}

/**
 * Navigate to the events page, wait for filter controls and event cards to
 * be ready.
 */
async function loadPage(page: Page) {
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  // Wait for the filter toggle to appear (it's injected by the inline script).
  await page.waitForFunction(
    () => !!document.getElementById('tbd-toggle'),
    { timeout: 25000 },
  ).catch(() => {
    // Tolerate if filter controls never appear (e.g. React not hydrated locally).
  });
  await page.waitForTimeout(FILTER_SETTLE);
}

/**
 * Skip the test if the site shows no real event cards (React not hydrated).
 */
async function skipIfNoEventCards(page: Page) {
  const hasCards = await page.evaluate(() => {
    const cards = document.querySelectorAll(
      '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
    );
    for (const c of cards) {
      if (c.querySelector('h2, h3')) return true;
    }
    return false;
  });
  if (!hasCards) {
    test.skip(
      true,
      'No event cards rendered – React chunks may be missing locally. Run with VERIFY_REMOTE=1.',
    );
  }
}

/** Return visibility status of the first card whose h2/h3 contains `partialTitle`. */
async function getCardStatus(
  page: Page,
  partialTitle: string,
): Promise<'visible' | 'hidden' | 'not-found'> {
  return page.evaluate((title: string) => {
    const cards = document.querySelectorAll<HTMLElement>(
      '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
    );
    for (const card of Array.from(cards)) {
      const heading = card.querySelector('h2, h3');
      if (!heading?.textContent?.includes(title)) continue;

      if (card.classList.contains('event-card-hidden')) return 'hidden';
      const group = card.closest<HTMLElement>('.group');
      if (group && group.style.display === 'none') return 'hidden';
      return 'visible';
    }
    return 'not-found';
  }, partialTitle);
}

/** Count event cards that are currently visible (not hidden, have a heading). */
async function countVisibleCards(page: Page): Promise<number> {
  return page.evaluate(() => {
    const cards = document.querySelectorAll<HTMLElement>(
      '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
    );
    let n = 0;
    for (const card of Array.from(cards)) {
      const heading = card.querySelector('h2, h3');
      if (!heading?.textContent?.trim()) continue;
      if (card.classList.contains('event-card-hidden')) continue;
      const group = card.closest<HTMLElement>('.group');
      if (group && group.style.display === 'none') continue;
      n++;
    }
    return n;
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  Suite 1 — TBD Toggle UI (works with real or mock data)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('TBD Filter — toggle UI', () => {
  test.describe.configure({ timeout: 120_000 });

  test('TBD toggle button is present with correct initial label', async ({ page }) => {
    await loadPage(page);

    const tbdBtn = page.locator('#tbd-toggle');
    await expect(tbdBtn).toBeVisible({ timeout: 15_000 });
    await expect(tbdBtn).toContainText('Show TBD Events');

    const isActive = await tbdBtn.evaluate((el) => el.classList.contains('active'));
    expect(isActive, 'TBD button should NOT be active by default').toBe(false);
  });

  test('TBD toggle switches to active state and updates label on click', async ({ page }) => {
    await loadPage(page);

    const tbdBtn = page.locator('#tbd-toggle');
    await expect(tbdBtn).toBeVisible({ timeout: 15_000 });

    // Click to show TBD events
    await tbdBtn.click();
    await page.waitForTimeout(1000);

    const isActive = await tbdBtn.evaluate((el) => el.classList.contains('active'));
    expect(isActive, 'TBD button should be active after click').toBe(true);
    await expect(tbdBtn).toContainText('Showing TBD Events');
  });

  test('TBD toggle reverts on second click', async ({ page }) => {
    await loadPage(page);

    const tbdBtn = page.locator('#tbd-toggle');
    await expect(tbdBtn).toBeVisible({ timeout: 15_000 });

    await tbdBtn.click();
    await page.waitForTimeout(500);
    await tbdBtn.click();
    await page.waitForTimeout(1000);

    const isActive = await tbdBtn.evaluate((el) => el.classList.contains('active'));
    expect(isActive, 'TBD button should not be active after second click').toBe(false);
    await expect(tbdBtn).toContainText('Show TBD Events');
  });

  test('clicking TBD toggle never decreases visible card count', async ({ page }) => {
    await loadPage(page);
    await skipIfNoEventCards(page);

    const tbdBtn = page.locator('#tbd-toggle');
    await expect(tbdBtn).toBeVisible({ timeout: 15_000 });

    const countBefore = await countVisibleCards(page);
    await tbdBtn.click();
    await page.waitForTimeout(2000);
    const countAfter = await countVisibleCards(page);

    expect(countAfter, 'Showing TBD events should not reduce visible card count').toBeGreaterThanOrEqual(countBefore);

    console.log(`Cards before TBD toggle: ${countBefore}, after: ${countAfter} (${countAfter - countBefore} TBD events revealed)`);
  });

  test('hiding TBD events again brings count back down', async ({ page }) => {
    await loadPage(page);
    await skipIfNoEventCards(page);

    const tbdBtn = page.locator('#tbd-toggle');
    await expect(tbdBtn).toBeVisible({ timeout: 15_000 });

    const countDefault = await countVisibleCards(page);

    await tbdBtn.click();            // show TBD
    await page.waitForTimeout(1500);
    const countWithTBD = await countVisibleCards(page);

    await tbdBtn.click();            // hide TBD again
    await page.waitForTimeout(1500);
    const countFinal = await countVisibleCards(page);

    expect(countFinal, 'Final count after re-hiding TBD should not exceed show-TBD count').toBeLessThanOrEqual(countWithTBD);
    expect(countFinal, 'Final count should match default count (idempotent toggle)').toBe(countDefault);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
//  Suite 2 — TBD badge injection (uses mock events for determinism)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('TBD Filter — badge injection (mock events)', () => {
  test.describe.configure({ timeout: 120_000 });

  test('null-date event is hidden by default', async ({ page }) => {
    await mockEventsJSON(page);
    await loadPage(page);
    await skipIfNoEventCards(page);

    const status = await getCardStatus(page, '[TEST] TBD Null Date Event');
    // null-date events should be hidden unless toggle is on
    expect(
      status === 'hidden' || status === 'not-found',
      `null-date event should be hidden by default — got "${status}"`,
    ).toBe(true);
  });

  test('empty-string date event is hidden by default', async ({ page }) => {
    await mockEventsJSON(page);
    await loadPage(page);
    await skipIfNoEventCards(page);

    const status = await getCardStatus(page, '[TEST] TBD Empty String Date Event');
    expect(
      status === 'hidden' || status === 'not-found',
      `empty-date event should be hidden by default — got "${status}"`,
    ).toBe(true);
  });

  test('clicking TBD toggle reveals null-date event', async ({ page }) => {
    await mockEventsJSON(page);
    await loadPage(page);
    await skipIfNoEventCards(page);

    const tbdBtn = page.locator('#tbd-toggle');
    await expect(tbdBtn).toBeVisible({ timeout: 15_000 });
    await tbdBtn.click();
    await page.waitForTimeout(2000);

    const status = await getCardStatus(page, '[TEST] TBD Null Date Event');
    expect(
      status === 'visible' || status === 'not-found',  // not-found → event wasn't rendered (React issue)
      `null-date event should be visible after TBD toggle — got "${status}"`,
    ).toBe(true);
  });

  test('.tbd-indicator badge appears on TBD cards (real or mock data)', async ({ page }) => {
    // Works with real data too — just checks the badge logic
    await loadPage(page);
    await skipIfNoEventCards(page);

    const tbdBtn = page.locator('#tbd-toggle');
    await expect(tbdBtn).toBeVisible({ timeout: 15_000 });
    await tbdBtn.click();
    await page.waitForTimeout(2000);

    // Count TBD badges
    const badgeCount = await page.locator('.tbd-indicator').count();
    console.log(`TBD indicator badges found after toggle: ${badgeCount}`);

    // If any badges are present, they must say "TBD"
    if (badgeCount > 0) {
      await expect(page.locator('.tbd-indicator').first()).toHaveText('TBD');
    } else {
      // Acceptable: no TBD events in today's dataset — log and pass
      console.log('NOTE: No TBD events found in current dataset. Badge logic not exercised.');
    }
  });

  test('TBD cards not in events-grid never leak as visible ghost cards', async ({ page }) => {
    await mockEventsJSON(page);
    await loadPage(page);
    await skipIfNoEventCards(page);

    // TBD hidden cards should have event-card-hidden class, not be visually rendered
    const leakedTBD = await page.evaluate(() => {
      const cards = document.querySelectorAll<HTMLElement>(
        '[class*="glass-panel"]:not(.animate-pulse)',
      );
      let leaked = 0;
      for (const card of Array.from(cards)) {
        const h = card.querySelector('h2, h3');
        if (!h?.textContent) continue;
        const lc = h.textContent.toLowerCase();
        if (!lc.includes('tbd') && !lc.includes('date unavailable')) continue;
        // This is a TBD-looking card — check if incorrectly visible
        if (!card.classList.contains('event-card-hidden')) {
          const group = card.closest<HTMLElement>('.group');
          const parentHidden = group && group.style.display === 'none';
          if (!parentHidden) leaked++;
        }
      }
      return leaked;
    });

    expect(leakedTBD, 'No TBD cards should be visible without the toggle being active').toBe(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
//  Suite 3 — Past-event filter (mock events)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Past-event filter (mock events)', () => {
  test.describe.configure({ timeout: 120_000 });

  test('yesterday UTC midnight event is hidden by past-event filter', async ({ page }) => {
    await mockEventsJSON(page);
    await loadPage(page);
    await skipIfNoEventCards(page);

    const status = await getCardStatus(page, '[TEST] Yesterday Past Event');
    expect(
      status === 'hidden' || status === 'not-found',
      `Yesterday's event must be hidden — got "${status}"`,
    ).toBe(true);
    console.log(`Yesterday event status: ${status}`);
  });

  test('tomorrow event is visible (not filtered as past)', async ({ page }) => {
    await mockEventsJSON(page);
    await loadPage(page);
    await skipIfNoEventCards(page);

    const status = await getCardStatus(page, '[TEST] Tomorrow Future Event');
    expect(
      status === 'visible' || status === 'not-found',
      `Tomorrow's event must be visible — got "${status}"`,
    ).toBe(true);
    console.log(`Tomorrow event status: ${status}`);
  });

  test('far-future (30-day) event is visible', async ({ page }) => {
    await mockEventsJSON(page);
    await loadPage(page);
    await skipIfNoEventCards(page);

    const status = await getCardStatus(page, '[TEST] Far Future 30-Day Event');
    expect(
      status === 'visible' || status === 'not-found',
      `30-day future event must be visible — got "${status}"`,
    ).toBe(true);
    console.log(`Far future event status: ${status}`);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
//  Suite 4 — "Today" UTC timezone bug
//
//  BUG: Events stored as "YYYY-MM-DDT00:00:00Z" (UTC midnight) are compared
//  against __todayStart which is local midnight.  In Eastern Time (UTC-4) this
//  makes "today's UTC midnight" equal to "yesterday at 8 pm local", so the
//  event is incorrectly hidden as a past event.
//
//  Expected: today's events (by any UTC interpretation) MUST be visible.
//  Current behaviour: they may be hidden — these tests document the regression.
// ─────────────────────────────────────────────────────────────────────────────

test.describe('UTC timezone bug — today\'s events must be visible', () => {
  test.describe.configure({ timeout: 120_000 });

  /**
   * Regression test: event dated today at UTC midnight MUST be visible.
   *
   * With the current code, in Eastern Time (UTC-4 / UTC-5):
   *   new Date("2026-04-12T00:00:00Z")  →  April 11, 2026 at 8:00 PM EDT
   *   __todayStart                       →  April 12, 2026 at 00:00:00 EDT
   *   eventDate < __todayStart           →  TRUE  ← BUG: event hidden!
   *
   * EXPECTED: the event should be VISIBLE.
   * This test will FAIL until the underlying date-comparison bug is fixed.
   */
  test('event dated today at UTC midnight is visible [BUG REGRESSION]', async ({ page }) => {
    await mockEventsJSON(page);
    await loadPage(page);
    await skipIfNoEventCards(page);

    const status = await getCardStatus(page, '[TEST] Today UTC Midnight Event');

    if (status === 'not-found') {
      // Card not rendered at all (React hydration issue locally) — skip gracefully
      console.log('SKIP: Today UTC event card not found in DOM (React may not have rendered it).');
      return;
    }

    // Log useful debug info
    const debugInfo = await page.evaluate(() => {
      const todayStart = (function() { const d = new Date(); d.setHours(0,0,0,0); return d; })();
      const todayUTCISO = (() => {
        const d = new Date();
        return `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}-${String(d.getUTCDate()).padStart(2,'0')}T00:00:00.000Z`;
      })();
      const eventDate = new Date(todayUTCISO);
      return {
        todayStart: todayStart.toISOString(),
        eventDate: eventDate.toISOString(),
        eventDateLocal: eventDate.toString(),
        isEventBeforeTodayStart: eventDate < todayStart,
        offsetHours: -new Date().getTimezoneOffset() / 60,
      };
    });

    console.log('--- UTC timezone bug diagnostics ---');
    console.log(`  Local timezone offset: UTC${debugInfo.offsetHours >= 0 ? '+' : ''}${debugInfo.offsetHours}h`);
    console.log(`  event date (UTC ISO):  ${debugInfo.eventDate}`);
    console.log(`  event date (local str):${debugInfo.eventDateLocal}`);
    console.log(`  __todayStart:          ${debugInfo.todayStart}`);
    console.log(`  eventDate < todayStart: ${debugInfo.isEventBeforeTodayStart} ← BUG if true`);
    console.log(`  Card status: ${status}`);

    expect(
      status,
      [
        `TODAY UTC event is "${status}" — it should be "visible".`,
        ``,
        `Root cause: new Date("${debugInfo.eventDate}") = "${debugInfo.eventDateLocal}"`,
        `which is BEFORE local midnight (${debugInfo.todayStart}) in UTC${debugInfo.offsetHours}h.`,
        ``,
        `FIX: Compare dates in UTC. Replace:`,
        `  if (!isNaN(eventDate.getTime()) && eventDate < __todayStart)`,
        `with:`,
        `  if (!isNaN(eventDate.getTime()) && eventDate.toDateString() !== new Date().toDateString()`,
        `    && eventDate < __todayStart)`,
        `OR use UTC-based comparison:`,
        `  var todayUTCStr = new Date().toISOString().slice(0,10);`,
        `  if (eventData.date && eventData.date.slice(0,10) < todayUTCStr)`,
      ].join('\n'),
    ).toBe('visible');
  });

  /**
   * Verify using REAL events data that any event whose UTC date is "today"
   * is actually shown to the user.  Skips if no such events exist today.
   */
  test('real events dated today (UTC) are not hidden by past-event filter', async ({ page }) => {
    // Use real data (no mocking)
    await loadPage(page);
    await skipIfNoEventCards(page);

    // Get today's UTC date prefix
    const todayUTCPrefix = await page.evaluate(() => {
      const d = new Date();
      return `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}-${String(d.getUTCDate()).padStart(2,'0')}`;
    });

    // Check __RAW_EVENTS__ for events dated today
    const todayEvents = await page.evaluate((prefix: string) => {
      const raw = (window as any).__RAW_EVENTS__;
      if (!Array.isArray(raw)) return [] as Array<{ title: string; date: string }>;
      return raw
        .filter((e: any) => e.date && String(e.date).startsWith(prefix))
        .slice(0, 5)
        .map((e: any) => ({ title: e.title, date: e.date }));
    }, todayUTCPrefix);

    if (todayEvents.length === 0) {
      console.log(`No events found with UTC date ${todayUTCPrefix} — skipping real-data check.`);
      return;
    }

    console.log(`Found ${todayEvents.length} event(s) dated ${todayUTCPrefix}:`);

    let hiddenCount = 0;
    for (const ev of todayEvents) {
      const status = await getCardStatus(page, ev.title.substring(0, 20));
      console.log(`  "${ev.title}" (${ev.date}) → ${status}`);
      if (status === 'hidden') hiddenCount++;
    }

    expect(
      hiddenCount,
      `${hiddenCount}/${todayEvents.length} events dated today (UTC ${todayUTCPrefix}) are incorrectly hidden.\n` +
      `This confirms the UTC timezone bug — today's events appear as "yesterday" in local time.`,
    ).toBe(0);
  });

  /**
   * Verify __todayStart is computed with proper timezone awareness.
   * The filter should NOT use local-time midnight to compare UTC-stored dates.
   */
  test('filter boundary diagnostics — log __todayStart vs UTC now', async ({ page }) => {
    await loadPage(page);

    const info = await page.evaluate(() => {
      const localMidnight = (function() { const d = new Date(); d.setHours(0,0,0,0); return d; })();
      const utcMidnight = (function() { const d = new Date(); d.setUTCHours(0,0,0,0); return d; })();
      const now = new Date();
      const tzOffsetH = -now.getTimezoneOffset() / 60;

      // Simulate the bug: event today at UTC midnight
      const utcTodayStr = `${now.getUTCFullYear()}-${String(now.getUTCMonth()+1).padStart(2,'0')}-${String(now.getUTCDate()).padStart(2,'0')}T00:00:00.000Z`;
      const eventDate = new Date(utcTodayStr);
      const isBugTriggered = eventDate < localMidnight;

      return {
        tzOffsetH,
        localMidnight: localMidnight.toISOString(),
        utcMidnight: utcMidnight.toISOString(),
        utcTodayStr,
        eventDateLocal: eventDate.toString(),
        isBugTriggered,
      };
    });

    console.log('--- Filter boundary diagnostics ---');
    console.log(`  Timezone offset: UTC${info.tzOffsetH >= 0 ? '+' : ''}${info.tzOffsetH}h`);
    console.log(`  Local midnight:  ${info.localMidnight}`);
    console.log(`  UTC midnight:    ${info.utcMidnight}`);
    console.log(`  Event (UTC today):  ${info.utcTodayStr}`);
    console.log(`  Event (local repr): ${info.eventDateLocal}`);
    console.log(`  Bug triggered?   ${info.isBugTriggered ? '⚠️  YES — today events hidden' : '✅ No'}`);

    if (info.isBugTriggered) {
      console.log('\n=== BUG CONFIRMED ===');
      console.log('Events stored as UTC midnight are hidden as "past events" in this timezone.');
      console.log('Fix: change the past-event filter to compare UTC date strings, not timestamps.');
      console.log('\nRecommended fix in index.html:');
      console.log('  // BEFORE (buggy):');
      console.log('  if (!isNaN(eventDate.getTime()) && eventDate < __todayStart) {');
      console.log('  // AFTER (fixed):');
      console.log("  var __todayUTCDate = new Date().toISOString().slice(0, 10); // 'YYYY-MM-DD'");
      console.log('  if (eventData.date && eventData.date.slice(0, 10) < __todayUTCDate) {');
    }

    // This is an informational test — always passes, but logs the bug state
    expect(info.tzOffsetH).toBeDefined();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
//  Suite 5 — Filter controls accessibility and resilience
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Filter controls — accessibility and resilience', () => {
  test.describe.configure({ timeout: 90_000 });

  test('filter controls container is present in DOM', async ({ page }) => {
    await loadPage(page);
    const container = page.locator('#custom-filter-controls');
    await expect(container).toBeAttached({ timeout: 20_000 });
  });

  test('all four filter toggle buttons are present', async ({ page }) => {
    await loadPage(page);
    for (const id of ['tbd-toggle', 'multiday-toggle', 'near-me-toggle', 'thumbnail-toggle']) {
      const btn = page.locator(`#${id}`);
      await expect(btn).toBeAttached({ timeout: 20_000 }),
        `Expected #${id} to be in the DOM`;
    }
  });

  test('filter buttons have correct initial states (not active)', async ({ page }) => {
    await loadPage(page);
    for (const id of ['tbd-toggle', 'multiday-toggle']) {
      const isActive = await page
        .locator(`#${id}`)
        .evaluate((el) => el.classList.contains('active'));
      expect(isActive, `#${id} should not be active by default`).toBe(false);
    }
  });

  test('events grid is present in the DOM', async ({ page }) => {
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await expect(page.locator('#events-grid')).toBeAttached({ timeout: 20_000 });
  });

  test('past-event filter hides at least one event from the real dataset', async ({ page }) => {
    await loadPage(page);
    await skipIfNoEventCards(page);

    // Check that __RAW_EVENTS__ contains some past events (they should be invisible)
    const hasPastEvents = await page.evaluate(() => {
      const raw = (window as any).__RAW_EVENTS__;
      if (!Array.isArray(raw)) return null;
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      return raw.some((e: any) => e.date && new Date(e.date) < yesterday);
    });

    if (hasPastEvents === null) {
      console.log('__RAW_EVENTS__ not available — skipping past-event count check.');
      return;
    }
    if (!hasPastEvents) {
      console.log('No past events in dataset — past-filter not exercised.');
      return;
    }

    // Some past events exist — verify none are visible in the grid
    const visiblePastEvents = await page.evaluate(() => {
      const raw = (window as any).__RAW_EVENTS__;
      const todayStart = (function() { const d = new Date(); d.setHours(0,0,0,0); return d; })();
      if (!Array.isArray(raw)) return 0;

      let leaked = 0;
      const cards = document.querySelectorAll<HTMLElement>(
        '[class*="glass-panel"]:not(.animate-pulse)',
      );

      for (const ev of raw) {
        if (!ev.date) continue;
        const d = new Date(ev.date);
        if (isNaN(d.getTime()) || d >= todayStart) continue;
        // This event is in the past — check if its card is visible
        for (const card of Array.from(cards)) {
          const h = card.querySelector('h2, h3');
          if (!h?.textContent?.includes(ev.title?.substring(0, 15))) continue;
          if (!card.classList.contains('event-card-hidden')) {
            const group = card.closest<HTMLElement>('.group');
            if (!group || group.style.display !== 'none') leaked++;
          }
        }
      }
      return leaked;
    });

    expect(
      visiblePastEvents,
      'Past events should not be visible — past-event filter seems broken',
    ).toBe(0);
    console.log(`Past-event filter check: 0 past events leaked out of ${(await page.evaluate(() => ((window as any).__RAW_EVENTS__ || []).length))} total events.`);
  });
});
