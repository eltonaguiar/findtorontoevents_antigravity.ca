#!/usr/bin/env python3
"""
KIMI Top 3 Picks — Automation & Tracking System
===============================================

Automates entry, tracking, and performance monitoring for:
1. Williams %R Mean Reversion
2. VWAP Bollinger Squeeze
3. Regime-Adaptive EMA Ribbon

Features:
- Real-time signal generation
- Auto-entry with risk management
- P/L tracking (realized & unrealized)
- Performance analytics
- Dashboard integration

Author: KIMI | Version: 1.0 | Date: 2026-03-14
"""

from __future__ import annotations

import json
import sys
import math
import sqlite3
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple

import numpy as np
import pandas as pd

# Path setup
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from genome.mutation_lab.innovative_mutations import (
    fetch_binance_klines, regime_kelly_mutation, 
    composite_ensemble_mutation, detect_regime, _smart_round, _now_iso, sma, ema, rsi, atr
)


# ==============================================================================
# CONFIGURATION
# ==============================================================================

@dataclass
class TopPickConfig:
    """Configuration for each top pick strategy."""
    name: str
    strategy_id: str
    symbols: List[str]
    timeframe: str
    kelly_pct: float
    weight: float
    min_confidence: float
    tp_mult: float
    sl_mult: float


TOP_3_CONFIGS = [
    TopPickConfig(
        name="Williams %R Mean Reversion",
        strategy_id="williams_r_reversion",
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="4h",
        kelly_pct=0.16,
        weight=0.35,
        min_confidence=0.65,
        tp_mult=2.5,
        sl_mult=1.5,
    ),
    TopPickConfig(
        name="VWAP Bollinger Squeeze",
        strategy_id="vwap_bollinger_squeeze",
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        timeframe="1h",
        kelly_pct=0.15,
        weight=0.35,
        min_confidence=0.65,
        tp_mult=2.0,
        sl_mult=1.5,
    ),
    TopPickConfig(
        name="Regime-Adaptive EMA Ribbon",
        strategy_id="ema_ribbon_macd",
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOTUSDT"],
        timeframe="1h",
        kelly_pct=0.12,
        weight=0.30,
        min_confidence=0.60,
        tp_mult=3.0,
        sl_mult=1.0,
    ),
]


# ==============================================================================
# DATABASE SETUP
# ==============================================================================

class TradeTracker:
    """SQLite-based trade tracking for realized/unrealized P/L."""
    
    def __init__(self, db_path: str = "genome/data/kimi_top_picks.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                entry_time TEXT NOT NULL,
                exit_price REAL,
                exit_time TEXT,
                take_profit REAL,
                stop_loss REAL,
                position_size REAL,
                position_value REAL,
                kelly_fraction REAL,
                regime TEXT,
                confidence REAL,
                status TEXT DEFAULT 'OPEN',
                realized_pnl REAL DEFAULT 0,
                realized_pnl_pct REAL DEFAULT 0,
                unrealized_pnl REAL DEFAULT 0,
                unrealized_pnl_pct REAL DEFAULT 0,
                exit_reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Performance summary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT NOT NULL,
                date TEXT NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                avg_win REAL DEFAULT 0,
                avg_loss REAL DEFAULT 0,
                profit_factor REAL DEFAULT 0,
                total_realized_pnl REAL DEFAULT 0,
                total_unrealized_pnl REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                sharpe_ratio REAL DEFAULT 0,
                UNIQUE(strategy_id, date)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def insert_trade(self, trade_data: dict) -> int:
        """Insert new trade and return trade ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO trades (
                strategy_id, symbol, direction, entry_price, entry_time,
                take_profit, stop_loss, position_size, position_value,
                kelly_fraction, regime, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_data['strategy_id'],
            trade_data['symbol'],
            trade_data['direction'],
            trade_data['entry_price'],
            trade_data['entry_time'],
            trade_data.get('take_profit'),
            trade_data.get('stop_loss'),
            trade_data.get('position_size'),
            trade_data.get('position_value'),
            trade_data.get('kelly_fraction'),
            trade_data.get('regime'),
            trade_data.get('confidence'),
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trade_id
    
    def update_unrealized_pnl(self, trade_id: int, current_price: float):
        """Update unrealized P/L for open trade."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT direction, entry_price, position_value FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        
        if row:
            direction, entry_price, position_value = row
            
            if direction == 'BUY':
                pnl_pct = (current_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - current_price) / entry_price
            
            unrealized_pnl = position_value * pnl_pct
            
            cursor.execute("""
                UPDATE trades 
                SET unrealized_pnl = ?, unrealized_pnl_pct = ?, updated_at = ?
                WHERE id = ?
            """, (unrealized_pnl, pnl_pct, _now_iso(), trade_id))
            
            conn.commit()
        
        conn.close()
    
    def close_trade(self, trade_id: int, exit_price: float, exit_reason: str):
        """Close trade and calculate realized P/L."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT direction, entry_price, position_value FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        
        if row:
            direction, entry_price, position_value = row
            
            if direction == 'BUY':
                pnl_pct = (exit_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - exit_price) / entry_price
            
            realized_pnl = position_value * pnl_pct
            
            cursor.execute("""
                UPDATE trades 
                SET status = 'CLOSED',
                    exit_price = ?,
                    exit_time = ?,
                    realized_pnl = ?,
                    realized_pnl_pct = ?,
                    unrealized_pnl = 0,
                    unrealized_pnl_pct = 0,
                    exit_reason = ?,
                    updated_at = ?
                WHERE id = ?
            """, (exit_price, _now_iso(), realized_pnl, pnl_pct, exit_reason, _now_iso(), trade_id))
            
            conn.commit()
        
        conn.close()
    
    def get_open_trades(self) -> List[dict]:
        """Get all open trades with current status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM trades WHERE status = 'OPEN' ORDER BY entry_time DESC
        """)
        
        columns = [description[0] for description in cursor.description]
        trades = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return trades
    
    def get_performance_summary(self, strategy_id: str = None, days: int = 30) -> dict:
        """Get performance summary for dashboard."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        query = """
            SELECT 
                strategy_id,
                COUNT(*) as total_trades,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN realized_pnl <= 0 THEN 1 ELSE 0 END) as losses,
                AVG(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE NULL END) as avg_win,
                AVG(CASE WHEN realized_pnl <= 0 THEN realized_pnl ELSE NULL END) as avg_loss,
                SUM(realized_pnl) as total_pnl,
                MAX(unrealized_pnl) as max_unrealized
            FROM trades 
            WHERE entry_time > ?
        """
        
        if strategy_id:
            query += " AND strategy_id = ?"
            cursor.execute(query, (since, strategy_id))
        else:
            cursor.execute(query, (since,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            total, wins, losses = row[1], row[2], row[3]
            win_rate = wins / total if total > 0 else 0
            
            return {
                'strategy_id': strategy_id or 'ALL',
                'total_trades': total,
                'winning_trades': wins,
                'losing_trades': losses,
                'win_rate': win_rate,
                'avg_win': row[4] or 0,
                'avg_loss': row[5] or 0,
                'total_realized_pnl': row[6] or 0,
                'profit_factor': abs(row[4] / row[5]) if row[5] and row[5] != 0 else 0,
            }
        
        return {}


# ==============================================================================
# SIGNAL GENERATION
# ==============================================================================

def williams_r_indicator(close: pd.Series, lookback: int = 14) -> pd.Series:
    """Calculate Williams %R indicator."""
    highest_high = close.rolling(lookback).max()
    lowest_low = close.rolling(lookback).min()
    
    williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)
    return williams_r.fillna(-50)


def generate_williams_r_signals(df: pd.DataFrame, config: TopPickConfig) -> List[dict]:
    """Generate signals for Williams %R Mean Reversion."""
    signals = []
    
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    if len(close) < 200:
        return signals
    
    williams_r = williams_r_indicator(close)
    sma_200 = close.rolling(200).mean()
    atr_val = atr(high, low, close, 14).iloc[-1]
    
    current_price = close.iloc[-1]
    current_wr = williams_r.iloc[-1]
    
    # Long signal: Oversold + above 200 SMA
    if current_wr < -80 and current_price > sma_200.iloc[-1]:
        entry = current_price
        tp = entry + (atr_val * config.tp_mult)
        sl = entry - (atr_val * config.sl_mult)
        
        signals.append({
            'strategy_id': config.strategy_id,
            'symbol': df.name if hasattr(df, 'name') else 'UNKNOWN',
            'direction': 'BUY',
            'entry_price': entry,
            'take_profit': tp,
            'stop_loss': sl,
            'confidence': min(0.95, 0.7 + abs(current_wr + 80) / 100),
            'indicators': {'williams_r': current_wr, 'sma200': sma_200.iloc[-1]},
        })
    
    # Short signal: Overbought + below 200 SMA
    elif current_wr > -20 and current_price < sma_200.iloc[-1]:
        entry = current_price
        tp = entry - (atr_val * config.tp_mult)
        sl = entry + (atr_val * config.sl_mult)
        
        signals.append({
            'strategy_id': config.strategy_id,
            'symbol': df.name if hasattr(df, 'name') else 'UNKNOWN',
            'direction': 'SELL',
            'entry_price': entry,
            'take_profit': tp,
            'stop_loss': sl,
            'confidence': min(0.95, 0.7 + abs(current_wr + 20) / 100),
            'indicators': {'williams_r': current_wr, 'sma200': sma_200.iloc[-1]},
        })
    
    return signals


def generate_vwap_squeeze_signals(df: pd.DataFrame, config: TopPickConfig) -> List[dict]:
    """Generate signals for VWAP Bollinger Squeeze."""
    # Import from supplemental mutations
    sys.path.insert(0, str(ROOT / 'genome' / 'mutation_lab'))
    from kimi_supplemental_mutations import vwap_bollinger_squeeze
    
    # Create mock data dict
    data = {config.symbols[0]: df}  # Use first symbol as key
    
    # This would need proper integration - simplified for now
    signals = []
    
    # Simplified squeeze detection
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    if len(close) < 50:
        return signals
    
    # Bollinger Bands
    sma_20 = close.rolling(20).mean()
    std_20 = close.rolling(20).std()
    bb_lower = sma_20 - 2 * std_20
    bb_upper = sma_20 + 2 * std_20
    bandwidth = (bb_upper - bb_lower) / sma_20
    
    # VWAP
    typical = (high + low + close) / 3
    vwap = (typical * volume).rolling(20).sum() / volume.rolling(20).sum()
    
    current = close.iloc[-1]
    rsi_val = rsi(close, 14).iloc[-1]
    
    # Buy: Near lower BB + oversold
    if current < bb_lower.iloc[-1] * 1.005 and rsi_val < 45:
        atr_val = atr(high, low, close, 14).iloc[-1]
        tp = max(vwap.iloc[-1], current + atr_val * 2)
        sl = current - atr_val * 1.5
        
        signals.append({
            'strategy_id': config.strategy_id,
            'symbol': config.symbols[0],
            'direction': 'BUY',
            'entry_price': current,
            'take_profit': tp,
            'stop_loss': sl,
            'confidence': 0.65 + (45 - rsi_val) / 100,
        })
    
    return signals


def generate_ema_ribbon_signals(df: pd.DataFrame, config: TopPickConfig) -> List[dict]:
    """Generate signals for EMA Ribbon MACD."""
    signals = []
    
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    if len(close) < 55:
        return signals
    
    # EMA Ribbon
    ema_9 = close.ewm(span=9).mean()
    ema_21 = close.ewm(span=21).mean()
    ema_50 = close.ewm(span=50).mean()
    
    # MACD
    ema_12 = close.ewm(span=12).mean()
    ema_26 = close.ewm(span=26).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9).mean()
    histogram = macd_line - signal_line
    
    current = close.iloc[-1]
    
    # Bullish ribbon + histogram turning up
    if (ema_9.iloc[-1] > ema_21.iloc[-1] > ema_50.iloc[-1] and 
        histogram.iloc[-1] > histogram.iloc[-2] > histogram.iloc[-3]):
        
        atr_val = atr(high, low, close, 14).iloc[-1]
        tp = current + atr_val * config.tp_mult
        sl = ema_21.iloc[-1]  # SL at middle EMA
        
        signals.append({
            'strategy_id': config.strategy_id,
            'symbol': config.symbols[0],
            'direction': 'BUY',
            'entry_price': current,
            'take_profit': tp,
            'stop_loss': sl,
            'confidence': 0.7,
        })
    
    return signals


# ==============================================================================
# MAIN AUTOMATION ENGINE
# ==============================================================================

class KIMITopPicksEngine:
    """Main automation engine for top 3 picks."""
    
    def __init__(self, account_equity: float = 10000):
        self.tracker = TradeTracker()
        self.account_equity = account_equity
        self.market_data = {}
    
    def fetch_all_data(self):
        """Fetch data for all symbols in top 3 picks."""
        all_symbols = set()
        for config in TOP_3_CONFIGS:
            all_symbols.update(config.symbols)
        
        print(f"Fetching data for {len(all_symbols)} symbols...")
        
        for symbol in all_symbols:
            # Use 1H as base, resample for 4H if needed
            df = fetch_binance_klines(symbol, "1h", limit=200)
            if not df.empty:
                self.market_data[symbol] = df
                print(f"  [OK] {symbol}: {len(df)} bars")
            else:
                print(f"  [ERR] {symbol}: No data")
    
    def generate_all_signals(self) -> List[dict]:
        """Generate signals for all 3 strategies."""
        all_signals = []
        
        for config in TOP_3_CONFIGS:
            print(f"\nGenerating signals for: {config.name}")
            
            for symbol in config.symbols:
                if symbol not in self.market_data:
                    continue
                
                df = self.market_data[symbol]
                
                if config.strategy_id == 'williams_r_reversion':
                    signals = generate_williams_r_signals(df, config)
                elif config.strategy_id == 'vwap_bollinger_squeeze':
                    signals = generate_vwap_squeeze_signals(df, config)
                elif config.strategy_id == 'ema_ribbon_macd':
                    signals = generate_ema_ribbon_signals(df, config)
                else:
                    signals = []
                
                for sig in signals:
                    if sig['confidence'] >= config.min_confidence:
                        # Add sizing
                        position_value = self.account_equity * config.kelly_pct
                        position_size = position_value / sig['entry_price']
                        
                        sig.update({
                            'symbol': symbol,
                            'position_size': position_size,
                            'position_value': position_value,
                            'kelly_fraction': config.kelly_pct,
                            'entry_time': _now_iso(),
                        })
                        
                        all_signals.append(sig)
                        print(f"  -> {symbol} {sig['direction']} @ ${sig['entry_price']:,.2f} (conf: {sig['confidence']:.2f})")
        
        return all_signals
    
    def execute_signals(self, signals: List[dict]):
        """Execute signals by adding to tracker."""
        print(f"\nExecuting {len(signals)} signals...")
        
        for sig in signals:
            trade_id = self.tracker.insert_trade(sig)
            print(f"  [TRADE ID: {trade_id}] {sig['symbol']} {sig['direction']} - Kelly: {sig['kelly_fraction']:.2%}")
    
    def update_portfolio(self):
        """Update unrealized P/L for all open trades."""
        open_trades = self.tracker.get_open_trades()
        
        if not open_trades:
            print("No open trades to update.")
            return
        
        print(f"\nUpdating {len(open_trades)} open trades...")
        
        for trade in open_trades:
            symbol = trade['symbol']
            
            # Fetch current price
            if symbol in self.market_data:
                current_price = self.market_data[symbol]['Close'].iloc[-1]
                self.tracker.update_unrealized_pnl(trade['id'], current_price)
    
    def generate_dashboard_data(self) -> dict:
        """Generate data for audit dashboard."""
        data = {
            'timestamp': _now_iso(),
            'account_equity': self.account_equity,
            'open_trades': self.tracker.get_open_trades(),
            'performance': {},
        }
        
        for config in TOP_3_CONFIGS:
            perf = self.tracker.get_performance_summary(config.strategy_id, days=30)
            data['performance'][config.strategy_id] = perf
        
        # Overall performance
        data['performance']['TOTAL'] = self.tracker.get_performance_summary(days=30)
        
        return data
    
    def run_cycle(self):
        """Complete automation cycle."""
        print("="*70)
        print("KIMI TOP 3 PICKS — Automation Cycle")
        print("="*70)
        print(f"Account Equity: ${self.account_equity:,.2f}")
        print(f"Time: {_now_iso()}")
        
        # Fetch data
        self.fetch_all_data()
        
        # Update existing positions
        self.update_portfolio()
        
        # Generate new signals
        signals = self.generate_all_signals()
        
        # Execute
        if signals:
            self.execute_signals(signals)
        else:
            print("\nNo new signals generated.")
        
        # Generate dashboard data
        dashboard_data = self.generate_dashboard_data()
        
        # Save dashboard data
        output_path = ROOT / 'genome' / 'data' / 'kimi_top_picks_dashboard.json'
        with open(output_path, 'w') as f:
            json.dump(dashboard_data, f, indent=2, default=str)
        
        print(f"\nDashboard data saved: {output_path}")
        print("="*70)
        
        return dashboard_data


# ==============================================================================
# CLI
# ==============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="KIMI Top 3 Picks Automation")
    parser.add_argument("--equity", type=float, default=10000, help="Account equity")
    parser.add_argument("--cycle", action="store_true", help="Run full cycle")
    parser.add_argument("--dashboard", action="store_true", help="Generate dashboard data only")
    args = parser.parse_args()
    
    engine = KIMITopPicksEngine(account_equity=args.equity)
    
    if args.cycle:
        engine.run_cycle()
    elif args.dashboard:
        data = engine.generate_dashboard_data()
        print(json.dumps(data, indent=2, default=str))
    else:
        # Default: run cycle
        engine.run_cycle()
