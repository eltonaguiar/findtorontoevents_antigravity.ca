# Two Sigma — Round 3 Review of Merged Synthesis (2026-05-12)

Reviewing `reports/quant_swarm_merged_round2_2026-05-12.md`. Terse, ML-rigorous.

## 1. Over-weighted: COMMODITY/CT=F unanimous-conviction framing

The merge promotes COMMODITY (§"STRONG CONVERGENCE #1", lines 13-24) on PF
1.78 / DSR ~1.0 / n=750 as 6/6 unanimous edge — but a single-asset
(CT=F-dominated) sleeve at n=750 is one regime sample. From an
ML-systematic lens, DSR at that n is fragile to autocorrelated trade
clustering, and the "unanimous" framing crowds out the harder question of
**effective sample size after de-clustering COT-cycle overlap** (likely
n_eff ≈ 150-200, not 750). Down-weight conviction until block-bootstrap'd
DSR clears 0.95.

## 2. Under-weighted: drift monitoring + covariate-shift alarms post-retrain

The merge plans a Week 3-4 ml_gatekeeper retrain (line 102-104) but never
schedules **population-stability-index (PSI), KL-divergence, or ADWIN
drift detectors on the post-leak feature distributions** vs. live. Without
a drift dashboard, the retrained model will silently degrade the same way
the current one did, and we'll find out only via realized PnL — a 30-90
day lag we cannot afford at $25k live.

## 3. Blind spot across all 7 personas: NO A/B TEST DESIGN

The entire swarm jumps from "ship fix" to "measure realized PnL" with
zero **randomized live A/B framework**. Citadel's dragger-zero-weight is
called the "immediate cash win" (+6-10pp WR, line 183-184) but is
**deployed 100% to treatment** — no shadow arm running the old weights on
paper for counterfactual lift, no power analysis on detectable effect
size, no pre-registered hypothesis. Same for the carry-momo wire-up and
the HMM emission gate. Every "expected lift" column in the prioritization
table (lines 81-88) is a point estimate with no confidence interval and
no plan to recover one. Without paired exposure buckets (treatment vs.
control on the same emission stream, randomized at pick_id-hash level),
we cannot distinguish intervention lift from regime tailwind — and every
"+Xpp" claim in this doc becomes a narrative, not a measurement.

---

**Word count:** 248

## NFA. Research surface.
