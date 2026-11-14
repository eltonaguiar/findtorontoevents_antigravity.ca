# Uncommitted / recently modified (last ~24h) — financial prediction related (main checkout)

**Window:** ~2026-11-13T21:50:00Z through scan time 2026-11-14T21:50Z (approx) based on filesystem `mtime`.  
**Source:** recursive scan of `alpha_engine`, `audit_dashboard`, `audit_trail`, `tools`, `ml_gatekeeper`, `ml_crypto_predictor`, `reports`, `tests`, `final_v2`, `final_2026_11_14` in `/home/eaguiar2015/findtorontoevents_antigravity.ca`, plus `git status --short` in that checkout.

## Git status highlights (from main checkout snapshot)
The main checkout had **many modified/untracked files** (see `00-inventory/git-status-main-short.txt`). Financial-prediction-relevant items visible in that snapshot include (non-exhaustive):
- `M ___HELL_HEALTH_OPENCODE.MD` (ops note, not core prediction math)
- `M audit_trail/dashboard_generator.py`
- `M audit_trail/universal_pick_resolver.py`
- `M ml_gatekeeper/gatekeeper.py` (leakage-default / gatekeeper changes contextually relevant)
- `M tools/live_pnl_tracker.py`, `M tools/backfill_missing_exit_prices.py`, `M tools/sync_summary_picks_json.py`
- **Untracked** (examples): `alpha_engine/pilot_verified_edges.py`, `alpha_engine/bootstrap_verified_edges.py`, `audit_dashboard/data/bootstrap_verified_edges.json`, `audit_dashboard/data/pilot_verified_edges_shadow.json`, many `final_2026_11_14/*` and `final_v2/*` bundles, `reports/cot_contrarian_2026-11-14.json`, etc., plus large `audit_dashboard/data/mf_backtest_cache/*.csv` sets marked untracked in the listing captured earlier (note: gitignore may already ignore some; the captured `git ls-files --others` included them in that grep window — verify).

## High-signal modified files (mtime in last ~24h, finance-relevant)
From the mtime scan (top of list, most recent first):
- `tools/stop_fill_replay.py` (2026-11-14 21:38Z) — stop-fill replay simulation (ties to final_v3 `stop_fill_*` evidence)
- `reports/cot_contrarian_2026-11-14.json` (21:33Z) — COT contrarian backtest artifact
- `audit_trail/stop_fill.py`, `tests/test_cot_contrarian_backtest.py`, `tests/test_stop_fill.py` (21:31Z)
- `tests/test_per_class_cost_gate.py`, `tools/per_class_cost_gate.py`, `tools/hc_gates_python.py`, `audit_trail/dashboard_generator.py` (21:30Z)
- `tools/cot_contrarian_backtest.py` (21:30Z)
- `audit_trail/universal_pick_resolver.py` (21:29Z)
- Several `final_v2/*` and `final_2026_11_14/*` files touched in this window (peer review bundles being edited) — documentation, not runtime logic; still relevant to “final review” provenance.

## Older but operationally important (from recent sessions / known state)
- `audit_dashboard/data/money_ready_verdict.json` mtime **2026-11-14 18:23Z** in main repo (per `ls -la`) — matches “nov snapshot referenced in audits”.
- `audit_dashboard/data/benchmark_ledger_proof.json` mtime **2026-11-12 20:19Z** — older than money_ready verdict; **paired benchmark snapshot may be stale** relative to Nov 14 verdict regenerations unless explicitly updated.

## Interpretation (for final review)
1. **Active code churn is happening now** in the exact risk/realism layer called out by final_v3 and prior audits: **stop-fill realism, cost gates, resolver/generator behavior, tests**. That is good directionally but means any “final” doc claiming fixed behavior should cite **current branch/commit** and re-run evidence.
2. **COT contrarian** artifacts/tests added/updated recently (`cot_contrarian_backtest.py`, report JSON) — treat as new research surface; requires the same statistical rigor (OOS, costs, MT correction) before any edge claim.
3. **Untracked `final_*` bundles** proliferate across worktrees/main checkout; for a “very final review” you need a **single canonical index** (this bundle is a step). Otherwise reviewers read conflicting `final_v3` snapshots.

## Files to inspect first (concrete)
- `audit_trail/stop_fill.py`, `audit_trail/universal_pick_resolver.py`, `audit_trail/dashboard_generator.py`
- `tools/stop_fill_replay.py`, `tools/per_class_cost_gate.py`, `tools/hc_gates_python.py`
- `tests/test_stop_fill.py`, `tests/test_per_class_cost_gate.py`, `tests/test_cot_contrarian_backtest.py`
- `reports/cot_contrarian_2026-11-14.json`
- `ml_gatekeeper/gatekeeper.py` (if leakage defaults/feature drops touched)
