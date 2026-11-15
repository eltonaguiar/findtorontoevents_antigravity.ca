# proof/ — what is proven here (currently: nothing new)

No candidate in this pass was taken through the gate. That is the finding, not an omission.
`proof/` will hold walk-forward outputs, Monte Carlo distributions, significance tests and equity
curves as soon as a candidate reaches stage 2 of its plan.

## What exists today, and where

| Artifact | Path | What it proves |
|---|---|---|
| Per-class gross measurement | `reports/quant_audit/ASSET_CLASS_TRIAGE_2026-11-15.md` | means/medians/WR/PF per class on 3,500 closed picks |
| Excess leg machinery | `tools/pick_excess.py` | excess vs benchmark conventions, clustered t, collapsed-window rule |
| Ledger + interim looks | `tools/forward_tracker.py`, `state/forward_test/plan.json` | pre-registered OF bounds, kill rules, fixed sample (152 windows) |
| Paired bootstrap vs benchmark | `audit_dashboard/data/benchmark_ledger_proof.json`, `audit_dashboard/benchmark_proof.html` | paired bootstrap + random-entry MC on the closed ledger |
| DSR results | `tools/deflated_sharpe_results.json` | 27 of 52 strategies in the DSR noise set |
| Hypothesis harness | `tools/hypothesis_test_harness.py`, `reports/hypothesis_registry.json` | pre-registration + adjudication |

## What is explicitly NOT MEASURED

- **Benchmark-adjusted class performance.** The 3,500-row table is gross. The join exists; it has
  not been run per class. Until it is, no class can be called profitable or unprofitable.
- **1,084 of 3,500 rows (31%).** Same-day windows cannot be benchmarked from daily closes. Their
  excess is unmeasurable by construction, not zero.
- **PBO and White's Reality Check on the current cohort.** Implementations live only in
  `.claude/worktrees/cluster-a-fix-2026-06-21/tools/`. Citing a number from them is not
  reproducible until they are ported to main.
- **Any forward result.** The ledger is empty by design: registration 2026-11-15, no pick has
  closed since. `rs-breakout-scout` is 0/152 windows.

## The rule for this folder

An artifact lands here only if it carries the exact command that regenerates it. A number without
a command is a claim, and claims belong in `Summary.MD` under "not measured".
