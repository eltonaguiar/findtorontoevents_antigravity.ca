# External quant feedback — collected index + Xiaomi MIMO deep audit

**Purpose:** Single markdown index of third-party quant / HF feedback applied to this repo, with the **Xiaomi MIMO / Mimo** (reviewer handoff label) analysis preserved in full. Numbers below are **as stated in each review** for a given snapshot date — recompute on current `audit_dashboard/data/dashboard_data.json` before operational decisions.

---

## 0. Index — where each feedback stream lives

| Source | Doc / artifact | Redis topic (if any) |
|--------|----------------|----------------------|
| **Xiaomi Mimo** — live `dashboard_data.json` deep dive | *This file, §1* | `EXTERNAL_QUANT_FEEDBACK_COLLECTED` |
| Google Antigravity — HF factor / VA / VaR / WF | [GOOGLE_ANTIGRAVITY_HF_FEEDBACK_2026-04-02.md](./GOOGLE_ANTIGRAVITY_HF_FEEDBACK_2026-04-02.md) | `GOOGLE_ANTIGRAVITY_HF_FEEDBACK` |
| Merged execution roadmap (audits + Antigravity) | [HF_MERGED_EXECUTION_PLAN_2026-04-02.md](./HF_MERGED_EXECUTION_PLAN_2026-04-02.md) | `HF_MERGED_EXECUTION_PLAN` |
| Cross-asset fleet / Smart / VA | [AUDIT_HF_MULTICLASS_FLEET_REVIEW_2026-04-07.md](./AUDIT_HF_MULTICLASS_FLEET_REVIEW_2026-04-07.md) | `AUDIT_HF_MULTICLASS_FLEET_REVIEW` |
| TP/SL / prediction quality | [AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md](./AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md) | `AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY` |
| Score–PnL / dashboard truth | [AUDIT_SCORE_IMPROVEMENT_PLAN_REVIEW_2026-04-07.md](./AUDIT_SCORE_IMPROVEMENT_PLAN_REVIEW_2026-04-07.md) | `audit_picks_score_improvement_review` (peer) |
| HF enhancement + edge addendum | `HEDGE_FUND_ENHANCEMENT_PLAN.md`, `EDGE_ADDENDUM.md` | `DEEP_RESEARCH_HF_PICK_QUALITY_GAPS` (historical) |
| Gate tightening memo | `HEDGE_FUND_QUALITY_ROADMAP.md` | (bus optional) |
| Optional Smart Picks HF gates (config) | `config/hf_quality_gates.json`, `alpha_engine/hf_quality_gate.py` | — |

---

## 1. Xiaomi MIMO — deep quant analysis (live `dashboard_data.json`, snapshot cited **2026-04-06**)

*Verbatim structure and claims from reviewer handoff; hypotheses (e.g. data leakage) require dedicated forensic validation.*

### 1.1 Critical — Goldmine / sports contamination

- **`goldmine_stocks`** reported **47 active picks** with one row described as a **college basketball matchup** (symbol like `Cal Poly Mustangs vs UC Irvine Anteaters`), **score 41**, **elite 24**, **`source_system: goldmine_unified`**, **strategy: value_bet**.
- **Interpretation:** unified goldmine feed may mix **sports** with **equities** — pipeline / classification failure.
- **Repo hooks:** `goldmine_unified` → `data/goldmine/unified_picks.json` in `audit_trail/dashboard_generator.py` and `audit_trail/universal_pick_resolver.py`. **Action:** asset-class guard + hard reject non-ticker symbols for equity buckets.

### 1.2 Critical — Score vs PnL on actives (inversion)

- **110 active picks** (reviewer count): **high score (≥70) + negative PnL: 0**; **low score (&lt;50) + positive PnL: 58** (~53% of actives).
- **Examples cited:** `elite_score` 60–81 with **`score` 0 or 5** on crypto (`alpha_engine`, `battleground`); low scores on `goldmine_stocks` names with positive short-horizon PnL.
- **Root cause (reviewer):** display **`score`** tracks **track record / forward metrics**; **`elite_score`** can diverge; short green window vs penalized new strategies (e.g. goldmine with **0 closed** history).
- **Repo context:** Smart ranking uses **`ml_composite`** in `alpha_engine/smart_picks_engine.py`; audit **`score`** vs **`elite_score`** semantics differ by path — see `audit_trail/quality_gates.py` and dashboard merge logic.

### 1.3 Critical — Suspicious consensus / PF combos

- Example combo **`chatgpt_combined_v1` + `proven_tsmom_momentum` + unknown** → **~280 trades**, **~9.3% WR**, **~691.9% total PnL** (reviewer: inconsistent → suspect leakage / lookahead / survivorship).
- **`quan_engine`** cited (**~93.4% WR**, **304 trades**, **PF ~42**).
- **Note:** These require **trade-level reconstruction** (exit reasons, timestamps, partial fills) — not assumed true without audit.

### 1.4 Critical — Weak systems still emitting

| System family (examples) | Reviewer stats | Demand |
|--------------------------|----------------|--------|
| `ml_bg_ensemble`, `ml_bg_system_c` | 0% WR, small n | Kill / block |
| `ml_bg_system_b`, `ml_bg_system_a` | ~5–10% WR | Kill / block |
| `momentum_evolver`, `contrarian_evolver`, `mega_mutation` | 0–14% WR | Kill / block |

- **Collective `ml_bg` loss** cited **~-141%** across A/B/C/ensemble.
- **Repo alignment:** extend **`BANNED_SYSTEMS`** / **`anti_overfit_registry`** / rolling IC firewall (**HF merged plan A2**).

### 1.5 Critical — Regime validation “empty” on actives

- Reviewer JSON shape: **`regime_validation.active_regime_composition`**: **248** total, **`with_regime_data: 0`** → **aligned/misaligned/neutral all 0**, **`signal_reduction_pct: 0`**.
- **Repo truth:** `compute_regime_validation()` in `audit_trail/dashboard_generator.py` counts actives with **`regime_alignment`** set (`active_with_regime = sum(1 for p in active if p.get("regime_alignment"))`). If enrichment never sets this on the active list, metrics stay zero — **routing is effectively off** until `regime_meta_router` / pick pipeline persist alignment on **actives** at build time.
- **Doc reference:** `data_coverage.enrichment_note` in same function describes required fields.

### 1.6 Critical — Performance alerts (decay) without auto-action

- **10/10 HIGH severity:** rolling **7d WR** drop **&gt;20pp** vs baseline for named strategies (keltner SOL, drawdown convexity, mtf ema slope, enhanced_ml xgboost, **ml_crypto_predictor**, etc.).
- **Gap:** detection without **auto-pause / size-down / regime re-check** (reviewer).
- **Repo alignment:** `quality_gates` penalties, Redis/dd alerts, **HF plan** drawdown tiers — wire **closed-loop** response.

### 1.7 Closed picks — decile table (reviewer)

| Score range | n | WR | Avg PnL |
|-------------|---|-----|---------|
| 1–10 | 27 | 48.1% | -1.10% |
| 11–20 | 28 | 50.0% | +0.32% |
| **21–30** | 83 | **15.7%** | **-1.91%** |
| 31–40 | 610 | 35.6% | -0.49% |
| 41–50 | 1,116 | 42.1% | +0.10% |
| 51–60 | 1,219 | **55.3%** | **+0.53%** |
| 61–70 | 313 | 57.8% | +0.63% |
| 71–80 | 50 | 68.0% | +0.80% |
| 81–90 | 4 | 75.0% | +0.54% |

- **21–30 bucket** called catastrophic (goldmine-like band).
- **Concentration:** mid buckets dominate **n**.

### 1.8 Closed mismatches (reviewer)

- **High-score losses:** score **≥70**, PnL **&lt;-1%** → cited **TAOUSDT** / **`rapid_fire`** concentration.
- **Low-score big winners:** e.g. **SPCE**, **AMC**, **CLOV**, **RENDERUSDT** — event/contrarian / low forward-WR track record but large realized wins.

### 1.9 Problem map (reviewer ASCII summary)

- **Data:** sports in equity feed; **TRXUSDT** toxicity; pair/symbol field mismatches.
- **Scoring:** score/elite decoupling; confidence issues; static weights; no WF calibration on live weights.
- **Execution:** no regime routing; no vol targeting; SL adaptation; drawdown halt; dead strategies still active.

### 1.10 Quant reviewer demand list (numbered)

1. Kill **`ml_bg`** family immediately.  
2. Kill **`mega_mutation`**.  
3. Quarantine **`goldmine_unified`** (sports + no track record).  
4. Fix / prove **99% WR-style** consensus stats (forensics).  
5. **Regime tagging must work** on actives (not fiction).  
6. **Auto-pause** on decay alerts.  
7. **Bayesian prior** for new strategies — don’t zero-score purely on n=0 closed.  
8. **TRXUSDT blacklist** — reviewer: 132 trades, 33% WR, -81% PnL.  
9. **Walk-forward recalibrate** live scoring.  
10. **Fix score / elite_score** composition for dashboard truth.

**Repo note (TRX):** `TRXUSDT` appears in **`SYMBOL_BLOCKLIST`** in `alpha_engine/smart_picks_engine.py` (2026-04-07 audit note). **Audit `/audit` merge** may still show TRX from other feeds — verify `quality_gates` + resolver paths.

---

## 2. Crosswalk — Xiaomi MIMO × merged HF plan

| MIMO theme | HF merged IDs / files |
|------------|------------------------|
| Sports in goldmine | P0 hygiene: source filters in `dashboard_generator` / `universal_pick_resolver` |
| Dead systems live | **A2** toxic firewall, `BANNED_SYSTEMS`, registry |
| Regime blind | **B1** regime routing; fix `regime_alignment` on actives in generator pipeline |
| score/elite disconnect | **A3** shrinkage; dashboard truth layer; `calculate_smart_score` / field unification |
| Decay alerts no action | **D2** DD / halt; strategy probation automation |
| WF / static weights | **B2**, **B5** |
| TRX / symbol toxicity | Symbol blocklists + audit cross-feed |

---

## 3. Revision log

| Date (UTC) | Change |
|------------|--------|
| 2026-04-07 | Initial collected doc + Xiaomi Mimo §1; index §0; crosswalk §2. |
