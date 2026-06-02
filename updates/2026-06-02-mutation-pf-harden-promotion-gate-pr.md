# Mutation PF harden + promotion gate wire-up + stale OPEN batch (2026-06-02)

## What changed

### P0 follow-up (post PR #464)

PR #464 fixed win-count/loss-count masquerading as PF. This PR **hardens** further:

- `compute_pf`: zero gross-loss → `0.0` (removes 999 sentinel inflation)
- Walk-forward ignores folds with PF outside `(0, 99]`
- INVERT `ADOPT`/`CONSIDER` requires ≥3 losing trades on inverted cohort

### Promotion gate (Pillar 3 caller)

- `production_scanner.py` §6f2.8: stamps `_promotion_gate_*` on each pick after EAGLE-6
- **Shadow default** — empty `PROMOTED_STRATEGIES` still emits (metadata only)
- **`PROMOTION_GATE_ENFORCE=1`** — deny-by-default capital lock

### Honest mutation scan

- `tools/run_mutation_scan_honest.py` → `reports/mutation_scan_honest_latest.json`
- 2271 closed rows / 35 strategies: **5** INVERT adopt/consider (not 14 fake PF 999+)

### Stale OPEN hygiene (operational)

```bash
python3 tools/resolve_stale_open_picks.py --execute --max-batches 10 --batch-size 500
```

Resolved **96** stale rows this run; OPEN count ~2489 (down from ~3806 post prior session).

### ETF allowlist — not added

`etf_verified_dual_momentum` remains **off** `PROMOTED_STRATEGIES` — forward `n_closed` still below shadow target (30). Re-check with `tools/etf_forward_stats.py` after pilot closes trades.

## Verify

```bash
python3 -m pytest tests/test_mutation_framework_pf.py -q
DB_PASS_STOCKS=... python3 tools/run_mutation_scan_honest.py
python3 -m py_compile alpha_engine/production_scanner.py verified_strategies/mutation_framework.py
```

## Related

- PR #464 (merged): initial `compute_pf` dollar-PF fix
- PR #457 (merged): resolver `forward_test` health before `conn.close()`
- `INCIDENT_OVERALL#78`: mutation PF P0 → RESOLVED in DB
