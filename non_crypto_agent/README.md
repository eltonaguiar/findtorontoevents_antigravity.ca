# Non-Crypto Pick Generator Agent

## Purpose
Deploys enhanced, research-backed strategies for Forex, Equity (stocks/penny/meme), Commodities/Futures.
Fixes low WR/PnL by:
- Dedicated forex_strategies.py (new)
- Proven academic strats (Connors RSI2, Carry, Momentum)
- Filters: ATR RR>1.5, conf <=0.72 non-crypto, volume/HMA (future)
- Elite scoring + quality filter

## Quick Start
```bash
pip install -r requirements.txt
python main.py
```

**Output**: `picks.json` with elite-scored picks (conf>0.6, RR>1.5)

## Strategies
- **Forex** (6): Carry Trade, Asian Range, ORB, Connors RSI2, X-Sectional Mom, COT Proxy
- **Equity** (6): Momentum 12m, Penny Vol Break, Meme Velocity, Quality-Value, Risk-On, S/R Bounce
- **Commodities** (5): Seasonal, Gold Safe Haven, Oil Mom, Metals MR, Ag Spread

## Integration
- picks.json → alpha_engine database or confluence_pipeline
- Schedule: cron daily `cd non_crypto_agent && python main.py`

## Next
- Add HMA/volume filters to strats
- Backtest forward 50+ trades
- Promote to live if 50%+ WR