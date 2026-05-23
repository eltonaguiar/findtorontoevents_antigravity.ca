# 2026-04-15 — Audit dashboard hoisting crashes (trackCombos / claude_gainer_1h)

## Symptoms

Two errors breaking `/audit/` init:

```
audit/:1928 [Audit] External data/dashboard_data.json fetch failed:
    Cannot read properties of undefined (reading 'claude_gainer_1h')

audit/:1858 Uncaught (in promise) TypeError:
    Cannot read properties of undefined (reading 'trackCombos')
    at getVerifiedTier (audit/:1858:25)
    at renderPicks (audit/:8283:231)
    at init (audit/:14624:3)
```

`init()` failed; the dashboard fell back to embedded data but then threw again the moment `fetchLivePrices` re-rendered picks.

## Root causes

Both bugs are `var`-hoisting traps introduced when someone shuffled code without re-reading execution order. `var` hoists the binding, but **not the assignment**, so a forward reference sees `undefined`.

### Bug 1 — `buildVerifiedEdgeIndex` (audit_dashboard/template.html ~L1789)

Loop order was:

1. `var goldenCombos = {}`
2. loop populating `trackCombos` — reads `goldenCombos[ck2]` (OK, it's an empty object)
3. loop populating `trackStrats` — reads `!verifiedStrats[sk3]`  ← crash
4. `var verifiedStrats = {}` (only now assigned)
5. loops that actually fill `goldenCombos` / `verifiedStrats`

On step 3, `verifiedStrats` is hoisted but still `undefined`, so `undefined[sk3]` throws `TypeError: Cannot read properties of undefined (reading 'claude_gainer_1h')` — "claude_gainer_1h" is just whichever strategy key happened to be iterated first. Red herring that sent us looking at the kill-list set when the bug was 100 lines away.

When `buildVerifiedEdgeIndex` threw, the assignment to `window._verifiedEdgeIndex = {...}` at the bottom never ran, so the index stayed `null`, which then caused bug 2 to fire the first time anything called `getVerifiedTier`.

### Bug 2 — `getVerifiedTier` (audit_dashboard/template.html ~L1856)

```js
function getVerifiedTier(p) {
  // TRACK: combo or strategy has 3+ trades but doesn't qualify...
  var combo_track = idx.trackCombos ? idx.trackCombos[combo_key] : null;  // ← crash
  ...
  return { tier: null, ... };
  var idx = window._verifiedEdgeIndex;   // dead code after the return
  var s = String(p.strategy || '');
  var combo_key = s + '||' + sym;
  ...
}
```

`idx`, `s`, `combo_key` are declared AFTER an unconditional `return`, so they're effectively unused-but-hoisted — `idx` is `undefined` when line 1858 reads `idx.trackCombos`. The TRACK branch was pasted in front of the variable declarations instead of after them, and the original GOLDEN/VERIFIED logic became unreachable dead code.

## Fix

`audit_dashboard/template.html` only (per CLAUDE.md — do not edit `index.html`).

**`buildVerifiedEdgeIndex`:** Moved the `goldenCombos` / `verifiedStrats` population loops to run *before* the `trackCombos` / `trackStrats` loops that depend on them. Order is now:

1. init `goldenCombos = {}`, `verifiedStrats = {}`
2. populate both (the dependencies)
3. init + populate `trackCombos` (reads `goldenCombos`)
4. init + populate `trackStrats` (reads `verifiedStrats`)
5. `stratOverallOk` (unchanged)
6. `window._verifiedEdgeIndex = { ... }`

**`getVerifiedTier`:** Hoisted `var idx = window._verifiedEdgeIndex; var s, sym, combo_key;` to the top of the function, added `if (!idx) return { tier: null, ... }` guard, and restored priority order (GOLDEN → VERIFIED → TRACK combo → TRACK strat). Defensive optional-chaining on `idx.goldenCombos && idx.goldenCombos[...]` etc., so a partial index can't crash the page.

## Verification

- `node -e` parsed all 8 `<script>` blocks in template.html — 0 syntax errors.
- Manual trace of both functions — no remaining forward `var` references.
- Not regenerated `index.html` locally (CLAUDE.md forbids running dashboard generators); CI will pick the change up on next publish.

## Lesson

Two separate blocks where somebody reordered code and the `var` hoist masked the bug at load time — the error only fired once iteration reached a key that tripped the property access. When a crash names a random-looking property (here, a strategy name from an unrelated kill list), look for *where the containing object became `undefined`*, not where the property name is defined.
