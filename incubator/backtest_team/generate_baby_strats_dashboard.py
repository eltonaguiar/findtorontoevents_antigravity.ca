#!/usr/bin/env python3
"""
Generate Baby Strat Dashboard Data
=================================

Builds a fresh `baby_strats_dashboard.json` from:
1) Current strategy files under `incubator/agents/**`
2) Per-strategy metadata (`.meta.json`) when present
3) Latest real-data sweep results (`incubator/backtest_results/real_data_sweep_*.json`)

Outputs:
- `incubator/config/baby_strats_dashboard.json`
- `battleground/data/baby_strats_dashboard.json`
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[2]
AGENTS_ROOT = ROOT / "incubator" / "agents"
BABY_ROOT = ROOT / "baby_strategies"
SWEEP_ROOT = ROOT / "incubator" / "backtest_results"
OUTPUT_MAIN = ROOT / "incubator" / "config" / "baby_strats_dashboard.json"
OUTPUT_PUBLIC = ROOT / "battleground" / "data" / "baby_strats_dashboard.json"
DISABLED_FILE = ROOT / "stabilization" / "disabled_strategies.json"


def _load_disabled_strategies() -> set[str]:
    """Load disabled strategy names from stabilization/disabled_strategies.json."""
    if not DISABLED_FILE.exists():
        return set()
    try:
        data = json.loads(DISABLED_FILE.read_text(encoding="utf-8"))
        return set(data.get("disabled", []))
    except Exception:
        return set()


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _norm_pct(v: Any) -> Optional[float]:
    x = _safe_float(v)
    if x is None:
        return None
    if abs(x) <= 1.5:
        return round(x * 100.0, 2)
    return round(x, 2)


def _latest_sweep_file() -> Optional[Path]:
    files = sorted(SWEEP_ROOT.glob("real_data_sweep_*.json"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def _latest_directional_file() -> Optional[Path]:
    files = sorted(SWEEP_ROOT.glob("real_data_directional_*.json"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def _load_latest_sweep() -> Dict[Tuple[str, str], Dict[str, Any]]:
    f = _latest_sweep_file()
    if not f:
        return {}

    data = json.loads(f.read_text(encoding="utf-8"))
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for r in data.get("results", []):
        key = (str(r.get("agent_id", "")).strip(), str(r.get("strategy_name", "")).strip())
        if not all(key):
            continue
        out[key] = r
    return out


def _load_latest_directional() -> Dict[Tuple[str, str], Dict[str, Any]]:
    f = _latest_directional_file()
    if not f:
        return {}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {}

    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for p in data.get("profiles", []):
        key = (str(p.get("agent_id", "")).strip(), str(p.get("strategy_name", "")).strip())
        if not all(key):
            continue
        out[key] = p
    return out


def _map_status(meta_status: str, sweep_status: Optional[str], total_trades: int) -> str:
    meta_status = (meta_status or "").strip().lower()
    sweep_status = (sweep_status or "").strip().lower() if sweep_status else None

    # Preserve forward stage if already advanced.
    if meta_status in {"paper_trading", "graduated", "live"}:
        return meta_status

    if sweep_status == "passed":
        return "backtest_passed"
    if sweep_status == "failed_insufficient_trades":
        return "insufficient_data"
    if sweep_status == "failed":
        return "backtest_failed"
    if sweep_status in {"timeout", "error"}:
        return "backtest_error"

    if meta_status in {"backtest_passed"}:
        return "backtest_passed"
    if meta_status in {"backtest_failed", "failed"}:
        return "backtest_failed"
    if meta_status in {"awaiting_backtest", "backtest_pending", "validating", ""}:
        return "validating"

    # Conservative fallback.
    if total_trades and total_trades < 3:
        return "insufficient_data"
    return "validating"


def _read_meta(meta_path: Path) -> Dict[str, Any]:
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _norm_directional_metrics(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {
            "trades": 0,
            "win_rate": None,
            "sharpe": None,
            "max_drawdown": None,
            "profit_factor": None,
            "total_return": None,
        }
    return {
        "trades": int(raw.get("trades") or 0),
        "win_rate": _norm_pct(raw.get("win_rate")),
        "sharpe": _safe_float(raw.get("sharpe")),
        "max_drawdown": _norm_pct(raw.get("max_drawdown")),
        "profit_factor": _safe_float(raw.get("profit_factor")),
        "total_return": _norm_pct(raw.get("total_return")),
    }


def _normalize_daily_pnl_list(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []

    out: List[Dict[str, Any]] = []
    for x in raw:
        if not isinstance(x, dict):
            continue
        day = str(x.get("date") or "").strip()
        if not day:
            continue
        out.append(
            {
                "date": day,
                "pnl": round(float(x.get("pnl") or 0.0), 6),
                "pnl_pct": round(float(x.get("pnl_pct") or 0.0), 4),
                "trades": int(x.get("trades") or 0),
                "wins": int(x.get("wins") or 0),
                "losses": int(x.get("losses") or 0),
            }
        )
    return out


def _verification_payload(py_file: Path, meta: Dict[str, Any]) -> Dict[str, Any]:
    name = py_file.stem.lower()
    stype = str(meta.get("strategy_type", "")).lower()

    # Cross-asset helper feeds in real_data_sweep_runner are deterministic proxies from BTC.
    is_proxy_mixed = ("crossasset" in name) or ("cross_asset" in stype)

    if not is_proxy_mixed:
        try:
            src = py_file.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            src = ""
        is_proxy_mixed = any(tok in src for tok in ("spx_data", "dxy_data", "vix_data"))

    if is_proxy_mixed:
        return {
            "real_data_verified": False,
            "verification_level": "mixed_real_plus_proxy",
            "market_data_basis": "real_btc_ohlcv",
            "auxiliary_data_basis": "proxy_series_derived_from_btc",
            "note": "Cross-asset helpers (SPX/DXY/VIX) are proxy-derived in sweep runner.",
        }
    return {
        "real_data_verified": True,
        "verification_level": "real_market_data",
        "market_data_basis": "real_btc_ohlcv",
        "auxiliary_data_basis": "not_used",
        "note": "Backtest uses real BTC OHLCV from crypto_data.db.",
    }


def _build_strategy_entry(
    py_file: Path,
    sweep_map: Dict[Tuple[str, str], Dict[str, Any]],
    directional_map: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    agent_id = py_file.parent.name
    name = py_file.stem
    meta_path = Path(str(py_file) + ".meta.json")
    meta = _read_meta(meta_path)
    sweep = sweep_map.get((agent_id, name))
    directional = directional_map.get((agent_id, name))

    meta_metrics = meta.get("backtest_metrics", {}) if isinstance(meta.get("backtest_metrics"), dict) else {}

    # Prefer latest sweep metrics when available.
    if sweep:
        win_rate = _norm_pct(sweep.get("win_rate"))
        max_dd = _norm_pct(sweep.get("max_drawdown"))
        sharpe = _safe_float(sweep.get("sharpe"))
        trades = int(sweep.get("total_trades") or 0)
        pf = _safe_float(sweep.get("profit_factor"))
        total_return = _norm_pct(sweep.get("total_return"))
        status_raw = sweep.get("status")
        failure_reason = None
        if status_raw == "failed_insufficient_trades":
            failure_reason = f"Insufficient trades: {trades} (need >= 3)."
        elif status_raw == "timeout":
            failure_reason = sweep.get("error_message") or "Backtest timed out."
        elif status_raw == "error":
            failure_reason = sweep.get("error_message") or "Backtest error."
        elif status_raw == "failed":
            failure_reason = "Failed validation metrics (Sharpe / WR / Max DD gate)."
    else:
        win_rate = _norm_pct(meta_metrics.get("win_rate"))
        max_dd = _norm_pct(meta_metrics.get("max_drawdown"))
        sharpe = _safe_float(meta_metrics.get("sharpe"))
        trades = int(meta_metrics.get("total_trades") or 0)
        pf = _safe_float(meta_metrics.get("profit_factor"))
        total_return = _norm_pct(meta_metrics.get("total_return"))
        status_raw = None
        failure_reason = meta.get("failure_reason")

    status = _map_status(str(meta.get("status", "")), status_raw, trades)

    entry: Dict[str, Any] = {
        "name": name,
        "agent_id": agent_id,
        "category": meta.get("strategy_type", "unknown"),
        "status": status,
        "stage": 2 if status == "paper_trading" else 3 if status in {"graduated", "live"} else 0,
        "backtest_metrics": {
            "win_rate": win_rate,
            "sharpe": round(sharpe, 4) if sharpe is not None else None,
            "max_drawdown": max_dd,
            "total_trades": trades,
            "profit_factor": round(pf, 4) if pf is not None else None,
            "total_return": total_return,
            "period_days": 180,
            "data_source": "real_crypto_db",
            "updated_from": "real_data_sweep" if sweep else "meta_json",
        },
        "unique_value": meta.get("unique_value", f"Strategy by {agent_id}"),
        "verification": _verification_payload(py_file, meta),
    }

    if failure_reason and status in {"backtest_failed", "insufficient_data", "backtest_error"}:
        entry["failure_reason"] = failure_reason

    paper = meta.get("paper_trading")
    if isinstance(paper, dict):
        # Normalize names for dashboard consumption.
        entry["paper_trading"] = {
            "started_at": paper.get("started_at"),
            "end_date": paper.get("end_date"),
            "days_remaining": paper.get("days_remaining"),
            "days_elapsed": paper.get("days_elapsed"),
            "trades_count": paper.get("trades_count") or paper.get("total_trades") or 0,
            "current_pnl": paper.get("current_pnl"),
            "progress_pct": paper.get("progress_pct"),
        }
        paper_daily = _normalize_daily_pnl_list(paper.get("daily_pnl") or paper.get("daily"))
        if paper_daily:
            entry["forward_daily_pnl"] = paper_daily

    fwd = meta.get("forward_metrics", {}) if isinstance(meta.get("forward_metrics"), dict) else {}
    entry["forward_metrics"] = {
        "win_rate": _norm_pct(fwd.get("win_rate")),
        "sharpe": _safe_float(fwd.get("sharpe")),
        "max_drawdown": _norm_pct(fwd.get("max_drawdown")),
        "total_trades": int(fwd.get("total_trades") or 0),
    }
    entry["forward_live_pick_count"] = int(meta.get("forward_live_pick_count") or 0)
    if isinstance(meta.get("forward_live_picks"), list):
        entry["forward_live_picks"] = meta.get("forward_live_picks")
    explicit_forward_daily = _normalize_daily_pnl_list(meta.get("forward_daily_pnl"))
    if explicit_forward_daily:
        entry["forward_daily_pnl"] = explicit_forward_daily

    # Individual trade records for audit trail
    raw_trades = meta.get("forward_trades")
    if isinstance(raw_trades, list) and raw_trades:
        entry["forward_trades"] = raw_trades

    if directional:
        entry["directional_metrics"] = {
            "overall": _norm_directional_metrics(directional.get("overall", {})),
            "long": _norm_directional_metrics(directional.get("long", {})),
            "short": _norm_directional_metrics(directional.get("short", {})),
        }
        entry["daily_pnl"] = _normalize_daily_pnl_list(directional.get("daily_pnl"))

    return entry


def _discover_strategy_files(sweep_keys: set[Tuple[str, str]]) -> List[Path]:
    disabled = _load_disabled_strategies()
    out: List[Path] = []
    skipped = 0

    # Scan incubator/agents/**
    for p in sorted(AGENTS_ROOT.rglob("*.py")):
        s = str(p).replace("\\", "/")
        if "/__pycache__/" in s:
            continue
        if p.name.startswith("test_"):
            continue
        # Skip disabled strategies
        if p.stem in disabled:
            skipped += 1
            continue
        meta_exists = Path(str(p) + ".meta.json").exists()
        in_sweep = (p.parent.name, p.stem) in sweep_keys
        if not (meta_exists or in_sweep):
            continue
        out.append(p)

    # Also scan baby_strategies/
    if BABY_ROOT.exists():
        for p in sorted(BABY_ROOT.glob("*.py")):
            if p.name.startswith("test_") or p.name.startswith("__"):
                continue
            if p.stem in disabled:
                skipped += 1
                continue
            meta_exists = Path(str(p) + ".meta.json").exists()
            in_sweep = (p.parent.name, p.stem) in sweep_keys
            if not (meta_exists or in_sweep):
                continue
            out.append(p)

    if skipped:
        print(f"[GUARD] Filtered {skipped} disabled strategies from dashboard")
    return out


def _build_calendar_mode_summary(strategies: List[Dict[str, Any]], key: str, mode: str) -> Dict[str, Any]:
    by_day: Dict[str, Dict[str, Any]] = {}
    for s in strategies:
        for d in s.get(key, []) or []:
            day = str(d.get("date") or "").strip()
            if not day:
                continue
            bucket = by_day.setdefault(
                day,
                {
                    "date": day,
                    "pnl": 0.0,
                    "pnl_pct": 0.0,
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "strategies": 0,
                },
            )
            bucket["pnl"] += float(d.get("pnl") or 0.0)
            bucket["pnl_pct"] += float(d.get("pnl_pct") or 0.0)
            bucket["trades"] += int(d.get("trades") or 0)
            bucket["wins"] += int(d.get("wins") or 0)
            bucket["losses"] += int(d.get("losses") or 0)
            bucket["strategies"] += 1

    days = [by_day[k] for k in sorted(by_day.keys())]
    if not days:
        return {
            "available": False,
            "mode": mode,
            "days": [],
            "summary": {"trades": 0, "wins": 0, "losses": 0, "pnl_pct": 0.0},
        }

    for d in days:
        d["pnl"] = round(float(d["pnl"]), 6)
        d["pnl_pct"] = round(float(d["pnl_pct"]), 4)

    return {
        "available": True,
        "mode": mode,
        "days": days,
        "summary": {
            "trades": sum(int(x["trades"]) for x in days),
            "wins": sum(int(x["wins"]) for x in days),
            "losses": sum(int(x["losses"]) for x in days),
            "pnl_pct": round(sum(float(x["pnl_pct"]) for x in days), 4),
        },
    }


def _build_calendar_summary(strategies: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "backtest": _build_calendar_mode_summary(strategies, "daily_pnl", "backtest_real_data"),
        "forward": _build_calendar_mode_summary(strategies, "forward_daily_pnl", "forward_paper_or_live"),
    }


def _load_existing_dashboard() -> Dict[str, Any]:
    """Load existing dashboard to preserve bundle sections and other persistent data."""
    for p in (OUTPUT_PUBLIC, OUTPUT_MAIN):
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
    return {}


def generate_dashboard() -> Dict[str, Any]:
    sweep_map = _load_latest_sweep()
    directional_map = _load_latest_directional()
    files = _discover_strategy_files(set(sweep_map.keys()))
    strategies = [_build_strategy_entry(f, sweep_map, directional_map) for f in files]

    by_agent: Dict[str, int] = {}
    for s in strategies:
        by_agent[s["agent_id"]] = by_agent.get(s["agent_id"], 0) + 1

    real_verified = sum(1 for s in strategies if s.get("verification", {}).get("real_data_verified") is True)
    mixed_proxy = sum(1 for s in strategies if s.get("verification", {}).get("verification_level") == "mixed_real_plus_proxy")

    # Count disabled strategies for transparency
    disabled = _load_disabled_strategies()

    dashboard = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "strategy_files": len(files),
            "latest_sweep_file": str(_latest_sweep_file().relative_to(ROOT)) if _latest_sweep_file() else None,
            "latest_directional_file": str(_latest_directional_file().relative_to(ROOT)) if _latest_directional_file() else None,
        },
        "total_strategies": len(strategies),
        "disabled_count": len(disabled),
        "passed_backtest": sum(1 for s in strategies if s["status"] in {"backtest_passed", "paper_trading", "graduated", "live"}),
        "failed_backtest": sum(1 for s in strategies if s["status"] in {"backtest_failed", "insufficient_data", "backtest_error"}),
        "in_paper_trading": sum(1 for s in strategies if s["status"] == "paper_trading"),
        "forward_live_pick_strategies": sum(1 for s in strategies if int(s.get("forward_live_pick_count") or 0) > 0),
        "forward_live_picks_total": sum(int(s.get("forward_live_pick_count") or 0) for s in strategies),
        "graduated": sum(1 for s in strategies if s["status"] in {"graduated", "live"}),
        "verification_summary": {
            "real_data_verified": real_verified,
            "mixed_real_plus_proxy": mixed_proxy,
            "unverified": max(0, len(strategies) - real_verified - mixed_proxy),
            "note": "Cross-asset helpers in sweep runner use BTC-derived proxies for SPX/DXY/VIX.",
        },
        "status_definitions": {
            "backtest_passed": "Passed Stage 1 historical backtest gates on real market data.",
            "validating": "Not yet fully evaluated; awaiting or running validation.",
            "insufficient_data": "Backtest completed but produced too few trades for confidence.",
            "backtest_failed": "Backtest completed on historical data but failed Sharpe/WR/DD gates.",
            "backtest_error": "Backtest could not complete due to timeout, import, or runtime error.",
            "paper_trading": "Passed backtest and is now in Stage 2 forward paper testing.",
            "graduated": "Passed forward stage and promoted to Stage 3 graduated.",
            "live": "Graduated strategy currently active in live monitoring.",
        },
        "metric_mode_definitions": {
            "forward": "Forward-looking paper/live metrics (when available).",
            "backtest": "Historical backtest metrics from real-data sweep.",
        },
        "calendar": _build_calendar_summary(strategies),
        "strategies": strategies,
        "summary": {
            "total": len(strategies),
            "by_agent": by_agent,
        },
    }

    # ── Early Hatch Check: flag baby strategies ready for fast-track promotion ──
    # Added 2026-03-16: 150 strategies in paper trading, 0 graduated.
    # The 45-day minimum blocked all of them. This checks for exceptional performers
    # that can "hatch early" with stricter quality gates but relaxed time requirements.
    try:
        from incubator.testing.forward_test_tracker import EARLY_HATCH
        early_hatch_candidates = []
        for s in strategies:
            if s["status"] != "paper_trading":
                continue
            fwd = s.get("forward_trades", [])
            if not isinstance(fwd, list) or len(fwd) < 10:
                continue
            wins = sum(1 for t in fwd if (t.get("pnl_pct") or t.get("pnl", 0)) > 0)
            losses = len(fwd) - wins
            wr = wins / len(fwd) if fwd else 0
            pnl_sum = sum(t.get("pnl_pct") or t.get("pnl", 0) for t in fwd)
            avg_win = sum(t.get("pnl_pct") or t.get("pnl", 0) for t in fwd if (t.get("pnl_pct") or t.get("pnl", 0)) > 0) / max(wins, 1)
            avg_loss = abs(sum(t.get("pnl_pct") or t.get("pnl", 0) for t in fwd if (t.get("pnl_pct") or t.get("pnl", 0)) <= 0) / max(losses, 1))
            pf = (wr * avg_win) / ((1 - wr) * avg_loss) if avg_loss > 0 and wr < 1 else 0
            metrics = {
                "days_in_test": s.get("days_in_forward", 7),
                "trades_count": len(fwd),
                "win_rate": wr,
                "sharpe": (s.get("forward_metrics") or {}).get("sharpe", 0) or 0,
                "max_drawdown": abs((s.get("forward_metrics") or {}).get("max_drawdown", 0) or 0),
                "pnl_pct": pnl_sum,
                "profit_factor": pf,
                "walk_forward_validated": s.get("walk_forward_validated", False),
                "consensus_agreement": s.get("consensus_agreement", 0),
            }
            passed, reasons, hatch_type = EARLY_HATCH.check(metrics)
            if passed:
                s["status"] = "graduated"
                s["graduation_type"] = hatch_type
                s["graduation_metrics"] = metrics
                early_hatch_candidates.append(s["name"])
        if early_hatch_candidates:
            print(f"  EARLY HATCH: {len(early_hatch_candidates)} strategies graduated early: {', '.join(early_hatch_candidates)}")
        dashboard["early_hatched"] = len(early_hatch_candidates)
        dashboard["early_hatch_names"] = early_hatch_candidates
    except Exception as e:
        print(f"  [WARN] Early hatch check skipped: {e}")
        dashboard["early_hatched"] = 0
        dashboard["early_hatch_names"] = []

    # Recount graduated after early hatch
    dashboard["graduated"] = sum(1 for s in strategies if s["status"] in {"graduated", "live"})

    # Preserve bundle sections from existing dashboard (bundles are managed separately)
    existing = _load_existing_dashboard()
    for key in ("sections", "total_bundles", "last_updated", "tiered_backtest"):
        if key in existing:
            dashboard[key] = existing[key]

    return dashboard


def write_dashboard(payload: Dict[str, Any]) -> None:
    OUTPUT_MAIN.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2)
    OUTPUT_MAIN.write_text(text, encoding="utf-8")
    OUTPUT_PUBLIC.write_text(text, encoding="utf-8")


def main() -> int:
    payload = generate_dashboard()
    write_dashboard(payload)
    print(f"Wrote {payload['total_strategies']} strategies")
    print(f"Main:   {OUTPUT_MAIN}")
    print(f"Public: {OUTPUT_PUBLIC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
