#!/usr/bin/env python3
"""elite_score_class_distribution.py

Measures the class-wise distribution of `elite_score` across closed + active
picks, to verify the crypto-bias hypothesis documented in
updates/2026-04-17-elite-score-recalibration-plan.md §2.

For each asset class, reports:
  - n, mean, median, p25/p50/p75/p90
  - pct_ge_{40,50,55,60}  (what fraction clears each candidate floor)

Gate-attribution Venn over CLOSED WINNERS:
  For each winner, which of {elite_score<50, confidence<0.50, RR<1.15} gated it?
  Reports counts by class so we know which gate is actually starving non-crypto.

No writes to production state. Prints a table + saves JSON under tools/out/.

Run from repo root:
  python tools/elite_score_class_distribution.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "alpha_engine"))

CLOSED_PICKS = ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"
DASHBOARD_PAYLOAD = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
OUT_DIR = ROOT / "tools" / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FLOORS = (40, 45, 50, 55, 60)
CONF_FLOOR = 0.50
RR_FLOOR = 1.15


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


# Symbol-based asset-class inference for legacy closed picks that lack the
# asset_class field. Mirrors the heuristic in dashboard_generator._normalize_pick
# but standalone so the diagnostic doesn't depend on dashboard_generator import.
_BOND_TICKERS = {"TLT", "IEF", "SHY", "AGG", "BND", "LQD", "HYG", "TIP", "TLH",
                 "GOVT", "JNK", "MUB", "BNDX"}
_COMMODITY_TICKERS = {"GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "PL=F", "PA=F",
                      "ZC=F", "ZW=F", "ZS=F", "BZ=F", "RB=F", "HO=F", "LE=F",
                      "GF=F", "HE=F", "OJ=F", "USO", "UNG", "DBA", "GLD", "SLV",
                      "USO", "DBC", "GSG"}
_ETF_TICKERS = {"SPY", "QQQ", "IWM", "DIA", "EFA", "EEM", "VTI", "VOO", "VEA",
                "VWO", "ARKK", "TQQQ", "SQQQ", "SOXL", "VTV", "VUG", "IXN",
                "IYR", "ACWI", "FXI", "INDA", "ARKG", "XBI", "GDX", "GDXJ",
                "VIXY", "XLF", "XLE", "XLK", "XLV", "XLI", "XLP", "XLY"}
_FUTURES_SUFFIX = ("=F",)
_FOREX_PAIRS = {"EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD",
                "USDCHF", "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "XAUUSD",
                "XAGUSD"}


def _infer_asset_class(symbol: str) -> str:
    s = (symbol or "").upper().replace("-USD", "USDT")
    if s.endswith("USDT") or s.endswith("BTC") or s.endswith("ETH"):
        return "CRYPTO"
    if s in _BOND_TICKERS:
        return "BOND"
    if s in _COMMODITY_TICKERS or s.endswith("=F"):
        # =F is futures, but commodity futures dominate this universe
        return "COMMODITY" if s in _COMMODITY_TICKERS else "FUTURES"
    if s in _ETF_TICKERS:
        return "ETF"
    if s in _FOREX_PAIRS or (len(s) == 6 and s.isalpha()):
        return "FOREX"
    # Stocks (single-ticker, no special suffix)
    if s.isalpha() and 1 <= len(s) <= 5:
        return "EQUITY"
    return "UNKNOWN"


def _asset_class(p: dict) -> str:
    explicit = (p.get("asset_class") or p.get("category") or "").upper()
    if explicit:
        return explicit
    return _infer_asset_class(p.get("symbol") or "")


def _pct(n: int, total: int) -> str:
    return f"{100 * n / total:.1f}%" if total else "n/a"


def _load(path: Path) -> list[dict]:
    if not path.exists():
        print(f"  MISSING: {path}")
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  ERROR reading {path}: {e}")
        return []
    if isinstance(data, dict):
        # Common shapes: {"picks": [...]}, {"active_raw": [...]}
        for key in ("picks", "active_raw", "closed_picks", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return []
    if isinstance(data, list):
        return data
    return []


def _quantiles(vals: list[float]) -> dict:
    if not vals:
        return {k: None for k in ("mean", "median", "p25", "p50", "p75", "p90")}
    vals = sorted(vals)
    n = len(vals)

    def q(pct: float) -> float:
        idx = min(n - 1, int(round(pct * (n - 1))))
        return vals[idx]

    return {
        "mean": round(statistics.mean(vals), 2),
        "median": round(statistics.median(vals), 2),
        "p25": round(q(0.25), 2),
        "p50": round(q(0.50), 2),
        "p75": round(q(0.75), 2),
        "p90": round(q(0.90), 2),
    }


def _score_of(p: dict) -> float | None:
    """Prefer an existing elite_score field; fall back to a live recompute."""
    for key in ("elite_score", "score"):
        if key in p and p[key] is not None:
            v = _safe_float(p[key], default=float("nan"))
            if v == v:  # NaN check
                return v
    # Live recompute — only attempt if elite_scorer is importable
    try:
        from elite_scorer import compute_elite_score  # type: ignore
    except Exception:
        return None
    try:
        res = compute_elite_score(p) or {}
        v = _safe_float(res.get("elite_score"), default=float("nan"))
        return v if v == v else None
    except Exception:
        return None


def analyze(tag: str, picks: list[dict]) -> dict:
    print(f"\n=== {tag} (n={len(picks)}) ===")
    by_class: dict[str, list[float]] = {}
    for p in picks:
        ac = _asset_class(p)
        s = _score_of(p)
        if s is None:
            continue
        by_class.setdefault(ac, []).append(s)

    report = {}
    print(f"  {'class':<12} {'n':>5} {'mean':>6} {'med':>6} {'p25':>6} {'p75':>6} "
          + " ".join(f">={f:<3}".rjust(7) for f in FLOORS))
    for ac in sorted(by_class, key=lambda k: len(by_class[k]), reverse=True):
        vals = by_class[ac]
        q = _quantiles(vals)
        row = {"n": len(vals), **q}
        for f in FLOORS:
            row[f"pct_ge_{f}"] = _pct(sum(1 for v in vals if v >= f), len(vals))
        report[ac] = row
        flr = " ".join(row[f"pct_ge_{f}"].rjust(7) for f in FLOORS)
        print(f"  {ac:<12} {len(vals):>5} {q['mean']:>6} {q['median']:>6} "
              f"{q['p25']:>6} {q['p75']:>6} {flr}")
    return report


def gate_attribution(closed: list[dict]) -> dict:
    """For closed WINNERS only, count which gates would have blocked them."""
    print("\n=== GATE ATTRIBUTION (winners only; which gate blocked?) ===")
    print(f"  gates: elite_score<50, confidence<{CONF_FLOOR}, risk_reward<{RR_FLOOR}")
    report: dict[str, dict[str, int]] = {}
    for p in closed:
        # Winner = closed with positive PnL OR status=="win"
        pnl = _safe_float(p.get("pnl_pct") or p.get("net_pnl_pct") or p.get("pnl"))
        outcome = (p.get("outcome") or p.get("status") or "").lower()
        is_winner = pnl > 0 or outcome in ("win", "target_hit", "tp_hit")
        if not is_winner:
            continue
        ac = _asset_class(p)
        row = report.setdefault(ac, {"winners": 0, "gated_by_score": 0,
                                     "gated_by_conf": 0, "gated_by_rr": 0,
                                     "score_only": 0, "all_clear": 0})
        row["winners"] += 1
        s = _score_of(p) or 0.0
        c = _safe_float(p.get("confidence"))
        rr = _safe_float(p.get("risk_reward"))
        by_score = s < 50
        by_conf = c < CONF_FLOOR
        by_rr = rr < RR_FLOOR
        if by_score:
            row["gated_by_score"] += 1
        if by_conf:
            row["gated_by_conf"] += 1
        if by_rr:
            row["gated_by_rr"] += 1
        if by_score and not by_conf and not by_rr:
            row["score_only"] += 1
        if not (by_score or by_conf or by_rr):
            row["all_clear"] += 1

    print(f"  {'class':<12} {'win':>4} {'scr':>4} {'conf':>4} {'rr':>4} "
          f"{'scr_only':>9} {'all_clear':>10}")
    for ac in sorted(report, key=lambda k: report[k]["winners"], reverse=True):
        r = report[ac]
        print(f"  {ac:<12} {r['winners']:>4} {r['gated_by_score']:>4} "
              f"{r['gated_by_conf']:>4} {r['gated_by_rr']:>4} "
              f"{r['score_only']:>9} {r['all_clear']:>10}")
    return report


def main() -> int:
    print(f"Elite-score class distribution — {datetime.now(timezone.utc).isoformat()}")
    closed = _load(CLOSED_PICKS)
    # dashboard_payload.json: active picks live under picks.active (nested)
    active = []
    if DASHBOARD_PAYLOAD.exists():
        try:
            dp = json.loads(DASHBOARD_PAYLOAD.read_text(encoding="utf-8"))
            picks_node = dp.get("picks", {})
            if isinstance(picks_node, dict):
                active = picks_node.get("active") or picks_node.get("active_raw") or []
            elif isinstance(picks_node, list):
                active = picks_node
        except Exception as e:
            print(f"  ERROR reading {DASHBOARD_PAYLOAD}: {e}")
    closed_report = analyze("CLOSED PICKS", closed)
    active_report = analyze("ACTIVE PICKS (current)", active)
    gate_report = gate_attribution(closed)

    out = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "closed_picks": {"n_total": len(closed), "by_class": closed_report},
        "active_picks": {"n_total": len(active), "by_class": active_report},
        "gate_attribution_winners": gate_report,
        "floors_tested": list(FLOORS),
        "conf_floor": CONF_FLOOR,
        "rr_floor": RR_FLOOR,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = OUT_DIR / f"elite_score_class_distribution_{stamp}.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
