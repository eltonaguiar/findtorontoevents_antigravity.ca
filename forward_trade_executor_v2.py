#!/usr/bin/env python3
"""
Forward Trade Executor v2 - Fixed Resolution Tracking
Addresses: 94% signal expiration issue from audit findings

Key Fixes:
- Hourly resolution checking (was: only during CI runs)
- Proper TP/SL calculation using 3x ATR
- Real-time Discord alerts
- Signal state persistence
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import sqlite3
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import time
import sys
import os

# Add project root to path for multi_source_fetcher import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'KIMI_RISEOFTHECLAW'))
from multi_source_fetcher import (
    fetch_latest_price_multi,
    fetch_symbol_data_multi,
    fetch_binance_price,
    fetch_bybit_price,
    fetch_kucoin_klines,
    fetch_kraken_ohlc,
    fetch_coincap_history,
    _yf_to_binance,
    _yf_to_bybit,
    _yf_to_kucoin,
    _yf_to_okx,
    _YF_TO_KRAKEN,
    _http_json,
    print_fetch_summary,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('forward_tracking.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SignalStatus(Enum):
    OPEN = "open"
    TP_HIT = "tp_hit"
    SL_HIT = "sl_hit"
    EXPIRED = "expired"
    MANUAL_CLOSE = "manual_close"


@dataclass
class ActiveSignal:
    id: str
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    tp_price: float
    sl_price: float
    risk_reward: float
    created_at: datetime
    system: str
    quality_score: float
    status: SignalStatus = SignalStatus.OPEN
    resolved_at: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl_pct: Optional[float] = None
    max_profit_pct: Optional[float] = None
    max_loss_pct: Optional[float] = None
    
    def to_dict(self):
        data = asdict(self)
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        return data


class ForwardTradeExecutor:
    """
    Fixed forward trade executor with proper resolution tracking.
    """
    
    def __init__(self, 
                 discord_webhook: Optional[str] = None,
                 db_path: str = "forward_tracking.db",
                 check_interval_minutes: int = 60):
        
        self.discord_webhook = discord_webhook
        self.db_path = db_path
        self.check_interval = check_interval_minutes
        
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for signal tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                tp_price REAL NOT NULL,
                sl_price REAL NOT NULL,
                risk_reward REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                system TEXT,
                quality_score REAL,
                status TEXT DEFAULT 'open',
                resolved_at TIMESTAMP,
                exit_price REAL,
                pnl_pct REAL,
                max_profit_pct REAL,
                max_loss_pct REAL,
                resolution_notes TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status ON signals(status)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol ON signals(symbol)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
        
    @staticmethod
    def _symbol_to_yf(symbol: str) -> str:
        """Convert BTCUSDT/BTC/USDT format to yfinance BTC-USD format."""
        s = symbol.replace('/', '').replace('-', '').upper()
        # Strip trailing USDT/USD
        for suffix in ('USDT', 'USD'):
            if s.endswith(suffix):
                base = s[:-len(suffix)]
                return f"{base}-USD"
        return f"{s}-USD"

    def fetch_current_price(self, symbol: str) -> Optional[float]:
        """Fetch current price using 7-exchange failover (no ccxt, no geo-block)."""
        yf_sym = self._symbol_to_yf(symbol)
        price = fetch_latest_price_multi(yf_sym)
        if price and price > 0:
            logger.info(f"Price for {symbol}: {price:.2f}")
            return price
        logger.error(f"All sources failed for {symbol} (yf: {yf_sym})")
        return None

    def calculate_atr(self, symbol: str, timeframe: str = '1h', periods: int = 14) -> Optional[float]:
        """Calculate ATR using 7-exchange failover OHLCV data."""
        yf_sym = self._symbol_to_yf(symbol)
        try:
            df = fetch_symbol_data_multi(yf_sym, period="1mo")
            if df is None or len(df) < periods:
                logger.warning(f"Insufficient OHLCV data for {symbol} ATR")
                return None

            # Calculate True Range
            df['tr1'] = df['High'] - df['Low']
            df['tr2'] = abs(df['High'] - df['Close'].shift())
            df['tr3'] = abs(df['Low'] - df['Close'].shift())
            df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

            atr = df['tr'].rolling(window=periods).mean().iloc[-1]
            if pd.isna(atr):
                return None
            logger.info(f"ATR for {symbol}: {atr:.4f}")
            return float(atr)
        except Exception as e:
            logger.warning(f"ATR calculation failed for {symbol}: {e}")
            return None
    
    def recalculate_tp_sl(self, 
                         entry_price: float, 
                         direction: str, 
                         symbol: str,
                         rr_target: float = 2.5) -> Tuple[float, float]:
        """
        Recalculate TP/SL using 3x ATR (FIXED from 2x).
        
        Args:
            entry_price: Entry price
            direction: 'LONG' or 'SHORT'
            symbol: Trading pair
            rr_target: Risk/Reward ratio target (default 2.5:1)
            
        Returns:
            (tp_price, sl_price)
        """
        atr = self.calculate_atr(symbol)
        
        if atr is None:
            logger.warning(f"Could not calculate ATR for {symbol}, using percentage fallback")
            # Fallback: 3% for SL, 7.5% for TP (2.5 RR)
            if direction == 'LONG':
                sl_price = entry_price * 0.97
                tp_price = entry_price * 1.075
            else:
                sl_price = entry_price * 1.03
                tp_price = entry_price * 0.925
            return tp_price, sl_price
        
        # Use 3x ATR for SL (FIXED: was 2x)
        atr_multiplier_sl = 3.0
        # Use 7.5x ATR for TP to achieve 2.5:1 RR
        atr_multiplier_tp = atr_multiplier_sl * rr_target
        
        if direction == 'LONG':
            sl_price = entry_price - (atr * atr_multiplier_sl)
            tp_price = entry_price + (atr * atr_multiplier_tp)
        else:  # SHORT
            sl_price = entry_price + (atr * atr_multiplier_sl)
            tp_price = entry_price - (atr * atr_multiplier_tp)
        
        logger.info(f"{symbol} {direction}: Entry={entry_price:.2f}, "
                   f"SL={sl_price:.2f} (3xATR), TP={tp_price:.2f} (7.5xATR)")
        
        return tp_price, sl_price
    
    def add_signal(self, signal: ActiveSignal) -> bool:
        """Add a new signal to tracking."""
        try:
            # Recalculate TP/SL with fixed ATR multiplier
            tp_price, sl_price = self.recalculate_tp_sl(
                signal.entry_price,
                signal.direction,
                signal.symbol
            )
            
            signal.tp_price = tp_price
            signal.sl_price = sl_price
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO signals 
                (id, symbol, direction, entry_price, tp_price, sl_price, 
                 risk_reward, created_at, system, quality_score, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.id, signal.symbol, signal.direction, signal.entry_price,
                signal.tp_price, signal.sl_price, signal.risk_reward,
                signal.created_at, signal.system, signal.quality_score,
                signal.status.value
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Added signal {signal.id} for {signal.symbol}")
            
            # Send Discord notification
            self._notify_discord(
                f"🆕 New Signal: {signal.symbol} {signal.direction}\n"
                f"Entry: {signal.entry_price:.2f}\n"
                f"TP: {signal.tp_price:.2f} | SL: {signal.sl_price:.2f}\n"
                f"R:R = {abs(signal.tp_price - signal.entry_price) / abs(signal.entry_price - signal.sl_price):.2f}:1\n"
                f"Quality Score: {signal.quality_score:.1f}",
                color=0x00ff00 if signal.direction == 'LONG' else 0xff0000
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add signal: {e}")
            return False
    
    def check_signal_resolution(self, signal: ActiveSignal) -> SignalStatus:
        """
        Check if a signal has hit TP or SL.
        
        Returns:
            Updated SignalStatus
        """
        current_price = self.fetch_current_price(signal.symbol)
        
        if current_price is None:
            logger.error(f"Could not fetch price for {signal.symbol}")
            return signal.status
        
        # Track max profit/loss
        if signal.direction == 'LONG':
            pnl_pct = (current_price - signal.entry_price) / signal.entry_price * 100
        else:
            pnl_pct = (signal.entry_price - current_price) / signal.entry_price * 100
        
        if signal.max_profit_pct is None or pnl_pct > signal.max_profit_pct:
            signal.max_profit_pct = pnl_pct
        if signal.max_loss_pct is None or pnl_pct < signal.max_loss_pct:
            signal.max_loss_pct = pnl_pct
        
        # Check TP hit
        if signal.direction == 'LONG':
            if current_price >= signal.tp_price:
                return SignalStatus.TP_HIT
            elif current_price <= signal.sl_price:
                return SignalStatus.SL_HIT
        else:  # SHORT
            if current_price <= signal.tp_price:
                return SignalStatus.TP_HIT
            elif current_price >= signal.sl_price:
                return SignalStatus.SL_HIT
        
        return SignalStatus.OPEN
    
    def update_signal(self, signal: ActiveSignal):
        """Update signal in database with current status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE signals 
            SET status = ?, max_profit_pct = ?, max_loss_pct = ?
            WHERE id = ?
        ''', (signal.status.value, signal.max_profit_pct, signal.max_loss_pct, signal.id))
        
        conn.commit()
        conn.close()
    
    def resolve_signal(self, 
                      signal: ActiveSignal, 
                      status: SignalStatus,
                      exit_price: float):
        """Mark a signal as resolved."""
        signal.status = status
        signal.resolved_at = datetime.now()
        signal.exit_price = exit_price
        
        # Calculate P&L
        if signal.direction == 'LONG':
            signal.pnl_pct = (exit_price - signal.entry_price) / signal.entry_price * 100
        else:
            signal.pnl_pct = (signal.entry_price - exit_price) / signal.entry_price * 100
        
        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE signals 
            SET status = ?, resolved_at = ?, exit_price = ?, pnl_pct = ?,
                max_profit_pct = ?, max_loss_pct = ?
            WHERE id = ?
        ''', (
            status.value, signal.resolved_at, exit_price, signal.pnl_pct,
            signal.max_profit_pct, signal.max_loss_pct, signal.id
        ))
        
        conn.commit()
        conn.close()
        
        # Discord notification
        emoji = "✅" if status == SignalStatus.TP_HIT else "❌"
        color = 0x00ff00 if status == SignalStatus.TP_HIT else 0xff0000
        
        self._notify_discord(
            f"{emoji} Signal Resolved: {signal.symbol} {signal.direction}\n"
            f"Result: {status.value.upper()}\n"
            f"Entry: {signal.entry_price:.2f} → Exit: {exit_price:.2f}\n"
            f"P&L: {signal.pnl_pct:+.2f}%\n"
            f"Max Favorable: {signal.max_profit_pct:+.2f}%\n"
            f"Max Adverse: {signal.max_loss_pct:+.2f}%",
            color=color
        )
        
        logger.info(f"Resolved signal {signal.id}: {status.value} at {exit_price:.2f}")
    
    def check_expiration(self, signal: ActiveSignal, max_age_hours: int = 72) -> bool:
        """Check if signal should expire due to age."""
        age = datetime.now() - signal.created_at
        return age > timedelta(hours=max_age_hours)
    
    def scan_all_signals(self):
        """Main loop: Check all open signals for resolution."""
        logger.info("Starting signal resolution scan...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, symbol, direction, entry_price, tp_price, sl_price,
                   risk_reward, created_at, system, quality_score, status
            FROM signals WHERE status = 'open'
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        logger.info(f"Found {len(rows)} open signals to check")
        
        resolved_count = 0
        expired_count = 0
        
        for row in rows:
            signal = ActiveSignal(
                id=row[0],
                symbol=row[1],
                direction=row[2],
                entry_price=row[3],
                tp_price=row[4],
                sl_price=row[5],
                risk_reward=row[6],
                created_at=datetime.fromisoformat(row[7]),
                system=row[8],
                quality_score=row[9],
                status=SignalStatus(row[10])
            )
            
            # Check for expiration first
            if self.check_expiration(signal):
                current_price = self.fetch_current_price(signal.symbol)
                if current_price:
                    self.resolve_signal(
                        signal, 
                        SignalStatus.EXPIRED, 
                        current_price
                    )
                    expired_count += 1
                continue
            
            # Check for TP/SL hit
            new_status = self.check_signal_resolution(signal)
            
            if new_status != SignalStatus.OPEN:
                exit_price = signal.tp_price if new_status == SignalStatus.TP_HIT else signal.sl_price
                self.resolve_signal(signal, new_status, exit_price)
                resolved_count += 1
            else:
                # Update max profit/loss tracking
                self.update_signal(signal)
        
        logger.info(f"Scan complete: {resolved_count} resolved, {expired_count} expired")
        print_fetch_summary()

        # Generate summary stats
        self._generate_stats()
    
    def _generate_stats(self):
        """Generate and log performance statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN status = 'sl_hit' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired,
                AVG(CASE WHEN status IN ('tp_hit', 'sl_hit') THEN pnl_pct END) as avg_pnl
            FROM signals
        ''')
        
        row = cursor.fetchone()
        total, wins, losses, expired, avg_pnl = row
        
        if total and wins is not None:
            resolved = wins + losses
            if resolved > 0:
                win_rate = wins / resolved * 100
                logger.info(f"=== FORWARD TESTING STATS ===")
                logger.info(f"Total Signals: {total}")
                logger.info(f"Resolved: {resolved} (W:{wins} L:{losses})")
                logger.info(f"Expired: {expired}")
                logger.info(f"Win Rate: {win_rate:.1f}%")
                logger.info(f"Avg P&L: {avg_pnl:.2f}%")
                logger.info(f"=============================")
                
                # Alert on low resolution rate
                if resolved / total < 0.1:
                    self._notify_discord(
                        f"⚠️ WARNING: Low resolution rate!\n"
                        f"Only {resolved}/{total} signals resolved ({resolved/total*100:.1f}%)\n"
                        f"Check TP/SL levels - may be too wide/tight",
                        color=0xffa500
                    )
        
        conn.close()
    
    def _notify_discord(self, message: str, color: int = 0x00ff00):
        """Send notification to Discord webhook."""
        if not self.discord_webhook:
            return
        
        try:
            payload = {
                "embeds": [{
                    "description": message,
                    "color": color,
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            
            response = requests.post(
                self.discord_webhook,
                json=payload,
                timeout=10
            )
            
            if response.status_code != 204:
                logger.warning(f"Discord notification failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Discord notification error: {e}")
    
    def run_continuous(self):
        """Run continuous monitoring loop."""
        logger.info(f"Starting continuous monitoring (interval: {self.check_interval} minutes)")
        
        while True:
            try:
                self.scan_all_signals()
            except Exception as e:
                logger.error(f"Error in scan loop: {e}")
            
            logger.info(f"Sleeping for {self.check_interval} minutes...")
            time.sleep(self.check_interval * 60)
    
    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Normalize symbol to BTCUSDT format for internal tracking."""
        s = symbol.upper().replace('/', '')
        if s.endswith('-USD'):
            return s.replace('-USD', '') + 'USDT'
        if not s.endswith('USDT') and not s.endswith('USD'):
            return s + 'USDT'
        return s

    @staticmethod
    def _normalize_pick(pick: dict, system: str) -> Optional[dict]:
        """Normalize a pick from any system format to a common structure.

        Supports:
          - Genome: {symbol, direction, entry_price, take_profit, stop_loss}
          - Alpha Engine: {symbol, direction, entry_price, take_profit, stop_loss}
          - KIMI: {symbol, signal, entryPrice, targetPrice, stopPrice}
        """
        try:
            # Determine direction
            direction = (
                pick.get('direction')
                or ('LONG' if pick.get('signal', '').upper() in ('BUY', 'LONG') else
                    'SHORT' if pick.get('signal', '').upper() in ('SELL', 'SHORT') else None)
            )
            if not direction:
                return None

            # Entry price
            entry = float(
                pick.get('entry_price')
                or pick.get('entryPrice')
                or 0
            )
            if entry <= 0:
                return None

            # TP / SL
            tp = float(
                pick.get('take_profit')
                or pick.get('targetPrice')
                or pick.get('grossTargetPrice')
                or 0
            )
            sl = float(
                pick.get('stop_loss')
                or pick.get('stopPrice')
                or 0
            )

            return {
                'id': pick.get('id', f"{system}_{datetime.now().timestamp()}"),
                'symbol': pick.get('symbol', ''),
                'direction': direction.upper(),
                'entry_price': entry,
                'take_profit': tp,
                'stop_loss': sl,
                'risk_reward': float(pick.get('risk_reward') or pick.get('riskReward') or 2.0),
                'quality_score': float(
                    pick.get('quality_score')
                    or pick.get('confidence', 0.7) * 100
                ),
            }
        except (ValueError, TypeError, KeyError):
            return None

    def import_from_json(self, json_path: str, system: str = "unknown"):
        """Import signals from JSON file.

        Handles multiple formats:
          - Genome:       {"picks": [...]}
          - Alpha Engine: [...] (bare list)
          - KIMI:         {"activePicks": [...]}
        """
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Extract picks list from any format
            if isinstance(data, list):
                picks = data
            elif isinstance(data, dict):
                picks = (
                    data.get('picks')
                    or data.get('activePicks')
                    or data.get('signals')
                    or []
                )
            else:
                picks = []

            if not picks:
                logger.warning(f"No picks found in {json_path}")
                return

            imported = 0
            for pick in picks:
                norm = self._normalize_pick(pick, system)
                if norm is None:
                    continue

                symbol = self._normalize_symbol(norm['symbol'])
                signal = ActiveSignal(
                    id=norm['id'],
                    symbol=symbol,
                    direction=norm['direction'],
                    entry_price=norm['entry_price'],
                    tp_price=norm['take_profit'],
                    sl_price=norm['stop_loss'],
                    risk_reward=norm['risk_reward'],
                    created_at=datetime.now(),
                    system=system,
                    quality_score=norm['quality_score'],
                )

                if self.add_signal(signal):
                    imported += 1

            logger.info(f"Imported {imported} signals from {json_path}")

        except Exception as e:
            logger.error(f"Failed to import from {json_path}: {e}")


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Forward Trade Executor v2')
    parser.add_argument('--discord-webhook', help='Discord webhook URL for alerts')
    parser.add_argument('--db-path', default='forward_tracking.db', help='Database path')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in minutes')
    parser.add_argument('--import-json', help='Import signals from JSON file')
    parser.add_argument('--system', default='genome', help='System name for imports')
    parser.add_argument('--run-once', action='store_true', help='Run once and exit')
    
    args = parser.parse_args()
    
    executor = ForwardTradeExecutor(
        discord_webhook=args.discord_webhook,
        db_path=args.db_path,
        check_interval_minutes=args.interval
    )
    
    if args.import_json:
        executor.import_from_json(args.import_json, args.system)
        # If only importing, exit (don't fall into continuous loop)
        if not args.run_once:
            return

    if args.run_once:
        executor.scan_all_signals()
    else:
        executor.run_continuous()


if __name__ == "__main__":
    main()
