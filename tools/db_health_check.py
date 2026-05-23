"""DB health check — converged forensic harness for /audit dashboard.

Consolidates 10 high-priority detection queries from three independent audits:
- this session's forensic sweep (F1-F20)
- Kimi-Agent's parallel review (`database/kimi_2026-05-08/FULL_DATABASE_REVIEW.md`)
- Freebuff's dashboard plan (`database/Freebuff_analysis/DB_DASHBOARD_ENHANCEMENT_PLAN.md`)

Output: `audit_dashboard/data/db_health.json` — machine-readable health payload
that feeds:
1. New `audit_dashboard/dashboard_enhancements.js` cards (PnL integrity, ghost
   counter, OPEN bloat, phantom row %, outcome coverage, ML readiness, signal
   tier health)
2. Standalone `audit_dashboard/db_health.html` (Tier 5 stretch in freebuff plan)
3. Discord alerts via existing `tools/swarm/comment_poster.ps1` infrastructure

Run modes:
- `python tools/db_health_check.py` — full check, write JSON + exit
- `python tools/db_health_check.py --quick` — Tier-1 critical checks only (<60s)
- `python tools/db_health_check.py --check pnl_integrity` — single check
- `python tools/db_health_check.py --json` — write to stdout, no file write

Connection: uses `audit_trail.mysql_client._create_connection()`. Set env vars
AUDIT_DB_USER / AUDIT_DB_PASS / AUDIT_DB_NAME for the backtests DB.

All queries are read-only SELECTs. No INSERT/UPDATE/DELETE.

Schedule: hourly via `audit-dashboard.yml` (freshness checks) + daily via
new `db-health.yml` (full audit). See `database/db_helper_scripts/SCRIPTS_GUIDE.md`
for the full Hermes cron schedule.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# repo root
REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


_READ_TIMEOUT = int(os.environ.get("DB_HEALTH_READ_TIMEOUT", "120"))
_CONNECT_TIMEOUT = int(os.environ.get("DB_HEALTH_CONNECT_TIMEOUT", "20"))
_RETRY_COUNT = int(os.environ.get("DB_HEALTH_RETRY", "2"))


def _conn():
    """Create a fresh MySQL connection w/ long read_timeout (overrides
    audit_trail.mysql_client._create_connection's hardcoded 10s)."""
    import pymysql  # type: ignore
    host = os.environ.get("AUDIT_DB_HOST", "mysql.50webs.com")
    user = os.environ.get("AUDIT_DB_USER", "ejaguiar1_stocks")
    pwd = os.environ.get("AUDIT_DB_PASS", "stocks")
    db = os.environ.get("AUDIT_DB_NAME", "ejaguiar1_stocks")
    c = pymysql.connect(
        host=host, user=user, password=pwd, database=db,
        connect_timeout=_CONNECT_TIMEOUT,
        read_timeout=_READ_TIMEOUT,
        write_timeout=_READ_TIMEOUT,
        charset="utf8mb4",
    )
    cur = c.cursor()
    cur.execute(f"SET SESSION MAX_EXECUTION_TIME={_READ_TIMEOUT*1000}")
    cur.execute(f"SET SESSION net_read_timeout={_READ_TIMEOUT}")
    cur.execute(f"SET SESSION net_write_timeout={_READ_TIMEOUT}")
    return c, cur


def _safe_run(name: str, fn):
    """Run a check w/ retry on connection drops; capture elapsed time."""
    t0 = time.time()
    last_err = None
    for attempt in range(1, _RETRY_COUNT + 2):
        try:
            out = fn()
            return {"name": name, "ok": True, "elapsed_s": round(time.time() - t0, 2),
                    "attempts": attempt, "data": out}
        except Exception as e:
            last_err = e
            if attempt <= _RETRY_COUNT:
                time.sleep(2 * attempt)  # 2s, 4s
                continue
    return {"name": name, "ok": False, "elapsed_s": round(time.time() - t0, 2),
            "attempts": _RETRY_COUNT + 1,
            "error": f"{type(last_err).__name__}: {last_err}"}


# ────────────────────────────────────────────────────────────────────────
# Tier 1 — CRITICAL (freebuff plan items 1.1, 1.2, 1.3, 4.1)
# ────────────────────────────────────────────────────────────────────────

def check_pnl_integrity() -> dict:
    """Freebuff 1.1: % of closed rows where stored pnl_pct disagrees with
    recomputed (exit-entry)/entry by >1pp. PK-bounded sample (id range)
    avoids shared-host /tmp blowup from full-table scans."""
    sampled = 0; gt1 = 0; gt001 = 0
    # Get min/max id, then sample ~100k via id BETWEEN
    c, cur = _conn()
    cur.execute("SELECT MIN(id), MAX(id) FROM bt_backtest_trades")
    mn, mx = cur.fetchone()
    c.close()
    if not mn or not mx:
        return {"sampled": 0, "tier": "yellow", "threshold_pass": False,
                "error": "no rows"}
    # Sample contiguous slice of 200k IDs from middle of range (avoids
    # the bias of latest-only or oldest-only)
    mid = (mn + mx) // 2
    slice_lo = max(mn, mid - 100000)
    slice_hi = min(mx, mid + 100000)
    c, cur = _conn()
    # Cast to DOUBLE to avoid Decimal*float TypeError when fetched in Python
    cur.execute("""
        SELECT
            COUNT(*) AS sampled,
            SUM(CASE WHEN ABS(CAST(pnl_pct AS DOUBLE) - ((CAST(exit_price AS DOUBLE) - CAST(entry_price AS DOUBLE)) / CAST(entry_price AS DOUBLE) * 100)) > 1
                     THEN 1 ELSE 0 END) AS gt1,
            SUM(CASE WHEN ABS(CAST(pnl_pct AS DOUBLE) - ((CAST(exit_price AS DOUBLE) - CAST(entry_price AS DOUBLE)) / CAST(entry_price AS DOUBLE) * 100)) > 0.01
                     THEN 1 ELSE 0 END) AS gt001
        FROM bt_backtest_trades
        WHERE id BETWEEN %s AND %s
          AND status IN ('WON','LOST','WIN','LOSS','TP_HIT','SL_HIT','CLOSED_TP','CLOSED_SL','closed','CLOSED')
          AND pnl_pct IS NOT NULL AND entry_price > 0 AND exit_price > 0
    """, (slice_lo, slice_hi))
    sampled, gt1, gt001 = cur.fetchone()
    c.close()
    sampled = int(sampled or 0)
    gt1 = int(gt1 or 0); gt001 = int(gt001 or 0)
    pct = round(100.0 * gt1 / sampled, 2) if sampled else 0
    return {
        "sampled": sampled,
        "id_range": [int(slice_lo), int(slice_hi)],
        "gt1pct_mismatch": gt1,
        "gt001pct_mismatch": gt001,
        "mismatch_pct": pct,
        "tier": "green" if pct < 5 else "yellow" if pct < 15 else "red",
        "threshold_pass": pct < 15,
    }


def check_ghost_rows() -> dict:
    """Freebuff 1.2 + my F2 + Kimi goldmine. Constant-pnl cohorts (n>1000,
    distinct_entries<5). Runs PER asset_class to fit shared-host /tmp budget
    (idx_bt_asset partitions the GROUP BY into ~2.6M-row buckets max)."""
    classes = ["CRYPTO", "MEMECOIN", "FOREX", "EQUITY", "FUTURES", "ETF",
               "PENNY_STOCK", "COMMODITY", "UNKNOWN"]
    cohorts = []
    per_class_errors = {}
    # Per-class LIMIT subquery (freebuff pattern) — caps GROUP BY tmp size per
    # class. 2026-05-22 P1 fix: heavy classes (CRYPTO ~1.8M rows) blow the
    # shared-host /tmp budget on the GROUP BY + COUNT(DISTINCT) temp table at
    # 500K, so CRYPTO silently contributed 0 ghosts (errno 28 / lost
    # connection). Retry down a sample ladder so the class still gets a
    # (smaller-sampled) count instead of vanishing from the metric. Ghost
    # cohorts are dense enough that a 50K sample still detects them.
    SAMPLE_LADDER = [500000, 150000, 50000]
    per_class_sample = {}
    for ac in classes:
        last_err = None
        for sample in SAMPLE_LADDER:
            c = None
            try:
                c, cur = _conn()
                cur.execute("""
                    SELECT strategy, symbol, direction, ROUND(pnl_pct, 4) AS pnl,
                           COUNT(*) AS n, COUNT(DISTINCT entry_price) AS distinct_entries
                    FROM (
                        SELECT strategy, symbol, direction, pnl_pct, entry_price
                        FROM bt_backtest_trades USE INDEX (idx_bt_asset)
                        WHERE asset_class = %s AND pnl_pct IS NOT NULL
                        LIMIT %s
                    ) t
                    GROUP BY strategy, symbol, direction, ROUND(pnl_pct, 4)
                    HAVING COUNT(*) > 1000 AND COUNT(DISTINCT entry_price) < 5
                    ORDER BY n DESC LIMIT 10
                """, (ac, sample))
                rows = cur.fetchall()
                c.close()
                for r in rows:
                    cohorts.append({
                        "asset_class": ac, "strategy": r[0], "symbol": r[1],
                        "direction": r[2],
                        "pnl_pct": float(r[3]) if r[3] is not None else None,
                        "n": int(r[4]), "distinct_entries": int(r[5]),
                        "sampled_at": sample,
                    })
                per_class_sample[ac] = sample
                last_err = None
                break  # this sample size worked — stop laddering down
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                try:
                    if c is not None:
                        c.close()
                except Exception:
                    pass
        if last_err:
            per_class_errors[ac] = last_err
    cohorts.sort(key=lambda x: x["n"], reverse=True)
    total_ghosts = sum(c_["n"] for c_ in cohorts)
    return {
        "total_ghost_rows": total_ghosts,
        "cohort_count": len(cohorts),
        "top_cohorts": cohorts[:15],
        "per_class_errors": per_class_errors,
        "per_class_sample": per_class_sample,
        "tier": "green" if total_ghosts < 1000 else "yellow" if total_ghosts < 100000 else "red",
        "threshold_pass": total_ghosts < 100000,
    }


def check_open_bloat() -> dict:
    """Freebuff 1.3 + my F1. OPEN row % + last terminal write age."""
    out = {}
    c, cur = _conn()
    # OPEN count
    cur.execute("SELECT COUNT(*) FROM bt_backtest_trades WHERE status='OPEN'")
    out["open_count"] = int(cur.fetchone()[0])
    c.close()
    c, cur = _conn()
    # Total via info_schema (approximation; under-counts by ~22x but we know that)
    cur.execute("""
        SELECT TABLE_ROWS FROM information_schema.TABLES
        WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_NAME='bt_backtest_trades'
    """)
    out["info_schema_estimate"] = int(cur.fetchone()[0] or 0)
    c.close()
    c, cur = _conn()
    # Last terminal write age
    cur.execute("""
        SELECT MAX(imported_at), TIMESTAMPDIFF(HOUR, MAX(imported_at), NOW())
        FROM bt_backtest_trades
        WHERE status IN ('WON','LOST','WIN','LOSS','TP_HIT','SL_HIT','CLOSED_TP','CLOSED_SL')
    """)
    last_ts, hours_ago = cur.fetchone()
    c.close()
    out["last_terminal_write"] = str(last_ts) if last_ts else None
    out["hours_since_last_close"] = int(hours_ago) if hours_ago is not None else None
    out["validator_frozen"] = bool(hours_ago and hours_ago > 26)
    out["tier"] = "red" if out["validator_frozen"] else "green"
    out["threshold_pass"] = not out["validator_frozen"]
    return out


def check_index_health() -> dict:
    """Freebuff 4.1 + my P0 #1 (partly obsolete). Confirm critical indexes."""
    c, cur = _conn()
    cur.execute("SHOW INDEX FROM bt_backtest_trades")
    indexes = {}  # key_name -> [columns]
    for row in cur.fetchall():
        key = row[2]
        col = row[4]
        indexes.setdefault(key, []).append(col)
    c.close()
    recommended = {
        "(asset_class, status)": False,
        "(strategy, asset_class)": False,
        "(source_db, source_table)": False,
        "(status, imported_at)": False,
        "(strategy, symbol, pnl_pct)": False,
    }
    # Check existing single-col coverage
    single = {k: True for k, cols in indexes.items() if len(cols) == 1}
    for rec in recommended:
        # Composite recommended; keep recommended==False unless exact match exists.
        cols_needed = [c.strip() for c in rec.strip("()").split(",")]
        for k, cols in indexes.items():
            if [c.strip("` ") for c in cols] == cols_needed:
                recommended[rec] = True
                break
    return {
        "existing_indexes": indexes,
        "single_col_coverage": list(single.keys()),
        "recommended_composites": recommended,
        "missing_count": sum(1 for v in recommended.values() if not v),
        "tier": "green" if all(recommended.values()) else "yellow",
        "threshold_pass": True,  # composites are nice-to-have, not blocking
    }


# ────────────────────────────────────────────────────────────────────────
# Tier 2 — HIGH (freebuff 2.1, 2.2)
# ────────────────────────────────────────────────────────────────────────

def check_phantom_expired() -> dict:
    """Freebuff 2.1 + my F3. Per-asset-class phantom EXPIRED row %.
    Use idx_bt_status partition: expired-only first (small set),
    then a separate count for closed totals to avoid GROUP BY on 30M rows."""
    c, cur = _conn()
    # Phantoms — bounded by status='expired' which is ~28k rows
    cur.execute("""
        SELECT asset_class,
               COUNT(*) AS expired_total,
               SUM(CASE WHEN pnl_pct=0 AND exit_price=entry_price THEN 1 ELSE 0 END) AS phantoms
        FROM bt_backtest_trades USE INDEX (idx_bt_status)
        WHERE status='expired'
        GROUP BY asset_class
    """)
    rows = []
    for r in cur.fetchall():
        ac, expired_total, phantoms = r
        expired_total = int(expired_total or 0)
        phantoms = int(phantoms or 0)
        rows.append({
            "asset_class": ac,
            "expired_total": expired_total,
            "phantoms": phantoms,
            "phantom_pct": round(100.0 * phantoms / expired_total, 2) if expired_total else 0,
        })
    c.close()
    worst = max((r["phantom_pct"] for r in rows), default=0)
    return {
        "by_class": rows,
        "worst_phantom_pct": worst,
        "tier": "green" if worst < 10 else "yellow" if worst < 50 else "red",
        "threshold_pass": worst < 50,
    }


def check_outcome_coverage() -> dict:
    """Freebuff 2.2 + Kimi #2. % of raw picks that have resolved outcomes."""
    c, cur = _conn()
    cur.execute("SELECT COUNT(*) FROM at_raw_picks")
    raw_total = int(cur.fetchone()[0])
    c.close()
    c, cur = _conn()
    cur.execute("""
        SELECT COUNT(*) FROM at_raw_picks
        WHERE pnl_pct IS NOT NULL AND status NOT IN ('OPEN','open','pending','PENDING')
    """)
    raw_resolved = int(cur.fetchone()[0])
    c.close()
    c, cur = _conn()
    cur.execute("SELECT COUNT(*) FROM at_signal_outcomes")
    try:
        outcomes = int(cur.fetchone()[0])
    except Exception:
        outcomes = None
    c.close()
    c, cur = _conn()
    cur.execute("SELECT COUNT(*) FROM trading_picks")
    tp_total = int(cur.fetchone()[0])
    c.close()
    c, cur = _conn()
    cur.execute("""
        SELECT COUNT(*) FROM trading_picks
        WHERE status IN ('WON','LOST','TP_HIT','SL_HIT','CLOSED','closed_win','closed_loss')
    """)
    tp_resolved = int(cur.fetchone()[0])
    c.close()
    raw_pct = round(100.0 * raw_resolved / raw_total, 4) if raw_total else 0
    tp_pct = round(100.0 * tp_resolved / tp_total, 2) if tp_total else 0
    return {
        "raw_picks_total": raw_total,
        "raw_picks_resolved": raw_resolved,
        "raw_resolved_pct": raw_pct,
        "trading_picks_total": tp_total,
        "trading_picks_resolved": tp_resolved,
        "trading_resolved_pct": tp_pct,
        "at_signal_outcomes_count": outcomes,
        "tier": "green" if raw_pct > 50 else "yellow" if raw_pct > 5 else "red",
        "threshold_pass": raw_pct > 0.5,
    }


# ────────────────────────────────────────────────────────────────────────
# Tier 3 — MEDIUM (freebuff 3.1, 3.2, 3.3)
# ────────────────────────────────────────────────────────────────────────

def check_ml_feature_store() -> dict:
    """Freebuff 3.1 + Kimi #4. ml_feature_store target NULL ratio."""
    c, cur = _conn()
    try:
        cur.execute("""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN target_direction IS NULL THEN 1 ELSE 0 END) AS dir_null,
                   SUM(CASE WHEN target_pnl_pct IS NULL THEN 1 ELSE 0 END) AS pnl_null
            FROM ml_feature_store
        """)
        total, dir_null, pnl_null = cur.fetchone()
        total = int(total or 0)
        out = {
            "total": total,
            "target_direction_null": int(dir_null or 0),
            "target_pnl_pct_null": int(pnl_null or 0),
            "dir_null_pct": round(100.0 * (dir_null or 0) / total, 2) if total else 100,
            "pnl_null_pct": round(100.0 * (pnl_null or 0) / total, 2) if total else 100,
            "tier": "green" if total > 100 and (dir_null or 0) / max(1, total) < 0.05 else "red",
        }
        out["threshold_pass"] = out["tier"] != "red"
    except Exception as e:
        out = {"error": f"ml_feature_store query failed: {e}",
               "tier": "yellow", "threshold_pass": False}
    c.close()
    return out


def check_signal_tier_writer() -> dict:
    """Kimi-aligned. at_discord_notifications.signal_tier NULL ratio."""
    c, cur = _conn()
    cur.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN signal_tier IS NULL OR signal_tier='None' OR signal_tier='' THEN 1 ELSE 0 END) AS null_n
        FROM at_discord_notifications
        WHERE created_at > NOW() - INTERVAL 7 DAY
    """)
    total, null_n = cur.fetchone()
    c.close()
    total = int(total or 0)
    null_n = int(null_n or 0)
    pct = round(100.0 * null_n / total, 2) if total else 0
    return {
        "total_7d": total,
        "null_n_7d": null_n,
        "null_pct_7d": pct,
        "tier": "green" if pct < 10 else "yellow" if pct < 50 else "red",
        "threshold_pass": pct < 50,
    }


def check_lm_signals_resolver() -> dict:
    """My F-NEW-P0-8. lm_signals expired rows with exit_price=0."""
    c, cur = _conn()
    cur.execute("""
        SELECT COUNT(*) AS expired_n,
               SUM(CASE WHEN exit_price = 0 OR exit_price IS NULL THEN 1 ELSE 0 END) AS no_resolve_n
        FROM lm_signals
        WHERE status = 'expired'
    """)
    expired_n, no_resolve_n = cur.fetchone()
    c.close()
    expired_n = int(expired_n or 0)
    no_resolve_n = int(no_resolve_n or 0)
    pct = round(100.0 * no_resolve_n / expired_n, 2) if expired_n else 0
    return {
        "expired_n": expired_n,
        "no_resolve_n": no_resolve_n,
        "no_resolve_pct": pct,
        "tier": "green" if pct < 5 else "yellow" if pct < 30 else "red",
        "threshold_pass": pct < 30,
    }


def check_won_pnl_contradiction() -> dict:
    """My F-Kimi#1. trading_picks WON-with-negative-PnL."""
    c, cur = _conn()
    cur.execute("""
        SELECT status, COUNT(*) AS n, AVG(pnl_pct) AS avg_pnl,
               SUM(CASE WHEN pnl_pct < 0 THEN 1 ELSE 0 END) AS neg_n
        FROM trading_picks
        WHERE status IN ('WON','LOST','TP_HIT','SL_HIT','closed_win','closed_loss')
          AND pnl_pct IS NOT NULL
        GROUP BY status
    """)
    rows = [{"status": r[0], "n": int(r[1]), "avg_pnl": float(r[2] or 0),
             "negative_pnl_count": int(r[3] or 0)} for r in cur.fetchall()]
    c.close()
    contradiction = any(
        (r["status"] in ("WON","TP_HIT","closed_win") and r["avg_pnl"] < 0) or
        (r["status"] in ("LOST","SL_HIT","closed_loss") and r["avg_pnl"] > 0)
        for r in rows
    )
    return {
        "by_status": rows,
        "contradiction_detected": contradiction,
        "tier": "red" if contradiction else "green",
        "threshold_pass": not contradiction,
    }


# ────────────────────────────────────────────────────────────────────────
# Orchestrator
# ────────────────────────────────────────────────────────────────────────

CHECKS = {
    "pnl_integrity":      ("Tier 1", check_pnl_integrity),
    "ghost_rows":         ("Tier 1", check_ghost_rows),
    "open_bloat":         ("Tier 1", check_open_bloat),
    "index_health":       ("Tier 1", check_index_health),
    "phantom_expired":    ("Tier 2", check_phantom_expired),
    "outcome_coverage":   ("Tier 2", check_outcome_coverage),
    "ml_feature_store":   ("Tier 3", check_ml_feature_store),
    "signal_tier_writer": ("Tier 3", check_signal_tier_writer),
    "lm_signals_resolver":("Tier 3", check_lm_signals_resolver),
    "won_pnl_contradiction": ("Tier 3", check_won_pnl_contradiction),
}

QUICK_CHECKS = {"pnl_integrity", "ghost_rows", "open_bloat", "won_pnl_contradiction"}


def main():
    ap = argparse.ArgumentParser(description="DB health check — converged forensic harness")
    ap.add_argument("--quick", action="store_true", help="Tier-1 critical only (<60s)")
    ap.add_argument("--check", action="append", default=[], help="Run named check(s) only")
    ap.add_argument("--json", action="store_true", help="Write to stdout instead of file")
    ap.add_argument("--out", default="audit_dashboard/data/db_health.json")
    args = ap.parse_args()

    if args.check:
        names = [c for c in args.check if c in CHECKS]
    elif args.quick:
        names = list(QUICK_CHECKS)
    else:
        names = list(CHECKS.keys())

    started = time.time()
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host": "mysql.50webs.com",
        "database": "ejaguiar1_stocks",
        "engine": "MySQL 8.4.7",
        "checks": {},
    }
    for name in names:
        tier, fn = CHECKS[name]
        sys.stderr.write(f"[{tier}] {name}...\n")
        sys.stderr.flush()
        results["checks"][name] = _safe_run(name, fn)
        results["checks"][name]["tier_label"] = tier

    results["overall"] = {
        "elapsed_s": round(time.time() - started, 2),
        "checks_run": len(names),
        "checks_passed": sum(1 for c in results["checks"].values() if c["ok"] and c.get("data", {}).get("threshold_pass", False)),
        "checks_failed": sum(1 for c in results["checks"].values() if not c["ok"] or not c.get("data", {}).get("threshold_pass", True)),
        "any_red": any(c.get("data", {}).get("tier") == "red" for c in results["checks"].values() if c["ok"]),
    }

    body = json.dumps(results, ensure_ascii=True, indent=2, default=str)
    if args.json:
        sys.stdout.write(body + "\n")
    else:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")
        sys.stderr.write(f"wrote {out} ({len(body):,} bytes, {results['overall']['elapsed_s']}s)\n")
    sys.exit(1 if results["overall"]["any_red"] else 0)


if __name__ == "__main__":
    main()
