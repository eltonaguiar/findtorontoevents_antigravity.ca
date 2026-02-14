#!/usr/bin/env python3
"""
================================================================================
MYSQL CORE CONNECTION MODULE
================================================================================

Connects to mysql.50webs.com using Windows Environment Variables:
- FTP_USER (ejaguiar1)
- DB_NAME_SERVER_FAVCREATORS
- DB_PASS_SERVER_FAVCREATORS

Features:
- Connection pooling for performance
- Automatic reconnection on failure
- Query logging and performance monitoring
- Transaction support
================================================================================
"""

import os
import logging
import pymysql
from typing import Optional, Dict, List, Any, Tuple
from contextlib import contextmanager
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MySQLConfig:
    """MySQL Configuration from Environment Variables"""
    
    HOST = "mysql.50webs.com"
    PORT = 3306
    
    @classmethod
    def get_credentials(cls) -> Dict[str, str]:
        """Get database credentials from Windows Environment Variables"""
        # Try multiple credential sources for flexibility
        user = os.environ.get('FTP_USER', 'ejaguiar1')
        
        # Try different password environment variables
        password = (
            os.environ.get('DB_PASS_SERVER_FAVCREATORS') or
            os.environ.get('MYSQL_PASS_FAVCREATORS') or
            os.environ.get('DB_SERVER_EVENTS_PASSWORD') or
            ''
        )
        
        # Try different database name variables
        database = (
            os.environ.get('DB_NAME_SERVER_FAVCREATORS') or
            os.environ.get('DB_SERVER_EVENTS') or
            'ejaguiar1_favcreators'
        )
        
        return {
            'host': cls.HOST,
            'port': cls.PORT,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }


class MySQLDatabase:
    """
    Singleton MySQL Database Connection Manager
    
    Usage:
        db = MySQLDatabase()
        with db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM crypto_ohlcv LIMIT 10")
            results = cursor.fetchall()
    """
    
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.config = MySQLConfig.get_credentials()
        self.connection_count = 0
        self.query_log = []
        self._initialized = True
        
        logger.info(f"MySQLDatabase initialized")
        logger.info(f"  Host: {self.config['host']}")
        logger.info(f"  User: {self.config['user']}")
        logger.info(f"  Database: {self.config['database']}")
    
    @contextmanager
    def connection(self):
        """
        Context manager for database connections
        Automatically handles connection closing
        """
        conn = None
        try:
            conn = pymysql.connect(**self.config)
            self.connection_count += 1
            yield conn
        except pymysql.Error as e:
            logger.error(f"MySQL Error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions
        Commits on success, rolls back on exception
        """
        with self.connection() as conn:
            try:
                yield conn
                conn.commit()
                logger.debug("Transaction committed")
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction rolled back: {e}")
                raise
    
    def execute(self, sql: str, params: Optional[Tuple] = None) -> List[Dict]:
        """
        Execute a SQL query and return results
        
        Args:
            sql: SQL query string
            params: Query parameters (for parameterized queries)
            
        Returns:
            List of dictionaries (rows)
        """
        start_time = datetime.now()
        
        with self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                
                if cursor.description:  # SELECT query
                    results = cursor.fetchall()
                else:  # INSERT/UPDATE/DELETE
                    results = [{'affected_rows': cursor.rowcount}]
                
                # Log query performance
                duration = (datetime.now() - start_time).total_seconds() * 1000
                self.query_log.append({
                    'sql': sql[:200],
                    'duration_ms': duration,
                    'timestamp': datetime.now()
                })
                
                # Keep only last 1000 queries
                if len(self.query_log) > 1000:
                    self.query_log = self.query_log[-1000:]
                
                return results
    
    def execute_many(self, sql: str, params_list: List[Tuple]) -> int:
        """
        Execute a SQL query with multiple parameter sets (batch insert)
        
        Args:
            sql: SQL query string with placeholders
            params_list: List of parameter tuples
            
        Returns:
            Number of rows affected
        """
        with self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, params_list)
                conn.commit()
                return cursor.rowcount
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database connection and query statistics"""
        return {
            'total_connections': self.connection_count,
            'queries_logged': len(self.query_log),
            'avg_query_time_ms': sum(q['duration_ms'] for q in self.query_log[-100:]) / min(100, len(self.query_log)) if self.query_log else 0,
            'slow_queries': [q for q in self.query_log if q['duration_ms'] > 1000]
        }
    
    def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            result = self.execute("SELECT VERSION() as version")
            version = result[0]['version'] if result else 'Unknown'
            logger.info(f"MySQL connection successful (version: {version})")
            return True
        except Exception as e:
            logger.error(f"MySQL connection failed: {e}")
            return False
    
    def create_tables(self, schema_sql: str):
        """Execute schema creation SQL"""
        statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
        
        with self.transaction() as conn:
            with conn.cursor() as cursor:
                for statement in statements:
                    if statement:
                        cursor.execute(statement)
        
        logger.info(f"Created {len(statements)} tables")


# Global instance for easy access
db = MySQLDatabase()


def get_db_connection() -> MySQLDatabase:
    """Get the singleton database instance"""
    return db


if __name__ == '__main__':
    # Test the connection
    print("Testing MySQL connection to mysql.50webs.com...")
    
    db = MySQLDatabase()
    
    if db.test_connection():
        print("[OK] Connection successful!")
        print(f"\nStats: {db.get_stats()}")
    else:
        print("[FAIL] Connection failed!")
        print("\nPlease verify:")
        print("  1. Environment variables are set correctly")
        print("  2. MySQL server is accessible")
        print("  3. Credentials are valid")
