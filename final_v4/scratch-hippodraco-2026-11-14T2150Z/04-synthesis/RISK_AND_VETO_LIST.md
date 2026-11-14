# Risk and veto list (carry forward to final review)

## Do NOT do (destructive / misleading)
- **Mass DELETE** of ghost/duplicate rows from production DBs without a reviewed backup + dry-run plan (v2/v4/scratch consensus).
- **Fabricate outcomes** (e.g. force TIME_EXIT→LOST with invented PnL, force-close batches to “clean” stats) — destroys truth.
- **Unblock FUTURES/COMMODITY/BOND trading paths** by flipping blocklists while feeds, contract specs, mappings, costs, or commodity proxies are wrong.
- **Invert ML confidence thresholds** as a “fix” without retrain, leakage audit, and OOS validation (data/leakage problems were flagged).
- **Publish WR>100% or mixed-unit PnL** as metrics; fix generators/sync paths and regenerate.
- **Treat `benchmark_ledger_proof.json` (Nov 12)** as current if truth/cost logic changed Nov 14 without regenerating it.
- **Treat any `final_v3` snapshot as authoritative alone** without noting which tree it came from; reconcile conflicts explicitly.

## Do (safe patterns)
- Mark/flag bad rows (quarantine columns / flags) rather than delete, with dedup rules documented.
- Fix math in the **correct** code paths (main + fallbacks) with unit tests (`test_sync_summary_picks_json`, `test_stop_fill`, `test_per_class_cost_gate`, etc.).
- Add warn/CI gates before hard gates when rolling out hygiene (per prior finpredict-v3 suggestions).
- Keep MUTUAL FUNDS labeled **not production-ready** until NAV/EOD + distributions + expenses + walk-forward exist.

## Review questions for every new “edge” claim (COT, new strategies)
1. Is the data source leak-free relative to decision time?
2. Were costs and fills modeled (stop/limit/bar-close assumptions stated)?
3. How many variants tested? What is `nb_trials`? Was FDR/DSR applied?
4. Is there a frozen OOS window? Walk-forward?
5. Can another reviewer reproduce from committed code + pinned data snapshots?
