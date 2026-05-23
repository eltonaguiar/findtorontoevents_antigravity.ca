"""
Sync Walk-Forward Results & Strategy Performance to MySQL
==========================================================
Reads local walk-forward results and closed picks, then syncs to
strategy_test_runs and strategy_symbol_coverage in ejaguiar1_stocks.

Usage:  python scripts/sync_backtests_to_mysql.py [--dry-run]
Env:    MYSQL_50WEBS_PASS  (fallback: "stocks")
"""

import datetime as dt
import json
import os
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
WF_RESULTS_PATH = REPO_ROOT / "alpha_engine" / "data" / "walkforward_results.json"
CLOSED_PICKS_PATH = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"

# ---------------------------------------------------------------------------
# DB config
# ---------------------------------------------------------------------------
DB_HOST = "mysql.50webs.com"
DB_PORT = 3306
DB_USER = "ejaguiar1_stocks"
DB_PASS = os.environ.get("MYSQL_50WEBS_PASS", os.environ.get("AUDIT_DB_PASS", "stocks"))
DB_NAME = "ejaguiar1_stocks"


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return default if f != f else f  # NaN guard
    except (ValueError, TypeError):
        return default


def _load_json(path):
    if not path.exists():
        print(f"  [WARN] File not found: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _connect(dry_run=False):
    """Connect to MySQL using pymysql (same as rest of project)."""
    try:
        import pymysql
    except ImportError:
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pymysql"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        import pymysql

    if dry_run:
        print("[DRY-RUN] Would connect to MySQL — skipping.")
        return None

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connect_timeout=15,
        read_timeout=30,
        write_timeout=30,
        charset="utf8mb4",
        autocommit=True,
    )
    print(f"Connected to {DB_HOST}/{DB_NAME}")
    return conn


# ---------------------------------------------------------------------------
# Sync walk-forward results -> strategy_test_runs
# ---------------------------------------------------------------------------
def sync_walkforward(conn, wf_data, dry_run=False):
    """Insert walk-forward strategy results into strategy_test_runs."""
    strategies = wf_data.get("strategies", [])
    if not strategies:
        print("  No strategies in walkforward_results.json")
        return 0

    now = _now()
    inserted = 0

    INSERT_SQL = """
        INSERT INTO strategy_test_runs
            (strategy_id, test_layer, asset_class, trades, win_rate,
             profit_factor, sharpe, max_drawdown, p_value, pass_flag,
             metadata_json, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            trades = VALUES(trades),
            win_rate = VALUES(win_rate),
            profit_factor = VALUES(profit_factor),
            sharpe = VALUES(sharpe),
            max_drawdown = VALUES(max_drawdown),
            p_value = VALUES(p_value),
            pass_flag = VALUES(pass_flag)
    """

    for strat in strategies:
        sid = strat.get("strategy", "")
        if not sid:
            continue

        # Determine test_layer based on wf_folds presence
        has_wf = strat.get("wf_folds") and strat["wf_folds"] > 0
        test_layer = "walk_forward" if has_wf else "backtest"

        # Asset class (take first from list)
        asset_classes = strat.get("asset_classes", [])
        asset_class = asset_classes[0] if asset_classes else None

        # Pass flag: verdict in (ELITE, STRONG, VIABLE)
        verdict = strat.get("verdict", "").upper()
        pass_flag = 1 if verdict in ("ELITE", "STRONG", "VIABLE") else 0

        # Metadata blob
        meta = {
            "source_systems": strat.get("source_systems", []),
            "perf_score": strat.get("perf_score"),
            "proof_score": strat.get("proof_score"),
            "final_score": strat.get("final_score"),
            "verdict": verdict,
            "wf_oos_wr": strat.get("wf_oos_wr"),
            "wf_oos_sharpe": strat.get("wf_oos_sharpe"),
            "wf_decay": strat.get("wf_decay"),
            "wf_consistency": strat.get("wf_consistency"),
            "wf_worst_fold": strat.get("wf_worst_fold"),
            "sharpe_ci_low": strat.get("sharpe_ci_low"),
            "sharpe_ci_high": strat.get("sharpe_ci_high"),
        }
        meta_json = json.dumps(meta, default=str)

        params = (
            sid, test_layer, asset_class,
            int(strat.get("trades", 0)),
            _safe_float(strat.get("win_rate")),
            _safe_float(strat.get("profit_factor")),
            _safe_float(strat.get("sharpe")),
            _safe_float(strat.get("max_drawdown")),
            _safe_float(strat.get("p_value")),
            pass_flag,
            meta_json,
            now,
        )

        if dry_run:
            print(f"  [DRY] Would insert test_run: {sid} ({test_layer})")
            inserted += 1
        else:
            cur = conn.cursor()
            cur.execute(INSERT_SQL, params)
            inserted += 1

    return inserted


# ---------------------------------------------------------------------------
# Sync closed picks -> strategy_symbol_coverage
# ---------------------------------------------------------------------------
def sync_symbol_coverage(conn, closed_picks, wf_strategies, dry_run=False):
    """Build and insert symbol coverage from closed picks per strategy."""
    if not closed_picks:
        print("  No closed picks data")
        return 0

    # Build a set of strategy IDs that have WF data
    wf_set = set()
    if wf_strategies:
        for s in wf_strategies:
            sid = s.get("strategy", "")
            if sid:
                wf_set.add(sid)

    # Aggregate: (strategy, symbol) -> {asset_class, has_backtest, has_wf, has_forward, last_ts}
    coverage = {}
    for pick in closed_picks:
        strategy = pick.get("strategy", "")
        symbol = pick.get("symbol", "")
        if not strategy or not symbol:
            continue

        key = (strategy, symbol)
        if key not in coverage:
            coverage[key] = {
                "asset_class": "CRYPTO",  # default; most picks are crypto
                "backtest": False,
                "walkforward": strategy in wf_set,
                "forward": True,  # closed picks = forward tested
                "last_ts": None,
            }

        # Update last timestamp
        closed_at = pick.get("closed_at") or pick.get("exit_time")
        if closed_at and (coverage[key]["last_ts"] is None or str(closed_at) > str(coverage[key]["last_ts"])):
            coverage[key]["last_ts"] = closed_at

    UPSERT_SQL = """
        INSERT INTO strategy_symbol_coverage
            (strategy_id, symbol, asset_class, tested_backtest,
             tested_walkforward, tested_forward, last_result_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            tested_walkforward = GREATEST(tested_walkforward, VALUES(tested_walkforward)),
            tested_forward = GREATEST(tested_forward, VALUES(tested_forward)),
            last_result_at = GREATEST(COALESCE(last_result_at, '2000-01-01'),
                                       COALESCE(VALUES(last_result_at), '2000-01-01'))
    """

    inserted = 0
    for (strategy, symbol), info in coverage.items():
        last_ts = None
        if info["last_ts"]:
            try:
                # Parse ISO timestamp to MySQL datetime
                ts = str(info["last_ts"]).replace("T", " ")[:19]
                last_ts = ts
            except Exception:
                last_ts = None

        params = (
            strategy, symbol, info["asset_class"],
            1 if info["backtest"] else 0,
            1 if info["walkforward"] else 0,
            1 if info["forward"] else 0,
            last_ts,
        )

        if dry_run:
            inserted += 1
        else:
            cur = conn.cursor()
            cur.execute(UPSERT_SQL, params)
            inserted += 1

    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("Backtest-to-MySQL Sync")
    print("=" * 60)

    # Load data files
    print("\nLoading walk-forward results ...")
    wf_data = _load_json(WF_RESULTS_PATH)
    wf_strategies = wf_data.get("strategies", []) if wf_data else []

    print("Loading closed picks ...")
    closed_picks = _load_json(CLOSED_PICKS_PATH)
    if isinstance(closed_picks, dict):
        closed_picks = closed_picks.get("picks", closed_picks.get("data", []))

    # Connect
    print()
    conn = _connect(dry_run=dry_run)

    # Sync walk-forward -> strategy_test_runs
    print("\n--- Syncing walk-forward results -> strategy_test_runs ---")
    runs_inserted = sync_walkforward(conn, wf_data or {}, dry_run=dry_run)
    print(f"  => {runs_inserted} test runs inserted/updated")

    # Sync symbol coverage
    print("\n--- Syncing symbol coverage -> strategy_symbol_coverage ---")
    cov_inserted = sync_symbol_coverage(
        conn, closed_picks or [], wf_strategies, dry_run=dry_run
    )
    print(f"  => {cov_inserted} symbol coverages inserted/updated")

    # Summary
    strat_count = len(wf_strategies) if wf_strategies else 0
    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {strat_count} strategies synced, "
          f"{runs_inserted} test runs, {cov_inserted} symbol coverages")
    if dry_run:
        print("  (DRY-RUN mode — nothing written to MySQL)")
    print(f"{'=' * 60}")

    if conn:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
