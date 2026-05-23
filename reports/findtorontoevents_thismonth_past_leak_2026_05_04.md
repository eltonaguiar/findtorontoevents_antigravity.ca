# findtorontoevents.ca "This Month" filter leaking past single-day events

**Date:** 2026-05-04
**Reporter:** UU1-THIS-MONTH-PAST-LEAK subagent (operator-flagged)
**Severity:** P1 — user-visible UI bug on live homepage
**Sister bug:** RR1's [TORONTOEVENTS_ANTIGRAVITY#11](https://github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY/pull/11) (Tomorrow filter)
**Fix PR:** [TORONTOEVENTS_ANTIGRAVITY#12](https://github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY/pull/12)

## Summary

With `today = 2026-05-04`, clicking the **This Month** chip on findtorontoevents.ca rendered single-day events dated **MAY 1** (already in the past). Multi-day events that ended in April were correctly filtered (`Memory Work` end-2022 was logged out), but the year+month-only `isThisMonth` predicate accepted any past day in the same calendar month.

## Evidence

### Console log (operator browser, 2026-05-04T02:40:13.011Z)
```
🔍 [validEvents] Computing with now=2026-05-04T02:40:13.011Z, sourceEvents=11290, dateFilter=this-month, showStarted=false
✅ [Filter] Including invalid date event in this-month filter: "222 — Surprise Social Experience (Toronto)"
✅ [Filter] Including invalid date event in this-month filter: "Timeleft — Dinner With Strangers (Toronto)"
❌ [Filter] Filtering ended event: "Memory Work" (ended: 2022-05-01T15:00:00.000Z, now: 2026-05-04T02:40:13.011Z)
📊 [Filter Results] Input: 11290, Output: 2871, Filtered out: 8419
[FILTERS] Counter span updated: 2871 → 46
```

### Visible cards (from the 46 surfaced after `index.html` post-cull)
- MAY 1 — "Before Borders Gallery Show"
- MAY 1 — "Contact Photography Festival 2026 Announces"
- MAY 1 — "We Are Gumbo: 10 Years of"

All three are single-day events whose `start_date < today`.

## Root cause

Two compounding bugs in `src/components/EventFeed.tsx` (React source repo `eltonaguiar/TORONTOEVENTS_ANTIGRAVITY`):

1. **Invalid-date passthrough was unconditional.** The `hasInvalidDate` branch logged "Including invalid date event in `${dateFilter}` filter" and returned without applying any filter — accepting undated events under every targeted view (today/tomorrow/this-week/this-month/nearby), not just `all`.

2. **`isThisMonth(date)` only checked year+month equality.** A MAY 1 event on MAY 4 satisfied `eventParts[0]===todayParts[0] && eventParts[1]===todayParts[1]` and passed through. There was no `>= today` clamp.

The `index.html` custom-filter override (lines ~3666-3708) already implements the correct `[today, end-of-month]` overlap window — but it only runs when `__thisMonthOverrideActive__ === true`, which is set by *our own injected chip*, not by clicking React's native chip. So when the user clicks React's "This Month", the override stays inactive and the React-side bug is the visible behavior. **`index.html` is NOT separately leaking** — its window math is correct; it just doesn't run unless the override flag is set.

## Fix applied (TORONTOEVENTS_ANTIGRAVITY#12)

`src/components/EventFeed.tsx` (+55 / -14):

- **Fix A:** invalid-date passthrough restricted to `dateFilter === 'all'`. All targeted filters now `return false` when the date is unparseable.
- **Fix D:** `'this-month'` branch:
  - **Single-day:** require `eventStartParts[0]===todayY && eventStartParts[1]===todayM && eventStartYMD >= todayStr`. Past-this-month days are explicitly dropped with a `❌ Event already passed this month` log.
  - **Multi-day:** require `endYMD >= todayStr` AND (`startMonth===todayM` OR `endMonth===todayM`). Keeps currently-running and upcoming multi-day events; drops events whose entire run was earlier in the month.
- TypeScript: `tsc --noEmit` clean.

Mirrors the window already used by the `index.html` override, and mirrors RR1's PR #11 invalid-date fix for the Tomorrow filter.

## Operator next steps (in order)

1. **Review and merge** [TORONTOEVENTS_ANTIGRAVITY#11](https://github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY/pull/11) (Tomorrow filter, RR1) and [#12](https://github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY/pull/12) (This Month filter, this fix). PR #11 must merge first or be rebased; PR #12 was branched off `origin/main` and does NOT depend on #11, so it can land independently.
2. **Build the React app** (`npm run build:next` or equivalent in the React repo).
3. **Deploy via the surgical helper** — `node scripts/upload-next-only.mjs` from inside the React source repo. **Do NOT use** `npm run deploy:sftp` (sequence bug overwrites `build/` between phases — see CLAUDE.md). **Do NOT** replace `/findtorontoevents.ca/index.html` on the FTP server with the Next.js build's `build/index.html` (strips ~3,000 lines of product, CLAUDE.md outage 2026-04-27).
4. **Smoke-verify** on production: open https://findtorontoevents.ca, click "This Month" chip, confirm no MAY 1/2/3 cards visible. Confirm undated cards ("Timeleft", "222") only show under "All Dates".

## Files

- React source (NOT in this repo): `eltonaguiar/TORONTOEVENTS_ANTIGRAVITY` :: `src/components/EventFeed.tsx`
- This repo's live HTML (untouched by this fix): `TORONTOEVENTS_ANTIGRAVITY/index.html` lines 3666-3708 already correct
- Worktree used for fix: `e:/findtorontoevents_antigravity.ca/.claude/worktrees/tev_react_src/` on branch `fix/this-month-filter-past-leak`
