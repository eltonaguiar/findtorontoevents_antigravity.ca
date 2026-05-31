# Phase 5 — Retire suspect-PF strategies from money_ready_verdict

## Targets
- `cta_golden_cross_200` — COMMODITY, PF 44 / WR 96% reported. Phase-4 forensic audit (PR #180) found 24/24 winners are HG=F LONG with `exit_reason = PRICE_RESOLVED*` overshooting TP by up to 286 bps. Resolver artifact, not edge.
- `prediction_market_consensus` — CRYPTO, PF 24.5 / WR 90% reported. Phase-4 audit found 23 DOGEUSDT SHORT rows tagged `SL_HIT_RESOLVED [PRICE_MISMATCH]` with positive PnL, plus one XRPUSDT row literally tagged `SL_HIT (REPAIRED_PNL_CONTRADIC)` worth +80.37%. Resolver corruption.

## Plan
1. Add both names to `audit_trail/quality_gates.py :: BLOCKED_SOURCE_SYSTEMS` (the canonical exclude-list consumed by `alpha_engine/money_ready_verdict.py` Layer-1 policy filter at lines ~258-272).
2. Server-side PR off origin/main via `gh api PUT`. No local working-tree commit (shared tree).
3. Reference Phase-4 forensic report `reports/peer_claude-phase4-suspect-pf-audit_result_2026-05-31.md` in the comment block.

## Why BLOCKED_SOURCE_SYSTEMS and not PERMANENTLY_KILLED_STRATEGIES
- The forensic evidence is about data quality (resolver artifacts), not necessarily proof that the underlying signal is bad. BLOCKED_SOURCE_SYSTEMS removes them from money_ready_verdict and dashboards immediately; PERMANENTLY_KILLED is a stronger statement reserved for proven-loser-on-clean-data strategies.
- Defense-in-depth pattern already used for `cot_positioning`, `quan_engine_scalp`, `futures_momentum`.

## Verification post-merge
- money_ready_verdict regenerator (`alpha_engine/money_ready_verdict.py`) runs on the resolved-picks cron; next run will recompute per-class stats with these excluded.
