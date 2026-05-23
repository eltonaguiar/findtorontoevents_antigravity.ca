#!/usr/bin/env python3
"""
Stream a large MySQL dump and report CREATE TABLE order + approximate row counts
from INSERT batches (counts "),(" tuples plus one per batch).

phpMyAdmin often uses one value tuple per line without "),(" on the INSERT header
line — those tables are undercounted (e.g. algorithms). Huge single-line INSERTs
are counted more accurately. For exact counts, query the live DB or count lines
inside each INSERT block.

Usage:
  python tools/analyze_sql_dump_stats.py "C:/path/to/dump.sql"
"""
from __future__ import annotations

import re
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python tools/analyze_sql_dump_stats.py <dump.sql>", file=sys.stderr)
        return 2
    path = sys.argv[1]
    bt = chr(96)  # backtick
    prefix = "CREATE TABLE " + bt
    tables_order: list[str] = []
    insert_re = re.compile(r"^INSERT INTO " + bt + r"([^`]+)" + bt)

    from collections import defaultdict

    rows_per_table: dict[str, int] = defaultdict(int)
    buf: list[str] = []
    current_insert_table: str | None = None

    def count_insert_rows(chunk: str) -> int:
        """Rows in one INSERT batch: max of ),( delimiters and value lines starting with '('.

        phpMyAdmin often emits VALUES then one tuple per line; ),( may not appear.
        """
        if "VALUES" not in chunk.upper():
            return 0
        n_delim = chunk.count("),(") + 1
        n_paren_lines = 0
        for line in chunk.splitlines():
            s = line.strip()
            if not s:
                continue
            if s.upper().startswith("INSERT "):
                continue
            if s.startswith("("):
                n_paren_lines += 1
        return max(n_delim, n_paren_lines)

    def flush_insert() -> None:
        nonlocal current_insert_table, buf
        if not current_insert_table or not buf:
            buf = []
            return
        chunk = "".join(buf)
        n = count_insert_rows(chunk)
        rows_per_table[current_insert_table] += n
        buf = []
        current_insert_table = None

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith(prefix):
                flush_insert()
                end = line.find(bt, len(prefix))
                name = line[len(prefix) : end] if end > len(prefix) else ""
                if name:
                    tables_order.append(name)
                continue

            m = insert_re.match(line)
            if m:
                flush_insert()
                current_insert_table = m.group(1)
                buf.append(line)
                if line.rstrip().endswith(";"):
                    flush_insert()
                continue

            if current_insert_table is not None:
                buf.append(line)
                if line.rstrip().endswith(";"):
                    flush_insert()

    flush_insert()

    print("tables_found\t%d" % len(tables_order))
    print("table\tapprox_rows")
    for t in tables_order:
        print("%s\t%d" % (t, rows_per_table.get(t, 0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
