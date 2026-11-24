# FX cost-sampler: make a failed strategy chain visible in the job log

**Date:** 2026-11-23
**Scope:** `tools/fx_cost_sampler.py` stdout only. No workflow change, no artifact
change, no verdict change, no restoration of `tools/fx_meanrev_research.py`.
**Base:** `origin/main` = `f2e97ecfdd7661064e9afa65605b2eb5c0aa36a3`, clean
worktree `/tmp/fxlogvis`, branch `fix/fx-cron-log-visibility-2026-11-23`.

---

## What was broken

`run_overlap()` calls the strategy chain at
`tools/fx_cost_sampler.py:613` inside a broad `except Exception`
(`:614`) that stores `{"state": "CHAIN_FAILED", "error": repr(exc)}` (`:615`).
`tools/fx_meanrev_research.py` is absent from `main`, so the import inside
`run_strategy_chain()` (`:379`) always raises, and the job still exits 0 with
`verdict: UNCHANGED_UNKNOWN`.

The console summary (`:705-717`) printed status, per-pair stats, decision cost
and the verdict - but never the chain state or its error. `CHAIN_FAILED` was
written only into the committed JSON and the rendered `.md`, so a maintainer saw
a **green run** with no indication that a subsystem failed. Documented in
`updates/2026-11-23-fx-cron-preflight.md` (Block 16).

## What changed

`tools/fx_cost_sampler.py:717-729` - appended to the console summary, immediately
before `return 0`:

- `chain is None` -> `strategy chain: NOT RUN - <why>` (dry run, or the blocking
  status/reason).
- `chain["state"] == "RAN"` -> `strategy chain: RAN (cost applied <n> bp round trip)`
  so the absence of a warning is itself informative.
- any other state -> `WARNING: strategy chain did NOT complete: <state> - <error>`
  followed by `NOTE: cost measurement is unaffected; strategy verdict requires the chain.`

Nothing else changed: the exit code is still `return 0`, `guard_verdict()`, the
verdict allowlist, `decide_strategy_verdict()` and the payload are untouched.

## How it was verified

Tests: `tests/test_fx_cost_sampler_chain_visibility.py` (new; no prior sampler
test existed on `main`). Sampling and the chain are monkeypatched - no network.

**Fail-before** (against the unmodified file):

```
FAILED tests/test_fx_cost_sampler_chain_visibility.py::test_chain_failed_warning_carries_state_and_error
FAILED tests/test_fx_cost_sampler_chain_visibility.py::test_chain_none_prints_not_run_line
FAILED tests/test_fx_cost_sampler_chain_visibility.py::test_chain_success_prints_info_and_no_warning
3 failed, 1 passed in 0.12s
```

The one that passed is `test_chain_failed_exit_code_unchanged` - the
behaviour-preservation proof, which must pass before and after.

**Pass-after:**

```
4 passed in 0.10s
```

Wider suites in the same worktree:

```
python3 -m pytest tests/ -q -k "fx_cost or fx_cost_sampler"   -> 4 passed, 6 skipped, 7494 deselected
python3 -m pytest tests/test_edge_research_tally_consistency.py -q -> 22 passed
python3 -c "import py_compile; py_compile.compile('tools/fx_cost_sampler.py', doraise=True)" -> OK
python3 tools/fx_cost_sampler.py --self-test -> rc=0 (7/7 PASS)
```

Real end-to-end console comparison (stubbed sampling, chain raising the actual
`ModuleNotFoundError`), before vs after:

```
BEFORE: decision cost: 2.975 bp | verdict: UNCHANGED_UNKNOWN
        RC = 0
AFTER:  decision cost: 2.975 bp | verdict: UNCHANGED_UNKNOWN
        WARNING: strategy chain did NOT complete: CHAIN_FAILED - ModuleNotFoundError("No module named 'tools.fx_meanrev_research'")
        NOTE: cost measurement is unaffected; strategy verdict requires the chain.
        RC = 0
```

Artifact payloads from the two runs were compared field by field: the only
differences are the wall-clock timestamps (`generated_utc`, `session.now_utc`)
and the output directory in `raw_samples_path`. Status, chain state, verdict and
every measured value are identical.

## Explicitly not done

`tools/fx_meanrev_research.py` was **NOT** restored or added - the defect fixed
here is the invisibility of the failure, not the failure itself.
`.github/workflows/fx-cost-overlap.yml` was not modified.
