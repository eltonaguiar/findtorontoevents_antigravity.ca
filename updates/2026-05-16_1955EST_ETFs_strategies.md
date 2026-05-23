# ETFs — Asset Class Strategy Audit
**Date:** 2026-05-16 19:55 EST  
**Author:** Buffy (Codebuff)  
**Scope:** Forward-test performance, backtest, strategy gaps, data coverage

---

## 1. Forward-Test Performance

| Metric | Value |
|--------|-------|
| Total closed picks | **0** |
| Win Rate | N/A |
| Profit Factor | N/A |

**Verdict:** ⚠️ **ZERO FORWARD-TEST DATA.** ETF strategies have strong backtests but are NOT generating live picks. This is a major gap.

---

## 2. Backtest Performance

| Backtest | WR | PF | Notes |
|----------|-----|-----|-------|
| `etf_sector_rotation_backtest.json` | 70.49% | 2.05 | Sector rotation |
| `etf_sector_rotation_long_short_backtest.json` | 54.92% | 0.94 | Long/short variant — worse |
| `etf_sector_rotation_slippage_backtest.json` | — | — | Slippage analysis |
| `etf_rotation_vix_regime_backtest.json` | — | — | VIX regime filter |

**Verdict:** ✅ Sector rotation backtests are **strong** (70.49% WR, 2.05 PF). Long/short variant underperforms (0.94 PF). VIX regime filtering improves rotation timing.

---

## 3. Prediction Market & Copytrader Coverage

| Data Source | Covers ETF? | Status |
|-------------|-------------|--------|
| **Kalshi signals** | ❌ No | Missing |
| **Polymarket signals** | ❌ No | Missing |
| **Multi-asset copytrader** | ❌ No | Missing |
| **Non-crypto consensus** | ✅ Yes | `copy_trader_intel/non_crypto_consensus.py` |

**Verdict:** ⚠️ The LEAST covered asset class for external data. Only non-crypto consensus covers ETFs. Prediction markets don't cover ETF-specific events.

---

## 4. Strategy Gaps & Missing Data Sources

### What we HAVE:
- ✅ Sector rotation (XLF, XLK, XLE, XLV, XLI, etc.)
- ✅ VIX regime filtering
- ✅ Relative strength ranking

### What we're MISSING:
- ❌ **ETF flow data (creation/redemption)**
  - Free API: **ETF.com**, **ETF Database**
  - Impact: Large creations = bullish institutional demand; large redemptions = bearish
- ❌ **Leveraged/inverse ETF decay arbitrage**
  - Free API: Price data only needed
  - Impact: Shorting both the 3x long AND 3x short ETF = harvest volatility decay
- ❌ **ETF premium/discount to NAV**
  - Free API: Issuer websites (iShares, State Street)
  - Impact: >1% discount to NAV is a buy signal for arbitrage
- ❌ **Thematic ETF rotation (ARKK, ICLN, etc.)**
  - Free API: Already have price data
  - Impact: Thematic ETFs have higher vol, bigger sector rotation returns
- ❌ **ETF options flow (SPY, QQQ, IWM)**
  - Free API: **CBOE** (free delayed)
  - Impact: Put/call ratios, gamma exposure levels

### Highest-ROI gap to fill:
**Wire the sector rotation strategy** — we have strong backtests (70.49% WR, 2.05 PF) but ZERO live picks. The strategy exists in backtest form but is not generating signals in production.

---

## 5. Statistical Edge Assessment

| Criterion | Status | Value |
|-----------|--------|-------|
| DSR (Deflated Sharpe) | ❌ | 0 picks — impossible |
| PBO | ⚠️ | Backtest PF 2.05, needs forward confirm |
| Backtest edge | ✅ | 70.49% WR, 2.05 PF |

**Bottom line:** ETFs have strong paper edge (70.49% WR backtest) but ZERO forward test. This is like having a Ferrari in the garage with no gas. The strategy code exists, it just needs to be activated in the production scanner.

---

## 6. Recommendations

1. **ACTIVATE ETF sector rotation in production scanner** — backtest PF 2.05 with 70.49% WR deserves live testing
2. **Configure ETF symbols in scanner config** — XLF, XLK, XLE, XLV, XLI, XLY, XLP, XLB, XLRE, XLU, SMH, IBB
3. **Add ETF flow data** — creation/redemption activity is a free, high-signal data source
4. **Add VIX regime filter to sector rotation** — already backtested, improves timing
5. **De-prioritize long/short variant** — 0.94 PF is below breakeven
