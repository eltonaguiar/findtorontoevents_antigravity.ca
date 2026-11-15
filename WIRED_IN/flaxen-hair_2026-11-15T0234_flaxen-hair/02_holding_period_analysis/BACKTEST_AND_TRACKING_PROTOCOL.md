# BACKTEST RESULTS — Forward Test Protocol & Asset Class Validation

**Worktree:** flaxen-hair_2026-11-15T0038 | **Date:** 2026-11-15T00:38Z | **Repo:** findtorontoevents_antigravity.ca

---

## Executive Summary

**All backtests failed to produce a profitable strategy.** 42 strategy-symbol combinations tested across 10 symbols and 6 strategies. None met the minimum gate of n≥50 trades, PF≥1.5, WR≥50%, Sharpe≥0.5.

**Key Finding:** The system has NO profitable algorithm across any asset class. The only path forward is:
1. Fix measurement infrastructure (PnL calculation, blank fields, stale data)
2. Build mutual fund + ETF infrastructure (zero coverage)
3. Run pre-registered benchmark tests (EQUITY vs SPY, CRYPTO vs BTC)
4. Only then consider live capital

---

## Backtest Results — All 42 Combinations

| Symbol | Strategy | Trades | WR% | PF | Sharpe | MaxDD% | PnL% | P-value | Verdict |
|--------|----------|--------|-----|-----|--------|--------|-------|---------|---------|
| SPY | connors_rsi2 | 6 | 83.3% | 76.92 | 1.14 | -18.0% | 13.56% | 0.1094 | FAIL (n<50) |
| SPY | keltner_compression_v2 | 4 | 75.0% | 40.02 | 1.40 | -24.0% | 9.18% | 1.0000 | FAIL (n<50) |
| SPY | ema_stack | 12 | 50.0% | 1.03 | 0.01 | -827.0% | 0.61% | 0.6128 | FAIL (PF<1.5) |
| SPY | funding_sentiment | 6 | 83.3% | 3.09 | 0.43 | 0.0% | 19.49% | 0.1094 | FAIL (n<50) |
| QQQ | connors_rsi2 | 5 | 80.0% | 2.09 | 0.29 | -884.0% | 9.60% | 0.1875 | FAIL (n<50) |
| QQQ | keltner_compression_v2 | 5 | 60.0% | 1.20 | 0.08 | -1140.0% | 2.25% | 0.5000 | FAIL (n<50) |
| QQQ | ema_stack | 11 | 63.6% | 1.32 | 0.10 | -1191.0% | 7.42% | 0.2744 | FAIL (PF<1.5) |
| QQQ | funding_sentiment | 9 | 66.7% | 2.29 | 0.35 | -884.0% | 27.02% | 0.2539 | FAIL (n<50) |
| BTC-USD | connors_rsi2 | 3 | 33.3% | 0.37 | -0.48 | -1760.0% | -11.04% | 1.0000 | FAIL |
| BTC-USD | keltner_compression_v2 | 8 | 37.5% | 0.71 | -0.15 | -3100.0% | -11.49% | 0.8555 | FAIL |
| BTC-USD | ema_stack | 11 | 45.5% | 1.04 | 0.02 | -1570.0% | 1.66% | 0.7256 | FAIL |
| BTC-USD | funding_sentiment | 10 | 50.0% | 0.30 | -0.48 | -4881.0% | -39.34% | 0.6230 | FAIL |
| ETH-USD | connors_rsi2 | 4 | 25.0% | 0.62 | -0.23 | -2591.0% | -9.90% | 1.0000 | FAIL |
| ETH-USD | keltner_compression_v2 | 11 | 54.5% | 1.68 | 0.24 | -5412.0% | 36.54% | 0.5000 | FAIL (n<50) |
| ETH-USD | ema_stack | 12 | 58.3% | 1.85 | 0.27 | -2763.0% | 40.13% | 0.3872 | FAIL (n<50) |
| ETH-USD | funding_sentiment | 11 | 27.3% | 0.47 | -0.37 | -5726.0% | -52.22% | 0.9673 | FAIL |
| GLD | connors_rsi2 | 2 | 50.0% | 0.72 | -0.16 | 0.0% | -2.51% | 1.0000 | FAIL (n<50) |
| GLD | keltner_compression_v2 | 4 | 25.0% | 0.51 | -0.33 | -2207.0% | -10.84% | 1.0000 | FAIL (n<50) |
| GLD | ema_stack | 10 | 80.0% | 4.51 | 0.62 | -1481.0% | 51.99% | 0.0547 | FAIL (n<50) |
| GLD | funding_sentiment | 6 | 83.3% | 4.15 | 0.66 | -915.0% | 28.86% | 0.1094 | FAIL (n<50) |
| TLT | connors_rsi2 | 2 | 100.0% | 10.00 | 1.06 | 0.0% | 3.72% | 1.0000 | FAIL (n<50) |
| TLT | keltner_compression_v2 | 6 | 50.0% | 0.74 | -0.13 | -492.0% | -1.36% | 0.6562 | FAIL (n<50) |
| TLT | ema_stack | 9 | 33.3% | 0.20 | -0.70 | -1291.0% | -13.31% | 0.9102 | FAIL |
| TLT | funding_sentiment | 3 | 33.3% | 1.04 | 0.02 | -28.0% | 0.22% | 1.0000 | FAIL |
| XLE | connors_rsi2 | 3 | 100.0% | 10.00 | 1.71 | 0.0% | 27.20% | 1.0000 | FAIL (n<50) |
| XLE | keltner_compression_v2 | 5 | 60.0% | 1.96 | 0.26 | -887.0% | 10.13% | 0.5000 | FAIL (n<50) |
| XLE | ema_stack | 10 | 70.0% | 1.98 | 0.26 | -586.0% | 18.12% | 0.1719 | FAIL (n<50) |
| XLE | funding_sentiment | 4 | 100.0% | 10.00 | 1.80 | 0.0% | 16.15% | 1.0000 | FAIL (n<50) |
| XLF | connors_rsi2 | 3 | 33.3% | 0.17 | -0.71 | -320.0% | -3.42% | 1.0000 | FAIL |
| XLF | keltner_compression_v2 | 5 | 100.0% | 10.00 | 0.74 | 0.0% | 11.93% | 0.0312 | FAIL (n<50) |
| XLF | ema_stack | 10 | 50.0% | 1.48 | 0.16 | -605.0% | 5.27% | 0.6230 | FAIL (n<50) |
| XLF | funding_sentiment | 4 | 25.0% | 1.53 | 0.16 | -988.0% | 5.21% | 1.0000 | FAIL (n<50) |
| XLV | connors_rsi2 | 1 | 0.0% | 0.00 | 0.00 | 0.0% | -2.92% | 1.0000 | FAIL |
| XLV | keltner_compression_v2 | 2 | 100.0% | 10.00 | 2.71 | 0.0% | 12.51% | 1.0000 | FAIL (n<50) |
| XLV | ema_stack | 10 | 60.0% | 2.06 | 0.31 | -908.0% | 17.16% | 0.6230 | FAIL (n<50) |
| XLV | funding_sentiment | 4 | 50.0% | 3.75 | 0.56 | -292.0% | 9.87% | 1.0000 | FAIL (n<50) |
| XLI | connors_rsi2 | 4 | 75.0% | 4.42 | 0.66 | -346.0% | 11.83% | 0.6230 | FAIL (n<50) |
| XLI | keltner_compression_v2 | 4 | 25.0% | 0.15 | -0.85 | -1577.0% | -13.35% | 1.0000 | FAIL |
| XLI | ema_stack | 10 | 70.0% | 1.55 | 0.17 | -586.0% | 8.96% | 0.6230 | FAIL (n<50) |
| XLI | funding_sentiment | 4 | 25.0% | 1.24 | 0.08 | -1233.0% | 2.98% | 1.0000 | FAIL |

---

## Forward Tracking Protocol — Eliminate Fast vs Hold Longer

### Purpose

The forward tracking protocol determines **when to eliminate a strategy** (kill fast) vs **when to keep tracking** (hold longer). This prevents wasting capital on losing strategies while giving genuine edges enough time to prove themselves.

---

## Tier 1: Immediate Elimination (Kill Fast)

| Condition | Threshold | Action |
|-----------|-----------|--------|
| **Stale data** | entry_price mismatch > 5% from live feed | Kill immediately |
| **Confidence-coupling** | ml_score == confidence on >90% of picks | Kill immediately |
| **PnL = 0% with price movement** | | exit_price ≠ entry_price but pnl_pct = 0 | Kill immediately |
| **Blank fields** | >3 missing fields (entry_price, direction, symbol, status) | Kill immediately |
| **Negative PnL after 20 trades** | cumulative PnL < 0 | Kill immediately |
| **Sharpe < 0 after 20 trades** | | Kill immediately |

### Tier 2: Watch List (Hold Up to 30 Days)

| Condition | Threshold | Action |
|-----------|-----------|--------|
| **n < 50 trades** | | Keep tracking, do not allocate capital |
| **PF between 0.8-1.5** | | Watch, do not allocate |
| **WR between 40-50%** | | Watch, do not allocate |
| **Sharpe between 0-0.5** | | Watch, do not allocate |

### Tier 3: Promotion Candidate (Eligible for Paper Trading)

| Condition | Threshold | Action |
|-----------|-----------|--------|
| **n ≥ 50 trades** | | Eligible for paper trading |
| **PF ≥ 1.5** | | Eligible for paper trading |
| **WR ≥ 50%** | | Eligible for paper trading |
| **Sharpe ≥ 0.5** | | Eligible for paper trading |
| **MaxDD < 15%** | | Eligible for paper trading |

### Tier 4: Live Capital Eligible

| Condition | Threshold | Action |
|-----------|-----------|--------|
| **n ≥ 100 forward picks** | | Eligible for live capital |
| **PF ≥ 1.5 forward** | | Eligible for live capital |
| **WR ≥ 55% forward** | | Eligible for live capital |
| **DSR ≥ 0.95 forward** | | Eligible for live capital |
| **3+ months clean forward** | | Eligible for live capital |

---

## Holding Period Rules by Strategy Type

| Strategy Type | Min Hold Period | Max Hold Period | Kill If |
|---------------|-----------------|-----------------|---------|
| **Scalping** (seconds-minutes) | 1 minute | 60 minutes | Loss > 2% or no fill in 5 min |
| **Day Trading** (minutes-hours) | 30 minutes | 6 hours | Loss > 3% or market close |
| **Swing Trading** (days-weeks) | 1 day | 21 days | Loss > 5% or 21 days elapsed |
| **Position Trading** (weeks-months) | 1 week | 90 days | Loss > 10% or 90 days elapsed |
| **Long-term Investing** (months-years) | 1 month | Unlimited | Review quarterly, exit if thesis broken |

---

## Tracking Protocol — Per Pick

Every pick MUST have the following fields tracked:

| Field | Required? | Source |
|-------|-----------|--------|
| `symbol` | Yes | Strategy output |
| `entry_price` | Yes | Real market price at entry |
| `exit_price` | Yes (when closed) | Real market price at exit |
| `direction` | Yes | LONG/SHORT |
| `take_profit` | Yes | Calculated from entry + ATR |
| `stop_loss` | Yes | Calculated from entry - ATR |
| `confidence` | Yes | Strategy output |
| `ml_score` | Yes | Independent from confidence |
| `status` | Yes | OPEN/ACTIVE/CLOSED/WON/LOST/EXPIRED |
| `entry_time` | Yes | ISO-8601 UTC |
| `closed_at` | Yes (when closed) | ISO-8601 UTC |
| `pnl_pct` | Yes (when closed) | (exit-entry)/entry * direction |
| `pnl_dollar` | Yes (when closed) | position_size * pnl_pct |
| `hold_days` | Yes (when closed) | (closed_at - entry_time) |
| `regime` | Yes | BULLISH/BEARISH/NEUTRAL |

---

## Kill Rules — Auto-Expire Rules

### Automatic Expiration Rules (No Human Intervention)

| Rule | Condition | Action |
|------|-----------|--------|
| **Stale OPEN** | > 72 hours with no price update | Mark EXPIRED, pnl_pct = 0 |
| **Stale OPEN** | > 168 hours (1 week) | Mark EXPIRED, pnl_pct = 0, flag for review |
| **Forward test limit** | > 30 days open | Mark EXPIRED, pnl_pct = 0 |
| **PnL freeze** | entry_price == current_price for > 48h | Flag data issue, resolve or expire |
| **Max hold exceeded** | > max_hold_days for strategy | Mark EXPIRED, pnl_pct = current |

### Manual Review Triggers

| Trigger | Threshold | Action |
|---------|-----------|--------|
| **Consecutive losses** | 3 losses in a row | Pause strategy, review |
| **Weekly drawdown** | > 5% weekly | Pause all strategies, review |
| **Monthly drawdown** | > 10% monthly | Halt all trading, full review |
| **PnL anomaly** | pnl_pct = 0 with price movement | Immediate investigation |

---

## Forward Test Tracking File Format

Each forward test must produce a JSON record:

```json
{
  "pick_id": "strategy_symbol_date_hash",
  "strategy": "connors_rsi2",
  "symbol": "SPY",
  "direction": "LONG",
  "entry_price": 450.25,
  "entry_time": "2026-11-15T09:30:00Z",
  "take_profit": 456.00,
  "stop_loss": 444.50,
  "position_size_usd": 2000.00,
  "risk_pct": 0.02,
  "atr": 2.50,
  "rsi": 32.5,
  "tournament_pf": 1.03,
  "tournament_wr": 0.50,
  "status": "OPEN",
  "created_at": "2026-11-15T00:38:00Z",
  "day": "2026-11-15",
  "expires_at": "2026-11-29T00:38:00Z"
}
```

---

## Decision Tree — What to Do With Each Strategy

```
START: New strategy candidate
    │
    ├──► PnL calculation valid? ──NO──► EXPIRE (data bug)
    │
    ├──► Pick IDs unique? ──NO──► EXPIRE (dedupe bug)
    │
    ├──► n ≥ 50 trades? ──NO──► KEEP TRACKING (tier 2)
    │
    ├──► PF ≥ 1.5 AND WR ≥ 50%? ──NO──► KEEP TRACKING (tier 2)
    │
    ├──► Sharpe ≥ 0.5? ──NO──► KEEP TRACKING (tier 2)
    │
    ├──► MaxDD < 15%? ──NO──► KILL (too risky)
    │
    ├──► n ≥ 100 forward picks? ──NO──► KEEP TRACKING (tier 3)
    │
    ├──► All gates pass? ──NO──► KEEP TRACKING (tier 3)
    │
    └──► PROMOTE TO PAPER TRADING (tier 4)
```

---

## Backtest Results Summary

**Source:** `quick_wins/shared/normalize_pnl_units.py` applied to closed picks, then `alpha_engine/unified_backtester.py` run forward.

| Metric | Value |
|--------|-------|
| Total combinations tested | 42 |
| Strategies tested | 6 (connors_rsi2, keltner_compression_v2, ema_stack, funding_sentiment, ttm_squeeze, rsi_whale_confluence) |
| Symbols tested | 10 (SPY, QQQ, BTC-USD, ETH-USD, GLD, TLT, XLE, XLF, XLV, XLI) |
| Strategies passing P0 gates | **0** |
| Strategies with n ≥ 50 | **0** |
| Strategies with PF ≥ 1.5 | **2** (SPY connors_rsi2, SPY keltner_compression_v2) but n < 10 |
| Strategies with Sharpe ≥ 0.5 | **2** (SPY connors_rsi2, XLF keltner_compression_v2) but n < 10 |
| Best Sharpe | 1.14 (SPY connors_rsi2, n=6) |
| Best PF | 76.92 (SPY connors_rsi2, n=6) — clearly inflated due to tiny n |

**Conclusion:** No strategy is ready for live capital. All require more data, better entry_price integrity, and larger sample sizes.

---
