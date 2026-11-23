# T3 — the live emit did NOT happen. Three independent reasons, all silent.

**Date:** 2026-11-23
**Run:** `45086985710` on `main` at `4e1adc252` — **status `completed/success`**, 00:43:33Z
**Result:** `reports/provenance/picks_provenance.jsonl` is **ABSENT on origin/main**
**Status:** T3 stays **OPEN**. A green check mark does not mean the feature worked.

---

## The headline

The job reported success. The thing the job exists to do did not happen. The reason it
looked fine is that the provenance write is wrapped in a **`non-fatal`** handler, so the
failure was printed as an informational line and the process exited 0.

This is the exact failure mode the provenance work was built to prevent: a number that
looks present but is not. Here it happened to the instrument itself.

## Three independent defects

### 1. The emit never ran — import failure

```
[PROVENANCE] skipped (non-fatal): No module named 'provenance_ledger'
```

The module exists on `main` at this very commit
(`git cat-file -e 4e1adc252:tools/provenance_ledger.py` → present), it is tracked, not
gitignored, and `alpha_engine/provenance_hook.py` at that commit contains the
`sys.path` guard that should make it importable. Locally the identical call path works —
a real pick writes `seq=1` and advances the chain head.

So the code is right and the **CI environment differs from the source tree in a way I
have not yet isolated**. Not guessable — it needs someone to reproduce inside the runner.

**This is not a one-off.** The same log carries a companion failure for a repo-root
package that has **125 tracked files**:

```
[SHADOW] Sizing override enforcement skipped (non-fatal): No module named 'audit_trail'
```

Two different imports, both of things that provably exist in the checkout, both reported
as missing. That points at one shared cause — `sys.path` in the runner — not at two
missing files.

### 2. Even with imports fixed, this cycle would have emitted ZERO rows

The scan did generate picks early on, but they did not survive to the write point:

```
[VALIDATE] Loading active picks...  34 active picks across 27 symbols
[4-TIER-CB] T4 HALT: clearing all 0 active picks -- manual review required to resume
[KILL LIST ENFORCEMENT] All 0 picks passed (748 strategies on kill list)
[WRITE] premium_signals.json  (0 signals: 0 HIGH / 0 MED / 0 WATCH)
```

By section 6y, `active` was empty. `emit_picks([])` writes nothing, by design. So even a
perfect import fix yields `n_records = 0` on this cycle, and T3's acceptance criterion
(> 0) would still not be met.

### 3. The workflow could never publish the ledger anyway — **this is the decisive one**

`alpha-engine-fast.yml:64`:

```yaml
git add alpha_engine/data/active_picks_fast.json alpha_engine/data/closed_picks_fast.json
```

That is the complete `git add`. **`reports/provenance/` appears nowhere in the
workflow.** There is no step that stages `picks_provenance.jsonl`, no step that runs
`provenance_ledger.py`, and no `workflow_run` hand-off that would let
`provenance-verify.yml` see it.

So even with (1) and (2) both fixed, the ledger would be written into the runner's
ephemeral filesystem and **thrown away when the job ends**. T3 as specified — "a run
produces `picks_provenance.jsonl` with `n_records > 0` **on main**" — cannot pass until
the workflow commits that path.

## What this means

The previous session's acceptance claim rested on code existing and unit tests passing.
Those were true. What was never done was **end-to-end verification that the emit reaches
a destination anyone can read.** The Wire-Up Rule catches a module with no caller; this is
its harder sibling — a module with a caller that is *switched off*, in a step whose
success is not checked.

Between merge (00:06Z) and now, every `alpha-engine-fast` run has silently recorded
nothing while reporting green.

## Fix list (not done here — recorded so it is not lost)

1. `alpha-engine-fast.yml`: stage `reports/provenance/picks_provenance.jsonl` in the
   commit step, and **fail the job** if provenance was skipped. A non-fatal provenance
   skip is precisely the state we must not ship.
2. Find the real CI `sys.path` cause. Treat `audit_trail` and `provenance_ledger`
   failing together as one bug, and reproduce inside the runner rather than locally.
3. Decide whether a zero-pick cycle is acceptable. If the 4-tier circuit breaker zeroes
   the book often, "> 0 records" is a flaky acceptance criterion and needs a defined
   observation window instead.

## Cleanup performed

While diagnosing, my reproduction call wrote a real record into the live ledger path —
`{"strategy": "test", "source_system": "repro"}` at `seq=1` with a zero chain head. Left
in place it would have poisoned the chain (a synthetic record at the root, and every
subsequent `prev_sha256` chaining from it).

Deleted immediately. `provenance_ledger.py --stats` confirms `n_emitted: 0` and
`git status reports/provenance/` is clean.

This is worth stating plainly: diagnostics that write to production artifacts need to be
run against a temp path. I got that wrong here and caught it before it committed.

Zero capital sanctioned. Not investment advice.
