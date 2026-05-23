# Production CI/CD & Live Tracking Setup
**Date:** 2026-02-28  
**Status:** DEPLOYMENT READY

---

## 🔄 GitHub Actions Workflows (Automated CI/CD)

### 1. Forward Test Validation (Every 4 Hours)
**File:** `.github/workflows/forward_test.yml`

```yaml
Schedule: 0 0,4,8,12,16,20 * * *  (Every 4 hours)
Trigger: Automatic + Manual dispatch
```

**What it does:**
- Runs 8-check validation on all strategies
- Tests on 24 symbols, 5 years of data
- Checks circuit breakers (WR > 45%, PF > 1.0, DD < 20%)
- Uploads results as artifacts
- Updates live dashboard

**Circuit Breakers:**
- Win Rate < 45% → Alert
- Profit Factor < 1.0 → Halt
- Drawdown > 20% → Halt
- Daily loss > 5% → Halt

---

### 2. Strategy Bundle Deployment (Manual)
**File:** `.github/workflows/deploy_bundle.yml`

```yaml
Trigger: workflow_dispatch (manual)
Inputs: bundle name, mode (paper/live)
```

**Deployment Process:**
1. **Validate** → Run 8-check validation
2. **Check** → Verify all strategies pass
3. **Deploy** → Deploy to paper or live
4. **Notify** → Slack notification on completion

**Usage:**
```bash
# Deploy to paper trading
github workflow run deploy_bundle.yml \
  -f bundle=williams_connors \
  -f mode=paper

# Deploy to live (after 100+ paper trades)
github workflow run deploy_bundle.yml \
  -f bundle=williams_connors \
  -f mode=live
```

---

### 3. Live Picks Tracker (Every 15 Minutes)
**File:** `.github/workflows/live_tracker.yml`

```yaml
Schedule: */15 * * * *  (Every 15 minutes)
```

**What it does:**
- Syncs picks from all systems (Alpha Engine, Mercury 2, Crypto ML Edge)
- Updates SQLite database (`data/live_picks.db`)
- Generates HTML dashboard
- Deploys to GitHub Pages
- Commits updated data

**Dashboard URL:** `https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/`

---

## 📊 Live Picks Tracking System

### Central Database
**File:** `data/live_picks.db` (SQLite)

**Tables:**
```sql
live_picks        -- Current active picks
pick_history      -- Historical updates
```

**Tracked per pick:**
- Symbol, strategy, system
- Entry/TP/SL prices
- Current price & unrealized PnL
- Bars held, status
- Full history of price updates

### Python Tracker
**File:** `live_picks_tracker.py`

**Usage:**
```python
from live_picks_tracker import LivePicksTracker, LivePick

# Initialize
tracker = LivePicksTracker()

# Register new pick
pick = LivePick(
    id="BTC_20260228_001",
    symbol="BTC-USD",
    strategy="connors_rsi2",
    system="alpha_engine",
    side="LONG",
    entry_price=65000,
    take_profit=68000,
    stop_loss=63000,
    current_price=65000,
    unrealized_pnl_pct=0,
    entry_time="2026-02-28T00:00:00Z",
    bars_held=0,
    status="ACTIVE"
)
tracker.register_pick(pick)

# Update with current market data
tracker.update_pick(
    pick_id="BTC_20260228_001",
    system="alpha_engine",
    current_price=66000,
    unrealized_pnl_pct=1.54,
    bars_held=5
)

# Close pick
tracker.close_pick(
    pick_id="BTC_20260228_001",
    system="alpha_engine",
    exit_price=68000,
    realized_pnl_pct=4.62,
    exit_reason="TAKE_PROFIT"
)

# Get summary
summary = tracker.get_summary()
print(f"Active: {summary['active']['total_active']}")
print(f"Unrealized PnL: {summary['active']['total_unrealized_pnl']:+.2f}%")

# Export to dashboard
tracker.export_to_dashboard()
```

### Sync All Systems
```bash
# Manual sync
python live_picks_tracker.py

# This reads from:
# - alpha_engine/data/active_picks.json
# - mercury2/data/active_picks.json
# - crypto_ml_edge/data/active_picks.json
# And writes to data/live_picks.db + dashboard/live_picks.json
```

---

## 🚀 Deployment Instructions

### Step 1: Enable GitHub Actions
1. Go to repository Settings → Actions → General
2. Enable "Read and write permissions"
3. Enable "Allow GitHub Actions to create and approve pull requests"

### Step 2: Set Secrets (Optional)
For Slack notifications:
```bash
github secrets set SLACK_WEBHOOK "https://hooks.slack.com/services/..."
```

### Step 3: Enable GitHub Pages
1. Settings → Pages
2. Source: Deploy from a branch
3. Branch: gh-pages / (root)
4. Dashboard will be at: `https://[username].github.io/[repo]/`

### Step 4: Deploy Bundle
```bash
# Via GitHub CLI
github workflow run deploy_bundle.yml -f bundle=williams_connors -f mode=paper

# Or via GitHub web UI
# Actions → Deploy Strategy Bundle → Run workflow
```

---

## 📈 Monitoring

### Dashboard Metrics
- **Active Picks:** Total count + by system/strategy
- **Unrealized PnL:** Sum of all open positions
- **Closed Today:** Count + realized PnL
- **Per-pick details:** Symbol, entry, current, PnL%, bars held

### Alerts (Via GitHub Actions)
- Circuit breaker triggered → Workflow fails + notification
- Daily loss > 5% → Red alert
- Win rate drops below 45% → Yellow warning
- New deployment → Success/failure notification

### Manual Checks
```bash
# View live picks summary
python live_picks_tracker.py

# Query database directly
sqlite3 data/live_picks.db "SELECT * FROM live_picks WHERE status='ACTIVE';"

# Check dashboard
cat dashboard/live_picks.json | jq '.summary'
```

---

## 🔒 Safety Features

1. **Paper Mode Default:** All deployments start in paper
2. **8-Check Validation:** Must pass before any deployment
3. **Circuit Breakers:** Auto-halt on bad performance
4. **Manual Approval:** Live deployments require manual trigger
5. **Audit Trail:** All picks tracked in database with history
6. **GitHub Pages:** Public dashboard for transparency

---

## 📁 Files Created

| File | Purpose |
|------|---------|
| `.github/workflows/forward_test.yml` | Automated validation every 4h |
| `.github/workflows/deploy_bundle.yml` | Manual deployment to paper/live |
| `.github/workflows/live_tracker.yml` | Update dashboard every 15min |
| `live_picks_tracker.py` | Central tracking system |
| `data/live_picks.db` | SQLite database |
| `dashboard/index.html` | Auto-generated web dashboard |
| `deploy_prod_bundle.py` | Deployment script |

---

## ✅ Status

| Component | Status |
|-----------|--------|
| GitHub Actions workflows | ✅ Created |
| Live tracker | ✅ Implemented |
| Database schema | ✅ Defined |
| Dashboard | ✅ Auto-generated |
| Circuit breakers | ✅ Configured |
| Paper trading | ✅ Ready |
| Live trading | ⏳ After 100 paper trades |

**Next:** Push to GitHub and enable Actions!
