#!/usr/bin/env python3
"""
CONSENSUS ENGINE v2.0 - FIXED VERSION
Addresses all 3 major problems:
1. Insider scores too low → Aggressive scoring with cluster/timing bonuses
2. F&G stuck at 51 → Ticker-specific momentum + RSI components
3. V/G/M stuck at 50 → Price-based proxy calculations
"""

import logging
from datetime import datetime, timedelta
from database import db
from utils import safe_request
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConsensusEngineFixed:
    """
    Multi-factor consensus engine with dynamic weighting
    """
    
    def __init__(self):
        self.name = "consensus_beast_v2"
        
        # Base weights for each factor
        self.weights = {
            'whale': 0.18,
            'insider': 0.18,
            'analyst': 0.14,
            'crowd': 0.12,
            'fear_greed': 0.12,
            'value': 0.09,
            'growth': 0.09,
            'momentum': 0.08
        }
    
    # ========================================================================
    # PROBLEM 1 FIX: AGGRESSIVE INSIDER SCORING
    # ========================================================================
    
    def get_insider_score(self, ticker):
        """
        Get insider score with AGGRESSIVE scoring
        Target: CEO buying $1M+ should return 85-95
        """
        query = """
            SELECT 
                insider_name,
                title,
                shares,
                price_per_share,
                total_value,
                transaction_date,
                transaction_type
            FROM insider_transactions
            WHERE ticker = %s
            AND transaction_type = 'P'  -- Purchases only
            AND transaction_date >= CURDATE() - INTERVAL 30 DAY
            ORDER BY total_value DESC
        """
        
        try:
            transactions = db.fetchall(query, (ticker,))
        except:
            # Fallback to stock_picks table
            query2 = """
                SELECT metadata 
                FROM stock_picks 
                WHERE ticker = %s 
                AND algorithm_name = 'insider_conviction'
                AND pick_date >= CURDATE() - INTERVAL 30 DAY
                ORDER BY confidence_score DESC
                LIMIT 1
            """
            result = db.fetchone(query2, (ticker,))
            if result and result.get('confidence_score'):
                return result['confidence_score']
            transactions = []
        
        if not transactions:
            return 0
        
        # Calculate score for EACH transaction, return the BEST
        best_score = 0
        
        for t in transactions:
            score = 25  # Base for any purchase (increased from 0)
            
            # ===== TITLE BONUS (CRITICAL) =====
            title = (t.get('title') or '').lower()
            
            if any(x in title for x in ['ceo', 'chief executive', 'chief exec']):
                score += 40  # Was 25 → Now 40
            elif any(x in title for x in ['cfo', 'chief financial', 'chief finance']):
                score += 35  # Was 20 → Now 35
            elif any(x in title for x in ['coo', 'chief operating', 'chief operation']):
                score += 32
            elif any(x in title for x in ['president', 'pres']):
                score += 28  # Was 15 → Now 28
            elif any(x in title for x in ['director', 'chairman']):
                score += 22  # Was 10 → Now 22
            elif 'officer' in title:
                score += 18
            elif 'vp' in title or 'vice president' in title:
                score += 12
            else:
                score += 8
            
            # ===== AMOUNT BONUS (CRITICAL) =====
            amount = t.get('total_value') or 0
            
            if amount >= 10_000_000:      # $10M+
                score += 35
            elif amount >= 5_000_000:     # $5M+
                score += 30
            elif amount >= 2_000_000:     # $2M+
                score += 25
            elif amount >= 1_000_000:     # $1M+
                score += 20
            elif amount >= 500_000:       # $500K+
                score += 15
            elif amount >= 250_000:       # $250K+
                score += 12
            elif amount >= 100_000:       # $100K+
                score += 8
            elif amount >= 50_000:        # $50K+
                score += 5
            
            # ===== CLUSTER BONUS =====
            # Multiple insiders buying same stock within 7 days
            cluster_query = """
                SELECT COUNT(DISTINCT insider_name) as cluster_count
                FROM insider_transactions
                WHERE ticker = %s
                AND transaction_type = 'P'
                AND transaction_date >= %s - INTERVAL 7 DAY
                AND transaction_date <= %s + INTERVAL 7 DAY
            """
            try:
                cluster_result = db.fetchone(cluster_query, 
                    (ticker, t['transaction_date'], t['transaction_date']))
                cluster_count = cluster_result['cluster_count'] if cluster_result else 1
                
                if cluster_count >= 5:
                    score += 20
                elif cluster_count >= 3:
                    score += 15
                elif cluster_count == 2:
                    score += 8
            except:
                pass
            
            # ===== TIMING BONUS (Buying the dip) =====
            # Check if stock was down before purchase
            try:
                price_query = """
                    SELECT close_price 
                    FROM daily_prices 
                    WHERE ticker = %s 
                    AND trade_date <= %s
                    ORDER BY trade_date DESC 
                    LIMIT 6
                """
                prices = db.fetchall(price_query, (ticker, t['transaction_date']))
                if len(prices) >= 6:
                    old_price = prices[-1]['close_price']  # 5 days before
                    new_price = prices[0]['close_price']   # Day of purchase
                    price_change = (new_price - old_price) / old_price * 100
                    
                    if price_change < -15:      # Bought after 15%+ drop
                        score += 15
                    elif price_change < -10:    # Bought after 10%+ drop
                        score += 10
                    elif price_change < -5:     # Bought after 5%+ drop
                        score += 5
            except:
                pass
            
            # Cap at 100
            score = min(100, score)
            best_score = max(best_score, score)
            
            logger.debug(f"Insider score for {ticker}: {score} (title={title}, amount={amount:,})")
        
        return best_score
    
    # ========================================================================
    # PROBLEM 2 FIX: TICKER-SPECIFIC FEAR & GREED
    # ========================================================================
    
    def get_market_fear_greed(self):
        """Get market-wide fear/greed from VIX"""
        # Try multiple sources
        vix = None
        
        # Source 1: Your database
        queries = [
            "SELECT close_price as vix FROM daily_prices WHERE ticker = 'VIX' ORDER BY trade_date DESC LIMIT 1",
            "SELECT price as vix FROM market_data WHERE symbol = '^VIX' ORDER BY timestamp DESC LIMIT 1",
            "SELECT value as vix FROM indicators WHERE name = 'VIX' ORDER BY date DESC LIMIT 1"
        ]
        
        for query in queries:
            try:
                result = db.fetchone(query)
                if result and result.get('vix'):
                    vix = float(result['vix'])
                    break
            except:
                continue
        
        # Source 2: Yahoo Finance (free)
        if vix is None:
            try:
                url = "https://query1.finance.yahoo.com/v8/finance/chart/^VIX?interval=1d&range=1d"
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                data = r.json()
                vix = data['chart']['result'][0]['meta']['regularMarketPrice']
            except:
                vix = 20  # Default neutral
        
        # Convert VIX to fear/greed (0-100 scale)
        # VIX 12 = Extreme Greed (95)
        # VIX 20 = Neutral (50)
        # VIX 30+ = Extreme Fear (10)
        if vix <= 12:
            return 95
        elif vix <= 15:
            return 90 - ((vix - 12) / 3 * 15)  # 90-75
        elif vix <= 20:
            return 75 - ((vix - 15) / 5 * 25)  # 75-50
        elif vix <= 25:
            return 50 - ((vix - 20) / 5 * 20)  # 50-30
        elif vix <= 30:
            return 30 - ((vix - 25) / 5 * 15)  # 30-15
        else:
            return max(5, 15 - ((vix - 30) / 20 * 10))  # 15-5
    
    def get_ticker_fear_greed(self, ticker):
        """
        Get TICKER-SPECIFIC fear/greed (not just market-wide)
        Combines: Market VIX (60%) + Ticker momentum/volume/RSI (40%)
        """
        # Market component (60%)
        market_fg = self.get_market_fear_greed()
        
        # Ticker-specific component (40%)
        # Calculate from price action
        query = """
            SELECT 
                close_price,
                open_price,
                high_price,
                low_price,
                volume,
                trade_date,
                LAG(close_price, 5) OVER (ORDER BY trade_date) as price_5d_ago,
                LAG(close_price, 20) OVER (ORDER BY trade_date) as price_20d_ago,
                AVG(close_price) OVER (ORDER BY trade_date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) as sma_20,
                AVG(close_price) OVER (ORDER BY trade_date ROWS BETWEEN 50 PRECEDING AND CURRENT ROW) as sma_50,
                AVG(volume) OVER (ORDER BY trade_date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) as avg_volume_20d,
                MAX(high_price) OVER (ORDER BY trade_date ROWS BETWEEN 252 PRECEDING AND CURRENT ROW) as high_52w,
                MIN(low_price) OVER (ORDER BY trade_date ROWS BETWEEN 252 PRECEDING AND CURRENT ROW) as low_52w
            FROM daily_prices
            WHERE ticker = %s
            ORDER BY trade_date DESC
            LIMIT 1
        """
        
        try:
            result = db.fetchone(query, (ticker,))
        except:
            result = None
        
        if not result:
            return market_fg  # Fallback to market-only
        
        # Calculate ticker greed score (0-100)
        ticker_greed = 50  # Neutral base
        
        # 1. Momentum factor (+/- 25 points)
        price_5d_ago = result.get('price_5d_ago')
        close = result['close_price']
        
        if price_5d_ago and price_5d_ago > 0:
            momentum_5d = (close - price_5d_ago) / price_5d_ago * 100
            
            if momentum_5d > 20:
                ticker_greed += 25
            elif momentum_5d > 15:
                ticker_greed += 20
            elif momentum_5d > 10:
                ticker_greed += 15
            elif momentum_5d > 5:
                ticker_greed += 8
            elif momentum_5d > 0:
                ticker_greed += 3
            elif momentum_5d < -20:
                ticker_greed -= 25
            elif momentum_5d < -15:
                ticker_greed -= 20
            elif momentum_5d < -10:
                ticker_greed -= 15
            elif momentum_5d < -5:
                ticker_greed -= 8
            else:
                ticker_greed -= 3
        
        # 2. Volume spike factor (+/- 15 points)
        volume = result.get('volume')
        avg_volume = result.get('avg_volume_20d')
        
        if volume and avg_volume and avg_volume > 0:
            vol_ratio = volume / avg_volume
            
            if vol_ratio > 5:      # 5x volume
                ticker_greed += 15
            elif vol_ratio > 3:    # 3x volume
                ticker_greed += 12
            elif vol_ratio > 2:    # 2x volume
                ticker_greed += 8
            elif vol_ratio > 1.5:
                ticker_greed += 4
        
        # 3. RSI proxy using price position (+/- 15 points)
        high_52w = result.get('high_52w')
        low_52w = result.get('low_52w')
        
        if high_52w and low_52w and high_52w > low_52w:
            range_position = (close - low_52w) / (high_52w - low_52w) * 100
            
            if range_position > 95:      # Near 52-week high
                ticker_greed += 15
            elif range_position > 90:
                ticker_greed += 12
            elif range_position > 80:
                ticker_greed += 8
            elif range_position > 70:
                ticker_greed += 4
            elif range_position < 5:     # Near 52-week low
                ticker_greed -= 15
            elif range_position < 10:
                ticker_greed -= 12
            elif range_position < 20:
                ticker_greed -= 8
            elif range_position < 30:
                ticker_greed -= 4
        
        # 4. Golden/Death cross (+/- 10 points)
        sma_20 = result.get('sma_20')
        sma_50 = result.get('sma_50')
        
        if sma_20 and sma_50:
            if sma_20 > sma_50 * 1.02:   # Golden cross
                ticker_greed += 10
            elif sma_20 < sma_50 * 0.98:  # Death cross
                ticker_greed -= 10
        
        # Cap ticker component
        ticker_greed = max(0, min(100, ticker_greed))
        
        # Blend: 60% market, 40% ticker-specific
        final_score = (market_fg * 0.6) + (ticker_greed * 0.4)
        
        logger.debug(f"F&G for {ticker}: Market={market_fg:.0f}, Ticker={ticker_greed:.0f}, Final={final_score:.0f}")
        
        return round(final_score)
    
    # ========================================================================
    # PROBLEM 3 FIX: REAL VALUE/GROWTH/MOMENTUM SCORES
    # ========================================================================
    
    def get_value_score(self, ticker):
        """
        Value score using price-based proxies (NO fundamentals needed)
        """
        query = """
            SELECT 
                close_price,
                AVG(close_price) OVER (ORDER BY trade_date ROWS BETWEEN 200 PRECEDING AND CURRENT ROW) as sma_200,
                MIN(low_price) OVER (ORDER BY trade_date ROWS BETWEEN 252 PRECEDING AND CURRENT ROW) as low_52w,
                MAX(high_price) OVER (ORDER BY trade_date ROWS BETWEEN 252 PRECEDING AND CURRENT ROW) as high_52w,
                AVG(close_price) OVER (ORDER BY trade_date ROWS BETWEEN 50 PRECEDING AND CURRENT ROW) as sma_50
            FROM daily_prices
            WHERE ticker = %s
            ORDER BY trade_date DESC
            LIMIT 1
        """
        
        try:
            result = db.fetchone(query, (ticker,))
        except:
            result = None
        
        if not result:
            return 50
        
        score = 50  # Neutral base
        close = result['close_price']
        sma_200 = result.get('sma_200')
        low_52w = result.get('low_52w')
        high_52w = result.get('high_52w')
        sma_50 = result.get('sma_50')
        
        # 1. Distance from 200-day MA (mean reversion = value)
        if sma_200 and sma_200 > 0:
            dist_from_ma = (close - sma_200) / sma_200 * 100
            
            if dist_from_ma < -20:       # 20%+ below 200MA
                score += 25
            elif dist_from_ma < -15:
                score += 22
            elif dist_from_ma < -10:
                score += 18
            elif dist_from_ma < -5:
                score += 12
            elif dist_from_ma < 0:
                score += 6
            elif dist_from_ma > 20:      # Extended = not value
                score -= 15
            elif dist_from_ma > 10:
                score -= 8
        
        # 2. Position in 52-week range
        if high_52w and low_52w and high_52w > low_52w:
            range_pos = (close - low_52w) / (high_52w - low_52w) * 100
            
            if range_pos < 20:           # Bottom 20% = value
                score += 20
            elif range_pos < 30:
                score += 15
            elif range_pos < 40:
                score += 10
            elif range_pos < 50:
                score += 5
            elif range_pos > 90:         # Top 10% = not value
                score -= 15
            elif range_pos > 80:
                score -= 10
        
        # 3. Short-term vs long-term MA (value stocks often have this pattern)
        if sma_50 and sma_200 and sma_200 > 0:
            if sma_50 < sma_200 * 0.95:  # Short-term below long-term
                score += 10
            elif sma_50 > sma_200 * 1.05:
                score -= 5
        
        return max(0, min(100, score))
    
    def get_growth_score(self, ticker):
        """
        Growth score using price momentum (proxy for earnings growth)
        """
        query = """
            SELECT 
                close_price,
                LAG(close_price, 21) OVER (ORDER BY trade_date) as price_1m_ago,
                LAG(close_price, 63) OVER (ORDER BY trade_date) as price_3m_ago,
                LAG(close_price, 126) OVER (ORDER BY trade_date) as price_6m_ago,
                LAG(close_price, 252) OVER (ORDER BY trade_date) as price_1y_ago,
                AVG(close_price) OVER (ORDER BY trade_date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) as sma_20,
                AVG(close_price) OVER (ORDER BY trade_date ROWS BETWEEN 50 PRECEDING AND CURRENT ROW) as sma_50
            FROM daily_prices
            WHERE ticker = %s
            ORDER BY trade_date DESC
            LIMIT 1
        """
        
        try:
            result = db.fetchone(query, (ticker,))
        except:
            result = None
        
        if not result:
            return 50
        
        score = 50
        close = result['close_price']
        
        # Calculate returns
        returns = {}
        for period, key in [('1m', 'price_1m_ago'), ('3m', 'price_3m_ago'), 
                           ('6m', 'price_6m_ago'), ('1y', 'price_1y_ago')]:
            old_price = result.get(key)
            if old_price and old_price > 0:
                returns[period] = (close - old_price) / old_price * 100
        
        # Score based on returns
        ret_1m = returns.get('1m', 0)
        ret_3m = returns.get('3m', 0)
        ret_6m = returns.get('6m', 0)
        
        # 1-month momentum
        if ret_1m > 25:
            score += 15
        elif ret_1m > 15:
            score += 12
        elif ret_1m > 10:
            score += 8
        elif ret_1m > 5:
            score += 4
        elif ret_1m < -15:
            score -= 12
        elif ret_1m < -10:
            score -= 8
        
        # 3-month momentum (higher weight)
        if ret_3m > 50:
            score += 25
        elif ret_3m > 35:
            score += 20
        elif ret_3m > 25:
            score += 15
        elif ret_3m > 15:
            score += 10
        elif ret_3m > 5:
            score += 5
        elif ret_3m < -25:
            score -= 15
        elif ret_3m < -15:
            score -= 10
        
        # 6-month momentum
        if ret_6m > 80:
            score += 20
        elif ret_6m > 50:
            score += 15
        elif ret_6m > 30:
            score += 10
        elif ret_6m < -30:
            score -= 10
        
        # Consistency bonus: all timeframes positive
        if ret_1m > 0 and ret_3m > 0 and ret_6m > 0:
            score += 10
        
        # Acceleration bonus: 1m > 3m (accelerating growth)
        if ret_1m > ret_3m / 3 * 1.5:  # Monthly rate accelerating
            score += 8
        
        return max(0, min(100, score))
    
    def get_momentum_score(self, ticker):
        """
        Technical momentum score
        """
        query = """
            SELECT 
                close_price,
                open_price,
                high_price,
                low_price,
                volume,
                AVG(close_price) OVER (ORDER BY trade_date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) as sma_10,
                AVG(close_price) OVER (ORDER BY trade_date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) as sma_20,
                AVG(close_price) OVER (ORDER BY trade_date ROWS BETWEEN 50 PRECEDING AND CURRENT ROW) as sma_50,
                LAG(close_price, 20) OVER (ORDER BY trade_date) as price_20d_ago,
                MAX(high_price) OVER (ORDER BY trade_date ROWS BETWEEN 252 PRECEDING AND CURRENT ROW) as high_52w,
                AVG(volume) OVER (ORDER BY trade_date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) as avg_vol_20d
            FROM daily_prices
            WHERE ticker = %s
            ORDER BY trade_date DESC
            LIMIT 1
        """
        
        try:
            result = db.fetchone(query, (ticker,))
        except:
            result = None
        
        if not result:
            return 50
        
        score = 50
        close = result['close_price']
        
        # 1. Moving average alignment
        sma_10 = result.get('sma_10')
        sma_20 = result.get('sma_20')
        sma_50 = result.get('sma_50')
        
        if sma_10 and sma_20 and sma_50:
            # Perfect alignment: 10 > 20 > 50
            if sma_10 > sma_20 > sma_50:
                score += 20
            elif sma_10 > sma_20 and sma_20 > sma_50 * 0.98:
                score += 15
            elif sma_20 > sma_50:
                score += 10
            elif sma_10 < sma_20 < sma_50:
                score -= 15
            elif sma_20 < sma_50:
                score -= 10
        
        # 2. 52-week high proximity
        high_52w = result.get('high_52w')
        if high_52w and high_52w > 0:
            proximity = close / high_52w * 100
            
            if proximity > 98:       # Within 2% of 52w high
                score += 15
            elif proximity > 95:
                score += 12
            elif proximity > 90:
                score += 8
            elif proximity < 70:     # Far from highs
                score -= 10
        
        # 3. Volume confirmation
        volume = result.get('volume')
        avg_vol = result.get('avg_vol_20d')
        
        if volume and avg_vol and avg_vol > 0:
            vol_ratio = volume / avg_vol
            
            if vol_ratio > 3:
                score += 12
            elif vol_ratio > 2:
                score += 8
            elif vol_ratio > 1.5:
                score += 4
        
        # 4. Recent return
        price_20d_ago = result.get('price_20d_ago')
        if price_20d_ago and price_20d_ago > 0:
            ret_20d = (close - price_20d_ago) / price_20d_ago * 100
            
            if ret_20d > 20:
                score += 15
            elif ret_20d > 15:
                score += 12
            elif ret_20d > 10:
                score += 8
            elif ret_20d > 5:
                score += 4
            elif ret_20d < -10:
                score -= 10
        
        # 5. Daily candle strength
        open_p = result.get('open_price')
        high_p = result.get('high_price')
        low_p = result.get('low_price')
        
        if all([open_p, high_p, low_p, open_p > 0, high_p > low_p]):
            # Bullish candle: close near high
            candle_range = high_p - low_p
            if candle_range > 0:
                close_position = (close - low_p) / candle_range
                
                if close > open_p and close_position > 0.8:
                    score += 8
                elif close > open_p and close_position > 0.6:
                    score += 4
                elif close < open_p and close_position < 0.2:
                    score -= 6
        
        return max(0, min(100, score))
    
    # ========================================================================
    # OTHER FACTORS (Whale, Analyst, Crowd, Regime)
    # ========================================================================
    
    def get_whale_score(self, ticker):
        """Get smart money (13F) score"""
        query = """
            SELECT confidence_score, metadata
            FROM stock_picks
            WHERE ticker = %s
            AND algorithm_name = 'smart_money_13f'
            AND pick_date >= CURDATE() - INTERVAL 45 DAY
            ORDER BY confidence_score DESC
            LIMIT 1
        """
        
        try:
            result = db.fetchone(query, (ticker,))
            if result:
                return result['confidence_score'] or 0
        except:
            pass
        
        return 0
    
    def get_analyst_score(self, ticker):
        """Get analyst consensus score"""
        query = """
            SELECT confidence_score
            FROM stock_picks
            WHERE ticker = %s
            AND algorithm_name = 'analyst_consensus'
            AND pick_date >= CURDATE() - INTERVAL 30 DAY
            ORDER BY confidence_score DESC
            LIMIT 1
        """
        
        try:
            result = db.fetchone(query, (ticker,))
            if result:
                return result['confidence_score'] or 0
        except:
            pass
        
        return 50  # Default neutral
    
    def get_crowd_score(self, ticker):
        """Get WSB/social sentiment score"""
        query = """
            SELECT confidence_score
            FROM stock_picks
            WHERE ticker = %s
            AND algorithm_name IN ('wsb_sentiment', 'social_sentiment')
            AND pick_date >= CURDATE() - INTERVAL 7 DAY
            ORDER BY confidence_score DESC
            LIMIT 1
        """
        
        try:
            result = db.fetchone(query, (ticker,))
            if result:
                return result['confidence_score'] or 0
        except:
            pass
        
        return 50  # Default neutral
    
    def get_regime_score(self):
        """Get market regime score (bullish/bearish/neutral)"""
        # Use SPY to determine regime
        query = """
            SELECT 
                close_price,
                AVG(close_price) OVER (ORDER BY trade_date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) as sma_20,
                AVG(close_price) OVER (ORDER BY trade_date ROWS BETWEEN 50 PRECEDING AND CURRENT ROW) as sma_50
            FROM daily_prices
            WHERE ticker = 'SPY'
            ORDER BY trade_date DESC
            LIMIT 1
        """
        
        try:
            result = db.fetchone(query)
            if result and result['sma_20'] and result['sma_50']:
                sma_20 = result['sma_20']
                sma_50 = result['sma_50']
                
                if sma_20 > sma_50 * 1.02:
                    return 75  # Bullish
                elif sma_20 < sma_50 * 0.98:
                    return 35  # Bearish
                else:
                    return 55  # Neutral
        except:
            pass
        
        return 55  # Default neutral
    
    # ========================================================================
    # MAIN CONSENSUS CALCULATION
    # ========================================================================
    
    def calculate_conviction(self, ticker):
        """
        Calculate final conviction score for a ticker
        """
        logger.info(f"Calculating conviction for {ticker}...")
        
        # Get all factor scores
        scores = {
            'whale': self.get_whale_score(ticker),
            'insider': self.get_insider_score(ticker),
            'analyst': self.get_analyst_score(ticker),
            'crowd': self.get_crowd_score(ticker),
            'fear_greed': self.get_ticker_fear_greed(ticker),
            'value': self.get_value_score(ticker),
            'growth': self.get_growth_score(ticker),
            'momentum': self.get_momentum_score(ticker),
            'regime': self.get_regime_score()
        }
        
        # Count non-zero signals (for quality check)
        non_zero = sum(1 for s in scores.values() if s > 0)
        
        # Calculate weighted average
        weighted_sum = 0
        total_weight = 0
        
        for factor, score in scores.items():
            if factor == 'regime':
                continue  # Regime is for adjustment, not direct weighting
            
            weight = self.weights.get(factor, 0.1)
            weighted_sum += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 50, scores  # Neutral if no data
        
        raw_conviction = weighted_sum / total_weight
        
        # Apply regime adjustment
        regime = scores['regime']
        if regime > 65:  # Bull market
            raw_conviction *= 1.05  # Boost conviction
        elif regime < 45:  # Bear market
            raw_conviction *= 0.95  # Reduce conviction
        
        # Quality penalty: if < 4 factors have data, reduce confidence
        if non_zero < 4:
            raw_conviction *= 0.9
        
        final_conviction = round(max(0, min(100, raw_conviction)))
        
        logger.info(f"{ticker} scores: {scores}")
        logger.info(f"{ticker} conviction: {final_conviction}")
        
        return final_conviction, scores
    
    def get_label(self, conviction):
        """Get label based on conviction score"""
        if conviction >= 75:
            return 'STRONG BUY'
        elif conviction >= 60:
            return 'BUY'
        elif conviction >= 45:
            return 'NEUTRAL'
        elif conviction >= 30:
            return 'HOLD'
        else:
            return 'SELL'
    
    def generate_top_picks(self, tickers=None, top_n=20):
        """Generate top consensus picks"""
        
        if tickers is None:
            # Get tickers from recent picks
            query = """
                SELECT DISTINCT ticker 
                FROM stock_picks 
                WHERE pick_date >= CURDATE() - INTERVAL 14 DAY
                AND algorithm_name IN ('smart_money_13f', 'analyst_consensus', 'wsb_sentiment')
                LIMIT 100
            """
            try:
                results = db.fetchall(query)
                tickers = [r['ticker'] for r in results]
            except:
                tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AMD']
        
        logger.info(f"Generating consensus for {len(tickers)} tickers...")
        
        picks = []
        for ticker in tickers:
            conviction, scores = self.calculate_conviction(ticker)
            
            picks.append({
                'ticker': ticker,
                'conviction': conviction,
                'label': self.get_label(conviction),
                'scores': scores,
                'whale': scores['whale'],
                'insider': scores['insider'],
                'analyst': scores['analyst'],
                'crowd': scores['crowd'],
                'fear_greed': scores['fear_greed'],
                'value': scores['value'],
                'growth': scores['growth'],
                'momentum': scores['momentum'],
                'regime': scores['regime']
            })
        
        # Sort by conviction
        picks.sort(key=lambda x: x['conviction'], reverse=True)
        
        return picks[:top_n]
    
    def store_picks(self, picks):
        """Store consensus picks in database"""
        if not picks:
            return
        
        query = """
            INSERT INTO stock_picks 
            (ticker, algorithm_name, pick_date, confidence_score, metadata)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            confidence_score = VALUES(confidence_score),
            metadata = VALUES(metadata)
        """
        
        values = []
        now = datetime.now()
        
        for pick in picks:
            metadata = (
                f"label:{pick['label']},"
                f"whale:{pick['whale']},"
                f"insider:{pick['insider']},"
                f"analyst:{pick['analyst']},"
                f"crowd:{pick['crowd']},"
                f"fg:{pick['fear_greed']},"
                f"v:{pick['value']},"
                f"g:{pick['growth']},"
                f"m:{pick['momentum']},"
                f"regime:{pick['regime']}"
            )
            
            values.append((
                pick['ticker'],
                self.name,
                now,
                pick['conviction'],
                metadata
            ))
        
        try:
            db.insert_many(query, values)
            logger.info(f"Stored {len(values)} consensus picks")
        except Exception as e:
            logger.error(f"Error storing picks: {e}")
    
    def generate_report(self, picks):
        """Generate text report"""
        lines = []
        lines.append("=" * 90)
        lines.append("🎯 CONSENSUS BEAST v2.0 - TOP PICKS")
        lines.append("=" * 90)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        
        # Header
        lines.append(f"{'#':<4}{'Ticker':<8}{'Conv':<6}{'Label':<12}{'WH':<5}{'IN':<5}{'AN':<5}{'CR':<5}{'F&G':<5}{'V':<5}{'G':<5}{'M':<5}{'REG':<5}")
        lines.append("-" * 90)
        
        for i, pick in enumerate(picks[:15], 1):
            lines.append(
                f"{i:<4}"
                f"{pick['ticker']:<8}"
                f"{pick['conviction']:<6}"
                f"{pick['label']:<12}"
                f"{pick['whale']:<5}"
                f"{pick['insider']:<5}"
                f"{pick['analyst']:<5}"
                f"{pick['crowd']:<5}"
                f"{pick['fear_greed']:<5}"
                f"{pick['value']:<5}"
                f"{pick['growth']:<5}"
                f"{pick['momentum']:<5}"
                f"{pick['regime']:<5}"
            )
        
        lines.append("=" * 90)
        lines.append("WH=Whale, IN=Insider, AN=Analyst, CR=Crowd, F&G=Fear/Greed")
        lines.append("V=Value, G=Growth, M=Momentum, REG=Market Regime")
        lines.append("=" * 90)
        
        return '\n'.join(lines)


# ========================================================================
# MAIN EXECUTION
# ========================================================================

if __name__ == '__main__':
    engine = ConsensusEngineFixed()
    
    # Test tickers
    test_tickers = ['NVDA', 'AAPL', 'META', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'AMD']
    
    # Generate picks
    picks = engine.generate_top_picks(test_tickers)
    
    # Print report
    report = engine.generate_report(picks)
    print(report)
    
    # Store in database
    engine.store_picks(picks)
    
    # Save report
    with open('consensus_report_v2.txt', 'w') as f:
        f.write(report)
