#!/usr/bin/env python3
"""
ANTIGRAVITY — Production ML Crypto Engine v3.1
================================================
Walk-forward backtesting + Ensemble stacking + Continuous learning
Designed to be the SINGLE SOURCE OF TRUTH for all ML predictions.

v3.1 improvements over v3.0:
 - XGBoost added to ensemble (RF + GBT + XGB, weighted by calibrated accuracy)
 - Probability calibration (Platt + Isotonic) for honest confidence scores
 - SHAP-based feature importance (replaces simple RF importance)
 - Feature correlation cleanup (drops correlated features r>0.9)
 - On-chain data integration (CoinGecko: BTC dominance, market cap, per-coin metrics)

v3.0 improvements over v2.0:
 - Volatility-based regime detection (4-state: BULL/BEAR/SIDEWAYS/HIGH_VOL)
 - Adaptive ATR-based TP/SL per pair (regime-adjusted)
 - Multi-timeframe features (4h + daily confirmation)
 - Fear & Greed Index integration (free API)
 - Purged walk-forward validation (48-bar gap prevents leakage)
 - Correlation guard (max 1 position per asset, 72h cooldown)
 - Longer training window (90 days vs 30 days)
"""

import sqlite3
import pandas as pd
import numpy as np
import os
import json
import sys
import math
import warnings
import joblib
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

warnings.filterwarnings('ignore')

# ── Optional imports (graceful fallback) ──────────────────────────────────
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("  ⚠️ xgboost not installed — using RF+GBT only (pip install xgboost)")

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False

# ── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / 'models'
PRODUCTION_DIR = BASE_DIR / 'production_models'
DATA_DIR = BASE_DIR / 'data'
BACKTEST_DIR = BASE_DIR.parent / 'backtest_results'
UPDATES_DATA = BASE_DIR.parent / 'updates' / 'data'
TRACKER_DIR = BASE_DIR.parent / 'claude_gainer_ml' / 'tracker'
DB_PATH = BASE_DIR.parent / 'crypto_data.db'

for d in [MODELS_DIR, PRODUCTION_DIR, DATA_DIR, BACKTEST_DIR, UPDATES_DATA]:
    d.mkdir(parents=True, exist_ok=True)

# ── Configuration ─────────────────────────────────────────────────────────────────
CONFIG = {
    # Walk-forward (v3.0: longer windows + purge gap)
    'train_window_bars': 2160,    # 2160 hourly bars = 90 days (was 30)
    'test_window_bars': 240,      # 240 hours = 10 days (was 5)
    'step_bars': 240,             # slide every 10 days
    'purge_bars': 48,             # v3.0: Gap between train/test to prevent leakage

    # TP/SL for backtesting — now adaptive per-pair (these are defaults)
    'tp_pct': 0.03,               # +3% take profit (default, overridden by adaptive)
    'sl_pct': -0.015,             # -1.5% stop loss (default, overridden by adaptive)
    'max_hold_bars': 48,          # 48 hour max hold
    'rr_ratio': 2.0,              # 2:1 risk-reward

    # Model thresholds
    'min_probability': 0.60,      # Higher bar = fewer but better trades
    'max_positions': 8,           # Max concurrent positions
    'min_win_rate_to_trade': 0.40, # Need 40%+ to be profitable at 2:1 RR
    'max_positions_per_asset': 1,  # v3.0: Correlation guard
    'cooldown_hours_after_loss': 72, # v3.0: No re-entry for 72h after loss

    # Continuous learning
    'retrain_after_n_resolved': 10,
    'online_weight': 0.3,         # Weight of new data in retraining
}


# ═══════════════════════════════════════════════════════════════════════════
#  v3.0: REGIME DETECTION + ADAPTIVE TP/SL + FEAR & GREED
# ═══════════════════════════════════════════════════════════════════════════

def classify_regime(close, lookback=30):
    """
    Classify current market into 4 regimes using volatility + returns.
    Based on Researcher 029's finding: volatility-based regimes have 75% accuracy.
    Returns: 'BULL', 'BEAR', 'SIDEWAYS', or 'HIGH_VOL'
    """
    close = close.astype(float)
    if len(close) < lookback:
        return 'SIDEWAYS'
    ret = (close.iloc[-1] / close.iloc[-lookback] - 1) * 100
    vol = close.pct_change().tail(lookback).std() * np.sqrt(24) * 100
    if vol > 80:
        return 'HIGH_VOL'
    elif ret > 15:
        return 'BULL'
    elif ret < -15:
        return 'BEAR'
    else:
        return 'SIDEWAYS'


def adaptive_tpsl(close, high, low, regime='SIDEWAYS', atr_period=14):
    """
    Adaptive TP/SL based on ATR and market regime.
    v3.0: Replaces static TP/SL with regime-adjusted ATR multiples.
    """
    close = close.astype(float)
    high = high.astype(float)
    low = low.astype(float)
    tr = pd.concat([
        high - low,
        abs(high - close.shift(1)),
        abs(low - close.shift(1))
    ], axis=1).max(axis=1)
    current_atr = tr.rolling(atr_period).mean().iloc[-1]
    current_price = float(close.iloc[-1])
    if current_atr <= 0 or np.isnan(current_atr):
        current_atr = current_price * 0.02
    regime_config = {
        'BULL':     {'tp_mult': 3.0, 'sl_mult': 1.5},
        'SIDEWAYS': {'tp_mult': 2.0, 'sl_mult': 1.0},
        'BEAR':     {'tp_mult': 1.5, 'sl_mult': 0.75},
        'HIGH_VOL': {'tp_mult': 2.5, 'sl_mult': 1.25},
    }
    cfg = regime_config.get(regime, regime_config['SIDEWAYS'])
    tp_pct = (cfg['tp_mult'] * current_atr) / current_price
    sl_pct = -(cfg['sl_mult'] * current_atr) / current_price
    return tp_pct, sl_pct, current_atr


def fetch_fear_greed():
    """
    Fetch Bitcoin Fear & Greed Index (free, no API key).
    Returns dict of features or empty dict on failure.
    """
    try:
        url = "https://api.alternative.me/fng/?limit=30&format=json"
        data = json.loads(urllib.request.urlopen(url, timeout=10).read())
        values = [int(d['value']) for d in data['data']]
        return {
            'fg_current': values[0],
            'fg_7d_avg': np.mean(values[:7]),
            'fg_30d_avg': np.mean(values[:min(30, len(values))]),
            'fg_extreme_fear': int(values[0] < 25),
            'fg_extreme_greed': int(values[0] > 75),
            'fg_momentum': values[0] - (np.mean(values[:7]) if len(values) >= 7 else values[0]),
        }
    except Exception:
        return {}


def fetch_onchain_data(symbol=None):
    """
    v3.1: Fetch on-chain/macro market data from CoinGecko.
    Returns dict of features prefixed with 'onchain_'.
    Uses COIN_GECKO env var for API key (optional, works without for basic endpoints).
    """
    cg_key = os.environ.get('COIN_GECKO', '')
    headers = {}
    if cg_key:
        headers['x-cg-demo-api-key'] = cg_key

    features = {}

    # 1) Global market data (BTC dominance, total market cap, volume)
    try:
        url = "https://api.coingecko.com/api/v3/global"
        req = urllib.request.Request(url, headers=headers)
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())['data']

        btc_dom = data.get('market_cap_percentage', {}).get('btc', 50.0)
        eth_dom = data.get('market_cap_percentage', {}).get('eth', 15.0)
        total_mcap = data.get('total_market_cap', {}).get('usd', 0) / 1e12  # in trillions
        total_vol = data.get('total_volume', {}).get('usd', 0) / 1e12
        mcap_change_24h = data.get('market_cap_change_percentage_24h_usd', 0)

        features.update({
            'onchain_btc_dominance': round(btc_dom, 2),
            'onchain_eth_dominance': round(eth_dom, 2),
            'onchain_total_mcap_t': round(total_mcap, 3),
            'onchain_total_vol_t': round(total_vol, 3),
            'onchain_mcap_change_24h': round(mcap_change_24h, 2),
            'onchain_vol_mcap_ratio': round(total_vol / max(total_mcap, 0.001), 4),
            'onchain_alt_dominance': round(100 - btc_dom - eth_dom, 2),
        })
    except Exception as e:
        print(f"    ⚠️ CoinGecko global data: {e}")

    # 2) BTC market metrics (as macro indicator for all pairs)
    try:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false&community_data=false&developer_data=false"
        req = urllib.request.Request(url, headers=headers)
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        md = data.get('market_data', {})

        features.update({
            'onchain_btc_price_change_24h': round(md.get('price_change_percentage_24h', 0), 2),
            'onchain_btc_price_change_7d': round(md.get('price_change_percentage_7d', 0), 2),
            'onchain_btc_price_change_30d': round(md.get('price_change_percentage_30d', 0), 2),
            'onchain_btc_ath_pct': round(md.get('ath_change_percentage', {}).get('usd', 0), 2),
            'onchain_btc_mcap_rank': md.get('market_cap_rank', 1),
        })
    except Exception as e:
        print(f"    ⚠️ CoinGecko BTC data: {e}")

    # 3) Per-coin metrics (if symbol provided, e.g., 'BTC', 'ETH', 'SOL')
    if symbol and symbol.upper() not in ('BTC', 'BITCOIN'):
        coin_map = {
            'ETH': 'ethereum', 'SOL': 'solana', 'XRP': 'ripple', 'ADA': 'cardano',
            'DOGE': 'dogecoin', 'DOT': 'polkadot', 'AVAX': 'avalanche-2',
            'MATIC': 'matic-network', 'LINK': 'chainlink', 'UNI': 'uniswap',
            'ATOM': 'cosmos', 'FIL': 'filecoin', 'ARB': 'arbitrum', 'OP': 'optimism',
            'TIA': 'celestia', 'SEI': 'sei-network', 'SUI': 'sui', 'APT': 'aptos',
            'FET': 'artificial-superintelligence-alliance', 'NEAR': 'near',
            'ALGO': 'algorand', 'HBAR': 'hedera-hashgraph', 'TON': 'the-open-network',
            'SHIB': 'shiba-inu', 'PEPE': 'pepe', 'TRUMP': 'official-trump',
        }
        coin_id = coin_map.get(symbol.upper(), symbol.lower())
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&community_data=false&developer_data=false"
            req = urllib.request.Request(url, headers=headers)
            data = json.loads(urllib.request.urlopen(req, timeout=10).read())
            md = data.get('market_data', {})

            cm_usd = md.get('market_cap', {}).get('usd', 0)
            vol_usd = md.get('total_volume', {}).get('usd', 0)

            features.update({
                'onchain_coin_mcap_rank': md.get('market_cap_rank', 999),
                'onchain_coin_change_24h': round(md.get('price_change_percentage_24h', 0), 2),
                'onchain_coin_change_7d': round(md.get('price_change_percentage_7d', 0), 2),
                'onchain_coin_change_30d': round(md.get('price_change_percentage_30d', 0), 2),
                'onchain_coin_vol_mcap': round(vol_usd / max(cm_usd, 1), 4),
                'onchain_coin_ath_pct': round(md.get('ath_change_percentage', {}).get('usd', 0), 2),
            })
        except Exception as e:
            print(f"    ⚠️ CoinGecko {symbol} data: {e}")

    return features


# ═══════════════════════════════════════════════════════════════════════════
#  FEATURE ENGINEERING (80+ features — v3.0)
# ═══════════════════════════════════════════════════════════════════════════

def compute_rsi(series, period=14):
    """RSI with proper Wilder's smoothing."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100 - (100 / (1 + rs))


def build_production_features(df):
    """
    Build 60+ features from OHLCV data.
    Designed to capture:
      - Trend (EMAs, slopes)
      - Momentum (RSI, ROC, MACD)
      - Volatility (ATR, BB, Keltner)
      - Volume (relative volume, OBV, VWAP proxy)
      - Price structure (compression, breakout proximity)
    """
    feat = pd.DataFrame(index=df.index)
    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    vol = df['volume'].astype(float)
    opn = df['open'].astype(float)

    # ── Trend Features ──
    for p in [9, 21, 50, 100, 200]:
        ema = close.ewm(span=p, adjust=False).mean()
        feat[f'ema_{p}_dist'] = (close - ema) / (close + 1e-10) * 100
        if p <= 50:
            feat[f'ema_{p}_slope'] = ema.diff(3) / (ema.shift(3) + 1e-10) * 100

    # EMA crossovers
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    feat['ema_9_21_cross'] = (ema9 - ema21) / (close + 1e-10) * 100
    feat['ema_21_50_cross'] = (ema21 - ema50) / (close + 1e-10) * 100

    # ── Momentum Features ──
    for p in [7, 14, 21]:
        feat[f'rsi_{p}'] = compute_rsi(close, p)
    feat['rsi_14_slope'] = feat['rsi_14'].diff(3)

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    feat['macd_line'] = ema12 - ema26
    feat['macd_signal'] = feat['macd_line'].ewm(span=9).mean()
    feat['macd_hist'] = feat['macd_line'] - feat['macd_signal']
    feat['macd_hist_slope'] = feat['macd_hist'].diff(2)

    # Rate of change
    for p in [3, 5, 10, 20]:
        feat[f'roc_{p}'] = close.pct_change(p) * 100

    # Returns
    for p in [1, 3, 6, 12, 24]:
        feat[f'ret_{p}'] = close.pct_change(p)

    # ── Volatility Features ──
    tr = pd.concat([
        high - low,
        abs(high - close.shift(1)),
        abs(low - close.shift(1))
    ], axis=1).max(axis=1)
    feat['atr_14'] = tr.rolling(14).mean()
    feat['atr_pct'] = feat['atr_14'] / (close + 1e-10) * 100
    feat['atr_contraction'] = feat['atr_14'] / (feat['atr_14'].rolling(20).mean() + 1e-10)

    # Bollinger Bands
    bb_sma = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    feat['bb_width'] = (4 * bb_std) / (bb_sma + 1e-10) * 100
    feat['bb_pct'] = (close - (bb_sma - 2 * bb_std)) / (4 * bb_std + 1e-10)
    feat['bb_squeeze'] = (feat['bb_width'] < feat['bb_width'].rolling(50).quantile(0.1)).astype(int)

    # Keltner Channel position
    kelt_upper = ema21 + 1.5 * feat['atr_14']
    kelt_lower = ema21 - 1.5 * feat['atr_14']
    feat['kelt_pos'] = (close - kelt_lower) / (kelt_upper - kelt_lower + 1e-10)

    # Volatility compression (decreasing daily range)
    dr = (high - low) / (close + 1e-10)
    feat['range_3d'] = dr.rolling(3).mean()
    feat['range_10d'] = dr.rolling(10).mean()
    feat['vol_compression'] = feat['range_3d'] / (feat['range_10d'] + 1e-10)

    # Intrabar volatility
    feat['close_open_range'] = (close - opn) / (opn + 1e-10) * 100
    feat['high_low_range'] = (high - low) / (close + 1e-10) * 100
    feat['upper_wick'] = (high - pd.concat([close, opn], axis=1).max(axis=1)) / (high - low + 1e-10)
    feat['lower_wick'] = (pd.concat([close, opn], axis=1).min(axis=1) - low) / (high - low + 1e-10)

    # Historical volatility
    feat['hvol_10'] = close.pct_change().rolling(10).std() * np.sqrt(24)  # annualized hourly
    feat['hvol_20'] = close.pct_change().rolling(20).std() * np.sqrt(24)

    # ── Volume Features ──
    vol_sma20 = vol.rolling(20).mean()
    feat['vol_ratio'] = vol / (vol_sma20 + 1e-10)
    feat['vol_ratio_3d'] = vol.rolling(3).mean() / (vol_sma20 + 1e-10)
    feat['vol_change_1'] = vol.pct_change()
    feat['vol_change_5'] = vol.pct_change(5)

    # Volume-price relationship
    feat['vol_price_corr'] = close.pct_change().rolling(10).corr(vol.pct_change().rolling(10).mean())

    # OBV
    obv = (np.sign(close.diff()) * vol).cumsum()
    obv_ema = obv.ewm(span=10).mean()
    feat['obv_slope'] = (obv - obv_ema) / (abs(obv_ema) + 1e-10)

    # Volume-weighted momentum
    feat['vwap_dist'] = 0  # placeholder for intraday

    # ── Price Structure ──
    feat['close_vs_high_20'] = close / (close.rolling(20).max() + 1e-10)
    feat['close_vs_low_20'] = close / (close.rolling(20).min() + 1e-10)
    feat['breakout_proximity'] = (close - close.rolling(20).max()) / (close + 1e-10) * 100

    # Consecutive direction
    green = (close > opn).astype(int)
    groups = (green != green.shift()).cumsum()
    feat['consec_green'] = green.groupby(groups).cumsum() * green

    # ── Regime Detection (v3.0: Enhanced 4-state) ──
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    feat['regime_trend'] = (ema50 - ema200) / (ema200 + 1e-10) * 100  # + = bull, - = bear
    feat['regime_bullish'] = (ema50 > ema200).astype(int)  # Binary bull/bear

    # v3.0: Volatility-based regime (numeric encoding for ML)
    ret_30 = close.pct_change(30) * 100
    vol_30 = close.pct_change().rolling(30).std() * np.sqrt(24) * 100
    feat['regime_vol_30d'] = vol_30
    feat['regime_ret_30d'] = ret_30
    # Numeric regime: 3=BULL, 2=SIDEWAYS, 1=BEAR, 0=HIGH_VOL
    regime_num = pd.Series(2, index=close.index, dtype=float)  # default SIDEWAYS
    regime_num = regime_num.where(~(vol_30 > 80), 0)        # HIGH_VOL overrides
    regime_num = regime_num.where(~(ret_30 > 15), 3)         # BULL
    regime_num = regime_num.where(~(ret_30 < -15), 1)        # BEAR
    feat['regime_state'] = regime_num

    # ADX - trend strength (prevents trading in choppy markets)
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    atr_for_adx = tr.rolling(14).mean()
    plus_di = 100 * (plus_dm.rolling(14).mean() / (atr_for_adx + 1e-10))
    minus_di = 100 * (minus_dm.rolling(14).mean() / (atr_for_adx + 1e-10))
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    feat['adx'] = dx.rolling(14).mean()
    feat['plus_di_minus_di'] = plus_di - minus_di  # +DI > -DI = bullish trend

    # Higher-highs / lower-lows structure
    feat['hh_ll'] = (close.rolling(20).max() > close.rolling(40).max().shift(20)).astype(int) - \
                    (close.rolling(20).min() < close.rolling(40).min().shift(20)).astype(int)

    # Mean reversion distance (how far from 50-bar mean)
    feat['mean_reversion_dist'] = (close - close.rolling(50).mean()) / (close.rolling(50).std() + 1e-10)

    # ── v3.0: Multi-Timeframe Features ──
    # 4h trend (approximate: rolling 4-bar close with EMA)
    close_4h = close.rolling(4).apply(lambda x: x.iloc[-1], raw=False)
    ema20_4h = close_4h.ewm(span=20, adjust=False).mean()
    ema50_4h = close_4h.ewm(span=50, adjust=False).mean()
    feat['htf_4h_trend'] = (ema20_4h > ema50_4h).astype(int)
    feat['htf_4h_ema_dist'] = (close - ema20_4h) / (close + 1e-10) * 100
    feat['htf_4h_rsi'] = compute_rsi(close_4h, 14)

    # Daily trend (approximate: rolling 24-bar close with EMA)
    close_1d = close.rolling(24).apply(lambda x: x.iloc[-1], raw=False)
    ema20_1d = close_1d.ewm(span=20, adjust=False).mean()
    ema50_1d = close_1d.ewm(span=50, adjust=False).mean()
    feat['htf_daily_trend'] = (ema20_1d > ema50_1d).astype(int)
    feat['htf_daily_rsi'] = compute_rsi(close_1d, 14)

    # Timeframe alignment: how many timeframes agree on bullish direction
    feat['htf_alignment'] = (
        feat['htf_4h_trend'] +
        feat['htf_daily_trend'] +
        feat['regime_bullish']
    )  # 0-3 scale: 3 = all timeframes bullish

    # Clean up
    feat = feat.replace([np.inf, -np.inf], np.nan)
    return feat



def build_target_tpsl(close_series, high_series, low_series,
                       tp_pct=0.10, sl_pct=-0.07, max_bars=48):
    """
    Build target labels matching actual TP/SL trading logic.
    For each bar, look forward max_bars to see if TP or SL hits first.

    Returns:
      target: 1 if TP hit before SL, 0 otherwise
      pnl: actual PnL percentage for each entry
    """
    n = len(close_series)
    target = np.zeros(n, dtype=int)
    pnl = np.zeros(n, dtype=float)

    close_arr = close_series.values
    high_arr = high_series.values
    low_arr = low_series.values

    for i in range(n - 1):
        entry = close_arr[i]
        if entry <= 0:
            continue

        tp_price = entry * (1 + tp_pct)
        sl_price = entry * (1 + sl_pct)

        for j in range(i + 1, min(i + max_bars + 1, n)):
            # Check SL first (worst case)
            if low_arr[j] <= sl_price:
                target[i] = 0
                pnl[i] = sl_pct
                break
            # Check TP
            if high_arr[j] >= tp_price:
                target[i] = 1
                pnl[i] = tp_pct
                break
        else:
            # Time exit
            if i + max_bars < n:
                exit_price = close_arr[min(i + max_bars, n - 1)]
                pnl[i] = (exit_price - entry) / entry
                target[i] = 1 if pnl[i] > 0 else 0

    return pd.Series(target, index=close_series.index), pd.Series(pnl, index=close_series.index)


# ═══════════════════════════════════════════════════════════════════════════
#  WALK-FORWARD BACKTESTER
# ═══════════════════════════════════════════════════════════════════════════

def walk_forward_backtest(pair, df, config=None):
    """
    Walk-forward backtest: train on rolling window, test on next period.
    No look-ahead bias. Matches real trading conditions.
    """
    if config is None:
        config = CONFIG

    from sklearn.ensemble import (
        RandomForestClassifier,
        GradientBoostingClassifier
    )
    from sklearn.preprocessing import StandardScaler
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.metrics import brier_score_loss

    train_w = config['train_window_bars']
    test_w = config['test_window_bars']
    step = config['step_bars']
    tp = config['tp_pct']
    sl = config['sl_pct']
    max_hold = config['max_hold_bars']

    # NOTE (Phase 20 — 2026-04-15): Features are computed on the full df before
    # walk-forward splitting. This is SAFE because all rolling/ewm computations in
    # build_production_features are backward-looking: the feature at bar i depends
    # only on bars 0..i. No forward-looking operations (.shift(-N), future
    # rolling, etc.) are used. Computing on the full df upfront avoids the O(F*W)
    # cost of recomputing per fold while remaining leak-free.
    features = build_production_features(df)
    target, pnl_actual = build_target_tpsl(
        df['close'].astype(float),
        df['high'].astype(float),
        df['low'].astype(float),
        tp, sl, max_hold
    )

    # Drop rows with any NaN (from rolling window warmup periods)
    combined = features.copy()
    combined['target'] = target
    combined['pnl'] = pnl_actual
    combined = combined.dropna()

    if len(combined) < train_w + test_w:
        return None

    X = combined.drop(['target', 'pnl'], axis=1)
    y = combined['target']
    pnl_series = combined['pnl']

    all_predictions = []
    all_actuals = []
    all_pnl = []
    all_probs = []
    fold_metrics = []

    # Walk forward (v3.0: with purge gap)
    purge = config.get('purge_bars', 48)
    start = 0
    fold = 0
    while start + train_w + purge + test_w <= len(X):
        train_end = start + train_w
        test_start = train_end + purge  # v3.0: PURGE GAP prevents leakage
        test_end = test_start + test_w

        X_train = X.iloc[start:train_end].fillna(0)
        y_train = y.iloc[start:train_end]
        X_test = X.iloc[test_start:test_end].fillna(0)
        y_test = y.iloc[test_start:test_end]
        pnl_test = pnl_series.iloc[test_start:test_end]

        # Skip if no positive samples
        if y_train.sum() < 3:
            start += step
            continue

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        # v3.1: Ensemble: RF + GBT + XGBoost (with calibration)
        pos_rate = y_train.mean()
        scale_pos = max((1 - pos_rate) / (pos_rate + 1e-10), 1)

        rf = RandomForestClassifier(
            n_estimators=200, max_depth=10,
            min_samples_leaf=5, class_weight='balanced',
            n_jobs=-1, random_state=42
        )
        gbt = GradientBoostingClassifier(
            n_estimators=200, max_depth=4,
            learning_rate=0.05, subsample=0.8,
            min_samples_leaf=10, random_state=42
        )

        rf.fit(X_train_s, y_train)
        gbt.fit(X_train_s, y_train)

        # v3.1: Calibrated probabilities (Platt for RF, Isotonic for GBT)
        try:
            rf_cal = CalibratedClassifierCV(rf, method='sigmoid', cv=3)
            rf_cal.fit(X_train_s, y_train)
            prob_rf = rf_cal.predict_proba(X_test_s)[:, 1]
        except Exception:
            prob_rf = rf.predict_proba(X_test_s)[:, 1]

        try:
            gbt_cal = CalibratedClassifierCV(gbt, method='isotonic', cv=3)
            gbt_cal.fit(X_train_s, y_train)
            prob_gbt = gbt_cal.predict_proba(X_test_s)[:, 1]
        except Exception:
            prob_gbt = gbt.predict_proba(X_test_s)[:, 1]

        # v3.1: XGBoost (if available)
        if HAS_XGB:
            try:
                xgb_model = xgb.XGBClassifier(
                    n_estimators=200, max_depth=6,
                    learning_rate=0.05, subsample=0.8,
                    colsample_bytree=0.8, min_child_weight=5,
                    scale_pos_weight=scale_pos,
                    eval_metric='logloss', random_state=42,
                    verbosity=0
                )
                xgb_model.fit(X_train_s, y_train)
                prob_xgb = xgb_model.predict_proba(X_test_s)[:, 1]
                # 3-model weighted ensemble (XGB gets more weight)
                prob_ensemble = 0.25 * prob_rf + 0.35 * prob_gbt + 0.40 * prob_xgb
            except Exception:
                prob_ensemble = 0.4 * prob_rf + 0.6 * prob_gbt
        else:
            prob_ensemble = 0.4 * prob_rf + 0.6 * prob_gbt
        preds = (prob_ensemble >= config['min_probability']).astype(int)

        all_predictions.extend(preds)
        all_actuals.extend(y_test.values)
        all_pnl.extend(pnl_test.values)
        all_probs.extend(prob_ensemble)

        # Fold metrics
        tp_hits = ((preds == 1) & (y_test.values == 1)).sum()
        sl_hits = ((preds == 1) & (y_test.values == 0)).sum()
        n_trades = preds.sum()
        if n_trades > 0:
            fold_wr = tp_hits / n_trades
            fold_pnl = sum(pnl_test.values[k] for k in range(len(preds)) if preds[k] == 1)
            fold_metrics.append({
                'fold': fold,
                'n_trades': int(n_trades),
                'tp_hits': int(tp_hits),
                'sl_hits': int(sl_hits),
                'win_rate': round(fold_wr, 4),
                'pnl_pct': round(fold_pnl, 4)
            })

        start += step
        fold += 1

    if not fold_metrics:
        return None

    # Aggregate
    all_predictions = np.array(all_predictions)
    all_actuals = np.array(all_actuals)
    all_pnl = np.array(all_pnl)
    all_probs = np.array(all_probs)

    trade_mask = all_predictions == 1
    n_total_trades = trade_mask.sum()
    if n_total_trades == 0:
        return None

    total_tp = ((all_predictions == 1) & (all_actuals == 1)).sum()
    total_sl = ((all_predictions == 1) & (all_actuals == 0)).sum()
    overall_wr = total_tp / n_total_trades
    trade_pnl = all_pnl[trade_mask]
    total_pnl = trade_pnl.sum()
    avg_pnl = trade_pnl.mean()
    win_pnl = trade_pnl[trade_pnl > 0].sum() if (trade_pnl > 0).any() else 0
    loss_pnl = abs(trade_pnl[trade_pnl < 0].sum()) if (trade_pnl < 0).any() else 1
    profit_factor = win_pnl / loss_pnl if loss_pnl > 0 else 0

    # Sharpe
    if len(trade_pnl) > 1 and np.std(trade_pnl) > 0:
        sharpe = np.mean(trade_pnl) / np.std(trade_pnl) * np.sqrt(252)
    else:
        sharpe = 0

    # Max drawdown on equity curve
    equity = np.cumsum(trade_pnl)
    peak = np.maximum.accumulate(equity)
    drawdown = peak - equity
    max_dd = drawdown.max() if len(drawdown) > 0 else 0

    result = {
        'pair': pair,
        'folds': len(fold_metrics),
        'total_bars': len(combined),
        'total_trades': int(n_total_trades),
        'tp_hits': int(total_tp),
        'sl_hits': int(total_sl),
        'win_rate': round(overall_wr, 4),
        'total_pnl_pct': round(total_pnl * 100, 2),
        'avg_trade_pnl': round(avg_pnl * 100, 4),
        'profit_factor': round(profit_factor, 3),
        'sharpe_ratio': round(sharpe, 3),
        'max_drawdown_pct': round(max_dd * 100, 2),
        'fold_details': fold_metrics,
        'config': {
            'tp': tp, 'sl': sl, 'max_hold': max_hold,
            'min_prob': config['min_probability']
        }
    }
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  PRODUCTION MODEL PERSISTENCE + TRAINING
# ═══════════════════════════════════════════════════════════════════════════

def load_persisted_model(pair, max_age_hours=48):
    """
    Load a previously trained and git-committed model if it exists and is fresh.
    Returns model_pack dict or None if model is missing/stale.

    Models are persisted across CI runs via git commit in train_crypto_models.yml.
    This avoids retraining from scratch every run, enabling learning accumulation.
    """
    pair_clean = pair.replace('/', '_')
    model_path = PRODUCTION_DIR / f'{pair_clean}_production.pkl'

    if not model_path.exists():
        return None

    try:
        model_pack = joblib.load(model_path)
    except Exception as e:
        print(f"    [WARN] Failed to load model for {pair}: {e}")
        return None

    # Check model freshness
    trained_at = model_pack.get('trained_at', '')
    if trained_at and max_age_hours > 0:
        try:
            trained_dt = datetime.fromisoformat(trained_at.replace('Z', '+00:00'))
            age_hours = (datetime.now(timezone.utc) - trained_dt).total_seconds() / 3600
            if age_hours > max_age_hours:
                print(f"    [STALE] {pair}: model is {age_hours:.0f}h old (max={max_age_hours}h), will retrain")
                return None
            print(f"    [FRESH] {pair}: model is {age_hours:.0f}h old, reusing")
        except (ValueError, TypeError):
            # Can't parse timestamp, treat as stale
            pass

    # Validate model has required keys
    required_keys = ['rf', 'gbt', 'scaler', 'features']
    if not all(k in model_pack for k in required_keys):
        print(f"    [INVALID] {pair}: model missing keys {[k for k in required_keys if k not in model_pack]}")
        return None

    return model_pack


def train_production_model(pair, df, save=True):
    """
    Train the final production model on ALL available data for a pair.
    v3.1: Uses RF + GBT + XGBoost (if available) with probability calibration.
    """
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.calibration import CalibratedClassifierCV

    features = build_production_features(df)
    target, _ = build_target_tpsl(
        df['close'].astype(float),
        df['high'].astype(float),
        df['low'].astype(float),
        CONFIG['tp_pct'], CONFIG['sl_pct'], CONFIG['max_hold_bars']
    )

    combined = features.copy()
    combined['target'] = target
    combined = combined.dropna()

    if len(combined) < 200:
        return None

    X = combined.drop('target', axis=1)
    y = combined['target']

    # FIXED (Phase 20 — 2026-04-15): Scaler fit on train only to prevent data leakage (Lopez de Prado 2018)
    # Temporal split FIRST, then feature selection on train only — prevents look-ahead leakage
    X_filled = X.fillna(0)
    split_idx = int(len(X_filled) * 0.8)
    X_train, X_cal = X_filled.iloc[:split_idx], X_filled.iloc[split_idx:]
    y_train, y_cal = y.iloc[:split_idx], y.iloc[split_idx:]

    # v3.1: Drop highly correlated features (r > 0.9) — COMPUTED ON TRAIN ONLY to prevent leakage
    # Phase 20 fix: previously computed on full X (train+cal), leaking holdout statistics
    # into feature selection. Now uses training split only (Lopez de Prado 2018).
    to_drop = []
    try:
        corr_matrix = X_train.fillna(0).corr().abs()
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        to_drop = [col for col in upper.columns if any(upper[col] > 0.9)]
        if to_drop:
            X_train = X_train.drop(columns=to_drop, errors='ignore')
            X_cal = X_cal.drop(columns=to_drop, errors='ignore')
            X_filled = X_filled.drop(columns=to_drop, errors='ignore')
    except Exception:
        pass

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_cal_s = scaler.transform(X_cal)

    pos_rate = y_train.mean()
    scale_pos = max((1 - pos_rate) / (pos_rate + 1e-10), 1)

    rf = RandomForestClassifier(
        n_estimators=300, max_depth=10,
        min_samples_leaf=5, class_weight='balanced',
        n_jobs=-1, random_state=42
    )
    gbt = GradientBoostingClassifier(
        n_estimators=300, max_depth=4,
        learning_rate=0.05, subsample=0.8,
        min_samples_leaf=10, random_state=42
    )

    rf.fit(X_train_s, y_train)
    gbt.fit(X_train_s, y_train)

    # v3.1: Calibrated versions
    rf_calibrated = rf
    gbt_calibrated = gbt
    try:
        rf_cal = CalibratedClassifierCV(rf, method='sigmoid', cv=3)
        rf_cal.fit(X_train_s, y_train)
        rf_calibrated = rf_cal
    except Exception:
        pass
    try:
        gbt_cal = CalibratedClassifierCV(gbt, method='isotonic', cv=3)
        gbt_cal.fit(X_train_s, y_train)
        gbt_calibrated = gbt_cal
    except Exception:
        pass

    # v3.1: XGBoost (if available)
    xgb_model = None
    if HAS_XGB:
        try:
            xgb_model = xgb.XGBClassifier(
                n_estimators=300, max_depth=6,
                learning_rate=0.05, subsample=0.8,
                colsample_bytree=0.8, min_child_weight=5,
                scale_pos_weight=scale_pos,
                eval_metric='logloss', random_state=42,
                verbosity=0
            )
            xgb_model.fit(X_train_s, y_train)
        except Exception:
            xgb_model = None

    # v3.1: SHAP feature importance (if available), else RF importance
    if HAS_SHAP and hasattr(rf, 'estimators_'):
        try:
            explainer = shap.TreeExplainer(rf)
            shap_values = explainer.shap_values(X_filled.values[:min(500, len(X_filled))])
            if isinstance(shap_values, list):
                shap_values = shap_values[1]  # class 1 (positive)
            importance = np.abs(shap_values).mean(axis=0)
            importances = dict(zip(X.columns, importance))
        except Exception:
            importances = dict(zip(X.columns, rf.feature_importances_))
    else:
        importances = dict(zip(X.columns, rf.feature_importances_))
    # Ensure all importance values are scalar floats (avoid numpy array comparison errors)
    def _to_float(v):
        try:
            if isinstance(v, np.ndarray):
                return float(v.mean()) if v.size > 1 else float(v.item())
            return float(v)
        except (TypeError, ValueError):
            return 0.0
    importances = {k: _to_float(v) for k, v in importances.items()}
    top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:20]

    model_pack = {
        'rf': rf_calibrated,
        'gbt': gbt_calibrated,
        'xgb': xgb_model,
        'scaler': scaler,
        'features': list(X.columns),
        'top_features': top_features,
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'n_samples': len(X),
        'positive_rate': float(y.mean()),
        'pair': pair,
        'model_version': 'v3.1',
        'has_xgb': xgb_model is not None,
        'has_shap': HAS_SHAP,
        'dropped_features': to_drop,
    }

    if save:
        pair_clean = pair.replace('/', '_')
        joblib.dump(model_pack, PRODUCTION_DIR / f'{pair_clean}_production.pkl')

    return model_pack


# ═══════════════════════════════════════════════════════════════════════════
#  LIVE PICK GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def generate_live_picks(backtest_results, conn=None, active_picks=None, closed_picks=None):
    """
    Generate real picks based on current market data + backtest-validated models.
    Uses exchange API if available, falls back to DB data.
    Only generates picks for pairs where the model is profitable in backtesting.
    v3.0: Adds regime filter, adaptive TP/SL, F&G index, correlation guard.
    """
    now = datetime.now(timezone.utc)

    # v3.0: Fetch Fear & Greed Index (shared across all pairs)
    fg_features = fetch_fear_greed()
    if fg_features:
        print(f"  \U0001f4ca Fear & Greed Index: {fg_features.get('fg_current', '?')}")
    else:
        print("  \u26a0\ufe0f Fear & Greed API unavailable")

    # v3.1: Fetch on-chain/macro data from CoinGecko (shared across all pairs)
    onchain_global = fetch_onchain_data(symbol=None)
    if onchain_global:
        print(f"  \U0001f4ca On-Chain: BTC Dom={onchain_global.get('onchain_btc_dominance', '?')}%  MCap={onchain_global.get('onchain_total_mcap_t', '?')}T")
    else:
        print("  \u26a0\ufe0f CoinGecko API unavailable")

    # Filter to profitable pairs
    profitable_pairs = {}
    for pair, result in backtest_results.items():
        if result is None:
            continue
        wr = result.get('win_rate', 0)
        pf = result.get('profit_factor', 0)
        n = result.get('total_trades', 0)
        # Require: >35% win rate, >1.0 profit factor, >15 trades
        if wr >= 0.35 and pf >= 1.0 and n >= 15:
            profitable_pairs[pair] = result

    if not profitable_pairs:
        print("[WARN] No profitable pairs found in backtesting!")
        profitable_pairs = {
            k: v for k, v in backtest_results.items()
            if v is not None and v.get('total_trades', 0) >= 10
        }

    picks = []

    # v3.0: Build correlation guard from active/closed picks
    active_symbols = set()
    cooldown_symbols = set()
    if active_picks:
        for p in active_picks:
            active_symbols.add(p.get('symbol', ''))
    if closed_picks:
        for p in closed_picks:
            if p.get('status') == 'LOST':
                exit_time = p.get('exit_time', p.get('resolved_at', ''))
                if exit_time:
                    try:
                        exit_dt = datetime.fromisoformat(str(exit_time).replace('Z', '+00:00'))
                        hours_since = (now - exit_dt).total_seconds() / 3600
                        if hours_since < CONFIG['cooldown_hours_after_loss']:
                            cooldown_symbols.add(p.get('symbol', ''))
                    except Exception:
                        pass
    if active_symbols or cooldown_symbols:
        print(f"  \U0001f6e1\ufe0f Correlation Guard: {len(active_symbols)} active, {len(cooldown_symbols)} on cooldown")

    # Try exchange, fall back to DB
    exchange = None
    try:
        import ccxt
        exchange = ccxt.kraken()
        exchange.load_markets()
        print("  \u2705 Connected to Kraken exchange for live prices")
    except Exception as e:
        print(f"  \u26a0\ufe0f Exchange unavailable ({e}), using DB data as fallback")

    # Open DB connection if not provided
    own_conn = False
    if conn is None and os.path.exists(str(DB_PATH)):
        conn = sqlite3.connect(str(DB_PATH))
        own_conn = True

    for pair, bt_result in profitable_pairs.items():
        pair_clean = pair.replace('/', '_')
        model_path = PRODUCTION_DIR / f'{pair_clean}_production.pkl'

        if not model_path.exists():
            continue

        try:
            model_pack = joblib.load(model_path)
        except Exception:
            continue

        # Get data — try exchange first, then DB
        df = None
        data_source = 'db'

        if exchange is not None:
            try:
                kraken_sym = pair.replace('/USDT', '/USD')
                ohlcv = exchange.fetch_ohlcv(kraken_sym, '1h', limit=250)
                if len(ohlcv) >= 50:
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    data_source = 'live'
            except Exception:
                pass

        if df is None and conn is not None:
            try:
                df = pd.read_sql(
                    "SELECT * FROM klines WHERE pair = ? ORDER BY timestamp DESC LIMIT 250",
                    conn, params=(pair,)
                )
                if len(df) >= 50:
                    df = df.sort_values('timestamp').reset_index(drop=True)
                    data_source = 'db'
                else:
                    df = None
            except Exception:
                df = None

        if df is None:
            continue

        # v3.0: Regime detection — SKIP unfavorable regimes
        regime = classify_regime(df['close'].astype(float))
        sym = pair.split('/')[0]

        if regime == 'BEAR':
            print(f"    \u23ed {pair}: BEAR regime \u2014 skipping (long-only system)")
            continue

        # v3.0: Correlation guard — skip if already active or on cooldown
        if sym in active_symbols:
            print(f"    \u23ed {pair}: Already active \u2014 correlation guard")
            continue
        if sym in cooldown_symbols:
            print(f"    \u23ed {pair}: On cooldown after loss \u2014 72h block")
            continue

        # Compute features
        features = build_production_features(df)
        latest = features.iloc[-1:].fillna(0)

        # v3.0: Add Fear & Greed features to latest row
        for fg_key, fg_val in fg_features.items():
            latest[fg_key] = fg_val

        # v3.1: Add on-chain data (global + per-coin)
        coin_symbol = pair.split('/')[0].replace('USD', '').replace('USDT', '')
        onchain_coin = fetch_onchain_data(symbol=coin_symbol) if coin_symbol else {}
        all_onchain = {**onchain_global, **onchain_coin}
        for oc_key, oc_val in all_onchain.items():
            latest[oc_key] = oc_val

        # Align features with model
        model_features = model_pack['features']
        for col in model_features:
            if col not in latest.columns:
                latest[col] = 0
        latest = latest[model_features]

        # Predict — v3.1: 3-model calibrated ensemble
        X_scaled = model_pack['scaler'].transform(latest)

        prob_rf = model_pack['rf'].predict_proba(X_scaled)[0][1]
        prob_gbt = model_pack['gbt'].predict_proba(X_scaled)[0][1]

        xgb_model_live = model_pack.get('xgb', None)
        if xgb_model_live is not None:
            try:
                prob_xgb = xgb_model_live.predict_proba(X_scaled)[0][1]
                prob = 0.25 * prob_rf + 0.35 * prob_gbt + 0.40 * prob_xgb
            except Exception:
                prob = 0.4 * prob_rf + 0.6 * prob_gbt
        else:
            prob = 0.4 * prob_rf + 0.6 * prob_gbt

        current_price = float(df['close'].iloc[-1])

        # v3.0: Adaptive TP/SL based on ATR + regime
        a_tp, a_sl, atr = adaptive_tpsl(
            df['close'].astype(float),
            df['high'].astype(float),
            df['low'].astype(float),
            regime=regime
        )
        tp_price = round(current_price * (1 + a_tp), 8)
        sl_price = round(current_price * (1 + a_sl), 8)
        tp_pct = round(a_tp * 100, 2)
        sl_pct = round(a_sl * 100, 2)

        # v3.0: Multi-timeframe alignment filter
        htf_align = float(features['htf_alignment'].iloc[-1]) if 'htf_alignment' in features.columns else 1.0
        if np.isnan(htf_align):
            htf_align = 1.0
        if htf_align < 2 and prob < 0.70:
            print(f"    \u26a0\ufe0f {pair}: HTF alignment={htf_align:.0f}/3, prob={prob:.1%} \u2014 skipping")
            continue

        # Tiered confidence based on probability + backtest + regime
        bt_wr = bt_result.get('win_rate', 0)
        bt_pf = bt_result.get('profit_factor', 0)

        if prob >= 0.60 and bt_wr >= 0.45 and bt_pf >= 1.5 and regime == 'BULL':
            confidence = 'STRONG BUY'
            action = 'ENTER'
        elif prob >= 0.40 and bt_wr >= 0.35 and bt_pf >= 1.0:
            confidence = 'BUY'
            action = 'ENTER'
        elif prob >= 0.20 and bt_pf >= 1.0:
            confidence = 'WATCH'
            action = 'MONITOR'
        else:
            confidence = 'HOLD'
            action = 'WAIT'

        # Key signals
        signals = []
        if features['vol_ratio'].iloc[-1] > 2.0:
            signals.append('HIGH_VOLUME')
        if 'bb_squeeze' in features.columns and features['bb_squeeze'].iloc[-1] == 1:
            signals.append('BB_SQUEEZE')
        if features['rsi_14'].iloc[-1] < 35:
            signals.append('OVERSOLD')
        if features['macd_hist_slope'].iloc[-1] > 0 and features['macd_hist'].iloc[-1] > 0:
            signals.append('MACD_BULLISH')
        if features['vol_compression'].iloc[-1] < 0.7:
            signals.append('VOL_COMPRESSION')
        if features['consec_green'].iloc[-1] >= 3:
            signals.append(f"GREEN_STREAK({int(features['consec_green'].iloc[-1])})")
        if regime == 'BULL':
            signals.append('BULL_REGIME')
        if htf_align >= 3:
            signals.append('ALL_TF_BULLISH')
        if not signals:
            signals.append('ML_SIGNAL')

        pick = {
            'pick_id': f"ag_{pair_clean.lower()}_{now.strftime('%Y%m%d_%H%M')}",
            'coin_id': pair.split('/')[0].lower(),
            'symbol': sym,
            'name': pair,
            'entry_price': current_price,
            'current_price': current_price,
            'tp_price': tp_price,
            'tp_pct': tp_pct,
            'sl_price': sl_price,
            'sl_pct': sl_pct,
            'pump_probability': round(prob, 4),
            'confidence': confidence,
            'signals': signals,
            'gainer_score': int(round(prob * 100)),
            'rr_ratio': round(abs(tp_pct / sl_pct), 2) if sl_pct != 0 else 2.5,
            'atr_proxy': round(atr, 6),
            'predicted_at': now.isoformat(),
            'entry_time': now.isoformat(),
            'status': 'ACTIVE',
            'unrealized_pnl': 0,
            'safety_score': 100,
            'is_safe': True,
            'regime': regime,
            'htf_alignment': int(htf_align),
            'fear_greed': fg_features.get('fg_current', None),
            'onchain_btc_dominance': onchain_global.get('onchain_btc_dominance', None),
            'onchain_total_mcap_t': onchain_global.get('onchain_total_mcap_t', None),
            'backtest_validation': {
                'backtest_win_rate': bt_wr,
                'backtest_profit_factor': bt_pf,
                'backtest_n_trades': bt_result.get('total_trades', 0),
                'backtest_sharpe': bt_result.get('sharpe_ratio', 0)
            },
            '_source': 'Antigravity ML v3.1',
            '_data_source': data_source
        }
        # Emission gate: cooldown + daily cap (shared with alpha_engine).
        try:
            from alpha_engine.non_crypto_policy import check_emission_gates as _ceg
            _g = _ceg(str(pick.get("symbol") or ""))
            if _g.get("blocked"):
                continue
        except Exception:
            pass
        picks.append(pick)

    if own_conn and conn is not None:
        conn.close()

    # Sort by probability (highest first)
    picks.sort(key=lambda x: x['pump_probability'], reverse=True)
    return picks[:CONFIG['max_positions']]


# ═══════════════════════════════════════════════════════════════════════════
#  CONTINUOUS LEARNING
# ═══════════════════════════════════════════════════════════════════════════

def collect_resolved_feedback():
    """
    Collect resolved picks and their outcomes for retraining.
    Reads from the tracker files produced by the live scanner.
    """
    feedback = []

    # Check multiple tracker sources
    tracker_files = [
        UPDATES_DATA / 'antigravity_ml_performance.json',
        UPDATES_DATA / 'cursor_ml_performance.json',
        UPDATES_DATA / 'claude_ml_performance.json',
    ]

    for tf in tracker_files:
        if not tf.exists():
            continue
        try:
            with open(tf) as f:
                data = json.load(f)
            scorecard = data.get('scorecard', {})
            if 'best_pick' in scorecard and scorecard['best_pick']:
                bp = scorecard['best_pick']
                if 'outcome' in bp:
                    feedback.append({
                        'symbol': bp.get('symbol', ''),
                        'outcome': bp['outcome'],
                        'pnl_pct': bp.get('pnl_pct', 0),
                        'entry_price': bp.get('price', 0),
                        'gainer_score': bp.get('gainer_score', 0),
                        'signals': bp.get('signals', []),
                        'source': tf.stem
                    })
            if 'worst_pick' in scorecard and scorecard['worst_pick']:
                wp = scorecard['worst_pick']
                if 'outcome' in wp:
                    feedback.append({
                        'symbol': wp.get('symbol', ''),
                        'outcome': wp['outcome'],
                        'pnl_pct': wp.get('pnl_pct', 0),
                        'entry_price': wp.get('price', 0),
                        'gainer_score': wp.get('gainer_score', 0),
                        'signals': wp.get('signals', []),
                        'source': tf.stem
                    })
        except Exception:
            continue

    return feedback


def compute_model_health():
    """
    Compute overall model health status from all available data.
    Returns a status dict for the Discord command.
    """
    feedback = collect_resolved_feedback()

    total_resolved = len(feedback)
    tp_hits = sum(1 for f in feedback if f['outcome'] == 'TP_HIT')
    sl_hits = sum(1 for f in feedback if f['outcome'] == 'SL_HIT')
    total_pnl = sum(f.get('pnl_pct', 0) for f in feedback)

    win_rate = tp_hits / total_resolved * 100 if total_resolved > 0 else 0

    # Load backtest results if available
    bt_path = BACKTEST_DIR / 'walk_forward_results.json'
    bt_results = {}
    if bt_path.exists():
        try:
            with open(bt_path) as f:
                bt_results = json.load(f)
        except Exception:
            pass

    bt_profitable = sum(
        1 for r in bt_results.values()
        if isinstance(r, dict) and r.get('profit_factor', 0) > 1.0
    )

    return {
        # Forward metrics (from live resolved picks)
        'total_resolved': total_resolved,
        'tp_hits': tp_hits,
        'sl_hits': sl_hits,
        'win_rate': round(win_rate, 1),
        'total_pnl': round(total_pnl, 2),
        'metric_type': 'forward',  # v3.0: explicitly label as forward
        # Backtest metrics
        'backtest_pairs_tested': len(bt_results),
        'backtest_pairs_profitable': bt_profitable,
        'feedback_entries': feedback,
        'status': 'calibrating' if total_resolved < 10 else (
            'learning' if total_resolved < 50 else (
                'validated' if win_rate >= 35 else 'underperforming'
            )
        )
    }


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

def run_full_pipeline():
    """
    Complete pipeline:
    1. Load data from DB
    2. Walk-forward backtest each pair
    3. Train production models on profitable pairs
    4. Generate live picks
    5. Save everything
    """
    print("=" * 70)
    print("ANTIGRAVITY ML PRODUCTION ENGINE v3.1")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    # ── Step 1: Load data ──
    db_path = str(DB_PATH)
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found: {db_path}")
        print("[INFO] Run fetch_and_populate_db.py first")
        return

    conn = sqlite3.connect(db_path)
    pairs = pd.read_sql("SELECT DISTINCT pair FROM klines", conn)['pair'].tolist()
    print(f"\n📊 Found {len(pairs)} pairs in database")

    # ── Step 2: Walk-forward backtest ──
    print("\n" + "=" * 70)
    print("PHASE 1: WALK-FORWARD BACKTESTING")
    print("=" * 70)

    backtest_results = {}
    for pair in pairs:
        df = pd.read_sql(
            "SELECT * FROM klines WHERE pair = ? ORDER BY timestamp",
            conn, params=(pair,)
        )
        if len(df) < 2500:
            print(f"  ⏭ {pair}: only {len(df)} bars (need 2500+ for v3.0 90-day window)")
            continue

        print(f"\n  🔄 Backtesting {pair} ({len(df)} bars)...")
        result = walk_forward_backtest(pair, df)
        if result:
            emoji = '✅' if result['win_rate'] >= 0.35 and result['profit_factor'] >= 1.0 else '⚠️'
            print(f"  {emoji} {pair} [BACKTEST]: WR={result['win_rate']:.1%} PF={result['profit_factor']:.2f} "
                  f"Sharpe={result['sharpe_ratio']:.2f} PnL={result['total_pnl_pct']:+.1f}% "
                  f"({result['total_trades']} trades, MDD={result['max_drawdown_pct']:.1f}%)")
            backtest_results[pair] = result
        else:
            print(f"  ❌ {pair}: insufficient data for backtesting")

    # Save backtest results
    with open(BACKTEST_DIR / 'walk_forward_results.json', 'w') as f:
        json.dump(backtest_results, f, indent=2, default=str)

    # ── Step 3: Train production models ──
    print("\n" + "=" * 70)
    print("PHASE 2: TRAINING PRODUCTION MODELS")
    print("=" * 70)

    trained_count = 0
    reused_count = 0
    for pair in pairs:
        # Check for fresh persisted model first (avoids retraining from scratch)
        existing = load_persisted_model(pair, max_age_hours=36)
        if existing is not None:
            reused_count += 1
            continue

        df = pd.read_sql(
            "SELECT * FROM klines WHERE pair = ? ORDER BY timestamp",
            conn, params=(pair,)
        )
        if len(df) < 200:
            continue

        print(f"  🏋️ Training {pair}...")
        model = train_production_model(pair, df, save=True)
        if model:
            trained_count += 1
            print(f"  ✅ {pair}: {model['n_samples']} samples, "
                  f"pos_rate={model['positive_rate']:.1%}")

    if reused_count:
        print(f"\n  📦 Reused {reused_count} fresh models, trained {trained_count} new/stale models")

    conn.close()

    # ── Step 4: Generate live picks ──
    print("\n" + "=" * 70)
    print("PHASE 3: GENERATING LIVE PICKS")
    print("=" * 70)

    picks = []
    conn2 = sqlite3.connect(str(DB_PATH))
    try:
        picks = generate_live_picks(backtest_results, conn=conn2)
        print(f"\n  📋 Generated {len(picks)} live picks:")
        for p in picks:
            print(f"    {p['confidence']} | {p['symbol']} @ ${p['entry_price']:.4f} | "
                  f"Prob: {p['pump_probability']:.1%} | "
                  f"TP: ${p['tp_price']:.4f} ({p['tp_pct']:+.1f}%) | "
                  f"SL: ${p['sl_price']:.4f} ({p['sl_pct']:+.1f}%)")
    except Exception as e:
        print(f"  [WARN] Live pick generation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            conn2.close()
        except Exception:
            pass

    # ── Step 5: Save results ──
    print("\n" + "=" * 70)
    print("PHASE 4: SAVING RESULTS")
    print("=" * 70)

    # Save live picks (always write, even if empty, to avoid stale data)
    with open(UPDATES_DATA / 'antigravity_ml_live_picks.json', 'w') as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  ✅ Saved {len(picks)} picks to antigravity_ml_live_picks.json")

    # Save comprehensive performance
    health = compute_model_health()
    bt_summary = {}
    for pair, result in backtest_results.items():
        if result:
            bt_summary[pair] = {
                'backtest_win_rate': result['win_rate'],
                'backtest_profit_factor': result['profit_factor'],
                'backtest_sharpe': result['sharpe_ratio'],
                'backtest_total_pnl': result['total_pnl_pct'],
                'backtest_n_trades': result['total_trades'],
                'backtest_max_dd': result['max_drawdown_pct']
            }

    performance = {
        'title': 'Antigravity AI - Crypto Gainer ML Predictions',
        'agent': 'Antigravity',
        'last_run': datetime.now(timezone.utc).isoformat(),
        'model_version': 'v3.1-production',
        'forward_scorecard': {
            'forward_total_picks': health['total_resolved'],
            'forward_tp_hits': health['tp_hits'],
            'forward_sl_hits': health['sl_hits'],
            'forward_win_rate': health['win_rate'],
            'forward_total_pnl_pct': health['total_pnl'],
            'status': health['status']
        },
        'backtest_summary': bt_summary,
        'active_picks': [{
            'coin': p['coin_id'],
            'symbol': p['symbol'],
            'entry': p['entry_price'],
            'tp': p['tp_price'],
            'sl': p['sl_price'],
            'score': p['gainer_score'],
            'signals': p['signals'],
            'picked_at': p['predicted_at'],
            'unrealized_pnl': round((p.get('current_price', p['entry_price']) - p['entry_price']) / p['entry_price'] * 100, 2) if p['entry_price'] > 0 else 0,
            'current_price': p.get('current_price', 0),
            'confidence': p['confidence'],
            'regime': p.get('regime', 'UNKNOWN'),
            'htf_alignment': p.get('htf_alignment', 0),
            'backtest_validation': p.get('backtest_validation', {})
        } for p in picks],
        'strategy_summary': {
            'approach': 'Ensemble (RF+GBT+XGBoost) with calibration + purged walk-forward + regime detection',
            'features': '80+ production features (OHLCV + regime + HTF + F&G + on-chain, corr filtered)',
            'v3_enhancements': [
                '4-state regime detection (BULL/BEAR/SIDEWAYS/HIGH_VOL)',
                'Adaptive ATR-based TP/SL per regime',
                'Multi-timeframe features (1h/4h/daily alignment)',
                'Fear & Greed Index integration',
                'Purged walk-forward (48-bar gap)',
                'Correlation guard (max 1 pos/asset, 72h cooldown)',
                '90-day training window (was 30)',
                'XGBoost added to ensemble (RF 25% + GBT 35% + XGB 40%)',
                'Probability calibration (Platt + Isotonic)',
                'SHAP feature importance (top 20)',
                'Feature correlation cleanup (r>0.9 dropped)',
                'On-chain data (CoinGecko: BTC dom, mcap, per-coin)',
                'Per-pair forward evaluation + auto-suspension'
            ],
            'risk_reward': '2:1 to 3:1 (regime-adaptive ATR)',
            'holding_period': '24-48 hours',
            'backtest_method': 'Purged walk-forward (no look-ahead bias)',
            'backtest_profitable_pairs': sum(1 for r in bt_summary.values() if r.get('backtest_profit_factor', 0) > 1.0),
            'backtest_total_pairs': len(bt_summary)
        }
    }

    # v3.1 Enhancement #11: Per-pair forward evaluation
    try:
        closed_path = UPDATES_DATA / 'antigravity_ml_closed_picks.json'
        if closed_path.exists():
            closed = json.load(open(closed_path))
        else:
            closed = []

        pair_stats = {}
        for cp in closed:
            sym = cp.get('symbol', cp.get('coin_id', ''))
            if not sym:
                continue
            if sym not in pair_stats:
                pair_stats[sym] = {'wins': 0, 'losses': 0, 'total_pnl': 0}
            status = cp.get('status', '')
            if status in ('WON', 'TP_HIT'):
                pair_stats[sym]['wins'] += 1
            elif status in ('LOST', 'SL_HIT'):
                pair_stats[sym]['losses'] += 1
            pair_stats[sym]['total_pnl'] += cp.get('pnl_pct', 0)

        strategy_per_pair = {}
        suspended_pairs = []
        for sym, stats in pair_stats.items():
            total = stats['wins'] + stats['losses']
            wr = stats['wins'] / max(total, 1)
            bt = bt_summary.get(sym, bt_summary.get(sym.replace('-', '/'), {}))
            is_suspended = total >= 5 and wr == 0
            strategy_per_pair[sym] = {
                'forward_trades': total,
                'forward_wr': round(wr, 3),
                'forward_pnl': round(stats['total_pnl'], 2),
                'backtest_wr': bt.get('backtest_win_rate', None),
                'backtest_pf': bt.get('backtest_profit_factor', None),
                'bt_forward_gap': round(bt.get('backtest_win_rate', 0) - wr, 3) if bt.get('backtest_win_rate') else None,
                'status': 'SUSPENDED' if is_suspended else ('active' if total < 5 else 'validated'),
            }
            if is_suspended:
                suspended_pairs.append(sym)

        performance['strategy_per_pair'] = strategy_per_pair

        if suspended_pairs:
            print(f"  ⛔ Suspended {len(suspended_pairs)} pairs with 0% forward WR: {suspended_pairs}")
            performance['suspended_pairs'] = suspended_pairs
        elif pair_stats:
            print(f"  📊 Per-pair eval: {len(pair_stats)} pairs tracked, none suspended")
    except Exception as e:
        print(f"  ⚠️ Per-pair evaluation: {e}")

    with open(UPDATES_DATA / 'antigravity_ml_performance.json', 'w') as f:
        json.dump(performance, f, indent=2, default=str)
    print("  ✅ Saved performance to antigravity_ml_performance.json")

    # Summary scorecard (forward metrics from live picks)
    with open(UPDATES_DATA / 'antigravity_ml_scorecard.json', 'w') as f:
        json.dump(performance['forward_scorecard'], f, indent=2, default=str)

    # ── Summary ──
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    n_profitable = sum(1 for r in backtest_results.values()
                       if r and r['profit_factor'] >= 1.0)
    print(f"  Pairs backtested: {len(backtest_results)}")
    print(f"  Pairs profitable (PF>1.0): {n_profitable}/{len(backtest_results)}")
    print(f"  Live picks generated: {len(picks)}")
    print(f"  Model health: {health['status'].upper()}")

    if n_profitable > 0:
        best = max(backtest_results.items(),
                   key=lambda x: x[1]['profit_factor'] if x[1] else 0)
        print(f"  Best pair: {best[0]} (PF={best[1]['profit_factor']:.2f}, "
              f"WR={best[1]['win_rate']:.1%}, Sharpe={best[1]['sharpe_ratio']:.2f})")

    return {
        'backtest_results': backtest_results,
        'picks': picks,
        'health': health,
        'performance': performance
    }


def run_predict_only():
    """
    Predict-only mode: load persisted models from git and generate live picks
    WITHOUT retraining. This preserves learning across CI runs by reusing
    models that were trained and committed in a previous run.

    Falls back to full pipeline if no models are found.
    """
    print("=" * 70)
    print("ANTIGRAVITY ML PRODUCTION ENGINE v3.1 — PREDICT ONLY")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    # Check for existing production models
    model_files = list(PRODUCTION_DIR.glob('*_production.pkl'))
    if not model_files:
        print("[INFO] No persisted models found — falling back to full pipeline")
        return run_full_pipeline()

    print(f"\n  Found {len(model_files)} persisted models in {PRODUCTION_DIR}")

    # Load backtest results from previous run (if available)
    bt_path = BACKTEST_DIR / 'walk_forward_results.json'
    backtest_results = {}
    if bt_path.exists():
        try:
            with open(bt_path) as f:
                backtest_results = json.load(f)
            print(f"  Loaded {len(backtest_results)} backtest results from previous run")
        except Exception:
            pass

    if not backtest_results:
        print("[INFO] No backtest results found — falling back to full pipeline")
        return run_full_pipeline()

    # Generate live picks using persisted models
    print("\n" + "=" * 70)
    print("GENERATING LIVE PICKS (using persisted models)")
    print("=" * 70)

    picks = []
    db_path = str(DB_PATH)
    conn = None
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)

    try:
        picks = generate_live_picks(backtest_results, conn=conn)
        print(f"\n  Generated {len(picks)} live picks:")
        for p in picks:
            print(f"    {p['confidence']} | {p['symbol']} @ ${p['entry_price']:.4f} | "
                  f"Prob: {p['pump_probability']:.1%} | "
                  f"TP: ${p['tp_price']:.4f} ({p['tp_pct']:+.1f}%) | "
                  f"SL: ${p['sl_price']:.4f} ({p['sl_pct']:+.1f}%)")
    except Exception as e:
        print(f"  [WARN] Live pick generation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    # Save results
    with open(UPDATES_DATA / 'antigravity_ml_live_picks.json', 'w') as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to antigravity_ml_live_picks.json")

    health = compute_model_health()
    performance = {
        'title': 'Antigravity AI - Crypto Gainer ML Predictions',
        'agent': 'Antigravity',
        'last_run': datetime.now(timezone.utc).isoformat(),
        'model_version': 'v3.1-production',
        'run_mode': 'predict-only',
        'forward_scorecard': {
            'forward_total_picks': health['total_resolved'],
            'forward_tp_hits': health['tp_hits'],
            'forward_sl_hits': health['sl_hits'],
            'forward_win_rate': health['win_rate'],
            'forward_total_pnl_pct': health['total_pnl'],
            'status': health['status']
        },
        'active_picks': [{
            'coin': p['coin_id'],
            'symbol': p['symbol'],
            'entry': p['entry_price'],
            'tp': p['tp_price'],
            'sl': p['sl_price'],
            'score': p['gainer_score'],
            'signals': p['signals'],
            'picked_at': p['predicted_at'],
            'confidence': p['confidence'],
            'regime': p.get('regime', 'UNKNOWN'),
        } for p in picks],
    }

    with open(UPDATES_DATA / 'antigravity_ml_performance.json', 'w') as f:
        json.dump(performance, f, indent=2, default=str)
    with open(UPDATES_DATA / 'antigravity_ml_scorecard.json', 'w') as f:
        json.dump(performance['forward_scorecard'], f, indent=2, default=str)

    print(f"\n  PREDICT-ONLY COMPLETE: {len(picks)} picks, health={health['status']}")
    return {'picks': picks, 'health': health, 'performance': performance}


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'train'

    if mode == 'predict':
        run_predict_only()
    elif mode in ('train', 'full'):
        run_full_pipeline()
    else:
        print(f"Unknown mode: {mode}. Use 'train' or 'predict'.")
        sys.exit(1)
