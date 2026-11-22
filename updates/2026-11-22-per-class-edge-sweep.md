# Per-class edge sweep across all 10 asset classes

**Why:** the desk needed every class measured on the same contract, after a sweep that silently dropped classes under a minimum row count.

**What:** `tools/per_class_edge_harness.py` (pre-registered mechanisms, block-bootstrap CI, 2× cost stress, split-half, DSR with n_trials=23, PBO via CSCV, benchmark excess) + `tools/build_per_class_report.py` + 7 invariant tests.

**Result:** 34 cells over 2012-01-02 → 2026-11-22; PBO 0.09; DATA_INTEGRITY_FAIL 2, FAILS_2X_COST 2, FAILS_BENCHMARK 6, FAILS_MULTIPLICITY 4, INSUFFICIENT_N 6, PASSES_ALL_BACKTEST_GATES 1, REFUTED_OR_WEAK 13.

**Two defects found and fixed while running it:** portfolio cells reported `n_trades=1` (PF meaningless) until PF was taken from monthly buckets; and `xsmom` replaced explicit zero weights with NaN before `ffill`, so dropped names kept their weight forever, exposure drifted above 1, and the first equity result (30 bps/day) was pure leverage artifact. Now guarded by an exposure assertion plus tests for exposure ≤ 1, closing dropped names, and lookahead independence.

**Verification:** `python3 -m pytest tests/test_per_class_edge_harness.py -q` → 7 passed; full table and verdicts in `reports/2026-11-22-per-class-edge-results.md`.
