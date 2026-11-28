#!/usr/bin/env python3
"""quarantine_bad_rows.py — quarantine invalid outcome rows, repair invalid brackets.

2026-11-28: the class audit found rows whose recorded numbers cannot describe a
real trade. Inspecting samples showed two DIFFERENT defects that deserve two
different actions, and conflating them would destroy good data:

  * a row whose terminal label contradicts its own PnL is unusable  -> QUARANTINE
  * a row whose PnL and label are fine but whose bracket (TP/SL) sits on the
    wrong side of entry is a bad FIELD, not a bad row              -> NULL the field

Example of the second: KAITOUSDT LONG entry 0.7858, TP 0.8153 (hit, +3.75%),
stop_loss 1.3482 — the stop is 72% ABOVE entry. The trade and its +3.75% are
correct; only the stop is garbage. Quarantining it would throw away a valid
outcome and shift the class win rate for no reason.

QUARANTINE rules — each is an internal contradiction, provable from the row:
  R1 pnl_sentinel      ABS(pnl_pct) >= 999999 — the clamp value writers emit
                       when a PnL computation blew up.
  R3 sign_conflict     a WIN label contradicts the PnL sign: TP_HIT/WON with
                       pnl < 0. A take-profit cannot realise a loss.
                       NOTE: the mirror case (SL_HIT/LOST with pnl > 0) is NOT
                       quarantined — that is exactly what a trailing stop looks
                       like, so it is only reported as a suspect. It is caught
                       by R6 when the stop itself is also invalid.
  R4 nonpositive_exit  terminal row with exit_price <= 0 (no fill price). A NULL
                       exit_price is NOT a defect: plenty of writers store only
                       the realised pnl, and flagging those discarded 2,184
                       otherwise-valid rows during the 2026-11-28 dry run.
  R5 magnitude         ABS(pnl_pct) > 1000 — a >10x move inside one trade; no
                       instrument in these holding windows does that, so the
                       entry price was recorded at the wrong decimal scale.
  R6 stop_out_no_stop  labelled SL_HIT but the stop was on the wrong side of
                       entry, so the stop-out it claims could not have happened.
  R7 scale_vs_ohlcv    an |pnl| > 50% row whose entry or exit is more than 2x
                       away from the real OHLCV close on its own date, so the
                       row was recorded at the wrong decimal scale. Uses the
                       close nearest `created_at` (within 3 days); rows with no
                       OHLCV coverage are reported as unverifiable, never
                       quarantined. This is what separates a genuine +60%
                       equity move (exit == the real close) from a corrupted
                       one (entry 3.6x the real close).

BRACKET repair rules (NULL the field, keep entry/exit/pnl/label):
  B1 bad_stop      LONG/BUY with stop >= entry, SHORT/SELL with stop <= entry
  B2 bad_take_profit  LONG/BUY with tp <= entry, SHORT/SELL with tp >= entry
Nothing is invented: an invalid bracket is removed, never recomputed.

Quarantine = copy the full row to `ejaguiar1_backups.<table>_quarantine_<ts>`,
record it in `ejaguiar1_stocks.data_quarantine`, then NULL `exit_price` and
`pnl_pct` (+ the intrabar_* mirror on at_signal_outcomes). Every aggregate
requires a non-NULL pnl, so the row leaves the scored ledger while staying fully
restorable and auditable. Bracket repairs are snapshotted to
`<table>_bracket_repair_<ts>` and logged the same way.

Deliberately NOT quarantined: rows whose |pnl| is merely large (e.g. TONUSDT
1.238 -> 2.47). The local OHLCV cache covers ~330 symbols and comparing a June
entry to a November close is not a valid test, so "implausible vs external
price" never triggers a mutation here — only internal contradictions do.

Usage:
  python3 tools/quarantine_bad_rows.py                    # dry-run (default)
  python3 tools/quarantine_bad_rows.py --table trading_picks
  python3 tools/quarantine_bad_rows.py --apply
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pymysql  # noqa: E402

from tools.db_env import get_backups_creds, get_stocks_creds  # noqa: E402

LONG_SIDE = ("LONG", "BUY")
SHORT_SIDE = ("SHORT", "SELL")
WIN_LABELS = ("TP_HIT", "WON")
LOSS_LABELS = ("SL_HIT", "LOST")
TERMINAL = WIN_LABELS + LOSS_LABELS + ("TIME_EXIT", "EXPIRED")

# table -> label column + the columns reset when a row is quarantined.
TABLES: dict[str, dict] = {
    "trading_picks": {
        "label": "status",
        "neutralize": ("exit_price", "pnl_pct"),
    },
    "at_signal_outcomes": {
        "label": "outcome",
        "neutralize": (
            "exit_price", "pnl_pct",
            "intrabar_status", "intrabar_pnl_pct",
            "intrabar_ambiguous", "intrabar_resolved_at",
        ),
    },
}

ROW_RULES = {
    "R1_pnl_sentinel": "ABS(pnl_pct) >= 999999 (clamp value from a blown-up PnL calc)",
    "R3_sign_conflict": "WIN label (TP_HIT/WON) with pnl < 0",
    "R4_nonpositive_exit": "terminal row with exit_price <= 0",
    "R5_magnitude": "ABS(pnl_pct) > 1000 (>10x move in one trade = scale corruption)",
    "R6_stop_out_no_stop": "labelled SL_HIT while the stop sat on the wrong side of entry",
    "R7_scale_vs_ohlcv": "|pnl|>50% row whose entry/exit is >2x off the real close on its own date",
}
BRACKET_RULES = {
    "B1_bad_stop": "stop on the wrong side of entry -> stop_loss NULLed",
    "B2_bad_take_profit": "take_profit on the wrong side of entry -> take_profit NULLed",
    "B3_bracket_scale": "bracket more than 100x from entry -> that field NULLed",
}

# ── R7 scale-vs-OHLCV parameters ─────────────────────────────────────────
# Only rows this extreme are candidates, so the price lookup stays bounded and
# a legitimate 1.5x entry drift on a normal row can never trigger a mutation.
R7_MIN_ABS_PNL = 50.0     # percent
R7_MAX_RATIO = 2.0        # entry/exit vs same-date close, either direction
R7_MAX_GAP_DAYS = 3       # require a close this close to created_at
# Bracket sanity: no legitimate take-profit/stop is 100x from its entry.
BRACKET_MAX_RATIO = 100.0
# A row whose prices are off-scale has ALL its prices unusable, not just pnl.
EXTRA_NEUTRALIZE = {
    "R7_scale_vs_ohlcv": ("entry_price", "take_profit", "stop_loss"),
}


def _conn(creds: dict):
    keep = ("host", "user", "password", "database", "port",
            "connect_timeout", "read_timeout")
    kwargs = {k: v for k, v in creds.items() if k in keep}
    kwargs.setdefault("read_timeout", 600)
    return pymysql.connect(**kwargs, cursorclass=pymysql.cursors.DictCursor)


def _in(values) -> str:
    return ",".join(["%s"] * len(values))


def meta_label(table: str) -> str:
    """The terminal-label column for a table (status / outcome)."""
    return TABLES[table]["label"]


def _side_sql(column: str, long_op: str, short_op: str) -> tuple[str, tuple]:
    """`column` on the wrong side of entry for the row's direction."""
    sql = (
        f"((UPPER(COALESCE(direction,'')) IN ({_in(LONG_SIDE)})"
        f"  AND entry_price > 0 AND {column} > 0 AND {column} {long_op} entry_price)"
        f" OR (UPPER(COALESCE(direction,'')) IN ({_in(SHORT_SIDE)})"
        f"  AND entry_price > 0 AND {column} > 0 AND {column} {short_op} entry_price))"
    )
    return sql, tuple(LONG_SIDE) + tuple(SHORT_SIDE)


def _nearest_close(cur, symbol: str, when, max_gap_days: int) -> float | None:
    """Real close nearest `when`, or None when no bar is close enough.

    Both OHLCV tables store the bar time as epoch MILLISECONDS.
    """
    if when is None or not symbol:
        return None
    import datetime as _dt
    if isinstance(when, str):
        try:
            when = _dt.datetime.fromisoformat(when)
        except ValueError:
            return None
    ms = int(when.replace(tzinfo=_dt.timezone.utc).timestamp() * 1000)
    best: float | None = None
    best_gap = None
    for table in ("stock_ohlcv", "crypto_ohlcv"):
        try:
            cur.execute(
                f"SELECT timestamp, close FROM {table} WHERE symbol = %s"
                " ORDER BY ABS(timestamp - %s) LIMIT 1",
                (symbol, ms),
            )
        except Exception:
            continue
        row = cur.fetchone()
        if not row:
            continue
        gap_days = abs(row["timestamp"] - ms) / 86_400_000
        if gap_days <= max_gap_days and (best_gap is None or gap_days < best_gap):
            best, best_gap = float(row["close"]), gap_days
    return best


def detect_scale_outliers(cur, table: str, hits: dict) -> dict:
    """R7: flag |pnl|>50 rows whose recorded prices are off the real scale.

    `hits` is the id-keyed dict built by detect_rows; flagged rows are merged in
    so a row caught by another rule keeps its existing rule list.
    """
    cur.execute(
        f"SELECT id, symbol, {meta_label(table)} AS label, direction,"
        " entry_price, exit_price, stop_loss, take_profit, pnl_pct, created_at"
        " FROM " + table +
        " WHERE pnl_pct IS NOT NULL AND ABS(pnl_pct) > %s",
        (R7_MIN_ABS_PNL,),
    )
    unverifiable = 0
    for r in cur.fetchall():
        close = _nearest_close(cur, str(r.get("symbol") or ""), r.get("created_at"),
                               R7_MAX_GAP_DAYS)
        if not close or close <= 0:
            unverifiable += 1
            continue
        ratios = []
        for field in ("entry_price", "exit_price"):
            val = r.get(field)
            if val:
                v = float(val)
                ratios.append(max(v / close, close / v))
        if ratios and max(ratios) > R7_MAX_RATIO:
            entry = hits.setdefault(r["id"], {**r, "rules": []})
            if "R7_scale_vs_ohlcv" not in entry["rules"]:
                entry["rules"].append("R7_scale_vs_ohlcv")
            entry["ohlcv_close"] = close
            entry["max_ratio"] = round(max(ratios), 2)
    if unverifiable:
        print(f"    unverifiable vs OHLCV (no bar within {R7_MAX_GAP_DAYS}d): "
              f"{unverifiable}")
    return hits


def detect_rows(cur, table: str) -> list[dict]:
    meta = TABLES[table]
    label = meta["label"]
    predicates: dict[str, tuple[str, tuple]] = {
        "R1_pnl_sentinel": ("(ABS(pnl_pct) >= 999999)", ()),
        "R3_sign_conflict": (
            f"(UPPER(COALESCE({label},'')) IN ({_in(WIN_LABELS)}) AND pnl_pct < 0)",
            tuple(WIN_LABELS),
        ),
        "R4_nonpositive_exit": (
            f"(UPPER(COALESCE({label},'')) IN ({_in(TERMINAL)})"
            " AND exit_price <= 0)",
            tuple(TERMINAL),
        ),
        "R5_magnitude": ("(ABS(pnl_pct) > 1000)", ()),
        "R6_stop_out_no_stop": (
            f"(UPPER(COALESCE({label},'')) = 'SL_HIT' AND "
            + _side_sql("stop_loss", ">=", "<=")[0] + ")",
            tuple(LONG_SIDE) + tuple(SHORT_SIDE),
        ),
    }
    hits: dict = {}
    for rule, (pred, params) in predicates.items():
        cur.execute(
            f"SELECT id, symbol, {label} AS label, direction, entry_price,"
            f" exit_price, stop_loss, take_profit, pnl_pct, created_at"
            f" FROM {table} WHERE {pred}",
            params or None,
        )
        for r in cur.fetchall():
            entry = hits.setdefault(r["id"], {**r, "rules": []})
            if rule not in entry["rules"]:
                entry["rules"].append(rule)
    detect_scale_outliers(cur, table, hits)
    return sorted(hits.values(), key=lambda h: str(h["id"]))


def bracket_repairs(cur, table: str) -> list[tuple[str, str, str, tuple]]:
    """(rule, column, where_sql, params) for every bracket-field defect."""
    out: list[tuple[str, str, str, tuple]] = []
    for rule, column, long_op, short_op in (
        ("B1_bad_stop", "stop_loss", ">=", "<="),
        ("B2_bad_take_profit", "take_profit", "<=", ">="),
    ):
        sql, params = _side_sql(column, long_op, short_op)
        out.append((rule, column, sql, params))
    # B3: a bracket more than 100x from entry is not a bracket at all (e.g. a
    # take_profit of 4433 on a token priced 0.00000475). Runs after B1/B2, which
    # may already have NULLed the field.
    for column in ("take_profit", "stop_loss"):
        out.append((
            "B3_bracket_scale",
            column,
            f"(entry_price > 0 AND {column} > 0"
            f" AND {column} > entry_price * {BRACKET_MAX_RATIO})",
            (),
        ))
    return out


def detect_brackets(cur, table: str) -> dict[str, int]:
    """Count rows with an invalid bracket field, per rule."""
    out: dict[str, int] = {}
    for rule, _column, sql, params in bracket_repairs(cur, table):
        cur.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE {sql}", params)
        out[rule] = out.get(rule, 0) + int(cur.fetchone()["n"])
    return out


def clean_ddl(ddl: str, source: str, dest: str, suffix: str) -> str:
    """Make a SHOW CREATE TABLE clone safe to create in the archive schema.

    FOREIGN KEYs are stripped (the referenced table may not exist there —
    errno 1824) and remaining named constraints get a suffix (MySQL 8 requires
    constraint names to be unique per schema, so a second snapshot collides).
    """
    ddl = ddl.replace(f"CREATE TABLE `{source}`", f"CREATE TABLE `{dest}`", 1)
    ddl = re.sub(
        r",?\s*CONSTRAINT `[^`]+` FOREIGN KEY \([^)]*\)"
        r" REFERENCES `[^`]+` \([^)]*\)[^,\n]*",
        "",
        ddl,
    )
    # Constraint suffix must be unique PER SNAPSHOT TABLE, not per run: two
    # snapshots taken in the same run share the timestamp, which collided on
    # 'chk_pnl_sign_coherence_<stamp>' (errno 3822). Hash the destination name.
    tag = hashlib.md5(dest.encode()).hexdigest()[:10]
    ddl = re.sub(
        r"CONSTRAINT `([^`]+)`",
        lambda m: "CONSTRAINT `" + (m.group(1) + "_" + tag)[:60] + "`",
        ddl,
    )
    return ddl


def snapshot(cur, table: str, ids: list, purpose: str, stamp: str) -> str | None:
    """Full-row snapshot of `ids` into ejaguiar1_backups. Returns table name."""
    if not ids:
        return None
    name = f"{table}_{purpose}_{stamp}"[:64]
    bconn = _conn(get_backups_creds())
    try:
        bcur = bconn.cursor()
        cur.execute(f"SHOW CREATE TABLE {table}")
        ddl = clean_ddl(cur.fetchone()["Create Table"], table, name, stamp)
        bcur.execute(f"DROP TABLE IF EXISTS `{name}`")
        bcur.execute(ddl)
        copied = 0
        for i in range(0, len(ids), 400):
            chunk = ids[i:i + 400]
            cur.execute(f"SELECT * FROM {table} WHERE id IN ({_in(chunk)})", chunk)
            cols = [d[0] for d in cur.description]
            payload = cur.fetchall()
            ins = (f"INSERT INTO `{name}` (`" + "`,`".join(cols) + "`) VALUES ("
                   + ",".join(["%s"] * len(cols)) + ")")
            bcur.executemany(ins, [tuple(r[c] for c in cols) for r in payload])
            bconn.commit()
            copied += len(payload)
        bcur.execute(f"SELECT COUNT(*) AS n FROM `{name}`")
        got = int(bcur.fetchone()["n"])
        print(f"  backup: {got:,} rows -> ejaguiar1_backups.{name}"
              f" (expected {len(ids):,}) {'OK' if got == len(ids) else 'MISMATCH'}")
        return name
    finally:
        bconn.close()


def ensure_ledger(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS data_quarantine (
            id BIGINT NOT NULL AUTO_INCREMENT,
            source_table VARCHAR(64) NOT NULL,
            source_id VARCHAR(100) NOT NULL,
            action VARCHAR(24) NOT NULL DEFAULT 'quarantine',
            rules VARCHAR(255) NOT NULL,
            symbol VARCHAR(50),
            label VARCHAR(32),
            direction VARCHAR(16),
            entry_price DECIMAL(24,8),
            exit_price DECIMAL(24,8),
            stop_loss DECIMAL(24,8),
            pnl_pct DECIMAL(18,4),
            backup_table VARCHAR(64),
            row_json LONGTEXT,
            quarantined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_src (source_table, source_id),
            KEY idx_action (action)
        )
        """
    )
    conn.commit()


def _log(conn, table: str, rows: list[dict], action: str, rules: dict, backup_name: str) -> None:
    lcur = conn.cursor()
    for r in rows:
        lcur.execute(
            "INSERT INTO data_quarantine (source_table, source_id, action, rules,"
            " symbol, label, direction, entry_price, exit_price, stop_loss,"
            " pnl_pct, backup_table, row_json)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                table, str(r["id"]), action, ",".join(r["rules"]),
                r.get("symbol"), r.get("label"), r.get("direction"),
                r.get("entry_price"), r.get("exit_price"), r.get("stop_loss"),
                r.get("pnl_pct"), backup_name,
                json.dumps(r, default=str),
            ),
        )
    conn.commit()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Quarantine invalid outcome rows and repair invalid brackets"
                    " (dry-run by default).")
    ap.add_argument("--table", action="append", choices=sorted(TABLES),
                    help="table to scan (repeatable; default: all)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    tables = args.table or sorted(TABLES)

    conn = _conn(get_stocks_creds())
    cur = conn.cursor()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print("=== QUARANTINE (row is unusable) ===")
    for k, v in ROW_RULES.items():
        print(f"  {k:<22} {v}")
    print("=== BRACKET REPAIR (field is unusable, row kept) ===")
    for k, v in BRACKET_RULES.items():
        print(f"  {k:<22} {v}")

    row_hits = {t: detect_rows(cur, t) for t in tables}
    bracket_hits = {t: detect_brackets(cur, t) for t in tables}

    total_rows = sum(len(v) for v in row_hits.values())
    for t in tables:
        cur.execute(f"SELECT COUNT(*) AS n FROM {t}")
        print(f"\n=== {t} ({int(cur.fetchone()['n']):,} rows) ===")
        print(f"  quarantine candidates: {len(row_hits[t]):,}")
        by_rule: dict[str, int] = {}
        for r in row_hits[t]:
            for rule in r["rules"]:
                by_rule[rule] = by_rule.get(rule, 0) + 1
        for rule in sorted(by_rule):
            print(f"    {rule:<22} {by_rule[rule]:>6,}")
        print(f"  bracket repairs: stop_loss={bracket_hits[t]['B1_bad_stop']:,}"
              f"  take_profit={bracket_hits[t]['B2_bad_take_profit']:,}")
        # Reported only, never mutated: a loss label with a positive pnl is what
        # a trailing stop produces. Flagging it would delete real wins.
        cur.execute(
            f"SELECT COUNT(*) AS n FROM {t}"
            f" WHERE UPPER(COALESCE({meta_label(t)},'')) IN ({_in(LOSS_LABELS)})"
            " AND pnl_pct > 0",
            tuple(LOSS_LABELS),
        )
        print(f"  reported, not quarantined: loss label with pnl>0 "
              f"(possible trailing stop) = {int(cur.fetchone()['n']):,}")
        for r in row_hits[t][:25]:
            print(f"    {str(r['id'])[:44]:<44} {str(r['symbol']):<12}"
                  f" {str(r['label']):<9} pnl={r['pnl_pct']}"
                  f" exit={r['exit_price']} {','.join(r['rules'])}")
        if len(row_hits[t]) > 25:
            print(f"    ... {len(row_hits[t]) - 25:,} more")

    if not total_rows and not any(sum(v.values()) for v in bracket_hits.values()):
        print("\nnothing to quarantine or repair")
        return 0

    if not args.apply:
        print(f"\nDRY-RUN (default): {total_rows:,} row(s) would be quarantined,"
              f" {sum(sum(v.values()) for v in bracket_hits.values()):,} bracket field(s)"
              " NULLed. Re-run with --apply to write.")
        return 0

    if total_rows > 5000:
        print(f"\nABORT: {total_rows:,} rows exceeds the 5,000 ceiling — too large"
              " for a silent bulk quarantine", file=sys.stderr)
        return 2

    ensure_ledger(conn)
    report: dict[str, dict] = {}
    print("\n=== APPLY ===")
    for t in tables:
        rows = row_hits[t]
        brackets = bracket_hits[t]
        if not rows and not sum(brackets.values()):
            continue
        print(f"\n[{t}]")
        meta = TABLES[t]

        if rows:
            ids = [r["id"] for r in rows]
            bname = snapshot(cur, t, ids, "quarantine", stamp)
            _log(conn, t, rows, "quarantine", ROW_RULES, bname)
            base_cols = tuple(meta["neutralize"])
            off_scale = tuple(EXTRA_NEUTRALIZE["R7_scale_vs_ohlcv"])
            groups = [
                ([r["id"] for r in rows if "R7_scale_vs_ohlcv" not in r["rules"]],
                 base_cols),
                ([r["id"] for r in rows if "R7_scale_vs_ohlcv" in r["rules"]],
                 base_cols + off_scale),
            ]
            touched = 0
            for group_ids, cols in groups:
                if not group_ids:
                    continue
                sets = ", ".join(f"{c} = NULL" for c in cols)
                for i in range(0, len(group_ids), 200):
                    chunk = group_ids[i:i + 200]
                    cur.execute(f"UPDATE {t} SET {sets} WHERE id IN ({_in(chunk)})",
                                chunk)
                    conn.commit()
                    touched += cur.rowcount or 0
            print(f"  quarantined {touched:,} rows (ledger: data_quarantine)")

        # Bracket repair: NULL each invalid field, set-based, logged.
        for rule, column, sql, params in bracket_repairs(cur, t):
            cur.execute(f"SELECT id, symbol, {meta['label']} AS label, direction,"
                        f" entry_price, exit_price, stop_loss, take_profit, pnl_pct"
                        f" FROM {t} WHERE {sql}", params or None)
            bad = cur.fetchall()
            if not bad:
                continue
            ids = [r["id"] for r in bad]
            logged = [{**r, "rules": [rule]} for r in bad]
            # Distinct purpose per column: reusing one name makes the second
            # CREATE collide on the cloned CHECK-constraint name (errno 3822).
            purpose = f"bracket_repair_{column}"[:40]
            bname = snapshot(cur, t, ids, purpose, stamp)
            _log(conn, t, logged, "nulled_bracket", {rule: BRACKET_RULES[rule]}, bname)
            cur.execute(f"UPDATE {t} SET {column} = NULL WHERE {sql}", params)
            conn.commit()
            print(f"  {rule}: NULLed {cur.rowcount:,} {column} values")

        report[t] = {
            "quarantined": len(rows),
            "bracket_repairs": brackets,
        }

    out = REPO_ROOT / "reports" / f"quarantine_bad_rows_{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated_at": stamp,
        "row_rules": ROW_RULES,
        "bracket_rules": BRACKET_RULES,
        "tables": report,
        "quarantined_rows": {t: r for t, r in row_hits.items() if r},
    }, indent=2, default=str), encoding="utf-8")
    print(f"\nreport: {out}")

    print("\n=== POST-STATE ===")
    left_rows = left_brackets = 0
    for t in tables:
        lr = detect_rows(cur, t)
        lb = detect_brackets(cur, t)
        left_rows += len(lr)
        left_brackets += sum(lb.values())
        print(f"  {t}: {len(lr):,} row(s) matching, {sum(lb.values()):,} bracket(s) invalid")
    print("  OK: clean" if not left_rows and not left_brackets
          else f"  WARNING: {left_rows:,} rows / {left_brackets:,} brackets remain")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
