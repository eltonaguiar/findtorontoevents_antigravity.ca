# Phase 5 — Retire suspect-PF strategies (RESULT)

## Outcome
- PR #182 opened: `fix(money-ready): retire cta_golden_cross_200 + prediction_market_consensus (Phase-4 resolver artifacts)`.
- Branch: `phase5/retire-suspect-pfs-20260531-0546`.
- Single config change: `audit_trail/quality_gates.py :: BLOCKED_SOURCE_SYSTEMS` += {`cta_golden_cross_200`, `prediction_market_consensus`} with inline comment block citing PR #180 forensic evidence.

## Forensic evidence (from `reports/peer_claude-phase4-suspect-pf-audit_result_2026-05-31.md` / PR #180)
- `cta_golden_cross_200` (COMMODITY): reported PF 44 / WR 96% on n=25. Reality: 24/24 winners are HG=F LONG with `exit_reason = PRICE_RESOLVED*` and `exit_price` overshooting TP by up to 286 bps. The resolver walks daily closes forward N days and stamps the first profitable close as exit, never checking intrabar SL. Resolver artifact.
- `prediction_market_consensus` (CRYPTO): reported PF 24.5 / WR 90% on n=89. PF inflated by (a) 23 DOGEUSDT SHORT rows tagged `SL_HIT_RESOLVED [PRICE_MISMATCH]` with POSITIVE pnl, (b) one XRPUSDT row literally tagged `SL_HIT (REPAIRED_PNL_CONTRADIC)` worth +80.37%. Data corruption.

## Plumbing path verified
- `alpha_engine/money_ready_verdict.py` lines 245-272 read `BLOCKED_SOURCE_SYSTEMS` + `BLOCKED_STRATEGIES` from `audit_trail/quality_gates.py` via Pass-1 global-blocks filter inside `_load_policy_excluded_sources()`. The `_is_policy_excluded(row)` helper short-circuits any row whose source_system OR strategy is in either set, so adding strategy-style names to `BLOCKED_SOURCE_SYSTEMS` is the canonical kill-switch.
- Defense-in-depth match: `cot_positioning`, `quan_engine_scalp`, `futures_momentum` already use the same dual-set pattern (also in `PERMANENTLY_KILLED_STRATEGIES`).

## Why BLOCKED_SOURCE_SYSTEMS rather than PERMANENTLY_KILLED_STRATEGIES
Forensic evidence is about data quality (resolver artifacts), not signal proven-bad-on-clean-data. BLOCKED_SOURCE_SYSTEMS removes them from money_ready_verdict + dashboards immediately. PERMANENTLY_KILLED_STRATEGIES is reserved for proven-loser-on-clean-data and would imply the signal is bad even if the resolver were fixed — that's a stronger claim than the forensic audit supports.

## Verification post-merge
`alpha_engine/money_ready_verdict.py` runs on the resolved-picks cron via `.github/workflows/outcome-resolver.yml`. Next run will:
1. Reload `BLOCKED_SOURCE_SYSTEMS` from the patched module.
2. Apply Pass-1 global-blocks filter excluding both strategies.
3. Recompute per-class CRYPTO + COMMODITY stats with the artifact rows gone.
4. Stamp the updated counts on `audit_dashboard/data/money_ready_verdict.json`.

Expected impact: COMMODITY n drops by ~25 (cta_golden_cross_200 rows); CRYPTO n drops by ~89 (prediction_market_consensus rows). Per-class PFs will move toward the policy-clean baseline reported in CLAUDE.md goal #1 (CRYPTO PF 1.14 / COMMODITY PF 0.31 sub-T2/INSUFF-N).
