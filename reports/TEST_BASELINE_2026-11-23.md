# Test baseline — 2026-11-23

Logged at the operator's direction: *"A repo with 79 pre-existing failures cannot gate anything. Do not fix
them today; do log them as a tracked defect with the count, so the next 'all tests pass' claim has a
baseline to be measured against."*

## Baseline

```
79 failed, 7546 passed, 43 skipped, 3 xfailed, 2 xpassed, 3 warnings, 10 subtests passed in 155.36s
```

Command: `python3 -m pytest tests/ -q -p no:cacheprovider`
Scope: `tests/` only — 691 test files, 7,669 collected. (Repo-wide there are 19,011 `test_*.py` files
including worktrees and vendored copies; those are not part of this baseline.)

## Failures by file

| File | Failed |
|---|---:|
| `tests/test_movies_db_config.py` | 27 |
| `tests/test_movies_rating_refresh.py` | 13 |
| `tests/test_sharpe_lower_bound.py` | 9 |
| `tests/test_etf_iwm_gld_kill.py` | 7 |
| `tests/test_m096_ctf_concentration_cap.py` | 4 |
| `tests/test_anti_overfit_gate_2026_11_20.py` | 4 |
| `tests/test_p1_gates_etf_tight_crypto_consensus.py` | 3 |
| `tests/test_kimi_promotion_unblock.py` | 2 |
| `tests/test_equity_pead_strategy.py` | 2 |
| `tests/test_trust_tier_non_crypto_default_on.py` | 1 |
| `tests/test_pf_registry_tournament_db.py` | 1 |
| `tests/test_ns_c_e_exec_gate_filters.py` | 1 |
| `tests/test_movies_legacy_wrapper.py` | 1 |
| `tests/test_meta_effectiveness.py` | 1 |
| `tests/test_m001_cot_stale_gate.py` | 1 |
| `tests/test_audit2_per_class_panel.py` | 1 |
| `tests/test_asset_class_edge_invariants.py` | 1 |
| **Total** | **79** |

## What this baseline does and does not license

- **It does NOT license "all tests pass".** That claim is now measurable: any future run must be compared
  against 79 failed / 7,546 passed. A claim of "all pass" requires 0 failed with this same command.
- **"None are in my files" is recorded but is not sufficient** (operator's words, accepted). 79 failures
  mean the suite cannot gate anything, regardless of whose files they are.
- The two largest clusters are movies (27 + 13 + 1 = 41 of 79, i.e. **52%**) — likely one shared cause
  (DB config / rating refresh), not 41 independent defects. That is the cheapest place to start if anyone
  chooses to reduce this.
- `tests/test_audit2_per_class_panel.py` (1 failure) is inside the `/audit` surface and may be genuinely
  load-bearing — it is the only failure here that looks like it could be blocking rather than incidental.

## Not fixed

Nothing in this list was fixed. This file records a starting line, not a cleanup.
