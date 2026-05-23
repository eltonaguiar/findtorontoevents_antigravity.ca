# findtorontoevents.ca — "Tomorrow" Filter Showing JAN/DEC Events

**Date:** 2026-05-04
**Reporter:** subagent RR1-TOMORROW-FILTER (operator-escalated)
**Severity:** P1 (user-visible product bug, wrong events shown for selected filter)
**Surface:** `findtorontoevents.ca` homepage events grid, "Tomorrow" date filter
**Source repo:** `eltonaguiar/TORONTOEVENTS_ANTIGRAVITY` (separate from this repo)
**Source file:** `src/components/EventFeed.tsx`
**Local worktree:** `e:/findtorontoevents_antigravity.ca/.claude/worktrees/tev_react_src/`

---

## Symptom

Today is 2026-05-04. Tomorrow = 2026-05-05.

User selects the "Tomorrow" date filter and sees:

- "& Juliet" (badge: **DEC 3**, multi-day)
- "Toronto History Museums Free" (**JAN 1**)
- "Free Concert Series" (**JAN 6**)
- "21C Music Festival" (**JAN 16**, multi-day)

Expected: only events whose start date is **2026-05-05**.

## Console evidence (live, 2026-05-04 01:04 Z)

```
[validEvents] Computing with now=2026-05-04T01:04:40.822Z, sourceEvents=11290, dateFilter=tomorrow, showStarted=false
[validEvents] 'now' is set, applying full filters...
[Filter] Including invalid date event in tomorrow filter: "222 - Surprise Social Experience (Toronto)"
[Filter] Including invalid date event in tomorrow filter: "Timeleft - Dinner With Strangers (Toronto)"
[Filter Results] Input: 11290, Output: 233, Filtered out: 11057
[EventFeed] Display events: 233 (validEvents: 233, liveEvents: 11290)
[FILTERS] Shown: 46 Hidden: 4
```

The `Including invalid date event in tomorrow filter` log is the smoking gun: invalid-date
events were intentionally bypassed by every targeted filter, not just `all`.

## Root cause

Two compounding bugs in `EventFeed.tsx::validEvents` memo:

### Bug 1 — invalid-date passthrough is too permissive (lines 526-539, pre-fix)

```ts
const hasInvalidDate = isNaN(eventStartDate.getTime());
if (hasInvalidDate) {
    console.log(`Including invalid date event in ${dateFilter} filter: ...`);
    // Skip to return true - invalid dates pass through all filters  <-- BUG
} else if (dateFilter !== 'all' && now && !hasInvalidDate) {
    // ... date-window logic
}
```

The earlier "surgical fix" intended to keep undated events visible on "All Dates" so the
feed wouldn't be empty. But it short-circuits _every_ targeted filter, so "Timeleft —
Dinner With Strangers", "222 — Surprise Social Experience", etc. (which have no parseable
date) appear on Today, Tomorrow, This-Week, This-Month — even though we cannot prove
they are happening in that window.

### Bug 2 — multi-day overlap shows wrong start-date badge (lines 569-570, pre-fix)

```ts
if (dateFilter === 'tomorrow') {
    const tomorrowStart = new Date(todayStart.getTime() + 24*60*60*1000);
    const tomorrowEnd   = new Date(tomorrowStart.getTime() + 24*60*60*1000 - 1);
    if (isMultiDay(e)) {
        // Include if event range OVERLAPS tomorrow
        if (!isNaN(eEndDate.getTime()) &&
            (eEndDate < tomorrowStart || eventStartDate > tomorrowEnd)) return false;
    } else {
        if (!isTomorrow(e.date)) return false;
    }
}
```

`& Juliet` has `start=Dec 3 2025` + `end=May 17 2026`. Its range overlaps
2026-05-05 (tomorrow), so the multi-day branch keeps it. But the `EventCard` renders
`event.date` (the original start) as **"DEC 3"**, with no current-window adjustment.
User sees "DEC 3" in a Tomorrow view and thinks it is broken — and they are right: a
multi-day event whose start is 5 months ago does not belong on a "Tomorrow" view.

PR #751 corrected `THIS_MONTH` / `NEXT_MONTH` along the same axis. `TOMORROW` and `TODAY`
were not touched and inherited the same multi-day-overlap leak.

## Fix decision tree

- **Fix A**: Tighten invalid-date passthrough to only fire when `dateFilter === 'all'`.
- **Fix B**: When a multi-day event is shown in `today`/`tomorrow`, render the badge as
  the current/upcoming day, not the original `start_date`. Higher risk: requires
  `EventCard` props change.
- **Fix C** (preferred minimum-risk): Targeted filters only include events whose `start`
  matches the target day (no fuzzy multi-day overlap). Multi-day events that happen to
  be running tomorrow live under the existing "Multi-Day" toggle, not under "Tomorrow".

## Applied fix

**Both A and C** were applied to `src/components/EventFeed.tsx`:

1. Invalid-date events are now excluded from targeted filters (today/tomorrow/this-week/
   this-month/nearby). They pass through only when `dateFilter === 'all'`.
2. `today` and `tomorrow` filters now require strict `isToday(e.date)` /
   `isTomorrow(e.date)` — no multi-day overlap. Multi-day events stay accessible via
   the Multi-Day toggle.
3. The "EMERGENCY FALLBACK" path that returned invalid-date events on empty results was
   gated to `dateFilter === 'all'` so it cannot re-introduce the bug.

Diff stat: `src/components/EventFeed.tsx | 114 ++++++++++++++++++-------------------`
(63 insertions, 51 deletions).

## Test cases that would catch this regression

```ts
describe('EventFeed validEvents — Tomorrow filter', () => {
    it('excludes invalid-date events from Tomorrow filter', () => {
        const events = [
            { title: 'Timeleft', date: 'TBA' },               // invalid
            { title: 'Real Tomorrow Event', date: tomorrowISO } // valid
        ];
        const filtered = computeValidEvents(events, { dateFilter: 'tomorrow', now });
        expect(filtered.map(e => e.title)).toEqual(['Real Tomorrow Event']);
    });

    it('excludes multi-day overlap with start in the past from Tomorrow filter', () => {
        const events = [
            { title: '& Juliet', date: '2025-12-03', endDate: '2026-05-17' }, // overlap, started Dec
            { title: 'Tomorrow Show', date: tomorrowISO }
        ];
        const filtered = computeValidEvents(events, { dateFilter: 'tomorrow', now: may4_2026 });
        expect(filtered.map(e => e.title)).toEqual(['Tomorrow Show']);
    });

    it('keeps invalid-date events on All Dates view', () => {
        const events = [{ title: 'Timeleft', date: 'TBA' }];
        const filtered = computeValidEvents(events, { dateFilter: 'all', now });
        expect(filtered).toHaveLength(1);
    });
});
```

## Operator next steps

1. PR is opened against `eltonaguiar/TORONTOEVENTS_ANTIGRAVITY` (the React source repo)
   from the local worktree. Once merged, run the standard Next.js build + FTP upload
   (`scripts/upload-next-only.mjs`) per `CLAUDE.md` — do NOT replace the live
   `/findtorontoevents.ca/index.html` 4845-line HTML.
2. After deploy, verify on findtorontoevents.ca:
   - Console has no `Including invalid date event in tomorrow filter` lines.
   - Tomorrow view shows only events with start = 2026-05-05 (no DEC/JAN cards).
   - All-Dates view still shows undated events ("Timeleft", "222 — Surprise...").
3. Audit other date filters (this-week, this-month, next-month) for the same
   multi-day-overlap badge mismatch. PR #751 covered month filters — confirm
   `this-week` doesn't have a sibling bug.

## Related

- PR #751 — fixed the same class of bug for `THIS_MONTH` / `NEXT_MONTH` (did not touch
  `TOMORROW` / `TODAY`).
- `updates/2026-05-01-events-filter-remaining-action-items.md` — pre-existing tracker
  for residual filter issues.
- `updates/2026-05-02-comprehensive-48h-review-and-fixes.md` — current 48h review.
