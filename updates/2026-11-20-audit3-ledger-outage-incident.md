# Incident: audit3 ledger build outage (2026-11-19 23:45 → 2026-11-20 00:11)

**Severity:** the 6-hourly `audit3-ledger` job could not publish; `/audit3` and
`/audit2` data would have gone stale.
**Detection:** the 30-minute deploy monitor (`/audit3` freshness + run status).
**Duration:** ~26 minutes of failed builds; no incorrect data was published (the
job aborts before writing the ledger).

## Timeline

| Time (UTC) | Event |
|---|---|
| 23:45 | scheduled run fails: `argparse.ArgumentError: conflicting option string: --history` |
| 23:49 | manual retry fails the same way |
| 23:51 | after removing the duplicate flags, run fails: `TypeError: build_report() got an unexpected keyword argument 'require_alpha'` |
| 00:03 | after the repair PR, ledger builds (8,632 scored) |
| 00:11 | `denylist_hits` restored to the report; ledger rebuilt |

## Root cause

A correctness port was merged **partially**: the caller side landed without its
callee counterpart. Four defects, none behavioural:

1. `audit3-ledger.yml` passed `$history_arg` **and** the same four flags
   explicitly → argparse rejected the repeated option.
2. `main()` passed `require_alpha=True`; `build_report()` did not accept it.
3. The N1 persistence block existed **twice** in `build_report`; the second copy
   reset `persistence_counters`, so `n_demoted_this_run` was always 0 and the
   sidecar could disagree with the published verdict.
4. `ALPHA_PASSTHROUGH_KEYS` was referenced but never defined → `NameError`
   whenever an alpha sidecar was present.
5. (Follow-on) the `denylist_hits` report line was dropped while its helper
   survived.

## Fixes

| PR | What |
|---|---|
| #971 | remove the duplicate `--history` flags (workflow) |
| #972 | accept `require_alpha`; delete the duplicated persistence block; define `ALPHA_PASSTHROUGH_KEYS`; reconcile cost-stress to cap at `CANDIDATE` instead of `WEAK` |
| #973 | restore `"denylist_hits": _denylist_hit_summary()` in the report |

## Guards added (so this cannot merge silently again)

| PR | Test | Catches |
|---|---|---|
| #974 | `tests/test_audit3_cli_smoke.py` | parser build (`--help`), `require_alpha` keyword, undefined constant, G8 capping |
| #975 | `tests/test_audit3_ledger_e2e.py` | the **whole CLI invocation** with the workflow's flags: exit 0, report contract, denominator invariant, sidecar written |

Both run in the normal CI test job.

## Verification after repair

- `pytest tests/test_audit3_*.py` → 101 passed (plus 5 new guard tests total).
- End-to-end build `rc=0`, 8,735 rows scored on the live payload.
- Ledger live: `2026-11-20T00:45Z`, canonical, 8,632 scored, 0 proven / 0
  candidate, persistence `true`, `denylist_hits n=41`.
- First **scheduled** run after the repair (`00:43`) succeeded.

## Lessons

1. **Merge the pair, not the half.** A keyword added in `main()` must land with
   its `build_report()` parameter in the same commit.
2. **Test the command the workflow runs**, not only the helpers — the CLI
   surface (argparse, kwargs, report keys) is where merge damage hides.
3. **Duplicated blocks are invisible in review.** The double persistence gate
   looked like one gate with a comment above it.
4. The deploy monitor caught this within one cycle because it checks
   `generated_at` freshness, not just HTTP 200.
