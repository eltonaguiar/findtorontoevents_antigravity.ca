# PRE-REGISTRATION — H-233: does the vol-target 60/40 advantage survive on a disjoint window?

**Filed:** 2026-11-23, before any number in this test was computed.
**Rule:** M-107. Filed and committed to `reports/hypothesis_registry.json` before touching data.
**Owner:** buffy (freebuff). **Status at filing:** `REGISTERED`.

## Why this exists

C-014 (`MEASURED`, `independent_runs: 0`) says vol-targeting a 60/40 book raised CAGR 7.85% → 9.28%,
Sharpe 0.750 → 0.895 and cut max drawdown −31.42% → −22.37% over 2005-01-03..2026-11-20. That is one
run over one window, and I have now put it forward as the only "stable rung" in the ladder memo
(`reports/asset_class_risk_reward_ladder_2026-11-23.md`). A rung I recommend on a single in-sample run
is exactly the kind of claim this programme has had to withdraw before. So it gets a replication
test with the decision rule fixed in advance.

## Disclosure that constrains what this can prove

**The holdout window is not virgin.** C-014 already used 2005-2026 as a whole, so 2016-2026 has been
*seen* in aggregate. I therefore label any result here `REPLICATION_NOT_VIRGIN_HOLDOUT`, and I claim
only what that supports: that the effect is not an artefact of the early sub-period and does not
depend on one drawdown episode. This cannot substitute for a forward clock, and it must not be
written up as out-of-sample evidence in the usual sense.

What pre-registration *does* buy here, and the only reason it is worth doing: it removes my freedom to
pick the sub-window, the statistic, or the rebalance convention after seeing which choice flatters the
rule. C-020 already showed the drawdown benefit is granularity-dependent (daily −22.37% vs −31.42%;
monthly −33.72% vs −28.45%), so that freedom is real and it is the thing being closed.

## The rule under test (unchanged from C-014, no re-tuning)

- Book: SPY 60% / TLT 40%, long only, no short leg.
- Leverage: scaled to a 10% annualised vol target using **yesterday's** realised 60-day vol only. No
  same-day information. Cap 2.0x, floor 0x.
- Turnover cost: 5 bp per unit of turnover.
- Rebalance: daily (primary), monthly (robustness diagnostic only, **not** an acceptance path).
- No parameters are estimated in this test. Nothing is fitted on either sub-window.

## Split (fixed now)

- Window A — development label: 2005-01-03 .. 2015-12-31.
- Window B — holdout label: 2016-01-01 .. 2026-11-20.
- The split point is the midpoint of the available history, chosen because it is the least
  discretionary choice available, not because of any result.

## Test statistic (one, as the registry rule requires)

**Primary: ΔCE** = certainty equivalent (annualised, risk aversion 1) of vol-target 60/40 minus plain
60/40, computed **within Window B only**, with a paired bootstrap 95% CI (10,000 resamples, daily
returns, block length 20 to respect serial correlation).

## Acceptance criteria (all must hold, no post-hoc rescue)

1. ΔCE point estimate in Window B is **positive**.
2. Paired bootstrap **95% CI lower bound > 0** on ΔCE in Window B.
3. Max drawdown in Window B is **not worse** than plain 60/40.
4. ΔCE sign agrees between Window A and Window B (a sign flip means the effect is period-specific).

## Pre-registered kill rule

If criterion 2 fails in Window B, H-233 is `REFUTED_OOS` and the ladder memo's tier-0 recommendation
is downgraded from "risk control with a return tailwind" to **"risk control only — no demonstrated
return gain"**, and that correction is published to COMS. No cheapening of the bar: no switch to a
lower vol target, no switch to the metric that happens to pass, no rebalancing convention swap, no
widening of the window.

## Secondary diagnostics (reported, never used for the verdict)

- Monthly-rebalanced variant, to expose the granularity dependence rather than hide it.
- Window A numbers side by side with Window B.
- Turnover and average leverage actually used, so the 5 bp assumption can be sanity-checked.
- Δ Sharpe and Δ maxDD with their own bootstraps, labelled descriptive.

## Note on family size

This test adds **one** trial to the multiplicity count and it is a test of an existing claim (C-014),
not a new search for alpha. It is a risk-overlay hypothesis, not a directional signal, so it does not
consume a feature family in the alpha family budget. Recorded here so the count is not quietly
claimed later.
