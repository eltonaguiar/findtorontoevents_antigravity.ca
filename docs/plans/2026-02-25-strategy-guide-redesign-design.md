# Strategy Guide Redesign — Approach A (In-Page)

**Date:** 2026-02-25
**Status:** Approved
**Scope:** Alpha Engine live_dashboard.html

## Problem

1. Strategy Guide shows only 8 of 42 strategies (static HTML cards)
2. "Why" reason text on pick cards uses jargon (r=, p-value, lag, Hurst H=) with no explanation
3. STRATEGY_GLOSSARY has 24 entries but 18 strategies have no glossary entry at all

## Solution

### 1. Dynamic Strategy Guide (replace static 8 cards)
- Generate cards from STRATEGY_GLOSSARY + strategy_performance.json
- Add category metadata (crypto/forex/equity/on-chain/quant) and style (momentum/reversal/breakout/carry/seasonal)
- Filter bar: Category pills + Style pills + search box
- Default: show top 8 by WR, "Show all N strategies" expander
- Each card: name (color by profitability), one-liner, live stats (WR/trades/P&L), expandable deep dive

### 2. Enhanced Jargon Tooltips
- Add ~10 statistical terms to JARGON dictionary (r=, p-value, p<0.05, lag, Hurst, H=, sigma, σ, 1-bar return, VR())
- Existing expandJargon() already handles rendering

### 3. Complete Glossary Coverage
- Add 18 missing strategy entries with: name, explain, source, category, style
- Total coverage: 42/42 strategies

## Files Modified
- `alpha_engine/live_dashboard.html` — all changes in this single file
