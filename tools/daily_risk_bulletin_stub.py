#!/usr/bin/env python3
"""§6 Daily risk bulletin stub (Mercury / HEDGE_FUND plan).

Aggregates **real** risk signals into one JSON snapshot for humans / future dashboard:

  * **Dashboard headline** — ``summary`` block from ``dashboard_data.json`` (when present).
  * **Closed-trade tail metrics** — VaR/CVaR 95/99 on ``pnl_pct`` (same spirit as
    ``portfolio_risk_metrics.py``), trade-order max drawdown on cumulative ``pnl_pct``.
  * **Active book concentration** — counts by ``symbol`` (top ``--top-symbols``).
  * **Satellite reports** — optional passthrough summaries from existing tool outputs
    if files exist: ``tail_risk_es995_mdd``, ``rolling_cvar``, ``rolling_correlation``,
    ``stress_test``, ``concept_drift``, ``fdr_results`` (BH-FDR),
    ``regime_performance_btc``.

No invented numbers: missing files yield ``null`` / omitted keys.

Output: ``tools/data/daily_risk_bulletin.json``

Usage:
  python tools/daily_risk_bulletin_stub.py
  python tools/daily_risk_bulletin_stub.py --crypto-only --redis-alert
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "daily_risk_bulletin.json"


def compute_tail_block(pnl_array: np.ndarray) -> Dict[str, Any]:
    if len(pnl_array) == 0:
        return {"n_trades": 0}
    sorted_pnl = np.sort(pnl_array)
    n = len(sorted_pnl)
    var95 = float(np.percentile(sorted_pnl, 5))
    var99 = float(np.percentile(sorted_pnl, 1))
    cvar95 = (
        float(sorted_pnl[sorted_pnl <= var95].mean())
        if np.any(sorted_pnl <= var95)
        else var95
    )
    cvar99 = (
        float(sorted_pnl[sorted_pnl <= var99].mean())
        if np.any(sorted_pnl <= var99)
        else var99
    )
    cum = np.cumsum(pnl_array)
    peak = np.maximum.accumulate(cum)
    max_dd = float((cum - peak).min())
    return {
        "n_trades": int(n),
        "mean_pnl_pct": round(float(pnl_array.mean()), 4),
        "win_rate_pct": round(float(np.mean(pnl_array > 0)) * 100.0, 2),
        "VaR_95_pct": round(var95, 4),
        "VaR_99_pct": round(var99, 4),
        "CVaR_95_pct": round(cvar95, 4),
        "CVaR_99_pct": round(cvar99, 4),
        "max_drawdown_cum_pnl_pct_points": round(max_dd, 4),
        "worst_trade_pct": round(float(sorted_pnl[0]), 4),
        "best_trade_pct": round(float(sorted_pnl[-1]), 4),
    }


def safe_read_json(path: Path) -> Optional[Any]:
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def satellite_tail_risk(doc: Optional[Dict]) -> Optional[Dict[str, Any]]:
    if not doc or not isinstance(doc, dict):
        return None
    s = doc.get("summary")
    if not isinstance(s, dict):
        return None
    return {
        "latest_es_99_5_pct": s.get("latest_es_99_5_pct"),
        "latest_mdd_pct_points": s.get("latest_mdd_pct_points"),
        "rolling_windows": s.get("rolling_windows"),
    }


def satellite_rolling_cvar(doc: Optional[Dict]) -> Optional[Dict[str, Any]]:
    if not doc or not isinstance(doc, dict):
        return None
    s = doc.get("summary")
    if not isinstance(s, dict):
        return None
    return {
        "current_cvar95": s.get("current_cvar95"),
        "current_cvar99": s.get("current_cvar99"),
        "trend_95": s.get("trend_95"),
        "trend_99": s.get("trend_99"),
    }


def satellite_corr(doc: Optional[Dict]) -> Optional[Dict[str, Any]]:
    if not doc or not isinstance(doc, dict):
        return None
    s = doc.get("summary")
    if not isinstance(s, dict):
        return None
    return {
        "pairs_flagged_30d": s.get("pairs_flagged_30d"),
        "pairs_flagged_90d": s.get("pairs_flagged_90d"),
        "symbols_90d": s.get("symbols_90d"),
    }


def satellite_stress(doc: Optional[Dict]) -> Optional[Dict[str, Any]]:
    if not doc or not isinstance(doc, dict):
        return None
    scenarios = doc.get("scenarios")
    slim: List[Dict[str, Any]] = []
    if isinstance(scenarios, list):
        for s in scenarios[:5]:
            if not isinstance(s, dict):
                continue
            slim.append(
                {
                    "name": s.get("name"),
                    "avg_portfolio_loss_pct": s.get("avg_portfolio_loss_pct"),
                    "positions_stopped_out": s.get("positions_stopped_out"),
                    "total_positions": s.get("total_positions"),
                }
            )
    return {
        "portfolio_size": doc.get("portfolio_size"),
        "generated_utc": doc.get("generated_utc"),
        "scenarios": slim,
    }


def satellite_concept(doc: Optional[Dict]) -> Optional[Dict[str, Any]]:
    if not doc or not isinstance(doc, dict):
        return None
    ks = doc.get("ks_two_sample")
    ks_alert = None
    if isinstance(ks, dict):
        ks_alert = ks.get("distribution_shift_alert")
    return {
        "drift_alert_any": doc.get("drift_alert_any"),
        "ks_distribution_shift_alert": ks_alert,
    }


def satellite_fdr(doc: Optional[Dict]) -> Optional[Dict[str, Any]]:
    if not doc or not isinstance(doc, dict):
        return None
    s = doc.get("summary")
    if not isinstance(s, dict):
        return None
    strategies = doc.get("strategies")
    sig: List[str] = []
    both: List[str] = []
    if isinstance(strategies, list):
        for r in strategies:
            if not isinstance(r, dict):
                continue
            name = r.get("strategy")
            if not name:
                continue
            if r.get("fdr_significant") and len(sig) < 12:
                sig.append(str(name))
            if r.get("both_pass") and len(both) < 12:
                both.append(str(name))
    return {
        "strategies_tested": s.get("strategies_tested"),
        "fdr_significant_count": s.get("fdr_significant"),
        "dsr_survivors_count": s.get("dsr_survivors"),
        "both_pass_count": s.get("both_pass"),
        "fdr_significant_strategy_sample": sig,
        "both_pass_strategy_sample": both,
    }


def satellite_regime_btc(doc: Optional[Dict]) -> Optional[Dict[str, Any]]:
    if not doc or not isinstance(doc, dict):
        return None
    s = doc.get("summary")
    pr = doc.get("per_regime")
    sharpes: Dict[str, Any] = {}
    if isinstance(pr, dict):
        for k, v in pr.items():
            if isinstance(v, dict) and "sharpe_like" in v:
                sharpes[str(k)] = v.get("sharpe_like")
    out: Dict[str, Any] = {"sharpe_like_by_regime": sharpes}
    if isinstance(s, dict):
        out["closed_picks_assigned"] = s.get("closed_picks_assigned")
        out["regimes_reported"] = s.get("regimes_reported")
    return out


def redis_broadcast(msg: str) -> None:
    bus = Path(r"C:\Users\zerou\redis-bus\agent_bus.py")
    if not bus.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(bus), "broadcast", "cursor-composer", msg],
            check=False,
            timeout=15,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dashboard", type=str, default=str(DEFAULT_DASHBOARD))
    ap.add_argument("--out", type=str, default=str(OUT_JSON))
    ap.add_argument("--top-symbols", type=int, default=12)
    ap.add_argument("--crypto-only", action="store_true")
    ap.add_argument("--redis-alert", action="store_true")
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("ERROR: dashboard not found: %s" % path, file=sys.stderr)
        return 1

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    headline = data.get("summary")
    if not isinstance(headline, dict):
        headline = {}

    closed = (data.get("picks") or {}).get("recent_closed") or []
    pnls: List[float] = []
    for p in closed:
        if not isinstance(p, dict):
            continue
        if args.crypto_only and str(p.get("asset_class") or "").upper() != "CRYPTO":
            continue
        v = p.get("pnl_pct")
        if isinstance(v, (int, float)):
            pnls.append(float(v))
        elif v is not None:
            try:
                pnls.append(float(v))
            except (TypeError, ValueError):
                pass

    closed_block = compute_tail_block(np.array(pnls, dtype=float))

    active = (data.get("picks") or {}).get("active") or []
    sym_counts: Counter = Counter()
    crypto_actives = 0
    for p in active:
        if not isinstance(p, dict):
            continue
        if str(p.get("asset_class") or "").upper() == "CRYPTO":
            crypto_actives += 1
        s = str(p.get("symbol") or "").strip().upper()
        if s:
            sym_counts[s] += 1
    top_syms = [
        {"symbol": s, "count": n}
        for s, n in sym_counts.most_common(args.top_symbols)
    ]

    tail_path = REPO / "tools" / "data" / "tail_risk_es995_mdd_report.json"
    cvar_path = REPO / "tools" / "rolling_cvar_results.json"
    corr_path = REPO / "tools" / "data" / "rolling_correlation_report.json"
    stress_path = REPO / "tools" / "stress_test_results.json"
    drift_path = REPO / "tools" / "data" / "concept_drift_report.json"
    fdr_path = REPO / "tools" / "data" / "fdr_results.json"
    regime_path = REPO / "tools" / "data" / "regime_performance_btc_report.json"

    bulletin: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(path).replace("\\", "/"),
        "config": {"crypto_only_closed": args.crypto_only, "top_symbols": args.top_symbols},
        "dashboard_headline": {
            k: headline.get(k)
            for k in (
                "total_active_picks",
                "total_closed_picks",
                "overall_win_rate",
                "total_pnl_pct",
                "net_sharpe",
                "rolling_30d_max_dd",
            )
            if k in headline
        },
        "closed_trade_tail_risk": closed_block,
        "active_book": {
            "active_picks_count": len([p for p in active if isinstance(p, dict)]),
            "crypto_active_count": crypto_actives,
            "top_symbols": top_syms,
        },
        "satellite_reports": {
            "tail_risk_es995_mdd": satellite_tail_risk(
                safe_read_json(tail_path)
            ),
            "rolling_cvar": satellite_rolling_cvar(
                safe_read_json(cvar_path)
            ),
            "rolling_correlation": satellite_corr(
                safe_read_json(corr_path)
            ),
            "stress_test": satellite_stress(
                safe_read_json(stress_path)
            ),
            "concept_drift": satellite_concept(
                safe_read_json(drift_path)
            ),
            "bh_fdr": satellite_fdr(safe_read_json(fdr_path)),
            "regime_performance_btc": satellite_regime_btc(
                safe_read_json(regime_path)
            ),
            "_paths": {
                "tail_risk_es995_mdd": str(tail_path).replace("\\", "/"),
                "rolling_cvar": str(cvar_path).replace("\\", "/"),
                "rolling_correlation": str(corr_path).replace("\\", "/"),
                "stress_test": str(stress_path).replace("\\", "/"),
                "concept_drift": str(drift_path).replace("\\", "/"),
                "bh_fdr": str(fdr_path).replace("\\", "/"),
                "regime_performance_btc": str(regime_path).replace("\\", "/"),
            },
        },
        "note": "Bulletin aggregates existing JSON; re-run upstream tools to refresh satellites.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bulletin, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(
        "active=%s closed_n=%s VaR95=%s -> %s"
        % (
            bulletin["active_book"]["active_picks_count"],
            closed_block.get("n_trades"),
            closed_block.get("VaR_95_pct"),
            out_path,
        )
    )

    if args.redis_alert:
        redis_broadcast(
            "HEDGE_PLAN §6 daily-risk-bulletin-stub: active=%s closed=%s VaR95=%s | %s"
            % (
                bulletin["active_book"]["active_picks_count"],
                closed_block.get("n_trades"),
                closed_block.get("VaR_95_pct"),
                str(out_path).replace("\\", "/"),
            )
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
