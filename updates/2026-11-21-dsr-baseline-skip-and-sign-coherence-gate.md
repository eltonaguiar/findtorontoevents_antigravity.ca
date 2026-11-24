# DSR gate skips when its baseline is missing; sign-coherence gate can finally run

Date: 2026-11-21
Files: `alpha_engine/money_ready_verdict.py`, `.github/workflows/sign-coherence-gate.yml`,
`tests/test_dsr_baseline_skip.py`, `tools/subq_delegate.py`

## 1. The DSR gate was passing classes it could not assess

`_dsr_gate()` resolved the class trial count as
`NB_TRIALS_BY_CLASS.get(_cls, 1)` — so any class **not** in the map silently fell
back to `nb_trials=1`, and a Deflated Sharpe Ratio with one trial applies zero
multiple-testing correction. The map covers only COMMODITY, CRYPTO and FOREX;
EQUITY, ETF, BOND, MUTUAL_FUND and FUTURES therefore published a
confident-looking DSR that had never been deflated.

With `nb_trials=1` the deflation term is zero, so DSR degenerates into the raw
Sharpe test. `NB_TRIALS_BY_CLASS` only covers COMMODITY, CRYPTO and FOREX;
EQUITY, ETF, BOND, MUTUAL_FUND and FUTURES therefore reported
`dsr_ok=True/False` on a number that had never been deflated. That is the
"absence of a baseline rendered as evidence of edge" failure: the classes with
no trial accounting were the ones most likely to show a clean DSR.

**Change**

- `_dsr_gate(returns, asset_class="")` looks the class up by upper-cased key
  **without a default**.
- **No baseline → skip, not pass**: returns `ok=None`, `skipped=True`,
  `dsr_score=None`, `nb_trials=None`, and a `note` naming the missing input. It
  does *not* compute an undeflated number, because a number that large reads as
  a result.
- One `stderr` warning per class per process, telling the operator to add the
  real trial count.
- Payload gains `dsr_nb_trials`, `dsr_skipped`, `dsr_note` beside `dsr_ok`, so the dashboard can show *why* a class has no DSR instead of a blank.

**Behaviour on the verdict**: unchanged in direction. `_verdict` already treated
`ok=None` as not-ok, so a skipped class cannot reach MONEY_READY on DSR; SPA
(family-wise) can still carry it, which is the documented substitution rule.

## 2. The sign-coherence gate could never decide anything

`audit_trail/sign_coherence_check.py` documents exit `1` = *flips found* and
`2` = DB unreachable. The workflow ran it under `set -euo pipefail`:

```yaml
python3 -m audit_trail.sign_coherence_check --json "$OUTPATH" 2>&1 | tee /tmp/scan.log
```

so exit 1 aborted the **scan step** before the gate decision ran. Every night
with ≥1 flip (i.e. every night) the job was red at the scan step, and the
tolerant branch — `flips ≤ baseline` → `::warning::` — was dead code. A 1-flip
night and a 400-flip night produced the identical red build, so the gate could
not distinguish "purge nearly done" from "corruption growing".

**Change**

- Capture `PIPESTATUS[0]`; only exit `> 1` is fatal. Exit 0/1 both feed the gate.
- Gate decision guards against an empty `$FLIPS` (report not written) instead of
  failing on an unset variable.
- The notice line records which exit code the scan returned.

## Verification

- `pytest tests/test_dsr_baseline_skip.py tests/test_money_ready_verdict_strict_json.py tests/test_profit_program_policies_2026_11_20.py tests/test_money_ready_verdict.py` → **32 passed**.
  New tests pin: EQUITY skips (`ok is None`, `skipped`, no score), the empty
  class skips, CRYPTO uses `n_trials=14`, lookup is case-insensitive, no
  baseline class may have `n<2`, and a skipped DSR cannot reach MONEY_READY
  without SPA.
- `python -m py_compile` on the edited module → OK.
- Workflow YAML parses (`yaml.safe_load`), scan step contains the `SCAN_STATUS`
  guard.
- Shell logic exercised against a stub checker exiting 1: `scan_exit=1` →
  `GATE_PASS_WITH_WARNING flips=1` (previously the job died at the pipe).

## Residual

- `NB_TRIALS_BY_CLASS` still only lists three classes. That is now *loud*
  (skip + warning + null DSR on the dashboard) rather than silently green, but
  EQUITY/ETF/BOND remain unassessed until someone records their real trial
  counts. Populating them is a measurement task, not a code change.
- Next nightly `Sign-Coherence Gate` run should go green with
  `::warning::Sign-flip count N (≤ baseline 367)`; if it still fails, the log
  will show exit 2 (DB) instead of masking the real gate decision.
