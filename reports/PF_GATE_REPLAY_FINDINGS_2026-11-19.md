# Replaying the sleeve PF gate onto current main — findings

**Author:** Buffy · **Date:** 2026-11-19 · **Requested:** apply the PF-gate patch to main and
confirm implausible sleeves still come out `rankable=False`

## Verdict: cannot be verified on main, because main does not run

The patch applies with conflicts and then the module fails **before the gate can be
exercised**. Worse — and this is the finding that matters more than my patch — **a pristine
`origin/main` checkout fails too, with no patch applied at all.**

Reproduced on an untouched worktree at `origin/main`, fixtures only, nothing edited:

```
$ git worktree add --detach /tmp/pristine origin/main      # HEAD 034a6a4f378
$ python3 -m alpha_engine.audit3_tribunal --picks /tmp/pf_picks.json --out /tmp/r.json
argparse.ArgumentError: argument --history: conflicting option string: --history
pristine rc=1
```

**`alpha_engine/audit3_tribunal.py` on main cannot start.** Two independent pre-existing
defects, both reproduced without any change of mine:

| # | Defect | Evidence on `origin/main` | Consequence |
|---|---|---|---|
| 1 | `--history` registered twice | `argparse.ArgumentError: conflicting option string: --history` at `main()` | module aborts at parse time — **nothing runs** |
| 2 | `required_n` and `mde_pct` used but never assigned | `grep -c required_n` → **1** (only the use at line 964); `mde_pct` appears **once**, at line 965, also only as a use | `NameError: name 'required_n' is not defined` in `evaluate_cell` |

`git log -S'required_n ='` shows the definition was **added** by
`1ed98e59aaa feat(audit3): per-cell required_n and MDE (power) in the ledger` and then
**removed** by `764fec86df2 feat(audit3): merge vanilla N-gates + deploy /audit2 page +
refresh ledger`. A merge dropped an assignment that a later line still consumes.

## Is this a live outage?

Not necessarily — and that is its own warning. A fresh ledger exists with
`source_generated_at 2026-11-19T21:55:00Z`, so **whatever produces the live ledger is not
main's copy of this file.** Either the workflow runs a pinned ref, a server-side copy, or
a different generator. Two possibilities, both bad:

- the live ledger is produced by code nobody is reviewing on main, or
- main's tribunal is broken and the next run from main will produce nothing.

Someone who owns the ledger workflow should say which. I am not editing that path.

## What my patch itself got wrong (four drift defects)

My branch was cut from opencode's branch, 1,555 commits behind main, so its diff carries
assumptions main no longer satisfies. All four surfaced only by *running* it:

1. **Foreign kwarg.** The patch's call site passes `require_alpha=` to `build_report()`,
   which main's signature does not accept → `TypeError`. That kwarg is opencode's
   feature, not mine; it has no business in this patch.
2. **Missing flags.** The patch's sleeve block reads `args.sleeves` and `args.benchmark`,
   but main registers neither → `unrecognized arguments: --sleeves`.
3. **Duplicate `--history`** — came along with the replayed block, on top of main's own
   duplicate.
4. **`required_n` / `mde_pct`** — consumed by the replayed cell-dict, undefined on main.

Defects 1 and 2 are mine to own: I shipped a patch whose entry points I had only tested on
the branch where they already existed. Defects 3 and 4 are main's.

## What *is* verified

On `fix/sleeve-implausible-pf-2026-11-19` (the branch where the surrounding code runs),
the gate behaves correctly:

| sleeve | pf | class_pf | implausible | rankable |
|---|---:|---:|---|---|
| FANTASY | 155.85 | 1.0 | **True** | **False** |
| REAL_ONE | 1.05 | 1.0 | False | **True** |
| TINY (n=5) | 1.20 | 1.0 | False | **False** (below n floor 30) |

So the *logic* holds. What does **not** hold is that it can be dropped onto today's main.

## Recommendation

Do not merge the sleeve patch onto main as-is. In order:

1. **Fix main first.** Remove the duplicate `--history` registration and restore the
   `required_n` / `mde_pct` assignments. Until then the tribunal cannot run, and any
   claim about ledger contents from main's code is unverifiable.
2. **Re-implement the gate natively** on the fixed main — roughly 45 lines inside whatever
   sleeve-ingestion block exists there, not a 137-line replay carrying foreign kwarg and
   flag assumptions.
3. Keep my branch as the **reference implementation and its test**, not as the merge unit.

`reports/patches/2026-11-19-sleeve-implausible-pf.patch` is regenerated from the originally
tested commit (`d9d5829`), so it is a faithful diff of the change — not of my ad-hoc repairs.
It is still branch-base-relative and needs relocation. Treat it as documentation of intent.
