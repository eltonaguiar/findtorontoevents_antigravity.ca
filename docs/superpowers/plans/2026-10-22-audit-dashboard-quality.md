# /audit Dashboard Maximum-Quality Plan (2026-10-22)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the verified performance-accuracy fixes to production, make them robust against regression, fix measurable data-quality gaps (asset-class mislabels, the 3,500-row "recent_closed" cap caveat), and verify end-to-end on the live site.

**Background — what is already done & verified (this session):**
- Root-caused the "0% p&l" items: 38 placeholder/sentinel-exit rows (`exit_price<=0`, `pnl_pct=0`, `outcome=null`, mostly `TIME_EXIT`) — a price-fetch failure stamped as a flat close. EQUITY×9 (`stocksunify2`: V, MA, JPM, JNJ, GOOGL, AMZN, LLY, GE, CAT), FOREX×29 (`signal_validation`: GBP-USD, EUR-USD). Independently corroborated by Grok's plan (R7 no-placeholder-exits).
- Fixed in `audit_trail/dashboard_generator.py::_is_valid_resolved_pick()` (reject `exit_price<=0`) and both renderer filter chains in `audit_dashboard/index.html` (`renderNonCryptoPanel()` + `renderCryptoPanel()`).
- Replicated the filter over the prod payload: exactly 38 rows removed; flat counts drop (EQUITY 14→5, FOREX 44→15).
- Integrated proven top-pick status via `renderProvenEdgeStrip()` (per-class verdict table from `money_ready_verdicts`); runtime render verified (10,183 chars, all badges present).
- Python (`py_compile`) and JS (`node --check`) syntax verified on all edited files.
- Documented in `updates/2026-10-22-perf-accuracy-placeholder-exit-fix.md`.

**Deployment reality (verified):** `tools/deploy_audit_files.py` covers only sidecar artifacts. The main page + data are deployed by the hourly `.github/workflows/audit-dashboard.yml` cron (runs `python -m audit_trail.dashboard_generator`, then FTP-deploys `audit_dashboard/index.html` + `audit_dashboard/data/dashboard_data.json` to `/findtorontoevents.ca/audit/`). Therefore the fixes reach production once committed to `main` (next hourly run), or immediately via `workflow_dispatch`.

## Data/API facts (verified 2026-10-22)

- Prod `dashboard_data.json` (fetched to `/tmp/prod_dashboard_data.json`, 25.4MB) `generated_at=2026-10-22T22:14:47Z` (0.68h old). `recent_closed_n=3500`, `active_n=21`.
- Placeholder-exit signature to reject: `exit_price` missing / `<=0` (or unparseable), `pnl_pct=0`, `outcome=null`, `exit_reason` mostly `TIME_EXIT`. 38 rows in prod.
- By-class after current fix would apply: CRYPTO n≈2045 WR≈44.9%, EQUITY n≈703 WR≈46.2%, ETF n≈519 WR≈43.5%, FOREX n≈194 WR≈38.7%, BOND n≈31, COMMODITY n≈7, FUTURES n≈1.
- Mislabel observation: crypto symbols (e.g. BTC-USD-class) appear tagged EQUITY/FOREX in some rows; `nc_asset_category_for_pick()` and `_derive_asset_class()`/`_coerce_asset_class()` are the relevant classification paths.
- `recent_closed` is capped at 3,500 rows; 1,951/3,500 rows are older than 30 days → "recent" UI label is misleading.

## File map

| File | Responsibility |
|------|----------------|
| `audit_trail/dashboard_generator.py` (already modified) | Generator-side placeholder-exit rejection. |
| `audit_dashboard/index.html` (already modified) | Renderer-side placeholder-exit rejection + `renderProvenEdgeStrip()`. |
| `tests/test_dashboard_generator_placeholder_exit.py` (create) | Regression tests for `_is_valid_resolved_pick` placeholder-exit rejection. |
| `tools/audit_mislabel_diagnostic.py` (create) | Reads payload, quantifies asset-class mislabels (crypto in EQUITY/FOREX). |
| `tools/audit_recent_window_report.py` (create) | Computes the >30d share of `recent_closed` per class for the UI caveat. |
| `audit_dashboard/index.html` (edit) | Add "recent_window caveat" note + wire report. |
| `updates/2026-10-22-audit-dashboard-quality.md` (create) | Documents this whole plan's changes + verification. |

---

### Task 1: Commit + deploy the completed fixes

**Files:** `audit_trail/dashboard_generator.py`, `audit_dashboard/index.html`, `updates/2026-10-22-perf-accuracy-placeholder-exit-fix.md`

- [ ] **Step 1: Check git status** — `git status --porcelain` and `git log --oneline -5`. Confirm ONLY my files (generator, index.html, updates doc) are staged. Do NOT push branches containing others' commits (per AGENTS.md safety rules).
- [ ] **Step 2: Verify current state** — re-run `py_compile` on the generator and `node --check` on the extracted main `<script>`; re-run the 38-row replication harness.
- [ ] **Step 3: Create clean branch** — e.g. `fix/audit-placeholder-exit-perf`. Commit only my files.
- [ ] **Step 4: Merge to main** (or ask user to merge). After merge, trigger immediate deploy:
  `gh workflow run audit-dashboard.yml --ref main` (or wait for the hourly cron).
- [ ] **Step 5: Verify live** — fetch `https://findtorontoevents.ca/audit/data/dashboard_data.json`, confirm `generated_at` bumped AND the 38 placeholder-exit rows are gone; fetch `.../audit/index.html`, grep for `renderProvenEdgeStrip` + `exit_price`.
- [ ] **Step 6: Commit verification evidence** to the updates doc.

### Task 2: Regression tests for placeholder-exit rejection (TDD)

**Files:** create `tests/test_dashboard_generator_placeholder_exit.py`

- [ ] **Step 1: Write failing tests** — call `_is_valid_resolved_pick` on fixture picks:
  - `{exit_price:0.0, pnl_pct:0.0}` → False
  - `{exit_price:-1, pnl_pct:0}` → False
  - `{exit_price:null}` → False
  - real row (`{exit_price:123.4, pnl_pct:1.2}`) → passes its other gates / not rejected by this one
- [ ] **Step 2: Run → confirm fail** (if function currently imported) or confirm import path works.
- [ ] **Step 3: Implement/confirm** the generator guard returns False for `exit_price<=0`. (Edit already in place; adjust if import of the module requires too heavy a chain, test the guard as a small pure helper instead.)
- [ ] **Step 4: Run → confirm pass.**
- [ ] **Step 5: Commit.**

### Task 3: Asset-class mislabel diagnostic + fix/caveat

**Files:** create `tools/audit_mislabel_diagnostic.py`; possibly edit `audit_trail/dashboard_generator.py` or `index.html`.

- [ ] **Step 1: Write diagnostic** that reads `dashboard_payload.json`/`dashboard_data.json` and classifies obvious crypto symbols (e.g. `*USDT`, `BTC`, `ETH*`, known crypto prefixes) that carry `asset_class` in {EQUITY, FOREX, ETF}. Print counts per source_system.
- [ ] **Step 2: Run against prod payload; record magnitude.**
- [ ] **Step 3: Decision gate** — if the mislabel count is material (>~1% of that class or concentrated in one source), fix at the source in `_coerce_asset_class()`/`nc_asset_category_for_pick()` and re-run the generator; otherwise write a documented caveat note into the UI. Do NOT silently reclassify without re-running the generator (would desync aggregates).
- [ ] **Step 4: Commit.**
- [ ] **Step 5: Redeploy** (workflow_dispatch) if a real fix landed.

### Task 4: Surface the 3,500-row cap caveat

**Files:** create `tools/audit_recent_window_report.py`; edit `audit_dashboard/index.html`.

- [ ] **Step 1: Report** — per class, compute `n_closed`, `n_older_than_30d`, `pct_older_than_30d` from `recent_closed`.
- [ ] **Step 2: Add UI note** — in the perf `<section>` header area (`#perf-section-header`), render a small disclaimer computed from the payload: "recent_closed is capped at 3,500 rows; X% predate 30 days." Reuse the existing data-loading path.
- [ ] **Step 3: Verify** locally via `serve_local.py` or a headless render; keep JS syntax valid.
- [ ] **Step 4: Commit.**

### Task 5: End-to-end verification + docs

**Files:** `updates/2026-10-22-audit-dashboard-quality.md`

- [ ] **Step 1: Live check** — confirm `generated_at` fresh, 38 placeholder rows absent, `renderProvenEdgeStrip` present in live `index.html`, mislabel caveat rendered (if applied).
- [ ] **Step 2: Write the updates/ doc** describing what was broken, what changed, verification evidence, and remaining caveats.
- [ ] **Step 3: Commit doc.**
- [ ] **Step 4: Final review** — request code review on the branch before/after merge.

---

## Execution handoff

This plan is ready to execute. Recommended mode: **subagent-driven-development** (tasks 3 and 4 are independent — they can be delegated in parallel to subagents while task 1/2 proceed inline). If you prefer, this can be executed inline in the current session instead.
