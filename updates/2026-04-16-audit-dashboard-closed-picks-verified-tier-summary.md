# Audit dashboard: Closed Picks parity, `getVerifiedTier` fix, and live verification

**Date:** 2026-04-16  
**Last updated:** 2026-04-16 — backend **`at_issue_*`** snapshots wired in `dashboard_generator.py` (see related note)  
**Scope:** Unified Audit Dashboard (`/audit/`) — Active vs Closed pick tables, verified-edge classification, payload shaping, and regression tests.

**Maintenance:** When you fix `/audit/` behavior, add a short subsection under **Fixes** (or **Enhancements**), bump **Last updated**, and add a focused note under **`updates/`** if the change deserves its own file (link it in **Related detail notes**).

---

## Summary

We restored reliable rendering of Active and Closed pick grids, aligned **Closed Picks** default columns with **Active Picks** (with sensible “at signal” vs “after close” semantics for stats that move when a trade hits the book), hardened **verified-edge** tier logic in shipped HTML, fixed **`buildVerifiedEdgeIndex()`** ordering in **`index.html`** so production no longer throws on strategy keys during index build, extended the dashboard generator so slim closed rows can show **Exit** when only `close_price` exists, added **Playwright** coverage (local + production), and deployed the fixed assets to **`https://findtorontoevents.ca/audit/`**.

---

## Fixes

### 1. Corrupted `getVerifiedTier` in `audit_dashboard/index.html`

**Problem:** A bad merge left the TRACK branch using `idx` / `combo_key` / `s` before declaration, with GOLDEN/VERIFIED logic after an unconditional `return`. Every row called `getVerifiedTier` → **`ReferenceError: idx is not defined`** → **`renderPicks()` aborted** → no `tbody` rows in `#tab-active` or `#tab-closed` (overview could still show summary chips, which was misleading).

**Change:** Replaced the function body to match the known-good `template.html` order: guard `window._verifiedEdgeIndex`, derive keys, **GOLDEN → VERIFIED → TRACK**, with null-safe reads. Additional guard: require `goldenCombos` and `verifiedStrats` on the index object so a partial index never throws during lookups.

**Expected benefit:** Pick tables render again; sorting, filters, and EDGE row styling work; no silent half-rendered dashboard.

**Follow-up hardening:** After loading external `dashboard_data.json`, the page calls **`buildVerifiedEdgeIndex()`** again when the payload is applied, and normalizes **`D.picks` / `D.summary`** so missing shapes do not break `init`/`renderPicks`.

**Expected benefit:** Fresh JSON from `/audit/data/` keeps verified-edge tiers in sync with the new closed book; fewer undefined-access crashes on partial or evolving payloads.

### 2. `verified_edge` / related control-flow in dashboard HTML

**Problem:** Prior edits had left brace/control-flow issues in the EDGE cell path (risk of parse errors or wrong branches).

**Change:** Repaired the `verified_edge` rendering chain so the file parses and behaves consistently (kept in sync between `index.html` and `template.html` per `audit_dashboard/check_template_sync.py`).

**Expected benefit:** Fewer brittle runtime/parse failures on deploy; consistent EDGE badges between generator output and hand-maintained template.

### 3. `buildVerifiedEdgeIndex()` — `verifiedStrats` used before initialization (`index.html`)

**Problem:** The **trackStrats** loop ran **before** **`verifiedStrats`** was assigned. Accessing **`verifiedStrats[sk3]`** threw (**`Cannot read properties of undefined (reading 'claude_gainer_1h')`** — first strategy key in iteration). That error surfaced inside **`loadExternalDashboardDataIfFresher()`**’s `try` and was reported as an external JSON “fetch failed”. The index was never assigned, so **`getVerifiedTier`** could then throw on **`trackCombos`**. **`template.html`** already had the correct order.

**Change:** Reordered **`audit_dashboard/index.html`** to match **`template.html`**: fill **goldenCombos** and **verifiedStrats** first, then **trackCombos** and **trackStrats**.

**Expected benefit:** Index build always completes; **`init()`** / **`renderPicks()`** succeed after external **`dashboard_data.json`** load; production console clean for this path.

### 3a. Non-crypto aggregate WR / PnL (Ex-killed client recompute)

**Problem:** Aggregate header counted only picks with **non-empty** `asset_class`, so **FOREX** rows like `*=X` with missing class were **dropped** from the aggregate while category cards still counted them. W/L used **`pnl > 0`** instead of **`FLAT_PNL_THRESHOLD` (0.01%)** / **`getResolvedTradePnl`**, diverging from server `compute_non_crypto_performance` and understating or skewing WR vs coin-flip expectations.

**Change:** **`isNonCryptoPickUnified`** + same outcome rules as server/cards; see **`updates/2026-04-16-audit-non-crypto-wr-pnl-measurement-fix.md`**.

**Expected benefit:** Aggregate line matches the non-crypto cards and server bucketing; fewer “broken” sub-40% artifacts driven by **excluded** winning FX volume or mis-bucketed micro-PnL.

---

## Enhancements

### 4. Closed Picks columns mirror Active defaults

**Behavior:**

- **`buildClosedColsFromActiveDefaults()`** builds the closed grid from **`allActiveCols.filter(c => c.default)`**, skipping live-only columns (e.g. `_livePrice`), mapping **`current_price` → `exit_price`**, and using delta column keys for trust and forward stats where the book changes after a close.
- **Trust / FWD WR / FWD N** use snapshot-style fields where available, with directional arrows when post-close (ledger) values differ; **tooltips** describe **NEW** values after TP/SL (and trust tier strings when present).
- **Exit** cell uses **`exit_price` || `close_price`**.
- **Resolved trades:** compact **TP / SL / TIME / WIN / LOSS / OUT** in status where applicable; TP/SL “remaining %” shows **—** when resolved.

**Expected benefit:** Users can compare “what we believed at signal” vs “how the strategy book moved after this trade closed” without cross-referencing Active vs Closed mentally; clearer post-mortems and less confusion about EDGE/FWD stats drifting after a close.

### 5. `audit_trail/dashboard_generator.py` — `close_price` on slim closed rows

**Change:** **`_CLOSED_PICK_KEEP_FIELDS`** includes **`close_price`** so `recent_closed` slim rows can populate the **Exit** column when `exit_price` is absent.

**Expected benefit:** Fewer blank Exit cells on historical rows; better data completeness in the dashboard JSON → UI.

---

## Testing & operations

| Asset | Role |
|--------|------|
| `tests/audit_verified_edge_active_picks.spec.ts` | Local `/audit/`: `getVerifiedTier` + index sanity; Active rows; Closed headers (Exit, Trust, FWD WR, FWD N, EDGE); critical console/page errors. |
| `tests/audit_remote_tabs_no_errors.spec.ts` | **Production** `findtorontoevents.ca/audit/`: load, tab clicks (Active, Closed, Overview, Smart Picks), same error gates + row sanity. |
| `playwright.config.ts` | `testMatch` entries so `npx playwright test` discovers the new specs. |

**Commands:**

```powershell
# Local (with serve_local via webServer)
npx playwright test tests/audit_verified_edge_active_picks.spec.ts --project="Desktop Chrome"

# Live site (no local server)
$env:VERIFY_REMOTE='1'; npx playwright test tests/audit_remote_tabs_no_errors.spec.ts --project="Desktop Chrome"
```

**Deploy:** `python tools/deploy_to_ftp.py --audit-only` uploads `/audit/` and `/audit_dashboard/` mirrors (including fixed `index.html` / `template.html`).

---

## Expected results (acceptance)

1. **Active Picks** and **Closed Picks** show **data tables with rows** after load (not empty panels behind correct summary counts).
2. **No critical JS errors** (SyntaxError, ReferenceError, ChunkLoadError, ModSecurity blocks, etc.) on initial load and when switching tabs.
3. **`getVerifiedTier`** runs without throw; **`_verifiedEdgeIndex`** has the expected maps for classification.
4. **Closed** grid shows **Exit / Trust / FWD WR / FWD N / EDGE** (and other default Active-aligned columns) with **at-issue vs delta** UX where implemented.
5. **CI / local** can lock this in via the Playwright specs above.

---

## Related detail notes

| File | Topic |
|------|--------|
| **`updates/2026-04-15-audit-getVerifiedTier-index-corruption.md`** | `getVerifiedTier` merge regression (`idx` before init); deploy / remote test commands. |
| **`updates/2026-04-16-audit-buildVerifiedEdgeIndex-verifiedStrats-order.md`** | `buildVerifiedEdgeIndex` **trackStrats** vs **verifiedStrats** order; `claude_gainer_1h` / `trackCombos` console errors. |
| **`updates/2026-04-16-audit-non-crypto-wr-pnl-measurement-fix.md`** | Non-crypto **aggregate** vs **cards** alignment; `FLAT_PNL_THRESHOLD` + symbol heuristics for empty `asset_class`. |
| **`updates/2026-04-16-audit-backend-at-issue-snapshot-wired.md`** | **`at_issue_*`** fields now set in **`dashboard_generator.py`** (were allowlist-only). |
