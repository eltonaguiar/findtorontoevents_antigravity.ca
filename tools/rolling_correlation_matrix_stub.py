#!/usr/bin/env python3
"""§2 Rolling correlation matrix stub (Mercury / HEDGE_FUND plan).

Builds **daily** per-symbol return proxies from ``recent_closed`` (sum of ``pnl_pct``
for trades closed that UTC calendar day), then Pearson correlation across symbols for
the last **30** and **90** calendar days (missing days filled with **0** — no trade
= flat day).

Flags pairs with **|correlation| >= threshold** (default **0.85**) for portfolio
concentration / risk-parity monitoring (monitor-only v0).

Output: ``tools/data/rolling_correlation_report.json``

Usage:
  python tools/rolling_correlation_matrix_stub.py
  python tools/rolling_correlation_matrix_stub.py --top-symbols 35 --redis-alert
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "rolling_correlation_report.json"

DEFAULT_THRESH = 0.85
MIN_DAYS_OBS = 5  # min distinct days with trades in window to include symbol


def parse_ts(ts_str: Any) -> Optional[datetime]:
    if not ts_str:
        return None
    s = str(ts_str).replace("+00:00", "Z").rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _norm_symbol(sym: Any) -> str:
    if not sym:
        return ""
    return str(sym).upper().replace("-", "").replace("/", "")


def load_daily_by_symbol(
    path: Path, crypto_only: bool
) -> Tuple[Dict[Tuple[Any, str], float], datetime.date, datetime.date]:
    """Return ( (date, symbol) -> sum_pnl_pct , min_date, max_date )."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = (data.get("picks") or {}).get("recent_closed") or []
    cell: Dict[Tuple[Any, str], float] = defaultdict(float)
    min_d: Optional[datetime.date] = None
    max_d: Optional[datetime.date] = None

    for p in picks:
        if not isinstance(p, dict):
            continue
        if crypto_only:
            if str(p.get("asset_class") or "").upper() != "CRYPTO":
                continue
        ts = parse_ts(p.get("closed_at"))
        if ts is None:
            continue
        sym = _norm_symbol(p.get("symbol"))
        if len(sym) < 4:
            continue
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        try:
            pf = float(pnl)
        except (TypeError, ValueError):
            continue
        d = ts.date()
        cell[(d, sym)] += pf
        if min_d is None or d < min_d:
            min_d = d
        if max_d is None or d > max_d:
            max_d = d

    if min_d is None or max_d is None:
        return {}, datetime.date.today(), datetime.date.today()
    return cell, min_d, max_d


def top_symbols_in_range(
    cell: Dict[Tuple[Any, str], float],
    end: datetime.date,
    span_days: int,
    top_k: int,
) -> List[str]:
    start = end - timedelta(days=span_days - 1)
    counts: Dict[str, int] = defaultdict(int)
    for (d, sym), _ in cell.items():
        if start <= d <= end:
            counts[sym] += 1
    ranked = sorted(counts.keys(), key=lambda s: counts[s], reverse=True)
    return ranked[:top_k]


def build_matrix(
    cell: Dict[Tuple[Any, str], float],
    end: datetime.date,
    span_days: int,
    symbols: List[str],
) -> np.ndarray:
    """Shape (span_days, n_symbols); row t = calendar day end - (span-1) + t."""
    start = end - timedelta(days=span_days - 1)
    n = len(symbols)
    idx = {s: j for j, s in enumerate(symbols)}
    X = np.zeros((span_days, n), dtype=np.float64)
    for i in range(span_days):
        d = start + timedelta(days=i)
        for sym in symbols:
            v = cell.get((d, sym), 0.0)
            X[i, idx[sym]] = v
    return X


def corrcoef_safe(X: np.ndarray) -> np.ndarray:
    """Column-wise correlation; columns with zero std -> nan diagonal off-diagonal."""
    n = X.shape[1]
    if n < 2:
        return np.eye(max(1, n))
    C = np.corrcoef(X, rowvar=False)
    if C.ndim < 2:
        C = np.array([[1.0]])
    # numpy may return nan if constant column
    C = np.nan_to_num(C, nan=0.0)
    np.fill_diagonal(C, 1.0)
    return C


def high_corr_pairs(C: np.ndarray, symbols: List[str], thresh: float) -> List[Dict[str, Any]]:
    n = len(symbols)
    out: List[Dict[str, Any]] = []
    for i in range(n):
        for j in range(i + 1, n):
            r = float(C[i, j])
            if abs(r) >= thresh:
                out.append(
                    {
                        "symbol_a": symbols[i],
                        "symbol_b": symbols[j],
                        "correlation": round(r, 6),
                    }
                )
    out.sort(key=lambda x: -abs(x["correlation"]))
    return out


def non_zero_days_per_col(X: np.ndarray) -> np.ndarray:
    return np.sum(np.abs(X) > 1e-12, axis=0)


def filter_symbols_by_activity(
    X: np.ndarray, symbols: List[str], min_days: int
) -> Tuple[np.ndarray, List[str]]:
    counts = non_zero_days_per_col(X)
    keep = [i for i, s in enumerate(symbols) if counts[i] >= min_days]
    if not keep:
        return X[:, []], []
    sym2 = [symbols[i] for i in keep]
    return X[:, keep], sym2


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
    ap.add_argument("--window-30", type=int, default=30)
    ap.add_argument("--window-90", type=int, default=90)
    ap.add_argument("--top-symbols", type=int, default=40)
    ap.add_argument("--corr-threshold", type=float, default=DEFAULT_THRESH)
    ap.add_argument("--min-nonzero-days", type=int, default=MIN_DAYS_OBS)
    ap.add_argument("--crypto-only", action="store_true")
    ap.add_argument("--redis-alert", action="store_true")
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("ERROR: dashboard not found: %s" % path, file=sys.stderr)
        return 1

    cell, _min_d, max_d = load_daily_by_symbol(path, args.crypto_only)
    if not cell:
        print("ERROR: no daily cells", file=sys.stderr)
        return 1

    end = max_d
    syms_90 = top_symbols_in_range(cell, end, args.window_90, args.top_symbols)
    if len(syms_90) < 2:
        print("ERROR: need at least 2 symbols", file=sys.stderr)
        return 1

    X90 = build_matrix(cell, end, args.window_90, syms_90)
    min_nd = args.min_nonzero_days
    X90, syms_90_f = filter_symbols_by_activity(X90, syms_90, min_nd)
    while len(syms_90_f) < 2 and min_nd > 2:
        min_nd -= 1
        X90 = build_matrix(cell, end, args.window_90, syms_90)
        X90, syms_90_f = filter_symbols_by_activity(X90, syms_90, min_nd)
    if len(syms_90_f) < 2:
        print("ERROR: after activity filter, <2 symbols", file=sys.stderr)
        return 1

    C90 = corrcoef_safe(X90)
    alert_90 = high_corr_pairs(C90, syms_90_f, args.corr_threshold)

    # 30d window: same symbol universe order as filtered 90 for comparability,
    # but only last 30 days of columns
    X30 = build_matrix(cell, end, args.window_30, syms_90_f)
    X30, syms_30_f = filter_symbols_by_activity(
        X30, syms_90_f, min(8, args.min_nonzero_days // 2 + 1)
    )
    if len(syms_30_f) < 2:
        syms_30_f = syms_90_f
        X30 = build_matrix(cell, end, args.window_30, syms_30_f)

    C30 = corrcoef_safe(X30)
    alert_30 = high_corr_pairs(C30, syms_30_f, args.corr_threshold)

    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(path).replace("\\", "/"),
        "config": {
            "window_30": args.window_30,
            "window_90": args.window_90,
            "top_symbols_cap": args.top_symbols,
            "corr_threshold": args.corr_threshold,
            "min_nonzero_days_90": args.min_nonzero_days,
            "crypto_only": args.crypto_only,
        },
        "summary": {
            "end_date": str(end),
            "symbols_90d": len(syms_90_f),
            "symbols_30d": len(syms_30_f),
            "pairs_flagged_90d": len(alert_90),
            "pairs_flagged_30d": len(alert_30),
        },
        "high_correlation_pairs_90d": alert_90[:50],
        "high_correlation_pairs_30d": alert_30[:50],
        "note": "Daily sum of pnl_pct per symbol; zeros on no-trade days. Pearson corr — not causal; use for risk concentration hints only.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(
        "symbols_90=%d pairs_|r|>=%.2f: 30d=%d 90d=%d -> %s"
        % (
            len(syms_90_f),
            args.corr_threshold,
            len(alert_30),
            len(alert_90),
            out_path,
        )
    )

    if args.redis_alert:
        redis_broadcast(
            "HEDGE_PLAN §2 rolling-corr stub: 90d symbols=%d flagged_pairs 30d=%d 90d=%d -> %s"
            % (
                len(syms_90_f),
                len(alert_30),
                len(alert_90),
                str(out_path).replace("\\", "/"),
            )
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
