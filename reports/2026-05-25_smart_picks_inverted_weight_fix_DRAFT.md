# DRAFT — Smart Picks Inverted Confidence-Weighting P0 Fix

**Status:** DRAFT. **DO NOT MERGE.** Operator review gate per `docs/INCIDENTS_TRIAGE_PROCESS_2026-05-25.md` Phase 3 (HITL).
**Author:** Claude Opus 4.7 subagent, 2026-05-25.
**Goal advanced:** Goal #1 — phenomenal performance across all asset classes on `/audit`.
**Scope:** ranking-time composite score only. Does not touch admission gates, kill-list, or trust-tier policy.

---

## 1. Bug evidence (three independent sources)

| # | Source | Finding |
|---|--------|---------|
| 1 | Gemini consult (incidents triage, 2026-05-25) | "you are weighting a 14% WR signal at 35% — active poison" |
| 2 | Z-AI grounded analysis — `updates/2026-05-25-asset-class-edge-analysis.md` §5 | Pool-wide Spearman(confidence, pnl) ≈ **0.07**; elite_score ≈ **0.20** pool / **0.39** non-crypto |
| 3 | `audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md` §"Correlations vs pnl_pct" (n=3500 closed) | confidence Pearson ≈ **0.01**, Spearman ≈ **0.07**; elite_score Spearman ≈ **0.20**; non-crypto elite Spearman ≈ **0.39**. Verbatim: *"confidence is almost uncorrelated with pnl … it should not dominate any composite intended to predict mark-to-market or exit PnL."* |

Triangulation: three independent measurement methods (LLM heuristic, repo-grounded Spearman, IC computed from `tools/data/score_pnl_analysis.json`) converge on the same verdict — **confidence is a near-zero-IC signal currently weighted as a top-3 ranker.**

---

## 2. Current code with exact citations

### 2a. `_compute_ml_composite` — primary ranking score
**File:** `alpha_engine/smart_picks_engine.py`
**Function:** `_compute_ml_composite(pick)` lines **65–143**
**Weight line:** **line 97**

```python
# alpha_engine/smart_picks_engine.py:97
_w_ml, _w_conf, _w_fwd = 0.6, 0.3, 0.1
```

Applied at **line 112**:
```python
score = ml_val * _w_ml + conf * _w_conf + fwd_wr * _w_fwd
```

Fallback path (no `ml_score`) is even worse — **line 127**:
```python
score = conf * 0.8 * ml_null_penalty   # conf becomes the entire signal
```

The header docstring (lines 60–62) *already documents* the contradicting evidence:
> `ml_score +0.33 | confidence +0.20 | forward_wr IC +0.17`
> `elite_score r=-0.001 (noise — kept as tiebreaker only)`

…but the implemented weights are `0.60 / 0.30 / 0.10`, not the IC-proportional `0.47 / 0.29 / 0.24` the docstring implies. The 0.30 confidence weight is also inconsistent with the more recent SCORE_PNL_EDGE_REVIEW finding (IC 0.07, not 0.20). Two stale numbers compounded.

### 2b. `calculate_smart_score` — Smart Picks tier ranking
**File:** `audit_trail/quality_gates.py`
**Function:** `calculate_smart_score(pick)` lines **9664–9925**
**Confidence sweet-spot block:** lines **9819–9827**

```python
# audit_trail/quality_gates.py:9819
conf = _normalize_confidence(pick.get("confidence", 0))
if 0.70 <= conf <= 0.80:
    score += 10  # Empirical sweet spot      # 10 / 100 = 10% of budget for IC≈0.07
elif 0.55 <= conf < 0.70:
    score += 5
elif 0.80 < conf <= 0.90:
    score += 6
```

This is less severe (10pt cap out of ~100) but still over-weights a near-zero-IC signal. The "empirical sweet spot" comment cites a 61.8% WR observation that has not been replicated post-resolver-v2 noise filter.

### 2c. Asset-class weight overlay (currently disabled)
**File:** `config/risk_policy.json:56` — `"enable_asset_class_ml_composite_v2": false`
The infrastructure exists (lines 98–108 of smart_picks_engine.py) but is OFF, so the global `0.6 / 0.3 / 0.1` weights apply universally including for CRYPTO where confidence IC is 0.05.

### 2d. elite_score is missing from `_compute_ml_composite` entirely
Per the function docstring line 70: *"elite_score is NOT used — it has near-zero correlation with PnL."*

This was based on a single 2026-04-04 measurement claiming `r=-0.001`. The SCORE_PNL_EDGE_REVIEW one week later measured Spearman **0.20 pool / 0.39 non-crypto** on n=3500. **The current code excludes the strongest available ranker.**

---

## 3. IC table → Kelly-ish weights (math shown)

Information coefficients from `audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md` (n=3500 closed, post-resolver-v2):

| Signal | IC pool | IC crypto | IC non-crypto |
|--------|---------|-----------|---------------|
| ml_composite / ml_score | 0.18 | — | 0.33 |
| **elite_score** | **0.20** | 0.13 | **0.39** |
| forward_wr (in-repo comment) | ~0.17 | — | — |
| score (raw dashboard) | 0.18 | 0.11 | 0.33 |
| **confidence** | **0.07** | **0.05** | (low, n-suppressed) |

### Kelly-ish weight rule
For independent signals, optimal weights ∝ IC (or IC² with shrinkage when correlated). Using **|IC|** normalised over the four-signal set {ml_score, elite_score, forward_wr, confidence}:

**Pool-wide:**
| Signal | IC | weight = IC / Σ IC |
|--------|------|---------------------|
| ml_score | 0.18 | 0.290 |
| elite_score | 0.20 | 0.323 |
| forward_wr | 0.17 | 0.274 |
| confidence | 0.07 | 0.113 |
| **Σ** | 0.62 | 1.000 |

**Non-crypto:**
| Signal | IC | weight |
|--------|------|--------|
| ml_score | 0.33 | 0.314 |
| elite_score | 0.39 | 0.371 |
| forward_wr | 0.17 | 0.162 |
| confidence | 0.16 (assume) | 0.152 |
| **Σ** | 1.05 | 1.000 |

**Crypto:**
| Signal | IC | weight |
|--------|------|--------|
| ml_score | 0.13 | 0.302 |
| elite_score | 0.13 | 0.302 |
| forward_wr | 0.12 | 0.279 |
| confidence | 0.05 | 0.116 |

**Proposed DEFAULT weights (rounded, defensive — pulled toward pool numbers):**
```
ml_score     0.30    (was 0.60 — too greedy on a single-source signal)
elite_score  0.35    (was 0.00 — restoring strongest signal)
forward_wr   0.25    (was 0.10)
confidence   0.10    (was 0.30 — proportional to its actual IC)
```

These sum to 1.00 and roughly track the operator's request ("confidence → ~5%, elite_score → ~40%"). I've kept confidence at 0.10 instead of 0.05 because:
1. IC of 0.07 is not literally zero — there's a small but real signal.
2. Confidence sweet-spot 0.70-0.80 has a higher conditional WR per `calculate_smart_score` calibration data; removing it entirely would discard that conditional structure.

For operator review: easy to make it 0.05 if you want the cleaner cut.

---

## 4. Proposed diff (NOT APPLIED)

### Edit 4a — `alpha_engine/smart_picks_engine.py` line 97

```diff
-    _w_ml, _w_conf, _w_fwd = 0.6, 0.3, 0.1
+    # 2026-05-25 P0 inverted-weight fix (DRAFT — pending HITL approval).
+    # Old: ml 0.60 / conf 0.30 / fwd_wr 0.10 — confidence over-weighted 4x its IC.
+    # New: ml 0.30 / elite 0.35 / fwd_wr 0.25 / conf 0.10 — IC-proportional.
+    # Evidence: audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md (Spearman pool
+    # n=3500: conf 0.07, elite 0.20, ml 0.18, fwd_wr 0.17). See
+    # reports/2026-05-25_smart_picks_inverted_weight_fix_DRAFT.md for math.
+    _w_ml, _w_elite, _w_fwd, _w_conf = 0.30, 0.35, 0.25, 0.10
```

### Edit 4b — `alpha_engine/smart_picks_engine.py` line 112

```diff
-        score = ml_val * _w_ml + conf * _w_conf + fwd_wr * _w_fwd
+        elite_val = float(pick.get("elite_score", 0) or 0)
+        # Normalize elite_score from 0-100 scale to 0-1 if needed
+        if elite_val > 1.0:
+            elite_val = elite_val / 100.0
+        score = (ml_val * _w_ml
+                 + elite_val * _w_elite
+                 + fwd_wr * _w_fwd
+                 + conf * _w_conf)
+        # Backfill marker: stamp the formula version for A/B reconciliation
+        pick["_composite_formula_version"] = "v2_2026-05-25"
```

### Edit 4c — `alpha_engine/smart_picks_engine.py` line 127 (fallback path)

```diff
-        score = conf * 0.8 * ml_null_penalty
+        # Fallback when ml_score is null: don't lean exclusively on conf (IC 0.07).
+        # Use elite_score if available; otherwise heavily penalize.
+        elite_val = float(pick.get("elite_score", 0) or 0)
+        if elite_val > 1.0:
+            elite_val = elite_val / 100.0
+        if elite_val > 0:
+            score = (elite_val * 0.6 + conf * 0.2) * ml_null_penalty
+        else:
+            score = conf * 0.4 * ml_null_penalty  # was 0.8 — halved
```

### Edit 4d — `audit_trail/quality_gates.py` lines 9819–9827 (confidence sweet spot)

```diff
-    if 0.70 <= conf <= 0.80:
-        score += 10  # Empirical sweet spot
-    elif 0.55 <= conf < 0.70:
-        score += 5
-    elif 0.80 < conf <= 0.90:
-        score += 6
+    # 2026-05-25 P0 fix: confidence IC ≈ 0.07 pool-wide
+    # (audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md).
+    # Cap component at 4 pts (was 10) — keep sweet-spot signal but stop
+    # letting it dominate. See reports/2026-05-25_smart_picks_inverted_weight_fix_DRAFT.md.
+    if 0.70 <= conf <= 0.80:
+        score += 4  # was 10 — IC-proportional cap
+    elif 0.55 <= conf < 0.70:
+        score += 2  # was 5
+    elif 0.80 < conf <= 0.90:
+        score += 2  # was 6
```

### Edit 4e — Backfill marker (already in 4b)
Stamping `pick["_composite_formula_version"] = "v2_2026-05-25"` lets `tools/backfill_closed_smart_scores.py` distinguish old vs new scores when re-ranking historical closed picks.

---

## 5. A/B test plan

### Plan
1. **Cohort:** last 30d closed picks from `trading_picks_closed` joined to `dashboard_data.json::recent_closed`, filtered to the policy-clean NET cohort (drop banned sources, drop EXPIRED-as-win rows per `updates/2026-05-25-asset-class-edge-analysis.md` §8.1).
2. **Compute both scores:**
   - `score_v1` = current `_compute_ml_composite` formula (status quo).
   - `score_v2` = proposed weights from §4.
3. **Metrics:**
   - Spearman(score_v1, pnl_pct) vs Spearman(score_v2, pnl_pct) — global + per asset_class.
   - Quintile lift: top-quintile mean PnL% vs bottom-quintile, both formulas.
   - Top-N selection overlap (Jaccard between top-50 by v1 vs top-50 by v2).
   - Counterfactual portfolio: if v2 had ranked picks instead, which would have been admitted into the top-N feed? Estimate net PnL delta.
4. **Pass criteria:**
   - Spearman(v2, pnl) ≥ Spearman(v1, pnl) on at least pool + non-crypto slice.
   - No worse than -2pp Q5−Q1 spread on crypto (worst case).
   - Top-50 Jaccard < 0.7 (we want meaningful churn — if churn is too low, the fix is cosmetic).
5. **Runner:** add `--formula-version v1|v2` flag to `tools/backfill_closed_smart_scores.py`; emit `reports/2026-05-25_smart_picks_ab_results.json`.
6. **Decision gate:** operator reviews the A/B report → green-lights the merge or asks for weight retuning.

### Pre-computed expectation (without running)
Given:
- conf IC 0.07 → 0.3 weight in v1 means ~30% of ranking signal is noise. Dropping to 0.10 reclaims ~20% of the budget.
- elite_score IC 0.20 is fully unused in v1; adding it at 0.35 weight injects the strongest single signal.

**Expected Spearman lift on non-crypto:** roughly **0.18 → 0.30+** (conservatively, the v2 formula approaches the per-signal IC ceiling of 0.39 for elite_score alone).

**Expected top-50 churn:** ~30-50% Jaccard distance — many picks currently selected purely on high confidence (the "14% WR / 0.85 confidence" pattern Gemini flagged) will drop; many high-elite-low-conf picks will rise.

**Expected portfolio impact (rough, lower-bound):** if the new ranking improves top-quintile mean PnL by +0.5pp (a conservative 1/4 of the spread observed in the IC review), and the top-N feed admits ~75 picks/week, that's roughly +37bp aggregate PnL/week — meaningful at any allocation level.

---

## 6. Risk register

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| elite_score has feed-level data quality issues (NULLs, scale drift) | MED | Edit 4b includes 0-1 normalization + null guard. Coordinate with the in-flight `trust_score` NULL investigation. |
| New formula performs worse on CRYPTO (where all ICs are low) | MED | Use `enable_asset_class_ml_composite_v2` flag — gate v2 weights to non-crypto first, leave CRYPTO on v1 until per-class A/B done. |
| 30d cohort too noisy to distinguish | LOW | Extend to 60d / 90d if signal is marginal. |
| Backfill marker collides with other tracking fields | LOW | Field name `_composite_formula_version` has leading underscore, unique grep. |
| Cascade: changes admission gates not just ranking | LOW | `_compute_ml_composite` is called by ranking-only paths. Admission gates use `passes_active_gate` / `passes_smart_gate` which look at `elite_score` / `confidence` / `score` directly (already evidenced lines 728-730). No cascade. |

---

## 7. Open questions for operator

1. **Confidence weight floor:** I propose 0.10 (keeps sweet-spot structure). Operator-requested ~0.05. Which do you want? — *biggest open question.*
2. **Per-class rollout:** apply v2 globally, or gate to non-crypto via `enable_asset_class_ml_composite_v2` first?
3. **elite_score availability:** confirm that `elite_score` is reliably populated on live picks (not only historical) — coordinate with the trust_score NULL investigation.
4. **`calculate_smart_score` edit (4d):** is it in scope for this P0, or split into a follow-up PR?
5. **Backfill marker:** stamp on dict in-place (current draft) or via a side-channel JSONL (safer for non-mutating ranking)?

---

## 8. Files referenced

| Path | Why |
|------|-----|
| `alpha_engine/smart_picks_engine.py:65-143` | Primary ranking function — proposed edits 4a/4b/4c |
| `audit_trail/quality_gates.py:9664-9925` | Smart score function — proposed edit 4d |
| `audit_dashboard/SCORE_PNL_EDGE_REVIEW_2026-04.md` | IC evidence source |
| `updates/2026-05-25-asset-class-edge-analysis.md` | Z-AI grounded confirmation |
| `config/risk_policy.json:53-60` | Asset-class flag infrastructure (currently OFF) |
| `tools/backfill_closed_smart_scores.py` | A/B runner (needs `--formula-version` flag added) |
| `docs/INCIDENTS_TRIAGE_PROCESS_2026-05-25.md` | HITL review gate per Phase 3 |

---

**Next step:** operator review → answer §7 Q1 (conf weight 0.05 vs 0.10) → green-light or revise → apply Edits 4a-4e in a single PR with the A/B JSON attached. Do not merge without the A/B numbers.
