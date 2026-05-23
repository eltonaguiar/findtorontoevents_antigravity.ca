"""
Market Regime Detector -- HMM-Based Adaptive Model Selection
=============================================================
Detects 3 market regimes using Gaussian Hidden Markov Model:
  - Bull   (trending up, expanding)
  - Bear   (trending down, contracting/panic)
  - Sideways (range-bound, low conviction)

Outputs transition probability matrix, regime persistence
probabilities, and per-regime TP/SL + position-size recs.

Falls back to KMeans (4 clusters) if hmmlearn is unavailable.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone

from sklearn.preprocessing import StandardScaler
import joblib

from .config import REGIME_CONFIG, MODELS_DIR, DATA_DIR

# ---------- optional HMM import ----------
try:
    from hmmlearn.hmm import GaussianHMM
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False


class RegimeDetector:
    """
    Adaptive market regime detection.

    Primary:  GaussianHMM with 3 hidden states (Bull / Bear / Sideways).
    Fallback: KMeans with 4 clusters (original behaviour) when hmmlearn
              is not installed.

    Features (unchanged from v1):
      - 20-day return  (trend direction)
      - 20-day realised volatility  (calm vs wild)
      - RSI-14  (momentum state)
      - ADX-14  (trend strength)
    """

    BULL     = "bull"
    BEAR     = "bear"
    SIDEWAYS = "sideways"

    N_HMM_STATES = 3

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.use_hmm = HMM_AVAILABLE
        self.regime_labels = REGIME_CONFIG["labels"]
        self.n_regimes = self.N_HMM_STATES if self.use_hmm else REGIME_CONFIG["n_regimes"]
        self._state_label_map: Dict[int, str] = {}
        self._load_model()

    def _load_model(self):
        """Load saved regime model if it exists."""
        model_path = MODELS_DIR / "regime_detector.joblib"
        scaler_path = MODELS_DIR / "regime_scaler.joblib"
        map_path = MODELS_DIR / "regime_state_map.json"

        if model_path.exists() and scaler_path.exists():
            try:
                self.model = joblib.load(str(model_path))
                self.scaler = joblib.load(str(scaler_path))
                self.use_hmm = hasattr(self.model, "transmat_")
                if map_path.exists():
                    with open(map_path) as fh:
                        raw = json.load(fh)
                    self._state_label_map = {int(k): v for k, v in raw.items()}
                backend = "HMM" if self.use_hmm else "KMeans"
                print(f"[RegimeDetector] Loaded saved model ({backend})")
            except Exception as exc:
                print(f"[RegimeDetector] Failed to load model: {exc}")
                self.model = None

    def _save_model(self):
        """Persist trained model + scaler + state-label mapping."""
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, str(MODELS_DIR / "regime_detector.joblib"))
        joblib.dump(self.scaler, str(MODELS_DIR / "regime_scaler.joblib"))
        if self._state_label_map:
            with open(MODELS_DIR / "regime_state_map.json", "w") as fh:
                json.dump(self._state_label_map, fh)

    def _compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute regime classification features from OHLCV data.
        
        Returns DataFrame with columns: [return_20d, volatility_20d, rsi_14, adx_14]
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]
        
        features = pd.DataFrame(index=df.index)
        
        # 1. Trend: 20-day return
        features["return_20d"] = close.pct_change(20) * 100
        
        # 2. Volatility: 20-day realized vol (annualized)
        log_returns = np.log(close / close.shift(1))
        features["volatility_20d"] = log_returns.rolling(20).std() * np.sqrt(252) * 100
        
        # 3. RSI-14
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        features["rsi_14"] = 100 - (100 / (1 + rs))
        
        # 4. ADX-14
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=high.index)
        minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=high.index)
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr_14 = tr.rolling(14).mean()
        plus_di = 100 * plus_dm.ewm(span=14).mean() / (atr_14 + 1e-10)
        minus_di = 100 * minus_dm.ewm(span=14).mean() / (atr_14 + 1e-10)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        features["adx_14"] = dx.ewm(span=14).mean()
        
        return features.dropna()
    
    def train(self, btc_df: pd.DataFrame):
        """
        Train regime detector on BTC data (BTC drives overall market regime).

        Uses GaussianHMM when hmmlearn is available, else KMeans.
        Should be called with >= 1 year of daily BTC data.
        """
        features = self._compute_features(btc_df)

        if len(features) < 100:
            print("[RegimeDetector] Insufficient data for training")
            return

        X = features.values
        X_scaled = self.scaler.fit_transform(X)

        if self.use_hmm:
            self._train_hmm(X_scaled, features)
        else:
            self._train_kmeans(X_scaled, features)

        self._save_model()

    def _train_hmm(self, X_scaled: np.ndarray, features: pd.DataFrame):
        """Fit a 3-state GaussianHMM and assign semantic labels."""
        self.model = GaussianHMM(
            n_components=self.N_HMM_STATES,
            covariance_type="full",
            n_iter=200,
            random_state=42,
            verbose=False,
        )
        self.model.fit(X_scaled)

        hidden_states = self.model.predict(X_scaled)

        state_means = {}
        for s in range(self.N_HMM_STATES):
            mask = hidden_states == s
            if mask.sum() > 0:
                state_means[s] = features.iloc[np.where(mask)[0]].mean()
            else:
                state_means[s] = pd.Series(
                    {"return_20d": 0, "volatility_20d": 0, "rsi_14": 50, "adx_14": 20}
                )

        sorted_by_return = sorted(state_means.items(), key=lambda kv: kv[1]["return_20d"])
        self._state_label_map = {
            sorted_by_return[0][0]: self.BEAR,
            sorted_by_return[1][0]: self.SIDEWAYS,
            sorted_by_return[2][0]: self.BULL,
        }

        print(f"[RegimeDetector] HMM trained on {len(features)} samples  "
              f"(3 states, log-likelihood={self.model.score(X_scaled):.1f})")
        for s in range(self.N_HMM_STATES):
            label = self._state_label_map[s]
            count = (hidden_states == s).sum()
            pct = count / len(hidden_states) * 100
            m = state_means[s]
            print(f"  State {s} [{label:>8s}]: return={m['return_20d']:.1f}%, "
                  f"vol={m['volatility_20d']:.1f}%, "
                  f"rsi={m['rsi_14']:.0f}, adx={m['adx_14']:.0f} "
                  f"({count} samples, {pct:.0f}%)")

        self._print_transition_matrix()

    def _print_transition_matrix(self):
        """Pretty-print the HMM transition probability matrix."""
        if not self.use_hmm or self.model is None:
            return
        T = self.model.transmat_
        labels = [self._state_label_map.get(i, f"S{i}") for i in range(T.shape[0])]
        print("\n  Transition Matrix (row -> col):")
        header = "           " + "  ".join(f"{l:>8s}" for l in labels)
        print(header)
        for i, row in enumerate(T):
            vals = "  ".join(f"{v:8.3f}" for v in row)
            print(f"  {labels[i]:>8s}  {vals}")
        print()

    def _train_kmeans(self, X_scaled: np.ndarray, features: pd.DataFrame):
        """Original KMeans-4 training (fallback)."""
        from sklearn.cluster import KMeans

        n_clusters = REGIME_CONFIG["n_regimes"]
        self.model = KMeans(
            n_clusters=n_clusters,
            init="k-means++",
            n_init=10,
            max_iter=300,
            random_state=42,
        )
        self.model.fit(X_scaled)

        centroids = self.scaler.inverse_transform(self.model.cluster_centers_)
        labels = self.model.labels_
        print(f"[RegimeDetector] KMeans trained on {len(features)} samples (fallback)")
        for i, centroid in enumerate(centroids):
            count = (labels == i).sum()
            pct = count / len(labels) * 100
            print(f"  Regime {i}: return={centroid[0]:.1f}%, "
                  f"vol={centroid[1]:.1f}%, "
                  f"rsi={centroid[2]:.0f}, adx={centroid[3]:.0f} "
                  f"({count} samples, {pct:.0f}%)")

    def detect_current_regime(self, df: pd.DataFrame) -> Dict:
        """
        Detect current market regime from latest OHLCV data.

        Returns dict with keys:
            regime_id, regime_label, confidence, features,
            recommendations, transition_probs, persistence_prob
        """
        if self.model is None:
            return self._unknown_result()

        features = self._compute_features(df)
        if features.empty:
            return self._unknown_result()

        if self.use_hmm:
            return self._detect_hmm(features)
        else:
            return self._detect_kmeans(features)

    def _detect_hmm(self, features: pd.DataFrame) -> Dict:
        """Detect regime using HMM (Viterbi on recent window)."""
        window = features.iloc[-60:] if len(features) >= 60 else features
        X = self.scaler.transform(window.values)

        _, state_seq = self.model.decode(X, algorithm="viterbi")
        current_state = int(state_seq[-1])
        label = self._state_label_map.get(current_state, self.SIDEWAYS)

        posteriors = self.model.predict_proba(X)
        last_posterior = posteriors[-1]
        confidence = float(last_posterior[current_state])

        trans_row = self.model.transmat_[current_state]
        transition_probs = {
            self._state_label_map.get(j, f"state_{j}"): round(float(trans_row[j]), 4)
            for j in range(self.N_HMM_STATES)
        }

        persistence_prob = round(float(trans_row[current_state]), 4)
        expected_duration = round(1.0 / (1.0 - persistence_prob + 1e-10), 1)

        latest_feats = features.iloc[-1]

        return {
            "regime_id": current_state,
            "regime_label": label,
            "confidence": round(confidence, 3),
            "features": {
                "return_20d": round(float(latest_feats["return_20d"]), 2),
                "volatility_20d": round(float(latest_feats["volatility_20d"]), 2),
                "rsi_14": round(float(latest_feats["rsi_14"]), 1),
                "adx_14": round(float(latest_feats["adx_14"]), 1),
            },
            "transition_probs": transition_probs,
            "persistence_prob": persistence_prob,
            "expected_duration_bars": expected_duration,
            "recommendations": self._regime_recommendations(label),
            "backend": "hmm",
        }

    def _detect_kmeans(self, features: pd.DataFrame) -> Dict:
        """Detect regime using KMeans (original logic)."""
        latest = features.iloc[-1:].values
        latest_scaled = self.scaler.transform(latest)

        regime_id = int(self.model.predict(latest_scaled)[0])

        distances = self.model.transform(latest_scaled)[0]
        min_dist = distances[regime_id]
        max_dist = distances.max()
        confidence = 1.0 - (min_dist / (max_dist + 1e-10))

        centroid = self.scaler.inverse_transform(
            self.model.cluster_centers_[regime_id : regime_id + 1]
        )[0]

        is_bull = centroid[0] > 0
        median_vol = np.median(
            self.scaler.inverse_transform(self.model.cluster_centers_)[:, 1]
        )
        is_high_vol = centroid[1] > median_vol

        if is_bull and not is_high_vol:
            label = "bull_low_vol"
        elif is_bull and is_high_vol:
            label = "bull_high_vol"
        elif not is_bull and not is_high_vol:
            label = "bear_low_vol"
        else:
            label = "bear_high_vol"

        latest_feats = features.iloc[-1]

        return {
            "regime_id": regime_id,
            "regime_label": label,
            "confidence": round(confidence, 3),
            "features": {
                "return_20d": round(float(latest_feats["return_20d"]), 2),
                "volatility_20d": round(float(latest_feats["volatility_20d"]), 2),
                "rsi_14": round(float(latest_feats["rsi_14"]), 1),
                "adx_14": round(float(latest_feats["adx_14"]), 1),
            },
            "transition_probs": {},
            "persistence_prob": None,
            "expected_duration_bars": None,
            "recommendations": self._regime_recommendations(label),
            "backend": "kmeans",
        }

    def get_transition_matrix(self) -> Optional[Dict]:
        """
        Return the HMM transition probability matrix as a labelled dict.

        Returns None if using KMeans fallback or model is untrained.
        """
        if not self.use_hmm or self.model is None:
            return None

        T = self.model.transmat_
        result = {}
        for i in range(T.shape[0]):
            from_label = self._state_label_map.get(i, f"state_{i}")
            result[from_label] = {
                self._state_label_map.get(j, f"state_{j}"): round(float(T[i, j]), 4)
                for j in range(T.shape[1])
            }
        return result

    def get_regime_persistence(self) -> Dict[str, float]:
        """
        Return {label: P(stay)} for every regime.

        Persistence = diagonal of transition matrix.
        """
        if not self.use_hmm or self.model is None:
            return {}

        T = self.model.transmat_
        return {
            self._state_label_map.get(i, f"state_{i}"): round(float(T[i, i]), 4)
            for i in range(T.shape[0])
        }

    def _regime_recommendations(self, label: str) -> Dict:
        """Per-regime model preference, TP/SL adjustment, and position sizing."""
        recommendations = {
            "bull": {
                "preferred_model": "B_lightgbm",
                "tp_adjustment": 1.3,
                "sl_adjustment": 0.8,
                "position_size_mult": 1.2,
                "strategy_note": (
                    "Bull regime -- trend-following bias, wider TP, "
                    "tighter SL, larger position sizes"
                ),
            },
            "bear": {
                "preferred_model": "D_ensemble_stack",
                "tp_adjustment": 0.7,
                "sl_adjustment": 1.4,
                "position_size_mult": 0.3,
                "strategy_note": (
                    "Bear regime -- defensive, very tight TP, wide SL "
                    "to avoid stop-hunts, minimal exposure"
                ),
            },
            "sideways": {
                "preferred_model": "A_xgboost",
                "tp_adjustment": 0.9,
                "sl_adjustment": 0.9,
                "position_size_mult": 0.7,
                "strategy_note": (
                    "Sideways regime -- mean-reversion bias, modest "
                    "TP/SL, reduced size to avoid chop"
                ),
            },
            "bull_low_vol": {
                "preferred_model": "B_lightgbm",
                "tp_adjustment": 1.2,
                "sl_adjustment": 0.8,
                "position_size_mult": 1.2,
                "strategy_note": "Trending market -- wider TP, tighter SL, larger positions",
            },
            "bull_high_vol": {
                "preferred_model": "A_xgboost",
                "tp_adjustment": 1.5,
                "sl_adjustment": 1.2,
                "position_size_mult": 0.8,
                "strategy_note": "Volatile uptrend -- wider everything, smaller positions",
            },
            "bear_low_vol": {
                "preferred_model": "C_random_forest",
                "tp_adjustment": 0.8,
                "sl_adjustment": 0.6,
                "position_size_mult": 0.5,
                "strategy_note": "Grinding down -- tight TP, tight SL, small positions",
            },
            "bear_high_vol": {
                "preferred_model": "D_ensemble_stack",
                "tp_adjustment": 0.7,
                "sl_adjustment": 1.5,
                "position_size_mult": 0.3,
                "strategy_note": "Panic mode -- very tight TP, wide SL for stops, tiny positions",
            },
        }
        return recommendations.get(label, self._default_recommendations())

    def _default_recommendations(self) -> Dict:
        return {
            "preferred_model": "D_ensemble_stack",
            "tp_adjustment": 1.0,
            "sl_adjustment": 1.0,
            "position_size_mult": 1.0,
            "strategy_note": "Default regime -- balanced approach",
        }

    def _unknown_result(self) -> Dict:
        return {
            "regime_id": -1,
            "regime_label": "unknown",
            "confidence": 0.0,
            "features": {},
            "transition_probs": {},
            "persistence_prob": None,
            "expected_duration_bars": None,
            "recommendations": self._default_recommendations(),
            "backend": "hmm" if self.use_hmm else "kmeans",
        }

    def export_regime_json(self, df: pd.DataFrame, path: Optional[Path] = None) -> Dict:
        """
        Detect regime and write results + transition matrix to JSON.

        Writes to DATA_DIR / "hmm_regime.json" by default.
        """
        result = self.detect_current_regime(df)
        result["transition_matrix"] = self.get_transition_matrix()
        result["regime_persistence"] = self.get_regime_persistence()
        result["updated_at"] = datetime.now(timezone.utc).isoformat()

        out_path = path or (DATA_DIR / "hmm_regime.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as fh:
            json.dump(result, fh, indent=2)

        print(f"[RegimeDetector] Exported regime data -> {out_path}")
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# V2 EXTENSIONS: BOCPD + Enhanced Trade Filtering
# ═══════════════════════════════════════════════════════════════════════════════

class BayesianChangePointDetector:
    """
    Bayesian Online Changepoint Detection (Adams & MacKay 2007).

    Detects regime transitions 1-3 bars BEFORE they're confirmed by HMM/GMM.
    Maintains a "run length" distribution — high P(r=0) means new regime.

    Usage with RegimeDetector:
        detector = RegimeDetector()
        bocpd = BayesianChangePointDetector()
        # Feed returns as they come in
        result = bocpd.update(current_return)
        if result['is_change_point']:
            print("Regime transition likely!")
    """

    def __init__(self, hazard_rate: float = 1/50, threshold: float = 0.3):
        self.hazard_rate = hazard_rate
        self.threshold = threshold
        self.run_length_probs = np.array([1.0])
        self._mean = 0.0
        self._var = 1.0
        self._n = 0

    def update(self, x: float) -> Dict:
        """
        Process new observation (typically a return value).

        Returns:
            'change_probability': P(regime change just happened)
            'is_change_point': whether probability exceeds threshold
            'current_run_length': most likely run length
            'mean_run_length': expected run length
        """
        if np.isnan(x):
            return {
                'change_probability': 0.0,
                'is_change_point': False,
                'current_run_length': int(np.argmax(self.run_length_probs)),
                'mean_run_length': float(np.sum(np.arange(len(self.run_length_probs)) * self.run_length_probs)),
            }

        # Predictive probability
        if self._n < 2:
            pred_prob = 1.0 / np.sqrt(2 * np.pi)
        else:
            std = np.sqrt(self._var / max(self._n, 1) + self._var) + 1e-10
            z = (x - self._mean) / std
            pred_prob = np.exp(-0.5 * z * z) / (std * np.sqrt(2 * np.pi))

        pred_probs = np.full(len(self.run_length_probs), pred_prob)

        # Growth probabilities
        growth_probs = self.run_length_probs * pred_probs * (1 - self.hazard_rate)

        # Changepoint probability
        change_prob = float(np.sum(self.run_length_probs * pred_probs * self.hazard_rate))

        # Updated distribution
        new_probs = np.zeros(len(self.run_length_probs) + 1)
        new_probs[0] = change_prob
        new_probs[1:] = growth_probs

        total = new_probs.sum()
        if total > 0:
            new_probs /= total

        # Truncate for efficiency
        if len(new_probs) > 300:
            keep = new_probs > 1e-6
            keep[0] = True
            new_probs = new_probs[keep]

        self.run_length_probs = new_probs

        # Update sufficient statistics
        self._n += 1
        old_mean = self._mean
        self._mean += (x - self._mean) / self._n
        self._var += (x - old_mean) * (x - self._mean)

        most_likely = int(np.argmax(self.run_length_probs))
        mean_run = float(np.sum(np.arange(len(self.run_length_probs)) * self.run_length_probs))

        return {
            'change_probability': change_prob,
            'is_change_point': change_prob > self.threshold,
            'current_run_length': most_likely,
            'mean_run_length': mean_run,
        }

    def reset(self):
        """Reset state for a new sequence."""
        self.run_length_probs = np.array([1.0])
        self._mean = 0.0
        self._var = 1.0
        self._n = 0


class EnhancedRegimeEngine:
    """
    V2 Regime Engine combining:
    1. RegimeDetector (HMM/KMeans — primary classification)
    2. BayesianChangePointDetector (early transition warning)
    3. Enhanced trade filtering (fixes v1.2's 96.3% BUY failure)

    Usage:
        engine = EnhancedRegimeEngine()
        engine.fit(btc_df)

        # Per-pick regime check
        should_buy, reason = engine.should_trade(df, direction="BUY")
        should_sell, reason = engine.should_trade(df, direction="SELL")

        # Full regime state for dashboard/Discord
        state = engine.get_full_state(df)
    """

    DIRECTION_RULES = {
        # regime_label: {direction: (allowed, reason)}
        "bull": {
            "BUY": (True, "Bull regime — BUY signals valid"),
            "SELL": (False, "Bull regime — avoid shorting uptrend"),
        },
        "bear": {
            "BUY": (False, "Bear regime — v1.2 lesson: 96.3% BUY failure in downtrend"),
            "SELL": (True, "Bear regime — SELL signals work (85.7% WR in v1.2)"),
        },
        "sideways": {
            "BUY": (True, "Sideways — BUY with reduced size (mean reversion)"),
            "SELL": (True, "Sideways — SELL with reduced size (mean reversion)"),
        },
        "bull_low_vol": {
            "BUY": (True, "Bull low vol — ideal for BUY"),
            "SELL": (False, "Bull low vol — avoid shorting"),
        },
        "bull_high_vol": {
            "BUY": (True, "Bull high vol — BUY with caution, reduce size"),
            "SELL": (True, "Bull high vol — SELL on spikes"),
        },
        "bear_low_vol": {
            "BUY": (False, "Bear low vol — no BUY in grinding downtrend"),
            "SELL": (True, "Bear low vol — ideal for SELL"),
        },
        "bear_high_vol": {
            "BUY": (False, "Bear high vol — CRISIS, no trading"),
            "SELL": (False, "Bear high vol — CRISIS, too volatile even for SELL"),
        },
    }

    def __init__(self):
        self.regime_detector = RegimeDetector()
        self.bocpd = BayesianChangePointDetector(hazard_rate=1/50, threshold=0.3)
        self._last_regime = None
        self._regime_start_bar = 0

    def fit(self, btc_df: pd.DataFrame):
        """Train on BTC data."""
        self.regime_detector.train(btc_df)

        # Warm up BOCPD with recent returns
        close = btc_df["close"]
        returns = close.pct_change().dropna()
        for ret in returns.values[-100:]:
            self.bocpd.update(ret)

    def should_trade(self, df: pd.DataFrame, direction: str = "BUY") -> Tuple[bool, str]:
        """
        Decide if a trade should be taken given current regime.

        Args:
            df: OHLCV data (BTC or the pair being traded)
            direction: "BUY" or "SELL"

        Returns:
            (should_trade, reason_string)
        """
        regime_result = self.regime_detector.detect_current_regime(df)
        label = regime_result.get("regime_label", "unknown")
        confidence = regime_result.get("confidence", 0)

        # Check BOCPD for transition warning
        close = df["close"]
        current_return = float(close.pct_change().iloc[-1]) if len(close) > 1 else 0.0
        bocpd_result = self.bocpd.update(current_return)

        # Gate 1: Regime transition likely — wait
        if bocpd_result['is_change_point'] and bocpd_result['change_probability'] > 0.5:
            return False, (
                f"Regime transition detected (P={bocpd_result['change_probability']:.0%}) "
                f"— wait for new regime to settle"
            )

        # Gate 2: Low confidence — wait
        if confidence < 0.4:
            return False, f"Low regime confidence ({confidence:.0%}) — insufficient clarity"

        # Gate 3: Direction-specific rules
        rules = self.DIRECTION_RULES.get(label, {})
        if direction in rules:
            allowed, reason = rules[direction]
            return allowed, f"[{label}] {reason} (conf: {confidence:.0%})"

        # Default: allow with caution
        return True, f"[{label}] No specific rule — trade with caution"

    def get_full_state(self, df: pd.DataFrame) -> Dict:
        """Get complete regime state for dashboard/Discord."""
        regime = self.regime_detector.detect_current_regime(df)

        # BOCPD state
        close = df["close"]
        ret = float(close.pct_change().iloc[-1]) if len(close) > 1 else 0.0
        bocpd = self.bocpd.update(ret)

        # Trade recommendations
        buy_ok, buy_reason = self.should_trade(df, "BUY")
        sell_ok, sell_reason = self.should_trade(df, "SELL")

        return {
            "regime": regime,
            "change_point_detection": {
                "change_probability": round(bocpd['change_probability'], 4),
                "is_change_point": bocpd['is_change_point'],
                "current_run_length": bocpd['current_run_length'],
            },
            "trade_recommendations": {
                "BUY": {"allowed": buy_ok, "reason": buy_reason},
                "SELL": {"allowed": sell_ok, "reason": sell_reason},
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
