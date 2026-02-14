# 📊 Data Update System Documentation
## How KIMI Trading Systems Stay Current

---

## 🔄 Update Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Data Sources  │────▶│  GitHub Actions  │────▶│  GitHub Pages   │
│                 │     │  (Auto-refresh)  │     │  (Dashboard)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                        │
         ▼                       ▼                        ▼
   • Exchange APIs       • Every 15 minutes       • Live dashboard
   • On-chain data       • Python scanners        • Auto-updated
   • Social sentiment    • Data aggregation       • No manual deploy
```

---

## ⏱️ Update Frequencies

| System | Frequency | Trigger | Data Source |
|--------|-----------|---------|-------------|
| **Alpha Signals** | Every 15 min | GitHub Actions cron | Price APIs, on-chain |
| **Gem Discovery** | Every 15 min | GitHub Actions cron | DEX scanners |
| **Predictions** | Every 15 min | GitHub Actions cron | Price check APIs |
| **Strategy Backtest** | Daily | GitHub Actions cron @ midnight | Historical data |
| **Dashboard** | Real-time | GitHub Pages + JS fetch | Aggregated data.json |

---

## 🔧 GitHub Actions Workflow

### File: `.github/workflows/alpha_monitoring.yml`

```yaml
Schedule:
  - cron: '*/15 6-23 * * *'  # Every 15 min (market hours)
  - cron: '0 */4 0-5 * * *'   # Every 4 hours (overnight)
  - cron: '0 0 * * *'         # Daily at midnight (backtest)

Jobs:
  1. scan-and-update:
     - Checkout repo
     - Setup Python
     - Run alpha scanner
     - Run gem scanner
     - Run prediction tracker
     - Update dashboard data
     - Commit changes
     - Deploy to GitHub Pages
  
  2. backtest-update (daily only):
     - Update backtest results
     - Recalculate strategy rankings
```

---

## 📁 Data Flow

### Step 1: Data Collection (Every 15 min)
```
alpha_signals/alpha_engine.py
├─ Fetches: Price data from CoinGecko/Kraken
├─ Calculates: Smart Money scores, on-chain metrics
└─ Outputs: data/signals/ALPHA_[TIMESTAMP].json

goldmine_finder/scanners/new_pair_scanner.py
├─ Fetches: DEX data from DexScreener/Birdeye
├─ Calculates: Gem scores, volume anomalies
└─ Outputs: data/gems/GEM_[SYMBOL]_[TIMESTAMP].json

predictions/alert_system.ps1
├─ Fetches: Current prices
├─ Compares: Entry vs current
├─ Checks: Target/Stop hits
└─ Outputs: data/predictions/current_status.json
```

### Step 2: Data Aggregation (After scans)
```
monitoring/update_dashboard.py
├─ Reads: All signal/gem/prediction files
├─ Aggregates: Statistics, top performers
├─ Calculates: Win rates, counts
└─ Outputs: monitoring/dashboard/data.json
```

### Step 3: Dashboard Update (Auto)
```
monitoring/dashboard/index.html
├─ Loads: data.json via JavaScript fetch()
├─ Displays: Real-time stats
├─ Refreshes: Every 5 minutes (client-side)
└─ GitHub Pages: Auto-deployed on commit
```

---

## 📊 Data Structure

### Aggregated Dashboard Data (`data.json`)
```json
{
  "metadata": {
    "generated_at": "2026-02-13T20:45:00Z",
    "version": "1.0",
    "systems": ["alpha", "gems", "predictions"]
  },
  "overview": {
    "total_alpha_signals": 12,
    "total_gem_discoveries": 8,
    "active_predictions": 4,
    "prediction_win_rate": 84.5,
    "high_priority_alerts": 3
  },
  "signals": [...],
  "gems": [...],
  "predictions": [...]
}
```

### Individual Signal Data (`data/signals/*.json`)
```json
{
  "symbol": "PENGU",
  "timestamp": "2026-02-13T20:30:00Z",
  "signal_type": "buy",
  "confidence_score": 94,
  "entry_price": 0.00665,
  "factors": {...},
  "grade": "S+"
}
```

---

## 🚀 How to Access Live Data

### Main Dashboard (Unified)
```
https://yourusername.github.io/findtorontoevents/monitoring/dashboard/
```
- Auto-refreshes every 5 minutes
- Shows all systems in one view
- Links to detailed dashboards

### Individual Dashboards
```
Alpha Signals:    /alpha_signals/ui/alpha_dashboard.html
Gem Finder:       /goldmine_finder/ui/goldmine_dashboard.html
Predictions:      /predictions/prediction-dashboard.html
Strategy Backtest:/strategy_backtest/ui/backtest_dashboard.html
Consensus:        /predictions/consensus_dashboard.html
```

### Raw Data Access
```
Aggregated:   /monitoring/dashboard/data.json
Signals:      /data/signals/
Gems:         /data/gems/
Predictions:  /data/predictions/
```

---

## 🔌 Manual Data Refresh

### Option 1: Trigger GitHub Actions
1. Go to GitHub repo
2. Click "Actions" tab
3. Select "Alpha Signal Monitor"
4. Click "Run workflow"
5. Choose scan type (full/quick/gems_only)

### Option 2: Local Update
```bash
cd findcryptopairs

# Update alpha signals
python alpha_signals/alpha_engine.py

# Update gem discoveries
python goldmine_finder/scanners/new_pair_scanner.py

# Update predictions
powershell -File predictions/alert_system.ps1

# Update dashboard
python monitoring/update_dashboard.py

# Commit and push
git add data/ monitoring/
git commit -m "Manual data update"
git push
```

---

## 📈 Data Retention

| Data Type | Retention | Cleanup |
|-----------|-----------|---------|
| Alpha Signals | 30 days | Auto (daily) |
| Gem Discoveries | 90 days | Auto (weekly) |
| Predictions | Until resolved | Manual |
| Backtest Results | Permanent | Never |
| Dashboard History | 7 days | Auto (daily) |

---

## 🔔 Notification System

### High-Certainty Alerts (90+ Score)
```python
# In GitHub Actions workflow
if high_confidence_signals > 0:
    send_webhook_to_discord()
    send_telegram_notification()
    create_github_issue()
```

### Target Hit Notifications
```python
# When prediction hits target
if prediction_status == "WIN":
    alert_user(f"🎉 {symbol} hit target! +{gain}%")
```

---

## 🛠️ Troubleshooting

### Dashboard Not Updating
1. Check GitHub Actions status
2. Verify workflow ran successfully
3. Check `data.json` was committed
4. Wait for GitHub Pages deploy (1-2 min)

### Missing Data
```bash
# Force manual update
python monitoring/update_dashboard.py --force

# Check data directories exist
ls data/signals/
ls data/gems/
ls data/predictions/
```

### API Rate Limits
- CoinGecko: 50 calls/min (free tier)
- DexScreener: 300 calls/min
- GitHub API: 5000 calls/hour

**Solution:** Scans staggered with delays

---

## 🔐 Security

### API Keys (if needed)
- Stored in GitHub Secrets
- Never committed to repo
- Accessed via `${{ secrets.KEY_NAME }}`

### Data Privacy
- All data is public (prices, signals)
- No personal information stored
- No wallet addresses exposed

---

## 📊 Performance Metrics

### Current Update Latency
| Step | Time |
|------|------|
| API Calls | 30-60 seconds |
| Data Processing | 10-20 seconds |
| Git Commit | 5-10 seconds |
| Pages Deploy | 60-120 seconds |
| **Total** | **2-4 minutes** |

### Data Freshness
- Alpha Signals: 15 minutes max
- Gem Discovery: 15 minutes max
- Predictions: 15 minutes max
- Dashboard: 5 minutes (client refresh)

---

## 🎯 Summary

### Automatic Updates (No Action Needed)
✅ Every 15 minutes during market hours  
✅ Aggregated dashboard data  
✅ GitHub Pages auto-deploy  
✅ Client-side refresh every 5 min  

### Manual Override (When Needed)
✅ Trigger workflow from GitHub  
✅ Run local scripts  
✅ Force dashboard update  
✅ Custom scan parameters  

### Access Points
✅ Main: `/monitoring/dashboard/`  
✅ Individual system dashboards  
✅ Raw JSON data files  
✅ GitHub Actions logs  

---

**Your monitoring page is always up-to-date with live data from multiple sources, refreshed every 15 minutes automatically.**

*Last documentation update: 2026-02-13*
