# HC Filter Rewrite v2 — validation checklist

**Cursor plan:** `C:\Users\zerou\.cursor\plans\hc_filter_rewrite_v2_945ff086.plan.md`  
**After plan completion:** end-to-end + GHA timing + Playwright HC flow → **`docs/HC_FILTER_POST_PLAN_E2E.md`**.  
**Re-run this doc** whenever a Cursor plan todo (`backtest-first` → `deploy-verify`) changes state.

**Repo note:** Implementation may live in `audit_dashboard/hc_filter.js` + `config/hc_gate_params.json` (not only inline `template.html`). Validate the **shipped** filter and keep `tools/dashboard_hc_rules.py` in parity.

---

## STEP 1 — Backtest before code changes (`backtest-first`)

| # | Check | Pass criteria |
|---|--------|----------------|
| 1.1 | Data source | Closed set is **not** calibrated from `paper_trading/data/` alone; prefer CSV / `dashboard_data.json` closed per `docs/QUANT_AUDIT_v2.md`. |
| 1.2 | Split | Chronological split ~2,400 train / ~1,029 test (or document if using 60/40 from `backtest_hc_filter.py`). |
| 1.3 | Metrics | Report pass rate, WR on passed, WR on rejected, mean PnL — **train and test**. |
| 1.4 | Test-set quality | Test-set WR not wildly below train (overfit check); if test WR plan threshold fails, **do not** proceed to deploy without tuning. |
| 1.5 | Commands | `python tools/backtest_hc_filter.py` and/or `python tools/walk_forward_thresholds.py` (as wired to proposed gates) exit 0; outputs saved or logged. |

---

## STEP 2 — HC filter implementation (`rewrite-hc-js`)

| # | Check | Pass criteria |
|---|--------|----------------|
| 2.1 | Gates present | Compound grade (floor 40, score 40–49 requires trust ≥ 8), trust tier blocklist, fwdN/fwdWR, trust floor, overconfidence, regime, WF FAILING, independent consensus (if enabled), correlation (if in filter vs portfolio-only). |
| 2.2 | No tier auto-pass bug | S/A/B cannot bypass all gates with SANDBOX / 0 fwd trades (spot-check 3 synthetic rows). |
| 2.3 | Correlation | If Gate 9 uses `window._hcPassedSyms`, caller resets and fills map in filter loop order (documented in code). |
| 2.4 | Static JS | `node tools/check_syntax.js audit_dashboard/hc_filter.js` **if** the file has inline script; else validate `template.html` scripts per project rules. |

---

## STEP 3 — Deployed HTML mirror (`mirror-index`)

| # | Check | Pass criteria |
|---|--------|----------------|
| 3.1 | Source of truth | Confirm whether `audit_dashboard/index.html` is **generated** from `template.html` / generator — do not hand-edit the wrong file. |
| 3.2 | Same behavior | `/audit` loads same `hc_filter.js` (or identical logic) as dev template. |

---

## STEP 4 — `conviction_stack_patch.py` (`neutralize-patch`)

| # | Check | Pass criteria |
|---|--------|----------------|
| 4.1 | No n=0 confidence shortcut | No `confidence >= 0.80` (or similar) substituting for missing forward stats. |
| 4.2 | `py_compile` | `python -m py_compile alpha_engine/conviction_stack_patch.py` exits 0. |

---

## STEP 5 — Python mirror (`update-python-mirror`)

| # | Check | Pass criteria |
|---|--------|----------------|
| 5.1 | Single source of behavior | `tools/dashboard_hc_rules.py` matches JS gates and `config/hc_gate_params.json` merges. |
| 5.2 | Unit tests | `pytest tests/test_dashboard_hc_rules.py` (and `tests/test_hc_filter.js` if applicable) pass. |

---

## STEP 6 — Parity + edge baseline (`run-parity-check`)

| # | Check | Pass criteria |
|---|--------|----------------|
| 6.1 | Parity | `python tools/validate_dashboard_parity.py` — **no drift** between JS path and Python (or documented allowed diff list). |
| 6.2 | Edge decay (optional baseline) | `python tools/edge_decay_monitor.py --json-out …` run once pre-deploy; file path recorded in changelog or RECENT if policy requires. |

---

## STEP 7 — Deploy + smoke (`deploy-verify`)

| # | Check | Pass criteria |
|---|--------|----------------|
| 7.1 | Local | `python tools/serve_local.py` + `npx playwright test tests/no_js_errors.spec.ts` (and audit URL if listed) — **0** pageerror / critical console errors. |
| 7.2 | HC count | Active HC-filtered count in expected band (plan: ~5–12); if near 0, use plan **Rollback Strategy** order, not ad-hoc. |
| 7.3 | Remote | After FTP: `npm run verify:remote` or project verify skill — events/audit load. |

---

## Portfolio layer (not in Cursor plan steps — still validate if touching placement)

| # | Check | Pass criteria |
|---|--------|----------------|
| P.1 | `config/portfolio_mandate.json` | Tier names match live TV portfolio names when routing. |
| P.2 | Correlation at placement | `tools/portfolio_correlation_gate.js` used where opens are created (if that integration is in scope). |

---

## LAYER NC — Non-crypto: validate **each** asset class explicitly

Universal gates (STEP 1–2) apply to all rows, but **HC tail heuristics** and **data quality** differ by `asset_class`. Before calling the rewrite “done” for the whole book, run **per-class** checks so equities/FX/etc. are not accidentally tuned only on USDT rows.

**Cross-cutting (do once per release that touches HC)**

| # | Check | Pass criteria |
|---|--------|----------------|
| NC.0 | Tagging | Spot-check 20 random non-USDT symbols: `asset_class` / `asset_class_type` is set correctly — not left empty (empty defaults to **CRYPTO** in `hc_filter.js`). |
| NC.0b | Sample size | For each class below, note **closed n** in the validation log. If `n` is below MERCURY2 guidance (e.g. equity under 30, forex under 20), label metrics **exploratory** — do not tune thresholds as if they were crypto-grade evidence. |
| NC.0c | Independent consensus | If `independentGroupsMin > 0`, confirm `signalGroups` in `hc_gate_params.json` includes patterns that actually appear on **non-crypto** `source_systems` (e.g. fundamentals / equity strategy prefixes). Otherwise consensus is blind for that class. |

**EQUITY** (`EQUITY` / `STOCK` / `STOCKS` / `PENNY_STOCK` / `EQUITIES`)

| # | Check | Pass criteria |
|---|--------|----------------|
| NC.E1 | HC pass rate | On closed equity slice: pass rate, WR, avg `pnl_pct` for `passesHighConvictionPick` vs baseline — recorded in log. |
| NC.E2 | Heuristic branch | Rows that should use equity tail (see `hc_filter.js` `EQUITY` block) behave as intended; no silent fallback to crypto tail due to wrong `asset_class`. |
| NC.E3 | Evidence | Cite or attach `tools/validate_hf_by_asset_class.py` JSON slice for `EQUITY`, or `docs/ASSET_CLASS_EDGE_SCORING_FLAWS_*.md` if thresholds change. |

**FOREX**

| # | Check | Pass criteria |
|---|--------|----------------|
| NC.F1 | HC pass rate | Same as NC.E1 for `FOREX` closed slice. |
| NC.F2 | Heuristic branch | Confirm `FOREX` block (e.g. bollinger / trust / score paths) matches Python mirror. |
| NC.F3 | Small-n warning | If closed n is tiny, document **no production tightening** from FX alone. |

**ETF**

| # | Check | Pass criteria |
|---|--------|----------------|
| NC.T1 | HC pass rate | Same as NC.E1 for `ETF` slice. |
| NC.T2 | Parity | ETF thresholds in JS vs `dashboard_hc_rules.py` identical. |

**COMMODITY**

| # | Check | Pass criteria |
|---|--------|----------------|
| NC.C1 | HC pass rate | Same as NC.E1 for `COMMODITY` slice. |
| NC.C2 | Symbol lists | Commodity symbol substring lists stay aligned JS/Python; no typo-only drift. |

**FUTURES**

| # | Check | Pass criteria |
|---|--------|----------------|
| NC.U1 | HC pass rate | Same as NC.E1 for `FUTURES` slice (often very small n — exploratory). |
| NC.U2 | Stricter bar | Confirm futures branch (high trust / WR / score) is intentional vs other classes. |

**CRYPTO (control)**

| # | Check | Pass criteria |
|---|--------|----------------|
| NC.X1 | Regression | Re-run STEP 1 metrics on `CRYPTO` (or USDT-suffixed) slice after any global gate change — ensure no accidental collapse of pass count or WR. |

---

## Quick command block

One-shot (reads Cursor plan path for status summary + runs stack):

```bash
python tools/run_hc_plan_validation.py
```

Or stepwise:

```bash
python tools/backtest_hc_filter.py
pytest tests/test_dashboard_hc_rules.py -q
python tools/validate_dashboard_parity.py
python -m py_compile alpha_engine/conviction_stack_patch.py
node tests/test_hc_filter.js
```

After HTML/JS changes to audit:

```bash
node tools/check_syntax.js audit_dashboard/template.html
```

Non-crypto / by-asset evidence (in addition to `backtest_hc_filter.py` on full book):

```bash
python tools/validate_hf_by_asset_class.py --json-out audit_trail/data/hf_asset_class_report.json
```

Slice closed rows by `asset_class` in a notebook or one-off script if you need exact `passes_high_conviction_pick` rates per class (validator focuses on tier/PnL by class; HC boolean may be a small add-on script later).

---

## Cursor plan ↔ validation mapping

| Cursor todo id | Primary validation section |
|----------------|----------------------------|
| `backtest-first` | STEP 1 |
| `rewrite-hc-js` | STEP 2 |
| `mirror-index` | STEP 3 |
| `neutralize-patch` | STEP 4 |
| `update-python-mirror` | STEP 5 |
| `run-parity-check` | STEP 6 |
| `deploy-verify` | STEP 7 |
| *(parallel)* | **LAYER NC** — after STEP 1 and any HC logic change (STEP 2/5) |

| Layer NC todo id (tracking) | Asset class / scope |
|----------------------------|---------------------|
| `v2-val-nc-cross` | NC.0 – NC.0c tagging, sample size, signalGroups for non-crypto |
| `v2-val-nc-equity` | NC.E1 – NC.E3 |
| `v2-val-nc-forex` | NC.F1 – NC.F3 |
| `v2-val-nc-etf` | NC.T1 – NC.T2 |
| `v2-val-nc-commodity` | NC.C1 – NC.C2 |
| `v2-val-nc-futures` | NC.U1 – NC.U2 |
| `v2-val-nc-crypto` | NC.X1 regression |
