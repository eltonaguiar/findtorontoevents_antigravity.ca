# Fix: `buildVerifiedEdgeIndex` used `verifiedStrats` before initialization (`index.html`)

## Symptoms (production console)

- `[Audit] External data/dashboard_data.json fetch failed: Cannot read properties of undefined (reading 'claude_gainer_1h')`
- `init() failed: TypeError: Cannot read properties of undefined (reading 'trackCombos')` at `getVerifiedTier`

## Root cause

In `audit_dashboard/index.html`, **`buildVerifiedEdgeIndex()`** ran the **trackStrats** loop **before** **`verifiedStrats`** was declared and populated. In that loop, `!verifiedStrats[sk3]` evaluated **`verifiedStrats`** while it was still **`undefined`** (only the `var` hoist applies; the object is assigned later). The first strategy key in the iteration (e.g. `claude_gainer_1h`) surfaced in the error message.

The function then **threw** before `window._verifiedEdgeIndex` was assigned, so the index stayed **`null`**. **`getVerifiedTier`** on older bundles could then hit **`idx.trackCombos`** with **`idx` null**, producing the **`trackCombos`** error.

`audit_dashboard/template.html` already used the correct order (golden + verified first, then track combos/strats).

## Change

Reordered **`index.html`** to match **`template.html`**: compute **`goldenCombos`** and **`verifiedStrats`** first, then **`trackCombos`** and **`trackStrats`**.

## Verification

- `python audit_dashboard/check_template_sync.py` — OK  
- `npx playwright test tests/audit_verified_edge_active_picks.spec.ts tests/audit_remote_tabs_no_errors.spec.ts --project="Desktop Chrome"`

## Expected benefit

External JSON load and initial index build complete without throwing; `_verifiedEdgeIndex` is always populated with **`trackCombos` / `trackStrats`**; **`init()`** and **`renderPicks()`** run cleanly on `https://findtorontoevents.ca/audit/`.

**Rolling summary:** **`updates/2026-04-16-audit-dashboard-closed-picks-verified-tier-summary.md`** — keep that file updated when adding new audit-dashboard fixes.
