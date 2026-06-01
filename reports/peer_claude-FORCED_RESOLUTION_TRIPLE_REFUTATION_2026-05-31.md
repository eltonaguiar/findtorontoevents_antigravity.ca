# Forced Resolution Triple Refutation — 2026-05-31

## Summary

Three independent verifications caught the same survivorship-bias artifact in the forced-resolution methodology:

## Refutation 1: Claude verbatim+RT verifier swarm
- PRs #318, #347, #343
- FOREX SHORT MC claim PF 3.43 → actual PF 1.087 (capping, not intrabar replay)
- COMMODITY LONG MC claim PF 4.43 → actual PF 0.685 raw, 96% concentration in 3 symbols

## Refutation 2: PR #362 deprecation
- monte_carlo_edge_audit.py deprecated: uses winsorization, not intrabar OHLC replay
- permutation p_max = 1.000 (no strategy beats random)

## Refutation 3: Kilo's own sensitivity analysis + 3-AI peer review
- SL floor drives apparent edge: SL=-0.05% → PF=17.03
- TP cap kills edge: TP=0.10% → PF=0.09
- COMBINED tight TP/SL: ALL configs PF<1
- Bootstrap 95% CI on EV: [-0.169%, +0.590%] — CROSSES ZERO
- CI excludes 0? NO — NOT statistically significant

## Conclusion

The forced_resolution.py methodology with tight TP/SL is FALSIFIED. The edge was an artifact of:
1. Capping/winsorization inflating PF 2-6x
2. Excluding TIME_EXIT trades from WR denominator
3. Thin-sample noise on specific strategies

Correct approach: wide TP/SL + time-based market exit, with n>=500 gate before any sizing.
