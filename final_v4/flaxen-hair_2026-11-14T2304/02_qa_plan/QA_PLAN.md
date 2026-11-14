# QA PLAN — Financial Prediction Data Quality & Validation

**Worktree:** flaxen-hair_2026-11-14T2304 | **Date:** 2026-11-14T23:04Z

This QA plan addresses the user's specific requirements:
1. **PnL = 0% validation** against real market data (open-to-closed and open-to-current periods)
2. **Blank field flags** especially under open and recently closed items
3. **Mutual funds + ETFs solid picks** validation
4. **Reasonability checks** on all pick data

---

## QA Framework Overview

| QA Check | Severity | Frequency | Source Data | Auto-Fail |
|----------|----------|-----------|-------------|-----------|
| PnL=0% with price movement | CRITICAL | Every scan | dashboard/live_picks.json | Yes |
| Blank required fields | HIGH | Every scan | All pick files | Yes |
| Stale open positions (>72h) | HIGH | Every scan | live_picks.json | No (warn) |
| Stale open positions (>168h) | CRITICAL | Every scan | live_picks.json | Yes |
| Recently closed missing exit data | HIGH | Every scan | All pick files | Yes |
| Mutual fund NAV staleness (>24h) | HIGH | Daily | mutual_fund_nav_cache/ | Yes |
| ETF bid-ask spread > threshold | MEDIUM | Every scan | ETF price feeds | No (warn) |
| Cross-source PnL inconsistency | CRITICAL | Daily | Multiple stores | Yes |
| Negative expectancy | CRITICAL | Weekly | Backtest results | Yes |

---

## QA Check 1: PnL = 0% Validation Against Real Market Data

### Problem
Many live picks show `pnl_pct = 0` or `unrealized_pnl_pct = 0` despite non-trivial price movement. This indicates resolver bugs, data feed issues, or calculation errors.

### Validation Method

For every pick with `pnl_pct` ≈ 0 (|pnl_pct| < 0.0001):

1. **Recompute from prices:** `calc_pnl = (exit_price / entry_price - 1) * direction_factor`
   - LONG: `pnl = (exit / entry - 1)`
   - SHORT: `pnl = (entry / exit - 1)`
   - Direction factor: +1 for LONG, -1 for SHORT

2. **Compare against real market data:**
   - Fetch current price from Binance (crypto), Nasdaq (stocks/ETFs), or er-api (forex)
   - Compute expected PnL from entry to current
   - If stored PnL=0 but real PnL ≠ 0, flag as CRITICAL

3. **Time period checks:**
   - **Open-to-closed:** For closed picks, compare entry→exit prices vs stated PnL
   - **Open-to-current:** For active picks, compare entry→current_price vs stated unrealized PnL
   - **Open-to-open:** For picks still open, verify entry_price matches the price at entry_time

### Implementation

See `alpha_engine/risk_qa_validator.py` → `validate_pnl_zero()` function (proposed in PROPOSED_EDITS.md, Edit 5).

**Example check:**
```python
pick = {
    "symbol": "JNK",
    "entry_price": 92.42,
    "exit_price": 92.8958,  # or current_price
    "pnl_pct": 0.0,  # SUSPICIOUS — price moved but PnL is 0
    "direction": "LONG"
}
# Expected: (92.8958 / 92.42 - 1) = +0.51% (LONG)
# Actual: 0.0% → FLAG as CRITICAL
```

### Pass Criteria
- Zero picks with `pnl_pct ≈ 0` AND non-trivial price movement (>0.01%)
- All recomputed PnL values match stored values within 0.05pp tolerance
- All open picks have realistic unrealized PnL (not artificially 0)

---

## QA Check 2: Blank Field Flags — Especially Open & Recently Closed Items

### Required Fields by Pick Status

| Field | OPEN/ACTIVE | CLOSED/WON/LOST | TP_HIT/SL_HIT |
|-------|-------------|-----------------|---------------|
| symbol | ✅ Required | ✅ Required | ✅ Required |
| entry_price | ✅ Required | ✅ Required | ✅ Required |
| direction | ✅ Required | ✅ Required | ✅ Required |
| strategy | ✅ Required | ✅ Required | ✅ Required |
| asset_class | ✅ Required | ✅ Required | ✅ Required |
| entry_time | ✅ Required | ✅ Required | ✅ Required |
| status | ✅ Required | ✅ Required | ✅ Required |
| stop_loss | ✅ Required | ✅ Required | ✅ Required |
| take_profit | ✅ Required | ✅ Required | ✅ Required |
| exit_price | ❌ Optional | ✅ Required | ✅ Required |
| exit_date | ❌ Optional | ✅ Required | ✅ Required |
| closed_at | ❌ Optional | ✅ Required | ✅ Required |
| pnl_pct | ❌ Optional | ✅ Required | ✅ Required |

### Validation Rules

1. **Open items:** All `required_open` fields must be non-null, non-empty
2. **Recently closed items:** All `required_closed` fields must be non-null, non-empty
3. **Blank = empty string, None, null, or "N/A"**

### Severity Matrix

| Missing Fields Count | Severity | Action |
|---------------------|----------|--------|
| 0 | PASS | Emit pick |
| 1-2 | MEDIUM | Warn, reduce size 50% |
| 3+ | HIGH | Block pick from emission |
| Any critical field (symbol, entry_price, direction) missing | CRITICAL | Immediate block |

### Implementation

See `alpha_engine/risk_qa_validator.py` → `validate_blank_fields()` and `validate_open_items()` / `validate_recently_closed()` functions.

---

## QA Check 3: Mutual Fund Solid Pick Validation

### Pre-Emission Criteria (All Must Pass)

| Criterion | Threshold | Check |
|-----------|-----------|-------|
| Expense ratio | ≤ 0.20% | `expense_ratio <= 0.002` |
| Load fees | None | `load_fee == 0` |
| 12b-1 fees | None | `b12b_fee == 0` |
| Minimum investment | ≤ $1,000 | `min_investment <= 1000` |
| AUM | ≥ $1B | `aum >= 1_000_000_000` |
| Turnover | ≤ 20% | `turnover <= 0.20` |
| Tracking error | ≤ 0.25% | `tracking_error <= 0.0025` |
| Track record | ≥ 10 years | `track_record_years >= 10` |
| Category benchmark | Beat benchmark net of fees | `net_return_5yr > benchmark_5yr` |
| NAV freshness | ≤ 24h stale | `nav_age_hours <= 24` |
| Classification | MUTUAL_FUND class | `asset_class == "MUTUAL_FUND"` |

### Mutual Fund NAV Validation

- NAV is priced once daily at 16:00 ET
- No intraday price movement (mutual funds don't trade intraday)
- PnL computed on NAV close-to-close only
- T+1 settlement: today's NAV available tomorrow
- Gap detection: missing NAV dates flagged, not backfilled

### ETF Solid Pick Criteria

| Criterion | Threshold |
|-----------|-----------|
| Expense ratio | ≤ 0.10% |
| AUM | ≥ $500M |
| Avg daily volume | ≥ $10M |
| Bid-ask spread | ≤ 0.05% |
| Tracking error | ≤ 0.20% |
| Track record | ≥ 5 years |
| No leverage/inverse | Plain beta only |
| Net return > benchmark | Over 3+ years after costs |

---

## QA Check 4: Reasonability Checks

### Price Reasonability

| Check | Rule | Severity |
|-------|------|----------|
| Entry price > 0 | `entry_price > 0` | CRITICAL |
| Current price > 0 | `current_price > 0` (if present) | CRITICAL |
| Stop loss < entry (LONG) | `stop_loss < entry_price` | CRITICAL |
| Stop loss > entry (SHORT) | `stop_loss > entry_price` | CRITICAL |
| Take profit > entry (LONG) | `take_profit > entry_price` | CRITICAL |
| Take profit < entry (SHORT) | `take_profit < entry_price` | CRITICAL |
| Stop distance reasonable | `0.5% <= |stop - entry| / entry <= 12%` | HIGH |
| R:R ratio >= 1.0 | `|tp - entry| / |sl - entry| >= 1.0` | MEDIUM |

### Time Reasonability

| Check | Rule | Severity |
|-------|------|----------|
| Entry time is parseable | Valid ISO-8601 UTC | CRITICAL |
| Entry time not in future | `entry_time <= now` | CRITICAL |
| Exit time after entry | `exit_time > entry_time` (if closed) | CRITICAL |
| Bars held >= 0 | `bars_held >= 0` | MEDIUM |
| Open position age reasonable | `< 168 hours (1 week)` | HIGH |

### Cross-Source Consistency

| Check | Rule | Severity |
|-------|------|----------|
| PnL matches across sources | Same pick, same class → same PnL | CRITICAL |
| Symbol classified consistently | Same symbol → same asset_class | HIGH |
| No duplicate picks | Unique (symbol, strategy, entry_time) | HIGH |

---

## QA Check 5: Mutual Fund & ETF Pick Probability Framework

### Probability of Success Calculation

```
Expectancy per trade = (Win_Rate × Avg_Win) − (Loss_Rate × Avg_Loss)
                     = (W × R_w) − ((1−W) × R_l)

Kelly fraction f* = Expectancy / Avg_Win
                  = W − ((1−W) × R_l / R_w)

Probability of Ruin ≈ ((1−Edge)/(1+Edge))^(Bankroll/Unit_Risk)
  where Edge = Expectancy / Avg_Loss
```

### Minimum Viable Thresholds for MF/ETF Picks

| Metric | Minimum | Target |
|--------|---------|--------|
| Win rate | > 40% (with R:R ≥ 1.5) OR > 50% (with R:R ≥ 1.0) | > 55% |
| Expectancy | > 0.5% of risked capital | > 1.0% |
| Profit factor | > 1.3 | > 1.5 |
| Sharpe ratio | > 0.5 | > 1.0 |
| Sortino ratio | > 1.0 | > 2.0 |
| Calmar ratio | > 0.5 | > 1.0 |
| Max drawdown | < 15% | < 10% |
| Forward sample | n ≥ 100 closed picks | n ≥ 200 |

### Sample Size Requirements

| Stage | Minimum Trades | Purpose |
|-------|---------------|---------|
| Discovery | n ≥ 30 | Initial signal validation |
| Validation | n ≥ 100 | Confirm edge persists |
| Money-Ready | n ≥ 200 | Live capital deployment |

---

## QA Implementation Schedule

| Frequency | Checks | Output |
|-----------|--------|--------|
| Every scan (minutes) | PnL=0%, blank fields, open items, price reasonability | QA flag report |
| Every hour | Recently closed exit data, NAV freshness | Data quality report |
| Every day | Cross-source consistency, expectancy calculation | Daily QA summary |
| Every week | Probability of success, risk-adjusted metrics | Weekly performance review |
| Every month | Full backtest re-run, protocol compliance | Monthly compliance report |

---

## QA Dashboard Page

A separate QA validation page (`qa_dashboard.html`) displays:

| Section | Metrics |
|---------|---------|
| PnL Zero Flags | Count, symbols, severity, correct PnL values |
| Blank Field Flags | Count, symbols, missing fields, severity |
| Open Item Flags | Count, symbols, age in hours, severity |
| Recently Closed Flags | Count, symbols, missing exit fields |
| Mutual Fund Quality | NAV staleness, expense ratio compliance, AUM compliance |
| ETF Quality | Spread, liquidity, tracking error compliance |
| Overall QA Score | Pass/fail percentage, trend over time |

---

## QA Pass/Fail Gates

| Gate | Condition | Action |
|------|-----------|--------|
| Gate 0 | Zero CRITICAL flags | Block emission |
| Gate 1 | Zero HIGH flags on open items | Block emission |
| Gate 2 | All mutual fund picks pass solid-pick criteria | Block emission |
| Gate 3 | All ETF picks pass ETF criteria | Block emission |
| Gate 4 | Forward sample n ≥ 100 with WR ≥ 50%, PF ≥ 1.5 | Block live capital |

---
