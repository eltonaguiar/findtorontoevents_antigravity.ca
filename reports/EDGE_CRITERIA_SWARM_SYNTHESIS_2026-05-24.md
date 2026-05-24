# Swarm Synthesis — EDGE_CRITERIA_SWARM (3 agents)

**Date:** 2026-05-24 | **Agents:** Quant Analyst, Systems Architect, Portfolio Manager

---

## Consensus Findings

### 1. regime_adaptive IS LIKELY DATA LEAKAGE (all 3 agree)
- 84.6% WR on n=13 isn't statistically significant (CI: [54.6%, 98.1%])
- Cross-asset consistency at implausible levels suggests regime labels use forward data
- **Action:** P0 audit of regime label generation (timestamp alignment check)

### 2. Only 2 Proven Edge Pairs Exist
| Pair | n | WR | PnL | Tier |
|------|---|-----|-----|------|
| deep_value × EQUITY | 60 | 60.0% | +1.07% | ✅ Tier-1 |
| momentum_breakout × ETF | 46 | 58.7% | +0.17% | ✅ Tier-1 |

All other pairs fail n<20 or WR<55% thresholds.

### 3. FOREX is a Statistical Trap (NOT an Edge)
- 57.3% WR but -0.39% avg PnL, Sharpe -0.22
- Many small wins, occasional large losers (3.2:1 loss-to-win ratio)
- **Recommendation:** Zero allocation. OR test faded signal (inverse picks).

### 4. Confidence Pipeline is Broken — Two Fixes
- **Immediate:** Use persona_WR as confidence proxy for Kelly sizing
- **Long-term:** Float 0-1 encoding, calibration layer, backfill legacy picks

### 5. FRED is Fixable — One-Line Change
- `fred_macro_sidecar.py:63` hardcodes `api_key=""` instead of reading env var
- CI workflow also needs `FRED_API_KEY` in env

### 6. Copy Trader Wireable with 30-line Adapter
- 20+ picks/2h across stocks/forex/commodities
- CopyTraderPick() has all fields tournament_picks needs

### 7. Position Sizing Rules (Portfolio Manager)
| Rule | Value |
|------|-------|
| Total risk budget | 2% of portfolio |
| Per-position risk | 1.5% of NAV |
| Max concurrent | 10 positions |
| Class concentration | 5% per class |
| Sizing method | Equal-weight until n≥20, then fractional Kelly |

### 8. Expected Resolution Dates
| Class | First Resolution |
|-------|-----------------|
| PENNY (7d) | May 31 - Jun 1 |
| FUTURES (14d) | Jun 7 - Jun 8 |
