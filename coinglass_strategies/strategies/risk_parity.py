"""S13: Crypto Risk Parity — systematic allocation framework that balances
risk contributions across crypto assets using inverse-volatility weighting
and correlation-adjusted position sizing.

Unlike the existing bundle_optimized portfolios (which use fixed weights),
this strategy dynamically sizes positions based on each asset's contribution
to total portfolio risk, aiming for equal risk from each asset.

Logic:
  - Fetch recent price data for all monitored symbols
  - Compute rolling ATR-based volatility for each
  - Compute pairwise correlation matrix
  - Calculate inverse-volatility weights (risk parity)
  - Apply correlation adjustments (reduce allocation to highly correlated pairs)
  - Generate LONG signals for assets with improving risk-adjusted momentum
  - Generate SHORT signals for assets with deteriorating risk profile

This fills the "Crypto Risk Parity / Portfolio Optimization" gap.
"""
import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

from .base import Signal

logger = logging.getLogger(__name__)

BINANCE_API = "https://api.binance.com"
OKX_API = "https://www.okx.com"

# Price history for volatility and correlation computation
_price_history: Dict[str, List[float]] = {}
_MAX_PRICE_HISTORY = 168  # 168 × 1h = 7 days


def _fetch_recent_closes(symbol: str, limit: int = 48) -> List[float]:
    """Fetch recent hourly closes from Binance/OKX."""
    try:
        resp = requests.get(
            f"{BINANCE_API}/api/v3/klines",
            params={"symbol": symbol, "interval": "1h", "limit": limit},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 10:
                return [float(k[4]) for k in data]
    except Exception as e:
        logger.debug("Binance klines failed for %s: %s", symbol, e)

    # OKX fallback
    try:
        okx_sym = symbol.replace("USDT", "-USDT")
        resp = requests.get(
            f"{OKX_API}/api/v5/market/candles",
            params={"instId": okx_sym, "bar": "1H", "limit": str(limit)},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data"):
                prices = [float(k[4]) for k in reversed(data["data"])]
                if len(prices) > 10:
                    return prices
    except Exception as e:
        logger.debug("OKX klines failed for %s: %s", symbol, e)

    return []


def _compute_returns(prices: List[float]) -> List[float]:
    """Compute log returns from price series."""
    if len(prices) < 2:
        return []
    return [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))
            if prices[i - 1] > 0 and prices[i] > 0]


def _compute_volatility(returns: List[float]) -> float:
    """Compute annualized volatility from hourly returns."""
    if len(returns) < 10:
        return 0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    hourly_vol = math.sqrt(variance)
    annualized = hourly_vol * math.sqrt(24 * 365)  # Hourly → annual
    return annualized


def _compute_momentum(prices: List[float], lookback: int = 24) -> float:
    """Compute momentum (return over lookback period)."""
    if len(prices) < lookback + 1:
        return 0
    return (prices[-1] - prices[-lookback - 1]) / prices[-lookback - 1]


def _compute_correlation(returns_a: List[float], returns_b: List[float]) -> float:
    """Compute Pearson correlation between two return series."""
    n = min(len(returns_a), len(returns_b))
    if n < 10:
        return 0

    a = returns_a[-n:]
    b = returns_b[-n:]

    mean_a = sum(a) / n
    mean_b = sum(b) / n

    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / n
    std_a = math.sqrt(sum((x - mean_a) ** 2 for x in a) / n)
    std_b = math.sqrt(sum((x - mean_b) ** 2 for x in b) / n)

    if std_a < 1e-10 or std_b < 1e-10:
        return 0

    return cov / (std_a * std_b)


def _compute_risk_parity_weights(vol_dict: Dict[str, float]) -> Dict[str, float]:
    """Compute inverse-volatility risk parity weights."""
    if not vol_dict:
        return {}

    # Filter out zero-vol assets
    valid = {k: v for k, v in vol_dict.items() if v > 0.01}
    if not valid:
        return {}

    inv_vols = {k: 1.0 / v for k, v in valid.items()}
    total_inv_vol = sum(inv_vols.values())

    return {k: v / total_inv_vol for k, v in inv_vols.items()}


def run(symbol: str, recent_rows: list, current_ratios: dict) -> Optional[Signal]:
    """Crypto risk parity strategy.

    Computes cross-asset risk-adjusted allocation signals using
    inverse-volatility weighting and momentum scoring.
    """
    # Fetch price data for this symbol
    prices = _fetch_recent_closes(symbol, limit=72)  # 3 days
    if len(prices) < 24:
        return None

    returns = _compute_returns(prices)
    if len(returns) < 20:
        return None

    # Store in history
    if symbol not in _price_history:
        _price_history[symbol] = []
    _price_history[symbol].extend(prices[-10:])
    if len(_price_history[symbol]) > _MAX_PRICE_HISTORY:
        _price_history[symbol] = _price_history[symbol][-_MAX_PRICE_HISTORY:]

    # Compute this asset's metrics
    vol = _compute_volatility(returns)
    momentum_24h = _compute_momentum(prices, 24)
    momentum_48h = _compute_momentum(prices, 48) if len(prices) >= 49 else momentum_24h

    # Risk-adjusted momentum (momentum / volatility = Sharpe-like ratio)
    sharpe_like = momentum_24h / vol if vol > 0.01 else 0

    # Compute cross-asset metrics using stored history
    all_vols = {}
    all_returns = {}
    from .. import config as cfg
    for sym in cfg.SYMBOLS:
        if sym in _price_history and len(_price_history[sym]) >= 24:
            sym_returns = _compute_returns(_price_history[sym][-48:])
            if len(sym_returns) >= 10:
                all_vols[sym] = _compute_volatility(sym_returns)
                all_returns[sym] = sym_returns

    # Risk parity weights
    rp_weights = _compute_risk_parity_weights(all_vols)
    my_weight = rp_weights.get(symbol, 1.0 / len(cfg.SYMBOLS))

    # Correlation with BTC (diversification bonus/penalty)
    btc_corr = 0.5  # Default
    if "BTCUSDT" in all_returns and symbol != "BTCUSDT":
        btc_corr = _compute_correlation(
            all_returns.get(symbol, returns), all_returns["BTCUSDT"]
        )

    # Decision logic
    # LONG: positive risk-adjusted momentum + lower volatility + decorrelation
    # SHORT: negative risk-adjusted momentum + rising volatility + high correlation

    SHARPE_THRESHOLD = 0.5
    VOL_HIGH_THRESHOLD = 1.5  # 150% annualized

    direction = None
    reason_parts = []

    if sharpe_like > SHARPE_THRESHOLD:
        direction = "LONG"
        reason_parts.append(
            f"Risk parity LONG: risk-adj momentum {sharpe_like:.3f} > {SHARPE_THRESHOLD}. "
            f"24h return: {momentum_24h*100:.2f}%. "
            f"Annualized vol: {vol*100:.1f}%. "
            f"RP weight: {my_weight*100:.1f}%. "
            f"BTC correlation: {btc_corr:.2f}."
        )
    elif sharpe_like < -SHARPE_THRESHOLD and vol > VOL_HIGH_THRESHOLD:
        direction = "SHORT"
        reason_parts.append(
            f"Risk parity SHORT: deteriorating risk profile. "
            f"Risk-adj momentum {sharpe_like:.3f}. "
            f"24h return: {momentum_24h*100:.2f}%. "
            f"Annualized vol: {vol*100:.1f}% (high). "
            f"RP weight: {my_weight*100:.1f}%. "
            f"BTC correlation: {btc_corr:.2f}."
        )

    if direction is None:
        return None

    # Confidence based on momentum strength, decorrelation, and vol regime
    momentum_score = min(abs(sharpe_like) / 2.0, 1.0)
    decorrelation_score = max(0, (1.0 - abs(btc_corr)) * 0.5)
    vol_score = 0.5 if 0.3 < vol < 1.2 else 0.2  # Normal vol range preferred

    conf = 0.45 + 0.15 * momentum_score + 0.10 * decorrelation_score + 0.10 * vol_score
    conf = round(min(conf, 0.80), 3)

    return Signal(
        symbol=symbol,
        direction=direction,
        strategy="coinglass_risk_parity",
        confidence=conf,
        reason=" | ".join(reason_parts),
        ratios={
            "risk_adj_momentum": round(sharpe_like, 4),
            "annualized_vol": round(vol, 4),
            "momentum_24h": round(momentum_24h, 6),
            "momentum_48h": round(momentum_48h, 6),
            "rp_weight": round(my_weight, 4),
            "btc_correlation": round(btc_corr, 3),
            **current_ratios,
        },
    )
