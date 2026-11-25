# Orphan tool workflows landed — 3 gates that already had their tools on `main`

**Date:** 2026-11-25
**Scope:** CI only. No production code path, no pick generation, no scoring changed.
**Related:** `docs/AGENT_DIFF_FABRICATION_PATTERN_2026-05-31.md`, Wire-Up Rule (`CLAUDE.md`)

---

## 1. What was broken

The repository's own **Wire-Up Rule** says an integration is not finished until
something in the production path actually calls it. The rule was written for
`alpha_engine/*_integration.py`, but the same failure mode had quietly appeared in
`tools/`: three finished tools sat on `main` with **no workflow, no caller, no
schedule** — so they had never executed even once in CI.

| Tool on `main` | Bytes | Callers before this change |
|---|---|---|
| `tools/gha_quality_framework.py` | present | **none** — no workflow referenced it |
| `tools/weekly_scorecard.py` | present | **none** — no workflow referenced it |
| `tools/pbo_cscv.py` | present | **none** — no workflow referenced it |

These are exactly the "breadth-over-depth" artifacts the Wire-Up Rule exists to
prevent: importable, tested-looking, and dead. The fix is not to write more tools —
it is to **land the workflows that run the tools that already exist.**

The workflows themselves already existed in PR #1116 (`coverage-and-verdict-tooling-2026-11-24`),
buried in a 1,846-file / `+894,530 −21,688` branch dump. This change extracts the
subset that is provably runnable against `main` today.

---

## 2. What changed — 6 files

### Workflows added (3)

| File | Runs | Why it is safe to land |
|---|---|---|
| `.github/workflows/gha-quality-framework.yml` | `tools/gha_quality_framework.py` Q1–Q10 static rules | tool already on `main`; `workflow_dispatch` **only** (schedule block still commented out) |
| `.github/workflows/weekly-scorecard.yml` | `tools/weekly_scorecard.py` | tool already on `main`; writes a generated `reports/weekly_scorecard/` artifact |
| `.github/workflows/validation-gates.yml` | `tools/pbo_cscv.py`, anti-overfit tests | tools/tests already on `main` |

### Support files added (3)

| File | Purpose |
|---|---|
| `GHACTIONS_LIVE/gha_quality_baseline.json` | Baseline for `--check`, so only **NEW** blocking violations fail |
| `tools/purge_zero_pnl_picks.py` | Dry-run-by-default dependency of `tests/test_purge_zero_pnl_picks.py` |
| `tests/test_purge_zero_pnl_picks.py` | Referenced by `validation-gates.yml`'s blocking pytest step |

### A fatal YAML defect was fixed in `validation-gates.yml`

`validation-gates.yml` as it existed in PR #1116 **could never have parsed**, which
means it had never run, which means its "blocking on PR" guarantee had never been
exercised. The "Run PBO/CSCV gate (blocking on PR)" step opened a `python -c "` string
on an indented line but put the Python body at **column 0** — which terminates a
`run: |` block scalar — and then closed the quote with an orphaned `"` on its own line.

Replaced with a heredoc, and the orphaned quote dropped:

```yaml
      - name: Run PBO/CSCV gate (blocking on PR)
        if: github.event_name == 'pull_request'
        run: |
          python - <<'PY'
          import sys
          sys.path.insert(0, '.')
          from alpha_engine.money_ready_verdict import money_ready_verdict

          results = money_ready_verdict()
          for ac, r in results.items():
              print(
                  f"{ac}: verdict={r.get('verdict')} dsr_ok={r.get('dsr_ok')} "
                  f"pbo_ok={r.get('pbo_ok')} n={r.get('n_resolved', r.get('n', 0))}"
              )
              # Hard gate: no MONEY_READY if DSR or PBO failed
              if r.get('verdict') == 'MONEY_READY':
                  assert r.get('dsr_ok') is True or r.get('dsr_ok') is None, f'{ac}: MONEY_READY but DSR failed'
                  assert r.get('pbo_ok') is True or r.get('pbo_ok') is None, f'{ac}: MONEY_READY but PBO failed'
          print('All hard gates passed.')
          PY
```

### The baseline had to be regenerated

The baseline inherited from #1116 was generated before ~5 days of `main` drift, so
`--check` reported **2 NEW blocking violations** and exited **1** — the gate would have
gone red on its first run for reasons unrelated to any change:

```
BEFORE: --check --baseline (inherited)  -> exit 1, "2 NEW blocking violation(s) of 103 total"
          NEW Q2 ETF Trend Forward Clock (month-end): third-party action not SHA-pinned
                                                      stefanzweifel/git-auto-commit-action@v7
          NEW Q7 CI: gate-shaped step swallows failure: Lint — Python style, changed files only

AFTER : --write-baseline against current main, then --check -> exit 0, "0 NEW blocking violation(s) of 103 total"
```

---

## 3. Deliberately NOT landed

### `audit-review-doc-lint.yml` (+ its `tools/test_doc_source_lint.py`) — **held back**

The tool and its 12 unit tests pass cleanly, but the workflow **would land red**:
running `tools/doc_source_lint.py` over `docs/audit_review_2026-11-22/` on current
`main` reports **11/13 clean, exit 1** on pre-existing content debt:

```
FAIL docs/audit_review_2026-11-22/09_PENNY_STOCK.md
  - 09_PENNY_STOCK.md:3: bare number '0.3' before any [SRC: ...] marker in its section, and not UNMEASURED
FAIL docs/audit_review_2026-11-22/13_PREDICTION_MARKET.md
  - 13_PREDICTION_MARKET.md:60: bare number '38.2' before any [SRC: ...] marker in its section, and not UNMEASURED
```

Landing a gate that is already red on unchanged content is precisely the anti-pattern
that made the Gitleaks PR gate ignorable for weeks (see
`updates/2026-11-25-gitleaks-pr-gate-false-red.md`). The two documents need real
`[SRC: ...]` citations — that is a content decision, not a CI decision, so it is
deferred to whoever owns those dossiers. The tool remains available on the #1116
branch, unchanged.

### The other 11 workflows from #1116 — **blocked, cannot land**

Each depends on a tool that does not exist on `main`. Landing the workflow alone would
fail on `No such file or directory`:

`carry_execution_cost.py`, `class_verdict_audit.py`, `verdict_drift_gate.py`,
`cost_model_reconciliation.py`, `digest_artifact_guard.py`, `etf_spread_sampler.py`,
`harness_certification.py`, `integrity_lint.py`, `hypothesis_registry_guard.py`,
`live_daytrade_sim.py`, `premia_forward_clock.py`, `price_freshness_sla.py`,
`assert_surface_parity.py`

### #1116's other 1,830 files — **must not land**

Of the 1,846 paths, **383 already exist on `main`** and **706 are data/state blobs**
plus **10 agent-scratch paths** (`.buffy-tools/`, `.coms*`, `.openclaude`). None of
that belongs in a CI change.

---

## 4. How it was verified

Every claim below was executed, not assumed.

1. **YAML parses** — all 3 files load through `yaml.safe_load`:
   `YAML OK: 3/3`.
2. **Every `run` block is valid shell** — `bash -n` over each step body:
   `run blocks: 16, failures: 0`.
3. **Every referenced path exists** — static audit of all paths named in the 3
   workflows: **12 referenced, 0 genuinely missing**. Two earlier gaps were closed by
   adding `tests/test_purge_zero_pnl_picks.py` and its dependency
   `tools/purge_zero_pnl_picks.py`. The one remaining non-existent path,
   `reports/weekly_scorecard/scorecard.md`, is an **output** the workflow generates
   before `cat`-ing it, so its absence in a clean checkout is expected.
4. **The blocking pytest step passes** — the exact command from the workflow:
   ```
   22 passed in 0.63s
   ```
   (3 files: `test_profit_program_math_2026_11_20.py`,
   `test_profit_program_policies_2026_11_20.py`, `test_purge_zero_pnl_picks.py`)
5. **The anti-overfit tests pass** — `27 passed in 5.18s` across
   `test_anti_overfit_validator.py`, `test_anti_overfit_gate_2026_11_20.py`,
   `test_anti_overfit_wireup.py`.
6. **The PBO/CSCV gate body actually runs and passes** — executed verbatim:
   ```
   CRYPTO: verdict=NOT_READY dsr_ok=False pbo_ok=None n=3733
   FOREX:  verdict=NOT_READY dsr_ok=False pbo_ok=None n=666
   EQUITY: verdict=NOT_READY dsr_ok=False pbo_ok=None n=264
   ...
   All hard gates passed.
   ```
   Note the gate is real: `MONEY_READY` with `dsr_ok=False` would raise. Today no class
   is `MONEY_READY`, so nothing trips — the assertion is live, not vestigial.
7. **The quality framework self-test passes** — `Q1..Q10 PASS`, `SELF-TEST PASS`.
8. **The quality gate is green against the shipped baseline** —
   `--check --baseline` → **exit 0**, `0 NEW blocking violation(s) of 103 total`.
   (Verified with the *real* exit code; an earlier reading of `0` was `sed`'s status,
   not Python's — see the lesson below.)
9. **The scorecard generator works** — wrote `scorecard.json` + `scorecard.md`, exit 0,
   both plain and `--strict`.
10. **`py_compile`** clean on all tools.

### Known non-blocking behaviour

`validation-gates.yml`'s anti-overfit audit step (`tools/run_anti_overfit_audit.py`)
needs `audit_dashboard/data/dashboard_data.json`, a generated artifact that does not
exist in a clean checkout, so it raises `FileNotFoundError` on a fresh clone. That step
is `continue-on-error: true` **by design** and therefore does not fail the job. It
becomes useful once the dashboard pipeline has produced the file.

---

## 5. Follow-ups (measured, not yet done)

| # | Item | Why it is deferred |
|---|---|---|
| 1 | Uncomment `schedule:` in `gha-quality-framework.yml` after one green dispatch | The workflow's own header documents a deliberate dispatch-first enablement policy |
| 2 | Fix the 2 pre-existing `[SRC:]` gaps in `09_PENNY_STOCK.md` and `13_PREDICTION_MARKET.md`, then land `audit-review-doc-lint.yml` | Requires real citations — an authoring task, not CI |
| 3 | Land the 11 blocked workflows, each alongside its missing tool | 13 tools do not exist on `main` |
| 4 | 4 pre-existing `bash -n` failures on `main` in `audit-drift-telemetry.yml`, `dynamic-alpha-engine.yml`, `wsl-runner-manager.yml` (2 steps) | Pre-existing, untouched here; worth their own fix |
| 5 | Arbitrate `alpha_engine/cost_gate.py` (add/add, 1,641 bytes on `main`) | Two implementations exist across branches; a human must pick |

---

## 6. Notes for the next agent

1. **A tool with no caller is not shipped.** `grep -rln '<toolname>' .github/workflows/`
   is the single fastest orphan check in this repo. Run it before believing a tool works.
2. **Never trust that a workflow file in a PR branch is valid.** `validation-gates.yml`
   in #1116 had never parsed, so its "blocking" promise had never run. Validate every
   YAML and every `run` block before landing it.
3. **`$?` after a pipe is the last command's status.** `cmd | tail` reports `tail`'s exit
   code. Capture with `cmd >/dev/null; rc=$?` or `${PIPESTATUS[0]}`. This produced a
   false "exit 0" reading on a gate that was actually failing.
4. **Regenerate baselines at land time.** A baseline is a snapshot of debt; `main` drifts
   under it daily. A stale baseline converts a useful gate into a permanent red.
5. **A gate that is red on unchanged content is worse than no gate** — it teaches
   reviewers to ignore red. Hold it back instead.
