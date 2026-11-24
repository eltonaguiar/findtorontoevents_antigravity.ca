# Canonical PBO threshold — my gate was 10× stricter than the definition

**Date:** 2026-11-20
**Workstream:** A5 (claimed from kilo/grok `docs/NEXT_PHASE_PLAN_2026-11-19.md`)
**Branch:** `fix/audit-ledger-population-survivorship`

## What was broken

`tools/anti_overfit_gate.py` declared its own PBO decision point:

```python
PBO_MAX = 0.05
```

That is 10× stricter than the Bailey & López de Prado (2014) definition, in which
**PBO ≥ 0.5** is the decision point (the in-sample winner's out-of-sample rank
falls below the median more often than not → selection is indistinguishable from
picking at random).

It also disagreed with every other PBO consumer in the repo:

| Threshold | Module |
|---|---|
| **0.05** | `tools/anti_overfit_gate.py:48` ← the outlier |
| **0.05** | `alpha_engine/fundamental_macro_gates.py:754` |
| **0.3** | `tools/build_cpcv_pbo_results.py` |
| **0.5** | `alpha_engine/eagle_gates.py:210` (`_EAGLE6_MAX_PBO_GLOBAL`) |
| **0.5** | `alpha_engine/admissibility_pipeline.py:409` |
| **0.5** | `tools/run_anti_overfit_audit.py:254` |
| **0.5** | `tools/build_cpcv_pbo_results.py:110` |
| **0.5** | `tools/anti_overfit_audit_sidecar.py:231` |
| **0.7** | `eagle_gates.py:295` (non-strict tier), `build_cpcv_pbo_results.py:112` |

Five decision points across four values. A5 called for exactly this cleanup.

## Why it mattered more than cosmetics

A gate set to a value nothing can pass is not a safety feature — it is a gate that
gets deleted, or wrapped in `continue-on-error`, within a week. That is the precise
failure mode the gate was built to prevent, and the same reasoning that forced the
ledger-fetch step in `anti-overfit-gate.yml` (a gate that exits 2 on every fresh
checkout is a false blocker, and false blockers get disabled).

PBO is `None` for most source systems anyway — `evaluate_strategy` returns `nan`
by design because PBO is not estimable from a single return series, and
`MIN_STRATEGIES_FOR_PBO = 2` means single-strategy classes can never compute it.
So `PBO < 0.05` was unpassable in the overwhelming majority of real cases.

## What changed

**`tools/pbo_cscv.py`** — new single source of truth:

```python
PBO_CANONICAL_THRESHOLD: float = 0.50
PBO_NOT_COMPUTED: str = "NOT_COMPUTED"
```

with a comment explaining why a locally-invented stricter number is the wrong move.

**`tools/anti_overfit_gate.py`** — imports instead of re-declaring:

```python
from tools.pbo_cscv import PBO_CANONICAL_THRESHOLD
...
PBO_MAX = PBO_CANONICAL_THRESHOLD
```

## The second half of A5: `0.0` is a measurement, `None` is not

A5 says "0.0 must render as 'not computed'". The underlying hazard is the reverse
and worse: Python makes `0.0` falsy, so `if not pbo` and `pbo or fallback` silently
report a **perfect selection as unmeasured**. That is the same bug class as
`status in {"WIN","LOST"}` dropping every `WON` row — a valid value disappearing
through a truthiness test rather than an explicit comparison.

This module already handled it correctly (`pbo is None` / `_is_bad_number`, never
`if not pbo`). The new tests pin it so a future edit cannot regress it.

## Verification

```
python3 -m pytest tests/test_pbo_canonical_threshold.py -q
  → 10 passed

python3 -m pytest tests/test_anti_overfit_validator.py tests/test_closed_pick_loader.py \
    tests/test_pbo_contract_and_gate.py tests/test_wfe.py \
    tests/test_pbo_canonical_threshold.py -q
  → 50 passed, 2 skipped   (2 skips are arch.bootstrap.SPA, not installed)

python3 tools/anti_overfit_gate.py --top 5
  → exit 1, 5/5 FAIL
```

**The verdict did not move.** All five systems still FAIL, on DSR or `MIN_PICKS`:

| system | n | DSR | PBO | SR/period |
|---|---|---|---|---|
| kimi_riseoftheclaw | 1714 | 9.70e−10 | None | −0.0802 |
| luxalgo_filters | 1224 | 0.1026 | None | +0.0424 |
| battleground | 122 | 0.4085 | None | +0.2058 |
| alpha_engine | 102 | 0.0010 | None | −0.0300 |
| ml_bg_system_f | 90 | 1.04e−13 | None | −0.8391 |

So the correction removed latent over-strictness **without weakening any live
decision**. That is the desired outcome: the threshold was wrong, but it was not
load-bearing.

## Deliberately NOT changed (needs owner decision)

Two non-canonical thresholds remain, in modules where the value is load-bearing
for **which picks emit**:

- `alpha_engine/fundamental_macro_gates.py:754` → `pbo < 0.05`
- `tools/build_cpcv_pbo_results.py` → `pbo < 0.3`

Changing either alters strategy emission behaviour. That is a behavioural change
deserving its own review, not a drive-by edit from a validation branch. The new
ratchet test (`test_every_pbo_consumer_agrees_on_half`) pins the current set so
the count cannot silently grow while the debt stays visible.

## Known unrelated finding (not fixed here)

`alpha_engine/eagle_gates.passes_pbo_global_gate()` returns `pass: True` when
global PBO data is unavailable ("no_data (fail-open)"). This is documented as
intentional, and it is currently **not** firing — `tools/cpcv_pbo_results.json`
exists, is git-tracked, and holds `pbo = 0.8222`, so the strict gate correctly
blocks (`global_pbo=0.822 >= 0.5`).

But the fail-open is one corrupted JSON away from passing everything, because
`_load_pbo_global()` wraps the whole read in `except Exception: return None`. A
parse error, a permission error, or a bad merge is indistinguishable from "no
data". If A5's doctrine is "0.0 must never read as not-computed", then the mirror
rule should be "not-computed must never read as PASS". That is a tri-state
(`PASS` / `FAIL` / `NOT_COMPUTED`) refactor of a Tier-1 promotion gate and needs
its own branch.
