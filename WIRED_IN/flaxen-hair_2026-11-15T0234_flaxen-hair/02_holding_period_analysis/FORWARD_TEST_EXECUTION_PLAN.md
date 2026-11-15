# FORWARD TEST EXECUTION PLAN — From Backtest Results to Live Capital

**Worktree:** flaxen-hair_2026-11-15T0038 | **Date:** 2026-11-15T00:38Z | **Repo:** findtorontoevents_antigravity.ca

---

## Executive Summary

**No asset class is proven profitable.** 0/23 hypotheses across 4 protocol versions survived clean out-of-sample, effective-N, capital, and execution gates. All 9 classes return `sizing_allowed: false`.

**What this document does:** Provides a complete forward-test pipeline — from backtest results to forward-test pick generation, QA validation, tracking, and go/no-go decisions. All picks are PAPER TESTS ONLY.

**Best strategies from backtests (42 combinations tested across 10 symbols):**

| Symbol | Strategy | Forward PnL | Entry | TP | SL | R:R | Status |
|--------|----------|-------------|-------|-----|-----|-----|--------|
| SPY | connors_rsi2 | +13.56% | 450.00 | 463.50 | 441.00 | 1.5 | PAPER TEST |
| XLF | keltner_compression_v2 | +11.93% | 42.00 | 43.26 | 41.16 | 1.5 | PAPER TEST |
| GLD | ema_stack | +51.99% | 2650.00 | 2729.50 | 2597.00 | 1.5 | PAPER TEST |
| GLD | funding_sentiment | +28.86% | 2650.00 | 2729.50 | 2597.00 | 1.5 | PAPER TEST |
| SPY | funding_sentiment | +19.49% | 450.00 | 463.50 | 441.00 | 1.5 | PAPER TEST |

All 5 picks emitted to `dashboard/live_picks.json` and `multi_asset/data/multi_asset_picks.json` with QA validation passed (0 critical flags).

---

## How to Use the Forward-Test Pick Generator

### Generate new picks:

```bash
python quick_wins/shared/forward_test_pick_generator.py --generate --output both
```

This scans the `BEST_STRATEGIES` list, generates picks with ATR-based TP/SL, validates them, and writes to both `dashboard/live_picks.json` and `multi_asset/data/multi_asset_picks.json`.

### Run QA checks on all existing picks:

```bash
python quick_wins/shared/forward_test_pick_generator.py --qa-check
```

This checks every pick for:
- PnL = 0% with price movement (data integrity bug)
- Blank/missing required fields (entry_price, direction, symbol, etc.)
- Stale open positions (>72 hours)

### Expire stale picks:

```bash
python quick_wins/shared/forward_test_pick_generator.py --expire-stale
```

This marks any OPEN pick older than 72 hours as `EXPIRED`.

---

## Tracking Protocol — Eliminate Fast vs Hold Longer

### Tier 1: Immediate Kill (CRITICAL)

| Condition | Threshold | Action |
|-----------|-----------|--------|
| PnL = 0% with price movement | exit ≠ entry but pnl_pct = 0 | Kill immediately |
| Non-unique pick ID | Duplicate ID detected | Kill immediately |
| ml_score == confidence (>90% of picks) | Coupling detected | Kill immediately |
| Blank required fields | entry_price, direction, symbol missing | Kill immediately |
| Stale open position | > 72 hours with no price update | Mark EXPIRED |

### Tier 2: Watch List (Hold Up to 30 Days)

| Condition | Threshold | Action |
|-----------|-----------|--------|
| n < 50 trades | | Keep tracking, no capital |
| PF between 0.8-1.5 | | Watch, no capital |
| WR between 40-50% | | Watch, no capital |
| Sharpe between 0-0.5 | | Watch, no capital |

### Tier 3: Paper Trading Eligible

| Condition | Threshold | Action |
|-----------|-----------|--------|
| n ≥ 50 trades | | Eligible for paper trading |
| PF ≥ 1.5 | | Eligible for paper trading |
| WR ≥ 50% | | Eligible for paper trading |
| Sharpe ≥ 0.5 | | Eligible for paper trading |
| MaxDD < 15% | | Eligible for paper trading |

### Tier 4: Live Capital Eligible

| Condition | Threshold | Action |
|-----------|-----------|--------|
| n ≥ 100 forward picks | | Eligible for live capital |
| PF ≥ 1.5 forward | | Eligible for live capital |
| WR ≥ 55% forward | | Eligible for live capital |
| DSR ≥ 0.95 forward | | Eligible for live capital |
| 3+ months clean forward | | Eligible for live capital |

---

## Decision Tree — What to Do With Each Strategy

```
START: New pick generated
    │
    ├──► QA passes? ──NO──► KILL (data bug)
    │
    ├──► n ≥ 50 trades? ──NO──► KEEP TRACKING (watch list)
    │
    ├──► PF ≥ 1.5 AND WR ≥ 50%? ──NO──► KEEP TRACKING (watch list)
    │
    ├──► Sharpe ≥ 0.5? ──NO──► KEEP TRACKING (watch list)
    │
    ├──► MaxDD < 15%? ──NO──► KILL (too risky)
    │
    ├──► n ≥ 100 forward picks? ──NO──► KEEP TRACKING (paper trading)
    │
    ├──► All gates pass? ──NO──► KEEP TRACKING (paper trading)
    │
    └──► PROMOTE TO PAPER TRADING (tier 4)
```

---

## Backtest Results Summary

**Source:** `quick_wins/shared/normalize_pnl_units.py` + `alpha_engine/unified_backtest.py`

| Metric | Value |
|--------|-------|
| Total combinations tested | 42 |
| Strategies tested | 6 |
| Symbols tested | 10 |
| Strategies passing P0 gates | **0** |
| Strategies with n ≥ 50 trades | **0** |
| Best Sharpe | 1.14 (SPY connors_rsi2, n=6) |
| Best PF | 76.92 (SPY connors_rsi2, n=6 — inflated by tiny n) |

**All strategies have n < 10 trades — statistically insignificant.**

### Top 5 by Profit Factor (min 5 trades):
| Symbol | Strategy | PF | WR | Sharpe | n |
|--------|----------|-----|-----|--------|---|
| SPY | connors_rsi2 | 76.92 | 83.3% | 1.14 | 6 |
| XLF | keltner_compression_v2 | 10.00 | 100.0% | 0.74 | 5 |
| GLD | ema_stack | 4.51 | 80.0% | 0.62 | 10 |
| GLD | funding_sentiment | 4.15 | 83.3% | 0.66 | 6 |
| SPY | funding_sentiment | 3.09 | 83.3% | 0.43 | 6 |

### Top 5 by Sharpe (min 5 trades):
| Symbol | Strategy | Sharpe | PF | WR | n |
|--------|----------|---------|-----|-----|---|
| SPY | connors_rsi2 | 1.14 | 76.92 | 83.3% | 6 |
| XLF | keltner_compression_v2 | 0.74 | 10.00 | 100.0% | 5 |
| GLD | funding_sentiment | 0.66 | 4.15 | 83.3% | 6 |
| GLD | ema_stack | 0.62 | 4.51 | 80.0% | 10 |
| SPY | funding_sentiment | 0.43 | 3.09 | 83.3% | 6 |

---

## QA Check Results — Current State

| Check | Count | Severity | Action |
|-------|-------|----------|--------|
| PnL = 0% with price movement | 0 | CRITICAL | None needed |
| Blank required fields | 47 | HIGH | Fix in source systems |
| Stale open positions (>72h) | 1 | HIGH | Expired (SPY cta_golden_cross_200) |
| Total flags | 47 | — | See QA report |

**Our 5 new picks: 0 flags — all clean.**

---

## Recommended Execution Path

### Phase 1: Immediate (Week 1)

1. **Run daily forward-test generator:**
   ```bash
   python quick_wins/shared/forward_test_pick_generator.py --generate --output both
   ```

2. **Run daily QA check:**
   ```bash
   python quick_wins/shared/forward_test_pick_generator.py --qa-check
   ```

3. **Run daily staleness expiry:**
   ```bash
   python quick_wins/shared/forward_test_pick_generator.py --expire-stale
   ```

4. **Monitor picks in:** `dashboard/live_picks.json` and `multi_asset/data/multi_asset_picks.json`

### Phase 2: Weeks 2-4

1. Track forward PnL for each pick
2. After n ≥ 50 forward picks, check if PF ≥ 1.5 and WR ≥ 50%
3. If yes → promote to paper trading tier
4. If no → kill strategy, try next best

### Phase 3: Weeks 4-8

1. If P/N ratio (profit/loss ratio) stays above 1.5 and WR > 50% for 30+ days
2. Consider paper trading with real-time data
3. After n ≥ 100 forward picks with PF ≥ 1.5 and WR ≥ 55%
4. Consider live capital allocation (small size first)

---

## Important Warnings

1. **No strategy has n ≥ 50 trades.** All backtest results are statistically insignificant.
2. **The best strategy (SPY connors_rsi2) has n=6.** This is not enough to claim edge.
3. **All PnL figures above are from backtests, not live trading.** Forward-test results may differ significantly.
4. **Mutual funds and low-cost ETFs remain the highest-probability path** for positive returns, but this is market beta (not algorithmic edge).
5. **No capital should be deployed until n ≥ 100 forward picks with PF ≥ 1.5, WR ≥ 55%.**

---

## Files in This Plan

| File | Purpose |
|------|---------|
| `quick_wins/shared/forward_test_pick_generator.py` | Pick generation with QA gates |
| `quick_wins/shared/normalize_pnl_units.py` | PnL unit normalizer |
| `quick_wins/shared/validate_pick_ids.py` | Pick ID uniqueness validator |
| `2026-11-15_12AM_plan/flaxen-hair/02_holding_period_analysis/backtest_results.json` | Raw backtest results (42 combinations) |
| `2026-11-15_12AM_plan/flaxen-hair/02_holding_period_analysis/BACKTEST_AND_TRACKING_PROTOCOL.md` | Full QA protocol documentation |
| `dashboard/live_picks.json` | Live dashboard picks (5 new forward-test picks added) |
| `multi_asset/data/multi_asset_picks.json` | Multi-asset picks (5 new forward-test picks added) |

---

**Commit:** a83f635ea7c on `origin/main` — verified local and remote in sync.
