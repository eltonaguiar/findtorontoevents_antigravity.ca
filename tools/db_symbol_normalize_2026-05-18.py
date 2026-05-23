"""One-shot: backup at_raw_picks, verify, then normalize symbol formats.

Per reports/RESOLUTION_PIPELINE_FIX_PLAN_2026-05-18.md Defect 1.
Passwords come from the process env (DB_PASS_STOCKS / DB_PASS_BACKUPS) — the
caller refreshes them from the Windows registry first. Nothing is printed that
reveals a credential.

Safety: full table backup + row-count verify BEFORE any UPDATE. Aborts hard if
the backup count does not match the source. Backup goes to ejaguiar1_backups if
reachable, else an at_raw_picks_bak_<date> table inside ejaguiar1_stocks.
"""
import os
import re
import sys
import time

import pymysql

HOST = "mysql.50webs.com"
BAK_NAME = "stocks__at_raw_picks_bak_20260518"
SELF_BAK_NAME = "at_raw_picks_bak_20260518"

FX_PAIRS = (
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD", "USDCHF",
    "EURJPY", "GBPJPY", "AUDJPY", "EURGBP", "CADJPY", "NZDJPY", "AUDNZD",
    "USDZAR", "USDMXN", "NZDCHF", "CADCHF", "ZARJPY", "NOKJPY",
)


def _conn(user, pw, db):
    last = None
    for _ in range(4):
        try:
            return pymysql.connect(
                host=HOST, user=user, password=pw, database=db,
                connect_timeout=25, read_timeout=180, write_timeout=180,
            )
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(4)
    raise last


def main():
    pw_s = os.environ.get("DB_PASS_STOCKS")
    pw_b = os.environ.get("DB_PASS_BACKUPS")
    if not pw_s:
        print("ABORT: DB_PASS_STOCKS not in env")
        return 2

    cs = _conn("ejaguiar1_stocks", pw_s, "ejaguiar1_stocks")
    scur = cs.cursor()
    scur.execute("SHOW CREATE TABLE at_raw_picks")
    ddl = scur.fetchone()[1]
    scur.execute("SELECT COUNT(*) FROM at_raw_picks")
    src_n = scur.fetchone()[0]
    print(f"source at_raw_picks rows: {src_n}")

    scur.execute("SELECT * FROM at_raw_picks LIMIT 0")
    cols = [d[0] for d in scur.description]
    collist = ",".join("`" + c + "`" for c in cols)

    # --- backup -----------------------------------------------------------
    bak_conn = None
    bak_cur = None
    bak_table = None
    bak_db = None
    if pw_b:
        try:
            bak_conn = _conn("ejaguiar1_backups", pw_b, "ejaguiar1_backups")
            bak_cur = bak_conn.cursor()
            bak_table = BAK_NAME
            bak_db = "ejaguiar1_backups"
        except Exception as exc:  # noqa: BLE001
            print(f"ejaguiar1_backups unreachable ({str(exc)[:60]}) "
                  f"-> backing up inside ejaguiar1_stocks instead")
    if bak_conn is None:
        bak_conn = cs
        bak_cur = scur
        bak_table = SELF_BAK_NAME
        bak_db = "ejaguiar1_stocks"

    bak_cur.execute("SHOW TABLES LIKE %s", (bak_table,))
    if bak_cur.fetchone():
        bak_cur.execute(f"SELECT COUNT(*) FROM `{bak_table}`")
        existing = bak_cur.fetchone()[0]
        if existing == src_n:
            print(f"backup {bak_db}.{bak_table} already exists, count matches "
                  f"({existing}) — reusing")
        else:
            print(f"ABORT: backup {bak_table} exists with {existing} rows "
                  f"!= source {src_n}; pick a new name manually")
            return 3
    else:
        ddl_bak = re.sub(r"AUTO_INCREMENT=\d+", "", ddl).replace(
            "CREATE TABLE `at_raw_picks`",
            "CREATE TABLE `" + bak_table + "`", 1,
        )
        # A backup table needs no foreign keys — strip FK constraint lines
        # (the referenced tables do not exist in the backups DB).
        ddl_bak = re.sub(
            r",?\n\s*(CONSTRAINT[^\n]*?)?FOREIGN KEY[^\n]*", "", ddl_bak)
        # repair any dangling comma left immediately before the closing paren
        ddl_bak = re.sub(r",(\s*\n\s*\))", r"\1", ddl_bak)
        bak_cur.execute(ddl_bak)
        bak_conn.commit()
        ph = ",".join(["%s"] * len(cols))
        ins = f"INSERT INTO `{bak_table}` ({collist}) VALUES ({ph})"
        # read source via a SEPARATE cursor so it does not collide with
        # bak_cur when both point at the same connection
        rcur = cs.cursor()
        rcur.execute(f"SELECT {collist} FROM at_raw_picks")
        copied = 0
        while True:
            rows = rcur.fetchmany(2500)
            if not rows:
                break
            bak_cur.executemany(ins, rows)
            bak_conn.commit()
            copied += len(rows)
        rcur.close()
        print(f"backup copied: {copied} rows -> {bak_db}.{bak_table}")

    bak_cur.execute(f"SELECT COUNT(*) FROM `{bak_table}`")
    bak_n = bak_cur.fetchone()[0]
    if bak_n != src_n:
        print(f"ABORT: backup verify FAILED — backup {bak_n} != source {src_n}")
        return 4
    print(f"BACKUP VERIFIED: {bak_db}.{bak_table} = {bak_n} rows (matches source)")

    # --- normalization UPDATEs (only after verified backup) ---------------
    scur.execute(
        "UPDATE at_raw_picks SET asset_class='FUTURES' "
        "WHERE symbol LIKE '%%=F' AND asset_class<>'FUTURES'"
    )
    n_fut = scur.rowcount
    scur.execute(
        "UPDATE at_raw_picks SET asset_class='FOREX' "
        "WHERE symbol LIKE '%%=X' AND asset_class<>'FOREX'"
    )
    n_fx_cls = scur.rowcount
    in_list = ",".join(["%s"] * len(FX_PAIRS))
    scur.execute(
        "UPDATE at_raw_picks SET symbol=CONCAT(symbol,'=X') "
        "WHERE asset_class='FOREX' AND symbol NOT LIKE '%%=X' "
        "AND symbol NOT LIKE '%%=F' AND symbol IN (" + in_list + ")",
        FX_PAIRS,
    )
    n_fx_sym = scur.rowcount
    cs.commit()
    print(f"UPDATE 1 (=F -> FUTURES): {n_fut} rows")
    print(f"UPDATE 2 (=X -> FOREX): {n_fx_cls} rows")
    print(f"UPDATE 3 (bare FOREX -> =X): {n_fx_sym} rows")

    # --- post verify ------------------------------------------------------
    scur.execute("SELECT COUNT(*) FROM at_raw_picks")
    post_n = scur.fetchone()[0]
    scur.execute("SELECT COUNT(*) FROM at_raw_picks WHERE symbol LIKE '%%=F' "
                 "AND asset_class<>'FUTURES'")
    leftover_f = scur.fetchone()[0]
    scur.execute("SELECT COUNT(*) FROM at_raw_picks WHERE asset_class='FOREX' "
                 "AND symbol IN (" + in_list + ")", FX_PAIRS)
    leftover_bare = scur.fetchone()[0]
    print(f"POST-VERIFY: total rows {post_n} (was {src_n} — must be equal: "
          f"{'OK' if post_n == src_n else 'MISMATCH'})")
    print(f"POST-VERIFY: leftover =F-not-FUTURES {leftover_f} (want 0)")
    print(f"POST-VERIFY: leftover bare-FOREX {leftover_bare} (want 0)")

    if bak_conn is not cs:
        bak_conn.close()
    cs.close()
    print("DONE — normalization complete; backup retained at "
          f"{bak_db}.{bak_table}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
