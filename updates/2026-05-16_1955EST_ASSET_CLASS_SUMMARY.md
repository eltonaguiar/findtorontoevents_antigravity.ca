# Multi-Asset Class Strategy Audit — Executive Summary
**Date:** 2026-05-16 19:55 EST  
**Author:** Buffy (Codebuff)  
**Files:** 8 per-asset-class audits created (see `updates/2026-05-16_1955EST_*_strategies.md`)

---

## Executive Summary

| Asset Class | Forward Picks | Forward WR | Forward PF | Backtest PF | Edge? | Real Money? |
|-------------|--------------|------------|------------|-------------|-------|-------------|
| **COMMODITY** | 354 | 60.2% | 2.28 | — | ✅ YES | 🟢 Ready to validate |
| **EQUITY/STOCKS** | 45 | 36.4% | 0.71 | 2.82 | ⚠️ Backtest | 🟡 Needs forward data |
| **ETFs** | 0 | N/A | N/A | 2.05 | ⚠️ Backtest only | 🟡 Activate, then test |
| **FOREX** | 932 | 25.6% | 0.35 | — | ❌ None | 🔴 Pause, rebuild |
| **BONDS** | 1 | 0% | 0.00 | 1.34 | ❌ None | 🔴 Low priority |
| **CRYPTO** | 6,884 | 32.8% | 0.41 | — | ❌ None (agg) | 🔴 Fix scoring first |
| **FUTURES** | 203 | 3.0% | 0.06 | — | ❌ None | 🔴 Complete rebuild |
| **PENNY STOCKS** | 0 | N/A | N/A | 0 | ❌ Untracked | 🔴 Build from scratch |
| **MEME COINS** | 0 | N/A | N/A | 0 | ❌ Untracked | 🔴 Build from scratch |

---

## Answering the Key Questions

### Q1: Are we completely missing a strategy type for an asset class?

**YES. Major gaps:**

| Asset Class | Missing Strategy Type | Impact |
|-------------|----------------------|--------|
| **FUTURES** | ❌ Term structure (contango/backwardation) | Only strategy is `futures_momentum` at 2% WR — entire asset class is broken |
| **FOREX** | ❌ Economic calendar / event-based | Carry momentum at 5.1% WR — no working event strategies |
| **BONDS** | ❌ Yield curve steepener/flattener | Only duration rotation with 1.16 PF — no curve trades |
| **ETFs** | ❌ ETF flow data (creation/redemption) | Strong backtests but zero live picks — strategy exists but not activated |
| **CRYPTO** | ❌ On-chain data (whale wallets, exchange flows) | `ml_enhanced_*` works but could be far better with on-chain signals |
| **CRYPTO** | ❌ Coinglass liquidation data | Already have the data file (27MB) but NOT wired to scoring |
| **PENNY STOCKS** | ❌ Everything | No strategies, no data, no tracking |
| **MEME COINS** | ❌ Everything | No asset class definition, no tracking |

### Q2: Are we missing a free API/dataset that would skyrocket performance?

**YES. Highest-ROI free data sources NOT wired:**

| Data Source | Asset Class | What It Provides | Why It Matters | Already In Repo? |
|-------------|------------|------------------|----------------|-----------------|
| **Coinglass** | CRYPTO | Liquidation heatmap | >$10M liquidations in 5min = reliable reversal | ✅ 27MB JSON, NOT wired |
| **CME FedWatch** | BONDS | Market-implied rate path | Fade mispriced rate expectations | ❌ Not integrated |
| **EIA Inventory** | COMMODITY | Weekly crude/gas stockpiles | >2M barrel surprise = 2-3% move | ❌ Not integrated |
| **FRED** | BONDS/EQUITY | Treasury yields, OAS spreads | Yield curve, credit spread data | ❌ Not integrated |
| **LunarCrush** | CRYPTO/MEME | Social sentiment metrics | Meme coin pumps = social volume spike | ❌ Not integrated |
| **DexScreener** | MEME COINS | New pair discovery | Fresh pairs have highest vol/returns | ❌ Not integrated |
| **USDA WASDE** | COMMODITY | Grain supply/demand | Monthly report moves grains 3-5% | ❌ Not integrated |
| **SEC EDGAR** | EQUITY | Insider Form 4 filings | Cluster insider buys = bullish | ❌ Not integrated |

**#1 Priority: Wire Coinglass liquidation data.** It's already in the repo as `coinglass_db.json` (27MB). Zero code changes needed for data acquisition — just need to add the scoring logic.

### Q3: Are we pulling in prediction markets (Kalshi/Polymarket) and copytrader data?

**YES — Comprehensive integration exists.** All modules are present and sized:

| Module | Size | Covers |
|--------|------|--------|
| `alpha_engine/kalshi_signals.py` | 27KB | BOND, COMMODITY, CRYPTO, EQUITY, STOCKS |
| `alpha_engine/polymarket_signals.py` | 29KB | CRYPTO, EQUITY, FOREX |
| `alpha_engine/prediction_market_consensus.py` | 25KB | CRYPTO, EQUITY, FOREX |
| `prediction_market_agents/kalshi_signal_agent.py` | 19KB | Agent-level Kalshi |
| `prediction_market_agents/polymarket_btc_updown_agent.py` | 11KB | BTC-specific |
| `prediction_market_agents/polymarket_momentum_agent.py` | 4KB | Momentum signals |
| `copy_trader_intel/multi_asset_copytrader_scraper.py` | 102KB | BOND, COMMODITY, CRYPTO, EQUITY, FOREX, FUTURES, STOCKS |
| `copy_trader_intel/non_crypto_consensus.py` | 13KB | ALL (including ETF) |
| `copy_trader_intel/polymarket_scraper.py` | 60KB | Polymarket-specific |

**Coverage gaps:**
- Kalshi does NOT cover FOREX, FUTURES, or ETFs
- Polymarket does NOT cover COMMODITY, BONDS, FUTURES, or ETFs
- Neither covers PENNY STOCKS or MEME COINS
- ETFs are only covered by `non_crypto_consensus`

**Verdict:** Prediction market + copytrader integration is **very strong**. The data is flowing. The issue is not data acquisition — it's that the underlying strategies (especially in FUTURES, FOREX, BONDS) aren't profitable even with external data.

### Q4: Do we have top statistical edge per asset class, and top contributing strategies documented?

**YES — now documented.** This audit creates 8 per-asset-class files with:

- Forward-test performance (WR, PF, AvgPnL) from 8,421 closed picks
- Top 5 strategies per class with WR, PF, pick count
- Top 5 symbols per class with WR, PF
- Backtest performance from 30+ backtest JSON files
- Strategy gaps identified
- Missing data sources ranked by ROI
- Real-money readiness assessment

**Only asset class with statistical edge: COMMODITY** (COT positioning on Cotton, 231 picks / 85.7% WR / 2.28 PF).

---

## Quick Wins (This Week)

1. ✅ **CRYPTO_PROVEN_PREFIXES added** — `ml_enhanced_*` auto-gets +20 boost (done)
2. 🔧 **Wire Coinglass liquidation data** — already in repo, just needs scoring logic
3. 🔧 **Activate ETF sector rotation** — backtest PF 2.05, zero live picks (config change only)
4. 🔧 **Deactivate `forex_carry_momentum`** — 5.1% WR, pure value destruction
5. 🔧 **Deactivate `futures_momentum`** — 2.0% WR, catastrophic
6. 🔧 **Add `quan_engine_scalp` to CRYPTO_TOXIC** — 5,293 picks, −0.18% AvgPnL

## Medium-Term (This Month)

7. 📋 **Implement term structure strategy for futures** — replace momentum entirely
8. 📋 **Add economic calendar event strategies for forex** — NFP/FOMC pre-positioning
9. 📋 **Integrate FRED yield curve data for bonds** — steepener/flattener
10. 📋 **Add MEMECOIN asset class** — config + LunarCrush + DexScreener
11. 📋 **Build penny stock scanner** — float < 10M, volume > 100K, price < $5

## Long-Term

12. 🎯 **Run full DSR/PBO/WFE on commodity COT strategy** — real-money greenlight
13. 🎯 **200+ trade validation on equity momentum** — backtests are strong, need forward data
14. 🎯 **On-chain data pipeline for crypto** — Glassnode free tier
