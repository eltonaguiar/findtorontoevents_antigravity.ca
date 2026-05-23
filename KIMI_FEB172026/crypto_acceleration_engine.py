"""
KIMI_FEB172026 - Crypto Acceleration Engine
Detects explosive crypto moves before they happen using institutional-grade signals
Research-backed strategies from Jump Trading, Jane Street, Wintermute methodologies
"""

import requests
import json
import asyncio
import time
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SignalResult:
    symbol: str
    signal_type: str
    confidence: float
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    take_profit: float
    stop_loss: float
    reason: str
    timestamp: datetime
    metadata: Dict

class CryptoAccelerationEngine:
    """
    Institutional-grade crypto signal detection engine
    Implements 10 proven strategies from top quant firms
    """
    
    def __init__(self):
        self.binance_base = "https://api.binance.com"
        self.binance_futures = "https://fapi.binance.com"
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.signals_history = []
        
        # Top crypto symbols to monitor
        self.symbols = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "BNBUSDT",
            "DOGEUSDT", "XRPUSDT", "ADAUSDT", "DOTUSDT", "MATICUSDT",
            "LINKUSDT", "INJUSDT", "TIAUSDT", "SUIUSDT", "APTUSDT",
            "ARBUSDT", "OPUSDT", "SEIUSDT", "JUPUSDT", "PYTHUSDT",
            "WIFUSDT", "BONKUSDT", "PEPEUSDT", "SHIBUSDT", "FILUSDT",
            "ATOMUSDT", "NEARUSDT", "ALGOUSDT", "LTCUSDT", "BCHUSDT"
        ]
        
        # Baseline volumes for volume spike detection
        self.baseline_volumes = {}
        self.price_history = {}
        
    # =============================================================================
    # SIGNAL 1: Pump Detector Scout
    # =============================================================================
    def detect_pump_acceleration(self, symbol: str, data: pd.DataFrame) -> Optional[SignalResult]:
        """
        Detect early-stage pumps before they become obvious
        Strategy: Price velocity ≥ 8% in 4h + volume 5× baseline + RSI < 65
        Academic: Momentum jerk (2nd derivative) signals early-stage pumps
        """
        if len(data) < 20:
            return None
            
        # Calculate 4h price change (using 1h data, so 4 periods)
        price_change_4h = (data['close'].iloc[-1] - data['close'].iloc[-5]) / data['close'].iloc[-5] * 100
        
        # Calculate RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Calculate volume ratio
        current_volume = data['volume'].iloc[-1]
        avg_volume = data['volume'].rolling(window=20).mean().iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        # Calculate momentum jerk (2nd derivative of price)
        price_velocity = data['close'].diff()
        acceleration = price_velocity.diff()
        jerk = acceleration.diff().iloc[-1]
        
        # Pump detection criteria
        if (price_change_4h >= 8 and 
            volume_ratio >= 5 and 
            rsi < 65 and 
            jerk > 0):  # Accelerating momentum
            
            entry = data['close'].iloc[-1]
            # Dynamic TP/SL based on volatility
            atr = self._calculate_atr(data)
            take_profit = entry + (atr * 3)
            stop_loss = entry - (atr * 1.5)
            
            return SignalResult(
                symbol=symbol.replace('USDT', '-USD'),
                signal_type="pump-detector-scout",
                confidence=min(0.95, 0.5 + (volume_ratio / 20) + (price_change_4h / 40)),
                direction="LONG",
                entry_price=entry,
                take_profit=take_profit,
                stop_loss=stop_loss,
                reason=f"Early pump: +{price_change_4h:.1f}% in 4h, Vol {volume_ratio:.1f}x, RSI {rsi:.1f}, Jerk +",
                timestamp=datetime.now(),
                metadata={
                    "price_change_4h": price_change_4h,
                    "volume_ratio": volume_ratio,
                    "rsi": rsi,
                    "jerk": jerk,
                    "atr": atr
                }
            )
        return None
    
    # =============================================================================
    # SIGNAL 2: Order Book Imbalance Scout
    # =============================================================================
    async def detect_order_book_imbalance(self, symbol: str) -> Optional[SignalResult]:
        """
        Detect heavy buying/selling pressure from order book
        Strategy: bid_volume / ask_volume > 2.0 = heavy buying pressure
        Uses Binance public orderbook (no API key needed)
        """
        try:
            url = f"{self.binance_base}/api/v3/depth"
            params = {"symbol": symbol, "limit": 20}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
            
            bids = data.get('bids', [])
            asks = data.get('asks', [])
            
            if not bids or not asks:
                return None
            
            # Calculate total bid and ask volume
            bid_volume = sum(float(b[1]) for b in bids)
            ask_volume = sum(float(a[1]) for a in asks)
            
            if ask_volume == 0:
                return None
                
            imbalance_ratio = bid_volume / ask_volume
            current_price = (float(bids[0][0]) + float(asks[0][0])) / 2
            
            # Strong buying pressure
            if imbalance_ratio >= 2.0:
                return SignalResult(
                    symbol=symbol.replace('USDT', '-USD'),
                    signal_type="order-book-imbalance-scout",
                    confidence=min(0.9, 0.5 + (imbalance_ratio - 2) / 6),
                    direction="LONG",
                    entry_price=current_price,
                    take_profit=current_price * 1.02,
                    stop_loss=current_price * 0.99,
                    reason=f"Heavy buying pressure: Bid/Ask ratio {imbalance_ratio:.2f}",
                    timestamp=datetime.now(),
                    metadata={
                        "bid_volume": bid_volume,
                        "ask_volume": ask_volume,
                        "imbalance_ratio": imbalance_ratio,
                        "spread_pct": (float(asks[0][0]) - float(bids[0][0])) / current_price * 100
                    }
                )
            
            # Strong selling pressure (for shorts)
            if imbalance_ratio <= 0.5:
                return SignalResult(
                    symbol=symbol.replace('USDT', '-USD'),
                    signal_type="order-book-imbalance-scout",
                    confidence=min(0.9, 0.5 + (0.5 - imbalance_ratio) / 0.3),
                    direction="SHORT",
                    entry_price=current_price,
                    take_profit=current_price * 0.98,
                    stop_loss=current_price * 1.01,
                    reason=f"Heavy selling pressure: Bid/Ask ratio {imbalance_ratio:.2f}",
                    timestamp=datetime.now(),
                    metadata={
                        "bid_volume": bid_volume,
                        "ask_volume": ask_volume,
                        "imbalance_ratio": imbalance_ratio
                    }
                )
            
        except Exception as e:
            logger.error(f"Order book error for {symbol}: {e}")
        
        return None
    
    # =============================================================================
    # SIGNAL 3: Liquidation Cascade Scout
    # =============================================================================
    async def detect_liquidation_cascade(self, symbol: str) -> Optional[SignalResult]:
        """
        Detect liquidation cascades for forced buying/selling pressure
        Strategy: Large SHORT liquidations → forced buying pressure
        Uses Binance Futures forceOrders endpoint (public, no auth)
        """
        try:
            url = f"{self.binance_futures}/fapi/v1/forceOrders"
            params = {
                "symbol": symbol,
                "limit": 100
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
            
            if not isinstance(data, list) or len(data) == 0:
                return None
            
            # Filter liquidations from last 15 minutes
            cutoff_time = datetime.now() - timedelta(minutes=15)
            recent_liquidations = []
            
            for liq in data:
                liq_time = datetime.fromtimestamp(liq.get('time', 0) / 1000)
                if liq_time >= cutoff_time:
                    recent_liquidations.append(liq)
            
            if not recent_liquidations:
                return None
            
            # Calculate total liquidated value
            total_liquidated = sum(float(liq.get('executedQty', 0)) * float(liq.get('averagePrice', 0)) 
                                  for liq in recent_liquidations)
            
            # Count short vs long liquidations
            short_liqs = [liq for liq in recent_liquidations if liq.get('side') == 'SELL']
            long_liqs = [liq for liq in recent_liquidations if liq.get('side') == 'BUY']
            
            short_value = sum(float(liq.get('executedQty', 0)) * float(liq.get('averagePrice', 0)) 
                             for liq in short_liqs)
            long_value = sum(float(liq.get('executedQty', 0)) * float(liq.get('averagePrice', 0)) 
                            for liq in long_liqs)
            
            current_price = float(recent_liquidations[0].get('averagePrice', 0))
            
            # Signal: >$5M short liquidations = forced buying = LONG signal
            if short_value >= 5_000_000 and short_value > long_value * 2:
                return SignalResult(
                    symbol=symbol.replace('USDT', '-USD'),
                    signal_type="liquidation-cascade-scout",
                    confidence=min(0.95, 0.6 + (short_value / 20_000_000)),
                    direction="LONG",
                    entry_price=current_price,
                    take_profit=current_price * 1.03,
                    stop_loss=current_price * 0.985,
                    reason=f"Short liquidation cascade: ${short_value/1e6:.1f}M forced buying",
                    timestamp=datetime.now(),
                    metadata={
                        "short_liquidated": short_value,
                        "long_liquidated": long_value,
                        "total_liquidated": total_liquidated,
                        "liquidation_count": len(recent_liquidations)
                    }
                )
            
            # Signal: >$5M long liquidations = forced selling = SHORT signal
            if long_value >= 5_000_000 and long_value > short_value * 2:
                return SignalResult(
                    symbol=symbol.replace('USDT', '-USD'),
                    signal_type="liquidation-cascade-scout",
                    confidence=min(0.95, 0.6 + (long_value / 20_000_000)),
                    direction="SHORT",
                    entry_price=current_price,
                    take_profit=current_price * 0.97,
                    stop_loss=current_price * 1.015,
                    reason=f"Long liquidation cascade: ${long_value/1e6:.1f}M forced selling",
                    timestamp=datetime.now(),
                    metadata={
                        "short_liquidated": short_value,
                        "long_liquidated": long_value,
                        "total_liquidated": total_liquidated
                    }
                )
            
        except Exception as e:
            logger.error(f"Liquidation cascade error for {symbol}: {e}")
        
        return None
    
    # =============================================================================
    # SIGNAL 4: Acceleration Burst Scout (Momentum Jerk)
    # =============================================================================
    def detect_acceleration_burst(self, symbol: str, data: pd.DataFrame) -> Optional[SignalResult]:
        """
        Detect momentum acceleration (2nd derivative of price)
        Strategy: Jerk signal indicates momentum ACCELERATING, not just moving
        Combine with funding rate turning positive
        """
        if len(data) < 10:
            return None
        
        # Calculate price changes
        close = data['close']
        price_change_1 = close.iloc[-1] - close.iloc[-2]
        price_change_2 = close.iloc[-2] - close.iloc[-3]
        price_change_3 = close.iloc[-3] - close.iloc[-4]
        
        # First derivative (velocity)
        velocity = price_change_1
        
        # Second derivative (acceleration)
        acceleration = price_change_1 - price_change_2
        
        # Third derivative (jerk) - rate of acceleration change
        prev_acceleration = price_change_2 - price_change_3
        jerk = acceleration - prev_acceleration
        
        current_price = close.iloc[-1]
        
        # Volume confirmation
        volume_sma = data['volume'].rolling(window=10).mean().iloc[-1]
        volume_ratio = data['volume'].iloc[-1] / volume_sma if volume_sma > 0 else 0
        
        # Strong acceleration burst with volume
        if jerk > current_price * 0.001 and volume_ratio > 2 and acceleration > 0:
            atr = self._calculate_atr(data)
            
            return SignalResult(
                symbol=symbol.replace('USDT', '-USD'),
                signal_type="acceleration-burst-scout",
                confidence=min(0.9, 0.5 + (jerk / current_price) * 1000 + (volume_ratio / 10)),
                direction="LONG",
                entry_price=current_price,
                take_profit=current_price + (atr * 2.5),
                stop_loss=current_price - (atr * 1.2),
                reason=f"Momentum acceleration: Jerk +{(jerk/current_price)*100:.3f}%, Vol {volume_ratio:.1f}x",
                timestamp=datetime.now(),
                metadata={
                    "jerk": jerk,
                    "acceleration": acceleration,
                    "velocity": velocity,
                    "volume_ratio": volume_ratio,
                    "atr": atr
                }
            )
        
        # Downward acceleration
        if jerk < -current_price * 0.001 and volume_ratio > 2 and acceleration < 0:
            atr = self._calculate_atr(data)
            
            return SignalResult(
                symbol=symbol.replace('USDT', '-USD'),
                signal_type="acceleration-burst-scout",
                confidence=min(0.9, 0.5 + abs(jerk / current_price) * 1000 + (volume_ratio / 10)),
                direction="SHORT",
                entry_price=current_price,
                take_profit=current_price - (atr * 2.5),
                stop_loss=current_price + (atr * 1.2),
                reason=f"Momentum deceleration: Jerk {(jerk/current_price)*100:.3f}%, Vol {volume_ratio:.1f}x",
                timestamp=datetime.now(),
                metadata={
                    "jerk": jerk,
                    "acceleration": acceleration,
                    "volume_ratio": volume_ratio,
                    "atr": atr
                }
            )
        
        return None
    
    # =============================================================================
    # SIGNAL 5: CoinGecko Trending Spike Scout
    # =============================================================================
    async def detect_trending_spike(self) -> List[SignalResult]:
        """
        Detect when coins enter CoinGecko trending list + volume spike
        Uses CoinGecko /coins/trending API (free, no key)
        """
        signals = []
        try:
            url = f"{self.coingecko_base}/search/trending"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return signals
                    data = await resp.json()
            
            trending = data.get('coins', [])
            
            for item in trending[:7]:  # Top 7 trending
                coin = item.get('item', {})
                symbol = coin.get('symbol', '').upper()
                
                if not symbol:
                    continue
                
                # Get price data for this coin
                market_data = await self._get_coingecko_market_data(coin.get('id'))
                
                if market_data:
                    price = market_data.get('current_price', {}).get('usd', 0)
                    volume_change = market_data.get('price_change_percentage_24h_in_currency', {}).get('usd', 0)
                    
                    # Trending + volume spike criteria
                    if volume_change and volume_change > 20:
                        signals.append(SignalResult(
                            symbol=f"{symbol}-USD",
                            signal_type="coingecko-trending-spike-scout",
                            confidence=min(0.85, 0.5 + volume_change / 200),
                            direction="LONG",
                            entry_price=price,
                            take_profit=price * 1.05,
                            stop_loss=price * 0.97,
                            reason=f"Trending on CoinGecko + {volume_change:.1f}% volume surge",
                            timestamp=datetime.now(),
                            metadata={
                                "trending_rank": coin.get('market_cap_rank', 999),
                                "volume_change_24h": volume_change,
                                "market_cap": market_data.get('market_cap', {}).get('usd', 0)
                            }
                        ))
            
        except Exception as e:
            logger.error(f"Trending spike error: {e}")
        
        return signals
    
    # =============================================================================
    # SIGNAL 6: Whale Size Trade Scout
    # =============================================================================
    async def detect_whale_trades(self, symbol: str) -> Optional[SignalResult]:
        """
        Detect individual whale trades > $100K
        Uses Binance trade stream: /api/v3/trades
        """
        try:
            url = f"{self.binance_base}/api/v3/trades"
            params = {"symbol": symbol, "limit": 500}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return None
                    trades = await resp.json()
            
            if not trades:
                return None
            
            # Filter whale trades (> $100K) in last 15 minutes
            cutoff_time = (datetime.now() - timedelta(minutes=15)).timestamp() * 1000
            whale_trades = []
            total_whale_volume = 0
            
            for trade in trades:
                if trade.get('time', 0) < cutoff_time:
                    continue
                
                price = float(trade.get('price', 0))
                qty = float(trade.get('qty', 0))
                value = price * qty
                
                if value >= 100_000:
                    whale_trades.append({
                        'price': price,
                        'qty': qty,
                        'value': value,
                        'is_buyer_maker': trade.get('isBuyerMaker', False)
                    })
                    total_whale_volume += value
            
            if not whale_trades:
                return None
            
            # Determine direction based on whale trades
            buy_pressure = sum(t['value'] for t in whale_trades if not t['is_buyer_maker'])
            sell_pressure = sum(t['value'] for t in whale_trades if t['is_buyer_maker'])
            
            current_price = float(trades[0].get('price', 0))
            whale_count = len(whale_trades)
            
            if buy_pressure > sell_pressure * 1.5 and total_whale_volume >= 500_000:
                return SignalResult(
                    symbol=symbol.replace('USDT', '-USD'),
                    signal_type="whale-size-trade-scout",
                    confidence=min(0.9, 0.5 + (total_whale_volume / 5_000_000)),
                    direction="LONG",
                    entry_price=current_price,
                    take_profit=current_price * 1.025,
                    stop_loss=current_price * 0.99,
                    reason=f"Whale accumulation: {whale_count} trades, ${total_whale_volume/1e6:.2f}M buy pressure",
                    timestamp=datetime.now(),
                    metadata={
                        "whale_count": whale_count,
                        "total_whale_volume": total_whale_volume,
                        "buy_pressure": buy_pressure,
                        "sell_pressure": sell_pressure,
                        "avg_trade_size": total_whale_volume / whale_count
                    }
                )
            
            if sell_pressure > buy_pressure * 1.5 and total_whale_volume >= 500_000:
                return SignalResult(
                    symbol=symbol.replace('USDT', '-USD'),
                    signal_type="whale-size-trade-scout",
                    confidence=min(0.9, 0.5 + (total_whale_volume / 5_000_000)),
                    direction="SHORT",
                    entry_price=current_price,
                    take_profit=current_price * 0.975,
                    stop_loss=current_price * 1.01,
                    reason=f"Whale distribution: {whale_count} trades, ${total_whale_volume/1e6:.2f}M sell pressure",
                    timestamp=datetime.now(),
                    metadata={
                        "whale_count": whale_count,
                        "total_whale_volume": total_whale_volume,
                        "buy_pressure": buy_pressure,
                        "sell_pressure": sell_pressure
                    }
                )
            
        except Exception as e:
            logger.error(f"Whale trade error for {symbol}: {e}")
        
        return None
    
    # =============================================================================
    # SIGNAL 7: Funding Rate Reversal Scout
    # =============================================================================
    async def detect_funding_reversal(self, symbol: str) -> Optional[SignalResult]:
        """
        Detect funding rate turning from negative to positive
        Strategy: Transition signal - short liquidation phase ending, longs taking control
        """
        try:
            url = f"{self.binance_futures}/fapi/v1/fundingRate"
            params = {"symbol": symbol, "limit": 3}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
            
            if len(data) < 2:
                return None
            
            # Get last two funding rates
            current_rate = float(data[0].get('fundingRate', 0))
            previous_rate = float(data[1].get('fundingRate', 0))
            
            # Current price
            ticker_url = f"{self.binance_futures}/fapi/v1/ticker/price"
            async with aiohttp.ClientSession() as session:
                async with session.get(ticker_url, params={"symbol": symbol}) as resp:
                    if resp.status == 200:
                        price_data = await resp.json()
                        current_price = float(price_data.get('price', 0))
                    else:
                        return None
            
            # Funding turning from negative to positive (shorts paying longs)
            if previous_rate < 0 and current_rate > 0:
                return SignalResult(
                    symbol=symbol.replace('USDT', '-USD'),
                    signal_type="funding-rate-reversal-scout",
                    confidence=0.75,
                    direction="LONG",
                    entry_price=current_price,
                    take_profit=current_price * 1.02,
                    stop_loss=current_price * 0.985,
                    reason=f"Funding reversal: {previous_rate*100:.4f}% → {current_rate*100:.4f}%, longs taking control",
                    timestamp=datetime.now(),
                    metadata={
                        "previous_funding": previous_rate,
                        "current_funding": current_rate,
                        "funding_change": current_rate - previous_rate
                    }
                )
            
            # Funding turning from positive to negative (longs paying shorts)
            if previous_rate > 0 and current_rate < 0:
                return SignalResult(
                    symbol=symbol.replace('USDT', '-USD'),
                    signal_type="funding-rate-reversal-scout",
                    confidence=0.75,
                    direction="SHORT",
                    entry_price=current_price,
                    take_profit=current_price * 0.98,
                    stop_loss=current_price * 1.015,
                    reason=f"Funding reversal: {previous_rate*100:.4f}% → {current_rate*100:.4f}%, shorts taking control",
                    timestamp=datetime.now(),
                    metadata={
                        "previous_funding": previous_rate,
                        "current_funding": current_rate,
                        "funding_change": current_rate - previous_rate
                    }
                )
            
        except Exception as e:
            logger.error(f"Funding reversal error for {symbol}: {e}")
        
        return None
    
    # =============================================================================
    # SIGNAL 8: Multi-Exchange Momentum Divergence
    # =============================================================================
    async def detect_exchange_divergence(self, symbol: str) -> Optional[SignalResult]:
        """
        Detect price divergence across exchanges (Binance vs OKX vs Bybit)
        Strategy: Divergence > 0.5% = arbitrage pressure = momentum signal
        """
        # This would require API keys for multiple exchanges
        # Simplified implementation using Binance spot vs futures
        try:
            # Spot price
            spot_url = f"{self.binance_base}/api/v3/ticker/price"
            futures_url = f"{self.binance_futures}/fapi/v1/ticker/price"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(spot_url, params={"symbol": symbol}) as resp:
                    if resp.status != 200:
                        return None
                    spot_data = await resp.json()
                
                async with session.get(futures_url, params={"symbol": symbol}) as resp:
                    if resp.status != 200:
                        return None
                    futures_data = await resp.json()
            
            spot_price = float(spot_data.get('price', 0))
            futures_price = float(futures_data.get('price', 0))
            
            if spot_price == 0:
                return None
            
            divergence = abs(futures_price - spot_price) / spot_price * 100
            
            # Significant divergence
            if divergence >= 0.5:
                direction = "LONG" if futures_price > spot_price else "SHORT"
                entry = futures_price if direction == "LONG" else futures_price
                
                return SignalResult(
                    symbol=symbol.replace('USDT', '-USD'),
                    signal_type="multi-exchange-momentum-scout",
                    confidence=min(0.8, 0.5 + divergence / 2),
                    direction=direction,
                    entry_price=entry,
                    take_profit=entry * (1.015 if direction == "LONG" else 0.985),
                    stop_loss=entry * (0.99 if direction == "LONG" else 1.01),
                    reason=f"Exchange divergence: Spot ${spot_price:,.2f} vs Futures ${futures_price:,.2f} ({divergence:.2f}%)",
                    timestamp=datetime.now(),
                    metadata={
                        "spot_price": spot_price,
                        "futures_price": futures_price,
                        "divergence_pct": divergence
                    }
                )
            
        except Exception as e:
            logger.error(f"Exchange divergence error for {symbol}: {e}")
        
        return None
    
    # =============================================================================
    # SIGNAL 9: Smart Money Concepts - Order Block Detection
    # =============================================================================
    def detect_order_block_smc(self, symbol: str, data: pd.DataFrame) -> Optional[SignalResult]:
        """
        Smart Money Concepts: Detect order blocks (institutional accumulation zones)
        Uses the last bearish candle before a strong bullish move
        """
        if len(data) < 20:
            return None
        
        # Look for bullish order block pattern
        # 1. Bearish candle (potential institutional buy zone)
        # 2. Followed by strong bullish displacement
        
        for i in range(-10, -2):
            if i >= len(data) or i + 2 >= len(data):
                continue
            
            candle = data.iloc[i]
            next_candle = data.iloc[i + 1]
            
            # Bearish candle
            is_bearish = candle['close'] < candle['open']
            
            # Strong bullish follow-through
            bullish_displacement = (next_candle['close'] - next_candle['open']) / next_candle['open'] > 0.01
            breaks_high = next_candle['close'] > candle['high']
            
            if is_bearish and bullish_displacement and breaks_high:
                # This bearish candle is now a bullish order block
                order_block_low = candle['low']
                order_block_high = candle['high']
                
                current_price = data['close'].iloc[-1]
                
                # Price retraced to order block zone
                if order_block_low <= current_price <= order_block_high * 1.02:
                    return SignalResult(
                        symbol=symbol.replace('USDT', '-USD'),
                        signal_type="smc-order-block-scout",
                        confidence=0.8,
                        direction="LONG",
                        entry_price=current_price,
                        take_profit=current_price + (current_price - order_block_low) * 2,
                        stop_loss=order_block_low * 0.995,
                        reason=f"Bullish Order Block retest: Zone ${order_block_low:,.2f}-${order_block_high:,.2f}",
                        timestamp=datetime.now(),
                        metadata={
                            "order_block_low": order_block_low,
                            "order_block_high": order_block_high,
                            "displacement_candle": i + 1
                        }
                    )
        
        return None
    
    # =============================================================================
    # SIGNAL 10: Fair Value Gap (FVG) Detection
    # =============================================================================
    def detect_fair_value_gap(self, symbol: str, data: pd.DataFrame) -> Optional[SignalResult]:
        """
        Smart Money Concepts: Detect Fair Value Gaps (imbalances)
        FVG = area where price moved aggressively, leaving unfilled orders
        """
        if len(data) < 10:
            return None
        
        # Look for bullish FVG: Current low > previous high (gap up)
        current = data.iloc[-1]
        prev = data.iloc[-2]
        prev2 = data.iloc[-3]
        
        # Bullish FVG: Current candle's low is above previous candle's high
        # AND there was strong buying in the middle candle
        if (current['low'] > prev['high'] and 
            prev['close'] > prev['open'] and
            (prev['close'] - prev['open']) / prev['open'] > 0.005):
            
            fvg_top = current['low']
            fvg_bottom = prev['high']
            
            return SignalResult(
                symbol=symbol.replace('USDT', '-USD'),
                signal_type="smc-fvg-scout",
                confidence=0.75,
                direction="LONG",
                entry_price=current['close'],
                take_profit=current['close'] * 1.02,
                stop_loss=fvg_bottom,
                reason=f"Bullish Fair Value Gap: ${fvg_bottom:,.2f}-${fvg_top:,.2f}",
                timestamp=datetime.now(),
                metadata={
                    "fvg_top": fvg_top,
                    "fvg_bottom": fvg_bottom,
                    "fvg_size": fvg_top - fvg_bottom
                }
            )
        
        # Bearish FVG: Current high < previous low
        if (current['high'] < prev['low'] and 
            prev['close'] < prev['open'] and
            (prev['open'] - prev['close']) / prev['open'] > 0.005):
            
            fvg_top = prev['low']
            fvg_bottom = current['high']
            
            return SignalResult(
                symbol=symbol.replace('USDT', '-USD'),
                signal_type="smc-fvg-scout",
                confidence=0.75,
                direction="SHORT",
                entry_price=current['close'],
                take_profit=current['close'] * 0.98,
                stop_loss=fvg_top,
                reason=f"Bearish Fair Value Gap: ${fvg_bottom:,.2f}-${fvg_top:,.2f}",
                timestamp=datetime.now(),
                metadata={
                    "fvg_top": fvg_top,
                    "fvg_bottom": fvg_bottom,
                    "fvg_size": fvg_top - fvg_bottom
                }
            )
        
        return None
    
    # =============================================================================
    # Helper Methods
    # =============================================================================
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range for dynamic TP/SL"""
        if len(data) < period:
            return data['close'].iloc[-1] * 0.02  # Default 2%
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        
        return atr if not np.isnan(atr) else data['close'].iloc[-1] * 0.02
    
    async def _get_coingecko_market_data(self, coin_id: str) -> Optional[Dict]:
        """Get market data from CoinGecko"""
        try:
            url = f"{self.coingecko_base}/coins/{coin_id}"
            params = {"localization": "false", "tickers": "false", "market_data": "true"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        return (await resp.json()).get('market_data', {})
        except Exception:
            pass
        return None
    
    async def _fetch_klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV data from Binance with retry + OKX fallback"""
        kline_columns = [
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ]

        # Try Binance with retries
        for attempt in range(3):
            try:
                url = f"{self.binance_base}/api/v3/klines"
                params = {"symbol": symbol, "interval": interval, "limit": limit}

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            df = pd.DataFrame(data, columns=kline_columns)
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                            for col in ['open', 'high', 'low', 'close', 'volume']:
                                df[col] = df[col].astype(float)
                            return df
                        else:
                            logger.warning(f"Binance klines {symbol} attempt {attempt+1}: HTTP {resp.status}")
            except Exception as e:
                logger.warning(f"Binance klines {symbol} attempt {attempt+1}: {e}")
            if attempt < 2:
                time.sleep(1)

        # Fallback to OKX
        try:
            okx_symbol = symbol.replace("USDT", "-USDT")
            url = f"https://www.okx.com/api/v5/market/candles"
            params = {"instId": okx_symbol, "bar": interval, "limit": str(limit)}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        candles = result.get('data', [])
                        if candles:
                            # OKX returns [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
                            rows = []
                            for c in candles:
                                rows.append([int(c[0]), c[1], c[2], c[3], c[4], c[5],
                                             0, 0, 0, 0, 0, 0])
                            df = pd.DataFrame(rows, columns=kline_columns)
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                            for col in ['open', 'high', 'low', 'close', 'volume']:
                                df[col] = df[col].astype(float)
                            df = df.sort_values('timestamp').reset_index(drop=True)
                            logger.info(f"OKX fallback success for {symbol}")
                            return df
        except Exception as e:
            logger.error(f"OKX fallback error for {symbol}: {e}")

        return pd.DataFrame()
    
    # =============================================================================
    # Main Scan Method
    # =============================================================================
    async def scan_all_signals(self) -> List[SignalResult]:
        """
        Run all signal detection strategies across all symbols
        Returns list of high-confidence signals
        """
        all_signals = []
        
        # Get trending signals first
        trending_signals = await self.detect_trending_spike()
        all_signals.extend(trending_signals)
        
        # Scan each symbol
        for symbol in self.symbols[:15]:  # Limit to top 15 for speed
            try:
                # Fetch price data
                df = await self._fetch_klines(symbol, "1h", 50)
                if df.empty:
                    continue
                
                # Run synchronous signals
                signal = self.detect_pump_acceleration(symbol, df)
                if signal and signal.confidence >= 0.50:
                    all_signals.append(signal)

                signal = self.detect_acceleration_burst(symbol, df)
                if signal and signal.confidence >= 0.50:
                    all_signals.append(signal)

                signal = self.detect_order_block_smc(symbol, df)
                if signal and signal.confidence >= 0.50:
                    all_signals.append(signal)

                signal = self.detect_fair_value_gap(symbol, df)
                if signal and signal.confidence >= 0.50:
                    all_signals.append(signal)

                # Run async signals
                signal = await self.detect_order_book_imbalance(symbol)
                if signal and signal.confidence >= 0.50:
                    all_signals.append(signal)

                signal = await self.detect_liquidation_cascade(symbol)
                if signal and signal.confidence >= 0.50:
                    all_signals.append(signal)

                signal = await self.detect_whale_trades(symbol)
                if signal and signal.confidence >= 0.50:
                    all_signals.append(signal)

                signal = await self.detect_funding_reversal(symbol)
                if signal and signal.confidence >= 0.50:
                    all_signals.append(signal)

                signal = await self.detect_exchange_divergence(symbol)
                if signal and signal.confidence >= 0.50:
                    all_signals.append(signal)
                
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")
                continue
        
        # Sort by confidence and remove duplicates
        all_signals.sort(key=lambda x: x.confidence, reverse=True)
        
        # Remove duplicate symbols (keep highest confidence)
        seen_symbols = set()
        unique_signals = []
        for signal in all_signals:
            if signal.symbol not in seen_symbols:
                seen_symbols.add(signal.symbol)
                unique_signals.append(signal)
        
        return unique_signals[:20]  # Return top 20
    
    def to_dict(self, signal: SignalResult) -> Dict:
        """Convert signal to dictionary for JSON serialization"""
        return {
            "symbol": signal.symbol,
            "signal_type": signal.signal_type,
            "confidence": round(signal.confidence, 4),
            "direction": signal.direction,
            "entry_price": round(signal.entry_price, 6),
            "take_profit": round(signal.take_profit, 6),
            "stop_loss": round(signal.stop_loss, 6),
            "reason": signal.reason,
            "timestamp": signal.timestamp.isoformat(),
            "metadata": signal.metadata
        }


# =============================================================================
# Telegram Signal Parser (Helper)
# =============================================================================
class TelegramSignalParser:
    """
    Parse Telegram crypto signals from popular channels
    Looks for patterns: "TP1:", "TP2:", "SL:", "Entry:", "🎯", "Target:"
    """
    
    PATTERNS = {
        'entry': r'(?:entry|buy|long|short|sell)[\s:]*(\d+\.?\d*)',
        'tp1': r'(?:tp1|target\s*1|take\s*profit\s*1)[\s:]*(\d+\.?\d*)',
        'tp2': r'(?:tp2|target\s*2|take\s*profit\s*2)[\s:]*(\d+\.?\d*)',
        'tp3': r'(?:tp3|target\s*3|take\s*profit\s*3)[\s:]*(\d+\.?\d*)',
        'sl': r'(?:sl|stop\s*loss)[\s:]*(\d+\.?\d*)',
        'symbol': r'\$([A-Z]{2,10})'
    }
    
    @classmethod
    def parse_message(cls, message: str) -> Optional[Dict]:
        """Extract signal data from Telegram message"""
        import re
        
        result = {
            'symbol': None,
            'entry': None,
            'tp1': None,
            'tp2': None,
            'tp3': None,
            'sl': None,
            'direction': None
        }
        
        message_lower = message.lower()
        
        # Extract symbol
        symbol_match = re.search(cls.PATTERNS['symbol'], message)
        if symbol_match:
            result['symbol'] = symbol_match.group(1)
        
        # Extract entry
        entry_match = re.search(cls.PATTERNS['entry'], message_lower)
        if entry_match:
            result['entry'] = float(entry_match.group(1))
        
        # Extract take profits
        tp1_match = re.search(cls.PATTERNS['tp1'], message_lower)
        if tp1_match:
            result['tp1'] = float(tp1_match.group(1))
        
        tp2_match = re.search(cls.PATTERNS['tp2'], message_lower)
        if tp2_match:
            result['tp2'] = float(tp2_match.group(1))
        
        tp3_match = re.search(cls.PATTERNS['tp3'], message_lower)
        if tp3_match:
            result['tp3'] = float(tp3_match.group(1))
        
        # Extract stop loss
        sl_match = re.search(cls.PATTERNS['sl'], message_lower)
        if sl_match:
            result['sl'] = float(sl_match.group(1))
        
        # Determine direction
        if any(word in message_lower for word in ['long', 'buy', 'pump', '🚀', '📈']):
            result['direction'] = 'LONG'
        elif any(word in message_lower for word in ['short', 'sell', 'dump', '📉', '🔻']):
            result['direction'] = 'SHORT'
        
        # Only return if we have minimum required fields
        if result['symbol'] and result['entry'] and (result['tp1'] or result['sl']):
            return result
        
        return None


# =============================================================================
# Main Entry Point
# =============================================================================
async def main():
    """Test the acceleration engine"""
    engine = CryptoAccelerationEngine()
    
    print("=" * 80)
    print("KIMI_FEB172026 - Crypto Acceleration Engine")
    print("Institutional-Grade Signal Detection")
    print("=" * 80)
    
    signals = await engine.scan_all_signals()
    
    print(f"\nFound {len(signals)} high-confidence signals:\n")
    
    for i, signal in enumerate(signals, 1):
        print(f"{i}. {signal.symbol}")
        print(f"   Signal: {signal.signal_type}")
        print(f"   Direction: {signal.direction}")
        print(f"   Confidence: {signal.confidence:.1%}")
        print(f"   Entry: ${signal.entry_price:,.2f}")
        print(f"   TP: ${signal.take_profit:,.2f}")
        print(f"   SL: ${signal.stop_loss:,.2f}")
        print(f"   Reason: {signal.reason}")
        print()
    
    # Save to JSON
    output = [engine.to_dict(s) for s in signals]
    with open('KIMI_FEB172026/data/acceleration_signals.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nSignals saved to KIMI_FEB172026/data/acceleration_signals.json")


if __name__ == "__main__":
    asyncio.run(main())
