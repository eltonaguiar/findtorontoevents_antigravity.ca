# HERMES_WIN_inspect-wt — Repo Mining, Failure Diagnosis & Profitability Plan

**Created:** 2026-11-15 07:08 UTC · **Worktree:** `inspect-wt` · **Branch target:** `main` under `WIRED_IN/`

This package is the output of a repository-archaeology pass over `findtorontoevents_antigravity.ca`, written under the assumption that **the most valuable thing we own is a rigorous negative result**, not another optimistic backtest.

## Start here

1. **`Summary.MD`** — living document: what was done, what was found, what happens next.
2. **`harvested_ideas/03_negative_result_diagnosis.md`** — the classification matrix. Which candidate died at which hurdle, and what each failure permits next.
3. **`proof/PROOF_PROTOCOL.md`** — the 10-step standard. Nothing is called profitable without passing all ten.
4. **`Plan/`** — one pre-registered hypothesis per asset class, each written *before* any code.
5. **`tracker/`** — forward-testing schema; every live pick must map to a `run_id`.
6. **`Questions/`** — the canonical question list agents must answer, plus the multi-perspective metric thresholds.

## Layout

```
Summary.MD                      living document
harvested_ideas/
  00_inventory.csv              30 strategies, cited to file paths
  01_failures_taxonomy.md       10 failure modes, verdicts
  02_methods_catalogue.md       what's already been tried (and the real gaps)
  03_negative_result_diagnosis.md   decision rule + classification matrix + pivots
Plan/<asset_class>/PLAN.md      pre-registered hypotheses (9 classes)
experiments/README.md           frozen-config run protocol
tracker/                        predictions_tracker.csv + scoring rules
proof/PROOF_PROTOCOL.md         10-step standard
Questions/                      questions + metrics + turnaround playbook
```

## The one-paragraph finding

Across ~30 catalogued strategy families and nine asset classes, **zero** candidates survive the full proof standard. The recurring killers are (a) look-ahead leaks in feature pipelines, (b) walk-forward parameter drift, and (c) friction that eats an edge that was real in-sample. Three candidates are near-misses that fail *only* on sample size or cost margin — those are worth paper-trading, nothing else is. Prediction-market copy-trading fails structurally (zero-sum + adverse selection + fees), not from bad implementation.

## Rules this package enforces

- No strategy is "profitable" without passing all 10 proof steps.
- No parameter change after seeing results — that's a new hypothesis and a new `run_id`.
- No deleting failed runs. The negative results are the deliverable.
- Every pick carries its benchmark, fees and slippage at write time.

## Reproduction

All numbers cited here come from repo files; each row in `00_inventory.csv` and `01_failures_taxonomy.md` names its source path. To verify a claim, open the cited file. No external data was invented.
