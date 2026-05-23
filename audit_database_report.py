#!/usr/bin/env python3
"""
Comprehensive Audit of Trading System Databases
Analyzes SQLite databases to understand stored data structure and content
"""

import sqlite3
import os
from datetime import datetime

# Database paths
DATABASES = {
    "audit_trail": "E:/findtorontoevents_antigravity.ca/data/audit_trail.db",
    "paper_trading": "E:/findtorontoevents_antigravity.ca/paper_trading/data/paper.db",
    "genetic_programmer": "E:/findtorontoevents_antigravity.ca/genome/genetic_programmer.db",
    "mape_evolver": "E:/findtorontoevents_antigravity.ca/genome/mape_evolver.db",
    "ensemble_evolver": "E:/findtorontoevents_antigravity.ca/genome/ensemble_evolver.db",
}

# Key tables to check
KEY_TABLES = [
    "evolved_strategy_picks",
    "evolved_strategies",
    "positions",
    "consensus_picks",
    "raw_picks",
    "gp_strategies",
    "mape_strategies",
    "ensemble_strategies",
    "trades",
    "signals",
    "backtests",
    "performance",
    "metrics",
]


def get_tables(conn):
    """Get list of all tables in database"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]


def get_table_schema(conn, table_name):
    """Get schema for a table"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()


def count_rows(conn, table_name):
    """Count rows in a table"""
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
    except Exception as e:
        return f"Error: {e}"


def sample_rows(conn, table_name, limit=3):
    """Sample rows from a table"""
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        rows = cursor.fetchall()
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        return columns, rows
    except Exception as e:
        return None, f"Error: {e}"


def check_schema_exists(conn, schema_name):
    """Check if a specific schema/table pattern exists"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?", (f"%{schema_name}%",))
    return [row[0] for row in cursor.fetchall()]


def analyze_database(db_name, db_path):
    """Analyze a single database"""
    report = []
    report.append(f"\n{'='*80}")
    report.append(f"DATABASE: {db_name}")
    report.append(f"PATH: {db_path}")
    report.append(f"{'='*80}")
    
    if not os.path.exists(db_path):
        report.append(f"[NOT FOUND] DATABASE DOES NOT EXIST")
        return "\n".join(report)
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Get file size
        file_size = os.path.getsize(db_path)
        report.append(f"[OK] File Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        
        # Get all tables
        tables = get_tables(conn)
        report.append(f"\nTOTAL TABLES: {len(tables)}")
        
        if not tables:
            report.append("   (No tables found - empty database)")
            conn.close()
            return "\n".join(report)
        
        # Analyze each table
        for table in tables:
            report.append(f"\n{'-'*60}")
            report.append(f"TABLE: {table}")
            report.append(f"{'-'*60}")
            
            # Get schema
            schema = get_table_schema(conn, table)
            report.append(f"\n   Schema ({len(schema)} columns):")
            for col in schema:
                col_id, name, col_type, not_null, default, pk = col
                pk_marker = " [PK]" if pk else ""
                null_marker = " NOT NULL" if not_null else ""
                report.append(f"      - {name}: {col_type}{pk_marker}{null_marker}")
            
            # Count rows
            row_count = count_rows(conn, table)
            report.append(f"\n   Row Count: {row_count:,}" if isinstance(row_count, int) else f"\n   Row Count: {row_count}")
            
            # Sample data if rows exist
            if isinstance(row_count, int) and row_count > 0:
                columns, rows = sample_rows(conn, table, limit=2)
                if rows and not isinstance(rows, str):
                    report.append(f"\n   Sample Data (up to 2 rows):")
                    for i, row in enumerate(rows):
                        report.append(f"      Row {i+1}:")
                        for col_name, value in zip(columns, row):
                            # Truncate long values
                            value_str = str(value)
                            if len(value_str) > 100:
                                value_str = value_str[:100] + "..."
                            report.append(f"         {col_name}: {value_str}")
        
        # Check for ejaguiar1_stocks
        ejaguiar_tables = check_schema_exists(conn, "ejaguiar1")
        if ejaguiar_tables:
            report.append(f"\n[FOUND] ejaguiar1_stocks Schema:")
            for t in ejaguiar_tables:
                report.append(f"   - {t}")
        
        conn.close()
        
    except Exception as e:
        report.append(f"[ERROR] {e}")
    
    return "\n".join(report)


def main():
    """Main analysis function"""
    full_report = []
    full_report.append("="*80)
    full_report.append("DATABASE AUDIT REPORT")
    full_report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    full_report.append("="*80)
    
    # Analyze each database
    for db_name, db_path in DATABASES.items():
        report = analyze_database(db_name, db_path)
        full_report.append(report)
    
    # Summary section
    full_report.append(f"\n\n{'='*80}")
    full_report.append("SUMMARY")
    full_report.append(f"{'='*80}")
    
    for db_name, db_path in DATABASES.items():
        full_report.append(f"\n{db_name}:")
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                tables = get_tables(conn)
                total_rows = 0
                for t in tables:
                    count = count_rows(conn, t)
                    if isinstance(count, int):
                        total_rows += count
                conn.close()
                full_report.append(f"   [OK] {len(tables)} tables, ~{total_rows:,} total rows")
            except:
                full_report.append(f"   [WARN] Error reading database")
        else:
            full_report.append(f"   [MISSING] Not found")
    
    output = "\n".join(full_report)
    print(output)
    
    # Save to file
    output_path = "E:/findtorontoevents_antigravity.ca/database_audit_report.txt"
    with open(output_path, 'w') as f:
        f.write(output)
    print(f"\n\nReport saved to: {output_path}")
    
    return output


if __name__ == "__main__":
    main()
