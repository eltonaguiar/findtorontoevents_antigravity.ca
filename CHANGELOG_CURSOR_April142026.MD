# Changelog — Cursor session (2026-04-14)

## Audit dashboard (`/audit/`) — High Conviction, console 404, integrity banner

### 1. `hc_gate_params.json` fetch URL (console 404)

**Issue:** `initHcGateParamsForAudit()` built the config URL with `new URL('config/hc_gate_params.json', origin + pathname)`. When the pathname was `/audit` (no trailing slash), the URL API resolved the relative path against the site root, producing **`/config/hc_gate_params.json`**, which returns **404** on findtorontoevents.ca. The live file is under **`/audit/config/hc_gate_params.json`**.

**Fix:** Normalize the pathname to a directory before resolving: strip a trailing filename (e.g. `index.html`), or append `/` for path segments like `/audit`. All of `/audit`, `/audit/`, and `/audit/index.html` now resolve to `/audit/config/hc_gate_params.json`.

**File:** `audit_dashboard/hc_filter.js`

**Note:** Embedded defaults in `hc_filter.js` still apply if the fetch fails; loading the deployed JSON removes drift vs production tuning and avoids noisy DevTools errors.

### 2. DATA INTEGRITY warning while “High Conviction” is on

**Issue:** The red banner compared “visible” active rows (after **High Conviction** and other narrowing) to the full backend active count, but it did **not** treat the High Conviction preset as an intentional filter. That produced a **false “stale embedded data”** message when only one row passed `filterHcStrict`.

**Fix:** Reuse the same narrowing predicate as the summary “filters active” logic via shared helpers:

- `computeUiFilterNarrowing()` — dropdown filters + score tier + `_convictionOnlyFilter`, Verified Alpha, Xiaomi Mimo entry, score gate, etc.
- `integrityStaleDataSuppressed()` — the above **or** hedge-fund book / proven narrowing **or** Smart Picks mode.

The integrity banner runs inside **`renderPicks`**, so it cannot reference `hasFilters` from **`renderSummary`** (different scope).

**Files:** `audit_dashboard/template.html`, `audit_dashboard/index.html` (kept in sync for FTP deploy).

### 3. Regression: `ReferenceError: hasFilters is not defined`

**Cause:** An intermediate edit referenced `hasFilters` inside `renderPicks`, where that binding does not exist, which **broke page init** until corrected with `integrityStaleDataSuppressed()` / the helpers above.

**Status:** Corrected and redeployed with `python tools/deploy_to_ftp.py --audit-only`.

### 4. “Only one High Conviction pick” — expected vs misleading

With **full** `dashboard_data.json` loaded, a **small** High Conviction row count is often **expected**:

- **`filterHcStrict`** = `filterHighConvictionOrdered` (`hc_filter.js` gates, e.g. forward stats, trust, independent group consensus where applicable) **plus** `passesValidatedEdgePerClass`, which only allows **CRYPTO / EQUITY / FOREX** with documented edge rules and **excludes** commodity / bond / ETF / futures from the HC view by design.
- Correlation dedup and strict gates further shrink the list.

The misleading part was the **integrity banner** implying broken data when HC was doing its job; that is addressed in §2.

### Deploy

- Audit bundle (including `hc_filter.js`, `index.html`, `template.html`, `data/dashboard_data.json`, `config/hc_gate_params.json`) uploaded under `findtorontoevents.ca/audit/` and mirrored `audit_dashboard/` paths per `tools/deploy_to_ftp.py`.

### Verification

- Remote: `https://findtorontoevents.ca/audit/` — hard refresh after deploy.
- Playwright: `VERIFY_REMOTE=1 npx playwright test tests/audit_hc_conviction_e2e.spec.ts --project="Desktop Chrome"` (use repo-root spec path if the workspace has duplicate specs under worktrees).

---

## AG — Antigravity analysis: `filterHcStrict` vs full pipeline (snapshot)

**Dataset:** `audit_dashboard/data/dashboard_data.json` (same two-stage rule as the UI: `filterHcStrict` = `filterHighConvictionOrdered` → `passesValidatedEdgePerClass`). **SPORTS** rows removed to match the dashboard’s global sports strip.

### Result: strict HC matches “crypto only”

| Stage | Count | By class |
|--------|--------|-----------|
| Active (no SPORTS) | 91 | CRYPTO 40, EQUITY 49, FOREX 2 |
| Pass `hc_filter` only (ordered, with correlation dedup) | 4 | CRYPTO 4 |
| Pass `filterHcStrict` (HC + validated-edge) | 4 | CRYPTO 4 |

**Edge step:** There are **no** picks that pass `hc_filter` and then fail only `passesValidatedEdgePerClass` (**0** such rows). Non-crypto are eliminated in **stage 1** (`hc_filter`), not hidden by the explainer / validated-edge panel.

### Why non-crypto never reaches HC (this payload)

Gates aligned with `tools/dashboard_hc_rules.py` / `audit_dashboard/hc_filter.js` and repo `config/hc_gate_params.json`:

- **EQUITY (49):** 43 fail `scoreAbsoluteFloor` (score &lt; 40); 6 fail compound (score &lt; 50 and trust &lt; 8). Example: `WFC` score 45, trust 4, `strat_fwd_trades` 0 — fails before consensus / tier shortcuts matter.
- **FOREX (2):** 1 fails forward WR (&lt; 45%); 1 fails score (&lt; 40).
- **Stamped HF tier path** (`passes_stamped_tier_supplemental_path`): **0** equity, **0** forex — non-crypto contract expects strategy substrings such as `pead_earnings_drift` / `quality_value`; active equity rows in this file do not satisfy that path.

**Conclusion:** For this snapshot, the only strict-HC picks are **crypto** because **scores / forward stats / (stamped) tiers** keep equity and forex out of `hc_filter`, not because the per-class “edge” UI is dropping them afterward.

### Row count drift (2–3 vs 4)

Checked-in JSON vs **live** `dashboard_data.json` can differ; table state (**Show all picks**, trust book, etc.) can change the pool. Class mix remains **crypto-only strict HC** until some non-crypto row clears `hc_filter`.

### Parity note

In the browser, `hc_filter.js` may derive `trust_tier` via `getTrustTier(p)` when the field is empty; the Python parity script used for this table relied on the **`trust_tier` field** on each pick. For this dataset, equity failures are dominated by **score / compound**, so that mismatch does not change the **no non-crypto HC** conclusion.

### If you want more non-crypto in HC

Adjust **upstream** (scoring, forward history on picks) or **`hc_gate_params.json`** — not the validated-edge block alone; **EQUITY** and **FOREX** are already allowed there once `hc_filter` passes.

---

## Goldmine & HC equity — backend fixes (2026-04-14)

**Commit:** `2f79308a52` (branch: `fix/dynamic-runner-conviction-workflows` at time of write).

### Problem

1. **Score depression:** `null_ml_solo_source(1):-20` fired on many `goldmine_stocks` picks because `_apply_score_penalties()` ran while `ml_score` / `ml_composite_score` were still empty; later enrichment filled them but the penalty and score were already frozen.
2. **No forward history for goldmine in the dashboard:** `data/goldmine/closed_trades.json` uses a top-level **`trades`** array. `_extract_picks()` did not look for that key, so the generic loader ingested **zero** closed goldmine rows → `strat_fwd_trades` stayed **0** for strategy rollups. Closed rows also needed aligned **`goldmine_Nx_consensus`** strategy keys and **`final_return_pct`** in the PnL fallback chain.

### Changes

| Area | File | What changed |
|------|------|----------------|
| HC penalties | `audit_trail/quality_gates.py` | Exempt **`goldmine_stocks`** from the null-ML solo/dual penalty (consensus row is the ML signal; penalty was a timing/semantics mismatch for this source). |
| Ingestion | `audit_trail/dashboard_generator.py` | `_extract_picks`: include key **`trades`**. `_normalize_pick`: **`final_return_pct`** in closed-book PnL chain; for `goldmine_stocks` with empty `strategy`, set **`goldmine_{N}x_consensus`** from **`consensus_count`** or **`algo_count`**. |
| Docs | `docs/HC_EQUITY_INVESTIGATION_2026-04-14.md` | Full root-cause write-up, what shipped, what was not changed. |
| API clarity | `audit_trail/dashboard_generator.py` | `collect_all_picks()` docstring: documents actual return **`(active, closed, all_closed_including_expired)`** (removed stale `ingest_meta` mention). |

### Verification

- `pytest tests/test_quality_gates.py tests/test_dashboard_generator.py` — **48 passed**.
- Local `collect_all_picks()`: **51** closed `goldmine_stocks` rows (count depends on repo data + dedup).

### Deploy / data refresh

Regenerate **`audit_dashboard/data/dashboard_data.json`** (dashboard generator / CI) and redeploy audit assets so live **`strat_fwd_*`** reflects the closed ledger. UI-only deploy does not refresh forward rollups baked into JSON.

---

## Peer note — vibe-trading strategies & scanner diversity (`10c6247e5c`)

**Source:** Claude (Antigravity). **Branch:** `fix/dynamic-runner-conviction-workflows`. **Commit:** `10c6247e5c`.

### What shipped

- **`alpha_engine/antigravity_strategies.py`:** Antigravity strategy wrappers expanded **7 → 13**. Six new **`ag_vt_*`** wrappers for vibe-trading session babies: import-safe `try`/`except`, symbol filters, `_signal_to_dict`, metadata (`source_tool`, framing, risk warnings).
- **`incubator/backtest_team/forward_signal_scanner.py`:** **`TIER1_STRATEGIES`** gains six **VT\*** entries with validation stats and operator risk notes.
- **`baby_strategies/vt_pattern_sweep.py`:** Restored from `7ca7f3d8a9` (was missing on the branch).

### Asset-class intent

Previously most registered strategies skewed **crypto**; the six additions aim to cover **US broad ETF**, **mega-cap equity**, **thematic ETF** (e.g. XBI/ARKK/SMH/SOXX/XHB/IBB/XRT/XOP/XME), **metals pair** (GDX/SLV stat arb), and **event-driven short** (restatement). Scanner runs should now **attempt** signals on SPY, QQQ, XBI, ARKK, SMH, SOXX, GDX, SLV, and SEC-event-driven names where before registration gaps yielded **zero** picks.

### Verified on that peer pass

- **`_compute_stats_from_picks()`** end-to-end on a synthetic closed pick: no `NameError` (exit_reason path clean in current tree).
- Cursor/Codebuff follow-ups (e.g. `ml_ranker` `split_idx`, `sys.path` ordering, `_sanitize_for_json`, forward-validator status/`exit_reason`): **no conflict** with this wiring per peer review.

### Deferred (peer queue — not in `10c6247e5c`)

1. **Scanner calibration** — load `.tmp-validation-mcp/scanner_calibration_config.json` (isotonic buckets) from `scanner.py`; still unwired.
2. **Luxalgo alts** — `baby_strategies/vt_csv_edge_luxalgo_alts.py` + small scanner hook.
3. **`closed_picks.json` dedup** — ~1,609 rows flagged by `data_quality_gate.py`; needs explicit approval before mutating state.
4. **~37 orphan baby strategies** on disk but unregistered — defer to avoid ownership collisions.
