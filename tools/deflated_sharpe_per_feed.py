"""Per-feed Deflated Sharpe Ratio (DSR) + Probabilistic Sharpe Ratio (PSR).

Companion to `tools/deflated_sharpe.py` (which is per-strategy / per-source).
This script slices closed picks by feed membership (ALL, HC, Smart, Verified
Alpha, per asset class) and reports SR, PSR vs SR=0 and SR=1, and DSR.

Stdlib fallback implementation of Bailey & Lopez de Prado (2014) because the
`pypbo` package is not available on PyPI. Read-only analysis; writes to
`tools/data/deflated_sharpe_results_2026_04_20.json`.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional

import numpy as np
from scipy.stats import norm

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from audit_trail.feed_membership import (  # noqa: E402
    evaluate_hc_tier,
    is_smart_pick_per_pick,
    is_verified_alpha_per_pick,
)

DATA_IN = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
DATA_OUT = REPO_ROOT / "tools" / "data" / "deflated_sharpe_results_2026_04_20.json"

TRADING_DAYS = 252
EULER_MASCHERONI = 0.5772156649015329


def _moments(x: np.ndarray) -> dict:
    n = int(x.size)
    if n < 2:
        return {"n": n, "mean": None, "std": None, "skew": None, "kurt": None}
    mu = float(np.mean(x))
    sd = float(np.std(x, ddof=1))
    if sd == 0:
        return {"n": n, "mean": mu, "std": 0.0, "skew": 0.0, "kurt": 0.0}
    xc = x - mu
    m2 = float(np.mean(xc ** 2))
    m3 = float(np.mean(xc ** 3))
    m4 = float(np.mean(xc ** 4))
    return {
        "n": n,
        "mean": mu,
        "std": sd,
        "skew": m3 / (m2 ** 1.5),
        "kurt": (m4 / (m2 ** 2)) - 3.0,  # excess kurtosis
    }


def sharpe_ratio(x: np.ndarray, periods_per_year: int = TRADING_DAYS) -> Optional[float]:
    if x.size < 2:
        return None
    sd = np.std(x, ddof=1)
    if sd == 0:
        return None
    return float((np.mean(x) / sd) * math.sqrt(periods_per_year))


def psr(sr_hat_annual: float, sr_bench_annual: float, n: int, skew: float,
        kurt: float) -> Optional[float]:
    """Probabilistic Sharpe Ratio P(trueSR > sr_bench | observed sr_hat).

    Inputs are annualised SRs; convert internally to per-period for the
    closed-form PSR (Bailey & LdP 2012).
    """
    if n < 2:
        return None
    sr_p = sr_hat_annual / math.sqrt(TRADING_DAYS)
    sr_b = sr_bench_annual / math.sqrt(TRADING_DAYS)
    denom = math.sqrt(max(1e-12, 1.0 - skew * sr_p + (kurt / 4.0) * (sr_p ** 2)))
    z = (sr_p - sr_b) * math.sqrt(n - 1) / denom
    return float(norm.cdf(z))


def expected_max_sr(n_trials: int, var_sr_trials_per_period: float) -> float:
    """Bailey & LdP (2014) closed form: E[max SR] over N independent trials."""
    n = max(1, int(n_trials))
    if n == 1:
        return 0.0
    sd = math.sqrt(max(var_sr_trials_per_period, 0.0))
    a = (1.0 - EULER_MASCHERONI) * norm.ppf(1.0 - 1.0 / n)
    b = EULER_MASCHERONI * norm.ppf(1.0 - 1.0 / (n * math.e))
    return sd * (a + b)


def dsr(sr_hat_annual: float, n: int, skew: float, kurt: float,
        n_trials: int, var_sr_trials_per_period: Optional[float]) -> Optional[float]:
    if n < 2:
        return None
    if var_sr_trials_per_period is None:
        var_sr_trials_per_period = 1.0 / TRADING_DAYS  # ~1.0 annualised variance
    sr0_p = expected_max_sr(n_trials, var_sr_trials_per_period)
    sr0_annual = sr0_p * math.sqrt(TRADING_DAYS)
    return psr(sr_hat_annual, sr0_annual, n, skew, kurt)


def _compute_feed(name: str, picks: list[dict]) -> dict:
    # pnl_pct is in percent units; convert to decimal for sensible SR scale.
    rets = np.array(
        [float(p["pnl_pct"]) / 100.0 for p in picks if p.get("pnl_pct") is not None],
        dtype=float,
    )
    m = _moments(rets)
    n = m["n"]
    strategies = {str(p.get("strategy") or "").strip() for p in picks}
    strategies.discard("")
    n_trials = max(1, len(strategies))

    out = {
        "feed": name,
        "n_picks": n,
        "n_strategies": int(n_trials),
        "mean_pnl_pct": (m["mean"] * 100.0) if m["mean"] is not None else None,
        "std_pnl_pct": (m["std"] * 100.0) if m["std"] is not None else None,
        "skew": m["skew"],
        "excess_kurt": m["kurt"],
        "sharpe_annualised": None,
        "psr_vs_sr0": None,
        "psr_vs_sr1": None,
        "dsr": None,
        "var_sr_trials_per_period": None,
    }
    if n < 2 or not m["std"]:
        return out

    sr = sharpe_ratio(rets)
    out["sharpe_annualised"] = sr
    out["psr_vs_sr0"] = psr(sr, 0.0, n, m["skew"], m["kurt"])
    out["psr_vs_sr1"] = psr(sr, 1.0, n, m["skew"], m["kurt"])

    # Variance of per-strategy per-period SRs -> input to E[max SR]
    strat_srs = []
    for s in strategies:
        xs = np.array(
            [float(p["pnl_pct"]) / 100.0 for p in picks
             if p.get("pnl_pct") is not None and str(p.get("strategy") or "").strip() == s],
            dtype=float,
        )
        if xs.size >= 3 and np.std(xs, ddof=1) > 0:
            strat_srs.append(float(np.mean(xs) / np.std(xs, ddof=1)))
    var_sr_p = float(np.var(strat_srs, ddof=1)) if len(strat_srs) >= 2 else 1.0 / TRADING_DAYS
    out["var_sr_trials_per_period"] = var_sr_p
    out["dsr"] = dsr(sr, n, m["skew"], m["kurt"], n_trials, var_sr_p)
    return out


def _filter(picks: Iterable[dict], pred: Callable[[dict], bool]) -> list[dict]:
    return [p for p in picks if pred(p)]


def main() -> int:
    with open(DATA_IN, "r", encoding="utf-8") as f:
        dash = json.load(f)
    picks = dash.get("picks", {}).get("recent_closed", []) or []

    feeds: dict[str, list[dict]] = {
        "ALL": list(picks),
        "HC": _filter(picks, lambda p: evaluate_hc_tier(p) in ("grade-a", "grade-b")),
        "SMART": _filter(picks, lambda p: is_smart_pick_per_pick(p) is True),
        "VERIFIED_ALPHA": _filter(picks, lambda p: is_verified_alpha_per_pick(p) is True),
    }
    for ac in ("CRYPTO", "EQUITY", "ETF", "FOREX", "COMMODITY", "BOND"):
        feeds[f"ASSET_{ac}"] = _filter(
            picks, lambda p, ac=ac: str(p.get("asset_class") or "").upper() == ac
        )

    results = [_compute_feed(name, ps) for name, ps in feeds.items()]

    payload = {
        "generated_at": "2026-04-20",
        "source": str(DATA_IN.relative_to(REPO_ROOT)).replace("\\", "/"),
        "total_picks": len(picks),
        "method": "stdlib-fallback (Bailey & Lopez de Prado 2014 closed-form)",
        "library_status": "pypbo unavailable on PyPI; numpy/scipy stdlib fallback",
        "periods_per_year": TRADING_DAYS,
        "feeds": results,
    }
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)

    print(f"Wrote {DATA_OUT}")
    hdr = f"{'feed':<22} {'n':>6} {'strat':>5} {'SR':>8} {'PSR0':>7} {'PSR1':>7} {'DSR':>7}"
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        def _f(v, w, p):
            return f"{v:>{w}.{p}f}" if v is not None else " " * (w - 3) + "n/a"
        print(f"{r['feed']:<22} {r['n_picks']:>6d} {r['n_strategies']:>5d} "
              f"{_f(r['sharpe_annualised'], 8, 3)} "
              f"{_f(r['psr_vs_sr0'], 7, 3)} "
              f"{_f(r['psr_vs_sr1'], 7, 3)} "
              f"{_f(r['dsr'], 7, 3)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
