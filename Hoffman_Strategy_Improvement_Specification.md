# Hoffman Strategy Improvement Specification

## 1. Overview
The Hoffman family of strategies (IRB + EMA angle) has demonstrated strong theoretical performance but suffers from practical execution issues:
- **Fixed SL/TP** and overly tight risk‑reward ratios.
- **No volatility awareness** – stops and targets do not adapt to market conditions.
- **Regime insensitivity** – the same parameters are used across trending, ranging, and low‑volume regimes.
- **Missing volume confirmation** and **chasing entries** after breakout.

This document defines three new variants that address those shortcomings while preserving the core IRB logic.

## 2. Identified Root Causes
| Source | Issue | Evidence |
|---|---|---|
| `incubator/agents/claude_code_01/crypto_hoffman_family_v1.py` (lines 8‑14) | EMA‑angle filter too strict, 45 % wick threshold too high, no volume filter, entry chasing | "Root cause analysis: EMA angle >= 30° filter is too strict … 45 % wick threshold misses many institutional bars … No volume confirmation … Entry at current price after breakout = chasing" |
| `AUDIT_REPORT_2026-03-06.md` (lines 57‑60) | Weak R:R on Proven Winners LONG picks | "Weak R:R on Proven Winners LONG picks … R:R 1.33:1 — barely positive at <57 % WR" |
| `AUDIT_REPORT_2026-03-06.md` (lines 71‑74) | Near‑USD short with extremely wide stop | "Entry $1.23, TP $0.73, SL $1.46 = 40.7 % downside target, 18.7 % upside risk … typical of the -430 % PnL drag" |
| `AUDIT_REPORT_2026-03-06.md` (lines 50‑55) | Conflicting signals on same asset | "BTCUSDT has 3 LONG positions AND 2 SHORT positions open simultaneously … self‑cancel P&L" |

## 3. Design Goals
1. **Volatility‑scaled risk** – SL/TP expressed in multiples of ATR or ATR‑percentile.
2. **Dynamic position sizing** – size based on Kelly criterion or volatility‑scaled fraction of equity.
3. **Regime‑aware entry** – optional filter using ATR‑rank, HMA‑slope, or multi‑timeframe RSI.
4. **Volume confirmation** – require breakout volume ≥ 1.2 × 20‑period average.
5. **Reduced chase** – entry price taken at breakout candle close, not after.

## 4. New Variant Designs
### 4.1 `HoffmanATRStop`
- **Base**: `IRBHoffmanStrategy` (see [`irb_hoffman.py:12`](e:/findtorontoevents_antigravity.ca/baby_strategies/irb_hoffman.py:12)).
- **SL/TP**: 
  ```python
  atr_val = atr(high, low, close, period=14).iloc[-1]
  # ATR‑percentile rank (0‑1) across last 100 candles
  atr_pct = (atr_val - atr_series.rolling(100).min()) / (atr_series.rolling(100).max() - atr_series.rolling(100).min())
  # Scale: tighter when low volatility, wider when high volatility
  sl_mult = 1.0 + 0.5 * (1 - atr_pct)   # 0.5‑1.5× ATR
  tp_mult = 2.0 + 2.0 * atr_pct       # 2‑4× ATR
  if direction == "LONG":
      sl = entry - sl_mult * atr_val
      tp = entry + tp_mult * atr_val
  else:
      sl = entry + sl_mult * atr_val
      tp = entry - tp_mult * atr_val
  ```
- **Rationale**: Guarantees a minimum R:R of ~1.5:1 while widening stops in volatile periods.

### 4.2 `HoffmanKellySized`
- **Base**: `IRBHoffmanStrategy`.
- **Position size** (fraction of equity):
  ```python
  # Estimate win probability from recent 30‑trade rolling WR
  win_prob = recent_wr  # e.g., 0.62
  # Estimate average payoff‑to‑risk ratio from recent trades
  avg_rr = recent_rr   # e.g., 1.8
  kelly_f = win_prob - (1 - win_prob) / avg_rr
  # Cap at 5 % of equity to limit exposure
  position_frac = min(max(kelly_f, 0), 0.05)
  ```
- **Integration**: Size = `position_frac * capital`.

### 4.3 `HoffmanRegimeFilter`
- **Regime indicators** (combined with AND logic):
  1. **ATR‑percentile** – require `atr_pct > 0.3` (i.e., not ultra‑low volatility).
  2. **HMA slope** – `hma_slope = np.sign(hma(close, 21).diff().iloc[-1])`; require `hma_slope == 1` for LONG, `-1` for SHORT.
  3. **Multi‑timeframe RSI** – both 1h and 4h RSI must be > 45 for LONG, < 55 for SHORT.
- **Implementation** (example snippet):
  ```python
  if not (atr_pct > 0.3 and hma_slope == direction_sign and rsi_1h > 45 and rsi_4h > 45):
      continue  # skip signal in unfavorable regime
  ```

## 5. Parameter Definitions (shared across variants)
| Parameter | Type | Default | Description |
|---|---|---|---|
| `atr_period` | int | 14 | Period for ATR calculation. |
| `atr_percentile_window` | int | 100 | Window for ATR‑percentile rank. |
| `volume_ma_window` | int | 20 | Moving‑average window for volume comparison. |
| `volume_ratio_threshold` | float | 1.2 | Minimum volume multiplier to accept breakout. |
| `hma_period` | int | 21 | Period for HMA trend filter. |
| `rsi_period` | int | 14 | RSI period for each timeframe. |
| `kelly_cap` | float | 0.05 | Maximum Kelly‑derived position fraction. |

## 6. Pseudocode – End‑to‑End Flow
```text
for each candle:
    # 1. Detect IRB (wick_pct >= 45%)
    if not irb_detected:
        continue

    # 2. Volume filter
    vol = volume[-1]
    avg_vol = volume[-volume_ma_window:].mean()
    if vol / avg_vol < volume_ratio_threshold:
        continue

    # 3. Regime filter (optional, enabled via config)
    if regime_filter_enabled:
        atr_val = atr[-1]
        atr_pct = (atr_val - atr_series[-atr_percentile_window:].min()) / (atr_series[-atr_percentile_window:].max() - atr_series[-atr_percentile_window:].min())
        hma_slope = sign(hma(close, hma_period).diff()[-1])
        rsi_1h = rsi(close_1h, rsi_period)[-1]
        rsi_4h = rsi(close_4h, rsi_period)[-1]
        if not (atr_pct > 0.3 and hma_slope == direction_sign and ((direction == "LONG" and rsi_1h > 45 and rsi_4h > 45) or (direction == "SHORT" and rsi_1h < 55 and rsi_4h < 55))):
            continue

    # 4. Entry price = close of breakout candle (no chase)
    entry = close[-1]

    # 5. Compute SL/TP using ATR‑scaled variant (choose variant class)
    sl, tp = compute_atr_stop_tp(entry, direction, atr_val, atr_pct, variant="ATRStop")

    # 6. Position size via Kelly or fixed fraction
    size = compute_position_size(equity, variant="KellySized")

    # 7. Submit order
    place_order(symbol, direction, entry, sl, tp, size)
```

## 7. Integration Steps
1. **Create new strategy classes** in `paper_trading/strategies/hoffman_variation_strategies.py`:
   - `HoffmanATRStop`
   - `HoffmanKellySized`
   - `HoffmanRegimeFilter`
2. **Add configuration flags** in `paper_trading/config.py` (e.g., `USE_ATR_STOP = True`).
3. **Update back‑test runner** (`backtest_hoffman_variations.py`) to include the new classes in `ALL_STRATEGIES`.
4. **Persist new parameters** to MySQL `strategy_registry` for UI exposure.
5. **Add dashboard columns** (`atr_pct`, `hma_slope`, `volume_ratio`) via migration script (see `AUDIT_REPORT_2026-03-06.md` suggestion).

## 8. Testing Plan
| Test | Description | Success Criteria |
|---|---|---|
| **Unit** | Verify `compute_atr_stop_tp` returns SL/TP with R:R ≥ 1.5:1 across low‑high volatility windows. | All generated trades pass `tp - entry >= 1.5 * (entry - sl)`.
| **Unit** | Kelly sizing never exceeds `kelly_cap`. | `position_frac <= 0.05` for all simulated trades.
| **Integration** | Run `backtest_hoffman_variations.py` with new variants on 6 symbols × 2 timeframes. | WR ↑ 5 pp vs baseline, Sharpe ↑ 0.2, max drawdown ≤ 10 %.
| **Regression** | Ensure existing `IRBHoffmanStrategy` unchanged. | No difference in its back‑test results.
| **Live‑simulation** | Deploy to sandbox for 2 weeks, monitor R:R and conflict count. | Conflict count ↓ 80 % (per audit issue 1), average R:R ≥ 1.7:1.

## 9. Documentation & UI Updates
- Add **Strategy Detail** page for each new variant showing ATR‑percentile, HMA slope, and volume ratio.
- Extend **Active Picks** table with columns `ATR%`, `HMA_Slope`, `Vol_Ratio` (SQL migration snippet in audit report).
- Provide a **Regime‑Filter toggle** in the UI.

---
*Prepared by the Architecture team – ready for implementation.*
