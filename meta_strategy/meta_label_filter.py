"""Meta-Labeling Filter — Lopez de Prado's secondary ML classifier.

Architecture:
    Base Strategy Signal (BUY) -> Meta-Label Classifier -> 0.85 probability -> EXECUTE
    Base Strategy Signal (BUY) -> Meta-Label Classifier -> 0.35 probability -> VETO

The meta-label classifier learns which base-strategy signals are likely to be
true positives vs false positives, dramatically improving precision without
sacrificing the base strategy's recall.

Reference: Lopez de Prado, "Advances in Financial Machine Learning" (2018), Ch. 3.
"""

import sqlite3
import json
import math
import statistics
import hashlib
import random
from pathlib import Path
from datetime import datetime, timezone

# Optional ML imports — graceful fallback to heuristic mode
try:
    import numpy as np
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    import joblib
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    np = None


# ---------------------------------------------------------------------------
# Triple Barrier Labeler
# ---------------------------------------------------------------------------

class TripleBarrierLabeler:
    """Labels historical trade signals using the triple-barrier method.

    Each signal is labeled based on which barrier was hit first:
      - Upper barrier (TP): price moves +tp_pct% -> label = 1 (true positive)
      - Lower barrier (SL): price moves -sl_pct% -> label = 0 (false positive)
      - Time barrier: max_hours pass without hitting either -> label = 0 (timeout)

    When historical pnl_pct is already available on the signal, we use that
    directly (>0 => 1, <=0 => 0) to avoid needing tick-level price data.
    """

    def __init__(self, tp_pct: float = 2.0, sl_pct: float = 1.5,
                 max_hours: int = 24):
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.max_hours = max_hours

    def label_signals(self, signals: list) -> list:
        """Add ``meta_label`` field to each signal dict.

        If the signal already carries ``pnl_pct`` we derive the label from
        that (positive pnl -> 1, else 0).  Otherwise all signals without
        outcome data are labeled 0 (conservative).
        """
        labeled = []
        for sig in signals:
            sig = dict(sig)  # don't mutate caller's data
            pnl = sig.get("pnl_pct")
            if pnl is not None:
                sig["meta_label"] = 1 if float(pnl) > 0 else 0
            else:
                # No outcome data — conservative label
                sig["meta_label"] = 0
            labeled.append(sig)
        return labeled


# ---------------------------------------------------------------------------
# Meta-Label Filter
# ---------------------------------------------------------------------------

class MetaLabelFilter:
    """Secondary ML classifier that sits on top of base strategy signals.

    Learns to VETO bad trades by predicting whether a given signal is likely
    to be a true positive (profitable) or false positive (losing).
    """

    MIN_SAMPLES = 30
    MIN_PER_CLASS = 5  # need at least 5 wins AND 5 losses

    def __init__(self, model_path: str = None):
        self.DB_PATH = Path(__file__).parent / "data" / "meta_strategy.db"
        self.MODEL_PATH = Path(model_path) if model_path else (
            Path(__file__).parent / "data" / "meta_label_model.joblib"
        )
        self.SIGNAL_DB_PATH = (
            Path(__file__).parent.parent / "signal_recorder" / "data" / "signal_log.db"
        )

        self.model = None
        self.mode = "heuristic"
        self._total_seen = 0
        self._vetoed = 0
        self._executed = 0

        # Ensure DB table exists
        self._init_db()

        # Try loading existing model
        self._load_model()

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _init_db(self):
        """Create the meta_label_predictions table if it doesn't exist."""
        try:
            self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.DB_PATH))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta_label_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    signal_id TEXT,
                    system_id TEXT,
                    symbol TEXT,
                    direction TEXT,
                    ml_probability REAL,
                    threshold REAL,
                    decision TEXT,
                    actual_outcome REAL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_mlp_system
                ON meta_label_predictions(system_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_mlp_symbol
                ON meta_label_predictions(symbol)
            """)
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _get_signal_db(self) -> sqlite3.Connection | None:
        """Open signal_log.db (read-only) or return None."""
        if not self.SIGNAL_DB_PATH.exists():
            return None
        try:
            conn = sqlite3.connect(str(self.SIGNAL_DB_PATH))
            conn.row_factory = sqlite3.Row
            return conn
        except Exception:
            return None

    def _load_model(self):
        """Load a previously trained model from disk."""
        if not HAS_SKLEARN:
            return
        if self.MODEL_PATH.exists():
            try:
                self.model = joblib.load(str(self.MODEL_PATH))
                self.mode = "ml"
            except Exception:
                self.model = None

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    def extract_features(self, signal: dict) -> dict:
        """Extract 24 features from a signal and its context.

        Feature groups:
          1-6:   System confidence, RSI, time cyclical (hour/dow)
          7-9:   System historical/recent WR, streak
          10-13: Combo agreement, symbol volatility, regime score, chattering
          14-16: Avg PnL, combo size, Fear & Greed bucket
          17-20: Funding rate, BTC dominance, ADX, ML mode active
          21-24: Portfolio drawdown, system age, day-of-month, combo rolling WR

        Returns a flat dict of numeric features suitable for sklearn.
        """
        features = {}

        # 1. System confidence
        features["system_confidence"] = float(signal.get("confidence", 0.5))

        # 2. RSI at signal time
        features["rsi_at_signal"] = float(signal.get("rsi", signal.get("rsi_at_signal", 50.0)))

        # 3-4. Hour of day (cyclical encoding)
        ts = signal.get("timestamp", "")
        hour = self._parse_hour(ts)
        features["hour_sin"] = math.sin(2 * math.pi * hour / 24)
        features["hour_cos"] = math.cos(2 * math.pi * hour / 24)

        # 5-6. Day of week (cyclical encoding)
        dow = self._parse_dow(ts)
        features["dow_sin"] = math.sin(2 * math.pi * dow / 7)
        features["dow_cos"] = math.cos(2 * math.pi * dow / 7)

        # 7. System historical win rate
        system_id = signal.get("system_id", "")
        hist = self._get_system_stats(system_id)
        features["system_historical_wr"] = hist.get("win_rate", 0.5)

        # 8. System recent win rate (last 20)
        features["system_recent_wr"] = hist.get("recent_wr", 0.5)

        # 9. System streak (positive = wins, negative = losses)
        features["system_streak"] = hist.get("streak", 0)

        # 10. Combo agreement %
        features["combo_agreement_pct"] = float(signal.get("combo_agreement_pct",
                                                            signal.get("agreement", 0.5)))

        # 11. Symbol volatility (rolling std of recent pnl)
        features["symbol_volatility"] = self._get_symbol_volatility(
            signal.get("symbol", "")
        )

        # 12. Regime score (-1 bear, 0 sideways, 1 bull)
        features["regime_score"] = float(signal.get("regime_score",
                                                     signal.get("regime", 0)))

        # 13. Signal count last hour (chattering detection)
        features["signal_count_last_hour"] = float(
            signal.get("signal_count_last_hour",
                        signal.get("recent_signal_count", 1))
        )

        # 14. Average historical PnL for this system
        features["avg_pnl_this_system"] = hist.get("avg_pnl", 0.0)

        # 15. Combo size
        features["combo_size"] = float(signal.get("combo_size",
                                                   signal.get("n_systems", 1)))

        # 16. Fear & Greed bucket (0-4)
        fg = signal.get("fear_greed", signal.get("fear_greed_index", 50))
        features["fear_greed_bucket"] = self._fg_bucket(fg)

        # 17. Funding rate at signal time (perp market structure)
        features["funding_rate"] = float(signal.get("funding_rate",
                                                     signal.get("funding_z", 0.0)))

        # 18. BTC dominance (altcoin rotation signal)
        features["btc_dominance"] = float(signal.get("btc_dominance", 55.0))

        # 19. ADX at signal time (trend strength)
        features["adx_at_signal"] = float(signal.get("adx", signal.get("adx_14", 25.0)))

        # 20. ML mode active (1=ML model, 0=heuristic fallback)
        features["ml_mode_active"] = float(signal.get("ml_mode", signal.get("mode", "heuristic")) != "heuristic")

        # 21. Portfolio current drawdown (risk awareness)
        features["portfolio_drawdown"] = float(signal.get("portfolio_drawdown", 0.0))

        # 22. System age in days (older systems more reliable)
        features["system_age_days"] = float(hist.get("age_days", 30))

        # 23. Day of month (calendar effects — FOMC, expiry)
        dom = self._parse_dom(ts)
        features["day_of_month_sin"] = math.sin(2 * math.pi * dom / 31)

        # 24. Rolling combo win rate
        features["combo_rolling_wr"] = float(signal.get("combo_rolling_wr",
                                                          signal.get("rolling_wr", 0.5)))

        return features

    @staticmethod
    def _parse_dom(ts: str) -> float:
        """Extract day of month from ISO timestamp, default 15."""
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return float(dt.day)
        except Exception:
            return 15.0

    @staticmethod
    def _parse_hour(ts: str) -> float:
        """Extract hour from ISO timestamp, default 12."""
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return float(dt.hour)
        except Exception:
            return 12.0

    @staticmethod
    def _parse_dow(ts: str) -> float:
        """Extract day-of-week (0=Mon) from ISO timestamp, default 3."""
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return float(dt.weekday())
        except Exception:
            return 3.0

    @staticmethod
    def _fg_bucket(value) -> float:
        """Map fear & greed index (0-100) to bucket 0-4."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return 2.0  # neutral
        if v <= 20:
            return 0.0  # extreme fear
        if v <= 40:
            return 1.0  # fear
        if v <= 60:
            return 2.0  # neutral
        if v <= 80:
            return 3.0  # greed
        return 4.0  # extreme greed

    def _get_system_stats(self, system_id: str) -> dict:
        """Query signal_log.db for system-level stats."""
        defaults = {"win_rate": 0.5, "recent_wr": 0.5, "streak": 0, "avg_pnl": 0.0}
        if not system_id:
            return defaults
        conn = self._get_signal_db()
        if conn is None:
            return defaults
        try:
            # All closed signals for this system
            rows = conn.execute("""
                SELECT pnl_pct FROM permutation_signals
                WHERE combo_id = ? AND status != 'OPEN' AND pnl_pct IS NOT NULL
                ORDER BY timestamp DESC
            """, (system_id,)).fetchall()
            if not rows:
                # Try the signal_log table pattern
                rows = conn.execute("""
                    SELECT pnl_pct FROM signal_log
                    WHERE system_id = ? AND pnl_pct IS NOT NULL
                    ORDER BY timestamp DESC
                """, (system_id,)).fetchall()
            if not rows:
                conn.close()
                return defaults

            pnls = [float(r[0]) for r in rows]
            wins = sum(1 for p in pnls if p > 0)
            total = len(pnls)
            wr = wins / total if total else 0.5

            recent = pnls[:20]
            recent_wins = sum(1 for p in recent if p > 0)
            recent_wr = recent_wins / len(recent) if recent else 0.5

            # Streak
            streak = 0
            if pnls:
                direction = 1 if pnls[0] > 0 else -1
                for p in pnls:
                    if (p > 0 and direction > 0) or (p <= 0 and direction < 0):
                        streak += direction
                    else:
                        break

            avg_pnl = statistics.mean(pnls) if pnls else 0.0

            conn.close()
            return {
                "win_rate": round(wr, 4),
                "recent_wr": round(recent_wr, 4),
                "streak": streak,
                "avg_pnl": round(avg_pnl, 4),
            }
        except Exception:
            conn.close()
            return defaults

    def _get_symbol_volatility(self, symbol: str) -> float:
        """Rolling std of recent pnl_pct for a symbol."""
        if not symbol:
            return 0.02
        conn = self._get_signal_db()
        if conn is None:
            return 0.02
        try:
            rows = conn.execute("""
                SELECT pnl_pct FROM permutation_signals
                WHERE symbol = ? AND pnl_pct IS NOT NULL
                ORDER BY timestamp DESC LIMIT 50
            """, (symbol,)).fetchall()
            if not rows or len(rows) < 3:
                rows = conn.execute("""
                    SELECT pnl_pct FROM signal_log
                    WHERE symbol = ? AND pnl_pct IS NOT NULL
                    ORDER BY timestamp DESC LIMIT 50
                """, (symbol,)).fetchall()
            conn.close()
            if not rows or len(rows) < 3:
                return 0.02
            pnls = [float(r[0]) for r in rows]
            return round(statistics.stdev(pnls), 6)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return 0.02

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self) -> dict:
        """Train the meta-label classifier on historical signal outcomes.

        1. Load signals with outcomes from signal_log.db
        2. Apply triple barrier labeling
        3. Extract features
        4. Train GradientBoostingClassifier
        5. 3-fold stratified CV
        6. If CV > 0.52: save model. Else: heuristic fallback.
        """
        signals = self._load_training_data()
        if not signals:
            return {"mode": "heuristic", "reason": "no training data",
                    "n_samples": 0}

        # Triple barrier labeling
        labeler = TripleBarrierLabeler()
        labeled = labeler.label_signals(signals)

        # Check class balance
        labels = [s["meta_label"] for s in labeled]
        n_pos = sum(labels)
        n_neg = len(labels) - n_pos

        if len(labeled) < self.MIN_SAMPLES:
            return {"mode": "heuristic",
                    "reason": f"insufficient samples ({len(labeled)} < {self.MIN_SAMPLES})",
                    "n_samples": len(labeled)}

        if n_pos < self.MIN_PER_CLASS or n_neg < self.MIN_PER_CLASS:
            return {"mode": "heuristic",
                    "reason": f"class imbalance (pos={n_pos}, neg={n_neg}, need {self.MIN_PER_CLASS} each)",
                    "n_samples": len(labeled)}

        if not HAS_SKLEARN:
            return {"mode": "heuristic", "reason": "sklearn not available",
                    "n_samples": len(labeled)}

        # Extract features
        feature_dicts = [self.extract_features(s) for s in labeled]
        feature_names = sorted(feature_dicts[0].keys())
        X = np.array([[fd[k] for k in feature_names] for fd in feature_dicts])
        y = np.array(labels)

        # Train
        clf = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=4,
            min_samples_leaf=5,
            learning_rate=0.08,
            random_state=42,
        )

        # 3-fold stratified CV
        n_folds = min(3, n_pos, n_neg)
        if n_folds < 2:
            n_folds = 2
        skf = StratifiedKFold(n_splits=n_folds, shuffle=False)
        cv_scores = cross_val_score(clf, X, y, cv=skf, scoring="accuracy")
        mean_cv = float(np.mean(cv_scores))

        if mean_cv <= 0.52:
            return {"mode": "heuristic",
                    "reason": f"poor CV accuracy ({mean_cv:.4f} <= 0.52)",
                    "n_samples": len(labeled), "cv_accuracy": round(mean_cv, 4)}

        # Full fit and save
        clf.fit(X, y)
        self.model = clf
        self.mode = "ml"

        self.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(clf, str(self.MODEL_PATH))

        # Feature importance
        importance = dict(zip(feature_names,
                              [round(float(v), 4) for v in clf.feature_importances_]))

        stats = {
            "mode": "ml",
            "cv_accuracy": round(mean_cv, 4),
            "cv_scores": [round(float(s), 4) for s in cv_scores],
            "n_samples": len(labeled),
            "n_positive": int(n_pos),
            "n_negative": int(n_neg),
            "feature_importance": importance,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }

        # Save stats
        stats_path = self.DB_PATH.parent / "meta_label_stats.json"
        try:
            with open(stats_path, "w") as f:
                json.dump(stats, f, indent=2)
        except Exception:
            pass

        return stats

    def _load_training_data(self) -> list:
        """Load signals with outcomes from signal_log.db and meta_strategy.db."""
        signals = []

        # Source 1: signal_recorder/data/signal_log.db
        conn = self._get_signal_db()
        if conn is not None:
            try:
                rows = conn.execute("""
                    SELECT * FROM signal_log
                    WHERE pnl_pct IS NOT NULL
                    ORDER BY timestamp DESC
                    LIMIT 5000
                """).fetchall()
                for r in rows:
                    signals.append(dict(r))
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        # Source 2: meta_strategy.db permutation_signals
        try:
            conn2 = sqlite3.connect(str(self.DB_PATH))
            conn2.row_factory = sqlite3.Row
            rows2 = conn2.execute("""
                SELECT * FROM permutation_signals
                WHERE status != 'OPEN' AND pnl_pct IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 5000
            """).fetchall()
            for r in rows2:
                d = dict(r)
                # Normalize field names
                if "combo_id" in d and "system_id" not in d:
                    d["system_id"] = d["combo_id"]
                signals.append(d)
            conn2.close()
        except Exception:
            pass

        return signals

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(self, signal: dict) -> float:
        """Predict probability that this signal is a true positive.

        Returns float in [0, 1].
        - ML mode: uses trained model's predict_proba
        - Heuristic mode: weighted score from key features
        """
        if self.model is not None and HAS_SKLEARN:
            try:
                features = self.extract_features(signal)
                feature_names = sorted(features.keys())
                X = np.array([[features[k] for k in feature_names]])
                proba = self.model.predict_proba(X)[0]
                # Index 1 = probability of class 1 (true positive)
                return float(proba[1]) if len(proba) > 1 else float(proba[0])
            except Exception:
                pass  # fall through to heuristic

        # Heuristic fallback
        return self._heuristic_score(signal)

    def _heuristic_score(self, signal: dict) -> float:
        """Simple weighted heuristic when no ML model is available.

        score = 0.4 * system_wr + 0.3 * (confidence > 0.6)
              + 0.2 * (combo_agreement > 0.5) + 0.1
        """
        features = self.extract_features(signal)

        wr = features.get("system_historical_wr", 0.5)
        conf = features.get("system_confidence", 0.5)
        agreement = features.get("combo_agreement_pct", 0.5)

        score = (
            0.4 * wr
            + 0.3 * (1.0 if conf > 0.6 else 0.0)
            + 0.2 * (1.0 if agreement > 0.5 else 0.0)
            + 0.1
        )
        return round(min(max(score, 0.0), 1.0), 4)

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    def should_execute(self, signal: dict,
                       threshold: float = 0.55) -> tuple:
        """Decide whether to execute or veto a signal.

        Returns (should_execute: bool, probability: float).
        Also logs the decision to meta_label_predictions.
        """
        prob = self.predict(signal)
        execute = prob >= threshold

        self._total_seen += 1
        if execute:
            self._executed += 1
        else:
            self._vetoed += 1

        # Log decision
        self._log_decision(signal, prob, threshold, execute)

        return (execute, prob)

    def _log_decision(self, signal: dict, prob: float,
                      threshold: float, execute: bool):
        """Persist decision to SQLite for later analysis."""
        try:
            conn = sqlite3.connect(str(self.DB_PATH))
            conn.execute("""
                INSERT INTO meta_label_predictions
                    (timestamp, signal_id, system_id, symbol, direction,
                     ml_probability, threshold, decision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                str(signal.get("signal_id", signal.get("id", ""))),
                signal.get("system_id", signal.get("combo_id", "")),
                signal.get("symbol", ""),
                signal.get("direction", signal.get("signal", "")),
                round(prob, 6),
                threshold,
                "EXECUTE" if execute else "VETO",
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def veto_stats(self) -> dict:
        """Return meta-label filter statistics."""
        # In-memory counts from this session
        stats = {
            "session_total_seen": self._total_seen,
            "session_vetoed": self._vetoed,
            "session_executed": self._executed,
            "session_veto_rate": round(
                self._vetoed / self._total_seen, 4
            ) if self._total_seen > 0 else 0.0,
            "mode": self.mode,
        }

        # Lifetime counts from DB
        try:
            conn = sqlite3.connect(str(self.DB_PATH))
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN decision = 'VETO' THEN 1 ELSE 0 END) as vetoed,
                    SUM(CASE WHEN decision = 'EXECUTE' THEN 1 ELSE 0 END) as executed
                FROM meta_label_predictions
            """).fetchone()
            conn.close()
            if row:
                total = row[0] or 0
                vetoed = row[1] or 0
                executed = row[2] or 0
                stats["lifetime_total_seen"] = total
                stats["lifetime_vetoed"] = vetoed
                stats["lifetime_executed"] = executed
                stats["lifetime_veto_rate"] = round(
                    vetoed / total, 4
                ) if total > 0 else 0.0
        except Exception:
            pass

        # Model stats if available
        stats_path = self.DB_PATH.parent / "meta_label_stats.json"
        if stats_path.exists():
            try:
                with open(stats_path) as f:
                    ml_stats = json.load(f)
                stats["ml_cv_accuracy"] = ml_stats.get("cv_accuracy")
                stats["ml_n_samples"] = ml_stats.get("n_samples")
                stats["ml_trained_at"] = ml_stats.get("trained_at")
            except Exception:
                pass

        return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    filt = MetaLabelFilter()
    result = filt.train()
    print(f"Meta-Label Filter: {result}")
    report = filt.veto_stats()
    print(f"Stats: {report}")
