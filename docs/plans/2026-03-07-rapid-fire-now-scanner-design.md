# Rapid Fire (NOW.py) — Real-Time 1h Crypto Scanner

## Overview
Single-script scanner (`NOW.py`) that runs 8 proven strategies on top 50 USDT pairs,
targeting crypto that skyrockets within 1 hour. Tracks every pick in MySQL with dual
R:R tracking (1.5:1 and 2:1).

## Decisions
- **Pairs:** Top 50 USDT by market cap (auto-updated)
- **Trigger:** Manual (`python NOW.py`) + GitHub Actions every 15 min
- **R:R:** Track both 1.5:1 and 2:1 scenarios
- **Report:** Local + FTP deploy to findtorontoevents.ca/findcryptopairs/now.html
- **Name:** "Rapid Fire" / `RAPID_FIRE` in audit DB
- **Integration:** Full — Discord #fresh-picks, cross-aggregator, audit dashboard

## Strategies
1. MACD Crossover 5m
2. RSI Oversold Bounce
3. MACD + RSI Confluence (proven 65% WR)
4. Volume Spike Breakout
5. Bollinger Squeeze Expansion
6. EMA Stack Alignment
7. Funding Rate Reversal (proven 71% WR)
8. StochRSI + MACD Combo

## DB Tables
- `now_history` — every pick with dual TP/SL tracking
- `now_strategy_stats` — aggregate performance per strategy

## Files
- `NOW.py` — main scanner script
- `findcryptopairs/now.html` — live report page
- `.github/workflows/now-scanner.yml` — Actions automation
