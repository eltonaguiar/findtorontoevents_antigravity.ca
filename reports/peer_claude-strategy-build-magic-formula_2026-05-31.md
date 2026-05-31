# Strategy Build Report — Magic Formula (Greenblatt 2006)

**Date:** 2026-05-31
**Builder:** peer_claude (subagent)
**Slug:** `magic-formula`
**Build dir:** `/tmp/strategy_builds_2026-05-31/magic_formula/`

## Files Shipped

| File | Lines | Purpose |
|---|---|---|
| `strategy.py` | 167 | Universe filter + EY/RoC ranking + statistical gate |
| `paper_pilot_harness.py` | 179 | Annual-rebalance simulator, JSON sidecar persistence |
| `tests.py` | 139 | 13 unit tests (universe, ranking, harness, admissibility) |
| `README.md` | 50 | Citation + rules + data source + statistical gate |
| `ai_consult_deepseek.md` | 22 | Verbatim DeepSeek consult on data sourcing |

**Tests:** 13/13 PASS (universe filters, EY+RoC ranking, top-N equal-weight,
Wilson LB, admissibility states INSUFFICIENT_N / WALK_FORWARD_READY /
LIVE_PROMOTION_OK, harness roundtrip + persistence).

## Implementation Summary

- **Universe gates:** market cap >= $1B, exclude SIC 6000-6999 (financials) and
  4900-4999 (utilities), exclude ADRs and REITs, exclude EBIT <= 0, exclude
  negative-capital firms (NWC + NFA <= 0).
- **Earnings Yield:** `EBIT / Enterprise Value` (rank desc).
- **Return on Capital:** `EBIT / (Net Working Capital + Net Fixed Assets)` (rank desc).
- **Combined rank:** sum of ordinals; pick top 30 equal-weight; 365d hold.
- **Persistence:** harness writes to `paper_pilot_state.json` (NOT to
  `trading_picks` DB — per build rule, avoids contaminating production
  ML-trust scoring).

## Cursor Statistical Framework

- **n>=500** floor for live promotion (`MIN_N_LIVE_PROMOTION`).
- **n>=120** = `WALK_FORWARD_READY` intermediate verdict (≈4 years × 30/yr).
- Wilson 95% LB on WR must exceed 0.45.
- Bootstrap PF CI (1000 resamples, seed=42) lower bound must exceed 1.0.
- **Bonferroni alpha = 0.05 / 7 ≈ 0.00714** (7 strategies in this build wave).

## AI Cross-Refinement — DeepSeek

Verbatim recommendation captured in `ai_consult_deepseek.md`. Two key changes
drawn from the response:

1. **Confirmed primary data source:** SEC EDGAR XBRL `companyfacts` API.
   Specific concept tags catalogued in the README:
   - `us-gaap:EarningsBeforeInterestAndTaxes` (EBIT)
   - `us-gaap:MarketCapitalization` + `us-gaap:LongTermDebtAndCapitalLeaseObligations` + `us-gaap:ShortTermBorrowings` − `us-gaap:CashAndCashEquivalentsAtCarryingValue` (EV)
   - `us-gaap:AssetsCurrent` − `us-gaap:LiabilitiesCurrent` (NWC)
   - `us-gaap:PropertyPlantAndEquipmentNet` (NFA)

2. **Look-ahead-bias gotcha:** must use the XBRL `filed` date (NOT `end` date)
   to map financials. yfinance / FMP return restated figures and silently inject
   future information. Added TODO in the consult note for the v1.1 fetcher to
   enforce `fiscal_year_end < filed_date <= rebalance_date`.

## Open Items for v1.1
- Wire live EDGAR fetcher (currently strategy expects `Fundamentals` dataclass
  to be populated externally — backtest dry-runnable via stub).
- Add backtest driver pulling 2005-2024 EDGAR snapshots for ~2000 large-caps.
- Replicate Alpha Architect's 12-15% CAGR / 5-8% TE benchmark before any
  promotion gate evaluation.

## Promotion Status
**NOT live.** Harness in dry-run mode. n = 0 closed picks. Status:
`INSUFFICIENT_N`. Will require ~4 years of paper-pilot or a clean point-in-time
backtest to advance to `WALK_FORWARD_READY`.

## Server-side PR
Docs-only PR opened against `main` via `gh api` so the shared working tree is
not disturbed (multi-agent freeze convention).
