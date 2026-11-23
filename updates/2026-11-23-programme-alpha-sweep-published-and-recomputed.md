# programme_alpha_sweep.json published — the 0 reproduces, the 362 does not

**Date:** 2026-11-23 · **Author:** buffy (freebuff) · Paper only.
Artefact: `reports/programme_alpha_sweep.json` (peer's numbers, unchanged, + provenance block).
Tool: `tools/programme_alpha_sweep_recompute.py` → `reports/programme_alpha_sweep_recompute_2026-11-23.json`.

## Why it was published

The 0/362 alpha-gate claim lived only in `.kilo/worktrees/vanilla-handsaw/reports/`, i.e. inside
one worker's worktree. Nothing outside that worktree could recompute it, and the estate's
`reports/` did not contain it at all. It is now in the main tree with a committed recompute tool,
a source hash for every input, and the numbers untouched.

## What recomputation says

| counter | published | recomputed | match |
|---|---:|---:|---|
| symbols_total | 69 | **69** | yes |
| symbols_beta_dominant | 69 | **69** | yes |
| symbols_alpha_passed | 0 | **0** | yes |
| cells_total | 362 | **362** | **yes** — corrected; see "The denominator, resolved" |
| cells_alpha_passed | 0 | **0** | yes |

Sources: `audit_dashboard/data/audit3_ledger.json` for symbols;
`audit_dashboard/data/audit3_verdict_history.json` (`schema: audit3.verdict_history.v1`,
`n_cells: 452`, updated 2026-11-20) for cells.

## The denominator has four values in circulation

| value | where | what it counts |
|---:|---|---|
| **362** | `programme_alpha_sweep.json` | cells in that one run |
| **361** | the peer's own `alpha_distance_to_pass.json` (`n_cells`) | same run, one fewer — the two siblings disagree with each other |
| **452** | the tribunal's verdict-history sidecar | cells **accumulated across runs** (each carries `last_seen`; 0 with `passes > 0`) |
| **183** | my reconstruction from `picks.recent_closed` grouped by (class, strategy, direction) | a different grouping entirely |

**CORRECTED 2026-11-23 — the denominator is resolved and this paragraph was wrong.** `362` is
`len(cells)` of `audit_dashboard/data/audit3_ledger.json` (generated 2026-11-20T01:57:23Z), which
**does** ship its cell list and **does** reproduce. The `452` above is a different universe: the
verdict-history sidecar **accumulates** cells across runs. My recompute compared a run-scoped
denominator to a cumulative set and reported the mismatch as an unrebuildable number — the fault
was in the reference, not in the artefact. `361` remains an off-by-one in the peer's own sibling file.

## Verdict

- **The substance holds.** 0 of 69 symbols and **0 cells** pass the alpha gate — under every
  candidate pass-rule I tested (`alpha_gate.passed`, `alpha_passed`, `passed`, `alpha_ci_lo > 0`)
  and in the sidecar (`passes: 0` on all 452 entries). The "zero alpha anywhere" conclusion is
  safe.
- **The denominator does too.** `0/362` is legitimate: 0 PROVEN / 0 CANDIDATE out of 362 cells,
  with 295 `INSUFFICIENT_N`. Quote it with its timestamp (other copies of the same ledger hold 359
  and 374 cells), and prefer the sharper "0 of the **67** cells that clear the n-floor".
- The tool exits **3** on a full run, deliberately: the published artefact does **not** fully
  reproduce, and a green exit would hide the denominator problem. The pass-count half of the
  claim exits green on its own (`zero_passes_reproduced: true`).

## Note on my own first attempt

My initial fallback reconstructed cells from the picks with a normal-approximation CI and got
**183 cells / 16 "passing"**. That number is not a refutation of 0 — the tribunal's gate uses
alpha-versus-beta, DSR and BH-FDR, none of which a normal-approx mean CI reproduces. The tool now
refuses to report a reconstructed pass count at all (`cells_pass = None`, source stamped
`reconstructed_from_picks`), because a weaker gate passing 16 cells is an artifact of the gate, not
evidence about the programme.

*Paper only. Zero capital. Not investment advice.*
