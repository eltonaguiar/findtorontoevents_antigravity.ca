"""
Sync Winners Registry to MySQL
================================
Compiles all winning strategies (WR>55%, PF>1.5) from:
  - walkforward_results.json
  - fear_greed_variant_backtest.json
  - mutation_backtest_results.json (if exists)
  - inverse_strategies.py HARDCODED_PASS_MUTATIONS

Writes winners_registry.json and optionally syncs to MySQL
strategy_test_runs + super_strategy_candidates tables.

Usage:  python scripts/sync_winners_to_mysql.py [--dry-run]
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
FG_VARIANT_PATH = REPO_ROOT / "alpha_engine" / "data" / "fear_greed_variant_backtest.json"
MUTATION_PATH = REPO_ROOT / "alpha_engine" / "data" / "mutation_backtest_results.json"
WINNERS_OUT_PATH = REPO_ROOT / "alpha_engine" / "data" / "winners_registry.json"

# ---------------------------------------------------------------------------
# DB config
# ---------------------------------------------------------------------------
DB_HOST = "mysql.50webs.com"
DB_PORT = 3306
DB_USER = "ejaguiar1_stocks"
DB_PASS = os.environ.get("MYSQL_50WEBS_PASS", os.environ.get("AUDIT_DB_PASS", "stocks"))
DB_NAME = "ejaguiar1_stocks"

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
MIN_WR = 55.0   # percent
MIN_PF = 1.5


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _load_json(path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return default if f != f else f
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Source 1: Walk-forward results
# ---------------------------------------------------------------------------
def extract_walkforward_winners(wf_data):
    """Extract strategies with WR > 55% and PF > 1.5 from walkforward results."""
    winners = []
    if not wf_data:
        return winners

    for strat in wf_data.get("strategies", []):
        wr = _safe_float(strat.get("win_rate"), 0)
        pf = _safe_float(strat.get("profit_factor"), 0)

        if wr >= MIN_WR and pf >= MIN_PF:
            has_wf = strat.get("wf_folds") and strat["wf_folds"] > 0
            verdict = strat.get("verdict", "").upper()
            winners.append({
                "strategy_id": strat["strategy"],
                "wr": round(wr, 2),
                "pf": round(pf, 4),
                "trades": int(strat.get("trades", 0)),
                "status": verdict if verdict else "VIABLE",
                "lineage": "walkforward" if has_wf else "backtest",
                "source": "walkforward_results.json",
                "sharpe": _safe_float(strat.get("sharpe")),
                "max_drawdown": _safe_float(strat.get("max_drawdown")),
                "p_value": _safe_float(strat.get("p_value")),
                "wf_oos_wr": _safe_float(strat.get("wf_oos_wr")),
                "wf_folds": strat.get("wf_folds", 0),
                "final_score": _safe_float(strat.get("final_score")),
                "source_systems": strat.get("source_systems", []),
            })

    return winners


# ---------------------------------------------------------------------------
# Source 2: Fear & Greed variant backtest
# ---------------------------------------------------------------------------
def extract_variant_winners(fg_data):
    """Extract accepted variants from fear_greed_variant_backtest.json."""
    winners = []
    if not fg_data:
        return winners

    base_strategy = fg_data.get("strategy", "unknown")
    baseline = fg_data.get("baseline", {})

    for variant in fg_data.get("variants", []):
        acceptance = variant.get("acceptance", {})
        if not acceptance.get("all_pass", False):
            continue

        wr = _safe_float(variant.get("estimated_win_rate_positive"), 0)
        pf = _safe_float(variant.get("estimated_pf"), 0)

        if wr >= MIN_WR and pf >= MIN_PF:
            winners.append({
                "strategy_id": f"{base_strategy}_{variant['name']}",
                "wr": round(wr, 2),
                "pf": round(pf, 4),
                "trades": int(variant.get("estimated_trades", 0)),
                "status": "VARIANT_ACCEPTED",
                "lineage": f"variant_of:{base_strategy}",
                "source": "fear_greed_variant_backtest.json",
                "sharpe": None,
                "max_drawdown": None,
                "p_value": None,
                "wf_oos_wr": None,
                "wf_folds": 0,
                "final_score": None,
                "source_systems": [base_strategy],
                "variant_details": {
                    "name": variant["name"],
                    "description": variant.get("description", ""),
                    "wr_delta_pp": variant.get("wr_delta_pp"),
                    "baseline_pf": _safe_float(baseline.get("profit_factor")),
                    "baseline_trades": baseline.get("trades"),
                },
            })

    return winners


# ---------------------------------------------------------------------------
# Source 3: Mutation backtest results
# ---------------------------------------------------------------------------
def extract_mutation_winners(mutation_data):
    """Extract passing mutations from mutation_backtest_results.json."""
    winners = []
    if not mutation_data:
        return winners

    for result in mutation_data.get("detailed_results", []):
        if result.get("verdict") != "PASS":
            continue

        overall = result.get("overall_stats", {})
        wr = _safe_float(overall.get("wr"), 0) * 100  # convert from decimal
        pf = _safe_float(overall.get("pf"), 0)

        if wr >= MIN_WR and pf >= MIN_PF:
            winners.append({
                "strategy_id": result.get("mutation", result.get("strategy", "unknown")),
                "wr": round(wr, 2),
                "pf": round(pf, 4),
                "trades": int(overall.get("count", 0)),
                "status": "MUTATION_PASS",
                "lineage": f"mutation_of:{result.get('strategy', 'unknown')}",
                "source": "mutation_backtest_results.json",
                "sharpe": None,
                "max_drawdown": None,
                "p_value": None,
                "wf_oos_wr": None,
                "wf_folds": 0,
                "final_score": None,
                "source_systems": [result.get("strategy", "unknown")],
            })

    return winners


# ---------------------------------------------------------------------------
# Source 4: HARDCODED_PASS_MUTATIONS from inverse_strategies.py
# ---------------------------------------------------------------------------
def extract_inverse_winners():
    """Extract validated inverse strategies from HARDCODED_PASS_MUTATIONS."""
    winners = []

    # Import the module
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from alpha_engine.inverse_strategies import HARDCODED_PASS_MUTATIONS
    except ImportError as e:
        print(f"  [WARN] Could not import inverse_strategies: {e}")
        return winners

    for orig_strategy, info in HARDCODED_PASS_MUTATIONS.items():
        wr = _safe_float(info.get("wr"), 0) * 100  # convert from decimal
        pf = _safe_float(info.get("pf"), 0)

        if wr >= MIN_WR and pf >= MIN_PF:
            winners.append({
                "strategy_id": info.get("inverse_name", f"inverse_{orig_strategy}"),
                "wr": round(wr, 2),
                "pf": round(pf, 4),
                "trades": int(info.get("trades", 0)),
                "status": "INVERSE_VALIDATED",
                "lineage": f"inverse_of:{orig_strategy}",
                "source": "inverse_strategies.py:HARDCODED_PASS_MUTATIONS",
                "sharpe": None,
                "max_drawdown": None,
                "p_value": None,
                "wf_oos_wr": None,
                "wf_folds": 0,
                "final_score": None,
                "source_systems": [orig_strategy],
                "confidence": _safe_float(info.get("confidence")),
            })

    return winners


# ---------------------------------------------------------------------------
# MySQL sync
# ---------------------------------------------------------------------------
def _connect(dry_run=False):
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
        print("[DRY-RUN] Would connect to MySQL -- skipping.")
        return None

    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=DB_NAME, connect_timeout=15, read_timeout=30,
        write_timeout=30, charset="utf8mb4", autocommit=True,
    )
    print(f"Connected to {DB_HOST}/{DB_NAME}")
    return conn


def sync_to_mysql(conn, winners, dry_run=False):
    """Insert winners into strategy_test_runs and super_strategy_candidates."""
    now = _now()
    test_runs_inserted = 0
    candidates_inserted = 0

    INSERT_TEST_RUN = """
        INSERT INTO strategy_test_runs
            (strategy_id, test_layer, asset_class, trades, win_rate,
             profit_factor, sharpe, max_drawdown, p_value, pass_flag,
             metadata_json, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    UPSERT_CANDIDATE = """
        INSERT INTO super_strategy_candidates
            (strategy_id, symbols_passed, asset_classes_passed, regimes_passed,
             concentration_ratio, fisher_p, status, notes, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            status = VALUES(status),
            notes = VALUES(notes),
            updated_at = VALUES(updated_at)
    """

    for w in winners:
        # Determine test_layer from lineage
        lineage = w.get("lineage", "")
        if "walkforward" in lineage:
            test_layer = "walk_forward"
        elif "variant" in lineage:
            test_layer = "variant_backtest"
        elif "inverse" in lineage:
            test_layer = "inverse_backtest"
        elif "mutation" in lineage:
            test_layer = "mutation_backtest"
        else:
            test_layer = "backtest"

        meta = json.dumps({
            "source": w.get("source"),
            "lineage": lineage,
            "source_systems": w.get("source_systems", []),
            "final_score": w.get("final_score"),
            "wf_oos_wr": w.get("wf_oos_wr"),
            "wf_folds": w.get("wf_folds"),
            "confidence": w.get("confidence"),
        }, default=str)

        test_params = (
            w["strategy_id"], test_layer, "CRYPTO",
            w["trades"], w["wr"], w["pf"],
            w.get("sharpe"), w.get("max_drawdown"), w.get("p_value"),
            1,  # pass_flag = True (all are winners)
            meta, now,
        )

        candidate_params = (
            w["strategy_id"],
            1,  # symbols_passed (at least 1)
            1,  # asset_classes_passed
            0,  # regimes_passed (unknown)
            None,  # concentration_ratio
            w.get("p_value"),
            w["status"],
            f"WR={w['wr']}% PF={w['pf']} Trades={w['trades']} Lineage={lineage}",
            now,
        )

        if dry_run:
            print(f"  [DRY] test_run + candidate: {w['strategy_id']}")
        else:
            cur = conn.cursor()
            cur.execute(INSERT_TEST_RUN, test_params)
            test_runs_inserted += 1
            cur.execute(UPSERT_CANDIDATE, candidate_params)
            candidates_inserted += 1

    if dry_run:
        test_runs_inserted = len(winners)
        candidates_inserted = len(winners)

    return test_runs_inserted, candidates_inserted


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def print_winners_table(winners):
    """Print a formatted summary table of all winning strategies."""
    if not winners:
        print("\nNo winning strategies found matching WR>55% and PF>1.5")
        return

    # Sort by PF descending
    sorted_winners = sorted(winners, key=lambda w: w["pf"], reverse=True)

    print(f"\n{'='*100}")
    print(f"  WINNERS REGISTRY -- {len(sorted_winners)} strategies (WR>{MIN_WR}%, PF>{MIN_PF})")
    print(f"{'='*100}")
    print(f"  {'Strategy':<45} {'WR%':>6} {'PF':>8} {'Trades':>7} {'Status':<20} {'Lineage'}")
    print(f"  {'-'*45} {'-'*6} {'-'*8} {'-'*7} {'-'*20} {'-'*30}")

    for w in sorted_winners:
        sid = w["strategy_id"][:44]
        lineage = w.get("lineage", "")[:30]
        print(f"  {sid:<45} {w['wr']:>6.1f} {w['pf']:>8.2f} {w['trades']:>7d} {w['status']:<20} {lineage}")

    print(f"  {'-'*45} {'-'*6} {'-'*8} {'-'*7} {'-'*20} {'-'*30}")
    print(f"  Total: {len(sorted_winners)} winning strategies")

    # Stats summary
    avg_wr = sum(w["wr"] for w in sorted_winners) / len(sorted_winners)
    avg_pf = sum(w["pf"] for w in sorted_winners) / len(sorted_winners)
    total_trades = sum(w["trades"] for w in sorted_winners)
    print(f"  Avg WR: {avg_wr:.1f}%  |  Avg PF: {avg_pf:.2f}  |  Total trades: {total_trades}")
    print(f"{'='*100}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("Winners Registry Builder + MySQL Sync")
    print("=" * 60)

    all_winners = []

    # Source 1: Walk-forward results
    print("\n[1] Loading walkforward_results.json ...")
    wf_data = _load_json(WF_RESULTS_PATH)
    wf_winners = extract_walkforward_winners(wf_data)
    print(f"    => {len(wf_winners)} winners (WR>{MIN_WR}%, PF>{MIN_PF})")
    all_winners.extend(wf_winners)

    # Source 2: Fear & Greed variant backtest
    print("\n[2] Loading fear_greed_variant_backtest.json ...")
    fg_data = _load_json(FG_VARIANT_PATH)
    fg_winners = extract_variant_winners(fg_data)
    print(f"    => {len(fg_winners)} accepted variants")
    all_winners.extend(fg_winners)

    # Source 3: Mutation backtest results
    print("\n[3] Loading mutation_backtest_results.json ...")
    mutation_data = _load_json(MUTATION_PATH)
    if mutation_data is None:
        print("    => File not found (skipping)")
    else:
        mut_winners = extract_mutation_winners(mutation_data)
        print(f"    => {len(mut_winners)} mutation winners")
        all_winners.extend(mut_winners)

    # Source 4: HARDCODED_PASS_MUTATIONS
    print("\n[4] Loading inverse_strategies.py HARDCODED_PASS_MUTATIONS ...")
    inv_winners = extract_inverse_winners()
    print(f"    => {len(inv_winners)} validated inverses")
    all_winners.extend(inv_winners)

    # Deduplicate by strategy_id (keep highest PF)
    seen = {}
    for w in all_winners:
        sid = w["strategy_id"]
        if sid not in seen or w["pf"] > seen[sid]["pf"]:
            seen[sid] = w
    all_winners = list(seen.values())

    # Print report
    print_winners_table(all_winners)

    # Write winners_registry.json
    registry = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "thresholds": {"min_wr_pct": MIN_WR, "min_pf": MIN_PF},
        "total_winners": len(all_winners),
        "sources": {
            "walkforward": len(wf_winners),
            "variants": len(fg_winners),
            "mutations": len([w for w in all_winners if "mutation" in w.get("lineage", "")]),
            "inverses": len(inv_winners),
        },
        "winners": sorted(all_winners, key=lambda w: w["pf"], reverse=True),
    }

    with open(WINNERS_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, default=str)
    print(f"Written: {WINNERS_OUT_PATH}")

    # MySQL sync
    print("\n--- MySQL Sync ---")
    conn = _connect(dry_run=dry_run)
    runs, cands = sync_to_mysql(conn, all_winners, dry_run=dry_run)
    print(f"  => {runs} test_runs inserted, {cands} super_strategy_candidates upserted")

    if conn:
        conn.close()

    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(all_winners)} winning strategies compiled")
    print(f"  Walk-forward winners: {len(wf_winners)}")
    print(f"  Variant winners:      {len(fg_winners)}")
    print(f"  Inverse winners:      {len(inv_winners)}")
    print(f"  MySQL test_runs:      {runs}")
    print(f"  MySQL candidates:     {cands}")
    if dry_run:
        print("  (DRY-RUN mode -- nothing written to MySQL)")
    print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
