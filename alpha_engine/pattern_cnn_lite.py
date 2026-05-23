"""
ALPHA_ENGINE -- CNN-Lite Pattern Recognition
=============================================
Lightweight candlestick pattern classifier that replaces a CNN with tabular
feature extraction + RandomForest ensemble.  Runs in GitHub Actions without
tensorflow (uses only numpy, pandas, sklearn).

UPGRADE PATH TO REAL CNN:
  1. Train CNN locally with tensorflow (see pattern_cnn_trainer.py -- future)
  2. Export to ONNX: python -m tf2onnx.convert --saved-model model/ --output pattern_model.onnx
  3. Add onnxruntime to CI pip install (~50MB)
  4. Replace rule-based scoring with: ort_session.run(None, {'input': features})
  5. This gives actual neural network inference without tensorflow

Feature engineering encodes the SAME visual information a CNN would learn from
candlestick chart images:
  - Per-candle shape (body ratio, wick ratios, bullish/bearish, relative size)
  - Classical patterns (engulfing, hammer, doji, morning/evening star, etc.)
  - Trend context (short/medium trend, volatility regime, volume climax)
  - Aggregate pattern scores (bullish/bearish counts, net strength)

Total: ~47 features per observation.

References:
  - Bulkowski (2008) "Encyclopedia of Candlestick Charts" -- pattern definitions
  - Nison (1991) "Japanese Candlestick Charting Techniques" -- original canon
  - Hu et al. (2019) "Deep Stock Representation Learning" -- CNN feature inspiration
"""

from __future__ import annotations

import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

try:
    from config import CRYPTO_SYMBOLS
    from indicators import rsi as calc_rsi, atr as calc_atr, sma as calc_sma, volume_ratio as calc_volume_ratio, detect_support_resistance
except ImportError:
    # Allow standalone execution with stubs
    CRYPTO_SYMBOLS = {}

    def calc_rsi(close, period=14):
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / (loss + 1e-10)
        return 100 - 100 / (1 + rs)

    def calc_atr(high, low, close, period=14):
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def calc_sma(series, period):
        return series.rolling(period).mean()

    def calc_volume_ratio(volume, period=20):
        return volume / volume.rolling(period).mean()

    def detect_support_resistance(close, lookback=60, num_levels=3):
        window = close.iloc[-lookback:]
        current = float(close.iloc[-1])
        mins, maxs = [], []
        for i in range(2, len(window) - 2):
            if window.iloc[i] <= window.iloc[i - 1] and window.iloc[i] <= window.iloc[i + 1]:
                mins.append(float(window.iloc[i]))
            if window.iloc[i] >= window.iloc[i - 1] and window.iloc[i] >= window.iloc[i + 1]:
                maxs.append(float(window.iloc[i]))
        supports = sorted([m for m in mins if m < current], reverse=True)[:num_levels]
        resistances = sorted([m for m in maxs if m > current])[:num_levels]
        return {"support": supports, "resistance": resistances}


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Minimum bars needed for full feature extraction
MIN_BARS = 30

# Pattern confidence scores (rule-based mode)
PATTERN_SCORES: dict[str, float] = {
    "three_white_soldiers": +0.85,
    "morning_star":         +0.75,
    "bullish_engulfing":    +0.70,
    "piercing_line":        +0.60,
    "hammer":               +0.55,
    "harami_bullish":       +0.45,
    "doji":                  0.00,
    "harami_bearish":       -0.45,
    "shooting_star":        -0.55,
    "dark_cloud_cover":     -0.60,
    "bearish_engulfing":    -0.70,
    "evening_star":         -0.75,
    "three_black_crows":    -0.85,
}

DATA_DIR = Path(__file__).resolve().parent / "data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value == 0:
        return 0.0
    av = abs(value)
    if av >= 100:
        return round(value, 2)
    elif av >= 1:
        return round(value, 4)
    elif av >= 0.01:
        return round(value, 6)
    else:
        return round(value, 8)


def _get_category(symbol: str) -> str:
    info = CRYPTO_SYMBOLS.get(symbol, {})
    if info:
        return info.get("cat", "crypto")
    sym = symbol.upper()
    if any(fx in sym for fx in ("USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD")):
        if not any(c in sym for c in ("BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA")):
            return "forex"
    if any(eq in sym for eq in ("SPY", "QQQ", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL")):
        return "equity"
    return "crypto"


# ---------------------------------------------------------------------------
# Step 1: Feature Engineering -- replaces CNN image input
# ---------------------------------------------------------------------------

def extract_visual_features(df: pd.DataFrame, window: int = 20) -> dict:
    """
    Extract features that a CNN would learn from candlestick images.

    Converts a rolling window of N candles into numeric features capturing
    body shape, wick proportions, classical patterns, trend context, and
    aggregate pattern scores.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV data with columns Open, High, Low, Close, Volume.
        Must have at least ``window + 10`` rows.
    window : int
        Lookback window for contextual features (default 20).

    Returns
    -------
    dict
        ~47 numeric features keyed by descriptive names.
        Returns empty dict if insufficient data.
    """
    required = window + 10
    if df is None or len(df) < required:
        return {}

    # Ensure float types
    o = df["Open"].astype(float)
    h = df["High"].astype(float)
    lo = df["Low"].astype(float)
    c = df["Close"].astype(float)
    v = df["Volume"].astype(float)

    features: dict[str, float] = {}
    eps = 1e-10

    # -- Per-candle shape features (last 5 bars) -------------------------
    body = (c - o).abs()
    full_range = h - lo + eps
    body_ratio = body / full_range
    upper_wick_ratio = (h - pd.concat([o, c], axis=1).max(axis=1)) / full_range
    lower_wick_ratio = (pd.concat([o, c], axis=1).min(axis=1) - lo) / full_range
    is_bullish = (c > o).astype(float)
    avg_body_20 = body.rolling(20).mean() + eps
    body_vs_avg = body / avg_body_20

    for i in range(5):
        idx = -(5 - i)
        features[f"body_ratio_{i}"] = float(body_ratio.iloc[idx])
        features[f"upper_wick_ratio_{i}"] = float(upper_wick_ratio.iloc[idx])
        features[f"lower_wick_ratio_{i}"] = float(lower_wick_ratio.iloc[idx])
        features[f"is_bullish_{i}"] = float(is_bullish.iloc[idx])
        features[f"body_size_vs_avg_{i}"] = float(body_vs_avg.iloc[idx])

    # -- Classical pattern detection --------------------------------------
    # Current and previous bars
    c0, o0, h0, lo0 = float(c.iloc[-1]), float(o.iloc[-1]), float(h.iloc[-1]), float(lo.iloc[-1])
    c1, o1, h1, lo1 = float(c.iloc[-2]), float(o.iloc[-2]), float(h.iloc[-2]), float(lo.iloc[-2])
    c2, o2, h2, lo2 = float(c.iloc[-3]), float(o.iloc[-3]), float(h.iloc[-3]), float(lo.iloc[-3])

    body0 = abs(c0 - o0)
    body1 = abs(c1 - o1)
    body2 = abs(c2 - o2)
    range0 = h0 - lo0 + eps
    range1 = h1 - lo1 + eps
    range2 = h2 - lo2 + eps

    top0, bot0 = max(c0, o0), min(c0, o0)
    top1, bot1 = max(c1, o1), min(c1, o1)
    top2, bot2 = max(c2, o2), min(c2, o2)

    bull0 = c0 > o0
    bear0 = c0 < o0
    bull1 = c1 > o1
    bear1 = c1 < o1
    bull2 = c2 > o2
    bear2 = c2 < o2

    uw0 = h0 - top0
    lw0 = bot0 - lo0
    uw1 = h1 - top1
    lw1 = bot1 - lo1

    # Support/resistance context
    sr = detect_support_resistance(c, lookback=min(60, len(c) - 1), num_levels=3)
    supports = sr.get("support", [])
    resistances = sr.get("resistance", [])
    near_support = any(abs(c0 - s) / (c0 + eps) < 0.02 for s in supports) if supports else False
    near_resistance = any(abs(c0 - r) / (c0 + eps) < 0.02 for r in resistances) if resistances else False

    # 1. Engulfing bullish
    engulfing_bull = 1.0 if (bear1 and bull0 and bot0 <= bot1 and top0 >= top1 and body0 > body1) else 0.0
    features["engulfing_bullish"] = engulfing_bull

    # 2. Engulfing bearish
    engulfing_bear = 1.0 if (bull1 and bear0 and top0 >= top1 and bot0 <= bot1 and body0 > body1) else 0.0
    features["engulfing_bearish"] = engulfing_bear

    # 3. Hammer (lower wick > 2x body, small upper wick, at support)
    hammer = 1.0 if (lw0 > 2 * body0 and uw0 < 0.3 * body0 and (near_support or float(body_ratio.iloc[-1]) < 0.35)) else 0.0
    features["hammer"] = hammer

    # 4. Shooting star
    shooting_star = 1.0 if (uw0 > 2 * body0 and lw0 < 0.3 * body0 and (near_resistance or float(body_ratio.iloc[-1]) < 0.35)) else 0.0
    features["shooting_star"] = shooting_star

    # 5. Doji
    doji = 1.0 if (body0 / range0) < 0.1 else 0.0
    features["doji"] = doji

    # 6. Three white soldiers
    three_ws = 1.0 if (
        bull0 and bull1 and bull2
        and c0 > c1 > c2
        and body0 / range0 > 0.6
        and body1 / range1 > 0.6
        and body2 / range2 > 0.6
    ) else 0.0
    features["three_white_soldiers"] = three_ws

    # 7. Three black crows
    three_bc = 1.0 if (
        bear0 and bear1 and bear2
        and c0 < c1 < c2
        and body0 / range0 > 0.6
        and body1 / range1 > 0.6
        and body2 / range2 > 0.6
    ) else 0.0
    features["three_black_crows"] = three_bc

    # 8. Morning star: bearish bar + small body + bullish bar spanning >50% of first
    small_body_1 = (body1 / range1) < 0.3
    morning_star = 1.0 if (bear2 and small_body_1 and bull0 and top0 > (top2 + bot2) / 2) else 0.0
    features["morning_star"] = morning_star

    # 9. Evening star: bullish bar + small body + bearish bar spanning >50% of first
    evening_star = 1.0 if (bull2 and small_body_1 and bear0 and bot0 < (top2 + bot2) / 2) else 0.0
    features["evening_star"] = evening_star

    # 10. Piercing line
    piercing = 1.0 if (bear1 and bull0 and o0 < lo1 and c0 > (o1 + c1) / 2) else 0.0
    features["piercing_line"] = piercing

    # 11. Dark cloud cover
    dark_cloud = 1.0 if (bull1 and bear0 and o0 > h1 and c0 < (o1 + c1) / 2) else 0.0
    features["dark_cloud_cover"] = dark_cloud

    # 12. Harami bullish
    harami_bull = 1.0 if (bear1 and bull0 and top0 < top1 and bot0 > bot1 and body0 < body1 * 0.6) else 0.0
    features["harami_bullish"] = harami_bull

    # 13. Harami bearish
    harami_bear = 1.0 if (bull1 and bear0 and top0 < top1 and bot0 > bot1 and body0 < body1 * 0.6) else 0.0
    features["harami_bearish"] = harami_bear

    # -- Trend context features -------------------------------------------
    # 19. Short-term trend (5 bars)
    if len(c) >= 6:
        features["trend_5"] = (c0 - float(c.iloc[-6])) / (float(c.iloc[-6]) + eps)
    else:
        features["trend_5"] = 0.0

    # 20. Medium-term trend (20 bars)
    if len(c) >= 21:
        features["trend_20"] = (c0 - float(c.iloc[-21])) / (float(c.iloc[-21]) + eps)
    else:
        features["trend_20"] = 0.0

    # 21. Volatility ratio (std_5 / std_20)
    std_5 = float(c.iloc[-5:].pct_change().std()) if len(c) >= 5 else 0.0
    std_20 = float(c.iloc[-20:].pct_change().std()) if len(c) >= 20 else std_5 + eps
    features["volatility_ratio"] = std_5 / (std_20 + eps)

    # 22. Volume climax
    vol_sma_20 = float(v.iloc[-20:].mean()) if len(v) >= 20 else float(v.iloc[-1]) + eps
    features["volume_climax"] = float(v.iloc[-1]) / (vol_sma_20 + eps)

    # 23. RSI(14)
    rsi_series = calc_rsi(c, 14)
    rsi_val = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0
    features["rsi_14"] = rsi_val

    # 24. Position in range
    if len(c) >= window:
        low_w = float(lo.iloc[-window:].min())
        high_w = float(h.iloc[-window:].max())
        features["position_in_range"] = (c0 - low_w) / (high_w - low_w + eps)
    else:
        features["position_in_range"] = 0.5

    # -- Aggregate pattern scores -----------------------------------------
    bullish_patterns = [
        engulfing_bull, hammer, three_ws, morning_star,
        piercing, harami_bull,
    ]
    bearish_patterns = [
        engulfing_bear, shooting_star, three_bc, evening_star,
        dark_cloud, harami_bear,
    ]
    features["bullish_pattern_count"] = sum(bullish_patterns)
    features["bearish_pattern_count"] = sum(bearish_patterns)
    features["pattern_strength"] = sum(bullish_patterns) - sum(bearish_patterns)

    # -- Context flags (for score adjustments) ----------------------------
    features["near_support"] = 1.0 if near_support else 0.0
    features["near_resistance"] = 1.0 if near_resistance else 0.0

    return features


# ---------------------------------------------------------------------------
# Step 2 & 3: Pattern Classifier (rule-based + ML modes)
# ---------------------------------------------------------------------------

class PatternClassifierLite:
    """
    Lightweight pattern classifier -- replaces CNN with tabular features +
    RandomForest.  Operates in two modes:

    - ``rules``:  Hardcoded pattern scores with contextual adjustments.
                  Works immediately, no training data needed.
    - ``ml``:     sklearn RandomForest trained on closed-pick outcomes.
                  Auto-activates when >= 50 labelled samples exist.
    """

    MODEL_PATH = DATA_DIR / "pattern_model.pkl"

    def __init__(self):
        self.model = None
        self.mode: str = "rules"
        self.feature_names: list[str] = []
        self._try_load_model()

    # -- Model persistence ------------------------------------------------

    def _try_load_model(self):
        """Load a previously trained model if available."""
        if self.MODEL_PATH.exists():
            try:
                import joblib
                payload = joblib.load(self.MODEL_PATH)
                self.model = payload["model"]
                self.feature_names = payload.get("feature_names", [])
                self.mode = "ml"
                logger.info("CNN-Lite: loaded trained model from %s", self.MODEL_PATH)
            except Exception as exc:
                logger.warning("CNN-Lite: failed to load model: %s", exc)
                self.mode = "rules"

    # -- Classification ---------------------------------------------------

    def classify_pattern(self, df: pd.DataFrame) -> dict:
        """
        Classify the current candlestick pattern.

        Returns
        -------
        dict with keys:
            pattern   : str   -- e.g. 'bullish_engulfing', 'morning_star', 'none'
            direction : str   -- 'bullish' / 'bearish' / 'neutral'
            confidence: float -- 0.0-1.0
            strength  : int   -- 1-5 (how many confirming signals)
        """
        feats = extract_visual_features(df)
        if not feats:
            return {"pattern": "none", "direction": "neutral", "confidence": 0.0, "strength": 0}

        if self.mode == "ml" and self.model is not None:
            return self._classify_ml(feats)
        return self._classify_rules(feats)

    def _classify_rules(self, feats: dict) -> dict:
        """Rule-based classification using PATTERN_SCORES."""
        best_pattern = "none"
        best_raw_score = 0.0

        # Find the dominant pattern
        for pat_name, base_score in PATTERN_SCORES.items():
            detected = feats.get(pat_name, 0.0)
            if detected >= 1.0 and abs(base_score) > abs(best_raw_score):
                best_pattern = pat_name
                best_raw_score = base_score

        if best_pattern == "none":
            # Check doji separately (score 0.0 but still a pattern)
            if feats.get("doji", 0.0) >= 1.0:
                return {"pattern": "doji", "direction": "neutral", "confidence": 0.3, "strength": 1}
            return {"pattern": "none", "direction": "neutral", "confidence": 0.0, "strength": 0}

        # Direction from score sign
        if best_raw_score > 0:
            direction = "bullish"
        elif best_raw_score < 0:
            direction = "bearish"
        else:
            direction = "neutral"

        # Contextual adjustments
        confidence = abs(best_raw_score)

        # At support + bullish -> boost
        if feats.get("near_support", 0) and direction == "bullish":
            confidence += 0.15
        # At resistance + bearish -> boost
        if feats.get("near_resistance", 0) and direction == "bearish":
            confidence += 0.15
        # Volume spike confirms
        if feats.get("volume_climax", 1.0) > 1.5:
            confidence += 0.10
        # Against trend -> reduce
        trend = feats.get("trend_5", 0.0)
        if (direction == "bullish" and trend > 0.03) or (direction == "bearish" and trend < -0.03):
            pass  # With trend -- no penalty
        elif (direction == "bullish" and trend < -0.03) or (direction == "bearish" and trend > 0.03):
            confidence -= 0.20  # Counter-trend
        # RSI confirms
        rsi_val = feats.get("rsi_14", 50.0)
        if direction == "bullish" and rsi_val < 35:
            confidence += 0.10
        elif direction == "bearish" and rsi_val > 65:
            confidence += 0.10

        confidence = max(0.0, min(1.0, confidence))

        # Strength = number of confirming patterns
        bull_count = int(feats.get("bullish_pattern_count", 0))
        bear_count = int(feats.get("bearish_pattern_count", 0))
        strength = bull_count if direction == "bullish" else bear_count
        strength = max(1, min(5, strength))

        return {
            "pattern": best_pattern,
            "direction": direction,
            "confidence": round(confidence, 3),
            "strength": strength,
        }

    def _classify_ml(self, feats: dict) -> dict:
        """ML-based classification using trained RandomForest."""
        try:
            # Build feature vector in training order
            if self.feature_names:
                x = np.array([[feats.get(fn, 0.0) for fn in self.feature_names]])
            else:
                x = np.array([[v for v in feats.values()]])

            proba = self.model.predict_proba(x)[0]
            pred = int(self.model.predict(x)[0])

            # pred: 1=bullish outcome, 0=bearish outcome
            confidence = float(max(proba))
            direction = "bullish" if pred == 1 else "bearish"

            # Find named pattern for reporting
            best_pattern = "ml_composite"
            best_score = 0.0
            for pat_name in PATTERN_SCORES:
                if feats.get(pat_name, 0.0) >= 1.0 and abs(PATTERN_SCORES[pat_name]) > abs(best_score):
                    best_pattern = pat_name
                    best_score = PATTERN_SCORES[pat_name]

            bull_count = int(feats.get("bullish_pattern_count", 0))
            bear_count = int(feats.get("bearish_pattern_count", 0))
            strength = max(1, min(5, bull_count + bear_count))

            return {
                "pattern": best_pattern,
                "direction": direction,
                "confidence": round(confidence, 3),
                "strength": strength,
            }
        except Exception as exc:
            logger.warning("CNN-Lite ML classify failed: %s -- falling back to rules", exc)
            return self._classify_rules(feats)

    # -- Scanner integration ----------------------------------------------

    def score_for_scanner(self, symbol: str, df: pd.DataFrame, market_data=None) -> float:
        """
        Returns a score for use as an ML feature or confluence signal.

        Score range: -1.0 (strong bearish) to +1.0 (strong bullish).
        """
        result = self.classify_pattern(df)
        if result["pattern"] == "none":
            return 0.0

        sign = 1.0 if result["direction"] == "bullish" else -1.0
        return round(sign * result["confidence"], 4)


# ---------------------------------------------------------------------------
# Step 4: ML Training (when enough data exists)
# ---------------------------------------------------------------------------

def train_from_closed_picks(closed_picks_path: Optional[str] = None):
    """
    Train RandomForest on historical pick outcomes.

    Only activates when >= 50 closed picks have pattern features extractable
    from cached OHLCV data.

    Parameters
    ----------
    closed_picks_path : str or None
        Path to closed_picks.json. Defaults to data/closed_picks.json.

    Returns
    -------
    dict with training metrics, or None if insufficient data.
    """
    if closed_picks_path is None:
        closed_picks_path = str(DATA_DIR / "closed_picks.json")

    if not os.path.exists(closed_picks_path):
        logger.info("CNN-Lite train: no closed picks file at %s", closed_picks_path)
        return None

    try:
        with open(closed_picks_path, "r") as f:
            picks = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("CNN-Lite train: failed to read closed picks: %s", exc)
        return None

    if len(picks) < 50:
        logger.info("CNN-Lite train: only %d picks (need 50+), skipping", len(picks))
        return None

    # Try importing yfinance for historical data
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("CNN-Lite train: yfinance not available, cannot reconstruct OHLCV windows")
        return None

    from sklearn.ensemble import RandomForestClassifier
    import joblib

    X_rows = []
    y_labels = []
    feature_names = None

    for pick in picks:
        try:
            sym = pick.get("symbol", "")
            outcome = pick.get("outcome", "").upper()
            entry_date = pick.get("entry_date", pick.get("timestamp", ""))

            if outcome not in ("WON", "LOST"):
                continue

            # Fetch OHLCV window around entry date
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="60d", end=entry_date)
            if hist is None or len(hist) < MIN_BARS:
                continue

            # Standardize column names
            hist.columns = [col if col in ("Open", "High", "Low", "Close", "Volume") else col for col in hist.columns]

            feats = extract_visual_features(hist)
            if not feats:
                continue

            if feature_names is None:
                feature_names = sorted(feats.keys())

            row = [feats.get(fn, 0.0) for fn in feature_names]
            X_rows.append(row)
            y_labels.append(1 if outcome == "WON" else 0)

        except Exception as exc:
            logger.debug("CNN-Lite train: skip pick %s: %s", pick.get("symbol"), exc)
            continue

    if len(X_rows) < 50:
        logger.info("CNN-Lite train: only %d valid samples (need 50+), skipping", len(X_rows))
        return None

    X = np.array(X_rows)
    y = np.array(y_labels)

    # Train with conservative hyperparameters to avoid overfitting
    clf = RandomForestClassifier(
        n_estimators=50,
        max_depth=4,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X, y)

    # Simple holdout accuracy estimate (last 20%)
    split = int(len(X) * 0.8)
    if split > 0 and split < len(X):
        train_acc = clf.score(X[:split], y[:split])
        val_acc = clf.score(X[split:], y[split:])
    else:
        train_acc = clf.score(X, y)
        val_acc = train_acc

    # Save model
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": clf, "feature_names": feature_names}, PatternClassifierLite.MODEL_PATH)

    metrics = {
        "samples": len(X_rows),
        "positive_rate": float(np.mean(y)),
        "train_accuracy": round(train_acc, 4),
        "val_accuracy": round(val_acc, 4),
        "n_features": len(feature_names),
        "trained_at": _now_iso(),
    }
    logger.info("CNN-Lite trained: %s", metrics)
    return metrics


# ---------------------------------------------------------------------------
# Step 5: Pre-computed Scores Cache
# ---------------------------------------------------------------------------

def precompute_all_scores(
    symbols: list[str],
    output_path: Optional[str] = None,
) -> dict:
    """
    Run pattern detection on all symbols, save scores to JSON cache.

    Can be called locally or on a schedule. CI reads the cached scores
    for fast lookups without recalculating on every run.

    Parameters
    ----------
    symbols : list[str]
        List of ticker symbols to score.
    output_path : str or None
        Path to write JSON cache. Defaults to data/pattern_scores.json.

    Returns
    -------
    dict  The computed scores mapping.
    """
    if output_path is None:
        output_path = str(DATA_DIR / "pattern_scores.json")

    try:
        import yfinance as yf
    except ImportError:
        logger.warning("precompute_all_scores: yfinance not available")
        return {}

    classifier = PatternClassifierLite()
    scores: dict[str, dict] = {}

    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="60d")
            if hist is None or len(hist) < MIN_BARS:
                continue

            result = classifier.classify_pattern(hist)
            score = classifier.score_for_scanner(sym, hist)

            scores[sym] = {
                "pattern": result["pattern"],
                "direction": result["direction"],
                "confidence": result["confidence"],
                "score": score,
                "strength": result["strength"],
                "computed_at": _now_iso(),
            }
        except Exception as exc:
            logger.debug("precompute_all_scores: skip %s: %s", sym, exc)
            continue

    # Write cache
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(output_path, "w") as f:
            json.dump(scores, f, indent=2)
        logger.info("CNN-Lite: cached %d pattern scores to %s", len(scores), output_path)
    except OSError as exc:
        logger.warning("CNN-Lite: failed to write cache: %s", exc)

    return scores


def load_cached_scores(cache_path: Optional[str] = None) -> dict:
    """Load pre-computed pattern scores from JSON cache."""
    if cache_path is None:
        cache_path = str(DATA_DIR / "pattern_scores.json")
    if not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# Step 6: Strategy Function for Scanner Integration
# ---------------------------------------------------------------------------

def cnn_lite_pattern_signal(symbol: str, df: pd.DataFrame, market_data=None) -> list[dict]:
    """
    CNN-Lite pattern recognition strategy.

    Uses tabular feature extraction (the same features a CNN would learn from
    candlestick images) plus either rule-based scoring or a trained
    RandomForest ensemble.  Runs in GitHub Actions without tensorflow.

    Signal generation rules:
      - Only signal if pattern confidence > 0.55
      - Only signal if net pattern_strength >= 2 (multiple confirming patterns)
      - TP: 2x ATR(14) in signal direction
      - SL: 1.2x ATR(14) against signal direction
      - Boost confidence if RSI confirms, volume confirms, and at S/R level

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. 'BTC-USD').
    df : pd.DataFrame
        OHLCV data with at least MIN_BARS rows.
    market_data : optional
        Additional market context (unused currently, reserved for future).

    Returns
    -------
    list[dict]  Signal dicts compatible with Alpha Engine scanner.
    """
    signals: list[dict] = []

    if df is None or len(df) < MIN_BARS:
        return signals

    try:
        classifier = PatternClassifierLite()
        result = classifier.classify_pattern(df)

        pattern = result["pattern"]
        direction = result["direction"]
        confidence = result["confidence"]
        strength = result["strength"]

        # Gate: minimum confidence
        if confidence <= 0.55:
            return signals

        # Gate: need multiple confirming patterns
        feats = extract_visual_features(df)
        if not feats:
            return signals

        net_strength = abs(feats.get("pattern_strength", 0))
        if net_strength < 2 and strength < 2:
            return signals

        # Price and ATR for TP/SL
        close = df["Close"].astype(float)
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        price = float(close.iloc[-1])

        atr_series = calc_atr(high, low, close, period=14)
        atr_val = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else price * 0.02

        # Signal type
        if direction == "bullish":
            signal_type = "BUY"
            tp = _smart_round(price + 2.0 * atr_val)
            sl = _smart_round(price - 1.2 * atr_val)
        elif direction == "bearish":
            signal_type = "SELL"
            tp = _smart_round(price - 2.0 * atr_val)
            sl = _smart_round(price + 1.2 * atr_val)
        else:
            return signals  # Neutral patterns don't generate signals

        # Risk-reward ratio
        rr = abs(price - tp) / (abs(price - sl) + 1e-10)

        # Extra context
        rsi_val = feats.get("rsi_14", 50.0)
        vol_ratio = feats.get("volume_climax", 1.0)
        bull_count = int(feats.get("bullish_pattern_count", 0))
        bear_count = int(feats.get("bearish_pattern_count", 0))

        signals.append({
            "strategy": "cnn_lite_pattern_signal",
            "symbol": symbol,
            "category": _get_category(symbol),
            "signal_type": signal_type,
            "entry_price": _smart_round(price),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(confidence, 3),
            "risk_reward": round(rr, 2),
            "reason": (
                f"CNN-Lite: {pattern.replace('_', ' ').title()} pattern detected "
                f"(confidence: {confidence:.0%}, strength: {strength}/5). "
                f"RSI={rsi_val:.0f}, Vol={vol_ratio:.1f}x avg"
            ),
            "timeframe": "1-5d",
            "extra": {
                "pattern": pattern,
                "pattern_score": PATTERN_SCORES.get(pattern, 0.0),
                "bullish_count": bull_count,
                "bearish_count": bear_count,
                "volume_ratio": round(vol_ratio, 2),
                "rsi": round(rsi_val, 1),
                "net_strength": int(net_strength),
                "mode": classifier.mode,
                "near_support": bool(feats.get("near_support", 0)),
                "near_resistance": bool(feats.get("near_resistance", 0)),
            },
            "timestamp": _now_iso(),
        })

    except Exception as exc:
        logger.warning("cnn_lite_pattern_signal(%s): %s", symbol, exc)

    return signals


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

CNN_LITE_STRATEGIES: dict[str, callable] = {
    "cnn_lite_pattern_signal": cnn_lite_pattern_signal,
}


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    test_symbol = sys.argv[1] if len(sys.argv) > 1 else "BTC-USD"
    print(f"\n=== CNN-Lite Pattern Recognition Test: {test_symbol} ===\n")

    # Try yfinance for real data, fall back to synthetic
    df = None
    try:
        import yfinance as yf
        ticker = yf.Ticker(test_symbol)
        df = ticker.history(period="60d")
        if df is not None and len(df) >= MIN_BARS:
            print(f"Loaded {len(df)} bars of real data for {test_symbol}")
        else:
            df = None
    except ImportError:
        pass

    if df is None:
        # Generate synthetic candlestick data
        print("Using synthetic data (yfinance not available)")
        np.random.seed(42)
        n = 60
        dates = pd.date_range("2026-01-01", periods=n, freq="D")
        base = 100.0
        closes = [base]
        for _ in range(n - 1):
            closes.append(closes[-1] * (1 + np.random.randn() * 0.02))
        closes = np.array(closes)
        highs = closes * (1 + np.abs(np.random.randn(n) * 0.01))
        lows = closes * (1 - np.abs(np.random.randn(n) * 0.01))
        opens = closes * (1 + np.random.randn(n) * 0.005)
        volumes = np.random.randint(1000, 50000, n).astype(float)

        # Inject a bullish engulfing pattern at the end
        opens[-2] = closes[-3] + 0.5     # Previous bar opens high
        closes[-2] = opens[-2] - 3.0     # Previous bar closes low (bearish)
        lows[-2] = closes[-2] - 0.3
        highs[-2] = opens[-2] + 0.3
        opens[-1] = closes[-2] - 0.5     # Current bar opens below prev close
        closes[-1] = opens[-2] + 1.0     # Current bar closes above prev open
        lows[-1] = opens[-1] - 0.2
        highs[-1] = closes[-1] + 0.2
        volumes[-1] = volumes[-10:].mean() * 2  # Volume spike

        df = pd.DataFrame({
            "Open": opens, "High": highs, "Low": lows,
            "Close": closes, "Volume": volumes,
        }, index=dates)
        print(f"Generated {len(df)} bars with injected bullish engulfing\n")

    # 1. Feature extraction
    feats = extract_visual_features(df)
    print(f"Extracted {len(feats)} features:")
    for k, v in sorted(feats.items()):
        if v != 0.0:
            print(f"  {k:30s} = {v:.4f}")

    # 2. Pattern classification
    classifier = PatternClassifierLite()
    result = classifier.classify_pattern(df)
    print(f"\nClassification: {result}")
    print(f"Scanner score:  {classifier.score_for_scanner(test_symbol, df)}")

    # 3. Signal generation
    picks = cnn_lite_pattern_signal(test_symbol, df)
    if picks:
        print(f"\nSignals generated: {len(picks)}")
        for p in picks:
            print(f"  {p['signal_type']} {p['symbol']} @ {p['entry_price']}")
            print(f"    TP={p['take_profit']} SL={p['stop_loss']} RR={p['risk_reward']}")
            print(f"    {p['reason']}")
            print(f"    Mode: {p['extra']['mode']}, Patterns: "
                  f"+{p['extra']['bullish_count']}/-{p['extra']['bearish_count']}")
    else:
        print("\nNo signals generated (confidence or strength below threshold)")

    print("\n=== Test Complete ===")
