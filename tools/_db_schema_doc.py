"""One-off: introspect ejaguiar1_stocks / ejaguiar1_backtests MySQL schemas and
write up-to-date documentation to docs/DB_SCHEMA_stocks_backtests_2026-05-15.md.

Credentials are read inline (same source as db_sync.py) but NEVER printed.
Output doc contains schema only — no passwords.
"""
import datetime
import os
from pathlib import Path

import pymysql

HOST = "mysql.50webs.com"
PORT = 3306

_DB_STOCKS = os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks")
_DB_BT = os.environ.get("DB_NAME_BACKTESTS", "ejaguiar1_backtests")

# (label, db, user, password) — passwords read from Windows env, never echoed
TARGETS = [
    (_DB_STOCKS, _DB_STOCKS, _DB_STOCKS, os.environ.get("DB_PASS_STOCKS", "")),
    (_DB_BT, _DB_BT, _DB_BT, os.environ.get("DB_PASS_BACKTESTS", "")),
]

OUT = Path("docs/DB_SCHEMA_stocks_backtests_2026-05-15.md")
lines: list[str] = [
    "# MySQL Schema — ejaguiar1_stocks & ejaguiar1_backtests",
    "",
    f"Generated: {datetime.datetime.utcnow().isoformat()}Z · host `mysql.50webs.com:3306`",
    "Source of truth: live `SHOW TABLES` / `DESCRIBE` introspection. Credentials redacted.",
    "",
]

for label, db, user, pw in TARGETS:
    lines.append(f"## `{label}`\n")
    try:
        conn = pymysql.connect(
            host=HOST, port=PORT, user=user, password=pw, database=db,
            connect_timeout=15, read_timeout=30,
        )
    except Exception as e:
        lines.append(f"- **UNREACHABLE** — `{type(e).__name__}: {e}`\n")
        print(f"{label}: UNREACHABLE ({type(e).__name__})")
        continue
    try:
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        tables = [r[0] for r in cur.fetchall()]
        lines.append(f"- {len(tables)} tables\n")
        print(f"{label}: {len(tables)} tables")
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM `{t}`")
                n = cur.fetchone()[0]
            except Exception:
                n = "?"
            cur.execute(f"DESCRIBE `{t}`")
            cols = cur.fetchall()
            lines.append(f"### `{t}`  ({n} rows)\n")
            lines.append("| Column | Type | Null | Key | Default |")
            lines.append("|---|---|---|---|---|")
            for c in cols:
                field, ctype, null, key, default, _extra = (list(c) + [None] * 6)[:6]
                lines.append(f"| {field} | {ctype} | {null} | {key or ''} | {default if default is not None else ''} |")
            lines.append("")
    finally:
        conn.close()

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"WROTE {OUT} ({OUT.stat().st_size:,} bytes)")
