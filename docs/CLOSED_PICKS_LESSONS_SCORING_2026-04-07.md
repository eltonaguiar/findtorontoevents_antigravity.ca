# Closed picks — lessons learned & scoring recommendations

**Date:** 2026-04-07 (memo) · **Redis bus:** `CLOSED_PICKS_LESSONS_SCORING` posted **2026-04-06T20:25:35Z**  
**Evidence:** `tools/analyze_audit_scores_vs_pnl.py` on `audit_dashboard/data/dashboard_data.json` → `tools/data/score_pnl_analysis.json`  
**Sample:** `n_recent_closed` = **3500** (CRYPTO **2855**, non-crypto **645**)

---

## 1. What the closed history says

### 1.1 Gates and tiers work — use them for **surface area**

| Cohort | n | Win rate | Mean `pnl_pct` |
|--------|---:|--------:|---------------:|
| **SMART** (quality @ signal time) | 504 | **77.4%** | **+1.43** |
| REJECTED | 1707 | 38.0% | −0.36 |
| ACTIVE | 1289 | 43.7% | −0.09 |
| **PROVEN** trust | 827 | **63.1%** | **+0.51** |
| RELIABLE trust | 1266 | 41.6% | +0.07 |
| BANNED | 542 | 40.6% | −0.40 |

**Lesson:** The **SMART** slice and **PROVEN** trust band are the only large cohorts with clearly positive edge in this window. **Default live / promoted surface should lean SMART + PROVEN** until pool metrics improve; “everything else” dilutes headline quality.

### 1.2 `smart_score` has a **strong top tail** (especially crypto)

**All recent closed — `smart_score` quintiles:**

| Quintile | Mean `pnl_pct` | Win rate |
|----------|---------------:|--------:|
| Q1 (lowest) | −0.35% | 37.1% |
| Q2 | −0.37% | 35.3% |
| Q3 | −0.50% | 38.3% |
| Q4 | +0.01% | 44.3% |
| **Q5 (highest)** | **+1.19%** | **73.7%** |

**Crypto only:** Q5 win rate **74.6%**, Q1 **39.0%**; Spearman(`smart_score`, `pnl_pct`) ≈ **0.23** vs elite ≈ **0.14** on crypto.

**Lesson:** Ranking is **not linear** in the middle (Q2–Q3 still lose). The model pays off in the **top decile/quintile**. Scoring UX and gates should **emphasize “top bucket”** rather than treating 40 vs 55 as equally informative.

### 1.3 `elite_score` vs `smart_score` is **asset-conditioned**

| Slice | Spearman(elite, pnl) | Spearman(smart_score, pnl) |
|-------|---------------------:|---------------------------:|
| Non-crypto closed | **0.35** | 0.19 |
| Crypto closed | 0.14 | **0.23** |

**Lesson:** **Raise elite’s influence on non-crypto** (and/or calibrate elite components that map to equity/forex fundamentals). **Keep smart_score / gate logic primary for crypto** in this dataset.

### 1.4 `confidence` barely moves outcomes

Pool-wide Spearman(`confidence`, `pnl_pct`) ≈ **0.09**; similar order on crypto.

**Lesson:** **Do not treat raw confidence as a primary ranker.** Recalibrate (e.g. reliability/Brier by strategy × asset class), or **shrink** its weight inside `calculate_smart_score` until it predicts realized outcomes.

### 1.5 Non-crypto **mean** outcomes are poor in this window

From raw closed rows (same dashboard JSON):

| Asset class | n | Win rate | Mean `pnl_pct` |
|-------------|---:|--------:|---------------:|
| CRYPTO | 2855 | 47.0% | +0.07% |
| EQUITY | 471 | 35.5% | **−0.78%** |
| FOREX | 147 | 31.3% | −0.28% |
| ETF / COMMODITY / FUTURES | small n | weak | negative means |

**Lesson:** **Equity/forex need harder gates** (smaller universe, strategy allowlist, or higher `smart_score` / PROVEN bar), not just the same thresholds as crypto.

### 1.6 Strategy-level toxicity (n ≥ 5, worst mean `pnl_pct`)

Examples from closed picks (same JSON): **Dividend Aristocrats**, **Value + Quality**, **Earnings Drift**, **Consecutive Beats**, **claude_gainer_1h**, **st_rsi_momentum_confluence** (large n, negative mean).

**Lesson:** Rolling **strategy-level expectancy** should feed **elite / smart penalties** (or hard bans) when n and negative mean are sustained — not only static registry flags.

---

## 2. Recommended scoring & product tweaks

1. **Surface control:** Prefer **SMART + PROVEN** for “default” views and any auto-sizing narrative; label non-SMART as exploratory.
2. **Non-linear smart score:** Consider **mapping** raw smart_score to tiers with steeper reward above ~50th–60th percentile (top quintile alignment), and **extra penalty** in the Q2–Q3 band where losses cluster.
3. **Asset-conditioned weights:** In composite / dashboard emphasis: **non-crypto → weight `elite_score` more**; **crypto → weight `smart_score` / gate output more** (per empirical Spearman split above).
4. **Confidence diet:** **Reduce** confidence contribution to smart_score (or gate on calibrated prob); add a TODO to log **calibration bins** by `source_system` × `asset_class`.
5. **Equity/forex:** Tighter **min smart_score**, **smaller strategy allowlist**, or **regime filter** before showing as “active” quality; align with `HEDGE_FUND_ENHANCEMENT_PLAN` / edge memos for non-crypto.
6. **Rolling strategy penalty:** Wire **recent closed mean `pnl_pct` / win rate** by `strategy` into `quality_gates` or `elite_scorer` as a **dynamic** demotion (with min-n guardrails).
7. **Re-run cadence:** After each dashboard refresh, run `python tools/analyze_audit_scores_vs_pnl.py` and track **Q5 vs Q1 spread** and **SMART vs REJECTED** as KPIs.

---

## 3. Redis bus

After publishing this file, broadcast topic **`CLOSED_PICKS_LESSONS_SCORING`** with `doc_path_repo_relative` = this path (see `tools/bus_post_closed_picks_scoring_review.py`).

---

## Revision

| Date | Notes |
|------|--------|
| 2026-04-07 | Initial memo from `score_pnl_analysis.json` + per-row aggregates |
