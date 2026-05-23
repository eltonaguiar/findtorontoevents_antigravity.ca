# Battleground Trading Guide
## How to Be Profitable — Exact Conditions

**Last updated:** 2026-03-13
**Based on:** 294 closed trades, 14 trading days, 86% winning days
**Only system with positive PnL** out of 8 systems tested.

---

## TL;DR — The 3 Rules

1. **Only trade Keltner Compression Expansion** on BTC, ETH, SOL (72.9% WR proven)
2. **Only trade during UTC 05:00-13:00** (highest win-rate window)
3. **Use trailing stops** — 49% of trades exit by TIME, leaving profit on the table

---

## Strategy Tier List (by proven edge)

| Tier | Strategy | WR | Trades | Avg PnL/Trade | Symbol |
|------|----------|-----|--------|---------------|--------|
| S | crypto_keltner_compression_expansion_v1 | 72.9% | 49 | +0.42% | BTCUSDT |
| S | crypto_drawdown_convexity_recovery_v1 | 71.4% | 16 | +0.26% | Multi |
| A | keltner_compression_expansion_sol_v1 | 64.9% | 37 | +0.40% | SOLUSDT |
| A | multi_period_rsi_confluence_xrp | 64.0% | 25 | +0.73% | XRPUSDT |
| A | drawdown_recovery_rsi_eth | 61.5% | 26 | +0.50% | ETHUSDT |
| A | multi_period_rsi_confluence_eth | 60.5% | 38 | +0.52% | ETHUSDT |
| B | drawdown_recovery_rsi | 55.9% | 34 | +0.69% | Multi |
| B | keltner_compression_expansion_xrp_v1 | 55.2% | 29 | +0.54% | XRPUSDT |
| B | crypto_choppiness_regime_switch_v1 | 55.0% | 20 | +0.29% | Multi |
| B | keltner_compression_expansion_eth_v1 | 55.0% | 40 | +0.61% | ETHUSDT |

---

## STRATEGY 1: Keltner Compression Expansion (S-Tier)

### What It Does
Detects when Bollinger Bands squeeze INSIDE the Keltner Channel (low volatility compression), then trades the breakout direction when price expands out of the channel — confirmed by Hull Moving Average trend and volume.

### Exact Entry Conditions (ALL must be true)

```
INDICATORS:
  ema_20    = EMA(Close, 20)          # or 30 depending on variant
  atr_14    = ATR(High, Low, Close, 14)  # or 20 depending on variant
  kc_upper  = ema + (multiplier * atr)
  kc_lower  = ema - (multiplier * atr)
  bb_mid    = SMA(Close, 20)
  bb_upper  = bb_mid + 2.0 * StdDev(Close, 20)
  bb_lower  = bb_mid - 2.0 * StdDev(Close, 20)
  hma_21    = HullMA(Close, 21)

SQUEEZE DETECTION (previous bar):
  bb_upper[prev] < kc_upper[prev]  AND  bb_lower[prev] > kc_lower[prev]
  → Bollinger Bands are INSIDE Keltner Channel = compression

LONG ENTRY:
  squeeze = True (previous bar)
  AND Close > kc_upper (breakout above Keltner)
  AND hma_21 is rising (hma[now] > hma[prev])
  AND Volume > 1.3 * Median(Volume, 20)

SHORT ENTRY:
  squeeze = True (previous bar)
  AND Close < kc_lower (breakdown below Keltner)
  AND hma_21 is falling (hma[now] < hma[prev])
  AND Volume > 1.3 * Median(Volume, 20)
```

### Per-Symbol Parameters

| Symbol | EMA | ATR | KC Mult | TP (ATR x) | SL (ATR x) | Timeframe |
|--------|-----|-----|---------|-----------|-----------|-----------|
| BTCUSDT | 30 | 20 | 1.8 | 2.3 | 1.3 | 4h |
| ETHUSDT | 30 | 20 | 1.9 | 2.4 | 1.3 | 1h |
| SOLUSDT | 30 | 20 | 2.0 | 2.6 | 1.2 | 1h |
| XRPUSDT | 30 | 20 | 1.9 | 2.4 | 1.3 | 1h |

### TP/SL Calculation

```
For LONG:
  take_profit = entry_price + (tp_mult * atr_value)
  stop_loss   = entry_price - (sl_mult * atr_value)

For SHORT:
  take_profit = entry_price - (tp_mult * atr_value)
  stop_loss   = entry_price + (sl_mult * atr_value)

Risk:Reward ratio = tp_mult / sl_mult = ~1.77:1 to 2.17:1
```

### Max Hold Time
- 4h chart: 12 bars = 48 hours
- 1h chart: 12 bars = 12 hours

---

## STRATEGY 2: Drawdown Recovery RSI (A-Tier)

### What It Does
Buys when price has dropped significantly from recent highs AND RSI confirms oversold. Catches the bounce.

### Exact Entry Conditions

```
drawdown = (Close / Max(Close, 50 bars) - 1)  # how far price fell

LONG ENTRY:
  drawdown < -6.0%    (BTC/multi) or -8.0% (ETH variant)
  AND RSI(14) < 35    (BTC/multi) or < 33 (ETH variant)

TP/SL:
  BTC:  TP = entry + 2.0 * ATR(14),  SL = entry - 1.5 * ATR(14)
  ETH:  TP = entry + 2.2 * ATR(14),  SL = entry - 1.3 * ATR(14)
```

---

## STRATEGY 3: Multi-Period RSI Confluence (A-Tier)

### What It Does
Requires BOTH short-term AND long-term RSI to be oversold simultaneously. Double-confirmation reduces false signals.

### Exact Entry Conditions

```
LONG ENTRY:
  RSI(14) < 33
  AND RSI(50) < 38

TP/SL:
  ETH:  TP = entry + 2.2 * ATR(14),  SL = entry - 1.4 * ATR(14)
  XRP:  TP = entry + 2.3 * ATR(14),  SL = entry - 1.4 * ATR(14)
```

---

## STRATEGY 4: Drawdown Convexity Recovery (S-Tier)

### What It Does
Detects deep drawdowns (-12%+) where momentum curvature turns positive (recovery acceleration). High WR because it waits for proof of recovery, not just oversold.

### Exact Entry Conditions

```
dd        = Close / Rolling_Max(Close, 80) - 1.0
momentum  = Close.pct_change(6)
convexity = momentum.diff()  # acceleration

LONG ENTRY:
  dd < -12%                    # deep drawdown
  AND dd[now] > dd[prev]       # recovering (drawdown shrinking)
  AND convexity > 0            # momentum accelerating upward
  AND Volume > 1.05 * SMA(Volume, 20)

SHORT ENTRY (post-recovery exhaustion):
  dd > -2%                     # almost recovered
  AND convexity < 0            # momentum decelerating
  AND Volume > 1.05 * SMA(Volume, 20)

TP: entry +/- 2.4 * ATR(14)
SL: entry -/+ 1.35 * ATR(14)
```

---

## TRAILING STOP RULES (Applied to ALL strategies)

```
TRAIL_ACTIVATE = +3% unrealized profit
TRAIL_DISTANCE = 3% below high-water mark

For LONG:
  hwm = max(all prices seen since entry)
  if (hwm - entry) / entry > 0.03:    # +3% profit
    trailing_sl = hwm * 0.97           # 3% below peak
    if trailing_sl > current_sl:
      sl = trailing_sl                 # only tighten, never widen

For SHORT:
  lwm = min(all prices seen since entry)
  if (entry - lwm) / entry > 0.03:    # +3% profit
    trailing_sl = lwm * 1.03           # 3% above trough
    if trailing_sl < current_sl:
      sl = trailing_sl
```

---

## POSITION SIZING (Quarter-Kelly)

```
kelly_fraction = WR - (1 - WR) / (avg_win / avg_loss)

For Keltner BTC (WR=72.9%, avg_win=+1.5%, avg_loss=-1.2%):
  kelly = 0.729 - 0.271 / (1.5/1.2) = 0.729 - 0.217 = 0.512 (51.2%)
  quarter_kelly = 0.512 / 4 = 12.8%

On $1,000 capital: risk $128 per trade
On $10,000 capital: risk $1,280 per trade
```

---

## REGIME FILTER

Only trade when market is NOT in full BEAR:
- VIX < 28 (or crypto equivalent: BTC 30d realized vol < 80%)
- BTC above 200-period SMA on the strategy timeframe
- If VIX > 28: reduce position size by 50% or sit out

---

## TIME-OF-DAY FILTER

Best performance: **UTC 05:00-13:00** (London + early US session overlap)
- During this window: full position size
- Outside window: reduce position size by 25% or skip

---

## WHAT NOT TO DO

1. Do NOT trade ml_battleground strategies (1.9% WR, -169% PnL)
2. Do NOT trade KIMI strategies (23.5% WR, -61% PnL)
3. Do NOT trade paper_trading strategies (0% WR, -30% PnL)
4. Do NOT stack 5+ picks on same symbol (correlation risk)
5. Do NOT hold past max hold time hoping for recovery
6. Do NOT ignore trailing stops — they are the #1 improvement needed
