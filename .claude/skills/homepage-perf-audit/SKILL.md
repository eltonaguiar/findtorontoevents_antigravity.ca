---
name: homepage-perf-audit
description: >
  Audit findtorontoevents.ca homepage for performance issues and filter bugs,
  including date-filter chips (All Dates, Today, This Week, This Month), the
  Dating/evergreen category, multi-day events toggle, and near-me proximity
  filter. Covers both the React event-grid widget and the vanilla JS
  applyFilters() layer in index.html. Aliases - homepageaudit, filteraudit,
  homepage-check, perf-audit
---

# Homepage Performance & Filter Audit — Skill

This skill diagnoses and fixes the dual-filter architecture on
`findtorontoevents.ca`, covering:

- **Date filter chips** (All Dates, Today, Tomorrow, This Week, This Month)
- **Evergreen / Dating category** (events with no specific date)
- **Multi-day events toggle** and **near-me proximity filter**
- **React `validEvents` pipeline** (in the minified Next.js bundle)
- **Vanilla JS `applyFilters()`** in `TORONTOEVENTS_ANTIGRAVITY/index.html` (~line 3450)
- **Redundant fetch chain** (4 simultaneous events.json requests)
- **Production console noise** (per-event debug logging for 11,560+ events)

---

## Step 1 — Gather live console output

Open DevTools → Console on `https://findtorontoevents.ca` and copy all log lines. 
Look for these prefixes:

| Prefix | Layer | What it means |
|--------|-------|---------------|
| `[FILTERS]` | Vanilla JS (`index.html`) | `applyFilters()` ran |
| `[validEvents]` | React widget | Data-layer filter ran |
| `[Filter Debug] Event N` | React widget | Per-event verbose log (perf issue if frequent) |
| `[Data Source]` | React widget | events.json fetch attempt |
| `[EventFeed]` | React widget | Display count after filtering |
| `⚠️ [EventFeed] 'now' not set` | React widget | Race condition — filter ran before clock set |

---

## Step 2 — Known issues checklist

Run through these checks. For each, note `PASS / WARN / FAIL`.

### A. Fetch redundancy
```
grep "[Data Source] Success" <console_log> | wc -l
```
Expected: 1 (canonical URL only). If >1, each extra fetch wastes ~1-2 MB bandwidth.

**Fix:** In the React data-fetching hook (`useEventsFromGitHub` or equivalent),
short-circuit after the first successful fetch. Remove the `Local Subdir` and
`Local Data Folder` fallbacks if `Local Root` already succeeds:

```js
// Before: all 4 sources tried in parallel
const sources = [localRoot, localSubdir, localDataFolder, github];

// After: waterfall — stop at first success
for (const src of sources) {
  try { const data = await fetchSource(src); if (data?.length) return data; }
  catch (_) {}
}
```

---

### B. `now=undefined` race condition
Look for `⚠️ [EventFeed] 'now' not set yet` in the log.

**Root cause:** `validEvents` memo runs synchronously on mount before `now` state
is initialised (typically set via `useEffect` → `setNow(new Date())`).

**Fix:** Initialise `now` to `new Date()` directly in `useState`:
```js
// Before:
const [now, setNow] = useState(null);

// After:
const [now, setNow] = useState(() => new Date());
```
This eliminates the `undefined` flash entirely.

---

### C. Dual-filter counter mismatch
Look for counter jumps like `6785 → 49 → 0 → 23`.

**Root cause:** Two independent systems update the same counter `<span>`:
1. React updates it to `validEvents.length` (e.g. 6,785)
2. `applyFilters()` in `index.html` overwrites it with DOM-visible card count (e.g. 49)

These run at different times and see different views of truth.

**Fix:** Make `applyFilters()` read the React-owned count rather than overwriting it:
```js
// In applyFilters() around line 4061 of index.html
// BEFORE:
counterSpan.textContent = shownCount;

// AFTER — only update if React hasn't already set a larger, authoritative count:
const reactCount = parseInt(counterSpan.dataset.reactCount || '0', 10);
if (reactCount === 0 || shownCount > 0) {
  counterSpan.textContent = shownCount;
}
```
And in the React component, set `data-react-count` on the span when updating.

---

### D. O(n) per-event debug logging
Look for repeated `[Filter Debug] Event N: ...` lines.

**Check:** Count log lines: if >500 `Filter Debug` lines, this is active in production.

**Fix:** Gate behind `localStorage`:
```js
// In React filter hook, replace:
console.log(`[Filter Debug] Event ${i}:`, title, event);

// With:
if (window.__FILTER_DEBUG__) console.log(`[Filter Debug] Event ${i}:`, title, event);
```
Users can enable via `localStorage.setItem('__FILTER_DEBUG__', '1')` and `location.reload()`.

---

### E. Evergreen / Dating events in time filters
Look for `✅ [Filter] Including event with invalid date: "..."` during `this-week` or `today` filters.

**Desired behavior:** Events with no parseable date should:
- Always appear in `All Dates` filter
- **NOT** appear in `Today`, `Tomorrow`, `This Week`, `This Month` filters
- Optionally: appear in a dedicated **"Dating" / "Ongoing"** chip

**Fix — React side** (in `validEvents` computation):
```js
const isEvergreen = !event.start_date || isNaN(Date.parse(event.start_date));
if (isEvergreen) {
  return dateFilter === 'all'; // only include in "all"
}
```

**Fix — Vanilla JS side** (`applyFilters()`, date extraction block ~line 3600):
```js
// After extracting dateStr from card:
const isEvergreenCard = !dateStr || dateStr === 'TBD' || dateStr === '';
if (isEvergreenCard && anyDateFilterActive) {
  card.style.display = 'none';
  hiddenCount++;
  return; // skip to next card
}
```

---

### F. applyFilters() called 6+ times per interaction
Look for 4+ consecutive `[FILTERS] Applying filters` log lines after a single chip click.

**Root cause:** Multiple async triggers all call `applyFilters()`:
- Mutation observer (card DOM changes)
- Chip click handler
- `setTimeout(applyFilters, 0)` in `_activate()` / `_deactivate()`
- Lazy-load handler
- This-month override loop

**Fix:** Replace `setTimeout(applyFilters, 0)` chains with a single `requestAnimationFrame` debounce:
```js
let _rafPending = false;
function scheduleApplyFilters() {
  if (_rafPending) return;
  _rafPending = true;
  requestAnimationFrame(() => { _rafPending = false; applyFilters(); });
}
// Replace all setTimeout(applyFilters, 0) calls with scheduleApplyFilters()
```

---

### G. AdSense 400 errors
Look for `ads?client=ca-pub-...&slotname=1234567890` returning HTTP 400.

**Root cause:** Slot IDs `1234567890` and `0987654321` are placeholders.

**Fix:** Either configure real slot IDs in `adsense-integration.js`, or wrap ad
slots in a check:
```js
const REAL_SLOT_IDS = ['YOUR_REAL_SLOT_1', 'YOUR_REAL_SLOT_2'];
// Only push ads if slot ID is not a placeholder:
if (!slotId.match(/^(0+|1234567890|0987654321)$/)) {
  adsbygoogle.push({});
}
```

---

### H. 404 WebP image
`HiRes%20Cabbagetown%20North%20-%20Necropolis%20Chapel%20_DSV9901.jpg.webp` → 404.

**Fix:** Add an `onerror` fallback on the `<img>` tag, or use a placeholder:
```js
img.onerror = function() {
  this.src = '/images/placeholder-event.webp';
  this.onerror = null;
};
```

---

## Step 3 — Run the swarm for multi-engine analysis

```powershell
# From repo root (Windows):
python tools/swarm/swarm_run.py --config tools/swarm/examples/homepage_perf_audit.yaml

# Check results:
python tools/swarm/swarm_inspect.py --latest
```

Or via ruflo swarm (for deeper analysis):
```bash
# From WSL or PowerShell with WSL:
python3 .ruflo/orchestrator.py --swarm bugs --no-verify
```

Results land in `swarm_runs/run_<timestamp>/`. The compiled JSON summary
is at `swarm_runs/run_<timestamp>/_summary.json`.

---

## Step 4 — Prioritize and implement

Order of fix priority (highest ROI first):

1. **CRITICAL** — `now=undefined` race (instant flash of 11,560 events)
2. **CRITICAL** — Dual-filter counter mismatch (user sees wrong counts)
3. **HIGH** — Evergreen events in time filters (wrong events shown)
4. **HIGH** — Remove O(n) debug logging (perf impact on low-end devices)
5. **MEDIUM** — Fetch waterfall (saves 3× bandwidth on events.json)
6. **MEDIUM** — applyFilters debounce (reduces wasted work)
7. **LOW** — AdSense placeholder slots (cosmetic / revenue impact)
8. **LOW** — 404 image fallback (UX polish)

---

## Step 5 — Verify fixes

After each fix, reload the page and confirm:
- No `⚠️ [EventFeed] 'now' not set` in console
- Counter shows consistent number (no jumps)
- Evergreen events absent from `Today` / `This Week` filters
- `[Filter Debug]` lines absent (unless `__FILTER_DEBUG__` set)
- Only 1-2 `[Data Source] Success` lines (not 4)
- No 4+ consecutive `[FILTERS] Applying filters` bursts

Run the Playwright smoke tests:
```powershell
npx playwright test tests/no_js_errors.spec.ts tests/mental-health-resources.spec.ts --project="Desktop Chrome"
```
