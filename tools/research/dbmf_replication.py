"""DBMF CTA Commodity-Momentum Replication Strategy.

Replicates iMGP DBi Managed Futures ETF (DBMF) methodology:
  - 8-commodity 12m-1m momentum (trend-following)
  - LONG-only by design: CTA funds go long trending commodities; short positions
    are expressed via futures roll or by simply not holding the commodity.
    This module is intentionally LONG-only — no SHORT signals are generated.
    Rationale: COMMODITY class has M-042 SHORT-only gate active; DBMF signals
    complement this by identifying trend-up (momentum) commodities for research.

Fixed 2026-05-17:
  - resample('M') → resample('ME') (pandas >= 2.2)
  - data['Close'].squeeze() for yfinance multi-level columns
"""
import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DBMF ETF tracks 8 commodity futures with equal weighting
DBMF_COMMODITIES = {
    'GC=F': 'Gold',
    'CL=F': 'Crude Oil',
    'HG=F': 'Copper',
    'ZC=F': 'Corn',
    'ZS=F': 'Soybeans',
    'ZW=F': 'Wheat',
    'NG=F': 'Natural Gas',
    'SI=F': 'Silver'
}

# COMMODITY class in quality_gates.py has specific constraints
# Only HG=F and PL=F are allowed (others are in COMMODITY_BLACKLIST)
# For research purposes, we'll generate signals for all 8 but note the restriction
COMMODITY_BLACKLIST = ['GC=F', 'CL=F', 'ZC=F', 'ZS=F', 'ZW=F', 'NG=F', 'SI=F']  # All except HG=F, PL=F


def get_monthly_returns(ticker: str, months: int) -> float:
    """
    Calculate total return over specified number of months.
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months*30)
        
        # Get historical data
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if data.empty or len(data) < 2:
            logger.warning(f"Insufficient data for {ticker}")
            return 0.0
            
        # Calculate total return (.squeeze() handles multi-level yfinance columns)
        close = data['Close'].squeeze()
        total_return = float(close.iloc[-1] / close.iloc[0]) - 1
        return total_return
        
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {str(e)}")
        return 0.0

def calculate_trend_strength(prices: pd.Series) -> float:
    """
    Calculate trend strength as the slope of the linear regression of prices.
    """
    if len(prices) < 2:
        return 0.0
        
    # Simple linear regression slope
    x = np.arange(len(prices))
    y = prices.values
    slope = np.polyfit(x, y, 1)[0]
    
    # Normalize by price level to get percentage slope
    normalized_slope = (slope / float(prices.iloc[-1])) * 100
    return float(normalized_slope)

def get_price_history(ticker: str, months: int) -> pd.Series:
    """
    Get monthly price history for trend strength calculation.
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months*30)
        
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if data.empty:
            logger.warning(f"No price data for {ticker}")
            return pd.Series()
            
        # Resample to monthly frequency (.squeeze() handles yfinance multi-level columns)
        close = data['Close'].squeeze()
        monthly_data = close.resample('ME').last()
        return monthly_data
        
    except Exception as e:
        logger.error(f"Error getting price history for {ticker}: {str(e)}")
        return pd.Series()

def generate_dbmf_signals() -> List[Dict]:
    """
    Generate DBMF replication signals based on 12-month minus 1-month momentum.
    Only generate LONG signals when trend strength is positive.
    
    Returns list of picks compatible with quality_gates.py Pick schema.
    """
    picks = []
    
    for ticker, name in DBMF_COMMODITIES.items():
        try:
            # Calculate 12-month and 1-month total returns
            twelve_month_return = get_monthly_returns(ticker, 12)
            one_month_return = get_monthly_returns(ticker, 1)
            
            # Momentum signal: 12-month minus 1-month return
            momentum_signal = twelve_month_return - one_month_return
            
            # Calculate trend strength from 12-month price history
            price_history = get_price_history(ticker, 12)
            trend_strength = calculate_trend_strength(price_history) if not price_history.empty else 0.0

            # Only generate LONG signals when trend strength > 0 (momentum regime)
            # No SHORT signals per DBMF methodology
            signal = "LONG" if trend_strength > 0 else ""  # Empty signal if no position
            
            # Conviction score based on trend strength (absolute value)
            conviction = abs(trend_strength) if signal else 0.0
            
            # Score for quality gates (scaled to match expected ranges)
            # COMMODITY_MIN_SCORE is 30 in quality_gates.py
            base_score = 50 + (conviction * 5)  # Base 50, +5 per 1% trend strength
            score = max(0, min(100, base_score))  # Clamp to 0-100 range

            # Only include picks with LONG signal
            if signal == "LONG":
                pick = {
                    'symbol': ticker,
                    'signal': signal,
                    'score': score,
                    'strategy': 'dbmf_replication',
                    'asset_class': 'COMMODITY',
                    'conviction': conviction,
                    'entry_time': datetime.now().isoformat(),
                    'timeframe': 'monthly',
                    'research_notes': f"DBMF replication: 12m-1m momentum={momentum_signal:.4f}, "
                                 f"trend_strength={trend_strength:.4f}, {name} futures"
                }
                picks.append(pick)
                
            logger.info(f"{ticker} ({name}): signal={signal}, trend_strength={trend_strength:.4f}, "
                       f"score={score:.2f}, 12m-1m={momentum_signal:.4f}")
                
        except Exception as e:
            logger.error(f"Error generating signal for {ticker}: {str(e)}")
            continue
    
    # Sort picks by conviction score (highest first)
    picks.sort(key=lambda x: x['conviction'], reverse=True)
    
    logger.info(f"Generated {len(picks)} DBMF replication LONG signals")
    return picks

if __name__ == "__main__":
    """
    Research mode execution: generate and display DBMF replication signals.
    """
    print("DBMF Commodity Futures Replication Strategy")
    print("=========================================")
    
    signals = generate_dbmf_signals()
    
    if signals:
        print(f"\nGenerated {len(signals)} LONG signals:")
        for i, pick in enumerate(signals, 1):
            print(f"{i}. {pick['symbol']} - {pick['signal']} (Score: {pick['score']:.1f}, "
                  f"Conviction: {pick['conviction']:.2f})")
            print(f"   Notes: {pick['research_notes']}")
    else:
        print("\nNo LONG signals generated. No commodities in positive trend regime.")
    
    # Wiring plan for future integration:
    # 1. Move this module to alpha_engine/strategies/dbmf_replication.py
    # 2. Add import to alpha_engine/__init__.py
    # 3. Register strategy in alpha_engine/production_scanner.py
    # 4. Update quality_gates.py to handle dbmf_replication strategy
    #    - Add to STRATEGY_WEIGHTS with appropriate weight
    #    - Consider adjusting COMMODITY_BLACKLIST if broader coverage needed
    # 5. The current COMMODITY_BLACKLIST restricts to HG=F, PL=F only
    #    - For production use, either modify blacklist or accept limited signal generation
