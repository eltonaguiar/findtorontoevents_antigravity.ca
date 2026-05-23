"""
Ghost-pattern sweep across ejaguiar1_stocks MySQL DB.
Read-only. Skips the 5 already-known cohorts and hunts for NEW patterns.

Usage: python tools/ghost_sweep_2026_05_08.py [phase]
  phase=discover  -> emit candidate tables to stdout
  phase=sweep     -> run pattern checks on candidates
  phase=all       -> default; both
"""
import json
import os
import sys
import time
import traceback
from collections import defaultdict
from contextlib import contextmanager

import pymysql


def _db_creds():
    raw = os.environ.get("DB_PASSWORDS_JSON")
    if not raw and os.path.exists(".env.dbpw"):
        raw = open(".env.dbpw").read()
    if not raw:
        raise SystemExit("DB_PASSWORDS_JSON not set — see docs/db_remediation.md")
    return json.loads(raw)


DB_HOST = "mysql.50webs.com"
DB_USER = "ejaguiar1_stocks"
DB_PASS = _db_creds()["stocks"]
DB_NAME = "ejaguiar1_stocks"

# Already-known ghosts -- skip pattern checks (we still discover them, just don't re-flag)
KNOWN_TABLE_GHOSTS = {
    "bt_backtest_trades": [
        "quan_engine MATICUSDT LONG @ pnl=-15.0 (217k rows)",
        "meta_strategy template @ pnl in {+5,-3} (~1.6M rows)",
        "KIMI_signal_tracker ETH/BTC LONG multi-TP",
        "irb_hoffman ADAUSDT SHORT 50/50 split @ {-1.78,+30.30}",
        "funding_rate_carry ROBOUSDT LONG pnl=-99.26 (566 rows)",
    ],
    "at_raw_picks": ["1525/1537 MATIC rows are quan_engine ghosts"],
    "goldmine_cursor_predictions": ["hardcoded +5/-3 PnL"],
    "meme_signals": ["synthetic training fixture (PEPE/PEPE2)"],
}

PNL_COL_CANDIDATES = [
    "pnl_pct", "pnl_percent", "pnlpct", "pnl", "pnl_usd", "pnl_dollars",
    "profit_pct", "profit_percent", "profit", "return_pct", "return_percent",
    "result_pct", "result", "outcome_pct", "outcome",
    "realized_pnl", "realized_pnl_pct", "realized_pct", "net_pnl",
]
SYMBOL_COL_CANDIDATES = ["symbol", "ticker", "pair", "asset", "base", "instrument"]
STRAT_COL_CANDIDATES = ["strategy", "algorithm", "source", "system", "engine", "method", "model", "source_system", "strategy_name", "algo"]
DIR_COL_CANDIDATES = ["direction", "side", "signal", "trade_side", "trade_direction"]
ENTRY_COL_CANDIDATES = ["entry_price", "entry", "open_price", "fill_price"]
TS_COL_CANDIDATES = ["created_at", "createdAt", "timestamp", "ts", "inserted_at", "insert_ts", "created_ts"]


def conn():
    return pymysql.connect(
        host=DB_HOST, port=3306, user=DB_USER, password=DB_PASS,
        database=DB_NAME, connect_timeout=15, read_timeout=60,
        charset="utf8mb4", autocommit=True,
    )


@contextmanager
def cursor(label=""):
    c = conn()
    try:
        with c.cursor(pymysql.cursors.DictCursor) as cur:
            yield cur
    finally:
        c.close()


def discover_candidates():
    """Find tables with rough row count > 100 and at least one PnL-like column."""
    with cursor("discover-cols") as cur:
        cur.execute("""
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
        """, (DB_NAME,))
        rows = cur.fetchall()

    tbl_cols = defaultdict(list)
    for r in rows:
        tbl_cols[r["TABLE_NAME"]].append((r["COLUMN_NAME"].lower(), r["COLUMN_NAME"], r["DATA_TYPE"]))

    # All tables with row counts (approx from information_schema, then refined)
    with cursor("discover-rows") as cur:
        cur.execute("""
            SELECT TABLE_NAME, TABLE_ROWS
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
        """, (DB_NAME,))
        approx = {r["TABLE_NAME"]: int(r["TABLE_ROWS"] or 0) for r in cur.fetchall()}

    candidates = []
    for tbl, cols in tbl_cols.items():
        lower = {c[0] for c in cols}
        pnl_col = next((orig for low, orig, _ in cols if low in PNL_COL_CANDIDATES), None)
        sym_col = next((orig for low, orig, _ in cols if low in SYMBOL_COL_CANDIDATES), None)
        strat_col = next((orig for low, orig, _ in cols if low in STRAT_COL_CANDIDATES), None)
        dir_col = next((orig for low, orig, _ in cols if low in DIR_COL_CANDIDATES), None)
        entry_col = next((orig for low, orig, _ in cols if low in ENTRY_COL_CANDIDATES), None)
        ts_col = next((orig for low, orig, _ in cols if low in TS_COL_CANDIDATES), None)

        approx_rows = approx.get(tbl, 0)
        # Always include these specifically requested probe tables even without PnL col
        explicit_probes = {
            "lm_signals", "rapid_signals", "at_consensus_picks", "alpha_picks",
            "stock_picks", "simulation_grid", "fxp_pair_picks", "cr_pair_picks",
            "lm_arena_bets",
        }
        is_probe = tbl in explicit_probes or tbl.startswith(("crypto_", "KIMI_GOLDMINE_", "gm_"))

        if approx_rows < 100 and not is_probe:
            continue
        if pnl_col is None and not is_probe:
            continue

        candidates.append({
            "table": tbl,
            "approx_rows": approx_rows,
            "pnl_col": pnl_col,
            "sym_col": sym_col,
            "strat_col": strat_col,
            "dir_col": dir_col,
            "entry_col": entry_col,
            "ts_col": ts_col,
            "is_probe": is_probe,
        })

    candidates.sort(key=lambda r: -r["approx_rows"])
    return candidates


def safe_q(cur, sql, params=()):
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    except Exception as e:
        return {"_err": str(e)[:200]}


def sweep_one(meta):
    tbl = meta["table"]
    findings = {"table": tbl, "approx_rows": meta["approx_rows"], "patterns": [], "errors": []}
    pnl = meta["pnl_col"]
    sym = meta["sym_col"]
    strat = meta["strat_col"]
    dirc = meta["dir_col"]
    entry = meta["entry_col"]
    ts = meta["ts_col"]

    quoted_tbl = f"`{tbl}`"

    try:
        with cursor(f"sweep-{tbl}") as cur:
            # Real row count
            r = safe_q(cur, f"SELECT COUNT(*) AS n FROM {quoted_tbl}")
            if isinstance(r, dict):
                findings["errors"].append(("count", r["_err"]))
                return findings
            real_rows = r[0]["n"]
            findings["real_rows"] = real_rows
            if real_rows < 100:
                findings["skipped"] = "row_count_under_100"
                return findings

            # Pattern 1: constant-pnl cohorts (only if we have pnl_col)
            if pnl:
                # Build group cols dynamically; minimum is pnl alone, plus whatever exists
                group_cols = []
                if strat: group_cols.append(strat)
                if sym: group_cols.append(sym)
                if dirc: group_cols.append(dirc)
                group_cols.append(f"ROUND(`{pnl}`, 4)")
                group_sql = ", ".join(f"`{g}`" if not g.startswith("ROUND") else g for g in group_cols)

                entry_clause = ""
                if entry:
                    entry_clause = f", COUNT(DISTINCT `{entry}`) AS dist_entries"
                else:
                    entry_clause = ", NULL AS dist_entries"

                q = f"""
                    SELECT {group_sql} AS gkey,
                           COUNT(*) AS n
                           {entry_clause}
                    FROM {quoted_tbl}
                    WHERE `{pnl}` IS NOT NULL
                    GROUP BY {group_sql}
                    HAVING COUNT(*) > 100
                    ORDER BY n DESC
                    LIMIT 20
                """
                # The above 'AS gkey' is wrong since multi-col group; rewrite
                select_cols = []
                for g in group_cols:
                    if g.startswith("ROUND"):
                        select_cols.append(g + " AS pnl_round")
                    else:
                        select_cols.append(f"`{g}`")
                select_sql = ", ".join(select_cols)
                q = f"""
                    SELECT {select_sql},
                           COUNT(*) AS n
                           {entry_clause}
                    FROM {quoted_tbl}
                    WHERE `{pnl}` IS NOT NULL
                    GROUP BY {group_sql}
                    HAVING COUNT(*) > 100
                    ORDER BY n DESC
                    LIMIT 20
                """
                rs = safe_q(cur, q)
                if isinstance(rs, dict):
                    findings["errors"].append(("constant_pnl_cohort", rs["_err"]))
                else:
                    cohorts = [dict(r) for r in rs if (r.get("dist_entries") in (None, 0, 1, 2))]
                    # Convert decimals/datetimes
                    for c in cohorts:
                        for k, v in list(c.items()):
                            try: json.dumps(v)
                            except Exception: c[k] = str(v)
                    if cohorts:
                        findings["patterns"].append({
                            "type": "constant_pnl_cohort",
                            "cohorts": cohorts[:10],
                        })

                # Pattern 2: distinct pnl count -- if very low across whole table
                rs = safe_q(cur, f"SELECT COUNT(DISTINCT ROUND(`{pnl}`,4)) AS dpnl FROM {quoted_tbl} WHERE `{pnl}` IS NOT NULL")
                if not isinstance(rs, dict):
                    dpnl = rs[0]["dpnl"]
                    if dpnl is not None and dpnl <= 5 and real_rows > 100:
                        findings["patterns"].append({
                            "type": "fixed_bracket",
                            "distinct_pnl": int(dpnl),
                            "rows": real_rows,
                        })

            # Pattern 3: round-number entry-price bias
            if entry:
                rs = safe_q(cur, f"""
                    SELECT
                      SUM(CASE WHEN `{entry}` = ROUND(`{entry}`,0) THEN 1 ELSE 0 END) AS whole,
                      COUNT(*) AS n
                    FROM {quoted_tbl}
                    WHERE `{entry}` IS NOT NULL
                """)
                if not isinstance(rs, dict) and rs[0]["n"]:
                    n = rs[0]["n"]
                    whole = rs[0]["whole"] or 0
                    pct = whole / n if n else 0
                    if pct > 0.6 and n > 200:
                        findings["patterns"].append({
                            "type": "round_number_entry",
                            "whole_pct": round(pct, 4),
                            "rows": n,
                        })

            # Pattern 4: timestamp clusters
            if ts:
                rs = safe_q(cur, f"""
                    SELECT `{ts}` AS t, COUNT(*) AS n
                    FROM {quoted_tbl}
                    WHERE `{ts}` IS NOT NULL
                    GROUP BY `{ts}`
                    HAVING COUNT(*) > 100
                    ORDER BY n DESC
                    LIMIT 5
                """)
                if not isinstance(rs, dict) and rs:
                    findings["patterns"].append({
                        "type": "timestamp_cluster",
                        "top": [{"t": str(r["t"]), "n": r["n"]} for r in rs],
                    })

            # Pull 3-row sample if any pattern hit
            if findings["patterns"]:
                rs = safe_q(cur, f"SELECT * FROM {quoted_tbl} LIMIT 3")
                if not isinstance(rs, dict):
                    sample = []
                    for r in rs:
                        d = {}
                        for k, v in r.items():
                            try: json.dumps(v); d[k] = v
                            except Exception: d[k] = str(v)
                        sample.append(d)
                    findings["sample"] = sample

    except Exception as e:
        findings["errors"].append(("outer", f"{e}\n{traceback.format_exc()[:400]}"))
    return findings


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    out_dir = "reports"
    os.makedirs(out_dir, exist_ok=True)

    print("Discovering candidate tables...", flush=True)
    candidates = discover_candidates()
    print(f"  found {len(candidates)} candidates", flush=True)
    with open("reports/_ghost_sweep_candidates.json", "w") as f:
        json.dump(candidates, f, indent=2, default=str)

    if phase == "discover":
        return

    print("Sweeping...", flush=True)
    results = []
    t0 = time.time()
    for i, c in enumerate(candidates):
        ts0 = time.time()
        print(f"[{i+1}/{len(candidates)}] {c['table']} (~{c['approx_rows']} rows)...", flush=True)
        try:
            r = sweep_one(c)
            r["elapsed_s"] = round(time.time() - ts0, 2)
            r["meta"] = {k: v for k, v in c.items() if k != "approx_rows"}
            results.append(r)
            if r.get("patterns"):
                print(f"  >> {len(r['patterns'])} pattern(s) flagged", flush=True)
        except Exception as e:
            print(f"  !! exception: {e}", flush=True)
            results.append({"table": c["table"], "fatal_error": str(e)})
        # Save incrementally
        with open("reports/_ghost_sweep_raw.json", "w") as f:
            json.dump(results, f, indent=2, default=str)

    print(f"DONE in {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
