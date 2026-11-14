# Gates checklist (copy into PRs / issues)

For any claim “this class/strategy is ready”, require **all** that apply:

## Data integrity
- [ ] Canonical closed ledger documented (path/table + fields). PnL units = percent, clamp enforced at write.
- [ ] No fabricated flat-PnL cohorts in promoted set (or explicitly excluded and documented).
- [ ] OPEN/backlog not counted as “active performance”; zombies handled.
- [ ] Freshness badges/fields present for resolver lanes used in the verdict.

## Economics
- [ ] Fees/spreads/slippage modeled per class (and stress-tested if uncertain).
- [ ] Funding/roll/dividends handled where relevant (perps, futures, bond ETFs).
- [ ] Net expectancy > 0 after costs (document assumptions).

## Statistics
- [ ] `nb_trials` = number of strategies/families tested in the same search window (documented).
- [ ] DSR ≥ 0.95 (or stated threshold) with that `nb_trials`.
- [ ] SPA/Reality Check considered; PBO only if enough strategies/power (or explicitly not run).
- [ ] OOS/walk-forward done (embargo/purge). No in-sample-only promotion.

## Stability
- [ ] Rolling 90d and frozen OOS both pass (Charter §4 spirit).
- [ ] 14d/48h panels agree (no recent collapse).
- [ ] Concentration within limits; no single-source artifact masquerading as edge.

## Governance
- [ ] `money_ready_verdict.json` regenerated from truth and matches narrative.
- [ ] `benchmark_ledger_proof.json` regenerated (direction-aware, class-appropriate benchmarks) when claiming benchmark-beating.
- [ ] Peer “veto” items not applied (mass destructive DB ops, blind unblocks, confidence inversion without retrain).
