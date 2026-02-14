"""
================================================================================
MYSQL DATABASE INFRASTRUCTURE - mysql.50webs.com
================================================================================

Multi-database setup across 3 MySQL databases:

1. ejaguiar1_memecoin (env: MEMECOIN_DB_PASS)
   - Primary crypto/meme coin database
   - Tables: crypto_ohlcv, crypto_signals, crypto_patterns, meme_coin_stats
   - ML model registry

2. ejaguiar1_stocks (stocks)
   - Stocks and penny stocks
   - Tables: stock_ohlcv, stock_signals, penny_stocks
   - Also has crypto_ohlcv for hybrid trading

3. ejaguiar1_favcreators (env: MYSQL_PASS_FAVCREATORS)
   - Forex and overflow
   - Tables: forex_ohlcv, forex_pairs, economic_events

Windows Environment Variables Used:
- FTP_USER=ejaguiar1 (base username)
- Set via environment variables (see .env.example)
================================================================================
"""

from .multi_db_manager import MultiDatabaseManager, manager
from .schema_extensions import SchemaManager
from .unified_interface import TradingDB, get_trading_db

__all__ = [
    'MultiDatabaseManager',
    'manager',
    'SchemaManager',
    'TradingDB',
    'get_trading_db'
]
