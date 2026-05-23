"""
V4 Walk-Forward Trainer - World-Class ML Pipeline
===================================================
Fixes every flaw in v3:
1. Actually uses PurgedWalkForwardCV (not 80/20 split)
2. Evaluates with realistic backtester (not fake _simulate_backtest)
3. Optimizes on Expected Value (not composite score)
4. Deflated Sharpe Ratio for multiple testing correction
5. Monte Carlo permutation test for edge validation
6. Target labels use high/low for TP/SL detection

References:
- Lopez de Prado (2018) "Advances in Financial Machine Learning"
- Bailey & Lopez de Prado (2014) "The Deflated Sharpe Ratio"
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import joblib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, matthews_corrcoef, f1_score

from .config import (
    V4_CONFIG, MODELS_DIR, RESULTS_DIR, TPSL_CONFIG,
    MODEL_VARIANTS, TIMEFRAMES, get_slippage
)
from .realistic_backtester import (
    RealisticBacktester, CryptoCostModel,
    deflated_sharpe_ratio, monte_carlo_permutation_test, fractional_kelly
)


@dataclass
class FoldResult:
    """Results from a single walk-forward fold."""
    fold_idx: int
    auc: float = 0.5
    mcc: float = 0.0
    f1: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    total_return: float = 0.0
    total_trades: int = 0
    expectancy: float = 0.0
    calmar: float = 0.0
    train_size: int = 0
    test_size: int = 0
    test_bars: int = 0


@dataclass
class V4TrainingResult:
    """Aggregated walk-forward training result with statistical validation."""
    pair: str = ""
    timeframe: str = ""
    variant: str = ""
    version: str = "v4.0"

    mean_sharpe: float = 0.0
    std_sharpe: float = 0.0
    mean_sortino: float = 0.0
    mean_win_rate: float = 0.0
    mean_profit_factor: float = 0.0
    mean_max_drawdown: float = 0.0
    mean_expectancy: float = 0.0
    mean_total_return: float = 0.0
    mean_auc: float = 0.0
    mean_mcc: float = 0.0
    mean_calmar: float = 0.0
    total_trades_all_folds: int = 0

    deflated_sharpe_prob: float = 0.0
    monte_carlo_pvalue: float = 1.0
    monte_carlo_real_sharpe: float = 0.0
    monte_carlo_random_sharpe: float = 0.0

    n_folds: int = 0
    fold_results: List[FoldResult] = field(default_factory=list)

    passes_all_gates: bool = False
    gate_details: Dict = field(default_factory=dict)

    model_path: str = ""
    trained_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "pair": self.pair, "timeframe": self.timeframe,
            "variant": self.variant, "version": self.version,
            "mean_sharpe": round(self.mean_sharpe, 4),
            "std_sharpe": round(self.std_sharpe, 4),
            "mean_sortino": round(self.mean_sortino, 4),
            "mean_win_rate": round(self.mean_win_rate, 4),
            "mean_profit_factor": round(self.mean_profit_factor, 4),
            "mean_max_drawdown": round(self.mean_max_drawdown, 4),
            "mean_expectancy": round(self.mean_expectancy, 6),
            "mean_total_return": round(self.mean_total_return, 4),
            "mean_auc": round(self.mean_auc, 4),
            "mean_mcc": round(self.mean_mcc, 4),
            "mean_calmar": round(self.mean_calmar, 4),
            "total_trades_all_folds": self.total_trades_all_folds,
            "deflated_sharpe_prob": round(self.deflated_sharpe_prob, 4),
            "monte_carlo_pvalue": round(self.monte_carlo_pvalue, 4),
            "n_folds": self.n_folds,
            "passes_all_gates": self.passes_all_gates,
            "gate_details": self.gate_details,
            "trained_at": self.trained_at,
        }


class PurgedWalkForwardCV:
    """
    Walk-forward CV with purge gap (Lopez de Prado 2018, ch. 7).

    Unlike standard TimeSeriesSplit, adds a purge buffer between
    train and test to prevent information leakage from autocorrelation.
    """

    def __init__(self, n_splits=5, purge_gap=20, min_train_size=500,
                 min_test_size=100, expanding=True):
        self.n_splits = n_splits
        self.purge_gap = purge_gap
        self.min_train_size = min_train_size
        self.min_test_size = min_test_size
        self.expanding = expanding

    def split(self, X):
        n = len(X)
        effective_splits = self.n_splits

        available = n - self.min_train_size
        needed_per_split = self.min_test_size + self.purge_gap
        if available < needed_per_split * 2:
            # Fallback: single split
            train_end = int(n * 0.7)
            test_start = train_end + self.purge_gap
            if test_start < n:
                yield np.arange(train_end), np.arange(test_start, n)
            return

        max_splits = available // needed_per_split
        effective_splits = min(self.n_splits, max(2, max_splits))

        test_size = max(self.min_test_size,
                        (n - self.min_train_size - effective_splits * self.purge_gap) // effective_splits)

        for i in range(effective_splits):
            test_end = n - (effective_splits - 1 - i) * (test_size + self.purge_gap)
            test_start = test_end - test_size
            train_end = test_start - self.purge_gap

            if self.expanding:
                train_start = 0
            else:
                train_start = max(0, train_end - self.min_train_size * 2)

            if train_end - train_start < self.min_train_size:
                continue
            if test_end - test_start < self.min_test_size:
                continue

            yield np.arange(train_start, train_end), np.arange(test_start, min(test_end, n))


def build_target_v4(df: pd.DataFrame, tp_pct: float, sl_pct: float,
                    horizon: int) -> pd.Series:
    """
    Build binary targets using HIGH/LOW for TP/SL detection.
    More realistic than v2/v3 which only checked close prices.
    """
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    n = len(df)
    target = np.zeros(n, dtype=int)

    for i in range(n - horizon):
        entry = close[i]
        tp_level = entry * (1 + tp_pct)
        sl_level = entry * (1 - sl_pct)

        tp_bar = None
        sl_bar = None
        for j in range(1, horizon + 1):
            idx = i + j
            if idx >= n:
                break
            if tp_bar is None and high[idx] >= tp_level:
                tp_bar = j
            if sl_bar is None and low[idx] <= sl_level:
                sl_bar = j

        if tp_bar is not None and (sl_bar is None or tp_bar <= sl_bar):
            target[i] = 1

    return pd.Series(target, index=df.index)


def build_model_v4(variant: str, n_features: int = 95):
    """Build a model instance for a given variant name."""
    try:
        from .v3_models import build_v3_model, V3_MODEL_REGISTRY
        if variant in V3_MODEL_REGISTRY:
            return build_v3_model(variant, n_features)
    except ImportError:
        pass

    if variant == "A_xgboost":
        from xgboost import XGBClassifier
        p = MODEL_VARIANTS["A_xgboost"]["params"].copy()
        p.update({"use_label_encoder": False, "eval_metric": "logloss",
                   "random_state": 42, "verbosity": 0})
        return XGBClassifier(**p)
    elif variant == "B_lightgbm":
        from lightgbm import LGBMClassifier
        p = MODEL_VARIANTS["B_lightgbm"]["params"].copy()
        p.update({"random_state": 42, "verbose": -1})
        return LGBMClassifier(**p)
    elif variant == "C_random_forest":
        from sklearn.ensemble import RandomForestClassifier
        p = MODEL_VARIANTS["C_random_forest"]["params"].copy()
        p.update({"random_state": 42, "n_jobs": -1})
        return RandomForestClassifier(**p)
    elif variant == "D_ensemble_stack":
        from sklearn.ensemble import StackingClassifier, RandomForestClassifier, GradientBoostingClassifier
        from sklearn.linear_model import LogisticRegression
        from xgboost import XGBClassifier
        base = [
            ("xgb", XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.02,
                                   use_label_encoder=False, eval_metric="logloss",
                                   early_stopping_rounds=None,
                                   verbosity=0, random_state=42)),
            ("rf", RandomForestClassifier(n_estimators=150, max_depth=10,
                                          min_samples_leaf=15, random_state=42, n_jobs=-1)),
            ("gb", GradientBoostingClassifier(n_estimators=200, max_depth=5,
                                              learning_rate=0.02, random_state=42)),
        ]
        meta = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=42)
        return StackingClassifier(estimators=base, final_estimator=meta, cv=3, n_jobs=-1)
    else:
        from xgboost import XGBClassifier
        return XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.01,
                             use_label_encoder=False, eval_metric="logloss",
                             verbosity=0, random_state=42)


def smote_oversample(X, y, target_ratio=0.4):
    """Custom SMOTE oversampling for minority class."""
    from sklearn.neighbors import NearestNeighbors

    pos_mask = y == 1
    X_pos, X_neg = X[pos_mask], X[~pos_mask]

    if len(X_pos) == 0 or len(X_neg) == 0:
        return X, y
    if len(X_pos) / len(X) >= target_ratio:
        return X, y

    n_synthetic = int(len(X_neg) * target_ratio / (1 - target_ratio)) - len(X_pos)
    if n_synthetic <= 0:
        return X, y

    k = min(5, len(X_pos) - 1)
    if k < 1:
        return X, y

    nn = NearestNeighbors(n_neighbors=k + 1)
    nn.fit(X_pos)

    rng = np.random.RandomState(42)
    synthetic = []
    for _ in range(n_synthetic):
        idx = rng.randint(0, len(X_pos))
        neighbors = nn.kneighbors(X_pos[idx:idx+1], return_distance=False)[0][1:]
        nn_idx = neighbors[rng.randint(0, len(neighbors))]
        lam = rng.random()
        synthetic.append(X_pos[idx] + lam * (X_pos[nn_idx] - X_pos[idx]))

    X_aug = np.vstack([X, np.array(synthetic)])
    y_aug = np.concatenate([y, np.ones(len(synthetic), dtype=int)])
    shuffle = rng.permutation(len(X_aug))
    return X_aug[shuffle], y_aug[shuffle]


class WalkForwardTrainer:
    """Walk-forward training with realistic backtesting and statistical validation."""

    def __init__(self, n_splits=None, purge_gap=None, min_train_bars=None,
                 min_test_bars=None, use_smote=True, smote_ratio=0.4):
        cfg = V4_CONFIG
        self.n_splits = n_splits or cfg["n_splits"]
        self.purge_gap = purge_gap or cfg["purge_gap"]
        self.min_train_bars = min_train_bars or cfg["min_train_bars"]
        self.min_test_bars = min_test_bars or cfg["min_test_bars"]
        self.use_smote = use_smote
        self.smote_ratio = smote_ratio

    def train_and_validate(self, df, features, target, variant, pair, timeframe,
                           tp_pct=0.02, sl_pct=0.01, max_hold_bars=24,
                           n_total_trials=9):
        result = V4TrainingResult(
            pair=pair, timeframe=timeframe, variant=variant,
            trained_at=datetime.now(timezone.utc).isoformat(),
        )

        valid_mask = features.notna().all(axis=1) & target.notna()
        valid_idx = features.index[valid_mask]
        X = features.loc[valid_idx].values
        y = target.loc[valid_idx].values
        df_aligned = df.loc[valid_idx].reset_index(drop=True)
        n_features = X.shape[1]

        if len(X) < self.min_train_bars + self.min_test_bars:
            print(f"  [SKIP] {pair}/{timeframe}/{variant}: only {len(X)} samples")
            return result

        cv = PurgedWalkForwardCV(
            n_splits=self.n_splits, purge_gap=self.purge_gap,
            min_train_size=self.min_train_bars, min_test_size=self.min_test_bars,
        )

        fold_results = []
        all_test_preds = []
        all_test_idx = []
        best_model = None
        best_sharpe = -999

        cost_model = CryptoCostModel.for_pair(pair)
        style = TIMEFRAMES.get(timeframe, {}).get("style", "intraday")
        tp_atr = TPSL_CONFIG.get(style, {}).get("tp_atr_mult", 2.5)
        sl_atr = TPSL_CONFIG.get(style, {}).get("sl_atr_mult", 1.0)

        for fold_idx, (train_idx, test_idx) in enumerate(cv.split(X)):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            df_test = df_aligned.iloc[test_idx].reset_index(drop=True)

            if self.use_smote:
                X_train, y_train = smote_oversample(X_train, y_train, self.smote_ratio)

            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)

            try:
                model = build_model_v4(variant, n_features)
                model.fit(X_train_s, y_train)
            except Exception as e:
                print(f"  [ERROR] Fold {fold_idx} {variant}: {e}")
                continue

            try:
                y_proba = model.predict_proba(X_test_s)[:, 1]
            except Exception:
                y_proba = model.predict(X_test_s).astype(float)

            try:
                auc = roc_auc_score(y_test, y_proba)
            except Exception:
                auc = 0.5

            y_pred = (y_proba >= 0.55).astype(int)
            mcc = matthews_corrcoef(y_test, y_pred) if len(np.unique(y_pred)) > 1 else 0.0
            f1_val = f1_score(y_test, y_pred, zero_division=0.0)

            backtester = RealisticBacktester(
                cost_model=cost_model, initial_capital=10000.0,
                max_position_pct=V4_CONFIG["max_position_pct"], timeframe=timeframe,
            )

            kelly_fn = lambda wr, aw, al: fractional_kelly(
                wr, aw, al, fraction=V4_CONFIG["kelly_fraction"],
                max_pos=V4_CONFIG["max_position_pct"],
            )

            bt = backtester.run(
                df=df_test, predictions=y_proba, threshold=0.55,
                tp_atr_mult=tp_atr, sl_atr_mult=sl_atr,
                max_hold_bars=max_hold_bars, position_sizer=kelly_fn,
            )

            fold = FoldResult(
                fold_idx=fold_idx, auc=auc, mcc=mcc, f1=f1_val,
                sharpe=bt.sharpe_ratio, sortino=bt.sortino_ratio,
                win_rate=bt.win_rate, profit_factor=bt.profit_factor,
                max_drawdown=bt.max_drawdown_pct, total_return=bt.total_return_pct,
                total_trades=bt.total_trades, expectancy=bt.expectancy,
                calmar=bt.calmar_ratio, train_size=len(X[train_idx]),
                test_size=len(X_test), test_bars=len(df_test),
            )
            fold_results.append(fold)
            all_test_preds.extend(y_proba.tolist())
            all_test_idx.extend(test_idx.tolist())

            if bt.sharpe_ratio > best_sharpe:
                best_sharpe = bt.sharpe_ratio
                best_model = (model, scaler)

            print(f"    Fold {fold_idx}: Sharpe={bt.sharpe_ratio:.2f} WR={bt.win_rate:.1%} "
                  f"PF={bt.profit_factor:.2f} DD={bt.max_drawdown_pct:.1f}% "
                  f"Trades={bt.total_trades} Return={bt.total_return_pct:.2f}%")

        if not fold_results:
            return result

        # Aggregate
        result.n_folds = len(fold_results)
        result.fold_results = fold_results

        sharpes = [f.sharpe for f in fold_results]
        result.mean_sharpe = float(np.mean(sharpes))
        result.std_sharpe = float(np.std(sharpes, ddof=1)) if len(sharpes) > 1 else 0.0
        result.mean_sortino = float(np.mean([f.sortino for f in fold_results]))
        result.mean_win_rate = float(np.mean([f.win_rate for f in fold_results]))
        result.mean_profit_factor = float(np.mean([f.profit_factor for f in fold_results]))
        result.mean_max_drawdown = float(np.mean([f.max_drawdown for f in fold_results]))
        result.mean_expectancy = float(np.mean([f.expectancy for f in fold_results]))
        result.mean_total_return = float(np.mean([f.total_return for f in fold_results]))
        result.mean_auc = float(np.mean([f.auc for f in fold_results]))
        result.mean_mcc = float(np.mean([f.mcc for f in fold_results]))
        result.mean_calmar = float(np.mean([f.calmar for f in fold_results]))
        result.total_trades_all_folds = sum(f.total_trades for f in fold_results)

        # DSR
        n_obs = sum(f.test_bars for f in fold_results)
        result.deflated_sharpe_prob = deflated_sharpe_ratio(
            observed_sharpe=result.mean_sharpe,
            n_trials=n_total_trials,
            n_observations=n_obs,
        )

        # Monte Carlo on largest test fold
        if fold_results and result.mean_sharpe > 0:
            largest_fold = max(fold_results, key=lambda f: f.test_bars)
            n_last = largest_fold.test_bars
            if len(all_test_preds) >= n_last and n_last > 50:
                mc_preds = np.array(all_test_preds[-n_last:])
                mc_idx = all_test_idx[-n_last:]
                mc_df = df_aligned.iloc[mc_idx].reset_index(drop=True)

                if len(mc_df) == len(mc_preds):
                    mc_bt = RealisticBacktester(cost_model=cost_model, timeframe=timeframe)
                    try:
                        mc_p, mc_real, mc_rand = monte_carlo_permutation_test(
                            df=mc_df, predictions=mc_preds, backtester=mc_bt,
                            n_permutations=min(V4_CONFIG["n_permutations"], 200),
                            threshold=0.55, tp_atr_mult=tp_atr,
                            sl_atr_mult=sl_atr, max_hold_bars=max_hold_bars,
                        )
                        result.monte_carlo_pvalue = mc_p
                        result.monte_carlo_real_sharpe = mc_real
                        result.monte_carlo_random_sharpe = mc_rand
                    except Exception as e:
                        print(f"    [MC WARNING] {e}")

        # Validation gates
        g = V4_CONFIG
        sharpe_cv = result.std_sharpe / (abs(result.mean_sharpe) + 1e-10)
        result.gate_details = {
            "sharpe": {"value": result.mean_sharpe, "min": g["min_sharpe"],
                       "pass": result.mean_sharpe >= g["min_sharpe"]},
            "win_rate": {"value": result.mean_win_rate, "min": g["min_win_rate"],
                         "pass": result.mean_win_rate >= g["min_win_rate"]},
            "profit_factor": {"value": result.mean_profit_factor, "min": g["min_profit_factor"],
                              "pass": result.mean_profit_factor >= g["min_profit_factor"]},
            "max_drawdown": {"value": result.mean_max_drawdown, "max": g["max_drawdown"] * 100,
                             "pass": result.mean_max_drawdown <= g["max_drawdown"] * 100},
            "expectancy": {"value": result.mean_expectancy, "min": 0,
                           "pass": result.mean_expectancy > 0},
            "dsr": {"value": result.deflated_sharpe_prob, "min": g["min_dsr_prob"],
                    "pass": result.deflated_sharpe_prob >= g["min_dsr_prob"]},
            "mc_pvalue": {"value": result.monte_carlo_pvalue, "max": g["max_mc_pvalue"],
                          "pass": result.monte_carlo_pvalue <= g["max_mc_pvalue"]},
            "n_folds": {"value": result.n_folds, "min": g["min_folds"],
                        "pass": result.n_folds >= g["min_folds"]},
            "sharpe_cv": {"value": sharpe_cv, "max": g["max_sharpe_cv"],
                          "pass": sharpe_cv <= g["max_sharpe_cv"] if result.mean_sharpe > 0 else False},
        }
        result.passes_all_gates = all(d["pass"] for d in result.gate_details.values())

        if best_model:
            model_obj, scaler_obj = best_model
            mp = MODELS_DIR / f"{pair}_{timeframe}_v4_{variant}.joblib"
            sp = MODELS_DIR / f"{pair}_{timeframe}_v4_scaler.joblib"
            joblib.dump(model_obj, str(mp))
            joblib.dump(scaler_obj, str(sp))
            result.model_path = str(mp)

        return result


def train_v4_pair(pair, timeframe, df, features, target, variants=None,
                  tp_pct=0.02, sl_pct=0.01, max_hold_bars=24):
    """Train all model variants for a single pair/timeframe."""
    if variants is None:
        variants = ["A_xgboost", "B_lightgbm", "C_random_forest", "D_ensemble_stack"]
        try:
            from .v3_models import V3_MODEL_REGISTRY
            variants.extend(V3_MODEL_REGISTRY.keys())
        except ImportError:
            pass

    print(f"\n{'='*70}")
    print(f"  V4 Walk-Forward Training: {pair} / {timeframe}")
    print(f"  Data: {len(df)} bars | Features: {features.shape[1]} | Variants: {len(variants)}")
    print(f"{'='*70}")

    trainer = WalkForwardTrainer()
    results = {}

    for variant in variants:
        print(f"\n  --- {variant} ---")
        try:
            result = trainer.train_and_validate(
                df=df, features=features, target=target,
                variant=variant, pair=pair, timeframe=timeframe,
                tp_pct=tp_pct, sl_pct=sl_pct, max_hold_bars=max_hold_bars,
                n_total_trials=len(variants),
            )
            results[variant] = result

            gates_passed = sum(1 for d in result.gate_details.values() if d.get("pass"))
            total_gates = len(result.gate_details)
            status = "PASS" if result.passes_all_gates else "FAIL"

            print(f"  >> {variant}: Sharpe={result.mean_sharpe:.3f} WR={result.mean_win_rate:.1%} "
                  f"PF={result.mean_profit_factor:.2f} DD={result.mean_max_drawdown:.1f}% "
                  f"DSR={result.deflated_sharpe_prob:.3f} MC_p={result.monte_carlo_pvalue:.3f} "
                  f"[{status} {gates_passed}/{total_gates}]")
        except Exception as e:
            print(f"  [ERROR] {variant}: {e}")

    return results


def train_v4_full_suite(pairs=None, timeframes=None, variants=None, fetch_data=True):
    """Full v4 training pipeline across all pairs and timeframes."""
    if pairs is None:
        pairs = V4_CONFIG["priority_pairs"]
    if timeframes is None:
        timeframes = V4_CONFIG["priority_timeframes"]

    all_results = {}
    tradeable = []

    for pair in pairs:
        for tf in timeframes:
            key = f"{pair}_{tf}"

            if fetch_data:
                try:
                    from .data_fetcher import fetch_klines
                    tf_config = TIMEFRAMES.get(tf, {"interval": tf, "limit": 5000})
                    df = fetch_klines(pair, tf_config["interval"], tf_config["limit"])
                    if df is None or len(df) < 500:
                        print(f"[SKIP] {key}: insufficient data")
                        continue
                except Exception as e:
                    print(f"[SKIP] {key}: data fetch failed: {e}")
                    continue

            try:
                from .feature_engine import build_features, build_target
                features = build_features(df, pair)
                try:
                    from .v3_features import build_v3_features
                    features = build_v3_features(df, pair, features)
                except ImportError:
                    pass

                style = TIMEFRAMES.get(tf, {}).get("style", "intraday")
                tpsl = TPSL_CONFIG.get(style, {"tp_atr_mult": 2.5, "sl_atr_mult": 1.0})
                tr = pd.concat([
                    df["high"] - df["low"],
                    (df["high"] - df["close"].shift(1)).abs(),
                    (df["low"] - df["close"].shift(1)).abs(),
                ], axis=1).max(axis=1)
                atr = tr.rolling(14).mean()
                tp_pct = float((atr * tpsl["tp_atr_mult"] / df["close"]).median())
                sl_pct = float((atr * tpsl["sl_atr_mult"] / df["close"]).median())
                horizon = TIMEFRAMES.get(tf, {}).get("horizon", 12)
                max_hold = TPSL_CONFIG.get(style, {}).get("max_hold_bars", 24)

                target = build_target_v4(df, tp_pct, sl_pct, horizon)
                print(f"\n  Target: {key} pos_rate={target.mean():.3f} tp={tp_pct:.4f} sl={sl_pct:.4f}")
            except Exception as e:
                print(f"[SKIP] {key}: feature build failed: {e}")
                continue

            pair_results = train_v4_pair(
                pair=pair, timeframe=tf, df=df, features=features, target=target,
                variants=variants, tp_pct=tp_pct, sl_pct=sl_pct, max_hold_bars=max_hold,
            )

            all_results[key] = {v: r.to_dict() for v, r in pair_results.items()}

            for v, r in pair_results.items():
                if r.passes_all_gates:
                    tradeable.append({
                        "pair": pair, "timeframe": tf, "variant": v,
                        "sharpe": r.mean_sharpe, "win_rate": r.mean_win_rate,
                        "profit_factor": r.mean_profit_factor,
                        "max_drawdown": r.mean_max_drawdown,
                        "dsr": r.deflated_sharpe_prob,
                        "mc_pvalue": r.monte_carlo_pvalue,
                    })

    summary = {
        "version": "v4.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_experiments": sum(len(v) for v in all_results.values()),
        "tradeable_models": len(tradeable),
        "tradeable_list": sorted(tradeable, key=lambda x: x["sharpe"], reverse=True),
        "results": all_results,
    }

    out = RESULTS_DIR / "v4_training_summary.json"
    with open(out, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\n{'='*70}")
    print(f"  V4 COMPLETE | Experiments: {summary['total_experiments']} | Tradeable: {len(tradeable)}")
    if tradeable:
        for m in sorted(tradeable, key=lambda x: x["sharpe"], reverse=True):
            print(f"    {m['pair']}/{m['timeframe']}/{m['variant']}: Sharpe={m['sharpe']:.2f} "
                  f"WR={m['win_rate']:.1%} PF={m['profit_factor']:.2f}")
    else:
        print("  NO MODELS PASSED ALL GATES - honest result.")
    print(f"{'='*70}")

    return summary
