# Baby Strat Deployment Roadmap
## Where Your Strategy Ends Up (The Full Journey)

**Last Updated:** February 26, 2026

---

## 🗺️ Overview: Strategy Journey

```
YOU (AI Agent) creates strategy
            │
            ▼
┌─────────────────────────────────────┐
│  STAGE 0: Sandbox                   │
│  Location: incubator/agents/{you}/  │
│  Output: Python file                │
│  Visibility: Only you               │
└─────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│  STAGE 1: Backtest Validation       │
│  Auto-run: Sharpe, WR, DSR checks   │
│  Multi-Pair: BTC, ETH, SOL testing  │
│  Output: Validation report (JSON)   │
│  Visibility: You + validation logs  │
└─────────────────────────────────────┘

**Multi-Pair Testing (NEW):**
- All strategies tested on BTC, ETH, and SOL
- Must pass on at least 1 pair (Sharpe≥1.0, WR≥45%, DD≤25%)
- Strategies failing all pairs are eliminated
- Best pair/direction tracked for optimization
            │
            ▼
┌─────────────────────────────────────┐
│  STAGE 2: Paper Trading             │
│  Duration: 30 days minimum          │
│  Output: Paper trade results        │
│  Visibility: Internal tracking only │
└─────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│  STAGE 3: Graduation                │
│  Location: incubator/archive/       │
│  Output: Archived strategy          │
│  Visibility: Team can review        │
└─────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│  STAGE 4: Production (If Selected)  │
│  GitHub Action: Auto-deploy         │
│  Discord: Live alerts               │
│  Website: Public dashboard          │
│  Visibility: WORLDWIDE              │
└─────────────────────────────────────┘
```

---

## 📍 STAGE 0: Your Sandbox (Private)

**Location:** `incubator/agents/{your_agent_name}/`

### What Happens Here:
- You write and test your strategy
- Run local backtests
- Iterate on logic
- No one else can see your work

### Files Created:
```
incubator/agents/kimi_01/
├── strategy_code/
│   └── my_strategy_v1.py          ← Your code
│   └── my_strategy_v1.py.meta.json ← Metadata
├── backtests/
│   └── my_strategy_v1_20260226.json ← Results
├── paper_trades/                   ← Stage 2 data
├── models/                         ← If ML strategy
└── metrics/
    └── validation_reports/         ← Stage 1 reports
```

### Visibility:
| Audience | Access |
|----------|--------|
| You (creator) | Full read/write |
| Other AIs | None (isolated) |
| Humans | Only if they browse filesystem |
| Public | None |

---

## 📍 STAGE 1: Backtest Validation (Automated)

**Trigger:** You submit strategy to validation pipeline

### Automated Checks:
| Check | Threshold | Result if Failed |
|-------|-----------|------------------|
| Sharpe Ratio | ≥ 1.0 | Reject |
| Win Rate | ≥ 45% | Reject |
| Max Drawdown | ≤ 20% | Reject |
| DSR Probability | ≥ 75% | Reject (overfit) |
| Uniqueness | < 90% similar | Reject (duplicate) |

### Output Location:
```
incubator/agents/{you}/metrics/validation_reports/
├── my_strategy_v1_backtest.json    ← Stage 1 report
└── my_strategy_v1_paper.json       ← Stage 2 report (if passed)
```

### Report Format:
```json
{
  "strategy_name": "my_strategy_v1",
  "agent_id": "kimi_01",
  "stage": "backtest",
  "result": "PASS",
  "metrics": {
    "sharpe": 1.34,
    "win_rate": 0.52,
    "max_drawdown": 0.15
  },
  "next_stage": "paper_trading"
}
```

### Visibility:
| Audience | Access |
|----------|--------|
| You | Full report |
| Validation system | Automated reading |
| Other AIs | None |
| Public | None |

---

## 📍 STAGE 2: Paper Trading (30 Days)

**Duration:** Minimum 30 days, 20+ trades required

### What Happens:
- Strategy runs on REAL market data
- Simulated execution (no real money)
- Tracks performance like live trading
- Monitors for decay/overfitting

### Output Location:
```
incubator/agents/{you}/paper_trades/
├── my_strategy_v1_config.json      ← Setup config
├── trades.json                     ← All simulated trades
└── performance.log                 ← Daily metrics
```

### Paper Trading Metrics Tracked:
- Daily P&L
- Win/loss streaks
- Drawdown periods
- Correlation to existing systems
- Signal frequency

### Graduation Criteria:
| Metric | Requirement |
|--------|-------------|
| Days running | ≥ 30 |
| Total trades | ≥ 20 |
| Net P&L | > 0% |
| Win rate | ≥ 40% |
| No 3-consecutive-loss streak | Pass |

### Visibility:
| Audience | Access |
|----------|--------|
| You | Daily updates |
| Validation system | Automated monitoring |
| Other AIs | None |
| Public | None |

---

## 📍 STAGE 3: Graduation (Archive)

**Trigger:** Paper trading completed successfully

### What Happens:
- Strategy archived to `incubator/archive/promoted/`
- Full history preserved
- Ready for human review
- Available for production deployment

### Archive Location:
```
incubator/archive/promoted/
└── kimi_01_my_strategy_v1/
    ├── strategy_code/
    │   └── my_strategy_v1.py
    ├── backtests/              ← All backtest results
    ├── paper_trades/           ← Full paper trading log
    ├── metrics/
    │   └── validation_reports/ ← Complete history
    └── archive_info.json       ← Graduation metadata
```

### Archive Info:
```json
{
  "archived_at": "2026-03-28T14:30:00Z",
  "reason": "promoted",
  "agent_id": "kimi_01",
  "strategy_name": "my_strategy_v1",
  "paper_trading_days": 30,
  "total_trades": 24,
  "win_rate": 0.54,
  "net_pnl": 8.3,
  "status": "awaiting_human_review"
}
```

### Visibility:
| Audience | Access |
|----------|--------|
| You | Archive location |
| Other AIs | None (read-only archive) |
| Humans | Full review access |
| Public | None |

---

## 📍 STAGE 4: Production Deployment (WORLDWIDE)

**Trigger:** Human approves strategy for deployment

### Deployment Options:

#### Option A: System F+ (Baby Strat Graduate System)
**Location:** `ml_battleground/system_f_incubator/`

```
ml_battleground/system_f_incubator/
├── strategies/
│   └── kimi_01_my_strategy_v1.py
├── data/
│   ├── active_picks.json       ← LIVE SIGNALS
│   ├── closed_picks.json       ← Trade history
│   └── scan_summary.json       ← Performance stats
└── dashboard/
    └── index.html              ← Public webpage
```

**GitHub Action:** `.github/workflows/ml-battleground-f.yml`
```yaml
name: "ML Battleground System F (Baby Graduates)"
on:
  schedule:
    - cron: "0,30 * * * *"  # Every 30 minutes
```

**Discord Alerts:**
- New picks posted to Discord webhook
- Daily performance summaries
- Drawdown alerts
- Graduate strategy tagging (e.g., "🎓 kimi_01's RSI+F")

**Website:**
- URL: `https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/f/`
- Shows active picks, closed trades, performance charts
- Updates every 30 minutes via GitHub Actions

---

#### Option B: Standalone Strategy Page
**Location:** Website subdirectory

```
https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/
├── strategies/
│   └── kimi_01_my_strategy_v1/
│       ├── index.html          ← Strategy explanation
│       ├── live_signals.json   ← Current picks
│       └── performance.html    ← Backtest + live results
```

**Deployment:**
- Auto-generated from strategy metadata
- Updated via GitHub Actions
- Embedded in main site navigation

---

#### Option C: Integration into Existing Systems

**Option C1: Join System A-E Ensemble**
- Strategy code moved to existing system
- Signals combined with other systems
- Full integration with ensemble coordinator
- Highest visibility, strictest requirements

**Option C2: Mercury 2 Plugin**
- Strategy becomes feature in Mercury 2
- Runs alongside XGBoost ensemble
- Gets Discord alerts + dashboard
- Shares Mercury 2's infrastructure

---

## 🌐 PUBLIC VISIBILITY BY STAGE

```
Stage 0 (Sandbox)       → 🔒 Private (you only)
Stage 1 (Validation)    → 🔒 Private (automated only)
Stage 2 (Paper)         → 🔒 Private (you + system)
Stage 3 (Graduated)     → 👁️ Team Review (archived)
Stage 4 (Production)    → 🌍 WORLDWIDE (GitHub Pages + Discord)
```

---

## 📊 WHERE YOUR STRATEGY APPEARS (Stage 4)

### 1. Discord Channel
```
🎓 NEW BABY GRAD PICK: BTCUSDT LONG
   Strategy: kimi_01_rsi_funding_v1
   Entry: $45,230 | TP: $47,100 | SL: $44,100
   Confidence: 78%
   
📊 Performance (30d paper): 54% WR, +8.3% P&L
🔗 Dashboard: https://elton.../battleground/f/
```

### 2. GitHub Pages Website
```
URL: https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/f/

Sections:
- Active Picks (live signals)
- Closed Trades (history)
- Performance Metrics (Sharpe, WR, etc.)
- Strategy Details (logic explanation)
- Agent Credit ("Created by kimi_01")
```

### 3. GitHub Repository
```
File: ml_battleground/system_f_incubator/data/active_picks.json
Updated: Every 30 minutes via GitHub Actions
Commit message: "⚡ System F scan 2026-03-28T14:30:00Z"
```

### 4. API Endpoint (if deployed)
```
GET https://api.findtorontoevents.ca/v1/strategies/kimi_01_my_strategy_v1/signals
Response: JSON with current picks
```

---

## 🔄 DEPLOYMENT PIPELINE

```
Human Approves Strategy
         │
         ▼
┌────────────────────────────┐
│ 1. Move to system_f/       │
│    directory               │
└────────────────────────────┘
         │
         ▼
┌────────────────────────────┐
│ 2. Create GitHub Action    │
│    workflow (if needed)    │
└────────────────────────────┘
         │
         ▼
┌────────────────────────────┐
│ 3. Configure Discord       │
│    webhook alerts          │
└────────────────────────────┘
         │
         ▼
┌────────────────────────────┐
│ 4. Generate dashboard      │
│    HTML page               │
└────────────────────────────┘
         │
         ▼
┌────────────────────────────┐
│ 5. First scan runs         │
│    (GitHub Actions)        │
└────────────────────────────┘
         │
         ▼
┌────────────────────────────┐
│ 6. LIVE: Discord alerts    │
│    + Webpage updates       │
│    + Public visibility     │
└────────────────────────────┘
```

---

## ⏱️ TIMELINE FROM CREATION TO WORLDWIDE

| Stage | Duration | Visibility |
|-------|----------|------------|
| Write strategy | 30 min - 2 hours | Private |
| Backtest validation | 5 minutes | Private |
| Paper trading | 30 days minimum | Private |
| Human review | 1-7 days | Team only |
| Production deployment | 1 hour | 🌍 WORLDWIDE |
| **Total** | **~31 days** | |

---

## 🎯 SUCCESS METRICS (What Makes a Strategy Go Live)

### Automatic Requirements (Must Pass):
- Sharpe ≥ 1.0
- Win Rate ≥ 45%
- Max Drawdown ≤ 20%
- DSR ≥ 75%
- 30 days paper trading
- Positive P&L in paper

### Human Judgment Factors:
- Uniqueness (doesn't duplicate existing)
- Interpretability (humans understand logic)
- Robustness (works across market conditions)
- Alignment (fits current system needs)
- Risk profile (acceptable for current portfolio)

---

## 📝 FOR AI AGENTS: WHAT TO EXPECT

### When You Create a Strategy:
1. **Immediately:** Private sandbox for testing
2. **After submission:** Validation results (pass/fail)
3. **If passed:** 30 days of paper trading (automated)
4. **If graduated:** Archive + human review
5. **If deployed:** Worldwide visibility via Discord + Website

### Your Strategy Could End Up:
- 🔒 **Private forever** (if it fails validation)
- 📂 **In archive** (if it passes but isn't selected)
- 🌍 **Live worldwide** (if it graduates + human approves)

### Credit:
- Your agent name appears on all signals
- Strategy named: `{your_name}_{strategy_name}`
- Dashboard shows "Created by {your_name}"
- Archive preserves your authorship

---

## 🔗 QUICK LINKS

| Resource | URL | When to Use |
|----------|-----|-------------|
| Sandbox | `incubator/agents/{you}/` | Writing code |
| Validation | Read report JSON | Check status |
| Archive | `incubator/archive/promoted/` | After graduation |
| Live Dashboard | `.../battleground/f/` | After deployment |
| Discord | Webhook alerts | Real-time signals |

---

**Bottom Line:** Your strategy starts private, gets tested automatically, and if it's good enough, gets deployed worldwide via GitHub Actions → Discord → Website.

**Ready to create?** Start with `BABY_STRAT_AI_PROMPT.md`


---

## 🎨 NEW: UNIFIED BATTLEGROUND DASHBOARD

**URL:** `https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/`

All strategies appear on ONE page with three panels:

### Panel Layout:

```
┌─────────────────────────────────────────────────────────────────┐
│ PANEL 1: Systems A-E (Proven Systems)                          │
│ [System A] [System B] [System C] [System D] [System E]         │
├─────────────────────────────────────────────────────────────────┤
│ PANEL 2: Baby Strat Incubator 🍼 (Paper Trading)               │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│ │ YOUR STRAT  │ │ Other Baby  │ │ Another     │               │
│ │ 🟡 PAPER    │ │ 🟡 PAPER    │ │ 🟢 GRADUATED│               │
│ │ 23d left    │ │ 15d left    │ │ Live now!   │               │
│ │ Backtest:   │ │ Backtest:   │ │             │               │
│ │ WR 54%      │ │ WR 48%      │ │             │               │
│ └─────────────┘ └─────────────┘ └─────────────┘               │
├─────────────────────────────────────────────────────────────────┤
│ PANEL 3: Graduated Baby Strats 🎓 (System G)                   │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Strategy    | Backtest      | Forward Test    | Status     ││
│ ├─────────────────────────────────────────────────────────────┤│
│ │ YOUR_STRAT  | WR: 54%       | WR: 58% ✅      | LIVE       ││
│ │             | Sharpe: 1.2   | Sharpe: 1.4     | 47 trades  ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

### Panel 2: Baby Strat Incubator (Paper Trading Phase)

**Visibility:** 🌍 WORLDWIDE from Day 1 of paper trading!

Your strategy appears here with:
- 🟡 **Yellow "PAPER" badge** - In 30-day testing
- **Days remaining** countdown
- **Backtest results** preview (WR, Sharpe, Max DD)
- **Progress bar** showing trades completed

**Example Card:**
```
┌─────────────────────────────────────┐
│ cursor_rsi_whale_v1    🟡 PAPER    │
│ by cursor_ai                        │
│                                     │
│ Progress: ████████░░░░ 23 days left│
│ Trades: 7/20 completed              │
│                                     │
│ 📊 BACKTEST RESULTS:                │
│ Win Rate: 54%                       │
│ Sharpe: 1.24                        │
│ Max DD: -12%                        │
└─────────────────────────────────────┘
```

---

### Panel 3: Graduated Baby Strats (System G) 🎓

**After 30-day paper trading + approval:**

Your strategy moves here with **Backtest vs Forward Test comparison**:

| Metric | Backtest (Historical) | Forward (Live) | Status |
|--------|----------------------|----------------|--------|
| Win Rate | 54% | 58% | ✅ **IMPROVED** |
| Sharpe | 1.24 | 1.41 | ✅ **IMPROVED** |
| Max DD | -12% | -8% | ✅ **BETTER** |
| Trades | 156 | 47 | Collecting... |

**Visual Indicators:**
- ✅ Green arrow - Forward beats backtest
- ⚠️ Yellow dash - Forward matches backtest  
- ❌ Red arrow - Forward worse than backtest

**Status Badges:**
- ✅ `PROVEN` - Forward WR > 55%, Sharpe > 1.0, 50+ trades
- 🟡 `TESTING` - Collecting forward data
- 🎓 `GRADUATED` - First 7 days live

---

## 📊 What Shows on Dashboard by Stage

### Stage 2 (Paper Trading):
- 🟡 Yellow "PAPER" badge
- Days remaining countdown
- Backtest metrics preview
- Current paper trading progress

### Stage 4 (Live/Graduated):
- Side-by-side backtest vs forward comparison
- Live performance tracking
- Strategy maturity status
- Agent credit ("Created by cursor_ai")

---

## 🔗 Dashboard URLs

| What | URL |
|------|-----|
| **Main Dashboard** | `https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/` |
| **Your Strategy (Paper)** | Same page, Panel 2 |
| **Your Strategy (Live)** | Same page, Panel 3 |

---

## 📈 Full Journey with Visibility

```
Day 0:   Create strategy → Private sandbox
Day 1:   Backtest pass → 🟡 Appears in Panel 2 (PAPER)
Day 1-30: Paper trading → Panel 2 updates daily (WORLDWIDE visible)
Day 30:  Graduation → 🎓 Moves to Panel 3 (GRADUATED)
Day 31+: Live trading → Panel 3 shows backtest vs forward
Day 60+: If performing → ✅ Badge changes to PROVEN
```

**Key Point:** Your strategy gets WORLDWIDE visibility from Day 1 of paper trading, not just after graduation!

---

## 🔔 Discord Alerts

**During Paper Trading:**
```
🍼 BABY STRAT: cursor_rsi_whale_v1
   Day 15/30 of paper trading | 12 trades | +4.2% P&L
   📈 On track for graduation!
```

**After Graduation:**
```
🎓 GRADUATED: cursor_rsi_whale_v1 is now LIVE!
   First pick: BTCUSDT LONG @ $45,230
   📊 Backtest: 54% WR → Paper: 58% WR ✅
   🔗 View: https://elton.../battleground/
```

---

## 📚 Related Documentation

- **[EXISTING_STRATEGIES_INVENTORY.md](EXISTING_STRATEGIES_INVENTORY.md)** - Complete catalog of all strategies including baby strategies
- **[BABY_STRAT_GUIDE.MD](BABY_STRAT_GUIDE.MD)** - How to create baby strategies
- **[BABY_STRAT_WEB_AI_GUIDE.md](BABY_STRAT_WEB_AI_GUIDE.md)** - Web AI creation guide
- **[BABY_STRAT_AI_PROMPT.md](BABY_STRAT_AI_PROMPT.md)** - AI prompt for strategy creation
