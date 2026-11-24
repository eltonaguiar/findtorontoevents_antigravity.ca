# One gate that can fail, and the CRYPTO PF that was never a contradiction

Date: 2026-11-20
Author: freebuff (deepseek-v4-flash)

## 1. The anti-overfit audit can now fail a build

**What was broken.** `tools/run_anti_overfit_audit.py` always returned 0. It printed
`DSR<0.95 SUSPECT` and exited success, so every consumer treated a failed audit as a pass.
The CI step that runs the sidecar masked its own failure twice over — `|| echo "::warning ..."`
on the command *and* `continue-on-error: true` on the step — so the only anti-overfit gate in
the pipeline could not fail under any circumstances.

**What changed.**
- `tools/run_anti_overfit_audit.py`: adds `--gate` / `--dsr-threshold` (default 0.95).
  `_gate_failures()` returns one line per system that fails. A **skipped** system counts as a
  failure — "insufficient sample" is not certification — and an unavailable DSR counts as a
  failure too. With `--gate`, any failure exits **2**.
- `tools/anti_overfit_audit_sidecar.py`: adds `gate_failures(payload, threshold, min_n)` — a pure
  function over the written artifact, so the CI logic is testable without a database — plus
  `--check-only` (judge the existing payload, no DB) and `--gate`. A missing payload exits **3**,
  not 0: an audit that cannot run is not a pass. `__main__` now propagates the exit code.
- `.github/workflows/audit-dashboard.yml`: the early sidecar step loses both masks (a DB failure
  should fail the step), and a new **blocking** step `Anti-overfit GATE` runs
  `tools/anti_overfit_audit_sidecar.py --check-only --gate --dsr-threshold 0.95` with no
  `continue-on-error`.

**Placement, stated deliberately.** The blocking step runs **after** commit and deploy, not at
the sidecar's original position (~step 12 of 53). Failing early would abort the entire hourly
refresh — ingest, resolution, payload build, deploy — so a statistical gate would take the data
pipeline down with it, and the artifact the gate judges would not exist yet. Here it can fail the
job without withholding data.

**It fails today.** Measured in this checkout: **74 of 80 strategies are below DSR 0.95**
(`commodity_rsi_divergence` 0.9032, `luxalgo_confluence` 0.6361, `high_trust_momentum` 0.5837, …).
The CLI path agrees: `run_anti_overfit_audit.py --top 3 --gate` exits 2 with
`kimi_riseoftheclaw` 0.000, `luxalgo_filters` 0.000, `alpha_engine` 0.000. That is the honest
state of the book, and it is why the gate was worth wiring: a gate that only ever passes teaches
nothing. The consequence is that the audit-dashboard run will now report failure until something
clears 0.95. Data still publishes; the run is red.

## 2. The CRYPTO PF "divergence" is a population gap

Copilot reported money_ready CRYPTO PF **0.26** against audit3 **0.83**. Measured, both from disk:

| cohort | n | PF | WR | mean net/pick | cost |
|---|---|---|---|---|---|
| dashboard `recent_closed` | 2,070 | 1.3131 | 46.14% | +0.5355% | none |
| audit3 ledger class node | 6,874 | 0.8339 | 40.18% | −0.3159% | 0.0985%/pick |
| money_ready policy-clean | 22,148 | 0.2628 | 41.38% | −0.0565% | via registry |

PF is `sum(wins)/|sum(losses)|` at all three sites (`audit3_tribunal.py:294`,
`money_ready_verdict.py:1585`, the sidecar), so no arithmetic can reconcile them. The population
ratio is **3.22x** and the PF ratio is **3.17x** — the same number. audit3's cohort is missing
69% of the class.

**Answer: the 0.26 is the right class-level figure**, because it is the only one computed over the
class's full resolved population. The 0.83 is correct for its 6,874-pick subset and is wrong only
when quoted as "CRYPTO" with no n. The 1.31 is a recent-window gross figure. All three are below
1.0 once cost and the full population are honoured, so the disagreement is magnitude, not
direction — CRYPTO loses money on every convention tested.

Tool: `tools/crypto_pf_reconcile.py` (regenerates the table from disk). Report:
`reports/crypto_pf_denominator_2026-11-20.md`.

## 3. `evaluate_strategy` does not compute PBO — claim not reproduced

Opencode's item (d) said `evaluate_strategy` fabricates its PBO from synthetic zero-mean peer
strategies. Not reproduced, at the level claimed:

- `stabilization/scan_and_test_strategies.py:143` `evaluate_strategy()` contains **no PBO code**.
  It compares trades / win_rate / sharpe / max_drawdown against `PASS_CRITERIA` and returns a
  status string. `grep -in "pbo|cscv|overfit" stabilization/*.py` returns **0 matches**.
- The PBO in this repo is `alpha_engine/anti_overfit_validator.py:cpcv_pbo`, which takes a
  `(T x S)` matrix of **actual** per-strategy returns and raises when `S < 2` or `T < 2*n_folds`.
  It does not synthesise peers.

The real defect nearby is different and worth recording: both callers mis-align the matrix.
`run_anti_overfit_audit.py:_build_pbo_matrix` truncates every strategy to the shortest series
(`v[:T]`), and the sidecar uses `[-min_len:]`. Per-strategy pick sequences are not row-aligned by
time, so the columns compare different calendar windows — that corrupts PBO without inventing
anything. PBO numbers from those two paths should be treated as unreliable until aligned by exit
timestamp; no code was changed here.

## 4. Verification

```
python3 -m pytest tests/test_anti_overfit_gate_2026_11_20.py -q     -> 7 passed
python3 tools/anti_overfit_audit_sidecar.py --check-only --gate    -> exit 2, 74/80 below 0.95
python3 tools/run_anti_overfit_audit.py --top 3 --B 200 --gate     -> exit 2 (3/3 below 0.95)
python3 tools/crypto_pf_reconcile.py                               -> report regenerated from disk
yaml.safe_load(audit-dashboard.yml)                                -> 53 steps, gate step blocking
```

Tests pin both directions: clean payload returns 0, a 0.31 DSR returns 2, a null DSR returns 2, a
missing payload returns 3, advisory mode returns 0, and the workflow assertion checks the gate
step has no `continue-on-error` and sits after `Deploy to all 3 FTP`.

## 5. Limits

- The gate covers strategy-level DSR only. PBO and Reality Check are still advisory; gating on an
  unaligned PBO would gate on noise.
- 0.95 is a fixed threshold with no multiple-testing correction on top of the per-strategy DSR;
  `n_trials` is the strategy count at run time.
- If red CI becomes noise rather than signal, the honest adjustment is a lower threshold with a
  stated reason, not `continue-on-error` again.
