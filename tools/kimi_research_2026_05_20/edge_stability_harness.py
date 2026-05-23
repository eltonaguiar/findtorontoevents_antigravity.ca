#!/usr/bin/env python3
"""
================================================================================
Edge Stability Harness — Regime Detection, Decay Alerts & Auto-Pause
================================================================================
Monitors strategy performance over time, detects when alpha decays,
identifies regime changes, and automatically pauses / resumes strategies.

Key Capabilities
----------------
* Rolling Sharpe (30 d, 90 d) with Z-score monitoring
* Volatility-regime detection (Markov-switching proxy via HMM-free clustering)
* Correlation-regime detection (average pairwise correlation shift)
* Strategy-decay alerts (Sharpe falls below threshold for N consecutive windows)
* Performance attribution — which factors are driving decay
* Auto-pause  — deactivate strategies failing stability tests
* Auto-recover — re-enable strategies that show sustained recovery

Integration
-----------
    from edge_stability_harness import EdgeStabilityHarness
    harness = EdgeStabilityHarness(db_path="./alpha_engine.db")
    alerts = harness.evaluate_all_strategies()
    harness.apply_auto_pauses(dry_run=False)

Author: Alpha Engine Team
Date: 2026-05-20
================================================================================
"""
from __future__ import annotations

import json
import logging
import sqlite3
import warnings
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans

logger = logging.getLogger("edge_stability_harness")


def _setup_logging(level: int = logging.INFO) -> None:
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(level)


_setup_logging()
warnings.filterwarnings("ignore", category=RuntimeWarning)

__version__ = "2.0.0"
__date__ = "2026-05-20"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RISK_FREE_RATE: float = 0.045 / 252  # 4.5% annual -> daily
SHARPE_DECAY_THRESHOLD: float = 0.5   # trigger alert if 30d Sharpe < 0.5
SHARPE_PAUSE_THRESHOLD: float = 0.0   # auto-pause if below 0
RECOVERY_THRESHOLD: float = 0.8       # re-enable if Sharpe > 0.8 sustained
CONSECUTIVE_WINDOWS_ALERT: int = 3    # alert after 3 bad windows
CONSECUTIVE_WINDOWS_PAUSE: int = 5    # pause after 5 bad windows
CONSECUTIVE_WINDOWS_RECOVER: int = 3  # recover after 3 good windows

VOLATILITY_LOOKBACK: int = 30
CORRELATION_LOOKBACK: int = 60
REGIME_CHANGE_ZSCORE: float = 2.0

DB_PATH: str = "./alpha_engine.db"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class RegimeState(Enum):
    LOW_VOL = "low_volatility"
    HIGH_VOL = "high_volatility"
    NORMAL = "normal"
    STRESS = "stress"
    UNKNOWN = "unknown"


class AlertLevel(Enum):
    GREEN = "green"      # healthy
    YELLOW = "yellow"    # caution
    ORANGE = "orange"    # decay detected
    RED = "red"          # pause triggered
    RECOVERING = "recovering"  # coming back


class Action(Enum):
    NONE = "none"
    PAUSE = "pause"
    RESUME = "resume"
    INVESTIGATE = "investigate"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class SharpePoint:
    """Single Sharpe observation for a strategy."""
    strategy_id: int
    strategy_name: str
    computed_at: datetime
    sharpe_30d: float
    sharpe_90d: float
    total_return_30d: float
    volatility_30d: float
    n_trades_30d: int


@dataclass
class RegimeSnapshot:
    """Market regime at a point in time."""
    snapshot_at: datetime
    regime: RegimeState
    avg_correlation: float
    avg_volatility: float
    correlation_zscore: float
    volatility_zscore: float
    description: str = ""


@dataclass
class DecayAlert:
    """Alert emitted when a strategy shows decay."""
    strategy_id: int
    strategy_name: str
    level: AlertLevel
    message: str
    current_sharpe_30d: float
    current_sharpe_90d: float
    consecutive_bad_windows: int
    consecutive_good_windows: int
    recommended_action: Action
    triggered_at: datetime = field(default_factory=lambda: datetime.utcnow())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "level": self.level.value,
            "message": self.message,
            "current_sharpe_30d": round(self.current_sharpe_30d, 4),
            "current_sharpe_90d": round(self.current_sharpe_90d, 4),
            "consecutive_bad_windows": self.consecutive_bad_windows,
            "consecutive_good_windows": self.consecutive_good_windows,
            "recommended_action": self.recommended_action.value,
            "triggered_at": self.triggered_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class StabilityReport:
    """Full report from a stability evaluation pass."""
    run_at: datetime
    strategies_evaluated: int
    active_strategies: int
    paused_strategies: int
    alerts: List[DecayAlert] = field(default_factory=list)
    regime: Optional[RegimeSnapshot] = None
    actions_taken: Dict[str, int] = field(default_factory=dict)
    sharpe_distribution: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_at": self.run_at.isoformat(),
            "strategies_evaluated": self.strategies_evaluated,
            "active_strategies": self.active_strategies,
            "paused_strategies": self.paused_strategies,
            "alert_count": len(self.alerts),
            "alerts": [a.to_dict() for a in self.alerts],
            "regime": asdict(self.regime) if self.regime else None,
            "actions_taken": self.actions_taken,
            "sharpe_distribution": self.sharpe_distribution,
        }


# ---------------------------------------------------------------------------
# Sharpe Calculator
# ---------------------------------------------------------------------------
class SharpeCalculator:
    """Compute rolling Sharpe ratios from daily returns."""

    @staticmethod
    def from_returns(daily_returns: pd.Series, window: int = 30) -> float:
        """Annualised Sharpe for the last *window* days."""
        if len(daily_returns) < window // 2:
            return 0.0
        recent = daily_returns.iloc[-window:].dropna()
        if len(recent) < 10:
            return 0.0
        excess = recent - RISK_FREE_RATE
        std = excess.std(ddof=1)
        if std == 0 or not np.isfinite(std):
            return 0.0
        sharpe = (excess.mean() / std) * np.sqrt(252)
        return float(np.clip(sharpe, -10, 10))

    @staticmethod
    def rolling_sharpe(
        daily_returns: pd.Series, window: int = 30
    ) -> pd.Series:
        """Full rolling Sharpe series."""
        excess = daily_returns - RISK_FREE_RATE
        roll_mean = excess.rolling(window=window, min_periods=window // 2).mean()
        roll_std = excess.rolling(window=window, min_periods=window // 2).std(ddof=1)
        sharpe = (roll_mean / roll_std) * np.sqrt(252)
        return sharpe.replace([np.inf, -np.inf], np.nan).fillna(0.0)


# ---------------------------------------------------------------------------
# Regime Detector
# ---------------------------------------------------------------------------
class RegimeDetector:
    """Detect volatility and correlation regime changes."""

    def __init__(
        self,
        vol_lookback: int = VOLATILITY_LOOKBACK,
        corr_lookback: int = CORRELATION_LOOKBACK,
        z_threshold: float = REGIME_CHANGE_ZSCORE,
    ) -> None:
        self.vol_lookback = vol_lookback
        self.corr_lookback = corr_lookback
        self.z_threshold = z_threshold
        self._vol_history: List[float] = []
        self._corr_history: List[float] = []

    def update(self, returns_matrix: pd.DataFrame) -> RegimeSnapshot:
        """
        *returns_matrix*: columns = strategies, index = dates, values = daily returns
        """
        now = datetime.utcnow()
        if returns_matrix.empty or returns_matrix.shape[1] < 2:
            return RegimeSnapshot(
                snapshot_at=now, regime=RegimeState.UNKNOWN,
                avg_correlation=0.0, avg_volatility=0.0,
                correlation_zscore=0.0, volatility_zscore=0.0,
                description="Insufficient data",
            )

        # rolling volatility (mean across strategies)
        vols = returns_matrix.iloc[-self.vol_lookback:].std(ddof=1)
        avg_vol = float(vols.mean())
        self._vol_history.append(avg_vol)
        if len(self._vol_history) > 252:
            self._vol_history = self._vol_history[-252:]

        # rolling correlation
        recent = returns_matrix.iloc[-self.corr_lookback:]
        corr_matrix = recent.corr()
        # upper-triangle mean
        mask = np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        corrs = corr_matrix.where(mask).stack().values
        avg_corr = float(np.nanmean(corrs)) if len(corrs) > 0 else 0.0
        self._corr_history.append(avg_corr)
        if len(self._corr_history) > 252:
            self._corr_history = self._corr_history[-252:]

        # z-scores
        vol_z = 0.0
        corr_z = 0.0
        if len(self._vol_history) > 30:
            vol_arr = np.array(self._vol_history)
            vol_mean, vol_std = vol_arr.mean(), vol_arr.std(ddof=1)
            if vol_std > 0:
                vol_z = (avg_vol - vol_mean) / vol_std
        if len(self._corr_history) > 30:
            corr_arr = np.array(self._corr_history)
            corr_mean, corr_std = corr_arr.mean(), corr_arr.std(ddof=1)
            if corr_std > 0:
                corr_z = (avg_corr - corr_mean) / corr_std

        # classify regime
        regime = RegimeState.NORMAL
        desc_parts: List[str] = []
        if vol_z > self.z_threshold:
            regime = RegimeState.HIGH_VOL
            desc_parts.append("High volatility regime")
        elif vol_z < -self.z_threshold:
            regime = RegimeState.LOW_VOL
            desc_parts.append("Low volatility regime")
        if corr_z > self.z_threshold:
            if regime == RegimeState.HIGH_VOL:
                regime = RegimeState.STRESS
                desc_parts.append("Stress regime (high vol + high corr)")
            else:
                desc_parts.append("Rising correlation regime")

        if not desc_parts:
            desc_parts.append("Normal regime")

        return RegimeSnapshot(
            snapshot_at=now,
            regime=regime,
            avg_correlation=round(avg_corr, 4),
            avg_volatility=round(avg_vol, 6),
            correlation_zscore=round(corr_z, 4),
            volatility_zscore=round(vol_z, 4),
            description="; ".join(desc_parts),
        )


# ---------------------------------------------------------------------------
# DB Interface
# ---------------------------------------------------------------------------
class StabilityDatabase:
    """Read/write strategy performance and control state."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def ensure_schema(self) -> None:
        """Create strategy_performance and strategy_control tables."""
        ddl_perf = """
            CREATE TABLE IF NOT EXISTS strategy_performance (
                perf_id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER NOT NULL,
                sharpe_30d REAL,
                sharpe_90d REAL,
                total_return REAL,
                max_drawdown REAL,
                n_trades INTEGER,
                win_rate REAL,
                computed_at TEXT NOT NULL
            )
        """
        ddl_control = """
            CREATE TABLE IF NOT EXISTS strategy_control (
                strategy_id INTEGER PRIMARY KEY,
                is_active INTEGER DEFAULT 1,
                consecutive_bad_windows INTEGER DEFAULT 0,
                consecutive_good_windows INTEGER DEFAULT 0,
                last_alert_level TEXT,
                paused_at TEXT,
                resumed_at TEXT,
                updated_at TEXT NOT NULL
            )
        """
        try:
            with self._conn() as conn:
                conn.execute(ddl_perf)
                conn.execute(ddl_control)
                conn.commit()
        except Exception as exc:
            logger.warning("Schema creation: %s", exc)

    def get_active_strategies(self) -> pd.DataFrame:
        """Return DataFrame of active strategies."""
        try:
            with self._conn() as conn:
                return pd.read_sql_query(
                    "SELECT strategy_id, strategy_name, category, asset_class FROM strategies WHERE is_active = 1",
                    conn,
                )
        except Exception as exc:
            logger.error("Failed to load strategies: %s", exc)
            return pd.DataFrame()

    def get_strategy_returns(self, strategy_id: int, lookback_days: int = 180) -> pd.Series:
        """Daily returns series for a strategy (synthetic from pick PnL)."""
        cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()
        try:
            with self._conn() as conn:
                df = pd.read_sql_query(
                    """SELECT
                        DATE(resolved_at) as trade_date,
                        AVG(pnl_pct) as daily_return
                    FROM picks
                    WHERE strategy_id = ?
                    AND resolved_at >= ?
                    AND status = 'resolved'
                    GROUP BY DATE(resolved_at)
                    ORDER BY trade_date""",
                    conn,
                    params=(strategy_id, cutoff),
                )
                if df.empty:
                    return pd.Series(dtype=float)
                df["trade_date"] = pd.to_datetime(df["trade_date"])
                df = df.set_index("trade_date")["daily_return"]
                # reindex to full business-day calendar, fill gaps with 0
                full_idx = pd.date_range(df.index.min(), df.index.max(), freq="B")
                return df.reindex(full_idx).fillna(0.0)
        except Exception as exc:
            logger.error("Failed to load returns for strategy %d: %s", strategy_id, exc)
            return pd.Series(dtype=float)

    def get_all_strategy_returns(self, lookback_days: int = 180) -> pd.DataFrame:
        """Returns matrix: columns=strategy_ids, index=dates."""
        cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()
        try:
            with self._conn() as conn:
                df = pd.read_sql_query(
                    """SELECT
                        strategy_id,
                        DATE(resolved_at) as trade_date,
                        AVG(pnl_pct) as daily_return
                    FROM picks
                    WHERE resolved_at >= ?
                    AND status = 'resolved'
                    GROUP BY strategy_id, DATE(resolved_at)
                    ORDER BY trade_date""",
                    conn,
                    params=(cutoff,),
                )
                if df.empty:
                    return pd.DataFrame()
                df["trade_date"] = pd.to_datetime(df["trade_date"])
                matrix = df.pivot(index="trade_date", columns="strategy_id", values="daily_return").fillna(0.0)
                return matrix
        except Exception as exc:
            logger.error("Failed to load returns matrix: %s", exc)
            return pd.DataFrame()

    def insert_performance(self, strategy_id: int, sharpe_30d: float, sharpe_90d: float,
                           total_return: float, max_dd: float, n_trades: int, win_rate: float) -> None:
        now = datetime.utcnow().isoformat()
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO strategy_performance
                    (strategy_id, sharpe_30d, sharpe_90d, total_return, max_drawdown, n_trades, win_rate, computed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (strategy_id, sharpe_30d, sharpe_90d, total_return, max_dd, n_trades, win_rate, now),
                )
                conn.commit()
        except Exception as exc:
            logger.error("Insert performance error: %s", exc)

    def get_control_state(self, strategy_id: int) -> Dict[str, Any]:
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT * FROM strategy_control WHERE strategy_id = ?", (strategy_id,)
                ).fetchone()
                if row:
                    return {
                        "strategy_id": row[0],
                        "is_active": bool(row[1]),
                        "consecutive_bad_windows": row[2] or 0,
                        "consecutive_good_windows": row[3] or 0,
                        "last_alert_level": row[4] or "green",
                        "paused_at": row[5],
                        "resumed_at": row[6],
                        "updated_at": row[7],
                    }
                else:
                    # create default
                    now = datetime.utcnow().isoformat()
                    conn.execute(
                        "INSERT OR IGNORE INTO strategy_control (strategy_id, updated_at) VALUES (?, ?)",
                        (strategy_id, now),
                    )
                    conn.commit()
                    return {
                        "strategy_id": strategy_id,
                        "is_active": True,
                        "consecutive_bad_windows": 0,
                        "consecutive_good_windows": 0,
                        "last_alert_level": "green",
                        "paused_at": None,
                        "resumed_at": None,
                        "updated_at": now,
                    }
        except Exception as exc:
            logger.error("Control state error: %s", exc)
            return {
                "strategy_id": strategy_id, "is_active": True,
                "consecutive_bad_windows": 0, "consecutive_good_windows": 0,
                "last_alert_level": "green", "paused_at": None,
                "resumed_at": None, "updated_at": datetime.utcnow().isoformat(),
            }

    def update_control_state(self, strategy_id: int, **kwargs) -> bool:
        now = datetime.utcnow().isoformat()
        fields = ["updated_at = ?"]
        values = [now]
        for key, val in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(val)
        values.append(strategy_id)
        sql = f"UPDATE strategy_control SET {', '.join(fields)} WHERE strategy_id = ?"
        try:
            with self._conn() as conn:
                conn.execute(sql, values)
                conn.commit()
                return True
        except Exception as exc:
            logger.error("Update control error: %s", exc)
            return False

    def set_strategy_active(self, strategy_id: int, active: bool) -> bool:
        try:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE strategies SET is_active = ? WHERE strategy_id = ?",
                    (1 if active else 0, strategy_id),
                )
                conn.commit()
                return True
        except Exception as exc:
            logger.error("Set active error: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Edge Stability Harness (main orchestrator)
# ---------------------------------------------------------------------------
class EdgeStabilityHarness:
    """Evaluate strategy health, detect decay, auto-pause / resume."""

    def __init__(
        self,
        db: Optional[StabilityDatabase] = None,
        sharpe_calc: Optional[SharpeCalculator] = None,
        regime_detector: Optional[RegimeDetector] = None,
    ) -> None:
        self.db = db or StabilityDatabase()
        self.sharpe_calc = sharpe_calc or SharpeCalculator()
        self.regime_detector = regime_detector or RegimeDetector()
        self.db.ensure_schema()
        self.alerts: List[DecayAlert] = []
        self.regime: Optional[RegimeSnapshot] = None

    # -- evaluation --------------------------------------------------------

    def evaluate_strategy(self, strategy_id: int, strategy_name: str = "") -> Optional[DecayAlert]:
        """Evaluate a single strategy and emit an alert if needed."""
        returns = self.db.get_strategy_returns(strategy_id)
        if len(returns) < 15:
            logger.debug("Strategy %d has only %d return days — skipping", strategy_id, len(returns))
            return None

        sharpe_30 = self.sharpe_calc.from_returns(returns, window=30)
        sharpe_90 = self.sharpe_calc.from_returns(returns, window=90)

        # drawdown
        cum = (1 + returns).cumprod()
        peak = cum.cummax()
        drawdown = (cum - peak) / peak
        max_dd = float(drawdown.min()) if len(drawdown) > 0 else 0.0

        # trade count proxy
        n_trades = int((returns != 0).sum())
        win_rate = float((returns > 0).mean()) if n_trades > 0 else 0.0

        # persist
        self.db.insert_performance(
            strategy_id, sharpe_30, sharpe_90,
            float(returns.sum()), max_dd, n_trades, win_rate,
        )

        # load control state
        ctrl = self.db.get_control_state(strategy_id)
        bad = ctrl["consecutive_bad_windows"]
        good = ctrl["consecutive_good_windows"]
        is_active = ctrl["is_active"]

        # update counters
        if sharpe_30 < SHARPE_DECAY_THRESHOLD:
            bad += 1
            good = 0
        elif sharpe_30 > RECOVERY_THRESHOLD:
            good += 1
            bad = 0
        else:
            # neutral zone — slowly decay counters
            bad = max(0, bad - 1)
            good = max(0, good - 1)

        self.db.update_control_state(
            strategy_id,
            consecutive_bad_windows=bad,
            consecutive_good_windows=good,
        )

        # determine alert level and action
        level = AlertLevel.GREEN
        action = Action.NONE
        message = f"Strategy healthy (30d Sharpe={sharpe_30:.2f})"

        # immediate extreme Sharpe alert (catastrophic failure detection)
        if sharpe_30 < -2.0 and is_active:
            level = AlertLevel.ORANGE
            action = Action.INVESTIGATE
            message = (
                f"Catastrophic Sharpe alert: 30d Sharpe={sharpe_30:.2f} — "
                f"immediate investigation required"
            )
        elif bad >= CONSECUTIVE_WINDOWS_PAUSE and is_active:
            level = AlertLevel.RED
            action = Action.PAUSE
            message = (
                f"Auto-pause triggered: 30d Sharpe={sharpe_30:.2f} "
                f"below threshold for {bad} consecutive windows"
            )
        elif bad >= CONSECUTIVE_WINDOWS_ALERT:
            level = AlertLevel.ORANGE
            action = Action.INVESTIGATE
            message = (
                f"Decay alert: 30d Sharpe={sharpe_30:.2f} "
                f"declining for {bad} consecutive windows"
            )
        elif not is_active and good >= CONSECUTIVE_WINDOWS_RECOVER:
            level = AlertLevel.RECOVERING
            action = Action.RESUME
            message = (
                f"Recovery detected: 30d Sharpe={sharpe_30:.2f} "
                f"improved for {good} consecutive windows"
            )
        elif not is_active:
            level = AlertLevel.YELLOW
            message = f"Strategy currently paused (30d Sharpe={sharpe_30:.2f})"

        alert = DecayAlert(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            level=level,
            message=message,
            current_sharpe_30d=sharpe_30,
            current_sharpe_90d=sharpe_90,
            consecutive_bad_windows=bad,
            consecutive_good_windows=good,
            recommended_action=action,
            metadata={
                "max_drawdown": round(max_dd, 4),
                "n_trades_30d": n_trades,
                "win_rate": round(win_rate, 4),
                "total_return_30d": round(float(returns.iloc[-30:].sum()), 6) if len(returns) >= 30 else round(float(returns.sum()), 6),
            },
        )

        # persist alert level
        self.db.update_control_state(strategy_id, last_alert_level=level.value)

        if level in (AlertLevel.ORANGE, AlertLevel.RED, AlertLevel.RECOVERING):
            logger.warning("[%s] Strategy %d: %s", level.value.upper(), strategy_id, message)
        else:
            logger.info("[%s] Strategy %d: %s", level.value.upper(), strategy_id, message)

        return alert

    def evaluate_all_strategies(self) -> StabilityReport:
        """Evaluate every active strategy and detect market regime."""
        self.alerts = []
        strategies = self.db.get_active_strategies()

        if strategies.empty:
            logger.warning("No strategies found in DB")
            return StabilityReport(
                run_at=datetime.utcnow(),
                strategies_evaluated=0,
                active_strategies=0,
                paused_strategies=0,
            )

        logger.info("Evaluating %d strategies...", len(strategies))

        for _, row in strategies.iterrows():
            sid = int(row["strategy_id"])
            sname = str(row.get("strategy_name", ""))
            alert = self.evaluate_strategy(sid, sname)
            if alert:
                self.alerts.append(alert)

        # market regime
        returns_matrix = self.db.get_all_strategy_returns(lookback_days=90)
        self.regime = self.regime_detector.update(returns_matrix)
        logger.info("Market regime: %s", self.regime.description)

        # paused count
        try:
            with self.db._conn() as conn:
                paused_count = conn.execute(
                    "SELECT COUNT(*) FROM strategies WHERE is_active = 0"
                ).fetchone()[0]
        except Exception:
            paused_count = 0

        # sharpe distribution
        sharpe_values = [a.current_sharpe_30d for a in self.alerts]
        distribution = {}
        if sharpe_values:
            distribution = {
                "p10": round(float(np.percentile(sharpe_values, 10)), 3),
                "p25": round(float(np.percentile(sharpe_values, 25)), 3),
                "p50": round(float(np.percentile(sharpe_values, 50)), 3),
                "p75": round(float(np.percentile(sharpe_values, 75)), 3),
                "p90": round(float(np.percentile(sharpe_values, 90)), 3),
                "mean": round(float(np.mean(sharpe_values)), 3),
                "std": round(float(np.std(sharpe_values, ddof=1)), 3),
            }

        return StabilityReport(
            run_at=datetime.utcnow(),
            strategies_evaluated=len(strategies),
            active_strategies=len(strategies) - paused_count,
            paused_strategies=paused_count,
            alerts=self.alerts,
            regime=self.regime,
            sharpe_distribution=distribution,
        )

    # -- auto-pause / resume -----------------------------------------------

    def apply_auto_pauses(self, dry_run: bool = True) -> Dict[str, int]:
        """Execute recommended pause/resume actions."""
        actions: Dict[str, int] = {"paused": 0, "resumed": 0, "investigated": 0, "none": 0}

        for alert in self.alerts:
            sid = alert.strategy_id
            action = alert.recommended_action

            if action == Action.PAUSE:
                if dry_run:
                    logger.info("[DRY-RUN] Would pause strategy %d", sid)
                else:
                    ok = self.db.set_strategy_active(sid, False)
                    if ok:
                        self.db.update_control_state(
                            sid,
                            is_active=0,
                            paused_at=datetime.utcnow().isoformat(),
                        )
                        actions["paused"] += 1
                        logger.info("PAUSED strategy %d", sid)

            elif action == Action.RESUME:
                if dry_run:
                    logger.info("[DRY-RUN] Would resume strategy %d", sid)
                else:
                    ok = self.db.set_strategy_active(sid, True)
                    if ok:
                        self.db.update_control_state(
                            sid,
                            is_active=1,
                            resumed_at=datetime.utcnow().isoformat(),
                            consecutive_bad_windows=0,
                        )
                        actions["resumed"] += 1
                        logger.info("RESUMED strategy %d", sid)

            elif action == Action.INVESTIGATE:
                actions["investigated"] += 1

            else:
                actions["none"] += 1

        logger.info("Auto-pause complete: %s", actions)
        return actions

    # -- performance attribution -------------------------------------------

    def attribute_decay(self, strategy_id: int) -> Dict[str, float]:
        """Simple attribution: which factor contributed most to recent decay."""
        returns = self.db.get_strategy_returns(strategy_id, lookback_days=90)
        if len(returns) < 30:
            return {"error": 1.0}

        recent = returns.iloc[-30:]
        prior = returns.iloc[-60:-30] if len(returns) >= 60 else returns.iloc[:30]

        attribution = {
            "return_shift": float(recent.mean() - prior.mean()),
            "vol_shift": float(recent.std(ddof=1) - prior.std(ddof=1)),
            "win_rate_shift": float((recent > 0).mean() - (prior > 0).mean()),
            "skewness_shift": float(recent.skew() - prior.skew()),
            "kurtosis_shift": float(recent.kurtosis() - prior.kurtosis()),
            "max_dd_recent": float(((1 + recent).cumprod().cummax() - (1 + recent).cumprod()).max()),
        }

        # normalise to percentages of total shift magnitude
        abs_vals = {k: abs(v) for k, v in attribution.items()}
        total = sum(abs_vals.values())
        if total > 0:
            attribution = {k: round(v / total, 4) for k, v in attribution.items()}

        return attribution


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Edge Stability Harness")
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--auto-pause", action="store_true", help="Apply pause/resume")
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    db = StabilityDatabase(db_path=args.db_path)
    harness = EdgeStabilityHarness(db=db)
    report = harness.evaluate_all_strategies()

    actions = harness.apply_auto_pauses(dry_run=not args.auto_pause)
    report.actions_taken = actions

    print(json.dumps(report.to_dict(), indent=2))

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
