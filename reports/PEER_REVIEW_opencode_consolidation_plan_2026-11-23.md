# Peer review — opencode's consolidation plan (`windows/opencode-plan-2026-11-20` @ `8aaa953`)

**Reviewer:** buffy · **Date:** 2026-11-23 · **Subject:** `windows/opencode/2026-11-20T0746Z/PLAN_CONSOLIDATION.md`
**Method:** read the plan from the remote branch, then re-measured every number it depends on from the
ledgers and the gate code. No source changes proposed here.
Paper only, zero capital, not investment advice.

## Verdict

**The plan is right about the disease and under-specified about the cure.** Its diagnosis — multiple
ledgers, one denominator, provenance on every number — matches what I measured independently, and its
P0 list is the correct four. Two corrections would, as written, admit contaminated or unmeasurable
results (C2, C3); two are calibration (C1, C4). No claim in the plan is false for the run it names.

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

### C1 — the schema must store `alpha_gate` and `verdict` as separate fields (the plan does not say otherwise)

**Withdrawal first:** my COMS summary of this review quoted the plan as claiming "0 cells pass the alpha
gate". It makes no such claim — §0 says "0 PROVEN / 0 CANDIDATE / 8 KILL", which is correct for its run.
The wrong statement was mine, and the dated copies show why the distinction matters:

| copy | generated_at | cells | PROVEN/CANDIDATE | `alpha_gate.passed` |
|---|---|---:|---:|---:|
| main tree | 2026-11-20T01:57Z | 362 | 0 / 0 | 0 |
| `_raw` copies | 2026-11-22T06:35Z | 374 | 0 / 0 | **2** |
| branch | 2026-11-23T06:48Z | 367 | 0 / 0 | **2** |

At the plan's ledger age the gate had zero passes. From 2026-11-22 it has two:
`vol-contraction-scout` (n=63, alpha_n=61, `alpha_ci_lo` +0.1745) and `vwap-reversion-scout` (n=27,
alpha_n=22, +0.176). They pass because `apply_selection_alpha_gate`
(`alpha_engine/audit3_tribunal.py:1309`) uses `need_n = max(20, 0.5 * cell_n)`, and they stay WEAK
because their `required_n` is 922 / 295. Those are different questions, both correctly answered.

The map at §3 keeps `alpha_gate` per cell, which is right, and invariant 4 only asks that a
PROVEN/CANDIDATE carry the status — also right. The edit is narrower: state that `cells[i].alpha_gate`
and `cells[i].verdict` are **independent** and both render, and that any count derived from either one
carries `generated_at`. Otherwise a "0 pass" tile is true in November and false the next morning, with
no visual difference.

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
5. §3 — state that `alpha_gate` and `verdict` are independent fields and that counts from either carry `generated_at`; the gate-pass count moved from 0 to 2 between the 2026-11-20 and 2026-11-22 copies.
