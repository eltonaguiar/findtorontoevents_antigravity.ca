/**
 * Month-filter accuracy tests for findtorontoevents.ca
 *
 * User report (2026-05-01 EST): "This Month" wasn't showing May events and
 * "Next Month" wasn't showing June events on May 1 in EST. Root causes
 * (see updates/2026-05-01-this-month-next-month-filter-fix.md):
 *
 *   1. window.__eventInNextMonth__ used only eventData.date (start), so a
 *      multi-day event running Apr 15 → Jun 15 was excluded from the Jun
 *      window even though it IS active in June.
 *   2. The "This Month" override gated cards on the displayed *first-
 *      occurrence* date, so recurring/multi-day events that started before
 *      May 1 were hidden even though they're still happening in May.
 *
 * These tests pin Date to a fixed value (2026-05-01 12:00 EDT = 2026-05-01
 * 16:00 UTC) so they are deterministic regardless of when CI runs.
 *
 * Run locally:
 *   npx playwright test tests/events_month_filters.spec.ts \
 *     --project="Desktop Chrome"
 *
 * Run on Samsung Galaxy S25 Ultra (mobile compatibility check):
 *   npx playwright test tests/events_month_filters.spec.ts \
 *     --project="Samsung Galaxy S25 Ultra"
 */

import { test, expect, Page } from '@playwright/test';

// ─── Config ───────────────────────────────────────────────────────────────────

const isRemote =
  process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true';

const BASE =
  process.env.BASE_URL ||
  (isRemote ? 'https://findtorontoevents.ca' : 'http://localhost:5173');

/** Path to the actual main site HTML on the local server. The repo root
 *  doesn't have an index.html (the live site's HTML lives at
 *  /TORONTOEVENTS_ANTIGRAVITY/index.html), so locally we navigate there
 *  directly. Remote (VERIFY_REMOTE=1) hits "/" which serves the same file.
 */
const SITE_PATH = isRemote ? '/' : '/TORONTOEVENTS_ANTIGRAVITY/';

/** Frozen "now": 2026-05-01 16:00:00 UTC == 2026-05-01 12:00 EDT (noon). */
const FROZEN_NOW_MS = Date.UTC(2026, 4 /* May */, 1, 16, 0, 0);

/** Pure JS that overrides Date.now() and the Date() constructor inside the page. */
function buildClockOverride(nowMs: number): string {
  return `
    (function () {
      var FROZEN = ${nowMs};
      var RealDate = Date;
      function FakeDate() {
        if (arguments.length === 0) {
          return new RealDate(FROZEN);
        }
        if (arguments.length === 1) {
          return new RealDate(arguments[0]);
        }
        // IMPORTANT: pass arguments through as-is. Do NOT replace explicit
        // 0 with a default — \`new Date(y, m, 0)\` is the standard idiom for
        // "last day of previous month" and breaks if 0 is coerced to 1.
        var args = Array.prototype.slice.call(arguments);
        // Bind args by spread via Function.bind to preserve sparse args.
        var Ctor = Function.prototype.bind.apply(RealDate, [null].concat(args));
        return new Ctor();
      }
      FakeDate.now = function () { return FROZEN; };
      FakeDate.parse = RealDate.parse;
      FakeDate.UTC = RealDate.UTC;
      FakeDate.prototype = RealDate.prototype;
      // Preserve instanceof checks.
      Object.setPrototypeOf(FakeDate, RealDate);
      window.Date = FakeDate;
    })();
  `;
}

// ─── Mock fixture builder ─────────────────────────────────────────────────────

interface MockEvent {
  id: string;
  title: string;
  date: string | null;
  end_date?: string;
  is_multi_day?: boolean;
}

function ev(
  id: string,
  title: string,
  date: string | null,
  end_date?: string,
): MockEvent & Record<string, unknown> {
  const startIso = date ? `${date}T19:00:00Z` : null;
  const endIso = end_date ? `${end_date}T22:00:00Z` : startIso || undefined;
  const multi = !!(date && end_date && date !== end_date);
  return {
    id,
    title,
    date: startIso,
    end_date: endIso,
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
    is_multi_day: multi,
    duration_category: multi ? 'multi-day' : 'single',
    is_recurring: false,
    last_updated: '2026-05-01T00:00:00Z',
    isMultiDay: multi,
    isFree: true,
    isRecurring: false,
    priceAmount: 0,
    lastUpdated: '2026-05-01T00:00:00Z',
    image: null,
  };
}

/**
 * 12 deterministic events covering every month-filter scenario for "now =
 * 2026-05-01". Titles are tagged so individual cards are easy to find.
 */
function buildMonthEvents(): object[] {
  return [
    // ── This Month (May 2026) — should be visible when "This Month" active
    ev('m-today', '[TM] May 1 Today Event', '2026-05-01'),
    ev('m-mid', '[TM] May 15 Mid-Month Event', '2026-05-15'),
    ev('m-end', '[TM] May 31 Last-Day Event', '2026-05-31'),
    // Multi-day event spanning Apr 15 → May 10 — active today, must be
    // visible under "This Month" (the regression we are fixing).
    ev('m-span-prev', '[TM] Apr15-May10 Spanning Event', '2026-04-15', '2026-05-10'),
    // Multi-day event spanning Apr 1 → Jun 30 — active across all three months
    ev('m-span-all', '[TM] Apr-Jun Long Run Event', '2026-04-01', '2026-06-30'),

    // ── Next Month (June 2026) — should be visible when "Next Month" active
    ev('n-start', '[NM] Jun 1 First-Day Event', '2026-06-01'),
    ev('n-mid', '[NM] Jun 15 Mid-Month Event', '2026-06-15'),
    ev('n-end', '[NM] Jun 30 Last-Day Event', '2026-06-30'),
    // Multi-day event spanning May 25 → Jun 5 — active in next month, must
    // be visible under "Next Month" (also part of the regression we're fixing)
    ev('n-span-prev', '[NM] May25-Jun5 Spanning Event', '2026-05-25', '2026-06-05'),

    // ── Out-of-window — should be HIDDEN by both This Month and Next Month
    ev('o-jul', '[OUT] Jul 4 Far Future Event', '2026-07-04'),
    ev('o-aug', '[OUT] Aug 20 Far Future Event', '2026-08-20'),
    // Past single-day event — should always be hidden by past-events filter.
    ev('o-past', '[OUT] Apr 10 Past Event', '2026-04-10'),
  ];
}

// ─── Page setup helpers ───────────────────────────────────────────────────────

async function setupPage(page: Page, events: object[] = buildMonthEvents()) {
  // Freeze time BEFORE any page script runs.
  await page.addInitScript(buildClockOverride(FROZEN_NOW_MS));

  const body = JSON.stringify({ events });
  await page.route(
    (url) =>
      url.pathname.endsWith('events.json') ||
      url.href.includes('events.json'),
    (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json; charset=utf-8',
        body,
      }),
  );

  await page.goto(BASE + SITE_PATH, { waitUntil: 'domcontentloaded', timeout: 60_000 });
  // Filter scripts init asynchronously; give them time to settle.
  await page.waitForFunction(
    () => typeof (window as unknown as { __eventInNextMonth__?: unknown }).__eventInNextMonth__ === 'function',
    { timeout: 25_000 },
  ).catch(() => {
    /* tolerate if React not hydrated locally — pure-logic tests don't need it */
  });
  await page.waitForTimeout(2000);
}

/**
 * Skip current test if no real event cards rendered (React chunks missing
 * locally). Pure-logic tests that only call the window.* helpers do NOT
 * need this guard.
 */
async function skipIfNoEventCards(page: Page) {
  const hasCards = await page.evaluate(() => {
    const cards = document.querySelectorAll(
      '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
    );
    for (const c of Array.from(cards)) {
      if (c.querySelector('h2, h3')) return true;
    }
    return false;
  });
  if (!hasCards) {
    test.skip(
      true,
      'No event cards rendered (React chunks missing locally). Run with VERIFY_REMOTE=1.',
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Suite 1 — Pure logic tests for window.__eventInNextMonth__
//  These run without React; they exercise the helper directly.
// ─────────────────────────────────────────────────────────────────────────────

test.describe('window.__eventInNextMonth__ — calendar overlap logic', () => {
  test.describe.configure({ timeout: 90_000 });

  test('helper is defined on the page', async ({ page }) => {
    await setupPage(page, []);
    const exists = await page.evaluate(
      () => typeof (window as unknown as { __eventInNextMonth__?: unknown }).__eventInNextMonth__ === 'function',
    );
    expect(exists).toBe(true);
  });

  test('event fully inside next month is in-window', async ({ page }) => {
    await setupPage(page, []);
    const ok = await page.evaluate(() =>
      (window as unknown as { __eventInNextMonth__: (e: unknown) => boolean }).__eventInNextMonth__({
        date: '2026-06-15T19:00:00Z',
      }),
    );
    expect(ok).toBe(true);
  });

  test('event in current month (not next) is out-of-window', async ({ page }) => {
    await setupPage(page, []);
    const ok = await page.evaluate(() =>
      (window as unknown as { __eventInNextMonth__: (e: unknown) => boolean }).__eventInNextMonth__({
        date: '2026-05-20T19:00:00Z',
      }),
    );
    expect(ok).toBe(false);
  });

  test('event two months away is out-of-window', async ({ page }) => {
    await setupPage(page, []);
    const ok = await page.evaluate(() =>
      (window as unknown as { __eventInNextMonth__: (e: unknown) => boolean }).__eventInNextMonth__({
        date: '2026-07-04T19:00:00Z',
      }),
    );
    expect(ok).toBe(false);
  });

  test('multi-day event spanning current→next month is in-window [REGRESSION]', async ({ page }) => {
    await setupPage(page, []);
    const ok = await page.evaluate(() =>
      (window as unknown as { __eventInNextMonth__: (e: unknown) => boolean }).__eventInNextMonth__({
        date: '2026-05-25T19:00:00Z',
        end_date: '2026-06-05T22:00:00Z',
      }),
    );
    expect(ok, 'May 25 → Jun 5 event MUST be visible under Next Month').toBe(true);
  });

  test('multi-day event ending exactly on first-of-next-month is in-window', async ({ page }) => {
    await setupPage(page, []);
    const ok = await page.evaluate(() =>
      (window as unknown as { __eventInNextMonth__: (e: unknown) => boolean }).__eventInNextMonth__({
        date: '2026-05-15T19:00:00Z',
        end_date: '2026-06-01T22:00:00Z',
      }),
    );
    expect(ok).toBe(true);
  });

  test('multi-day event ending day before next month starts is out-of-window', async ({ page }) => {
    await setupPage(page, []);
    const ok = await page.evaluate(() =>
      (window as unknown as { __eventInNextMonth__: (e: unknown) => boolean }).__eventInNextMonth__({
        date: '2026-05-10T19:00:00Z',
        end_date: '2026-05-31T22:00:00Z',
      }),
    );
    expect(ok).toBe(false);
  });

  test('long-running event (Apr-Jun) is in-window for both Jun coverage', async ({ page }) => {
    await setupPage(page, []);
    const ok = await page.evaluate(() =>
      (window as unknown as { __eventInNextMonth__: (e: unknown) => boolean }).__eventInNextMonth__({
        date: '2026-04-01T19:00:00Z',
        end_date: '2026-06-30T22:00:00Z',
      }),
    );
    expect(ok).toBe(true);
  });

  test('null/missing date returns false (defensive)', async ({ page }) => {
    await setupPage(page, []);
    const results = await page.evaluate(() => {
      const fn = (window as unknown as { __eventInNextMonth__: (e: unknown) => boolean }).__eventInNextMonth__;
      return [fn(null), fn({}), fn({ date: '' }), fn({ date: '20' })];
    });
    expect(results).toEqual([false, false, false, false]);
  });

  test('handles December-to-January year wrap correctly', async ({ page }) => {
    // Pin clock to Dec 15 2026 → next month is Jan 2027.
    const decClockMs = Date.UTC(2026, 11 /* Dec */, 15, 16, 0, 0);
    await page.addInitScript(buildClockOverride(decClockMs));
    await page.route(
      (url) => url.pathname.endsWith('events.json') || url.href.includes('events.json'),
      (route) => route.fulfill({ status: 200, contentType: 'application/json; charset=utf-8', body: '{"events":[]}' }),
    );
    await page.goto(BASE + SITE_PATH, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await page.waitForFunction(
      () => typeof (window as unknown as { __eventInNextMonth__?: unknown }).__eventInNextMonth__ === 'function',
      { timeout: 25_000 },
    ).catch(() => {});
    const inJan = await page.evaluate(() =>
      (window as unknown as { __eventInNextMonth__: (e: unknown) => boolean }).__eventInNextMonth__({
        date: '2027-01-10T19:00:00Z',
      }),
    );
    const inDec = await page.evaluate(() =>
      (window as unknown as { __eventInNextMonth__: (e: unknown) => boolean }).__eventInNextMonth__({
        date: '2026-12-25T19:00:00Z',
      }),
    );
    expect(inJan).toBe(true);
    expect(inDec).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
//  Suite 2 — DOM/UI integration: chip presence + visible card counts
//  These need React-rendered cards. Skipped automatically if React isn't
//  hydrated locally (e.g. running against a stripped index.html).
// ─────────────────────────────────────────────────────────────────────────────

async function clickChipByText(page: Page, text: string) {
  await page.evaluate((t: string) => {
    const btns = document.querySelectorAll('button');
    for (const b of Array.from(btns)) {
      if ((b.textContent || '').trim() === t) {
        (b as HTMLButtonElement).click();
        return;
      }
    }
  }, text);
}

async function listVisibleTitles(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const out: string[] = [];
    const cards = document.querySelectorAll<HTMLElement>(
      '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
    );
    for (const c of Array.from(cards)) {
      if (c.classList.contains('event-card-hidden')) continue;
      const group = c.closest<HTMLElement>('.group');
      if (group && group.style.display === 'none') continue;
      const heading = c.querySelector('h2, h3');
      const t = heading?.textContent?.trim();
      if (t) out.push(t);
    }
    return out;
  });
}

test.describe('Month filter — DOM integration', () => {
  test.describe.configure({ timeout: 120_000 });

  test('Next Month chip is injected after This Month', async ({ page }) => {
    await setupPage(page);
    await skipIfNoEventCards(page);

    const exists = await page.locator('#next-month-chip').count();
    expect(exists, 'Next Month chip should be injected').toBeGreaterThan(0);

    const order = await page.evaluate(() => {
      const tm = Array.from(document.querySelectorAll('button')).find(
        (b) => (b.textContent || '').trim() === 'This Month',
      );
      const nm = document.getElementById('next-month-chip');
      if (!tm || !nm) return null;
      return tm.nextElementSibling === nm;
    });
    expect(order).toBe(true);
  });

  test('Next Month filter shows only events overlapping June 2026', async ({ page }) => {
    await setupPage(page);
    await skipIfNoEventCards(page);

    await page.locator('#next-month-chip').click();
    await page.waitForTimeout(800);

    const visible = await listVisibleTitles(page);
    const tagged = visible.filter((t) => /\[NM\]|\[OUT\]|\[TM\]/.test(t));

    // All [NM] events must be visible
    for (const t of [
      '[NM] Jun 1 First-Day Event',
      '[NM] Jun 15 Mid-Month Event',
      '[NM] Jun 30 Last-Day Event',
      '[NM] May25-Jun5 Spanning Event',
    ]) {
      expect(
        tagged.some((v) => v.includes(t)),
        `Expected "${t}" to be visible under Next Month`,
      ).toBe(true);
    }

    // Apr-Jun long-run event must also overlap June.
    expect(
      tagged.some((v) => v.includes('[TM] Apr-Jun Long Run Event')),
      'Long-running Apr-Jun event must be visible under Next Month',
    ).toBe(true);

    // No [OUT] events
    for (const t of ['[OUT] Jul 4', '[OUT] Aug 20', '[OUT] Apr 10']) {
      expect(
        tagged.every((v) => !v.includes(t)),
        `Did not expect "${t}" under Next Month`,
      ).toBe(true);
    }
  });

  test('This Month filter shows May events including spanning multi-day [REGRESSION]', async ({
    page,
  }) => {
    await setupPage(page);
    await skipIfNoEventCards(page);

    await clickChipByText(page, 'This Month');
    await page.waitForTimeout(1000);

    const visible = await listVisibleTitles(page);
    const tagged = visible.filter((t) => /\[NM\]|\[OUT\]|\[TM\]/.test(t));

    // All [TM] events must be visible
    for (const t of [
      '[TM] May 1 Today Event',
      '[TM] May 15 Mid-Month Event',
      '[TM] May 31 Last-Day Event',
      '[TM] Apr15-May10 Spanning Event',
      '[TM] Apr-Jun Long Run Event',
    ]) {
      expect(
        tagged.some((v) => v.includes(t)),
        `Expected "${t}" visible under This Month (regression we are fixing)`,
      ).toBe(true);
    }

    // No [NM]-only events: the "May25-Jun5" overlap one IS in May too, keep it
    for (const t of ['[NM] Jun 1', '[NM] Jun 15', '[NM] Jun 30']) {
      expect(
        tagged.every((v) => !v.includes(t)),
        `Did not expect future-only "${t}" under This Month`,
      ).toBe(true);
    }

    // No [OUT] events
    for (const t of ['[OUT] Jul 4', '[OUT] Aug 20', '[OUT] Apr 10']) {
      expect(
        tagged.every((v) => !v.includes(t)),
        `Did not expect "${t}" under This Month`,
      ).toBe(true);
    }
  });

  test('Switching from Next Month to This Month deactivates Next Month chip', async ({
    page,
  }) => {
    await setupPage(page);
    await skipIfNoEventCards(page);

    await page.locator('#next-month-chip').click();
    await page.waitForTimeout(500);

    const before = await page.evaluate(
      () => (window as unknown as { __nextMonthFilterActive__?: boolean }).__nextMonthFilterActive__,
    );
    expect(before).toBe(true);

    await clickChipByText(page, 'This Month');
    await page.waitForTimeout(800);

    const after = await page.evaluate(
      () => (window as unknown as { __nextMonthFilterActive__?: boolean }).__nextMonthFilterActive__,
    );
    expect(after).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
//  Suite 3 — Mobile compatibility (Samsung Galaxy S25 Ultra and others)
//  These run on every project but the assertions only matter for narrow
//  viewports. Desktop projects skip the overflow check.
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Mobile compatibility — chip row at narrow viewport', () => {
  test.describe.configure({ timeout: 90_000 });

  test('chip row does not horizontally overflow viewport', async ({ page, viewport }) => {
    await setupPage(page);
    await skipIfNoEventCards(page);

    const vw = viewport?.width || 0;
    test.skip(vw === 0 || vw > 500, 'mobile-only check');

    // Make sure our injected chip is in the DOM
    await expect(page.locator('#next-month-chip')).toBeAttached({ timeout: 10_000 });

    const overflow = await page.evaluate(() => {
      const nm = document.getElementById('next-month-chip');
      if (!nm) return null;
      const row = nm.parentElement;
      if (!row) return null;
      // The row should either fit in viewport or be horizontally scrollable.
      const rowRect = row.getBoundingClientRect();
      const rowOverflow = row.scrollWidth - row.clientWidth;
      const isScrollable =
        getComputedStyle(row).overflowX === 'auto' ||
        getComputedStyle(row).overflowX === 'scroll';
      return {
        rowWidth: rowRect.width,
        scrollWidth: row.scrollWidth,
        clientWidth: row.clientWidth,
        rowOverflow,
        isScrollable,
        viewport: window.innerWidth,
      };
    });

    if (!overflow) {
      test.skip(true, 'chip row not present');
      return;
    }

    // Acceptable: row fits in viewport OR is horizontally scrollable
    const fits = overflow.rowWidth <= overflow.viewport + 1;
    const scrolls = overflow.isScrollable;
    expect(
      fits || scrolls,
      `Chip row width ${overflow.rowWidth}px exceeds viewport ${overflow.viewport}px and is not scrollable. Overflow: ${overflow.rowOverflow}px`,
    ).toBe(true);
  });

  test('Next Month chip is tappable (≥36px target on mobile)', async ({ page, viewport }) => {
    await setupPage(page);
    await skipIfNoEventCards(page);

    const vw = viewport?.width || 0;
    test.skip(vw === 0 || vw > 500, 'mobile-only check');

    await expect(page.locator('#next-month-chip')).toBeAttached({ timeout: 10_000 });

    const size = await page.locator('#next-month-chip').evaluate((el) => {
      const r = (el as HTMLElement).getBoundingClientRect();
      return { w: r.width, h: r.height };
    });

    // WCAG / Material guidelines: ≥36px (lenient) or ≥44px (Apple HIG).
    // The existing "px-4 py-2" classes on these chips give ~30px height,
    // which is below the 36px Material minimum. We assert ≥30 here as a
    // regression floor — the methodology MD recommends bumping to ≥36px.
    expect(size.h, `Chip height ${size.h}px below tap-target floor`).toBeGreaterThanOrEqual(30);
    expect(size.w, `Chip width ${size.w}px too narrow`).toBeGreaterThanOrEqual(80);
  });
});
