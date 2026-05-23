# 🤖 Autonomous Crypto Trading Bot

**Fully autonomous trading system that runs 24/7 without any user intervention.**

[![Autonomous Trading](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/autonomous_trading.yml/badge.svg)](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/autonomous_trading.yml)

---

## 🚀 What Is This?

This is a **completely autonomous** cryptocurrency trading bot that:
- ✅ Runs automatically every 4 hours (24/7)
- ✅ Uses **FREE** data sources (no exchange account needed)
- ✅ Implements institutional-grade trading strategies
- ✅ Saves results directly to this repository
- ✅ Requires **ZERO** setup from users

---

## 📊 Live Performance

| Metric | Value |
|--------|-------|
| **Data Source** | CoinGecko + CryptoCompare (FREE) |
| **Trading Mode** | Paper Trading (Simulated) |
| **Run Frequency** | Every 4 hours |
| **Strategies** | Momentum, Mean Reversion, Order Book |
| **Assets** | BTC, ETH, SOL, ADA, DOT |

📈 **View Latest Results:** [PERFORMANCE_REPORT.md](PERFORMANCE_REPORT.md)

---

## 🔄 How It Works

```
Every 4 Hours:
┌─────────────────┐
│  GitHub Actions │ ← Triggered automatically
│   (Scheduled)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Fetch Prices   │ ← CoinGecko API (FREE)
│  (BTC, ETH...)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Run Strategies  │ ← Momentum, Mean Reversion
│  (Analyze Data) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Generate Signals│ ← BUY/SELL/HOLD
│  (Paper Trade)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Save Results    │ ← Committed to repo
│  (JSON + Log)   │
└─────────────────┘
```

---

## 🎯 Trading Strategies

### 1. Momentum Strategy
- **Entry:** EMA 12 crosses above EMA 26 + RSI > 50
- **Exit:** EMA 12 crosses below EMA 26 + RSI < 50
- **Rationale:** Trend-following based on institutional research

### 2. Mean Reversion
- **Entry:** Price below lower Bollinger Band + RSI < 30
- **Exit:** Price above upper Bollinger Band + RSI > 70
- **Rationale:** Statistical arbitrage from Jane Street research

### 3. Order Book Imbalance
- **Entry:** Bid volume > Ask volume by 20%+
- **Exit:** Ask volume > Bid volume by 20%+
- **Rationale:** Microstructure edge from Jump Trading research

---

## 📁 Repository Structure

```
.
├── live_trading_bot_canada.py      # Main trading bot
├── .github/workflows/
│   └── autonomous_trading.yml      # Auto-run every 4 hours
├── trading_results.json            # Latest results (auto-updated)
├── trading_bot.log                 # Detailed logs (auto-updated)
├── PERFORMANCE_REPORT.md           # Human-readable summary
└── requirements.txt                # Python dependencies
```

---

## 🔧 Technical Details

### Data Sources (FREE)
| Source | API Key | Rate Limit | Data Provided |
|--------|---------|------------|---------------|
| CoinGecko | Pre-configured | 10-30/min | Prices, Market Cap, Volume |
| CryptoCompare | Pre-configured | 100k/month | OHLCV, Historical Data |

### Risk Management
- **Max Risk Per Trade:** 2%
- **Max Positions:** 5
- **Stop Loss:** 2%
- **Take Profit:** 6%
- **Initial Capital:** $10,000 (simulated)

### Schedule
- **Frequency:** Every 4 hours
- **Times (UTC):** 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
- **Timezone:** Runs on GitHub's UTC servers

---

## 🎓 For Developers

### Want to Modify the Bot?

1. **Fork this repository**
2. **Edit `live_trading_bot_canada.py`**
3. **Push to your fork** - GitHub Actions will run automatically

### Key Configuration

```python
# In live_trading_bot_canada.py
config = Config(
    PRIMARY_EXCHANGE='FREE_DATA',  # Use free APIs
    INITIAL_CAPITAL=10000,          # Starting capital
    RISK_PER_TRADE=0.02,           # 2% risk per trade
    MAX_POSITIONS=5,               # Max concurrent positions
    CRYPTO_SYMBOLS=['BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 'DOT-USD']
)
```

---

## ⚠️ Disclaimer

**This is a PAPER TRADING bot (simulated).**

- No real money is used
- All trades are simulated
- For educational purposes only
- Past performance ≠ future results

**To trade with real money:**
1. Get API keys from Coinbase/Kraken/KuCoin
2. Add them to GitHub Secrets
3. Change `DRY_RUN` to `'false'`
4. **⚠️ Risk only what you can afford to lose**

---

## 📜 License

MIT License - Feel free to use, modify, and distribute.

---

## 🙏 Acknowledgments

- Strategies based on research from Jump Trading, Jane Street, and Virtu
- Data provided by CoinGecko and CryptoCompare
- Hosted on GitHub Actions (free tier)

---

**🤖 The bot is running autonomously right now. Check the [Actions tab](../../actions) to see it in action!**
