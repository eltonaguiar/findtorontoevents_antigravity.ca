---
tags: [reference]
created: 2026-06-06
---

# Data Quality & Admissibility Checklist

10-step admissibility pipeline from `reports/EAGLE_JUNE2_*.md`.

## Pre-Flight Checks

- [ ] **Dedup signal-ts groups** — check for duplicate timestamps (mega_mutation had 31% dup)
- [ ] **created_at≠NULL** — created_at=NULL is root cause of most duplicates
- [ ] **closed_at populated** — bootstrap_forward_stats.json had ~95% NULL; only ~7 live rows had real closed_at
- [ ] **EXPIRED→WON mislabels** — resolver may incorrectly close as WON
- [ ] **Concentration check** — single source HHI>0.30 fails gate (measure at strategy level, not engine)

## Resolver Checks

- [ ] **Resolver version** ≥v2.1 (2026-05-02 bug bundle)
- [ ] **Intrabar OHLC replay** — TP/SL must be cross-checked against intrabar bars
- [ ] **PNL_WIN_THRESHOLD_BY_CLASS** applied (CRYPTO 0.1bp, others 5bp)
- [ ] **BACKFILL_EXCLUDE_DATE filter** active (2026-06-04 backfill contaminated walk-forward)

## Statistical Checks

- [ ] **n≥100** clean trades before T2 claim
- [ ] **14d panel** checked (not just historical aggregate)
- [ ] **48h panel** checked (recency signal)
- [ ] **Walk-forward PASS** for the strategy
- [ ] **OOS test** separate from in-sample

## Data Sources

- Verdict-grade numbers: `asset_class_health` table
- Raw (pre-fix): `by_asset_class`
- Dashboard: `audit_dashboard/data/dashboard_data.json` (NOT the legacy `audit/data/`)
- Recency: `audit_dashboard/data/pick_summary_stats_{14d,48h}.json`
