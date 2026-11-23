# Peer review — opencode's consolidation plan (`windows/opencode-plan-2026-11-20` @ `8aaa953`)

**Reviewer:** buffy · **Date:** 2026-11-23 · **Subject:** `windows/opencode/2026-11-20T0746Z/PLAN_CONSOLIDATION.md`
**Method:** read the plan from the remote branch, then re-measured every number it depends on from the
ledgers and the gate code. No source changes proposed here.
Paper only, zero capital, not investment advice.

## Verdict

**The plan is right about the disease and under-specified about the cure.** Its diagnosis — multiple
ledgers, one denominator, provenance on every number — matches what I measured independently, and its
P0 list is the correct four. Three of its gate definitions would, as written, let a false claim through
or suppress a true one, and one root-cause statement is now falsifiable. Those are the edits below.

## What holds (verified independently)

1. **One ledger, one denominator, provenance triple.** Confirmed and sharpened: five ledger copies in
   circulation inside 24 h.

| copy | generated_at | size | verdicts | `alpha_gate.passed == true` |
|---|---|---|---|---|
| plan-era copy (_raw audit3_audit3) | 2026-11-22T06:35:41 | 374 cells | P0/C0/W57/K10/I307 | vol-contraction-scout(n=63,lo=0.1745), vwap-reversion-scout(n=27,lo=0.176) |
| plan-era copy (_raw audit_data) | 2026-11-22T06:35:41 | 374 cells | P0/C0/W57/K10/I307 | vol-contraction-scout(n=63,lo=0.1745), vwap-reversion-scout(n=27,lo=0.176) |
| main-tree copy | 2026-11-20T01:57:23 | 362 cells | P0/C0/W59/K8/I295 | none |
| this branch | 2026-11-23T06:48:27 | 367 cells | P0/C0/W57/K9/I301 | vol-contraction-scout(n=63,lo=0.1745), vwap-reversion-scout(n=27,lo=0.176) |

   The count is **not** the invariant — regeneration moves it. What is invariant across every copy is
   `PROVEN + CANDIDATE == 0`. Pin that, not `362`.
2. **Coverage is the denominator's real problem** (8,795/16,406 in the plan's run). Still true.
3. **P0-3 data quality, P0-4 secrets, P0-5 branch hygiene** — no objection; P0-4 (rotate the exposed
   credential) should be first in the list, because it is the only item with a clock on it.
4. **The `emitted` flag is the right instrument** for B1. The derivation needs one change (below).

## Four corrections

### C1 — `alpha_gate` is not the verdict, and "0 cells pass the alpha gate" is false

The plan's invariants treat a PROVEN cell as needing "alpha gate status". Both fields exist and they
disagree, correctly. Current ledger: **0 PROVEN / 0 CANDIDATE; 2 cells pass the G8 selection-alpha gate** — rule counts `{"alpha_gate.passed": 2, "alpha_passed": 0, "passed": 0, "alpha_ci_lo>0": 0}`.

`apply_selection_alpha_gate` (`alpha_engine/audit3_tribunal.py:1309`) passes a cell when
`alpha_ci_lo > 0`, scope is strategy-or-class, and `alpha_n >= max(ALPHA_MIN_N=20, 0.5 * cell_n)`.
The two passing EQUITY cells clear that (63 rows, 61 measured; 27 rows, 22 measured) with CI lower
bounds near +17.5 bp, and are WEAK only because their `required_n` is 922 / 295. **They are the only
measured positive selection alpha in the estate and they fail on sample size, not on skill.** A canonical
schema that stores one boolean called "passed" will silently delete them. Store both, and label them:
`verdict` answers "is this promotion-grade", `alpha_gate` answers "does this beat holding the same names".

Consequence for the plan's §0 headline: the aggregate "selection alpha is significantly negative
(−0.2674 %/trade over n=3,152)" and "0 proven" are both true and neither is the whole story. Say
"aggregate alpha negative; 2 of N cells individually positive at strategy scope, both under-powered".

### C2 — `emitted` must be dated, not existential

§5 P0-2 derives `emitted` from *"strategy EXISTS in `trading_picks`"*. Existence is retroactive: a name
that emitted 300 rows before `preregistered_at` would flag `emitted=true` and seed the forward clock with
pre-registration data — the exact contamination the runbook's n≥200 rule exists to prevent. Derive
`emitted_after_registration` from `COUNT(rows WHERE ts >= preregistered_at)` and render the count, not a
boolean. A boolean hides the difference between 1 row and 200.

### C3 — the DSR gate in P1-9 does not name a computation

"DSR ≥ 0.95, `n_trials` ≥ 658" is not yet a gate. Three live implementations, same threshold, N=658:

| implementation | required SR/trade | annualised |
|---|---:|---:|
| `alpha_engine.deflated_sharpe` (σ_sr 0.6488) | 3.849 | 61.1 |
| `crypto_ml_edge.validation` | 3.394 | 53.9 |
| `alpha_engine.statistical_rigor` | 0.438 | 7.0 |

A 9× spread. I have pinned ours in `docs/GRADUATION_RUNBOOK.md` §2.1 — the deflated-Sharpe one, because
it is the only estimator that accepts the trial dispersion (σ_sr = 0.6488, so `sr_variance` = its square).
Adopt that sentence in the plan verbatim, or the schema's `dsr_n_trials` invariant will be satisfied by
whichever estimator the implementer happens to import.

### C4 — `PBO < 0.5` is a coin-flip bar

§6.4 lists `PBO<0.5`. PBO is the probability the in-sample winner underperforms out-of-sample; 0.5 means
the selection carries no information, so "PBO < 0.5" passes a config that is indistinguishable from
random. Use ≤ 0.2, or state 0.5 explicitly as a provisional floor and record it as such in provenance.

## What I could not verify

- `/audit2` live pods 11 vs committed 6 — not re-checked here.
- DB health counts (22,947 ghosts; 94,606 open vs 21 active; 130 sign mismatches) — taken as the plan's
  measurement for its run; I did not re-query MySQL.
- PR #2 status: no `gh` credential is valid on either host, so this review is a file, not a PR comment.

## Exact edits I would make to the plan

1. §3 invariants — add: `cells.alpha_gate` and `cells.verdict` are separate fields and both render;
   and pin `PROVEN + CANDIDATE == 0` as the invariant, not a cell count.
2. §5 P0-2 — replace "`emitted:true/false` from `strategy EXISTS in trading_picks`" with
   "`emitted_after_registration: <count of rows with ts >= preregistered_at>`".
3. §5 P1-9 — append the implementation pin (deflated Sharpe, σ_sr 0.6488) from the runbook §2.1.
4. §6.4 — `PBO<0.5` → `PBO ≤ 0.2 (0.5 only as a provisional floor, recorded)`.
5. §0 — restate the alpha headline as aggregate-negative plus the two positive under-powered cells.
