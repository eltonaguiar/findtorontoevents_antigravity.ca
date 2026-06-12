Fair null: randomize only over what the candidate could have known ex ante.

1. **Randomization subtleties**
- Match **trade count** or its distribution; otherwise one lucky random trade can dominate PF.
- Match **holding-time distribution** only if you want to test entry/direction skill, not horizon selection.
- Match **long/short mix** if the candidate is constrained long-only or has fixed directional exposure.
- Match **per-symbol/per-date/per-time exposure** only if those are operational/risk constraints. If the candidate’s edge is “which symbols/times/holds to select,” conditioning on them washes out the edge.
- Enforce identical universe, tradable bars, costs/slippage, leverage, overlapping-position rules, missing-data treatment, survivorship, and PnL aggregation. No lookahead.

2. **95th percentile of PF**
The 95th percentile of net PF is an empirical one-sided null cutoff for PF. It is not a confidence lower bound. It is acceptable only if PF is the pre-specified decision metric and the null is well calibrated.

But PF is fragile: ratio-based, unstable with few/no losing trades, ignores trade count, and is heavy-tailed. I would prefer a **t-stat / mean-return-over-clustered-SE** or block-bootstrap null under the same exposure constraints. If using PF, require enough trades and possibly require the candidate’s PF lower confidence bound to exceed the monkey 95th percentile. Also, 1,000 monkeys gives noisy top-quantile estimates; use more simulations.

3. **Unfair failure mode**
Over-conditioning on the signal. Example: the real edge is identifying rare high-drift windows for one symbol. If randoms are forced to use the same symbol/date/hold/exposure profile, they inherit that conditional drift; the monkey 95th PF becomes artificially high, and the real opportunity-selection edge fails even though it is genuine.