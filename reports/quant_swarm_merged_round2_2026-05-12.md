# Quant Swarm Round 2 — Merged Synthesis (2026-05-12)

Synthesis of 6 parallel quant-persona reports from Round 1:
- `reports/quant_swarm_round1_renaissance_2026-05-12.md` (Medallion-style stat-arb)
- `reports/quant_swarm_round1_two_sigma_2026-05-12.md` (ML-heavy systematic)
- `reports/quant_swarm_round1_de_shaw_2026-05-12.md` (event-driven + alt-data)
- `reports/quant_swarm_round1_citadel_2026-05-12.md` (multi-asset systematic)
- `reports/quant_swarm_round1_aqr_2026-05-12.md` (factor investing)
- `reports/quant_swarm_round1_bridgewater_2026-05-12.md` (All Weather macro)

## STRONG CONVERGENCE (4-6 of 6 agree)

### 1. COMMODITY is the highest-conviction edge — start here

**Unanimous (6/6).** Every persona names CT=F + COT positioning as the
single most-bankable signal on the system. PF 1.78-2.08 / DSR 1.0 / n=750
post-resolver-v2. AQR cites Miffre 2010 (SSRN 1127213) 21% alpha
class-wide. Bridgewater positions it as the inflation-leg of All Weather.
DE Shaw treats COT as alt-data the rest of the market still under-uses.

**Action:** ship the 4-week CT=F paper-pilot graduation (already in
flight per `audit_dashboard/paper_pilot.html`). Promote to LIVE_ELIGIBLE
at 1-contract sizing after Step 6 + regime-gate add for fold_1 outlier.

### 2. Gatekeeper feature set is **self-referential / leakage-prone**

**4/6 explicit (Renaissance, Two Sigma, AQR, Bridgewater).** The top-3
gatekeeper features per `ml_gatekeeper/models/training_report.json` are
`strat_fwd_wr` (13.4%) + `forward_wr` (8.7%) + `age_hours` (8.4%). All
three are **downstream proxies of the very outcome the model is supposed
to predict.** This is target leakage; the CV lift +9.21pp is partly
illusory.

**Action:** drop `strat_fwd_wr` + `forward_wr` from the feature set. Retrain
on price/regime/macro-derived features only. Expect CV accuracy to drop
on paper; live performance should improve once the leak is plugged.

### 3. CPCV + PBO + DSR enforcement on EVERY new model — Day 1

**5/6 explicit (Renaissance, Two Sigma, DE Shaw, AQR, Bridgewater).**
Already partially scaffolded: `tools/anti_overfit_audit_sidecar.py`
runs DSR hourly; `alpha_engine/anti_overfit_validator.py` has CPCV/PBO
code but is **orphan per memory `project_next_phase_integrations_2026_04_22.md`**.

**Action:** wire `anti_overfit_validator` into `calculate_smart_score`
or `passes_smart_gate` per CLAUDE.md Wire-Up Rule. Hard-fail any
strategy promotion to LIVE_ELIGIBLE without DSR ≥ 0.95 AND PBO < 0.05
AND WFE > 60%.

### 4. Kill MEMECOIN + PENNY_STOCK + FUTURES routes

**5/6 agree.** Per Kimi audit corpus:
- MEMECOIN: n=1869, WR 15.73%, PF 0.499 → already class-quarantined
- PENNY_STOCK: n=148, WR 6.76%, PF 0.194 → noise
- FUTURES: n=172, WR 17.44%, Sharpe -3.73 → only CT=F is real

**Action:** keep current quarantines; harden the active-pick gate to
hard-reject these classes from emission until the rebuild plans (FUTURES
deep-dive Tier 1 — CT=F + GC=F only) clear.

### 5. ML must be re-anchored — current state is "fit to 69% zero-PnL noise"

**4/6 explicit.** ML accuracy 32.6% / Brier 0.374 is worse-than-random
binary, partially because of the zero-PnL artifact rows (now filtered
via commit `dd8e8282537`) and partially because of the feature-leakage
issue above.

**Action:** retrain ml_gatekeeper + ml_consensus AFTER:
(a) zero-PnL filter is in production aggregates
(b) `strat_fwd_wr` / `forward_wr` removed from feature set
(c) per-class calibrators stratified (per Two Sigma's recommendation —
fixes the −16.67pp CRYPTO inversion that the current single-class
calibrator masks).

## STRATEGIC DIVERGENCE — orthogonal Day-1 priorities (all valid)

Each persona's Day-1 is complementary, not contradictory. A real hedge
fund would parallelize them across 5-6 quants. We have ~1 quant of
bandwidth, so prioritize:

| Persona | Day 1 priority | Effort | Expected lift |
|---|---|---|---|
| **Renaissance** | Halt all capital; tick warehouse; CPCV+PBO+DSR everywhere | Med (1-2 weeks) | Foundational — no edge claim valid until this lands |
| **Two Sigma** | Purged-CPCV + embargo to close 31pp BT-vs-live gap | Med | +5-15pp BT-live convergence |
| **Citadel** | Zero-weight 4 CRYPTO draggers | **Low (already shipped)** | **+6-10pp WR free** |
| **AQR** | Wire `commodity_carry_momo.py` into `calculate_smart_score` | Low | Activates 30-yr-validated factor |
| **DE Shaw** | PEAD on EQUITY top-100 | Med-high | New T2 candidate sleeve |
| **Bridgewater** | Wire HMM states into emission gating | Low-med | Removes anti-regime trades |

### Synthesized prioritization

**Week 1 (already shipped today):**
- ✓ Citadel: dragger quarantine (5-cohort triple block + meta_strategy CRYPTO + crypto_soc + kimi_signal_tracking)
- ✓ Renaissance: data integrity (zero-PnL filter + WON-vs-PnL guard + ML staleness watchdog)
- ✓ Two Sigma: v3b SignalSpec foundation (PR #1 of 4)

**Week 2 (next session):**
- Renaissance/Two Sigma: wire `anti_overfit_validator.py` (CPCV+PBO) into `passes_smart_gate`
- AQR: wire `commodity_carry_momo.py` into `calculate_smart_score`
- Bridgewater: HMM state metadata on emission per strategy

**Week 3-4:**
- Two Sigma: retrain ml_gatekeeper without leakage features + per-class calibrators
- DE Shaw: PEAD on EQUITY top-100 sleeve
- Bridgewater: per-quadrant per-strategy target tagging

**Month 2:**
- Renaissance: market-neutral pair construction (EQUITY cross-sectional, BOND curve, FOREX triangular)
- Two Sigma: stacked LGBM+XGB+CatBoost ensemble with meta-labeling

## Hidden-insight queries — synthesized answers

### Q1. Low-score-but-high-PnL outliers

**Renaissance:** score uses `strat_fwd_wr` which lags the actual signal;
when a strategy has fresh edge that hasn't yet shown up in historical WR,
the score under-weights the trade.

**Two Sigma:** suggests external residual signal not in current 11
features — likely a regime feature missing (VIX, DXY, term-structure).

**AQR:** likely captures a factor exposure the score doesn't measure
(e.g. carry-positive trades in a momentum-dominated scoring layer).

**Synthesized action:** compute the score-vs-realized-PnL **residual**
per pick over a 30-day window. Group by class + strategy + regime.
Top-decile residuals reveal the missing signal. Add the most predictive
residual-correlate as a new feature.

### Q2. High-score-but-low-PnL overfit

**Two Sigma:** classic overfit signature; CPCV would catch this. The
gatekeeper's 12% acceptance rate (61/500 holdout) is suspiciously low —
points to over-selection on noise.

**DE Shaw:** likely high-score is being awarded based on event-momentum
that has already played out by the time the pick emits (latency-poisoned).

**Synthesized action:** rank picks by `(score - realized_pnl_quantile)`.
The top decile is the over-fit cohort. Investigate the common strategy +
timeframe. Tighten the gate for that combination (raise floor).

### Q3. Top strategies dormant (no picks in a while)

**Bridgewater:** emission decay is regime-driven; HMM state currently
disfavors them; that's a feature, not a bug — unless the strategy is
broken.

**Renaissance:** likely candidate dies on `confidence < gate_floor`; the
strategy still computes a signal but the score doesn't clear.

**Synthesized action:** weekly cron that flags any strategy with
`hours_since_last_pick > 7d` AND historical WR > class T2 floor. Either
re-tune the gate or accept that the regime has changed.

### Q4. DNA mutation

**All 6 agree** the three-axis mutation protocol per
`docs/MUTATION_THREE_AXIS_PROTOCOL.md` is the right framework. The
disagreement is mutation rate. Renaissance prefers slow + statistically
significant (n ≥ 100 per mutation). Two Sigma wants high-throughput
genetic search with PBO gate. AQR prefers principled mutations (e.g.
move from momo → carry on FOREX). Bridgewater wants regime-stratified
mutations.

**Synthesized action:** mutate top-3 underperformers per class via
`tools/mutation_analysis.py`. Run each mutation through CPCV gate before
promoting. Cap mutation rate to 2/week to avoid p-value mining.

## THE ONE THING — synthesized

If hired Monday morning and given one bullet-point on the company-wide
priority slide:

> **Stop trusting any number that includes a `strat_fwd_wr` feature.**
>
> Either: (a) drop it from gatekeeper + retrain, OR (b) accept that the
> entire ML stack is rolling its own outcome forward as a feature.
> Currently the system is largely measuring "did this strategy win
> recently" and reporting that as a signal. That's not edge; that's a
> mirror.

Citadel's 6-10pp WR recovery via dragger zero-weighting is the
**immediate cash win**. AQR's commodity_carry wire-up is the
**fastest principled edge activation**. Renaissance/Two Sigma's
CPCV+PBO+DSR enforcement is the **long-term moat** without which every
edge claim is suspect.

## Real-money allocation (post-rescue, conditional)

**Earliest LIVE_ELIGIBLE date by class** (assuming Week 2-4 work clears):

| Class | Earliest LIVE | First capital (1-contract / $5k / 1% pos) |
|---|---|---|
| COMMODITY (CT=F) | 2026-06-15 (after 4w paper) | $1,200 margin → 1 contract |
| EQUITY (top-N) | 2026-07-15 (after 8w T2) | $5,000 sleeve |
| BOND | 2026-08-15 (n≥100 ramp) | $5,000 sleeve |
| ETF | 2026-08-15 | $3,000 sleeve |
| CRYPTO (curated) | 2026-09-15 (after ml retrain + cal fix) | $2,000 sleeve |
| FOREX (SHORT-only) | 2026-10-15 (after 60d test) | $2,000 sleeve |
| FUTURES (CT=F + GC=F only) | 2026-11-15 | $3,000 sleeve |

Total Month-6 capital envelope: ~$25k across all sleeves. No class >25%
of total. No single trade >0.5% of equity.

## NFA

Research surface. The 10-step Lopez de Prado AFML readiness pipeline
remains the canonical real-money bar.

## Refs

- All 6 Round 1 reports (cited at top)
- `reports/rescue_plan_per_asset_class_2026-05-12.md`
- `reports/grok_audit_red_team_synthesis_2026-05-12.md` (Grok's audit + red-team)
- `reports/ml_staleness_audit_2026-05-12.md`
- `reports/v3b_signal_translator_spec_2026-05-12.md`
- `audit_dashboard/real_money.html`

## Round 3 plan

Dispatch each persona to review THIS merged doc. Each flags:
- One thing the merge over-weights from their lens
- One thing the merge under-weights
- One blind spot across all 6

Save to `reports/quant_swarm_round3_<persona>_review_2026-05-12.md`.
Final merge: `reports/quant_rescue_master_plan_2026-05-12.md`.
