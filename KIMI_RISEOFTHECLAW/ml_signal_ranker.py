"""
ml_signal_ranker.py -- KIMI Rise of the Claw v11.0
Random Forest Signal Ranking Engine

Learns which algorithms/symbols/regimes produce winning trades.
- Warm-start heuristic mode when < 50 closed picks
- Auto-trains RF model when >= 50 closed picks
- Injects win_probability weights into live_scanner.py all_data dict
- Outputs: data/ml_weights.json, data/rf_model.pkl, data/ml_training_stats.json
"""

import json
import logging
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
MODEL_PATH = DATA_DIR / "rf_model.pkl"
WEIGHTS_PATH = DATA_DIR / "ml_weights.json"
STATS_PATH = DATA_DIR / "ml_training_stats.json"

MIN_SAMPLES_FOR_ML = 50  # Below this, use heuristic
MIN_SAMPLES_PER_CLASS = 5  # Minimum wins AND losses for training
MIN_AUC_FOR_ML = 0.55  # Minimum CV AUC to use ML predictions

# Category encoding
CAT_MAP = {"stock": 0, "crypto": 1, "meme": 2, "penny": 3, "forex": 4}
TIER_MAP = {"TIER_1": 1, "SCOUT": 0}
REGIME_MAP = {"bull": 1, "neutral": 0, "bear": -1}
CRYPTO_REGIME_MAP = {"risk_on": 1, "neutral": 0, "defensive": -1}

# Top symbols to encode (rest -> 99)
TOP_SYMBOLS = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
    "AVAX-USD",
    "BNB-USD",
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "META",
    "GOOGL",
    "AMZN",
    "SPY",
    "QQQ",
    "DOGE-USD",
    "SHIB-USD",
    "PEPE-USD",
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "LINK-USD",
    "XRP-USD",
    "ADA-USD",
    "MATIC-USD",
]
SYM_MAP = {sym: i for i, sym in enumerate(TOP_SYMBOLS)}


def _encode_symbol(sym: str) -> int:
    return SYM_MAP.get(sym, 99)


class MLSignalRanker:
    """
    Two-mode signal ranker:
    1. Heuristic mode (< 50 closed picks): weights based on tournament Sharpe + WR + tier
    2. ML mode (>= 50 closed picks): RandomForest trained on closed pick features
    """

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.model_path = self.data_dir / "rf_model.pkl"
        self.weights_path = self.data_dir / "ml_weights.json"
        self.stats_path = self.data_dir / "ml_training_stats.json"
        self.model = None
        self.is_trained = False
        self.cv_auc = 0.0  # Track AUC of loaded/trained model
        self.weights: dict = {}
        self._load_or_train()

    def _load_existing_model(self) -> bool:
        """Try to load a previously trained model and its AUC stats."""
        try:
            import joblib
            if self.model_path.exists():
                self.model = joblib.load(self.model_path)
                self.is_trained = True
                # Load AUC from training stats if available
                if self.stats_path.exists():
                    try:
                        with open(self.stats_path) as f:
                            stats = json.load(f)
                        self.cv_auc = stats.get("cv_auc_mean", 0.0)
                    except Exception:
                        pass
                logger.info(f"Loaded existing RF model from disk (AUC={self.cv_auc:.3f})")
                return True
        except Exception as e:
            logger.debug(f"Could not load model: {e}")
        return False

    def _load_closed_picks(self) -> pd.DataFrame:
        """Extract all closed picks from live_competition.json."""
        comp_path = self.data_dir / "live_competition.json"
        if not comp_path.exists():
            return pd.DataFrame()
        try:
            with open(comp_path) as f:
                comp = json.load(f)
        except Exception:
            return pd.DataFrame()
        records = []
        for algo in comp.get("algorithms", []):
            algo_id = algo.get("id", "")
            category = algo.get("category", "stock")
            tier = algo.get("tier", "SCOUT")
            for pick in algo.get("closedPicks", []):
                # Derive status from exitReason/pnl if no explicit status field
                status = pick.get("status", "")
                if not status or status == "OPEN":
                    exit_reason = (pick.get("exitReason") or "").upper()
                    pnl = pick.get("pnl", pick.get("pnl_pct", 0)) or 0
                    if "TAKE_PROFIT" in exit_reason:
                        status = "WON"
                    elif "STOP_LOSS" in exit_reason:
                        status = "LOST"
                    elif "EXPIRED" in exit_reason or "MAX_HOLD" in exit_reason:
                        status = "WON" if pnl > 0 else "LOST"
                    elif pick.get("exitDate"):
                        # Has an exit date = closed trade, derive from PnL
                        status = "WON" if pnl > 0 else "LOST"
                    else:
                        continue  # Truly unclosed, skip
                if status not in ("WON", "LOST", "EXPIRED"):
                    continue
                # Use returnPct (percentage) if available, fall back to pnl_pct
                pnl_pct = pick.get("returnPct", pick.get("grossReturnPct",
                          pick.get("pnl_pct", 0))) or 0
                records.append({
                    "algo_id": algo_id,
                    "symbol": pick.get("symbol", ""),
                    "category": category,
                    "tier": tier,
                    "entry_price": pick.get("entryPrice", 0),
                    "exit_price": pick.get("currentPrice", pick.get("exitPrice", 0)),
                    "pnl_pct": pnl_pct,
                    "status": status,
                    "won": 1 if status == "WON" else 0,
                    "reason": pick.get("reason", ""),
                    "algo_drought": algo.get("droughtScans", 0),
                    # v11.7: ML market-context features (stored at entry time)
                    "rsi_at_entry": pick.get("rsi_at_entry"),
                    "volume_ratio": pick.get("volume_ratio"),
                    "fear_greed": pick.get("fear_greed"),
                    "risk_reward": pick.get("risk_reward", pick.get("riskReward")),
                    "hour_of_day": pick.get("hour_of_day"),
                    "btc_24h_change": pick.get("btc_24h_change", pick.get("btcChange24h")),
                    # Also pass through entry time and prices for _extract_market_context fallback
                    "entryPrice": pick.get("entryPrice", 0),
                    "targetPrice": pick.get("targetPrice", 0),
                    "stopPrice": pick.get("stopPrice", 0),
                    "entryDate": pick.get("entryDate", ""),
                })
        return pd.DataFrame(records)

    def _load_tournament_stats(self) -> dict:
        """Load current tournament scores per algo."""
        t_path = self.data_dir / "tournament.json"
        if not t_path.exists():
            return {}
        try:
            with open(t_path) as f:
                t = json.load(f)
            stats = {}
            for r in t.get("rankings", []):
                stats[r["id"]] = {
                    "score": r.get("score", 46.0),
                    "sharpe": r.get("sharpe", 0.0),
                    "win_rate": r.get("winRate", 50.0) / 100,
                    "closed_picks": r.get("closedPicks", 0),
                    "kelly": r.get("kellyFraction", 0.0),
                    "tier": r.get("tier", "SCOUT"),
                    "category": r.get("category", "stock"),
                    "drought": r.get("droughtScans", 0),
                }
            return stats
        except Exception:
            return {}

    def _load_regime_cache(self) -> dict:
        """Load current market regime."""
        cache_paths = [
            self.data_dir.parent.parent / "STOCKS" / "competition" / ".regime_cache.json",
            Path("STOCKS/competition/.regime_cache.json"),
        ]
        for p in cache_paths:
            if p.exists():
                try:
                    with open(p) as f:
                        return json.load(f)
                except Exception:
                    pass
        return {"regime": "neutral", "crypto_regime": "neutral",
                "hmm_confidence": 0.5, "vol_20d": 0.01}

    # Canonical feature order — dead features removed (regime_enc, crypto_regime_enc,
    # hmm_confidence, vol_20d, btc_eth_ratio all had 0.0 importance in RF)
    # v11.1: Added 6 market-context features per Grok recommendation
    FEATURE_COLS = [
        "algo_id_enc", "category_enc", "symbol_enc", "tier_enc",
        "algo_wr", "algo_sharpe", "algo_drought", "algo_closed", "algo_kelly",
        "rsi_at_entry", "volume_ratio", "fear_greed", "risk_reward",
        "hour_of_day", "btc_24h_change",
    ]

    @staticmethod
    def _extract_market_context(pick: dict) -> dict:
        """Extract 6 market-context features from a pick/signal dict.

        All features are normalized to [0, 1] (or [-1, 1] for btc_24h_change).
        Uses sensible defaults when data is missing.
        """
        # RSI at entry — normalize /100
        rsi_raw = pick.get("rsi", pick.get("rsi_at_entry", pick.get("RSI", 50.0)))
        rsi_at_entry = min(max(float(rsi_raw or 50.0), 0.0), 100.0) / 100.0

        # Volume ratio — cap at 10, normalize /10
        vol_raw = pick.get("volume_ratio", pick.get("volumeRatio", pick.get("volRatio", 1.0)))
        volume_ratio = min(max(float(vol_raw or 1.0), 0.0), 10.0) / 10.0

        # Fear & Greed index — normalize /100
        fg_raw = pick.get("fear_greed", pick.get("fearGreed", pick.get("fg_index", 50.0)))
        fear_greed = min(max(float(fg_raw or 50.0), 0.0), 100.0) / 100.0

        # Risk/reward ratio from TP/SL distances
        entry = float(pick.get("entryPrice", pick.get("entry_price", 0)) or 0)
        tp = float(pick.get("targetPrice", pick.get("target_price", 0)) or 0)
        sl = float(pick.get("stopPrice", pick.get("stop_price", 0)) or 0)
        if entry > 0 and sl > 0 and abs(entry - sl) > 1e-10:
            rr_raw = abs(tp - entry) / abs(entry - sl) if tp > 0 else 1.5
        else:
            rr_raw = 1.5
        risk_reward = min(max(rr_raw, 0.0), 5.0) / 5.0

        # Hour of day (UTC) — normalize /23
        entry_time = pick.get("entryTime", pick.get("entryDate", pick.get("timestamp", "")))
        hour = 12  # default
        if entry_time:
            try:
                if isinstance(entry_time, str) and len(entry_time) >= 13:
                    dt = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
                    hour = dt.hour
                elif isinstance(entry_time, (int, float)):
                    dt = datetime.fromtimestamp(entry_time, tz=timezone.utc)
                    hour = dt.hour
            except Exception:
                pass
        hour_of_day = hour / 23.0

        # BTC 24h change — cap [-20, 20], normalize /20 to [-1, 1]
        btc_raw = pick.get("btc_24h_change", pick.get("btc24hChange", pick.get("btcChange24h", 0.0)))
        btc_clamped = min(max(float(btc_raw or 0.0), -20.0), 20.0)
        btc_24h_change = btc_clamped / 20.0

        return {
            "rsi_at_entry": round(rsi_at_entry, 4),
            "volume_ratio": round(volume_ratio, 4),
            "fear_greed": round(fear_greed, 4),
            "risk_reward": round(risk_reward, 4),
            "hour_of_day": round(hour_of_day, 4),
            "btc_24h_change": round(btc_24h_change, 4),
        }

    def _build_features(self, df: pd.DataFrame, tournament_stats: dict) -> pd.DataFrame:
        """Build feature matrix from closed picks."""
        features = []
        for _, row in df.iterrows():
            algo_stats = tournament_stats.get(row["algo_id"], {})
            feat = {
                "algo_id_enc": hash(row["algo_id"]) % 1000,
                "category_enc": CAT_MAP.get(row["category"], 0),
                "symbol_enc": _encode_symbol(row["symbol"]),
                "tier_enc": TIER_MAP.get(row["tier"], 0),
                "algo_wr": algo_stats.get("win_rate", 0.5),
                "algo_sharpe": min(algo_stats.get("sharpe", 0.0), 5.0),
                "algo_drought": row.get("algo_drought", 0),
                "algo_closed": algo_stats.get("closed_picks", 0),
                "algo_kelly": algo_stats.get("kelly", 0.0),
            }
            # Market-context features (use row dict which has pick-level data)
            feat.update(self._extract_market_context(row.to_dict()))
            features.append(feat)
        return pd.DataFrame(features)[self.FEATURE_COLS]

    def train_if_ready(self) -> bool:
        """Train RF model if enough closed picks available.

        IMPORTANT: If a valid model is already loaded (self.is_trained=True),
        we still attempt retraining to refresh with latest data, but we NEVER
        reset is_trained or overwrite ML weights on failure -- the existing
        model remains valid.
        """
        had_model = self.is_trained and self.model is not None
        df = self._load_closed_picks()
        if len(df) < MIN_SAMPLES_FOR_ML:
            if had_model:
                # Model already loaded from disk -- don't destroy it just
                # because closed picks file was temporarily unavailable
                logger.info(f"ML ranker: keeping loaded RF model (closed picks "
                            f"file returned {len(df)} rows, model AUC={self.cv_auc:.3f})")
                return True
            logger.info(f"ML ranker: heuristic mode ({len(df)} closed picks, need {MIN_SAMPLES_FOR_ML})")
            self.is_trained = False
            self._compute_heuristic_weights()
            return False
        wins = int(df["won"].sum())
        losses = len(df) - wins
        if wins < MIN_SAMPLES_PER_CLASS or losses < MIN_SAMPLES_PER_CLASS:
            if had_model:
                logger.info(f"ML ranker: keeping loaded RF model (class imbalance "
                            f"wins={wins}, losses={losses} but model AUC={self.cv_auc:.3f})")
                return True
            logger.info(f"ML ranker: class imbalance (wins={wins}, losses={losses}), using heuristic")
            self._compute_heuristic_weights()
            return False
        return self._train_model(df, had_model)

    def _train_model(self, df: pd.DataFrame, had_prior_model: bool = False) -> bool:
        """Train RandomForest on closed picks + optional mega dataset augmentation."""
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import cross_val_score, TimeSeriesSplit
            import joblib
            t_stats = self._load_tournament_stats()
            X = self._build_features(df, t_stats)
            y = df["won"].values
            n_live = len(y)

            # --- Mega dataset augmentation ---
            sample_weights = np.ones(len(y))  # Live data weight = 1.0
            mega_samples = 0
            try:
                from mega_data_bridge import load_mega_training_data
                mega_df = load_mega_training_data(max_samples=5000)
                if len(mega_df) > 0:
                    mega_feature_cols = self.FEATURE_COLS
                    X_mega = mega_df[mega_feature_cols]
                    y_mega = mega_df["won"].values
                    w_mega = mega_df["source_weight"].values * 0.5  # Halve mega weights
                    X = pd.concat([X, X_mega], ignore_index=True)
                    y = np.concatenate([y, y_mega])
                    sample_weights = np.concatenate([sample_weights, w_mega])
                    mega_samples = len(y_mega)
                    mega_wins = int(y_mega.sum())
                    print(f"  [MEGA] Augmented training: {n_live} live + {mega_samples} mega "
                          f"= {len(y)} total ({mega_wins}W/{mega_samples - mega_wins}L from mega)")
            except Exception as e:
                print(f"  [MEGA] Augmentation skipped: {e}")

            wins = int(y.sum())
            feature_names = list(X.columns)
            tscv = TimeSeriesSplit(n_splits=5)

            # --- Fix 3: Optuna hyperparameter tuning ---
            best_params = {'n_estimators': 500, 'max_depth': 8, 'min_samples_leaf': 3}
            optuna_ran = False
            try:
                import optuna
                optuna.logging.set_verbosity(optuna.logging.WARNING)

                def objective(trial):
                    params = {
                        'n_estimators': trial.suggest_int('n_estimators', 200, 800),
                        'max_depth': trial.suggest_int('max_depth', 4, 12),
                        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 2, 10),
                        'min_samples_split': trial.suggest_int('min_samples_split', 3, 15),
                        'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', 0.5, 0.7]),
                    }
                    rf = RandomForestClassifier(**params, class_weight='balanced', random_state=42, n_jobs=-1)
                    scores = cross_val_score(rf, X, y, cv=tscv, scoring='roc_auc')
                    return scores.mean()

                study = optuna.create_study(direction='maximize')
                study.optimize(objective, n_trials=15, timeout=60)  # 15 trials, max 60 seconds
                best_params = study.best_params
                print(f"  [OPTUNA] Best params: {best_params} (AUC: {study.best_value:.4f})")
                optuna_ran = True
                optuna_best_auc = study.best_value
            except ImportError:
                print("  [OPTUNA] optuna not installed, using default params")
            except Exception as e:
                print(f"  [OPTUNA] Tuning failed: {e}, using defaults")

            model = RandomForestClassifier(
                **best_params,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
            # TimeSeriesSplit prevents look-ahead bias in trading data. Fixed 2026-03-13
            cv_scores = cross_val_score(model, X, y, cv=tscv, scoring="roc_auc")
            avg_auc = cv_scores.mean()

            # Check AUC threshold before accepting the model
            if avg_auc < MIN_AUC_FOR_ML:
                logger.warning(f"RF AUC {avg_auc:.3f} below threshold {MIN_AUC_FOR_ML}, "
                               f"{'keeping prior model' if had_prior_model else 'using heuristic'}")
                if not had_prior_model:
                    self._compute_heuristic_weights()
                return had_prior_model

            # Train/test split for SHAP and permutation importance analysis
            from sklearn.model_selection import train_test_split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y if wins >= 5 else None
            )

            model.fit(X, y, sample_weight=sample_weights)  # Final model trained on ALL data
            self.model = model
            self.is_trained = True
            self.cv_auc = avg_auc
            self.data_dir.mkdir(parents=True, exist_ok=True)
            joblib.dump(model, self.model_path)
            feat_importance = dict(zip(feature_names, model.feature_importances_.tolist()))
            training_stats = {
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "n_samples": len(y),
                "n_live_samples": n_live,
                "n_mega_samples": mega_samples,
                "n_wins": int(y.sum()),
                "n_losses": int(len(y) - y.sum()),
                "cv_auc_mean": round(float(avg_auc), 4),
                "cv_auc_std": round(float(cv_scores.std()), 4),
                "feature_importances": feat_importance,
                "mode": "random_forest",
            }
            if optuna_ran:
                training_stats['optuna_best_params'] = best_params
                training_stats['optuna_best_auc'] = round(float(optuna_best_auc), 4)

            # --- Fix 1: SHAP feature importance ---
            try:
                import shap
                explainer = shap.TreeExplainer(model)
                shap_values = explainer.shap_values(X_test)
                if isinstance(shap_values, list):
                    shap_values = shap_values[1]  # For binary classification, use class 1
                mean_abs_shap = np.abs(shap_values).mean(axis=0)
                shap_feature_importance = dict(zip(feature_names, mean_abs_shap))
                # Log top features
                sorted_features = sorted(shap_feature_importance.items(), key=lambda x: -x[1])
                print(f"  [SHAP] Top features: {[(f, round(v,4)) for f,v in sorted_features[:5]]}")
                # Save to training stats
                training_stats['shap_importance'] = {f: round(float(v), 6) for f, v in sorted_features}
            except ImportError:
                print("  [SHAP] shap not installed, using Gini importance")
            except Exception as e:
                print(f"  [SHAP] Failed: {e}")

            # --- Fix 2: Permutation importance ---
            try:
                from sklearn.inspection import permutation_importance
                perm_result = permutation_importance(model, X_test, y_test, n_repeats=10, random_state=42, n_jobs=-1)
                perm_imp = dict(zip(feature_names, perm_result.importances_mean))
                sorted_perm = sorted(perm_imp.items(), key=lambda x: -x[1])
                print(f"  [PERM] Top features: {[(f, round(v,4)) for f,v in sorted_perm[:5]]}")
                # Features with negative importance can be dropped
                droppable = [f for f, v in perm_imp.items() if v < 0]
                if droppable:
                    print(f"  [PERM] DROPPABLE features (negative importance): {droppable}")
                training_stats['permutation_importance'] = {f: round(float(v), 6) for f, v in sorted_perm}
            except Exception as e:
                print(f"  [PERM] Permutation importance failed: {e}")

            with open(self.stats_path, "w") as f:
                json.dump(training_stats, f, indent=2)
            logger.info(f"RF model trained: {len(df)} samples, AUC={avg_auc:.3f}")
            self._compute_ml_weights(t_stats)
            return True
        except Exception as e:
            logger.warning(f"RF training failed: {e}")
            if had_prior_model:
                # Keep the existing model -- don't overwrite ML weights
                logger.info("Keeping previously loaded RF model after training failure")
            else:
                logger.info("No prior model, falling back to heuristic weights")
                self._compute_heuristic_weights()
            return had_prior_model

    def _compute_heuristic_weights(self):
        """Heuristic weights based on Sharpe + WR + tier (no ML)."""
        t_stats = self._load_tournament_stats()
        weights = {}
        for algo_id, stats in t_stats.items():
            tier = stats.get("tier", "")
            tier_bonus = 0.25 if tier == "TIER_1" else (-0.05 if tier == "SCOUT" else 0.0)
            wr = stats.get("win_rate", 0.5)
            sharpe = min(stats.get("sharpe", 0.0), 3.0) / 3.0
            drought = stats.get("drought", 0)
            drought_pen = min(drought * 0.01, 0.2)  # Penalize droughts
            score = 0.5 + (wr - 0.5) * 0.4 + sharpe * 0.3 + tier_bonus - drought_pen
            weights[algo_id] = {"overall": round(min(max(score, 0.1), 0.95), 3), "mode": "heuristic"}
        self.weights = weights
        self._save_weights(weights)

    def _build_single_feature_row(self, algo_id: str, algo_stats: dict,
                                   symbol: str = "",
                                   pick: Optional[dict] = None) -> pd.DataFrame:
        """Build a single feature row for prediction (shared by _compute_ml_weights and predict_win_probability)."""
        feat_row = {
            "algo_id_enc": hash(algo_id) % 1000,
            "category_enc": CAT_MAP.get(algo_stats.get("category", "stock"), 0),
            "symbol_enc": _encode_symbol(symbol) if symbol else 99,
            "tier_enc": TIER_MAP.get(algo_stats.get("tier", "SCOUT"), 0),
            "algo_wr": algo_stats.get("win_rate", 0.5),
            "algo_sharpe": min(algo_stats.get("sharpe", 0.0), 5.0),
            "algo_drought": algo_stats.get("drought", 0),
            "algo_closed": algo_stats.get("closed_picks", 0),
            "algo_kelly": algo_stats.get("kelly", 0.0),
        }
        # Market-context features from the pick dict (defaults used when no pick)
        feat_row.update(self._extract_market_context(pick or {}))
        return pd.DataFrame([feat_row])[self.FEATURE_COLS]

    def _compute_ml_weights(self, t_stats: dict):
        """Compute per-algo ML win probabilities using trained RF model.

        Only called when self.model is trained and valid. Uses
        model.predict_proba() to generate per-algorithm win probabilities.
        """
        if self.model is None:
            logger.warning("_compute_ml_weights called but model is None, falling back to heuristic")
            self._compute_heuristic_weights()
            return

        weights = {}
        errors = 0
        for algo_id in t_stats:
            algo_stats = t_stats.get(algo_id, {})
            X = self._build_single_feature_row(algo_id, algo_stats)
            try:
                prob = float(self.model.predict_proba(X)[0][1])
                weights[algo_id] = {"overall": round(prob, 3), "mode": "random_forest"}
            except Exception:
                weights[algo_id] = {"overall": 0.5, "mode": "error"}
                errors += 1

        if errors > 0:
            logger.warning(f"ML weight prediction errors for {errors}/{len(t_stats)} algorithms")

        if not weights:
            # t_stats was empty (tournament.json missing) -- don't save empty weights
            logger.warning("No algorithms in tournament stats, skipping ML weight save")
            return

        self.weights = weights
        self._save_weights(weights)

    def _save_weights(self, weights: dict):
        """Save weights to data/ml_weights.json."""
        # Determine mode from actual per-algo weights, not just self.is_trained
        ml_count = sum(1 for w in weights.values() if w.get("mode") == "random_forest")
        heuristic_count = sum(1 for w in weights.values() if w.get("mode") == "heuristic")
        if ml_count > 0 and ml_count >= heuristic_count:
            top_mode = "random_forest"
        else:
            top_mode = "heuristic"

        out = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "mode": top_mode,
            "cv_auc": round(self.cv_auc, 4) if self.cv_auc else None,
            "algo_weights": weights,
        }
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.weights_path, "w") as f:
            json.dump(out, f, indent=2)

    def _load_or_train(self):
        """Load existing model or compute weights.

        Flow:
        1. Try loading model from disk (rf_model.pkl)
        2. If loaded successfully AND AUC > threshold: compute ML weights
        3. If no model on disk: train_if_ready() (which trains or falls back to heuristic)
        """
        if self._load_existing_model():
            if self.cv_auc >= MIN_AUC_FOR_ML:
                t_stats = self._load_tournament_stats()
                if t_stats:
                    self._compute_ml_weights(t_stats)
                    logger.info(f"ML weights computed from loaded model "
                                f"(AUC={self.cv_auc:.3f}, {len(self.weights)} algos)")
                else:
                    logger.warning("Model loaded but tournament.json empty, using heuristic")
                    self._compute_heuristic_weights()
            else:
                logger.info(f"Loaded model AUC {self.cv_auc:.3f} below threshold "
                            f"{MIN_AUC_FOR_ML}, using heuristic")
                self._compute_heuristic_weights()
        else:
            self.train_if_ready()

    def get_weights(self) -> dict:
        """Return current weights dict for injection into all_data.

        If weights are empty (e.g. tournament.json was missing), recompute
        using whatever mode is available. Does NOT blindly fall back to
        heuristic if ML model is loaded.
        """
        if not self.weights:
            if self.is_trained and self.model is not None and self.cv_auc >= MIN_AUC_FOR_ML:
                t_stats = self._load_tournament_stats()
                if t_stats:
                    self._compute_ml_weights(t_stats)
            if not self.weights:
                # Still empty -- fall back to heuristic
                self._compute_heuristic_weights()
        return self.weights

    def get_allocation_multiplier(self, algo_id: str) -> float:
        """Return allocation multiplier based on ML win probability (0.5x - 1.5x)."""
        weights = self.get_weights()
        prob = weights.get(algo_id, {}).get("overall", 0.5)
        multiplier = 0.5 + prob  # prob=0.5 -> 1.0x, prob=0.8 -> 1.3x, prob=0.3 -> 0.8x
        return round(min(max(multiplier, 0.5), 1.5), 2)

    def predict_win_probability(self, features: dict) -> float:
        """Predict win probability for a single pick.

        Args:
            features: dict with keys 'algorithm', 'symbol', 'confidence', 'regime'
                      (as passed from live_scanner.py)

        Returns:
            float 0.0-1.0 win probability
        """
        algo_id = features.get("algorithm", "")
        symbol = features.get("symbol", "")
        confidence = float(features.get("confidence", 50))

        # If RF model is trained, use it
        if self.is_trained and self.model is not None:
            t_stats = self._load_tournament_stats()
            algo_stats = t_stats.get(algo_id, {})
            X = self._build_single_feature_row(algo_id, algo_stats, symbol=symbol, pick=features)
            try:
                prob = float(self.model.predict_proba(X)[0][1])
                return min(max(prob, 0.0), 1.0)
            except Exception as e:
                logger.debug(f"RF predict failed for {algo_id}: {e}, using heuristic")

        # Heuristic fallback: combine confidence + tournament stats
        t_stats = self._load_tournament_stats()
        algo_stats = t_stats.get(algo_id, {})
        wr = algo_stats.get("win_rate", 0.5)
        sharpe = min(algo_stats.get("sharpe", 0.0), 3.0) / 3.0
        tier = algo_stats.get("tier", "SCOUT")
        tier_bonus = 0.1 if tier == "TIER_1" else 0.0
        conf_norm = confidence / 100.0
        # Weighted blend: 30% confidence, 40% win rate, 20% sharpe, 10% tier
        score = 0.3 * conf_norm + 0.4 * wr + 0.2 * sharpe + tier_bonus
        return min(max(round(score, 4), 0.0), 1.0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("MLSignalRanker -- testing...")
    ranker = MLSignalRanker()
    weights = ranker.get_weights()
    mode = "random_forest" if ranker.is_trained else "heuristic"
    print(f"Mode: {mode}")
    print(f"CV AUC: {ranker.cv_auc:.4f}")
    print(f"Algorithms weighted: {len(weights)}")
    if weights:
        ml_count = sum(1 for w in weights.values() if w.get("mode") == "random_forest")
        heur_count = sum(1 for w in weights.values() if w.get("mode") == "heuristic")
        print(f"  ML weights: {ml_count}, Heuristic weights: {heur_count}")
        top = sorted(weights.items(), key=lambda x: x[1].get("overall", 0), reverse=True)[:5]
        print("Top 5 by win probability:")
        for algo_id, w_item in top:
            ov = w_item.get("overall", 0)
            wmode = w_item.get("mode", "?")
            print(f"  {algo_id}: {ov:.3f} ({wmode})")
    print(f"Weights saved to {WEIGHTS_PATH}")
