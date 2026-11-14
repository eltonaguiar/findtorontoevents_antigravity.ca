# 02 — Local Uncommitted / Last-24h Review (Prediction-Relevant)

**Snapshot:** worktree dirty (1 tracked mod, many untracked). No cleanup performed.

## Tracked Modification
| Path | Relevance | Note |
|---|---|---|
| `___HELL_HEALTH_OPENCODE.MD` | Health context | Exclude from prediction commits. |

## Untracked — Prediction-Relevant
| Path | Why it matters | Action |
|---|---|---|
| `alpha_engine/data/mutual_fund_metadata.csv`, `mutual_fund_ranker.py`, `fund_holdings_deriver.py` | Low-cap/low-fee MF subset & ranking infra | Validate provenance, test, wire to `MUTUAL_FUND` via clean branch |
| `audit_trail/{compound_overlap_aware,integrity_gates,ledger_gates}.py` | Integrity/overlap/ledger gating | Audit, test — P0 candidates |
| `audit_dashboard/data/*mf*`, `mutual-funds.html` | MF rankings/WF/NAV artifacts (point-in-time) | Verify freshness/methodology; treat as research |
| `calculate_metrics.py`, `calculate_metrics_debug.py` | Metrics correctness (units/costs/benchmarks) | Reconcile with canonical PnL before use |
| `final_v2/fix-p0-safe-fixes-2026-11-14-main/`, `final_v3/childlike-airport/`, `final_v3/feat-stop-fill-cost-gate-final-v3/` | Review artifacts | Publish via clean branch from fresh `origin/main` (own files only) |
| `mega_mutation_closed_ledger.json` | Candidate claim evidence | Require independent reproduction |
| `dashboard/live_picks.json` (recent) | Freshness/source-of-truth | Reconcile with canonical store |

## Exclude from prediction commits
Large unrelated untracked set (job-search/infra/notes/skills/docs not tied to trading signals).

## Last-24h notable prediction files
`research/profitability/**` (v1–v4, VWAP validation/falsification, SCORECARD 0 proved), `research/asset_class/*/run_2026-11-14T06-11-*` (exploratory), `updates/2026-11-14-PROFITABLE-APPROACH-VWAP-MEAN-REVERSION.md`.
