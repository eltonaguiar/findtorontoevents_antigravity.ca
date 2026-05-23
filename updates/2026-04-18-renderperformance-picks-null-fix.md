# Fix: TypeError — Cannot read properties of undefined (reading 'picks')

**Date:** 2026-04-18
**File:** `audit_dashboard/template.html`
**Commit:** `eeacc3d7af` (branch: `fix/audit-gate-regressions-20260414`)

---

## What was broken

The audit dashboard crashed at runtime with:

```
Uncaught (in promise) TypeError: Cannot read properties of undefined (reading 'picks')
    at audit/:13370:24
    at Array.forEach (<anonymous>)
    at renderPerformance (audit/:13367:10)
    at init (audit/:14552:3)
```

**Root cause:** Inside `renderPerformance()`, `Object.entries(strategyMap)` iterates `[name, data]` pairs. In 8 locations, `data.picks` was accessed without optional chaining. When `data` was `undefined` (possible if the map entry was malformed or a strategy alias resolved to a key with no entry), the `.picks` property access threw a TypeError.

The init-time guard `if (!D.picks) D.picks = {...}` only protects `D.picks` — not intermediate objects inside `strategyMap`.

## What was changed

8 instances of `data.picks` → `data?.picks` (optional chaining) in `audit_dashboard/template.html`:

### Inside `renderPerformance()` (5 fixes — the crash site)

| Line (approx) | Before | After |
|---|---|---|
| ~13391 | `calcStats(data.picks \|\| [])` | `calcStats(data?.picks \|\| [])` |
| ~13393 | `(data.picks \|\| []).map(p => p.pnl_pct \|\| 0)` | `(data?.picks \|\| []).map(p => p.pnl_pct \|\| 0)` |
| ~13399 | `(data.picks \|\| []).map(p => p.close_time \|\| ...)` | `(data?.picks \|\| []).map(p => p.close_time \|\| ...)` |
| ~13846 | `(data.picks \|\| []).length >= 3` | `(data?.picks \|\| []).length >= 3` |
| ~13847 | `calcStats(data.picks \|\| [])` | `calcStats(data?.picks \|\| [])` |

### Outside `renderPerformance()` (3 fixes — same vulnerability pattern)

| Line (approx) | Before | After |
|---|---|---|
| ~10311 | `resolved.liveRows.length ? resolved.liveRows : (data.picks \|\| [])` | `...(data?.picks \|\| [])` |
| ~14271 | `(data.picks \|\| []).map(p => ...)` — claude parser | `(data?.picks \|\| []).map(...)` |
| ~14274 | `(data.picks \|\| []).map(p => ...)` — kimi parser | `(data?.picks \|\| []).map(...)` |

### Lines NOT changed (already safe)

- `data && Array.isArray(data.picks)` — guarded by `data &&`
- `(data && data.picks) \|\| []` — guarded by `data &&`
- `!data \|\| !data.picks` — guarded by `!data \|\|`
- `const picks = data.picks;` — guarded by prior `if (!data \|\| !data.picks)` early return

## How it was verified

1. **Post-fix search:** `grep -c 'data?.picks'` confirmed 8 occurrences; `grep 'data.picks'` (excluding `data?.picks`) confirmed only 4 already-guarded lines remain.
2. **Python compile check:** `py_compile.compile('audit_trail/dashboard_generator.py')` passed (template.html is embedded by the generator).
3. **Code review:** 2 rounds of `code-reviewer-lite` approved. Second review flagged 3 additional unsafe lines outside `renderPerformance`, which were also fixed.
4. **Behavior preserved:** The `|| []` fallback is retained in all 8 fixes, so when `data` is `undefined`, the result is an empty array — identical to the previous behavior when `data` was defined with an empty picks list.

## Related: hc_gate_params.json 404

The browser console also showed a 404 for `config/hc_gate_params.json`. This was fixed separately in commit `86ddea2130` ("hc_filter.js 404 cleanup"). The `initHcGateParamsForAudit()` function tries multiple URLs and gracefully falls through — the 404 is cosmetic.

## Deployment note

Per project convention, only `template.html` was edited (not `index.html`). The CI `audit-dashboard` workflow regenerates `index.html` from `template.html` on the next scheduled or push-triggered run.
