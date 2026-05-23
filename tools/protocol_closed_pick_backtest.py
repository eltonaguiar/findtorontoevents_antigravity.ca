#!/usr/bin/env python3
"""
Protocol-aligned observational backtest on real closed picks (TESTING_PROTOCOL.MD).

Uses audit_dashboard/data/dashboard_data.json (no synthetic trades):
  - Strategy edge table (mean pnl, WR, n) with Wilson 95%% lower bound
  - Train/test split empirical Bayes calibration (avoid in-sample peeking)
  - GateFilter pass rate and realized WR on a synthetic \"at-entry\" slice from closes
  - Adaptive stop: share of closes where net_rr at entry would reject

Output: tools/data/protocol_backtest_report.json (+ stdout summary)

Run from repo root:
  python tools/protocol_closed_pick_backtest.py
  python tools/protocol_closed_pick_backtest.py --dashboard path/to/dashboard_data.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
DEFAULT_DASH = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "protocol_backtest_report.json"


def _f(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _won(t: dict) -> bool | None:
    p = t.get("pnl_pct")
    if p is not None:
        try:
            return float(p) > 0
        except (TypeError, ValueError):
            pass
    return None


def wilson_lb(wins: int, n: int, z: float = 1.96) -> float | None:
    if n <= 0:
        return None
    p = wins / n
    denom = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return max(0.0, (center - margin) / denom)


def load_closed(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    picks = raw.get("picks") or {}
    closed = picks.get("recent_closed") or []
    return [x for x in closed if isinstance(x, dict)]


def strategy_table(closed: list[dict], min_n: int = 15) -> list[dict]:
    by: dict[str, list[dict]] = defaultdict(list)
    for t in closed:
        s = str(t.get("strategy") or "unknown")[:80]
        by[s].append(t)
    rows = []
    for strat, trades in by.items():
        n = len(trades)
        if n < min_n:
            continue
        wins = sum(1 for t in trades if _won(t) is True)
        losses = sum(1 for t in trades if _won(t) is False)
        unknown = n - wins - losses
        pnls = [_f(t.get("pnl_pct")) for t in trades if t.get("pnl_pct") is not None]
        mean_pnl = sum(pnls) / len(pnls) if pnls else 0.0
        wr = 100.0 * wins / n if n else 0.0
        rows.append(
            {
                "strategy": strat,
                "n": n,
                "wins": wins,
                "losses": losses,
                "unknown_outcome": unknown,
                "wr_pct": round(wr, 2),
                "mean_pnl_pct": round(mean_pnl, 4),
                "wilson_lb_wr": round(wilson_lb(wins, n) or 0, 4) if wins >= 0 else None,
            }
        )
    rows.sort(key=lambda r: (r["wilson_lb_wr"] or 0, r["mean_pnl_pct"]), reverse=True)
    return rows


def eb_walk_forward(closed: list[dict], train_ratio: float = 0.5) -> dict:
    """Train EmpiricalBayesScorer on first fraction; bucket test set by predicted prob."""
    from audit_trail.empirical_bayes_scorer import EmpiricalBayesScorer

    valid = [t for t in closed if _won(t) is not None]

    def _ts(t: dict) -> str:
        return str(t.get("closed_at") or t.get("timestamp") or "")

    valid.sort(key=_ts)
    if len(valid) < 100:
        return {"error": "insufficient_labeled_closes", "n": len(valid)}
    split = int(len(valid) * train_ratio)
    train, test = valid[:split], valid[split:]
    scorer = EmpiricalBayesScorer(train)

    buckets: dict[str, list[bool]] = defaultdict(list)
    for t in test:
        sym = str(t.get("symbol") or "")
        strat = str(t.get("strategy") or "")
        direction = str(t.get("direction") or "LONG")
        ac = str(t.get("asset_class") or "CRYPTO")
        pr = scorer.win_prob(sym, strat, direction, asset_class=ac)
        p = float(pr["win_prob"])
        b = "p_%.0f_%.0f" % (math.floor(p * 10) / 10, math.ceil(p * 10) / 10)
        if p >= 0.55:
            b = "high_>=0.55"
        elif p >= 0.45:
            b = "mid_0.45_0.55"
        else:
            b = "low_<0.45"
        w = _won(t)
        assert w is not None
        buckets[b].append(w)

    out = {}
    for name, outcomes in sorted(buckets.items()):
        n = len(outcomes)
        wn = sum(1 for x in outcomes if x)
        out[name] = {
            "n": n,
            "realized_wr": round(wn / n, 4) if n else None,
            "wilson_lb": round(wilson_lb(wn, n) or 0, 4) if n else None,
        }
    return {"train_n": len(train), "test_n": len(test), "buckets": out}


def gate_and_adaptive_slice(closed: list[dict]) -> dict:
    """How many closes had valid TP/SL geometry; adaptive_stop net reject rate (proxy)."""
    from audit_trail.adaptive_stops import calculate_adaptive_stop_dict, classify_regime
    from audit_trail.forward_test_gates import forward_pick_passes_gates, closed_pick_to_forward_shape

    valid_geom = 0
    light_pass = 0
    atr_proxy_hits = 0
    adaptive_reject = 0

    for t in closed:
        entry = _f(t.get("entry_price"))
        tp = _f(t.get("take_profit"))
        sl = _f(t.get("stop_loss"))
        if entry <= 0 or tp <= 0 or sl <= 0:
            continue
        valid_geom += 1
        shaped = closed_pick_to_forward_shape(t)
        ok, _ = forward_pick_passes_gates(
            {
                "entry_price": shaped["entry_price"],
                "tp_price": shaped["tp_price"],
                "sl_price": shaped["sl_price"],
                "direction": shaped["direction"],
                "strategy": shaped["strategy"],
                "score": shaped.get("score"),
            }
        )
        if ok:
            light_pass += 1

        ac = str(t.get("asset_class") or "CRYPTO").upper()
        sym = str(t.get("symbol") or "")
        atr = abs(entry - sl) * 1.2
        if atr <= 0:
            continue
        regime = classify_regime(vix=18.0, spx_vs_200dma=2.0)
        d = calculate_adaptive_stop_dict(
            entry, atr, ac if ac else "CRYPTO", direction=str(t.get("direction", "LONG")), regime=regime, vix=18.0
        )
        if d.get("rejected"):
            adaptive_reject += 1
        atr_proxy_hits += 1

    return {
        "closes_with_tp_sl": valid_geom,
        "light_geometry_pass": light_pass,
        "light_pass_wr_note": "geometry-only gate (not Layer 2.5 full)",
        "adaptive_atr_proxy_rows": atr_proxy_hits,
        "adaptive_net_rr_reject": adaptive_reject,
    }


def asset_class_summary(closed: list[dict]) -> dict[str, dict]:
    by: dict[str, list[dict]] = defaultdict(list)
    for t in closed:
        ac = str(t.get("asset_class") or "UNKNOWN").upper()
        by[ac].append(t)
    out = {}
    for ac, trades in by.items():
        n = len(trades)
        labeled = [t for t in trades if _won(t) is not None]
        if not labeled:
            continue
        wn = sum(1 for t in labeled if _won(t))
        pnls = [_f(t.get("pnl_pct")) for t in labeled]
        out[ac] = {
            "n": n,
            "labeled_n": len(labeled),
            "wr_pct": round(100.0 * wn / len(labeled), 2),
            "mean_pnl_pct": round(sum(pnls) / len(pnls), 4),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dashboard", default=str(DEFAULT_DASH))
    ap.add_argument("--min-n", type=int, default=15)
    args = ap.parse_args()
    path = Path(args.dashboard)
    if not path.is_file():
        print("Missing dashboard JSON:", path)
        return 1

    closed = load_closed(path)
    report = {
        "source": str(path),
        "total_closed": len(closed),
        "protocol_ref": "TESTING_PROTOCOL.MD Layer 2.5 + empirical calibration",
        "asset_class_summary": asset_class_summary(closed),
        "top_strategies_by_wilson_lb": strategy_table(closed, min_n=args.min_n)[:40],
        "empirical_bayes_walk_forward": eb_walk_forward(closed),
        "gates_and_adaptive_proxy": gate_and_adaptive_slice(closed),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Wrote", OUT_JSON)

    top = report["top_strategies_by_wilson_lb"][:12]
    print("\n=== Top strategies (n>=%d, Wilson LB) ===" % args.min_n)
    for r in top:
        print(
            "  %6.1f%% LB | n=%4d | mean_pnl=%7.3f%% | %s"
            % (
                (r["wilson_lb_wr"] or 0) * 100,
                r["n"],
                r["mean_pnl_pct"],
                r["strategy"][:55],
            )
        )

    eb = report["empirical_bayes_walk_forward"]
    if "buckets" in eb:
        print("\n=== EB walk-forward (test set realized WR by predicted bucket) ===")
        for k, v in eb["buckets"].items():
            print("  %s: n=%d realized_wr=%s wilson_lb=%s" % (k, v["n"], v["realized_wr"], v["wilson_lb"]))

    print("\n=== Asset class ===")
    for ac, s in sorted(report["asset_class_summary"].items(), key=lambda x: -x[1]["n"]):
        print("  %s: n=%d WR=%.1f%% mean_pnl=%.3f%%" % (ac, s["n"], s["wr_pct"], s["mean_pnl_pct"]))

    g = report["gates_and_adaptive_proxy"]
    print(
        "\n=== Gate / adaptive proxy ===\n  TP/SL present: %d | light pass: %d | adaptive reject (proxy): %d / %d"
        % (
            g["closes_with_tp_sl"],
            g["light_geometry_pass"],
            g["adaptive_net_rr_reject"],
            g["adaptive_atr_proxy_rows"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
