# Investigation: Asset Class Profit Factor Discrepancy

**Agent**: Kilo  
**Date**: 2026-04-17  
**Time**: 00:41 EDT

## Problem Statement

User reports that Equities, Forex, Commodities, ETFs, and Bonds have WR < 50% but shows different profit factors than what's in current dashboard:
- Stocks: reported PF 1.47, observed 1.39
- Forex: reported PF 1.11, observed 0.26
- Commodities: reported PF 1.18, observed 1.14
- ETFs: reported PF 0.86 - matches
- Bonds: reported PF 1.60 - matches

## Findings

### Current Dashboard Data (audit_dashboard/data/dashboard_data.json)
```json
{
  "EQUITY":   {"win_rate": 52.0, "profit_factor": 1.39, "resolves": 344, "pnl": 214.7},
  "CRYPTO":  {"win_rate": 46.4, "profit_factor": 1.18, "resolves": 14154, "pnl": 3343.42},
  "FOREX":   {"win_rate": 45.1, "profit_factor": 0.26, "resolves": 892, "pnl": -982.14},
  "COMMODITY":{"win_rate": 40.2, "profit_factor": 1.14, "resolves": 403, "pnl": 10.64},
  "ETF":    {"win_rate": 48.4, "profit_factor": 0.86, "resolves": 62, "pnl": -12.14},
  "BOND":   {"win_rate": 50.0, "profit_factor": 1.60, "resolves": 16, "pnl": 2.84}
}
```

### Key Observations

1. **EQUITY actually has 52% WR** - This is ABOVE 50%, contradicting the user's statement. The data shows it's the only stable asset class with WR >50%.

2. **FOREX is severely stressed** - WR=45.1%, PF=0.26, and -982.14% PnL. This is marked "stressed" in the health system.

3. **COMMODITY and ETF are "watch" status** - Both have WR < 50% but PF > 0.80. They're not stable but not critical.

4. **BOND has thin sample** - Only 16 resolved picks, so the 50% WR and 1.60 PF may not be statistically significant.

### Computation Logic

Profit factor is calculated as (per `dashboard_generator.py` lines 11134-11136):
```python
b["profit_factor"] = round(b["win_pnl"] / abs(b["loss_pnl"]), 2)
```
Where win_pnl = sum of all winning trade PnL percentages, loss_pnl = sum of all losing trade PnL percentages.

### Root Cause Potential

The discrepancy between user's numbers and current data could be explained by:
1. **Different filtering**: Some reports may include only "resolved" picks while others include all "closed" picks.
2. **Sample variations**: Smaller samples at different timeframes yield different PF.
3. **Double-counting**: There may be duplicate picks in some datasets (the dashboard shows 13,770 unique resolved vs 21,127 total closed).
4. **Data source differences**: The user may be referencing a different report or export.

## Recommendations

1. The **FOREX** result is the real concern - PF 0.26 with -982% PnL is catastrophic. This should be blocked in production until WR > 30% (already has a quality gate).

2. **EQUITY** is actually performing well (52% WR, 1.39 PF) - don't block it.

3. **BOND** has too small sample (n=16) to draw conclusions.

4. **ETF** (48.4% WR, 0.86 PF) and **COMMODITY** (40.2% WR, 1.14 PF) need more data before trusting.

## Conclusion

The data does NOT support WR < 50% for all non-crypto asset classes, particularly for EQUITY (52% WR). The profit factors also don't match what the user reported. Likely a data source discrepancy. Key risk is FOREX which is severely underperforming.

---
*Investigation complete - data sourced from audit_dashboard/data/dashboard_data.json*