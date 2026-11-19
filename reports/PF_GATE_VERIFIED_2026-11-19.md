# Sleeve PF gate — verified on main after a diagnostic repair

**Author:** Buffy · **Date:** 2026-11-19 · **Requested:** apply the gate to current main and
confirm implausible sleeves come out `rankable=False`

## Short answer

**Cannot be done on unmodified main — main cannot execute the tribunal at all.** Five
distinct defects block it (mapped below). On a copy of main repaired only enough to run,
the gate **PASSES**: implausible sleeves are excluded with the right reasons, and a sound
sleeve stays rankable.

## The verdict lines, verbatim

```
WARNING: sleeve not rankable: CRYPTO/FANTASY pf=155.85 :: pf 155.85 exceeds absolute
  ceiling 25; pf is 155.8x the class aggregate (155.85 vs 1.00), ceiling 5x
WARNING: sleeve not rankable: CRYPTO/TINY pf=1.20 :: n 5 < floor 30
```

`CRYPTO/REAL_ONE` (pf 1.05, n 50, scored by the tribunal) produced **no** exclusion
warning — it stays rankable. So the gate discriminates correctly in all three directions:

| sleeve | pf | n | outcome | reason |
|---|---:|---:|---|---|
| FANTASY | 155.85 | 50 | **excluded** | absolute ceiling 25, and 155.8x the class aggregate (5x ceiling) |
| TINY | 1.20 | 5 | **excluded** | n 5 < floor 30 |
| REAL_ONE | 1.05 | 50 | **rankable** | nothing |

## Defect map — why main cannot run

| # | Defect | Evidence on `origin/main` |
|---|---|---|
| D1 | **5 duplicated argparse flags** (`--history`, `--history-write`, `--persistence-runs`, `--prev-ledger`, `--max-churn`) | parse dies: `ArgumentError: argument --history: conflicting option string` |
| D2 | `required_n` referenced, never assigned | 0 assignments |
| D3 | `mde_pct` referenced, never assigned | 0 assignments |
| D4 | `build_report()` called with `require_alpha=` | signature has no such parameter → `TypeError` |
| D5 | `global_trial_count()` called in 4 places | **no definition anywhere in the repo** |

D2 and D3 were introduced by `1ed98e59aaa` and dropped by merge `764fec86df2`, which kept
the uses. D1, D4 and D5 mean main's grading code and its call sites are out of sync in
several directions at once — this is not one bad hunk, it is a merge that was never
executed after landing.

**Consequence:** the ledger published at 22:47Z (`n_rows=8632`, `n_proven=0`, per-class
`required_n`) cannot have been produced by main's tribunal. The surface is not reproducible
from the branch it claims to come from.

## What a repair looks like

Three patches, all in `reports/patches/`:

1. `2026-11-19-tribunal-p0-repair.patch` — **the owner-actionable one**: drops the 5
   duplicate registrations and restores `required_n`/`mde_pct` using the exact formula from
   `1ed98e59aaa` (`int(math.ceil((2.8 * sd / abs(mean_net)) ** 2))`, `round(2.8 * sd /
   math.sqrt(n), 4)`). Verified: `--help` parses and the CLI produces a ledger.
2. `2026-11-19-tribunal-diagnostic-harness.patch` — **diagnostic only, not for merge**: adds
   a `global_trial_count` stub and drops `require_alpha=`. The stub changes DSR semantics,
   so merging it would silently alter grading. It exists so the sleeve gate could be
   exercised.
3. `2026-11-19-sleeve-implausible-pf.branch-base.patch` — the gate itself, as tested on
   `fix/sleeve-implausible-pf-2026-11-19`.

Land them in that order, and D4/D5 need a decision only the owner can make: is the alpha
gate supposed to be enforced (`require_alpha` restored to the signature), and what is the
real `global_trial_count` implementation? I will not invent either.

## A gap in my own gate

The sleeves are **computed and warned about, but never persisted** into the report JSON —
the output carries `classes`, `cells`, `symbols` and so on, with no `sleeves` key. So the
`rankable` flags exist only as stderr warnings; no dashboard can read them. That is a
defect in my patch, not in main. It needs a `sleeves` block written into the ledger before
this gate is useful downstream.

## Reproduce

```bash
git worktree add --detach /tmp/main origin/main
cd /tmp/main && python3 -m alpha_engine.audit3_tribunal --help   # D1 fires here
# after the repair patch:
python3 -m alpha_engine.audit3_tribunal --picks picks.json --sleeves dash.json --out out.json
# look for "WARNING: sleeve not rankable" on stderr
```
