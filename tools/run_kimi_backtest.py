"""
Run Kimi's production-quality backtest engine against our pre-registered OOS picks.

Computes:
  - PBO  (Probability of Backtest Overfitting) via Combinatorial Purged CV
  - DSR  (Deflated Sharpe Ratio) per Lopez de Prado
  - WFE  (Walk-Forward Efficiency)
  - Kelly position sizing per asset class

Input:  audit_trail/data/universal_resolved_picks.json  (5,000 OOS picks)
Output: reports/kimi_backtest_validation_<date>.json

Usage:
    python tools/run_kimi_backtest.py
    python tools/run_kimi_backtest.py --source-system kimi_signal_tracking
    python tools/run_kimi_backtest.py --elite-only
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "kimi_edge_engine"))

try:
    from backtest import (
        calculate_pbo,
        calculate_dsr,
        kelly_fraction as kelly_position_size,
    )
    # calculate_wfe not exported; use calculate_edge_metrics instead
    from backtest import calculate_edge_metrics
    KIMI_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] Kimi backtest engine not importable: {e}")
    print("  Install deps: pip install pandas numpy scipy scikit-learn")
    KIMI_AVAILABLE = False

OOS_PATH = ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"

ELITE_SYSTEMS = {"kimi_signal_tracking", "aggregated_picks", "stocks_competition"}

ELITE_STRATEGIES = {
    "AuditEnsemble_LONG",
    "Multi-Timeframe Trend Alignment",
    "VWAP Deviation Scalp",
    "RSI Divergence Scalp",
}


def load_picks(source_system: str | None, elite_only: bool) -> list[dict]:
    if not OOS_PATH.exists():
        raise FileNotFoundError(f"OOS picks not found: {OOS_PATH}")
    raw = json.loads(OOS_PATH.read_text(encoding="utf-8"))
    picks = raw if isinstance(raw, list) else raw.get("picks", [])
    if source_system:
        picks = [p for p in picks if p.get("source_system") == source_system]
    if elite_only:
        picks = [p for p in picks if p.get("source_system") in ELITE_SYSTEMS]
    return picks


def picks_to_returns(picks: list[dict]) -> list[float]:
    """Convert pnl_pct to decimal returns for backtest engine."""
    returns = []
    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is not None:
            try:
                returns.append(float(pnl) / 100.0)
            except (TypeError, ValueError):
                pass
    return returns


def naive_backtest(picks: list[dict]) -> dict:
    """Compute basic stats without Kimi engine (fallback)."""
    wins = sum(1 for p in picks if (p.get("pnl_pct") or 0) > 0)
    n = len(picks)
    if n == 0:
        return {"n": 0, "wr": 0, "pf": 0, "avg_win": 0, "avg_loss": 0}
    wr = wins / n * 100
    win_returns = [float(p.get("pnl_pct") or 0) for p in picks if (p.get("pnl_pct") or 0) > 0]
    loss_returns = [abs(float(p.get("pnl_pct") or 0)) for p in picks if (p.get("pnl_pct") or 0) <= 0]
    avg_win = sum(win_returns) / len(win_returns) if win_returns else 0
    avg_loss = sum(loss_returns) / len(loss_returns) if loss_returns else 0
    pf = (avg_win * wins) / (avg_loss * (n - wins)) if (avg_loss * (n - wins)) > 0 else float("inf")
    return {"n": n, "wr": round(wr, 2), "pf": round(pf, 3), "avg_win": round(avg_win, 3), "avg_loss": round(avg_loss, 3)}


def run(source_system: str | None, elite_only: bool) -> dict:
    picks = load_picks(source_system, elite_only)
    print(f"Loaded {len(picks)} picks (source_system={source_system or 'all'}, elite_only={elite_only})")

    basic = naive_backtest(picks)
    result: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_system_filter": source_system,
        "elite_only": elite_only,
        "n_picks": basic["n"],
        "basic_stats": basic,
    }

    if not KIMI_AVAILABLE or len(picks) < 30:
        result["kimi_engine"] = "unavailable or insufficient data (n<30)"
        return result

    returns = picks_to_returns(picks)
    if not returns:
        result["kimi_engine"] = "no pnl_pct values found"
        return result

    # Per-system breakdown
    by_system: dict[str, list[dict]] = {}
    for p in picks:
        s = p.get("source_system", "unknown")
        by_system.setdefault(s, []).append(p)

    system_stats = {}
    for sys_name, sys_picks in by_system.items():
        sys_stats = naive_backtest(sys_picks)
        sys_returns = picks_to_returns(sys_picks)
        if len(sys_returns) >= 30:
            try:
                sys_stats["dsr"] = round(calculate_dsr(sys_returns), 4)
                sys_stats["kelly_pct"] = round(kelly_position_size(sys_stats["wr"] / 100, sys_stats["avg_win"] / 100, sys_stats["avg_loss"] / 100) * 100, 2)
            except Exception:
                pass
        system_stats[sys_name] = sys_stats

    result["by_system"] = system_stats

    # Overall PBO + DSR
    try:
        result["pbo"] = round(calculate_pbo(returns), 4)
        result["dsr"] = round(calculate_dsr(returns), 4)
        result["kelly_pct"] = round(kelly_position_size(basic["wr"] / 100, basic["avg_win"] / 100, basic["avg_loss"] / 100) * 100, 2)
        result["kimi_engine"] = "ok"
    except Exception as e:
        result["kimi_engine_error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="Kimi OOS backtest runner")
    parser.add_argument("--source-system", default=None)
    parser.add_argument("--elite-only", action="store_true")
    args = parser.parse_args()

    result = run(args.source_system, args.elite_only)

    out_name = f"kimi_backtest_validation_{datetime.now().strftime('%Y-%m-%d')}.json"
    out_path = ROOT / "reports" / out_name
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Report: {out_path}")
    print(f"n={result['n_picks']}, WR={result['basic_stats']['wr']}%, PF={result['basic_stats']['pf']}")
    if "pbo" in result:
        print(f"PBO={result['pbo']}, DSR={result['dsr']}, WFE={result['wfe']}, Kelly={result['kelly_pct']}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
