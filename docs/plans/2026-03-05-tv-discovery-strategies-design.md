# TV Discovery Strategies — Design Doc
**Date:** 2026-03-05

## Goal
Create 6 new incubator strategies sourced from TradingView discovery (Editor's Picks, LuxAlgo, lesser-known gems), wire them into paper trading, and backtest.

## Strategies

| # | Name | File | Logic |
|---|------|------|-------|
| 1 | SuperTrend AI Adaptive | crypto_supertrend_ai_adaptive_v1.py | Regime-adaptive SuperTrend + 5-factor score filter |
| 2 | VCP Minervini Breakout | crypto_vcp_minervini_breakout_v1.py | ATR contraction + pivot breakout + volume + EMA |
| 3 | HMM Regime Detector | crypto_hmm_regime_detector_v1.py | 3-state HMM (Bull/Range/Bear) regime filter |
| 4 | Liquidity Cluster Order Flow | crypto_liquidity_cluster_orderflow_v1.py | Volume profile POC + delta + void detection |
| 5 | Consecutive Candle Streak | crypto_consecutive_candle_streak_v1.py | Streak z-score mean reversion |
| 6 | Central Bank Liquidity Gap | crypto_central_bank_liquidity_v1.py | Hayes Fed BS-RRP-TGA formula |

## Architecture
- **Incubator:** `incubator/agents/claude_code_01/` (Signal class pattern)
- **Paper Trading:** `paper_trading/strategies/tv_discovery_strategies.py` (BaseStrategy wrapper)
- **Backtest:** Via existing `alpha_engine/backtest/engine.py`

## Conventions
- All follow existing Signal/class pattern with generate_signals()
- ATR-based TP/SL (3.0x TP, 2.25x SL)
- Multi-layer confluence (3-5 conditions AND'd)
- Min bars check, no lookahead bias
- Confidence = base + modifiers
