# GHA Hourly Health Monitor — 2026-08-23

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** CI Tests workflow NOT FOUND — workflow does not exist in this repository under the name "CI Tests" (API returned 404; also absent from last 100 main-branch runs). PR #665 (`fix/ci-tests-drift-reconciliation`) may be addressing CI test infrastructure drift.

**Chronic workflows — failures (not cancellations):**
- `robust-edge-miner` — **CHRONIC FAILURE**: 15/15 consecutive failures with 0 successes, spanning runs #99–#127 (2026-08-09 to 2026-08-23, ~14 days). Latest run: [#32640914655](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/32640914655) (2026-08-23T12:58Z). Failure class: test logic / script error (not infra flake — multiple retries per run, each exhausted). Action: `AUTHOR_FIX` required.

**Chronic workflows — cancellations:** none detected in last 100 main-branch runs.

**All other production workflows (last 100 main runs):** healthy — success or in_progress. Notable active workflows: Signal Recorder, Picks-Now Live PnL, Deploy FindCryptoPairs, ML Battleground System F, CRYPTO SMART PICKS, Claude Gainer ML Live Scanner, Winner Pattern Precursor Scanner, Sustained Gainer, TV Paper TP/SL Watchdog, Rapid Fire NOW Scanner, Prediction Quality Tracker, Dashboard Pick Trader, Mega Mutation Live Tracker, Live Trading Monitor, Polymarket Signals, Copy Trader Portfolio, ALPHA ENGINE Gainer Capture, Claude Gainer Short-Term, Continuous Improvement Monitor, Dynamic Universe, MOMENTUM TRACKER, Mercury 2, Skyrocket Detector, ALPHA ENGINE Quant Stack, Sports data snapshots, Conflict Marker Check.

**Open PRs (9 total):** #667, #666, #665, #657, #600, #595, #581, #564, #562 — CI check rollup not fetched (no active "CI Tests" workflow to check against).

**Action required:** Author should investigate and fix `robust-edge-miner` — 14-day unbroken failure streak (runs 99–127), each run retried up to 9 times before final failure. Root cause unknown from log tail (cleanup phase only captured). Check `alpha_engine/` for the script called by `.github/workflows/robust-edge-miner.yml`.
