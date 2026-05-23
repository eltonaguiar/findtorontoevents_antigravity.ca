# HC filter rewrite v2 — post-plan end-to-end verification

**Cursor plan:** `C:\Users\zerou\.cursor\plans\hc_filter_rewrite_v2_945ff086.plan.md`  
When all YAML todos are **completed**, run this checklist before declaring production-safe (no “coin toss” book).

## 1. Automated stack (repo)

```bash
python tools/run_hc_plan_validation.py
```

Must exit **0** (backtest, parity, pytest, node tests, `py_compile`).

**Coin-toss guard (data):** closed-book filter should beat baseline WR by a wide margin — see `backtest_hc_filter.py` output. Tune `config/hc_gate_params.json` only with `docs/QUANT_AUDIT_v2.md` hygiene (no paper-trading-only calibration).

## 2. Wait for fresh dashboard payload (optional but recommended)

GitHub Actions **Unified Audit Dashboard** (`.github/workflows/audit-dashboard.yml`) runs **hourly at :10 UTC** and regenerates `dashboard_data.json` paths used by `/audit`.

- After a deploy touching `audit_dashboard/` or data pipelines, either:
  - **Pull** latest `main` after the workflow finishes, **or**
  - Manually run `workflow_dispatch` on that workflow and wait for green.

Local Playwright uses whatever `audit_dashboard/data/dashboard_data.json` exists under `serve_local.py`; for **live** parity use step 4.

## 3. Playwright — High Conviction E2E

```bash
python tools/serve_local.py
npx playwright test tests/audit_hc_conviction_e2e.spec.ts --project="Desktop Chrome"
```

This test:

- Loads `/audit/`, clicks **HIGH CONVICTION** (`#btn-conviction-picks-hero`).
- Asserts `window._convictionOnlyFilter === true`.
- Asserts **no `SANDBOX`** trust cell in `#tab-active` (HC v3 blacklist).
- Fails on **pageerror** or critical **console.error** patterns.

## 4. Remote verification (after FTP)

```bash
set VERIFY_REMOTE=1
npm run verify:remote
```

Or point Playwright at production:

```bash
set VERIFY_REMOTE=1
set BASE_URL=https://findtorontoevents.ca
npx playwright test tests/audit_hc_conviction_e2e.spec.ts --project="Desktop Chrome"
```

(Requires `playwright.config.ts` remote mode — adjust env vars to match your `verify:remote` script.)

## 5. Quality bar (“coin toss” prevention)

| Check | Where |
|--------|--------|
| SANDBOX / bad trust not in HC view | Playwright E2E + `trustTierBlacklist` in JSON |
| Forward history + WR floors | `hc_gate_params.json` + backtest |
| JS/Python drift | `validate_dashboard_parity.py` |
| Placement vs filter | Mandate + correlation **not** only in HC — `portfolio_mandate.json`, `tools/portfolio_correlation_gate.js` |
| Non-crypto | `docs/HC_FILTER_REWRITE_V2_VALIDATION.md` LAYER NC |

### 5.1 Empirical CSV export validation (optional)

Re-run whenever you download **`antigravity_*_picks_*.csv`** from the dashboard:

```bash
python tools/analyze_antigravity_picks_export.py ^
  --closed path/to/antigravity_closed_picks_*.csv ^
  --active path/to/antigravity_active_picks_*.csv ^
  --all-picks path/to/antigravity_all_picks_*.csv
```

**What it does**

- **Closed:** win rate and average **PnL%** by **asset class**, **trust tier**, and **grade** (sanity-checks the “coin toss” book vs PROVEN / SANDBOX / PROBATION).
- **Active:** count of rows that would pass **`passes_high_conviction_pick`** in `tools/dashboard_hc_rules.py` (Gate 1–9 + stamped tier path), broken down by asset class and trust tier.

**Findings snapshot — 2026-04-09 export (3,430 closed / 90 active rows analyzed)**

| Lens | Result | Implication for HC plan |
|------|--------|-------------------------|
| **Closed book overall** | ~**47%** WR, ~**+0.11%** avg PnL% | Full book still near coin-toss; filtering is mandatory for “high conviction” UX. |
| **Trust tier (closed)** | **PROVEN** ~**69%** WR, **+0.96%** avg; **SANDBOX** ~**27%** WR, **−1.26%**; **PROBATION** ~**42%** WR | Validates **trustTierBlacklist** and alignment with `conviction_stack.py`. |
| **Grade (closed)** | **A** ~**83%** WR; **C/D** poor | Validates compound **score floors** (kill C/D/F tail). |
| **Asset class (closed)** | **CRYPTO** majority of rows, ~**50%** WR; **EQUITY/FOREX** weaker avg PnL in window | Supports **crypto-first** HC + **non-crypto** bar (`HC_FILTER_REWRITE_V2_VALIDATION.md`). |
| **Active vs HC rules** | **7/90** (~**8%**) pass HC; **0** HC for SANDBOX/PROBATION/WATCH in sample; **6/7** **PROVEN** pass | Matches intended **narrow funnel** (~5–12 picks); blacklist + gates behave as designed. |

**Limitations**

- **Closed** CSV does not include full **consensus → `source_systems`** / **regime** needed to replay Gate 8 exactly; book-level stats are **unfiltered**.
- **Forward WR / trades** must remain **correctly populated** in live payloads (see code-review note: promote from `extra_json` if needed).

## 6. Redis bus (optional)

Notify fleet: `HF_MERGED_PLAN_PEER_APPEND` after validation green; see `docs/REDIS_BUS_SCHEMA.md`. Topic **`HC_FILTER_EXPORT_VALIDATION_FINDINGS`** may carry empirical snapshot summaries after CSV analysis (see `tools/bus_post_hc_filter_export_validation_findings.py`).
