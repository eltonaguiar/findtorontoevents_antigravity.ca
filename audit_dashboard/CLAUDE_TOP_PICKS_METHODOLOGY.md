# Claude Top Picks — Methodology & Architecture

**Version:** 1.0 | **Created:** 2026-03-14 | **Author:** Claude Opus 4.6

## Overview

Claude Top Picks is a curated selection of 3 highest-conviction trades from across all scanning systems (momentum scalp, tracked live picks, genesis momentum blend). Picks are selected through multi-factor analysis and auto-tracked against live Binance prices for 24h with full P/L reporting.

## Selection Criteria (Multi-Factor Analysis)

Each pick is scored across 5 dimensions:

| Factor | Weight | Why |
|--------|--------|-----|
| RSI Position | High | RSI < 65 = not overbought, room to run. RSI 30-45 ideal for entry |
| Volume Liquidity | High | Min $1M 24h volume, prefer >$10M for clean entry/exit |
| Momentum Quality | Medium | Steady gains preferred over spike-then-dump patterns |
| Genesis Score | Medium | Multi-indicator consensus (SuperTrend, ADX, RSI, MACD, momentum) |
| Sector Narrative | Low | AI, meme revival, L1 chains — active narratives get slight edge |

## Data Pipeline

```
Binance API (24h tickers)
    ↓
momentum_scalp_scanner.py → momentum_scalp_picks.json (44+ picks)
generate_tracked_picks.py → tracked_live_picks.json (11+ picks)
    ↓
Claude Multi-Factor Analysis (best 3)
    ↓
claude_top_picks.json ← check_top_picks_outcome.py (every 4h)
    ↓
audit_dashboard/index.html → "Claude Top Picks" tab
```

## Files

| File | Purpose |
|------|---------|
| `audit_dashboard/data/claude_top_picks.json` | Active picks + historical rounds + lifetime stats |
| `audit_dashboard/check_top_picks_outcome.py` | Fetches Binance prices, checks TP/SL/expiry, updates JSON |
| `audit_dashboard/index.html` | Dashboard tab with live P/L, price visualizer, history |
| `.github/workflows/momentum-scanner.yml` | Runs scanner + outcome checker every 4h |

## Outcome Rules

- **TP Hit** within 24h = WIN (target: 1.33x R:R)
- **SL Hit** within 24h = LOSS
- **Expired** after 24h = close at current price, P/L determines outcome
- All picks use ATR-based TP/SL levels

## Dashboard Features

- Live Binance price fetching on page load
- Unrealized P/L with color coding
- TP/SL distance indicators
- Price position visualizer (SL ← → TP bar with entry + live markers)
- Historical round tracking with cumulative stats
- Win rate, avg PnL, best/worst pick tracking

## Round 1 — Initial Picks (2026-03-14)

| # | Symbol | Entry | TP | SL | Confidence | Reasoning |
|---|--------|-------|----|----|------------|-----------|
| 1 | RENDERUSDT | 1.847 | 1.945 | 1.7735 | 85% | AI sector leader, RSI=40, $35M vol, not overbought |
| 2 | TRUMPUSDT | 4.168 | 4.5537 | 3.8787 | 90% | Genesis 9/10, RSI=45 after +39% (consolidated), $185M vol |
| 3 | SEIUSDT | 0.0667 | 0.0685 | 0.0654 | 85% | ADX=24 (strongest trend), RSI=41, L1 blockchain |

First outcome check (13 min after entry):
- TRUMPUSDT: **+2.21%** (in profit)
- SEIUSDT: **+0.15%** (slight up)
- RENDERUSDT: **-0.43%** (slight dip, well above SL)
- Round avg: **+0.64%**
