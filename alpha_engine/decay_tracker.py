"""Decay Tracker -- auto-demotion based on rolling Sharpe decline.

Monitors each strategy's 90-day rolling Sharpe and auto-demotion status:
- GREEN: Sharpe > 1.5 and stable
- YELLOW: Sharpe 0.8-1.5 or declining >20% from peak
- RED: Sharpe < 0.8 -- auto-demotion to paper trading
- BLACK: Sharpe < 0 or PF < 1.0 for 5+ consecutive days -- halt

Usage:
    from alpha_engine.decay_tracker import DecayTracker
    dt = DecayTracker()
    status = dt.check_strategy("Equity_L100", recent_returns)
    # status --> {"tier": "GREEN", "sharpe_90d": 2.1, "action": "MAINTAIN"}
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import numpy as np

from .statistical_rigor import sharpe as _sharpe


@dataclass
class StrategyStatus:
    """Current health status of a strategy."""
    strategy_name: str
    tier: str  # GREEN, YELLOW, RED, BLACK
    sharpe_90d: float | None = None
    sharpe_peak: float | None = None
    sharpe_decline_pct: float | None = None  # % decline from peak
    profit_factor_30d: float | None = None
    win_rate_30d: float | None = None
    n_trades_30d: int = 0
    consecutive_red_days: int = 0
    action: str = "MONITOR"  # MAINTAIN, REDUCE_SIZE, PAPER_TRADE, HALT
    size_multiplier: float = 1.0
    review_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "tier": self.tier,
            "sharpe_90d": round(self.sharpe_90d, 4) if self.sharpe_90d else None,
            "sharpe_peak": round(self.sharpe_peak, 4) if self.sharpe_peak else None,
            "sharpe_decline_pct": round(self.sharpe_decline_pct, 4) if self.sharpe_decline_pct else None,
            "profit_factor_30d": round(self.profit_factor_30d, 4) if self.profit_factor_30d else None,
            "win_rate_30d": round(self.win_rate_30d, 4) if self.win_rate_30d else None,
            "n_trades_30d": self.n_trades_30d,
            "consecutive_red_days": self.consecutive_red_days,
            "action": self.action,
            "size_multiplier": self.size_multiplier,
            "review_date": self.review_date,
        }


class DecayTracker:
    """Tracks strategy decay and manages auto-demotion ladder."""

    # Tier thresholds
    GREEN_SHARPE_MIN = 1.5
    YELLOW_SHARPE_MIN = 0.8
    RED_SHARPE_MIN = 0.0

    # Decline thresholds
    DECLINE_WARNING_PCT = 0.20  # 20% decline from peak --> YELLOW
    DECLINE_CRITICAL_PCT = 0.40  # 40% decline --> RED

    # Kill switch
    HALT_CONSECUTIVE_RED_DAYS = 5
    HALT_PF_FLOOR = 0.8

    # Size multipliers by tier
    SIZE_GREEN = 1.0
    SIZE_YELLOW = 0.5
    SIZE_RED = 0.25
    SIZE_BLACK = 0.0

    def __init__(self, state_file: str | None = None):
        self.state_file = state_file or os.environ.get(
            "DECAY_STATE_PATH", "alpha_engine/data/decay_tracker_state.json"
        )
        self._history: dict[str, list[dict]] = {}  # strategy -> daily metrics
        self._status: dict[str, StrategyStatus] = {}
        self._load_state()

    def _load_state(self) -> None:
        """Load previous state if exists."""
        if os.path.exists(self.state_file):
            with open(self.state_file) as f:
                data = json.load(f)
            for name, status_dict in data.get("status", {}).items():
                self._status[name] = StrategyStatus(**status_dict)
            self._history = data.get("history", {})

    def _save_state(self) -> None:
        """Persist current state."""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump({
                "last_updated": datetime.utcnow().isoformat(),
                "status": {k: v.to_dict() for k, v in self._status.items()},
                "history": self._history,
            }, f, indent=2, default=str)

    def _compute_sharpe(self, returns: np.ndarray, periods: int = 252) -> float:
        """Annualized Sharpe ratio."""
        if len(returns) < 10:
            return 0.0
        mean_ret = np.mean(returns)
        std_ret = np.std(returns, ddof=1)
        if std_ret == 0:
            return 0.0
        return float((mean_ret / std_ret) * math.sqrt(periods))

    def _compute_pf(self, returns: np.ndarray) -> float | None:
        """Profit factor from return series."""
        wins = np.sum(returns[returns > 0])
        losses = abs(np.sum(returns[returns < 0]))
        if losses == 0:
            return float("inf") if wins > 0 else None
        return float(wins / losses)

    def check_strategy(
        self, name: str, returns_90d: np.ndarray,
        returns_30d: np.ndarray | None = None
    ) -> StrategyStatus:
        """Check strategy health and determine tier/action.

        Args:
            name: strategy identifier
            returns_90d: last 90 days of daily returns
            returns_30d: last 30 days (optional, computed from 90d if not provided)
        """
        if returns_30d is None and len(returns_90d) >= 30:
            returns_30d = returns_90d[-30:]

        # Calculate metrics
        sharpe_90d = self._compute_sharpe(returns_90d)
        pf_30d = self._compute_pf(returns_30d) if returns_30d is not None else None

        # Track history
        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily_entry = {
            "date": today,
            "sharpe_90d": sharpe_90d,
            "pf_30d": pf_30d,
        }

        if name not in self._history:
            self._history[name] = []
        self._history[name].append(daily_entry)

        # Keep only last 180 days
        self._history[name] = self._history[name][-180:]

        # Peak Sharpe (rolling max over history)
        historical_sharpes = [h["sharpe_90d"] for h in self._history[name] if h["sharpe_90d"]]
        sharpe_peak = max(historical_sharpes) if historical_sharpes else sharpe_90d

        decline_pct = None
        if sharpe_peak and sharpe_peak > 0:
            decline_pct = (sharpe_peak - sharpe_90d) / sharpe_peak

        # Count consecutive RED days
        prev_status = self._status.get(name)
        consecutive_red = 0
        if prev_status and prev_status.tier in ("RED", "BLACK"):
            consecutive_red = prev_status.consecutive_red_days + 1

        # Determine tier
        tier, action, size_mult = self._determine_tier(
            sharpe_90d, decline_pct, pf_30d, consecutive_red
        )

        # Win rate 30d
        if returns_30d is not None and len(returns_30d) > 0:
            wr_30d = float(np.mean(returns_30d > 0))
            n_trades = len(returns_30d)
        else:
            wr_30d = None
            n_trades = 0

        # Review date for non-GREEN
        review_date = None
        if tier != "GREEN":
            review_date = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")

        status = StrategyStatus(
            strategy_name=name,
            tier=tier,
            sharpe_90d=sharpe_90d,
            sharpe_peak=sharpe_peak,
            sharpe_decline_pct=decline_pct,
            profit_factor_30d=pf_30d,
            win_rate_30d=wr_30d,
            n_trades_30d=n_trades,
            consecutive_red_days=consecutive_red if tier in ("RED", "BLACK") else 0,
            action=action,
            size_multiplier=size_mult,
            review_date=review_date,
        )

        self._status[name] = status
        self._save_state()

        return status

    def _determine_tier(
        self, sharpe: float, decline_pct: float | None,
        pf: float | None, consecutive_red: int
    ) -> tuple[str, str, float]:
        """Determine tier, action, and size multiplier."""

        # BLACK: halt conditions
        if consecutive_red >= self.HALT_CONSECUTIVE_RED_DAYS:
            return "BLACK", "HALT", self.SIZE_BLACK
        if pf is not None and pf < self.HALT_PF_FLOOR and sharpe < self.RED_SHARPE_MIN:
            return "BLACK", "HALT", self.SIZE_BLACK

        # RED: Sharpe < 0.8 or critical decline
        if sharpe < self.YELLOW_SHARPE_MIN:
            return "RED", "PAPER_TRADE", self.SIZE_RED
        if decline_pct and decline_pct > self.DECLINE_CRITICAL_PCT:
            return "RED", "PAPER_TRADE", self.SIZE_RED

        # YELLOW: moderate Sharpe or warning decline
        if sharpe < self.GREEN_SHARPE_MIN:
            return "YELLOW", "REDUCE_SIZE", self.SIZE_YELLOW
        if decline_pct and decline_pct > self.DECLINE_WARNING_PCT:
            return "YELLOW", "REDUCE_SIZE", self.SIZE_YELLOW

        # GREEN: healthy
        return "GREEN", "MAINTAIN", self.SIZE_GREEN

    def get_all_statuses(self) -> dict[str, StrategyStatus]:
        """Get all strategy statuses."""
        return dict(self._status)

    def export_dashboard(self, output_path: str | None = None) -> dict[str, Any]:
        """Export for audit dashboard consumption."""
        output_path = output_path or "alpha_engine/data/decay_dashboard.json"

        statuses = {k: v.to_dict() for k, v in self._status.items()}

        summary = {
            "total": len(statuses),
            "GREEN": sum(1 for s in statuses.values() if s["tier"] == "GREEN"),
            "YELLOW": sum(1 for s in statuses.values() if s["tier"] == "YELLOW"),
            "RED": sum(1 for s in statuses.values() if s["tier"] == "RED"),
            "BLACK": sum(1 for s in statuses.values() if s["tier"] == "BLACK"),
        }

        output = {
            "generated_at": datetime.utcnow().isoformat(),
            "summary": summary,
            "strategies": statuses,
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        return output

    def get_kill_switch_alerts(self) -> list[dict[str, Any]]:
        """Get immediate kill switch alerts (BLACK tier strategies)."""
        alerts = []
        for name, status in self._status.items():
            if status.tier == "BLACK":
                alerts.append({
                    "strategy": name,
                    "alert": "KILL_SWITCH_TRIGGERED",
                    "consecutive_red_days": status.consecutive_red_days,
                    "action": "HALT_IMMEDIATELY",
                    "size_multiplier": 0.0,
                })
        return alerts


# ---------------------------------------------------------------------------
# Per-source decay blocks (Theme F): rolling-90d vs rolling-365d Sharpe
# ---------------------------------------------------------------------------
# Stateless function used by tools/run_strategy_research.py and tests. Restored
# after a91419 (DecayTracker class refactor) accidentally dropped it. Original
# spec lives in PR #626 (commit c3e109f0a6c).
def _parse_ts(ts) -> datetime | None:
    """Best-effort parse of the closed_picks.json timestamp formats."""
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if not isinstance(ts, str) or not ts:
        return None
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:
            dt = datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def compute_decay_blocks(
    closed_picks: Iterable[dict],
    *,
    short_days: int = 90,
    long_days: int = 365,
    min_short_window_trades: int = 10,
    min_long_window_trades: int = 30,
    decay_threshold: float = 0.5,
    now: datetime | None = None,
    pnl_field: str = "pnl_pct",
    ts_field: str = "closed_at",
    source_field: str = "source_system",
) -> dict:
    """Per-source-system decay block.

    Returns ``{source_system: {sharpe_short, sharpe_long, ratio, status,
    n_short, n_long}}``. ``status`` is one of:

        * ``"healthy"``      -- ratio >= decay_threshold
        * ``"decaying"``     -- ratio < decay_threshold
        * ``"insufficient"`` -- not enough trades in either window
    """
    ref = now or datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    short_cut = ref - timedelta(days=short_days)
    long_cut = ref - timedelta(days=long_days)

    short_pnl: dict[str, list[float]] = {}
    long_pnl: dict[str, list[float]] = {}
    for p in closed_picks:
        src = p.get(source_field) or "unknown"
        ts = _parse_ts(p.get(ts_field) or p.get("resolved_at") or p.get("timestamp"))
        if ts is None:
            continue
        pnl = p.get(pnl_field)
        if pnl is None:
            continue
        try:
            pnl_f = float(pnl)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(pnl_f):
            continue
        if ts >= long_cut:
            long_pnl.setdefault(src, []).append(pnl_f)
        if ts >= short_cut:
            short_pnl.setdefault(src, []).append(pnl_f)

    out: dict[str, dict] = {}
    sources = set(long_pnl) | set(short_pnl)
    for src in sources:
        short_returns = short_pnl.get(src, [])
        long_returns = long_pnl.get(src, [])
        n_short = len(short_returns)
        n_long = len(long_returns)
        if n_short < min_short_window_trades or n_long < min_long_window_trades:
            out[src] = {
                "sharpe_short": None,
                "sharpe_long": None,
                "ratio": None,
                "status": "insufficient",
                "n_short": n_short,
                "n_long": n_long,
            }
            continue
        sh_short = _sharpe(short_returns, periods_per_year=252.0)
        sh_long = _sharpe(long_returns, periods_per_year=252.0)
        if sh_long == 0:
            ratio = None
            status = "insufficient"
        else:
            ratio = sh_short / sh_long
            status = "healthy" if ratio >= decay_threshold else "decaying"
        out[src] = {
            "sharpe_short": sh_short,
            "sharpe_long": sh_long,
            "ratio": ratio,
            "status": status,
            "n_short": n_short,
            "n_long": n_long,
        }
    return out


__all__ = [
    "StrategyStatus",
    "DecayTracker",
    "compute_decay_blocks",
]
