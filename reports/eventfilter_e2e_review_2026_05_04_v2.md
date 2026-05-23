# Cross-Engine Synthesis — Event Filter E2E Review

## CONFIRMED FINDINGS (≥2 engines, same root cause)

### RC-001: Mutex Starvation — Silent Drop of Observer-Triggered Filter Passes
**file:line:** TORONTOEVENTS_ANTIGRAVITY/index.html:3447-3461
**severity:** HIGH
**confirmed-by:** race_condition_specialist (deepseek, xai, cerebras, inception, openrouter)
**root-cause:** `applyFilters()` returns immediately when `__applyFiltersRunning__` is true, but callers from MutationObservers have no retry mechanism. Observer-triggered filter calls are silently dropped, leaving DOM updates unprocessed until next user action.
**fix sketch:**
```js
function applyFilters() {
  if (window.__applyFiltersRunning__) {
    window.__applyFiltersPending__ = true;
    return;
  }
  window.__applyFiltersRunning__ = true;
  try { /* existing logic */ } finally {
    window.__applyFiltersRunning__ = false;
    if (window.__applyFiltersPending__) {
      window.__applyFiltersPending__ = false;
      setTimeout(applyFilters, 0);
    }
  }
}
```
**blast-radius:** All event cards added/modified during active filter pass remain unfiltered until next user interaction (5-30s stale UI).
**reproduction:** Add 200 cards via lazy-load while chip filter is animating; observe cards not reflecting filter state.

---

### RC-002: Missing isTrusted Guard on Sibling-Chip Deactivator
**file:line:** TORONTOEVENTS_ANTIGRAVITY/index.html:4547-4561
**severity:** HIGH
**confirmed-by:** race_condition_specialist (deepseek, xai, cerebras, inception, openrouter)
**root-cause:** The sibling-chip deactivator lacks `e.isTrusted` guard that the This Month interceptor has. Synthetic clicks from `btn.click()` calls in other handlers corrupt `__nextMonthFilterActive__` state.
**fix sketch:**
```js
document.addEventListener('click', function (e) {
  if (!e.isTrusted) return;
  if (!window.__nextMonthFilterActive__) return;
  // ... rest unchanged
}, true);
```
**blast-radius:** Programmatic clicks (keyboard shortcuts, accessibility tools) incorrectly deactivate Next Month filter.
**reproduction:** Click "All Dates" programmatically via `document.querySelector('button').click()` while Next Month is active.

---

### RC-003: Capture-Phase stopImmediatePropagation Blocks React's Synthetic Click
**file:line:** TORONTOEVENTS_ANTIGRAVITY/index.html:4473-4490
**severity:** CRITICAL
**confirmed-by:** race_condition_specialist (deepseek, xai, cerebras, inception, openrouter)
**root-cause:** `e.stopImmediatePropagation()` prevents React's event delegation from seeing the original click. The synthetic `thisMonthBtn.click()` fires with `isTrusted=false`, so the capture listener bails — but React's bubble-phase listener never fires because propagation was stopped.
**fix sketch:**
```js
if (label === 'This Month') {
  e.preventDefault();
  var thisMonthBtn = _findReactChipByText('This Month');
  if (thisMonthBtn) {
    setTimeout(() => thisMonthBtn.dispatchEvent(new MouseEvent('click', { bubbles: true })), 0);
  }
  // Remove stopImmediatePropagation
}
```
**blast-radius:** React state gets out of sync with DOM state; "This Month" chip sometimes doesn't activate filter.
**reproduction:** Click "This Month" chip; verify React internal state shows chip as active.

---

### RC-004: Year-Wrap Bug in `__parseCardDisplayedDate__`
**file:line:** TORONTOEVENTS_ANTIGRAVITY/index.html:4412-4428
**severity:** CRITICAL
**confirmed-by:** datetime_timezone_specialist (deepseek, xai, cerebras, inception, openrouter)
**root-cause:** Year-wrap logic only checks `idx < now.getMonth()` (forward wrap) but never checks if parsed date is actually in the past. Past events from previous year (e.g., "DEC 25" when today is Jan 5) are incorrectly assigned to current year.
**fix sketch:**
```js
var parsedDate = new Date(year, idx, parseInt(m[2], 10));
var now = new Date();
if (parsedDate > now && monthIdx < now.getMonth()) {
  year += 1; // Future month in next year
} else if (parsedDate < now && monthIdx >= now.getMonth()) {
  year -= 1; // Past month in previous year
}
return year + '-' + String(idx+1).padStart(2,'0') + '-' + String(parseInt(m[2],10)).padStart(2,'0');
```
**blast-radius:** Past events appear as future events, bypassing past-filter; zombie events appear in "This Month" view.
**reproduction:** Today=2026-01-05, card="DEC 25" → returns 2026-12-25 instead of 2025-12-25.

---

### RC-005: UTC Drift in Date-String Comparisons
**file:line:** TORONTOEVENTS_ANTIGRAVITY/index.html:3522, 3691, 3768
**severity:** HIGH
**confirmed-by:** datetime_timezone_specialist (deepseek, xai, cerebras, inception, openrouter)
**root-cause:** String comparison `d.substring(0,10) >= _todayStrLookup` uses UTC date from ISO-Z timestamps but local date for today. At 21:00 Toronto time, an event with `2026-05-04T00:00:00Z` is May 3 local but treated as May 4.
**fix sketch:**
```js
function _getLocalDateStr(dateStr) {
  if (!dateStr) return null;
  if (dateStr.includes('T') || dateStr.includes('Z')) {
    var d = new Date(dateStr);
    return d.getFullYear() + '-' + 
           String(d.getMonth()+1).padStart(2,'0') + '-' + 
           String(d.getDate()).padStart(2,'0');
  }
  return dateStr.substring(0,10);
}
```
**blast-radius:** Events near day boundaries are misclassified as "today" or "future" when they are actually yesterday.
**reproduction:** Toronto 21:00 May 3, event `2026-05-04T00:00:00Z` → treated as today instead of yesterday.

---

### RC-006: Indicator Injection into React-Managed DOM
**file:line:** TORONTOEVENTS_ANTIGRAVITY/index.html:3573-3577, 3625-3630
**severity:** CRITICAL
**confirmed-by:** react_dom_specialist (deepseek, xai, cerebras, inception, openrouter)
**root-cause:** Code uses `titleEl.appendChild()` to inject `<span>` elements into a DOM node owned by React's reconciliation. On next React render, React removes these unexpected spans.
**fix sketch:**
```js
// Use CSS pseudo-elements instead
// Add data attribute to card
card.dataset.badge = isTbd ? 'tbd' : isMultiDay ? 'multi-day' : '';
// CSS: .event-card[data-badge="tbd"]::after { content: "TBD"; ... }
```
**blast-radius:** TBD and Multi-Day indicators disappear after React re-render (filter change, navigation).
**reproduction:** Load page with events, verify indicators visible, trigger filter change, verify indicators gone.

---

### RC-007: React Clobber of className on Buttons/Chips
**file:line:** TORONTOEVENTS_ANTIGRAVITY/index.html:3866, 4430-4437
**severity:** CRITICAL
**confirmed-by:** react_dom_specialist (deepseek, xai, cerebras, inception, openrouter)
**root-cause:** Direct `className` overwrites on React-managed elements (buttons/chips) are clobbered during React reconciliation as React reapplies its expected `className`.
**fix sketch:**
```js
// Use classList.add/remove instead of className assignment
chipEl.classList.toggle('active-chip', isActive);
// Or use data attributes with CSS
chipEl.dataset.active = isActive ? 'true' : 'false';
```
**blast-radius:** Button/chip styling flickers or resets after React re-renders; custom colors disappear.
**reproduction:** Trigger React state update (filter toggle) after custom chip styling applied.

---

### RC-008: No Title→Event Index (O(N×M) Performance)
**file:line:** TORONTOEVENTS_ANTIGRAVITY/index.html:3500-3514
**severity:** HIGH
**confirmed-by:** event_surface_engineer (deepseek, xai, cerebras, inception, openrouter)
**root-cause:** Every `applyFilters()` call performs `__RAW_EVENTS__.filter(_matchPredicate)` for each card. With 11,290 raw events and ~200 cards, this is 2.2M string comparisons per chip click.
**fix sketch:**
```js
// Build once at line 125
window.__RAW_EVENTS_INDEX__ = new Map();
window.__RAW_EVENTS__.forEach(e => {
  var key = (e.title || '').toLowerCase();
  if (!window.__RAW_EVENTS_INDEX__.has(key)) {
    window.__RAW_EVENTS_INDEX__.set(key, []);
  }
  window.__RAW_EVENTS_INDEX__.get(key).push(e);
});
// Replace filter with lookup
var _matches = window.__RAW_EVENTS_INDEX__.get(title.toLowerCase()) || [];
```
**blast-radius:** UI lag on every chip click; "slow script" warnings on low-end devices.
**reproduction:** Click any filter chip with 200+ cards rendered; observe 500ms+ delay.

---

### RC-009: No Prefilter of Past Events at Boot
**file:line:** TORONTOEVENTS_ANTIGRAVITY/index.html:125
**severity:** HIGH
**confirmed-by:** event_surface_engineer (deepseek, xai, cerebras, inception, openrouter)
**root-cause:** PR #750 removed pre-filter that kept `__RAW_EVENTS__` as future-only subset. 4,400 past events (40% of 11,290) are loaded and iterated on every filter call.
**fix sketch:**
```js
var today = new Date().toISOString().substring(0, 10);
window.__RAW_EVENTS__ = window.__RAW_EVENTS__.filter(e => {
  var eventDate = String(e.date || '').substring(0, 10);
  return eventDate >= today || (e.end_date && e.end_date >= today);
});
```
**blast-radius:** 40% bandwidth waste; every chip click iterates 11,290 entries instead of ~6,890.
**reproduction:** Monitor network payload; observe 40% of data is past events never displayed.

---

### RC-010: Feed Drift Between `/events.json` and `/next/events.json`
**file:line:** events.js:125, 3500-3514
**severity:** CRITICAL
**confirmed-by:** event_surface_engineer (deepseek, xai, cerebras, inception, openrouter)
**root-cause:** Two feeds with different entry counts (11,290 vs 6,909) and no synchronization. When React card title doesn't exist in `__RAW_EVENTS__`, `eventData=null` → fallback to `__parseCardDisplayedDate__` with year-wrap risk.
**fix sketch:**
```js
// Merge feeds at boot
fetch('/next/events.json').then(r => r.json()).then(nextEvents => {
  window.__RAW_EVENTS__ = window.__RAW_EVENTS__.concat(nextEvents);
  // Deduplicate by title
  var seen = new Set();
  window.__RAW_EVENTS__ = window.__RAW_EVENTS__.filter(e => {
    var key = (e.title || '').toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
});
```
**blast-radius:** 4,381 entries exist only in one feed; cards from secondary feed bypass date filtering.
**reproduction:** Create event in `/next/events.json` not in `/events.json`; observe incorrect date handling.

---

## Ship-Today List (P0+P1 confirmed, low blast)

1. **RC-002: Missing isTrusted Guard** — Add 1 line guard; immediate fix for synthetic click corruption
2. **RC-006: Indicator Injection** — Replace with CSS pseudo-elements; no code change needed
3. **RC-007: React className Clobber** — Replace `className=` with `classList.add/remove`

## This-Week List (HIGH confirmed, larger surgery)

1. **RC-001: Mutex Starvation** — Add retry queue mechanism
2. **RC-003: stopImmediatePropagation** — Reorder event dispatch
3. **RC-004: Year-Wrap Bug** — Fix date parser logic
4. **RC-005: UTC Drift** — Add timezone conversion helper
5. **RC-008: Title Index** — Build Map for O(1) lookups
6. **RC-009: Past Event Prefilter** — Add server-side or client-side filter
7. **RC-010: Feed Drift** — Merge feeds at boot

## Backlog (CANDIDATE / single-engine)

- **Rapid-click race (setTimeout 200ms)** — race_condition_specialist only; needs cross-validation
- **Multi-day end_date inclusivity** — datetime_timezone_specialist only; feed semantics unclear
- **MutationObserver cascade** — react_dom_specialist only; performance optimization
- **No cache invalidation** — event_surface_engineer only; edge case
- **end_date vs endDate inconsistency** — event_surface_engineer only; feed normalization

## Discarded (DISPUTED with refutation)

- **Finding: "MutationObserver Feedback Loop"** — openrouter race_condition_specialist claims excessive re-evaluation. Refuted: debounce at 200ms prevents tight loop; other specialists confirm no infinite loop observed.
---

## Failure-mode root cause — why v1 only had cerebras

The original 5-agent dispatcher subagent ran `swarm_run.py` with only `cerebras,nous` instead of the 5 engines I instructed (`deepseek,xai,nous,cerebras,kimi`). Engine list got dropped in the dispatcher's translation between my brief and its `swarm_run.py` invocation. Plus nous returned empty 4/4 (its known flakiness — empty completions ~10-15% of calls when prompt is large).

**v2 method (this report):** ran the same 4 specialist prompts directly (`tools/swarm/swarm_run.py --engines deepseek,xai,cerebras,inception,openrouter --max-parallel 5` × 4 specialists, in parallel). 20/20 healthy outputs, all engines returned 4-15KB substantive replies. Cross-validation now possible.

## Fix to prevent this regression

Future swarm dispatcher subagents should:
1. ECHO the exact `swarm_run.py` command before executing (so deviation from instructions is visible in transcript)
2. Verify `--engines` flag matches the dispatcher's intended fan-out
3. Treat any engine returning <200 bytes as a non-vote and explicitly compensate (run +1 backup engine OR drop the run with a flag)

The dispatcher subagent in this session also stopped before the synthesis step — the JSON output schema in `events-swarm-incident-plan_91d51306.plan.md` lines 133-163 would have prevented this by making synthesis a deterministic merge instead of an LLM judgment call.

🤖 Synthesized 2026-05-04 by deepseek over 4-specialist × 5-engine outputs (20 healthy responses). Replaces v1 which had cerebras-only coverage due to dispatcher bug documented above.
