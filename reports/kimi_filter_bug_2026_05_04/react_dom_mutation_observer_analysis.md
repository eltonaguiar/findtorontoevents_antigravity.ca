# React DOM Integration & MutationObserver Bug Analysis
## `/mnt/agents/repos/index.html`

---

## Finding 1: chipObserver Infinite-Loop Risk via Self-Triggering Mutations
**Severity:** HIGH
**Location:** Lines 4483–4488, 4275–4302

### Root Cause
`chipObserver` watches `document.body` with `{childList: true, subtree: true}`. When React re-renders the chip row, `_scheduleInject()` schedules `_injectNextMonthChip()` after 250 ms. However, `_injectNextMonthChip()` unconditionally removes the existing chip (`existing.parentNode.removeChild(existing)` at line 4284) and inserts a new one via `thisMonthBtn.insertAdjacentElement('afterend', btn)` at line 4300. Both `removeChild()` and `insertAdjacentElement()` are DOM mutations that match the observer's `childList` filter and will fire back into `_scheduleInject()`. The 250 ms debounce (`_injectDebounce`) prevents an *immediate* tight loop, but if React re-renders again during that 250 ms window, the queue becomes a chain of back-to-back injections. The `existing && existing.previousElementSibling === thisMonthBtn` guard at line 4279 should short-circuit on the *next* observer tick, but during the first re-render it evaluates `false` because the old chip was just yanked, so the removal+insertion path always runs at least once per React re-render, doubling the DOM churn.

### Fix Recommendation
Track a "re-entrant" flag inside `_injectNextMonthChip` so the observer-scheduled call is skipped while the function itself is actively mutating the chip row:
```js
var _injecting = false;
function _injectNextMonthChip() {
  if (_injecting) return;
  _injecting = true;
  try { /* existing body */ } finally { _injecting = false; }
}
function _scheduleInject() {
  if (_injectDebounce || _injecting) return;
  _injectDebounce = setTimeout(function () {
    _injectDebounce = null;
    _injectNextMonthChip();
  }, 250);
}
```

### Affected Scenario
Any React state change that re-renders the chip row (e.g., user clicks "This Week" then "This Month", or Next.js router transition causing a layout refresh).

---

## Finding 2: Fragile Sibling-Guard in `_injectNextMonthChip` Breaks on Row Restructure
**Severity:** CRITICAL
**Location:** Lines 4275–4284

### Root Cause
The chip-injection guard `existing && existing.previousElementSibling === thisMonthBtn` (line 4279) assumes the Next Month chip must be the *immediate* next sibling of the "This Month" button. If React re-renders and inserts an additional chip (e.g., an "Ongoing" toggle or a new category chip) between "This Month" and the Next Month chip, this condition becomes `false`. The code then falls through to line 4284 (`existing.parentNode.removeChild(existing)`), **removes the already-correctly-placed chip**, and later re-inserts it at line 4300 *after* `thisMonthBtn` — which is now the wrong position because the new React chip now sits between them. Worse, if `_findReactChipByText('This Month')` moves or is removed by React, `thisMonthBtn` is null and the entire injection silently fails with `return false`.

### Fix Recommendation
Replace the strict `previousElementSibling` test with a looser "is this chip still inside the same chip-row parent" check, and use a dedicated marker class to locate the chip regardless of sibling order:
```js
var chipRow = thisMonthBtn && thisMonthBtn.closest('[class*="chip-row"], [role="tablist"]');
var existing = document.getElementById('next-month-chip');
if (existing && chipRow && chipRow.contains(existing)) {
  _setNextMonthChipClass(existing, !!window.__nextMonthFilterActive__);
  return true;
}
```

### Affected Scenario
Next.js releases a UI update that adds chips to the filter bar, or A/B tests a new chip ordering.

---

## Finding 3: React Reconciliation Can Erase Imperative `visibility: hidden` on Date Labels
**Severity:** MEDIUM
**Location:** Lines 4207–4226

### Root Cause
`_renderNextMonthDateBadges()` walks card leaf nodes and hides React's intrinsic date label by setting `node.style.visibility = 'hidden'` (line 4222). The inline comment at line 4204 claims: *"React will not reconcile away"* an inline style change because they *"do NOT mutate React's tree (no textContent rewrite, no removal) — only toggle visibility"*. This is a dangerous assumption. When React re-renders a card (e.g., because the parent list re-sorts, or a prop update refreshes the component), React's reconciliation **fully rewrites inline styles** if the component's render path applies any style prop or CSS-in-JS class to that same element. If the date-label element receives a `style` or `className` from React's virtual DOM, React's commit phase will overwrite the imperative `visibility: hidden` with whatever the VDOM prescribes (typically `visibility: visible` or an empty style). Once that happens, both the original React date label and the overlay badge are visible simultaneously.

### Fix Recommendation
Instead of mutating the leaf's inline style, use CSS `!important` injected by the vanilla script:
```js
// In a one-time injected <style>:
// .__nm_date_override ~ [data-date-label] { visibility: hidden !important; }
```
Or, wrap the badge inside a positioned overlay container that completely covers the date column with an opaque background, so even if React restores visibility, the label is physically hidden behind the badge tile. The existing `min-width:64px; min-height:56px;` badge already partially does this, but ensure it fully occludes the React label area.

### Affected Scenario
React lazy-loads new cards, user scrolls, or React state change causes card re-render while Next Month filter is active.

---

## Finding 4: Inline `display: none` on `.group` Parent Is Vulnerable to React Reconciliation
**Severity:** HIGH
**Location:** Lines 3738–3742, 3731–3735

### Root Cause
`applyFilters()` mutates the parent `.group` wrapper's inline display style:
```js
var gridItem = card.closest('.group');
if (gridItem) { gridItem.style.display = 'none'; }   // line 3742
```
The parent `.group` is likely rendered by React as part of the grid layout component. React does not "own" the inline style on a DOM node in the sense that it ignores unknown attributes, but if the React component that renders the `.group` ever receives a prop/state update that affects layout classes or a `style` prop on that same node, React will overwrite the entire inline style block. Because vanilla JS sets `display: none` on the *parent* while React manages the *child* card, a React re-render of the grid item can reset `gridItem.style.display = ''` (or whatever the component's render output dictates), causing a hidden card to reappear even though the child `card` still carries the `event-card-hidden` class.

### Fix Recommendation
Use a CSS class toggle on the `.group` wrapper instead of an inline style mutation, because React typically preserves unknown classes during reconciliation:
```js
// In injected stylesheet:
// .group.event-group-hidden { display: none !important; }

// In applyFilters:
if (shouldShow) {
  card.classList.remove('event-card-hidden');
  var gridItem = card.closest('.group');
  if (gridItem) gridItem.classList.remove('event-group-hidden');
} else {
  card.classList.add('event-card-hidden');
  var gridItem = card.closest('.group');
  if (gridItem) gridItem.classList.add('event-group-hidden');
}
```

### Affected Scenario
React lazy-load triggers a re-render of grid items, or user interacts with a filter that causes the parent grid component to update its wrapper props.

---

## Finding 5: Race Condition Between 800ms Capture Listener and 200ms `_wireThisMonthOverride`
**Severity:** CRITICAL
**Location:** Lines 4539–4552, 4424–4430

### Root Cause
Two independent timers compete after a user clicks a React chip:
1. **Capture-phase listener** (line 4539): on any click inside a `<button>` not owned by `#custom-filter-controls`, schedules `safeApply()` at **800 ms**.
2. **`_wireThisMonthOverride`** (line 4373): when the user clicks "This Month", it first calls `thisMonthBtn.click()` (line 4425) — which itself fires the capture listener — then schedules `applyFilters()` at **200 ms** (line 4429).

Timeline of the race:
- `t=0`: User clicks This Month chip. The override handler fires.
- `t=0`: Override handler calls `thisMonthBtn.click()`, which synthesizes a click event. The capture listener at line 4539 sees this synthetic click and schedules `safeApply()` at `t=800`.
- `t=200`: Override's own `applyFilters()` runs. It mutates DOM visibility and may inject/remove chips.
- `t=500–800`: React finishes its own re-render in response to the chip click.
- `t=800`: The capture listener's `safeApply()` fires. At this point the DOM may be in an **inconsistent intermediate state**: React has partially committed new cards, but some old cards still linger in the DOM tree. `applyFilters()` runs over this mixed DOM. Since `safeApply()` sets `_selfModifying = true` for the duration, the MutationObserver (line 4511) is *reentrantly* suppressed, so any new cards React injects during this window are **not** observed, and the filter pass may miss them entirely.

### Fix Recommendation
Add a `window._lastUserFilterClick` timestamp in `_wireThisMonthOverride` and check it in the capture listener so the 800ms callback is skipped when the override handler already ran the much sooner 200ms pass:
```js
// In _wireThisMonthOverride:
window._lastUserFilterClick = Date.now();
setTimeout(function () { /* existing applyFilters */ }, 200);

// In capture listener:
window._categoryClickTimeout = setTimeout(function() {
  if (window._lastUserFilterClick && Date.now() - window._lastUserFilterClick < 900) {
    return; // Override handler already handled this interaction
  }
  safeApply();
}, 800);
```

### Affected Scenario
User clicks "This Month" or any other React chip; the 800ms stale-DOM pass corrupts card visibility and counter sync.

---

## Finding 6: `requestAnimationFrame` Polling Stalls in Background Tabs; 5s Fallback Can Fire Prematurely
**Severity:** HIGH
**Location:** Lines 4589–4603

### Root Cause
`__whenReactHydrated__` polls via `requestAnimationFrame(poll)` (line 4592). In background tabs, browsers throttle `rAF` to ~1 fps or pause it entirely. If the user opens the page in a background tab, `rAF` may fire only sporadically, delaying the `hydrated()` probe. The 5-second `setTimeout(fire, 5000)` hard fallback (line 4600) exists, but `arm()` is only called once, and `poll()` loops on `rAF`. If the tab is backgrounded, `poll()` may miss the window between `t=0` and `t=5000` when React finishes hydration, and then the 5-second fallback fires `init()` even though `hydrated()` is still `false` — because `fire()` does not re-check `hydrated()`; it is an unconditional *"give up"* trigger. This means `init()` can run while `thisMonthBtn` does not exist yet, causing `_injectNextMonthChip()` to return `false` and the chip is never injected.

### Fix Recommendation
Change `fire()` to perform a final hydration check before proceeding, and replace the single `rAF` loop with a mixed strategy that also uses `setInterval` for background-tab resilience:
```js
function fire() {
  if (fired) return;
  if (!hydrated()) {
    // Still not ready; keep polling via setInterval as fallback
    var iv = setInterval(function() {
      if (hydrated()) { clearInterval(iv); fire(); }
    }, 250);
    // Absolute ceiling: 10s total
    setTimeout(function() { clearInterval(iv); if (!fired) { fired = true; window.__reactHydrated__ = true; try { cb(); } catch(_) {} } }, 10000);
    return;
  }
  fired = true;
  window.__reactHydrated__ = true;
  try { cb(); } catch (_) {}
}
```

### Affected Scenario
User opens the events page in a background tab on mobile/desktop; React hydration completes after the 5s fallback but before the tab becomes active.

---

## Finding 7: MutationObserver Debounce (500ms) Is Too Short for Large Lazy-Load Batches
**Severity:** HIGH
**Location:** Lines 4511–4534

### Root Cause
The `MutationObserver` for new event cards uses a 500 ms debounce (line 4527). React's lazy-loader may insert cards in waves: e.g., first 10 cards at `t=0`, next 15 at `t=300`, next 25 at `t=600`. The observer fires on the first wave, and `safeApply()` runs at `t=500`. At that point only 25 cards exist, but 50 more are still in-flight. `applyFilters()` then evaluates the partial set. If the "This Month" override is active and the first 25 cards are all past events (common because React orders by start-date ascending), the loop-guard (line 3772) sees `purePeriodShownCount === 0` and `hiddenCount = 25`, increments `__thisMonthHideStreak__` by 25, and at `t=500` the streak is only 25 (below the 50 threshold). But when the *remaining* 25 cards arrive at `t=600` (after the debounce fired), the observer schedules a second pass. Now the streak becomes 50 and the guard **disables the override prematurely** even though the full batch would have contained valid current-month cards had `safeApply()` waited for the complete lazy-load batch.

### Fix Recommendation
Extend the debounce to at least **1500 ms** for lazy-load scenarios, or add a "batch settled" heuristic: reset and extend the timeout if mutations keep arriving within a sliding window:
```js
var _cardTimeout = null;
function scheduleSafeApply() {
  clearTimeout(_cardTimeout);
  _cardTimeout = setTimeout(function() {
    safeApply();
    hideSkeletons && hideSkeletons();
  }, 1200); // 1200ms covers typical React lazy-load burst
}
```

### Affected Scenario
User scrolls down on a filtered view (e.g., "This Month") while React's infinite-scroll loader is fetching the next page of events.

---

## Summary Table

| # | Severity | Location | Trigger |
|---|----------|----------|---------|
| 1 | HIGH | 4483–4488, 4275–4302 | React re-renders chip row |
| 2 | CRITICAL | 4275–4284 | Chip row structure changes |
| 3 | MEDIUM | 4207–4226 | Card re-render while Next Month active |
| 4 | HIGH | 3738–3742 | React reconciles `.group` parent |
| 5 | CRITICAL | 4539–4552, 4424–4430 | User clicks React chip (This Month) |
| 6 | HIGH | 4589–4603 | Page loaded in background tab |
| 7 | HIGH | 4511–4534 | Lazy-loaded card batches arriving |

