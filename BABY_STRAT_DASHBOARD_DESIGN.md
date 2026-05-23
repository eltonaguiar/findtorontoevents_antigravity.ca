# Baby Strat Dashboard Design
## Integrated Battleground View

**URL:** `https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/`

---

## 🎨 Layout Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SUPERPOWERS ARENA - The Horse Race                        │
│              5 ML systems + Baby Strat Incubator compete                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PANEL 1: PROVEN SYSTEMS (A-E)                                      │   │
│  │ [Cards for System A, B, C, D, E - as existing]                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PANEL 2: BABY STRAT INCUBATOR 🍼                                    │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │ │ Baby Strat 1│ │ Baby Strat 2│ │ Baby Strat 3│ │   ...       │    │   │
│  │ │ [PAPER]     │ │ [PAPER]     │ │ [PAPER]     │ │             │    │   │
│  │ │ 30d left    │ │ 15d left    │ │ 22d left    │ │             │    │   │
│  │ │ Backtest:   │ │ Backtest:   │ │ Backtest:   │ │             │    │   │
│  │ │ WR 52%      │ │ WR 48%      │ │ WR 61%      │ │             │    │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  │                                                                     │   │
│  │ Legend: 🟡 Paper Trading | 🟢 Graduated | 🔴 Failed               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PANEL 3: GRADUATED BABY STRATS (System G) 🎓                        │   │
│  │                                                                     │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │ STRATEGY          | BACKTEST      | FORWARD TEST  | STATUS   │  │   │
│  │  ├───────────────────────────────────────────────────────────────┤  │   │
│  │  │ cursor_rsi_whale  | WR: 54%      | WR: 58%       | ✅ LIVE  │  │   │
│  │  │                   | Sharpe: 1.2  | Sharpe: 1.4   | 47 trades│  │   │
│  │  │                   | 90 days      | 45 days       |          │  │   │
│  │  ├───────────────────────────────────────────────────────────────┤  │   │
│  │  │ kimi_macd_funding | WR: 51%      | WR: 49%       | ⚠️ MARGINAL│  │   │
│  │  │                   | Sharpe: 1.1  | Sharpe: 0.8   | 32 trades│  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                                                     │   │
│  │  [View Detailed Dashboard →]                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PANEL 4: COMPARISON TABLE (All Systems + Baby Strats)               │   │
│  │ [Existing table + new columns for Baby Strat status]               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Panel Specifications

### PANEL 1: Proven Systems (A-E) - EXISTING
No changes to current Systems A-E cards.

---

### PANEL 2: Baby Strat Incubator 🍼

**Purpose:** Show strategies currently in paper trading phase

**Data Source:** 
```
incubator/agents/{agent}/paper_trades/*_config.json
```

**Card Design:**
```html
<div class="baby-strat-card status-paper">
  <div class="strat-header">
    <span class="strat-name">cursor_rsi_whale_v1</span>
    <span class="badge badge-paper">🟡 PAPER</span>
  </div>
  <div class="strat-meta">
    <span class="agent">by cursor_ai</span>
    <span class="days-left">23 days left</span>
  </div>
  <div class="backtest-preview">
    <div class="metric">
      <label>Backtest WR</label>
      <value class="positive">54%</value>
    </div>
    <div class="metric">
      <label>Sharpe</label>
      <value class="positive">1.24</value>
    </div>
    <div class="metric">
      <label>Max DD</label>
      <value class="warning">-12%</value>
    </div>
  </div>
  <div class="paper-status">
    <div class="progress-bar">
      <div class="progress" style="width: 23%"></div>
    </div>
    <span class="trades">7/20 trades</span>
  </div>
</div>
```

**Status Badges:**
- 🟡 `PAPER` - In paper trading (30 days)
- 🟢 `GRADUATED` - Ready for production
- 🔴 `FAILED` - Didn't pass validation
- ⚪ `VALIDATING` - In backtest phase

---

### PANEL 3: Graduated Baby Strats (System G) 🎓

**Purpose:** Show strategies that completed paper trading and are now live

**Data Source:**
```
ml_battleground/system_g_incubator/data/dashboard.json
```

**Table Columns:**

| Column | Description | Data Source |
|--------|-------------|-------------|
| Strategy Name | Agent + strategy name | `strategy_name` |
| Status | LIVE / MARGINAL / TESTING | Validation gate |
| Backtest WR | Win rate from backtest | `backtest_metrics.win_rate` |
| Backtest Sharpe | Sharpe from backtest | `backtest_metrics.sharpe` |
| Forward WR | Win rate from paper/live | `forward_metrics.win_rate` |
| Forward Sharpe | Sharpe from paper/live | `forward_metrics.sharpe` |
| Trades | Total live trades | `total_trades` |
| Age | Days since graduation | `graduated_date` |

**Visual Indicators:**

```
Backtest vs Forward Comparison:

Strategy: cursor_rsi_whale_v1
┌─────────────┬─────────────┬─────────────┐
│   Metric    │  Backtest   │   Forward   │
├─────────────┼─────────────┼─────────────┤
│ Win Rate    │    54%      │    58%  ✅  │  ← Improved!
│ Sharpe      │    1.24     │    1.41 ✅  │  ← Improved!
│ Max DD      │    -12%     │    -8%  ✅  │  ← Better!
│ Trades      │    156      │    47       │
│ Period      │   90 days   │   45 days   │
└─────────────┴─────────────┴─────────────┘

Legend: ✅ Beats backtest | ⚠️ Close to backtest | ❌ Worse than backtest
```

**Status Badges:**
- ✅ `PROVEN` - Forward test > 50 trades, WR > 55%, Sharpe > 1.0
- 🟡 `TESTING` - Forward test < 50 trades, collecting data
- 🟠 `MARGINAL` - Forward test underperforming backtest
- ❌ `DEGRADED` - Forward test significantly worse (circuit breaker)

**Multi-Pair Verification Badges:**
- 🔵 `MULTI` - Strategy verified on BTC, ETH, or SOL (multi-pair tested)
- ⚪ `SINGLE` - Single pair only (not multi-pair verified)

**Multi-Pair Criteria:**
| Pair | Directions | Min Sharpe | Min WR | Max DD |
|------|------------|------------|--------|--------|
| BTC | LONG/SHORT/BOTH | 1.0 | 45% | 25% |
| ETH | LONG/SHORT/BOTH | 1.0 | 45% | 25% |
| SOL | LONG/SHORT/BOTH | 1.0 | 45% | 25% |

*Strategy must pass on at least 1 pair to be multi-pair verified*

---

## 📈 Data Structure

### Baby Strat in Paper Trading:
```json
{
  "strategy_name": "cursor_rsi_whale_v1",
  "agent_id": "cursor_ai",
  "status": "paper_trading",
  "stage": 2,
  
  "backtest_metrics": {
    "win_rate": 0.54,
    "sharpe": 1.24,
    "max_drawdown": 0.12,
    "total_trades": 156,
    "period_days": 90
  },
  
  "paper_trading": {
    "started_at": "2026-02-26T10:30:00Z",
    "days_remaining": 23,
    "trades_count": 7,
    "current_pnl": 3.2,
    "projected_annual": 45.0
  }
}
```

### Graduated Baby Strat (Live):
```json
{
  "strategy_name": "cursor_rsi_whale_v1",
  "agent_id": "cursor_ai",
  "status": "live",
  "stage": 4,
  "graduated_at": "2026-03-28T14:30:00Z",
  
  "backtest_metrics": {
    "win_rate": 0.54,
    "sharpe": 1.24,
    "max_drawdown": 0.12,
    "total_trades": 156,
    "period_days": 90
  },
  
  "forward_metrics": {
    "win_rate": 0.58,
    "sharpe": 1.41,
    "max_drawdown": 0.08,
    "total_trades": 47,
    "period_days": 45
  },
  
  "validation_gate": {
    "status": "PROVEN",
    "checks_passed": 8,
    "forward_vs_backtest": "IMPROVED"
  }
}
```

---

## 🎯 Backtest vs Forward Test Comparison Logic

### Performance Comparison:
```javascript
function comparePerformance(backtest, forward) {
  const wrDiff = forward.win_rate - backtest.win_rate;
  const sharpeDiff = forward.sharpe - backtest.sharpe;
  const ddDiff = backtest.max_drawdown - forward.max_drawdown; // Lower is better
  
  if (wrDiff > 0.05 && sharpeDiff > 0.2 && ddDiff > 0.02) {
    return { status: "IMPROVED", icon: "✅", color: "#22c55e" };
  } else if (wrDiff > -0.05 && sharpeDiff > -0.3) {
    return { status: "CONSISTENT", icon: "⚠️", color: "#eab308" };
  } else {
    return { status: "DEGRADED", icon: "❌", color: "#ef4444" };
  }
}
```

### Visual Indicators:
- **Green arrow up** ↑ - Forward beats backtest
- **Yellow dash** − - Forward matches backtest
- **Red arrow down** ↓ - Forward worse than backtest

---

## 📱 Mobile Layout

```
Mobile View (< 768px):
┌─────────────────────────────┐
│ Systems A-E (horizontal    │
│ scroll cards)              │
├─────────────────────────────┤
│ Baby Strats (vertical      │
│ stack)                     │
├─────────────────────────────┤
│ Graduated Strats (table    │
│ with expandable rows)      │
└─────────────────────────────┘
```

---

## 🔗 API Endpoints

### Baby Strats (Paper Trading):
```
GET https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/incubator/config/baby_strats_dashboard.json
```

### Graduated Strats (Live):
```
GET https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/ml_battleground/system_g_incubator/data/dashboard.json
```

---

## 🎨 Color Scheme

| Element | Color | Hex |
|---------|-------|-----|
| Paper Trading Badge | Yellow | `#eab308` |
| Graduated Badge | Green | `#22c55e` |
| Failed Badge | Red | `#ef4444` |
| Backtest Data | Blue | `#3b82f6` |
| Forward Data | Purple | `#a855f7` |
| Improved Indicator | Green | `#22c55e` |
| Degraded Indicator | Red | `#ef4444` |

---

## 📋 Implementation Checklist

- [ ] Create `incubator/config/baby_strats_dashboard.json` generator
- [ ] Create `ml_battleground/system_g_incubator/data/dashboard.json` structure
- [ ] Update battleground HTML with Panel 2 (Baby Strats)
- [ ] Update battleground HTML with Panel 3 (Graduated Strats)
- [ ] Add backtest vs forward comparison logic
- [ ] Style cards for mobile responsiveness
- [ ] Test data fetching from GitHub raw URLs
- [ ] Add auto-refresh (every 60 seconds)

---

## 📚 Related Documentation

- **[EXISTING_STRATEGIES_INVENTORY.md](EXISTING_STRATEGIES_INVENTORY.md)** - Complete catalog of all strategies including baby strategies
- **[BABY_STRAT_GUIDE.MD](BABY_STRAT_GUIDE.MD)** - How to create baby strategies
- **[BABY_STRAT_DEPLOYMENT_ROADMAP.md](BABY_STRAT_DEPLOYMENT_ROADMAP.md)** - Strategy deployment journey
- **[BABY_STRAT_WEB_AI_GUIDE.md](BABY_STRAT_WEB_AI_GUIDE.md)** - Web AI creation guide

**Result:** One unified dashboard showing all systems + Baby Strats in incubation + Graduated strats with clear backtest vs forward performance comparison.
