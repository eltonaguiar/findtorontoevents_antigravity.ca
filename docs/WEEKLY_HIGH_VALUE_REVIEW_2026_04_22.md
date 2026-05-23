# Weekly High-Value Review — 2026-04-22

## Low-performing asset classes / documented pain

- **FOREX:** `kimi_signal_tracking` + `default` composite block and related docs (`STRATEGY_SUMMARY_BY_ASSET_CLASS_*`) — aggregate bleed heavily driven by a few pairs; blocklist already encodes the fix.
- **EQUITY:** HC snapshot (`docs/TOP_HC_PICKS_2026_04_20.md`) noted **score compression** — few names pass HC gates; Phase 4 risk metrics and net-of-cost PF should guide promotion, not raw headline WR.
- **BONDS / commodities:** Many strategies remain **paper-only** per `strategy_blocklist.py` until Strategy Factory v1.1 evidence exists — do not promote without DSR/PBO sign-off (Phase 4 M1 draft PR).

## Blocklist / rehab / mutations

- **Hard-retired:** `non_crypto_consensus`, `st_fear_greed_contrarian`, `fear_greed_contrarian`, `copy_hl_lb_None`, etc. — documented in `alpha_engine/strategy_blocklist.py` with rationale dates.
- **Paper-only basket:** Large set of bond/forex/futures/ETF names — **tracked** for future promotion when hypotheses + backtests exist; inverse/DNA mutations should go through `docs/MUTATION_THREE_AXIS_PROTOCOL.md` and genome scripts, not ad-hoc unblocks.
- **Rehab path:** Disabled strategies remain in catalog/genome for **mutation** (`battleground_quality_filter.get_evolution_candidates`, DNA mutation tables) — no change required this sweep.

## Machine learning

See `docs/ML_SYSTEMS_HEALTH_CHECK_2026_04_22.md`. Artifacts are fresh (Apr 20–21). Swing models slightly older — verify usage.

## GitHub Actions

See `docs/GHA_WEEKLY_SWEEP_2026_04_22.md`. **CI Tests** failures on main need a single triage pass; Dynamic Runner long failures need timeout/log review.

## Shipped fix this cycle

- **`forward_win_rate` silent-zero:** New `forward_metrics_compat.forward_win_rate_percent()` and call sites in battleground ranking, bundle gate evaluation, Discord bundle formatter, and bundle audit text — aligns readers with nested `forward_metrics` and `strat_fwd_wr`.
