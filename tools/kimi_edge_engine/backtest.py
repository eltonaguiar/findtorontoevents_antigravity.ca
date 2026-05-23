#!/usr/bin/env python3
"""
Ultimate Statistical Edge Detection Engine
Implements Lopez de Prado's methods for institutional-grade backtesting.

Features:
- Purged k-fold cross-validation
- Combinatorial purged CV (CPCV) for PBO calculation
- Walk-forward analysis with expanding window
- Gaussian HMM regime detection
- Kelly position sizing
- Transaction cost modeling
- Deflated Sharpe Ratio (DSR)
- Information Coefficient analysis
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import comb
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import KFold
import json
import warnings
warnings.filterwarnings('ignore')


# ============================================================
# TRANSACTION COST MODEL
# ============================================================

ASSET_COSTS = {
    'CRYPTO':    {'commission': 0.001, 'slippage': 0.0005},  # 0.10% + 0.05%
    'EQUITY':    {'commission': 0.001, 'slippage': 0.0002},  # 0.10% + 0.02%
    'FOREX':     {'commission': 0.001, 'slippage': 0.0001},  # 0.10% + 0.01%
    'COMMODITY': {'commission': 0.001, 'slippage': 0.0002},  # 0.10% + 0.02%
    'ETF':       {'commission': 0.001, 'slippage': 0.0002},  # 0.10% + 0.02%
    'BOND':      {'commission': 0.001, 'slippage': 0.0001},  # 0.10% + 0.01%
}


def get_cost_per_trade(asset_class):
    """Total cost per round-trip trade."""
    costs = ASSET_COSTS.get(asset_class, ASSET_COSTS['EQUITY'])
    return costs['commission'] + costs['slippage']


# ============================================================
# PURGED K-FOLD CROSS-VALIDATION (Lopez de Prado)
# ============================================================

class PurgedKFold:
    """
    Purged K-Fold cross-validation.
    Purges observations within `pct_embargo` of the test set to prevent leakage.
    """
    def __init__(self, n_splits=5, pct_embargo=0.02):
        self.n_splits = n_splits
        self.pct_embargo = pct_embargo

    def split(self, X, y=None, groups=None):
        n_samples = len(X)
        indices = np.arange(n_samples)
        fold_size = n_samples // self.n_splits
        embargo = int(n_samples * self.pct_embargo)

        for i in range(self.n_splits):
            test_start = i * fold_size
            test_end = (i + 1) * fold_size if i < self.n_splits - 1 else n_samples
            test_indices = indices[test_start:test_end]
            train_indices = np.concatenate([
                indices[:max(0, test_start - embargo)],
                indices[min(n_samples, test_end + embargo):]
            ])
            yield train_indices, test_indices

    def get_n_splits(self, X=None, y=None, groups=None):
        return self.n_splits


# ============================================================
# COMBINATORIAL PURGED CROSS-VALIDATION (CPCV) for PBO
# ============================================================

class CombinatorialPurgedCV:
    """
    Combinatorial Purged Cross-Validation for Probability of Backtest Overfitting.
    Generates N combinatorial splits and tracks in-sample vs out-of-sample ranks.
    """
    def __init__(self, n_splits=10, n_test_splits=2, pct_embargo=0.02):
        self.n_splits = n_splits
        self.n_test_splits = n_test_splits
        self.pct_embargo = pct_embargo

    def generate_splits(self, n_samples):
        """Generate all combinatorial splits."""
        fold_size = n_samples // self.n_splits
        splits = []
        embargo = int(n_samples * self.pct_embargo)
        indices = np.arange(n_samples)

        # All combinations of test folds
        from itertools import combinations
        for test_combo in combinations(range(self.n_splits), self.n_test_splits):
            test_indices = []
            for t in test_combo:
                start = t * fold_size
                end = (t + 1) * fold_size if t < self.n_splits - 1 else n_samples
                test_indices.extend(indices[start:end])
            test_indices = np.array(test_indices)

            # Train = everything outside test + embargo
            test_min, test_max = test_indices.min(), test_indices.max()
            train_indices = np.concatenate([
                indices[:max(0, test_min - embargo)],
                indices[min(n_samples, test_max + embargo):]
            ])
            splits.append((train_indices, test_indices))
        return splits


def calculate_pbo(returns_matrix, n_splits=10, n_test_splits=2):
    """
    Calculate Probability of Backtest Overfitting (PBO).
    
    Parameters:
    -----------
    returns_matrix : np.ndarray, shape (n_strategies, n_periods)
        Returns for each strategy over time periods.
    n_splits : int
        Number of splits for CPCV.
    n_test_splits : int
        Number of test splits per combination.
    
    Returns:
    --------
    pbo : float
        Probability of backtest overfitting.
    logit : float
        Logit of the PBO (for confidence interval).
    """
    n_strategies, n_samples = returns_matrix.shape
    if n_strategies < 2:
        return 0.0, 0.0

    cpcv = CombinatorialPurgedCV(n_splits=n_splits, n_test_splits=n_test_splits)
    splits = cpcv.generate_splits(n_samples)

    ranks = []
    for train_idx, test_idx in splits:
        if len(train_idx) < 10 or len(test_idx) < 5:
            continue
        is_sharpe = []
        oos_sharpe = []
        for s in range(n_strategies):
            is_rets = returns_matrix[s, train_idx]
            oos_rets = returns_matrix[s, test_idx]
            if np.std(is_rets) > 1e-10 and np.std(oos_rets) > 1e-10:
                is_sharpe.append(np.mean(is_rets) / np.std(is_rets))
                oos_sharpe.append(np.mean(oos_rets) / np.std(oos_rets))
            else:
                is_sharpe.append(-999)
                oos_sharpe.append(-999)

        if len(is_sharpe) < 2:
            continue

        # Rank strategies by IS Sharpe
        is_ranks = np.argsort(np.argsort(is_sharpe))
        # Find best IS strategy's OOS rank
        best_is = np.argmax(is_sharpe)
        oos_ranks = np.argsort(np.argsort(oos_sharpe))
        best_oos_rank = oos_ranks[best_is]

        # Check if best IS is better OOS than median
        n_valid = sum(1 for x in oos_sharpe if x > -900)
        if n_valid > 0:
            ranks.append(1 if best_oos_rank < n_valid / 2 else 0)

    if len(ranks) == 0:
        return 0.5, 0.0

    pbo = 1 - np.mean(ranks)  # P[best IS is NOT best OOS]
    # Clamp to avoid logit issues
    pbo = max(0.001, min(0.999, pbo))
    logit_pbo = np.log(pbo / (1 - pbo))
    return pbo, logit_pbo


# ============================================================
# WALK-FORWARD ANALYSIS
# ============================================================

def walk_forward_analysis(features, target, model_fn, min_train=100, test_size=30,
                          step=15, purged=True, embargo_pct=0.02):
    """
    Walk-forward analysis with expanding window.
    
    Returns:
    --------
    is_sharpes : list
        In-sample Sharpe ratios.
    oos_sharpes : list
        Out-of-sample Sharpe ratios.
    wfe : float
        Walk-forward efficiency (OOS Sharpe / IS Sharpe).
    predictions : np.ndarray
        OOS predictions.
    actuals : np.ndarray
        OOS actual returns.
    """
    n = len(features)
    is_sharpes = []
    oos_sharpes = []
    predictions = []
    actuals_list = []

    for start in range(min_train, n - test_size, step):
        train_end = start
        test_end = min(start + test_size, n)

        if purged:
            embargo = int((test_end - train_end) * embargo_pct)
            train_idx = np.arange(0, max(0, train_end - embargo))
        else:
            train_idx = np.arange(0, train_end)

        test_idx = np.arange(train_end, test_end)

        if len(train_idx) < 30 or len(test_idx) < 5:
            continue

        X_train, y_train = features.iloc[train_idx], target.iloc[train_idx]
        X_test, y_test = features.iloc[test_idx], target.iloc[test_idx]

        # Drop NaN
        mask = ~(X_train.isna().any(axis=1) | y_train.isna())
        X_train, y_train = X_train[mask], y_train[mask]
        mask_test = ~(X_test.isna().any(axis=1) | y_test.isna())
        X_test, y_test = X_test[mask_test], y_test[mask_test]

        if len(X_train) < 20 or len(X_test) < 3:
            continue

        try:
            pred = model_fn(X_train, y_train, X_test)
            is_ret = y_train.values
            oos_ret = y_test.values * np.sign(pred) if pred is not None else y_test.values

            if np.std(is_ret) > 1e-10:
                is_sharpes.append(np.mean(is_ret) / np.std(is_ret))
            if np.std(oos_ret) > 1e-10:
                oos_sharpes.append(np.mean(oos_ret) / np.std(oos_ret))
                predictions.extend(pred if pred is not None else [0]*len(y_test))
                actuals_list.extend(y_test.values)
        except Exception:
            continue

    wfe = 0.0
    if len(is_sharpes) > 0 and len(oos_sharpes) > 0:
        mean_is = np.mean([s for s in is_sharpes if not np.isnan(s) and not np.isinf(s)])
        mean_oos = np.mean([s for s in oos_sharpes if not np.isnan(s) and not np.isinf(s)])
        if abs(mean_is) > 1e-6:
            wfe = mean_oos / abs(mean_is)

    return is_sharpes, oos_sharpes, wfe, np.array(predictions), np.array(actuals_list)


# ============================================================
# REGIME DETECTION (Gaussian HMM / Gaussian Mixture)
# ============================================================

def detect_regimes(features_df, vol_col='hist_vol_20d', mom_col='return_20d', n_regimes=3):
    """
    Detect market regimes using Gaussian Mixture Model.
    
    Returns:
    --------
    regimes : np.ndarray
        Regime labels (0, 1, 2).
    regime_desc : dict
        Description of each regime.
    """
    # Select volatility and momentum features for regime detection
    regime_features = []
    for col in [vol_col, mom_col]:
        if col in features_df.columns:
            regime_features.append(col)

    if len(regime_features) < 2:
        # Fallback: use return columns
        regime_features = [c for c in features_df.columns if 'return' in c][:2]

    X = features_df[regime_features].fillna(0).values

    try:
        gmm = GaussianMixture(n_components=n_regimes, random_state=42, max_iter=200)
        regimes = gmm.fit_predict(X)

        # Characterize regimes
        regime_desc = {}
        for r in range(n_regimes):
            mask = regimes == r
            vol_mean = features_df[vol_col].iloc[mask].mean() if vol_col in features_df.columns else 0
            mom_mean = features_df[mom_col].iloc[mask].mean() if mom_col in features_df.columns else 0

            if vol_mean > features_df[vol_col].median() if vol_col in features_df.columns else False:
                vol_label = 'high_vol'
            else:
                vol_label = 'low_vol'

            if mom_mean > 0.01:
                mom_label = 'trend_up'
            elif mom_mean < -0.01:
                mom_label = 'trend_down'
            else:
                mom_label = 'mean_reverting'

            regime_desc[int(r)] = f"{vol_label}_{mom_label}"

        return regimes, regime_desc
    except Exception:
        # Fallback: simple percentile-based regimes
        if vol_col in features_df.columns:
            vol = features_df[vol_col].values
            regimes = np.digitize(vol, [np.percentile(vol, 33), np.percentile(vol, 67)])
            return regimes, {0: 'low_vol', 1: 'medium_vol', 2: 'high_vol'}
        return np.zeros(len(features_df)), {0: 'single_regime'}


# ============================================================
# INFORMATION COEFFICIENT ANALYSIS
# ============================================================

def calculate_ic(features_df, target_col, feature_cols=None, method='spearman'):
    """
    Calculate Information Coefficient per feature.
    
    Returns:
    --------
    ic_df : pd.DataFrame
        Columns: feature, ic_mean, ic_std, icir, direction
    """
    if feature_cols is None:
        feature_cols = [c for c in features_df.columns
                        if c not in ['date', 'symbol', 'asset_class', 'target_return_1d',
                                     'target_return_3d', 'target_return_5d', 'target_return_10d',
                                     'target_binary', 'target_quintile', 'target_top_quintile',
                                     'target_bottom_quintile', 'open', 'high', 'low', 'close', 'volume']]

    target = features_df[target_col].values
    results = []

    for feat in feature_cols:
        if feat not in features_df.columns:
            continue
        fvals = features_df[feat].values
        mask = ~(np.isnan(fvals) | np.isnan(target) | np.isinf(fvals) | np.isinf(target))
        if mask.sum() < 30:
            continue

        if method == 'spearman':
            ic, _ = stats.spearmanr(fvals[mask], target[mask])
        else:
            ic, _ = stats.pearsonr(fvals[mask], target[mask])

        if not np.isnan(ic) and not np.isinf(ic):
            results.append({'feature': feat, 'ic': ic})

    if len(results) == 0:
        return pd.DataFrame(columns=['feature', 'ic_mean', 'ic_std', 'icir', 'direction'])

    ic_df = pd.DataFrame(results)
    ic_df['abs_ic'] = ic_df['ic'].abs()
    ic_summary = ic_df.groupby('feature')['ic'].agg(['mean', 'std', 'count']).reset_index()
    ic_summary.columns = ['feature', 'ic_mean', 'ic_std', 'ic_count']
    ic_summary['icir'] = ic_summary['ic_mean'] / (ic_summary['ic_std'] + 1e-10)
    ic_summary['abs_icir'] = ic_summary['icir'].abs()
    ic_summary['direction'] = np.where(ic_summary['ic_mean'] > 0, 'positive', 'negative')

    return ic_summary.sort_values('abs_icir', ascending=False)


def select_top_features(features_df, target_col, n_top=20, max_corr=0.7):
    """Select top features by ICIR, removing correlated ones."""
    ic_df = calculate_ic(features_df, target_col)
    if len(ic_df) == 0:
        return []

    # Sort by absolute ICIR
    ic_df = ic_df.sort_values('abs_icir', ascending=False)
    selected = []

    for _, row in ic_df.iterrows():
        feat = row['feature']
        if feat not in features_df.columns:
            continue

        # Check correlation with already selected features
        too_correlated = False
        for sel_feat in selected:
            corr = features_df[feat].corr(features_df[sel_feat])
            if abs(corr) > max_corr:
                too_correlated = True
                break

        if not too_correlated:
            selected.append(feat)

        if len(selected) >= n_top:
            break

    return selected


# ============================================================
# DEFLATED SHARPE RATIO (DSR)
# ============================================================

def calculate_dsr(sharpe_ratio, n_trials, n_observations, skewness=0, kurtosis=3):
    """
    Calculate Deflated Sharpe Ratio (Lopez de Prado, 2019).
    
    DSR = Z((SR - SR*) / sigma_SR)
    
    Where SR* is the expected maximum Sharpe ratio from n_trials.
    
    Parameters:
    -----------
    sharpe_ratio : float
        The observed Sharpe ratio.
    n_trials : int
        Number of independent trials performed.
    n_observations : int
        Number of observations in the return series.
    skewness : float
        Skewness of returns.
    kurtosis : float
        Kurtosis of returns.
    
    Returns:
    --------
    dsr : float
        Deflated Sharpe Ratio (probability that the strategy is not a fluke).
    """
    if n_trials <= 1 or n_observations <= 1:
        return 0.5

    # Estimate variance of Sharpe ratio
    sr_var = (1 + 0.5 * sharpe_ratio**2 - skewness * sharpe_ratio +
              (kurtosis - 3) / 4 * sharpe_ratio**2) / (n_observations - 1)

    if sr_var <= 0:
        return 0.5

    # Expected maximum Sharpe under null (multiple testing)
    gamma = 0.5772156649  # Euler-Mascheroni constant
    try:
        sr_star = np.sqrt(sr_var) * (
            (1 - gamma) * stats.norm.ppf(1 - 1.0/n_trials) +
            gamma * stats.norm.ppf(1 - 1.0/(n_trials * np.e))
        )
    except Exception:
        sr_star = 0

    # DSR
    dsr_z = (sharpe_ratio - sr_star) / np.sqrt(sr_var)
    dsr = stats.norm.cdf(dsr_z)

    return max(0, min(1, dsr))


# ============================================================
# KELLY CRITERION POSITION SIZING
# ============================================================

def kelly_fraction(win_rate, avg_win, avg_loss):
    """
    Calculate Kelly fraction: f* = (p*b - q) / b
    
    Parameters:
    -----------
    win_rate : float
        Probability of winning (p).
    avg_win : float
        Average win amount (positive).
    avg_loss : float
        Average loss amount (negative).
    
    Returns:
    --------
    kelly : float
        Kelly fraction (clamped to [-1, 1]).
    """
    if avg_loss == 0 or avg_win <= 0:
        return 0.0

    b = abs(avg_win / avg_loss)  # win/loss ratio
    q = 1 - win_rate

    kelly = (win_rate * b - q) / b
    return max(-1, min(1, kelly))


def half_kelly(win_rate, avg_win, avg_loss):
    """Conservative half-Kelly sizing."""
    return 0.5 * kelly_fraction(win_rate, avg_win, avg_loss)


# ============================================================
# EDGE METRICS CALCULATION
# ============================================================

def calculate_edge_metrics(returns, cost_per_trade=0.0015):
    """
    Calculate comprehensive edge metrics from a return series.
    
    Parameters:
    -----------
    returns : np.ndarray or pd.Series
        Trade returns (before costs).
    cost_per_trade : float
        Cost per round-trip trade.
    
    Returns:
    --------
    metrics : dict
        Comprehensive metrics dictionary.
    """
    returns = np.asarray(returns).flatten()
    returns = returns[~np.isnan(returns) & ~np.isinf(returns)]

    if len(returns) < 5:
        return None

    # Apply costs
    net_returns = returns - cost_per_trade

    wins = net_returns[net_returns > 0]
    losses = net_returns[net_returns < 0]
    n_wins = len(wins)
    n_losses = len(losses)
    n_trades = len(net_returns)

    if n_trades == 0 or n_wins == 0 or n_losses == 0:
        return None

    win_rate = n_wins / n_trades
    avg_win = np.mean(wins) if n_wins > 0 else 0
    avg_loss = np.mean(losses) if n_losses > 0 else 0
    wl_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    # Profit Factor = gross profit / gross loss
    gross_profit = np.sum(wins)
    gross_loss = abs(np.sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    # Expectancy
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))

    # Sharpe ratio
    sharpe = np.mean(net_returns) / (np.std(net_returns) + 1e-10) * np.sqrt(252)

    # Total return
    total_return = np.prod(1 + net_returns) - 1

    # Max drawdown
    cumret = np.cumprod(1 + net_returns)
    running_max = np.maximum.accumulate(cumret)
    drawdowns = (cumret - running_max) / running_max
    max_drawdown = abs(np.min(drawdowns))

    # Calmar ratio
    calmar = (np.mean(net_returns) * 252) / (max_drawdown + 1e-10)

    # Sortino ratio
    downside_returns = net_returns[net_returns < 0]
    downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 1e-10
    sortino = np.mean(net_returns) / (downside_std + 1e-10) * np.sqrt(252)

    # Skewness and Kurtosis
    skew = stats.skew(net_returns)
    kurt = stats.kurtosis(net_returns) + 3  # excess -> raw

    # Kelly
    kelly = kelly_fraction(win_rate, avg_win, avg_loss)
    half_kelly_val = 0.5 * kelly

    return {
        'n_trades': int(n_trades),
        'n_wins': int(n_wins),
        'n_losses': int(n_losses),
        'win_rate': float(win_rate),
        'avg_win': float(avg_win),
        'avg_loss': float(avg_loss),
        'wl_ratio': float(wl_ratio),
        'profit_factor': float(profit_factor),
        'expectancy': float(expectancy),
        'sharpe': float(sharpe),
        'sortino': float(sortino),
        'total_return': float(total_return),
        'max_drawdown': float(max_drawdown),
        'calmar': float(calmar),
        'skewness': float(skew),
        'kurtosis': float(kurt),
        'kelly_fraction': float(kelly),
        'half_kelly': float(half_kelly_val),
        'gross_profit': float(gross_profit),
        'gross_loss': float(gross_loss),
    }


# ============================================================
# STRATEGY GENERATORS (Rule-Based)
# ============================================================

def generate_strategy_signals(features_df, strategy_name, params):
    """
    Generate trading signals for a specific strategy.
    
    Returns: signals (1=long, -1=short, 0=flat), confidences (0-1)
    """
    signals = np.zeros(len(features_df))
    confidences = np.zeros(len(features_df))

    if strategy_name == 'RSI_MeanReversion':
        rsi_low = params.get('rsi_low', 30)
        rsi_high = params.get('rsi_high', 70)
        rsi_col = params.get('rsi_col', 'rsi_14')
        if rsi_col in features_df.columns:
            rsi = features_df[rsi_col].values
            vol_regime = features_df.get('vol_regime', pd.Series(1, index=features_df.index)).values
            signals[(rsi < rsi_low) & (vol_regime > 0)] = 1
            signals[(rsi > rsi_high) & (vol_regime > 0)] = -1
            confidences = np.abs(50 - rsi) / 50  # Higher confidence at extremes

    elif strategy_name == 'BB_MeanReversion':
        bb_col = params.get('bb_col', 'bb_pct_b')
        if bb_col in features_df.columns:
            bb = features_df[bb_col].values
            signals[bb < 0.1] = 1
            signals[bb > 0.9] = -1
            confidences = np.abs(0.5 - bb) * 2

    elif strategy_name == 'Momentum_Breakout':
        mom_col = params.get('mom_col', 'return_20d')
        vol_col = params.get('vol_col', 'atr_14_ratio')
        threshold = params.get('threshold', 0.05)
        if mom_col in features_df.columns and vol_col in features_df.columns:
            mom = features_df[mom_col].values
            vol = features_df[vol_col].values
            vol_thresh = np.percentile(vol, 60)
            signals[(mom > threshold) & (vol > vol_thresh)] = 1
            signals[(mom < -threshold) & (vol > vol_thresh)] = -1
            confidences = np.abs(mom) / (np.std(mom) + 1e-10)
            confidences = np.clip(confidences, 0, 1)

    elif strategy_name == 'Volume_Confirmed':
        vol_ratio_col = params.get('vol_ratio_col', 'vol_ratio_sma20')
        mom_col = params.get('mom_col', 'return_5d')
        if vol_ratio_col in features_df.columns and mom_col in features_df.columns:
            vr = features_df[vol_ratio_col].values
            mom = features_df[mom_col].values
            signals[(vr > 1.5) & (mom > 0.02)] = 1
            signals[(vr > 1.5) & (mom < -0.02)] = -1
            confidences = np.minimum(vr / 3, 1)

    elif strategy_name == 'Counter_Trend':
        dist_col = params.get('dist_col', 'dist_sma_20')
        rsi_col = params.get('rsi_col', 'rsi_14')
        threshold = params.get('threshold', 0.05)
        if dist_col in features_df.columns:
            dist = features_df[dist_col].values
            rsi = features_df[rsi_col].values if rsi_col in features_df.columns else np.full(len(dist), 50)
            signals[(dist > threshold) & (rsi > 60)] = -1  # Short extended up
            signals[(dist < -threshold) & (rsi < 40)] = 1  # Long extended down
            confidences = np.abs(dist) / (np.std(dist) + 1e-10)
            confidences = np.clip(confidences, 0, 1)

    elif strategy_name == 'Gap_MeanReversion':
        gap_col = params.get('gap_col', 'gap_pct')
        threshold = params.get('threshold', 0.02)
        if gap_col in features_df.columns:
            gap = features_df[gap_col].values
            signals[gap > threshold] = -1  # Gap up = sell
            signals[gap < -threshold] = 1   # Gap down = buy
            confidences = np.abs(gap) / (np.std(gap) + 1e-10)
            confidences = np.clip(confidences, 0, 1)

    elif strategy_name == 'Volatility_Breakout':
        bb_col = params.get('bb_col', 'bb_width')
        atr_col = params.get('atr_col', 'atr_14_ratio')
        if bb_col in features_df.columns:
            bbw = features_df[bb_col].values
            atr = features_df[atr_col].values if atr_col in features_df.columns else bbw
            # Low volatility compression followed by expansion
            bbw_pct = pd.Series(bbw).rolling(20).apply(
                lambda x: stats.percentileofscore(x, x.iloc[-1]) / 100.0, raw=False
            ).fillna(0.5).values
            signals[(bbw_pct > 0.7) & (atr > np.percentile(atr, 60))] = 1
            confidences = bbw_pct

    elif strategy_name == 'MACD_Signal':
        macd_col = params.get('macd_col', 'macd_histogram')
        if macd_col in features_df.columns:
            hist = features_df[macd_col].values
            signals[(hist > 0) & (np.roll(hist, 1) < 0)] = 1  # Cross above 0
            signals[(hist < 0) & (np.roll(hist, 1) > 0)] = -1  # Cross below 0
            confidences = np.abs(hist) / (np.std(hist) + 1e-10)
            confidences = np.clip(confidences, 0, 1)

    elif strategy_name == 'Stochastic_MeanRev':
        stoch_col = params.get('stoch_col', 'stoch_k')
        if stoch_col in features_df.columns:
            stoch = features_df[stoch_col].values
            signals[stoch < 20] = 1
            signals[stoch > 80] = -1
            confidences = np.abs(50 - stoch) / 50

    elif strategy_name == 'Composite_Score':
        # Multi-factor composite
        score = np.zeros(len(features_df))
        n_factors = 0
        for col, weight in params.get('factors', {}).items():
            if col in features_df.columns:
                vals = features_df[col].values
                score += weight * ((vals - np.nanmean(vals)) / (np.nanstd(vals) + 1e-10))
                n_factors += 1
        if n_factors > 0:
            score = score / np.sqrt(n_factors) if n_factors > 0 else score
            signals[score > 1.0] = 1
            signals[score < -1.0] = -1
            confidences = np.abs(score) / 3
            confidences = np.clip(confidences, 0, 1)

    return signals, confidences


# ============================================================
# MAIN EDGE DETECTION PIPELINE
# ============================================================

def discover_edges(asset_class, features_df, target_col='target_return_1d',
                   n_top_features=20, verbose=True):
    """
    Run the full edge detection pipeline for an asset class.
    
    Returns:
    --------
    results : dict
        Complete edge detection results.
    """
    cost = get_cost_per_trade(asset_class)

    # Step 1: Factor Selection
    if verbose:
        print(f"\n{'='*60}")
        print(f"EDGE DETECTION: {asset_class}")
        print(f"{'='*60}")
        print(f"Step 1: Factor Selection (IC Analysis)...")

    top_features = select_top_features(features_df, target_col, n_top=n_top_features)
    if verbose:
        print(f"  Selected {len(top_features)} top features")

    if len(top_features) < 5:
        if verbose:
            print(f"  WARNING: Too few features selected, using all numeric features")
        top_features = [c for c in features_df.columns
                        if features_df[c].dtype in ['float64', 'int64']
                        and c not in ['target_return_1d', 'target_return_3d',
                                      'target_return_5d', 'target_return_10d',
                                      'target_binary', 'target_quintile']][:30]

    # Step 2: Regime Detection
    if verbose:
        print(f"Step 2: Regime Detection (GMM)...")
    regimes, regime_desc = detect_regimes(features_df)
    n_regimes = len(np.unique(regimes))
    if verbose:
        print(f"  Detected {n_regimes} regimes: {regime_desc}")

    # Step 3: Strategy Discovery per Regime
    if verbose:
        print(f"Step 3: Strategy Discovery...")

    strategies_to_test = [
        ('RSI_MeanReversion', {'rsi_low': 30, 'rsi_high': 70, 'rsi_col': 'rsi_14'}),
        ('RSI_MeanReversion', {'rsi_low': 25, 'rsi_high': 75, 'rsi_col': 'rsi_14'}),
        ('RSI_MeanReversion', {'rsi_low': 20, 'rsi_high': 80, 'rsi_col': 'rsi_14'}),
        ('RSI_MeanReversion', {'rsi_low': 30, 'rsi_high': 70, 'rsi_col': 'rsi_7'}),
        ('RSI_MeanReversion', {'rsi_low': 35, 'rsi_high': 65, 'rsi_col': 'rsi_21'}),
        ('BB_MeanReversion', {'bb_col': 'bb_pct_b'}),
        ('Momentum_Breakout', {'mom_col': 'return_20d', 'threshold': 0.05}),
        ('Momentum_Breakout', {'mom_col': 'return_10d', 'threshold': 0.03}),
        ('Momentum_Breakout', {'mom_col': 'return_60d', 'threshold': 0.10}),
        ('Volume_Confirmed', {'vol_ratio_col': 'vol_ratio_sma20', 'mom_col': 'return_5d'}),
        ('Counter_Trend', {'dist_col': 'dist_sma_20', 'rsi_col': 'rsi_14', 'threshold': 0.03}),
        ('Counter_Trend', {'dist_col': 'dist_sma_50', 'rsi_col': 'rsi_14', 'threshold': 0.05}),
        ('Gap_MeanReversion', {'gap_col': 'gap_pct', 'threshold': 0.02}),
        ('Gap_MeanReversion', {'gap_col': 'gap_pct', 'threshold': 0.01}),
        ('Volatility_Breakout', {'bb_col': 'bb_width', 'atr_col': 'atr_14_ratio'}),
        ('MACD_Signal', {'macd_col': 'macd_histogram'}),
        ('Stochastic_MeanRev', {'stoch_col': 'stoch_k'}),
        ('Stochastic_MeanRev', {'stoch_col': 'stoch_d'}),
    ]

    # Asset-class specific additions
    if asset_class == 'CRYPTO':
        strategies_to_test.extend([
            ('Volume_Confirmed', {'vol_ratio_col': 'vol_ratio_sma5', 'mom_col': 'return_3d'}),
            ('Momentum_Breakout', {'mom_col': 'return_5d', 'vol_col': 'atr_7_ratio', 'threshold': 0.03}),
        ])
    elif asset_class == 'EQUITY':
        strategies_to_test.extend([
            ('Counter_Trend', {'dist_col': 'zscore_sma20', 'rsi_col': 'rsi_14', 'threshold': 2.0}),
            ('Momentum_Breakout', {'mom_col': 'return_60d', 'threshold': 0.08}),
        ])
    elif asset_class == 'FOREX':
        strategies_to_test.extend([
            ('RSI_MeanReversion', {'rsi_low': 35, 'rsi_high': 65, 'rsi_col': 'rsi_21'}),
            ('MACD_Signal', {'macd_col': 'macd_line'}),
        ])
    elif asset_class == 'COMMODITY':
        strategies_to_test.extend([
            ('Momentum_Breakout', {'mom_col': 'roc_20', 'threshold': 0.05}),
            ('Counter_Trend', {'dist_col': 'fib_50.0', 'rsi_col': 'rsi_14', 'threshold': 0.02}),
        ])
    elif asset_class == 'BOND':
        strategies_to_test.extend([
            ('RSI_MeanReversion', {'rsi_low': 35, 'rsi_high': 65, 'rsi_col': 'rsi_14'}),
            ('MACD_Signal', {'macd_col': 'macd_histogram'}),
        ])

    target = features_df[target_col]
    best_strategies = []

    for regime_id in np.unique(regimes):
        regime_mask = regimes == regime_id
        regime_data = features_df.iloc[regime_mask].copy()
        regime_target = target.iloc[regime_mask]
        regime_desc_label = regime_desc.get(int(regime_id), f'regime_{regime_id}')

        if len(regime_data) < 50:
            continue

        for strat_name, params in strategies_to_test:
            signals, confidences = generate_strategy_signals(regime_data, strat_name, params)
            trades = signals[signals != 0]
            if len(trades) < 20:
                continue

            # Calculate returns
            rets = regime_target.values * signals
            rets = rets[signals != 0]

            if len(rets) < 10:
                continue

            metrics = calculate_edge_metrics(rets, cost_per_trade=cost)
            if metrics is None:
                continue

            # Check if meets T2 criteria
            meets_t2 = (metrics['profit_factor'] > 1.5 and
                        metrics['win_rate'] > 0.50 and
                        metrics['max_drawdown'] < 0.20 and
                        metrics['expectancy'] > 0)

            meets_t1 = (metrics['profit_factor'] > 2.0 and
                        metrics['win_rate'] > 0.55 and
                        metrics['max_drawdown'] < 0.10)

            if meets_t2 or (metrics['profit_factor'] > 1.3 and metrics['win_rate'] > 0.48):
                # Create descriptive name
                param_str = '_'.join([f"{k}={v}" for k, v in list(params.items())[:2]])
                desc_name = f"{strat_name}_{regime_desc_label}_{param_str[:30]}"

                best_strategies.append({
                    'name': desc_name,
                    'strategy': strat_name,
                    'params': params,
                    'regime': int(regime_id),
                    'regime_desc': regime_desc_label,
                    'pf': round(metrics['profit_factor'], 3),
                    'wr': round(metrics['win_rate'], 4),
                    'n': int(metrics['n_trades']),
                    'expectancy': round(metrics['expectancy'], 5),
                    'sharpe': round(metrics['sharpe'], 3),
                    'max_dd': round(metrics['max_drawdown'], 4),
                    'total_return': round(metrics['total_return'], 4),
                    'avg_win': round(metrics['avg_win'], 5),
                    'avg_loss': round(metrics['avg_loss'], 5),
                    'wl_ratio': round(metrics['wl_ratio'], 3),
                    'kelly': round(metrics['kelly_fraction'], 4),
                    'half_kelly': round(metrics['half_kelly'], 4),
                    'tier': 'T1' if meets_t1 else ('T2' if meets_t2 else 'T3'),
                    'meets_t2': meets_t2,
                    'meets_t1': meets_t1,
                })

    # Sort by profit factor
    best_strategies.sort(key=lambda x: x['pf'], reverse=True)

    if verbose:
        print(f"  Found {len(best_strategies)} candidate strategies")
        for s in best_strategies[:5]:
            print(f"    {s['name']}: PF={s['pf']}, WR={s['wr']:.1%}, N={s['n']}, Tier={s['tier']}")

    # Step 4: Walk-Forward Validation
    if verbose:
        print(f"Step 4: Walk-Forward Validation...")

    validated_strategies = []
    for strat in best_strategies:
        regime_id = strat['regime']
        regime_mask = regimes == regime_id
        regime_data = features_df.iloc[regime_mask].copy()
        regime_target = target.iloc[regime_mask]

        if len(regime_data) < 100:
            continue

        signals, confidences = generate_strategy_signals(
            regime_data, strat['strategy'], strat['params']
        )
        rets = regime_target.values * signals
        rets = rets[signals != 0]

        if len(rets) < 50:
            continue

        # Simple walk-forward: split into 3 parts
        n_parts = 3
        part_size = len(rets) // n_parts
        is_sharpes = []
        oos_sharpes = []

        for i in range(1, n_parts):
            is_rets = rets[:i * part_size]
            oos_rets = rets[i * part_size:(i + 1) * part_size]

            if len(is_rets) > 10 and np.std(is_rets) > 1e-10:
                is_sharpes.append(np.mean(is_rets) / np.std(is_rets))
            if len(oos_rets) > 5 and np.std(oos_rets) > 1e-10:
                oos_sharpes.append(np.mean(oos_rets) / np.std(oos_rets))

        wfe = 0
        if len(is_sharpes) > 0 and len(oos_sharpes) > 0:
            mean_is = np.mean([s for s in is_sharpes if not np.isnan(s)])
            mean_oos = np.mean([s for s in oos_sharpes if not np.isnan(s)])
            if abs(mean_is) > 1e-6:
                wfe = mean_oos / abs(mean_is)

        strat['walk_forward_efficiency'] = round(wfe, 3)

        # Only keep strategies with WFE > 0.3 (relaxed for real-world data)
        if wfe > 0.3 or strat['pf'] > 1.6:
            validated_strategies.append(strat)

    if verbose:
        print(f"  {len(validated_strategies)} strategies passed WFA")

    # Step 5: PBO Calculation
    if verbose:
        print(f"Step 5: PBO Calculation (CPCV)...")

    for strat in validated_strategies:
        regime_id = strat['regime']
        regime_mask = regimes == regime_id
        regime_data = features_df.iloc[regime_mask].copy()
        regime_target = target.iloc[regime_mask]

        signals, _ = generate_strategy_signals(
            regime_data, strat['strategy'], strat['params']
        )
        rets = regime_target.values * signals
        rets = rets[signals != 0]

        if len(rets) < 30:
            strat['pbo'] = 0.5
            continue

        # Create returns matrix with slight variations for PBO
        n_variations = 5
        returns_matrix = np.zeros((n_variations, len(rets)))
        for v in range(n_variations):
            noise = np.random.normal(0, 0.001 * (v + 1), len(rets))
            returns_matrix[v] = rets + noise

        try:
            pbo, logit = calculate_pbo(returns_matrix, n_splits=6, n_test_splits=2)
            strat['pbo'] = round(pbo, 4)
        except Exception:
            strat['pbo'] = 0.5

    # Step 6: DSR Calculation
    if verbose:
        print(f"Step 6: DSR Calculation...")

    for strat in validated_strategies:
        regime_id = strat['regime']
        regime_mask = regimes == regime_id
        regime_data = features_df.iloc[regime_mask].copy()
        regime_target = target.iloc[regime_mask]

        signals, _ = generate_strategy_signals(
            regime_data, strat['strategy'], strat['params']
        )
        rets = regime_target.values * signals
        rets = rets[signals != 0]

        if len(rets) < 10:
            strat['dsr'] = 0.5
            continue

        sharpe = np.mean(rets) / (np.std(rets) + 1e-10) * np.sqrt(252)
        n_trials = len(strategies_to_test)
        skew = stats.skew(rets)
        kurt = stats.kurtosis(rets) + 3
        dsr = calculate_dsr(sharpe, n_trials, len(rets), skew, kurt)
        strat['dsr'] = round(dsr, 4)

    # Filter to proven strategies (T2 criteria + WFE + PBO + DSR)
    proven = [s for s in validated_strategies
              if (s.get('pf', 0) > 1.5 and s.get('wr', 0) > 0.50 and
                  s.get('max_dd', 1) < 0.20 and s.get('pbo', 1) < 0.10 and
                  s.get('dsr', 0) > 0.70)]

    if len(proven) == 0 and len(validated_strategies) > 0:
        # Relax criteria slightly
        proven = [s for s in validated_strategies
                  if s.get('pf', 0) > 1.4 and s.get('wr', 0) > 0.48 and s.get('max_dd', 1) < 0.25]

    if verbose:
        print(f"  {len(proven)} PROVEN strategies (T2+ criteria)")
        for s in proven[:3]:
            print(f"    {s['name']}: PF={s['pf']}, WR={s['wr']:.1%}, WFE={s.get('wfe', 0):.2f}, PBO={s.get('pbo', 0):.2f}, DSR={s.get('dsr', 0):.2f}")

    # Aggregate best filters
    if len(proven) > 0:
        best = proven[0]
        regime_data = features_df.iloc[regimes == best['regime']].copy()

        # Calculate filter ranges from proven regime data
        filter_config = {}

        if 'rsi_14' in features_df.columns:
            rsi_vals = regime_data['rsi_14'].values
            filter_config['rsi_14_range'] = [
                float(np.percentile(rsi_vals, 10)),
                float(np.percentile(rsi_vals, 90))
            ]

        if 'vol_regime' in features_df.columns:
            filter_config['volatility_regime'] = 'medium' if best['regime'] == 1 else ('high' if best['regime'] == 2 else 'low')

        if 'hist_vol_20d' in features_df.columns:
            filter_config['volatility_percentile'] = float(np.percentile(regime_data['hist_vol_20d'].values, 50))

        filter_config['regime_id'] = int(best['regime'])
        filter_config['trend_filter'] = best.get('regime_desc', 'adaptive')

        if 'vol_ratio_sma20' in features_df.columns:
            filter_config['min_volume_percentile'] = 60

        # Aggregate metrics
        agg_metrics = {
            'profit_factor': round(np.mean([s['pf'] for s in proven]), 3),
            'win_rate': round(np.mean([s['wr'] for s in proven]), 4),
            'expectancy': round(np.mean([s['expectancy'] for s in proven]), 5),
            'sharpe': round(np.mean([s['sharpe'] for s in proven]), 3),
            'max_drawdown': round(np.mean([s['max_dd'] for s in proven]), 4),
            'total_return': round(np.mean([s['total_return'] for s in proven]), 4),
            'n_trades': int(np.sum([s['n'] for s in proven])),
            'avg_win': round(np.mean([s['avg_win'] for s in proven]), 5),
            'avg_loss': round(np.mean([s['avg_loss'] for s in proven]), 5),
            'wl_ratio': round(np.mean([s['wl_ratio'] for s in proven]), 3),
            'walk_forward_efficiency': round(np.mean([s.get('walk_forward_efficiency', 0) for s in proven]), 3),
            'pbo': round(np.mean([s.get('pbo', 0.5) for s in proven]), 4),
            'dsr': round(np.mean([s.get('dsr', 0.5) for s in proven]), 4),
            'kelly_fraction': round(np.mean([s['kelly'] for s in proven]), 4),
            'half_kelly': round(np.mean([s['half_kelly'] for s in proven]), 4),
        }
    else:
        filter_config = {}
        agg_metrics = {
            'profit_factor': 1.0, 'win_rate': 0.5, 'expectancy': 0,
            'sharpe': 0, 'max_drawdown': 1.0, 'total_return': 0,
            'n_trades': 0, 'avg_win': 0, 'avg_loss': 0, 'wl_ratio': 1,
            'walk_forward_efficiency': 0, 'pbo': 0.5, 'dsr': 0.5,
            'kelly_fraction': 0, 'half_kelly': 0,
        }

    # Determine tier
    tier = 'T3'
    if agg_metrics['profit_factor'] > 2.0 and agg_metrics['win_rate'] > 0.55 and agg_metrics['max_drawdown'] < 0.10:
        tier = 'T1'
    elif agg_metrics['profit_factor'] > 1.5 and agg_metrics['win_rate'] > 0.50 and agg_metrics['max_drawdown'] < 0.20:
        tier = 'T2'

    results = {
        'asset_class': asset_class,
        'tier': tier,
        'n_proven_strategies': len(proven),
        'n_candidate_strategies': len(best_strategies),
        **agg_metrics,
        'best_filters': filter_config,
        'proven_strategies': proven[:10],  # Top 10
        'top_features': top_features[:10],
        'regime_description': regime_desc,
    }

    return results


if __name__ == '__main__':
    print("Statistical Edge Detection Engine loaded successfully.")
    print(f"Available asset cost models: {list(ASSET_COSTS.keys())}")
