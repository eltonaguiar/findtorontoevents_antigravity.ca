# Filter Bug Audit — Consolidated Patch Plan (2026-05-04)

## Executive Summary

The core bug is a capture-phase `stopImmediatePropagation()` call in `_wireThisMonthOverride` (line 4384) that swallows programmatic `thisMonthBtn.click()` calls from `_activateNextMonth` (line 4256), preventing React from ever switching filter state. This causes dual-filter activation where both React's chip state and the custom `__nextMonthFilterActive__` flag are simultaneously active, producing empty grids. PRs #746-#748 shipped partial fixes (debounce adjustments, observer tuning) but did not address the root cause. PR #750 attempts to add `e.isTrusted` guards but still doesn't fix the missing re-entry guard on `applyFilters()` — the single highest-leverage fix is adding a global mutex (`window.__applyFiltersRunning__`) and consolidating all scheduling through one helper.

## Ranked Bug List

1. **`stopImmediatePropagation()` swallows programmatic clicks** — P0, HIGH confidence, 5/5 engines
   - **Lines:** 4376-4384 (`_wireThisMonthOverride`), 4256 (`_activateNextMonth`)
   - **Fix:** Add `if (!e.isTrusted) return;` at top of capture-phase handler (line 4376). This lets synthetic clicks from `_activateNextMonth` reach React's event system while still intercepting real user clicks.
   - **Blast radius:** None — `e.isTrusted` is read-only and universally supported. All user clicks remain intercepted; only programmatic clicks bypass.
   - **Test:** Playwright: `await page.click('[data-testid="next-month"]'); await expect(page.locator('[data-testid="this-month-chip"]')).toHaveClass(/active/);`

2. **No global re-entry guard on `applyFilters()`** — P0, HIGH confidence, 5/5 engines
   - **Lines:** 3416-3850 (function body), 4259-4262 (120ms timeout), 4429-4430 (200ms timeout), 4511-4534 (observer debounce)
   - **Fix:** Add `if (window.__applyFiltersRunning__) return;` at line 3418; set `window.__applyFiltersRunning__ = true` before DOM mutations, `false` in finally block. Funnel all scheduling through `scheduleApplyFilters(delay)` that cancels pending timeouts.
   - **Blast radius:** Prevents overlapping passes that corrupt `shownCount`, `hiddenCount`, and `__thisMonthHideStreak__`. May expose latent timing bugs that were masked by concurrent runs.
   - **Test:** Unit test: call `applyFilters()` twice synchronously; assert second call returns immediately. Playwright: rapid-click "Next Month" then "This Week" within 50ms; assert no empty-grid flash.

3. **`__parseCardDisplayedDate__` wrap-around bug** — P1, HIGH confidence, 5/5 engines
   - **Lines:** 4333-4336: `if (idx < now.getMonth()) year += 1`
   - **Fix:** Replace with delta-based heuristic: `var delta = idx - now.getMonth(); if (delta > 6) year -= 1; else if (delta < -6) year += 1;` This handles both forward and backward wrap-around symmetrically.
   - **Blast radius:** Changes year assignment for all cards without `eventData`. Could affect "This Month" and "Next Month" views for recurring events.
   - **Test:** Unit test: `__parseCardDisplayedDate__` with mock dates for Jan→Feb (should stay current year), Nov→Jan (should wrap to next year), Feb→Jan (should wrap to previous year).

4. **UTC vs local timezone mismatch in events cache** — P1, HIGH confidence, 5/5 engines
   - **Lines:** 94: `_today = new Date().toISOString().slice(0, 10)`
   - **Fix:** Replace with local date: `var d = new Date(); _today = d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');`
   - **Blast radius:** Changes which events are considered "today" for all timezone-sensitive logic. Users in UTC-negative zones will see events appear 1 day earlier.
   - **Test:** Unit test: mock `Date` to 11 PM EDT (3 AM UTC next day); assert `_today` equals local date, not UTC date.

5. **MutationObserver debounce too short (500ms)** — P1, HIGH confidence, 5/5 engines
   - **Lines:** 4511-4534: `_filterTimeout = setTimeout(safeApply, 500);`
   - **Fix:** Increase to 1200ms and reset on each new mutation. Add batch-settled check: if no new mutations for 1200ms, run `safeApply()`.
   - **Blast radius:** Slower initial filter application after lazy-load. May cause brief flash of unfiltered cards.
   - **Test:** Playwright: scroll to trigger lazy-load; assert filter applies after all batches render, not after first batch.

6. **`isMultiDayEvent()` UTC→Local off-by-one** — P2, HIGH confidence, 5/5 engines
   - **Lines:** 3242-3243: `new Date("2026-05-04T00:00:00Z").toDateString()`
   - **Fix:** Compare YYYY-MM-DD substrings directly instead of constructing Date objects: `startDate.slice(0,10) !== endDate.slice(0,10)`.
   - **Blast radius:** Changes multi-day classification for events spanning midnight UTC. Minimal impact as most events are same-day.
   - **Test:** Unit test: `isMultiDayEvent("2026-05-04T00:00:00Z", "2026-05-04T23:59:00Z")` returns false; `isMultiDayEvent("2026-05-04T00:00:00Z", "2026-05-05T00:00:00Z")` returns true.

7. **Inline `display:none` on `.group` vulnerable to React** — P2, HIGH confidence, 5/5 engines
   - **Lines:** 3738-3742: `gridItem.style.display = 'none'`
   - **Fix:** Replace with CSS class: `gridItem.classList.add('event-group-hidden')` and define `.event-group-hidden { display: none !important; }` in stylesheet.
   - **Blast radius:** None — CSS class approach is standard and React-safe.
   - **Test:** Playwright: assert hidden groups have class `event-group-hidden`; assert React re-render does not remove class.

## Ship Schedule

**Ship today:**
- Add `if (!e.isTrusted) return;` guard in `_wireThisMonthOverride` (P0, one-line fix, safe)
- Add global re-entry guard `window.__applyFiltersRunning__` in `applyFilters()` (P0, well-understood pattern)
- Fix UTC `_today` to use local date (P1, isolated change, easy to verify)
- Replace inline `display:none` with CSS class (P2, trivial, no blast radius)

**This week:**
- Fix `__parseCardDisplayedDate__` wrap-around heuristic (P1, needs careful testing with real event data)
- Increase MutationObserver debounce to 1200ms (P1, may need tuning based on observed lazy-load patterns)
- Fix `isMultiDayEvent()` to compare substrings (P2, low risk but needs unit tests)

**Next sprint:**
- Consolidate all `applyFilters()` scheduling into single `scheduleApplyFilters(delay)` helper (refactor-grade, reduces future bugs)
- Replace `stopImmediatePropagation()` architecture with React state-driven approach (speculative, requires architectural review)

## Kimi Findings That Did NOT Survive Cross-Critique

- **`_findReactChipByText` not defined in scope** — False positive. Function exists in non-excerpted code; all 5 engines confirmed it's called correctly.
- **`applyThumbnails` called without definition check** — Fabricated. Function is defined elsewhere in the full codebase.
- **`_setNextMonthChipClass` not defined in scope** — Fabricated. Same as above.
- **`hideSkeletons` referenced but not defined** — Fabricated. Function exists in non-excerpted initialization code.
- **`requestAnimationFrame` polling stalls in background tabs** — Overreach. Line numbers (4589-4603) outside provided regions; no evidence of actual stalling in production.
- **`chipObserver` infinite-loop risk** — Overreach. Observer registration not shown; 250ms debounce prevents tight loops in practice.
- **`e.isTrusted` vs `e.detail` comparison** — Not a bug. This is a fix recommendation, not a defect. All engines agree `e.isTrusted` is correct.

## Open Questions / Need-More-Evidence

- Does the 1200ms debounce value work for all lazy-load patterns? Need to test with slow 3G and large event datasets.
- Does `e.isTrusted` work correctly in all target browsers (Safari 15+, Chrome 90+, Firefox 90+)? Need cross-browser E2E tests.
- Does the `__parseCardDisplayedDate__` delta-based heuristic correctly handle all month-boundary cases? Need to test with real event data spanning Dec→Jan and Jan→Feb transitions.
- Is there a race between the 800ms capture listener and the 200ms override that still causes issues after the `e.isTrusted` fix? Need to test with rapid user clicks.