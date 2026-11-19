# audit3 P0/P1 correctness — three gate gaps and the unscheduled forward ledger

**Date:** 2026-11-19
**Branch:** `fix/audit3-alpha-scope`
**Base:** `3dfa66e` ("feat(audit3): P0/P1 correctness …")
**Verified by:** independent 3-agent review of `3dfa66e` + re-derivation of every claim

## What was broken

An independent review of commit `3dfa66e` found that three of its five claims did
not hold at the stated acceptance criterion, and that the forward ledger it added
had no writer on a schedule.

### 1. G8 selection-alpha gate was class-wide, so it could not stop a beta-only strategy

`apply_selection_alpha_gate()` looked up alpha by `asset_class` and
`asset_class/direction` only. Every strategy cell in a class with positive alpha
therefore inherited the class's proof. The acceptance criterion — "a beta-only
*profitable* cell cannot reach PROVEN_T2" — was not met: a strategy that lost to
buy-and-hold inside a class that beat it passed.

### 2. DSR multiplicity used the payload slice, not the search space

`n_trials = len(strat_groups)` counted the distinct cells present in the loaded
3,500-row slice. The live registry is ~658 strategies (`MASTER_AUDIT.md`
2026-11-14: 658 strategies, 682 asset×strategy pairs). Correcting for 45–60
observed cells instead of ~658 under-corrects exactly the way G4 exists to
prevent.

Applied literally to every tier this has a second failure: at 658 trials a
promising-but-unproven cell falls below the `DSR >= 0.50` CANDIDATE floor, so
nothing reaches forward paper — the "one-way ratchet to zero" the review
criticised. The fix therefore splits the correction by tier: **PROVEN_T2 pays the
global null-max (658); CANDIDATE is judged against the bucket width actually
observed.** CANDIDATE means "worth forward paper", not "a discovery".

### 3. Source-family cells skipped every gate

`source_families` were emitted straight from `evaluate_cell()` with no
Benjamini-Hochberg pass, no `_promote()` (FDR/DSR/forward), and no harm gate.
They were the only verdict-bearing bucket that could reach `PROVEN_T2` on raw
statistics alone.

### 4. The forward-observation ledger had no scheduled writer

`reports/forward_observations.jsonl` was filled once by hand (430 H-119 rows,
commit `5c0c42d`) and stopped. `forward_observations_ingest` defaults to a dry
run and no workflow invoked it, so P1-4's "accrues rows" was false in practice —
a ledger that never grows cannot mint a forward-based verdict.

## What changed

| File | Change |
|---|---|
| `alpha_engine/audit3_selection_alpha.py` | Emit `by_strategy` slices keyed `CLASS/STRATEGY/DIRECTION` (same 20-row floor as `by_slice`) |
| `alpha_engine/audit3_tribunal.py` | G8 is scope-aware: only a **strategy-level** measurement proves a strategy cell; a class number is recorded as `class_proxy` and demotes PROVEN_T2. Alpha gate now returns and publishes an `applied/tested/demoted/scopes` summary so an absent sidecar cannot read as "all passed". Added `GLOBAL_TRIAL_FLOOR=658` + `global_trial_count()`; `evaluate_cell()` now takes `n_trials_local`, exposing `dsr` (global, gates PROVEN) and `dsr_local` (bucket width, gates CANDIDATE). Source families now get BH + `_promote` + harm gate. Fixed the stale "2x stress is report-only" comment. |
| `.github/workflows/forward-observations-ingest.yml` | New 6-hourly job (`41 */6 * * *`) running the ingest with `--apply`, committing the ledger, and printing promotion-eligible cells that lack a forward instrument |
| `tests/test_audit3_tribunal.py` | +9 tests: class-proxy demotion, strategy-level acceptance, CANDIDATE flagging, `applied=false` reporting, DSR floor, family gating, report-level gate record |

Scope note: `class_proxy` still **informs** (it is recorded and flagged); it
never proves. When the alpha sidecar is absent entirely the gate stays fail-open
and now says so.

## Verification

```
python3 -m pytest tests/ -k "audit3 or denylist or forward_observations or selection_alpha" -q
# 48 passed
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/forward-observations-ingest.yml'))"
# valid; jobs=['ingest']
```

Manual checks:
- `apply_selection_alpha_gate` demotes a PROVEN_T2 strategy cell whose class
  alpha is +0.5 but whose strategy alpha is −0.6 (`scope=class_proxy`).
- A strategy cell with its own +0.2 CI lower bound keeps PROVEN_T2.
- `global_trial_count(3) == 658`, `global_trial_count(2000) == 2000`.
- A PROVEN_T2 cell with global `dsr=0.40` demotes to CANDIDATE even when its
  local DSR is 0.99; a CANDIDATE in a single-cell bucket is not judged against
  the 658-trial null.
- Pre-existing note: `pytest tests/ -k "audit3 ..."` shows 3 order-dependent
  slippage-test failures that pass when their files run alone. They reproduce
  without these changes (global-constant pollution), so they are recorded, not
  fixed, here.
- `build_report(...)["source_families"][i]["q_value"]` is populated.

## Known remaining gaps (not fixed here)

1. **P0-3 at-issue stamping** — still absent from `audit_trail/pick_schema.py`;
   needs a writer-side change, not a gate change.
2. **Class/symbol alpha only** — symbol cells still have no same-scope alpha
   measurement, so G8 demotes their PROVEN_T2. That is deliberate (fail-closed),
   but a per-symbol alpha would let a genuinely skilled single-name cell prove.
3. **Forward coverage** — only H-119 has a registered forward instrument today;
   the equity-breakout pod has a condition but no rows yet. The new workflow
   prints the promotion-eligible cells that have no forward path, rather than
   inventing shadow trades for them.
