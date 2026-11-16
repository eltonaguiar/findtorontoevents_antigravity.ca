# CI Tests red on main: my feed-health test leaked `sys.modules`

**Date:** 2026-11-16
**Worktree:** `.worktrees/p0-audit-json-2026-11-16`
**Failing run:** [43820418075](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/43820418075) — `completed/failure`, 06:58Z, jobs `test (3.11)` and `test (3.12)`
**Fix file:** `tests/test_dashboard_payload_health_optional.py`

## What was broken

`CI Tests` on `main` failed for three consecutive pushes (05:27Z, 06:50Z, 06:58Z) after a green run at 05:13Z. The gating step reported:

```
= 21 failed, 6630 passed, 65 skipped, 87 deselected, 2 xfailed, 16 errors in 137.37s =
##[error]Process completed with exit code 1.
```

Two distinct error shapes, both about the same module:

- `ImportError: module audit_trail.dashboard_generator not in sys.modules` — 10 collection errors in `tests/test_derive_asset_class_precedence.py`
- `ImportError: cannot import name 'enrich_health_with_recent_window' from 'audit_trail.dashboard_generator' (unknown location)` — failures in `test_etf_elite_floor_and_60d_enrich.py`, `test_hc_after_cost_gate.py`, `test_m033_blocked_aggregator.py`, `test_m067_registry_reader.py`

`audit_trail/dashboard_generator.py` on `main` was **intact** — 18,774 lines, all five symbols present (`enrich_health_with_recent_window`, `stamp_after_cost_fields`, `collect_system_stats`, `_registry_backed_ac_breakdown`, `compute_asset_class_health`), and it compiles clean. So this was never a code regression in the generator.

## Root cause

My own new test file, shipped in `f107b7da3e5` (feed-health optional PM sources), installs a stub module directly into `sys.modules`:

```python
sys.modules["audit_trail.dashboard_generator"] = fake
```

Nothing restored the real module afterwards. pytest collects files in **alphabetical order**, and `test_dashboard_payload_health_optional.py` sorts before all five affected modules — so the stub shadowed the real package for the remainder of the session and every later import from `audit_trail.dashboard_generator` failed.

`(unknown location)` is the tell: the module object existed but was my `types.ModuleType` stub with no `__file__` and none of the real names.

**Why it escaped review:** the new tests pass in isolation, and my earlier check ran only the four new tests. A two-file reproduction of the failing module (`test_derive_asset_class_precedence.py` + `test_m067_registry_reader.py`) also passed, because the leaking file was not part of that pytest session.

## What changed

An autouse fixture in `tests/test_dashboard_payload_health_optional.py` snapshots the prior module object before each test and restores it after:

```python
_ABSENT = object()


@pytest.fixture(autouse=True)
def _restore_generator_module():
    prior = sys.modules.get("audit_trail.dashboard_generator", _ABSENT)
    yield
    if prior is _ABSENT:
        sys.modules.pop("audit_trail.dashboard_generator", None)
    else:
        sys.modules["audit_trail.dashboard_generator"] = prior
```

When the real module was never imported (`_ABSENT`), it is popped rather than left behind as a stub. No production code changed; the fix is test-only (+23 lines, no deletions).

## How it was verified

| Check | Before fix | After fix |
|---|---|---|
| 6-file repro: my file + all 5 CI-failing modules | **21 failed, 16 errors** in 0.68s | **54 passed** in 0.81s |
| `tests/test_dashboard_payload_health_optional.py` alone | 4 passed | 4 passed |

Post-push, the real confirmation is the next `CI Tests` run on `main` turning green — the local repro reproduces the exact CI error text and the exact failing modules, but it is a reproduction, not the CI run itself.

## Process lessons

1. **Any test that writes to `sys.modules` must restore it via a fixture or `monkeypatch.setitem`.** Alphabetical collection order makes the leak invisible in per-file runs and guaranteed in full-suite runs.
2. **A blanket cleanup loop is dangerous:** `git status --porcelain | ... | git checkout -- "$f"` treated this edited test file as test dirt and reverted the fix once. Cleanup after test runs must exclude files under edit.
3. Verifying a fix means running it in the **same order the gate runs it** — the opposite of the narrowest possible repro.
