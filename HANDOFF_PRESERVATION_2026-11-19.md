# Preservation branch — auditcopytrader v2/v3/v4 handoffs (2026-11-19)

This branch preserves work that existed only as uncommitted/untracked files in
three parallel worktrees before they were deleted. **It is NOT intended to merge
to main as-is** — review and cherry-pick what you want.

Sources and what each contributed:

## From `auditcopytrader-v2`
- `reports/subscriptions/2026-11-18-copytrader-llm-audit/` (8 files)
  Copy-trader LLM audit: verified-source identification, backtest logic +
  results, reliability summary, ActionItems. `C_backtest_results.json`
  validated: 200 results / 88 verified / 0 timestamp inversions.

## From `auditcopytrader-v3`
- `copy_trader_intel/regime_feed_adapters.py` — EtherSignals + AA Signals
  regime-feed normalizers with a future-bias guard. Compiles. Per v3 handoff:
  regime overlays only, deliberately NOT registered in SYSTEM_SOURCES (no edge
  in forward test).
- `copy_trader_intel/data/regime_feeds/` — 5 captured snapshots.
- `reports/github_stock_crypto_prediction_sources_2026-11-18.md`
- `reports/github_sources_fanout/`, `reports/github_sources_fanout2/` — LLM
  fanout reports (one empty file removed).
- `toronto-job-kit/` — job-board kit.
- `updates/2026-11-18-regime-feed-adapters.md`

## From `auditcopytrader-v4`
- `copy_trader_intel/source_truth_verifier.py` (52 KB) — probe/backtest/github/
  registry verifier for copytrader sources (free+reachable, trade-level
  timestamps, no lookahead, Wilson LB / PF / split-half / bootstrap). Compiles.
- `copy_trader_intel/data/` — copytrader_github_repos, copytrader_verified_sources,
  source_truth_backtest, source_truth_report, verifier_todos.
- `audit_dashboard/audit_surface_truth_banner.js` (modified)
- `audit_dashboard/data/audit_surface_truth.json` (modified, +235/-39 data)
- `tools/build_audit_surface_truth.py` (modified) — adds monitoring-only
  `verified_copytrader_sources` to the /audit surface (WATCH/DATA_OK; excluded
  from money-ready sizing).
- `updates/2026-11-18-copytrader-source-verification-summary.md`

## Not salvaged (already on main / intentional)
- Kalshi snapshot-age fix (`tools/verify_kalshi_picks.py`) is already on main.
- v3 P0 truth-layer fixes were investigations/plans, not code changes.

## Caveats
- The three `audit_dashboard/*` + `tools/build_audit_surface_truth.py` files are
  v4's *modified* versions; merging them would change /audit surface output.
  Review before use.
- All copied code was verified with `py_compile`; data files are captured
  snapshots, not live.
