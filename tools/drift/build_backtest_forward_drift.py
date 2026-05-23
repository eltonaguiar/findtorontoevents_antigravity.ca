#!/usr/bin/env python3
"""Build canonical backtest-vs-forward drift report.

This script joins forward performance from dashboard picks with backtest baselines
from collect_strategy_leaderboard, then emits a normalized drift artifact used by
validation and scoring layers.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any


def _safe_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _normalize_ac(v: str | None) -> str:
    if not v:
        return "UNKNOWN"
    x = str(v).upper().strip()
    if x in ("STOCK", "STOCKS"):
        return "EQUITY"
    return x


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists():
            return None
        return _read_json(path)
    except Exception:
        return None


def _build_strategy_asset_map(active: list[dict], closed: list[dict], systems: list[dict]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)

    for pick in [*active, *closed]:
        strat = str(pick.get("strategy") or "").strip()
        if not strat:
            continue
        out[strat].add(_normalize_ac(pick.get("asset_class")))

    for s in systems:
        name = str(s.get("name") or "").strip()
        if not name:
            continue
        acs = s.get("asset_classes") or []
        if isinstance(acs, list):
            for ac in acs:
                out[name].add(_normalize_ac(ac))

    return out


def _median_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return float(round(median(values), 2))


def _load_backtest_baselines(repo_root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}

    # Source 1: survivor backtest results
    survivor = _safe_read_json(repo_root / "alpha_engine/data/survivor_backtest_results.json") or {}
    for name, r in (survivor.get("results") or {}).items():
        if not isinstance(r, dict):
            continue
        out[str(name)] = {
            "bt_wr": _safe_float(r.get("win_rate_pct")),
            "bt_pf": _safe_float(r.get("profit_factor")),
            "bt_n": int(r.get("total_trades") or 0),
            "source": "survivor_backtest_results",
        }

    # Source 2: baby strats dashboard backtest metrics
    bsd = _safe_read_json(repo_root / "battleground/data/baby_strats_dashboard.json") or {}
    for s in (bsd.get("strategies") or []):
        if not isinstance(s, dict):
            continue
        name = str(s.get("name") or "").strip()
        if not name:
            continue
        bm = s.get("backtest_metrics") or {}
        bt_n = int(bm.get("total_trades") or 0)
        bt_wr = _safe_float(bm.get("win_rate"))
        if bt_wr is not None and 0 < bt_wr <= 1:
            bt_wr *= 100
        bt_pf = _safe_float(bm.get("profit_factor"))
        if name not in out or (out[name].get("bt_n") or 0) <= 0:
            out[name] = {
                "bt_wr": bt_wr,
                "bt_pf": bt_pf,
                "bt_n": bt_n,
                "source": "baby_strats_dashboard",
            }

    # Source 3: KIMI backtest rankings
    rankings = _safe_read_json(repo_root / "KIMI_RISEOFTHECLAW/data/backtest_rankings.json")
    if isinstance(rankings, dict):
        rankings_list = rankings.get("rankings") or rankings.get("results") or []
    elif isinstance(rankings, list):
        rankings_list = rankings
    else:
        rankings_list = []
    for r in rankings_list:
        if not isinstance(r, dict):
            continue
        name = str(r.get("strategy_id") or r.get("id") or r.get("name") or "").strip()
        if not name:
            continue
        bt_n = int(r.get("total_trades") or r.get("trades") or 0)
        bt_wr = _safe_float(r.get("win_rate") or r.get("win_rate_pct"))
        bt_pf = _safe_float(r.get("profit_factor"))
        if name not in out or (out[name].get("bt_n") or 0) <= 0:
            out[name] = {
                "bt_wr": bt_wr,
                "bt_pf": bt_pf,
                "bt_n": bt_n,
                "source": "backtest_rankings",
            }

    # Source 4: walk-forward aggregate_oos rollup
    wf = _safe_read_json(repo_root / "alpha_engine/data/walk_forward_results.json") or {}
    strategies = wf.get("strategies") or {}
    if isinstance(strategies, dict):
        for strat_name, strat_blob in strategies.items():
            if not isinstance(strat_blob, dict):
                continue
            per_symbol = strat_blob.get("per_symbol") or {}
            weighted_wr = 0.0
            weighted_pf = 0.0
            total_n = 0
            for sym_blob in per_symbol.values():
                if not isinstance(sym_blob, dict):
                    continue
                oos = sym_blob.get("aggregate_oos") or {}
                n = int(oos.get("total_trades") or 0)
                wr = _safe_float(oos.get("win_rate"))
                pf = _safe_float(oos.get("profit_factor"))
                if n <= 0 or wr is None:
                    continue
                weighted_wr += wr * n
                weighted_pf += (pf or 0.0) * n
                total_n += n
            if total_n > 0:
                out.setdefault(str(strat_name), {})
                if (out[str(strat_name)].get("bt_n") or 0) <= 0:
                    out[str(strat_name)] = {
                        "bt_wr": round(weighted_wr / total_n, 2),
                        "bt_pf": round(weighted_pf / total_n, 3) if weighted_pf > 0 else None,
                        "bt_n": total_n,
                        "source": "walk_forward_results",
                    }

    return out


def _compute_forward_stats(active: list[dict], closed: list[dict]) -> dict[str, dict[str, Any]]:
    by_strategy: dict[str, dict[str, Any]] = {}
    for p in closed:
        strat = str(p.get("strategy") or "").strip()
        if not strat:
            continue
        by_strategy.setdefault(
            strat,
            {
                "fw_n": 0,
                "wins": 0,
                "losses": 0,
                "flat": 0,
                "total_pnl": 0.0,
                "asset_classes": set(),
            },
        )
        row = by_strategy[strat]
        pnl = _safe_float(p.get("pnl_pct"))
        if pnl is None:
            continue
        row["fw_n"] += 1
        row["total_pnl"] += pnl
        if pnl > 0:
            row["wins"] += 1
        elif pnl < 0:
            row["losses"] += 1
        else:
            row["flat"] += 1
        row["asset_classes"].add(_normalize_ac(p.get("asset_class")))

    # Include asset classes from active picks for sparse strategies
    for p in active:
        strat = str(p.get("strategy") or "").strip()
        if not strat:
            continue
        by_strategy.setdefault(
            strat,
            {
                "fw_n": 0,
                "wins": 0,
                "losses": 0,
                "flat": 0,
                "total_pnl": 0.0,
                "asset_classes": set(),
            },
        )
        by_strategy[strat]["asset_classes"].add(_normalize_ac(p.get("asset_class")))

    # Derive win rate
    for strat, row in by_strategy.items():
        n = int(row.get("fw_n") or 0)
        wins = int(row.get("wins") or 0)
        row["fw_wr"] = round(100.0 * wins / n, 2) if n > 0 else None
        row["total_pnl"] = round(float(row.get("total_pnl") or 0.0), 2)

    return by_strategy


def build_report(input_path: Path) -> dict[str, Any]:
    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}. "
            "Run the audit-dashboard pipeline first to generate dashboard_data.json."
        )
    payload = _read_json(input_path)
    picks = payload.get("picks") or {}
    active = picks.get("active") or []
    closed = picks.get("recent_closed") or []
    systems = payload.get("systems") or []

    repo_root = Path(__file__).resolve().parents[2]
    bt_baselines = _load_backtest_baselines(repo_root)
    forward = _compute_forward_stats(active, closed)
    strategy_ac_map = _build_strategy_asset_map(active, closed, systems)

    rows: list[dict[str, Any]] = []
    ac_group: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for name, s in forward.items():
        fw_n = int(s.get("fw_n") or 0)
        fw_wr = _safe_float(s.get("fw_wr"))
        if fw_n <= 0 or fw_wr is None:
            continue

        bt = bt_baselines.get(name, {})
        bt_n = int(bt.get("bt_n") or 0)
        bt_wr = _safe_float(bt.get("bt_wr"))
        bt_pf = _safe_float(bt.get("bt_pf"))
        fw_pf = None

        total_pnl = round(float(s.get("total_pnl") or 0.0), 2)
        wr_gap = round(fw_wr - bt_wr, 2) if bt_wr is not None and bt_n > 0 else None

        acs = sorted(strategy_ac_map.get(name) or {"UNKNOWN"})
        row = {
            "name": name,
            "asset_classes": ",".join(acs),
            "fw_wr": round(fw_wr, 2),
            "fw_n": fw_n,
            "fw_pf": round(fw_pf, 3) if fw_pf is not None else None,
            "bt_wr": round(bt_wr, 2) if bt_wr is not None else None,
            "bt_n": bt_n,
            "bt_pf": round(bt_pf, 3) if bt_pf is not None else None,
            "wr_gap": wr_gap,
            "total_pnl": total_pnl,
            "bt_source": bt.get("source"),
        }
        rows.append(row)
        for ac in acs:
            ac_group[ac].append(row)

    coverage_total = len(rows)
    coverage_with_bt = sum(1 for r in rows if r.get("bt_n", 0) > 0 and r.get("bt_wr") is not None)

    asset_class_summary: list[dict[str, Any]] = []
    for ac, ac_rows in sorted(ac_group.items(), key=lambda kv: kv[0]):
        fw_wrs = [float(r["fw_wr"]) for r in ac_rows if r.get("fw_wr") is not None]
        bt_wrs = [float(r["bt_wr"]) for r in ac_rows if r.get("bt_wr") is not None and (r.get("bt_n") or 0) > 0]
        gaps = [float(r["wr_gap"]) for r in ac_rows if r.get("wr_gap") is not None]

        avg_fw = round(sum(fw_wrs) / len(fw_wrs), 2) if fw_wrs else None
        avg_bt = round(sum(bt_wrs) / len(bt_wrs), 2) if bt_wrs else None
        avg_gap = round(sum(gaps) / len(gaps), 2) if gaps else None

        asset_class_summary.append(
            {
                "asset_class": ac,
                "systems": len(ac_rows),
                "avg_fw_wr": avg_fw,
                "avg_bt_wr": avg_bt,
                "avg_wr_gap": avg_gap,
                "median_wr_gap": _median_or_none(gaps),
                "negative_pnl_systems": sum(1 for r in ac_rows if (r.get("total_pnl") or 0) < 0),
                "high_drift_systems": sum(
                    1
                    for r in ac_rows
                    if r.get("wr_gap") is not None and r.get("wr_gap") <= -15 and (r.get("fw_n") or 0) >= 20
                ),
                "bt_coverage_pct": round(
                    100.0
                    * sum(1 for r in ac_rows if (r.get("bt_n") or 0) > 0 and r.get("bt_wr") is not None)
                    / max(1, len(ac_rows)),
                    2,
                ),
            }
        )

    top_wr_drift = sorted(
        rows,
        key=lambda r: (
            0 if r.get("wr_gap") is not None else 1,
            r.get("wr_gap") if r.get("wr_gap") is not None else 999.0,
            -float(r.get("fw_n") or 0),
        ),
    )[:50]

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(input_path).replace("\\", "/"),
        "integrity": {
            "strategies_total": coverage_total,
            "strategies_with_backtest": coverage_with_bt,
            "backtest_coverage_pct": round(100.0 * coverage_with_bt / max(1, coverage_total), 2),
        },
        "asset_class_summary": asset_class_summary,
        "top_wr_drift": top_wr_drift,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build backtest-vs-forward drift report")
    parser.add_argument("--input", default="audit_dashboard/data/dashboard_data.json")
    parser.add_argument("--output", default="tmp/backtest_forward_drift_analysis.json")
    parser.add_argument("--snapshot-dir", default="audit_dashboard/data/drift_snapshots")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    snapshot_dir = Path(args.snapshot_dir)

    if not input_path.exists():
        print(f"SKIP: {input_path} not found — dashboard_data.json is generated by the "
              "audit-dashboard pipeline. Drift telemetry will run after that pipeline completes.")
        # Write minimal skip artifact so downstream validation step doesn't crash
        output_path.parent.mkdir(parents=True, exist_ok=True)
        skip_report = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": str(input_path).replace("\\", "/"),
            "skipped": True,
            "reason": f"Input file not found: {input_path}",
            "integrity": {"strategies_total": 0, "strategies_with_backtest": 0, "backtest_coverage_pct": 0},
            "asset_class_summary": [],
            "top_wr_drift": [],
        }
        output_path.write_text(json.dumps(skip_report, indent=2), encoding="utf-8")
        print(f"Wrote skip artifact to {output_path}")
        return 0  # graceful skip, not a failure

    report = build_report(input_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snap_path = snapshot_dir / f"backtest_forward_drift_{ts}.json"
    shutil.copy2(output_path, snap_path)

    print(f"Wrote {output_path}")
    print(f"Snapshot {snap_path}")
    print(
        "Backtest coverage:",
        report["integrity"]["strategies_with_backtest"],
        "/",
        report["integrity"]["strategies_total"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
