# Meme Coins — Asset Class Reference

## Overview
Meme coins are **deprioritized**. Pure sentiment-driven with no fundamental anchor. Included for completeness but capital allocation should be minimal or zero. Our crypto prediction systems have consistently underperformed.

## Status: DEPRIORITIZED
- No new portfolios planned
- No active scanning
- Existing KIMI signals for meme coins remain in monitoring-only mode
- Will revisit only if sentiment detection improves significantly

## Why Deprioritized
1. Crypto prediction has failed to be reliable across our systems
2. Meme coins are the worst subset — pure speculation
3. 150%+ daily swings make risk management nearly impossible at leverage
4. No fundamental valuation anchor (unlike stocks/forex)

## Existing Infrastructure (read-only)
- `alpha_engine/crypto_strategies.py` — includes `signal_pump_detector`, `signal_whale_size_trade`
- `KIMI_RISEOFTHECLAW/` — 81 algorithms monitoring crypto (not meme-specific)
- Consensus dashboard at `cross_aggregation/consensus_dashboard.html`

## If Revisiting Later
- **Strategy candidates:** `signal_pump_detector`, `signal_whale_size_trade`, social sentiment scrapers
- **Risk:** ≤ 0.5% capital per trade, max 3 concurrent positions
- **Filter:** Volatility ≤ 150%, TP/SL ratio ≥ 1.5
- **Requirement:** Must demonstrate p < 0.05 in 30-day forward test before any capital allocation

## Action Items
- [ ] _(Future)_ Build social sentiment scraper for Twitter/Telegram meme coin mentions
- [ ] _(Future)_ Backtest pump_detector on historical meme coin data
- [ ] _(No action now)_ — Focus resources on futures, stocks, and forex instead
