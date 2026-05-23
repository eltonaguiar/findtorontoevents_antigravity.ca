"""
ALPHA_ENGINE -- On-Chain & Macro Strategies
============================================
12 strategies using on-chain metrics, macro liquidity, and blockchain data.
All use FREE API sources (no paid subscriptions required).

Strategies 34-45:
  34. mvrv_sma_proxy           -- MVRV Z-Score approximation via 200d SMA ratio
  35. hash_ribbon_buy          -- Miner capitulation/recovery from blockchain.info
  36. stablecoin_buying_power  -- SSR (Stablecoin Supply Ratio) from CoinGecko
  37. nvt_overvaluation        -- NVT ratio from blockchain.info TX volume
  38. fear_greed_extreme_dca   -- F&G ≤10 extreme-fear DCA (Nasdaq-backtested)
  39. sopr_dip_buy_proxy       -- SOPR-like metric via STH cost-basis proxy
  40. onchain_composite_score  -- Multi-layer on-chain confluence (Layers 1-4)
  41. hayes_liquidity_index    -- Arthur Hayes' Fed BS - RRP - TGA formula (FRED)
  42. pentoshi_htf_structure   -- Weekly higher lows + EMA support pullback
  43. funding_rate_arbitrage   -- Market-neutral carry (long spot + short perps)
  44. difficulty_ribbon_signal -- Difficulty ribbon compression/expansion (Woo/Puell)
  45. active_address_momentum  -- Active address 30d/90d MA crossover (Metcalfe's Law)

Data sources (all FREE):
  - api.alternative.me/fng/          (Fear & Greed, no key)
  - blockchain.info/charts/          (hash rate, TX volume, no key)
  - api.coingecko.com/api/v3/        (market caps, rate-limited)
  - fred.stlouisfed.org/             (Fed BS, RRP, TGA -- free CSV)
  - Binance public API                (funding, OI, no key)
  - yfinance price data               (already loaded by scanner)

References:
  - MVRV: Murad Mahmudov & David Puell (2018)
  - Hash Ribbons: Charles Edwards (2019)
  - NVT: Willy Woo (2017)
  - F&G Backtest: Nasdaq Research (2024)
  - SOPR: Renato Shirakashi (2019)
  - SSR: CryptoQuant (2020)
  - Liquidity Index: Arthur Hayes (2024-2026)
  - HTF Structure: Pentoshi
  - Funding Arb: Documented 19-115% annual (Amberdata/ScienceDirect)
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import (
    CRYPTO_SYMBOLS, FEAR_GREED_URL, COINGECKO_BASE,
)
from indicators import rsi, atr, sma, ema, volume_ratio


# Circuit breaker for CoinMetrics community API (403 Forbidden waste prevention)
_COINMETRICS_FAIL_COUNT = 0
_COINMETRICS_DISABLED = False


# -- Helpers (reuse from crypto_strategies) ----------------------------

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
               tp_mult: float = 3.0, sl_mult: float = 2.25,  # sl_mult aligned with crypto_strategies.py 2026-03-13
               atr_period: int = 14) -> tuple[float, float, float]:
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price + tp_mult * current_atr
    sl = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


def _fetch_json(url: str, timeout: int = 8) -> Optional[dict | list]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


# =====================================================================
# STRATEGY 34: MVRV Z-Score Proxy (200d SMA as Realized Price)
# =====================================================================
# Real MVRV = Market Cap / Realized Cap. We approximate Realized Price
# with the 200-day SMA (average cost basis of ~200-day holders).
# Ratio < 1.0 ≈ market undervalued. Ratio > 3.7 ≈ overvalued.
# BUY when ratio < 1.0 (price below average cost → capitulation).
# Academic: Mahmudov & Puell (2018); CryptoQuant validation.
# =====================================================================

def mvrv_sma_proxy(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY when price falls below 200d SMA (MVRV proxy < 1.0) with recovery."""
    signals: list[dict] = []
    # MVRV proxy works for any crypto with 200d+ price history (SMA as realized price proxy)
    target_symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                      "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "DOGE-USD",
                      "TAO-USD", "XLM-USD", "ARB11841-USD", "KAS-USD",
                      "ETC-USD", "FIL-USD", "ZEC-USD", "BAT-USD", "QNT-USD"]

    for symbol in target_symbols:
        if symbol not in data:
            continue
        try:
            df = data[symbol]
            if len(df) < 210:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            sma_200 = sma(close, 200)

            price = float(close.iloc[-1])
            sma_val = float(sma_200.iloc[-1])
            if sma_val <= 0:
                continue

            ratio = price / sma_val  # MVRV proxy

            # Z-score of ratio over 200 days
            ratios = close / sma_200
            ratios = ratios.dropna()
            if len(ratios) < 50:
                continue
            z = (ratio - float(ratios.mean())) / max(float(ratios.std()), 0.001)

            # BUY: ratio < 1.0 (below realized) AND starting to recover
            # (price > yesterday, RSI turning up from oversold)
            rsi_val = float(rsi(close, 14).iloc[-1])
            recovering = float(close.iloc[-1]) > float(close.iloc[-2])

            if ratio < 1.0 and z < -1.0 and recovering and rsi_val < 40:
                entry, tp, sl = _atr_tp_sl(close, high, low, 3.5, 1.5)

                rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
                if rr < 1.3:
                    continue

                # Confidence: deeper below SMA = higher conviction
                depth = 1.0 - ratio  # e.g., 0.15 = 15% below SMA
                conf = min(0.85, 0.55 + depth * 2.0)

                signals.append({
                    "strategy": "mvrv_sma_proxy",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"MVRV proxy {ratio:.2f} (below realized), "
                        f"Z-score {z:.1f}, RSI {rsi_val:.0f} recovering"
                    ),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "mvrv_ratio": round(ratio, 3),
                        "z_score": round(z, 2),
                        "sma_200": _smart_round(sma_val),
                        "source": "Mahmudov & Puell (2018) -- MVRV Z-Score",
                    },
                    "timestamp": _now_iso(),
                })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 34b: Real NUPL (Net Unrealized Profit/Loss) from Coin Metrics
# =====================================================================
# NUPL = (Market Cap - Realized Cap) / Market Cap
# BUY when NUPL < 0.2 (fear/capitulation zone)
# SELL when NUPL > 0.7 (euphoria zone)
# Data: Coin Metrics Community API (free, no key).
# Reference: Adamant Capital (2019), Glassnode (2020)
# =====================================================================

_COINMETRICS_NUPL_URL = (
    "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
    "?assets=btc&metrics=CapMrktCurUSD,CapRealUSD&frequency=1d&page_size=30"
)


def _fetch_nupl() -> Optional[float]:
    """Fetch real NUPL from Coin Metrics: (MarketCap - RealizedCap) / MarketCap.

    Returns latest NUPL value, or None on failure.
    """
    global _COINMETRICS_FAIL_COUNT, _COINMETRICS_DISABLED
    if _COINMETRICS_DISABLED:
        return None
    try:
        req = urllib.request.Request(
            _COINMETRICS_NUPL_URL,
            headers={"User-Agent": "AlphaEngine/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
        _COINMETRICS_FAIL_COUNT = 0  # Reset on success
        rows = raw.get("data", [])
        if not rows:
            return None
        # Use latest row with both metrics present
        for row in reversed(rows):
            mcap = row.get("CapMrktCurUSD")
            rcap = row.get("CapRealUSD")
            if mcap is not None and rcap is not None:
                mcap_f = float(mcap)
                rcap_f = float(rcap)
                if mcap_f > 0:
                    return (mcap_f - rcap_f) / mcap_f
        return None
    except Exception:
        _COINMETRICS_FAIL_COUNT += 1
        if _COINMETRICS_FAIL_COUNT >= 3 and not _COINMETRICS_DISABLED:
            _COINMETRICS_DISABLED = True
            try:
                print(f"  [onchain] CoinMetrics CIRCUIT BREAKER: disabled after {_COINMETRICS_FAIL_COUNT} failures")
            except ValueError:
                pass
        return None


def nupl_zone_signal(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY BTC in NUPL fear zone (< 0.2), SELL in euphoria (> 0.7).

    Primary: Real NUPL from Coin Metrics (MarketCap & RealizedCap).
    Fallback: Skip signal if API unavailable (no proxy -- NUPL needs real on-chain data).
    Reference: Adamant Capital (2019) -- NUPL zones predict cycle tops/bottoms.
    """
    signals: list[dict] = []

    if "BTC-USD" not in data:
        return signals

    nupl = _fetch_nupl()
    if nupl is None:
        return signals  # No proxy fallback -- NUPL requires real on-chain data

    try:
        df = data["BTC-USD"]
        if len(df) < 30:
            return signals

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        price = float(close.iloc[-1])
        rsi_val = float(rsi(close, 14).iloc[-1])

        # -- BUY zone: NUPL < 0.2 (fear / capitulation) --
        if nupl < 0.2:
            entry, tp, sl = _atr_tp_sl(close, high, low, 4.0, 1.5)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr >= 1.3:
                # Deeper fear = higher confidence
                depth = max(0.0, 0.2 - nupl)
                conf = min(0.85, 0.60 + depth * 3.0)

                zone = "capitulation" if nupl < 0.0 else "fear"
                signals.append({
                    "strategy": "nupl_zone_signal",
                    "symbol": "BTC-USD",
                    "category": "crypto",
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"NUPL {nupl:.3f} ({zone} zone < 0.2) -- "
                        f"market-wide unrealized loss = accumulation opportunity. "
                        f"RSI {rsi_val:.0f}"
                    ),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "nupl": round(nupl, 4),
                        "nupl_zone": zone,
                        "data_source": "Coin Metrics Community API (real NUPL)",
                        "source": "Adamant Capital (2019) -- NUPL Cycle Zones",
                    },
                    "timestamp": _now_iso(),
                })

        # -- SELL zone: NUPL > 0.7 (euphoria / greed) --
        elif nupl > 0.7:
            entry, tp, sl = _atr_tp_sl(close, high, low, 3.0, 1.5)
            # Invert for SELL: tp below, sl above
            tp_sell = round(price * 0.95, 2)
            sl_sell = round(price * 1.03, 2)
            rr = abs(price - tp_sell) / max(abs(sl_sell - price), 0.01)
            if rr >= 1.0:
                conf = min(0.80, 0.55 + (nupl - 0.7) * 3.0)

                signals.append({
                    "strategy": "nupl_zone_signal",
                    "symbol": "BTC-USD",
                    "category": "crypto",
                    "signal_type": "SELL",
                    "entry_price": _smart_round(price),
                    "take_profit": tp_sell,
                    "stop_loss": sl_sell,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"NUPL {nupl:.3f} (euphoria zone > 0.7) -- "
                        f"extreme unrealized profit = distribution risk. "
                        f"RSI {rsi_val:.0f}"
                    ),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "nupl": round(nupl, 4),
                        "nupl_zone": "euphoria",
                        "data_source": "Coin Metrics Community API (real NUPL)",
                        "source": "Adamant Capital (2019) -- NUPL Cycle Zones",
                    },
                    "timestamp": _now_iso(),
                })

    except Exception:
        pass

    return signals


# =====================================================================
# STRATEGY 35: Hash Ribbon Buy Signal (Miner Capitulation Recovery)
# =====================================================================
# 30-day hash rate MA crosses ABOVE 60-day MA after being below =
# miner capitulation ends → historically strong BUY signal.
# Data: blockchain.info/charts/hash-rate (FREE, no key).
# Charles Edwards (2019): 14 signals since 2013, 64% profitable,
# premium data variant: 78% success rate.
# =====================================================================

_HASHRATE_URL = "https://api.blockchain.info/charts/hash-rate?timespan=180days&format=json&rollingAverage=1days"


def hash_ribbon_buy(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY BTC when Hash Ribbon is bullish (30d MA above 60d MA after recent cross or proximity)."""
    signals: list[dict] = []

    # BTC-ONLY: Hash rate data from blockchain.info is Bitcoin-specific (PoW mining).
    # Other chains use PoS or different consensus -- no hash ribbon equivalent.
    if "BTC-USD" not in data:
        return signals

    try:
        # Fetch hash rate from blockchain.info (FREE) -- 180 days for reliable MAs
        raw = _fetch_json(_HASHRATE_URL, timeout=10)
        if not raw or "values" not in raw:
            return signals

        values = raw["values"]
        if len(values) < 65:
            return signals

        # Convert to pandas Series
        dates = [datetime.fromtimestamp(v["x"], tz=timezone.utc) for v in values]
        hr_values = [v["y"] for v in values]
        hr_series = pd.Series(hr_values, index=dates)

        # Calculate 30d and 60d moving averages
        ma_30 = hr_series.rolling(30, min_periods=25).mean()
        ma_60 = hr_series.rolling(60, min_periods=50).mean()

        if ma_30.isna().iloc[-1] or ma_60.isna().iloc[-1]:
            return signals

        current_30 = float(ma_30.iloc[-1])
        current_60 = float(ma_60.iloc[-1])

        # Check for recent crossover in last 7 data points (not just 1-bar)
        crossed_up_recently = False
        for lookback in range(1, min(8, len(ma_30) - 1)):
            p30 = float(ma_30.iloc[-(lookback + 1)])
            p60 = float(ma_60.iloc[-(lookback + 1)])
            if p30 <= p60 and current_30 > current_60:
                crossed_up_recently = True
                break

        # Also allow: 30d MA is above 60d MA and gap is still small (< 3%)
        # This captures the early recovery phase after capitulation
        bullish_ribbon = (current_30 > current_60 and
                          (current_30 - current_60) / current_60 < 0.03)

        if not crossed_up_recently and not bullish_ribbon:
            return signals

        df = data["BTC-USD"]
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        rsi_val = float(rsi(close, 14).iloc[-1])
        entry, tp, sl = _atr_tp_sl(close, high, low, 4.0, 2.0)  # wider stops for macro signal

        rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
        if rr < 1.0:
            return signals

        # Confidence based on how strongly 30d crossed above 60d
        gap_pct = (current_30 - current_60) / current_60 * 100
        conf = min(0.80, 0.60 + gap_pct * 0.05)

        signals.append({
            "strategy": "hash_ribbon_buy",
            "symbol": "BTC-USD",
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Hash Ribbon BUY: 30d MA above 60d MA "
                f"(gap {gap_pct:.1f}%), miner capitulation recovery phase"
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "hashrate_30d_ma": round(current_30, 2),
                "hashrate_60d_ma": round(current_60, 2),
                "gap_pct": round(gap_pct, 2),
                "source": "Charles Edwards (2019) -- Hash Ribbons",
            },
            "timestamp": _now_iso(),
        })
    except Exception:
        pass

    return signals


# =====================================================================
# STRATEGY 36: Stablecoin Supply Ratio (SSR) -- Buying Power
# =====================================================================
# SSR = BTC Market Cap / Total Stablecoin Market Cap.
# LOW SSR = large stablecoin reserves relative to BTC = high buying
# pressure = bullish. Uses CoinGecko free API for market caps.
# CryptoQuant (2020): SSR is a reliable indicator of potential buying power.
# =====================================================================

def stablecoin_buying_power(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY BTC when Stablecoin Supply Ratio is low (high buying power)."""
    signals: list[dict] = []

    # BTC-ONLY: SSR = BTC market cap / stablecoin market cap. The ratio is specific
    # to Bitcoin's dominance vs stablecoins. Could extend to total crypto cap in future.
    if "BTC-USD" not in data:
        return signals

    try:
        # Get BTC market cap from CoinGecko
        btc_url = f"{COINGECKO_BASE}/simple/price?ids=bitcoin&vs_currencies=usd&include_market_cap=true"
        btc_data = _fetch_json(btc_url, timeout=10)
        if not btc_data or "bitcoin" not in btc_data:
            return signals

        btc_mcap = btc_data["bitcoin"].get("usd_market_cap", 0)
        if btc_mcap <= 0:
            return signals

        # Get top stablecoin market caps
        stable_url = f"{COINGECKO_BASE}/simple/price?ids=tether,usd-coin,dai,first-digital-usd&vs_currencies=usd&include_market_cap=true"
        stable_data = _fetch_json(stable_url, timeout=10)
        if not stable_data:
            return signals

        total_stable_mcap = sum(
            v.get("usd_market_cap", 0) for v in stable_data.values()
        )
        if total_stable_mcap <= 0:
            return signals

        # Calculate SSR
        ssr = btc_mcap / total_stable_mcap

        # Historically SSR < 5 suggests high buying power (bullish)
        # SSR > 15 suggests low buying power (bearish)
        # We focus on low SSR for BUY signals
        if ssr >= 8.0:
            return signals  # Not enough buying power

        df = data["BTC-USD"]
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        rsi_val = float(rsi(close, 14).iloc[-1])

        # Extra check: don't buy into extreme overbought
        if rsi_val > 75:
            return signals

        entry, tp, sl = _atr_tp_sl(close, high, low, 3.0, 1.5)
        rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
        if rr < 1.3:
            return signals

        # Confidence: lower SSR = higher conviction
        if ssr < 3.0:
            conf = 0.80
        elif ssr < 5.0:
            conf = 0.70
        else:
            conf = 0.60

        signals.append({
            "strategy": "stablecoin_buying_power",
            "symbol": "BTC-USD",
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"SSR {ssr:.1f} (low = high buying power), "
                f"stablecoin dry powder ${total_stable_mcap/1e9:.0f}B vs "
                f"BTC mcap ${btc_mcap/1e9:.0f}B"
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "ssr": round(ssr, 2),
                "btc_mcap_b": round(btc_mcap / 1e9, 1),
                "stablecoin_mcap_b": round(total_stable_mcap / 1e9, 1),
                "source": "CryptoQuant (2020) -- Stablecoin Supply Ratio",
            },
            "timestamp": _now_iso(),
        })
    except Exception:
        pass

    return signals


# =====================================================================
# STRATEGY 37: NVT Ratio Signal -- Overvaluation Warning / Value Buy
# =====================================================================
# NVT = Market Cap / Daily TX Volume (90d MA). Like P/E for Bitcoin.
# Willy Woo (2017): NVT > 150 = overbought, NVT dropping = undervalued.
# Data: blockchain.info/charts/ (FREE, no key).
# =====================================================================

_TX_VOLUME_URL = "https://api.blockchain.info/charts/estimated-transaction-volume-usd?timespan=180days&format=json&rollingAverage=90days"
_MARKET_CAP_URL = "https://api.blockchain.info/charts/market-cap?timespan=180days&format=json"


def nvt_overvaluation(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY BTC when NVT is low (undervalued network). SELL when NVT > 150."""
    signals: list[dict] = []

    # BTC-ONLY: NVT uses blockchain.info TX volume data, which is Bitcoin-specific.
    # ETH NVT would require Etherscan API (paid). Other chains lack reliable TX volume APIs.
    if "BTC-USD" not in data:
        return signals

    try:
        # Fetch TX volume (90d rolling average) and market cap
        tx_raw = _fetch_json(_TX_VOLUME_URL, timeout=10)
        mcap_raw = _fetch_json(_MARKET_CAP_URL, timeout=10)

        if not tx_raw or "values" not in tx_raw:
            return signals
        if not mcap_raw or "values" not in mcap_raw:
            return signals

        tx_vals = tx_raw["values"]
        mcap_vals = mcap_raw["values"]

        if len(tx_vals) < 30 or len(mcap_vals) < 30:
            return signals

        # Get latest values
        latest_tx = float(tx_vals[-1]["y"])
        latest_mcap = float(mcap_vals[-1]["y"])

        if latest_tx <= 0:
            return signals

        nvt = latest_mcap / latest_tx

        # Calculate NVT history for Z-score
        nvt_history = []
        # Match timestamps as closely as possible
        tx_dict = {v["x"]: v["y"] for v in tx_vals}
        for mv in mcap_vals:
            tx_v = tx_dict.get(mv["x"])
            if tx_v and tx_v > 0:
                nvt_history.append(mv["y"] / tx_v)

        if len(nvt_history) < 30:
            return signals

        nvt_arr = np.array(nvt_history)
        nvt_mean = float(np.mean(nvt_arr))
        nvt_std = float(np.std(nvt_arr))
        if nvt_std < 0.01:
            return signals

        z = (nvt - nvt_mean) / nvt_std

        df = data["BTC-USD"]
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        rsi_val = float(rsi(close, 14).iloc[-1])

        # BUY: NVT below mean (undervalued network activity relative to price)
        # Relaxed from z < -1.0 to z < -0.7 to catch more value opportunities
        if z < -0.7 and rsi_val < 65:
            entry, tp, sl = _atr_tp_sl(close, high, low, 3.5, 1.5)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr < 1.3:
                return signals

            conf = min(0.80, 0.55 + abs(z) * 0.10)

            signals.append({
                "strategy": "nvt_overvaluation",
                "symbol": "BTC-USD",
                "category": "crypto",
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"NVT {nvt:.0f} (Z={z:.1f}), network undervalued -- "
                    f"TX volume high relative to market cap"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "nvt_ratio": round(nvt, 1),
                    "nvt_z_score": round(z, 2),
                    "nvt_mean": round(nvt_mean, 1),
                    "daily_tx_volume_usd": round(latest_tx, 0),
                    "source": "Willy Woo (2017) -- NVT Ratio",
                },
                "timestamp": _now_iso(),
            })

        # SELL: NVT very high (overvalued, price disconnected from usage)
        # Relaxed from z > 2.0 to z > 1.5 and nvt > 100 (from 120)
        elif z > 1.5 and nvt > 100:
            entry_p = float(close.iloc[-1])
            atr_val = float(atr(high, low, close, 14).iloc[-1])
            tp_sell = entry_p - 3.0 * atr_val  # target below
            sl_sell = entry_p + 1.5 * atr_val  # stop above
            rr = abs(entry_p - tp_sell) / max(abs(sl_sell - entry_p), 0.01)
            if rr < 1.3:
                return signals

            conf = min(0.75, 0.50 + z * 0.05)

            signals.append({
                "strategy": "nvt_overvaluation",
                "symbol": "BTC-USD",
                "category": "crypto",
                "signal_type": "SELL",
                "entry_price": _smart_round(entry_p),
                "take_profit": _smart_round(tp_sell),
                "stop_loss": _smart_round(sl_sell),
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"NVT {nvt:.0f} (Z={z:.1f}), network OVERVALUED -- "
                    f"price disconnected from transaction volume"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "nvt_ratio": round(nvt, 1),
                    "nvt_z_score": round(z, 2),
                    "source": "Willy Woo (2017) -- NVT Ratio",
                },
                "timestamp": _now_iso(),
            })
    except Exception:
        pass

    return signals


# =====================================================================
# STRATEGY 38: Fear & Greed Extreme DCA (Nasdaq-Backtested)
# =====================================================================
# Different from existing crypto_fear_greed_contrarian -- this uses
# the exact Nasdaq-published backtested rules:
# BUY when F&G ≤ 10 (extreme fear), SELL when F&G > 35.
# Returned 14.6% annually, 133.4% cumulative, max DD -25.3%.
# Also tracks multi-day persistence (3+ days at extreme = stronger).
# Source: Nasdaq Research (2024); crypto-alpha-drip Medium backtest.
# =====================================================================

def fear_greed_extreme_dca(data: dict[str, pd.DataFrame],
                           context: Optional[dict] = None) -> list[dict]:
    """BUY any major crypto when F&G hits extreme fear (≤10) for 2+ days."""
    signals: list[dict] = []

    try:
        # Fetch Fear & Greed history (last 10 days)
        fg_url = f"{FEAR_GREED_URL}?limit=10"
        fg_data = _fetch_json(fg_url, timeout=8)

        if not fg_data or "data" not in fg_data:
            return signals

        fg_entries = fg_data["data"]
        if not fg_entries:
            return signals

        current_fg = int(fg_entries[0]["value"])

        # Count consecutive days of extreme fear (≤10)
        consecutive_extreme = 0
        for entry in fg_entries:
            if int(entry["value"]) <= 10:
                consecutive_extreme += 1
            else:
                break

        # Need at least 2 consecutive days of extreme fear
        if current_fg > 10 or consecutive_extreme < 2:
            return signals

        # Target major caps for DCA safety -- F&G is market-wide, applies to all liquid crypto
        target_symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                          "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "DOGE-USD",
                          "TAO-USD", "XLM-USD", "ARB11841-USD", "KAS-USD",
                          "ETC-USD", "FIL-USD", "ZEC-USD", "BAT-USD", "QNT-USD"]

        for symbol in target_symbols:
            if symbol not in data:
                continue
            try:
                df = data[symbol]
                if len(df) < 50:
                    continue

                close = df["Close"]
                high = df["High"]
                low = df["Low"]
                rsi_val = float(rsi(close, 14).iloc[-1])

                # Don't buy into complete freefall -- need some stabilization
                price = float(close.iloc[-1])
                price_2d_ago = float(close.iloc[-3])
                still_crashing = (price - price_2d_ago) / price_2d_ago < -0.15

                if still_crashing:
                    continue

                entry, tp, sl = _atr_tp_sl(close, high, low, 4.0, 2.0)
                rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
                if rr < 1.0:
                    continue

                # Confidence: more consecutive extreme days = higher
                conf = min(0.85, 0.60 + consecutive_extreme * 0.05)

                signals.append({
                    "strategy": "fear_greed_extreme_dca",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"F&G {current_fg} (EXTREME FEAR x{consecutive_extreme}d), "
                        f"Nasdaq-backtested DCA rule: buy ≤10, sell >35. "
                        f"RSI {rsi_val:.0f}"
                    ),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "fear_greed": current_fg,
                        "consecutive_extreme_days": consecutive_extreme,
                        "fg_classification": fg_entries[0].get("value_classification", ""),
                        "source": "Nasdaq Research (2024) -- F&G DCA Backtest",
                    },
                    "timestamp": _now_iso(),
                })
            except Exception:
                continue
    except Exception:
        pass

    return signals


# =====================================================================
# STRATEGY 39: SOPR Dip-Buy Proxy (Short-Term Holder Cost Basis)
# =====================================================================
# Real SOPR needs UTXO data. We approximate STH-SOPR using the
# 30-day SMA as short-term holder cost basis. When price drops below
# the 30d SMA by > 5% then recovers above it = "SOPR reset to 1.0"
# in an uptrend → buy the dip.
# Renato Shirakashi (2019): SOPR resets in uptrends are buy signals.
# Academic: After STH-SOPR at 0.96, BTC rallied 62% (Apr 2025 data).
# =====================================================================

def _fetch_sth_sopr() -> Optional[list[float]]:
    """Fetch real STH-SOPR from Coin Metrics free community API.

    Returns last 7 days of STH-SOPR values, or None on failure.
    API: community-api.coinmetrics.io (no key needed).
    """
    url = (
        "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
        "?assets=btc&metrics=SOPRSth&frequency=1d&page_size=30"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
        rows = raw.get("data", [])
        if not rows:
            return None
        # Extract SOPRSth values -- last 7 days
        values = []
        for row in rows[-7:]:
            val = row.get("SOPRSth")
            if val is not None:
                values.append(float(val))
        return values if values else None
    except Exception:
        return None


def sopr_dip_buy_proxy(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY BTC when STH-SOPR < 0.98 (short-term holder capitulation).

    Primary: Real STH-SOPR from Coin Metrics free API.
    Fallback: SMA-based proxy if API is unavailable.
    Reference: Renato Shirakashi (2019) -- SOPR capitulation buy signal.
    """
    signals: list[dict] = []

    # -- Try real STH-SOPR from Coin Metrics first --
    sth_sopr_values = _fetch_sth_sopr()
    use_real_sopr = sth_sopr_values is not None and len(sth_sopr_values) >= 3

    if use_real_sopr and "BTC-USD" in data:
        try:
            df = data["BTC-USD"]
            if len(df) >= 30:
                close = df["Close"]
                high = df["High"]
                low = df["Low"]
                price = float(close.iloc[-1])
                latest_sopr = sth_sopr_values[-1]
                avg_sopr_7d = sum(sth_sopr_values) / len(sth_sopr_values)

                # Signal: STH-SOPR < 0.98 = short-term holders selling at loss (capitulation)
                if latest_sopr < 0.98:
                    rsi_val = float(rsi(close, 14).iloc[-1])
                    # Don't buy into extreme overbought
                    if rsi_val <= 72:
                        entry, tp, sl = _atr_tp_sl(close, high, low, 3.0, 1.5)
                        rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
                        if rr >= 1.3:
                            # Deeper capitulation = higher confidence
                            depth = max(0.0, 0.98 - latest_sopr)  # e.g., 0.05 if SOPR=0.93
                            conf = min(0.85, 0.60 + depth * 5.0)

                            signals.append({
                                "strategy": "sopr_dip_buy_proxy",
                                "symbol": "BTC-USD",
                                "category": "crypto",
                                "signal_type": "BUY",
                                "entry_price": entry,
                                "take_profit": tp,
                                "stop_loss": sl,
                                "confidence": round(conf, 2),
                                "risk_reward": round(rr, 2),
                                "reason": (
                                    f"STH-SOPR {latest_sopr:.3f} (< 0.98) -- short-term holders "
                                    f"selling at loss = capitulation. 7d avg SOPR {avg_sopr_7d:.3f}. "
                                    f"RSI {rsi_val:.0f}"
                                ),
                                "timeframe": "1d",
                                "rsi_at_entry": round(rsi_val, 1),
                                "extra": {
                                    "sth_sopr": round(latest_sopr, 4),
                                    "sth_sopr_7d_avg": round(avg_sopr_7d, 4),
                                    "data_source": "Coin Metrics Community API (real STH-SOPR)",
                                    "source": "Shirakashi (2019) -- SOPR Capitulation Buy Signal",
                                },
                                "timestamp": _now_iso(),
                            })
                # If real SOPR fetched, return whether or not signal triggered
                return signals
        except Exception:
            pass  # Fall through to proxy

    # -- Fallback: SMA-based SOPR proxy (old logic) --
    for symbol in ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                   "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "DOGE-USD",
                   "TAO-USD", "XLM-USD", "ARB11841-USD", "KAS-USD",
                   "ETC-USD", "FIL-USD", "ZEC-USD", "BAT-USD", "QNT-USD"]:
        if symbol not in data:
            continue
        try:
            df = data[symbol]
            if len(df) < 210:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            sma_30 = sma(close, 30)
            sma_200_val = sma(close, 200)

            price = float(close.iloc[-1])
            sma30_val = float(sma_30.iloc[-1])
            sma200_val = float(sma_200_val.iloc[-1])

            if sma30_val <= 0 or sma200_val <= 0:
                continue

            # Must be in uptrend (price above 200d SMA)
            if price < sma200_val * 0.98:
                continue

            # Check: was below 30d SMA recently (within last 5 bars)
            was_below = False
            max_dip = 0.0
            for i in range(-5, -1):
                p = float(close.iloc[i])
                s = float(sma_30.iloc[i])
                if s > 0 and p < s:
                    was_below = True
                    dip = (s - p) / s
                    max_dip = max(max_dip, dip)

            # Now must be above 30d SMA (recovery)
            recovered = price > sma30_val

            if not was_below or not recovered:
                continue

            # Need meaningful dip (> 3%)
            if max_dip < 0.03:
                continue

            rsi_val = float(rsi(close, 14).iloc[-1])

            # Don't buy into extreme overbought
            if rsi_val > 72:
                continue

            entry, tp, sl = _atr_tp_sl(close, high, low, 3.0, 1.5)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr < 1.3:
                continue

            # Confidence: deeper the dip was, the better
            conf = min(0.80, 0.55 + max_dip * 3.0)

            signals.append({
                "strategy": "sopr_dip_buy_proxy",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"SOPR proxy reset (fallback): dipped {max_dip*100:.1f}% below 30d SMA "
                    f"then recovered -- uptrend intact (above 200d SMA). "
                    f"RSI {rsi_val:.0f}"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "max_dip_pct": round(max_dip * 100, 1),
                    "sma_30": _smart_round(sma30_val),
                    "sma_200": _smart_round(sma200_val),
                    "sopr_proxy": round(price / sma30_val, 3),
                    "data_source": "SMA proxy (Coin Metrics API unavailable)",
                    "source": "Shirakashi (2019) -- SOPR Reset Buy Signal",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 40: On-Chain Composite Confluence Score
# =====================================================================
# Multi-layer signal combining on-chain metrics:
#   Layer 1 (Macro):  MVRV proxy + price vs 200d SMA
#   Layer 2 (Flow):   Volume trend + stablecoin buying power hint
#   Layer 3 (Timing): Fear & Greed + RSI
#   Layer 4 (Smart $): Whale-size volume bars (>5x avg)
# Fires BUY only when 3+ layers agree. This is the "kitchen sink"
# composite signal for maximum conviction entries.
# =====================================================================

def onchain_composite_score(data: dict[str, pd.DataFrame],
                            context: Optional[dict] = None) -> list[dict]:
    """BUY when 3+ on-chain layers agree (MVRV, volume, F&G, whale bars)."""
    signals: list[dict] = []

    # Composite score uses price-based proxies (SMA, volume, F&G, whale bars) -- works for all liquid crypto
    for symbol in ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                   "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "DOGE-USD",
                   "TAO-USD", "XLM-USD", "ARB11841-USD", "KAS-USD",
                   "ETC-USD", "FIL-USD", "ZEC-USD", "BAT-USD", "QNT-USD"]:
        if symbol not in data:
            continue
        try:
            df = data[symbol]
            if len(df) < 210:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            vol = df["Volume"]

            price = float(close.iloc[-1])

            # -- Layer 1: Macro -- price vs 200d SMA (MVRV proxy) --
            sma_200_s = sma(close, 200)
            sma_200_v = float(sma_200_s.iloc[-1])
            layer1_score = 0
            if sma_200_v > 0:
                ratio = price / sma_200_v
                if ratio < 1.05:  # Near or below realized → bullish
                    layer1_score = 2
                elif ratio < 1.15:
                    layer1_score = 1

            # -- Layer 2: Volume trend -- rising volume on up-days --
            vol_r = volume_ratio(vol, 20)
            vol_ratio_val = float(vol_r.iloc[-1])
            # Check if recent volume is on up-days
            up_vol_days = 0
            for i in range(-5, 0):
                try:
                    if (float(close.iloc[i]) > float(close.iloc[i - 1])
                            and float(vol.iloc[i]) > float(vol.rolling(20).mean().iloc[i])):
                        up_vol_days += 1
                except (IndexError, ValueError):
                    pass
            layer2_score = 0
            if vol_ratio_val >= 2.0:
                layer2_score = 2
            elif vol_ratio_val >= 1.3:
                layer2_score = 1

            # -- Layer 3: Fear & Greed -- extreme fear --
            layer3_score = 0
            fg_val = None
            if context and "fear_greed" in context:
                fg_val = context["fear_greed"]
            else:
                fg_data = _fetch_json(f"{FEAR_GREED_URL}?limit=1", timeout=5)
                if fg_data and "data" in fg_data and fg_data["data"]:
                    fg_val = int(fg_data["data"][0]["value"])

            if fg_val is not None:
                if fg_val <= 15:
                    layer3_score = 2
                elif fg_val <= 25:
                    layer3_score = 1

            # -- Layer 4: Whale accumulation -- volume > 5x average --
            layer4_score = 0
            avg_vol = float(vol.rolling(20).mean().iloc[-1])
            recent_whale_bars = 0
            if avg_vol > 0:
                for i in range(-5, 0):
                    v = float(vol.iloc[i])
                    c = float(close.iloc[i])
                    o = float(df["Open"].iloc[i])
                    if v > 5.0 * avg_vol and c > o:  # whale bar + bullish
                        recent_whale_bars += 1

            if recent_whale_bars >= 2:
                layer4_score = 2
            elif recent_whale_bars >= 1:
                layer4_score = 1

            # -- Composite --
            total_score = layer1_score + layer2_score + layer3_score + layer4_score
            max_score = 8
            layers_agreeing = sum(1 for s in [layer1_score, layer2_score,
                                              layer3_score, layer4_score] if s > 0)

            # Need at least 3 layers to agree for a signal
            if layers_agreeing < 3 or total_score < 4:
                continue

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 72:
                continue

            entry, tp, sl = _atr_tp_sl(close, high, low, 3.5, 1.5)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr < 1.3:
                continue

            conf = min(0.90, 0.50 + (total_score / max_score) * 0.40)

            layer_desc = []
            if layer1_score > 0:
                layer_desc.append(f"MVRV({layer1_score})")
            if layer2_score > 0:
                layer_desc.append(f"VOL({layer2_score})")
            if layer3_score > 0:
                layer_desc.append(f"F&G({layer3_score})")
            if layer4_score > 0:
                layer_desc.append(f"WHALE({layer4_score})")

            signals.append({
                "strategy": "onchain_composite_score",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"On-chain composite {total_score}/{max_score}: "
                    f"{'+'.join(layer_desc)} -- {layers_agreeing}/4 layers agree"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "composite_score": total_score,
                    "max_score": max_score,
                    "layers_agreeing": layers_agreeing,
                    "layer1_mvrv": layer1_score,
                    "layer2_volume": layer2_score,
                    "layer3_fg": layer3_score,
                    "layer4_whale": layer4_score,
                    "fear_greed": fg_val,
                    "whale_bars_5d": recent_whale_bars,
                    "source": "Multi-layer on-chain confluence model",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 41: Hayes USD Liquidity Index (Macro Crypto Timing)
# =====================================================================
# Arthur Hayes' formula: Liquidity = Fed Balance Sheet - RRP - TGA.
# When liquidity is rising → BUY crypto. When falling → reduce/SELL.
# Data: FRED (WALCL, RRPONTSYD, WTREGEN) -- all FREE CSV, weekly update.
# Hayes predicted BTC to $200K in 2026 using this framework.
# "The traditional 4-year Bitcoin cycle is dead -- liquidity is king."
# =====================================================================

_FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
# WALCL = Fed balance sheet (weekly, Wed), RRPONTSYD = RRP (daily), WTREGEN = TGA (weekly)


def _fetch_fred_csv(series_id: str, days_back: int = 120) -> Optional[pd.Series]:
    """Fetch FRED time series as CSV (FREE, no API key needed)."""
    from datetime import timedelta
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    url = (
        f"{_FRED_CSV_BASE}?id={series_id}"
        f"&cosd={start.strftime('%Y-%m-%d')}"
        f"&coed={end.strftime('%Y-%m-%d')}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            text = resp.read().decode("utf-8")

        lines = text.strip().split("\n")
        if len(lines) < 2:
            return None

        dates, vals = [], []
        for line in lines[1:]:  # skip header
            parts = line.split(",")
            if len(parts) != 2 or parts[1] == ".":
                continue
            try:
                d = datetime.strptime(parts[0], "%Y-%m-%d")
                v = float(parts[1])
                dates.append(d)
                vals.append(v)
            except (ValueError, IndexError):
                continue

        if not dates:
            return None

        return pd.Series(vals, index=pd.DatetimeIndex(dates), name=series_id)
    except Exception:
        return None


def hayes_liquidity_index(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY BTC/ETH when Hayes USD Liquidity Index is rising (expanding)."""
    signals: list[dict] = []

    if "BTC-USD" not in data:
        return signals

    try:
        # Fetch the three FRED series
        walcl = _fetch_fred_csv("WALCL", 120)      # Fed balance sheet (millions)
        rrp = _fetch_fred_csv("RRPONTSYD", 120)     # Reverse repo (billions)
        tga = _fetch_fred_csv("WTREGEN", 120)        # Treasury general account (millions)

        if walcl is None or rrp is None or tga is None:
            return signals

        if len(walcl) < 8 or len(rrp) < 8 or len(tga) < 8:
            return signals

        # Normalize units: WALCL is in millions, RRP is in billions, TGA is in millions
        # Convert all to billions for consistency
        walcl_b = walcl / 1000.0          # millions → billions
        rrp_b = rrp                        # already billions
        tga_b = tga / 1000.0              # millions → billions

        # Align to common dates (use last available for each)
        latest_walcl = float(walcl_b.iloc[-1])
        latest_rrp = float(rrp_b.iloc[-1])
        latest_tga = float(tga_b.iloc[-1])

        # Hayes formula: Liquidity = Fed BS - RRP - TGA
        current_liq = latest_walcl - latest_rrp - latest_tga

        # Calculate liquidity change over last 4 weeks
        # Use weekly values for WALCL and TGA, approximate for RRP
        if len(walcl_b) >= 5 and len(rrp_b) >= 20 and len(tga_b) >= 5:
            prev_walcl = float(walcl_b.iloc[-5])   # ~4 weeks ago
            prev_rrp = float(rrp_b.iloc[-20])       # ~4 weeks ago (daily)
            prev_tga = float(tga_b.iloc[-5])         # ~4 weeks ago
            prev_liq = prev_walcl - prev_rrp - prev_tga
        else:
            return signals

        liq_change = current_liq - prev_liq
        liq_change_pct = liq_change / abs(prev_liq) * 100 if prev_liq != 0 else 0

        # Signal: BUY when liquidity is expanding (rising)
        # The bigger the expansion, the stronger the signal
        if liq_change <= 0:
            return signals  # Liquidity contracting -- no buy

        # Hayes liquidity is a macro signal -- rising Fed liquidity lifts all crypto boats
        for symbol in ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                        "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "DOGE-USD",
                        "TAO-USD", "XLM-USD", "ARB11841-USD", "KAS-USD",
                        "ETC-USD", "FIL-USD", "ZEC-USD", "BAT-USD", "QNT-USD"]:
            if symbol not in data:
                continue
            try:
                df = data[symbol]
                if len(df) < 50:
                    continue

                close = df["Close"]
                high = df["High"]
                low = df["Low"]
                rsi_val = float(rsi(close, 14).iloc[-1])

                # Don't buy into extreme overbought
                if rsi_val > 78:
                    continue

                entry, tp, sl = _atr_tp_sl(close, high, low, 4.0, 2.0)
                rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
                if rr < 1.0:
                    continue

                # Confidence: larger liquidity expansion = higher conviction
                if liq_change_pct > 2.0:
                    conf = 0.82
                elif liq_change_pct > 1.0:
                    conf = 0.72
                elif liq_change_pct > 0.3:
                    conf = 0.62
                else:
                    conf = 0.55

                signals.append({
                    "strategy": "hayes_liquidity_index",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"Hayes Liquidity expanding +{liq_change_pct:.1f}% "
                        f"(${current_liq:.0f}B, was ${prev_liq:.0f}B). "
                        f"Fed BS ${latest_walcl:.0f}B - RRP ${latest_rrp:.0f}B "
                        f"- TGA ${latest_tga:.0f}B"
                    ),
                    "timeframe": "1w",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "liquidity_index_b": round(current_liq, 1),
                        "liquidity_change_pct": round(liq_change_pct, 2),
                        "fed_bs_b": round(latest_walcl, 1),
                        "rrp_b": round(latest_rrp, 1),
                        "tga_b": round(latest_tga, 1),
                        "source": "Arthur Hayes (2024-2026) -- USD Liquidity Index",
                    },
                    "timestamp": _now_iso(),
                })
            except Exception:
                continue
    except Exception:
        pass

    return signals


# =====================================================================
# STRATEGY 42: Pentoshi HTF Market Structure (Weekly S/R + Trend)
# =====================================================================
# Pentoshi's method: Weekly chart structure + 21-week EMA + 200d EMA.
# BUY when: weekly higher lows intact, price retests HTF support,
# both 21w EMA and 200d EMA are below price (bullish structure).
# Grew small account to multi-millions. "Compound wisely, ride trends."
# =====================================================================

def pentoshi_htf_structure(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY when weekly market structure is bullish with EMA support confluence."""
    signals: list[dict] = []

    # Pentoshi's HTF structure works for any crypto with enough daily history for 200d EMA
    for symbol in ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                   "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "DOGE-USD",
                   "TAO-USD", "XLM-USD", "ARB11841-USD", "KAS-USD",
                   "ETC-USD", "FIL-USD", "ZEC-USD", "BAT-USD", "QNT-USD"]:
        if symbol not in data:
            continue
        try:
            df = data[symbol]
            if len(df) < 210:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            price = float(close.iloc[-1])

            # 200-day EMA (Pentoshi's key level)
            ema_200 = ema(close, 200)
            ema_200_val = float(ema_200.iloc[-1])

            # 21-week EMA ≈ 147-day EMA (21 * 7 = 147)
            ema_147 = ema(close, 147)
            ema_147_val = float(ema_147.iloc[-1])

            # Both EMAs must be below price (bullish structure)
            if price < ema_200_val or price < ema_147_val:
                continue

            # Check weekly higher lows (use 5-day windows as weekly proxy)
            # Look at last 4 "weekly" swing lows
            weekly_lows = []
            for w in range(4):
                start_idx = -(w + 1) * 5
                end_idx = -w * 5 if w > 0 else None
                if end_idx is None:
                    window = low.iloc[start_idx:]
                else:
                    window = low.iloc[start_idx:end_idx]
                if len(window) > 0:
                    weekly_lows.append(float(window.min()))

            # Need at least 3 weekly lows to check structure
            if len(weekly_lows) < 3:
                continue

            # Check for higher lows (bullish structure)
            # weekly_lows[0] = most recent, [1] = 1 week ago, etc.
            higher_lows = all(
                weekly_lows[i] >= weekly_lows[i + 1] * 0.995  # 0.5% tolerance
                for i in range(len(weekly_lows) - 1)
            )

            if not higher_lows:
                continue

            # Check for pullback to EMA support (price near 21w or 200d EMA)
            dist_to_ema147 = (price - ema_147_val) / ema_147_val
            dist_to_ema200 = (price - ema_200_val) / ema_200_val
            near_support = dist_to_ema147 < 0.04 or dist_to_ema200 < 0.04

            if not near_support:
                continue  # Too far from EMA support -- wait for pullback

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 75:
                continue

            entry, tp, sl = _atr_tp_sl(close, high, low, 4.0, 2.0)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr < 1.3:
                continue

            # Confidence: closer to EMA support = higher conviction
            min_dist = min(dist_to_ema147, dist_to_ema200)
            conf = min(0.82, 0.60 + (0.04 - min_dist) * 5.0)

            signals.append({
                "strategy": "pentoshi_htf_structure",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Pentoshi HTF: weekly higher lows intact, "
                    f"pullback to EMA support ({min_dist*100:.1f}% from EMA). "
                    f"21w EMA {_smart_round(ema_147_val)}, "
                    f"200d EMA {_smart_round(ema_200_val)}"
                ),
                "timeframe": "1w",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "ema_21w": _smart_round(ema_147_val),
                    "ema_200d": _smart_round(ema_200_val),
                    "dist_to_support_pct": round(min_dist * 100, 2),
                    "weekly_lows": [round(x, 2) for x in weekly_lows],
                    "source": "Pentoshi -- HTF Market Structure + EMA Compounding",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 43: Funding Rate Arbitrage Signal (Market-Neutral Carry)
# =====================================================================
# Long spot + Short perps when funding is highly positive.
# Collect funding payments every 8 hours (delta-neutral).
# Documented returns: up to 115.9% over 6 months, avg 19.26%/yr.
# Signal: Funding > 0.03% (annualized ~33%) with declining trend =
# entry opportunity. Uses Binance Futures API (FREE).
# =====================================================================

_BINANCE_FUNDING_URLS = [
    "https://fapi.binance.com/fapi/v1/fundingRate",
    "https://fapi1.binance.com/fapi/v1/fundingRate",
    "https://fapi2.binance.com/fapi/v1/fundingRate",
]
_BINANCE_FUNDING_URL = _BINANCE_FUNDING_URLS[0]


def funding_rate_arbitrage(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Signal funding rate arbitrage opportunities (long spot + short perps)."""
    signals: list[dict] = []

    # Only for liquid coins with Binance perpetual futures (arb requires deep liquidity)
    arb_symbols = {
        "BTC-USD": "BTCUSDT",
        "ETH-USD": "ETHUSDT",
        "SOL-USD": "SOLUSDT",
        "BNB-USD": "BNBUSDT",
        "XRP-USD": "XRPUSDT",
        "DOGE-USD": "DOGEUSDT",
        "ADA-USD": "ADAUSDT",
        "AVAX-USD": "AVAXUSDT",
        "LINK-USD": "LINKUSDT",
        "DOT-USD": "DOTUSDT",
    }

    for symbol, binance_sym in arb_symbols.items():
        if symbol not in data:
            continue
        try:
            # Fetch recent funding rates from Binance
            fr_data = None
            for _furl in _BINANCE_FUNDING_URLS:
                fr_data = _fetch_json(f"{_furl}?symbol={binance_sym}&limit=10", timeout=8)
                if fr_data is not None:
                    break

            if not fr_data or len(fr_data) < 3:
                continue

            # Get current and recent funding rates
            current_fr = float(fr_data[-1]["fundingRate"])
            recent_frs = [float(x["fundingRate"]) for x in fr_data[-5:]]
            avg_fr = sum(recent_frs) / len(recent_frs)

            # Annualized return from funding (3 payments/day * 365)
            annual_pct = avg_fr * 3 * 365 * 100

            # Signal: funding consistently positive and high enough to be worth it
            # Minimum threshold: ~0.02% per 8h = ~22% annualized
            if avg_fr < 0.0002:  # 0.02%
                continue

            # All recent must be positive
            if any(fr < 0 for fr in recent_frs):
                continue

            df = data[symbol]
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            price = float(close.iloc[-1])
            rsi_val = float(rsi(close, 14).iloc[-1])

            # For arb, TP/SL is based on funding income, not price movement
            # But we still set them for the signal format
            atr_val = float(atr(high, low, close, 14).iloc[-1])
            # TP: conservative (arb is market-neutral, target funding income)
            tp = price + 0.5 * atr_val   # small price appreciation bonus
            sl = price - 2.0 * atr_val   # wider stop (position is hedged)

            rr = abs(tp - price) / max(abs(price - sl), 0.01)

            # Confidence: higher funding = more profitable arb
            if annual_pct > 50:
                conf = 0.85
            elif annual_pct > 30:
                conf = 0.75
            else:
                conf = 0.65

            signals.append({
                "strategy": "funding_rate_arbitrage",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Funding arb: {binance_sym} avg FR {avg_fr*100:.4f}%/8h "
                    f"(~{annual_pct:.0f}% annualized). "
                    f"Long spot + short perps = delta-neutral carry"
                ),
                "timeframe": "8h",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "current_funding_rate": round(current_fr, 6),
                    "avg_funding_rate_5": round(avg_fr, 6),
                    "annualized_pct": round(annual_pct, 1),
                    "binance_symbol": binance_sym,
                    "strategy_type": "market_neutral_carry",
                    "source": "Funding Rate Arbitrage -- documented 19-115% annual",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 44: Difficulty Ribbon (Miner Stress → Recovery BUY)
# =====================================================================
# The Difficulty Ribbon plots 8 simple MAs of Bitcoin mining difficulty.
# When difficulty drops, weak miners capitulate (ribbon compresses).
# When difficulty recovers (ribbon expands after compression), surviving
# miners signal network health → historically strong BUY.
# Data: blockchain.info/charts/difficulty (FREE, no key).
# Reference: Willy Woo & David Puell (2019) -- Difficulty Ribbon.
# =====================================================================

_DIFFICULTY_URL = "https://blockchain.info/charts/difficulty?timespan=1year&format=json"


def _fetch_difficulty_data() -> Optional[pd.Series]:
    """Fetch Bitcoin mining difficulty from blockchain.info (1 year).

    Returns a pandas Series indexed by datetime, or None on failure.
    """
    try:
        req = urllib.request.Request(
            _DIFFICULTY_URL,
            headers={"User-Agent": "AlphaEngine/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
        if not raw or "values" not in raw:
            return None
        values = raw["values"]
        if len(values) < 200:
            return None
        dates = [datetime.fromtimestamp(v["x"], tz=timezone.utc) for v in values]
        diff_values = [float(v["y"]) for v in values]
        return pd.Series(diff_values, index=dates)
    except Exception:
        return None


def difficulty_ribbon_signal(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY BTC when difficulty ribbon expands after compression (miner recovery)."""
    signals: list[dict] = []

    # BTC-ONLY: Mining difficulty is a Bitcoin PoW metric.
    if "BTC-USD" not in data:
        return signals

    try:
        diff_series = _fetch_difficulty_data()
        if diff_series is None:
            return signals

        # Compute 8 difficulty MAs (the ribbon)
        ma_periods = [9, 14, 25, 40, 60, 90, 128, 200]
        ma_dict = {}
        for p in ma_periods:
            ma_val = diff_series.rolling(p, min_periods=p).mean()
            ma_dict[p] = ma_val

        # Check we have valid values for all MAs at the end
        current_mas = []
        for p in ma_periods:
            val = ma_dict[p].iloc[-1]
            if pd.isna(val):
                return signals
            current_mas.append(float(val))

        # Ribbon width = std dev of normalized MAs (relative to mean)
        mean_ma = np.mean(current_mas)
        if mean_ma <= 0:
            return signals
        normalized = [m / mean_ma for m in current_mas]
        current_std = float(np.std(normalized))

        # Check historical ribbon width for context (last 30 data points)
        lookback = min(30, len(diff_series) - 200)
        if lookback < 10:
            return signals

        historical_stds = []
        for i in range(lookback, 0, -1):
            mas_at_i = []
            for p in ma_periods:
                v = ma_dict[p].iloc[-(i + 1)]
                if pd.isna(v):
                    break
                mas_at_i.append(float(v))
            if len(mas_at_i) == len(ma_periods):
                m = np.mean(mas_at_i)
                if m > 0:
                    norm = [x / m for x in mas_at_i]
                    historical_stds.append(float(np.std(norm)))

        if len(historical_stds) < 10:
            return signals

        avg_std = np.mean(historical_stds)
        compression_threshold = avg_std * 0.6  # compressed = below 60% of average width

        # Was recently compressed (any of last 5-15 data points)?
        was_compressed = False
        for i in range(5, min(16, len(historical_stds))):
            if historical_stds[-i] < compression_threshold:
                was_compressed = True
                break

        # Current ribbon is expanding (above threshold)
        is_expanding = current_std > compression_threshold

        if not (was_compressed and is_expanding):
            return signals

        # Use BTC price data for entry/TP/SL
        df = data["BTC-USD"]
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        rsi_val = float(rsi(close, 14).iloc[-1])
        entry, tp, sl = _atr_tp_sl(close, high, low, 3.0, 2.0)  # high conviction, wide stops

        rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
        if rr < 1.0:
            return signals

        # Confidence: stronger expansion = higher conviction
        expansion_ratio = current_std / max(compression_threshold, 0.0001)
        conf = min(0.80, 0.55 + expansion_ratio * 0.08)

        signals.append({
            "strategy": "difficulty_ribbon_signal",
            "symbol": "BTC-USD",
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Difficulty ribbon expanding after compression -- "
                f"miner recovery signal. Ribbon std {current_std:.4f} "
                f"(threshold {compression_threshold:.4f}), RSI {rsi_val:.0f}"
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "ribbon_std": round(current_std, 6),
                "compression_threshold": round(compression_threshold, 6),
                "expansion_ratio": round(expansion_ratio, 2),
                "was_compressed": True,
                "source": "Willy Woo & David Puell (2019) -- Difficulty Ribbon",
            },
            "timestamp": _now_iso(),
        })
    except Exception:
        pass

    return signals


# =====================================================================
# STRATEGY 45: Active Address Momentum (Network Growth Acceleration)
# =====================================================================
# Tracks unique active Bitcoin addresses as a proxy for network adoption.
# When 30d MA of active addresses crosses above 90d MA = adoption
# accelerating → price tends to follow (Metcalfe's Law correlation).
# LONG only -- declining addresses = no signal (avoid shorting on-chain).
# Data: blockchain.info/charts/n-unique-addresses (FREE, no key).
# Reference: Metcalfe's Law applied to Bitcoin (Clearblocks, 2020)
# =====================================================================

_ACTIVE_ADDR_URL = "https://blockchain.info/charts/n-unique-addresses?timespan=180days&format=json"


def _fetch_active_addresses() -> Optional[pd.Series]:
    """Fetch unique active Bitcoin addresses from blockchain.info (180 days).

    Returns a pandas Series indexed by datetime, or None on failure.
    """
    try:
        req = urllib.request.Request(
            _ACTIVE_ADDR_URL,
            headers={"User-Agent": "AlphaEngine/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
        if not raw or "values" not in raw:
            return None
        values = raw["values"]
        if len(values) < 95:  # need at least 90d + buffer
            return None
        dates = [datetime.fromtimestamp(v["x"], tz=timezone.utc) for v in values]
        addr_values = [float(v["y"]) for v in values]
        return pd.Series(addr_values, index=dates)
    except Exception:
        return None


def active_address_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY BTC when 30d active address MA crosses above 90d MA (network growth)."""
    signals: list[dict] = []

    # BTC-ONLY: Active address data from blockchain.info is Bitcoin-specific.
    if "BTC-USD" not in data:
        return signals

    try:
        addr_series = _fetch_active_addresses()
        if addr_series is None:
            return signals

        # Compute 30d and 90d MAs
        ma_30 = addr_series.rolling(30, min_periods=25).mean()
        ma_90 = addr_series.rolling(90, min_periods=80).mean()

        if ma_30.isna().iloc[-1] or ma_90.isna().iloc[-1]:
            return signals

        current_30 = float(ma_30.iloc[-1])
        current_90 = float(ma_90.iloc[-1])

        # LONG only: 30d must be above 90d
        if current_30 <= current_90:
            return signals

        # Check for recent crossover in last 7 data points
        crossed_up_recently = False
        for lookback in range(1, min(8, len(ma_30) - 1)):
            prev_30 = float(ma_30.iloc[-(lookback + 1)])
            prev_90 = float(ma_90.iloc[-(lookback + 1)])
            if prev_30 <= prev_90 and current_30 > current_90:
                crossed_up_recently = True
                break

        # Also allow: 30d just above 90d (gap < 5%) = early acceleration
        gap_pct = (current_30 - current_90) / current_90 * 100
        early_acceleration = (current_30 > current_90 and gap_pct < 5.0)

        if not crossed_up_recently and not early_acceleration:
            return signals

        # Use BTC price data for entry/TP/SL
        df = data["BTC-USD"]
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        rsi_val = float(rsi(close, 14).iloc[-1])
        entry, tp, sl = _atr_tp_sl(close, high, low, 2.5, 1.5)

        rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
        if rr < 1.0:
            return signals

        # Confidence: stronger crossover gap = higher conviction
        conf = min(0.78, 0.52 + gap_pct * 0.04)

        signals.append({
            "strategy": "active_address_momentum",
            "symbol": "BTC-USD",
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Active address 30d MA ({current_30:,.0f}) crossed above "
                f"90d MA ({current_90:,.0f}) -- network growth accelerating. "
                f"Gap {gap_pct:.1f}%, RSI {rsi_val:.0f}"
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {
                "addr_ma_30": round(current_30, 0),
                "addr_ma_90": round(current_90, 0),
                "gap_pct": round(gap_pct, 2),
                "crossed_recently": crossed_up_recently,
                "source": "Metcalfe's Law -- Active Address Momentum (Clearblocks, 2020)",
            },
            "timestamp": _now_iso(),
        })
    except Exception:
        pass

    return signals


# =========================================================================
# Registry -- all on-chain strategies
# =========================================================================

ONCHAIN_STRATEGIES = {
    "mvrv_sma_proxy":           mvrv_sma_proxy,
    "nupl_zone_signal":         nupl_zone_signal,
    "hash_ribbon_buy":          hash_ribbon_buy,
    "stablecoin_buying_power":  stablecoin_buying_power,
    "nvt_overvaluation":        nvt_overvaluation,
    "fear_greed_extreme_dca":   fear_greed_extreme_dca,
    "sopr_dip_buy_proxy":       sopr_dip_buy_proxy,
    "onchain_composite_score":  onchain_composite_score,
    "hayes_liquidity_index":    hayes_liquidity_index,
    "pentoshi_htf_structure":   pentoshi_htf_structure,
    "funding_rate_arbitrage":   funding_rate_arbitrage,
    "difficulty_ribbon_signal": difficulty_ribbon_signal,
    "active_address_momentum":  active_address_momentum,
}
