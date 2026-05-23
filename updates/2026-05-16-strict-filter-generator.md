# Strict Filter Generator - 2026-05-16

## What Was Broken

The weekly real-money filter process existed mainly as Markdown analysis. That made it easy for agents to loosen claims by hand, especially around classes with attractive headline stats but real blockers:

- `COMMODITY` has strong PF/WR but concentration/readiness blockers.
- `ETF` has good WR but PF below the Tier 2 threshold.
- `CRYPTO` has positive expectancy but fails class-wide WR/PF and worst-fold checks.
- `FOREX`, `BOND`, and `FUTURES` are not currently sizeable.

## What Changed

Added `tools/filter_generator.py`, a machine-readable strict gate that reads `audit_dashboard/data/dashboard_data.json` and emits JSON for each asset class.

The generator checks:

- `resolved_n >= 100`
- `win_rate >= 50`
- `profit_factor >= 1.5`
- positive expectancy
- no concentration `WARN` or `BLOCK`
- readiness sizing is not blocked
- walk-forward `worst_fold_wr >= 40` when available

It also computes quarter-Kelly sizing with `alpha_engine.kelly_position_sizer.compute_position_size()` and caps live swing sizing at the `docs/PERFORMANCE_CHARTER.md` 1% per-trade limit.

## How To Run

```powershell
python tools/filter_generator.py
python tools/filter_generator.py --asset-class EQUITY
python tools/filter_generator.py --output reports/strict_filters.json
```

## Verification

Verified against the fresh 2026-05-16 dashboard payload and generated a strict report at:

- `reports/weekly_filter_strict_20260516T051032Z.md`

Expected current verdict:

- `EQUITY`: `FILTER_READY_SMALL_SIZE`
- All other classes: `RESEARCH_ONLY` until their blockers clear
