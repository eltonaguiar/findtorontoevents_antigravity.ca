# P0: `alpha_engine/audit3_tribunal.py` cannot run on `origin/main`

**Author:** Buffy · **Date:** 2026-11-19 · **Severity:** P0 — blocks every tribunal run from main
**Status:** reproduced on a pristine checkout **with no patch applied**, so this is not
caused by my sleeve-PF work.

## What happens

```
$ git worktree add --detach /tmp/pristine origin/main   # no edits, no patch
$ python3 -m alpha_engine.audit3_tribunal --picks /tmp/pf_picks.json --out /tmp/r.json
argparse.ArgumentError: argument --history: conflicting option string: --history
```

Two independent defects, both present on `origin/main`:

1. **Duplicate argparse registration.** `--history` is added twice. Argument parsing dies
   before a single row is read, so *nothing* downstream can execute.
2. **Undefined names in `evaluate_cell`.** Line ~964 builds the cell dict with
   `"required_n": required_n` and `"mde_pct": mde_pct`, but neither name is assigned
   anywhere in the file on main:

   - `required_n` assignments on `origin/main`: **0**
   - `mde_pct` assignments on `origin/main`: **0**

   Commit `1ed98e59aaa feat(audit3): per-cell required_n and MDE (power) in the ledger`
   introduced both. The later merge `764fec86df2 feat(audit3): merge vanilla N-gates +
   deploy /audit2 page + refresh ledger` dropped the definitions while keeping the uses —
   a classic bad-merge that leaves the code referencing names it no longer defines.

## Why it matters

The `/audit3` ledger published at 22:47Z tonight reports `n_rows=8632`, `n_proven=0` and a
per-class `required_n` field. Those numbers cannot be produced by this file as it sits on
main. So either:

- the deployed ledger was built from a **different commit** than main (a provenance gap —
  the surface is not reproducible from the branch it claims to come from), or
- the workflow pins a stale ref.

Either way, **no one can reproduce tonight's ledger from main**, which breaks the one
invariant this fleet keeps insisting on: every number re-derivable from a committed
artifact.

## The definitions that went missing

From `1ed98e59aaa`:

```python
    required_n = None
    mde_pct = None
    required_n = int(math.ceil((2.8 * sd / abs(mean_net)) ** 2))
    mde_pct = round(2.8 * sd / math.sqrt(n), 4)
```

## Fix (small, but it belongs to the owner of the merge)

1. Delete the **second** `ap.add_argument("--history", ...)` registration.
2. Restore the `required_n` / `mde_pct` computation shown above, immediately before the
   `out = dict(label)` cell construction in `evaluate_cell`.
3. Add a regression test that simply **runs the module** (`--help` plus one tiny picks
   file). A duplicate argparse flag and two undefined names would both have been caught by
   a three-line smoke test. That is the real defect: the suite does not execute the CLI.

I am not applying this myself: `audit3_tribunal.py` is a claimed hot shared file, three
agents are editing it, and unilaterally changing main's grading code during a merge freeze
is exactly the collision the protocol exists to prevent.

## Consequence for the sleeve PF gate

The gate **cannot be verified on main** while main cannot parse its own arguments. It was
verified on `fix/sleeve-implausible-pf-2026-11-19`, where the surrounding code runs:
`FANTASY` pf 155.85 → `implausible=True, rankable=False`;
`REAL_ONE` pf 1.05, n=50 → `rankable=True`; `TINY` n=5 → `rankable=False`.
Replay of the patch onto main additionally surfaced three branch-drift defects (duplicate
`--history`, missing `--sleeves`/`--benchmark` flags, a foreign `require_alpha=` kwarg).
Any replay must land **after** the P0 above is repaired.
