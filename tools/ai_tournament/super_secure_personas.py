"""Super Secure Picks — conservative personas for each asset class.

Criteria (hedge fund capital preservation standard):
  - F-Score >= 7/9 (equity only)
  - Altman Z'' >= 2.6 (equity only) 
  - Beneish M <= -1.78 (equity only)
  - WR >= 55% at persona level with n >= 30
  - Max Drawdown <= 10% trailing 6 months
  - Sharpe >= 0.5 trailing 3 months
  - Beta <= 1.2
  - Kelly allocation <= 1%
  - Position size <= 1.5% per trade
"""

SUPER_SECURE_PERSONAS = {
    "super_secure_value": {
        "asset_class": "EQUITY",
        "philosophy": "Capital preservation through deep value investing in financially sound, non-manipulated companies with strong cash flows. Filters out ALL speculative names.",
        "min_score": 0.70,
        "entry_criteria": [
            "F-Score >= 7/9 (Piotroski financial health)",
            "Altman Z'' >= 2.6 (bankruptcy risk safe zone)",
            "Beneish M <= -1.78 (no earnings manipulation)",
            "ROIC >= 15% (quality capital allocator)",
            "FCF Yield >= 5% (strong free cash flow generation)",
            "Price <= 0.75 * Intrinsic Value (margin of safety >= 25%)",
            "Market Cap >= $10B (avoid micro-cap liquidity risk)",
        ],
        "exit_criteria": [
            "Trailing stop at 2x ATR(14) from peak",
            "Hard stop at -8% (max loss per position)",
            "Take profit at 90% of intrinsic value (don't hold to full IV)",
            "Time stop: exit after 90 days if no price movement > 3%",
        ],
        "risk_factors": [
            "Value traps — companies cheap for structural reasons",
            "Sector concentration risk — avoid > 30% in any GICS sector",
            "Regulatory risk — exclude companies with pending antitrust/regulation",
        ],
        "rr_target": "2.0 to 3.0",
        "max_risk_pct": 1.5,
        "confidence_threshold": 0.70,
        "worst_conditions": [
            "Momentum-driven markets where value underperforms",
            "Rapid industry disruption making fundamentals obsolete",
        ],
    },
    
    "super_secure_macro": {
        "asset_class": ["FOREX", "BOND"],
        "philosophy": "Macro-conviction picks with regime confirmation from FRED data (yield curve, inflation, unemployment). Only trade when macro aligns with technical setup.",
        "min_score": 0.65,
        "entry_criteria": [
            "FRED macro regime confirms direction (expansion → risk-on, contraction → risk-off)",
            "Yield curve slope confirms (steepening = long bonds, flattening = short)",
            "Real rate differential >= 0.5% for carry trades",
            "VIX < 25 (low stress environment for macro trades)",
            "RSI(14) confirming momentum direction (not counter-trend)",
        ],
        "exit_criteria": [
            "Trailing stop at 1.5x ATR(14)",
            "Hard stop at -5%",
            "Exit when macro regime flips or VIX > 30",
        ],
        "risk_factors": [
            "Central bank intervention invalidating rate assumptions",
            "Geopolitical shocks causing flight-to-safety correlations",
            "Liquidity gaps in off-hours FX trading",
        ],
        "rr_target": "1.5 to 2.5",
        "max_risk_pct": 1.0,
        "confidence_threshold": 0.65,
    },
    
    "super_secure_trend": {
        "asset_class": ["CRYPTO", "COMMODITY", "ETF"],
        "philosophy": "Low-volatility trend following in established uptrends. Skips all counter-trend and momentum-reversal setups. Only enters confirmed trends with volume confirmation.",
        "min_score": 0.60,
        "entry_criteria": [
            "Price above 50 and 200 SMA (confirmed uptrend)",
            "ADX(14) > 25 and +DI > -DI (trend strength + direction)",
            "Volume >= 1.5x 20-day average (volume confirmation)",
            "ATR(14) < 1.5x 50-day average (not volatility spike entry)",
            "No RSI divergence bearish (RSI not making lower highs while price makes higher highs)",
        ],
        "exit_criteria": [
            "Trailing stop at 3x ATR(14) from peak (wider for trend-following)",
            "Hard stop at -10%",
            "Exit when ADX drops below 20 (trend weakens)",
            "Exit on RSI bearish divergence",
        ],
        "risk_factors": [
            "Trend exhaustion — late entry after most of move is done",
            "Whipsaw in choppy/sideways markets",
            "Gap risk in crypto on weekends",
        ],
        "rr_target": "2.0 to 3.0",
        "max_risk_pct": 1.5,
        "confidence_threshold": 0.60,
    },
}

if __name__ == "__main__":
    import json
    print(json.dumps(SUPER_SECURE_PERSONAS, indent=2))
    print(f"\n{len(SUPER_SECURE_PERSONAS)} super secure personas defined")
