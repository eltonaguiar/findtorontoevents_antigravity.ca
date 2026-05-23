"""
Walk-Forward Validation

The gold standard for time-series strategy validation.
Train on window, test on next period, roll forward.
No lookahead bias by construction.

Includes two validators:
  1. WalkForwardValidator  — operates on raw price/feature DataFrames (original)
  2. TradeWalkForwardValidator — operates on trade-level dicts
     (entry_date, exit_date, pnl_pct, symbol, asset_class)

Asset-specific windows per TESTING_PROTOCOL Layer 3:
  crypto:          6-month train  / 6-week forward
  equity / etf:    2-year  train  / 3-month forward
  forex / futures: 1-year  train  / 2-month forward

Quarterly re-walk-forward required for all PRODUCTION strategies.
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .metrics import PerformanceMetrics, StrategyMetrics

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardFold:
    """A single walk-forward fold."""
    fold_id: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    train_metrics: StrategyMetrics
    test_metrics: StrategyMetrics
    n_trades: int


@dataclass
class WalkForwardResult:
    """Aggregate walk-forward results."""
    folds: List[WalkForwardFold]
    aggregate_metrics: StrategyMetrics
    oos_sharpe: float           # Out-of-sample Sharpe
    oos_return: float
    is_sharpe: float            # In-sample Sharpe
    sharpe_decay: float         # How much Sharpe decays OOS
    consistency: float          # % of folds with positive OOS return
    avg_oos_sharpe: float
    total_oos_trades: int


ASSET_CLASS_WINDOWS: Dict[str, Dict[str, int]] = {
    # (train_days, test_days) per TESTING_PROTOCOL v4.0 Section Layer 3
    "crypto":   {"train_days": 126, "test_days": 30},   # 6-month train, 6-week forward
    "equity":   {"train_days": 504, "test_days": 63},   # 2-year train, 3-month forward
    "etf":      {"train_days": 504, "test_days": 63},   # same as equity
    "forex":    {"train_days": 252, "test_days": 42},   # 1-year train, 2-month forward
    "futures":  {"train_days": 252, "test_days": 42},   # same as forex
}


class WalkForwardValidator:
    """
    Walk-forward optimization and validation.

    Splits data into rolling train/test windows.
    Trains strategy on each window, tests on next period.
    Aggregates results across all folds.

    This is the "truth machine" — if it works here, it's real.

    Asset-class-specific window defaults (TESTING_PROTOCOL v4.0 Layer 3):
      crypto:          train=126d (~6 months),  test=30d  (~6 weeks)
      equity / etf:    train=504d (~2 years),   test=63d  (~3 months)
      forex / futures: train=252d (~1 year),    test=42d  (~2 months)

    Explicit train_days / test_days always take precedence over asset_class.
    """

    def __init__(
        self,
        train_days: Optional[int] = None,
        test_days: Optional[int] = None,
        step_days: int = 63,      # ~3 months roll
        min_trades: int = 10,
        asset_class: str = "crypto",   # crypto | equity | etf | forex | futures
    ):
        from .. import config

        # Resolve window sizes: explicit args beat asset_class lookup, which beats
        # the legacy hard-coded defaults (756 / 126) kept here only as last resort.
        _defaults = ASSET_CLASS_WINDOWS.get(asset_class.lower(), ASSET_CLASS_WINDOWS["crypto"])
        self.asset_class = asset_class.lower()
        self.train_days = train_days if train_days is not None else _defaults["train_days"]
        self.test_days  = test_days  if test_days  is not None else _defaults["test_days"]
        self.step_days = step_days
        self.min_trades = min_trades

    def generate_folds(self, dates: pd.DatetimeIndex) -> List[Tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
        """Generate train/test fold date ranges."""
        folds = []
        total_needed = self.train_days + self.test_days
        n = len(dates)

        if n < total_needed:
            logger.warning(f"Insufficient data: {n} days, need {total_needed}")
            return folds

        start = 0
        while start + total_needed <= n:
            train_idx = dates[start:start + self.train_days]
            test_idx = dates[start + self.train_days:start + self.train_days + self.test_days]

            if len(test_idx) > 0:
                folds.append((train_idx, test_idx))

            start += self.step_days

        logger.info(f"Generated {len(folds)} walk-forward folds")
        return folds

    def validate(
        self,
        strategy_fn: Callable,
        features: pd.DataFrame,
        prices: pd.DataFrame,
        benchmark: Optional[pd.Series] = None,
    ) -> WalkForwardResult:
        """
        Run walk-forward validation.
        
        Args:
            strategy_fn: Callable that takes (train_features, test_features, train_prices, test_prices)
                        and returns test_returns Series
            features: Full feature matrix
            prices: Full price data
            benchmark: Benchmark returns
            
        Returns:
            WalkForwardResult with fold-by-fold and aggregate metrics
        """
        dates = prices.index
        folds_dates = self.generate_folds(dates)

        if not folds_dates:
            return WalkForwardResult(
                folds=[], aggregate_metrics=StrategyMetrics(),
                oos_sharpe=0, oos_return=0, is_sharpe=0,
                sharpe_decay=0, consistency=0, avg_oos_sharpe=0, total_oos_trades=0,
            )

        fold_results = []
        all_oos_returns = []
        is_sharpes = []
        oos_sharpes = []

        for i, (train_dates, test_dates) in enumerate(folds_dates):
            try:
                # Split data
                train_features = features.loc[features.index.isin(train_dates) | 
                                              (isinstance(features.index, pd.MultiIndex) and 
                                               features.index.get_level_values(0).isin(train_dates))]
                test_features = features.loc[features.index.isin(test_dates) |
                                             (isinstance(features.index, pd.MultiIndex) and 
                                              features.index.get_level_values(0).isin(test_dates))]
                train_prices = prices.loc[train_dates]
                test_prices = prices.loc[test_dates]

                # Run strategy
                test_returns = strategy_fn(train_features, test_features, train_prices, test_prices)

                if test_returns is None or len(test_returns) < 5:
                    continue

                # Compute metrics
                bench_test = benchmark.loc[test_dates] if benchmark is not None else None
                test_metrics = PerformanceMetrics.compute_all(test_returns, bench_test)

                # In-sample metrics (quick estimate)
                train_returns = prices.loc[train_dates].pct_change().mean(axis=1).dropna()
                train_metrics = PerformanceMetrics.compute_all(train_returns)

                fold = WalkForwardFold(
                    fold_id=i,
                    train_start=train_dates[0],
                    train_end=train_dates[-1],
                    test_start=test_dates[0],
                    test_end=test_dates[-1],
                    train_metrics=train_metrics,
                    test_metrics=test_metrics,
                    n_trades=0,
                )
                fold_results.append(fold)
                all_oos_returns.append(test_returns)
                is_sharpes.append(train_metrics.sharpe_ratio)
                oos_sharpes.append(test_metrics.sharpe_ratio)

            except Exception as e:
                logger.warning(f"Fold {i} failed: {e}")
                continue

        if not fold_results:
            return WalkForwardResult(
                folds=[], aggregate_metrics=StrategyMetrics(),
                oos_sharpe=0, oos_return=0, is_sharpe=0,
                sharpe_decay=0, consistency=0, avg_oos_sharpe=0, total_oos_trades=0,
            )

        # Aggregate OOS returns
        combined_oos = pd.concat(all_oos_returns)
        aggregate = PerformanceMetrics.compute_all(combined_oos, benchmark)

        avg_is = np.mean(is_sharpes) if is_sharpes else 0
        avg_oos = np.mean(oos_sharpes) if oos_sharpes else 0
        decay = 1 - (avg_oos / avg_is) if avg_is != 0 else 1

        consistency = sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) if oos_sharpes else 0

        return WalkForwardResult(
            folds=fold_results,
            aggregate_metrics=aggregate,
            oos_sharpe=aggregate.sharpe_ratio,
            oos_return=aggregate.total_return,
            is_sharpe=avg_is,
            sharpe_decay=decay,
            consistency=consistency,
            avg_oos_sharpe=avg_oos,
            total_oos_trades=sum(f.n_trades for f in fold_results),
        )


# ---------------------------------------------------------------------------
# Asset-specific window configs (human-readable, per TESTING_PROTOCOL Layer 3)
# ---------------------------------------------------------------------------

WINDOWS: Dict[str, Dict[str, int]] = {
    "crypto": {"train_months": 6, "forward_weeks": 6},
    "equity": {"train_months": 24, "forward_months": 3},
    "forex":  {"train_months": 12, "forward_months": 2},
}


def _months_delta(dt: datetime, months: int) -> datetime:
    """Add *months* calendar months to *dt*."""
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, 28)  # safe across all months
    return dt.replace(year=year, month=month, day=day)


def _window_end(start: datetime, cfg: Dict[str, int]) -> datetime:
    """Compute window end from a config dict that has either forward_weeks or forward_months."""
    if "forward_weeks" in cfg:
        return start + timedelta(weeks=cfg["forward_weeks"])
    return _months_delta(start, cfg["forward_months"])


def _train_end(start: datetime, cfg: Dict[str, int]) -> datetime:
    """Compute train window end from config."""
    return _months_delta(start, cfg["train_months"])


# ---------------------------------------------------------------------------
# Trade-level metrics helpers
# ---------------------------------------------------------------------------

def _compute_trade_metrics(pnls: List[float]) -> Dict[str, float]:
    """
    Compute Sharpe, win-rate, profit-factor from a list of trade PnL percentages.

    Returns dict with keys: sharpe, win_rate, profit_factor, mean_pnl, n_trades.
    """
    if not pnls:
        return {"sharpe": 0.0, "win_rate": 0.0, "profit_factor": 0.0,
                "mean_pnl": 0.0, "n_trades": 0}

    arr = np.array(pnls, dtype=float)
    n = len(arr)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if n > 1 else 1e-9

    # Annualised Sharpe (assume ~250 trades/year as rough scaling)
    sharpe = (mean / std) * math.sqrt(min(n, 250)) if std > 1e-12 else 0.0

    wins = arr[arr > 0]
    losses = arr[arr < 0]
    win_rate = float(len(wins) / n) if n else 0.0

    gross_profit = float(np.sum(wins)) if len(wins) else 0.0
    gross_loss = float(abs(np.sum(losses))) if len(losses) else 1e-9
    profit_factor = gross_profit / gross_loss if gross_loss > 1e-12 else (
        float("inf") if gross_profit > 0 else 0.0
    )

    return {
        "sharpe": round(sharpe, 4),
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "mean_pnl": round(mean, 6),
        "n_trades": n,
    }


# ---------------------------------------------------------------------------
# Single-window result
# ---------------------------------------------------------------------------

@dataclass
class TradeWindowResult:
    """Result for one rolling walk-forward window."""
    window_id: int
    train_start: str
    train_end: str
    forward_start: str
    forward_end: str
    is_metrics: Dict[str, float] = field(default_factory=dict)
    oos_metrics: Dict[str, float] = field(default_factory=dict)
    sharpe_within_10pct: bool = False
    passed: bool = False
    note: str = ""


# ---------------------------------------------------------------------------
# Aggregate result
# ---------------------------------------------------------------------------

@dataclass
class TradeWalkForwardReport:
    """Full walk-forward report across all windows."""
    strategy_name: str
    asset_class: str
    windows: List[TradeWindowResult] = field(default_factory=list)
    overall_passed: bool = False
    avg_is_sharpe: float = 0.0
    avg_oos_sharpe: float = 0.0
    avg_sharpe_decay_pct: float = 0.0
    pct_windows_passed: float = 0.0
    quarterly_revalidation_due: bool = False
    last_walk_forward_date: Optional[str] = None
    summary: str = ""


# ---------------------------------------------------------------------------
# Trade-level Walk-Forward Validator
# ---------------------------------------------------------------------------

class TradeWalkForwardValidator:
    """
    Walk-forward validation on trade-level data.

    Expects trades as list of dicts::

        {
            "entry_date": "2025-06-01" or datetime,
            "exit_date":  "2025-06-05" or datetime,
            "pnl_pct":    2.35,          # percent return of trade
            "symbol":     "BTCUSDT",
            "asset_class": "crypto",     # crypto | equity | forex
        }

    Asset-specific rolling windows (TESTING_PROTOCOL Layer 3):
        crypto:  6-month train + 6-week forward
        equity:  2-year train  + 3-month forward
        forex:   1-year train  + 2-month forward

    OOS Sharpe must be within 10 % of IS Sharpe (Layer 2 requirement).
    Quarterly re-walk-forward is checked against *last_walk_forward_date*.
    """

    SHARPE_TOLERANCE = 0.10  # OOS Sharpe must be >= IS Sharpe * (1 - tolerance)
    MIN_TRADES_PER_WINDOW = 5  # need at least this many trades in each half
    QUARTERLY_DAYS = 90

    def __init__(
        self,
        asset_class: str = "crypto",
        sharpe_tolerance: float = 0.10,
        min_trades: int = 5,
        step_months: int = 1,
    ):
        ac = asset_class.lower()
        # Normalize etf -> equity, futures -> forex
        if ac in ("etf",):
            ac = "equity"
        if ac in ("futures",):
            ac = "forex"
        if ac not in WINDOWS:
            logger.warning("Unknown asset_class %r, defaulting to crypto", ac)
            ac = "crypto"

        self.asset_class = ac
        self.window_cfg = WINDOWS[ac]
        self.sharpe_tolerance = sharpe_tolerance
        self.min_trades = min_trades
        self.step_months = step_months  # how far to roll between windows

    # ------------------------------------------------------------------
    # Core: run walk-forward on a list of trade dicts
    # ------------------------------------------------------------------

    def validate(
        self,
        trades: List[Dict[str, Any]],
        strategy_name: str = "unknown",
        last_walk_forward_date: Optional[str] = None,
    ) -> TradeWalkForwardReport:
        """
        Run rolling walk-forward validation on trade-level data.

        Args:
            trades: list of trade dicts (entry_date, exit_date, pnl_pct, symbol, asset_class)
            strategy_name: label for reporting
            last_walk_forward_date: ISO date string of last walk-forward run (for quarterly check)

        Returns:
            TradeWalkForwardReport with per-window breakdown and overall pass/fail.
        """
        if not trades:
            return TradeWalkForwardReport(
                strategy_name=strategy_name,
                asset_class=self.asset_class,
                summary="No trades provided",
            )

        # Parse dates
        parsed = self._parse_trades(trades)
        if not parsed:
            return TradeWalkForwardReport(
                strategy_name=strategy_name,
                asset_class=self.asset_class,
                summary="Could not parse any trades",
            )

        # Sort by exit_date
        parsed.sort(key=lambda t: t["exit_dt"])

        earliest = parsed[0]["exit_dt"]
        latest = parsed[-1]["exit_dt"]

        cfg = self.window_cfg
        train_months = cfg["train_months"]

        # Generate rolling windows
        window_results: List[TradeWindowResult] = []
        win_id = 0
        cursor = earliest

        while True:
            train_start = cursor
            train_end = _train_end(train_start, cfg)
            fwd_start = train_end
            fwd_end = _window_end(fwd_start, cfg)

            # Stop if forward window exceeds data
            if fwd_end > latest + timedelta(days=1):
                break

            # Collect trades in each window (by exit_date)
            is_trades = [t for t in parsed if train_start <= t["exit_dt"] < train_end]
            oos_trades = [t for t in parsed if fwd_start <= t["exit_dt"] < fwd_end]

            is_pnls = [t["pnl_pct"] for t in is_trades]
            oos_pnls = [t["pnl_pct"] for t in oos_trades]

            is_metrics = _compute_trade_metrics(is_pnls)
            oos_metrics = _compute_trade_metrics(oos_pnls)

            # Check OOS Sharpe within 10% of IS Sharpe
            is_sharpe = is_metrics["sharpe"]
            oos_sharpe = oos_metrics["sharpe"]

            if is_sharpe > 0:
                sharpe_ok = oos_sharpe >= is_sharpe * (1 - self.sharpe_tolerance)
            elif is_sharpe < 0:
                # If IS Sharpe is negative, OOS just needs to be no worse
                sharpe_ok = oos_sharpe >= is_sharpe * (1 + self.sharpe_tolerance)
            else:
                sharpe_ok = oos_sharpe >= 0

            enough_trades = (is_metrics["n_trades"] >= self.min_trades and
                             oos_metrics["n_trades"] >= self.min_trades)

            passed = sharpe_ok and enough_trades and oos_sharpe > 0

            note_parts = []
            if not enough_trades:
                note_parts.append(
                    f"insufficient trades (IS={is_metrics['n_trades']}, "
                    f"OOS={oos_metrics['n_trades']}, min={self.min_trades})"
                )
            if not sharpe_ok:
                note_parts.append(
                    f"OOS Sharpe {oos_sharpe:.4f} not within 10% of IS Sharpe {is_sharpe:.4f}"
                )
            if oos_sharpe <= 0:
                note_parts.append(f"OOS Sharpe non-positive ({oos_sharpe:.4f})")

            wr = TradeWindowResult(
                window_id=win_id,
                train_start=train_start.strftime("%Y-%m-%d"),
                train_end=train_end.strftime("%Y-%m-%d"),
                forward_start=fwd_start.strftime("%Y-%m-%d"),
                forward_end=fwd_end.strftime("%Y-%m-%d"),
                is_metrics=is_metrics,
                oos_metrics=oos_metrics,
                sharpe_within_10pct=sharpe_ok,
                passed=passed,
                note="; ".join(note_parts) if note_parts else "PASS",
            )
            window_results.append(wr)
            win_id += 1

            # Roll forward
            cursor = _months_delta(cursor, self.step_months)

        # Aggregate
        if not window_results:
            return TradeWalkForwardReport(
                strategy_name=strategy_name,
                asset_class=self.asset_class,
                summary="Not enough data to form any walk-forward window",
            )

        n_passed = sum(1 for w in window_results if w.passed)
        pct_passed = n_passed / len(window_results)

        is_sharpes = [w.is_metrics.get("sharpe", 0) for w in window_results]
        oos_sharpes = [w.oos_metrics.get("sharpe", 0) for w in window_results]
        avg_is = float(np.mean(is_sharpes)) if is_sharpes else 0.0
        avg_oos = float(np.mean(oos_sharpes)) if oos_sharpes else 0.0
        avg_decay = (1 - avg_oos / avg_is) * 100 if abs(avg_is) > 1e-9 else 0.0

        # Quarterly re-validation check
        quarterly_due = self._check_quarterly_due(last_walk_forward_date)

        # Overall pass: >=50% of windows pass and avg OOS Sharpe positive
        overall = pct_passed >= 0.5 and avg_oos > 0

        summary_parts = [
            f"{len(window_results)} windows, {n_passed} passed ({pct_passed:.0%})",
            f"avg IS Sharpe={avg_is:.3f}, avg OOS Sharpe={avg_oos:.3f}, decay={avg_decay:.1f}%",
        ]
        if quarterly_due:
            summary_parts.append("QUARTERLY RE-VALIDATION OVERDUE")
        if not overall:
            summary_parts.append("OVERALL: FAIL")
        else:
            summary_parts.append("OVERALL: PASS")

        return TradeWalkForwardReport(
            strategy_name=strategy_name,
            asset_class=self.asset_class,
            windows=window_results,
            overall_passed=overall,
            avg_is_sharpe=round(avg_is, 4),
            avg_oos_sharpe=round(avg_oos, 4),
            avg_sharpe_decay_pct=round(avg_decay, 2),
            pct_windows_passed=round(pct_passed, 4),
            quarterly_revalidation_due=quarterly_due,
            last_walk_forward_date=last_walk_forward_date,
            summary=" | ".join(summary_parts),
        )

    # ------------------------------------------------------------------
    # Quarterly re-validation check
    # ------------------------------------------------------------------

    def _check_quarterly_due(self, last_wf_date: Optional[str]) -> bool:
        """Return True if >90 days since last walk-forward validation."""
        if last_wf_date is None:
            return True  # never validated => overdue
        try:
            last_dt = datetime.fromisoformat(last_wf_date)
        except (ValueError, TypeError):
            return True
        return (datetime.utcnow() - last_dt).days > self.QUARTERLY_DAYS

    # ------------------------------------------------------------------
    # Trade parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_trades(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalise trade dicts: ensure exit_dt is a datetime."""
        out = []
        for t in trades:
            try:
                exit_raw = t.get("exit_date") or t.get("exit_dt")
                entry_raw = t.get("entry_date") or t.get("entry_dt")
                pnl = float(t.get("pnl_pct", 0))

                if isinstance(exit_raw, str):
                    exit_dt = datetime.fromisoformat(exit_raw)
                elif isinstance(exit_raw, datetime):
                    exit_dt = exit_raw
                elif isinstance(exit_raw, pd.Timestamp):
                    exit_dt = exit_raw.to_pydatetime()
                else:
                    continue

                if isinstance(entry_raw, str):
                    entry_dt = datetime.fromisoformat(entry_raw)
                elif isinstance(entry_raw, datetime):
                    entry_dt = entry_raw
                elif isinstance(entry_raw, pd.Timestamp):
                    entry_dt = entry_raw.to_pydatetime()
                else:
                    entry_dt = exit_dt  # fallback

                out.append({
                    "entry_dt": entry_dt,
                    "exit_dt": exit_dt,
                    "pnl_pct": pnl,
                    "symbol": t.get("symbol", ""),
                    "asset_class": t.get("asset_class", "crypto"),
                })
            except Exception:
                continue
        return out
