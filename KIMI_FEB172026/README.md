# KIMI_FEB172026 - Institutional Trading System

**Version:** 11.0.0  
**Algorithms:** 68  
**Markets:** Crypto, Forex, Stocks, Meme Coins

## Overview

KIMI_FEB172026 is an institutional-grade algorithmic trading system designed to detect explosive market moves before they happen. It combines proven quant strategies from top firms (Jump Trading, Jane Street, Wintermute) with machine learning signal ranking and automated algorithm elimination.

## Core Features

### 1. Crypto Acceleration Engine
10 institutional-grade signal detectors:

| Signal | Strategy | Description |
|--------|----------|-------------|
| pump-detector-scout | Early Pump Detection | Price velocity ≥8% + volume 5× + RSI <65 |
| order-book-imbalance-scout | Order Flow | Bid/Ask ratio >2.0 = buying pressure |
| liquidation-cascade-scout | Forced Liquidations | Short liquidations >$5M = buy signal |
| acceleration-burst-scout | Momentum Jerk | 2nd derivative of price (acceleration) |
| coingecko-trending-spike-scout | Trending | CoinGecko trending + volume 3× |
| whale-size-trade-scout | Whale Detection | Individual trades >$100K |
| funding-rate-reversal-scout | Funding Arb | Funding turning negative→positive |
| multi-exchange-momentum-scout | Divergence | Cross-exchange price divergence |
| smc-order-block-scout | Smart Money | Order block retest patterns |
| smc-fvg-scout | Fair Value Gap | Imbalance zone detection |

### 2. ML Signal Ranker
- **Model:** Random Forest Classifier (200 estimators)
- **Features:** 24 engineered features
- **Target:** Binary WIN/LOSS prediction
- **Fallback:** Heuristic scoring when <50 training samples

### 3. Elimination Engine
- Tournament-style league system (Champions → Premier → Challenger)
- Auto-elimination for underperformers (<20 score, 7+ days)
- Auto-promotion for consistent performers (>55 score, 5+ days)
- 20 challenger algorithms in reserve pool

### 4. SQLite Store
- Persistent storage for signals, picks, rankings
- ML feature extraction for training
- Performance analytics and reporting

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python sqlite_store.py

# Run initial scan
python live_scanner.py
```

## Usage

### CLI Mode
```bash
python live_scanner.py
```

### Web Dashboard
```bash
python -m uvicorn live_scanner:create_app --reload --port 8000
```

Then open http://localhost:8000

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard HTML |
| `GET /api/signals` | Latest signals |
| `GET /api/scan` | Run live scan |
| `GET /api/performance` | Performance summary |
| `GET /api/rankings` | Algorithm rankings |
| `GET /api/signal/{symbol}` | Signal for specific symbol |

## Signal Format

```json
{
  "symbol": "BTC-USD",
  "signal_type": "pump-detector-scout",
  "direction": "LONG",
  "confidence": 0.85,
  "win_probability": 0.72,
  "entry_price": 96500.00,
  "take_profit": 98500.00,
  "stop_loss": 95500.00,
  "reason": "Early pump: +12% in 4h, Vol 5.5x, RSI 55",
  "position_size": 5000
}
```

## Performance Targets

- **Win Rate:** >65% for high-confidence signals
- **Risk/Reward:** Minimum 1:2 ratio
- **Sharpe Ratio:** >1.5
- **Max Drawdown:** <15%

## Architecture

```
KIMI_FEB172026/
├── crypto_acceleration_engine.py   # 10 signal functions
├── ml_signal_ranker.py             # Random Forest ranking
├── sqlite_store.py                 # Database persistence
├── elimination_engine.py           # Tournament management
├── live_scanner.py                 # Main integration + API
├── config/
│   └── telegram_channels.json      # Signal source config
├── data/
│   ├── kimi_trading.db            # SQLite database
│   └── latest_signals.json        # Web dashboard cache
└── templates/
    └── dashboard.html             # Web interface
```

## Research Backing

Strategies based on research from:
- Jump Trading (HFT, market microstructure)
- Jane Street (ETF arbitrage, options)
- Wintermute (crypto market making)
- Virtu Financial (statistical arbitrage)
- Smart Money Concepts (ICT/SMC methodology)

## License

Proprietary - Institutional Trading System
