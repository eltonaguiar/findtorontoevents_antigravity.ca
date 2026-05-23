#!/usr/bin/env python3
"""
Meta-Consensus Scorer — Cross-System ML Meta-Learner
=====================================================
Combines predictions from KIMI, Alpha Engine, and Copy Trader Intelligence
into a single ML model that learns WHICH source to trust UNDER WHICH conditions.

Input features per pick:
  - consensus_count, source_agreement_type
  - enrichment signals (funding_rate, oi_change, fear_greed, dvol, ls_ratio)
  - symbol_category (large_cap / alt_l1 / defi / meme)
  - direction (LONG=1, SHORT=0)
  - time features (hour_sin/cos, day_of_week)
  - volatility (24h change %)
  - market regime (fear_greed bucket)

Training data: closed trades from KIMI, Alpha Engine, portfolio_1x.

Output: P(win) for each pick — gate at P(win) > 0.55
"""

import json
import math
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows charmap encoding — force UTF-8 stdout/stderr
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

warnings.filterwarnings("ignore")

# ======================================================================
# Constants
# ======================================================================

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
KIMI_DATA = BASE_DIR.parent / "KIMI_RISEOFTHECLAW" / "data"
COPY_TRADER_DATA = BASE_DIR.parent / "copy_trader_intel" / "data"
MODEL_PATH = DATA_DIR / "meta_learner_model.json"

# Symbol category mapping
LARGE_CAP = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
             "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
             "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD", "DOGE-USD",
             "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
             "BTCUSD", "ETHUSD"}
ALT_L1 = {"NEARUSDT", "APTUSDT", "SUIUSDT", "SEIUSDT", "TIAUSDT", "INJUSDT",
           "TONUSDT", "TRXUSDT", "ATOMUSDT", "ALGOUSDT", "FTMUSDT", "OPUSDT",
           "ARBUSDT", "STXUSDT", "KASUSDT", "HYPEUSDT",
           "NEAR-USD", "APT-USD", "SUI-USD", "TRX-USD", "TON-USD", "KAS-USD"}
DEFI = {"UNIUSDT", "AAVEUSDT", "MKRUSDT", "COMPUSDT", "CRVUSDT", "SUSHIUSDT",
        "SNXUSDT", "DYDXUSDT", "GMXUSDT", "PENDLEUSDT", "JUPUSDT",
        "UNI-USD", "AAVE-USD", "MKR-USD", "DYDX-USD", "JUP-USD"}
MEME = {"DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "FLOKIUSDT", "BONKUSDT",
        "WIFUSDT", "MEMEUSDT", "BOMEUSDT", "TURBOUSDT", "NEIROUSDT",
        "DOGE-USD", "SHIB-USD", "PEPE-USD", "BONK-USD", "WIF-USD"}


def categorize_symbol(symbol: str) -> str:
    """Categorize a symbol into large_cap / alt_l1 / defi / meme / other."""
    s = symbol.upper().replace("-", "").replace("/", "")
    # Normalize to USDT suffix for matching
    for suffix in ["USDT", "USD", "PERP"]:
        base = s.replace(suffix, "") + "USDT"
        if base in MEME or s in MEME:
            return "meme"
        if base in LARGE_CAP or s in LARGE_CAP:
            return "large_cap"
        if base in ALT_L1 or s in ALT_L1:
            return "alt_l1"
        if base in DEFI or s in DEFI:
            return "defi"
    return "other"


def normalize_symbol(symbol: str) -> str:
    """Normalize BTC-USD / BTCUSD / BTCUSDT -> BTCUSDT."""
    s = symbol.upper().replace("-", "").replace("/", "").replace("=X", "")
    if not s.endswith("USDT") and not s.endswith("USD"):
        return s
    if s.endswith("USD") and not s.endswith("USDT"):
        s = s + "T"
    return s


# ======================================================================
# Feature Engineering
# ======================================================================

def extract_time_features(date_str: str) -> dict:
    """Extract cyclical time features from a date string."""
    try:
        if isinstance(date_str, str):
            # Handle various formats
            for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z",
                        "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(date_str.replace("+00:00", "Z").rstrip("Z") + "Z",
                                           "%Y-%m-%dT%H:%M:%S.%fZ")
                    break
                except (ValueError, AttributeError):
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        break
                    except (ValueError, AttributeError):
                        continue
            else:
                dt = datetime.now(timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
    except Exception:
        dt = datetime.now(timezone.utc)

    hour = dt.hour
    day = dt.weekday()
    return {
        "hour_sin": math.sin(2 * math.pi * hour / 24),
        "hour_cos": math.cos(2 * math.pi * hour / 24),
        "day_of_week": day,
        "is_weekend": 1 if day >= 5 else 0,
    }


def infer_source_type(pick: dict) -> str:
    """Classify source as copy_trader / sentiment / strategy / mixed."""
    source = pick.get("source_system", "").lower()
    strategy = pick.get("strategy", "").lower()

    is_copy = ("copy_trader" in source or "clone_" in strategy or
               "copy_" in strategy or source in ("okx", "bitget", "bybit", "bingx", "gate"))
    is_sentiment = ("sentiment" in source or "coinglass" in source or
                    "htx" in source or "okx_futures" in source or
                    "nansen" in source or "dune" in source)

    if is_copy and is_sentiment:
        return "both"
    elif is_copy:
        return "copy_trader"
    elif is_sentiment:
        return "sentiment"
    return "strategy"


def extract_enrichment_features(pick: dict) -> dict:
    """Extract numerical features from the enrichment block."""
    enrichment = pick.get("enrichment", {})
    features = {}

    # Funding rate
    funding = enrichment.get("funding", {})
    features["funding_rate"] = float(funding.get("last_funding_rate",
                                     funding.get("funding_rate", 0)) or 0)

    # OI change
    oi = enrichment.get("open_interest", {})
    features["oi_change_pct"] = float(oi.get("oi_change_pct",
                                     oi.get("oi_change_percent", 0)) or 0)

    # Fear & Greed
    sentiment = enrichment.get("sentiment", {})
    features["fear_greed_index"] = float(sentiment.get("fear_greed_index", 50) or 50)

    # DVOL / IV
    derivatives = enrichment.get("derivatives", {})
    features["dvol_index"] = float(derivatives.get("dvol_index",
                                   derivatives.get("dvol", 0)) or 0)

    # L/S ratio
    ms = enrichment.get("market_structure", {})
    features["long_short_ratio"] = float(ms.get("long_short_ratio",
                                         ms.get("ls_ratio", 1.0)) or 1.0)

    # Alignment
    features["alignment_score"] = int(enrichment.get("alignment_score", 0) or 0)
    features["contrary_score"] = int(enrichment.get("contrary_score", 0) or 0)

    # RSI
    rsi_data = enrichment.get("rsi", {})
    features["rsi"] = float(rsi_data.get("rsi", rsi_data.get("rsi_14", 50)) or 50)

    # 24h price change
    ticker = enrichment.get("ticker_24h", {})
    features["price_change_24h_pct"] = float(ticker.get("priceChangePercent",
                                             ticker.get("price_change_pct", 0)) or 0)

    return features


def build_feature_vector(pick: dict) -> dict:
    """Build a complete feature vector from a pick dict."""
    features = {}

    # 1. Consensus count
    features["consensus_count"] = int(pick.get("consensus_count", 1) or 1)
    features["cross_exchange"] = 1 if pick.get("cross_exchange_consensus") else 0

    # 2. Enrichment signals
    enrich_feats = extract_enrichment_features(pick)
    features.update(enrich_feats)

    # 3. Source agreement type
    src_type = infer_source_type(pick)
    features["src_copy_trader"] = 1 if src_type in ("copy_trader", "both") else 0
    features["src_sentiment"] = 1 if src_type in ("sentiment", "both") else 0
    features["src_strategy"] = 1 if src_type == "strategy" else 0

    # 4. Symbol category (one-hot)
    cat = categorize_symbol(pick.get("symbol", ""))
    for c in ["large_cap", "alt_l1", "defi", "meme", "other"]:
        features[f"cat_{c}"] = 1 if cat == c else 0

    # 5. Direction
    direction = (pick.get("direction", pick.get("signal_type", "LONG"))).upper()
    features["direction_long"] = 1 if direction in ("BUY", "LONG") else 0

    # 6. Time features
    entry_date = pick.get("entry_date", pick.get("entryDate", pick.get("opened_at", "")))
    time_feats = extract_time_features(str(entry_date))
    features.update(time_feats)

    # 7. Volatility proxy
    features["volatility_24h"] = abs(features.get("price_change_24h_pct", 0))

    # 8. Confidence from source system
    features["source_confidence"] = float(pick.get("confidence",
                                          pick.get("ml_score", 0.5)) or 0.5)

    # 9. Market regime bucket from Fear & Greed
    fg = features.get("fear_greed_index", 50)
    if fg <= 20:
        regime = "extreme_fear"
    elif fg <= 40:
        regime = "fear"
    elif fg <= 60:
        regime = "neutral"
    elif fg <= 80:
        regime = "greed"
    else:
        regime = "extreme_greed"
    for r in ["extreme_fear", "fear", "neutral", "greed", "extreme_greed"]:
        features[f"regime_{r}"] = 1 if regime == r else 0

    # 10. ATR / RSI at entry (from alpha engine closed picks)
    features["atr_at_entry"] = float(pick.get("atr_at_entry", pick.get("atrValue", 0)) or 0)
    features["rsi_at_entry"] = float(pick.get("rsi_at_entry", features.get("rsi", 50)) or 50)

    return features


# Feature names in stable order for the model
FEATURE_NAMES = [
    "consensus_count", "cross_exchange",
    "funding_rate", "oi_change_pct", "fear_greed_index", "dvol_index",
    "long_short_ratio", "alignment_score", "contrary_score",
    "rsi", "price_change_24h_pct",
    "src_copy_trader", "src_sentiment", "src_strategy",
    "cat_large_cap", "cat_alt_l1", "cat_defi", "cat_meme", "cat_other",
    "direction_long",
    "hour_sin", "hour_cos", "day_of_week", "is_weekend",
    "volatility_24h", "source_confidence",
    "regime_extreme_fear", "regime_fear", "regime_neutral",
    "regime_greed", "regime_extreme_greed",
    "atr_at_entry", "rsi_at_entry",
]


def feature_vector_to_list(fv: dict) -> list:
    """Convert feature dict to ordered list matching FEATURE_NAMES."""
    return [float(fv.get(name, 0) or 0) for name in FEATURE_NAMES]


# ======================================================================
# Training Data Loading
# ======================================================================

def load_kimi_closed() -> list:
    """Load closed picks from KIMI live_competition.json."""
    records = []
    comp_file = KIMI_DATA / "live_competition.json"
    if not comp_file.exists():
        print(f"  [META] KIMI data not found at {comp_file}")
        return records

    try:
        with open(comp_file, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [META] Error loading KIMI data: {e}")
        return records

    algorithms = data.get("algorithms", [])
    for algo in algorithms:
        algo_name = algo.get("name", algo.get("id", "unknown"))
        algo_cat = algo.get("category", "crypto")

        for pick in algo.get("closedPicks", []):
            ret_pct = pick.get("returnPct", pick.get("grossReturnPct", 0))
            if ret_pct is None:
                continue

            record = {
                "symbol": pick.get("symbol", ""),
                "direction": pick.get("signal", "BUY"),
                "signal_type": pick.get("signal", "BUY"),
                "strategy": algo_name,
                "source_system": f"kimi_{algo.get('id', 'unknown')}",
                "category": algo_cat,
                "entry_date": pick.get("entryDate", ""),
                "entryDate": pick.get("entryDate", ""),
                "entry_price": pick.get("entryPrice", 0),
                "confidence": pick.get("signalProbability", 50) / 100.0 if pick.get("signalProbability") else 0.5,
                "ml_score": pick.get("signalProbability", 50) / 100.0 if pick.get("signalProbability") else 0.5,
                "consensus_count": pick.get("confluence_count", 1),
                "atr_at_entry": pick.get("atrValue", 0),
                "rsi_at_entry": 50,  # Not stored in KIMI, use neutral default
                "pnl_pct": ret_pct,
                "status": "WON" if ret_pct > 0 else "LOST",
                "exit_reason": pick.get("exitReason", ""),
                "_source_dataset": "kimi",
            }
            records.append(record)

    print(f"  [META] Loaded {len(records)} closed picks from KIMI ({len(algorithms)} algorithms)")
    return records


def load_alpha_closed() -> list:
    """Load closed picks from alpha_engine/data/closed_picks.json."""
    records = []
    closed_file = DATA_DIR / "closed_picks.json"
    if not closed_file.exists():
        print(f"  [META] Alpha closed picks not found at {closed_file}")
        return records

    try:
        with open(closed_file, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [META] Error loading alpha closed picks: {e}")
        return records

    if not isinstance(data, list):
        return records

    for pick in data:
        if not isinstance(pick, dict):
            continue
        status = pick.get("status", "")
        if status not in ("WON", "LOST"):
            continue

        record = pick.copy()
        record["_source_dataset"] = "alpha"
        record.setdefault("direction", pick.get("signal_type", "BUY"))
        record.setdefault("source_system", "alpha_engine")
        record.setdefault("consensus_count", 1)
        records.append(record)

    print(f"  [META] Loaded {len(records)} closed picks from Alpha Engine")
    return records


def load_portfolio_closed() -> list:
    """Load closed positions from portfolio_1x.json."""
    records = []
    for pf_name in ["portfolio_1x.json", "portfolio_20x.json"]:
        pf_file = DATA_DIR / pf_name
        if not pf_file.exists():
            continue

        try:
            with open(pf_file, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [META] Error loading {pf_name}: {e}")
            continue

        closed = data.get("closed_positions", [])
        for pos in closed:
            if not isinstance(pos, dict):
                continue
            pnl = pos.get("pnl_pct", 0)
            if pnl is None:
                continue

            record = {
                "symbol": pos.get("symbol", ""),
                "direction": pos.get("direction", "BUY"),
                "signal_type": pos.get("direction", "BUY"),
                "strategy": pos.get("strategy", "unknown"),
                "source_system": pos.get("source_system", "portfolio"),
                "entry_price": pos.get("entry_price", 0),
                "entry_date": pos.get("opened_at", ""),
                "opened_at": pos.get("opened_at", ""),
                "confidence": pos.get("ml_score_at_entry", 0.5),
                "ml_score": pos.get("ml_score_at_entry", 0.5),
                "consensus_count": 1,
                "pnl_pct": pnl,
                "status": "WON" if pnl > 0 else "LOST",
                "exit_reason": pos.get("close_reason", ""),
                "_source_dataset": f"portfolio_{pf_name.replace('.json', '')}",
            }
            records.append(record)

        if closed:
            print(f"  [META] Loaded {len(closed)} closed positions from {pf_name}")

    return records


def load_all_training_data() -> list:
    """Load and combine all closed trade data."""
    print("\n--- Meta-Learner: Loading Training Data ---")
    all_records = []
    all_records.extend(load_kimi_closed())
    all_records.extend(load_alpha_closed())
    all_records.extend(load_portfolio_closed())
    print(f"  [META] Total training records: {len(all_records)}")
    return all_records


# ======================================================================
# Model: Logistic Regression (from scratch, no sklearn needed)
# ======================================================================

class SimpleLogisticRegression:
    """Pure-Python logistic regression with L2 regularization.
    No external dependencies required.
    """

    def __init__(self, n_features: int, learning_rate: float = 0.01,
                 reg_lambda: float = 0.01, max_iter: int = 2000):
        self.n_features = n_features
        self.lr = learning_rate
        self.reg_lambda = reg_lambda
        self.max_iter = max_iter
        self.weights = [0.0] * n_features
        self.bias = 0.0
        self.feature_means = [0.0] * n_features
        self.feature_stds = [1.0] * n_features
        self.trained = False

    @staticmethod
    def _sigmoid(z: float) -> float:
        z = max(-500, min(500, z))  # clip to avoid overflow
        return 1.0 / (1.0 + math.exp(-z))

    def _standardize(self, X: list) -> list:
        """Standardize features (z-score normalization)."""
        return [
            [(x[i] - self.feature_means[i]) / self.feature_stds[i]
             if self.feature_stds[i] > 1e-10 else 0.0
             for i in range(self.n_features)]
            for x in X
        ]

    def fit(self, X: list, y: list):
        """Train logistic regression with gradient descent."""
        n = len(X)
        if n == 0:
            return

        # Compute feature means and stds for standardization
        for j in range(self.n_features):
            vals = [X[i][j] for i in range(n)]
            mean = sum(vals) / n
            var = sum((v - mean) ** 2 for v in vals) / n
            self.feature_means[j] = mean
            self.feature_stds[j] = math.sqrt(var) if var > 1e-10 else 1.0

        X_std = self._standardize(X)

        for iteration in range(self.max_iter):
            # Forward pass
            predictions = []
            for i in range(n):
                z = self.bias + sum(self.weights[j] * X_std[i][j]
                                    for j in range(self.n_features))
                predictions.append(self._sigmoid(z))

            # Compute gradients
            grad_w = [0.0] * self.n_features
            grad_b = 0.0

            for i in range(n):
                error = predictions[i] - y[i]
                grad_b += error
                for j in range(self.n_features):
                    grad_w[j] += error * X_std[i][j]

            # Update with L2 regularization
            for j in range(self.n_features):
                grad_w[j] = grad_w[j] / n + self.reg_lambda * self.weights[j]
                self.weights[j] -= self.lr * grad_w[j]
            grad_b /= n
            self.bias -= self.lr * grad_b

        self.trained = True

    def predict_proba(self, x: list) -> float:
        """Predict P(win) for a single sample."""
        if not self.trained:
            return 0.5
        x_std = [(x[i] - self.feature_means[i]) / self.feature_stds[i]
                 if self.feature_stds[i] > 1e-10 else 0.0
                 for i in range(self.n_features)]
        z = self.bias + sum(self.weights[j] * x_std[j]
                            for j in range(self.n_features))
        return self._sigmoid(z)

    def predict_proba_batch(self, X: list) -> list:
        """Predict P(win) for a batch."""
        return [self.predict_proba(x) for x in X]

    def get_coefficients(self) -> dict:
        """Return named coefficients (on standardized scale)."""
        return {FEATURE_NAMES[i]: round(self.weights[i], 4)
                for i in range(self.n_features)}

    def to_dict(self) -> dict:
        """Serialize model to dict."""
        return {
            "weights": self.weights,
            "bias": self.bias,
            "feature_means": self.feature_means,
            "feature_stds": self.feature_stds,
            "n_features": self.n_features,
            "trained": self.trained,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SimpleLogisticRegression":
        """Deserialize model from dict."""
        model = cls(n_features=d["n_features"])
        model.weights = d["weights"]
        model.bias = d["bias"]
        model.feature_means = d["feature_means"]
        model.feature_stds = d["feature_stds"]
        model.trained = d["trained"]
        return model


# ======================================================================
# Sklearn Models (optional — used if sklearn is available)
# ======================================================================

def try_sklearn_models(X_train, y_train, X_test, y_test, feature_names):
    """Try sklearn LogisticRegression and GradientBoosting if available."""
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score, roc_auc_score
    except ImportError:
        print("  [META] sklearn not available — using pure-Python model only")
        return None, None

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # Logistic Regression
    lr = LogisticRegression(max_iter=2000, C=1.0, random_state=42)
    lr.fit(X_train_s, y_train)
    lr_pred = lr.predict(X_test_s)
    lr_proba = lr.predict_proba(X_test_s)[:, 1]
    lr_acc = accuracy_score(y_test, lr_pred)
    try:
        lr_auc = roc_auc_score(y_test, lr_proba)
    except ValueError:
        lr_auc = 0.5

    print(f"\n  [SKLEARN] LogisticRegression — Accuracy: {lr_acc:.3f}, AUC: {lr_auc:.3f}")
    print(f"  Coefficient analysis (sklearn LR):")
    coefs = sorted(zip(feature_names, lr.coef_[0]), key=lambda x: abs(x[1]), reverse=True)
    for name, coef in coefs:
        if abs(coef) > 0.01:
            direction = "+" if coef > 0 else ""
            print(f"    {name:30s}: {direction}{coef:.4f}")

    # Gradient Boosting
    gb = GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.1,
                                    random_state=42, min_samples_leaf=10)
    gb.fit(X_train_s, y_train)
    gb_pred = gb.predict(X_test_s)
    gb_proba = gb.predict_proba(X_test_s)[:, 1]
    gb_acc = accuracy_score(y_test, gb_pred)
    try:
        gb_auc = roc_auc_score(y_test, gb_proba)
    except ValueError:
        gb_auc = 0.5

    print(f"\n  [SKLEARN] GradientBoosting — Accuracy: {gb_acc:.3f}, AUC: {gb_auc:.3f}")
    print(f"  Feature importance (top 10):")
    importances = sorted(zip(feature_names, gb.feature_importances_),
                         key=lambda x: x[1], reverse=True)
    for name, imp in importances[:10]:
        print(f"    {name:30s}: {imp:.4f}")

    # Return the better model
    if gb_auc > lr_auc:
        print(f"\n  [META] GradientBoosting wins (AUC {gb_auc:.3f} > {lr_auc:.3f})")
        return gb, scaler
    else:
        print(f"\n  [META] LogisticRegression wins (AUC {lr_auc:.3f} >= {gb_auc:.3f})")
        return lr, scaler


# ======================================================================
# Training Pipeline
# ======================================================================

_model = None
_sklearn_model = None
_sklearn_scaler = None


def train_meta_learner(min_samples: int = 30) -> bool:
    """Train the meta-learner on all available closed trade data."""
    global _model, _sklearn_model, _sklearn_scaler

    records = load_all_training_data()
    if len(records) < min_samples:
        print(f"  [META] Insufficient training data ({len(records)} < {min_samples}) — using heuristic mode")
        return False

    # Build feature vectors and labels
    X = []
    y = []
    skipped = 0

    for record in records:
        try:
            fv = build_feature_vector(record)
            x = feature_vector_to_list(fv)
            label = 1.0 if record.get("status") == "WON" else 0.0
            X.append(x)
            y.append(label)
        except Exception:
            skipped += 1

    if skipped:
        print(f"  [META] Skipped {skipped} records due to feature extraction errors")

    n = len(X)
    if n < min_samples:
        print(f"  [META] Only {n} usable records — need {min_samples}")
        return False

    win_rate = sum(y) / n
    print(f"\n  [META] Training set: {n} trades, win rate: {win_rate:.1%}")
    print(f"         WON: {int(sum(y))}, LOST: {n - int(sum(y))}")

    # Time-based train/test split (80/20) — use chronological order
    split_idx = int(n * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"  [META] Train: {len(X_train)}, Test: {len(X_test)}")

    # Train pure-Python logistic regression
    print(f"\n  [META] Training SimpleLogisticRegression...")
    _model = SimpleLogisticRegression(
        n_features=len(FEATURE_NAMES),
        learning_rate=0.01,
        reg_lambda=0.01,
        max_iter=2000,
    )
    _model.fit(X_train, y_train)

    # Evaluate
    test_preds = _model.predict_proba_batch(X_test)
    correct = sum(1 for pred, actual in zip(test_preds, y_test)
                  if (pred >= 0.5) == (actual >= 0.5))
    accuracy = correct / len(y_test) if y_test else 0
    print(f"  [META] SimpleLogisticRegression — Accuracy: {accuracy:.3f}")

    # Print coefficients
    coefs = _model.get_coefficients()
    sorted_coefs = sorted(coefs.items(), key=lambda x: abs(x[1]), reverse=True)
    print(f"\n  Coefficient analysis (pure-Python LR):")
    for name, coef in sorted_coefs:
        if abs(coef) > 0.01:
            direction = "+" if coef > 0 else ""
            print(f"    {name:30s}: {direction}{coef:.4f}")

    # Try sklearn models
    _sklearn_model, _sklearn_scaler = try_sklearn_models(
        X_train, y_train, X_test, y_test, FEATURE_NAMES
    ) or (None, None)

    # Save model
    model_data = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": n,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "test_accuracy": round(accuracy, 4),
        "win_rate": round(win_rate, 4),
        "feature_names": FEATURE_NAMES,
        "model": _model.to_dict(),
        "coefficients": coefs,
    }
    with open(MODEL_PATH, "w", encoding="utf-8") as f:
        json.dump(model_data, f, indent=2)
    print(f"\n  [META] Model saved to {MODEL_PATH}")

    return True


# ======================================================================
# Scoring (Inference)
# ======================================================================

def load_model():
    """Load a trained model from disk."""
    global _model
    if _model is not None and _model.trained:
        return True

    if not MODEL_PATH.exists():
        return False

    try:
        with open(MODEL_PATH, encoding="utf-8") as f:
            data = json.load(f)
        _model = SimpleLogisticRegression.from_dict(data["model"])
        return _model.trained
    except Exception as e:
        print(f"  [META] Error loading model: {e}")
        return False


def score_single_pick(pick: dict) -> float:
    """Score a single pick with the meta-learner. Returns P(win)."""
    global _model, _sklearn_model, _sklearn_scaler

    fv = build_feature_vector(pick)
    x = feature_vector_to_list(fv)

    # Try sklearn model first (usually better)
    if _sklearn_model is not None and _sklearn_scaler is not None:
        try:
            import numpy as np
            x_arr = np.array([x])
            x_scaled = _sklearn_scaler.transform(x_arr)
            proba = _sklearn_model.predict_proba(x_scaled)[0][1]
            return float(proba)
        except Exception:
            pass

    # Fallback to pure-Python model
    if _model is not None and _model.trained:
        return _model.predict_proba(x)

    # Heuristic fallback: weighted average of available signals
    return _heuristic_score(pick)


def _heuristic_score(pick: dict) -> float:
    """Heuristic scoring when no model is trained.
    Uses a simple weighted combination of available signals.
    """
    score = 0.50  # base

    # Consensus is strong signal
    consensus = pick.get("consensus_count", 1)
    if consensus >= 3:
        score += 0.10
    elif consensus >= 2:
        score += 0.05

    # Cross-exchange consensus is very strong
    if pick.get("cross_exchange_consensus"):
        score += 0.05

    # Source confidence as weak signal
    conf = float(pick.get("confidence", pick.get("ml_score", 0.5)) or 0.5)
    score += (conf - 0.5) * 0.2  # scale confidence contribution

    # Enrichment alignment
    enrichment = pick.get("enrichment", {})
    grade = enrichment.get("context_grade", "")
    if "STRONG_ALIGNMENT" in grade:
        score += 0.08
    elif "MODERATE_ALIGNMENT" in grade:
        score += 0.04
    elif "STRONG_CONTRARY" in grade:
        score -= 0.06

    # Fear & Greed contrarian signal
    fg = float((enrichment.get("sentiment", {}).get("fear_greed_index", 50)) or 50)
    direction = (pick.get("direction", pick.get("signal_type", "LONG"))).upper()
    if fg < 25 and direction in ("BUY", "LONG"):
        score += 0.05  # buying in fear
    elif fg > 75 and direction in ("SHORT", "SELL"):
        score += 0.05  # shorting in greed

    return max(0.01, min(0.99, score))


def score_picks(picks: list, gate: float = 0.55, retrain: bool = True) -> list:
    """
    Score picks with the meta-learner. Re-rank by meta-score.

    Args:
        picks: list of pick dicts (already enriched)
        gate: minimum P(win) threshold to pass
        retrain: if True, retrain model before scoring (if enough data)

    Returns:
        list of picks that pass the gate, sorted by meta_score descending
    """
    if not picks:
        return picks

    print(f"\n--- Meta-Consensus Scorer ---")

    # Train or load model
    model_ready = False
    if retrain:
        model_ready = train_meta_learner(min_samples=30)
    if not model_ready:
        model_ready = load_model()

    if not model_ready:
        print(f"  [META] No trained model — using heuristic scoring")

    # Score all picks
    scored = []
    for pick in picks:
        try:
            meta_score = score_single_pick(pick)
            pick["meta_score"] = round(meta_score, 4)
            pick["meta_model"] = "trained" if (_model and _model.trained) else "heuristic"
            scored.append(pick)
        except Exception as e:
            pick["meta_score"] = 0.5
            pick["meta_model"] = "error"
            scored.append(pick)

    # Apply gate
    pre_gate = len(scored)
    passed = [p for p in scored if p.get("meta_score", 0) >= gate]
    rejected = pre_gate - len(passed)

    # Sort by meta_score descending
    passed.sort(key=lambda p: p.get("meta_score", 0), reverse=True)

    # Summary
    if passed:
        avg_score = sum(p["meta_score"] for p in passed) / len(passed)
        top = passed[0]
        print(f"  [META] Scored {pre_gate} picks, {len(passed)} passed gate (P(win) >= {gate})")
        print(f"  [META] Rejected {rejected} picks below threshold")
        print(f"  [META] Average meta-score: {avg_score:.3f}")
        print(f"  [META] Top pick: {top.get('symbol', '?')} "
              f"(meta_score={top['meta_score']:.3f}, "
              f"strategy={top.get('strategy', '?')})")
    else:
        print(f"  [META] No picks passed the gate (P(win) >= {gate})")
        print(f"  [META] All {pre_gate} picks scored below threshold")

    return passed


# ======================================================================
# Standalone Mode
# ======================================================================

def main():
    """Train the meta-learner and print analysis."""
    print("=" * 70)
    print("  META-CONSENSUS SCORER — Cross-System ML Meta-Learner")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    success = train_meta_learner(min_samples=30)

    if success and _model and _model.trained:
        print("\n" + "=" * 70)
        print("  MODEL TRAINED SUCCESSFULLY")
        print("=" * 70)

        # Load current active picks and score them as a demo
        active_file = COPY_TRADER_DATA / "active_picks.json"
        if active_file.exists():
            try:
                with open(active_file, encoding="utf-8") as f:
                    active = json.load(f)
                if isinstance(active, list) and active:
                    print(f"\n--- Scoring {len(active)} active copy trader picks ---")
                    scored = score_picks(active, gate=0.55, retrain=False)
                    print(f"\n  Passed gate: {len(scored)} / {len(active)} picks")
                    for p in scored[:10]:
                        print(f"    {p.get('symbol', '?'):12s} {p.get('direction', '?'):6s} "
                              f"meta={p['meta_score']:.3f} "
                              f"src={p.get('source_system', '?')} "
                              f"strat={p.get('strategy', '?')}")
            except Exception as e:
                print(f"  [META] Error scoring active picks: {e}")
    else:
        print("\n  [META] Model not trained — will use heuristic mode")
        print("  [META] Heuristic mode uses weighted consensus + enrichment signals")

    print("\n" + "=" * 70)
    print("  DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
