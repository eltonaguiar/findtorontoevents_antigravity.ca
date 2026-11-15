# Forward-Test Tracking Protocol — Fast Elimination vs Hold Longer

**Purpose:** A simple, rules-based system to track forward-tested strategies and decide quickly whether to **kill** (eliminate fast) or **hold longer** (continue testing). Designed to prevent over-testing losing strategies while giving genuine edges enough time to prove themselves.

**Date:** 2026-11-15 (AM)
**Applies to:** All forward-tested picks from any asset class (EQUITY, CRYPCO, ETF, MF, etc.)

---

## Core Principle

> **Eliminate fast, hold longer only if arithmetic justifies it.**  
> Most strategies will fail within 20-50 trades. A genuine edge should show positive expectancy early. Don't give losing strategies extra chances "just to see."

---

## Part 1: Fast Elimination — Kill Signals (EXIT Criteria)

Kill a strategy immediately (do not forward test further) if ANY of these trigger:

| Kill Signal | Threshold | Rationale |
|-------------|-----------|-----------|
| **K1 — Negative expectancy after costs** | Cumulative net PnL < 0 after 20 trades | If you can't make money after costs in 20 trades, the edge is gone or never existed. |
| **K2 — Win rate < 35%** | WR < 35% after 30 trades | Below ~35% requires extremely high R:R to survive; almost never sustainable. |
| **K3 — Profit factor < 0.80** | PF < 0.80 after 25 trades | Gross losses exceed gross profits by 25%+; structural loser. |
| **K4 — Max drawdown > 15%** | Drawdown from peak > 15% of starting capital | Capital preservation violation. Halt immediately. |
| **K5 — Sharpe < 0** | Negative Sharpe after 30 trades | Risk-adjusted return is negative; not worth the risk. |
| **K6 — Zero trades in 14 days** | No signals generated for 14 consecutive calendar days | Strategy is dormant or broken; stop allocating attention. |
| **K7 — Consecutive losses** | 8 losing trades in a row | Statistical anomaly or regime change; pause and re-evaluate. |
| **K8 — Cost ratio > 200%** | Total costs > 200% of gross profit | Costs are eating the edge; strategy untradeable at current size. |

**Kill decision:** If any K1-K8 triggers, the strategy moves to **ELIMINATED** status. No further forward testing. Log reason.

---

## Part 2: Hold Longer — Promote Signals (CONTINUE Criteria)

A strategy earns the right to continue forward testing (beyond the initial 30-trade trial) only if ALL of these hold:

| Promote Signal | Threshold | Rationale |
|----------------|-----------|-----------|
| **P1 — Positive net expectancy** | Cumulative net PnL > 0 after 20 trades | Must be making money after costs early. |
| **P2 — Win rate ≥ 45%** | WR ≥ 45% after 30 trades | Reasonable baseline for a sustainable edge. |
| **P3 — Profit factor ≥ 1.10** | PF ≥ 1.10 after 25 trades | Gross profits exceed gross losses by 10%+. |
| **P4 — Max drawdown < 10%** | Drawdown < 10% of starting capital | Conservative capital preservation during trial. |
| **P5 — Sharpe > 0.5** | Sharpe > 0.5 after 30 trades | Positive risk-adjusted return. |
| **P6 — Trade frequency ≥ 1 per week** | ≥ 1 trade/week average | Strategy is active enough to generate meaningful data. |
| **P7 — No consecutive loss streak > 5** | Max consecutive losses ≤ 5 | Not in a persistent losing regime. |

**Promote decision:** If P1-P7 all hold after 30 trades, the strategy moves to **EXTENDED TEST** status (continue forward testing up to 100 trades / 3 months).

---

## Part 3: The Decision Lifecycle

```
NEW STRATEGY (forward test start)
        │
        ▼
┌─────────────────┐
│ TRIAL PHASE     │  First 30 trades OR first 30 days,
│                 │ whichever comes first
│ Check: K1-K8    │  Kill signals checked after every trade
│ Check: P1-P7    │  Promote signals checked at trade 30
└─────────────────┘
        │
    ┌───┴───┐
    ▼       ▼
KILL     PROMOTE
(ELIMINATED)  (EXTENDED TEST)
                │
                ▼
    ┌─────────────────────┐
    │ EXTENDED TEST       │  Up to 100 trades OR 3 months,
    │                     │ whichever comes first
    │ Check: Money-ready  │  Full gates (PF≥1.15, WR≥50%,
    │ gates               │  Sharpe≥1.0, DSR≥0.95, PBO≤0.10,
    │                     │ MaxDD<15%, n≥100)
    └─────────────────────┘
                │
    ┌───────────┴───────────┐
    ▼                       ▼
FAIL                    PASS
(ELIMINATED)        (MONEY-READY — consider capital allocation)
```

---

## Part 4: Time-Based Kill Rules (Independent of Trade Count)

Even if trade count is low, apply these calendar-based halts:

| Time Window | Action | Condition |
|-------------|--------|-----------|
| **Day 1-7** | Monitor only | No kill/promote yet (warm-up period) |
| **Day 8-30** | Kill if K1-K4 triggers | Early warning signals |
| **Day 31-60** | Kill if K1-K8 triggers | Full kill criteria active |
| **Day 61-90** | Decision required | Either promote to extended test or eliminate |
| **Day 91+** | Auto-eliminate | If not promoted by day 90, strategy is dead |

**Rule:** No strategy forward-tests longer than 90 days without reaching EXTENDED TEST or ELIMINATED status.

---

## Part 5: Tracking Template (CSV Format)

Use this single-row-per-strategy tracking log. One file: `forward_test_tracker.csv`

| Column | Description | Example |
|--------|-------------|---------|
| `strategy_id` | Unique strategy identifier | `EQ_RSI2_SPY_20261115` |
| `asset_class` | EQUITY / CRYPCO / ETF / MF / etc. | `EQUITY` |
| `symbol` | Trading symbol | `SPY` |
| `start_date` | Forward test start date | `2026-11-15` |
| `total_trades` | Cumulative trade count | `23` |
| `winning_trades` | Count of winning trades | `11` |
| `losing_trades` | Count of losing trades | `12` |
| `win_rate_pct` | Win rate percentage | `47.83` |
| `gross_profit_pct` | Sum of winning trade PnL | `+8.50` |
| `gross_loss_pct` | Sum of losing trade PnL (abs) | `-6.20` |
| `profit_factor` | Gross profit / gross loss | `1.37` |
| `net_pnl_pct` | Net PnL after costs | `+2.30` |
| `max_drawdown_pct` | Max drawdown from peak | `-4.10` |
| `sharpe` | Sharpe ratio | `0.62` |
| `consecutive_losses` | Current loss streak | `2` |
| `max_consecutive_losses` | Worst loss streak | `5` |
| `days_active` | Calendar days since start | `18` |
| `trades_per_week` | Avg trades per week | `1.8` |
| `cost_ratio_pct` | Costs / gross profit × 100 | `12.5` |
| `status` | TRIAL / EXTENDED / ELIMINATED / MONEY_READY | `TRIAL` |
| `kill_reason` | K1-K8 code if eliminated, else blank | `K1` |
| `last_updated` | Timestamp of last update | `2026-12-03T14:30:00Z` |

---

## Part 6: Daily Update Routine (5 minutes)

Every trading day, after market close:

1. **Update `forward_test_tracker.csv`** with today's trade results for each active strategy.
2. **Recompute K1-K8** for each strategy in TRIAL status.
3. **Recompute P1-P7** for any strategy at trade 30.
4. **Recompute money-ready gates** for any strategy in EXTENDED TEST.
5. **Log decisions:** If any strategy hit a kill signal, mark ELIMINATED with reason. If any hit promote criteria, mark EXTENDED.
6. **Archive eliminated strategies** to `forward_test_eliminated.csv` with kill reason and final stats.

---

## Part 7: Fast Elimination Examples

### Example 1 — Fast Kill (Day 12, 14 trades)
| Metric | Value | Kill Signal |
|--------|-------|-------------|
| Net PnL | -3.2% | K1 (negative expectancy after costs) |
| Win rate | 28.6% | K2 (WR < 35%) |
| Max DD | -6.1% | — |
| Trades | 14 | — |

**Decision:** ELIMINATED. Reason: K1 + K2. Do not test further.

### Example 2 — Hold Longer / Promote (Day 28, 32 trades)
| Metric | Value | Promote Signal |
|--------|-------|----------------|
| Net PnL | +4.5% | P1 (positive expectancy) |
| Win rate | 53.1% | P2 (WR ≥ 45%) |
| Profit factor | 1.28 | P3 (PF ≥ 1.10) |
| Max DD | -3.8% | P4 (DD < 10%) |
| Sharpe | 0.71 | P5 (Sharpe > 0.5) |
| Trades/week | 2.1 | P6 (active) |
| Max consecutive losses | 4 | P7 (≤ 5) |

**Decision:** PROMOTE to EXTENDED TEST. Continue up to 100 trades / 3 months.

### Example 3 — Extended Test Failure (Day 75, 87 trades)
| Metric | Value | Gate |
|--------|-------|------|
| Net PnL | +1.2% | — |
| Win rate | 46.0% | WR ≥ 50% ✗ |
| Profit factor | 1.08 | PF ≥ 1.15 ✗ |
| Sharpe | 0.42 | Sharpe ≥ 1.0 ✗ |
| DSR | 0.12 | DSR ≥ 0.95 ✗ |
| PBO | 0.89 | PBO ≤ 0.10 ✗ |
| Max DD | -9.2% | MaxDD < 15% ✓ |

**Decision:** ELIMINATED. Fails full money-ready gates (WR, PF, Sharpe, DSR, PBO). Do not deploy capital.

---

## Part 8: When to Hold Longer vs Eliminate — Decision Matrix

| Situation | Recommendation |
|-----------|---------------|
| Negative PnL after 20 trades | **Eliminate immediately** (K1) |
| Positive PnL but Sharpe < 0 after 30 trades | **Eliminate** (K5 — risk not worth it) |
| WR < 35% after 30 trades | **Eliminate** (K2) |
| All P1-P7 pass at trade 30 | **Hold longer / Extended test** |
| Extended test (60+ trades) but PF < 1.15 | **Eliminate** (no edge after costs) |
| Extended test passes all gates | **Consider capital allocation** (small size first) |
| No trades for 14 days | **Eliminate** (K6 — dormant) |
| 8 consecutive losses | **Eliminate** (K7 — regime broken) |

---

## Part 9: Integration with QA Protocol

Before any strategy enters forward testing, it must pass QA Gate 0 (PnL=0% validation) and Gate 1 (blank-field check) from `08_qa_validation/qa_protocol.md`. Forward testing without QA validation is prohibited.

**Forward test only starts after:**
- Strategy passed backtest with PF ≥ 1.0 (not ≥1.15 yet — that's for money-ready)
- Strategy passed QA Gates 0-1
- Strategy has a defined `strategy_id` and is registered in `forward_test_tracker.csv`

---

## Part 10: Files to Maintain

| File | Purpose |
|------|---------|
| `forward_test_tracker.csv` | Active strategies being forward tested |
| `forward_test_eliminated.csv` | Eliminated strategies with kill reasons |
| `forward_test_money_ready.csv` | Strategies that passed all money-ready gates |
| `forward_test_daily_log.md` | Daily notes on decisions made |

**Location:** `alpha_engine/data/forward_testing/` (create this directory)

---

## Bottom Line

This protocol forces **fast elimination** of losing strategies (typically within 20-30 trades or 30-60 days) and only **holds longer** strategies that show positive expectancy, acceptable drawdown, and acceptable risk-adjusted returns early. The goal is to stop wasting capital and attention on strategies that are never going to work, while giving the rare genuine edge enough runway to reach 100+ trades and full money-ready validation.

**Remember: The simulation results (0/37 combos passed all gates) show that most strategies will be eliminated quickly. That is the correct outcome.**
