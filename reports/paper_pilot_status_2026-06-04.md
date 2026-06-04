# Paper Pilot Status — 2026-06-04 11:30 UTC

Quick reality check on what's actually paper-piloting toward live capital allocation.

## Bootstrap-tracked sleeves (canonical source)

| Sleeve | Lab PF | Lab n | Forward n | Forward WR | Forward PF | Gates blocking |
|---|---:|---:|---:|---:|---:|---|
| b_flip_price_roc | 35.91 | 157 | **2** | 50.0% | 3.12 | n<100, pf<0.85*oos |
| inverse_ml_btc_15m | 34.46 | 65 | **3** | 66.7% | 2.24 | n<100, pf<0.85*oos |

**any_promotion_ready: false.**

## Independent paper-pilot state files (not bootstrap-tracked)

| Strategy | Last run | Current state | Notes |
|---|---|---|---|
| etf_dual_momentum | 2026-06-04 11:24Z | OPEN XLK BUY @ $195.76 since 2026-06-02 | Holding |
| equity_vix_regime_rotator | 2026-06-04 11:24Z | RISK_ON regime, 25% each SPY/QQQ/IWM/XLK | Paper-only |
| macd_rsi_m048 | 2026-06-04 (workflow OK) | static 65 closed / 75.4% WR / day 27 of 30 | **No new trades for 22 days** — log frozen at lab snapshot |
| inverse_ml_btc | 2026-06-04 closed BTC SELL +0.99% | 6 trades total | Modest |
| b_flip_price_roc | 5 log rows | sparse | |

## Reality

The 75.4% WR on macd_rsi is a **lab-backtest snapshot** that the daily workflow logs unchanged — it's not 27 days of live paper trading. The bootstrap-forward path (b_flip_price_roc / inverse_ml_btc_15m) is the truthful forward-test surface, and both sleeves are at n<5 forward trades after ~22 days.

**Bottleneck**: signal rarity. Lab strategies generated 65-157 trades historically but forward gen at ~1 trade per 7-11 days. At that rate, n>=100 takes 2+ years.

## Recommendations

1. **Audit the entry filters** on b_flip + inverse_ml — are they too tight in current regime?
2. **Expand universe**: b_flip on ETHUSDT only is too narrow; add 5-10 majors.
3. **Add timeframe variants**: 15m + 1h side-by-side to multiply signal opportunities.
4. **Don't conflate macd_rsi_m048 paper log with live paper trading** — it's snapshotting strategy_performance.json, not generating new signals.
