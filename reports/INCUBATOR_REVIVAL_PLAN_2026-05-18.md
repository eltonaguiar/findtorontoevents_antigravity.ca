# Incubator Revival Plan — 2026-05-18

The path forward for real-money edge is **new signal sources**, and the vehicle
already exists: the strategy incubator (`incubator/`). This is the honest state
of that vehicle and the concrete steps to make it produce graduated, edge-validated
strategies.

## Current state — the incubator is dormant

- **442 strategies catalogued** (`incubator/BABY_STRATEGY_INVENTORY.md`,
  last updated 2026-02-26): 174 OHLCV-ready, 46 parked (need external APIs),
  20 Antigravity, 222 legacy. No shortage of *candidates*.
- **Graduation-gate code exists** — `incubator/testing/forward_test_tracker.py`:
  `StrategyGraduationCriteria` (45d / 50 trades / WR 50% / Sharpe 1.0 / MDD 20% /
  PnL 5% / composite score ≥75) + `EarlyHatchCriteria` (7d fast-track).
- **But the pipeline is not flowing.** The live `incubator/forward_test.db` has
  only `forward_signals` (12 rows) + `forward_summary` (189 rows) — **not** the
  `strategies` / `forward_trades` schema `forward_test_tracker.py` expects.
  Schema mismatch: the tracker and the live DB are not wired together.
- `incubator-pipeline.yml` ("Strategy Graduation", daily 06:00 UTC) failed its
  last runs on the **403 git-push** bug — **fixed in PR #1173** (added
  `permissions: contents: write`); the next cron run should be the first green
  one. Verify after 2026-05-18 06:00 UTC.

## Fixed this PR — the graduation gate now requires walk-forward stability

The old gate is a **single-window snapshot**: a strategy lucky for one 45-day
window graduates, then dies live. That is exactly how the live book filled with
no-edge strategies (`reports/EDGE_VERDICT_2026-05-18.md`: `method_a_score`
eff 1.14 → 0.42 the next window; COT year-unstable; 7/7 candidates killed).

Added to `StrategyGraduationCriteria`: `min_window_consistency` (0.60) +
`n_stability_windows` (4). The forward period is split into 4 chronological
chunks; a strategy must be net-positive in ≥60% of them, not merely
net-positive overall. Backward-compatible — skipped if the caller does not
supply `window_pnls`. 7 tests, all pass.

This implements the user's described system ("strategies must forward-test and
meet parameters to continue") with the **stability parameter** this session
proved is the one that matters.

## Remaining revival steps (ranked)

1. **Wire the schema** — reconcile `forward_test_tracker.py`'s expected
   `strategies` / `forward_trades` tables with the live `forward_test.db`
   (`forward_signals` / `forward_summary`). Until this is done the graduation
   gate runs on no data. P0.
2. **Confirm the cron flows** — after the #1173 fix, verify `incubator-pipeline.yml`
   actually forward-tests strategies and writes results. P0.
3. **Feed `window_pnls` into `evaluate_graduation()`** — compute the 4-chunk
   pnl split from each strategy's forward trades and pass it into `check()` so
   the new stability gate is active, not dormant. P1.
4. **/audit system-readiness filter** — the pick schema already carries
   `trust_tier` (`UNKNOWN < PROBATION < SANDBOX < WATCH < VALIDATING < RELIABLE
   < PROVEN`), `forward_validated`, `forward_test_only`. Add a dashboard filter
   so `/audit` can show only graduated / `RELIABLE`+ strategies — separating
   testing-only emitters from validated ones. P1.
5. **Run graduated strategies through `edge_stability_harness.py`** before any
   real-money sizing — graduation is necessary, the harness is the final gate.

## Bottom line

The incubator has the candidates and the gate code; it lacks a flowing
pipeline and, until this PR, a stability gate. Step 1 (schema wiring) is the
real unlock — once strategies flow through, the hardened gate ensures only
walk-forward-stable ones graduate to live.
