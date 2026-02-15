#!/usr/bin/env python3
"""
FAST VALIDATOR - 15-Minute Signal Resolution Engine
====================================================
Checks signals every 15 minutes and resolves them based on TP/SL hits
Compresses months of validation into days

CLAUDECODE_Feb152026
"""

import json
import os
import sys
import time
import mysql.connector
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import ccxt

# Database configuration
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'favcreators', 'public', 'api'))
try:
    from events_db_config import events_servername, events_username, events_password, events_dbname
    DB_HOST = events_servername
    DB_USER = events_username
    DB_PASS = events_password
    DB_NAME = events_dbname
except:
    # Fallback to env vars
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASS = os.getenv('DB_PASS', '')
    DB_NAME = os.getenv('DB_NAME', 'rapid_validation')


class FastValidator:
    """
    Auto-resolves signals every 15 minutes by checking TP/SL hits
    """

    EXIT_STRATEGIES = {
        'scalp': {
            'tp_field': 'tp_scalp',
            'sl_field': 'sl_scalp',
            'time_limit_minutes': 15,
            'label': 'Scalp (0.5%/0.3%)'
        },
        'swing': {
            'tp_field': 'tp_swing',
            'sl_field': 'sl_swing',
            'time_limit_minutes': 240,  # 4 hours
            'label': 'Swing (2.0%/1.0%)'
        },
        'position': {
            'tp_field': 'tp_position',
            'sl_field': 'sl_position',
            'time_limit_minutes': 1440,  # 24 hours
            'label': 'Position (5.0%/2.5%)'
        }
    }

    def __init__(self, exchange_id='binance'):
        self.exchange_class = getattr(ccxt, exchange_id)
        self.exchange = self.exchange_class({'enableRateLimit': True})
        self.db = None
        self.connect_db()

    def connect_db(self):
        """Connect to MySQL database"""
        try:
            self.db = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME
            )
            print(f"✅ Connected to database: {DB_NAME}")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print(f"   Creating rapid_validation database...")
            self.create_database()

    def create_database(self):
        """Create rapid_validation database and tables"""
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS
            )
            cursor = conn.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS rapid_validation")
            cursor.execute("USE rapid_validation")

            # Create rapid_signals table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rapid_signals (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    signal_id VARCHAR(100) UNIQUE,
                    strategy VARCHAR(100),
                    pair VARCHAR(20),
                    timeframe VARCHAR(10),
                    signal_type VARCHAR(10),
                    entry_price DECIMAL(20,8),
                    tp_scalp DECIMAL(20,8),
                    sl_scalp DECIMAL(20,8),
                    tp_swing DECIMAL(20,8),
                    sl_swing DECIMAL(20,8),
                    tp_position DECIMAL(20,8),
                    sl_position DECIMAL(20,8),
                    confidence INT,
                    indicators JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'ACTIVE',
                    INDEX idx_status (status),
                    INDEX idx_strategy (strategy),
                    INDEX idx_created (created_at)
                )
            """)

            # Create rapid_outcomes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rapid_outcomes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    signal_id VARCHAR(100),
                    exit_strategy VARCHAR(20),
                    outcome VARCHAR(20),
                    exit_price DECIMAL(20,8),
                    pnl_pct DECIMAL(10,4),
                    pnl_usd DECIMAL(10,2),
                    duration_minutes INT,
                    highest_price DECIMAL(20,8),
                    lowest_price DECIMAL(20,8),
                    resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (signal_id) REFERENCES rapid_signals(signal_id),
                    INDEX idx_outcome (outcome),
                    INDEX idx_exit_strategy (exit_strategy),
                    INDEX idx_resolved (resolved_at)
                )
            """)

            # Create rapid_strategy_stats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rapid_strategy_stats (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    strategy VARCHAR(100),
                    timeframe VARCHAR(10),
                    exit_strategy VARCHAR(20),
                    total_trades INT DEFAULT 0,
                    wins INT DEFAULT 0,
                    losses INT DEFAULT 0,
                    expired INT DEFAULT 0,
                    win_rate DECIMAL(5,2),
                    profit_factor DECIMAL(10,2),
                    sharpe_ratio DECIMAL(10,2),
                    total_pnl_pct DECIMAL(10,2),
                    total_pnl_usd DECIMAL(10,2),
                    avg_pnl_pct DECIMAL(10,4),
                    max_drawdown_pct DECIMAL(10,2),
                    consecutive_losses INT DEFAULT 0,
                    max_consecutive_losses INT DEFAULT 0,
                    avg_duration_minutes DECIMAL(10,2),
                    status VARCHAR(20) DEFAULT 'TESTING',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_strategy_tf_exit (strategy, timeframe, exit_strategy)
                )
            """)

            conn.commit()
            print("✅ Created rapid_validation database with tables")
            self.db = conn

        except Exception as e:
            print(f"❌ Failed to create database: {e}")

    def load_signals_from_json(self, json_file: str = 'rapid_validation/rapid_signals.json'):
        """Load signals from JSON and insert into database"""
        if not os.path.exists(json_file):
            print(f"❌ Signal file not found: {json_file}")
            return 0

        with open(json_file, 'r') as f:
            data = json.load(f)

        cursor = self.db.cursor()
        inserted = 0

        for signal in data['signals']:
            try:
                cursor.execute("""
                    INSERT INTO rapid_signals
                    (signal_id, strategy, pair, timeframe, signal_type, entry_price,
                     tp_scalp, sl_scalp, tp_swing, sl_swing, tp_position, sl_position,
                     confidence, indicators)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE signal_id=signal_id
                """, (
                    signal['signal_id'], signal['strategy'], signal['pair'],
                    signal['timeframe'], signal['signal_type'], signal['entry_price'],
                    signal['tp_scalp'], signal['sl_scalp'],
                    signal['tp_swing'], signal['sl_swing'],
                    signal['tp_position'], signal['sl_position'],
                    signal['confidence'], json.dumps(signal['indicators'])
                ))
                inserted += 1
            except Exception as e:
                print(f"  ⚠️  Error inserting signal {signal['signal_id']}: {e}")

        self.db.commit()
        print(f"✅ Inserted {inserted} signals into database")
        return inserted

    def get_current_price(self, pair: str) -> Optional[float]:
        """Fetch current price from exchange"""
        try:
            ticker = self.exchange.fetch_ticker(pair)
            return ticker['last']
        except Exception as e:
            print(f"  ⚠️  Error fetching price for {pair}: {e}")
            return None

    def check_signal_outcome(self, signal: Dict, current_price: float, elapsed_minutes: int) -> List[Dict]:
        """Check if signal hit TP, SL, or expired for all exit strategies"""
        outcomes = []
        entry_price = signal['entry_price']
        signal_type = signal['signal_type']

        for exit_name, exit_config in self.EXIT_STRATEGIES.items():
            tp_price = signal[exit_config['tp_field']]
            sl_price = signal[exit_config['sl_field']]
            time_limit = exit_config['time_limit_minutes']

            outcome = None
            exit_price = current_price
            pnl_pct = 0

            if signal_type == 'long':
                if current_price >= tp_price:
                    outcome = 'WIN'
                    exit_price = tp_price
                    pnl_pct = ((tp_price - entry_price) / entry_price) * 100
                elif current_price <= sl_price:
                    outcome = 'LOSS'
                    exit_price = sl_price
                    pnl_pct = ((sl_price - entry_price) / entry_price) * 100
                elif elapsed_minutes >= time_limit:
                    outcome = 'EXPIRED'
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:  # short
                if current_price <= tp_price:
                    outcome = 'WIN'
                    exit_price = tp_price
                    pnl_pct = ((entry_price - tp_price) / entry_price) * 100
                elif current_price >= sl_price:
                    outcome = 'LOSS'
                    exit_price = sl_price
                    pnl_pct = ((entry_price - sl_price) / entry_price) * 100
                elif elapsed_minutes >= time_limit:
                    outcome = 'EXPIRED'
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100

            if outcome:
                # Assume $100 position size for paper trading
                pnl_usd = (pnl_pct / 100) * 100

                outcomes.append({
                    'signal_id': signal['signal_id'],
                    'exit_strategy': exit_name,
                    'outcome': outcome,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl_usd,
                    'duration_minutes': elapsed_minutes
                })

        return outcomes

    def validate_active_signals(self):
        """Check all active signals and resolve them"""
        cursor = self.db.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM rapid_signals
            WHERE status = 'ACTIVE'
        """)
        active_signals = cursor.fetchall()

        print(f"\n{'='*60}")
        print(f"FAST VALIDATOR - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"{'='*60}")
        print(f"Active signals to check: {len(active_signals)}")
        print(f"{'='*60}\n")

        resolved_count = 0

        for signal in active_signals:
            pair = signal['pair']
            current_price = self.get_current_price(pair)

            if current_price is None:
                continue

            elapsed_minutes = int((datetime.now(timezone.utc) - signal['created_at']).total_seconds() / 60)
            outcomes = self.check_signal_outcome(signal, current_price, elapsed_minutes)

            if outcomes:
                # Insert outcomes
                for outcome in outcomes:
                    cursor.execute("""
                        INSERT INTO rapid_outcomes
                        (signal_id, exit_strategy, outcome, exit_price, pnl_pct, pnl_usd, duration_minutes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        outcome['signal_id'], outcome['exit_strategy'], outcome['outcome'],
                        outcome['exit_price'], outcome['pnl_pct'], outcome['pnl_usd'],
                        outcome['duration_minutes']
                    ))

                # Mark signal as resolved
                cursor.execute("""
                    UPDATE rapid_signals
                    SET status = 'RESOLVED'
                    WHERE signal_id = %s
                """, (signal['signal_id'],))

                resolved_count += 1
                print(f"✅ Resolved: {signal['strategy']} | {pair} | {outcomes[0]['outcome']} | {outcomes[0]['pnl_pct']:.2f}%")

        self.db.commit()
        print(f"\n{'='*60}")
        print(f"RESOLVED: {resolved_count}/{len(active_signals)} signals")
        print(f"{'='*60}\n")

        return resolved_count

    def update_strategy_stats(self):
        """Update strategy performance statistics"""
        cursor = self.db.cursor(dictionary=True)

        # Get all strategy/exit combinations
        cursor.execute("""
            SELECT DISTINCT s.strategy, s.timeframe, o.exit_strategy
            FROM rapid_signals s
            JOIN rapid_outcomes o ON s.signal_id = o.signal_id
        """)
        combinations = cursor.fetchall()

        for combo in combinations:
            strategy = combo['strategy']
            timeframe = combo['timeframe']
            exit_strategy = combo['exit_strategy']

            # Calculate stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN outcome = 'EXPIRED' THEN 1 ELSE 0 END) as expired,
                    SUM(pnl_pct) as total_pnl_pct,
                    SUM(pnl_usd) as total_pnl_usd,
                    AVG(pnl_pct) as avg_pnl_pct,
                    STDDEV(pnl_pct) as stddev_pnl,
                    AVG(duration_minutes) as avg_duration
                FROM rapid_outcomes o
                JOIN rapid_signals s ON o.signal_id = s.signal_id
                WHERE s.strategy = %s AND s.timeframe = %s AND o.exit_strategy = %s
            """, (strategy, timeframe, exit_strategy))

            stats = cursor.fetchone()

            if stats['total_trades'] > 0:
                win_rate = (stats['wins'] / stats['total_trades']) * 100

                # Calculate profit factor
                cursor.execute("""
                    SELECT
                        SUM(CASE WHEN pnl_usd > 0 THEN pnl_usd ELSE 0 END) as total_wins_usd,
                        SUM(CASE WHEN pnl_usd < 0 THEN ABS(pnl_usd) ELSE 0 END) as total_losses_usd
                    FROM rapid_outcomes o
                    JOIN rapid_signals s ON o.signal_id = s.signal_id
                    WHERE s.strategy = %s AND s.timeframe = %s AND o.exit_strategy = %s
                """, (strategy, timeframe, exit_strategy))

                pf_data = cursor.fetchone()
                profit_factor = pf_data['total_wins_usd'] / pf_data['total_losses_usd'] if pf_data['total_losses_usd'] > 0 else 0

                # Calculate Sharpe ratio
                sharpe_ratio = stats['avg_pnl_pct'] / stats['stddev_pnl'] if stats['stddev_pnl'] and stats['stddev_pnl'] > 0 else 0

                # Determine status
                if stats['total_trades'] >= 100:
                    if win_rate >= 60 and profit_factor >= 1.5 and sharpe_ratio >= 1.2:
                        status = 'PROMOTED'
                    elif win_rate < 40 or profit_factor < 0.8:
                        status = 'ELIMINATED'
                    else:
                        status = 'TESTING'
                elif stats['total_trades'] >= 50:
                    if win_rate < 40 or profit_factor < 0.8:
                        status = 'ELIMINATED'
                    else:
                        status = 'TESTING'
                else:
                    status = 'TESTING'

                # Insert or update stats
                cursor.execute("""
                    INSERT INTO rapid_strategy_stats
                    (strategy, timeframe, exit_strategy, total_trades, wins, losses, expired,
                     win_rate, profit_factor, sharpe_ratio, total_pnl_pct, total_pnl_usd,
                     avg_pnl_pct, avg_duration_minutes, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        total_trades = VALUES(total_trades),
                        wins = VALUES(wins),
                        losses = VALUES(losses),
                        expired = VALUES(expired),
                        win_rate = VALUES(win_rate),
                        profit_factor = VALUES(profit_factor),
                        sharpe_ratio = VALUES(sharpe_ratio),
                        total_pnl_pct = VALUES(total_pnl_pct),
                        total_pnl_usd = VALUES(total_pnl_usd),
                        avg_pnl_pct = VALUES(avg_pnl_pct),
                        avg_duration_minutes = VALUES(avg_duration_minutes),
                        status = VALUES(status)
                """, (
                    strategy, timeframe, exit_strategy, stats['total_trades'],
                    stats['wins'], stats['losses'], stats['expired'],
                    win_rate, profit_factor, sharpe_ratio,
                    stats['total_pnl_pct'], stats['total_pnl_usd'],
                    stats['avg_pnl_pct'], stats['avg_duration'],
                    status
                ))

        self.db.commit()
        print("✅ Updated strategy statistics")


def main():
    validator = FastValidator()

    # Load signals from JSON if exists
    validator.load_signals_from_json()

    # Validate active signals
    validator.validate_active_signals()

    # Update stats
    validator.update_strategy_stats()


if __name__ == '__main__':
    main()
