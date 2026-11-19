# Repair the audit3 merge regressions (2026-11-19)

**Scope:** `alpha_engine/audit3_tribunal.py`,
`tests/test_audit3_expectancy_gates.py`.

The scheduled `audit3-ledger` build failed at 23:45 and 23:51. Both failures came
from a partially-merged correctness port, not from the running code paths.

## 1. Duplicate `--history` (fixed in the workflow, PR #971)

`audit3-ledger.yml` passed `$history_arg` **and** the same four flags explicitly.
`argparse` raised `conflicting option string: --history`.

## 2. `build_report()` had no `require_alpha`

`main()` passes `require_alpha=True` (G8), but the signature did not accept it:
`TypeError: unexpected keyword argument 'require_alpha'`.

Added the parameter with its intended semantics: when the build requires alpha and
the sidecar supplied none, a `PROVEN_T2` cell is capped at `CANDIDATE`
("selection alpha required for this build but not computed (G8)").

## 3. The persistence gate was duplicated

The N1 repeated-looks block appeared **twice** in `build_report`. The first copy
demoted cells and counted them; the second re-ran the gate and reset
`persistence_counters`, so `n_demoted_this_run` was always 0 and the sidecar's
`last_verdict` could disagree with the published verdict. The first copy was
removed; the surviving block is the one that stamps `raw_verdict` and runs after
the selection-alpha gate.

## 4. `ALPHA_PASSTHROUGH_KEYS` was referenced but undefined

`report["selection_alpha"]` raised `NameError`. Defined as
`("covered", "n_universe", "overall", "generated_at", "schema", "source", "note")`.

## 5. Cost-stress verdict reconciled: cap at CANDIDATE

Two intents collided: "2x cost is required" (E5) and "failing it caps one tier"
(G9). Resolved as: **PROVEN_T2 requires the 2× stress; failing it keeps the cell at
CANDIDATE** (observable, paper-only) instead of erasing it to WEAK. The CANDIDATE
branch no longer re-demotes on stress, and the regression test now asserts
CANDIDATE with the stress reason.

## Verification

```
pytest tests/test_audit3_*.py -q            # 101 passed
python3 -m alpha_engine.audit3_tribunal \
  --picks /tmp/audit3/dashboard_data.json --out /tmp/audit3/ledger.json \
  --history audit_dashboard/data/audit3_verdict_history.json --history-write \
  --persistence-runs 2 --prev-ledger audit_dashboard/data/audit3_ledger.json \
  --max-churn 0.30
# rc=0 · 8,735 scored · selection alpha: not available (G8 caps PROVEN)
```
