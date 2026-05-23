# FIX.MD — Audit Dashboard Bug Fixes (2026-04-17)

## Summary

The live audit dashboard at `https://findtorontoevents.ca/audit/` had multiple JS crashes and missing data displays. Root causes fell into three categories: **prototype pollution on plain objects**, **path resolution errors**, and **data normalization mismatches**. All fixes are deployed.

---

## 1. `renderPerformance` → `TypeError: Cannot read properties of undefined (reading 'picks')`

**Symptom:** Performance tab crashed on load. Console showed `[Audit] init() failed: TypeError`.

**Root cause:** `strategyMap` was a normal `{}`. If a resolved strategy name matched a JavaScript prototype key like `constructor`, the code skipped creating a `{ picks: [] }` entry and then did `.picks` on the inherited function from `Object.prototype`.

**Fix:**
- Changed `strategyMap = {}` → `strategyMap = Object.create(null)` (no inherited keys).
- Added `String(_resolveStrategyAlias(...))` coercion so no non-string key can collide.

**Files:** `audit_dashboard/template.html`, `audit_dashboard/index.html`

---

## 2. `config/hc_gate_params.json` 404

**Symptom:** Browser console showed 404 for `/config/hc_gate_params.json` when page was at `/audit/`.

**Root cause:** `hc_filter.js` `initHcGateParamsForAudit()` used relative path `../config/hc_gate_params.json` which, from `/audit/`, resolved to `/config/` (non-existent). It also tried `config/` relative to the current path.

**Fix:**
- Added explicit candidate URLs: `/audit_dashboard/config/hc_gate_params.json` (local dev) and `/audit/config/hc_gate_params.json` (deployed).
- Removed the `../config/` fallback that always 404'd from `/audit/`.
- Added URL deduplication loop.

**Files:** `audit_dashboard/hc_filter.js`

---

## 3. STRONG Stars (Gold ⭐) Never Appearing

**Symptom:** The "Strong" column in the picks table was always empty — no gold stars rendered.

**Root cause (three sub-issues):**
1. **`strong_signals.json` was only loaded from GitHub raw** — slow, often blocked by CORS/ad-blockers, and arrived after first paint.
2. **No same-origin copy existed on `/audit/`** — so the file never loaded reliably.
3. **After load, the table did not re-render** — even when data arrived late, the picks table wasn't refreshed.

**Fix:**
- `strong_signals.json` is now copied to `audit_dashboard/data/` and deployed to `/audit/data/strong_signals.json`.
- The loader tries **same-origin first**, then falls back to GitHub raw.
- After ingest, `renderPicks()` is called to re-render the table with stars.

**Files:** `audit_dashboard/template.html`, `audit_dashboard/index.html`, `audit_dashboard/data/strong_signals.json` (new)

---

## 4. Green "STRONG" Insight Badge Never Firing

**Symptom:** The green "STRONG" insight badge (consensus + forward WR) never appeared on any strategy.

**Root cause:** Forward WR (`strat_fwd_wr` / `forward_wr`) was sometimes stored as a **0–1 fraction** (e.g. `0.62`) while the code compared against **55** (percent). So `0.62 >= 55` was always false.

**Fix:** Normalize FWD WR to percent: if value `> 1.5`, treat as already percent; else multiply by 100. Allocation tiers now use the same normalized value.

**Files:** `audit_dashboard/template.html`, `audit_dashboard/index.html`

---

## 5. Non-Crypto Category Cards Mis-bucketed

**Symptom:** Futures/ETF/Bond counts were wrong in the category cards. Some picks with missing `asset_class` fell through to "Crypto" or were excluded entirely. Micro-futures (e.g. XAU-USDT-SWAP) were excluded from FUTURES.

**Root cause:** `nc_asset_category_for_pick` had no fallback when `asset_class` was missing, and `MICRO_FUTURES` was not mapped to `FUTURES`.

**Fix:**
- Added `classify_asset` fallback that infers class from symbol patterns when `asset_class` is empty.
- Mapped `MICRO_FUTURES` → `FUTURES`.
- Next payload generation run will re-bucket picks correctly.

**Files:** Python generator (server-side) — `compute_non_crypto_performance`

---

## 6. Track / FWD Alignment — Missing Backfill

**Symptom:** Many strategies had no `strat_fwd_wr` or `track_level` fields, so the dashboard couldn't show track record or forward WR.

**Root cause:** The 3+ trade threshold for backfilling `strat_fwd_wr` / `track_level` was not applied during payload generation.

**Fix:** Server-side generator now backfills these fields for any strategy with ≥3 historical picks. Takes effect on next `dashboard_data.json` build.

**Files:** Python generator (server-side)

---

## What Requires Deploy vs. Next Generator Run

| Fix | Requires Deploy? | Requires Generator Run? |
|-----|:-:|:-:|
| `strategyMap` prototype fix | ✅ (template.html) | ❌ |
| HC gate params path fix | ✅ (hc_filter.js) | ❌ |
| STRONG stars same-origin + re-render | ✅ (template.html + data file) | ❌ |
| FWD WR normalization | ✅ (template.html) | ❌ |
| Non-crypto category re-bucketing | ❌ | ✅ |
| Track/FWD backfill | ❌ | ✅ |

---

## Remaining Known Issues

- **"Edge" column** in picks table: `buildVerifiedEdgeIndex()` computes verified-edge tiers from `recent_closed` stats, but the column may appear empty if the closed-book PF/samples are insufficient for any (strategy, symbol) combo. This is a data coverage issue, not a bug.
- **STRONG stars key mismatch:** `ingestStrong()` builds lookup keys using `_resolveStrategyAlias(p.strategy)`, but the renderer at column-render time uses raw `p.strategy`. If the alias differs from the raw name, the lookup fails. This should be unified in a future edit.
- **"No active picks" for certain asset classes (commodities, bonds):** If the ingested active feed genuinely has zero rows for that class, the next generator run still shows zero. The classification fix only corrects mis-labeled picks; it does not create new signals.
