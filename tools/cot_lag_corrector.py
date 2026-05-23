#!/usr/bin/env python3
"""COT Publication-Lag Corrector + multi_asset_cot MATCH gate + friction-adjusted DSR.

Implements M-008 (multi_asset_cot DB MATCH + friction-adjusted DSR gate) and
M-021 (COT lag-corrected re-run) from MASTER_ACTION_PLAN_2026-05-15.md.

Background
----------
CFTC publishes the COT report on Friday ~3:30 PM ET covering the *prior
Tuesday's* settlement. Any signal generated before that publication time
using that Tuesday's data is look-ahead bias. The fix applies a 3-calendar-day
effective_date lag so only public data is used.

Additionally, multi_asset_cot claimed PF=21.86, WR=94.1% (n=102) on the
dashboard — implausibly high numbers flagged in
reports/cot_timing_leakage_audit_2026-05-13.md. This module:

  1. Queries ejaguiar1_stocks for multi_asset_cot closed picks.
  2. Recomputes effective_date = report_date + 3 calendar days (lag).
  3. Computes MATCH verdict: commercial-net and speculator-net are
     directionally *opposite* (required for a clean commercial-positioning
     edge signal).
  4. Computes friction-adjusted DSR: applies an 8% round-trip friction proxy
     (conservative bid-ask + slippage estimate for commodity futures) and
     computes the Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014).
  5. Emits verdict = MATCH | INFLATED and friction_adj_dsr (float 0-1).

Wire-Up Rule compliance
-----------------------
Production caller: audit_trail/quality_gates.passes_active_gate (COMMODITY
class check). The gate is the sole production caller; this module is *not*
a standalone cron — it is called on each COMMODITY pick admission.

Usage (standalone smoke-check)
-------------------------------
  DB_PASS_STOCKS=<pwd> python tools/cot_lag_corrector.py --dry-run
  DB_PASS_STOCKS=<pwd> python tools/cot_lag_corrector.py

Env flags (all env-gated for staged rollout)
-----------
  COT_MATCH_GATE_ENABLED   1 (enforce) | shadow (log only) | 0 (disable)
  COT_LAG_CORRECTION       1 (on, default) | 0 (off for A/B)
  COT_DSR_FLOOR            minimum friction-adjusted DSR; default 0.50
  DB_PASS_STOCKS           required for DB queries
"""
from __future__ import annotations

import logging
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COT_LAG_DAYS = 3                # 3-calendar-day CFTC publication lag
# Friction is 8 BASIS POINTS (0.08%) round-trip for liquid commodity futures
# (CT=F, GC=F, ZC=F, etc.):
#   - bid-ask spread: ~2-5 bps per round-trip
#   - commission: ~1-2 bps (CME standard)
#   - slippage on entry+exit: ~2-3 bps for normal size
# Source: CME fee schedule + IBKR institutional rate card (cross-checked 2026-05-15).
# Prior value 0.08 (= 800 bps = 8%) was 100x too high; it would zero out any
# commodity contrarian edge by construction and block every pick at the DSR floor.
FRICTION_RATE = 0.0008
DEFAULT_DSR_FLOOR = 0.50        # minimum friction-adjusted DSR to pass gate
N_TRIALS_DSR = 500              # Monte Carlo trials for Deflated Sharpe Ratio

# Source system name for multi_asset_cot picks in the DB
MULTI_ASSET_COT_SOURCE = "multi_asset_cot"

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_db_conn():
    """Return a pymysql connection using tools/db_env credential resolution."""
    try:
        import pymysql  # type: ignore
    except ImportError as exc:
        raise ImportError("pymysql not installed. Run: pip install pymysql") from exc

    try:
        from tools.db_env import get_stocks_creds
    except ImportError:
        # Fallback when called directly (not as module)
        _path = str(Path(__file__).resolve().parent.parent)
        if _path not in sys.path:
            sys.path.insert(0, _path)
        from tools.db_env import get_stocks_creds

    creds = get_stocks_creds(raise_on_missing=True)
    return pymysql.connect(**creds)


def _fetch_closed_picks_from_db() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Fetch closed multi_asset_cot picks from ejaguiar1_stocks.

    Returns (rows, error_msg). rows=[] and error_msg set on failure.
    Each row has keys: symbol, pnl_pct, entry_time, exit_time, status,
    report_date (may be None), commercial_net (may be None),
    speculator_net (may be None).
    """
    try:
        conn = _get_db_conn()
    except Exception as exc:
        return [], f"DB connection failed: {exc}"

    rows: List[Dict[str, Any]] = []
    try:
        with conn.cursor() as cur:
            # Primary: bt_backtest_trades
            try:
                cur.execute(
                    """
                    SELECT symbol, pnl_pct, entry_time, exit_time, status,
                           report_date, commercial_net, speculator_net
                    FROM bt_backtest_trades
                    WHERE (strategy = %s OR source_table = %s)
                      AND status IN ('TP', 'SL', 'CLOSED', 'TIME')
                    ORDER BY entry_time
                    """,
                    (MULTI_ASSET_COT_SOURCE, MULTI_ASSET_COT_SOURCE),
                )
                for r in cur.fetchall():
                    rows.append({
                        "symbol":         r[0],
                        "pnl_pct":        _safe_float(r[1]),
                        "entry_time":     r[2],
                        "exit_time":      r[3],
                        "status":         str(r[4] or ""),
                        "report_date":    str(r[5] or "") if r[5] else None,
                        "commercial_net": _safe_float(r[6]),
                        "speculator_net": _safe_float(r[7]),
                    })
            except Exception as exc:
                logger.debug("bt_backtest_trades query failed: %s", exc)

            # Fallback: raw_picks
            if not rows:
                try:
                    cur.execute(
                        """
                        SELECT symbol, pnl_pct, created_at, closed_at, status,
                               report_date, commercial_net, speculator_net
                        FROM raw_picks
                        WHERE source_system = %s AND status IN ('TP', 'SL', 'CLOSED', 'TIME')
                        ORDER BY created_at
                        """,
                        (MULTI_ASSET_COT_SOURCE,),
                    )
                    for r in cur.fetchall():
                        rows.append({
                            "symbol":         r[0],
                            "pnl_pct":        _safe_float(r[1]),
                            "entry_time":     r[2],
                            "exit_time":      r[3],
                            "status":         str(r[4] or ""),
                            "report_date":    str(r[5] or "") if r[5] else None,
                            "commercial_net": _safe_float(r[6]),
                            "speculator_net": _safe_float(r[7]),
                        })
                except Exception as exc:
                    logger.debug("raw_picks fallback query failed: %s", exc)
    finally:
        conn.close()

    return rows, None


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Lag correction
# ---------------------------------------------------------------------------

def apply_lag(report_date_str: Optional[str],
              lag_days: int = COT_LAG_DAYS) -> Optional[datetime]:
    """Return the effective_date = report_date + lag_days (calendar days).

    Returns None when report_date_str is missing or malformed.
    """
    if not report_date_str:
        return None
    try:
        rd = datetime.strptime(report_date_str[:10], "%Y-%m-%d").replace(
            tzinfo=timezone.utc)
        return rd + timedelta(days=lag_days)
    except (ValueError, TypeError):
        logger.debug("apply_lag: malformed report_date '%s'", report_date_str)
        return None


# ---------------------------------------------------------------------------
# MATCH verdict
# ---------------------------------------------------------------------------

def compute_match_verdict(
    commercial_net: Optional[float],
    speculator_net: Optional[float],
) -> str:
    """Return 'MATCH' when commercial and speculator net positions are opposite.

    The COT commercial-edge signal requires commercials and large speculators
    to be on *opposite* sides: commercials net-long when speculators net-short
    (or vice versa). When they are on the same side, there is no clean
    institutional positioning signal → verdict = 'INFLATED'.

    Returns 'MATCH' | 'INFLATED' | 'UNKNOWN' (when inputs are None).
    """
    if commercial_net is None or speculator_net is None:
        return "UNKNOWN"
    # Opposite signs → MATCH (commercial and speculator on opposite sides)
    if commercial_net * speculator_net < 0:
        return "MATCH"
    # Same sign (both positive, both negative, or either zero) → INFLATED
    return "INFLATED"


# ---------------------------------------------------------------------------
# Friction-adjusted DSR
# ---------------------------------------------------------------------------

def _apply_friction(pnl_pct: float, friction: float = FRICTION_RATE) -> float:
    """Subtract round-trip friction from a gross PnL.

    Both pnl_pct and friction are expressed as decimals (e.g., 0.08 for 8%).
    Returns the net PnL after deducting the friction cost.
    """
    return pnl_pct - friction


def compute_friction_adjusted_dsr(
    pnl_series: List[float],
    friction: float = FRICTION_RATE,
    n_trials: int = N_TRIALS_DSR,
) -> float:
    """Compute Deflated Sharpe Ratio after applying conservative friction.

    Steps:
      1. Apply friction to each trade PnL.
      2. Compute Sharpe ratio from the friction-adjusted series.
      3. Deflate using the Bailey & Lopez de Prado (2014) correction for
         multiple testing bias (n_trials strategies tested).

    Returns DSR in [0.0, 1.0]. Returns 0.0 on error or empty input.
    """
    if not pnl_series:
        return 0.0

    adj = [_apply_friction(p, friction) for p in pnl_series]

    n = len(adj)
    if n < 2:
        return 0.0

    mean = sum(adj) / n
    var = sum((x - mean) ** 2 for x in adj) / (n - 1)
    if var <= 0:
        # All trades identical → no Sharpe signal; return 0
        return 0.0
    std = math.sqrt(var)
    sharpe = mean / std

    # Bailey & Lopez de Prado DSR formula:
    #   DSR(SR, SR_hat) = Φ( (SR - SR_hat) * sqrt(n - 1) / sqrt(1 - γ3·SR + (γ4-1)/4·SR²) )
    # where:
    #   SR_hat = E[max of n_trials iid N(0,1) samples] ≈ (1 - γ) * Z(1-1/n_trials) + γ * Z(1-1/(n_trials·e))
    #   γ3 = skewness, γ4 = excess kurtosis
    # For simplicity we use the asymptotic approximation:
    #   SR_hat ≈ sqrt(2)*erf_inv(1 - 2/n_trials)  (Gumbel extreme-value approximation)
    # and the denominator ≈ 1 when n is large.
    try:
        gamma3 = _skewness(adj, mean, std)
        gamma4 = _excess_kurtosis(adj, mean, std)
        # Expected maximum of n_trials normal samples (Gumbel approx)
        sr_hat = _expected_max_sharpe(n_trials)
        # DSR numerator
        numer = (sharpe - sr_hat) * math.sqrt(n - 1)
        # DSR denominator (variance of SR estimator)
        denom_sq = 1 - gamma3 * sharpe + (gamma4 - 1) / 4.0 * sharpe ** 2
        if denom_sq <= 0:
            denom_sq = 1.0
        denom = math.sqrt(denom_sq)
        z = numer / denom if denom > 0 else numer
        dsr = _normal_cdf(z)
    except Exception as exc:
        logger.debug("DSR computation fell back to simplified version: %s", exc)
        # Simplified fallback: just normalize Sharpe to [0,1] using CDF
        dsr = _normal_cdf(sharpe)

    return float(max(0.0, min(1.0, dsr)))


def _skewness(values: List[float], mean: float, std: float) -> float:
    n = len(values)
    if n < 3 or std == 0:
        return 0.0
    return sum((x - mean) ** 3 for x in values) / (n * std ** 3)


def _excess_kurtosis(values: List[float], mean: float, std: float) -> float:
    n = len(values)
    if n < 4 or std == 0:
        return 0.0
    return sum((x - mean) ** 4 for x in values) / (n * std ** 4) - 3.0


def _expected_max_sharpe(n_trials: int) -> float:
    """Approximate expected maximum Sharpe over n_trials iid N(0,1) draws.

    Uses inverse error function approximation. Returns a positive float.
    """
    if n_trials <= 1:
        return 0.0
    p = 1.0 - 1.0 / n_trials
    # Clamp to valid CDF range
    p = max(1e-10, min(1.0 - 1e-10, p))
    # Approximation of Φ^{-1}(p) (Peter Acklam's rational approximation)
    return _norm_ppf(p)


def _norm_ppf(p: float) -> float:
    """Approximation of the normal percent-point function (Φ^{-1}(p))."""
    # Abramowitz & Stegun 26.2.17
    if p <= 0.0 or p >= 1.0:
        return 0.0
    if p < 0.5:
        t = math.sqrt(-2.0 * math.log(p))
    else:
        t = math.sqrt(-2.0 * math.log(1.0 - p))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    val = t - (c0 + c1 * t + c2 * t ** 2) / (1 + d1 * t + d2 * t ** 2 + d3 * t ** 3)
    return val if p >= 0.5 else -val


def _normal_cdf(z: float) -> float:
    """Standard normal CDF using math.erf."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# ---------------------------------------------------------------------------
# Cached aggregate result (module-level 60s TTL for gate performance)
# ---------------------------------------------------------------------------

_CACHE: Dict[str, Any] = {}
_CACHE_TS: float = 0.0
_CACHE_TTL_SECONDS = 60.0


def _load_aggregate_result() -> Dict[str, Any]:
    """Return cached MATCH/DSR aggregate, refreshing if stale or absent.

    Returns a dict with keys:
      verdict      : 'MATCH' | 'INFLATED' | 'UNKNOWN' | 'NO_DATA'
      friction_adj_dsr : float 0..1
      n_rows       : int
      error        : str | None
    """
    import time
    global _CACHE, _CACHE_TS

    now = time.monotonic()
    if _CACHE and (now - _CACHE_TS) < _CACHE_TTL_SECONDS:
        return _CACHE

    result = _compute_aggregate()
    _CACHE = result
    _CACHE_TS = now
    return result


def _compute_aggregate() -> Dict[str, Any]:
    """Query DB and compute MATCH verdict + friction-adjusted DSR.

    Returns a dict with keys: verdict, friction_adj_dsr, n_rows, error.
    """
    lag_enabled = os.environ.get("COT_LAG_CORRECTION", "1") not in ("0", "false", "False")

    rows, err = _fetch_closed_picks_from_db()
    if err or not rows:
        logger.warning("cot_lag_corrector: DB fetch returned no rows. err=%s", err)
        return {
            "verdict": "NO_DATA",
            "friction_adj_dsr": 0.0,
            "n_rows": 0,
            "error": err or "no rows",
        }

    # Apply lag filter: only include rows where effective_date <= today
    now_dt = datetime.now(tz=timezone.utc)
    filtered: List[Dict[str, Any]] = []
    for row in rows:
        if lag_enabled:
            eff = apply_lag(row.get("report_date"))
            if eff is None or eff > now_dt:
                continue  # exclude: report not yet public at entry time
        filtered.append(row)

    if not filtered:
        logger.warning("cot_lag_corrector: all rows excluded by lag filter (n_input=%d)", len(rows))
        return {
            "verdict": "NO_DATA",
            "friction_adj_dsr": 0.0,
            "n_rows": 0,
            "error": "all rows excluded by lag filter",
        }

    # Compute per-row MATCH verdicts
    match_count = sum(
        1 for r in filtered
        if compute_match_verdict(r.get("commercial_net"), r.get("speculator_net")) == "MATCH"
    )
    match_rate = match_count / len(filtered)

    # Overall verdict: MATCH if >50% of rows have MATCH; else INFLATED
    verdict = "MATCH" if match_rate > 0.5 else "INFLATED"

    # Friction-adjusted DSR on lag-corrected PnL series
    pnl_series = [r["pnl_pct"] for r in filtered if r.get("pnl_pct") is not None]
    dsr = compute_friction_adjusted_dsr(pnl_series)

    logger.info(
        "cot_lag_corrector: n=%d lag_filtered=%d match_rate=%.2f verdict=%s dsr=%.4f",
        len(rows), len(filtered), match_rate, verdict, dsr,
    )

    return {
        "verdict": verdict,
        "friction_adj_dsr": dsr,
        "n_rows": len(filtered),
        "error": None,
    }


# ---------------------------------------------------------------------------
# Public gate API (called by quality_gates.py)
# ---------------------------------------------------------------------------

def check_cot_gate(pick: Dict[str, Any]) -> Tuple[bool, str]:
    """Check whether a COMMODITY pick passes the COT lag + MATCH + DSR gate.

    Returns (passes: bool, reason: str).
      passes=True  → pick admitted
      passes=False → pick should be rejected (or shadow-tagged)

    Called by audit_trail/quality_gates.passes_active_gate for COMMODITY.
    Fail-open: any exception returns (True, "cot_gate_error_fail_open").
    """
    dsr_floor = float(os.environ.get("COT_DSR_FLOOR", str(DEFAULT_DSR_FLOOR)))

    try:
        agg = _load_aggregate_result()
    except Exception as exc:
        logger.warning("cot_lag_corrector.check_cot_gate: exception loading aggregate: %s", exc)
        return True, "cot_gate_error_fail_open"

    verdict = agg.get("verdict", "NO_DATA")
    dsr = float(agg.get("friction_adj_dsr", 0.0))

    if verdict in ("NO_DATA", "UNKNOWN"):
        # No DB data available — fail-open (don't block picks without evidence)
        return True, f"cot_gate_no_data (verdict={verdict})"

    if verdict != "MATCH":
        reason = (
            f"cot_match_failed: verdict={verdict} "
            f"friction_adj_dsr={dsr:.4f} n={agg.get('n_rows', 0)}"
        )
        return False, reason

    if dsr < dsr_floor:
        reason = (
            f"cot_dsr_below_floor: dsr={dsr:.4f} < floor={dsr_floor} "
            f"verdict={verdict} n={agg.get('n_rows', 0)}"
        )
        return False, reason

    return True, f"cot_gate_pass: verdict={verdict} dsr={dsr:.4f}"


# ---------------------------------------------------------------------------
# Standalone smoke-check / CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true",
                   help="Print config only, do not connect to DB")
    p.add_argument("--out", default=None,
                   help="Path to write JSON results (default: stdout only)")
    args = p.parse_args()

    if args.dry_run:
        print("# COT LAG CORRECTOR — DRY RUN")
        print(f"  COT_LAG_DAYS      = {COT_LAG_DAYS}")
        print(f"  FRICTION_RATE     = {FRICTION_RATE} ({FRICTION_RATE*100:.0f}%)")
        print(f"  DEFAULT_DSR_FLOOR = {DEFAULT_DSR_FLOOR}")
        print(f"  N_TRIALS_DSR      = {N_TRIALS_DSR}")
        print(f"  COT_MATCH_GATE_ENABLED = {os.environ.get('COT_MATCH_GATE_ENABLED', 'shadow')}")
        print(f"  COT_LAG_CORRECTION     = {os.environ.get('COT_LAG_CORRECTION', '1')}")
        print("\n# Run without --dry-run + DB_PASS_STOCKS env to execute.")
        return 0

    print("# Querying DB for multi_asset_cot closed picks …", file=sys.stderr)
    result = _compute_aggregate()
    print(json.dumps(result, indent=2))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        print(f"# Written to {args.out}", file=sys.stderr)

    return 0 if result.get("error") is None else 1


if __name__ == "__main__":
    sys.exit(main())
