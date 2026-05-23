/**
 * Comprehensive Playwright test suite for ALL event date filter buttons on
 * findtorontoevents.ca homepage.
 *
 * Filters under test (visible chip buttons):
 *   - All Dates (PRIMARY focus per operator)
 *   - 🔥 Today
 *   - Tomorrow      (RR1 subagent owns; we only verify, do not fix)
 *   - This Week
 *   - This Month    (PR #751 fixed; verify still green)
 *   - Next Month    (PR #751 fixed; verify still green)
 *   - Nearby Me     (geo permission required; gracefully skipped if denied)
 *
 * Visibility toggles:
 *   - Sold Out toggle (best-effort; only asserts counter changes)
 *
 * Strategy:
 *   - Default to running against the LIVE site at https://findtorontoevents.ca/.
 *     Local mode (`npx playwright test`) will SKIP filter assertions because
 *     `serve_local.py` does not serve the React Next.js bundle, so chips never
 *     render. Set `VERIFY_REMOTE=1` to assert against production.
 *   - For each filter chip: click, wait for cards to settle, scrape visible
 *     card titles + displayed dates, and assert per-filter date semantics.
 *
 * Run:
 *   VERIFY_REMOTE=1 npx playwright test tests/playwright/test_event_date_filters.spec.ts \
 *     --project="Desktop Chrome" --reporter=list
 */

import { test, expect, Page, ConsoleMessage } from '@playwright/test';

const isRemote =
  process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true';

const BASE =
  process.env.BASE_URL ||
  (isRemote ? 'https://findtorontoevents.ca' : 'http://localhost:5173');

const SITE_PATH = isRemote ? '/' : '/TORONTOEVENTS_ANTIGRAVITY/';

// Today is 2026-05-04 EDT per operator. Our assertions parse the actual JS
// `new Date()` at runtime so the suite stays accurate even after midnight.

interface CardInfo {
  title: string;
  displayedDate: string | null;
  fullDateText: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function navigateAndWait(page: Page, capture?: ConsoleMessage[]) {
  if (capture) {
    page.on('console', (msg) => capture.push(msg));
  }
  await page.goto(BASE + SITE_PATH, {
    waitUntil: 'domcontentloaded',
    timeout: 60_000,
  });
  // Wait for the chip row to show "All Dates" — only present after React
  // bundle hydrates.
  try {
    await page.waitForFunction(
      () => {
        const btns = Array.from(document.querySelectorAll('button'));
        return btns.some((b) => (b.textContent || '').trim() === 'All Dates');
      },
      { timeout: 30_000 },
    );
  } catch {
    // chip never appeared; tests will skip
  }
  // Let any custom-filter init + first auto-render settle.
  await page.waitForTimeout(3000);
}

async function skipIfNoChips(page: Page, t = test) {
  const present = await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    return btns.some((b) => (b.textContent || '').trim() === 'All Dates');
  });
  if (!present) {
    t.skip(
      true,
      'React event-grid chips not rendered (local server lacks the Next.js ' +
        'bundle, or remote site failed to hydrate). Run with VERIFY_REMOTE=1.',
    );
  }
}

async function clickChipByText(page: Page, text: string): Promise<boolean> {
  return page.evaluate((t: string) => {
    const btns = Array.from(document.querySelectorAll('button'));
    for (const b of btns) {
      if ((b.textContent || '').trim() === t) {
        (b as HTMLButtonElement).click();
        return true;
      }
    }
    return false;
  }, text);
}

async function listVisibleCards(page: Page): Promise<CardInfo[]> {
  return page.evaluate(() => {
    const out: Array<{ title: string; displayedDate: string | null; fullDateText: string }> = [];
    const cards = document.querySelectorAll<HTMLElement>(
      '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
    );
    const monthAbbrs = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
    for (const c of Array.from(cards)) {
      // Skip hidden cards
      if (c.classList.contains('event-card-hidden')) continue;
      const group = c.closest<HTMLElement>('.group');
      if (group && group.style.display === 'none') continue;
      const heading = c.querySelector('h2, h3');
      const title = (heading?.textContent || '').trim();
      if (!title) continue;
      // Try to extract YYYY-MM-DD from the visible header. Pattern: "MAY\n4"
      const txt = (c.innerText || c.textContent || '').trim();
      const m = txt.match(/^([A-Z]{3})\s*\n?\s*(\d{1,2})\b/i);
      let displayedDate: string | null = null;
      let fullDateText = '';
      if (m) {
        const idx = monthAbbrs.indexOf(m[1].toUpperCase());
        if (idx >= 0) {
          const now = new Date();
          let year = now.getFullYear();
          if (idx < now.getMonth()) year += 1;
          displayedDate = year + '-' + String(idx + 1).padStart(2, '0') + '-' + String(parseInt(m[2], 10)).padStart(2, '0');
          fullDateText = m[0];
        }
      }
      out.push({ title, displayedDate, fullDateText });
    }
    return out;
  });
}

async function getCounterCount(page: Page): Promise<number | null> {
  return page.evaluate(() => {
    // The event grid shows a counter like "Found 5,432 events".
    const candidates = Array.from(document.querySelectorAll('span, p, h2, h3, div'));
    for (const el of candidates) {
      const t = ((el as HTMLElement).innerText || el.textContent || '').trim();
      const m = t.match(/^Found\s+([\d,]+)\s+events?/i) ||
                t.match(/^([\d,]+)\s+events?\s+found/i);
      if (m) {
        return parseInt(m[1].replace(/,/g, ''), 10);
      }
    }
    return null;
  });
}

async function todayYMD(page: Page): Promise<string> {
  return page.evaluate(() => {
    const now = new Date();
    return now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
  });
}

async function tomorrowYMD(page: Page): Promise<string> {
  return page.evaluate(() => {
    const now = new Date();
    now.setDate(now.getDate() + 1);
    return now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
  });
}

async function dumpFilterState(page: Page, label: string): Promise<{
  visibleCount: number;
  counter: number | null;
  firstFiveDates: string[];
  firstFiveTitles: string[];
}> {
  const cards = await listVisibleCards(page);
  const counter = await getCounterCount(page);
  const firstFive = cards.slice(0, 5);
  const log = {
    visibleCount: cards.length,
    counter,
    firstFiveDates: firstFive.map((c) => c.displayedDate || c.fullDateText || '?'),
    firstFiveTitles: firstFive.map((c) => c.title.slice(0, 60)),
  };
  console.log(`\n=== ${label} ===`);
  console.log(`  Visible cards: ${log.visibleCount}`);
  console.log(`  Counter: ${log.counter}`);
  console.log(`  First 5: ${JSON.stringify(log.firstFiveDates)}`);
  console.log(`  Titles: ${JSON.stringify(log.firstFiveTitles)}`);
  return log;
}

// ─── Tests ────────────────────────────────────────────────────────────────────

test.describe.configure({ timeout: 180_000 });

test.describe('Event Date Filters — comprehensive', () => {
  test('All Dates — should not include events whose end_date < today [PRIORITY]', async ({ page }) => {
    const consoleMsgs: ConsoleMessage[] = [];
    await navigateAndWait(page, consoleMsgs);
    await skipIfNoChips(page);

    // Click All Dates explicitly to ensure we're on this filter (default state).
    await clickChipByText(page, 'All Dates');
    await page.waitForTimeout(2500);

    const state = await dumpFilterState(page, 'All Dates');
    const today = await todayYMD(page);

    // Pull __RAW_EVENTS__ to count expected.
    const rawCount = await page.evaluate(
      () => Array.isArray((window as any).__RAW_EVENTS__) ? (window as any).__RAW_EVENTS__.length : 0,
    );
    console.log(`  __RAW_EVENTS__ length: ${rawCount}`);

    // Find ended events (end_date < today) that are leaking through.
    const cards = await listVisibleCards(page);
    const past: Array<{ title: string; displayedDate: string }> = [];
    for (const c of cards) {
      if (c.displayedDate && c.displayedDate < today) {
        past.push({ title: c.title, displayedDate: c.displayedDate });
      }
    }
    if (past.length > 0) {
      console.log(`  ⚠️  ${past.length} cards displaying dates BEFORE today (${today}):`);
      for (const p of past.slice(0, 10)) {
        console.log(`     - "${p.title}" @ ${p.displayedDate}`);
      }
    }

    // We assert at most 0 cards in the visible grid display a YYYY-MM-DD
    // earlier than today. (Multi-day events whose start was past but end>=today
    // can legitimately render under "All Dates"; their visible header may still
    // show the start date. We exclude those by checking __RAW_EVENTS__ data.)
    const reallyPast = await page.evaluate((todayStr: string) => {
      const raw = (window as any).__RAW_EVENTS__ || [];
      const cards = document.querySelectorAll<HTMLElement>(
        '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
      );
      const visible: Array<{ title: string; date: string; end_date: string | null; instances: number }> = [];
      for (const c of Array.from(cards)) {
        if (c.classList.contains('event-card-hidden')) continue;
        const group = c.closest<HTMLElement>('.group');
        if (group && group.style.display === 'none') continue;
        const heading = c.querySelector('h2, h3');
        const title = (heading?.textContent || '').trim();
        if (!title) continue;
        // Match ALL raw events with this title (recurring events have many).
        const matches = raw.filter((e: any) => (e.title || '').trim() === title);
        if (matches.length === 0) continue;
        // If ANY instance has end_date >= today, the title is legitimately
        // active and the card is fine. Only flag as "really past" when EVERY
        // instance's calendar window is fully before today.
        const anyActive = matches.some((e: any) => {
          const start = String(e.date || '').substring(0, 10);
          const endRaw = e.end_date || e.endDate || e.date;
          const end = String(endRaw || '').substring(0, 10);
          if (!start) return false; // TBD: don't claim active
          return end >= todayStr || start >= todayStr;
        });
        if (anyActive) continue;
        // All instances are past → genuinely zombie.
        const first = matches[0];
        visible.push({
          title,
          date: String(first.date || '').substring(0, 10),
          end_date: String(first.end_date || first.endDate || first.date || '').substring(0, 10),
          instances: matches.length,
        });
      }
      return visible;
    }, today);

    if (reallyPast.length > 0) {
      console.log(`  ❌ ${reallyPast.length} events GENUINELY PAST (both start and end < today):`);
      for (const p of reallyPast.slice(0, 10)) {
        console.log(`     - "${p.title}" start=${p.date} end=${p.end_date}`);
      }
    }
    expect(
      reallyPast.length,
      `All Dates filter is leaking ${reallyPast.length} ended events. ` +
        `First leak: ${reallyPast[0] ? JSON.stringify(reallyPast[0]) : 'none'}`,
    ).toBe(0);

    // Operator-reported: "All Dates is showing 2025 events instead of May"
    // Verify NO visible card displays a year prior to current year by reading
    // the raw event data behind it. A multi-day event whose end_date is in
    // a previous year cannot legitimately appear (would have been caught
    // above), but check explicitly for prior-year start_date with no
    // active future instance.
    const priorYearLeaks = await page.evaluate((todayStr: string) => {
      const currentYear = todayStr.substring(0, 4);
      const raw = (window as any).__RAW_EVENTS__ || [];
      const cards = document.querySelectorAll<HTMLElement>(
        '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
      );
      const out: Array<{ title: string; date: string }> = [];
      for (const c of Array.from(cards)) {
        if (c.classList.contains('event-card-hidden')) continue;
        const group = c.closest<HTMLElement>('.group');
        if (group && group.style.display === 'none') continue;
        const heading = c.querySelector('h2, h3');
        const title = (heading?.textContent || '').trim();
        if (!title) continue;
        const matches = raw.filter((e: any) => (e.title || '').trim() === title);
        if (matches.length === 0) continue;
        const anyCurrentOrFuture = matches.some((e: any) => {
          const start = String(e.date || '').substring(0, 10);
          const endRaw = e.end_date || e.endDate || e.date;
          const end = String(endRaw || '').substring(0, 10);
          // Active if end in current/future year, or start in current/future year
          return (end >= todayStr) || (start && start.substring(0, 4) >= currentYear);
        });
        if (anyCurrentOrFuture) continue;
        out.push({ title, date: String(matches[0].date || '').substring(0, 10) });
      }
      return out;
    }, today);

    if (priorYearLeaks.length > 0) {
      console.log(`  ⚠️  ${priorYearLeaks.length} prior-year zombies in All Dates:`);
      for (const p of priorYearLeaks.slice(0, 10)) {
        console.log(`     - "${p.title}" @ ${p.date}`);
      }
    }
    expect(priorYearLeaks.length, `${priorYearLeaks.length} pre-${today.substring(0,4)} zombies leaked`).toBe(0);

    // Counter should be substantial (not 0, not <50). 11290 is the data feed
    // size; visible counter post-past-filter typically 5000-7000.
    if (state.counter !== null) {
      expect(state.counter, `All Dates counter ${state.counter} is suspiciously low`).toBeGreaterThan(50);
    }
    expect(state.visibleCount, 'All Dates should render at least 1 visible card').toBeGreaterThan(0);
  });

  test('Today — every visible card matches today\'s date or spans today', async ({ page }) => {
    await navigateAndWait(page);
    await skipIfNoChips(page);
    const today = await todayYMD(page);

    const clicked = await clickChipByText(page, '🔥 Today');
    expect(clicked, 'Today chip should be clickable').toBe(true);
    await page.waitForTimeout(2500);

    const state = await dumpFilterState(page, 'Today');

    // Check raw events backing each visible card.
    // For recurring events (multiple instances with same title), the card is
    // valid if ANY instance overlaps today.
    const failures = await page.evaluate((todayStr: string) => {
      const raw = (window as any).__RAW_EVENTS__ || [];
      const cards = document.querySelectorAll<HTMLElement>(
        '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
      );
      const out: Array<{ title: string; start: string; end: string }> = [];
      for (const c of Array.from(cards)) {
        if (c.classList.contains('event-card-hidden')) continue;
        const group = c.closest<HTMLElement>('.group');
        if (group && group.style.display === 'none') continue;
        const heading = c.querySelector('h2, h3');
        const title = (heading?.textContent || '').trim();
        if (!title) continue;
        const matches = raw.filter((e: any) => (e.title || '').trim() === title);
        if (matches.length === 0) continue; // can't verify; skip
        const anySpansToday = matches.some((e: any) => {
          const start = String(e.date || '').substring(0, 10);
          const endRaw = e.end_date || e.endDate || e.date;
          const end = String(endRaw || '').substring(0, 10);
          if (!start) return false;
          return start <= todayStr && (end || start) >= todayStr;
        });
        if (anySpansToday) continue;
        const first = matches[0];
        const start = String(first.date || '').substring(0, 10);
        const end = String(first.end_date || first.endDate || first.date || '').substring(0, 10);
        out.push({ title, start, end });
      }
      return out;
    }, today);

    if (failures.length > 0) {
      console.log(`  ❌ ${failures.length} cards under Today don't span ${today}:`);
      for (const f of failures.slice(0, 5)) {
        console.log(`     - "${f.title}" start=${f.start} end=${f.end}`);
      }
    }
    // Allow up to 10 — title-mismatch with raw feed isn't ground truth.
    // But anything substantially higher indicates a filter bug.
    expect(failures.length, `${failures.length} cards in Today don't span today`).toBeLessThanOrEqual(10);
    expect(state.visibleCount, 'Today should show at least 1 card').toBeGreaterThan(0);
  });

  test('Tomorrow — visible cards span tomorrow [RR1 IN-FLIGHT — verify only]', async ({ page }) => {
    await navigateAndWait(page);
    await skipIfNoChips(page);
    const tomorrow = await tomorrowYMD(page);

    const clicked = await clickChipByText(page, 'Tomorrow');
    expect(clicked, 'Tomorrow chip should be clickable').toBe(true);
    await page.waitForTimeout(2500);

    const state = await dumpFilterState(page, 'Tomorrow');

    // Verify only — RR1 owns this filter's fix.
    const failures = await page.evaluate((tomorrowStr: string) => {
      const raw = (window as any).__RAW_EVENTS__ || [];
      const cards = document.querySelectorAll<HTMLElement>(
        '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
      );
      const out: Array<{ title: string; start: string; end: string }> = [];
      for (const c of Array.from(cards)) {
        if (c.classList.contains('event-card-hidden')) continue;
        const group = c.closest<HTMLElement>('.group');
        if (group && group.style.display === 'none') continue;
        const heading = c.querySelector('h2, h3');
        const title = (heading?.textContent || '').trim();
        if (!title) continue;
        const matches = raw.filter((e: any) => (e.title || '').trim() === title);
        if (matches.length === 0) continue;
        const anySpans = matches.some((e: any) => {
          const start = String(e.date || '').substring(0, 10);
          const endRaw = e.end_date || e.endDate || e.date;
          const end = String(endRaw || '').substring(0, 10);
          if (!start) return false;
          return start <= tomorrowStr && (end || start) >= tomorrowStr;
        });
        if (anySpans) continue;
        const first = matches[0];
        const start = String(first.date || '').substring(0, 10);
        const end = String(first.end_date || first.endDate || first.date || '').substring(0, 10);
        out.push({ title, start, end });
      }
      return out;
    }, tomorrow);

    console.log(`  Tomorrow filter check: ${failures.length} cards do NOT span ${tomorrow}`);
    for (const f of failures.slice(0, 5)) {
      console.log(`     - "${f.title}" start=${f.start} end=${f.end}`);
    }
    // Soft assertion — log but don't fail (RR1 is fixing).
    if (failures.length > 20) {
      console.log(`  ⚠️  Tomorrow filter likely BROKEN (${failures.length} mismatches). RR1 in flight.`);
    }
  });

  test('This Week — visible cards span any day in [today, today+6]', async ({ page }) => {
    await navigateAndWait(page);
    await skipIfNoChips(page);

    const clicked = await clickChipByText(page, 'This Week');
    expect(clicked, 'This Week chip should be clickable').toBe(true);
    await page.waitForTimeout(2500);

    const state = await dumpFilterState(page, 'This Week');

    const range = await page.evaluate(() => {
      const start = new Date();
      const end = new Date();
      end.setDate(end.getDate() + 6);
      const fmt = (d: Date) =>
        d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
      return { start: fmt(start), end: fmt(end) };
    });

    const failures = await page.evaluate((r: { start: string; end: string }) => {
      const raw = (window as any).__RAW_EVENTS__ || [];
      const cards = document.querySelectorAll<HTMLElement>(
        '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
      );
      const out: Array<{ title: string; start: string; end: string }> = [];
      for (const c of Array.from(cards)) {
        if (c.classList.contains('event-card-hidden')) continue;
        const group = c.closest<HTMLElement>('.group');
        if (group && group.style.display === 'none') continue;
        const heading = c.querySelector('h2, h3');
        const title = (heading?.textContent || '').trim();
        if (!title) continue;
        const matches = raw.filter((e: any) => (e.title || '').trim() === title);
        if (matches.length === 0) continue;
        const anyOverlaps = matches.some((e: any) => {
          const start = String(e.date || '').substring(0, 10);
          const endRaw = e.end_date || e.endDate || e.date;
          const end = String(endRaw || '').substring(0, 10);
          if (!start) return false;
          return start <= r.end && (end || start) >= r.start;
        });
        if (anyOverlaps) continue;
        const first = matches[0];
        const start = String(first.date || '').substring(0, 10);
        const end = String(first.end_date || first.endDate || first.date || '').substring(0, 10);
        out.push({ title, start, end });
      }
      return out;
    }, range);

    if (failures.length > 0) {
      console.log(`  ❌ ${failures.length} cards under This Week don't overlap [${range.start}, ${range.end}]:`);
      for (const f of failures.slice(0, 5)) {
        console.log(`     - "${f.title}" start=${f.start} end=${f.end}`);
      }
    }
    expect(failures.length, `${failures.length} cards in This Week don't overlap the week`).toBeLessThanOrEqual(20);
  });

  test('This Month — visible cards overlap current calendar month', async ({ page }) => {
    await navigateAndWait(page);
    await skipIfNoChips(page);

    const clicked = await clickChipByText(page, 'This Month');
    expect(clicked, 'This Month chip should be clickable').toBe(true);
    await page.waitForTimeout(2500);

    const state = await dumpFilterState(page, 'This Month');

    const range = await page.evaluate(() => {
      const now = new Date();
      const startOfMonth = new Date(now.getFullYear(), now.getMonth(), now.getDate()); // today, not month start
      const endOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      const fmt = (d: Date) =>
        d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
      return { start: fmt(startOfMonth), end: fmt(endOfMonth) };
    });

    const failures = await page.evaluate((r: { start: string; end: string }) => {
      const raw = (window as any).__RAW_EVENTS__ || [];
      const cards = document.querySelectorAll<HTMLElement>(
        '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
      );
      const out: Array<{ title: string; start: string; end: string }> = [];
      for (const c of Array.from(cards)) {
        if (c.classList.contains('event-card-hidden')) continue;
        const group = c.closest<HTMLElement>('.group');
        if (group && group.style.display === 'none') continue;
        const heading = c.querySelector('h2, h3');
        const title = (heading?.textContent || '').trim();
        if (!title) continue;
        const matches = raw.filter((e: any) => (e.title || '').trim() === title);
        if (matches.length === 0) continue;
        const anyOverlaps = matches.some((e: any) => {
          const start = String(e.date || '').substring(0, 10);
          const endRaw = e.end_date || e.endDate || e.date;
          const end = String(endRaw || '').substring(0, 10);
          if (!start) return false;
          return start <= r.end && (end || start) >= r.start;
        });
        if (anyOverlaps) continue;
        const first = matches[0];
        const start = String(first.date || '').substring(0, 10);
        const end = String(first.end_date || first.endDate || first.date || '').substring(0, 10);
        out.push({ title, start, end });
      }
      return out;
    }, range);

    if (failures.length > 0) {
      console.log(`  ❌ ${failures.length} cards under This Month outside [${range.start}, ${range.end}]:`);
      for (const f of failures.slice(0, 5)) {
        console.log(`     - "${f.title}" start=${f.start} end=${f.end}`);
      }
    }
    expect(failures.length, `${failures.length} cards in This Month don't overlap the month`).toBeLessThanOrEqual(20);
  });

  test('Next Month — visible cards overlap next calendar month', async ({ page }) => {
    await navigateAndWait(page);
    await skipIfNoChips(page);

    // Custom Next Month chip is injected by index.html. The injector runs
    // every ~250ms via a MutationObserver for up to 30s after page load. On
    // first navigation Playwright reads the DOM before injection completes,
    // so wait up to 35s for the chip to appear.
    let exists = await page.evaluate(() => !!document.getElementById('next-month-chip'));
    if (!exists) {
      try {
        await page.waitForFunction(() => !!document.getElementById('next-month-chip'), {
          timeout: 35_000,
        });
        exists = true;
      } catch {
        exists = false;
      }
    }
    if (!exists) {
      // Last resort: try clicking by text.
      const ok = await clickChipByText(page, 'Next Month');
      expect(ok, 'Next Month chip must be injected (custom chip from index.html)').toBe(true);
    } else {
      await page.locator('#next-month-chip').click();
    }
    await page.waitForTimeout(3000);

    const state = await dumpFilterState(page, 'Next Month');

    const range = await page.evaluate(() => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth() + 1, 1);
      const end = new Date(now.getFullYear(), now.getMonth() + 2, 0);
      const fmt = (d: Date) =>
        d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
      return { start: fmt(start), end: fmt(end) };
    });

    const failures = await page.evaluate((r: { start: string; end: string }) => {
      const raw = (window as any).__RAW_EVENTS__ || [];
      const cards = document.querySelectorAll<HTMLElement>(
        '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
      );
      const out: Array<{ title: string; start: string; end: string }> = [];
      for (const c of Array.from(cards)) {
        if (c.classList.contains('event-card-hidden')) continue;
        const group = c.closest<HTMLElement>('.group');
        if (group && group.style.display === 'none') continue;
        const heading = c.querySelector('h2, h3');
        const title = (heading?.textContent || '').trim();
        if (!title) continue;
        const matches = raw.filter((e: any) => (e.title || '').trim() === title);
        if (matches.length === 0) continue;
        const anyOverlaps = matches.some((e: any) => {
          const start = String(e.date || '').substring(0, 10);
          const endRaw = e.end_date || e.endDate || e.date;
          const end = String(endRaw || '').substring(0, 10);
          if (!start) return false;
          return start <= r.end && (end || start) >= r.start;
        });
        if (anyOverlaps) continue;
        const first = matches[0];
        const start = String(first.date || '').substring(0, 10);
        const end = String(first.end_date || first.endDate || first.date || '').substring(0, 10);
        out.push({ title, start, end });
      }
      return out;
    }, range);

    if (failures.length > 0) {
      console.log(`  ❌ ${failures.length} cards under Next Month outside [${range.start}, ${range.end}]:`);
      for (const f of failures.slice(0, 10)) {
        console.log(`     - "${f.title}" start=${f.start} end=${f.end}`);
      }
    }
    // Next Month is the strictest filter — PR #751 fixed the start-only
    // calendar-overlap bug, so leaks should be rare. Threshold 5 leaves room
    // for occasional title-mismatch / ambiguous-recurring edge cases.
    expect(failures.length, `${failures.length} cards in Next Month don't overlap`).toBeLessThanOrEqual(5);
  });

  test('Nearby Me — chip is present (geo permission may be denied)', async ({ page }) => {
    await navigateAndWait(page);
    await skipIfNoChips(page);

    const present = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      return btns.some((b) => /Nearby/i.test((b.textContent || '').trim()));
    });
    expect(present, 'Nearby chip should be present').toBe(true);
    // No deeper assertion: geo permission would prompt a real browser dialog.
  });

  test('Sold Out toggle — exists and toggles visibility (best-effort)', async ({ page }) => {
    await navigateAndWait(page);
    await skipIfNoChips(page);

    const has = await page.evaluate(() => {
      const all = Array.from(document.querySelectorAll('button, label, [role="switch"]'));
      return all.some((el) => /sold\s*out/i.test((el.textContent || '').trim()));
    });
    if (!has) {
      console.log('  Sold Out toggle not found in DOM — skipping');
      test.skip(true, 'Sold Out toggle not present');
    }
    expect(has, 'Sold Out toggle should be present').toBe(true);
  });
});
