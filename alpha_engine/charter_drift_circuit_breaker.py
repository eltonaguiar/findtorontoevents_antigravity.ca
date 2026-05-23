"""Charter §7 drift circuit-breaker — auto-disable sizing when realized WR
collapses vs backtest baseline.

Companion to charter_position_sizer.py + charter_slippage.py. Pure functions,
no I/O at import. Reads `recent_closed` for realized WR and
`walkforward.by_class` for the backtest baseline; trips when realized falls
more than 2 sigma below baseline.

Spec: reports/implementation_plan_v2_2026-05-13.md P0.5-3.

Rationale: CRYPTO has a documented −31.12pp backtest-vs-live gap that today is
*charted but not acted on*. This module produces a deterministic kill-switch
verdict so sizing flips to 0 automatically when drift breaches threshold.

The "n<30 cold-start" guard is critical: a thin recent sample can be 100%
losses by chance and would false-positive trip. The breaker only fires when
the realized sample is large enough to make the comparison meaningful.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any


DEFAULT_LOOKBACK_DAYS: int = 30
# Lowered 30→20 (2026-05-17 swarm Q5): ETF has ~25 resolved/30d which always
# cold-started at 30, preventing circuit-breaker coverage. At n=20 a 2σ trip
# still requires WR<28% (binomial σ≈11%), so the guard against thin-sample
# false positives holds. BOND (n≈12 total) still cold-starts, which is correct.
DEFAULT_MIN_REALIZED_N: int = 20
DEFAULT_SIGMA_THRESHOLD: float = 2.0


def _parse_timestamp(ts: Any) -> datetime | None:
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def compute_realized_wr_30d(
    recent_closed: list[dict],
    asset_class: str,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    now: datetime | None = None,
) -> tuple[float | None, int]:
    """Return (realized_wr_pct, n) over the last `lookback_days` for the given
    asset_class. Reads BOTH `_outcome` and `status` so the function works
    pre- and post- resolver-gap fix. Returns (None, 0) if no resolved picks.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback_days)
    target = asset_class.upper()
    wins = 0
    losses = 0
    for r in recent_closed:
        if not isinstance(r, dict):
            continue
        if str(r.get("asset_class", "")).upper() != target:
            continue
        outc = (r.get("_outcome") or r.get("status") or "").upper()
        # Accept both "WIN"/"LOSS" (_outcome field) and "WON"/"LOST" (status field).
        if outc not in ("WIN", "WON", "LOSS", "LOST"):
            continue
        # Use close timestamp for the 30d window — entry `timestamp` predates close.
        ts = _parse_timestamp(
            r.get("closed_at") or r.get("resolved_at")
            or r.get("close_time") or r.get("timestamp")
        )
        if ts is None or ts < cutoff:
            continue
        if outc in ("WIN", "WON"):
            wins += 1
        else:
            losses += 1
    n = wins + losses
    if n == 0:
        return None, 0
    return 100.0 * wins / n, n


def is_sizing_breached(
    recent_closed: list[dict],
    walkforward_by_class: dict[str, dict],
    asset_class: str,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    min_realized_n: int = DEFAULT_MIN_REALIZED_N,
    sigma_threshold: float = DEFAULT_SIGMA_THRESHOLD,
    now: datetime | None = None,
) -> tuple[bool, str]:
    """Return (breached, reason). breached=True means sizing should be flipped
    to 0 for this asset class.

    Trip rule: realized_wr_30d < (backtest_oos_wr - sigma_threshold * oos_wr_std).

    Conservative guards:
    - Returns (False, "cold_start") when realized n < min_realized_n
    - Returns (False, "no_backtest") when walkforward.by_class missing this class
    - Returns (False, "no_baseline") when oos_wr is None or oos_wr_std is None
    """
    wf = walkforward_by_class.get(asset_class.upper())
    if not wf:
        return False, "no_backtest"
    backtest_wr = wf.get("oos_wr")
    backtest_std = wf.get("oos_wr_std")
    if backtest_wr is None or backtest_std is None:
        return False, "no_baseline"

    realized_wr, realized_n = compute_realized_wr_30d(
        recent_closed, asset_class,
        lookback_days=lookback_days, now=now,
    )
    if realized_n < min_realized_n:
        return False, f"cold_start (n={realized_n}<{min_realized_n})"

    lower_bound = float(backtest_wr) - sigma_threshold * float(backtest_std)
    if realized_wr < lower_bound:
        return True, (
            f"drift_breach: realized_wr_30d={realized_wr:.1f}% < "
            f"backtest_wr ({backtest_wr:.1f}%) - {sigma_threshold}*sigma "
            f"({backtest_std:.1f}%) = {lower_bound:.1f}%"
        )
    return False, (
        f"ok: realized_wr_30d={realized_wr:.1f}% >= "
        f"{lower_bound:.1f}% lower bound"
    )


def evaluate_all_classes(
    recent_closed: list[dict],
    walkforward_by_class: dict[str, dict],
    classes: list[str] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, dict]:
    """Run is_sizing_breached for every class and return a verdict map suitable
    for /audit consumption.
    """
    if classes is None:
        classes = ["CRYPTO", "EQUITY", "ETF", "COMMODITY", "FOREX", "BOND", "FUTURES"]
    out = {}
    for cls in classes:
        breached, reason = is_sizing_breached(
            recent_closed, walkforward_by_class, cls, now=now,
        )
        realized_wr, realized_n = compute_realized_wr_30d(
            recent_closed, cls, now=now,
        )
        out[cls] = {
            "breached": breached,
            "reason": reason,
            "realized_wr_30d": realized_wr,
            "realized_n_30d": realized_n,
        }
    return out
