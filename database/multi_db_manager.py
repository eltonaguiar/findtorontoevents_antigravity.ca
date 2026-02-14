#!/usr/bin/env python3
"""
================================================================================
MULTI-DATABASE MANAGER
================================================================================

Manages connections to multiple MySQL databases:
- ejaguiar1_memecoin (meme coins + new crypto tables)
- ejaguiar1_stocks (stocks + new crypto tables)
- ejaguiar1_favcreators (existing - can add crypto prefix tables)

Credentials from environment:
- Uses environment variables for credentials
- ejaguiar1_stocks password = stocks
================================================================================
"""

import os
import pymysql
from typing import Dict, List, Optional
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class DatabaseConfig:
    """Database configuration"""
    name: str
    host: str
    user: str
    password: str
    database: str
    port: int = 3306


class MultiDatabaseManager:
    """
    Manages multiple database connections
    """
    
    def __init__(self):
        self.databases = {}
        self._setup_configs()
    
    def _setup_configs(self):
        """Setup all database configurations"""
        
        # Database 1: MemeCoin (best for crypto/meme coin data)
        self.databases['memecoin'] = DatabaseConfig(
            name='memecoin',
            host='mysql.50webs.com',
            user='ejaguiar1_memecoin',
            password=os.environ.get('MEMECOIN_DB_PASS', ''),
            database='ejaguiar1_memecoin'
        )
        
        # Database 2: Stocks (best for stocks/penny stocks)
        self.databases['stocks'] = DatabaseConfig(
            name='stocks',
            host='mysql.50webs.com',
            user='ejaguiar1_stocks',
            password='stocks',
            database='ejaguiar1_stocks'
        )
        
        # Database 3: FavCreators (existing, use for overflow/forex)
        # Try different credential combinations
        fav_password = (
            os.environ.get('DB_PASS_SERVER_FAVCREATORS') or
            os.environ.get('MYSQL_PASS_FAVCREATORS') or
            os.environ.get('DB_PASS_SERVER_FAVCREATORS', '')
        )
        self.databases['favcreators'] = DatabaseConfig(
            name='favcreators',
            host='mysql.50webs.com',
            user='ejaguiar1',
            password=fav_password,
            database='ejaguiar1_favcreators'
        )
    
    def get_connection(self, db_name: str):
        """Get database connection by name"""
        if db_name not in self.databases:
            raise ValueError(f"Unknown database: {db_name}. Available: {list(self.databases.keys())}")
        
        config = self.databases[db_name]
        return pymysql.connect(
            host=config.host,
            user=config.user,
            password=config.password,
            database=config.database,
            port=config.port,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    @contextmanager
    def connection(self, db_name: str):
        """Context manager for database connection"""
        conn = None
        try:
            conn = self.get_connection(db_name)
            yield conn
        finally:
            if conn:
                conn.close()
    
    def execute(self, db_name: str, sql: str, params: Optional[tuple] = None) -> List[Dict]:
        """Execute SQL on specific database"""
        with self.connection(db_name) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                if cursor.description:
                    return cursor.fetchall()
                return [{'affected_rows': cursor.rowcount}]
    
    def list_tables(self, db_name: str) -> List[str]:
        """List all tables in a database"""
        result = self.execute(db_name, "SHOW TABLES")
        tables = []
        for row in result:
            # Get the first value from each row dict
            tables.append(list(row.values())[0])
        return tables
    
    def get_table_schema(self, db_name: str, table_name: str) -> List[Dict]:
        """Get schema for a specific table"""
        return self.execute(db_name, f"DESCRIBE {table_name}")
    
    def test_all_connections(self) -> Dict[str, bool]:
        """Test all database connections"""
        results = {}
        for name in self.databases:
            try:
                result = self.execute(name, "SELECT VERSION() as version")
                version = result[0]['version'] if result else 'unknown'
                results[name] = True
                print(f"[OK] {name}: Connected (MySQL {version})")
            except Exception as e:
                results[name] = False
                print(f"[FAIL] {name}: Failed - {e}")
        return results
    
    def get_table_counts(self, db_name: str) -> Dict[str, int]:
        """Get row counts for all tables in a database"""
        tables = self.list_tables(db_name)
        counts = {}
        for table in tables:
            try:
                result = self.execute(db_name, f"SELECT COUNT(*) as cnt FROM {table}")
                counts[table] = result[0]['cnt'] if result else 0
            except:
                counts[table] = -1
        return counts


# Global instance
manager = MultiDatabaseManager()


if __name__ == '__main__':
    print("Testing Multi-Database Manager")
    print("=" * 50)
    
    # Test connections
    results = manager.test_all_connections()
    
    print("\nExploring databases...")
    for db_name in manager.databases:
        if results[db_name]:
            print(f"\n📊 {db_name.upper()} Database:")
            tables = manager.list_tables(db_name)
            print(f"   Tables: {', '.join(tables) if tables else '(empty)'}")
            
            # Get row counts
            counts = manager.get_table_counts(db_name)
            for table, count in counts.items():
                print(f"   - {table}: {count:,} rows")
