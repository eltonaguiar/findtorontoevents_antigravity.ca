# final_v3 review (all three copies in this bundle)

## What exists locally (copied into this bundle)
| Source copy | Path in bundle | File count (observed) | Notes |
|---|---|---:|---|
| Main repo `/final_v3` | `01-final_v3-review/main-repo/` | 46 | Includes `00_common_themes/`, `01_plan/`, `02_subq/`, `03_focus/`, `05_evidence/` (text/JSON snippets), `childlike-airport/`, `feat-stop-fill-cost-gate-final-v3/`, `quant-audit-2026-11-14/` |
| Finpredict worktree `.../finpredict/final_v3` | `01-final_v3-review/finpredict-worktree/` | 6 | Smaller bundle: `finpredict/{README,PLAN,FOCUS_DECISION,subq/*}` |
| Hilarious-seer worktree `.../hilarious-seer/final_v3` | `01-final_v3-review/hilarious-seer-worktree/` | 39 | Includes `00_common_themes/`, `01_plan/`, `02_subq/`, `03_focus/`, `05_evidence/`, `finpredict/*`, `hilarious-seer/*`, plus `quant-audit-2026-11-14/*` variants in that tree |

## Cross-cutting themes visible in `main-repo/00_common_themes/` (read summary)
From `BUGS.md` and `DEEP_INVESTIGATION.md` (main repo copy):
- **TP vs SL ordering / bar-close assumptions** (CLASSIC bug class): intrabar path can be wrong if resolved by end-of-bar; short-side stop logic gaps noted conceptually in earlier audits — `final_v3` evidence files (`stop_fill_*`) suggest stop-fill replay work happened (JSON/text present). This is consistent with prior `scratch-hippodraco.MD` notes about TP-before-SL inflation risk.
- **Costs / friction ignored** in parts of the pipeline (general fixes plan files reference cost gates). `tools/per_class_cost_gate.py` and `tools/stop_fill_replay.py` appear in the **last-24h modified** list below — suggesting active iteration after/during final_v3 packaging.
- **Data integrity / survivorship / zombie picks** themes recur in deep investigation docs (aligns with prior v2/v4 conclusions).
- **Mutual funds / “subset” focus**: `03_focus/MUTUAL_FUNDS_SUBSET.md`, `feat-stop-fill-cost-gate-final-v3/03-focus/MUTUAL_FUND_SCREEN.md` show MF considered as a focus subset in some branches — but **production reality** per prior audits was “not built / prototype only” in the main product path. Any MF profitability claims must be gated by the same Charter + real NAV/EOD pipeline rules.

## Notable plan files (main repo copy)
- `01_plan/BACKTEST_SIMULATIONS.md`, `GENERAL_FIXES.md`, `GITHUB_ACTIONS_FIXES.md`, `ASSET_CLASS_FIXES.md`
- `feat-stop-fill-cost-gate-final-v3/*` — cohesive track: cost gates, stop-fill replay, focus decision, mutual fund screen (reads like an implementation-oriented branch bundle)
- `childlike-airport/*` under `final_v3/childlike-airport/` — peer-named folder with themes/improvement/subq/focus/backtest/evidence subdirs

## What this means for “final review”
- `final_v3` is **not a single canonical artifact**: three different snapshots exist (main repo, finpredict worktree, hilarious-seer worktree) with overlap and divergence (e.g. hilarious-seer copy includes extra `hilarious-seer/*` and `quant-audit-2026-11-14/*` blocks not identical in structure to main). A true “final” must state which snapshot is authoritative or reconcile differences explicitly.
- Evidence files under `05_evidence/` (replay JSON/txt, cost gate reports) are valuable inputs but should be **re-run or timestamped** against current code — especially because `tools/stop_fill_replay.py`, `audit_trail/stop_fill.py`, `tools/per_class_cost_gate.py` were modified **2026-11-14** (see `02-uncommitted-last24h/`).
