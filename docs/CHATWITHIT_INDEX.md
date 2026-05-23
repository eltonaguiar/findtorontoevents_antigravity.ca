# CHATWITHIT — Quick Start for New AIs

> Last updated: 2026-03-17 02:30 UTC

## What Is This?
Multi-AI coordination system for a crypto/forex/equity trading platform. Multiple AIs (Claude, Grok, Mercury, Kilo-Code, Antigravity) collaborate on strategy development, signal generation, and portfolio management.

## File Architecture
| File | Purpose | Read When |
|------|---------|-----------|
| `docs/CHATWITHIT_INDEX.md` | This file — start here | First time joining |
| `docs/CHATWITHIT.md` | Active coordination log | Understanding recent decisions |
| `docs/CHATWITHIT_STATUS.md` | Current state snapshot | Checking what's live now |
| `docs/CHATWITHIT_ARCHIVE_PRE_MAR12.md` | Historical archive | Deep context on past decisions |

## Key Systems
Brief 1-liner for each system (read the actual files for details):
- **Alpha Engine** (`alpha_engine/`) — 100+ strategy scanner, runs every 30 min
- **KIMI Rise of the Claw** (`KIMI_RISEOFTHECLAW/`) — 81-algorithm crypto scanner, runs every 15 min
- **Cross-Aggregator** (`cross_aggregation/`) — Consensus engine across systems
- **Audit Dashboard** (`audit_dashboard/`) — Live monitoring UI

## Scoring System
- **elite_score** (0-100): Computed in `alpha_engine/elite_scorer.py`, 7 components
- **Top components:** ML Score (35 pts), Forward Win Rate (30 pts), Confluence (15 pts)
- **Grades:** S (90+), A (75+), B (60+), C (45+), D (30+), F (<30)
- **For 20x leverage:** Only use Grade B+ (score >= 65)

## Key Rules (MUST READ)
1. **API Failover**: Never use single Binance API. Always 3+ fallback chain.
2. **Mutate Before Kill**: Try inverse/DNA mutation before killing any strategy.
3. **No SHORTs**: System-wide SHORT WR = 20.5%. Hard-blocked until WR > 40%.
4. **Never test HTML generators locally**: They overwrite live files.
5. **System freeze**: No new strategies until active count <= 20.
6. **TP/SL standard**: 1-1.5% TP, 1.5-2% SL (or ATR-scaled: 0.8x ATR TP, 0.5x ATR SL).

## How to Contribute
1. Read `CHATWITHIT_STATUS.md` for current state
2. Check open action items in `CHATWITHIT.md`
3. Tag your entries with `[YOUR_NAME]` and date
4. Update `CHATWITHIT_STATUS.md` if you change system state
5. Newest entries go at the TOP of the log

## Terminology
WR=Win Rate, PnL=Profit/Loss, TP=Take Profit, SL=Stop Loss, R:R=Risk:Reward, OOS=Out-of-Sample, MFE=Max Favorable Excursion, AUC=Area Under Curve, PF=Profit Factor, ATR=Average True Range
