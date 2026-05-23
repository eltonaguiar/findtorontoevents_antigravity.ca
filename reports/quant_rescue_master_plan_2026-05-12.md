# Quant Rescue Master Plan — 2026-05-12

Final synthesis of a 3-round swarm collaboration on
**"how to get to hedge-fund-level performance acting as a quant hired to
save the company."**

- Round 1 — 7 parallel personas (Renaissance / Two Sigma / DE Shaw /
  Citadel / AQR / Bridgewater + Grok-practical)
- Round 2 — synthesis merge (`reports/quant_swarm_merged_round2_2026-05-12.md`)
- Round 3 — 6 personas cross-reviewed the merge, each flagging
  over-weight / under-weight / cross-swarm blind spot
- This doc — incorporates Round 3 corrections into a final action plan

## Cross-swarm blind spots (4-6 of 6 R3 reviewers flag)

| # | Blind spot | Flagged by | Implication |
|---|---|---|---|
| 1 | **CT=F edge is over-stated** in Round 2 merge | Renaissance, Two Sigma, DE Shaw, Bridgewater (4/6) | Multiple-testing DSR + n_eff << raw n + COT is public + no quadrant conditioning. Real conviction lower than headline. |
| 2 | **Real-world frictions ignored** (execution / slippage / capacity / market impact) | Renaissance, DE Shaw, Citadel (3/6) | Backtest PnL ≠ live PnL after fills. Sizing math (`reports/cotton_cot_real_money_sizing_2026-05-12.md`) doesn't model these. |
| 3 | **Effective sample size mirage** (autocorrelation) | Renaissance, Two Sigma (2/6, but identical root cause) | n=100 closed picks ≠ 100 independent observations. Same regime + overlapping holding periods → n_eff likely 20-40. DSR inflated accordingly. |
| 4 | **No A/B / randomized-treatment design** | Two Sigma (1/6) | All current "improvement" claims are pre/post observational. Cannot attribute changes to a specific fix without a control sleeve. |
| 5 | **Factor-beta vs alpha conflation** | AQR (1/6) | "CT=F edge" is Commodity Carry/TSMOM factor exposure (Miffre 2010) — beta, not proprietary alpha. CTA crowding risk applies. |
| 6 | **Principle vs data-fit** | Bridgewater (1/6) | Most current strategies are data-fit (mined patterns); few have principled economic causation. |
| 7 | **Budget for tick-warehouse / CPCV compute / vendor concentration** | DE Shaw (1/6) | Renaissance-style infra is expensive. We haven't budgeted. |
| 8 | **Correlation regime shift + operational liquidity contagion** | Citadel (1/6) | Per-class sleeves look diversified until a regime flip correlates them all. |

## Day-1 priority (synthesized from all 13 inputs across 3 rounds)

**SINGLE NON-NEGOTIABLE:**

> **Drop `strat_fwd_wr` + `forward_wr` from the ml_gatekeeper feature
> set, retrain, and verify the +9.21pp CV lift survives.**

This is the truth-detector. If the lift survives → the ML stack has real
edge. If the lift collapses → we've been measuring our own outcome.
Either result is actionable; the current ambiguity is not.

## Top 5 actions (Week 2-3 priorities, each addresses ≥1 R3 blind spot)

### 1. Gatekeeper feature-leakage purge + retrain (#1, #4 from blind spots)

- Drop `strat_fwd_wr`, `forward_wr`, `age_hours` from feature set
- Retrain on price/regime/macro features only
- **Wire A/B sleeve:** 50% of new emissions go through old gate, 50%
  through new. Compare realized 30d WR/Sharpe. Use this as Two Sigma's
  randomized-treatment design.
- **Effective-n correction:** report `n_eff = n / (1 + 2 * sum(autocorr_k))`
  alongside raw n on every metric the gatekeeper produces.
- Effort: 4-6h code + 30 days observation
- Gate: A/B sleeve shows new-gate WR ≥ old-gate WR with p<0.10 (one-sided)

### 2. Effective-N reporting across `tools/anti_overfit_audit_sidecar.py` + dashboard (#3)

- Compute Newey-West-style autocorrelation correction per strategy
- Expose `n_eff` alongside `n` on /audit anti_overfit + DB Health panels
- Tier thresholds (PF/WR/MDD) reference `n_eff`, not `n`
- Effort: 2-3h
- Gate: every per-class metric on /audit shows n_eff column

### 3. Transaction-cost overlay on CT=F paper-pilot (#2)

- Add per-fill slippage estimate: 0.5 tick × volatility-state multiplier
- Re-run Step 7 risk-of-ruin MC with friction-adjusted pnl distribution
- Compare friction-adjusted Sharpe to current 1.59 (raw)
- Effort: 2h code + 30 min MC re-run
- Gate: friction-adjusted DSR still ≥ 0.85 at n_trials=500. If not, CT=F
  is NOT LIVE_ELIGIBLE regardless of paper-pilot result.

### 4. Wire `commodity_carry_momo.py` as principled factor (NOT alpha) (#5, #6)

- AQR's prescription: activate the Miffre 2010 carry+momentum signal as
  a **factor exposure**, not as a strategy with proprietary alpha
- Cap allocation to this factor at the CTA-crowding-adjusted size (≤25%
  of COMMODITY sleeve)
- Document the exposure as factor-beta in `reports/cot_paper_pilot_status.json`
  (new field `factor_beta_pct`)
- Effort: 3h (wire-up per CLAUDE.md Wire-Up Rule + factor-beta field)
- Gate: realized return decomposed into factor-beta + residual-alpha; only
  residual-alpha counts toward LIVE_ELIGIBLE Sharpe requirement.

### 5. Correlation-regime-shift early-warning (#8)

- Compute rolling 30d cross-asset correlation matrix
- Alert when any pair crosses 0.5 from <0.3 baseline
- Reduce sleeve sizing inversely with mean(|correlation|)
- Effort: 4h (new sidecar) + dashboard card
- Gate: alert fires on the next macro-stress event (out-of-sample test)

## Per-class roadmap (refined by Round 3)

| Class | Round 2 verdict | Round 3 sharpening | Final Day-1 |
|---|---|---|---|
| COMMODITY (CT=F) | Highest conviction; LIVE_ELIGIBLE post-paper | NOT bankable as alpha; factor-beta exposure capped at 25% sleeve; friction-adjusted DSR required | Treat as factor sleeve, not alpha sleeve |
| EQUITY | Top-N rank backtest + ml_gatekeeper lift | DE Shaw: PEAD edge is real, not yet shipped | Ship PEAD on EQUITY top-100 (Week 3) |
| ETF | n=87 sub-floor | AQR: factor home is sector-rotation + risk-parity | Audit which of 4 ETF strategies actually emits |
| BOND | FRED fix shipped; n=18 → 50+ ramp | Bridgewater: deflation-quadrant hedge; needs principle, not just data | Tag each BOND strategy with its target macro-quadrant |
| FOREX | SHORT-only + regime gate plan | AQR: failing because momo was applied where carry has 30yr alpha | Wire carry factor; SHORT-only as secondary |
| CRYPTO | ml_gatekeeper threshold gate (70) shipped | Two Sigma: per-class calibrator stratification needed | Train CRYPTO-only calibrator after leakage purge |
| FUTURES | CT=F + GC=F anchor | Renaissance: still wait for n_eff justification | Defer until CT=F factor-beta calibrated |

## Realistic timeline (corrected)

Round 2 said 2026-06-15 for CT=F LIVE_ELIGIBLE. Round 3 corrections
extend this:

- **CT=F LIVE_ELIGIBLE:** 2026-07-15 (after +30d for friction-adjusted MC
  + A/B sleeve verification)
- **EQUITY (PEAD subset):** 2026-08-15
- **BOND:** 2026-09-15 (post-FRED ramp + n≥100)
- **ETF (curated):** 2026-09-15
- **CRYPTO (curated):** 2026-10-15 (post-ml-retrain + per-class calibrator)
- **FOREX (carry + SHORT):** 2026-11-15
- **FUTURES (CT=F + GC=F mutation):** 2026-12-15

**No real-money sizing until ≥2 classes have 30 consecutive days of
LIVE_ELIGIBLE T2 metrics on friction-adjusted, n_eff-corrected
measurement.**

## Institutional process additions (Round 3 prescription)

Per Grok-practical + Bridgewater + Citadel reviews, add:

- **Pre-registration log** at `reports/strategy_preregistrations.jsonl`
  — every new strategy idea documented BEFORE testing. Closes the
  "data-fit not principle" blind spot.
- **Capacity model** per strategy — estimate $-volume at which slippage
  > 50% of expected edge. Closes the "no friction model" blind spot.
- **Operational liquidity contagion playbook** — if 2+ classes hit
  drawdown >5% in same week, auto-reduce all sleeves to 50% sizing.
- **CTA-crowding monitor** for COT-based COMMODITY/FUTURES strategies.

## Total commits this session (running tally)

~30 commits today on origin/main. Week 1 rescue actions per Grok roadmap
ALL shipped (data pipeline, dragger quarantine, ML staleness hard-fail,
v3b SignalSpec). Week 2-4 plan is this master plan + per-class
roadmaps already in `reports/`.

## NFA

Research surface only. The 10-step Lopez de Prado AFML readiness pipeline
+ blind-spot corrections above remain the canonical real-money bar.
**Do not size real capital until the gatekeeper feature-leakage purge
(Action #1) and effective-N reporting (Action #2) are live, plus 30
consecutive days of friction-adjusted T2 on the candidate sleeve.**

## Refs

- 7 Round 1 reports: `reports/quant_swarm_round1_<persona>_2026-05-12.md`
- Round 2 merge: `reports/quant_swarm_merged_round2_2026-05-12.md`
- 6 Round 3 reviews: `reports/quant_swarm_round3_<persona>_review_2026-05-12.md`
- Companion plans:
  - `reports/rescue_plan_per_asset_class_2026-05-12.md`
  - `reports/expanded_rescue_roadmap_2026-05-12.md`
  - `reports/week1_draft_prs_2026-05-12.md`
  - `reports/v3b_signal_translator_spec_2026-05-12.md`
  - `reports/grok_audit_red_team_synthesis_2026-05-12.md`
  - `reports/expected_impact_plain_english_2026-05-12.md`
- /audit hub: `audit_dashboard/real_money.html`
