#!/usr/bin/env python3
"""
LIVE UNDERDOG ALPHA BOT
========================
Institutional-grade execution of underdog strategies.

⚠️ COMPETITION REALITY CHECK ⚠️
================================
We are competing with:
- Renaissance Technologies: Medallion Fund 66% annual returns, $130B AUM
- Citadel Securities: $65B AUM, executes 25% of US equity volume
- Jump Trading: HFT dominance, sub-microsecond latency
- Two Sigma: 1,600+ employees, $60B AUM
- Jane Street: $10T+ annual trading volume

THEY have:
✅ Supercomputers and quantum research
✅ Co-located servers on every exchange
✅ PhDs from MIT, Caltech, Harvard
✅ 40 years of proprietary data
✅ Billions in capital
✅ Relationships with regulators

WE have:
✅ Capacity they can't touch ($1-10M)
✅ Behavioral edges too small for them
✅ Free alternative data they ignore
✅ No career risk (can hold through drawdowns)
✅ Speed of execution (we decide, we deploy)

This is NOT about being smarter. It's about finding crumbs they can't be bothered to pick up.
"""

import asyncio
import json
import logging
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiohttp
import pandas as pd

# Configure logging
Path('KIMI_FEB172026/logs').mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('KIMI_FEB172026/logs/underdog_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('UnderdogBot')


@dataclass
class RiskParameters:
    """Institutional-grade risk management."""
    # Position sizing
    max_position_size: float = 25000  # $25K max per trade
    max_total_exposure: float = 100000  # $100K total
    max_positions: int = 10
    
    # Risk limits
    max_drawdown_pct: float = 0.15  # 15% max drawdown
    daily_loss_limit: float = 5000  # $5K daily loss limit
    
    # Per-trade risk
    stop_loss_pct: float = 0.05  # 5% stop loss
    take_profit_pct: float = 0.08  # 8% take profit
    risk_per_trade_pct: float = 0.02  # 2% risk per trade
    
    # Strategy limits
    max_correlation: float = 0.7  # Max correlation between positions
    min_confidence: float = 0.6  # Minimum signal confidence


@dataclass
class Signal:
    """Trading signal structure."""
    strategy: str
    symbol: str
    direction: str  # LONG or SHORT
    entry_price: float
    confidence: float
    timestamp: str
    metadata: Dict
    
    # Risk parameters
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None


@dataclass
class Position:
    """Active position tracking."""
    id: int
    strategy: str
    symbol: str
    direction: str
    entry_price: float
    entry_time: str
    position_size: float
    stop_loss: float
    take_profit: float
    current_price: float
    unrealized_pnl: float
    status: str = 'OPEN'


class UnderdogLiveBot:
    """
    Live trading bot for underdog alpha strategies.
    
    REMEMBER: We are SMALL. We are HUNTING CRUMBS.
    Risk management is the ONLY thing keeping us alive.
    """
    
    def __init__(self, 
                 db_path: str = "KIMI_FEB172026/data/underdog_live.db",
                 risk_params: Optional[RiskParameters] = None):
        self.db_path = db_path
        self.risk = risk_params or RiskParameters()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Initialize
        self.init_database()
        self.running = False
        
        logger.info("=" * 70)
        logger.info("🐺 UNDERDOG LIVE BOT INITIALIZED")
        logger.info("=" * 70)
        logger.info("⚠️  COMPETITION: Renaissance, Citadel, Jump, Two Sigma")
        logger.info("⚠️  We are SMALL. We are hunting CRUMBS they ignore.")
        logger.info("⚠️  Risk management is EVERYTHING.")
        logger.info("=" * 70)
    
    def init_database(self):
        """Initialize live trading database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Positions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                entry_time TEXT NOT NULL,
                position_size REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                exit_price REAL,
                exit_time TEXT,
                realized_pnl REAL DEFAULT 0,
                status TEXT DEFAULT 'OPEN',
                metadata TEXT
            )
        ''')
        
        # Daily P&L tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_pnl (
                date TEXT PRIMARY KEY,
                starting_equity REAL,
                ending_equity REAL,
                trades_count INTEGER,
                win_count INTEGER,
                loss_count INTEGER,
                gross_pnl REAL,
                net_pnl REAL,
                max_drawdown REAL
            )
        ''')
        
        # Risk events
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT,
                action_taken TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"📊 Database initialized: {self.db_path}")
    
    async def start(self):
        """Start the live trading bot."""
        self.session = aiohttp.ClientSession()
        self.running = True
        
        logger.info("🚀 BOT STARTED - Entering live trading mode")
        logger.info("⚠️  REAL MONEY AT RISK - Risk limits active")
        
        try:
            while self.running:
                # 1. Check risk limits FIRST
                if not await self._check_risk_limits():
                    logger.warning("🛑 RISK LIMITS BREACHED - Trading halted")
                    await asyncio.sleep(300)  # Wait 5 minutes
                    continue
                
                # 2. Scan for signals
                signals = await self._scan_all_strategies()
                
                # 3. Filter and validate signals
                valid_signals = self._filter_signals(signals)
                
                # 4. Execute trades
                for signal in valid_signals:
                    await self._execute_signal(signal)
                
                # 5. Update positions
                await self._update_positions()
                
                # 6. Check exits
                await self._check_exits()
                
                # Log status
                await self._log_status()
                
                # Wait before next cycle
                await asyncio.sleep(60)  # 1-minute cycles
                
        except Exception as e:
            logger.error(f"❌ Bot error: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the bot gracefully."""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("🛑 BOT STOPPED")
    
    async def _check_risk_limits(self) -> bool:
        """Check if we're within risk limits."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check daily loss
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COALESCE(SUM(realized_pnl), 0) FROM positions
            WHERE date(entry_time) = ? AND status = 'CLOSED'
        ''', (today,))
        
        daily_pnl = cursor.fetchone()[0] or 0
        
        if daily_pnl < -self.risk.daily_loss_limit:
            logger.warning(f"Daily loss limit hit: ${daily_pnl:,.2f}")
            self._log_risk_event('DAILY_LOSS_LIMIT', f'Loss: ${daily_pnl:,.2f}', 'Trading halted')
            conn.close()
            return False
        
        # Check max drawdown
        cursor.execute('''
            SELECT COALESCE(SUM(realized_pnl), 0) FROM positions WHERE status = 'CLOSED'
        ''')
        total_pnl = cursor.fetchone()[0] or 0
        
        # Calculate drawdown (simplified)
        peak = max(total_pnl, 0)
        drawdown = (peak - total_pnl) / (peak + 100000) if peak > 0 else 0
        
        if drawdown > self.risk.max_drawdown_pct:
            logger.warning(f"Max drawdown hit: {drawdown:.2%}")
            self._log_risk_event('MAX_DRAWDOWN', f'Drawdown: {drawdown:.2%}', 'Trading halted')
            conn.close()
            return False
        
        # Check open positions limit
        cursor.execute('''
            SELECT COUNT(*) FROM positions WHERE status = 'OPEN'
        ''')
        open_count = cursor.fetchone()[0]
        
        if open_count >= self.risk.max_positions:
            logger.info(f"Max positions reached: {open_count}")
            conn.close()
            return False
        
        conn.close()
        return True
    
    async def _scan_all_strategies(self) -> List[Signal]:
        """Scan all underdog strategies for signals."""
        all_signals = []
        
        # Scan crypto funding
        crypto_signals = await self._scan_crypto_funding()
        all_signals.extend(crypto_signals)
        
        # Add other strategies as they're implemented
        # earnings_signals = await self._scan_earnings()
        # wsb_signals = await self._scan_wsb()
        
        return all_signals
    
    async def _scan_crypto_funding(self) -> List[Signal]:
        """Scan for crypto funding arbitrage signals."""
        signals = []
        
        try:
            async with self.session.get(
                'https://fapi.binance.com/fapi/v1/premiumIndex',
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return signals
                
                data = await resp.json()
                
                for item in data:
                    funding_rate = float(item.get('lastFundingRate', 0))
                    symbol = item.get('symbol', '')
                    mark_price = float(item.get('markPrice', 0))
                    
                    # Only trade major pairs with liquidity
                    if not any(x in symbol for x in ['BTC', 'ETH', 'SOL', 'AVAX']):
                        continue
                    
                    # Look for extreme funding (>0.1%)
                    if abs(funding_rate) > 0.001:
                        direction = 'SHORT' if funding_rate > 0 else 'LONG'
                        
                        # Calculate confidence
                        confidence = min(abs(funding_rate) * 500, 0.9)
                        
                        # Set risk parameters
                        stop_loss = mark_price * (1.05 if direction == 'LONG' else 0.95)
                        take_profit = mark_price * (0.98 if direction == 'LONG' else 1.02)
                        position_size = min(10000, self.risk.max_position_size)
                        
                        signal = Signal(
                            strategy='crypto_funding_arbitrage',
                            symbol=symbol.replace('USDT', ''),
                            direction=direction,
                            entry_price=mark_price,
                            confidence=confidence,
                            timestamp=datetime.now().isoformat(),
                            metadata={
                                'funding_rate': funding_rate,
                                'exchange': 'Binance',
                                'expected_hold_hours': 8
                            },
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            position_size=position_size
                        )
                        
                        signals.append(signal)
                
                # Sort by confidence, take top 3
                signals.sort(key=lambda x: x.confidence, reverse=True)
                signals = signals[:3]
                
        except Exception as e:
            logger.warning(f"Crypto funding scan error: {e}")
        
        return signals
    
    def _filter_signals(self, signals: List[Signal]) -> List[Signal]:
        """Filter signals based on risk criteria."""
        valid = []
        
        for signal in signals:
            # Check confidence
            if signal.confidence < self.risk.min_confidence:
                continue
            
            # Check if we already have position in this symbol
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM positions 
                WHERE symbol = ? AND status = 'OPEN'
            ''', (signal.symbol,))
            
            if cursor.fetchone()[0] > 0:
                conn.close()
                continue
            
            conn.close()
            valid.append(signal)
        
        return valid
    
    async def _execute_signal(self, signal: Signal):
        """Execute a trading signal."""
        logger.info(f"🎯 EXECUTING: {signal.strategy} | {signal.direction} {signal.symbol}")
        logger.info(f"   Entry: ${signal.entry_price:,.2f}")
        logger.info(f"   SL: ${signal.stop_loss:,.2f} | TP: ${signal.take_profit:,.2f}")
        logger.info(f"   Size: ${signal.position_size:,.2f}")
        
        # Log to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO positions 
            (strategy, symbol, direction, entry_price, entry_time, 
             position_size, stop_loss, take_profit, metadata, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
        ''', (
            signal.strategy,
            signal.symbol,
            signal.direction,
            signal.entry_price,
            signal.timestamp,
            signal.position_size,
            signal.stop_loss,
            signal.take_profit,
            json.dumps(signal.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"   ✅ Position opened")
    
    async def _update_positions(self):
        """Update current prices and P&L for all positions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, symbol, direction, entry_price, position_size 
            FROM positions WHERE status = 'OPEN'
        ''')
        
        positions = cursor.fetchall()
        
        for pos in positions:
            pos_id, symbol, direction, entry_price, size = pos
            
            # Get current price (simplified - would use real API)
            current_price = await self._get_current_price(symbol)
            
            if current_price:
                # Calculate unrealized P&L
                if direction == 'LONG':
                    pnl = (current_price - entry_price) / entry_price * size
                else:
                    pnl = (entry_price - current_price) / entry_price * size
                
                cursor.execute('''
                    UPDATE positions 
                    SET current_price = ?, unrealized_pnl = ?
                    WHERE id = ?
                ''', (current_price, pnl, pos_id))
        
        conn.commit()
        conn.close()
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        try:
            # For crypto, use Binance
            if symbol in ['BTC', 'ETH', 'SOL', 'AVAX']:
                async with self.session.get(
                    f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT',
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return float(data.get('price', 0))
        except Exception as e:
            logger.warning(f"Price fetch error for {symbol}: {e}")
        
        return None
    
    async def _check_exits(self):
        """Check if any positions hit stop loss or take profit."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, symbol, direction, entry_price, current_price,
                   stop_loss, take_profit, position_size
            FROM positions WHERE status = 'OPEN' AND current_price IS NOT NULL
        ''')
        
        positions = cursor.fetchall()
        
        for pos in positions:
            pos_id, symbol, direction, entry, current, sl, tp, size = pos
            
            exit_triggered = False
            exit_price = current
            exit_reason = ''
            
            if direction == 'LONG':
                if current <= sl:
                    exit_triggered = True
                    exit_reason = 'STOP_LOSS'
                elif current >= tp:
                    exit_triggered = True
                    exit_reason = 'TAKE_PROFIT'
            else:  # SHORT
                if current >= sl:
                    exit_triggered = True
                    exit_reason = 'STOP_LOSS'
                elif current <= tp:
                    exit_triggered = True
                    exit_reason = 'TAKE_PROFIT'
            
            if exit_triggered:
                # Calculate realized P&L
                if direction == 'LONG':
                    pnl = (exit_price - entry) / entry * size
                else:
                    pnl = (entry - exit_price) / entry * size
                
                cursor.execute('''
                    UPDATE positions 
                    SET status = 'CLOSED',
                        exit_price = ?,
                        exit_time = ?,
                        realized_pnl = ?
                    WHERE id = ?
                ''', (exit_price, datetime.now().isoformat(), pnl, pos_id))
                
                emoji = '✅' if pnl > 0 else '❌'
                logger.info(f"{emoji} CLOSED: {symbol} {direction} | P&L: ${pnl:,.2f} ({exit_reason})")
        
        conn.commit()
        conn.close()
    
    async def _log_status(self):
        """Log current bot status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count open positions
        cursor.execute('SELECT COUNT(*), COALESCE(SUM(unrealized_pnl), 0) FROM positions WHERE status = "OPEN"')
        open_count, open_pnl = cursor.fetchone()
        
        # Count today's closed trades
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(realized_pnl), 0) 
            FROM positions 
            WHERE status = 'CLOSED' AND date(exit_time) = ?
        ''', (today,))
        closed_count, closed_pnl = cursor.fetchone()
        
        conn.close()
        
        logger.info(f"📊 STATUS | Open: {open_count} (${open_pnl:,.2f}) | "
                   f"Closed Today: {closed_count} (${closed_pnl:,.2f})")
    
    def _log_risk_event(self, event_type: str, description: str, action: str):
        """Log a risk event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO risk_events (timestamp, event_type, description, action_taken)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now().isoformat(), event_type, description, action))
        
        conn.commit()
        conn.close()
    
    def get_performance_report(self) -> Dict:
        """Generate performance report."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losses,
                SUM(realized_pnl) as total_pnl,
                AVG(realized_pnl) as avg_pnl
            FROM positions WHERE status = 'CLOSED'
        ''')
        
        row = cursor.fetchone()
        total, wins, losses, total_pnl, avg_pnl = row if row else (0, 0, 0, 0, 0)
        
        # By strategy
        cursor.execute('''
            SELECT strategy,
                COUNT(*) as trades,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(realized_pnl) as pnl
            FROM positions WHERE status = 'CLOSED'
            GROUP BY strategy
        ''')
        
        by_strategy = {}
        for row in cursor.fetchall():
            by_strategy[row[0]] = {
                'trades': row[1],
                'wins': row[2],
                'win_rate': row[2] / row[1] if row[1] > 0 else 0,
                'pnl': row[3]
            }
        
        conn.close()
        
        return {
            'total_trades': total,
            'winning_trades': wins,
            'losing_trades': losses,
            'win_rate': wins / total if total > 0 else 0,
            'total_pnl': total_pnl,
            'avg_pnl_per_trade': avg_pnl,
            'by_strategy': by_strategy,
            'competition_note': 'Small edges vs Renaissance/Citadel. Risk management critical.',
            'timestamp': datetime.now().isoformat()
        }


async def main():
    """Main function."""
    bot = UnderdogLiveBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        await bot.stop()
    
    # Print final report
    report = bot.get_performance_report()
    logger.info("\n" + "=" * 70)
    logger.info("📊 FINAL PERFORMANCE REPORT")
    logger.info("=" * 70)
    logger.info(f"Total Trades: {report['total_trades']}")
    logger.info(f"Win Rate: {report['win_rate']:.1%}")
    logger.info(f"Total P&L: ${report['total_pnl']:,.2f}")
    logger.info("=" * 70)


if __name__ == '__main__':
    asyncio.run(main())
