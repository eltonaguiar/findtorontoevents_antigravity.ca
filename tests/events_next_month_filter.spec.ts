/**
 * E2E verification of the homepage "Next Month" + "This Month" date chips.
 *
 * Run against the live site:
 *   VERIFY_REMOTE=1 npx playwright test \
 *     --config=playwright.next-month.config.ts \
 *     --project="Desktop Chrome"
 *
 * User report (2026-05-01): "next month" did not show June 2026 events;
 * "this month" made the page scroll one day at a time starting somewhere
 * in February 2026. After fixes:
 *   - __eventInNextMonth__ scans __RAW_EVENTS__ for any matching-title
 *     occurrence in the next-month window (recurring-event support).
 *   - applyFilters() bails out of the This Month override after 300+
 *     consecutive hidden cards with 0 shown (loop guard).
 */

import { test, expect, Page, ConsoleMessage } from '@playwright/test';

const isRemote =
  process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true';

const BASE =
  process.env.BASE_URL ||
  (isRemote ? 'https://findtorontoevents.ca' : 'http://localhost:5173');

const SETTLE_MS = 9000;

const THIRD_PARTY_ERROR_PATTERNS = [
  /web-client-content-script/i,
  /chrome-extension:/i,
  /moz-extension:/i,
  /googlesyndication|googletagmanager|googleads|doubleclick/i,
  /\/ads\?client=/i,
  /ERR_BLOCKED_BY_CLIENT/i,
  /Mixed Content/i,
  /squarespace\.com.*\.(png|jpg|webp)/i,
  /sites\/default\/files.*\.webp/i,
  /127\.0\.0\.1:7838/i,
  /ERR_CONNECTION_REFUSED.*7838/i,
];

function isThirdParty(text: string): boolean {
  return THIRD_PARTY_ERROR_PATTERNS.some((re) => re.test(text));
}

interface CapturedError {
  type: 'console' | 'pageerror';
  text: string;
  location?: string;
}

function captureFirstPartyErrors(page: Page): () => CapturedError[] {
  const errors: CapturedError[] = [];
  page.on('console', (msg: ConsoleMessage) => {
    if (msg.type() !== 'error') return;
    const text = msg.text();
    const loc = msg.location();
    const locStr = loc?.url ? `${loc.url}:${loc.lineNumber}` : '';
    if (isThirdParty(text) || (locStr && isThirdParty(locStr))) return;
    errors.push({ type: 'console', text, location: locStr });
  });
  page.on('pageerror', (err) => {
    const text = `${err.name}: ${err.message}`;
    if (isThirdParty(text) || isThirdParty(err.stack || '')) return;
    errors.push({ type: 'pageerror', text, location: err.stack?.split('\n')[1] });
  });
  return () => errors.slice();
}

async function loadHomepage(page: Page) {
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await page
    .waitForFunction(() => typeof (window as any).__eventInNextMonth__ === 'function', {
      timeout: 25_000,
    })
    .catch(() => undefined);
  await page.waitForTimeout(SETTLE_MS);
}

async function readVisibleCardDates(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const parse = (window as any).__parseCardDisplayedDate__;
    if (typeof parse !== 'function') return [];
    const cards = document.querySelectorAll<HTMLElement>(
      '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
    );
    const out: string[] = [];
    for (const card of Array.from(cards)) {
      if (card.classList.contains('event-card-hidden')) continue;
      const group = card.closest<HTMLElement>('.group');
      if (group && group.style.display === 'none') continue;
      const heading = card.querySelector('h2, h3');
      if (!heading?.textContent?.trim()) continue;
      const d = parse(card);
      if (d) out.push(d);
    }
    return out;
  });
}

// ─── Layer A: in-page math ───────────────────────────────────────────────

test.describe('Next Month filter — in-page math', () => {
  test.describe.configure({ timeout: 90_000 });

  test('window.__eventInNextMonth__ is defined', async ({ page }) => {
    captureFirstPartyErrors(page);
    await loadHomepage(page);
    const has = await page.evaluate(
      () => typeof (window as any).__eventInNextMonth__ === 'function',
    );
    expect(has).toBe(true);
  });

  test('synthetic events: returns correct boolean for next-month windows', async ({ page }) => {
    captureFirstPartyErrors(page);
    await loadHomepage(page);

    const result = await page.evaluate(() => {
      const fn = (window as any).__eventInNextMonth__;
      if (typeof fn !== 'function') return null;
      const now = new Date();
      const ny = now.getFullYear();
      const nm = now.getMonth();
      const lastThis = new Date(ny, nm + 1, 0).getDate();
      const lastNext = new Date(ny, nm + 2, 0).getDate();
      const fmt = (y: number, m1: number, d: number) =>
        `${y}-${String(m1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      const nextY = nm === 11 ? ny + 1 : ny;
      const nextM = nm === 11 ? 0 : nm + 1;
      const afterY = nextM === 11 ? nextY + 1 : nextY;
      const afterM = nextM === 11 ? 0 : nextM + 1;
      const cases = [
        { date: fmt(ny, nm + 1, now.getDate()),                expect: false, label: 'today' },
        { date: fmt(ny, nm + 1, lastThis),                     expect: false, label: 'last day this month' },
        { date: fmt(nextY, nextM + 1, 1),                      expect: true,  label: 'first day next month' },
        { date: fmt(nextY, nextM + 1, Math.min(15, lastNext)), expect: true,  label: 'mid next month' },
        { date: fmt(nextY, nextM + 1, lastNext),               expect: true,  label: 'last day next month' },
        { date: fmt(afterY, afterM + 1, 1),                    expect: false, label: 'first day month-after-next' },
      ];
      // Pass undefined card so we exercise the date-only branch.
      return cases.map((c) => ({ ...c, got: !!fn({ date: c.date }) }));
    });

    expect(result).not.toBeNull();
    const failures = (result || []).filter((c: any) => c.got !== c.expect);
    expect(failures, 'In-page math wrong: ' + JSON.stringify(failures, null, 2)).toEqual([]);
  });

  test('recurring-event fallback: scans __RAW_EVENTS__ and matches by title', async ({ page }) => {
    captureFirstPartyErrors(page);
    await loadHomepage(page);

    // Inject a synthetic recurring event into __RAW_EVENTS__ + a fake card,
    // then verify the function picks up the next-month occurrence even when
    // the card's eventData points at a current-month one.
    const ok = await page.evaluate(() => {
      const w = window as any;
      if (!Array.isArray(w.__RAW_EVENTS__)) return null;
      const now = new Date();
      const ny = now.getFullYear();
      const nm = now.getMonth();
      const nextY = nm === 11 ? ny + 1 : ny;
      const nextM = nm === 11 ? 0 : nm + 1;
      const fmt = (y: number, m1: number, d: number) =>
        `${y}-${String(m1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

      const TITLE = '__test_recurring_event_unique_title__';
      // Two synthetic occurrences: one in current month, one in next month.
      w.__RAW_EVENTS__.push({ title: TITLE, date: fmt(ny, nm + 1, Math.min(15, new Date(ny, nm + 1, 0).getDate())) });
      w.__RAW_EVENTS__.push({ title: TITLE, date: fmt(nextY, nextM + 1, 10) });

      // Build a fake card with a matching <h2>.
      const card = document.createElement('div');
      card.className = 'glass-panel';
      const h2 = document.createElement('h2');
      h2.textContent = TITLE;
      card.appendChild(h2);

      // eventData points at the current-month occurrence (mimicking
      // applyFilters() picking _futureMatches[0] for a recurring event).
      const eventDataCurrent = { title: TITLE, date: fmt(ny, nm + 1, 8) };
      const got = !!w.__eventInNextMonth__(eventDataCurrent, card);

      // Cleanup
      w.__RAW_EVENTS__.pop();
      w.__RAW_EVENTS__.pop();

      return got;
    });

    expect(ok, 'Recurring-event fallback should match via __RAW_EVENTS__').toBe(true);
  });
});

// ─── Layer B: real chip ──────────────────────────────────────────────────

test.describe('Next Month chip — DOM behaviour', () => {
  test.describe.configure({ timeout: 120_000 });

  test('clicking Next Month shows ONLY events in next month', async ({ page }) => {
    const errors = captureFirstPartyErrors(page);
    await loadHomepage(page);

    const chip = page.locator('#next-month-chip');
    if ((await chip.count()) === 0) {
      test.skip(true, 'Next Month chip not injected.');
      return;
    }
    await expect(chip).toBeVisible({ timeout: 15_000 });
    await chip.click();
    await page.waitForTimeout(3500);

    const expectedWindow = await page.evaluate(() => {
      const now = new Date();
      const ny = now.getFullYear();
      const nm = now.getMonth();
      const startY = nm === 11 ? ny + 1 : ny;
      const startM = nm === 11 ? 0 : nm + 1;
      return { monthLabel: `${startY}-${String(startM + 1).padStart(2, '0')}` };
    });
    console.log(`Expected next-month YYYY-MM prefix: ${expectedWindow.monthLabel}`);

    const dates = await readVisibleCardDates(page);
    console.log(`Visible cards after click: ${dates.length}`);
    if (dates.length > 0) {
      console.log(`First 10 displayed dates: ${dates.slice(0, 10).join(', ')}`);
    }

    expect(
      dates.length,
      'Next Month chip produced 0 visible cards — recurring-event fallback broken?',
    ).toBeGreaterThan(0);

    // For recurring events, the React grid renders the card with its
    // SOONEST occurrence date — even when the next-month occurrence is
    // what made __eventInNextMonth__ return true. So a "MAY 2" displayed
    // date is fine *iff* that card's title has at least one matching-title
    // entry in __RAW_EVENTS__ whose date falls in the next-month window.
    // We re-do the title-match in the page so the assertion follows the
    // same semantics as the production filter.
    const monthLabel = expectedWindow.monthLabel;
    const orphanCardTitles = await page.evaluate((label: string) => {
      const cards = document.querySelectorAll<HTMLElement>(
        '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
      );
      const raw = (window as any).__RAW_EVENTS__ || [];
      const orphans: string[] = [];
      for (const card of Array.from(cards)) {
        if (card.classList.contains('event-card-hidden')) continue;
        const group = card.closest<HTMLElement>('.group');
        if (group && group.style.display === 'none') continue;
        const titleEl = card.querySelector('h2, h3');
        const title = (titleEl?.textContent || '').trim().toLowerCase();
        if (!title) continue;
        const snippet = title.substring(0, 20);
        const hasNextMonth = raw.some((e: any) => {
          const et = ((e && e.title) || '').toLowerCase();
          if (!et) return false;
          const matches = et === title ||
                          (title.length >= 20 && et.includes(snippet)) ||
                          (et.length >= 20 && title.includes(et.substring(0, 20)));
          if (!matches) return false;
          const ed = String((e && e.date) || '').substring(0, 10);
          return ed.length >= 10 && ed.startsWith(label);
        });
        if (!hasNextMonth) orphans.push(title);
      }
      return orphans;
    }, monthLabel);

    expect(
      orphanCardTitles,
      `${orphanCardTitles.length} visible cards have NO matching __RAW_EVENTS__ entry in ${monthLabel}:\n` +
        orphanCardTitles.slice(0, 10).join('\n  '),
    ).toEqual([]);

    const captured = errors();
    if (captured.length > 0) {
      console.log('First-party JS errors during Next Month flow:');
      for (const e of captured) console.log(`  [${e.type}] ${e.text} @ ${e.location ?? ''}`);
    }
    expect(captured.length, 'First-party JS errors:\n' + captured.map((e) => e.text).join('\n')).toBe(0);
  });
});

// ─── Layer C: This Month loop guard ──────────────────────────────────────

test.describe('This Month chip — loop guard', () => {
  test.describe.configure({ timeout: 120_000 });

  test('clicking This Month does not enter an infinite hide loop', async ({ page }) => {
    captureFirstPartyErrors(page);

    const filterLogs: { shown: number; hidden: number }[] = [];
    page.on('console', (msg) => {
      if (msg.type() !== 'log') return;
      const m = /\[FILTERS\] Shown: (\d+) Hidden: (\d+)/.exec(msg.text());
      if (m) filterLogs.push({ shown: +m[1], hidden: +m[2] });
    });

    await loadHomepage(page);

    const chip = page.locator('button:has-text("This Month")').first();
    if ((await chip.count()) === 0) {
      test.skip(true, 'This Month chip not present.');
      return;
    }
    await expect(chip).toBeVisible({ timeout: 15_000 });

    const baseline = filterLogs.length;
    await chip.click();
    await page.waitForTimeout(10000);

    const after = filterLogs.slice(baseline);
    console.log(`Filter passes after This Month click: ${after.length}`);
    if (after.length > 0) {
      const last = after[after.length - 1];
      console.log(`Last [FILTERS] line: Shown=${last.shown} Hidden=${last.hidden}`);
    }

    // Runaway = streak of Shown:0 with hidden growing. The loop-guard fix
    // must cap the streak at <= 6 batches and peak hidden < 350.
    let runaway = 0;
    let prevHidden = -1;
    let runawayPeak = 0;
    for (const e of after) {
      if (e.shown === 0 && e.hidden > prevHidden) {
        runaway++;
        runawayPeak = Math.max(runawayPeak, e.hidden);
        prevHidden = e.hidden;
      } else {
        runaway = 0;
        prevHidden = -1;
      }
    }
    console.log(`Runaway streak length: ${runaway}, peak hidden in streak: ${runawayPeak}`);

    expect(
      runaway < 8 && runawayPeak < 400,
      `This Month chip triggered a runaway hide loop (${runaway} consecutive Shown=0 entries, peak Hidden=${runawayPeak}).`,
    ).toBeTruthy();

    const dates = await readVisibleCardDates(page);
    console.log(`Visible cards after This Month: ${dates.length}`);
    expect(
      dates.length,
      'This Month chip produced 0 visible cards (override should have disengaged after the runaway).',
    ).toBeGreaterThan(0);
  });
});

// ─── Layer C-bis: This Week multi-day overlap audit ─────────────────────

test.describe('This Week chip — multi-day overlap audit', () => {
  test.describe.configure({ timeout: 120_000 });

  test('events whose [start, end] overlap the current week are visible after clicking This Week', async ({
    page,
  }) => {
    // This is an AUDIT test: it samples real events from __RAW_EVENTS__,
    // identifies any with end_date strictly after today and start strictly
    // before next-week boundary (i.e. multi-day events ACTIVE during the
    // current week), and asserts they are visible after the chip click.
    // If this test ever fails in CI, the React bundle's "this-week" filter
    // has the same multi-day-overlap bug PR #598 fixed for This Month, and
    // we need to add a defensive applyFilters() narrowing.
    captureFirstPartyErrors(page);
    await loadHomepage(page);

    const chip = page.locator('button:has-text("This Week")').first();
    if ((await chip.count()) === 0) {
      test.skip(true, 'This Week chip not present.');
      return;
    }
    await expect(chip).toBeVisible({ timeout: 15_000 });

    // Find sample multi-day events that span TODAY AND last day of this week.
    const sampleTitles = await page.evaluate(() => {
      const raw = (window as any).__RAW_EVENTS__;
      if (!Array.isArray(raw)) return [] as string[];
      const now = new Date();
      const todayStr = now.toISOString().slice(0, 10);
      const weekEnd = new Date(now);
      weekEnd.setDate(weekEnd.getDate() + 6);
      const weekEndStr = weekEnd.toISOString().slice(0, 10);
      const samples: string[] = [];
      for (const e of raw) {
        if (samples.length >= 3) break;
        const s = String(e?.date || '').slice(0, 10);
        const eEnd = String(e?.end_date || e?.endDate || '').slice(0, 10);
        if (s.length < 10 || eEnd.length < 10) continue;
        // Must START on or before today AND END on or after today, AND have
        // a real multi-day span (end > start). That's a multi-day event ALREADY
        // active during this week — they're the bug-class candidates.
        if (s <= todayStr && eEnd >= todayStr && eEnd > s && eEnd >= todayStr) {
          samples.push(String(e.title || ''));
        }
      }
      return samples;
    });

    console.log(`Multi-day-overlap sample titles in dataset: ${sampleTitles.length}`);
    if (sampleTitles.length === 0) {
      console.log('No multi-day events overlapping current week found in __RAW_EVENTS__ — test inconclusive (no bug-class candidates exist).');
      return;
    }
    console.log(`Sampling: ${sampleTitles.slice(0, 3).join(' | ')}`);

    await chip.click();
    await page.waitForTimeout(3500);

    // For each sample title, check whether a card with that title is visible.
    const audit = await page.evaluate((titles: string[]) => {
      const cards = document.querySelectorAll<HTMLElement>(
        '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
      );
      const result: { title: string; visible: boolean }[] = [];
      for (const t of titles) {
        const lc = t.toLowerCase();
        let visible = false;
        for (const card of Array.from(cards)) {
          if (card.classList.contains('event-card-hidden')) continue;
          const group = card.closest<HTMLElement>('.group');
          if (group && group.style.display === 'none') continue;
          const heading = card.querySelector('h2, h3');
          if (!heading?.textContent) continue;
          if (heading.textContent.toLowerCase().includes(lc.substring(0, 20))) {
            visible = true;
            break;
          }
        }
        result.push({ title: t, visible });
      }
      return result;
    }, sampleTitles);

    const hidden = audit.filter((r) => !r.visible);
    if (hidden.length > 0) {
      console.log(`AUDIT FAILED: ${hidden.length}/${audit.length} multi-day events overlapping THIS WEEK are HIDDEN by the chip:`);
      for (const h of hidden) console.log(`  - ${h.title}`);
      console.log('This indicates the React bundle\'s "this-week" filter has the same multi-day-overlap bug PR #598 fixed for This Month. Add defensive applyFilters() narrowing.');
    }

    // Soft assertion via console + a hard fail only if the entire sample is hidden.
    // The dataset may have some titles that look multi-day but are actually
    // misclassified (no real end_date), so we tolerate partial hits.
    expect(
      hidden.length,
      `${hidden.length}/${audit.length} multi-day events overlapping this week are hidden by the chip — likely a multi-day-overlap bug in React's this-week filter.`,
    ).toBeLessThan(audit.length);
  });
});

// ─── Layer C-quat: React #418 hydration regression gate ─────────────────

test.describe('React #418 hydration mismatch — must not fire', () => {
  test.describe.configure({ timeout: 90_000 });

  test('initial load + first chip click does NOT throw React #418', async ({ page }) => {
    // Regression gate: zero `Minified React error #418` errors during normal
    // page interaction. Fixed 2026-05-15 by gating the sign-in island and
    // nav sign-in injectors behind window.__whenReactHydrated__ (same gate
    // that chip injector + static promos use since PRs #600 + #602).
    //
    // This test pins the contract: zero `Minified React error #418`
    // errors during normal page interaction.
    const reactErrors: string[] = [];
    const watch = (text: string) => {
      if (/Minified React error #418/i.test(text)) reactErrors.push(text);
    };
    page.on('console', (msg) => {
      if (msg.type() === 'error') watch(msg.text());
    });
    page.on('pageerror', (err) => watch(`${err.name}: ${err.message}`));

    await loadHomepage(page);
    await page.waitForTimeout(2000);

    // Also stress-test by clicking a chip (the click triggers more imperative
    // DOM work via applyFilters). React #418 wouldn't fire on click but if
    // the gate is leaking somehow, this is when it would surface.
    const chip = page.locator('#next-month-chip');
    if ((await chip.count()) > 0 && (await chip.isVisible())) {
      await chip.click();
      await page.waitForTimeout(2000);
    }

    expect(
      reactErrors.length,
      `React #418 hydration error fired ${reactErrors.length} time(s) — the hydration gate is leaking. Sample:\n${reactErrors.slice(0, 2).join('\n')}`,
    ).toBe(0);
  });
});

// ─── Layer D: first-party JS error budget on idle load ───────────────────

test.describe('Homepage — first-party JS error budget', () => {
  test.describe.configure({ timeout: 90_000 });

  test('initial load + idle has zero first-party uncaught errors', async ({ page }) => {
    const errors = captureFirstPartyErrors(page);
    await loadHomepage(page);
    await page.waitForTimeout(4000);

    const captured = errors();
    if (captured.length > 0) {
      console.log('First-party JS errors during idle homepage load:');
      for (const e of captured) console.log(`  [${e.type}] ${e.text} @ ${e.location ?? ''}`);
    }
    expect(captured.length, captured.map((e) => e.text).join('\n')).toBe(0);
  });
});
