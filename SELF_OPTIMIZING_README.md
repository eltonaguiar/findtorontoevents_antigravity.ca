# 🤖 Self-Optimizing Autonomous Trading Bot

## 🚀 FULLY AUTONOMOUS - ZERO USER SETUP REQUIRED

This trading bot runs **completely autonomously** - it validates its own performance and tweaks itself live, without any human intervention.

---

## ✨ Key Features

### 1. ✅ Live Performance Validation
- **Tracks every trade** and calculates win rates per strategy
- **Validates performance** every 4 hours automatically
- **Detects underperforming strategies** and adjusts weights
- **Saves complete history** for analysis

### 2. 🎛️ Auto-Tweaking (Self-Optimization)

| Condition | Action | Result |
|-----------|--------|--------|
| Win rate < 45% | Reduce risk | Protect capital |
| Win rate > 65% | Increase risk | Capture more profit |
| High volatility | Faster EMAs | Better trend capture |
| Low volatility | Slower EMAs | Reduce false signals |
| Strategy underperforming | Reduce weight | Focus on winners |

### 3. 🔄 Self-Healing
- **API Failover**: CoinGecko fails → Auto-switches to CryptoCompare
- **Auto-Recovery**: Retries failed APIs after cooldown
- **No Downtime**: Always has backup data source

### 4. 📊 Live Dashboard
- Auto-generates `PERFORMANCE_DASHBOARD.md`
- Shows real-time metrics
- Displays optimization recommendations
- Updates every 4 hours

---

## 📈 How It Works

```
Every 4 Hours:
┌─────────────────────┐
│ 1. VALIDATE         │ ← Check last 20 trades
│    PERFORMANCE      │   Calculate win rates
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 2. AUTO-TWEAK       │ ← Adjust risk & parameters
│    PARAMETERS       │   based on performance
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 3. FETCH DATA       │ ← Get prices (with failover)
│    (Self-Healing)   │   CoinGecko → CryptoCompare
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 4. GENERATE SIGNALS │ ← Adaptive strategies
│    (Auto-Adapt)     │   EMA periods adjust
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 5. EXECUTE TRADES   │ ← Paper trading
│    (Simulated)      │   No real money
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 6. SAVE RESULTS     │ ← Commit to repo
│    & DASHBOARD      │   Auto-push to GitHub
└─────────────────────┘
```

---

## 🎯 Trading Strategies (Auto-Adaptive)

### Adaptive Momentum
- **Normal conditions**: EMA 12/26 crossover
- **High volatility**: Auto-switches to EMA 8/21
- **RSI confirmation**: Adjustable threshold

### Adaptive Mean Reversion
- **Normal conditions**: 2σ Bollinger Bands
- **High volatility**: Widens to 2.5σ
- **Low volatility**: Tightens to 1.5σ

---

## 📊 Performance Metrics Tracked

| Metric | Description | Auto-Action |
|--------|-------------|-------------|
| Win Rate | % of winning trades | Adjust risk up/down |
| Total P&L | Cumulative profit/loss | Track overall performance |
| Strategy Win Rate | Per-strategy performance | Adjust strategy weights |
| Current Risk | % risk per trade | Dynamic 1.4% - 2.4% |
| Return % | Total return vs initial | Primary success metric |

---

## 🔄 Automation Schedule

- **Frequency**: Every 4 hours
- **Times (UTC)**: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
- **Trigger**: GitHub Actions (free tier)
- **Commits**: Results auto-pushed to repository

---

## 📁 Files Auto-Updated

| File | Content | Update Frequency |
|------|---------|------------------|
| `trading_results.json` | Full trade data | Every 4 hours |
| `performance_history.json` | Historical validation | Every 4 hours |
| `trading_bot.log` | Detailed logs | Every 4 hours |
| `PERFORMANCE_DASHBOARD.md` | Human-readable summary | Every 4 hours |

---

## 🎓 For Users

### What You Need to Do
**NOTHING!** The bot runs autonomously.

### What You Can Do (Optional)

1. **Watch It Run**
   - Go to [Actions tab](../../actions)
   - See it run every 4 hours
   - View live logs

2. **Check Performance**
   - Open `PERFORMANCE_DASHBOARD.md`
   - See current metrics
   - Read optimization recommendations

3. **Fork & Customize**
   ```bash
   # Fork the repository
   # Edit self_optimizing_bot.py
   # Push changes - bot auto-adapts
   ```

---

## ⚙️ Configuration (Optional)

Set these environment variables in GitHub Secrets to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `INITIAL_CAPITAL` | 10000 | Starting capital |
| `RISK_PER_TRADE` | 0.02 | Base risk (2%) |
| `MAX_POSITIONS` | 5 | Max concurrent trades |
| `MIN_WIN_RATE_THRESHOLD` | 0.45 | Reduce risk below this |
| `HIGH_WIN_RATE_THRESHOLD` | 0.65 | Increase risk above this |

---

## 🛡️ Risk Management (Auto-Adjusted)

```
Win Rate < 45%  →  Risk: 2.0% → 1.4%  (Protect capital)
Win Rate 45-65%  →  Risk: 2.0%         (Normal operation)
Win Rate > 65%   →  Risk: 2.0% → 2.4%  (Capture more profit)
```

**Hard Limits:**
- Minimum risk: 1%
- Maximum risk: 5%
- Max positions: 5
- Stop loss: 2% per trade

---

## 📜 Example Performance Log

```
🤖 SELF-OPTIMIZING BOT - 2026-02-18T04:25:51
==================================================
📊 PORTFOLIO STATS
==================================================
💰 Equity: $10,450.00
💵 Cash: $5,230.00
📈 Open Positions: 2
🔄 Total Trades: 15
🎯 Win Rate: 68.0%
📉 Current Risk: 2.4% (increased due to high win rate)
💵 Total P&L: +$450.00
📊 Return: +4.50%

🎛️ OPTIMIZATION RECOMMENDATIONS:
   • Win rate 68.0% excellent. Increasing risk slightly.
   • Increasing AdaptiveMomentum weight due to strong performance
```

---

## 🔗 Repository Structure

```
.
├── self_optimizing_bot.py          ← Main bot (auto-validates & tweaks)
├── .github/workflows/
│   └── self_optimizing_trading.yml ← Auto-runs every 4 hours
├── trading_results.json            ← Latest results (auto-updated)
├── performance_history.json        ← Validation history (auto-updated)
├── PERFORMANCE_DASHBOARD.md        ← Live dashboard (auto-updated)
└── SELF_OPTIMIZING_README.md       ← This file
```

---

## ⚠️ Disclaimer

**This is PAPER TRADING (simulated).**
- No real money is used
- All trades are simulated
- For educational purposes
- Past performance ≠ future results

**To use real money:**
1. Get exchange API keys
2. Add to GitHub Secrets
3. Set `DRY_RUN=false`
4. **⚠️ Risk only what you can afford to lose**

---

## 🙏 Acknowledgments

- Strategies based on Jump Trading, Jane Street, Virtu research
- Data from CoinGecko & CryptoCompare (free tiers)
- Hosted on GitHub Actions (free tier)

---

**🤖 The bot is running autonomously RIGHT NOW. Check the [Actions tab](../../actions) to watch it work!**
