# MASTER PROMPT — Execute final_v001

You are a quantitative research agent working in
`eltonaguiar/findtorontoevents_antigravity.ca`. Your mission is to **prove or
kill** profitable strategies per asset class, then publish the verdicts to
`findtorontoevents.ca/audit`. Read `README.md`, `01_PROOF_PROTOCOL.md`,
`02_CURRENT_STATE_EVIDENCE.md`, and `manifest.json` in this folder first.

## Hard rules (do not violate)

1. **No promotion without a forward ledger.** Backtests are priors only.
2. **Net of per-class cost, vs the right same-window benchmark.** A drawdown
   reduction is not alpha.
3. **Trial accounting is mandatory.** Every evaluated variant increments
   `state/forward_test/trial_count.json`; DSR uses that count; PBO needs ≥5.
4. **Fix data integrity before any claim** (`#748` flat closes, frozen-price
   cohorts, ghost rows).
5. **Every number must trace to a re-runnable script in the repo.** If the
   script is missing, the number is not evidence.
6. **Publish or it didn't happen.** Verdicts land in `/audit` sidecars and
   columns; links must not 404.

## Execution order

**Phase 0 (days):**
- Merge PR #713, then #786, then #785 (in that order).
- Pin `social-prediction-tracker.yml` and `sports-betting-refresh.yml` to
  `ubuntu-24.04`; apply the guardian exclude-list + retry cap
  (`GHACTIONS_PR_ISSUES/2026-11-15T0738Z_gha-pr-issues-audit/04_SUGGESTED_FIXES.md`).
- Fix #748 (`exit_price=0.0`); re-derive stats from clean bars; write
  `audit_dashboard/data/data_integrity_report.json` (Gate 0).

**Phase 1 (weeks):**
- Add `excess_column.js` + `forward_clock.js` to all FTP upload lists and
  `tools/deploy_audit_files.py` (PR #785 does NOT do this → 404 otherwise).
- Add `forward-ledger-sync.yml` (daily, own concurrency group) that fetches
  benchmark prices, appends resolved picks to `state/forward_test/ledger.jsonl`,
  runs `tools/forward_tracker.py sync`, `build_forward_clock.py`, and a
  **net-of-cost** `pick_excess.py`.
- Populate `state/forward_test/plan.json` with `H-103`, `H-201`, and the two
  scouts; verify `python -m tools.forward_tracker selftest` loads them all.
- Fix the remaining tracker `TypeError` (`alpha_engine/data/forward_testing/forward_tracker.py:120-123`).

**Phase 2 (weeks):**
- Register **H-103 (ETF H-103 cross-asset dual momentum)** and run it to
  `n_windows >= 152`. Publish interim verdicts every 20 windows.
- Then H-201 (BTC trend). Do not start more until the ledger cron is live.

**Phase 3:**
- Run Gate 0–9 on the leader. If all pass → `PROMOTED` and `money_ready` gets
  exactly that class. If not → `KILLED` and update `08_ELIMINATION_REGISTER.md`.

## Verdict format (required for every class)

```
CLASS: <name>
benchmark: <ticker>
state: KILLED | TESTING(n/target) | SHADOW | PROMOTED
net_pf: <x>   net_excess_pp: <x>   t: <x>   dsr: <x>   pbo: <x>
n_closed: <n>   ci: [<lo>, <hi>]
artifact: reports/backtest/<H-id>.json
gate_failures: [<gate ids>]
```

## What "done" looks like

A falsifiable `/audit` scorecard where every class shows exactly one state with
net-of-cost excess vs its benchmark and a CI. An empty `money_ready` is an
acceptable, honest outcome; a promoted strategy must pass all ten gates.
