#!/usr/bin/env python3
"""
Commodity Strategy Signal Generator
====================================
Generates live trading signals for commodity strategies (XAU/WTI)
to feed into the forward test pipeline.

Run standalone: python alpha_engine/commodity_signal_generator.py
"""

import sys
sys.path.insert(0, '.')
import json
import pandas as pd
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
COMMODITY_PICKS_FILE = DATA_DIR / "commodity_active_picks.json"


# ============= DATA FETCHING =============
def get_klines(symbol: str, interval: str = '15m', limit: int = 100) -> Optional[pd.DataFrame]:
    """Fetch klines from Binance"""
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote', 'trades', 'taker_base', 'taker_quote', 'ignore'
        ])
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        return df[['open', 'high', 'low', 'close']]
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None


# ============= BOLLINGER MR SIGNAL (Reusable) =============
def bollinger_mr_signal(df: pd.DataFrame, symbol: str, strategy_name: str, commodity_type: str) -> Optional[Dict]:
    """Bollinger Band Mean Reversion Strategy - reusable for Gold, Silver, Platinum"""
    close = df['close']
    high = df['high']
    low = df['low']
    
    bb_period = 20
    bb_std = 2.0
    sma_period = 200
    
    sma = close.rolling(bb_period).mean()
    std = close.rolling(bb_period).std()
    lower_band = sma - bb_std * std
    sma200 = close.rolling(sma_period).mean()
    
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=1).mean()
    
    if len(df) < sma_period + bb_period:
        return None
    
    current_price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2])
    current_lower = float(lower_band.iloc[-1])
    current_middle = float(sma.iloc[-1])
    current_sma200 = float(sma200.iloc[-1])
    current_atr = float(atr.iloc[-1])
    
    # Entry: price at lower band in broader uptrend
    if (current_price <= current_lower and 
        current_price > current_sma200 * 0.9 and 
        prev_price > current_lower and 
        current_atr > 0):
        
        tp = current_middle
        sl = current_price - (current_atr * 1.5)
        
        # Confidence based on band depth
        band_depth = (current_lower - current_price) / current_atr if current_atr > 0 else 0.0
        confidence = min(0.5 + band_depth * 0.15 + 0.1, 0.90)
        
        # Price precision based on commodity type (all precious metals use 2 decimals)
        decimals = 2 if commodity_type in ("gold", "silver", "platinum") else 4
        
        return {
            "symbol": symbol,
            "direction": "LONG",
            "entry_price": round(current_price, decimals),
            "take_profit": round(tp, decimals),
            "stop_loss": round(sl, decimals),
            "confidence": round(confidence, 3),
            "strategy": strategy_name,
            "asset_class": "COMMODITY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": f"{commodity_type} strategy: {symbol} at lower BB"
        }
    
    return None


# ============= WTI ENSEMBLE STRATEGY =============
def wti_ensemble_signal(df: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """WTI Ensemble Trend-Following Strategy"""
    close = df['close']
    
    sma_short = 20
    sma_medium = 50
    rsi_period = 14
    
    sma20 = close.rolling(sma_short).mean()
    sma50 = close.rolling(sma_medium).mean()
    
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    
    if len(df) < sma_medium + rsi_period:
        return None
    
    current_price = float(close.iloc[-1])
    current_sma20 = float(sma20.iloc[-1])
    current_sma50 = float(sma50.iloc[-1])
    current_rsi = float(rsi.iloc[-1])
    prev_sma20 = float(sma20.iloc[-2])
    prev_sma50 = float(sma50.iloc[-2])
    
    tp_pct = 4.0
    sl_pct = 2.5
    
    # LONG: SMA20 crosses above SMA50 + RSI not overbought
    long_cond = (current_sma20 > current_sma50 and prev_sma20 <= prev_sma50 and current_rsi < 70)
    # SHORT: SMA20 crosses below SMA50 + RSI not oversold
    short_cond = (current_sma20 < current_sma50 and prev_sma20 >= prev_sma50 and current_rsi > 30)
    
    if long_cond:
        tp = current_price * (1 + tp_pct / 100)
        sl = current_price * (1 - sl_pct / 100)
        
        rsi_conf = (70 - current_rsi) / 50
        confidence = min(0.60 + rsi_conf * 0.25, 0.90)
        
        return {
            "symbol": symbol,
            "direction": "LONG",
            "entry_price": round(current_price, 8),
            "take_profit": round(tp, 8),
            "stop_loss": round(sl, 8),
            "confidence": round(confidence, 3),
            "strategy": "wti_ensemble_rehab",
            "asset_class": "COMMODITY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": f"wti_ensemble LONG: trend up + RSI {current_rsi:.1f}"
        }
    elif short_cond:
        tp = current_price * (1 - tp_pct / 100)
        sl = current_price * (1 + sl_pct / 100)
        
        rsi_conf = (current_rsi - 30) / 50
        confidence = min(0.60 + rsi_conf * 0.25, 0.90)
        
        return {
            "symbol": symbol,
            "direction": "SHORT",
            "entry_price": round(current_price, 8),
            "take_profit": round(tp, 8),
            "stop_loss": round(sl, 8),
            "confidence": round(confidence, 3),
            "strategy": "wti_ensemble_rehab",
            "asset_class": "COMMODITY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": f"wti_ensemble SHORT: trend down + RSI {current_rsi:.1f}"
        }
    
    return None


# ============= MAIN SIGNAL GENERATION =============
def generate_commodity_signals() -> List[Dict]:
    """Generate signals for all commodity strategies"""
    # Defensive import of pre-emission policy gates. Fail-open if broken.
    try:
        from alpha_engine.non_crypto_policy import passes_non_crypto_policy
        _policy_available = True
    except Exception:
        _policy_available = False

    signals: List[Dict] = []

    def _emit(signal: Optional[Dict], label: str) -> None:
        """Apply pre-emission policy gates then append the signal.

        Stamps `asset_class='COMMODITY'` (this module only emits commodities)
        so the policy gate can route correctly.
        """
        if signal is None:
            return
        signal.setdefault("asset_class", "COMMODITY")
        signal.setdefault("category", "commodity")

        if _policy_available:
            try:
                ok, reason = passes_non_crypto_policy(signal)
                if not ok:
                    print(f"  POLICY BLOCK: {signal.get('symbol')} ({label}): {reason}")
                    return
            except Exception:
                # Fail-open on unexpected gate errors.
                pass

        signals.append(signal)
        print(f"  {signal.get('symbol')} ({label}): {signal.get('direction')} "
              f"@ {signal.get('entry_price')} (conf={signal.get('confidence')})")

    # Gold symbols (available on Binance)
    gold_symbols = ["PAXGUSDT", "XAUTUSDT"]
    for symbol in gold_symbols:
        df = get_klines(symbol, '15m', 100)
        if df is not None:
            signal = bollinger_mr_signal(df, symbol, "xau_bollinger_mr_rehab", "gold")
            _emit(signal, "Gold")

    # Silver proxy: Use high-volatility crypto as silver proxy
    # Note: XAGUSDT not available on Binance - using RNDR, ARBUSDT as silver-like proxies
    silver_proxies = ["RNDRUSDT", "ARBUSDT"]
    for symbol in silver_proxies:
        df = get_klines(symbol, '15m', 100)
        if df is not None:
            signal = bollinger_mr_signal(df, symbol, "silver_proxy_bollinger_mr", "silver")
            _emit(signal, "Silver proxy")

    # Platinum proxy: Use high-volatility crypto as platinum proxy
    # Note: XPTUSDT not available on Binance - using INJ, AVAX as platinum-like proxies
    platinum_proxies = ["INJUSDT", "AVAXUSDT"]
    for symbol in platinum_proxies:
        df = get_klines(symbol, '15m', 100)
        if df is not None:
            signal = bollinger_mr_signal(df, symbol, "platinum_proxy_bollinger_mr", "platinum")
            _emit(signal, "Platinum proxy")

    # WTI proxy symbols (high-volatility alternatives since direct WTI not on Binance)
    wti_symbols = ["XLMUSDT", "DOTUSDT"]
    for symbol in wti_symbols:
        df = get_klines(symbol, '15m', 100)
        if df is not None:
            signal = wti_ensemble_signal(df, symbol)
            _emit(signal, "Oil proxy")

    return signals


def save_signals(signals: List[Dict]) -> None:
    """Save signals to JSON file for forward test pipeline"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(COMMODITY_PICKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(signals, f, indent=2, default=str)
    print(f"Saved {len(signals)} signals to {COMMODITY_PICKS_FILE}")


def main():
    print("="*60)
    print("COMMODITY SIGNAL GENERATOR")
    print(f"Time: {datetime.now(timezone.utc).isoformat()} UTC")
    print("="*60)
    
    signals = generate_commodity_signals()
    
    if signals:
        save_signals(signals)
        print(f"\nGenerated {len(signals)} commodity signals")
    else:
        print("\nNo signals generated (market conditions not met)")
        # Save empty file anyway to maintain pipeline consistency
        save_signals([])
    
    return 0


if __name__ == "__main__":
    sys.exit(main())