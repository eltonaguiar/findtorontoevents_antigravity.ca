#!/usr/bin/env python3
"""Check schema of audit_trail.db.
Usage: python check_schema.py [--db PATH]"""
import argparse
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser(description="Check schema of audit_trail.db")
parser.add_argument("--db", default=None, help="Path to audit_trail.db (default: audit_trail/data/audit_trail.db)")
args = parser.parse_args()

if args.db:
    db_path = args.db
else:
    db_path = str(Path(__file__).resolve().parent / "data" / "audit_trail.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(raw_picks);")
print(cursor.fetchall())
conn.close()
