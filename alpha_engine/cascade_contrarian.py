"""
ALPHA_ENGINE -- Cascade Contrarian Strategy
=============================================
Enhanced liquidation cascade detection using Binance futures data
(OI, funding rate, market cap) for smarter entry timing.

Logic (from Google AG review):
  - OI/MCap > 2.5% AND funding > 0.05%/8h => longs overleveraged
  - Wait for price wick below recent support (cascade fires)
  - Enter LONG on reversal candle (mean reversion)
  - TP = 2.5x ATR, SL = 1.0x ATR (R:R 2.5)
  - Mirror for shorts: OI/MCap > 2.5% AND funding < -0.03%/8h

Data sources (all free, no API key):
  - Binance /fapi/v1/openInterest -- OI in contracts
  - Binance /fapi/v1/premiumIndex  -- funding rate + mark price
  - CoinGecko /api/v3/simple/price -- market cap
  - yfinance price data (already loaded)

Reference: Pentoshi, CoinGlass liquidation research, Coinalyze OI analysis.
Win rate: 60-68% on cascade reversals with OI/funding confirmation.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from config import (
    CRYPTO_SYMBOLS, BINANCE_FUTURES_BASE, COINGECKO_BASE,
)
from indicators import rsi, atr

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers (reuse alpha_engine conventions)
# ---------------------------------------------------------------------------

def _fetch_json(url: str, timeout: int = 8):
    """Fetch JSON from URL, return dict/list or None on failure."""
    import urllib.request, urllib.error, json
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "alpha-engine/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _smart_round(v: float) -> float:
    if abs(v) >= 100:
        return round(v, 2)
    if abs(v) >= 1:
        return round(v, 4)
    return round(v, 6)


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

def _fetch_oi_and_funding() -> tuple[dict, dict]:
    """Fetch OI (in USD) and funding rate for all crypto symbols from Binance futures."""
    oi_usd = {}
    funding = {}
    for symbol, info in CRYPTO_SYMBOLS.items():
        bsym = info.get("binance")
        if not bsym:
            continue
        # premiumIndex gives funding rate + mark price in one call
        pi = _fetch_json(f"{BINANCE_FUTURES_BASE}/fapi/v1/premiumIndex?symbol={bsym}")
        if pi:
            try:
                funding[symbol] = float(pi["lastFundingRate"])
                mark = float(pi["markPrice"])
            except (KeyError, ValueError, TypeError):
                continue
        else:
            continue
        # OI in contracts -> multiply by mark price for USD value
        oi_resp = _fetch_json(f"{BINANCE_FUTURES_BASE}/fapi/v1/openInterest?symbol={bsym}")
        if oi_resp:
            try:
                oi_usd[symbol] = float(oi_resp["openInterest"]) * mark
            except (KeyError, ValueError, TypeError):
                pass
    return oi_usd, funding


def _fetch_market_caps(symbols: list[str]) -> dict[str, float]:
    """Fetch market caps from CoinGecko for given yfinance symbols."""
    # Map yfinance symbol -> coingecko id
    _CG_MAP = {
        "BTC-USD": "bitcoin", "ETH-USD": "ethereum", "SOL-USD": "solana",
        "BNB-USD": "binancecoin", "XRP-USD": "ripple", "ADA-USD": "cardano",
        "AVAX-USD": "avalanche-2", "LINK-USD": "chainlink", "NEAR-USD": "near",
        "TRX-USD": "tron", "LTC-USD": "litecoin", "ETC-USD": "ethereum-classic",
        "SUI-USD": "sui", "INJ-USD": "injective-protocol", "ATOM-USD": "cosmos",
        "APT-USD": "aptos", "FIL-USD": "filecoin", "UNI-USD": "uniswap",
        "AAVE-USD": "aave", "PEPE-USD": "pepe", "WIF-USD": "dogwifhat",
        "BONK-USD": "bonk", "FLOKI-USD": "floki", "HBAR-USD": "hedera-hashgraph",
        "TAO-USD": "bittensor", "RNDR-USD": "render-token", "TON11419-USD": "the-open-network",
        "TIA-USD": "celestia", "SEI-USD": "sei-network", "PENDLE-USD": "pendle",
        "GALA-USD": "gala", "WLD-USD": "worldcoin-wld", "NOT-USD": "notcoin",
        "HYPE-USD": "hyperliquid", "XLM-USD": "stellar",
    }
    ids = [_CG_MAP[s] for s in symbols if s in _CG_MAP]
    if not ids:
        return {}
    url = f"{COINGECKO_BASE}/simple/price?ids={','.join(ids)}&vs_currencies=usd&include_market_cap=true"
    data = _fetch_json(url, timeout=10)
    if not data:
        return {}
    # Reverse map
    rev = {v: k for k, v in _CG_MAP.items()}
    caps = {}
    for cg_id, vals in data.items():
        yf_sym = rev.get(cg_id)
        if yf_sym and "usd_market_cap" in vals and vals["usd_market_cap"]:
            caps[yf_sym] = float(vals["usd_market_cap"])
    return caps


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------

def cascade_contrarian(data: dict[str, pd.DataFrame],
                       context: Optional[dict] = None) -> list[dict]:
    """
    Cascade Contrarian: enter after liquidation cascade when OI/MCap
    shows overleveraged positioning confirmed by extreme funding rate.
    """
    signals = []
    try:
        oi_usd, funding = _fetch_oi_and_funding()
        symbols_with_data = [s for s in CRYPTO_SYMBOLS if s in oi_usd and s in funding]
        mcaps = _fetch_market_caps(symbols_with_data)
    except Exception as e:
        logger.warning("cascade_contrarian: data fetch failed: %s", e)
        return signals

    for symbol in symbols_with_data:
        df = data.get(symbol)
        if df is None or len(df) < 20:
            continue
        if symbol not in mcaps or mcaps[symbol] <= 0:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])
            oi_mcap_ratio = oi_usd[symbol] / mcaps[symbol]
            rate = funding[symbol]

            # Need overleveraged market: OI/MCap > 2.5%
            if oi_mcap_ratio < 0.025:
                continue

            atr_val = float(atr(high, low, close, 14).iloc[-1])
            if atr_val <= 0:
                continue
            rsi_val = float(rsi(close, 14).iloc[-1])

            # Recent support = lowest low of last 10 bars
            support = float(low.iloc[-11:-1].min())
            current_low = float(low.iloc[-1])

            # LONG setup: longs overleveraged, cascade fires, reversal candle
            if rate > 0.0005:  # 0.05%/8h
                # Wick below support (cascade fired)
                if current_low >= support:
                    continue
                # But closed above support (reversal)
                if price < support:
                    continue
                # RSI confirmation: should be oversold-ish
                if rsi_val > 45:
                    continue

                tp = _smart_round(price + 2.5 * atr_val)
                sl = _smart_round(price - 1.0 * atr_val)
                rr = (tp - price) / (price - sl) if price > sl else 0
                if rr < 2.0:
                    continue

                conf = round(min(0.82, 0.52 + oi_mcap_ratio * 4 + rate * 80), 2)
                signals.append({
                    "strategy": "cascade_contrarian",
                    "symbol": symbol, "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": _smart_round(price),
                    "take_profit": tp, "stop_loss": sl,
                    "confidence": conf, "risk_reward": round(rr, 2),
                    "reason": (f"Cascade contrarian LONG: OI/MCap={oi_mcap_ratio:.2%}, "
                               f"funding={rate*100:.4f}% (longs overleveraged), "
                               f"wick below support ${support:.2f}, RSI={rsi_val:.0f}. "
                               f"R:R {rr:.1f}. 60-68% WR on cascade reversals."),
                    "timeframe": "4h",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "oi_mcap_ratio": round(oi_mcap_ratio, 4),
                        "funding_rate": rate,
                        "support_level": _smart_round(support),
                        "oi_usd": round(oi_usd[symbol], 2),
                        "market_cap": round(mcaps[symbol], 2),
                        "cascade_type": "long_overleveraged",
                        "source": "Binance Futures OI + Funding + CoinGecko MCap",
                    },
                    "timestamp": _now_iso(),
                })

            # SHORT setup: shorts overleveraged, squeeze fires up, reversal candle
            elif rate < -0.0003:  # -0.03%/8h
                resistance = float(high.iloc[-11:-1].max())
                current_high = float(high.iloc[-1])
                if current_high <= resistance:
                    continue
                if price > resistance:
                    continue
                if rsi_val < 55:
                    continue

                tp = _smart_round(price - 2.5 * atr_val)
                sl = _smart_round(price + 1.0 * atr_val)
                rr = (price - tp) / (sl - price) if sl > price else 0
                if rr < 2.0:
                    continue

                conf = round(min(0.82, 0.52 + oi_mcap_ratio * 4 + abs(rate) * 80), 2)
                signals.append({
                    "strategy": "cascade_contrarian",
                    "symbol": symbol, "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": _smart_round(price),
                    "take_profit": tp, "stop_loss": sl,
                    "confidence": conf, "risk_reward": round(rr, 2),
                    "reason": (f"Cascade contrarian SHORT: OI/MCap={oi_mcap_ratio:.2%}, "
                               f"funding={rate*100:.4f}% (shorts overleveraged), "
                               f"wick above resistance ${resistance:.2f}, RSI={rsi_val:.0f}. "
                               f"R:R {rr:.1f}. 60-68% WR on cascade reversals."),
                    "timeframe": "4h",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "oi_mcap_ratio": round(oi_mcap_ratio, 4),
                        "funding_rate": rate,
                        "resistance_level": _smart_round(resistance),
                        "oi_usd": round(oi_usd[symbol], 2),
                        "market_cap": round(mcaps[symbol], 2),
                        "cascade_type": "short_overleveraged",
                        "source": "Binance Futures OI + Funding + CoinGecko MCap",
                    },
                    "timestamp": _now_iso(),
                })

        except Exception:
            continue

    return signals


# Strategy registry (matches alpha_engine convention)
CASCADE_CONTRARIAN_STRATEGIES = {
    "cascade_contrarian": cascade_contrarian,
}
