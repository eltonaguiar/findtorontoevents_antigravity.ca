# Risk Management Plan & Separate Webpage Design

**Worktree:** flaxen-hair_2026-11-14T2304 | **Date:** 2026-11-14T23:04Z

---

## Risk Management Framework

### Position Sizing Methodology

| Parameter | Conservative | Moderate | Aggressive (Max) |
|-----------|-------------|----------|------------------|
| Fixed % risk per trade | 1.0% | 1.5% | 2.0% |
| Kelly fraction | 0.25 (quarter-Kelly) | 0.25 | 0.25 |
| Max single position | 3% | 4% | 5% |
| Max crypto allocation | 10% | 15% | 20% |
| Min trades before Kelly | 30 | 30 | 30 |

**Position size formula:**
```
size = (equity × risk_pct) / stop_distance
where stop_distance = |entry_price - stop_loss_price|
```

### Stop Loss / Take Profit Methodology

| Parameter | Value |
|-----------|-------|
| Primary method | ATR-based |
| SL multiplier | 1.0 × ATR |
| TP multiplier | 1.5 × ATR |
| Min R:R | 1.5:1 |
| Stop floor | 0.5 × ATR (prevents noise whipsaws) |
| Stop cap | 10% distance |
| Trailing stop | 1.5 × ATR, activate at +1R |
| Regime adjustment | CRISIS=1.5x, BEARISH=1.2x, BULLISH=0.9x |

### Drawdown Controls

| Horizon | Conservative | Moderate | Aggressive | Action |
|---------|-------------|----------|------------|--------|
| Daily | -0.5% | -1.0% | -2.0% | Block new picks at 100% |
| Weekly | -1.5% | -3.0% | -5.0% | 48h halt + review |
| Monthly | -3.0% | -6.0% | -10.0% | Full halt + external review |
| Quarterly | -5.0% | -10.0% | -15.0% | Strategy reset |
| Annual | -10.0% | -20.0% | -30.0% | Capital reallocation |

### Correlation Limits

| Limit | Value |
|-------|-------|
| Max positions per group | 3 |
| Max pair correlation | 0.70 (alert), 0.80 (reduce 50%), 0.90 (block) |
| Max directional exposure | 20% of portfolio |
| Max single symbol exposure | 5% crypto, 10% other |

---

## Risk-Adjusted Return Metrics

| Metric | Minimum Threshold | Target |
|--------|------------------|--------|
| Sharpe Ratio | > 0.5 | > 1.0 |
| Sortino Ratio | > 1.0 | > 2.0 |
| Calmar Ratio | > 0.5 | > 1.0 |
| Max Drawdown | < 15% | < 10% |
| VaR (95%, 1-day) | < 2% of NAV | < 1.5% |
| Probabilistic Sharpe | > 0.80 | > 0.95 |
| Ulcer Index | < 5% | < 3% |
| Information Coefficient | > 0.05 | > 0.10 |

---

## Probability of Success Framework

```
Expectancy = (Win_Rate × Avg_Win) − (Loss_Rate × Avg_Loss)
Kelly f* = Expectancy / Avg_Win
Prob_Ruin = ((1−Edge)/(1+Edge))^(Bankroll/Unit_Risk)
```

### Minimum Thresholds

| Metric | Minimum | Target |
|--------|---------|--------|
| Win rate | > 40% (R:R ≥ 1.5) or > 50% (R:R ≥ 1.0) | > 55% |
| Expectancy | > 0.5% per trade | > 1.0% |
| Profit factor | > 1.3 | > 1.5 |
| Kelly fraction | > 0 after shrinkage | > 0.1 |

---

## Separate Risk Management Webpage

### Design Specification

**File:** `risk_dashboard.html` (standalone, under `audit_dashboard/`)

**Technology:** Single HTML file with embedded Chart.js (CDN), vanilla JavaScript, reads JSON data files

**Auto-refresh:** Every 60 seconds

### Page Sections

#### 1. Portfolio Health Gauge
```
[Equity Curve Sparkline]  [Drawdown Gauge: Green/Yellow/Red]
Current Equity: $X,XXX,XXX
Peak Equity:    $X,XXX,XXX
Current DD:     X.XX%  [████████░░░░░░░░░░░░░░]
Daily PnL:      +$X,XXX (X.XX%)
VaR 95%:        -$X,XXX
CVaR 95%:       -$X,XXX
```

#### 2. Drawdown Controls Progress Bars
```
Daily Loss:   [████░░░░░░░░░░] 1.2% / 2.0%  [WARNING]
Weekly Loss:  [██░░░░░░░░░░░░░░] 0.8% / 5.0%  [OK]
Monthly Loss: [█░░░░░░░░░░░░░░░░] 0.3% / 10.0% [OK]
Circuit Breaker: GREEN (Active)
Consecutive Losses: 2 / 5
```

#### 3. Position Sizing Table
| Symbol | Strategy | Kelly % | Position % | Risk $ | ATR Stop | Regime |
|--------|----------|---------|------------|--------|----------|--------|
| SPY | equity_dual_momentum | 1.2% | 3.5% | $350 | 2.4% | BULLISH |
| BTCUSDT | crypto_macd_rsi | 0.8% | 4.0% | $400 | 5.2% | BEARISH |

#### 4. Correlation Heatmap
[Heatmap visualization of asset correlations]

| | SPY | QQQ | BTC | ETH |
|---|-----|-----|-----|-----|
| SPY | 1.00 | 0.89 | 0.34 | 0.31 |
| QQQ | 0.89 | 1.00 | 0.41 | 0.38 |
| BTC | 0.34 | 0.41 | 1.00 | 0.72 |
| ETH | 0.31 | 0.38 | 0.72 | 1.00 |

#### 5. Risk-Adjusted Returns Table
| Strategy | Sharpe | Sortino | Calmar | PSR | Max DD | Verdict |
|----------|--------|---------|--------|-----|--------|---------|
| equity_momentum | 1.23 | 1.89 | 0.78 | 0.94 | -8.2% | PASS |
| crypto_macd_rsi | 0.87 | 1.34 | 0.45 | 0.76 | -12.1% | WATCH |
| bond_yield | 0.45 | 0.67 | 0.23 | 0.44 | -5.1% | FAIL |

#### 6. Kill Switch Status
```
Circuit Breaker: GREEN
Size Multiplier: 1.0x
Auto-Recovery: Enabled (within 2% of peak)
Last Trigger: Never
```

#### 7. QA Alerts (Red Flag List)
| Symbol | Issue | Severity | Age |
|--------|-------|----------|-----|
| JNK | PnL=0% with price movement | CRITICAL | 2h |
| SPY | Blank stop_loss field | HIGH | 4h |
| QQQ | Open position > 72h | HIGH | 85h |

---

## Risk Data JSON Schema

The webpage reads from these JSON files:

```json
// alpha_engine/data/risk_metrics.json
{
  "timestamp": "2026-11-14T23:04:00Z",
  "portfolio": {
    "current_equity": 100000.00,
    "peak_equity": 102000.00,
    "current_drawdown_pct": -1.96,
    "daily_pnl": 1250.00,
    "var_95": -1850.00,
    "cvar_95": -2400.00
  },
  "positions": [...],
  "risk_metrics": {
    "sharpe": 1.23,
    "sortino": 1.89,
    "calmar": 0.78,
    "max_drawdown_pct": -8.2,
    "ulcer_index": 3.4
  },
  "circuit_breaker": {
    "level": "GREEN",
    "size_multiplier": 1.0,
    "daily_loss_used_pct": 1.2,
    "weekly_loss_used_pct": 0.8,
    "monthly_loss_used_pct": 0.3
  },
  "qa_alerts": [...]
}
```

### Data Generation Script

`tools/risk_dashboard_data.py` — aggregates all risk data into single JSON:

```python
def compile_risk_snapshot() -> dict:
    """Aggregate all risk data into single JSON for dashboard."""
    return {
        "timestamp": now_iso(),
        "portfolio": get_portfolio_state(),
        "positions": get_position_risks(),
        "risk_metrics": compute_risk_metrics(),
        "circuit_breaker": get_circuit_breaker_state(),
        "qa_alerts": run_all_qa_checks(),
    }
```

---

## Risk Management Integration Points

```
production_scanner.py
  → risk_controls.run_all_risk_controls() (existing)
  → weekly_loss_limit.check_weekly_limit() (NEW)
  → monthly_loss_limit.check_monthly_limit() (NEW)
  → expectancy_calculator.validate_expectancy() (NEW)
  → portfolio_correlation_guard.filter_picks_by_correlation() (existing)
  → var_enforcer.apply_var_enforcement() (existing)
  → drawdown_circuit_breaker.check_drawdown_breaker() (existing)
  → risk_qa_validator.run_all_qa_checks() (NEW)
  → risk_dashboard_data.compile_risk_snapshot() (NEW, for webpage)
```

---

## Risk Management QA Checks

| Check | Severity | Fail Action |
|-------|----------|-------------|
| Position size > 5% | CRITICAL | Block trade |
| Stop loss missing | CRITICAL | Block trade |
| R:R < 1.0 | MEDIUM | Reduce size 50% |
| Daily loss > 2% | HIGH | Block new picks |
| Weekly loss > 5% | CRITICAL | 48h halt |
| Monthly loss > 10% | CRITICAL | Full halt |
| Correlation > 0.90 | HIGH | Block new position |
| Sharpe < 0.5 | MEDIUM | Downgrade tier |
| Expectancy < 0 | CRITICAL | Do not trade |

---
