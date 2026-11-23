# D5 — two-hurdle rule shipped as an OPT-IN sidecar, with the blocker named

**Date:** 2026-11-23 · **Backlog:** D5 in `docs/BACKLOG_100_2026-11-23.md`
**Files:** `alpha_engine/two_hurdle_gate.py` (new, sidecar), `tests/test_two_hurdle_gate_sidecar.py` (new, 9 tests)
**Decision:** the rule is implemented and tested but **deliberately not wired into production**, because wiring it changes the verdict on every existing pick. That is an operator decision, not an implementation detail.

---

## The rule

```
Hurdle 1 (cash):   annualised net return on committed capital > 4.32% T-bill
Hurdle 2 (signal): beta-adjusted Jensen-alpha bootstrap CI excludes zero
```

Hurdle 2 is **beta-adjusted**, not a raw paired difference. A raw `strategy − benchmark` is non-zero for any change in beta, so a **1.5× index fund passes it** while adding no information — measured and recorded in `cd44a8cab33`. A zero-variance residual also produced a false significance at float epsilon (2e-16), which the same commit guards.

## Why not wired in

Two reasons, and the second is the real one.

1. **It would change published verdicts.** Every existing pick carries a point PnL, not a return series. Re-gating them is a decision with consequences, not a refactor.
2. **The data does not exist yet.** `gate_pick()` requires a paired `return_series` + `benchmark_series`. Picks today store a single PnL figure. **The blocker is the missing per-pick series, not this module.** Shipping the module and calling the item "done" would hide that.

## Wiring Plan (the Wire-Up Rule's opt-in clause)

| item | value |
|---|---|
| Target caller | `audit_trail/quality_gates.py` → `passes_active_gate(pick)`, as an **additional** check — not a replacement for the blocked-pair rules |
| Function | `two_hurdle_gate(strategy_returns, benchmark_returns)` |
| Prerequisite | pick records must gain `return_series` + `benchmark_series` |
| Expected wire-up | next audit-quality PR **after** that field lands |
| Until then | callable from `tools/` and tests only; imported by no production path |

## The opt-in property is enforced by a test, not by intent

`test_no_production_module_imports_the_sidecar` walks every `.py` under `audit_trail/` and `alpha_engine/` and **fails** if any of them mentions `two_hurdle_gate` (other than the module itself). A sidecar that silently becomes load-bearing is not a sidecar, and this estate has already been burned by a gate that reported success while discarding its input.

## How it was verified

```
python3 -m pytest tests/test_two_hurdle_gate_sidecar.py -q   ->  9 passed
```

| test | property |
|---|---|
| `test_no_production_module_imports_the_sidecar` | opt-in holds today, and fails loudly the day it stops |
| `test_hurdle_constant_is_432bp` | 0.0432 exactly — a 4.31% result must not pass |
| `test_pure_beta_fails_signal_hurdle` | benchmark-as-strategy → `BETA_ONLY_FAIL_HURDLE_2` |
| `test_leveraged_beta_fails_signal_hurdle` | 1.75× beta still fails |
| `test_genuine_alpha_passes` | +12bp/period on a 10bp-vol benchmark → `PASS` |
| `test_missing_series_is_unvettable_not_a_pass` | absence ≠ pass; `UNVETTABLE` |
| `test_unpaired_lengths_are_unvettable` | mismatched series → `UNVETTABLE` |
| `test_gate_pick_does_not_mutate_input` | pure function |
| `test_delegates_to_the_single_pbs_implementation` | no re-derivation; agrees with `tools/` exactly |

That last test exists because two copies of a statistical routine drift — this estate currently has **seven divergent copies** of the hypothesis registry, which is the same failure mode one level up.

## Not done

- The prerequisite field (`return_series` / `benchmark_series` on pick records) is not implemented. Without it the gate cannot run on a live pick at all.
- No production verdict has been re-based on the two-hurdle rule, so **the "0 of 6" headline still rests on the single cash hurdle.** That is a known weakness and it is now documented rather than implied.

Zero capital sanctioned. Paper only. Not investment advice.
