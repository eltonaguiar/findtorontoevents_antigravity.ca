"""Generate up-to-date markdown DB documentation from schema-baseline.sql.

schema-baseline.sql is the live `SHOW CREATE TABLE` dump of ejaguiar1_stocks
produced by tools/schema_dump.py. Live re-introspection from a dev machine is
blocked by 50webs Remote-MySQL IP whitelisting, so this parses the committed
baseline instead. Writes docs/DB_SCHEMA_stocks_backtests_2026-05-15.md.
"""
import datetime
import re
from pathlib import Path

SRC = Path("schema-baseline.sql")
OUT = Path("docs/DB_SCHEMA_stocks_backtests_2026-05-15.md")

# ejaguiar1_backtests holds these tables, migrated from ejaguiar1_stocks
# (see tools/migrate_backtests_to_backtests_db.py DEFAULT_TABLES).
BACKTESTS_TABLES = {
    "bt_backtest_trades", "bt_backtest_runs", "backtest_trades",
    "backtest_results", "at_large_backtest_results", "at_incubator_backtest_results",
}

text = SRC.read_text(encoding="utf-8", errors="replace")
# split on each CREATE TABLE block
blocks = re.split(r"(?=^CREATE TABLE )", text, flags=re.MULTILINE)

tables: list[tuple[str, list[str]]] = []
for b in blocks:
    m = re.match(r"CREATE TABLE `([^`]+)`", b)
    if not m:
        continue
    name = m.group(1)
    cols = re.findall(r"^\s*`([^`]+)`\s+([^\n,]+?)(?:,|\n\) )", b, flags=re.MULTILINE)
    tables.append((name, cols))

tables.sort(key=lambda t: t[0].lower())

# group by prefix before first underscore
groups: dict[str, list] = {}
for name, cols in tables:
    pfx = name.split("_")[0] if "_" in name else name
    groups.setdefault(pfx, []).append((name, cols))

today = datetime.date(2026, 5, 15).isoformat()
L: list[str] = [
    "# MySQL Schema — ejaguiar1_stocks & ejaguiar1_backtests",
    "",
    f"_Last updated {today}_",
    "",
    "Host: `mysql.50webs.com:3306`. Source of truth: `schema-baseline.sql` "
    "(live `SHOW CREATE TABLE` dump via `tools/schema_dump.py`). Live "
    "re-introspection from a dev host is blocked by 50webs Remote-MySQL IP "
    "whitelisting — re-run `tools/schema_dump.py` from a CI runner to refresh.",
    "",
    "## Databases",
    "",
    f"- **`ejaguiar1_stocks`** — primary trading/audit DB, **{len(tables)} tables**.",
    "- **`ejaguiar1_backtests`** — backtest-heavy tables split out of "
    "`ejaguiar1_stocks` (see `tools/migrate_backtests_to_backtests_db.py`): "
    + ", ".join(f"`{t}`" for t in sorted(BACKTESTS_TABLES)) + ".",
    "",
    "## Table groups (`ejaguiar1_stocks`)",
    "",
]
for pfx in sorted(groups, key=str.lower):
    L.append(f"- `{pfx}_*` — {len(groups[pfx])} tables")
L.append("")
L.append("## Tables")
L.append("")
for pfx in sorted(groups, key=str.lower):
    L.append(f"### `{pfx}_*`")
    L.append("")
    for name, cols in sorted(groups[pfx], key=lambda t: t[0].lower()):
        tag = " _(also in ejaguiar1_backtests)_" if name in BACKTESTS_TABLES else ""
        L.append(f"#### `{name}`{tag}")
        L.append("")
        L.append("| Column | Type |")
        L.append("|---|---|")
        for col, ctype in cols:
            L.append(f"| {col} | {ctype.strip()} |")
        L.append("")

OUT.write_text("\n".join(L), encoding="utf-8")
print(f"WROTE {OUT}  ({len(tables)} tables, {OUT.stat().st_size:,} bytes)")
