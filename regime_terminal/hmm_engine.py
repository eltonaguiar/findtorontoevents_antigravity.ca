"""
HMM Regime Detection Engine — Core Gaussian Hidden Markov Model.

Uses hmmlearn's GaussianHMM to classify market data into 7 hidden regimes.
Features: log returns, volatility (range), volume change, 5d momentum, 20d momentum.

Each regime has its own multivariate Gaussian distribution. The model learns:
  1. The probability of being in each regime (stationary distribution)
  2. The transition matrix (probability of switching regimes)
  3. The emission parameters (mean/covariance of features per regime)

This solves the chicken-and-egg problem of our current ML systems:
  - Random Forest needs 50+ trade outcomes → but no trades are generating
  - HMM trains on 17,000+ price observations → always has data
"""

import json
import os
import pickle
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler

from . import config

warnings.filterwarnings("ignore", category=DeprecationWarning)


class RegimeDetector:
    """
    Gaussian HMM-based market regime detector.

    Trains on OHLCV data to identify 7 hidden market states using
    multivariate Gaussian distributions over 5 engineered features.
    """

    def __init__(self, n_regimes=None):
        self.n_regimes = n_regimes or config.HMM_N_REGIMES
        self.model = None
        self.scaler = StandardScaler()
        self.regime_labels = {}
        self.regime_stats = {}
        self.is_fitted = False
        self.feature_names = [
            "log_return", "volatility", "volume_change",
            "momentum_5d", "momentum_20d"
        ]

    # ── Feature Engineering ─────────────────────────────────────────────────

    def prepare_features(self, df):
        """
        Extract 5 features from OHLCV DataFrame for HMM training.

        Features (chosen for Gaussian distribution fit):
          1. log_return    — ln(Close_t / Close_{t-1}), approximately normal
          2. volatility    — (High - Low) / Close, captures intrabar range
          3. volume_change — pct change in volume, captures participation shifts
          4. momentum_5d   — 5-day return, short-term trend
          5. momentum_20d  — 20-day return, medium-term trend
        """
        features = pd.DataFrame(index=df.index)

        close = df["Close"].astype(float)
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        volume = df["Volume"].astype(float)

        # 1. Log returns (approximately Gaussian)
        features["log_return"] = np.log(close / close.shift(1))

        # 2. Normalized range (volatility proxy)
        features["volatility"] = (high - low) / close

        # 3. Volume change (participation shift)
        # Handle forex/instruments with zero volume — use price-derived proxy
        if (volume == 0).all() or volume.isna().all():
            # Use intraday range as volume proxy for forex
            features["volume_change"] = ((high - low) / close).pct_change()
        else:
            vol_safe = volume.replace(0, np.nan)
            features["volume_change"] = vol_safe.pct_change()

        # 4-5. Multi-period momentum
        features["momentum_5d"] = close.pct_change(5)
        features["momentum_20d"] = close.pct_change(20)

        # Drop NaN rows (first 20 bars)
        features = features.dropna()

        # Clip extreme outliers (>5 sigma) to prevent HMM divergence
        for col in features.columns:
            mean = features[col].mean()
            std = features[col].std()
            if std > 0:
                features[col] = features[col].clip(mean - 5 * std, mean + 5 * std)

        return features

    # ── Training ────────────────────────────────────────────────────────────

    def fit(self, df):
        """
        Train the HMM on OHLCV data.

        Args:
            df: DataFrame with columns [Open, High, Low, Close, Volume]
                Must have 100+ rows (ideally 365-730 days).

        Returns:
            self (for chaining)
        """
        features = self.prepare_features(df)

        if len(features) < 50:
            raise ValueError(f"Need at least 50 data points, got {len(features)}")

        # Standardize features (zero mean, unit variance)
        X = self.scaler.fit_transform(features.values)

        # Fit Gaussian HMM
        # Use multiple restarts to avoid local optima
        best_score = -np.inf
        best_model = None

        for seed in [42, 123, 456, 789, 1337]:
            try:
                model = GaussianHMM(
                    n_components=self.n_regimes,
                    covariance_type=config.HMM_COVARIANCE_TYPE,
                    n_iter=config.HMM_N_ITER,
                    tol=config.HMM_TOL,
                    random_state=seed,
                )
                model.fit(X)
                score = model.score(X)
                if score > best_score:
                    best_score = score
                    best_model = model
            except Exception:
                continue

        if best_model is None:
            raise RuntimeError("HMM training failed on all random seeds")

        self.model = best_model
        self._label_regimes(features)
        self.is_fitted = True
        self._training_points = len(features)
        self._log_likelihood = best_score

        return self

    def _label_regimes(self, features):
        """
        Assign human-readable labels to each hidden state based on
        the Gaussian mean of the log_return feature (first feature).

        States with highest mean return → "Strong Bull"
        States with lowest mean return  → "Crash"
        """
        # Get means in original (un-scaled) space
        means_scaled = self.model.means_
        # Inverse transform to original feature space
        means_original = self.scaler.inverse_transform(means_scaled)

        # Sort states by log_return mean (column 0)
        return_means = means_original[:, 0]
        sorted_indices = np.argsort(return_means)

        labels = config.REGIME_LABELS
        self.regime_labels = {}
        self.regime_stats = {}

        for rank, state_idx in enumerate(sorted_indices):
            label = labels[rank] if rank < len(labels) else f"State_{rank}"
            self.regime_labels[state_idx] = label

            # Store statistics for each regime
            cov_matrix = self.model.covars_[state_idx]
            if config.HMM_COVARIANCE_TYPE == "full":
                vol_diag = np.sqrt(np.diag(cov_matrix))
            else:
                vol_diag = np.sqrt(cov_matrix)

            self.regime_stats[label] = {
                "state_id": int(state_idx),
                "mean_return": float(means_original[state_idx, 0]),
                "mean_volatility": float(means_original[state_idx, 1]),
                "mean_volume_change": float(means_original[state_idx, 2]),
                "mean_momentum_5d": float(means_original[state_idx, 3]),
                "mean_momentum_20d": float(means_original[state_idx, 4]),
                "return_std": float(
                    self.scaler.inverse_transform(
                        vol_diag.reshape(1, -1)
                    )[0, 0]
                ) if len(vol_diag) > 0 else 0.0,
                "stationary_probability": float(
                    self._stationary_distribution()[state_idx]
                ),
            }

    def _stationary_distribution(self):
        """Compute the stationary (long-run) distribution from transition matrix."""
        T = self.model.transmat_
        n = T.shape[0]
        # Solve π = πT, sum(π) = 1
        # Equivalent to (T' - I)π = 0, with normalization
        A = np.vstack([T.T - np.eye(n), np.ones(n)])
        b = np.zeros(n + 1)
        b[-1] = 1.0
        try:
            pi = np.linalg.lstsq(A, b, rcond=None)[0]
            pi = np.maximum(pi, 0)  # Ensure non-negative
            pi /= pi.sum()
        except Exception:
            pi = np.ones(n) / n
        return pi

    # ── Prediction ──────────────────────────────────────────────────────────

    def predict(self, df):
        """
        Predict regime for each bar in the DataFrame.

        Returns:
            List of dicts with regime info for each bar (after warmup period).
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        features = self.prepare_features(df)
        X = self.scaler.transform(features.values)

        hidden_states = self.model.predict(X)
        posteriors = self.model.predict_proba(X)

        results = []
        for i in range(len(features)):
            state = hidden_states[i]
            label = self.regime_labels.get(state, f"State_{state}")
            confidence = float(posteriors[i, state])

            # All regime probabilities
            all_probs = {}
            for s, lbl in self.regime_labels.items():
                all_probs[lbl] = float(posteriors[i, s])

            results.append({
                "date": str(features.index[i]),
                "regime": label,
                "regime_id": int(state),
                "confidence": round(confidence, 4),
                "probabilities": all_probs,
            })

        return results

    def current_regime(self, df):
        """
        Get the current (latest bar) regime classification.

        Returns:
            Dict with regime, confidence, transition probabilities, and signal.
        """
        predictions = self.predict(df)
        if not predictions:
            return None

        current = predictions[-1]
        regime = current["regime"]
        conf = current["confidence"]

        # Check regime persistence (hysteresis)
        recent = predictions[-config.MIN_REGIME_BARS:]
        regime_stable = all(p["regime"] == regime for p in recent)

        # Determine trading signal
        leverage = config.LEVERAGE_MAP.get(regime, 0.0)
        if not regime_stable:
            signal = "WAIT"
            signal_reason = f"Regime '{regime}' not confirmed ({config.MIN_REGIME_BARS}-bar hysteresis)"
        elif leverage > 0:
            signal = "LONG"
            signal_reason = f"Bullish regime '{regime}' confirmed, leverage {leverage}x"
        elif leverage < 0:
            signal = "SHORT"
            signal_reason = f"Bearish regime '{regime}' confirmed, leverage {abs(leverage)}x"
        else:
            signal = "CASH"
            signal_reason = f"Neutral regime '{regime}', stay flat"

        # Transition probabilities from current state
        trans_probs = {}
        state_id = current["regime_id"]
        for s, lbl in self.regime_labels.items():
            trans_probs[lbl] = float(self.model.transmat_[state_id, s])

        # Most likely next regime
        next_state = np.argmax(self.model.transmat_[state_id])
        next_regime = self.regime_labels.get(next_state, "Unknown")

        return {
            "regime": regime,
            "confidence": conf,
            "regime_stable": regime_stable,
            "signal": signal,
            "signal_reason": signal_reason,
            "leverage": leverage if regime_stable else 0.0,
            "transition_probs": trans_probs,
            "most_likely_next": next_regime,
            "all_probabilities": current["probabilities"],
            "regime_stats": self.regime_stats.get(regime, {}),
            "training_points": getattr(self, "_training_points", 0),
            "log_likelihood": getattr(self, "_log_likelihood", 0),
        }

    # ── Regime History Analysis ─────────────────────────────────────────────

    def regime_history(self, df):
        """
        Analyze regime distribution and transitions over full history.
        Returns summary statistics useful for the dashboard.
        """
        predictions = self.predict(df)
        if not predictions:
            return {}

        regimes = [p["regime"] for p in predictions]
        confidences = [p["confidence"] for p in predictions]

        # Regime distribution
        from collections import Counter
        counts = Counter(regimes)
        total = len(regimes)

        distribution = {}
        for label in config.REGIME_LABELS:
            c = counts.get(label, 0)
            distribution[label] = {
                "count": c,
                "percentage": round(100.0 * c / total, 1) if total > 0 else 0,
            }

        # Average confidence
        avg_conf = np.mean(confidences)

        # Regime durations (average bars per regime stint)
        durations = []
        current_regime = regimes[0]
        current_len = 1
        for r in regimes[1:]:
            if r == current_regime:
                current_len += 1
            else:
                durations.append((current_regime, current_len))
                current_regime = r
                current_len = 1
        durations.append((current_regime, current_len))

        avg_duration = {}
        for label in config.REGIME_LABELS:
            durs = [d for r, d in durations if r == label]
            avg_duration[label] = round(np.mean(durs), 1) if durs else 0

        return {
            "total_bars": total,
            "distribution": distribution,
            "avg_confidence": round(float(avg_conf), 4),
            "avg_regime_duration": avg_duration,
            "transition_matrix": self.model.transmat_.tolist(),
            "regime_stats": self.regime_stats,
        }

    # ── Technical Confirmations ─────────────────────────────────────────────

    def get_confirmations(self, df):
        """
        Check 8 technical confirmation indicators for entry quality.
        Returns count of confirmations and details.
        """
        close = df["Close"].astype(float)
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        volume = df["Volume"].astype(float)

        confirmations = {}

        # 1. RSI alignment
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1] if len(rsi) > 0 else 50
        confirmations["rsi"] = 30 < rsi_val < 70  # Not overbought/oversold

        # 2. MACD direction
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9).mean()
        macd_hist = macd - macd_signal
        confirmations["macd"] = float(macd_hist.iloc[-1]) > 0

        # 3. EMA 9/21 cross
        ema9 = close.ewm(span=9).mean()
        ema21 = close.ewm(span=21).mean()
        confirmations["ema_cross"] = float(ema9.iloc[-1]) > float(ema21.iloc[-1])

        # 4. Volume above average
        vol_avg = volume.rolling(20).mean()
        confirmations["volume"] = float(volume.iloc[-1]) > float(vol_avg.iloc[-1]) * 1.0

        # 5. 5-day momentum positive
        mom5 = close.pct_change(5)
        confirmations["momentum"] = float(mom5.iloc[-1]) > 0

        # 6. Bollinger position (price above middle band)
        bb_mid = close.rolling(20).mean()
        confirmations["bb_position"] = float(close.iloc[-1]) > float(bb_mid.iloc[-1])

        # 7. ATR expansion (current ATR > 20d average ATR)
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        atr_avg = atr.rolling(20).mean()
        confirmations["atr_expansion"] = float(atr.iloc[-1]) > float(atr_avg.iloc[-1])

        # 8. Trend alignment (50 SMA > 200 SMA)
        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()
        if not np.isnan(sma50.iloc[-1]) and not np.isnan(sma200.iloc[-1]):
            confirmations["trend_align"] = float(sma50.iloc[-1]) > float(sma200.iloc[-1])
        else:
            confirmations["trend_align"] = False  # Insufficient data

        count = sum(1 for v in confirmations.values() if v)
        return {
            "count": count,
            "total": 8,
            "met_threshold": count >= config.MIN_CONFIRMATIONS,
            "details": {k: bool(v) for k, v in confirmations.items()},
            "rsi_value": round(float(rsi_val), 1),
        }

    # ── Persistence ─────────────────────────────────────────────────────────

    def save(self, path):
        """Save trained model to disk."""
        data = {
            "model": self.model,
            "scaler": self.scaler,
            "regime_labels": self.regime_labels,
            "regime_stats": self.regime_stats,
            "n_regimes": self.n_regimes,
            "is_fitted": self.is_fitted,
            "training_points": getattr(self, "_training_points", 0),
            "log_likelihood": getattr(self, "_log_likelihood", 0),
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def load(self, path):
        """Load pre-trained model from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.regime_labels = data["regime_labels"]
        self.regime_stats = data["regime_stats"]
        self.n_regimes = data["n_regimes"]
        self.is_fitted = data["is_fitted"]
        self._training_points = data.get("training_points", 0)
        self._log_likelihood = data.get("log_likelihood", 0)
        return self
