#!/usr/bin/env python3
"""Insert missing strategy descriptions into _STRATEGY_DESCRIPTIONS in template.html."""

import re

# New descriptions to insert — keyed by strategy name
NEW_DESCRIPTIONS = {
    # --- Non-crypto / multi-asset strategies ---
    'cftc_cot_commercial_signal': (
        "CFTC Commitment of Traders — Commercial Signal: Uses real CFTC Socrata API data. "
        "Detects when commercial hedgers (smart money) are heavily net-long (>55%) while speculators "
        "are net-short (>50%) → BUY. Opposite → SELL. 60-70% WR academic. "
        "Entry: weekly COT report divergence. TP=2x ATR, SL=1.5x ATR."
    ),
    'clone_hl_copy_PensionFund_24M': (
        "OKX Copy Trader Clone — PensionFund_24M: Mirrors the open position profile of the OKX "
        "top copy trader 'PensionFund_24M' (870-day track record, +58.6% PnL, 55.6% WR, 600 copiers). "
        "Entry: when this trader opens a new position. Direction matches trader's direction. "
        "Confidence scaled by trader's win ratio and AUM. TP/SL from ATR-based sizing."
    ),
    'clone_hl_copy_lb_None': (
        "OKX Copy Trader Clone — Leaderboard Top Trader: Mirrors positions of OKX leaderboard "
        "top traders (highest PnL ratio, >30-day track record). Entry: when a leaderboard trader "
        "opens a new position. Direction matches. Confidence based on trader's win ratio and AUM. "
        "TP/SL from ATR-based sizing."
    ),
    'cot_positioning': (
        "COT Positioning Strategy: Analyzes CFTC Commitments of Traders data for commodity and "
        "forex futures. Commercial net positioning z-score > +1.5 → BUY (smart money accumulation). "
        "Z-score < -1.5 → SELL (smart money distributing). Cross-referenced with Binance top "
        "trader L/S ratio. Entry: weekly COT divergence + price confirmation. TP=2x ATR, SL=1.5x ATR."
    ),
    'cta_commodity_momentum_term': (
        "CTA Commodity Momentum — Term Structure: Combines momentum ranking across lookback windows "
        "(1/3/6/12 month) with futures term structure (contango vs backwardation). "
        "Long the top-ranked commodity by momentum when in backwardation (term-structure bonus). "
        "Short the bottom-ranked when in contango. Entry: ranked momentum + term-structure alignment. "
        "TP=2.5x ATR, SL=1.5x ATR. Confidence from ADX + momentum percentile."
    ),
    'cta_cross_asset_tsmom': (
        "CTA Cross-Asset Time-Series Momentum: Classic TSMOM approach across commodities, FX, and "
        "equity index futures. 12-month lookback momentum signal: positive momentum → LONG, negative "
        "→ SHORT. Volatility-targeted position sizing (target 10% annualized vol). "
        "Entry: 12m return > 0 and volatility < threshold. TP/SL from ATR. Confidence from "
        "Sharpe ratio of the momentum signal."
    ),
    'forex_carry_momentum': (
        "Forex Carry + Momentum: Combines interest rate differential (carry) with EMA20/50 trend "
        "alignment. BUY when: (1) positive carry (long the high-yielding currency), (2) EMA20 > EMA50 "
        "(trend confirmation), (3) RSI < 70 (not overbought). SELL when negative carry + bearish "
        "trend + RSI > 30. Entry: carry > 2% annual + EMA stack aligned + RSI not extreme. "
        "TP=1.5x ATR, SL=1x ATR. Confidence from carry magnitude + trend strength."
    ),
    'forex_rsi2_mean_reversion': (
        "Forex Connors RSI-2 Mean Reversion: Connors RSI(2) pullback strategy — proven 68%+ WR "
        "in academic studies. BUY when: RSI(2) < 10 (deep oversold) AND price > SMA(200) "
        "(long-term uptrend). SELL when: RSI(2) > 90 (deep overbought) AND price < SMA(200). "
        "Entry: RSI2 extreme + trend filter. TP at SMA(5) or 1x ATR. SL at 1.5x ATR below "
        "recent swing. Confidence capped at 0.70 by _forex_conf_cap."
    ),
    'futures_bb_mean_reversion': (
        "Futures Bollinger Band Mean Reversion: Identifies overextended futures contracts using "
        "Bollinger Bands (20,2). BUY when: price < lower BB AND RSI < 30 AND volume > 1.2x avg "
        "(capitulation reversal). SELL when: price > upper BB AND RSI > 70 AND volume spike. "
        "Entry: BB extreme + RSI confirmation + volume spike. TP at BB midline. "
        "SL beyond BB by 0.5x ATR. Works on ES, NQ, CL, GC futures."
    ),
    'futures_momentum': (
        "Futures EMA Stack Momentum: Trend-following on commodity and index futures using "
        "EMA12/26/50 stack alignment. BUY when: EMA12 > EMA26 > EMA50 (full bullish stack) AND "
        "ADX > 20 (trending market) AND price > EMA12. SELL on full bearish stack + ADX > 20. "
        "Entry: EMA stack + ADX filter. TP=2x ATR, SL=1x ATR. Confidence from ADX strength "
        "+ stack alignment score. Metals (SI, HG, PL) favored historically."
    ),
    'ig_contrarian_sentiment': (
        "IG Client Sentiment Contrarian: Uses IG's retail client positioning data. When >70% of "
        "retail traders are LONG → SELL (contrarian fade). When >70% SHORT → BUY. The crowd is "
        "usually wrong at extremes. Entry: retail positioning >70% one-sided + price at support/"
        "resistance. TP=1.5x ATR, SL=1x ATR. Confidence from how extreme the positioning is "
        "(75%+ = higher confidence). Applied to major forex pairs."
    ),
    'myfxbook_retail_contrarian': (
        "Myfxbook Retail Positioning Contrarian: Similar to IG contrarian but uses Myfxbook's "
        "aggregated retail trader positioning across multiple brokers. When >65% retail LONG → SELL "
        "(fade the crowd). When >65% retail SHORT → BUY. Entry: retail extreme + RSI divergence + "
        "key level. TP=1.5x ATR, SL=1x ATR. Confidence from positioning extreme + RSI confirming "
        "exhaustion. Applied to AUDJPY, EURJPY, GBPJPY, EURUSD, GBPUSD, USDCAD."
    ),
    'regime_mild_bull': (
        "Regime Mild Bull: Broad market regime detection — when SPY > SMA50 AND VIX < 22 AND "
        "SPY 5d return > 0% (mildly bullish regime). Buys high-quality equity names that are "
        "in pullback within the uptrend. Entry: bullish regime + stock RSI(2) < 20 + SMA(200) "
        "uptrend. TP=7-8% target, SL=4-5%. Confidence from regime strength + stock quality. "
        "Picks: large-cap growth (GOOGL, SPY, SOFI)."
    ),
    'regime_strong_bull': (
        "Regime Strong Bull: Aggressive equity accumulation when SPY > SMA20 AND VIX < 18 AND "
        "SPY 5d > +2% (strong bull regime). Buys mega-cap tech leadership names. "
        "Entry: strong bull regime + stock breaking out to new highs + volume confirmation. "
        "TP=7-8% target, SL=4-5%. Confidence from regime strength (0.95 = max). "
        "Picks: MSFT, mega-cap tech leaders."
    ),
    'stocks_rsi2_pullback': (
        "Stocks RSI-2 Pullback: Connors RSI(2) pullback on large-cap equities. BUY when: RSI(2) < 10 "
        "(deeply oversold) AND price > SMA(200) (long-term uptrend intact) AND stock is in the "
        "S&P 500 or equivalent quality universe. SELL on RSI(2) > 90 + below SMA(200). "
        "Entry: RSI2 extreme + quality filter + uptrend. TP=4% (SMA5 target), SL=3% (1.5x ATR). "
        "Confidence from RSI2 depth + proximity to SMA(200). 88.9% WR on 9 trades."
    ),
    'stocks_rsi2_pullback_fast': (
        "Stocks RSI-2 Pullback — Fast Variant: Same core logic as stocks_rsi2_pullback but with "
        "shorter lookback (RSI2 fast exit). BUY: RSI(2) < 10 + price > SMA(200). "
        "Faster exit: sell when RSI(2) > 70 (vs 90 for standard). TP tighter at 3.5%, SL at 3%. "
        "Better for volatile names where you want to capture the snap-back quickly."
    ),
    'stocks_rsi2_pullback_slow': (
        "Stocks RSI-2 Pullback — Slow Variant: Same entry as stocks_rsi2_pullback but with longer "
        "hold. BUY: RSI(2) < 10 + price > SMA(200). Slower exit: hold until RSI(2) > 90 AND "
        "price closes below SMA(5). TP at 5%, SL at 3%. Better for slow-grind uptrends "
        "where you want maximum ride on the mean-reversion bounce."
    ),
    'stocks_rsi2_pullback_tight': (
        "Stocks RSI-2 Pullback — Tight Variant: Same RSI(2) < 10 entry but with tight risk "
        "management. TP=3.5% (tight), SL=2.5% (tight). For conservative entries where you want "
        "to be quickly stopped out if wrong. Best for high-quality names with tight ATR ranges."
    ),
    'stocks_rsi2_pullback_wide': (
        "Stocks RSI-2 Pullback — Wide Variant: Same RSI(2) < 10 entry but with wide stops for "
        "noisy names. TP=5.5% (wide), SL=4% (wide). Allows more room for the pullback to develop "
        "before the mean-reversion bounce. Best for volatile stocks or during choppy markets."
    ),

    # --- ML-enhanced strategies (pattern-based descriptions) ---
    'ml_enhanced_APEUSDT_1d_D_ensemble_stack': (
        "ML Enhanced — APE/USDT 1d Ensemble Stack: Machine learning ensemble (LightGBM + XGBoost "
        "+ RF stack) trained on APEUSDT daily candles. Entry: model predicts positive return with "
        ">55% probability. Direction from ensemble majority vote. TP=2x ATR, SL=1.5x ATR. "
        "Confidence from model probability + walk-forward validation score."
    ),
    'ml_enhanced_DYDXUSDT_15m_D_ensemble_stack': (
        "ML Enhanced — DYDX/USDT 15m Ensemble Stack: ML ensemble on DYDXUSDT 15-minute candles. "
        "Entry: ensemble majority vote on direction. Short-term momentum + orderflow features. "
        "TP=2x ATR, SL=1.5x ATR. Confidence from ensemble agreement + forward-test WR."
    ),
    'ml_enhanced_FETUSDT_1d_B_lightgbm': (
        "ML Enhanced — FET/USDT 1d LightGBM: LightGBM model trained on FETUSDT daily data. "
        "Entry: model predicts directional move with >60% confidence. Uses technical features "
        "(RSI, MACD, BB position, volume z-score). TP=2.5x ATR, SL=1.5x ATR. "
        "High confidence (0.80) indicates strong model conviction."
    ),
    'ml_enhanced_HBARUSDT_1d_D_ensemble_stack': (
        "ML Enhanced — HBAR/USDT 1d Ensemble Stack: ML ensemble on HBARUSDT daily candles. "
        "Entry: ensemble majority vote. Features include momentum, mean-reversion, and regime "
        "indicators. TP=2x ATR, SL=1.5x ATR. Confidence from model probability."
    ),
    'ml_enhanced_INJUSDT_1d_B_lightgbm': (
        "ML Enhanced — INJ/USDT 1d LightGBM: LightGBM on INJUSDT daily data. Entry: model "
        "signal with >55% probability. Features: RSI, MACD, volume, BB. TP=2x ATR, SL=1.5x ATR. "
        "Confidence 0.60 = moderate model conviction."
    ),
    'ml_enhanced_JTOUSDT_1d_B_lightgbm': (
        "ML Enhanced — JTO/USDT 1d LightGBM: LightGBM on JTOUSDT daily data. Entry: model "
        "directional prediction. Features: momentum + volatility regime. TP=2x ATR, SL=1.5x ATR. "
        "Confidence from model probability + walk-forward score."
    ),
    'ml_enhanced_POLUSDT_1d_B_lightgbm': (
        "ML Enhanced — POL/USDT 1d LightGBM: LightGBM on POLUSDT daily data. Entry: model "
        "directional prediction. Features: RSI, MACD, volume z-score, BB position. "
        "TP=2x ATR, SL=1.5x ATR. Confidence from model probability."
    ),
    'ml_enhanced_RENDERUSDT_1h_D_ensemble_stack': (
        "ML Enhanced — RENDER/USDT 1h Ensemble Stack: ML ensemble on RENDERUSDT 1-hour candles. "
        "Intraday model with orderflow + momentum features. Entry: ensemble majority vote. "
        "TP=2x ATR, SL=1.5x ATR. High confidence (0.80) = strong model conviction."
    ),
    'ml_enhanced_STRKUSDT_15m_D_ensemble_stack': (
        "ML Enhanced — STRK/USDT 15m Ensemble Stack: ML ensemble on STRKUSDT 15-minute candles. "
        "Short-term directional model. Entry: ensemble vote. Features: micro-momentum + volume "
        "profile. TP=2x ATR, SL=1.5x ATR. Confidence from model agreement."
    ),
    'ml_enhanced_TONUSDT_4h_D_ensemble_stack': (
        "ML Enhanced — TON/USDT 4h Ensemble Stack: ML ensemble on TONUSDT 4-hour candles. "
        "Entry: ensemble majority vote on direction. Features: momentum regime + volume. "
        "TP=2x ATR, SL=1.5x ATR. Confidence from model probability."
    ),
    'ml_enhanced_TRXUSDT_1d_B_lightgbm': (
        "ML Enhanced — TRX/USDT 1d LightGBM: LightGBM on TRXUSDT daily data. Entry: model "
        "directional prediction. Features: RSI, MACD, BB, volume z-score. TP=2x ATR, SL=1.5x ATR. "
        "Confidence from model probability + forward validation."
    ),
    'ml_enhanced_ZKUSDT_4h_D_ensemble_stack': (
        "ML Enhanced — ZK/USDT 4h Ensemble Stack: ML ensemble on ZKUSDT 4-hour candles. "
        "Entry: ensemble majority vote. Features: momentum + mean-reversion regime indicators. "
        "TP=2x ATR, SL=1.5x ATR. Confidence from model agreement score."
    ),
}

def main():
    filepath = "audit_dashboard/template.html"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the last entry before closing brace of _STRATEGY_DESCRIPTIONS
    # The block ends with:
    #   'tsmom_volscaled': '...',
    # };
    
    # Build the new entries string
    new_lines = []
    new_lines.append("")  # blank line before comment
    new_lines.append("  // --- Non-crypto / multi-asset strategies (added 2026-04-19) ---")
    
    # Non-ML strategies first
    non_ml_keys = [k for k in NEW_DESCRIPTIONS if not k.startswith("ml_enhanced_")]
    ml_keys = [k for k in NEW_DESCRIPTIONS if k.startswith("ml_enhanced_")]
    
    for key in non_ml_keys:
        desc = NEW_DESCRIPTIONS[key]
        # Escape single quotes in description
        desc_escaped = desc.replace("'", "\\'")
        new_lines.append(f"  '{key}': '{desc_escaped}',")
    
    new_lines.append("")
    new_lines.append("  // --- ML-enhanced per-symbol strategies (added 2026-04-19) ---")
    
    for key in ml_keys:
        desc = NEW_DESCRIPTIONS[key]
        desc_escaped = desc.replace("'", "\\'")
        new_lines.append(f"  '{key}': '{desc_escaped}',")
    
    new_entries_str = "\n".join(new_lines)
    
    # Insert before the closing "};" of _STRATEGY_DESCRIPTIONS
    # Find the exact anchor point
    anchor = "  'tsmom_volscaled': 'Time-series momentum with vol scaling: ranked lookback momentum, BTC regime filter, vol-targeted sizing per TSMOM literature (see tsmom_strategy.py).',\n};"
    
    if anchor not in content:
        print("ERROR: Could not find the anchor text for insertion!")
        print("Looking for tsmom_volscaled entry...")
        # Try to find just the closing pattern
        import sys
        sys.exit(1)
    
    replacement = (
        "  'tsmom_volscaled': 'Time-series momentum with vol scaling: ranked lookback momentum, BTC regime filter, vol-targeted sizing per TSMOM literature (see tsmom_strategy.py).',\n"
        + new_entries_str + "\n"
        + "};"
    )
    
    content = content.replace(anchor, replacement)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"SUCCESS: Inserted {len(NEW_DESCRIPTIONS)} strategy descriptions into template.html")
    print(f"  Non-ML strategies: {len(non_ml_keys)}")
    print(f"  ML-enhanced strategies: {len(ml_keys)}")

if __name__ == "__main__":
    main()
