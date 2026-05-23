"""Unified Performance Loader — Bridges ALL strategy data into the DNA Genome.

Ingests performance metadata from every system in the codebase:
  1. Alpha Engine    — closed_picks.json + strategy_performance.json
  2. Baby Strategies — baby_strats_dashboard.json + tiered backtest results
  3. Incubator       — agent backtest CSV/JSON results (Codex, Cursor AI, etc.)
  4. KIMI            — kimi_trading.db algorithm performance
  5. Meta-Combos     — combo_metrics.json (already partially ingested)
  6. Genome Results  — quant_lab evolved DNA fitness scores
  7. Forward Tests   — incubator/forward_test.db outcomes
  8. Signal Recorder — signal_log.db trade outcomes

Output: Unified metrics dict per strategy, plus DB injection into
        meta_strategy.db permutation_results for genome seeding.

Usage:
  python -m meta_strategy.unified_performance_loader          # load all
  python -m meta_strategy.unified_performance_loader --dry    # preview only
"""
import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "meta_strategy" / "data"

# ── Source file paths ────────────────────────────────────────────

ALPHA_CLOSED = ROOT / "alpha_engine" / "data" / "closed_picks.json"
ALPHA_PERF = ROOT / "alpha_engine" / "data" / "strategy_performance.json"
BABY_DASHBOARD = ROOT / "battleground" / "data" / "baby_strats_dashboard.json"
BABY_TIERED = ROOT / "battleground" / "data"  # tiered_backtest_results_*.json
COMBO_METRICS = ROOT / "battleground" / "data" / "combo_metrics.json"
INCUBATOR_RESULTS = ROOT / "incubator" / "backtest_results"
GENOME_RESULTS = ROOT / "quant_lab" / "genome_results"
KIMI_DB = ROOT / "KIMI_RISEOFTHECLAW" / "data" / "kimi_trading.db"
SIGNAL_TRACKER_DB = ROOT / "KIMI_RISEOFTHECLAW" / "data" / "signal_tracker.db"
FORWARD_TEST_DB = ROOT / "incubator" / "forward_test.db"
SIGNAL_LOG_DB = ROOT / "signal_recorder" / "data" / "signal_log.db"
META_DB = DATA_DIR / "meta_strategy.db"
PERMUTATION_RESULTS = ROOT / "quant_lab" / "combo_results" / "permutation_results.json"

# ── Output ────────────────────────────────────────────────────────

UNIFIED_OUTPUT = DATA_DIR / "unified_strategy_catalog.json"


def _safe_json_load(path: Path) -> Optional[dict | list]:
    """Load JSON file, return None if missing/corrupt."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _safe_db_connect(path: Path) -> Optional[sqlite3.Connection]:
    """Connect to SQLite DB, return None if missing."""
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


# ── Loaders ──────────────────────────────────────────────────────


def load_alpha_engine() -> list[dict]:
    """Load Alpha Engine strategy performance from JSON files."""
    strategies = []

    # Primary source: strategy_performance.json (aggregated)
    perf = _safe_json_load(ALPHA_PERF)
    if perf and isinstance(perf, dict):
        for name, metrics in perf.items():
            if not isinstance(metrics, dict):
                continue
            strategies.append({
                "name": name,
                "source": "alpha_engine",
                "source_type": "forward_live",
                "trades": metrics.get("closed_picks", 0),
                "wins": metrics.get("wins", 0),
                "losses": metrics.get("losses", 0),
                "win_rate": metrics.get("win_rate", 0),
                "avg_pnl_pct": metrics.get("avg_pnl_pct", 0),
                "total_pnl_pct": metrics.get("total_pnl_pct", 0),
                "sharpe": metrics.get("sharpe", 0),
                "sortino": metrics.get("sortino", 0),
                "max_drawdown": metrics.get("max_drawdown", 0),
                "profit_factor": metrics.get("profit_factor", 0),
                "kelly_fraction": metrics.get("kelly_fraction", 0),
                "p_value": metrics.get("p_value", 1.0),
                "by_symbol": metrics.get("by_symbol", {}),
            })

    # Supplementary: closed_picks.json (individual trades for detailed analysis)
    closed = _safe_json_load(ALPHA_CLOSED)
    if closed and isinstance(closed, list):
        # Group by strategy for any strategies not in performance.json
        from collections import defaultdict
        by_strat = defaultdict(list)
        for pick in closed:
            if isinstance(pick, dict) and pick.get("strategy"):
                by_strat[pick["strategy"]].append(pick)

        existing_names = {s["name"] for s in strategies}
        for name, picks in by_strat.items():
            if name in existing_names:
                continue
            wins = sum(1 for p in picks if float(p.get("pnl_pct", 0) or 0) > 0)
            losses = len(picks) - wins
            pnls = [float(p.get("pnl_pct", 0) or 0) for p in picks]
            strategies.append({
                "name": name,
                "source": "alpha_engine",
                "source_type": "forward_live",
                "trades": len(picks),
                "wins": wins,
                "losses": losses,
                "win_rate": wins / max(len(picks), 1),
                "avg_pnl_pct": sum(pnls) / max(len(pnls), 1),
                "total_pnl_pct": sum(pnls),
                "sharpe": 0,
                "profit_factor": 0,
                "p_value": 1.0,
            })

    return strategies


def load_baby_strategies() -> list[dict]:
    """Load Baby Strategy performance from battleground dashboard."""
    strategies = []

    dashboard = _safe_json_load(BABY_DASHBOARD)
    if dashboard and isinstance(dashboard, dict):
        strats = dashboard.get("strategies", [])
        if isinstance(strats, list):
            for s in strats:
                if not isinstance(s, dict):
                    continue
                # Primary: backtest_metrics (the actual field name in the JSON)
                bm = s.get("backtest_metrics", {})
                if not isinstance(bm, dict):
                    bm = {}
                # Forward metrics for strategies in paper trading
                fm = s.get("forward_metrics", {})
                if not isinstance(fm, dict):
                    fm = {}
                # Forward trades list for realized P/L
                fwd_trades = s.get("forward_trades", [])
                if not isinstance(fwd_trades, list):
                    fwd_trades = []
                fwd_wins = sum(1 for t in fwd_trades if isinstance(t, dict) and (t.get("pnl_pct", 0) or 0) > 0)
                fwd_pnl = sum(t.get("pnl_pct", 0) or 0 for t in fwd_trades if isinstance(t, dict))

                bt_trades = bm.get("total_trades", 0) or 0
                bt_wr = bm.get("win_rate", 0) or 0
                bt_wins = int(bt_trades * (bt_wr / 100.0 if bt_wr > 1 else bt_wr))

                strategies.append({
                    "name": s.get("name", s.get("strategy_name", "unknown")),
                    "source": "baby_strategies",
                    "source_type": "forward" if fwd_trades else "backtest",
                    "trades": len(fwd_trades) if fwd_trades else bt_trades,
                    "wins": fwd_wins if fwd_trades else bt_wins,
                    "losses": (len(fwd_trades) - fwd_wins) if fwd_trades else (bt_trades - bt_wins),
                    "win_rate": bt_wr / 100.0 if bt_wr > 1 else bt_wr,
                    "forward_win_rate": (fm.get("win_rate", 0) or 0) / 100.0 if (fm.get("win_rate", 0) or 0) > 1 else fm.get("win_rate", 0),
                    "forward_trades": len(fwd_trades),
                    "forward_pnl_pct": fwd_pnl,
                    "avg_pnl_pct": (bm.get("total_return", 0) or 0) / max(bt_trades, 1) if bt_trades else 0,
                    "total_pnl_pct": bm.get("total_return", 0) or 0,
                    "sharpe": bm.get("sharpe", 0) or 0,
                    "max_drawdown": bm.get("max_drawdown", 0) or 0,
                    "profit_factor": bm.get("profit_factor", 0) or 0,
                    "p_value": 1.0,
                    "status": s.get("status", "unknown"),
                    "stage": s.get("stage", 0),
                    "category": s.get("category", ""),
                    "live_picks": s.get("forward_live_pick_count", 0) or 0,
                })

    # Also try tiered backtest results
    tiered_files = sorted(BABY_TIERED.glob("tiered_backtest_results_*.json"), reverse=True)
    if tiered_files:
        tiered = _safe_json_load(tiered_files[0])
        if tiered and isinstance(tiered, dict):
            existing_names = {s["name"] for s in strategies}
            for tier_name, tier_data in tiered.items():
                if not isinstance(tier_data, dict):
                    continue
                for strat_name, pair_results in tier_data.items():
                    if strat_name in existing_names or not isinstance(pair_results, dict):
                        continue
                    # Aggregate across pairs
                    total_trades = 0
                    total_wins = 0
                    total_losses = 0
                    sharpes = []
                    for pair, res in pair_results.items():
                        if not isinstance(res, dict):
                            continue
                        total_trades += res.get("trades", 0)
                        total_wins += res.get("wins", 0)
                        total_losses += res.get("losses", 0)
                        if res.get("sharpe_ratio"):
                            sharpes.append(res["sharpe_ratio"])
                    if total_trades > 0:
                        strategies.append({
                            "name": strat_name,
                            "source": "baby_strategies",
                            "source_type": "tiered_backtest",
                            "trades": total_trades,
                            "wins": total_wins,
                            "losses": total_losses,
                            "win_rate": total_wins / max(total_trades, 1),
                            "sharpe": sum(sharpes) / max(len(sharpes), 1) if sharpes else 0,
                            "p_value": 1.0,
                        })

    return strategies


def load_incubator_results() -> list[dict]:
    """Load incubator agent backtest results from CSV/JSON files."""
    strategies = []

    if not INCUBATOR_RESULTS.exists():
        return strategies

    # JSON results
    for jf in INCUBATOR_RESULTS.glob("*.json"):
        data = _safe_json_load(jf)
        if not data:
            continue
        # Support all JSON formats: raw list, {"results": [...]}, {"rows": [...]}
        if isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            results = data.get("results", data.get("rows", []))
        else:
            results = []
        if not isinstance(results, list):
            continue
        for r in results:
            if not isinstance(r, dict):
                continue
            strategies.append({
                "name": r.get("strategy_name", r.get("strategy", jf.stem)),
                "source": "incubator",
                "source_type": "agent_backtest",
                "source_file": jf.name,
                "trades": r.get("total_trades", 0),
                "wins": int(r.get("total_trades", 0) * r.get("win_rate", 0)) if r.get("win_rate") else 0,
                "win_rate": r.get("win_rate", 0),
                "sharpe": r.get("sharpe", r.get("sharpe_ratio", 0)),
                "max_drawdown": r.get("max_drawdown", 0),
                "profit_factor": r.get("profit_factor", 0),
                "total_return": r.get("total_return", 0),
                "p_value": 1.0,
                "pair": r.get("pair", ""),
            })

    # CSV summary files
    for cf in INCUBATOR_RESULTS.glob("*_summary.csv"):
        try:
            with open(cf, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    strategies.append({
                        "name": row.get("strategy_name", row.get("strategy", cf.stem)),
                        "source": "incubator",
                        "source_type": "agent_backtest_csv",
                        "source_file": cf.name,
                        "trades": int(row.get("total_trades", 0)),
                        "win_rate": float(row.get("win_rate", 0)),
                        "sharpe": float(row.get("sharpe", row.get("sharpe_ratio", 0))),
                        "max_drawdown": float(row.get("max_drawdown", 0)),
                        "profit_factor": float(row.get("profit_factor", 0)),
                        "p_value": 1.0,
                    })
        except Exception:
            continue

    return strategies


def load_kimi_performance() -> list[dict]:
    """Load KIMI algorithm performance from SQLite databases."""
    strategies = []

    conn = _safe_db_connect(KIMI_DB)
    if conn:
        try:
            # First try to get table names
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

            # Look for aggregated performance tables first
            for table in ["algorithm_performance", "algorithms"]:
                if table not in tables:
                    continue
                try:
                    all_rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                    for r in all_rows:
                        rd = dict(r)
                        strategies.append({
                            "name": rd.get("algorithm", rd.get("name", rd.get("strategy", "kimi_unknown"))),
                            "source": "kimi_rotc",
                            "source_type": "live_scanner",
                            "trades": rd.get("total_trades", rd.get("trades", 0)),
                            "wins": rd.get("wins", 0),
                            "losses": rd.get("losses", 0),
                            "win_rate": rd.get("win_rate", 0),
                            "sharpe": rd.get("sharpe", 0),
                            "p_value": 1.0,
                        })
                    break
                except Exception:
                    continue
            else:
                # No aggregated table — try to aggregate from signals table
                for table in tables:
                    if "signal" not in table.lower():
                        continue
                    # Get column names to find the strategy/algorithm column
                    try:
                        cols = [desc[1] for desc in conn.execute(f"PRAGMA table_info({table})").fetchall()]
                        strat_col = None
                        for candidate in ["algorithm", "strategy", "algo_name", "signal_type"]:
                            if candidate in cols:
                                strat_col = candidate
                                break
                        if not strat_col:
                            continue

                        pnl_col = "pnl_pct" if "pnl_pct" in cols else None
                        outcome_col = "outcome" if "outcome" in cols else None

                        if pnl_col:
                            win_expr = f"SUM(CASE WHEN {pnl_col} > 0 THEN 1 ELSE 0 END)"
                        elif outcome_col:
                            win_expr = f"SUM(CASE WHEN {outcome_col}='WIN' OR {outcome_col}='TP_HIT' THEN 1 ELSE 0 END)"
                        else:
                            continue

                        rows = conn.execute(f"""
                            SELECT {strat_col} as strategy, COUNT(*) as trades, {win_expr} as wins
                            FROM {table}
                            WHERE {strat_col} IS NOT NULL
                            GROUP BY {strat_col}
                            HAVING trades >= 3
                        """).fetchall()
                        for r in rows:
                            rd = dict(r)
                            t = rd.get("trades", 0) or 0
                            w = rd.get("wins", 0) or 0
                            strategies.append({
                                "name": rd.get("strategy", "kimi_algo"),
                                "source": "kimi_rotc",
                                "source_type": "live_aggregated",
                                "trades": t,
                                "wins": w,
                                "losses": t - w,
                                "win_rate": w / max(t, 1),
                                "p_value": 1.0,
                            })
                        if strategies:
                            break
                    except Exception:
                        continue
        finally:
            conn.close()

    # Signal tracker DB — individual trade outcomes
    conn = _safe_db_connect(SIGNAL_TRACKER_DB)
    if conn:
        try:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for table in tables:
                if "signal" in table.lower() or "track" in table.lower():
                    try:
                        rows = conn.execute(f"""
                            SELECT strategy, COUNT(*) as trades,
                                   SUM(CASE WHEN outcome='WIN' OR pnl_pct > 0 THEN 1 ELSE 0 END) as wins
                            FROM {table}
                            WHERE strategy IS NOT NULL
                            GROUP BY strategy
                        """).fetchall()
                        for r in rows:
                            rd = dict(r)
                            t = rd.get("trades", 0)
                            w = rd.get("wins", 0)
                            strategies.append({
                                "name": rd.get("strategy", "kimi_tracked"),
                                "source": "kimi_signal_tracker",
                                "source_type": "live_validated",
                                "trades": t,
                                "wins": w,
                                "losses": t - w,
                                "win_rate": w / max(t, 1),
                                "p_value": 1.0,
                            })
                    except Exception:
                        continue
        finally:
            conn.close()

    return strategies


def load_genome_results() -> list[dict]:
    """Load evolved DNA genome results from quant_lab."""
    strategies = []

    if not GENOME_RESULTS.exists():
        return strategies

    # Get latest genome results file
    result_files = sorted(GENOME_RESULTS.glob("genome_results_*.json"), reverse=True)
    if not result_files:
        return strategies

    data = _safe_json_load(result_files[0])
    if not data:
        return strategies

    genomes = data if isinstance(data, list) else data.get("genomes", data.get("results", []))
    if not isinstance(genomes, list):
        return strategies

    for g in genomes:
        if not isinstance(g, dict):
            continue
        strategies.append({
            "name": g.get("name", g.get("dna_id", "dna_unknown")),
            "source": "dna_genome",
            "source_type": "evolved",
            "trades": g.get("trades", 0),
            "wins": int(g.get("trades", 0) * g.get("win_rate", 0)),
            "win_rate": g.get("win_rate", 0),
            "sharpe": g.get("sharpe", 0),
            "max_drawdown": g.get("max_dd", 0),
            "total_pnl_pct": g.get("total_pnl", 0),
            "fitness_score": g.get("fitness_score", 0),
            "generation": g.get("generation", 0),
            "origin": g.get("origin", ""),
            "signals": g.get("signals", []),
            "gate": g.get("gate", ""),
            "combiner": g.get("combiner", ""),
            "p_value": 1.0,
        })

    return strategies


def load_forward_tests() -> list[dict]:
    """Load forward test outcomes from incubator forward_test.db."""
    strategies = []

    conn = _safe_db_connect(FORWARD_TEST_DB)
    if not conn:
        return strategies

    try:
        # Method 1: Read aggregated metrics from `strategies` table (correct schema)
        try:
            rows = conn.execute("""
                SELECT strategy_name, forward_win_rate, forward_sharpe,
                       forward_max_dd, forward_pnl_pct, forward_trades_count,
                       forward_days, status, graduation_score
                FROM strategies
                WHERE forward_trades_count > 0
            """).fetchall()
            for r in rows:
                rd = dict(r)
                trades = rd.get("forward_trades_count", 0) or 0
                wr = rd.get("forward_win_rate", 0) or 0
                if wr > 1.0:
                    wr = wr / 100.0
                wins = int(trades * wr)
                strategies.append({
                    "name": rd.get("strategy_name", "fwd_unknown"),
                    "source": "forward_test",
                    "source_type": "forward_validated",
                    "trades": trades,
                    "wins": wins,
                    "losses": trades - wins,
                    "win_rate": wr,
                    "sharpe": rd.get("forward_sharpe"),
                    "max_dd": rd.get("forward_max_dd"),
                    "pnl": rd.get("forward_pnl_pct"),
                    "p_value": 1.0,
                    "status": rd.get("status", "unknown"),
                    "graduation_score": rd.get("graduation_score"),
                    "forward_days": rd.get("forward_days", 0),
                })
        except Exception:
            pass

        # Method 2: Also count actual trades from `forward_trades` table
        try:
            rows = conn.execute("""
                SELECT strategy_name, COUNT(*) as trades,
                       SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                       AVG(pnl_pct) as avg_pnl
                FROM forward_trades
                WHERE strategy_name IS NOT NULL
                GROUP BY strategy_name
                HAVING trades >= 1
            """).fetchall()
            existing = {s["name"] for s in strategies}
            for r in rows:
                rd = dict(r)
                name = rd.get("strategy_name", "fwd_unknown")
                if name in existing:
                    continue  # already have aggregated data
                t = rd.get("trades", 0)
                w = rd.get("wins", 0)
                strategies.append({
                    "name": name,
                    "source": "forward_test",
                    "source_type": "forward_validated",
                    "trades": t,
                    "wins": w,
                    "losses": t - w,
                    "win_rate": w / max(t, 1),
                    "pnl": rd.get("avg_pnl"),
                    "p_value": 1.0,
                })
        except Exception:
            pass

    finally:
        conn.close()

    return strategies


def load_combo_metrics() -> list[dict]:
    """Load meta-strategy combo metrics from battleground."""
    strategies = []

    data = _safe_json_load(COMBO_METRICS)
    if not data or not isinstance(data, dict):
        return strategies

    winners = data.get("winners", [])
    if not isinstance(winners, list):
        return strategies

    for w in winners:
        if not isinstance(w, dict):
            continue
        strategies.append({
            "name": w.get("combo_id", "combo_unknown"),
            "source": "meta_combos",
            "source_type": "permutation_backtest",
            "trades": w.get("total_trades", 0),
            "wins": int(w.get("total_trades", 0) * w.get("win_rate", 0)),
            "win_rate": w.get("win_rate", 0),
            "sharpe": w.get("sharpe", 0),
            "sortino": w.get("sortino", 0),
            "max_drawdown": w.get("max_drawdown_pct", 0),
            "profit_factor": w.get("profit_factor", 0),
            "kelly_pct": w.get("kelly_pct", 0),
            "p_value": w.get("p_value", 1.0),
            "systems": w.get("systems", []),
            "logic_type": w.get("logic_type", ""),
        })

    return strategies


def load_permutation_results() -> list[dict]:
    """Load quant_lab permutation results (GOLD/SILVER/BRONZE combos)."""
    strategies = []

    data = _safe_json_load(PERMUTATION_RESULTS)
    if not data:
        return strategies

    # Handle both dict-with-tiers and flat-list formats
    combos = []
    if isinstance(data, dict):
        for tier_name, tier_combos in data.items():
            if isinstance(tier_combos, list):
                for c in tier_combos:
                    if isinstance(c, dict):
                        c["tier"] = tier_name
                        combos.append(c)
    elif isinstance(data, list):
        combos = [c for c in data if isinstance(c, dict)]

    for c in combos:
        strategies.append({
            "name": c.get("combo_name", c.get("combo_id", "perm_unknown")),
            "source": "quant_lab_combos",
            "source_type": "permutation_backtest",
            "tier": c.get("tier", ""),
            "trades": c.get("total_trades", 0),
            "wins": c.get("wins", 0),
            "losses": c.get("losses", 0),
            "win_rate": c.get("win_rate", 0),
            "sharpe": c.get("sharpe", 0),
            "profit_factor": c.get("profit_factor", 0),
            "expectancy": c.get("expectancy", 0),
            "kelly_pct": c.get("kelly_pct", 0),
            "calmar_ratio": c.get("calmar_ratio", 0),
            "p_value": 1.0,
        })

    return strategies


# ── Unified catalog builder ──────────────────────────────────────


def build_unified_catalog() -> dict:
    """Load ALL strategy data from every system and build unified catalog.

    Returns:
        {
            "generated_at": "...",
            "total_strategies": N,
            "by_source": {"alpha_engine": N, "baby_strategies": N, ...},
            "strategies": [... unified strategy dicts ...],
            "summary": {
                "sources_loaded": N,
                "total_trades_tracked": N,
                "avg_win_rate": X,
                "edge_strategies": N,
                "trap_strategies": N,
            }
        }
    """
    all_strategies = []

    print("Loading Alpha Engine strategies...")
    alpha = load_alpha_engine()
    all_strategies.extend(alpha)
    print(f"  -> {len(alpha)} strategies")

    print("Loading Baby Strategies...")
    babies = load_baby_strategies()
    all_strategies.extend(babies)
    print(f"  -> {len(babies)} strategies")

    print("Loading Incubator agent results...")
    incubator = load_incubator_results()
    all_strategies.extend(incubator)
    print(f"  -> {len(incubator)} strategies")

    print("Loading KIMI performance...")
    kimi = load_kimi_performance()
    all_strategies.extend(kimi)
    print(f"  -> {len(kimi)} strategies")

    print("Loading DNA Genome results...")
    genomes = load_genome_results()
    all_strategies.extend(genomes)
    print(f"  -> {len(genomes)} strategies")

    print("Loading Forward test results...")
    forward = load_forward_tests()
    all_strategies.extend(forward)
    print(f"  -> {len(forward)} strategies")

    print("Loading Meta-Combo metrics...")
    combos = load_combo_metrics()
    all_strategies.extend(combos)
    print(f"  -> {len(combos)} strategies")

    print("Loading Quant Lab permutation results...")
    perms = load_permutation_results()
    all_strategies.extend(perms)
    print(f"  -> {len(perms)} strategies")

    # Normalize win_rate to 0-1 range (some sources use 0-100)
    for s in all_strategies:
        wr = s.get("win_rate", 0) or 0
        if wr > 1.0:
            s["win_rate"] = wr / 100.0

    # Deduplicate by name+source (keep richest entry)
    seen = {}
    for s in all_strategies:
        key = f"{s['name']}|{s['source']}"
        existing = seen.get(key)
        if existing is None or (s.get("trades", 0) or 0) > (existing.get("trades", 0) or 0):
            seen[key] = s

    deduped = list(seen.values())

    # Classify each strategy
    for s in deduped:
        s["verdict"] = _classify_strategy(s)

    # Build summary
    by_source = {}
    for s in deduped:
        src = s.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1

    total_trades = sum(s.get("trades", 0) for s in deduped)
    win_rates = [s.get("win_rate", 0) or 0 for s in deduped if s.get("trades", 0) and s.get("trades", 0) > 0]

    verdicts = {}
    for s in deduped:
        v = s.get("verdict", "UNKNOWN")
        verdicts[v] = verdicts.get(v, 0) + 1

    catalog = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_strategies": len(deduped),
        "by_source": by_source,
        "verdicts": verdicts,
        "strategies": deduped,
        "summary": {
            "sources_loaded": len(by_source),
            "total_trades_tracked": total_trades,
            "avg_win_rate": sum(win_rates) / max(len(win_rates), 1) if win_rates else 0,
            "edge_strategies": verdicts.get("EDGE", 0) + verdicts.get("EDGE*", 0),
            "asymmetric_strategies": verdicts.get("ASYMMETRIC", 0),
            "trap_strategies": verdicts.get("TRAP", 0) + verdicts.get("DEAD", 0),
        },
    }

    return catalog


def _classify_strategy(s: dict) -> str:
    """Classify strategy as EDGE/ASYMMETRIC/MARGINAL/TRAP/DEAD."""
    trades = s.get("trades", 0)
    if trades < 3:
        return "INSUFFICIENT"

    wr = s.get("win_rate", 0) or 0
    sharpe = s.get("sharpe", 0) or 0
    avg_pnl = s.get("avg_pnl_pct", 0) or 0
    pf = s.get("profit_factor", 0) or 0

    # Compute expectancy if we have enough data
    wins = s.get("wins", 0)
    losses = s.get("losses", 0)
    total_pnl = s.get("total_pnl_pct", avg_pnl * trades)

    if total_pnl > 0 and sharpe > 0.5 and wr > 0.5:
        if trades < 10:
            return "EDGE*"
        return "EDGE"

    if total_pnl > 0 and wr < 0.4:
        return "ASYMMETRIC"

    if total_pnl > 0 or (sharpe > 0 and wr > 0.45):
        return "MARGINAL"

    if total_pnl < -20 or sharpe < -1:
        return "DEAD"

    return "TRAP"


# ── DB injection for genome seeding ──────────────────────────────


def inject_into_genome_db(catalog: dict, dry_run: bool = False) -> int:
    """Inject unified catalog entries into meta_strategy.db for genome seeding.

    Creates permutation entries for each strategy so the genome evolution
    can discover and recombine them.

    Returns number of entries injected.
    """
    from meta_strategy.db import get_db, register_permutation, save_result

    conn = get_db()
    injected = 0

    for s in catalog.get("strategies", []):
        source = s.get("source", "unknown")
        name = s.get("name", "unknown")
        combo_id = f"UNI:{source}:{name}"
        trades = s.get("trades", 0)

        if trades < 1:
            continue

        if dry_run:
            wr_val = s.get('win_rate', 0) or 0
            print(f"  [DRY] Would inject: {combo_id} ({trades} trades, WR={wr_val:.1%})")
            injected += 1
            continue

        # Register as a permutation
        register_permutation(
            conn,
            combo_id=combo_id,
            systems=[source],
            logic_type="unified_catalog",
            parameters={"original_name": name, "source_type": s.get("source_type", "")},
        )

        # Save performance metrics
        metrics = {
            "total_trades": trades,
            "wins": s.get("wins", 0),
            "losses": s.get("losses", 0),
            "win_rate": s.get("win_rate", 0),
            "avg_pnl_pct": s.get("avg_pnl_pct", 0),
            "total_pnl_pct": s.get("total_pnl_pct", 0),
            "sharpe": s.get("sharpe", 0),
            "sortino": s.get("sortino", 0),
            "max_drawdown_pct": s.get("max_drawdown", 0),
            "profit_factor": s.get("profit_factor", 0),
            "p_value": s.get("p_value", 1.0),
            "kelly_pct": s.get("kelly_pct", s.get("kelly_fraction", 0)),
            "is_significant": 1 if s.get("p_value", 1) < 0.05 else 0,
            "is_winner": 1 if s.get("verdict") in ("EDGE", "EDGE*", "ASYMMETRIC") else 0,
            "eval_period": f"unified_load_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        }
        save_result(conn, combo_id, symbol=None, metrics=metrics)
        injected += 1

    conn.close()
    return injected


# ── Main ─────────────────────────────────────────────────────────


def main():
    import sys
    dry_run = "--dry" in sys.argv

    print("=" * 60)
    print("UNIFIED PERFORMANCE LOADER — Building Complete Strategy Catalog")
    print("=" * 60)

    catalog = build_unified_catalog()

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {catalog['total_strategies']} strategies from {len(catalog['by_source'])} sources")
    print(f"By source: {json.dumps(catalog['by_source'], indent=2)}")
    print(f"Verdicts:  {json.dumps(catalog['verdicts'], indent=2)}")
    print(f"Total trades tracked: {catalog['summary']['total_trades_tracked']:,}")
    print(f"Avg win rate: {catalog['summary']['avg_win_rate']:.1%}")
    print(f"Edge strategies: {catalog['summary']['edge_strategies']}")
    print(f"Asymmetric: {catalog['summary']['asymmetric_strategies']}")
    print(f"Trap/Dead: {catalog['summary']['trap_strategies']}")

    # Save unified catalog JSON
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(UNIFIED_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, default=str)
    print(f"\nSaved catalog to: {UNIFIED_OUTPUT}")

    # Inject into genome DB
    print(f"\n{'Injecting' if not dry_run else '[DRY RUN] Would inject'} into meta_strategy.db...")
    count = inject_into_genome_db(catalog, dry_run=dry_run)
    print(f"{'Injected' if not dry_run else 'Would inject'}: {count} entries")

    print(f"\n{'=' * 60}")
    print("Done. Genome evolution can now seed from ALL system data.")


if __name__ == "__main__":
    main()
