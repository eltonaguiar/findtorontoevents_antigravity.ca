# Antigravity Top Picks — Methodology & File Documentation

**Date:** March 13, 2026 23:30 EST  
**Author:** Antigravity AI  
**Version:** v1.0.0

---

## Overview

The Antigravity Top Picks system is a concentrated 3-pick portfolio selected from a universe of 557 Binance USDT pairs. Unlike the broader 51-pick forward-test (which tracks all signals found), the Top Picks represent the highest-conviction, best risk-adjusted trades identified by the MEGA SCANNER v2.

## Selection Methodology

### Step 1: Universe Scan
- Scanned **557 USDT pairs** from Binance (all perpetual futures pairs)
- Deep-scanned **123 pairs** that passed initial volume filters (>$500K 24h volume)
- Filtered out **15 scam/pump-and-dump** tokens using 6-layer scam filter

### Step 2: Signal Detection
Applied 5 Antigravity BUY signal strategies:
1. **Momentum Cascade** — Triple-speed momentum (3/8/21 bar) all positive
2. **Gravity Well** — Oversold RSI with bullish momentum reversal
3. **EMA Stack** — Bullish EMA alignment (9 > 21 > 50)
4. **RSI Bounce** — RSI recovering from oversold (<30) within 3 bars
5. **Volume Breakout** — Volume 2x above 20-bar average with positive price action

### Step 3: Ranking & Selection
From 65 total signals, selected 3 using these criteria:
- **Not chasing pumps** — Excluded symbols already up >15% (TRUMP +40%, DEGO +19%)
- **Signal diversity** — One pick per signal type (Cascade, RSI Bounce, EMA Stack)
- **Risk/Reward** — Prioritized RR > 1.3x
- **Liquidity** — Minimum $28M 24h volume
- **Narrative strength** — AI/ML sector (hottest crypto narrative)
- **Mean-reversion balance** — ADA provides conservative oversold-bounce hedge

### Final Picks

| Rank | Symbol | Signal | Entry | TP | SL | R:R | Confidence |
|------|--------|--------|-------|-----|-----|-----|-----------|
| 1 | TAOUSDT | Momentum Cascade | $245.00 | $258.47 (+5.5%) | $234.90 (-4.1%) | 1.33x | 82% |
| 2 | ADAUSDT | RSI Bounce | $0.2657 | $0.2717 (+2.3%) | $0.2621 (-1.4%) | 1.67x | 70% |
| 3 | RENDERUSDT | EMA Stack | $1.85 | $1.948 (+5.3%) | $1.7765 (-4.0%) | 1.33x | 74% |

**Portfolio Avg:** TP +4.35% | SL -3.15% | R:R 1.44x | Confidence 75.3%

## Files Changed

### New Files Created
| File | Purpose |
|------|---------|
| `audit_dashboard/antigravity_picks.html` | Standalone live tracker page with Binance price feeds, real-time P/L, historical snapshots, equity curve, CSV export |
| `audit_dashboard/antigravity_picks_data.json` | Data file with 3 picks including rationale, entry/TP/SL, tracking fields |
| `audit_dashboard/antigravity_picks_methodology.md` | This file — documents methodology and file structure |
| `genome/mutation_lab/ag_forward_tracker.py` | Forward-test tracking pipeline (create/check/report) |
| `genome/data/ag_forward_test_tracked.json` | 51 broad forward-test picks with timestamps |
| `genome/data/ag_forward_test_report.md` | Report template for forward-test results |

### Modified Files
| File | Change |
|------|--------|
| `audit_dashboard/template.html` | Added "🚀 Antigravity Top Picks" tab button in tab bar |
| `docs/CHATWITHIT.md` | Added v108 (scan results), v110 (forward-test pipeline), v111 (this entry) |

## Tracking Architecture

### Live Tracking (antigravity_picks.html)
- Fetches live prices from **Binance REST API** every 10 seconds
- Calculates **unrealized P/L** in real-time for each pick
- Automatically detects **TP/SL hits** and updates outcome badges
- Stores **P/L snapshots every 5 minutes** in localStorage
- Renders **equity curve SVG** from snapshot history
- Supports **CSV export** of all historical snapshots

### Forward-Test Tracking (ag_forward_tracker.py)
- 51 broader picks tracked with exact UTC/EST entry timestamps
- `check` command fetches 1h candles from Binance and only checks post-entry bars
- `report` command generates CHATWITHIT.md-formatted performance summaries
- 24h max hold time, auto-expires picks

## Risk Disclosure
- These are AI-generated signals, NOT financial advice
- Past scan performance does not guarantee future results
- The initial outcome checker had a bug (checking pre-entry bars) — was caught and fixed within minutes
- All tracking is transparent and documented in CHATWITHIT.md
