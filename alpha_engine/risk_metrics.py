#!/usr/bin/env python3
"""
Tail Risk & Concentration Metrics for the Alpha Engine.

Computes:
  1. Value-at-Risk (VaR) at 95%
  2. Expected Shortfall (ES) at 95%
  3. Gini coefficient (profit concentration)
  4. Sortino ratio (downside-only risk-adjusted return)
  5. Calmar ratio (annual return / max drawdown)
  6. Realistic Sharpe ratio (with transaction costs deducted per trade)
  7. Information Coefficient (Spearman rank correlation: score vs realized PnL)
  8. Probabilistic Sharpe Ratio (PSR) — per-source, cached for hot paths.

Data sources (in order):
  - audit_trail/data/dashboard_payload.json  (picks.recent_closed)
  - alpha_engine/data/closed_picks.json      (fallback)
  - audit_dashboard/data/dashboard_data.json (picks.recent_closed) — used for
    the per-source PSR cache that backs ``psr_for_source`` / ``psr_points``.

Output:
  - alpha_engine/data/risk_metrics.json
  - alpha_engine/data/precision_recall_report.json  (IC appended)
  - Formatted console summary

Public PSR API (used by audit_trail/quality_gates.py::calculate_smart_score):
  - psr(returns, benchmark_sharpe=0.0) -> probability in [0, 1]
  - psr_for_source(source_system) -> Optional[float] (None if n<MIN_TRADES_FOR_PSR)
  - psr_points(source_system, fallback_pts=0.0) -> float in [0, 15]
"""

import json
import math
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

# ── Windows UTF-8 fix ──────────────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"

# ── Transaction cost defaults (per-trade, one-way) ───────────────────────────
# Used by compute_realistic_sharpe when per-pick cost info is unavailable.
_DEFAULT_COST = {
    "crypto": 0.001,   # 0.1% per trade (Binance default tier)
    "meme": 0.005,     # 0.5% per trade (meme coin slippage + fees)
    "forex": 0.0002,   # 0.02% per trade (tight spreads)
    "stock": 0.0002,   # 0.02% per trade (commission-free era)
    "penny": 0.005,    # 0.5% per trade (wide spreads)
}


# ── Data Loading ───────────────────────────────────────────────────────────────

def _load_closed_picks_full() -> list[dict]:
    """Load full closed pick dicts (needed for IC, realistic Sharpe).

    Returns a list of pick dicts, each guaranteed to have at least pnl_pct.
    """
    # Primary: dashboard_payload.json -> picks.recent_closed
    payload_path = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
    if payload_path.exists():
        try:
            with open(payload_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            closed = data.get("picks", {}).get("recent_closed", [])
            picks = [
                p for p in closed
                if p.get("pnl_pct") is not None
                and not p.get("_auto_expired", False)
            ]
            if picks:
                return picks
        except Exception:
            pass

    # Fallback: closed_picks.json
    fallback_path = DATA_DIR / "closed_picks.json"
    if fallback_path.exists():
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                picks = json.load(f)
            return [p for p in picks if p.get("pnl_pct") is not None]
        except Exception:
            pass

    return []


def _load_pnl_values() -> list[float]:
    """Load pnl_pct from closed picks.  Try dashboard payload first, then fallback."""
    pnl_values: list[float] = []

    # Primary: dashboard_payload.json -> picks.recent_closed
    payload_path = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
    if payload_path.exists():
        try:
            with open(payload_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            closed = data.get("picks", {}).get("recent_closed", [])
            pnl_values = [
                float(p["pnl_pct"])
                for p in closed
                if p.get("pnl_pct") is not None
                and not p.get("_auto_expired", False)
            ]
            if pnl_values:
                print(f"[risk_metrics] Loaded {len(pnl_values)} closed picks from dashboard_payload.json")
                return pnl_values
        except Exception as e:
            print(f"[risk_metrics] Warning: failed to read dashboard_payload.json: {e}")

    # Fallback: closed_picks.json
    fallback_path = DATA_DIR / "closed_picks.json"
    if fallback_path.exists():
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                picks = json.load(f)
            pnl_values = [
                float(p["pnl_pct"])
                for p in picks
                if p.get("pnl_pct") is not None
            ]
            if pnl_values:
                print(f"[risk_metrics] Loaded {len(pnl_values)} closed picks from closed_picks.json (fallback)")
                return pnl_values
        except Exception as e:
            print(f"[risk_metrics] Warning: failed to read closed_picks.json: {e}")

    return pnl_values


# ── Metric Computations (stdlib only) ─────────────────────────────────────────

def _percentile(sorted_vals: list[float], pct: float) -> float:
    """Linear-interpolation percentile on a pre-sorted list."""
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    k = (pct / 100.0) * (n - 1)
    lo = int(math.floor(k))
    hi = min(lo + 1, n - 1)
    frac = k - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


def compute_var(pnl: list[float], confidence: float = 0.95) -> float:
    """Value-at-Risk: the loss threshold at the given confidence level.

    Returns a positive number representing the worst-case daily loss
    at the (1 - confidence) tail.  For 95% VaR we look at the 5th percentile.
    """
    if not pnl:
        return 0.0
    sorted_pnl = sorted(pnl)
    cutoff_pct = (1.0 - confidence) * 100.0  # e.g. 5.0
    var_value = _percentile(sorted_pnl, cutoff_pct)
    return -var_value  # convention: VaR is positive when there is a loss


def compute_es(pnl: list[float], confidence: float = 0.95) -> float:
    """Expected Shortfall (CVaR): average loss beyond VaR.

    Returns a positive number.
    """
    if not pnl:
        return 0.0
    sorted_pnl = sorted(pnl)
    cutoff_pct = (1.0 - confidence) * 100.0
    var_value = _percentile(sorted_pnl, cutoff_pct)
    tail = [v for v in sorted_pnl if v <= var_value]
    if not tail:
        return -var_value
    return -(sum(tail) / len(tail))


def compute_gini(values: list[float]) -> float:
    """Gini coefficient of *absolute* PnL contributions.

    0 = perfectly equal, 1 = one pick holds all profit.
    Uses absolute values so both wins and losses contribute.
    """
    if not values:
        return 0.0
    abs_vals = sorted(abs(v) for v in values)
    n = len(abs_vals)
    total = sum(abs_vals)
    if total == 0:
        return 0.0
    # Mean absolute difference formula
    cumsum = 0.0
    weighted_sum = 0.0
    for i, v in enumerate(abs_vals):
        cumsum += v
        weighted_sum += (2 * (i + 1) - n - 1) * v
    return weighted_sum / (n * total)


def compute_sortino(pnl: list[float], target: float = 0.0) -> float:
    """Sortino ratio: mean excess return / downside deviation.

    Only penalises returns below *target* (default 0).
    """
    if len(pnl) < 2:
        return 0.0
    mean_ret = sum(pnl) / len(pnl)
    downside_sq = [((r - target) ** 2) for r in pnl if r < target]
    if not downside_sq:
        return float("inf") if mean_ret > 0 else 0.0
    downside_dev = math.sqrt(sum(downside_sq) / len(downside_sq))
    if downside_dev == 0:
        return 0.0
    return (mean_ret - target) / downside_dev


def compute_max_drawdown(pnl: list[float]) -> float:
    """Max drawdown from cumulative PnL curve.  Returns a positive number."""
    if not pnl:
        return 0.0
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in pnl:
        cum += r
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    return max_dd


def compute_calmar(pnl: list[float], trading_days: int = 365) -> float:
    """Calmar ratio: annualised return / max drawdown.

    Assumes each PnL entry ~ one trade-day for annualisation.
    """
    if not pnl:
        return 0.0
    total_return = sum(pnl)
    n = len(pnl)
    annual_return = (total_return / n) * trading_days if n > 0 else 0.0
    max_dd = compute_max_drawdown(pnl)
    if max_dd == 0:
        return float("inf") if annual_return > 0 else 0.0
    return annual_return / max_dd


# ── Gap 1: Realistic Sharpe (with fees) ──────────────────────────────────────

# DEPRECATED: Use alpha_engine.validation.sharpe_metrics instead (canonical implementation per TESTING_PROTOCOL v4.0)
def compute_sharpe(pnl: list[float], risk_free_per_trade: float = 0.0) -> float:
    """Standard Sharpe ratio: (mean_return - risk_free) / std_dev.

    Parameters:
        pnl: list of per-trade PnL percentages
        risk_free_per_trade: risk-free rate per trade period (default 0)
    """
    if len(pnl) < 2:
        return 0.0
    mean_ret = sum(pnl) / len(pnl)
    variance = sum((r - mean_ret) ** 2 for r in pnl) / (len(pnl) - 1)
    std_dev = math.sqrt(variance)
    if std_dev == 0:
        return 0.0
    return (mean_ret - risk_free_per_trade) / std_dev


def compute_realistic_sharpe(picks: list[dict]) -> dict:
    """Sharpe ratio computed on net-of-fees PnL.

    For each pick, deducts a round-trip transaction cost based on asset class:
      - crypto: 0.1% per side (0.2% round-trip)
      - forex:  0.02% per side (0.04% round-trip)
      - stock:  0.02% per side (0.04% round-trip)
      - meme:   0.5% per side (1.0% round-trip)

    Returns dict with gross_sharpe, realistic_sharpe, total_cost_drag, and
    the net PnL series statistics.
    """
    if len(picks) < 2:
        return {"gross_sharpe": 0.0, "realistic_sharpe": 0.0, "total_cost_drag": 0.0}

    gross_pnls = []
    net_pnls = []
    total_cost = 0.0

    for p in picks:
        pnl = float(p.get("pnl_pct", 0) or 0)
        gross_pnls.append(pnl)

        # Determine per-trade cost (round-trip = 2x one-way)
        category = (p.get("category", "") or "").lower()
        # Check if pick already has net_pnl computed with costs
        extra = p.get("extra_json", "")
        if isinstance(extra, str) and extra:
            try:
                extra_data = json.loads(extra)
                txn_cost = extra_data.get("transaction_cost_pct")
                if txn_cost is not None:
                    cost = float(txn_cost)
                    net_pnls.append(pnl - cost)
                    total_cost += cost
                    continue
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        # Fall back to default cost model
        one_way = _DEFAULT_COST.get(category, _DEFAULT_COST["crypto"])
        round_trip = one_way * 2.0
        net_pnls.append(pnl - round_trip)
        total_cost += round_trip

    gross_sharpe = compute_sharpe(gross_pnls)
    realistic_sharpe = compute_sharpe(net_pnls)

    return {
        "gross_sharpe": round(gross_sharpe, 4),
        "realistic_sharpe": round(realistic_sharpe, 4),
        "total_cost_drag_pct": round(total_cost, 4),
        "avg_cost_per_trade_pct": round(total_cost / len(picks), 6) if picks else 0.0,
        "net_mean_pnl_pct": round(sum(net_pnls) / len(net_pnls), 6) if net_pnls else 0.0,
    }


# ── Gap 2: Information Coefficient (IC) ──────────────────────────────────────

def _spearman_rank_correlation(x: list[float], y: list[float]) -> float:
    """Compute Spearman rank correlation between two lists (stdlib only).

    Uses the formula: rho = 1 - (6 * sum(d_i^2)) / (n * (n^2 - 1))
    where d_i is the difference in ranks.
    """
    n = len(x)
    if n < 3 or len(y) != n:
        return 0.0

    def _rank(vals: list[float]) -> list[float]:
        """Average-rank with tie handling."""
        indexed = sorted(enumerate(vals), key=lambda t: t[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0  # 1-based
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = _rank(x)
    ry = _rank(y)

    d_sq_sum = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    rho = 1.0 - (6.0 * d_sq_sum) / (n * (n * n - 1))
    return rho


def compute_information_coefficient(picks: list[dict]) -> dict:
    """Information Coefficient: Spearman rank correlation of score vs realized PnL.

    Tries these score fields in order: elite_score, ml_score, confidence.
    IC > 0.05 is considered predictive (Grinold & Kahn threshold).

    Returns dict with ic, score_field_used, n_picks, and interpretation.
    """
    if len(picks) < 10:
        return {
            "ic": 0.0,
            "score_field_used": "none",
            "n_picks": len(picks),
            "is_predictive": False,
            "interpretation": "Insufficient data (need >= 10 picks)",
        }

    # Try multiple score fields
    for score_field in ("elite_score", "ml_score", "confidence"):
        scores = []
        pnls = []
        for p in picks:
            s = p.get(score_field)
            pnl = p.get("pnl_pct")
            if s is not None and pnl is not None:
                try:
                    scores.append(float(s))
                    pnls.append(float(pnl))
                except (TypeError, ValueError):
                    continue

        if len(scores) >= 10:
            ic = _spearman_rank_correlation(scores, pnls)
            is_pred = abs(ic) > 0.05
            if ic > 0.10:
                interp = "Strong predictive signal"
            elif ic > 0.05:
                interp = "Moderate predictive signal (IC > 0.05)"
            elif ic > 0.02:
                interp = "Weak signal, marginal predictive value"
            elif ic > -0.02:
                interp = "No predictive value (IC near zero)"
            else:
                interp = "Negative IC -- scores inversely predict PnL"

            return {
                "ic": round(ic, 4),
                "score_field_used": score_field,
                "n_picks": len(scores),
                "is_predictive": is_pred,
                "interpretation": interp,
            }

    return {
        "ic": 0.0,
        "score_field_used": "none",
        "n_picks": 0,
        "is_predictive": False,
        "interpretation": "No score fields found in picks data",
    }


# ── Orchestration ──────────────────────────────────────────────────────────────

def run() -> dict:
    """Compute all risk metrics and save to JSON.  Returns the metrics dict."""
    pnl = _load_pnl_values()
    if not pnl:
        print("[risk_metrics] ERROR: No closed picks found -- cannot compute risk metrics.")
        return {}

    # Load full picks for IC and realistic Sharpe
    full_picks = _load_closed_picks_full()

    n = len(pnl)
    mean_pnl = sum(pnl) / n
    total_pnl = sum(pnl)

    var_95 = compute_var(pnl, 0.95)
    es_95 = compute_es(pnl, 0.95)
    gini = compute_gini(pnl)
    sortino = compute_sortino(pnl)
    max_dd = compute_max_drawdown(pnl)
    calmar = compute_calmar(pnl)

    # Gap 1: Realistic Sharpe (with fees deducted)
    gross_sharpe = compute_sharpe(pnl)
    sharpe_data = compute_realistic_sharpe(full_picks) if full_picks else {
        "gross_sharpe": round(gross_sharpe, 4),
        "realistic_sharpe": 0.0,
        "total_cost_drag_pct": 0.0,
        "avg_cost_per_trade_pct": 0.0,
        "net_mean_pnl_pct": 0.0,
    }

    # Gap 2: Information Coefficient
    ic_data = compute_information_coefficient(full_picks) if full_picks else {
        "ic": 0.0, "score_field_used": "none", "n_picks": 0,
        "is_predictive": False, "interpretation": "No data",
    }

    # Annualised ratios (sqrt-of-time scaling)
    sortino_annual = sortino * math.sqrt(365) if math.isfinite(sortino) else sortino
    realistic_sharpe_annual = (
        sharpe_data["realistic_sharpe"] * math.sqrt(365)
        if math.isfinite(sharpe_data["realistic_sharpe"]) else sharpe_data["realistic_sharpe"]
    )

    metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_closed_picks": n,
        "total_pnl_pct": round(total_pnl, 4),
        "mean_pnl_pct": round(mean_pnl, 4),
        "var_95_pct": round(var_95, 4),
        "es_95_pct": round(es_95, 4),
        "gini_coefficient": round(gini, 4),
        "sortino_ratio": round(sortino, 4),
        "sortino_ratio_annual": round(sortino_annual, 4) if math.isfinite(sortino_annual) else "inf",
        "max_drawdown_pct": round(max_dd, 4),
        "calmar_ratio": round(calmar, 4) if math.isfinite(calmar) else "inf",
        # Gap 1: Realistic Sharpe
        "gross_sharpe": sharpe_data["gross_sharpe"],
        "realistic_sharpe": sharpe_data["realistic_sharpe"],
        "realistic_sharpe_annual": round(realistic_sharpe_annual, 4) if math.isfinite(realistic_sharpe_annual) else "inf",
        "total_cost_drag_pct": sharpe_data["total_cost_drag_pct"],
        "avg_cost_per_trade_pct": sharpe_data["avg_cost_per_trade_pct"],
        "net_mean_pnl_pct": sharpe_data.get("net_mean_pnl_pct", 0.0),
        # Gap 2: Information Coefficient
        "information_coefficient": ic_data["ic"],
        "ic_score_field": ic_data["score_field_used"],
        "ic_is_predictive": ic_data["is_predictive"],
        "ic_interpretation": ic_data["interpretation"],
    }

    # ── Save risk_metrics.json ─────────────────────────────────────────────────
    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = DATA_DIR / "risk_metrics.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"[risk_metrics] Saved to {out_path}")

    # ── Append IC to precision_recall_report.json ──────────────────────────────
    pr_path = DATA_DIR / "precision_recall_report.json"
    pr_data = {}
    if pr_path.exists():
        try:
            with open(pr_path, "r", encoding="utf-8") as f:
                pr_data = json.load(f)
        except Exception:
            pr_data = {}
    pr_data["information_coefficient"] = ic_data
    pr_data["ic_updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(pr_path, "w", encoding="utf-8") as f:
        json.dump(pr_data, f, indent=2)
    print(f"[risk_metrics] IC data saved to {pr_path}")

    # ── Console summary ───────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  TAIL RISK & CONCENTRATION REPORT")
    print("=" * 60)
    print(f"  Closed picks analysed : {n}")
    print(f"  Total PnL             : {total_pnl:+.2f}%")
    print(f"  Mean PnL per pick     : {mean_pnl:+.4f}%")
    print("-" * 60)
    print(f"  VaR (95%)             : {var_95:.4f}%")
    print(f"      Interpretation    : 95% of days, loss < {var_95:.2f}%")
    print(f"  Expected Shortfall    : {es_95:.4f}%")
    print(f"      Interpretation    : When VaR is breached, avg loss = {es_95:.2f}%")
    print("-" * 60)
    print(f"  Gini coefficient      : {gini:.4f}")
    if gini > 0.6:
        print(f"      WARNING: High concentration -- few picks drive most PnL")
    elif gini > 0.4:
        print(f"      Moderate concentration")
    else:
        print(f"      PnL is well-distributed across picks")
    print("-" * 60)
    print(f"  Sortino ratio         : {sortino:.4f}")
    print(f"  Sortino (annualised)  : {sortino_annual:.4f}" if math.isfinite(sortino_annual) else f"  Sortino (annualised)  : inf")
    print(f"  Max drawdown          : {max_dd:.2f}%")
    print(f"  Calmar ratio          : {calmar:.4f}" if math.isfinite(calmar) else f"  Calmar ratio          : inf")
    print("-" * 60)
    print(f"  Gross Sharpe          : {sharpe_data['gross_sharpe']:.4f}")
    print(f"  Realistic Sharpe      : {sharpe_data['realistic_sharpe']:.4f}  (net of fees)")
    print(f"  Realistic Sharpe (ann): {realistic_sharpe_annual:.4f}" if math.isfinite(realistic_sharpe_annual) else f"  Realistic Sharpe (ann): inf")
    print(f"  Avg cost per trade    : {sharpe_data['avg_cost_per_trade_pct']*100:.4f}%")
    print("-" * 60)
    print(f"  Information Coeff.    : {ic_data['ic']:.4f}  ({ic_data['score_field_used']})")
    print(f"  IC predictive?        : {'YES' if ic_data['is_predictive'] else 'NO'}")
    print(f"      {ic_data['interpretation']}")
    print("=" * 60)

    return metrics


# ── Probabilistic Sharpe Ratio (PSR) — public API ────────────────────────────
#
# PSR converts a realized Sharpe and its standard error into a probability
# that the *true* Sharpe exceeds a benchmark. Reference:
#   Bailey & Lopez de Prado (2014), "The Sharpe Ratio Efficient Frontier".
#
# Why PSR over a hand-tuned trust tier?
#   - Trust tier is categorical, so it discretizes a continuous edge signal.
#   - PSR has known statistical interpretation (probability in [0, 1]) and
#     auto-penalises short track records (small n -> wide SE -> PSR -> 0.5).
#
# The implementation here is a thin wrapper around the canonical
# ``alpha_engine.validation.sharpe_metrics.probabilistic_sharpe_ratio``
# that accepts a plain iterable (list/tuple/np.array) of pnl_pct values
# (NOT pre-converted to Sharpe). Returns probability in [0, 1].
#
# A per-source PSR cache is built on cold start from
# ``audit_dashboard/data/dashboard_data.json`` (picks.recent_closed) and
# refreshed on a TTL. ``psr_points`` exposes a 0–15 band suitable as a
# drop-in replacement for the legacy trust-tier component in
# ``audit_trail/quality_gates.py::calculate_smart_score``.

# Minimum closed trades before PSR is considered reliable. Below this n,
# callers fall back to legacy trust-tier scoring (see quality_gates.py).
MIN_TRADES_FOR_PSR = 30

# Cache TTL (seconds). The dashboard_data.json snapshot is rewritten by the
# pipeline roughly hourly, so a 30-min TTL is conservative.
_PSR_CACHE_TTL_SEC = 1800

# Path to the dashboard snapshot used for the per-source cache.
_DASHBOARD_SNAPSHOT = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"

# Module-level cache state. Guarded by ``_PSR_CACHE_LOCK``.
_PSR_CACHE_LOCK = threading.Lock()
_PSR_CACHE: dict[str, dict] = {}     # source_system -> {"psr": float, "n": int}
_PSR_CACHE_BUILT_AT: float = 0.0      # epoch seconds; 0 means not yet built


def psr(returns: Iterable[float], benchmark_sharpe: float = 0.0) -> float:
    """Probabilistic Sharpe Ratio: P(true_sharpe > benchmark_sharpe).

    Parameters
    ----------
    returns : iterable of per-trade pnl in *fractional* form (e.g. 0.012 = 1.2%).
              List / tuple / numpy array all accepted.
    benchmark_sharpe : annualised Sharpe to test against. Default 0.0
              (i.e. probability the source beats coin-flip).

    Returns
    -------
    float in [0, 1].  Returns 0.0 on any failure (insufficient data,
    zero-variance series, missing scipy/pandas).  Never raises.
    """
    try:
        # Lazy import so a numpy/pandas/scipy failure doesn't break
        # the rest of risk_metrics.py.
        import pandas as pd  # noqa: PLC0415
        from alpha_engine.validation.sharpe_metrics import (  # noqa: PLC0415
            probabilistic_sharpe_ratio,
        )

        series = pd.Series([float(x) for x in returns if x is not None])
        if len(series) < 2:
            return 0.0
        val = probabilistic_sharpe_ratio(
            series,
            risk_free_rate=0.0,
            target_sharpe=float(benchmark_sharpe),
            freq="daily",
        )
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return 0.0
        # Clamp to [0, 1] in case of tiny float drift.
        return max(0.0, min(1.0, float(val)))
    except Exception:
        return 0.0


def _build_per_source_psr_cache() -> dict[str, dict]:
    """Pre-compute PSR per source_system from the dashboard snapshot.

    Reads ``audit_dashboard/data/dashboard_data.json`` -> picks.recent_closed,
    groups pnl_pct by source_system, and computes PSR(returns, benchmark=0)
    for every source with >= MIN_TRADES_FOR_PSR closed trades.

    pnl_pct is stored on the snapshot as a percentage (e.g. 1.2 = +1.2%).
    We convert to fractional returns (/100) so the underlying Sharpe math
    matches the canonical ``compute_sharpe`` convention.
    """
    if not _DASHBOARD_SNAPSHOT.exists():
        return {}

    try:
        with open(_DASHBOARD_SNAPSHOT, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    closed = snapshot.get("picks", {}).get("recent_closed", [])
    if not isinstance(closed, list):
        return {}

    # Group fractional returns per source.
    by_source: dict[str, list[float]] = {}
    for pick in closed:
        src = pick.get("source_system") or pick.get("source")
        if not src:
            continue
        pnl = pick.get("pnl_pct")
        if pnl is None:
            continue
        try:
            by_source.setdefault(str(src).lower(), []).append(float(pnl) / 100.0)
        except (TypeError, ValueError):
            continue

    out: dict[str, dict] = {}
    for src, returns in by_source.items():
        n = len(returns)
        if n < MIN_TRADES_FOR_PSR:
            # Skip — caller will fall back to trust tier for tiny n.
            continue
        out[src] = {"psr": psr(returns, benchmark_sharpe=0.0), "n": n}
    return out


def _ensure_psr_cache(force: bool = False) -> dict[str, dict]:
    """Return per-source PSR map, rebuilding if stale or unbuilt."""
    global _PSR_CACHE_BUILT_AT, _PSR_CACHE

    now = time.time()
    needs_build = (
        force
        or _PSR_CACHE_BUILT_AT == 0.0
        or (now - _PSR_CACHE_BUILT_AT) > _PSR_CACHE_TTL_SEC
    )
    if not needs_build:
        return _PSR_CACHE

    with _PSR_CACHE_LOCK:
        # Double-check after acquiring the lock.
        now = time.time()
        if not (
            force
            or _PSR_CACHE_BUILT_AT == 0.0
            or (now - _PSR_CACHE_BUILT_AT) > _PSR_CACHE_TTL_SEC
        ):
            return _PSR_CACHE
        _PSR_CACHE = _build_per_source_psr_cache()
        _PSR_CACHE_BUILT_AT = now
    return _PSR_CACHE


def psr_for_source(source_system: str) -> Optional[float]:
    """Return cached PSR for a source_system, or None if n < MIN_TRADES_FOR_PSR.

    Caller convention: ``None`` means "fall back to trust tier".
    """
    if not source_system:
        return None
    cache = _ensure_psr_cache()
    row = cache.get(str(source_system).lower())
    if not row:
        return None
    return row.get("psr")


def psr_points(source_system: str, fallback_pts: float = 0.0) -> float:
    """Map per-source PSR to a 0–12 point band for calculate_smart_score.

    Mapping (log-shape, calibrated against the PSR distribution per the
    integration spec — see PR body "Score mapping" section):
      PSR <= 0.20 ->  0 pts   (high probability of true_sharpe < 0)
      PSR == 0.50 ->  6 pts   (coin-flip on edge)
      PSR == 0.80 ->  9 pts   (industry "decent confidence" threshold)
      PSR >= 0.95 -> 12 pts   (Bailey-LdP "publishable" threshold)

    Linear interpolation between anchors. Total band 0–12 matches the
    documented trust-tier component (per the calculate_smart_score
    docstring) so downstream gates do not need recalibration.

    If the source has fewer than MIN_TRADES_FOR_PSR closed trades, returns
    ``fallback_pts`` (the caller's pre-computed legacy trust-tier points).
    """
    val = psr_for_source(source_system)
    if val is None:
        return fallback_pts

    # Anchor points: (psr_value, points).  Log-shape (faster early, then slows)
    # so middling PSRs aren't over-rewarded.
    anchors = [
        (0.00, 0.0),
        (0.20, 0.0),
        (0.50, 6.0),
        (0.80, 9.0),
        (0.95, 12.0),
        (1.00, 12.0),
    ]
    for i in range(len(anchors) - 1):
        lo_p, lo_v = anchors[i]
        hi_p, hi_v = anchors[i + 1]
        if val <= hi_p:
            if hi_p == lo_p:
                return lo_v
            frac = (val - lo_p) / (hi_p - lo_p)
            return lo_v + frac * (hi_v - lo_v)
    return 12.0


def reset_psr_cache() -> None:
    """Test hook — drop the cache so the next call rebuilds."""
    global _PSR_CACHE, _PSR_CACHE_BUILT_AT
    with _PSR_CACHE_LOCK:
        _PSR_CACHE = {}
        _PSR_CACHE_BUILT_AT = 0.0


if __name__ == "__main__":
    run()
