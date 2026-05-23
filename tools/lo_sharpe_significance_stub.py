#!/usr/bin/env python3
"""§1 Lo (2002) / moment-based Sharpe significance stub (HEDGE_FUND plan).

``HEDGE_FUND_ENHANCEMENT_PLAN.md`` §1: **Sharpe significance (Lo 2002)** on live
closed-trade outcomes.

Uses the same **variance of the Sharpe estimator** shape as ``statistical_validator.py``
(DSR block):

  Var(SR̂) ≈ (1 + γ₁·SR + ((κ−1)/4)·SR²) / (T−1)

where **γ₁** is **mean(z³)** on standardized trades, **κ** is **mean(z⁴)** (Pearson-style; normal ≈ 3), **T** is
the number of trades, and **SR** is the **trade-scaled** Sharpe proxy
``(mean/std)·√T`` on ``pnl_pct`` (consistent with other audit stubs — not annualized
to 252 unless you treat each trade as one “period”).

Reports **standard error**, **z vs benchmark Sharpe** (default 0), **two-sided
p-value** (normal approx), and **PSR-style** ``P(SR̂ > benchmark)`` = Φ(z).

Data: ``picks.recent_closed`` from ``dashboard_data.json`` (real ``pnl_pct`` only).

Output: ``tools/data/lo_sharpe_significance_report.json``

Usage:
  python tools/lo_sharpe_significance_stub.py
  python tools/lo_sharpe_significance_stub.py --crypto-only --benchmark-sharpe 0 --redis-alert
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "lo_sharpe_significance_report.json"


def load_pnls(path: Path, crypto_only: bool) -> List[float]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = (data.get("picks") or {}).get("recent_closed") or []
    out: List[float] = []
    for p in picks:
        if not isinstance(p, dict):
            continue
        if crypto_only and str(p.get("asset_class") or "").upper() != "CRYPTO":
            continue
        v = p.get("pnl_pct")
        if v is None:
            continue
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


def norm_cdf(x: float) -> float:
    """Standard normal CDF (no scipy — import can stall on some hosts)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def standardized_moments_skew_kurt_pearson(r: np.ndarray, mu: float, sd: float) -> tuple:
    """Skewness and Pearson kurtosis of z-scores (mean(z^3), mean(z^4)); normal → 0, 3."""
    if sd < 1e-15:
        return 0.0, 3.0
    z = (r - mu) / sd
    return float(np.mean(z**3)), float(np.mean(z**4))


def sharpe_variance_lo_style(sr: float, T: int, skew: float, kurt_pearson: float) -> float:
    """Match statistical_validator deflated_sharpe_ratio variance numerator form."""
    if T < 2:
        return float("nan")
    return (1.0 + skew * sr + ((kurt_pearson - 1.0) / 4.0) * sr * sr) / float(T - 1)


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
    ap.add_argument("--min-trades", type=int, default=30)
    ap.add_argument("--benchmark-sharpe", type=float, default=0.0)
    ap.add_argument("--crypto-only", action="store_true")
    ap.add_argument("--redis-alert", action="store_true")
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("ERROR: dashboard not found: %s" % path, file=sys.stderr)
        return 1

    pnls = load_pnls(path, args.crypto_only)
    T = len(pnls)
    if T < args.min_trades:
        print("ERROR: need >= %s trades, got %s" % (args.min_trades, T), file=sys.stderr)
        return 1

    r = np.array(pnls, dtype=np.float64)
    mu = float(r.mean())
    sd = float(r.std(ddof=1))
    if sd < 1e-12:
        print("ERROR: zero std", file=sys.stderr)
        return 1

    sr_obs = (mu / sd) * math.sqrt(float(T))
    skew, kurt_pearson = standardized_moments_skew_kurt_pearson(r, mu, sd)

    var_sr = sharpe_variance_lo_style(sr_obs, T, skew, kurt_pearson)
    if var_sr != var_sr or var_sr < 0:
        se = None
        z = None
        p_two = None
        psr = None
    else:
        se = math.sqrt(var_sr)
        if se < 1e-18:
            z = None
            p_two = None
            psr = None
        else:
            z = (sr_obs - args.benchmark_sharpe) / se
            p_two = float(2.0 * (1.0 - norm_cdf(abs(z))))
            psr = float(norm_cdf(z))

    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(path).replace("\\", "/"),
        "config": {
            "min_trades": args.min_trades,
            "benchmark_sharpe": args.benchmark_sharpe,
            "crypto_only": args.crypto_only,
            "variance_formula": "(1 + skew*SR + ((kurt_pearson-1)/4)*SR^2)/(T-1)  [repo DSR block]",
            "sharpe_definition": "(mean/std)*sqrt(T) on pnl_pct trades",
        },
        "summary": {
            "n_trades": T,
            "mean_pnl_pct": round(mu, 6),
            "std_pnl_pct": round(sd, 6),
            "skewness_z3": round(skew, 6),
            "kurtosis_pearson_z4": round(kurt_pearson, 6),
            "sharpe_observed": round(sr_obs, 6),
            "sharpe_stderr": round(se, 8) if se is not None else None,
            "z_vs_benchmark": round(z, 6) if z is not None else None,
            "p_value_two_sided_normal": round(p_two, 8) if p_two is not None else None,
            "psr_vs_benchmark": round(psr, 8) if psr is not None else None,
            "significant_at_05_two_sided": bool(p_two is not None and p_two < 0.05),
        },
        "note": "Normal approx; heavy tails can understate uncertainty. Aligns with statistical_validator variance term, not full Lo (2002) bootstrap.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    p2 = report["summary"]["p_value_two_sided_normal"]
    print("T=%s SR=%.4f se=%s p_two=%s -> %s" % (T, sr_obs, report["summary"]["sharpe_stderr"], p2, out_path))

    if args.redis_alert:
        redis_broadcast(
            "HEDGE_PLAN §1 Lo-Sharpe-stub: T=%s SR=%.3f p_two=%s | %s"
            % (T, sr_obs, p2, str(out_path).replace("\\", "/"))
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
