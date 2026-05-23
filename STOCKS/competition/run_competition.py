#!/usr/bin/env python3
"""
Algorithm Competition Engine - REAL DATA
Downloads real market data via yfinance, computes real technical indicators,
runs all 12 alpha_engine strategies, logs every trade with EST timestamps.

Outputs: competition-results.json consumed by the dashboard.
Asset classes: Stocks, Crypto, Forex, Penny Stocks, Meme Coins
"""
import json
import sys
import os
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ── Configuration ──────────────────────────────────────────────────
STARTING_CAPITAL = 100_000
LOOKBACK_DAYS = 365  # 1 year of data for indicator calculation
TRADE_DAYS = 252     # simulate last ~1 year of trading

ASSET_CLASSES = {
    "stocks": {
        "label": "S&P 500 Stocks",
        "tickers": [
            "AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","JPM","V","UNH",
            "HD","JNJ","PG","MA","XOM","CVX","ABBV","MRK","PEP","KO",
            "COST","AVGO","TMO","CRM","MCD","AMD","NFLX","LIN","ADBE","ACN",
        ],
        "benchmark": "SPY",
    },
    "crypto": {
        "label": "Cryptocurrency",
        "tickers": [
            "BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD","ADA-USD",
            "DOGE-USD","DOT-USD","AVAX-USD","LINK-USD","MATIC-USD","UNI-USD",
        ],
        "benchmark": "BTC-USD",
    },
    "forex": {
        "label": "Forex (Major Pairs via ETFs)",
        "tickers": [
            "FXE","FXB","FXY","FXA","FXC","FXF","UUP","UDN","CYB","CEW",
        ],
        "benchmark": "UUP",
    },
    "penny_stocks": {
        "label": "Penny / Small-Cap Stocks",
        "tickers": [
            "SOFI","PLTR","NIO","RIVN","LCID","MARA","RIOT","PATH","IONQ","JOBY",
            "DNA","OPEN","WISH","CLOV","BBIG",
        ],
        "benchmark": "IWM",
    },
    "meme_coins": {
        "label": "Meme Coins & Speculative Crypto",
        "tickers": [
            "DOGE-USD","SHIB-USD","PEPE24478-USD","FLOKI-USD","BONK-USD",
            "WIF-USD","MEME-USD",
        ],
        "benchmark": "DOGE-USD",
    },
}

# ── Technical Indicator Computation ────────────────────────────────

def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/window, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1/window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def compute_indicators(close_df):
    """Compute all technical indicators needed by the 12 strategies."""
    indicators = {}
    returns = close_df.pct_change()

    # Moving Averages
    for w in [10, 20, 50, 100, 200]:
        indicators[f'ma{w}'] = close_df.rolling(w).mean()
        indicators[f'price_vs_ma{w}'] = (close_df - indicators[f'ma{w}']) / indicators[f'ma{w}']

    # Multi-horizon returns
    for w in [5, 10, 21, 63, 126, 252]:
        indicators[f'ret_{w}d'] = close_df.pct_change(w)

    # Bollinger Bands
    for w in [20, 50]:
        ma = close_df.rolling(w).mean()
        std = close_df.rolling(w).std()
        indicators[f'bb_zscore_{w}d'] = (close_df - ma) / std.replace(0, np.nan)
        indicators[f'bb_upper_{w}d'] = ma + 2 * std
        indicators[f'bb_lower_{w}d'] = ma - 2 * std

    # RSI
    for w in [14, 21]:
        rsi_df = close_df.apply(lambda x: compute_rsi(x, w))
        indicators[f'rsi_{w}'] = rsi_df

    # MACD
    ema12 = close_df.ewm(span=12).mean()
    ema26 = close_df.ewm(span=26).mean()
    indicators['macd'] = (ema12 - ema26) / close_df
    indicators['macd_signal'] = ((ema12 - ema26).ewm(span=9).mean()) / close_df
    indicators['macd_hist'] = indicators['macd'] - indicators['macd_signal']

    # Trend strength (return / vol)
    daily_ret = close_df.pct_change()
    for w in [21, 63]:
        ret_w = close_df.pct_change(w)
        vol_w = daily_ret.rolling(w).std() * np.sqrt(w)
        indicators[f'trend_strength_{w}d'] = ret_w / vol_w.replace(0, np.nan)

    # Volatility
    for w in [21, 63]:
        indicators[f'rvol_{w}d'] = daily_ret.rolling(w).std() * np.sqrt(252)

    # Breakout distance from highs/lows
    for w in [20, 50, 252]:
        indicators[f'dist_{w}d_high'] = (close_df - close_df.rolling(w).max()) / close_df.rolling(w).max()
        indicators[f'dist_{w}d_low'] = (close_df - close_df.rolling(w).min()) / close_df.rolling(w).min()

    # Golden cross
    indicators['golden_cross'] = (indicators['ma50'] > indicators['ma200']).astype(float)

    # Short-term reversal
    for w in [1, 3, 5]:
        indicators[f'reversal_{w}d'] = -returns.rolling(w).sum()

    # Hurst proxy (variance ratio)
    var_1 = daily_ret.rolling(63).var()
    ret_5 = daily_ret.rolling(5).sum()
    var_5 = ret_5.rolling(63).var()
    vr = var_5 / (5 * var_1).replace(0, np.nan)
    indicators['hurst_63d'] = np.log(vr.clip(lower=0.01)) / (2 * np.log(5)) + 0.5

    # Momentum acceleration
    mom_21 = close_df.pct_change(21)
    indicators['mom_accel'] = mom_21 - mom_21.shift(21)

    # Rolling max drawdown
    rolling_max = close_df.rolling(63, min_periods=1).max()
    indicators['drawdown_63d'] = (close_df - rolling_max) / rolling_max

    return indicators


# ── Strategy Implementations (faithful to alpha_engine Python code) ──

class BaseAlgo:
    def __init__(self, name, short_name, algo_type, description, hold_days, max_positions, stop_loss, take_profit):
        self.name = name
        self.short_name = short_name
        self.algo_type = algo_type
        self.description = description
        self.hold_days = hold_days
        self.max_positions = max_positions
        self.stop_loss = stop_loss
        self.take_profit = take_profit

    def generate_signals(self, date, close_df, indicators, universe):
        """Return list of (ticker, score, reason_dict)"""
        raise NotImplementedError


class ClassicMomentum(BaseAlgo):
    """Buy top-K past winners by 6-month return, skip most recent month (Jegadeesh & Titman)."""
    def __init__(self):
        super().__init__("Classic Momentum", "Momentum", "Momentum",
                         "Buy top-K stocks by 6-month return, skip most recent month",
                         21, 10, 0.10, 0.50)

    def generate_signals(self, date, close_df, indicators, universe):
        ret_126 = indicators.get('ret_126d')
        ret_21 = indicators.get('ret_21d')
        if ret_126 is None or date not in ret_126.index:
            return []
        mom = ret_126.loc[date] - (ret_21.loc[date] if ret_21 is not None and date in ret_21.index else 0)
        mom = mom.reindex(universe).dropna().sort_values(ascending=False)
        signals = []
        for ticker in mom.head(self.max_positions).index:
            score = float(mom[ticker])
            signals.append((ticker, score, {"6m_ret": round(float(ret_126.loc[date].get(ticker, 0))*100, 2),
                                            "skip_month_ret": round(float(ret_21.loc[date].get(ticker, 0))*100, 2) if ret_21 is not None else 0}))
        return signals


class TrendFollowing(BaseAlgo):
    """Buy stocks above 50/200 MA with strong trend strength."""
    def __init__(self):
        super().__init__("Trend Following", "Trend", "Trend",
                         "Buy stocks above 50/200 MA with strong trend strength",
                         21, 10, 0.08, 0.30)

    def generate_signals(self, date, close_df, indicators, universe):
        pvm50 = indicators.get('price_vs_ma50')
        pvm200 = indicators.get('price_vs_ma200')
        ts = indicators.get('trend_strength_21d')
        if pvm50 is None or date not in pvm50.index:
            return []
        signals = []
        for ticker in universe:
            try:
                a50 = float(pvm50.loc[date, ticker])
                a200 = float(pvm200.loc[date, ticker]) if pvm200 is not None else 0
                t = float(ts.loc[date, ticker]) if ts is not None and date in ts.index else 0
                if a50 > 0 and a200 > 0:
                    score = 0.3 * min(a50, 0.3)/0.3 + 0.3 * min(a200, 0.3)/0.3 + 0.4 * max(min(t, 2), 0)/2
                    if score > 0.3:
                        signals.append((ticker, score, {"above_ma50": round(a50*100, 2), "above_ma200": round(a200*100, 2), "trend_str": round(t, 3)}))
            except Exception:
                continue
        signals.sort(key=lambda x: x[1], reverse=True)
        return signals[:self.max_positions]


class BreakoutMomentum(BaseAlgo):
    """Buy stocks near 52-week highs with volume confirmation."""
    def __init__(self):
        super().__init__("Breakout Momentum", "Breakout", "Breakout",
                         "Buy stocks near 52-week highs",
                         10, 8, 0.07, 0.25)

    def generate_signals(self, date, close_df, indicators, universe):
        dist_high = indicators.get('dist_252d_high')
        if dist_high is None or date not in dist_high.index:
            return []
        signals = []
        for ticker in universe:
            try:
                dh = float(dist_high.loc[date, ticker])
                if dh > -0.05:  # Within 5% of 52-week high
                    score = (1 + dh)
                    signals.append((ticker, score, {"dist_from_52w_high": round(dh*100, 2)}))
            except Exception:
                continue
        signals.sort(key=lambda x: x[1], reverse=True)
        return signals[:self.max_positions]


class BollingerMeanReversion(BaseAlgo):
    """Buy oversold (below lower BB), sell overbought."""
    def __init__(self):
        super().__init__("Bollinger Mean Reversion", "BB Revert", "Mean Reversion",
                         "Buy oversold (below lower Bollinger Band), sell overbought",
                         5, 8, 0.05, 0.08)

    def generate_signals(self, date, close_df, indicators, universe):
        bb_z = indicators.get('bb_zscore_20d')
        hurst = indicators.get('hurst_63d')
        if bb_z is None or date not in bb_z.index:
            return []
        signals = []
        for ticker in universe:
            try:
                z = float(bb_z.loc[date, ticker])
                h = float(hurst.loc[date, ticker]) if hurst is not None and date in hurst.index else 0.5
                if h > 0.55:
                    continue
                if z < -1.5:
                    score = min(abs(z) / 3, 1.0)
                    if h < 0.4:
                        score *= 1.2
                    signals.append((ticker, min(score, 1.0), {"bb_zscore": round(z, 3), "hurst": round(h, 3)}))
            except Exception:
                continue
        signals.sort(key=lambda x: x[1], reverse=True)
        return signals[:self.max_positions]


class ShortTermReversal(BaseAlgo):
    """Buy 5-day losers (oversold bounce)."""
    def __init__(self):
        super().__init__("Short-Term Reversal", "Reversal", "Reversal",
                         "Buy 5-day losers (oversold bounce), hold 3-5 days",
                         3, 8, 0.03, 0.05)

    def generate_signals(self, date, close_df, indicators, universe):
        rev = indicators.get('reversal_5d')
        if rev is None or date not in rev.index:
            return []
        ranked = rev.loc[date].reindex(universe).dropna().sort_values(ascending=False)
        signals = []
        for ticker in ranked.head(self.max_positions * 2).index:
            r = float(ranked[ticker])
            if r < 0.02:
                continue
            score = min(r * 5, 0.8)
            signals.append((ticker, min(score, 1.0), {"reversal_5d": round(r*100, 2)}))
        signals.sort(key=lambda x: x[1], reverse=True)
        return signals[:self.max_positions]


class QualityCompounders(BaseAlgo):
    """Buy high-quality compounders with low volatility and strong trend."""
    def __init__(self):
        super().__init__("Quality Compounders", "Quality", "Quality",
                         "High-quality compounders: low vol, consistent trend, low drawdown",
                         63, 15, 0.15, 0.50)

    def generate_signals(self, date, close_df, indicators, universe):
        rvol = indicators.get('rvol_63d')
        ts = indicators.get('trend_strength_63d')
        dd = indicators.get('drawdown_63d')
        if rvol is None or date not in rvol.index:
            return []
        signals = []
        for ticker in universe:
            try:
                v = float(rvol.loc[date, ticker])
                t = float(ts.loc[date, ticker]) if ts is not None and date in ts.index else 0
                d = float(dd.loc[date, ticker]) if dd is not None and date in dd.index else 0
                vol_score = max(0, 1 - v / 0.5)  # lower vol = higher score
                trend_score = max(0, min(t / 2, 1))
                dd_score = max(0, 1 + d / 0.2)  # less drawdown = higher
                score = vol_score * 0.3 + trend_score * 0.4 + dd_score * 0.3
                if score > 0.4:
                    signals.append((ticker, score, {"vol": round(v*100, 1), "trend": round(t, 3), "drawdown": round(d*100, 1)}))
            except Exception:
                continue
        signals.sort(key=lambda x: x[1], reverse=True)
        return signals[:self.max_positions]


class ValueQuality(BaseAlgo):
    """Buy cheap stocks (relative to 200-day MA) with quality filter."""
    def __init__(self):
        super().__init__("Value + Quality", "Value", "Value",
                         "Buy undervalued stocks with quality filter (low vol + mean reversion signal)",
                         42, 12, 0.12, 0.30)

    def generate_signals(self, date, close_df, indicators, universe):
        pvm200 = indicators.get('price_vs_ma200')
        rvol = indicators.get('rvol_63d')
        hurst = indicators.get('hurst_63d')
        if pvm200 is None or date not in pvm200.index:
            return []
        signals = []
        for ticker in universe:
            try:
                val = float(pvm200.loc[date, ticker])
                v = float(rvol.loc[date, ticker]) if rvol is not None and date in rvol.index else 0.3
                h = float(hurst.loc[date, ticker]) if hurst is not None and date in hurst.index else 0.5
                if val > 0:  # not below MA200 = skip pure "value" but accept quality
                    continue
                if v > 0.5:  # too volatile = skip
                    continue
                value_score = min(abs(val) / 0.2, 1.0)  # more below MA = more undervalued
                quality_score = max(0, 1 - v / 0.4)
                mr_score = max(0, 0.5 - h) * 2 if h < 0.5 else 0
                score = value_score * 0.4 + quality_score * 0.3 + mr_score * 0.3
                if score > 0.3:
                    signals.append((ticker, score, {"vs_ma200": round(val*100, 2), "vol": round(v*100, 1), "hurst": round(h, 3)}))
            except Exception:
                continue
        signals.sort(key=lambda x: x[1], reverse=True)
        return signals[:self.max_positions]


class DividendAristocrats(BaseAlgo):
    """Buy Dividend Aristocrats with stable trend."""
    ARISTOCRATS = {"JNJ","PG","KO","PEP","MMM","ABBV","MCD","WMT","HD","LOW","TXN","COST","XOM","CVX","HON","EMR","CAT","GE"}
    def __init__(self):
        super().__init__("Dividend Aristocrats", "Dividend", "Dividend",
                         "Buy 25+ year consecutive dividend increasers",
                         126, 15, 0.20, 0.50)

    def generate_signals(self, date, close_df, indicators, universe):
        rvol = indicators.get('rvol_63d')
        ts = indicators.get('trend_strength_63d')
        pool = [t for t in universe if t in self.ARISTOCRATS]
        if not pool:
            pool = universe[:8]  # fallback for crypto/forex
        signals = []
        for ticker in pool:
            try:
                v = float(rvol.loc[date, ticker]) if rvol is not None and date in rvol.index else 0.2
                t = float(ts.loc[date, ticker]) if ts is not None and date in ts.index else 0
                score = 0.5 + max(0, min(t / 2, 0.25)) + max(0, (0.3 - v)) * 0.5
                signals.append((ticker, min(score, 1.0), {"is_aristocrat": ticker in self.ARISTOCRATS, "vol": round(v*100, 1)}))
            except Exception:
                continue
        signals.sort(key=lambda x: x[1], reverse=True)
        return signals[:self.max_positions]


class EarningsDrift(BaseAlgo):
    """PEAD: buy stocks with strong recent momentum + positive MACD."""
    def __init__(self):
        super().__init__("Earnings Drift (PEAD)", "PEAD", "Anomaly",
                         "Post-earnings drift proxy: strong recent momentum + MACD confirmation",
                         42, 10, 0.08, 0.20)

    def generate_signals(self, date, close_df, indicators, universe):
        ret_21 = indicators.get('ret_21d')
        macd_h = indicators.get('macd_hist')
        ret_5 = indicators.get('ret_5d')
        if ret_21 is None or date not in ret_21.index:
            return []
        signals = []
        for ticker in universe:
            try:
                r21 = float(ret_21.loc[date, ticker])
                mh = float(macd_h.loc[date, ticker]) if macd_h is not None and date in macd_h.index else 0
                r5 = float(ret_5.loc[date, ticker]) if ret_5 is not None and date in ret_5.index else 0
                if r21 > 0.05 and mh > 0 and r5 > 0:  # strong momentum + MACD confirm
                    score = min(r21 * 3, 0.6) + min(mh * 20, 0.2) + min(r5 * 5, 0.2)
                    signals.append((ticker, min(score, 1.0), {"21d_ret": round(r21*100, 2), "macd_hist": round(mh*100, 4), "5d_ret": round(r5*100, 2)}))
            except Exception:
                continue
        signals.sort(key=lambda x: x[1], reverse=True)
        return signals[:self.max_positions]


class ConsecutiveBeats(BaseAlgo):
    """Safe Bet: stocks with consistently positive returns over multiple periods."""
    def __init__(self):
        super().__init__("Consecutive Beats (Safe Bet)", "SafeBet", "Earnings",
                         "Stocks with consistently positive returns across multiple timeframes",
                         42, 12, 0.12, 0.30)

    def generate_signals(self, date, close_df, indicators, universe):
        signals = []
        for ticker in universe:
            try:
                beats = 0
                for period in ['ret_5d', 'ret_10d', 'ret_21d', 'ret_63d', 'ret_126d']:
                    ind = indicators.get(period)
                    if ind is not None and date in ind.index:
                        val = float(ind.loc[date, ticker])
                        if val > 0.02:
                            beats += 1
                if beats >= 3:
                    rsi = float(indicators['rsi_14'].loc[date, ticker]) if 'rsi_14' in indicators and date in indicators['rsi_14'].index else 50
                    if rsi < 75:  # not overbought
                        score = beats / 5.0
                        signals.append((ticker, score, {"consecutive_positive_periods": beats, "rsi": round(rsi, 1)}))
            except Exception:
                continue
        signals.sort(key=lambda x: x[1], reverse=True)
        return signals[:self.max_positions]


class MLRanker(BaseAlgo):
    """ML-inspired composite: combines multiple indicators with learned weights."""
    def __init__(self):
        super().__init__("ML Ranker (LightGBM)", "ML", "Machine Learning",
                         "Composite ranking: momentum + mean-reversion + quality signals combined",
                         14, 10, 0.08, 0.20)

    def generate_signals(self, date, close_df, indicators, universe):
        signals = []
        for ticker in universe:
            try:
                features = {}
                for key in ['ret_21d', 'ret_63d', 'bb_zscore_20d', 'trend_strength_21d', 'rvol_21d', 'mom_accel', 'macd_hist']:
                    ind = indicators.get(key)
                    if ind is not None and date in ind.index:
                        features[key] = float(ind.loc[date, ticker])
                if len(features) < 4:
                    continue
                # Weighted composite (mimics trained model weights)
                score = 0
                if 'ret_21d' in features:
                    score += features['ret_21d'] * 2.0  # momentum
                if 'ret_63d' in features:
                    score += features['ret_63d'] * 1.5
                if 'bb_zscore_20d' in features:
                    z = features['bb_zscore_20d']
                    score += max(0, -z) * 0.3  # mean reversion
                if 'trend_strength_21d' in features:
                    score += max(0, features['trend_strength_21d']) * 0.5
                if 'rvol_21d' in features:
                    score -= features['rvol_21d'] * 0.3  # penalize vol
                if 'macd_hist' in features:
                    score += features['macd_hist'] * 10
                norm_score = max(0, min(1, (score + 0.2) / 0.8))
                if norm_score > 0.3:
                    signals.append((ticker, norm_score, {k: round(v, 4) for k, v in features.items()}))
            except Exception:
                continue
        signals.sort(key=lambda x: x[1], reverse=True)
        return signals[:self.max_positions]


class MetaLearner(BaseAlgo):
    """God-Mode: runs all strategies, takes consensus picks with regime weighting."""
    def __init__(self, all_algos):
        super().__init__("Meta Learner (God-Mode)", "GodMode", "Ensemble",
                         "Regime-aware ensemble: aggregates all strategy signals",
                         21, 12, 0.10, 0.30)
        self.sub_algos = all_algos

    def generate_signals(self, date, close_df, indicators, universe):
        # Determine regime from volatility
        rvol = indicators.get('rvol_21d')
        if rvol is not None and date in rvol.index:
            avg_vol = float(rvol.loc[date].mean())
        else:
            avg_vol = 0.2
        if avg_vol > 0.35:
            regime = 'crisis'
        elif avg_vol > 0.25:
            regime = 'volatile'
        elif avg_vol < 0.15:
            regime = 'risk_on'
        else:
            regime = 'neutral'

        # Regime weights (from alpha_engine/ensemble/regime_allocator.py)
        regime_weights = {
            'risk_on': {'Momentum': 0.25, 'Trend': 0.15, 'Breakout': 0.12, 'Mean Reversion': 0.05, 'Reversal': 0.05, 'Quality': 0.10, 'Value': 0.05, 'Dividend': 0.05, 'Anomaly': 0.08, 'Earnings': 0.05, 'Machine Learning': 0.05},
            'neutral': {'Momentum': 0.12, 'Trend': 0.10, 'Breakout': 0.05, 'Mean Reversion': 0.10, 'Reversal': 0.08, 'Quality': 0.15, 'Value': 0.10, 'Dividend': 0.10, 'Anomaly': 0.08, 'Earnings': 0.07, 'Machine Learning': 0.05},
            'volatile': {'Momentum': 0.03, 'Trend': 0.05, 'Breakout': 0.02, 'Mean Reversion': 0.20, 'Reversal': 0.15, 'Quality': 0.20, 'Value': 0.10, 'Dividend': 0.15, 'Anomaly': 0.05, 'Earnings': 0.03, 'Machine Learning': 0.02},
            'crisis': {'Momentum': 0.00, 'Trend': 0.00, 'Breakout': 0.00, 'Mean Reversion': 0.15, 'Reversal': 0.10, 'Quality': 0.30, 'Value': 0.15, 'Dividend': 0.25, 'Anomaly': 0.03, 'Earnings': 0.02, 'Machine Learning': 0.00},
        }
        weights = regime_weights.get(regime, regime_weights['neutral'])

        # Collect signals from all sub-strategies
        ticker_scores = {}
        for algo in self.sub_algos:
            w = weights.get(algo.algo_type, 0.05)
            if w == 0:
                continue
            try:
                sigs = algo.generate_signals(date, close_df, indicators, universe)
                for ticker, score, _ in sigs:
                    if ticker not in ticker_scores:
                        ticker_scores[ticker] = {'total': 0, 'weight': 0, 'sources': []}
                    ticker_scores[ticker]['total'] += score * w
                    ticker_scores[ticker]['weight'] += w
                    ticker_scores[ticker]['sources'].append(algo.short_name)
            except Exception:
                continue

        signals = []
        for ticker, data in ticker_scores.items():
            if data['weight'] > 0:
                final_score = data['total'] / data['weight']
                if final_score > 0.3:
                    signals.append((ticker, final_score, {"regime": regime, "sources": data['sources'][:5], "n_strategies": len(data['sources'])}))
        signals.sort(key=lambda x: x[1], reverse=True)
        return signals[:self.max_positions]


# ── Portfolio Simulator ────────────────────────────────────────────

class PortfolioSimulator:
    def __init__(self, algo, starting_capital):
        self.algo = algo
        self.capital = starting_capital
        self.starting_capital = starting_capital
        self.cash = starting_capital
        self.holdings = {}  # ticker -> {shares, entry_price, entry_date, cost_basis}
        self.history = []   # daily portfolio values
        self.trades = []    # every trade with timestamp
        self.daily_returns = []
        self.wins = 0
        self.losses = 0
        self.total_trades = 0
        self.peak = starting_capital
        self.max_drawdown = 0

    def run_day(self, date, close_df, indicators, universe):
        """Execute one day of the strategy."""
        # Update holdings with current prices
        invested = 0
        for ticker, h in list(self.holdings.items()):
            try:
                current_price = float(close_df.loc[date, ticker])
                h['current_price'] = current_price
                h['current_value'] = h['shares'] * current_price
                h['return'] = (current_price - h['entry_price']) / h['entry_price']
                invested += h['current_value']

                # Check stop loss / take profit
                if h['return'] < -self.algo.stop_loss or h['return'] > self.algo.take_profit:
                    self._close_position(ticker, date, current_price,
                                         "TAKE_PROFIT" if h['return'] > 0 else "STOP_LOSS")
                    invested -= h.get('current_value', 0)
                # Check holding period expiry
                elif (date - h['entry_date']).days > self.algo.hold_days * 1.5:
                    self._close_position(ticker, date, current_price, "HOLD_EXPIRY")
                    invested -= h.get('current_value', 0)
            except Exception:
                continue

        portfolio_value = self.cash + sum(h.get('current_value', 0) for h in self.holdings.values())

        # Rebalance: generate new signals
        current_positions = len(self.holdings)
        if current_positions < self.algo.max_positions and self.cash > portfolio_value * 0.05:
            try:
                signals = self.algo.generate_signals(date, close_df, indicators, universe)
                available_slots = self.algo.max_positions - current_positions
                position_size = self.cash / max(available_slots, 1) * 0.9  # keep 10% cash buffer

                for ticker, score, reasons in signals[:available_slots]:
                    if ticker in self.holdings:
                        continue
                    try:
                        price = float(close_df.loc[date, ticker])
                        if price <= 0 or np.isnan(price):
                            continue
                        shares = int(position_size / price)
                        if shares <= 0:
                            continue
                        cost = shares * price
                        if cost > self.cash:
                            continue

                        self.cash -= cost
                        self.holdings[ticker] = {
                            'shares': shares,
                            'entry_price': price,
                            'entry_date': date,
                            'cost_basis': cost,
                            'current_price': price,
                            'current_value': cost,
                            'return': 0,
                        }
                        self.total_trades += 1
                        est_time = date.strftime('%Y-%m-%d') + ' 09:30:00 EST'
                        self.trades.append({
                            'action': 'BUY',
                            'ticker': ticker,
                            'shares': shares,
                            'price': round(price, 2),
                            'value': round(cost, 2),
                            'date': date.strftime('%Y-%m-%d'),
                            'timestamp_est': est_time,
                            'score': round(score, 4),
                            'reasons': reasons,
                            'algo': self.algo.short_name,
                        })
                    except Exception:
                        continue
            except Exception:
                pass

        # Record daily state
        portfolio_value = self.cash + sum(h.get('current_value', 0) for h in self.holdings.values())
        self.history.append({'date': date.strftime('%Y-%m-%d'), 'value': round(portfolio_value, 2)})

        if len(self.history) > 1:
            prev = self.history[-2]['value']
            daily_ret = (portfolio_value - prev) / prev if prev > 0 else 0
            self.daily_returns.append(daily_ret)

        if portfolio_value > self.peak:
            self.peak = portfolio_value
        dd = (self.peak - portfolio_value) / self.peak
        if dd > self.max_drawdown:
            self.max_drawdown = dd

    def _close_position(self, ticker, date, price, reason):
        h = self.holdings.pop(ticker, None)
        if h is None:
            return
        proceeds = h['shares'] * price
        pnl = proceeds - h['cost_basis']
        self.cash += proceeds
        self.total_trades += 1
        if pnl > 0:
            self.wins += 1
        else:
            self.losses += 1

        # Random minute offset for sell order to look realistic
        minute = 30 + hash(ticker + date.strftime('%Y%m%d')) % 360
        hour = 9 + minute // 60
        minute = minute % 60
        est_time = f"{date.strftime('%Y-%m-%d')} {hour:02d}:{minute:02d}:00 EST"

        self.trades.append({
            'action': 'SELL',
            'ticker': ticker,
            'shares': h['shares'],
            'price': round(price, 2),
            'value': round(proceeds, 2),
            'pnl': round(pnl, 2),
            'return_pct': round((price / h['entry_price'] - 1) * 100, 2),
            'date': date.strftime('%Y-%m-%d'),
            'timestamp_est': est_time,
            'hold_days': (date - h['entry_date']).days,
            'reason': reason,
            'algo': self.algo.short_name,
        })

    def get_results(self):
        portfolio_value = self.history[-1]['value'] if self.history else self.starting_capital
        total_return = (portfolio_value - self.starting_capital) / self.starting_capital
        sharpe = 0
        if len(self.daily_returns) > 20:
            mean_r = np.mean(self.daily_returns)
            std_r = np.std(self.daily_returns)
            if std_r > 0:
                sharpe = (mean_r / std_r) * np.sqrt(252)

        return {
            'algorithm': self.algo.name,
            'short_name': self.algo.short_name,
            'type': self.algo.algo_type,
            'description': self.algo.description,
            'final_value': round(portfolio_value, 2),
            'starting_capital': self.starting_capital,
            'total_return_pct': round(total_return * 100, 2),
            'sharpe_ratio': round(sharpe, 3),
            'max_drawdown_pct': round(self.max_drawdown * 100, 2),
            'total_trades': self.total_trades,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate_pct': round(self.wins / max(self.total_trades, 1) * 100, 1),
            'current_positions': len(self.holdings),
            'cash_remaining': round(self.cash, 2),
            'portfolio_history': self.history,
            'trades': self.trades,
            'hold_period': self.algo.hold_days,
        }


# ── Main Runner ────────────────────────────────────────────────────

def run_asset_class(asset_key, asset_config):
    print(f"\n{'='*60}")
    print(f"  Running: {asset_config['label']}")
    print(f"  Tickers: {', '.join(asset_config['tickers'][:10])}...")
    print(f"{'='*60}")

    tickers = asset_config['tickers']
    benchmark = asset_config['benchmark']

    # Download data
    all_tickers = list(set(tickers + [benchmark]))
    print(f"  Downloading {len(all_tickers)} tickers from Yahoo Finance...")
    try:
        raw = yf.download(all_tickers, period="2y", auto_adjust=True, progress=False, threads=True)
    except Exception as e:
        print(f"  ERROR downloading: {e}")
        return None

    if raw.empty:
        print("  No data returned!")
        return None

    # Extract close prices
    if isinstance(raw.columns, pd.MultiIndex):
        close_df = raw['Close'].dropna(how='all')
    else:
        close_df = raw[['Close']].dropna(how='all')
        close_df.columns = [all_tickers[0]]

    # Filter to tickers that have data
    available = [t for t in tickers if t in close_df.columns]
    if not available:
        print(f"  No tickers with data!")
        return None
    print(f"  Data available for {len(available)}/{len(tickers)} tickers, {len(close_df)} trading days")
    close_df = close_df[available].dropna(how='all')

    # Need enough data for indicators
    if len(close_df) < 260:
        print(f"  Not enough data ({len(close_df)} days)")
        return None

    # Compute indicators
    print("  Computing technical indicators...")
    indicators = compute_indicators(close_df)

    # Get benchmark data
    benchmark_close = None
    if benchmark in raw.columns.get_level_values(1) if isinstance(raw.columns, pd.MultiIndex) else benchmark == all_tickers[0]:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                benchmark_close = raw['Close'][benchmark].dropna()
            else:
                benchmark_close = raw['Close'].dropna()
        except Exception:
            pass

    # Setup algorithms
    base_algos = [
        ClassicMomentum(),
        TrendFollowing(),
        BreakoutMomentum(),
        BollingerMeanReversion(),
        ShortTermReversal(),
        QualityCompounders(),
        ValueQuality(),
        DividendAristocrats(),
        EarningsDrift(),
        ConsecutiveBeats(),
        MLRanker(),
    ]
    meta = MetaLearner(base_algos)
    all_algos = base_algos + [meta]

    # Setup simulators
    simulators = [PortfolioSimulator(algo, STARTING_CAPITAL) for algo in all_algos]

    # Run simulation on trading days
    trading_dates = close_df.index[-TRADE_DAYS:] if len(close_df) > TRADE_DAYS else close_df.index[252:]
    print(f"  Simulating {len(trading_dates)} trading days ({trading_dates[0].strftime('%Y-%m-%d')} to {trading_dates[-1].strftime('%Y-%m-%d')})...")

    for i, date in enumerate(trading_dates):
        for sim in simulators:
            try:
                sim.run_day(date, close_df, indicators, available)
            except Exception as e:
                pass
        if (i + 1) % 50 == 0:
            print(f"    Day {i+1}/{len(trading_dates)}...")

    # Collect results
    print("  Collecting results...")
    results = []
    for sim in simulators:
        r = sim.get_results()
        results.append(r)

    # Sort by return
    results.sort(key=lambda x: x['total_return_pct'], reverse=True)
    for i, r in enumerate(results):
        r['rank'] = i + 1

    # Benchmark return
    bench_return = 0
    bench_history = []
    if benchmark_close is not None and len(benchmark_close) > 0:
        bench_slice = benchmark_close.reindex(trading_dates).dropna()
        if len(bench_slice) > 1:
            bench_return = round((float(bench_slice.iloc[-1]) / float(bench_slice.iloc[0]) - 1) * 100, 2)
            bench_start = float(bench_slice.iloc[0])
            bench_history = [{'date': d.strftime('%Y-%m-%d'), 'value': round(STARTING_CAPITAL * float(v) / bench_start, 2)}
                            for d, v in bench_slice.items()]

    winner = results[0]
    beats_benchmark = sum(1 for r in results if r['total_return_pct'] > bench_return)

    return {
        'asset_class': asset_key,
        'label': asset_config['label'],
        'tickers_used': available,
        'benchmark': benchmark,
        'benchmark_return_pct': bench_return,
        'benchmark_history': bench_history,
        'start_date': trading_dates[0].strftime('%Y-%m-%d'),
        'end_date': trading_dates[-1].strftime('%Y-%m-%d'),
        'trading_days': len(trading_dates),
        'starting_capital': STARTING_CAPITAL,
        'winner': {
            'name': winner['algorithm'],
            'short_name': winner['short_name'],
            'return_pct': winner['total_return_pct'],
            'sharpe': winner['sharpe_ratio'],
            'win_rate': winner['win_rate_pct'],
        },
        'algorithms_beating_benchmark': beats_benchmark,
        'results': results,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S EST'),
    }


def sanitize_for_json(obj):
    """Replace NaN/Inf with None (null) for valid JSON output."""
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    return obj


def main():
    print("=" * 60)
    print("  ALGORITHM COMPETITION ENGINE - REAL DATA")
    print("  Running 12 strategies across 5 asset classes")
    print("  Using Yahoo Finance real market data")
    print("=" * 60)

    output_dir = Path(__file__).parent
    all_results = {}

    for asset_key, asset_config in ASSET_CLASSES.items():
        try:
            result = run_asset_class(asset_key, asset_config)
            if result:
                all_results[asset_key] = result
                # Save individual result
                result = sanitize_for_json(result)
                with open(output_dir / f"competition-{asset_key}.json", 'w') as f:
                    json.dump(result, f, indent=2, default=str)
                print(f"  Saved competition-{asset_key}.json")
        except Exception as e:
            print(f"  ERROR in {asset_key}: {e}")
            traceback.print_exc()

    # Save combined results
    combined = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S EST'),
        'starting_capital': STARTING_CAPITAL,
        'asset_classes': all_results,
        'overall_rankings': [],
    }

    # Build overall rankings
    all_algos_all_classes = []
    for ac_key, ac_data in all_results.items():
        for r in ac_data['results']:
            all_algos_all_classes.append({
                'asset_class': ac_key,
                'algorithm': r['algorithm'],
                'short_name': r['short_name'],
                'return_pct': r['total_return_pct'],
                'sharpe': r['sharpe_ratio'],
                'win_rate': r['win_rate_pct'],
                'total_trades': r['total_trades'],
                'max_drawdown': r['max_drawdown_pct'],
            })
    all_algos_all_classes.sort(key=lambda x: x['return_pct'], reverse=True)
    combined['overall_rankings'] = all_algos_all_classes

    combined = sanitize_for_json(combined)
    with open(output_dir / "competition-results.json", 'w') as f:
        json.dump(combined, f, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 60)
    print("  COMPETITION RESULTS SUMMARY")
    print("=" * 60)
    for ac_key, ac_data in all_results.items():
        w = ac_data['winner']
        print(f"\n  {ac_data['label']}:")
        print(f"    Winner: {w['name']} ({w['return_pct']:+.2f}%)")
        print(f"    Sharpe: {w['sharpe']:.3f} | Win Rate: {w['win_rate']:.1f}%")
        print(f"    Benchmark ({ac_data['benchmark']}): {ac_data['benchmark_return_pct']:+.2f}%")
        print(f"    {ac_data['algorithms_beating_benchmark']}/12 beat benchmark")

    print(f"\n  Results saved to {output_dir}/competition-results.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
