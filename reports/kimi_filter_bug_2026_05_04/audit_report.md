# Event Filtering Logic — Race Condition & State Management Audit Report

## Executive Summary

The reported bug where **"This Week" and "Next Month" can both be active** is confirmed and traced to a **CRITICAL** DOM event-propagation flaw: `_wireThisMonthOverride` intercepts every click on the "This Month" React chip in the **capture phase** on `document`, calls `stopImmediatePropagation()`, and then programmatically clicks the same chip again. Because the programmatic `click()` targets the **same element**, the browser swallows the second event entirely—React never processes it. When the user clicks "Next Month" while React is internally showing "This Week", the `thisMonthBtn.click()` inside `_activateNextMonth` is swallowed, React stays on "This Week", but our `__nextMonthFilterActive__` flag is set to `true`. Both filters are then simultaneously applied to the DOM.

Multiple additional race conditions, lack of re-entry guards, and unprotected global flags compound the issue.

---

## Finding 1: Programmatic `thisMonthBtn.click()` Is Swallowed by Capture-Phase `stopImmediatePropagation()` — Dual-Filter Root Cause

**Severity:** CRITICAL  
**Location:** Lines 4245–4256 (`_activateNextMonth`), 4373–4445 (`_wireThisMonthOverride`), 4424–4425 (`thisMonthBtn.click()` inside handler)  

### Root Cause
`_wireThisMonthOverride` installs a **capture-phase** listener on `document` (line 4376). When a user clicks the React "This Month" chip, this listener fires before the event reaches the button. It calls `e.stopImmediatePropagation()` (line 4384), which stops all further propagation of that event—including to the target element itself. Immediately after, it calls `thisMonthBtn.click()` (line 4425) to "re-dispatch" the click.  

Browser testing (verified in Chromium/Playwright) confirms that when `stopImmediatePropagation()` is called in **capture phase on `document`** and the handler then calls `click()` on the **same element** that was the original target, the programmatic click is **completely swallowed**—the capture listener does not fire again, and the target's own listeners (including React's synthetic-event delegation) never run.

Consequences:
- **User clicks "This Month"**: React's internal state **never changes**. `__thisMonthOverrideActive__` becomes `true`, and `applyFilters()` imperatively hides cards. React still believes it is showing whatever filter was previously selected.
- **`_activateNextMonth` calls `thisMonthBtn.click()`** (line 4256): This programmatic click is also swallowed by the same `_wireThisMonthOverride` listener. React's state is **unchanged**.

If React was already on "This Week" when the user clicks "Next Month":
1. `thisMonthBtn.click()` is swallowed → React stays on "This Week".
2. `__nextMonthFilterActive__ = true`.
3. Next Month chip is styled active.
4. `applyFilters(120 ms)` runs with `__nextMonthFilterActive__ = true` against React's "This Week" DOM.
5. **Both "This Week" (React internal) and "Next Month" (our flag) are active simultaneously.**

### Fix Recommendation
Replace the synchronous `thisMonthBtn.click()` inside `_wireThisMonthOverride` with an **asynchronous** dispatch using `setTimeout(..., 0)` (or `queueMicrotask`). The `stopImmediatePropagation()` only blocks events in the same synchronous propagation phase; a `setTimeout`-deferred click will start a fresh event flow that reaches React:

```javascript
// Inside _wireThisMonthOverride, label === 'This Month' branch:
// WRONG — swallowed:
// if (thisMonthBtn) thisMonthBtn.click();

// CORRECT — escapes the stopped propagation:
setTimeout(function () {
  if (thisMonthBtn) thisMonthBtn.click();
}, 0);
```

Apply the same fix to `_activateNextMonth` (line 4256) and the `_todayIsLastDayOfMonth` path (line 4397).

### Bug Reproduction Steps
1. Load the page. React defaults to "All Dates" or another filter.
2. Click React's "This Week" chip. React renders This Week cards.
3. Click the injected "Next Month" chip.
4. Observe: "Next Month" chip is styled active. "This Week" chip **still looks active** (React never got the click to change it). The grid is filtered by BOTH conditions (only cards that are in This Week AND in Next Month). Typically results in an empty or nearly-empty grid.

---

## Finding 2: Capture-Phase Listener Ordering Races with `thisMonthBtn.click()` Inside `_activateNextMonth`

**Severity:** CRITICAL  
**Location:** Lines 4450–4464 (`_wireSiblingChipDeactivation`), 4373–4445 (`_wireThisMonthOverride`), 4539–4552 (`init()` click listener)  

### Root Cause
All three listeners are registered in **capture phase** on `document`, in this order (lines 4469–4470, 4539):

1. `_wireSiblingChipDeactivation`
2. `_wireThisMonthOverride`
3. `init()` re-apply click listener

When `_activateNextMonth` calls `thisMonthBtn.click()` programmatically, the event enters the capture phase at `document`:
1. Listener 1 (`_wireSiblingChipDeactivation`) fires. At this exact moment, `__nextMonthFilterActive__` has **not yet been set** (it is assigned on line 4257, AFTER the `click()` call). So the check `if (!window.__nextMonthFilterActive__) return;` (line 4455) is true, and it returns early.
2. Listener 2 (`_wireThisMonthOverride`) fires. It sees `label === 'This Month'` and calls `stopImmediatePropagation()` (line 4384). This blocks listener 3 and ALL subsequent propagation. React never sees the click.

So the programmatic `thisMonthBtn.click()` from `_activateNextMonth` is **intercepted by the same override code meant for user clicks**, and the `stopImmediatePropagation()` blocks not only React but also the `init()` re-apply listener (which would have scheduled `safeApply` in 800 ms). The 800 ms debounce is therefore **lost** for this interaction path, meaning `applyFilters` only runs from the 120 ms timeout—one fewer safety net.

### Fix Recommendation
Add a guard in `_wireThisMonthOverride` to ignore **programmatic / non-trusted** events, OR remove `stopImmediatePropagation()` and use a different interception strategy:

```javascript
document.addEventListener('click', function (e) {
  // Ignore programmatic clicks so _activateNextMonth's thisMonthBtn.click() works
  if (!e.isTrusted) return;
  // ... rest of handler
}, true);
```

If `e.isTrusted` is unavailable or unreliable in the target browser, set a transient flag before programmatic clicks:

```javascript
window.__skipThisMonthOverride__ = true;
thisMonthBtn.click();
window.__skipThisMonthOverride__ = false;
```

And check it at the top of `_wireThisMonthOverride`.

### Bug Reproduction Steps
1. Set a breakpoint or log in `_wireSiblingChipDeactivation` and `init()` click listener.
2. Click "Next Month" chip.
3. Observe: `_wireSiblingChipDeactivation` exits early because `__nextMonthFilterActive__` is still false. `init()` click listener **never fires** because `stopImmediatePropagation()` blocks it. No 800 ms debounced re-apply is scheduled.

---

## Finding 3: User Clicks "This Week" During the 120 ms Window — Partial-DOM Filter Application

**Severity:** HIGH  
**Location:** Lines 4245–4263 (`_activateNextMonth`), 4450–4464 (`_wireSiblingChipDeactivation`), 4525–4531 (`MutationObserver` debounce)  

### Root Cause
The sequence when a user clicks "Next Month" then immediately clicks "This Week" (< 120 ms):

1. **t = 0 ms**: User clicks "Next Month" chip.
   - `_activateNextMonth` runs.
   - `thisMonthBtn.click()` is swallowed (Finding 1). React state unchanged.
   - `__nextMonthFilterActive__ = true`.
   - `setTimeout(applyFilters, 120)` scheduled.

2. **t = 50 ms**: User clicks "This Week" chip.
   - **Capture phase**, `_wireSiblingChipDeactivation` fires first. It sees `__nextMonthFilterActive__` is `true`. It sets `__nextMonthFilterActive__ = false` and styles the Next Month chip inactive.
   - **Capture phase**, `_wireThisMonthOverride` fires second. Label is "This Week", not "This Month". `__thisMonthOverrideActive__` is false. No action.
   - React processes "This Week" click (not swallowed). React begins re-render.

3. **t = 120 ms**: The timeout from step 1 fires.
   - `applyFilters()` runs.
   - `__nextMonthFilterActive__` is now `false` (turned off at step 2).
   - BUT React may still be in the middle of re-rendering "This Week". The DOM could contain:
     - Old cards from the previous React state that haven't been removed yet.
     - New "This Week" cards that haven't finished mounting.
   - `applyFilters` computes visibility against this **partially-updated DOM**.
   - The `MutationObserver` (line 4511) may or may not yet have observed new cards, because React's batch update might not have flushed to the DOM.

4. **t = 500–800 ms**: Observer or click-listener timeout fires.
   - `safeApply()` runs again, re-filtering the now-complete DOM.

Between t = 120 ms and t = 500–800 ms, the user sees a **stale, partially-filtered DOM**. Cards may be incorrectly hidden or shown. The counter sync (lines 3808–3878) at t = 120 ms writes an incorrect `shownCount` to the counter span, which persists until the next `applyFilters` pass.

### Fix Recommendation
1. Make `_activateNextMonth` wait for React's state to settle before scheduling `applyFilters`. Use a longer timeout (e.g., 300 ms) or, better, wrap the timeout in `requestAnimationFrame` + `setTimeout` to wait for the next paint:
   ```javascript
   requestAnimationFrame(function () {
     setTimeout(function () { applyFilters(); }, 0);
   });
   ```
2. Ensure that sibling-chip deactivation also **cancels** the pending 120 ms timeout:
   ```javascript
   // In _wireSiblingChipDeactivation, when deactivating:
   clearTimeout(window._nextMonthApplyTimeout);
   ```

### Bug Reproduction Steps
1. Throttle CPU to 4× slowdown (DevTools Performance tab).
2. Click "Next Month".
3. Within 50 ms, click "This Week".
4. Observe the grid between 120 ms and 500 ms: cards may flash, be incorrectly hidden, or the counter may show a wrong number.

---

## Finding 4: Multiple Overlapping `setTimeout` Sources — No Global Re-Entry Guard

**Severity:** HIGH  
**Location:** Lines 4259–4262, 4467–4553 (`init()`), 3756–3806 (`applyFilters` loop-guard)  

### Root Cause
`applyFilters()` can be invoked from **at least seven independent asynchronous sources**, with **no global mutex** to prevent concurrent or re-entrant execution:

| Source | Timeout | Guard |
|--------|---------|-------|
| `_activateNextMonth` | 120 ms | **None** |
| `_deactivateNextMonth` | 120 ms | **None** |
| `_wireThisMonthOverride` (This Month) | 200 ms | **None** |
| `_wireThisMonthOverride` (Last Day) | 180 ms | **None** |
| `init()` MutationObserver | 500 ms (`window._filterTimeout`) | `clearTimeout` only |
| `init()` capture click listener | 800 ms (`window._categoryClickTimeout`) | `clearTimeout` only |
| `init()` initial load | 2500 ms | `_selfModifying` (local) |
| Loop-guard bail-out | 0 ms (`setTimeout(0)`) | **None** |

The only guard is `_selfModifying` inside `safeApply()` (lines 4501–4507), but:
- It is a **local variable**, not global. Two separate `safeApply` invocations from overlapping timeouts each get their own `_selfModifying` instance and can run concurrently.
- The 120 ms, 180 ms, 200 ms, and 0 ms timeouts call `applyFilters` **directly**, bypassing `safeApply` entirely.

If `applyFilters` is running while React is simultaneously re-rendering (e.g., after a chip click), the function reads and mutates the DOM mid-mutation:
- It adds `event-card-hidden` classes and sets `gridItem.style.display = 'none'`.
- It injects TBD tags, multi-day indicators, and distance indicators into card titles.
- It updates the counter span (line 3849).

A second overlapping `applyFilters` pass sees the already-mutated DOM and computes `shownCount`/`hiddenCount` against a mixture of React's new cards and the first pass's CSS mutations. The loop-guard (lines 3766–3803) uses `purePeriodShownCount` which depends on card dates that may have shifted between passes.

### Fix Recommendation
Introduce a **global re-entry guard** at the top of `applyFilters`:

```javascript
function applyFilters() {
  if (window.__applyFiltersRunning__) return;
  window.__applyFiltersRunning__ = true;
  try {
    // ... existing body ...
  } finally {
    window.__applyFiltersRunning__ = false;
  }
}
```

Also, consolidate all `setTimeout` IDs into a single cancellation mechanism and ensure every path that triggers `applyFilters` goes through the guarded wrapper:

```javascript
function scheduleApplyFilters(delay) {
  clearTimeout(window._filterTimeout);
  window._filterTimeout = setTimeout(function () {
    safeApply();
  }, delay);
}
```

### Bug Reproduction Steps
1. Load the page with a slow network.
2. Rapidly click "This Month", then "Next Month", then "All Dates" within 300 ms.
3. Observe console: multiple `[FILTERS] Applying filters` logs appear within the same millisecond.
4. The grid may end up in an inconsistent state (wrong cards visible, wrong counter).

---

## Finding 5: Second `applyFilters` Pass Computes Counts Against Already-Mutated DOM, Loop-Guard Can Bail Incorrectly

**Severity:** MEDIUM  
**Location:** Lines 3730–3744 (visibility toggle), 3756–3806 (loop-guard)  

### Root Cause
Lines 3730–3744 mutate the DOM imperatively:
```javascript
card.classList.remove('event-card-hidden');   // or .add(...)
gridItem.style.display = '';                  // or 'none'
```

If `applyFilters` runs twice in rapid succession (e.g., the 120 ms timeout from `_activateNextMonth` and the 800 ms timeout from `init()` click listener), the second pass:
1. Calls `document.querySelectorAll('[class*="glass-panel"]...')` (line 3421).
2. Iterates over cards that may already have `event-card-hidden` class and `display: none` from the first pass.
3. Recomputes `shouldShow` for each card. Some cards that were hidden in pass 1 may now be shown (or vice versa) because global flags changed.
4. The `shownCount` and `hiddenCount` reflect the **second pass's decisions**, but the DOM is a mix of React's latest render and the first pass's mutations.

The **loop-guard** (lines 3756–3806) is especially vulnerable:
```javascript
if (window.__thisMonthOverrideActive__) {
  if (purePeriodShownCount === 0 && hiddenCount > 0) {
    window.__thisMonthHideStreak__ = (window.__thisMonthHideStreak__ || 0) + hiddenCount;
    if (window.__thisMonthHideStreak__ >= 50) {
      window.__thisMonthOverrideActive__ = false;  // ← bail
      window.__thisMonthHideStreak__ = 0;
      setTimeout(function () { applyFilters(); }, 0);  // ← re-run
    }
  }
}
```

If pass 1 (e.g., from the 120 ms timeout) runs with `__thisMonthOverrideActive__ = true` and hides 50 cards with `purePeriodShownCount = 0`, the guard bails, sets `__thisMonthOverrideActive__ = false`, and schedules a 0 ms re-run. If, in the meantime, the 800 ms timeout from `init()` also fires, or the observer fires, we now have **three** `applyFilters` calls queued or running concurrently. The 0 ms re-run sees a DOM already mutated by pass 1. If React also re-rendered in the interim, the card set is different. The re-run computes a new `shownCount`/`hiddenCount`. If this re-run also finds 0 pure-period cards and >0 hidden, the streak could increment again—but `__thisMonthHideStreak__` was reset to 0 at bail, so it starts from the new `hiddenCount`.

More importantly, if the **first** pass hid cards that React has since removed, the second pass won't find them, resulting in a lower `hiddenCount`. The guard may then NOT bail when it should, or it may bail when it shouldn't, depending on the exact interleaving.

### Fix Recommendation
1. Make the loop-guard use **React's raw data** (`__RAW_EVENTS__`) rather than DOM-derived counts to decide whether to bail. DOM mutation counts are inherently racy.
2. Alternatively, snapshot the card list at the start of `applyFilters` and operate on the snapshot array, so concurrent passes don't interfere:
   ```javascript
   const cards = Array.from(document.querySelectorAll(...));
   cards.forEach(function(card) { ... });
   ```
   This is already mostly true because `querySelectorAll` returns a static NodeList, but the **properties and children** of each node are live.
3. Reset `__thisMonthHideStreak__` at the **beginning** of every `applyFilters` when `__thisMonthOverrideActive__` is true, rather than conditionally:
   ```javascript
   if (window.__thisMonthOverrideActive__) {
     window.__thisMonthHideStreak__ = 0;  // fresh start each pass
   }
   ```

### Bug Reproduction Steps
1. Enable "This Month" on a day where the first 50 React-rendered cards are all past/ongoing events (so `purePeriodShownCount = 0`).
2. The loop-guard bails after the first pass.
3. Before the 0 ms re-run fires, scroll the page to trigger React lazy-loading.
4. The re-run sees a different card set. The counter and grid may show inconsistent numbers.

---

## Finding 6: Global Flags Read/Written by Multiple Async Paths Without Atomic Guards

### Flag 6a: `__nextMonthFilterActive__`

**Severity:** CRITICAL  
**Location:** Lines 4257, 4267, 4387–4388, 4460, 3640, 3752  

**Read/Write Sites:**
- **Write** in `_activateNextMonth` (line 4257): `window.__nextMonthFilterActive__ = true;`
- **Write** in `_deactivateNextMonth` (line 4267): `window.__nextMonthFilterActive__ = false;`
- **Write** in `_wireThisMonthOverride` (line 4387–4388): sets `false` when "This Month" is clicked while Next Month was active.
- **Write** in `_wireSiblingChipDeactivation` (line 4460): sets `false` when any sibling chip is clicked.
- **Read** in `applyFilters` (line 3640): gates Next Month filtering.
- **Read** in `applyFilters` (line 3752): gates Next Month badge refresh.
- **Read** in `_wireSiblingChipDeactivation` (line 4455): early-return guard.
- **Read** in `_injectNextMonthChip` (line 4281): visual sync.
- **Read** in `_renderNextMonthDateBadges` (line 4104): bail if inactive.

**Root Cause:** This flag is a plain boolean on `window`. There is no lock, mutex, or transaction. It can be toggled by:
  - A capture-phase click handler (synchronous with user input)
  - An `applyFilters` pass (asynchronous, 120–800 ms later)
  - A `MutationObserver` callback (microtask or subsequent tick)

A user can click "Next Month" (sets `true`), then click "This Week" (sets `false` via `_wireSiblingChipDeactivation`), but the 120 ms `applyFilters` timeout from the first click still fires and runs with `__nextMonthFilterActive__ = false`. That specific case is benign. However, the reverse race is dangerous: if `_wireSiblingChipDeactivation` fires AFTER the 120 ms timeout begins executing but BEFORE it reads `__nextMonthFilterActive__`, the flag could flip mid-function. In practice, because JavaScript is single-threaded, the flag read inside `applyFilters` is atomic relative to the event loop. But if `applyFilters` were made asynchronous internally (e.g., `await` or generator), this would be a real data race.

More importantly, the **logical** race is severe: the flag is set to `true` (line 4257) BEFORE React has actually updated its DOM. If the programmatic `thisMonthBtn.click()` were not swallowed, React would still be re-rendering. During that re-render, the flag says `true`, but the DOM is stale. Any `applyFilters` call in that window (from the 120 ms timeout, observer, or click listener) uses the stale DOM.

**Fix Recommendation:** Make the flag assignment happen ONLY after React's DOM update is confirmed, or couple the flag tightly with the chip's visual state and always read it from the chip itself rather than a separate global:
```javascript
function isNextMonthActive() {
  var chip = document.getElementById('next-month-chip');
  return chip && chip.classList.contains('bg-gradient-to-r');  // or similar
}
```

---

### Flag 6b: `__thisMonthOverrideActive__`

**Severity:** HIGH  
**Location:** Lines 4400, 4426, 4436, 4442, 3505, 3659, 3766, 3783, 3802  

**Read/Write Sites:**
- **Write** in `_wireThisMonthOverride` (line 4400): `false` for last-day shortcut.
- **Write** in `_wireThisMonthOverride` (line 4426): `true` for normal This Month click.
- **Write** in `_wireThisMonthOverride` (line 4436): `false` when sibling clicked.
- **Write** in `_wireThisMonthOverride` (line 4442): `false` when Next Month chip clicked.
- **Write** in `applyFilters` loop-guard (line 3783): `false` on bail-out.
- **Read** in `applyFilters` (line 3505): gates TBD fallback hiding.
- **Read** in `applyFilters` (line 3659): gates This Month override filtering.
- **Read** in `applyFilters` (line 3766): gates loop-guard.
- **Read** in `applyFilters` (line 3802): resets streak.
- **Read** in `applyFilters` (line 3804): resets streak when override off.

**Root Cause:** Same as 6a—no atomic guard. A particularly dangerous sequence:
1. User clicks "This Month" → `__thisMonthOverrideActive__ = true`.
2. Loop-guard in `applyFilters` sees 50 hidden, 0 pure-period → bails, sets `__thisMonthOverrideActive__ = false`.
3. `setTimeout(applyFilters, 0)` scheduled.
4. Before the 0 ms timeout, user clicks "This Week" → `_wireThisMonthOverride` sees `__thisMonthOverrideActive__` is now `false`, does nothing.
5. React processes "This Week".
6. 0 ms timeout fires → `applyFilters` without override.
7. 800 ms timeout from `init()` click listener fires → `safeApply` runs AGAIN.

The DOM flickers as three passes compete. The flag transitions from `true` → `false` in `applyFilters`, but there's no queue or state machine to serialize these transitions.

**Fix Recommendation:** Centralize all state transitions in a single state machine function, e.g.:
```javascript
function setFilterState(next) {
  window.__nextMonthFilterActive__ = next.nextMonth || false;
  window.__thisMonthOverrideActive__ = next.thisMonth || false;
  if (next.nextMonth === false) { _removeNextMonthDateBadges(); }
  scheduleApplyFilters(0);
}
```

---

### Flag 6c: `__thisMonthHideStreak__`

**Severity:** MEDIUM  
**Location:** Lines 3773, 3784, 3782, 3802, 3805  

**Read/Write Sites:**
- **Write** in `applyFilters` (line 3773): increments by `hiddenCount`.
- **Write** in `applyFilters` (line 3784): resets to `0` on bail.
- **Write** in `applyFilters` (line 3802): resets to `0` when pure-period shown.
- **Write** in `applyFilters` (line 3805): resets to `0` when override inactive.
- **Read** in `applyFilters` (line 3782): threshold check `>= 50`.

**Root Cause:** The streak is incremented by `hiddenCount` from the **current pass**. If two `applyFilters` runs overlap and the second pass sees a different DOM (e.g., React lazy-loaded more cards), the streak value may be nonsensical—either too high (first pass hid 50, second pass adds 50 more → 100) or too low (first pass reset to 0, second pass starts over). Because there is no re-entry guard (Finding 4), overlapping passes can corrupt the streak logic.

**Fix Recommendation:** Compute the streak purely from `__RAW_EVENTS__` metadata or from a stable snapshot, not from live DOM counts. Or guard the streak update so only one pass at a time can modify it:
```javascript
if (window.__thisMonthOverrideActive__ && !window.__applyFiltersRunning__) {
  // ... streak logic ...
}
```

---

### Flag 6d: `__todayStart`

**Severity:** LOW  
**Location:** Lines 3418, 3551–3555, 3596–3600, 3664, 3748  

**Read/Write Sites:**
- **Write** in `applyFilters` (line 3418): recomputed at start.
- **Read** in multiple filter blocks throughout `applyFilters`.

**Root Cause:** Recomputed at the start of every `applyFilters` call. If two calls overlap, the second call overwrites the value while the first call is still using it. In practice, because all date comparisons use `__todayStart` consistently within a single synchronous pass, this is low risk. However, if any async operation were introduced inside `applyFilters` (e.g., fetching additional data), the shared variable could cause inconsistent date boundaries.

**Fix Recommendation:** Pass `todayStart` as a local variable instead of a global:
```javascript
var todayStart = (function() { ... })();
// use todayStart locally, don't assign to window.__todayStart
```

---

## Summary Table

| # | Severity | Location | Root Cause | Fix |
|---|----------|----------|------------|-----|
| 1 | CRITICAL | 4245–4256, 4373–4445 | `stopImmediatePropagation()` in capture phase swallows same-element `click()` | Defer programmatic clicks with `setTimeout(..., 0)` |
| 2 | CRITICAL | 4450–4464, 4373–4445, 4539–4552 | Capture listener registration order + `stopImmediatePropagation()` blocks init()'s debounce | Guard against programmatic clicks with `!e.isTrusted` or flag |
| 3 | HIGH | 4245–4263, 4450–4464 | 120 ms timeout fires against partially-updated React DOM | Cancel pending timeout on sibling click; use `rAF` + `setTimeout` |
| 4 | HIGH | 4259–4262, 4467–4553 | 7 independent `setTimeout` sources, no global re-entry guard | Add `window.__applyFiltersRunning__` mutex; consolidate scheduling |
| 5 | MEDIUM | 3730–3744, 3756–3806 | Second pass counts against DOM mutated by first pass; loop-guard uses DOM-derived counts | Use raw data for bail logic; reset streak at start of each pass |
| 6a | CRITICAL | 4257, 4267, 4387–4388, 4460 | `__nextMonthFilterActive__` toggled by multiple async paths | Centralize state transitions; derive from chip DOM |
| 6b | HIGH | 4400, 4426, 4436, 4442, 3766, 3783 | `__thisMonthOverrideActive__` toggled by handlers and loop-guard | Single state machine; re-entry guard |
| 6c | MEDIUM | 3773, 3784, 3782, 3802, 3805 | `__thisMonthHideStreak__` corrupted by overlapping passes | Guard with `__applyFiltersRunning__` or compute from raw data |
| 6d | LOW | 3418 | `__todayStart` global overwritten by concurrent passes | Use local variable |

---

*Report generated from static analysis of `/mnt/agents/repos/index.html` and verified with live browser event-propagation tests.*
