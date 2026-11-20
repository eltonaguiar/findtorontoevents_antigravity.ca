# `/audit` showed COMMODITY as **WATCH** next to **PF 0.29**

**Date:** 2026-11-20
**File:** `alpha_engine/money_ready_verdict.py`
**Tests:** `tests/test_money_ready_verdict.py::TestWatchRequiresPublishedPfAtLeastOne`

## What was broken

`money_ready_verdict.json` published COMMODITY with:

| field | value |
|---|---|
| `verdict` | `WATCH` |
| `pf` (headline, policy-clean) | **0.2897** |
| `sizing_pf` (intrabar truth) | 1.0306 |
| `verdict_basis` | `intrabar_truth` |

A profit factor of 0.29 means the book loses money on every dollar risked, yet
the page advertised it as a *near miss*. `/audit3` meanwhile called the same
class `KILL`, so the two surfaces contradicted each other.

Root cause, confirmed by reading the call site:

```python
_policy_n, _policy_wr, _policy_pf = n, wr, pf
_sizing_n, _sizing_wr, _sizing_pf, _sizing_source = _sizing_metrics_from_intrabar(...)
verdict = _verdict(_sizing_n, _sizing_wr, _sizing_pf, ...)   # sizing PF only
```

`_verdict()` already had a `if pf < 1.0: return "NOT_READY"` guard, but `pf` there
is the **intrabar sizing** PF. The published headline PF was never passed in, so
the guard could not fire even though the page printed a sub-1.0 number. This is a
*labelling* defect, not a measurement one: both numbers are correct, they just
described different cohorts and only one of them reached the reader.

## What changed

1. `_verdict()` takes `published_pf: float | None = None` (default keeps every
   existing caller and test behaving exactly as before).
2. The three `WATCH` exits (single-symbol concentration cap, single-source
   concentration cap, near-miss `wr_ok or pf_ok` branch) now return through a
   `_watch_label()` helper, which downgrades to `NOT_READY` when
   `published_pf < 1.0`.
3. The call site passes `published_pf=pf`, i.e. the policy-clean PF that is
   written to `money_ready_verdict.json`.

Boundary is deliberate: `published_pf == 1.0` is break-even and stays `WATCH`;
only a strictly sub-1.0 headline PF loses money gross. `MONEY_READY` is
unreachable with a sub-1.0 published PF anyway (it requires `pf >= 1.5`), so the
clamp cannot manufacture a downgrade on a winning book.

## How it was verified

```bash
python3 -m pytest tests/test_money_ready_verdict.py -q     # 64 passed
python3 -m pytest tests/test_selection_alpha_coverage.py \
    tests/test_audit3_g8_defaults.py tests/test_audit3_falsifiers.py -q   # 24 passed
```

Five new tests pin the rule: the COMMODITY-shaped case
(`sizing pf 1.0306`, `published 0.2897` → `NOT_READY`), a healthy published PF
(still `WATCH`), the absent-argument path (unchanged `WATCH`), `== 1.0`
(still `WATCH`), and `MONEY_READY` passthrough.

Live effect appears on the next `audit-dashboard.yml` run: COMMODITY moves from
`watch: [...]` to the not-ready bucket, and the `/audit` label stops
contradicting the printed PF and `/audit3`'s `KILL`.

## Related

The two audit3 contract bugs that were red in CI Tests (the 7-vs-11
`ALPHA_PASSTHROUGH_KEYS` tuple and the old `apply_selection_alpha_gate`
contract) were already repaired upstream in PR #996 (`cbda8da5e84`, merged as
`48fd154df20`); CI Tests on that sha is green. No duplicate fix was made here.
