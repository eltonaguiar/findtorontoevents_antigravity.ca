# Active picks by asset class — diagnosis (2026-04-22)

**Data:** `audit_dashboard/data/dashboard_data.json` (`generated_at` embedded in file; re-run `tools/audit_closed_quadrants.py` after each regen).

**Symptom:** Live `/audit` active book skewed to CRYPTO / FOREX / COMMODITY while **EQUITY, ETF, and BOND** often read **zero** active rows despite `recent_closed` showing positive expectancy in places (especially ETF and EQUITY in short windows).

---

## 1. Executive summary

| Class      | Upstream `active_picks*.json` supply (approx.) | Typical failure mode |
|-----------|-----------------------------------------------|------------------------|
| CRYPTO    | Large                                         | Gating + pool-level bleed vs **recent** window strength |
| FOREX     | Moderate                                      | Trust / forward / pair blocks |
| COMMODITY | Moderate                                      | Score floors, symbol blocks |
| **EQUITY**| **Present** (dozens of rows across scanners) | **Downstream gates** (forward WR floor, elite score, trust, matrix blocks) — not “no emitters” |
| **ETF**   | **Effectively none**                          | **No strategy pipeline writes ETF rows** into upstream JSON |
| **BOND**  | **Effectively none**                          | Same — strategies exist in code but **not scheduled** into active JSON |

---

## 2. Root-cause detail

### 2.1 EQUITY — gate stack, not missing supply

- Emitters such as `multi_asset_copytrader`, `ml_gatekeeper`, `stocks_competition` produce EQUITY-shaped rows in scattered `active_picks*.json` files (see repo-wide scan in companion investigation).
- **`passes_active_gate`** (`audit_trail/quality_gates.py` ~3540+) applies:
  - `elite_grade` D/F block
  - `clone_safety_mode == EXEMPT_FROM_SAFETY_GATES` block (#320)
  - Strategy / matrix / source blocks
  - **Large-sample forward WR floor** (PR #288 family): for `edge_trades >= 20` and `0 < edge_wr < floor` → reject.
- Historically a **single** floor `ACTIVE_NON_CRYPTO_MIN_FORWARD_WR = 0.45` applied to *all* non-crypto classes. Many equity scanners sit **41–44%** forward WR with `n >= 20` — economically debatable but **not** the same as crypto’s super-signals failure mode — yet they were treated identically and **removed from the active book**.

**Fix shipped in this PR:** `active_non_crypto_forward_wr_floor(asset_class)` — **EQUITY 0.40**, **ETF 0.40**, **BOND 0.35**, others remain **0.45**. Unit test `test_active_gate_keeps_equity_marginal_forward_wr_above_class_floor` locks the regression.

### 2.2 ETF / BOND — emitter gap

- `alpha_engine/etf_strategies.py` and `alpha_engine/bond_strategies.py` define strategy **libraries**.
- No cron path consistently merges their output into `alpha_engine/data/active_picks.json` (or sibling pools) the way crypto scanners do.
- **Proof-of-concept (not production ingest):** `tools/etf_emitter_spike.py` → `alpha_engine/data/active_picks_etf_draft.json`, `tools/bond_emitter_spike.py` → `alpha_engine/data/active_picks_bond_draft.json`. Next step is a **thin workflow** + scanner hook after methodology sign-off.

### 2.3 CRYPTO — “last 20 looks great, pool looks awful”

From `tools/audit_closed_quadrants.py` on the 2026-04-22 snapshot:

- **last 10 / 20 / 50 / 100** closed CRYPTO rows (newest first): **~60–68% WR**, positive mean `pnl_pct`, PF **~3–5**.
- **All** CRYPTO in the same window: **~38% WR**, PF **~0.9**, negative mean.

**Interpretation:** Recency + selection (fresh picks differ from the 1,650-row tail dominated by retired toxic strategies). Do **not** treat “last 20 green” as proof the whole book is fixed — treat it as **conditional** edge until Phase 4 risk metrics land.

---

## 3. Score × PnL quadrants (closed book)

Run `tools/audit_closed_quadrants.py` for fresh counts. Snapshot findings:

- **High score, losing PnL:** CRYPTO shows non-trivial false positives (e.g. some drawdown-recovery / MTF names) — scoring and outcome still diverge.
- **Low score, winning PnL:** Large **“missed edge”** bucket on CRYPTO and EQUITY — classic calibration debt (`st_fear_greed_contrarian`, `luxalgo_confluence`, `Classic Momentum`, etc.).

---

## 4. Simple filter edges

On the same snapshot, **`rr_ratio >= 1.5`**:

- **EQUITY / ETF:** WR roughly flat, **PF slightly improves** (gentle quality tilt, not a magic bullet).
- **CRYPTO:** Almost no PF lift — do not use R:R alone as a crypto rescue filter.

RSI / volume_ratio columns are sparse in the payload; the script skips empty slices.

---

## 5. Files touched by the accompanying code fix

| File | Change |
|------|--------|
| `audit_trail/quality_gates.py` | `active_non_crypto_forward_wr_floor()`, per-class floors in forward gate; `SMART_PICKS_MIN_SCORE_EQUITY` **70 → 60** (comments already argued for 60). |
| `tests/test_quality_gates.py` | Adjust block test to WR **0.35**; add **pass** test at **0.419** forward WR. |
| `tools/audit_closed_quadrants.py` | **New** — reproducible quadrant / crypto-window / R:R table. |

---

## 6. Follow-ups (not in this PR)

1. **Wire ETF/BOND spikes** into a guarded alpha-engine job (shadow JSON first, then merge to `active_picks`).
2. **Phase 4** banner metrics (`tools/feed_risk_metrics.py` draft PR) — methodology review before UI quotes numbers.
3. **Reconcile** `MIN_ELITE_SCORE_BY_CLASS` in `alpha_engine/config.py` with smart-pick floors in `quality_gates.py` (single source of truth design doc).
