# Audit Dashboard — Data Quality & Feature Enhancement Design

**Date:** 2026-03-06
**URL:** https://findtorontoevents.ca/audit/
**Trigger:** External quality review identifying critical data gaps

## Problem Statement

The audit dashboard has a 44% win rate but -4750% total PnL, indicating catastrophic risk:reward.
The primary missing metric is **Profit Factor** (avg_win / avg_loss) — without it, win rate alone is misleading.
95% of strategies lack backtest validation, and the leaderboard ranks 1-trade strategies at #1.

## Changes

### 1. Generator (`audit_trail/dashboard_generator.py`)

**New leaderboard fields per strategy:**
- `fwd_avg_win` — mean PnL of winning trades
- `fwd_avg_loss` — mean abs(PnL) of losing trades
- `fwd_pf` — profit factor: sum(wins) / abs(sum(losses))
- `fwd_expectancy` — (WR × avg_win) - (LR × avg_loss)
- `fwd_max_dd` — max peak-to-trough drawdown from cumulative PnL
- `sample_quality` — "strong" (≥20), "moderate" (10-19), "weak" (5-9), "insufficient" (<5)

**New system stats fields:**
- `profit_factor`, `avg_win`, `avg_loss`, `expectancy`, `max_drawdown`

**New asset class breakdown fields:**
- `profit_factor`, `avg_win`, `avg_loss`, `expectancy`

### 2. Template UI (`audit_dashboard/template.html`)

**Overview Tab:**
- Add Profit Factor and Expectancy columns to asset class table
- Clickable counts: clicking Active/Closed counts drills to filtered Picks tab
- Top Systems: system name links to live dashboard, counts drill down
- "All Time" / "Last 30 Days" toggle for time-windowed view

**Leaderboard Tab:**
- Add Profit Factor, Expectancy, FWD Max DD columns
- Sample quality badge (color-coded by trade count)
- Min Trades filter dropdown (≥5, ≥10, ≥20)
- Decay warning: red left-border on rows with decay < -40%
- Dim rows with <5 trades
- Strategy names hoverable with performance tooltip
- System links in Systems column

**Systems Tab:**
- Add Profit Factor, Avg Win, Avg Loss, Expectancy, Max Drawdown rows
- Last Pick date/time prominently displayed
- System name links to live dashboard where URL exists
- Clickable Active/Closed counts drill to filtered Picks tab

**Active Picks Tab:**
- Correlation warning banner when ≥3 picks share strategy + direction on correlated assets

**Header:**
- Data age indicator: green (<15m), yellow (15-60m), red (>1hr)

### 3. System Dashboard Links

| System | URL |
|---|---|
| battleground | /battleground/ |
| alpha_engine | GitHub Pages /alpha/ |
| kimi_riseoftheclaw | /riseoftheclaw.html |
| baby_strats_forward | /battleground/ |

### 4. Policy: No Auto-Kill

Strategies are never auto-retired. All strategies continue running to allow recovery.
Time-windowed metrics (30-day) let users see improvement trends.
Sample quality badges flag statistical unreliability without hiding data.
