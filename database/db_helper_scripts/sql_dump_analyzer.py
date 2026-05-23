"""Streaming analyzer for phpMyAdmin MySQL dumps.

Built for files too large to load into memory. Walks the dump line-by-line and
extracts:

- database name
- CREATE TABLE blocks (full DDL) per table
- INSERT INTO row counts per table (counts top-level value tuples)
- per-table cumulative INSERT byte size
- N sample row tuples per table

Writes a JSON summary + a Markdown report. Designed for read-only forensic
analysis of dumps from `audit_dashboard/data/*` upstream tables.

Usage:
    python tools/sql_dump_analyzer.py <dump.sql> [--out report.md] [--samples 3]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

CREATE_RE = re.compile(r"^CREATE TABLE `([^`]+)`")
INSERT_RE = re.compile(r"^INSERT INTO `([^`]+)`(?:\s*\([^)]*\))?\s+VALUES\s+")
DB_RE = re.compile(r"^(?:USE|CREATE DATABASE.*) `([^`]+)`")
HOST_RE = re.compile(r"^-- Host:\s*(.+)$")
GEN_RE = re.compile(r"^-- Generation Time:\s*(.+)$")


def split_top_level_tuples(values_blob: str) -> int:
    """Count top-level `(...)` tuples in an INSERT VALUES blob.

    Respects single-quote string escaping (`''` and `\\'`) so commas / parens
    inside string literals are not miscounted as tuple boundaries.
    """
    count = 0
    depth = 0
    in_str = False
    escape = False
    i = 0
    n = len(values_blob)
    while i < n:
        ch = values_blob[i]
        if escape:
            escape = False
        elif ch == "\\" and in_str:
            escape = True
        elif ch == "'":
            # check doubled '' inside string -> escaped quote
            if in_str and i + 1 < n and values_blob[i + 1] == "'":
                i += 2
                continue
            in_str = not in_str
        elif not in_str:
            if ch == "(":
                if depth == 0:
                    pass  # tuple start
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    count += 1
        i += 1
    return count


def first_n_tuples(values_blob: str, n: int) -> List[str]:
    """Return up to n top-level (...) tuples as strings (with parens)."""
    out: List[str] = []
    depth = 0
    in_str = False
    escape = False
    start = -1
    for i, ch in enumerate(values_blob):
        if escape:
            escape = False
            continue
        if in_str:
            if ch == "\\":
                escape = True
            elif ch == "'":
                if i + 1 < len(values_blob) and values_blob[i + 1] == "'":
                    continue
                in_str = False
            continue
        if ch == "'":
            in_str = True
            continue
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and start >= 0:
                out.append(values_blob[start : i + 1])
                if len(out) >= n:
                    return out
    return out


def analyze(path: Path, samples: int = 3) -> Dict:
    size = path.stat().st_size
    print(f"[scan] {path.name} ({size/1e9:.2f} GB)", file=sys.stderr)

    db_name = ""
    host = ""
    generated = ""
    create_blocks: Dict[str, str] = {}
    table_rows: Dict[str, int] = defaultdict(int)
    table_insert_bytes: Dict[str, int] = defaultdict(int)
    table_inserts: Dict[str, int] = defaultdict(int)
    table_samples: Dict[str, List[str]] = defaultdict(list)
    columns_by_table: Dict[str, List[str]] = {}

    in_create = False
    create_table = ""
    create_buf: List[str] = []
    in_insert = False
    insert_table = ""
    insert_buf: List[str] = []
    insert_byte_count = 0

    bytes_seen = 0
    start = time.time()
    last_report = start

    with path.open("rb") as f:
        for raw in f:
            bytes_seen += len(raw)
            try:
                line = raw.decode("utf-8", errors="replace")
            except Exception:
                continue

            now = time.time()
            if now - last_report > 5:
                pct = 100.0 * bytes_seen / size
                rate = bytes_seen / (now - start) / 1e6
                print(
                    f"[scan] {pct:5.1f}%  {bytes_seen/1e9:.2f}GB  {rate:.0f} MB/s  tables={len(create_blocks)}  inserts={sum(table_inserts.values())}",
                    file=sys.stderr,
                )
                last_report = now

            if not host:
                m = HOST_RE.match(line)
                if m:
                    host = m.group(1).strip()
                    continue
            if not generated:
                m = GEN_RE.match(line)
                if m:
                    generated = m.group(1).strip()
                    continue
            if not db_name:
                m = DB_RE.match(line)
                if m:
                    db_name = m.group(1)

            if in_create:
                create_buf.append(line)
                if line.rstrip().endswith(";"):
                    create_blocks[create_table] = "".join(create_buf)
                    cols = re.findall(r"^\s*`([^`]+)`\s+", "".join(create_buf), re.M)
                    if cols:
                        columns_by_table[create_table] = cols
                    in_create = False
                    create_table = ""
                    create_buf = []
                continue

            cm = CREATE_RE.match(line)
            if cm:
                create_table = cm.group(1)
                in_create = True
                create_buf = [line]
                continue

            if in_insert:
                insert_buf.append(line)
                insert_byte_count += len(raw)
                stripped = line.rstrip()
                if stripped.endswith(";"):
                    full = "".join(insert_buf)
                    vidx = full.find("VALUES")
                    blob = full[vidx + len("VALUES"):].strip()
                    if blob.endswith(";"):
                        blob = blob[:-1]
                    row_count = split_top_level_tuples(blob)
                    table_rows[insert_table] += row_count
                    table_inserts[insert_table] += 1
                    table_insert_bytes[insert_table] += insert_byte_count
                    if len(table_samples[insert_table]) < samples:
                        needed = samples - len(table_samples[insert_table])
                        new_samples = first_n_tuples(blob, needed)
                        table_samples[insert_table].extend(new_samples)
                    in_insert = False
                    insert_table = ""
                    insert_buf = []
                    insert_byte_count = 0
                continue

            im = INSERT_RE.match(line)
            if im:
                insert_table = im.group(1)
                in_insert = True
                insert_buf = [line]
                insert_byte_count = len(raw)
                stripped = line.rstrip()
                if stripped.endswith(";"):
                    full = line
                    vidx = full.find("VALUES")
                    blob = full[vidx + len("VALUES"):].strip()
                    if blob.endswith(";"):
                        blob = blob[:-1]
                    row_count = split_top_level_tuples(blob)
                    table_rows[insert_table] += row_count
                    table_inserts[insert_table] += 1
                    table_insert_bytes[insert_table] += insert_byte_count
                    if len(table_samples[insert_table]) < samples:
                        needed = samples - len(table_samples[insert_table])
                        new_samples = first_n_tuples(blob, needed)
                        table_samples[insert_table].extend(new_samples)
                    in_insert = False
                    insert_table = ""
                    insert_buf = []
                    insert_byte_count = 0
                continue

    elapsed = time.time() - start
    return {
        "path": str(path),
        "size_bytes": size,
        "elapsed_sec": round(elapsed, 1),
        "db_name": db_name,
        "host": host,
        "generated": generated,
        "tables": sorted(create_blocks.keys()),
        "create_blocks": create_blocks,
        "columns_by_table": columns_by_table,
        "rows_by_table": dict(table_rows),
        "inserts_by_table": dict(table_inserts),
        "insert_bytes_by_table": dict(table_insert_bytes),
        "samples_by_table": {k: v for k, v in table_samples.items()},
    }


def write_report(summary: Dict, out_md: Path, out_json: Path) -> None:
    out_json.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")

    rows = sorted(
        summary["rows_by_table"].items(), key=lambda kv: kv[1], reverse=True
    )
    total_rows = sum(v for _, v in rows)
    total_tables = len(summary["tables"])

    lines = []
    lines.append(f"# SQL Dump Analysis — {Path(summary['path']).name}\n")
    lines.append(f"- **Path**: `{summary['path']}`")
    lines.append(f"- **Size**: {summary['size_bytes']/1e9:.2f} GB ({summary['size_bytes']:,} bytes)")
    lines.append(f"- **Source host**: `{summary['host']}`")
    lines.append(f"- **Dump generated**: {summary['generated']}")
    lines.append(f"- **Database**: `{summary['db_name'] or '(unspecified)'}`")
    lines.append(f"- **Tables**: {total_tables}")
    lines.append(f"- **Total rows (sum of INSERTs)**: {total_rows:,}")
    lines.append(f"- **Scan time**: {summary['elapsed_sec']}s\n")

    lines.append("## Tables by row count\n")
    lines.append("| # | table | rows | inserts | insert_MB | columns |")
    lines.append("|---|---|---|---|---|---|")
    for i, (tbl, rc) in enumerate(rows, 1):
        ib = summary["insert_bytes_by_table"].get(tbl, 0) / 1e6
        ic = summary["inserts_by_table"].get(tbl, 0)
        col_count = len(summary["columns_by_table"].get(tbl, []))
        lines.append(f"| {i} | `{tbl}` | {rc:,} | {ic:,} | {ib:,.1f} | {col_count} |")
    lines.append("")

    # tables w/o INSERTs (schema-only)
    empty = [t for t in summary["tables"] if t not in summary["rows_by_table"]]
    if empty:
        lines.append("## Empty / schema-only tables\n")
        for t in empty:
            lines.append(f"- `{t}`")
        lines.append("")

    # per-table detail (top 20 by rows)
    lines.append("## Top 20 tables — schema + sample\n")
    for tbl, rc in rows[:20]:
        cols = summary["columns_by_table"].get(tbl, [])
        samples = summary["samples_by_table"].get(tbl, [])
        lines.append(f"### `{tbl}` — {rc:,} rows\n")
        lines.append(f"**columns** ({len(cols)}): {', '.join('`'+c+'`' for c in cols)}")
        ddl = summary["create_blocks"].get(tbl, "")
        if ddl:
            lines.append("\n```sql\n" + ddl.rstrip() + "\n```")
        if samples:
            lines.append("\n**sample rows**:")
            for s in samples:
                clean = s if len(s) < 400 else s[:400] + "…"
                lines.append(f"- `{clean}`")
        lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump", type=Path)
    ap.add_argument("--out-md", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--samples", type=int, default=3)
    args = ap.parse_args()

    out_md = args.out_md or Path("reports") / f"db_analysis_{args.dump.stem.replace(' ','_')}.md"
    out_json = args.out_json or out_md.with_suffix(".json")
    out_md.parent.mkdir(parents=True, exist_ok=True)

    summary = analyze(args.dump, samples=args.samples)
    write_report(summary, out_md, out_json)
    print(f"[done] md={out_md}  json={out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
