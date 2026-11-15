# Failure taxonomy — derived from the 2026-11-15 scan

Derived from `00_inventory.csv` (14,830 flagged files: 2,561 implemented, 3,101 tested,
8,355 documented, 813 abandoned) plus the closed ledger. Each row cites a path.

## The structural signature of this repo

| Ratio | Value | What it means |
|---|---:|---|
| documented / implemented | **3.3 : 1** | prose about methods outruns code implementing them |
| files mentioning DSR vs files using a backtest framework | **756 : 51** | the repo measures more rigorously than it executes |
| abandoned / implemented | 813 / 2,561 | a third of everything built was walked away from |
| closed picks that cannot be benchmarked from daily closes | **1,084 / 3,500 (31%)** | the central question is unanswerable for a third of the ledger |

The 51 `BT:framework` files against 756 `STAT:dsr` files is the single most diagnostic number
here: statistical rigour was written *around* bespoke pipelines rather than inside a standard
engine, so every pipeline had its own fill assumptions and its own idea of costs.

## Taxonomy (F1–F10) with evidence

| Code | Failure | Evidence | Where |
|---|---|---|---|
| F1 | Overfitting / data snooping | 149 `ml_enhanced` per-symbol variants, 119 with n=1; best-of selection produced PF 6.67 while the family PF was 0.63 | `crypto_enhanced/` variants; `NO_EDGE_BRAINSTORM_CLOUD.MD` |
| F1 | Same, at project scale | 3,000+ configurations across the tree; 813 abandoned files; DSR exists in 756 files and rejected all 5 tested strategies (DSR < 1.64) | `.claude/PEER_INTEL.md:279`, `alpha_engine/deflated_sharpe.py` |
| F2 | Look-ahead | documented incidents; resolver re-scores use the resolved bar, not the decision bar | `reports/CO...`; `updates/2026-11-14-ML-AUDIT-childlike-airport.md` |
| F3 | Survivorship / universe | universe rebuilt daily from gainers (`dynamic_universe.json`), so the sample is the survivors | `alpha_engine/data/dynamic_universe.json` |
| F4 | Unrealistic costs | cost fields absent from the dashboard payload entirely; ledger must impose 6 bps/side | `tools/forward_tracker.py` (`DEFAULT_FEE_BPS_PER_SIDE`) |
| F5 | Edge below noise | mean +0.54% with median −0.88% (CRYPTO); +0.46% / −0.18% (EQUITY) — the mean is a tail, not an edge | `reports/quant_audit/ASSET_CLASS_TRIAGE_2026-11-15.md` |
| F6 | Regime dependence | `REGIME` appears in 8,609 files — the most common signal in the tree — yet no class is reported per regime | scan, `00_inventory.csv` |
| F7 | Backtest-vs-live gap | `EXEC:paper` 2,107 files vs `EXEC:live` 2,061; forward WR 21% reported against backtest WR much higher | `reports/2026-06-05-LIVE-FORWARD-TRIAGE.md` |
| F8 | Insufficient sample | BOND n=28, COMMODITY n=9, FUTURES n=1 — three classes judged on noise or not judged at all | `audit_dashboard/data/dashboard_data.json` |
| F9 | Wrong objective | PF and raw return dominate; excess-vs-benchmark only existed from 2026-11-15 | `tools/pick_excess.py` (added this cycle) |
| F10 | Risk management | same-day rows (1,084) mean intraday churn with no time in market; FOREX PF 0.66/WR 32% ran 199 trades without stopping | ledger |

## What is *not* a failure mode here

- **Not a lack of ideas.** 3,000+ configurations, 25 technique families, 149 ML variants.
- **Not a lack of statistics.** DSR, PBO, CPCV, White's Reality Check, bootstrap, clustering —
  all present, several of them only in worktrees.
- **Not a lack of tooling.** The measurement layer (`pick_excess.py`, `forward_tracker.py`,
  `benchmark_closed_ledger.py`) is good and recent.

The failure is that all three existed in parallel and never met in one decision path.
