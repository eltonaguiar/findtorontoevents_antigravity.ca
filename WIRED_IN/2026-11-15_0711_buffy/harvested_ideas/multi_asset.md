# MULTI-ASSET

**Scan footprint:** 142 flagged files — the smallest of the researched classes.

**Closed-ledger measurement:** none directly. Multi-asset picks are stored under their
underlying class, so a rotation strategy's performance is scattered across CRYPTO/EQUITY/ETF
rows and cannot be measured as a portfolio from the payload.

**Verdict: INSTRUMENTED — NOT MEASURED.** The class exists in research (bundle portfolios,
Sentinel Fund, cross-asset synthesis reports) but has no measurable closed-pick series.

**What has been tried:** bundle portfolios, `cross_asset_edge_synthesis`,
`cross_aggregation/super_signals`, persona-mix portfolios, tactical rotation
(`reports/TACTICAL_ROTATION_EDGE_2026-07-04.md`), dual-momentum variants.

**The structural problem:** correlation. Every multi-asset result in this repo is a sum of
single-class edges computed separately; without a correlation matrix and a portfolio-level
drawdown path, a multi-asset "edge" is not a measurable object. `reports/2026-05-25_top_edges_full_combinatorial.md`
and `ctf_correlation_regime_cross_check` are the only attempts at that.

**Next experiment (only after single-class results exist):** build one portfolio from the
surviving per-class candidates, measure at portfolio level with correlation-clustered
significance, and compare against a fixed 60/40 and equal-weight benchmark. Until at least one
single-class candidate survives the gate, there is nothing to combine.
