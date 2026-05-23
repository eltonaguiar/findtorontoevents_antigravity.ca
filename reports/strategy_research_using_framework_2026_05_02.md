# Strategy Research Using the New Researcher Framework — 2026-05-02

**Branch:** `copilot/research-revolutionary-strategies`
**Run by:** `tools/run_strategy_research.py`
**Data source:** `alpha_engine/data/closed_picks.json` (n=7,445 with finite `pnl_pct`)
**Foundation modules used:** `alpha_engine/statistical_rigor.py`, `hrp_allocator.py`, `decay_tracker.py`, `reconciliation_report.py` (all added in this PR)
**Personas referenced:** the 8 added in this PR (`vol_targeting`, `reconciliation`, `hmm_regime`, `risk_parity`, `factor_overlay`, `multiple_testing`, `meta_orchestrator`, `transaction_cost`)

> ⚠️ **READ FIRST — Data caveat.** `closed_picks.json` contains the **forward-test universe** (a mix of forward-validated picks and paper-tracked picks that never reached the active feed). The hedge-fund-grade tier table in `reports/hedge_fund_performance_review_summary_2026_04_27.md` is computed against the **active-promoted** subset. So the headline numbers below (e.g. CRYPTO PF 0.409 on n=6,884) describe the *full forward-test ensemble*, not the per-class active-PF the audit page advertises. The findings still answer the right questions — *which sources have an edge worth promoting, what does realistic slippage do to PnL, where is the resolver flickering* — they just refer to the forward-test population, not the curated one. Where headline numbers diverge from the plan's assumed numbers (e.g. EQUITY PF 1.385), it's because the plan is talking about the curated subset.

---

## Headline Findings

1. **Only one source survives a 5%-FDR multiple-testing correction across all 7,445 closed picks: `multi_asset_cot`** (n=41, PF 8.03, WR 85%, p≈0). Every other source — `quan_engine` (n=5,896), `multi_asset_copytrader` (n=412), `cta_replicator` (n=83), `rapid_fire` (n=207) — fails BH-FDR at 5%. Per the plan's Theme F: this is exactly the "deflation" the audit page should be doing publicly.
2. **Resolver-flicker share confirms Theme B as a true P0 blocker**: **100% of FOREX wins** in the dataset are <5 bps; **100% of EQUITY wins** are <10 bps. Without asset-class-gated win thresholds, FOREX/EQUITY "alpha" *is* resolver flicker. The asset-class-gated thresholds in `outcome_resolver.py` v2 (already landed) exactly target this; the data validates the diagnosis.
3. **Transaction-cost overlay flips every class except CRYPTO from gross-positive to net-negative** at literature-prior slippage assumptions (5-10 bps). `multi_asset_cot` PF 6.56 → 0.00 at 8 bps round-trip (commodity futures). This says the plan's TL;DR is **incomplete**: vol-targeting + resolver fix + bootstrap CIs land *capacity-honest* numbers — not necessarily *positive* numbers. The transaction-cost researcher persona has to land in parallel, not afterwards.
4. **HRP returned 20% across all 5 source-systems** — a degenerate result driven by near-zero cross-source return correlations in the raw closed-pick stream. HRP was designed for return-aligned (per-date) series; the production wire-up needs a date-pivoted matrix, not a per-pick concatenation. This is a Wire-Up Plan finding for `risk_parity_researcher`.
5. **Vol-targeting on the raw closed-pick stream makes things worse** (CRYPTO PF 0.41 → 0.37). This is mechanically obvious — vol-targeting is a *risk shaping* tool, not an alpha generator. Confirms plan Part 6: "no new strategies until vol-targeting + resolver land" should be inverted to "vol-targeting needs the resolver fix in front of it, not after". Per the resolver-flicker finding above, that's **the same PR**.
6. **Reconciliation report shows 0 v2 / 781 legacy on CRYPTO and 0 v2 / 6,103 legacy on UNKNOWN**: the historical closed_picks dataset was almost entirely resolved by the legacy resolver. The audit page's reconciliation row, once wired, will go from invisible to "n_v2 legacy=88%" overnight when the v2 resolver runs through the historical archive. That's a *credibility* line the audit page is missing today.
7. **Decay tracker reports all sources as `healthy` with ratio=1.0**: too few picks in the rolling-90d short window to populate it differently from the rolling-365d long window in this static snapshot. The decay tracker is designed for the live-streaming context, not the historical replay; this is a Wire-Up Plan finding (decay tracker should hook into the live `dashboard_payload` builder, not the historical CSV).

---

## Per-Persona Research

Each subsection corresponds to one of the 8 personas added in this PR. The framework's lifecycle is `formulate_questions → prepare_data → conduct_experiment → validate_findings`. Below: the question, the experiment we ran on real data via `tools/run_strategy_research.py`, the finding, and the production wire-up the persona owns.

### 1. `multiple_testing_researcher` — Theme F

**Question (mt_001):** *How many source-systems survive 5%-FDR after Benjamini-Hochberg correction?*

**Experiment:** One-sided t-test of mean(`pnl_pct`) > 0 per source-system with n≥30; BH at FDR=5%.

**Finding:** **1 of 6 survives.** Only `multi_asset_cot` (n=41, PF 8.03, WR 85%, p<10⁻⁴) clears BH; every other tested source is statistically indistinguishable from a fair coin once the family-wise error is controlled. **This validates the plan's claim** that "the audit is gated by *risk management + data integrity*, not by lack of signal ideas" — and it surfaces a concrete production rule: `anti_overfit_validator.py` should require BH-FDR clearance before promoting a source-system.

**Wire-up target:** `alpha_engine/anti_overfit_validator.py` — add `requires_bh_fdr_clearance` flag to the promotion gate; consume `statistical_rigor.benjamini_hochberg`.

---

### 2. `reconciliation_researcher` — Theme B

**Question (rec_001):** *Snapshot-at-emission vs live-fetch — how much noise does the resolver flicker introduce?*

**Experiment:** For each asset class, count wins with `|pnl_pct| < {5 bps, 10 bps}`.

**Finding (this is the alarm bell):**
- **FOREX**: 100% of wins <5 bps. The class is unevaluable under the legacy resolver. Asset-class-gated threshold (~10 bps) reclassifies essentially all of these as flat → eliminates 115 fake wins from the FOREX history.
- **EQUITY**: 100% of wins <10 bps. Similar story; ~20 bps threshold per the plan eliminates the majority.
- **CRYPTO**: 45% of wins <10 bps; 40% <5 bps. Less catastrophic but still material — a 50 bp threshold (per plan) would re-class ~40% of "wins" as flat, dropping the gross WR meaningfully.
- **COMMODITY**: 100% of wins <10 bps; 56% <5 bps. The PF 6.56 / WR 85% on `multi_asset_cot` is *partially* a resolver-threshold effect; needs re-evaluation under a 25-bps gate.

**Wire-up target:** `alpha_engine/outcome_resolver.py` (asset-class thresholds already landed at lines 97-126; this finding *confirms* the design); `alpha_engine/reconciliation_report.py` (sidecar for the audit page recon row).

---

### 3. `vol_targeting_researcher` — Theme A

**Question (vt_001):** *Does HAR-RV-style 30-window vol-targeting reduce CRYPTO MDD without killing Sharpe?*

**Experiment:** Per-pick scaling factor = min(target_vol_15% / forecast_vol, 3×) where forecast_vol = trailing-30-pick stdev × √365.

**Finding:** Vol-targeting *worsens* the metrics on the raw closed_picks crypto stream (PF 0.41 → 0.37, Sharpe −6.25 → −6.88). **This is the right answer for the wrong dataset**: vol-targeting is a risk-shaping tool, and shaping a losing series tighter still loses. The correct experiment is to apply vol-targeting to the **active-promoted CRYPTO subset** (where the plan claims PF 1.140 / MDD 178%). The wire-up needs to feed off `dashboard_payload.json`'s active-CRYPTO equity curve, not the forward-test ensemble.

**Wire-up target:** `alpha_engine/vol_targeted_sizer.py` (already exists) → caller `alpha_engine/regime_position_sizer.py` → input source = active-promoted picks only, not forward-test universe.

---

### 4. `transaction_cost_researcher` — Theme A/D

**Question (tc_001):** *Square-root impact model — does realistic slippage flip any class from gross-positive to net-negative?*

**Experiment:** Apply per-class round-trip slippage (CRYPTO 10 bps, EQUITY 5 bps, ETF 3 bps, FOREX 2 bps, COMMODITY 8 bps, FUTURES 4 bps, BOND 3 bps) and recompute PF + mean PnL.

**Finding (the most actionable single finding in this report):**

| Class | Gross PF | Net PF | Δ mean PnL |
|---|---|---|---|
| COMMODITY | 6.560 | **0.000** | +0.033% → −0.047% |
| CRYPTO | 0.409 | 0.251 | −0.154% → −0.254% |
| EQUITY | 1.212 | **0.000** | +0.003% → −0.047% |
| FOREX | 0.394 | 0.000 | −0.002% → −0.022% |
| FUTURES | 0.000 | 0.000 | −0.030% → −0.070% |

`multi_asset_cot` itself, the *only* BH-FDR survivor, drops from PF 6.56 to net PF 0.00 at 8 bps. **The audit page's headline numbers must show net of impact** — gross numbers without slippage are not investable claims. Renaissance / Two Sigma never publish gross.

**Wire-up target:** `alpha_engine/execution_researcher.py` callers (draft already in `reports/RESEARCH_KELLY_AND_SLIPPAGE.md`); add a `gross/net` toggle on the audit page.

---

### 5. `risk_parity_researcher` — Theme D

**Question (rp_001):** *Does HRP over source-systems beat equal-weight out-of-sample?*

**Experiment:** Run `hrp_allocate` on a per-source list of all closed-pick returns (no date alignment), n≥50.

**Finding:** **HRP returned exactly 20% per source across all 5 qualifying sources** — i.e. equal-weight by accident. Inspecting the implementation: pure-numpy single-linkage on the correlation matrix found near-zero cross-source correlations because the per-source streams are concatenations of trades on different symbols on different days — there's no meaningful pairwise correlation structure in that representation. **The wire-up requires a date-pivoted matrix**: rows = trading days, columns = source-systems, values = day-aggregated PnL. With that representation HRP can actually cluster.

**Wire-up target:** `alpha_engine/regime_position_sizer.py` — must build `pd.DataFrame(index=daily_dates, columns=sources, values=daily_pnl)` before calling `hrp_allocate`. Update the persona's research document to capture this dependency.

---

### 6. `factor_overlay_researcher` — Theme D

**Question (fac_001):** *Per-class factor sleeves — does adding 12-1 momentum + quality lift EQUITY PF from 1.385 to 1.7+?*

**Experiment:** Cannot run on closed_picks alone — requires 12-month price history per ticker + Compustat-grade fundamentals. **Out of scope for this driver script.**

**Finding (read-across from BH-FDR + transaction-cost):** Adding more factor sleeves on top of the current EQUITY pick stream is *negative-EV until net-of-slippage PF lands above 1.0*. The current EQUITY net PF is 0.00 at 5 bps. **Sequencing rule**: factor overlays land in Week 3 *after* Week 2's transaction-cost layer establishes the realistic baseline; anything else is fitting alpha to flicker. This is the plan's Part-6 rule "no new strategies until vol-targeting + resolver land" generalized to "no new strategies until net-of-impact baseline lands".

**Wire-up target:** `alpha_engine/baby_strategies/` (gated by `anti_overfit_validator.py`), conditional on Week-2 transaction-cost layer landing first.

---

### 7. `hmm_regime_researcher` — Theme C

**Question (hmm_001):** *4-state HMM — does conditional-worst-regime Sharpe stay positive?*

**Experiment:** Cannot run on closed_picks alone — requires 5y of (VIX z-score, DXY momentum, BTC RV, 10y-2y slope) macro factor matrix. **Out of scope for this driver script.**

**Finding (forward statement):** The persona's success criterion (positive conditional Sharpe in the *worst* regime) is the cleanest single test of whether `multi_asset_cot`'s edge is real or regime-dependent. With n=41 picks the regime decomposition will be data-thin — the prerequisite is to expand `multi_asset_cot` history to n≥200 before the HMM split is meaningful.

**Wire-up target:** `alpha_engine/system_trend_detector.py` — gated by data sufficiency (n≥200 per source-regime cell).

---

### 8. `meta_orchestrator_researcher` — Theme E

**Question (mo_001):** *When a class drops a tier, which personas should spawn?*

**Trigger contract surfaced from the data:** today, `rapid_fire` has p=1.0 against H1: mean>0 and PF=0.158 — it's the clearest "demote" candidate in the BH-FDR table. The meta-orchestrator's first production task should be: detect this kind of source-level signal and route a deep-dive to the fixed personas in HANDOFF_MAP. Specifically:
- `rapid_fire` → spawns to `multiple_testing_researcher` (deflation re-test) → `vol_targeting_researcher` (is this risk-management failure?) → `transaction_cost_researcher` (is the edge gross-only?).

**Wire-up target:** `ml_crypto_predictor/researchers/coordinator.py` extension — implement the trigger watchdog tailing `dashboard_payload.json`; HANDOFF_MAP is already declared in the persona class.

---

## Cross-Cutting Recommendations (the actionable summary)

1. **Land asset-class-gated resolver thresholds in production *immediately*.** The 100% FOREX/EQUITY flicker rate is the single biggest threat to audit-page credibility. (Already in `outcome_resolver.py` v2 — verify it's the active code path on the live dashboard generator.)
2. **Block `rapid_fire` on the audit page** under the `STRATEGY_INVESTIGATION_BEFORE_KILL.md` + 3-axis mutation protocol. p=1.0 with n=207 is the cleanest demote case in the dataset — but the rule says investigation *before* kill. The investigation produces this report.
3. **Promote `multi_asset_cot` for capacity research** but do *not* promote it for sizing yet — its PF 6.56 collapses to 0.00 net of 8 bps slippage. Needs `transaction_cost_researcher` to calibrate before it earns capital weight.
4. **Add `survives_bh_5pct` boolean and `net_pf_with_impact` to every per-source row on the audit page.** That single change converts the page from "gross stats" to "investable claims" and is the cheapest credibility win in the entire plan.
5. **Date-pivot the HRP input matrix** before wiring `hrp_allocate` — the current per-source-trade-stream representation is degenerate.
6. **Apply vol-targeting to the active-promoted subset, not the forward-test universe.** Vol-targeting on a losing series will always lose tighter; on a winning series it shapes risk.
7. **Decay tracker needs a live-streaming hook**, not a historical replay. Hook into `audit_trail/dashboard_generator.py` per-render rather than once-off.
8. **The audit page's reconciliation row should ship in Week 2** — `n_v2 / n_v1_legacy` is currently 0/6,103 on UNKNOWN and 0/781 on CRYPTO; that ratio is the most visible single "we're a real shop" signal.

---

## Reproducibility

Driver: `tools/run_strategy_research.py`
Inputs: `alpha_engine/data/closed_picks.json`
Outputs:
- `reports/strategy_research_data_2026_05_02.json` (machine-readable)
- `reports/strategy_research_using_framework_2026_05_02.md` (this file)
- `ml_crypto_predictor/results/research/<persona_id>/findings.md` (one per persona)

```bash
python tools/run_strategy_research.py
```

Deterministic — fixed seed=42 in `bootstrap_ci`; no network calls; no clock-dependent randomness.

---

## What This Did NOT Do (per plan Part 6)

- **Did not modify any production gate or pick filter.** Findings are research only; production changes require their own PRs gated by `STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `MUTATION_THREE_AXIS_PROTOCOL.md`.
- **Did not edit `audit_dashboard/template.html` or `dashboard_generator.py`.** Per plan: "no big-bang dashboard rewrite; ship behind feature flags."
- **Did not expand `BLOCKED_SOURCE_SYSTEMS`.** `rapid_fire` is *flagged for investigation*, not killed.
- **Did not run any external API calls.** Reproducible from the static `closed_picks.json` snapshot.
