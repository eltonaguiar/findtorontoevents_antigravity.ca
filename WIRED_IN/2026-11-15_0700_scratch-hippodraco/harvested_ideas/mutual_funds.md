# Asset Class Deep Dive: MUTUAL FUNDS

**Source:** scratch-hippodraco research session  
**Date:** 2026-11-15T07:00Z  
**Status:** NOT_A_CLASS — Not a predicted asset class

## Current State

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Class ID | -1 | ≥0 | FAIL |
| Scanner | None | required | MISSING |
| NAV Data Source | None | required | MISSING |
| Dashboard Tile | None | required | MISSING |
| Class in ASSET_CLASS_MAP | No | required | MISSING |
| Class in _CAT_MAP | No | required | MISSING |

## Strategies Identified in Repo

| Strategy | File | WR | PF | n | Status |
|----------|------|-----|-----|-----|--------|
| None | N/A | N/A | N/A | N/A | NOT_A_CLASS |

## Key Issues

1. **Not a predicted class**: `ASSET_CLASS_MAP` has no `MUTUAL_FUND` entry
2. **Class id -1**: Dropped by ML gate (`.get(..., -1)`)
3. **No NAV data source**: NAV struck once daily after close
4. **No scanner/strategy**: `mutual_fund_strategies.py` does not exist
5. **No dashboard tile**: `"mutual_fund"` not in `_PER_ASSET_CLASSES`
6. **30-day frequent trading limits**: Intra-day TP/SL meaningless
7. **Expense ratios**: 0.03%-1.0%+ drag not modeled
8. **Loads**: Front-end/back-end loads not modeled

## Why MF Is NOT a Prediction Class

| Characteristic | Implication |
|---------------|-------------|
| NAV struck once daily after close | No intraday TP/SL; orders fill at next NAV |
| 30-day frequent-trading limits | Day trading/scalping impossible; penalties apply |
| Expense ratios (0.03%-1.0%+/yr) | Drag on returns; must be modeled |
| Loads (front-end/back-end) | Transaction costs killing short-horizon edges |
| No cash-flow beta for active timing | Long-run returns = equity risk premium, not alpha |

## Recommendation

**Do NOT build mutual fund prediction picks.** Instead:

1. **Low-cost index MF allocation**: VFIAX, VTSAX, FXAIX, SWTSX (ER ≤0.20%, AUM ≥$1B, turnover ≤20%)
2. **ER ≤0.10-0.20%, high AUM, low turnover (<20%/yr), long track record (10+ years)**
3. **Monthly clock allocation**: Not day trading — monthly rebalance
4. **This is allocation/cost discipline, NOT ML prediction**

## If MF Prediction Infrastructure Is Ever Built (Future)

| Requirement | Status | Action |
|-------------|--------|--------|
| Register MUTUAL_FUND class | Missing | Add to ASSET_CLASS_MAP, _CAT_MAP, _LOWER_TO_UPPER |
| NAV data source | Missing | Source CSV/JSON feed; yfinance fallback |
| Freshness gate | Missing | Stale if NAV > 24h (T+1) |
| Scanner/strategy stubs | Missing | Build mirroring bond structure |
| Dashboard tile | Missing | Add to _PER_ASSET_CLASSES, _CANONICAL |
| ML gate registration | Missing | Add ASSET_CLASS_MAP["MUTUAL_FUND"] = 7 |
| EOD/NAV pipeline | Missing | Build separate from crypto tick loop |
| Expense ratio modeling | Missing | Wire into PnL calculation |
| Load modeling | Missing | Wire into transaction costs |
| T+1 settlement handling | Missing | Orders fill at next NAV |
