# 2026-05-01 — Events homepage filter: remaining action items + plan

After PR #591 / #594 / #598 landed (Next Month + This Month filter regressions
+ multi-day overlap), several follow-ups are still open. This document
inventories them, prioritizes by user-visible impact, and proposes a single
focused PR. A scheduled routine (May 15 2026) tracks the longest-running
item separately.

## Inventory

Sourced from: PR #591 code-reviewer punch list, the cloud agent's
methodology MD (`updates/2026-05-01-this-month-next-month-filter-fix.md`),
the Playwright spec's TODO comment, and direct production testing.

| # | Item | User-visible impact | Effort | Bucket |
|---|---|---|---|---|
| 1 | **React #418 hydration mismatch on every page load** | High — full client re-render, brief flash, lost focus, ad-blocker confusion | Medium | Page boot |
| 2 | **"This Week" filter likely has the same multi-day-overlap bug** as the Next Month / This Month chips did | High — multi-day events spanning the week boundary get hidden | Low | Filter logic |
| 3 | **Mobile tap targets** — chip row at 384×854 (Galaxy S21) and 412×915 (S25 Ultra) may have chips below the 44 px iOS / 48 px Material baseline | Medium — fat-finger tap misses on mobile | Low | Mobile UX |
| 4 | Recurring-event `__RAW_EVENTS__` scan in `__eventInNextMonth__` is O(N×cards) per filter pass | Low — only when chip is on, ~547k comparisons / pass on 10 951-event dataset | Low | Perf |
| 5 | Title-match logic duplicated between `applyFilters` (~3397) and `__eventInNextMonth__` (~3877) | Low — drift risk; bug fix in one site won't propagate | Medium | Refactor |
| 6 | Loop-guard `__thisMonthHideStreak__` variable name is misleading (it's not a streak length, it's accumulated hide count) | Cosmetic | Trivial | Refactor |
| 7 | `cardTitle.length >= 8` magic in recurring fallback is undocumented | Cosmetic | Trivial | Refactor |
| 8 | Counter `(N node total)` parity — `__RAW_EVENTS__.length` may not match React's pre-filtered N | Low — number on screen could be off by ~50 | Low | Counter |
| 9 | Playwright spec doesn't directly assert: counter rewrite, title-prefix collision, applyThumbnails dedup | Low — silent regression risk | Medium | Test |
| 10 | FakeDate / time-freeze harness in `tests/events_month_filters.spec.ts` is local; should be promoted to shared `tests/_helpers/freeze_clock.ts` for reuse | Low | Low | Test infra |
| 11 | The This Month override clicks `All Dates + Show Ongoing`, surfacing 10 951 events ordered start-asc → first 50 rendered are months in the past, hidden by the gate, lazy-load loop until guard fires. Even with the threshold lowered to 50 + auto re-run, the experience is "click → empty → cards re-show after ~150 ms" | Medium — visible flash | Medium | Architecture |
| 12 | 24 inline `<script>` blocks each have their own `DOMContentLoaded` handler; consolidating would reduce hydration thrash | Medium (couples to #1) | High | Refactor |

## Priority cuts

**This PR (high user-impact, low/medium effort):**

- **#2 — "This Week" multi-day overlap.** Almost certainly has the same bug shape
  the cloud agent fixed in This Month. A weekend festival running Sat–Sun
  whose `eventData.date` is the festival's first-ever year shouldn't get
  hidden when "This Week" is active.
- **#3 — Mobile tap targets.** Verify with Playwright on the S21 + S25 Ultra
  profiles, then inject min-height/min-width CSS if any chip falls below
  the touch baseline.
- **#1 — React #418 hydration.** The single biggest user-visible bug remaining.
  Add a `__whenReactHydrated__` helper and gate the first-paint imperative
  injectors on it (chip, thumbnails, static promos).

**Defer to follow-up PR (code quality):** #4, #5, #6, #7, #8, #9, #10.

**Defer indefinitely / out of scope:** #11 (architecture rework), #12 (boot
block consolidation). Both need cross-repo work in
`eltonaguiar/TORONTOEVENTS_ANTIGRAVITY`.

## Plan: Item #2 — "This Week" multi-day overlap

### Investigation

`Ctrl+F` on `TORONTOEVENTS_ANTIGRAVITY/index.html` for `__thisWeek` / `this-week-chip`.
React's chip dispatches `dateFilter='this-week'` in the bundle (we saw it in
the user's console log: `dateFilter=this-week, sourceEvents=11016, Output:
1116`). The bundle's filter likely uses `event.date` only — same start-only
single-date check the Next Month bug had.

If a custom override exists in our HTML (analogous to `__thisMonthOverrideActive__`),
apply the same `[start, end]` overlap with `event.end_date` fallback.

If no override exists and React's bundle is what hides multi-day events,
add an override following the same pattern as This Month:

1. Intercept the click on the "This Week" React chip.
2. Click "All Dates" + apply our own gate.
3. Gate checks `[start, end]` overlap with `[today, today + 7 days]`.

### Trade-off vs leaving it alone

If This Week's React filter only hides events whose start IS in the past,
that's a specific subset of the bug, not the full multi-day overlap.
Investigate first; only override if confirmed.

## Plan: Item #3 — Mobile tap targets

### Verification

Use `tests/events_month_filters.spec.ts` (already on main, frozen at
2026-05-01) running on the `Samsung Galaxy S25 Ultra` and `Samsung Galaxy
S21` projects. Add a new test case:

```ts
test('chips meet 44 px touch baseline on mobile', async ({ page, isMobile }) => {
  test.skip(!isMobile);
  await loadPage(page);
  for (const id of ['next-month-chip', 'tbd-toggle', 'multiday-toggle', 'thumbnail-toggle']) {
    const chip = page.locator(`#${id}`);
    if ((await chip.count()) === 0) continue;
    const box = await chip.boundingBox();
    expect(box?.height ?? 0, `#${id} height`).toBeGreaterThanOrEqual(44);
    expect(box?.width ?? 0, `#${id} width`).toBeGreaterThanOrEqual(44);
  }
});
```

### Fix

If any chip fails: inject CSS targeting touch viewports.

```html
<style>
  @media (hover: none) and (pointer: coarse) {
    #next-month-chip,
    #tbd-toggle,
    #multiday-toggle,
    #thumbnail-toggle,
    #near-me-toggle,
    button.px-4.py-2.rounded-full {
      min-height: 44px;
      min-width: 44px;
    }
  }
</style>
```

The CSS pattern matches both our injected chips and React's chip class
shape (`px-4 py-2 rounded-full ...`).

## Plan revisions after peer review (Cerebras + superpowers code-reviewer, 2026-05-01)

Both reviewers converged on the same load-bearing critiques. Plan revised:

1. **Hydration detection: replace pure timing heuristic with a witness pattern.**
   `load + 2 rAF + 2 s timeout` is not robust against React lazy chunks that
   commit hydration after window load. Switch to: `__RAW_EVENTS__` is a
   non-empty array AND a non-skeleton glass-panel card has a hydrated `<h2>`.
   Poll on rAF until both true, with a 5 s timeout fallback.
2. **Item #2 (This Week): investigate first, prefer post-React DOM narrowing
   over click-All-Dates.** The original "duplicate the This Month override
   architecture" plan would recreate the runaway loop conditions PR #591
   just guard-railed.
3. **Tap target: 48 px, not 44** (Material/WCAG, covers iOS too).
4. **Cherry-pick safety:** land Item #3 (CSS-only) as the first commit.
5. **Allowlist removal as a SEPARATE commit in the same PR**, not after.
6. **Bonus:** `_thumbLookupMap` invalidation guard against in-place push by
   the React chunk.
7. **Bonus:** explicit Playwright assertion that #418 is NOT thrown.

## Plan: Item #1 — React #418 hydration

### Root cause

Inline `<script>` blocks fire on `DOMContentLoaded`, which fires before
React's `hydrateRoot()` finishes. Our injectors mutate DOM (chip,
thumbnails, promo container), React sees mismatch, throws #418, falls back
to client-only render.

### Fix

Add a single `window.__whenReactHydrated__(cb)` helper that fires `cb` after
BOTH:

1. `document.readyState === 'complete'` (window `load`)
2. Two `requestAnimationFrame` ticks (1 frame for `hydrateRoot()` to commit,
   1 more to settle effects)

Hard fallback: `setTimeout(fire, 2000)` so we don't strand on a stalled
bundle.

```js
window.__reactHydrated__ = false;
window.__whenReactHydrated__ = function (cb) {
  if (window.__reactHydrated__) { try { cb(); } catch (_) {} return; }
  var fired = false;
  function fire() {
    if (fired) return;
    fired = true;
    window.__reactHydrated__ = true;
    try { cb(); } catch (_) {}
  }
  function arm() {
    requestAnimationFrame(function () {
      requestAnimationFrame(fire);
    });
    setTimeout(fire, 2000);
  }
  if (document.readyState === 'complete') arm();
  else window.addEventListener('load', arm, { once: true });
};
```

Wrap each first-paint injection. Re-injection paths (MutationObserver,
filter-chip click handlers) stay synchronous — they fire post-hydration by
definition.

Sites to wrap (line numbers from current main):
- Static promos init (~line 1915 DOMContentLoaded)
- Chip injector init (~line 4212-4213 DOMContentLoaded)
- Thumbnail injector init (~line 3291 — invoked from filter activate, may also be in a DOMContentLoaded block to verify)
- Other injectors discovered in the audit pass: ~line 4339, 4435, 4479, 4507, 4826

After landing the gate, REMOVE the `Minified React error #418` allowlist
from `tests/events_next_month_filter.spec.ts` so the JS-error-budget test
becomes the regression gate. The scheduled May 15 routine becomes a no-op
and can be deleted.

## Test plan

1. `node --test tests/event_date_filters.unit.test.js` — unit math (regression gate).
2. Add Node unit test for "This Week" overlap math.
3. `VERIFY_REMOTE=1 npx playwright test --config=playwright.next-month.config.ts`
   — verifies hydration gate (the #418 budget test must pass without the
   allowlist).
4. `VERIFY_REMOTE=1 npx playwright test tests/events_month_filters.spec.ts
   --project="Samsung Galaxy S25 Ultra"` — verifies This Week overlap and
   chip tap targets at 412×915 viewport.

## Out of scope

- Code-quality refactors (#4–#10)
- This Month override architecture (#11)
- Boot-block consolidation (#12)
- Cross-repo work in `eltonaguiar/TORONTOEVENTS_ANTIGRAVITY`

## Risks

| Risk | Mitigation |
|---|---|
| Hydration gate's 2 s fallback fires before React on slow networks → mismatch returns | Identical symptom to today's #418, not a regression. Bump to 5 s if observed in wild. |
| `requestAnimationFrame` doesn't fire on background tabs | `setTimeout` fallback covers it. |
| "This Week" override breaks an existing user flow we don't know about | Keep React's native filter as the primary; only add overlap as a defensive narrowing. |
| Chip CSS injection bumps hit area onto un-touch-target React buttons we don't own | Scoped to specific IDs first; `button.px-4.py-2.rounded-full` is broad — limit to `#events-grid` ancestor selector if regressions appear. |
| 3 fixes in one PR makes review harder | Each is independent and small (~30 lines). Easier than 3 separate PRs given the page-boot interdependence. |
