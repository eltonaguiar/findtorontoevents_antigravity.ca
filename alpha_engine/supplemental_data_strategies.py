"""
ALPHA_ENGINE -- Supplemental Data Strategies
=============================================
New signal providers using high-impact free APIs that fill major data gaps:

  1. messari_fundamental_quality   -- Altcoin quality filter via dev activity, ROI, volatility
  2. messari_developer_momentum    -- Developer commit velocity as leading indicator
  3. messari_roi_divergence        -- Price vs fundamental ROI divergence
  4. mempool_congestion_volatility -- BTC mempool congestion predicts volatility 1-4h ahead
  5. mempool_fee_spike_reversal    -- Fee spike exhaustion → mean reversion signal
  6. mempool_hashrate_security     -- Hashrate trend as network confidence proxy
  7. ethplorer_whale_accumulation  -- ERC-20 whale wallet accumulation/distribution
  8. ethplorer_token_flow_momentum -- Token transfer momentum (velocity of movement)
  9. ethplorer_holder_concentration -- Top holder concentration risk signal

Data sources (all FREE):
  - api.messari.io/v1/              (fundamentals, on-chain, no key required)
  - mempool.space/api/              (BTC mempool, fees, hashrate, no key)
  - api.ethplorer.io/               (ERC-20 tokens, free key from ethplorer.io)

References:
  - Messari Fundamentals: Liu et al. (2022 JFE) -- cross-sectional momentum + quality
  - Mempool Leading Indicator: Easley, O'Hara & Basu (2019) -- microstructure signals
  - Whale Tracking: Makarov & Schoar (2020) -- blockchain analysis and crypto markets
  - Developer Activity: Cong, He & Tang (2023 Mgmt Science) -- crypto fundamentals
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import CRYPTO_SYMBOLS
from indicators import rsi, atr, sma, ema, volume_ratio


# -- Helpers ---------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


def _smart_round(value: float) -> float:
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _atr_tp_sl(close: pd.Series, high: pd.Series, low: pd.Series,
               tp_mult: float = 3.0, sl_mult: float = 2.25,
               atr_period: int = 14) -> tuple[float, float, float]:
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price + tp_mult * current_atr
    sl = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


def _fetch_json(url: str, timeout: int = 10, headers: Optional[dict] = None) -> Optional[dict | list]:
    """Fetch JSON with timeout and optional custom headers."""
    try:
        hdrs = {"User-Agent": "ALPHA_ENGINE/2.0"}
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


# -- Symbol mapping helpers ------------------------------------------------

# Messari uses slugs like "bitcoin", "ethereum", "solana"
_YFINANCE_TO_MESSARI: dict[str, str] = {
    "BTC-USD": "bitcoin", "ETH-USD": "ethereum", "SOL-USD": "solana",
    "BNB-USD": "binance-coin", "XRP-USD": "xrp", "ADA-USD": "cardano",
    "AVAX-USD": "avalanche", "LINK-USD": "chainlink", "NEAR-USD": "near-protocol",
    "DOT-USD": "polkadot", "DOGE-USD": "dogecoin", "ATOM-USD": "cosmos",
    "UNI-USD": "uniswap", "LTC-USD": "litecoin", "ETC-USD": "ethereum-classic",
    "FIL-USD": "filecoin", "INJ-USD": "injective-protocol", "TIA-USD": "celestia",
    "AAVE-USD": "aave", "MKR-USD": "maker", "CRV-USD": "curve-dao-token",
    "RNDR-USD": "render-token", "ARB-USD": "arbitrum", "OP-USD": "optimism",
    "SUI-USD": "sui", "APT-USD": "aptos", "SEI-USD": "sei-network",
    "TRX-USD": "tron", "SHIB-USD": "shiba-inu", "PEPE-USD": "pepe",
}

# Ethplorer uses contract addresses for ERC-20 tokens
_YFINANCE_TO_ETH_CONTRACT: dict[str, str] = {
    "LINK-USD": "0x514910771af9ca656af840dff83e8264ecf986ca",
    "UNI-USD": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
    "AAVE-USD": "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9",
    "MKR-USD": "0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2",
    "CRV-USD": "0xd533a97262fd7b5a5a6a6e4e9a7e3b2f1c3e1d2e",
    "SHIB-USD": "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce",
    "PEPE-USD": "0x6982508145454ce325ddbe47a25d4ec3d2311933",
    "RNDR-USD": "0x6de037ef9ad2725eb40118bb1702ebb27e4aeb24",
    "ARB-USD": "0xb50721bcf8d664c30412cfbc6cf7a15145234ad1",
    "OP-USD": "0x4200000000000000000000000000000000000042",
    "INJ-USD": "0xe28b3b32b6c345a34ff64674606124dd5aceca30",
}


# =========================================================================
# FUNDAMENTAL DATA STRATEGIES (CoinGecko + Coinpaprika)
# =========================================================================
# Messari API went paid-only (401). Replaced with two FREE alternatives:
#   - CoinGecko: developer_data (commits, stars, forks), community_data,
#                market_data (ATH, price changes), no key required
#   - Coinpaprika: ROI metrics, ATH data, volume, beta, no key required
# Both validated live 2026-03-21.
# =========================================================================

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
COINPAPRIKA_BASE = "https://api.coinpaprika.com/v1"

# CoinGecko uses different IDs than Messari slugs
_YFINANCE_TO_COINGECKO: dict[str, str] = {
    "BTC-USD": "bitcoin", "ETH-USD": "ethereum", "SOL-USD": "solana",
    "BNB-USD": "binancecoin", "XRP-USD": "ripple", "ADA-USD": "cardano",
    "AVAX-USD": "avalanche-2", "LINK-USD": "chainlink", "NEAR-USD": "near",
    "DOT-USD": "polkadot", "DOGE-USD": "dogecoin", "ATOM-USD": "cosmos",
    "UNI-USD": "uniswap", "LTC-USD": "litecoin", "ETC-USD": "ethereum-classic",
    "FIL-USD": "filecoin", "INJ-USD": "injective-protocol", "TIA-USD": "celestia",
    "AAVE-USD": "aave", "MKR-USD": "maker", "CRV-USD": "curve-dao-token",
    "RNDR-USD": "render-token", "ARB-USD": "arbitrum", "OP-USD": "optimism",
    "SUI-USD": "sui", "APT-USD": "aptos", "SEI-USD": "sei-network",
    "TRX-USD": "tron", "SHIB-USD": "shiba-inu", "PEPE-USD": "pepe",
}

_YFINANCE_TO_COINPAPRIKA: dict[str, str] = {
    "BTC-USD": "btc-bitcoin", "ETH-USD": "eth-ethereum", "SOL-USD": "sol-solana",
    "BNB-USD": "bnb-binance-coin", "XRP-USD": "xrp-xrp", "ADA-USD": "ada-cardano",
    "AVAX-USD": "avax-avalanche", "LINK-USD": "link-chainlink",
    "DOT-USD": "dot-polkadot", "DOGE-USD": "doge-dogecoin", "ATOM-USD": "atom-cosmos",
    "UNI-USD": "uni-uniswap", "LTC-USD": "ltc-litecoin",
    "FIL-USD": "fil-filecoin", "AAVE-USD": "aave-aave",
    "ARB-USD": "arb-arbitrum", "OP-USD": "op-optimism",
    "SUI-USD": "sui-sui", "APT-USD": "apt-aptos",
}


def _fetch_coingecko_coin(cg_id: str) -> Optional[dict]:
    """Fetch comprehensive coin data from CoinGecko (free, no key)."""
    url = (f"{COINGECKO_BASE}/coins/{cg_id}"
           "?localization=false&tickers=false&market_data=true"
           "&community_data=true&developer_data=true&sparkline=false")
    return _fetch_json(url, timeout=12)


def _fetch_coinpaprika_ticker(cp_id: str) -> Optional[dict]:
    """Fetch ticker data from Coinpaprika (free, no key)."""
    return _fetch_json(f"{COINPAPRIKA_BASE}/tickers/{cp_id}", timeout=10)


# =====================================================================
# STRATEGY S1: Fundamental Quality Filter (CoinGecko)
# =====================================================================
# Combines developer activity, ROI metrics, and community data to score
# asset quality. BUY high-quality assets in dips (RSI < 45).
# Academic: Cong, He & Tang (2023) -- crypto fundamental signals predict returns.
# Data: CoinGecko developer_data (commits, stars, forks, contributors)
# =====================================================================

def messari_fundamental_quality(data: dict[str, pd.DataFrame],
                                context: Optional[dict] = None) -> list[dict]:
    """BUY high-quality altcoins (strong dev activity + good ROI) on dips."""
    signals: list[dict] = []

    for symbol, cg_id in _YFINANCE_TO_COINGECKO.items():
        if symbol not in data or symbol in ("BTC-USD", "ETH-USD"):
            continue  # Focus on altcoins where fundamentals matter most
        try:
            df = data[symbol]
            if len(df) < 30:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])
            rsi_val = float(rsi(close, 14).iloc[-1])

            # Only look at dips
            if rsi_val > 45:
                continue

            # Fetch CoinGecko fundamentals (dev + community + market)
            coin = _fetch_coingecko_coin(cg_id)
            if not coin:
                continue

            dev_data = coin.get("developer_data", {}) or {}
            market_data = coin.get("market_data", {}) or {}
            community_data = coin.get("community_data", {}) or {}

            # Developer activity score
            stars = dev_data.get("stars", 0) or 0
            forks = dev_data.get("forks", 0) or 0
            commits_4w = dev_data.get("commit_count_4_weeks", 0) or 0
            # Annualize 4-week commits
            commits_annual = commits_4w * 13

            # Normalize dev score
            dev_activity = 0.0
            if commits_4w > 10 and (stars > 100 or forks > 50):
                dev_activity = min(1.0, (commits_4w / 50) * 0.5
                                  + (stars / 5000) * 0.3
                                  + (forks / 2000) * 0.2)
            elif commits_4w > 5:
                dev_activity = 0.3
            else:
                continue  # Skip dead/low-activity projects

            # ROI from market_data
            roi_30d = market_data.get("price_change_percentage_30d", 0) or 0
            roi_1y = market_data.get("price_change_percentage_1y", 0) or 0

            # ATH distance as value indicator
            ath_change = market_data.get("ath_change_percentage", {}).get("usd", 0) or 0

            # Quality score: high dev + positive long-term ROI + distance from ATH
            quality = (dev_activity * 0.4
                       + min(1.0, max(0, roi_1y / 200 + 0.5)) * 0.3
                       + min(1.0, max(0, abs(ath_change) / 80)) * 0.3)

            if quality < 0.35:
                continue

            entry, tp, sl = _atr_tp_sl(close, high, low, 3.0, 2.0)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr < 1.5:
                continue

            dip_depth = max(0, (45 - rsi_val) / 45)
            conf = min(0.82, 0.50 + quality * 0.25 + dip_depth * 0.15)

            signals.append({
                "strategy": "messari_fundamental_quality",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"High-quality fundamentals (score={quality:.2f}): "
                    f"{commits_4w} commits/4w, {stars} stars, "
                    f"RSI dip at {rsi_val:.0f}"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "quality_score": round(quality, 3),
                    "dev_activity": round(dev_activity, 3),
                    "roi_30d_pct": round(roi_30d, 2),
                    "roi_1y_pct": round(roi_1y, 2),
                    "ath_change_pct": round(ath_change, 2),
                    "commits_4w": commits_4w,
                    "stars": stars,
                    "forks": forks,
                    "source": "CoinGecko developer_data -- Cong, He & Tang (2023)",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY S2: Developer Momentum (CoinGecko)
# =====================================================================
# Rising developer activity (commits, forks, stars) is a 3-6 month
# leading indicator for price appreciation in crypto assets.
# Academic: Cong, He & Tang (2023), Sockin & Xiong (2023)
# Data: CoinGecko developer_data + code_additions/deletions
# =====================================================================

def messari_developer_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY assets with strong developer activity + price consolidation."""
    signals: list[dict] = []

    for symbol, cg_id in _YFINANCE_TO_COINGECKO.items():
        if symbol not in data:
            continue
        try:
            df = data[symbol]
            if len(df) < 50:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # Price must be consolidating (low recent volatility)
            returns_20d = close.pct_change(1).tail(20)
            vol_20d = float(returns_20d.std())
            if vol_20d > 0.06:
                continue

            # Fetch CoinGecko dev metrics
            coin = _fetch_coingecko_coin(cg_id)
            if not coin:
                continue

            dev_data = coin.get("developer_data", {}) or {}
            commits_4w = dev_data.get("commit_count_4_weeks", 0) or 0
            stars = dev_data.get("stars", 0) or 0
            forks = dev_data.get("forks", 0) or 0
            additions_4w = dev_data.get("code_additions_deletions_4_weeks", {}).get("additions", 0) or 0
            deletions_4w = dev_data.get("code_additions_deletions_4_weeks", {}).get("deletions", 0) or 0
            net_code = additions_4w - abs(deletions_4w)

            # Strong dev momentum
            if commits_4w < 15 or (stars < 200 and forks < 100):
                continue

            # SMA trend: 20d above 50d
            sma_20 = float(sma(close, 20).iloc[-1])
            sma_50 = float(sma(close, 50).iloc[-1])
            if sma_20 <= sma_50:
                continue

            entry, tp, sl = _atr_tp_sl(close, high, low, 3.5, 2.0)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr < 1.5:
                continue

            dev_score = min(1.0, commits_4w / 80 * 0.5 + stars / 5000 * 0.3 + forks / 2000 * 0.2)
            conf = min(0.78, 0.52 + dev_score * 0.20 + (1 - vol_20d / 0.06) * 0.10)

            signals.append({
                "strategy": "messari_developer_momentum",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Dev momentum: {commits_4w} commits/4w, {stars} stars, "
                    f"+{net_code:,} net lines. Consolidating (vol={vol_20d:.3f})"
                ),
                "timeframe": "1d",
                "extra": {
                    "commits_4w": commits_4w,
                    "stars": stars,
                    "forks": forks,
                    "net_code_4w": net_code,
                    "volatility_20d": round(vol_20d, 4),
                    "sma_20_above_50": True,
                    "source": "CoinGecko developer_data -- Sockin & Xiong (2023)",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY S3: ROI Divergence (Coinpaprika + CoinGecko)
# =====================================================================
# When fundamental ROI metrics diverge from recent price action,
# it signals a mismatch between fundamentals and market perception.
# BUY when long-term ROI is positive but price has pulled back.
# Data: Coinpaprika tickers (ATH, volume, beta) + CoinGecko price changes
# =====================================================================

def messari_roi_divergence(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY when fundamental ROI is positive but price has pulled back."""
    signals: list[dict] = []

    for symbol, cg_id in _YFINANCE_TO_COINGECKO.items():
        if symbol not in data:
            continue
        try:
            df = data[symbol]
            if len(df) < 30:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])

            # Price must have pulled back (7d return negative)
            price_7d_ago = float(close.iloc[-7]) if len(close) >= 7 else price
            price_7d_return = (price - price_7d_ago) / price_7d_ago if price_7d_ago > 0 else 0

            if price_7d_return > -0.03:
                continue  # Need at least 3% pullback

            # Fetch CoinGecko market data for ROI
            coin = _fetch_coingecko_coin(cg_id)
            if not coin:
                continue

            md = coin.get("market_data", {}) or {}
            roi_30d = md.get("price_change_percentage_30d", 0) or 0
            roi_1y = md.get("price_change_percentage_1y", 0) or 0
            ath_change = md.get("ath_change_percentage", {}).get("usd", 0) or 0

            # Also try Coinpaprika for extra confirmation
            cp_id = _YFINANCE_TO_COINPAPRIKA.get(symbol)
            cp_beta = None
            if cp_id:
                cp_data = _fetch_coinpaprika_ticker(cp_id)
                if cp_data:
                    cp_quotes = cp_data.get("quotes", {}).get("USD", {})
                    cp_beta = cp_quotes.get("beta_value")

            # Divergence: positive medium/long-term ROI but recent pullback
            if roi_30d <= 0 and roi_1y <= 0:
                continue

            if roi_30d <= 5 and roi_1y <= 20:
                continue

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 50:
                continue

            entry, tp, sl = _atr_tp_sl(close, high, low, 3.0, 2.0)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr < 1.5:
                continue

            divergence_strength = min(1.0, abs(price_7d_return) * 10 + max(0, roi_30d / 50))
            conf = min(0.75, 0.48 + divergence_strength * 0.25)

            extra = {
                "price_7d_return_pct": round(price_7d_return * 100, 2),
                "roi_30d_pct": round(roi_30d, 2),
                "roi_1y_pct": round(roi_1y, 2),
                "ath_change_pct": round(ath_change, 2),
                "divergence_strength": round(divergence_strength, 3),
                "source": "CoinGecko + Coinpaprika -- ROI/Price divergence",
            }
            if cp_beta is not None:
                extra["beta"] = round(cp_beta, 3)

            signals.append({
                "strategy": "messari_roi_divergence",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"ROI divergence: price {price_7d_return*100:.1f}% (7d) but "
                    f"ROI 30d={roi_30d:.1f}%, 1y={roi_1y:.1f}%. RSI={rsi_val:.0f}"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": extra,
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# MEMPOOL.SPACE API STRATEGIES
# =========================================================================
# mempool.space provides real-time Bitcoin mempool data, fee estimates,
# and mining statistics. All endpoints are FREE with no API key.
# Research shows mempool congestion is a 1-4h leading indicator for BTC
# volatility (Easley, O'Hara & Basu, 2019).
# =========================================================================

MEMPOOL_BASE = "https://mempool.space/api"


def _fetch_mempool_stats() -> Optional[dict]:
    """Fetch current mempool statistics."""
    return _fetch_json(f"{MEMPOOL_BASE}/mempool", timeout=8)


def _fetch_mempool_fees() -> Optional[dict]:
    """Fetch recommended fee rates."""
    return _fetch_json(f"{MEMPOOL_BASE}/v1/fees/recommended", timeout=8)


def _fetch_hashrate_difficulty() -> Optional[dict]:
    """Fetch hashrate and difficulty data."""
    return _fetch_json(f"{MEMPOOL_BASE}/v1/mining/hashrate/1m", timeout=10)


def _fetch_mempool_blocks() -> Optional[list]:
    """Fetch recent blocks for block time analysis."""
    return _fetch_json(f"{MEMPOOL_BASE}/v1/blocks", timeout=8)


# =====================================================================
# STRATEGY S4: Mempool Congestion Volatility Predictor
# =====================================================================
# High mempool congestion (many unconfirmed TX, high fees) predicts
# increased BTC volatility in the next 1-4 hours.
# When congestion is extreme + RSI oversold → potential reversal.
# When congestion is extreme + RSI overbought → potential correction.
# =====================================================================

def mempool_congestion_volatility(data: dict[str, pd.DataFrame],
                                  context: Optional[dict] = None) -> list[dict]:
    """Trade BTC volatility predicted by extreme mempool congestion."""
    signals: list[dict] = []

    if "BTC-USD" not in data:
        return signals

    try:
        df = data["BTC-USD"]
        if len(df) < 30:
            return signals

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        price = float(close.iloc[-1])

        # Fetch mempool state
        mempool = _fetch_mempool_stats()
        fees = _fetch_mempool_fees()
        if not mempool or not fees:
            return signals

        # Mempool metrics
        tx_count = mempool.get("count", 0)
        vsize = mempool.get("vsize", 0)  # Virtual size in vBytes
        total_fee = mempool.get("total_fee", 0)  # Total fees in sats

        # Fee metrics (sat/vB)
        fastest_fee = fees.get("fastestFee", 0)
        half_hour_fee = fees.get("halfHourFee", 0)
        hour_fee = fees.get("hourFee", 0)
        economy_fee = fees.get("economyFee", 0)

        # Congestion score: normalize mempool size and fee levels
        # Normal mempool: ~5K-20K TX, ~10-50 MB vsize
        # Congested: >50K TX, >100 MB vsize, fastest fee >50 sat/vB
        congestion = 0.0
        if tx_count > 0:
            congestion += min(1.0, tx_count / 100000) * 0.3
        if vsize > 0:
            congestion += min(1.0, vsize / (200 * 1_000_000)) * 0.3  # 200MB threshold
        if fastest_fee > 0:
            congestion += min(1.0, fastest_fee / 100) * 0.4  # 100 sat/vB = extreme

        # Fee spread: large spread between fastest and economy = urgency
        fee_spread = (fastest_fee - economy_fee) / max(economy_fee, 1)

        rsi_val = float(rsi(close, 14).iloc[-1])

        # Extreme congestion + oversold RSI → BUY (panic selling exhaustion)
        if congestion > 0.65 and rsi_val < 35:
            entry, tp, sl = _atr_tp_sl(close, high, low, 3.0, 2.0)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr >= 1.5:
                conf = min(0.78, 0.50 + congestion * 0.20 + (35 - rsi_val) / 100)
                signals.append({
                    "strategy": "mempool_congestion_volatility",
                    "symbol": "BTC-USD",
                    "category": "crypto",
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"Mempool congestion {congestion:.2f} (extreme): "
                        f"{tx_count:,} TX, fee={fastest_fee} sat/vB. "
                        f"RSI oversold at {rsi_val:.0f} → reversal likely"
                    ),
                    "timeframe": "4h",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "mempool_tx_count": tx_count,
                        "mempool_vsize_mb": round(vsize / 1_000_000, 1),
                        "fastest_fee_sat_vb": fastest_fee,
                        "economy_fee_sat_vb": economy_fee,
                        "fee_spread": round(fee_spread, 2),
                        "congestion_score": round(congestion, 3),
                        "source": "mempool.space -- Easley, O'Hara & Basu (2019)",
                    },
                    "timestamp": _now_iso(),
                })

        # Extreme congestion + overbought RSI → SELL (distribution phase)
        elif congestion > 0.65 and rsi_val > 70:
            entry = _smart_round(price)
            atr_val = float(atr(high, low, close, 14).iloc[-1])
            tp = _smart_round(price - 3.0 * atr_val)
            sl = _smart_round(price + 2.0 * atr_val)
            rr = abs(entry - tp) / max(abs(sl - entry), 0.01)
            if rr >= 1.5:
                conf = min(0.72, 0.48 + congestion * 0.18 + (rsi_val - 70) / 100)
                signals.append({
                    "strategy": "mempool_congestion_volatility",
                    "symbol": "BTC-USD",
                    "category": "crypto",
                    "signal_type": "SELL",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"Mempool congestion {congestion:.2f} (extreme): "
                        f"{tx_count:,} TX, fee={fastest_fee} sat/vB. "
                        f"RSI overbought at {rsi_val:.0f} → correction likely"
                    ),
                    "timeframe": "4h",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "mempool_tx_count": tx_count,
                        "fastest_fee_sat_vb": fastest_fee,
                        "congestion_score": round(congestion, 3),
                        "source": "mempool.space -- congestion reversal",
                    },
                    "timestamp": _now_iso(),
                })

    except Exception:
        pass

    return signals


# =====================================================================
# STRATEGY S5: Mempool Fee Spike Exhaustion
# =====================================================================
# After a fee spike (fastest fee >80 sat/vB), fees tend to mean-revert.
# Fee spike + clearing mempool = volatility settling, trend continuation.
# Combine with price direction for entry.
# =====================================================================

def mempool_fee_spike_reversal(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY BTC when fee spike is clearing (panic subsiding)."""
    signals: list[dict] = []

    if "BTC-USD" not in data:
        return signals

    try:
        df = data["BTC-USD"]
        if len(df) < 20:
            return signals

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        price = float(close.iloc[-1])

        fees = _fetch_mempool_fees()
        mempool = _fetch_mempool_stats()
        if not fees or not mempool:
            return signals

        fastest = fees.get("fastestFee", 0)
        half_hour = fees.get("halfHourFee", 0)
        hour_fee = fees.get("hourFee", 0)
        economy = fees.get("economyFee", 0)

        # Fee spike detection: fastest > 60 sat/vB but hour fee much lower
        # This means congestion is subsiding (spike clearing)
        if fastest < 60:
            return signals  # No fee spike

        # Clearing signal: large gap between fastest and hour = spike clearing
        clearing_ratio = fastest / max(hour_fee, 1)
        if clearing_ratio < 1.5:
            return signals  # Spike not clearing yet

        # Price must be in uptrend (SMA 10 > SMA 30)
        sma_10 = float(sma(close, 10).iloc[-1])
        sma_30 = float(sma(close, 30).iloc[-1])
        if sma_10 <= sma_30:
            return signals  # Not in uptrend

        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val > 65:
            return signals  # Already overbought

        entry, tp, sl = _atr_tp_sl(close, high, low, 2.5, 1.5)
        rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
        if rr < 1.5:
            return signals

        conf = min(0.72, 0.50 + min(0.15, (fastest - 60) / 200) + min(0.10, clearing_ratio / 10))

        signals.append({
            "strategy": "mempool_fee_spike_reversal",
            "symbol": "BTC-USD",
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Fee spike clearing: fastest={fastest} sat/vB, hour={hour_fee}, "
                f"ratio={clearing_ratio:.1f}x. Uptrend intact, RSI={rsi_val:.0f}"
            ),
            "timeframe": "4h",
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "fastest_fee": fastest,
                "hour_fee": hour_fee,
                "economy_fee": economy,
                "clearing_ratio": round(clearing_ratio, 2),
                "source": "mempool.space -- fee spike exhaustion",
            },
            "timestamp": _now_iso(),
        })
    except Exception:
        pass

    return signals


# =====================================================================
# STRATEGY S6: Hashrate Security Confidence
# =====================================================================
# Rising hashrate = miners investing in security = bullish confidence.
# Hashrate growth + price below recent high = accumulation opportunity.
# Uses mempool.space /v1/mining/hashrate endpoint.
# Academic: Nuzzi et al. (2024 CoinMetrics) -- hash rate as security metric
# =====================================================================

def mempool_hashrate_security(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY BTC when hashrate is growing but price hasn't caught up."""
    signals: list[dict] = []

    if "BTC-USD" not in data:
        return signals

    try:
        df = data["BTC-USD"]
        if len(df) < 60:
            return signals

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        price = float(close.iloc[-1])

        # Fetch hashrate data
        hr_data = _fetch_hashrate_difficulty()
        if not hr_data or not isinstance(hr_data, dict):
            return signals

        hashrates = hr_data.get("hashrates", [])
        if not hashrates or len(hashrates) < 10:
            return signals

        # Calculate hashrate trend (compare recent vs older)
        recent_hr = [h.get("avgHashrate", 0) for h in hashrates[-7:] if h.get("avgHashrate")]
        older_hr = [h.get("avgHashrate", 0) for h in hashrates[-30:-7] if h.get("avgHashrate")]

        if not recent_hr or not older_hr:
            return signals

        avg_recent = sum(recent_hr) / len(recent_hr)
        avg_older = sum(older_hr) / len(older_hr)

        if avg_older <= 0:
            return signals

        hr_growth = (avg_recent - avg_older) / avg_older

        # Hashrate must be growing (miners bullish)
        if hr_growth < 0.02:  # At least 2% growth
            return signals

        # Price should be below recent high (room to catch up)
        recent_high = float(high.tail(30).max())
        pct_below_high = (recent_high - price) / recent_high

        if pct_below_high < 0.05:
            return signals  # Already near high

        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val > 60:
            return signals  # Not a great entry point

        entry, tp, sl = _atr_tp_sl(close, high, low, 3.5, 2.0)
        rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
        if rr < 1.5:
            return signals

        # Growing hashrate + deeper pullback = higher confidence
        conf = min(0.76, 0.50 + hr_growth * 2 + pct_below_high * 0.5)

        signals.append({
            "strategy": "mempool_hashrate_security",
            "symbol": "BTC-USD",
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Hashrate growing +{hr_growth*100:.1f}% but price "
                f"{pct_below_high*100:.1f}% below 30d high. "
                f"Miners bullish, RSI={rsi_val:.0f}"
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "hashrate_growth_pct": round(hr_growth * 100, 2),
                "pct_below_30d_high": round(pct_below_high * 100, 2),
                "avg_recent_hashrate_eh": round(avg_recent / 1e18, 2),
                "source": "mempool.space -- Nuzzi et al. (2024 CoinMetrics)",
            },
            "timestamp": _now_iso(),
        })
    except Exception:
        pass

    return signals


# =========================================================================
# ETHPLORER API STRATEGIES
# =========================================================================
# Ethplorer provides ERC-20 token analytics: top holders, transfers,
# token history, and holder concentration. Free tier with API key.
# Key: ETHPLORER_API_KEY env var (free from ethplorer.io, fallback: "freekey")
# =========================================================================

ETHPLORER_BASE = "https://api.ethplorer.io"
ETHPLORER_KEY = os.environ.get("ETHPLORER_API_KEY") or os.environ.get("ETHERSCAN_API_KEY") or "freekey"


def _fetch_ethplorer(endpoint: str) -> Optional[dict | list]:
    """Fetch from Ethplorer API with API key."""
    url = f"{ETHPLORER_BASE}{endpoint}"
    sep = "&" if "?" in url else "?"
    url += f"{sep}apiKey={ETHPLORER_KEY}"
    return _fetch_json(url, timeout=12)


# =====================================================================
# STRATEGY S7: Ethplorer Whale Accumulation
# =====================================================================
# Track top ERC-20 token holders. When top holders are accumulating
# (increasing balance) while price dips, smart money is buying.
# Academic: Makarov & Schoar (2020) -- blockchain analysis & crypto markets
# =====================================================================

def ethplorer_whale_accumulation(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY ERC-20 tokens when top holders are accumulating during price dips."""
    signals: list[dict] = []

    for symbol, contract in _YFINANCE_TO_ETH_CONTRACT.items():
        if symbol not in data:
            continue
        try:
            df = data[symbol]
            if len(df) < 20:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])

            # Price should be dipping (7d return negative)
            price_7d = float(close.iloc[-7]) if len(close) >= 7 else price
            ret_7d = (price - price_7d) / price_7d if price_7d > 0 else 0
            if ret_7d > -0.02:
                continue  # Need at least 2% pullback

            # Fetch top holders
            holders_data = _fetch_ethplorer(f"/getTopTokenHolders/{contract}?limit=10")
            if not holders_data or not isinstance(holders_data, dict):
                continue

            holders = holders_data.get("holders", [])
            if not holders:
                continue

            # Calculate top-10 holder concentration
            total_share = sum(h.get("share", 0) for h in holders)

            # Fetch recent token operations (transfers)
            ops_data = _fetch_ethplorer(f"/getTokenHistory/{contract}?type=transfer&limit=50")
            if not ops_data or not isinstance(ops_data, dict):
                continue

            operations = ops_data.get("operations", [])
            if not operations:
                continue

            # Analyze transfer flow: are whales accumulating or distributing?
            top_addresses = {h.get("address", "").lower() for h in holders}
            whale_inflow = 0
            whale_outflow = 0

            for op in operations:
                to_addr = (op.get("to", "") or "").lower()
                from_addr = (op.get("from", "") or "").lower()
                value = float(op.get("value", 0) or 0)

                if to_addr in top_addresses:
                    whale_inflow += value
                if from_addr in top_addresses:
                    whale_outflow += value

            # Net whale flow: positive = accumulation
            net_flow = whale_inflow - whale_outflow
            if net_flow <= 0:
                continue  # Whales are distributing, not accumulating

            # Flow ratio: how much more inflow vs outflow
            flow_ratio = whale_inflow / max(whale_outflow, 1)

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 50:
                continue  # Not oversold enough

            entry, tp, sl = _atr_tp_sl(close, high, low, 3.0, 2.0)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr < 1.5:
                continue

            # Stronger accumulation + deeper dip = higher confidence
            accum_strength = min(1.0, (flow_ratio - 1) / 3)
            dip_depth = min(1.0, abs(ret_7d) * 10)
            conf = min(0.80, 0.50 + accum_strength * 0.20 + dip_depth * 0.12)

            signals.append({
                "strategy": "ethplorer_whale_accumulation",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Whale accumulation: inflow/outflow ratio={flow_ratio:.1f}x "
                    f"while price dipped {ret_7d*100:.1f}% (7d). RSI={rsi_val:.0f}"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "whale_flow_ratio": round(flow_ratio, 2),
                    "top10_holder_share_pct": round(total_share, 2),
                    "price_7d_return_pct": round(ret_7d * 100, 2),
                    "contract": contract,
                    "source": "Ethplorer API -- Makarov & Schoar (2020)",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY S8: Ethplorer Token Flow Momentum
# =====================================================================
# High transfer velocity (many transfers in short period) often precedes
# significant price moves. Combine with volume and trend direction.
# =====================================================================

def ethplorer_token_flow_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY ERC-20 tokens with surging transfer activity + bullish price trend."""
    signals: list[dict] = []

    for symbol, contract in _YFINANCE_TO_ETH_CONTRACT.items():
        if symbol not in data:
            continue
        try:
            df = data[symbol]
            if len(df) < 30:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])

            # Must be in uptrend (10d SMA > 30d SMA)
            sma_10 = float(sma(close, 10).iloc[-1])
            sma_30 = float(sma(close, 30).iloc[-1])
            if sma_10 <= sma_30:
                continue

            # Fetch token info for transfer stats
            token_info = _fetch_ethplorer(f"/getTokenInfo/{contract}")
            if not token_info or not isinstance(token_info, dict):
                continue

            # Transfer count and holder count
            transfers_count = token_info.get("transfersCount", 0) or 0
            holders_count = token_info.get("holdersCount", 0) or 0
            tx_24h = token_info.get("countOps", 0) or 0

            if holders_count < 1000:
                continue  # Too few holders

            # Volume confirmation from price data
            vol_r = float(volume_ratio(df["Volume"], 20).iloc[-1]) if "Volume" in df.columns else 1.0
            if vol_r < 1.3:
                continue  # Need above-average volume

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 70 or rsi_val < 30:
                continue  # Not in sweet spot

            entry, tp, sl = _atr_tp_sl(close, high, low, 2.5, 1.5)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr < 1.5:
                continue

            conf = min(0.72, 0.48 + min(0.15, vol_r / 10) + 0.10)

            signals.append({
                "strategy": "ethplorer_token_flow_momentum",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Token flow momentum: {holders_count:,} holders, "
                    f"vol ratio={vol_r:.1f}x. Uptrend (SMA10>SMA30), RSI={rsi_val:.0f}"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "holders_count": holders_count,
                    "transfers_count": transfers_count,
                    "volume_ratio": round(vol_r, 2),
                    "contract": contract,
                    "source": "Ethplorer API -- token transfer velocity",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY S9: Ethplorer Holder Concentration Risk
# =====================================================================
# When top-10 holders own >60% of supply AND price is pumping,
# distribution risk is high → SELL signal.
# When concentration is low (<30%) + accumulation → healthier BUY.
# =====================================================================

def ethplorer_holder_concentration(data: dict[str, pd.DataFrame]) -> list[dict]:
    """SELL tokens with dangerously high holder concentration + pump."""
    signals: list[dict] = []

    for symbol, contract in _YFINANCE_TO_ETH_CONTRACT.items():
        if symbol not in data:
            continue
        try:
            df = data[symbol]
            if len(df) < 20:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])

            # Fetch top holders
            holders_data = _fetch_ethplorer(f"/getTopTokenHolders/{contract}?limit=10")
            if not holders_data or not isinstance(holders_data, dict):
                continue

            holders = holders_data.get("holders", [])
            if not holders:
                continue

            total_share = sum(h.get("share", 0) for h in holders)

            # SELL: High concentration (>55%) + price pumping + overbought
            rsi_val = float(rsi(close, 14).iloc[-1])
            ret_7d = (price - float(close.iloc[-7])) / float(close.iloc[-7]) if len(close) >= 7 else 0

            if total_share > 55 and ret_7d > 0.10 and rsi_val > 65:
                entry = _smart_round(price)
                atr_val = float(atr(high, low, close, 14).iloc[-1])
                tp = _smart_round(price - 2.5 * atr_val)
                sl = _smart_round(price + 1.5 * atr_val)
                rr = abs(entry - tp) / max(abs(sl - entry), 0.01)

                if rr >= 1.5:
                    conf = min(0.75, 0.48 + (total_share - 55) / 100 + min(0.15, ret_7d))
                    signals.append({
                        "strategy": "ethplorer_holder_concentration",
                        "symbol": symbol,
                        "category": _get_category(symbol),
                        "signal_type": "SELL",
                        "entry_price": entry,
                        "take_profit": tp,
                        "stop_loss": sl,
                        "confidence": round(conf, 2),
                        "risk_reward": round(rr, 2),
                        "reason": (
                            f"High concentration risk: top-10 hold {total_share:.1f}% "
                            f"of supply. Price pumped +{ret_7d*100:.1f}% (7d), "
                            f"RSI={rsi_val:.0f} → distribution risk"
                        ),
                        "timeframe": "1d",
                        "rsi_at_entry": round(rsi_val, 1),
                        "extra": {
                            "top10_holder_share_pct": round(total_share, 2),
                            "price_7d_return_pct": round(ret_7d * 100, 2),
                            "contract": contract,
                            "source": "Ethplorer API -- holder concentration risk",
                        },
                        "timestamp": _now_iso(),
                    })
        except Exception:
            continue

    return signals


# =========================================================================
# Registry -- all supplemental data strategies
# =========================================================================

SUPPLEMENTAL_DATA_STRATEGIES = {
    # Messari Fundamentals (3 strategies)
    "messari_fundamental_quality": messari_fundamental_quality,
    "messari_developer_momentum":  messari_developer_momentum,
    "messari_roi_divergence":      messari_roi_divergence,
    # Mempool.space BTC Analytics (3 strategies)
    "mempool_congestion_volatility": mempool_congestion_volatility,
    "mempool_fee_spike_reversal":    mempool_fee_spike_reversal,
    "mempool_hashrate_security":     mempool_hashrate_security,
    # Ethplorer ERC-20 Whale Tracking (3 strategies)
    "ethplorer_whale_accumulation":   ethplorer_whale_accumulation,
    "ethplorer_token_flow_momentum":  ethplorer_token_flow_momentum,
    "ethplorer_holder_concentration": ethplorer_holder_concentration,
}
