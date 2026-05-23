# Update: Strategy Correlation Guard + Commodity Range-Position Reversion

**Date:** 2026-04-18  
**Branch:** `feature/correlation-guard-commodity-strategy`  
**Author:** Kimi Code CLI

## Summary

Following the batch 1–4 baby-strategy audit, we identified a need for two things:
1. **An automated correlation guard** to ensure new strategies are genuinely novel (not just rehashes of existing validated strategies).
2. **A novel commodity-focused strategy template** that uses intraday range-position + ATR regime detection — fundamentally different from the RSI/Stochastic-based survivor pool.

This update delivers both.

---

## 1. Strategy Correlation Guard (`scripts/strategy_correlation_guard.py`)

### What it does
- Auto-discovers all `survivor_validated=True` strategies from `forward_signal_scanner.py`
- Runs a candidate strategy + every validated strategy through a rolling-window backtest on 6 cross-asset symbols (BTC, ETH, AAPL, MSFT, EURUSD, GC)
- Computes Pearson correlation of daily P&L series
- Returns `PASS` if `|corr| < 0.30` with all validated strategies

### Usage
```bash
python scripts/strategy_correlation_guard.py \
    --candidate baby_strategies/my_new_strategy.py \
    --threshold 0.30
```

### Validation
Tested against `ConnorsRSI2Strategy` — correctly flagged it as correlated with `VolumePriceConfirmationReversalStrategy` (|corr| = 0.405), confirming the tool works as intended.

---

## 2. Commodity Range-Position Reversion (`baby_strategies/commodity_range_position_reversion.py`)

### Signal Logic
- **Extreme condition:** ATR(14) > 1.5 × ATR(50) (volatility expansion)
- **Exhaustion filter:** (Close − Low) / (High − Low) < 0.20 (price in bottom 20% of daily range)
- **Trend filter:** Close > SMA(200)

### Differentiation from existing pool
| Feature | Existing Survivors | This Strategy |
|---|---|---|
| Primary indicator | RSI(2), MFI, CMO, %R | ATR regime + range position |
| Oversold detection | Oscillator threshold | Intraday footprint |
| Volatility awareness | Static ATR multiples | Adaptive ATR(14) vs ATR(50) |

### Backtest Results (Quick Screen, 17 symbols, 2yr daily, 0.2% cost)

| Asset Class | Trades | Win Rate | Profit Factor | Sharpe |
|---|---|---|---|---|
| Crypto | 461 | 54.4% | 4.70 | **2.11** |
| Equity | 19 | 36.8% | 0.75 | −0.58 |
| Forex | 71 | 32.4% | 0.32 | −2.16 |
| Commodity | 101 | 7.9% | 0.01 | −7.31 |
| **Aggregate** | 652 | 44.3% | 3.38 | 0.11 |

### Status: EXPERIMENTAL
- **Does NOT pass** the validation gate (fails on equity/forex/commodity classes)
- Shows genuine edge in **crypto** (Sharpe 2.11, PF 4.70)
- Flagged as `experimental` in registry pending refinement or asset-class specialization
- Next steps: test with volume spike confirmation, or narrow to crypto-only with tighter filters

---

## 3. Registry Updates

Added to `incubator/backtest_team/forward_signal_scanner.py`:
- `CommodityRangePositionReversionStrategy` — agent "batch_april_2026", `survivor_validated=False`, note "EXPERIMENTAL: crypto edge only, Sharpe 2.11"

---

## Files Changed

```
scripts/strategy_correlation_guard.py              (new)
baby_strategies/commodity_range_position_reversion.py  (new)
updates/2026-04-18-correlation-guard-commodity-strategy.md  (new)
incubator/backtest_team/forward_signal_scanner.py  (modified)
```

## Verification

- [x] Correlation guard runs without errors
- [x] Correlation guard correctly catches high-correlation candidates
- [x] Commodity strategy file is importable and has `generate_signals` method
- [x] Commodity strategy produces signals on test data
- [x] Registry entry added with correct metadata
