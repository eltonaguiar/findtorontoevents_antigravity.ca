#!/usr/bin/env python3
"""
================================================================================
UNIFIED TRADING DATABASE INTERFACE
================================================================================

Single interface to rule them all:
- Automatically routes queries to correct database
- Unified API for all asset classes (crypto, stocks, forex, meme coins)
- Pattern matching with caching
- ML model registry integration
- Zero-config usage - just call methods

Usage:
    from unified_interface import TradingDB
    
    db = TradingDB()
    
    # Store OHLCV data (auto-routes to correct DB)
    db.save_ohlcv('BTC', '1h', timestamp, open, high, low, close, volume)
    
    # Query patterns
    patterns = db.find_patterns('BTC', 'bull_flag', min_confidence=0.8)
    
    # Save ML model
    db.register_model('xgboost_v1', version='1.0', accuracy=0.85)
================================================================================
"""

import json
import hashlib
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from functools import lru_cache

from multi_db_manager import manager


class TradingDB:
    """
    Unified interface for all trading databases
    
    Routes data to appropriate backend:
    - Crypto/Meme coins -> ejaguiar1_memecoin
    - Stocks/Penny stocks -> ejaguiar1_stocks  
    - Forex -> ejaguiar1_favcreators
    """
    
    def __init__(self):
        self.manager = manager
        self._connection_cache = {}
        
        # Asset class routing
        self.crypto_symbols = set()
        self.stock_symbols = set()
        self.forex_symbols = set()
        
        self._load_symbol_mappings()
    
    def _load_symbol_mappings(self):
        """Load known symbols from databases"""
        try:
            # Load crypto symbols
            result = self.manager.execute('memecoin', 
                "SELECT symbol FROM crypto_assets")
            self.crypto_symbols = {r['symbol'] for r in result}
            
            # Load stock symbols
            result = self.manager.execute('stocks', 
                "SELECT symbol FROM stock_assets")
            self.stock_symbols = {r['symbol'] for r in result}
            
            # Load forex symbols
            result = self.manager.execute('favcreators', 
                "SELECT symbol FROM forex_pairs")
            self.forex_symbols = {r['symbol'] for r in result}
            
        except Exception as e:
            print(f"Warning: Could not load symbol mappings: {e}")
    
    def _get_db_for_symbol(self, symbol: str) -> str:
        """Determine which database to use for a symbol"""
        symbol = symbol.upper()
        
        if symbol in self.crypto_symbols or self._is_crypto_symbol(symbol):
            return 'memecoin'
        elif symbol in self.stock_symbols or self._is_stock_symbol(symbol):
            return 'stocks'
        elif symbol in self.forex_symbols or self._is_forex_symbol(symbol):
            return 'favcreators'
        else:
            # Default to memecoin for unknown symbols
            return 'memecoin'
    
    def _is_crypto_symbol(self, symbol: str) -> bool:
        """Heuristic: Crypto symbols are typically 3-5 chars"""
        return len(symbol) <= 5 and symbol.isalpha()
    
    def _is_stock_symbol(self, symbol: str) -> bool:
        """Heuristic: Stock symbols vary widely"""
        return len(symbol) <= 5
    
    def _is_forex_symbol(self, symbol: str) -> bool:
        """Heuristic: Forex pairs contain 6 chars (e.g., EURUSD)"""
        return len(symbol) == 6 and symbol.isalpha()
    
    # ============================================
    # OHLCV OPERATIONS
    # ============================================
    
    def save_ohlcv(self, symbol: str, timeframe: str, timestamp: int,
                   open_price: float, high: float, low: float, 
                   close: float, volume: float, source: str = 'api') -> bool:
        """Save OHLCV candlestick data"""
        db = self._get_db_for_symbol(symbol)
        
        sql = """
            INSERT INTO crypto_ohlcv 
            (symbol, timeframe, timestamp, open, high, low, close, volume, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            open=VALUES(open), high=VALUES(high), low=VALUES(low),
            close=VALUES(close), volume=VALUES(volume), source=VALUES(source)
        """
        
        try:
            self.manager.execute(db, sql, 
                (symbol.upper(), timeframe, timestamp, open_price, high, low, close, volume, source))
            return True
        except Exception as e:
            print(f"Error saving OHLCV for {symbol}: {e}")
            return False
    
    def save_ohlcv_batch(self, symbol: str, timeframe: str, 
                         data: List[Tuple]) -> int:
        """
        Batch insert OHLCV data
        
        Args:
            data: List of (timestamp, open, high, low, close, volume) tuples
        """
        db = self._get_db_for_symbol(symbol)
        
        sql = """
            INSERT INTO crypto_ohlcv 
            (symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            open=VALUES(open), high=VALUES(high), low=VALUES(low),
            close=VALUES(close), volume=VALUES(volume)
        """
        
        # Prepare batch params
        params = [(symbol.upper(), timeframe, *row) for row in data]
        
        try:
            with self.manager.connection(db) as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(sql, params)
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            print(f"Error batch saving OHLCV for {symbol}: {e}")
            return 0
    
    def get_ohlcv(self, symbol: str, timeframe: str, 
                  start_time: Optional[int] = None,
                  end_time: Optional[int] = None,
                  limit: int = 1000) -> List[Dict]:
        """Get OHLCV data for a symbol"""
        db = self._get_db_for_symbol(symbol)
        
        sql = """
            SELECT * FROM crypto_ohlcv 
            WHERE symbol = %s AND timeframe = %s
        """
        params = [symbol.upper(), timeframe]
        
        if start_time:
            sql += " AND timestamp >= %s"
            params.append(start_time)
        if end_time:
            sql += " AND timestamp <= %s"
            params.append(end_time)
        
        sql += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        return self.manager.execute(db, sql, tuple(params))
    
    # ============================================
    # SIGNAL OPERATIONS
    # ============================================
    
    def save_signal(self, signal_id: str, symbol: str, signal_type: str,
                    entry_price: float, target_price: Optional[float] = None,
                    stop_loss: Optional[float] = None, 
                    confidence: Optional[float] = None,
                    strategy: Optional[str] = None,
                    metadata: Optional[Dict] = None) -> bool:
        """Save a trading signal"""
        db = self._get_db_for_symbol(symbol)
        
        sql = """
            INSERT INTO crypto_signals 
            (signal_id, symbol, signal_type, entry_price, target_price_1, 
             stop_loss, confidence, strategy, indicators_triggered)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            signal_type=VALUES(signal_type), entry_price=VALUES(entry_price),
            target_price_1=VALUES(target_price_1), stop_loss=VALUES(stop_loss)
        """
        
        try:
            self.manager.execute(db, sql, (
                signal_id, symbol.upper(), signal_type, entry_price,
                target_price, stop_loss, confidence, strategy,
                json.dumps(metadata) if metadata else None
            ))
            return True
        except Exception as e:
            print(f"Error saving signal: {e}")
            return False
    
    def get_active_signals(self, symbol: Optional[str] = None,
                           strategy: Optional[str] = None) -> List[Dict]:
        """Get active trading signals"""
        # Query all databases
        all_signals = []
        
        for db in ['memecoin', 'stocks', 'favcreators']:
            try:
                sql = "SELECT * FROM crypto_signals WHERE status = 'active'"
                params = []
                
                if symbol:
                    sql += " AND symbol = %s"
                    params.append(symbol.upper())
                if strategy:
                    sql += " AND strategy = %s"
                    params.append(strategy)
                
                sql += " ORDER BY created_at DESC"
                
                result = self.manager.execute(db, sql, tuple(params) if params else None)
                all_signals.extend(result)
            except:
                pass  # Table might not exist
        
        return all_signals
    
    def close_signal(self, signal_id: str, exit_price: float,
                     pnl_percent: Optional[float] = None,
                     status: str = 'closed') -> bool:
        """Close a trading signal with result"""
        # Try to find in all databases
        for db in ['memecoin', 'stocks', 'favcreators']:
            try:
                sql = """
                    UPDATE crypto_signals 
                    SET status = %s, exit_price = %s, pnl_percent = %s,
                        updated_at = NOW()
                    WHERE signal_id = %s
                """
                result = self.manager.execute(db, sql, 
                    (status, exit_price, pnl_percent, signal_id))
                if result and result[0].get('affected_rows', 0) > 0:
                    return True
            except:
                pass
        return False
    
    # ============================================
    # PATTERN OPERATIONS
    # ============================================
    
    def save_pattern(self, symbol: str, pattern_type: str, pattern_name: str,
                     timeframe: str, start_ts: int, end_ts: int,
                     confidence: float, price: float,
                     target: Optional[float] = None,
                     stop_loss: Optional[float] = None,
                     embedding: Optional[List[float]] = None) -> bool:
        """Save a detected pattern"""
        db = self._get_db_for_symbol(symbol)
        
        sql = """
            INSERT INTO crypto_patterns 
            (symbol, pattern_type, pattern_name, timeframe, start_timestamp,
             end_timestamp, confidence, price_at_detection, target_price,
             stop_loss, embedding_vector)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            self.manager.execute(db, sql, (
                symbol.upper(), pattern_type, pattern_name, timeframe,
                start_ts, end_ts, confidence, price, target, stop_loss,
                json.dumps(embedding) if embedding else None
            ))
            return True
        except Exception as e:
            print(f"Error saving pattern: {e}")
            return False
    
    @lru_cache(maxsize=100)
    def find_patterns(self, symbol: str, pattern_type: Optional[str] = None,
                      min_confidence: float = 0.7, limit: int = 50) -> List[Dict]:
        """Find patterns for a symbol (cached for performance)"""
        db = self._get_db_for_symbol(symbol)
        
        sql = """
            SELECT * FROM crypto_patterns 
            WHERE symbol = %s AND confidence >= %s
        """
        params = [symbol.upper(), min_confidence]
        
        if pattern_type:
            sql += " AND pattern_type = %s"
            params.append(pattern_type)
        
        sql += " ORDER BY confidence DESC, created_at DESC LIMIT %s"
        params.append(limit)
        
        return self.manager.execute(db, sql, tuple(params))
    
    # ============================================
    # ML MODEL OPERATIONS
    # ============================================
    
    def register_model(self, model_name: str, version: str,
                       model_type: str, asset_class: str,
                       accuracy: float, features: List[str],
                       hyperparameters: Optional[Dict] = None,
                       model_path: Optional[str] = None) -> bool:
        """Register a new ML model version"""
        
        sql = """
            INSERT INTO ml_models 
            (model_name, model_version, model_type, asset_class, accuracy,
             features_used, hyperparameters, model_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            accuracy=VALUES(accuracy), features_used=VALUES(features_used)
        """
        
        try:
            self.manager.execute('memecoin', sql, (
                model_name, version, model_type, asset_class, accuracy,
                json.dumps(features), 
                json.dumps(hyperparameters) if hyperparameters else None,
                model_path
            ))
            return True
        except Exception as e:
            print(f"Error registering model: {e}")
            return False
    
    def get_active_model(self, model_name: str) -> Optional[Dict]:
        """Get the active version of a model"""
        sql = """
            SELECT * FROM ml_models 
            WHERE model_name = %s AND is_active = TRUE
            ORDER BY created_at DESC LIMIT 1
        """
        result = self.manager.execute('memecoin', sql, (model_name,))
        return result[0] if result else None
    
    def get_model_performance(self, model_name: str, 
                              days: int = 30) -> Dict[str, Any]:
        """Get performance statistics for a model"""
        sql = """
            SELECT 
                COUNT(*) as total_predictions,
                SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct_predictions,
                AVG(confidence) as avg_confidence,
                AVG(pnl_if_followed) as avg_pnl
            FROM ml_model_performance p
            JOIN ml_models m ON p.model_id = m.id
            WHERE m.model_name = %s
            AND p.prediction_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        """
        
        result = self.manager.execute('memecoin', sql, (model_name, days))
        return result[0] if result else {}
    
    # ============================================
    # MEME COIN SPECIAL OPERATIONS
    # ============================================
    
    def get_meme_coins(self, min_volatility: Optional[float] = None,
                       category: Optional[str] = None,
                       limit: int = 50) -> List[Dict]:
        """Get meme coins with filters"""
        sql = "SELECT * FROM meme_coin_stats WHERE 1=1"
        params = []
        
        if min_volatility:
            sql += " AND volatility_30d >= %s"
            params.append(min_volatility)
        if category:
            sql += " AND meme_category = %s"
            params.append(category)
        
        sql += " ORDER BY volatility_30d DESC LIMIT %s"
        params.append(limit)
        
        return self.manager.execute('memecoin', sql, tuple(params))
    
    # ============================================
    # STATS & MONITORING
    # ============================================
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        stats = {}
        
        for db_name in ['memecoin', 'stocks', 'favcreators']:
            try:
                tables = self.manager.list_tables(db_name)
                table_counts = {}
                
                for table in tables:
                    count = self.manager.get_table_counts(db_name).get(table, 0)
                    table_counts[table] = count
                
                stats[db_name] = {
                    'tables': len(tables),
                    'row_counts': table_counts,
                    'total_rows': sum(table_counts.values())
                }
            except Exception as e:
                stats[db_name] = {'error': str(e)}
        
        return stats
    
    def clear_cache(self):
        """Clear internal caches"""
        self.find_patterns.cache_clear()


# Global instance
_db_instance = None

def get_trading_db() -> TradingDB:
    """Get singleton TradingDB instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = TradingDB()
    return _db_instance


if __name__ == '__main__':
    print("Testing Unified TradingDB Interface")
    print("=" * 50)
    
    db = TradingDB()
    
    # Test database stats
    print("\n[STATS] Database Statistics:")
    stats = db.get_database_stats()
    for db_name, db_stats in stats.items():
        if 'error' in db_stats:
            print(f"\n{db_name}: ERROR - {db_stats['error']}")
        else:
            print(f"\n{db_name}: {db_stats['tables']} tables, {db_stats['total_rows']:,} total rows")
    
    # Test OHLCV save
    print("\n[TEST] Testing OHLCV save...")
    ts = int(datetime.now().timestamp())
    success = db.save_ohlcv('BTC', '1h', ts, 69000, 69500, 68800, 69200, 1500.5)
    print(f"  Save BTC OHLCV: {'[OK]' if success else '[FAIL]'}")
    
    # Test signal save
    print("\n[TEST] Testing signal save...")
    signal_id = f"TEST_{ts}"
    success = db.save_signal(signal_id, 'BTC', 'buy', 69200, 
                             target_price=72000, stop_loss=67000,
                             confidence=0.85, strategy='test')
    print(f"  Save signal: {'[OK]' if success else '[FAIL]'}")
    
    # Test query active signals
    print("\n[LIST] Active signals:")
    signals = db.get_active_signals()
    for sig in signals[:5]:
        print(f"  - {sig['symbol']}: {sig['signal_type']} @ {sig['entry_price']}")
    
    print("\n[OK] TradingDB interface test complete")
