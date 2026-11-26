# Local run of every GitHub Actions workflow — findings + 8 fixes (2026-11-26)

## What "run each workflow locally" means here

Full containerised execution of 383 workflows is not possible on one machine:
they need repository secrets, live MySQL, FTP credentials, and (with `act`) a
~1 GB runner image per distinct `runs-on`. What *is* reproducible locally — and
what catches the defects that turn CI red before a job connects to anything — was
executed for **every** workflow:

| Check | Tool | Scope |
|---|---|---|
| Workflow loads in a second, independent schema parser | `act --list -W <file>` | 383/383 files |
| YAML parse + job/step structure | PyYAML + structural rules | 383 files, 422 jobs |
| Every `run:` block parsed by its shell | `bash -n` / `sh -n` / `python -m py_compile` | 2,780 steps |
| Every `run:` block linted | `shellcheck -S warning` | 2,780 steps |
| Every script an interpreter is handed | exists? compiles? (`py_compile`, `node --check`, `php -l`) | cwd- and `working-directory`-aware |

New tool: **`tools/gha_local_run_check.py`** (writes
`reports/gha_local_run_check.{json,md}`).

```bash
python3 tools/gha_local_run_check.py                 # all workflows
python3 tools/gha_local_run_check.py --only audit3   # filename filter
python3 tools/gha_local_run_check.py --fail-on-error # CI gate mode
```

Baseline and after-fix state (validated against `origin/main`, since CI only
runs the default branch):

| | Workflows | Jobs | Steps | Clean | Warning | Error |
|---|---|---|---|---|---|---|
| Baseline `3f69e44f` | 383 | 422 | 2,780 | 363 | 18 | 2 |
| After these fixes | 383 | 422 | 2,780 | **368** | **13** | **2** |

## Fix 1 (critical) — six workflows failed every time they pushed successfully

`crypto-intraday-sim` run `45737629745` failed with:

```
Pushed successfully on attempt 1
##[error]tick could not be pushed
##[error]Process completed with exit code 1.
```

The push had **succeeded**. The step was:

```yaml
bash .github/scripts/safe_push.sh
echo "::error title=crypto-intraday-sim::tick could not be pushed"
exit 1
```

`safe_push.sh` exits 0 on success (`.github/scripts/safe_push.sh:222`), but the
next two lines run unconditionally — so the step always reported failure after a
successful push. This was introduced by the `safe_push.sh` conversion sweep
(PR #1151, merged 2026-11-26) and affects **six** workflows:

| Workflow | Step | Effect |
|---|---|---|
| `audit3-ledger.yml` | `ledger#11` | red after every successful ledger push (every scheduled run) |
| `audit3-evidence.yml` | `evidence#5` | red after every successful registry push |
| `crypto-intraday-sim.yml` | `tick#7` | red every 30 min |
| `forward-observations-ingest.yml` | `ingest#7` | red after every forward-ledger push |
| `peer-claim-verification.yml` | `verify#7` | red after every weekly refresh |
| `sleeve-daily.yml` | `marks#5` | red after every daily marks push |

All six now guard the call so the error path is reachable only on real failure:

```yaml
if ! bash .github/scripts/safe_push.sh; then
  echo "::error title=...::..."
  exit 1
fi
```

The other 19 converted workflows were checked with the same scan and do not have
the pattern (they already use `||`, `if`, or a `push_ok` flag).

## Fix 2 — `NaN` in a dashboard payload turned the CI build red

`ci.yml` run `45737767680`, step *"Build — deployable static tree is
consistent"*:

```
payloads checked: 352
BUILD FAILED:
  audit_dashboard/data/ueps_picks.json: not strict JSON (NaN)
```

Cause: `tools/run_ueps_pickers.py::write_payload` used
`json.dumps(payload, indent=2, default=str)`. `default=str` does not touch
floats, and `allow_nan` defaults to `True`, so yfinance's `NaN` price/valuation
for an unpriced ticker is written as the bare token `NaN` — invalid JSON.

Changes:

- added `_json_safe()` (recursively maps non-finite floats, including
  `numpy.float32`, to `null`) and switched the writer to
  `json.dumps(_json_safe(payload), ..., allow_nan=False)` so this fails in the
  producer rather than in CI;
- repaired `audit_dashboard/data/ueps_picks.json` (22 bare `NaN` → `null`).

Repo-wide scan of all 352 files in `audit_dashboard/data/*.json` after the
repair: **0** bare `NaN`/`Infinity` tokens remain, so the build gate is green on
every payload, not just this one.

## Verification performed

```
tools/run_ueps_pickers.py                 py_compile OK
_json_safe({'a': nan, 'b': inf, 'c': [ -inf, {'x': nan} ]})
    -> {'a': None, 'b': None, 'c': [None, {'x': None}]}   strict-serialisable
numpy.float32('nan')                      -> None
ueps_picks.json strict parse (parse_constant raises)  PASS
audit_dashboard/data/*.json              352 scanned, 0 non-strict
```

```
6 patched workflows: yaml.safe_load OK, bash -n on every step: 0 failures
actionlint on the 6 files: no new findings (only pre-existing info-level SC2086)
full sweep after fixes: 383 workflows / 422 jobs / 2,780 steps
                        368 clean, 13 warning, 2 error
```

## Findings logged, deliberately not changed

1. **`deploy_bundle.yml` → `deploy_prod_bundle.py` missing** (the only
   *unguarded* missing script). `workflow_dispatch`-only, zero runs ever, and the
   script never existed in git history (`git log --all -- deploy_prod_bundle.py`
   is empty) — the workflow was committed referencing a script that was never
   added. It will fail when first dispatched. Recommendation: retire it, or add
   the script; not deleted here because that is a product decision.
2. **`fast-stocks-competition.yml` → `run_fast_competition.py` missing.** Also
   `workflow_dispatch`-only; its schedule was disabled 2026-03-16 ("System
   blocked … Proven loser"). The script was removed in the main-only history
   strip. Same recommendation.
3. **Seven permanently-masked steps** (`script-missing-guarded`): the workflow
   already degrades with `[ -f ]` / `|| echo "::warning::"`, so the job stays
   green while the capability never runs —
   `STOCKS/competition/run_competition.py` (×2),
   `genome/dna_macd_mutations.py`, `genome/dna_pumpwatch_mutations.py`,
   `tools/update_custom_sports_picks.py`, `alpha_engine/swing_screener_runner.py`,
   `alpha_engine/value_resolver_runner.py` (plus
   `tools/ai_tournament/generate_diagnostics.py`). These are pre-existing,
   documented in-workflow deliberate skips (INCIDENT #126 for the competition
   runner) — left as-is.
4. **7 × SC2046** (`$(date …)` inside a path, `make -j$(nproc)`): word splitting
   cannot occur (no spaces are ever produced) and `worldclass-pipeline`'s
   `make -j$(nproc)` is idiomatic. No behaviour change; left untouched.
5. **1 × SC2154** (`gha-failure-digest` `$rc`): false positive — `rc=$?` is
   assigned inside the `trap` body immediately before use.
6. **4 × act schema gap**: act 0.2.98 predates `concurrency.queue` (GitHub added
   it 2026-05). Those workflows run green on GitHub (e.g. `db-freshness-guardian`
   success at 2026-11-26T01:17Z), so no change.
7. **`forward-observations-ingest` watchdog failure is by design.** Run
   `45731825183`: `FAIL POD-EQUITY-BREAKOUT has 0 forward rows 7.1d after
   pre-registration (grace 7.0d) — the emitter never landed`. That is the gate
   doing its job (a missing emitter, not a workflow defect).

## Note on branch coverage

388 workflow files exist in the working tree; only **383** are on `main` and
registered with GitHub. Files such as `cost-model-reconciliation.yml`,
`hypothesis-registry-append-guard.yml` and `premia-pod-forward-clock.yml` exist
only on feature branches and have never run — they were validated in the
branch sweep but are excluded from the `main` numbers above.

## Files changed

```
.github/workflows/audit3-evidence.yml
.github/workflows/audit3-ledger.yml
.github/workflows/crypto-intraday-sim.yml
.github/workflows/forward-observations-ingest.yml
.github/workflows/peer-claim-verification.yml
.github/workflows/sleeve-daily.yml
tools/run_ueps_pickers.py
audit_dashboard/data/ueps_picks.json
tools/gha_local_run_check.py                (new)
reports/gha_local_run_check.{json,md}       (generated)
updates/2026-11-26-workflow-local-run-validation.md
```

Backups of every edited file were taken to `/tmp/bak_2026-11-26/` before
editing.

---

## Addendum — a second `NaN` producer (same day, after the first fix)

Merging the fix above exposed that `ueps_picks.json` was not the only poisoned
payload: the `ci.yml` build on the merge commit (`67c2ecfa`, run `45738440769`)
failed again, this time on

```
audit_dashboard/data/forex_futures_picks.json: not strict JSON (NaN)
```

A scheduled workflow regenerated that file minutes after the 352-payload scan
had reported zero. The producer is
`copy_trader_intel/multi_asset_bridge.py::save_json`, which used
`json.dump(data, f, indent=2, ensure_ascii=False)` — `allow_nan` defaults to
`True`, so `NaN` confidence / ML-score / cross-signal values (which yfinance and
the backtest engines return for unpriced or untraded symbols) were written
verbatim.

Fixed the same way as the ueps writer:

| File | Change |
|---|---|
| `copy_trader_intel/multi_asset_bridge.py` | `save_json` sanitises non-finite floats (incl. numpy scalars) to `null` and passes `allow_nan=False` |
| `multi_asset/backtest_focused_noncrypto_strategies.py` | zero-trade strategies produce `NaN` sharpe/return; writer now sanitises and refuses `allow_nan` |
| `audit_dashboard/data/forex_futures_picks.json` | repaired (8 → 0) |
| `multi_asset/data/multi_asset_picks.json` | repaired (8 → 0) |
| `multi_asset/data/focused_noncrypto_backtest_results.json` | repaired (8 → 0) |

`tools/hyro_ml_pick_optimizer.py` already had the guard (`allow_nan=False`), so
it was not touched.

Verified: both writers `py_compile` clean; the sanitiser unit-checked on
`NaN`/`+Inf`/nested lists; strict-JSON parse (`parse_constant` raises) passes for
all three repaired payloads; a final scan of every JSON under
`audit_dashboard/data/` and `multi_asset/data/` reports **0** bare
`NaN`/`Infinity` tokens.

**Still systemic:** any producer of a gate-checked payload that calls
`json.dump` without `allow_nan=False` can reintroduce this. The CI gate catches
it (loudly, naming the file), which is the desired safety net; the durable fix
is to give all such producers the `_json_safe` guard. Two producers now have it,
one already had it.
