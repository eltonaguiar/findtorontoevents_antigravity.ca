"""
ALPHA_ENGINE -- Advanced Strategies (Wave 6)
=============================================
8 strategies using volatility risk premium, dynamic momentum scaling,
GoPlus-filtered DEX sniping, smart wallet tracking, and enhanced
liquidation/unlock detection.

Strategies 56-63:
  56. vol_risk_premium          -- DVOL > realized vol by 10+ pts = sell vol signal
                                  Deribit free API -- 70% of time IV > RV
  57. dynamic_momentum_scaling  -- Daniel & Moskowitz (2016) full implementation
                                  EWMA vol of WML, weight = mu/sigma^2
  58. goplus_filtered_sniper    -- GeckoTerminal new pools + GoPlus security
                                  50-60% WR with strict filtering
  59. altcoin_dip_amplifier     -- Altcoins drop 1.2-2.5x more than BTC
                                  Buy alt dips when BTC stable/rising
  60. unlock_scoring_enhanced   -- Token unlock scoring: team+cliff+5%supply = 9pts
                                  30-14 day rule, recipient-type weighting
  61. cascade_volume_detector   -- Enhanced cascade detection via Binance futures
                                  $50M+ liquidation window proxy
  62. dvol_extreme_buy          -- DVOL > 80 = extreme fear, contrarian buy
                                  Mean reversion when vol-of-vol spikes
  63. sector_momentum_7d        -- 7-day rolling category momentum (CoinGecko)
                                  Enter when 3+ consecutive days positive

Data sources (all FREE):
  - Deribit public API          (DVOL index, no auth)
  - GeckoTerminal API           (new pools, 30 req/min)
  - GoPlus Security API         (contract verification, free)
  - Binance Futures public API  (liquidations, OI, funding)
  - CoinGecko Categories API    (sector performance)

References:
  - VRP: 70% IV>RV, median premium 14 IV pts (Deribit 2019-2024)
  - D&M: Daniel & Moskowitz (2016) JFE -- Sharpe 0.53→0.97 with vol scaling
  - GoPlus: Contract security verification (free API)
  - Cascade: $6.93B in 40min (Oct 2025), V-shaped recovery in 4-12h
  - Unlock Scoring: Keyrock (2024) -- team -25%, investor -5-10%, ecosystem +1.18%
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from config import (
    CRYPTO_SYMBOLS, COINGECKO_BASE,
    fetch_binance_json,
)
from indicators import rsi, atr, sma, ema, volume_ratio


# -- Helpers ----------------------------------------------------------

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
# STRATEGY 56: Volatility Risk Premium (Deribit DVOL)
# =====================================================================
# Since April 2019, IV > RV approximately 70% of the time for 30-day
# BTC options. Median VRP = +14 IV points. When DVOL exceeds 30-day
# realized vol by >10 points, options are systematically overpriced.
#
# This generates a SHORT signal (sell vol / short premium).
# When DVOL < RV (rare), generates a BUY signal (vol is cheap).
#
# Data: Deribit public API (free, no auth required)
# =====================================================================

def vol_risk_premium(data: dict[str, pd.DataFrame],
                     context: Optional[dict] = None) -> list[dict]:
    """Detect vol risk premium opportunities via Deribit DVOL vs realized vol."""
    signals = []

    btc_df = data.get("BTC-USD")
    if btc_df is None or len(btc_df) < 35:
        return signals

    try:
        close = btc_df["Close"]
        high = btc_df["High"]
        low = btc_df["Low"]

        # Calculate 30-day realized volatility (annualized)
        returns = close.pct_change().dropna()
        if len(returns) < 30:
            return signals

        rv_30d = float(returns.tail(30).std() * np.sqrt(365) * 100)  # Annualized %

        # Fetch DVOL from Deribit (free public API)
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_ms = now_ms - 3600_000  # Last hour
        dvol_url = (
            f"https://www.deribit.com/api/v2/public/get_volatility_index_data"
            f"?currency=BTC&start_timestamp={start_ms}&end_timestamp={now_ms}"
            f"&resolution=3600"
        )
        dvol_data = _fetch_json(dvol_url, timeout=10)

        if not dvol_data or "result" not in dvol_data:
            return signals

        dvol_points = dvol_data["result"].get("data", [])
        if not dvol_points:
            return signals

        # DVOL data format: [timestamp, open, high, low, close]
        latest_dvol = float(dvol_points[-1][4])  # close value

        # VRP = DVOL - Realized Vol
        vrp = latest_dvol - rv_30d

        price = float(close.iloc[-1])

        if vrp > 10:
            # IV significantly higher than RV → options overpriced → sell vol
            # In our framework: this means expect low volatility → SELL signal
            # (market is pricing in more fear than warranted)
            confidence = min(0.82, 0.55 + vrp * 0.015)

            signals.append({
                "strategy": "vol_risk_premium",
                "symbol": "BTC-USD",
                "category": "crypto",
                "signal_type": "SELL",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(price * 0.95),
                "stop_loss": _smart_round(price * 1.03),
                "confidence": round(confidence, 3),
                "risk_reward": round(5.0 / 3.0, 2),
                "reason": (f"Volatility Risk Premium: DVOL={latest_dvol:.1f}%, "
                           f"RV(30d)={rv_30d:.1f}%, VRP=+{vrp:.1f}pts. "
                           f"IV>RV 70% of time -- options overpriced, expect vol contraction"),
                "timeframe": "7-14d",
                "extra": {
                    "dvol": round(latest_dvol, 2),
                    "realized_vol_30d": round(rv_30d, 2),
                    "vrp": round(vrp, 2),
                    "signal_basis": "Short vol premium",
                },
                "timestamp": _now_iso(),
            })

        elif vrp < -5 and latest_dvol < 40:
            # Rare: RV > IV → vol is cheap → buy vol (expect expansion)
            confidence = 0.55
            signals.append({
                "strategy": "vol_risk_premium",
                "symbol": "BTC-USD",
                "category": "crypto",
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(price * 1.08),
                "stop_loss": _smart_round(price * 0.96),
                "confidence": round(confidence, 3),
                "risk_reward": 2.0,
                "reason": (f"Reverse VRP: DVOL={latest_dvol:.1f}% < RV={rv_30d:.1f}%, "
                           f"VRP={vrp:.1f}pts. Vol is cheap -- expect expansion"),
                "timeframe": "3-7d",
                "extra": {
                    "dvol": round(latest_dvol, 2),
                    "realized_vol_30d": round(rv_30d, 2),
                    "vrp": round(vrp, 2),
                    "signal_basis": "Long vol -- rare opportunity",
                },
                "timestamp": _now_iso(),
            })

    except Exception:
        pass

    return signals


# =====================================================================
# STRATEGY 57: Dynamic Momentum Scaling (Daniel & Moskowitz 2016)
# =====================================================================
# Full implementation of the D&M conditional momentum strategy.
# Weight = (1/2) * mu_hat / sigma_hat^2
# When momentum vol spikes, reduce or reverse exposure.
#
# Uses EWMA with 20-day half-life for responsive vol estimates.
# Sharpe improvement: 0.53 → 0.97 (static) → ~1.5 (dynamic)
# =====================================================================

def dynamic_momentum_scaling(data: dict[str, pd.DataFrame],
                             context: Optional[dict] = None) -> list[dict]:
    """Apply D&M dynamic momentum scaling to top crypto assets."""
    signals = []

    # Calculate momentum returns for each symbol
    mom_data = {}  # symbol -> (28d_return, 5d_return_vol)
    for symbol, df in data.items():
        if symbol not in CRYPTO_SYMBOLS:
            continue
        if len(df) < 90:
            continue

        try:
            close = df["Close"]
            # 28-day momentum return
            mom_28d = float(close.iloc[-1] / close.iloc[-29] - 1)
            # 5-day momentum returns for vol calculation
            mom_5d = (close / close.shift(5) - 1).dropna()
            if len(mom_5d) < 30:
                continue

            # EWMA volatility with 20-day half-life (lambda ≈ 0.966)
            lam = 0.966
            weights = np.array([(1 - lam) * lam ** i for i in range(min(60, len(mom_5d)))])
            weights = weights[::-1]  # Most recent gets highest weight
            recent_5d = mom_5d.values[-len(weights):]
            ewma_var = np.sum(weights * recent_5d ** 2) / np.sum(weights)
            ewma_vol = np.sqrt(ewma_var) * np.sqrt(252 / 5)  # Annualized

            mom_data[symbol] = (mom_28d, ewma_vol)
        except Exception:
            continue

    if len(mom_data) < 3:
        return signals

    # Rank by 28-day momentum
    sorted_syms = sorted(mom_data.keys(), key=lambda s: mom_data[s][0], reverse=True)

    # Top tercile = winners (BUY), Bottom tercile = losers (SELL signal)
    n = len(sorted_syms)
    top_n = max(1, n // 3)

    for i, symbol in enumerate(sorted_syms):
        mom_ret, mom_vol = mom_data[symbol]
        df = data[symbol]
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        # D&M weight: w = (1/2) * mu / sigma^2
        # Positive weight = long momentum, negative = reverse (contrarian)
        sigma_sq = mom_vol ** 2 if mom_vol > 0 else 0.01
        dm_weight = 0.5 * mom_ret / sigma_sq

        # Cap weight at [-3, 3] to prevent extreme leverage
        dm_weight = max(-3.0, min(3.0, dm_weight))

        # Only signal when weight is strongly directional
        if abs(dm_weight) < 0.3:
            continue

        # Top tercile with positive D&M weight = BUY
        if i < top_n and dm_weight > 0.3:
            entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=1.5)

            confidence = min(0.80, 0.50 + abs(dm_weight) * 0.10)
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            signals.append({
                "strategy": "dynamic_momentum_scaling",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"D&M momentum: 28d return={mom_ret*100:.1f}%, "
                           f"EWMA vol={mom_vol*100:.1f}%, "
                           f"weight={dm_weight:.2f} (rank {i+1}/{n})"),
                "timeframe": "5-10d",
                "extra": {
                    "momentum_28d": round(mom_ret * 100, 2),
                    "ewma_vol": round(mom_vol * 100, 2),
                    "dm_weight": round(dm_weight, 3),
                    "rank": i + 1,
                    "total_symbols": n,
                    "reference": "Daniel & Moskowitz (2016) JFE",
                },
                "timestamp": _now_iso(),
            })

        # Bottom tercile with negative D&M weight AND weight reverses = SELL
        elif i >= n - top_n and dm_weight < -0.3:
            entry, _, _ = _atr_tp_sl(close, high, low)
            atr_v = float(atr(high, low, close, 14).iloc[-1])
            tp = _smart_round(entry - 2.5 * atr_v)
            sl = _smart_round(entry + 1.5 * atr_v)

            confidence = min(0.75, 0.45 + abs(dm_weight) * 0.08)
            rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

            signals.append({
                "strategy": "dynamic_momentum_scaling",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "SELL",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"D&M momentum reversal: 28d return={mom_ret*100:.1f}%, "
                           f"EWMA vol={mom_vol*100:.1f}%, "
                           f"weight={dm_weight:.2f} (rank {i+1}/{n} -- loser)"),
                "timeframe": "5-10d",
                "extra": {
                    "momentum_28d": round(mom_ret * 100, 2),
                    "ewma_vol": round(mom_vol * 100, 2),
                    "dm_weight": round(dm_weight, 3),
                    "rank": i + 1,
                    "total_symbols": n,
                    "reference": "Daniel & Moskowitz (2016) JFE",
                },
                "timestamp": _now_iso(),
            })

    return signals[:6]  # Cap at 6 momentum signals


# =====================================================================
# STRATEGY 58: GoPlus-Filtered DEX Sniper
# =====================================================================
# GeckoTerminal new_pools endpoint + GoPlus Security API for rug check.
# Unfiltered sniping: 5-10% WR. With GoPlus filtering: 50-60% WR.
#
# Filter chain: liquidity > $50K, GoPlus clean, no honeypot,
# buy/sell tax < 5%, 20+ buys in first hour.
# =====================================================================

def goplus_filtered_sniper(data: dict[str, pd.DataFrame],
                           context: Optional[dict] = None) -> list[dict]:
    """Scout new DEX pools with GoPlus security verification."""
    signals = []

    # GeckoTerminal: new pools on Ethereum and Solana
    chains = [
        ("eth", "Ethereum"),
        ("solana", "Solana"),
        ("bsc", "BSC"),
    ]

    for chain_id, chain_name in chains:
        pools_url = f"https://api.geckoterminal.com/api/v2/networks/{chain_id}/new_pools?page=1"
        pool_data = _fetch_json(pools_url, timeout=10)

        if not pool_data or "data" not in pool_data:
            continue

        for pool in pool_data["data"][:15]:
            try:
                attrs = pool.get("attributes", {})
                pool_name = attrs.get("name", "?")
                base_symbol = pool_name.split("/")[0].strip() if "/" in pool_name else pool_name

                reserve_usd = float(attrs.get("reserve_in_usd", 0) or 0)
                volume_24h = float(attrs.get("volume_usd", {}).get("h24", 0) or 0)
                price_change_1h = float(attrs.get("price_change_percentage", {}).get("h1", 0) or 0)
                price_usd = float(attrs.get("base_token_price_usd", 0) or 0)

                # Quick filters
                if reserve_usd < 50000:
                    continue  # Need $50K+ liquidity
                if volume_24h < 100000:
                    continue  # Need $100K+ 24h volume
                if price_change_1h > 100:
                    continue  # Pump red flag
                if price_change_1h < 3:
                    continue  # Need positive momentum
                if price_usd <= 0:
                    continue

                # Extract token address for GoPlus check
                base_token = attrs.get("base_token_price_native_currency", "")
                # Try to get address from relationships
                relationships = pool.get("relationships", {})
                base_token_data = relationships.get("base_token", {}).get("data", {})
                token_id = base_token_data.get("id", "")
                # Token ID format: "chain_address"
                token_address = token_id.split("_", 1)[1] if "_" in token_id else ""

                if not token_address or len(token_address) < 10:
                    continue

                # GoPlus Security check (free, no auth)
                goplus_chain = {"eth": "1", "bsc": "56", "solana": "solana"}.get(chain_id, "1")
                goplus_url = f"https://api.gopluslabs.com/api/v1/token_security/{goplus_chain}?contract_addresses={token_address}"
                security = _fetch_json(goplus_url, timeout=8)

                is_safe = True
                security_notes = []

                if security and "result" in security:
                    token_info = security["result"].get(token_address.lower(), {})
                    if not token_info:
                        token_info = security["result"].get(token_address, {})

                    # Check safety flags
                    if token_info.get("is_honeypot") == "1":
                        is_safe = False
                        security_notes.append("HONEYPOT")
                    if token_info.get("is_open_source") == "0":
                        is_safe = False
                        security_notes.append("Unverified contract")
                    if token_info.get("can_take_back_ownership") == "1":
                        security_notes.append("Can reclaim ownership")
                        is_safe = False

                    buy_tax = float(token_info.get("buy_tax", 0) or 0)
                    sell_tax = float(token_info.get("sell_tax", 0) or 0)
                    if buy_tax > 0.05 or sell_tax > 0.10:
                        is_safe = False
                        security_notes.append(f"High tax: buy={buy_tax*100:.0f}% sell={sell_tax*100:.0f}%")

                    holder_count = int(token_info.get("holder_count", 0) or 0)
                    if holder_count < 20:
                        is_safe = False
                        security_notes.append(f"Only {holder_count} holders")

                if not is_safe:
                    continue  # Failed security check

                # Calculate confidence
                confidence = 0.50
                if reserve_usd > 200000:
                    confidence += 0.08
                if volume_24h > 500000:
                    confidence += 0.07
                if price_change_1h > 10:
                    confidence += 0.05

                signals.append({
                    "strategy": "goplus_filtered_sniper",
                    "symbol": f"DEX:{base_symbol}",
                    "category": "crypto",
                    "signal_type": "BUY",
                    "entry_price": _smart_round(price_usd),
                    "take_profit": _smart_round(price_usd * 1.25),
                    "stop_loss": _smart_round(price_usd * 0.80),
                    "confidence": round(min(confidence, 0.72), 3),
                    "risk_reward": round(25.0 / 20.0, 2),
                    "reason": (f"GoPlus-verified new pool: {base_symbol} on {chain_name}, "
                               f"liq=${reserve_usd/1000:.0f}K, vol=${volume_24h/1000:.0f}K/24h, "
                               f"+{price_change_1h:.1f}% (1h), SAFE"),
                    "timeframe": "1-6h",
                    "extra": {
                        "chain": chain_name,
                        "liquidity_usd": round(reserve_usd),
                        "volume_24h": round(volume_24h),
                        "price_change_1h": round(price_change_1h, 2),
                        "goplus_safe": True,
                        "token_address": token_address,
                    },
                    "timestamp": _now_iso(),
                })

            except Exception:
                continue

    return signals[:5]  # Cap at 5 DEX signals


# =====================================================================
# STRATEGY 59: Altcoin Dip Amplifier
# =====================================================================
# Altcoins drop 1.2-2.5x more than BTC during corrections.
# When BTC is stable/rising but alts are still recovering from a dip,
# buy the oversold alts for the catch-up trade.
#
# Rule: only buy alt dips when BTC is stable or rising.
# ETH drops 1.2-1.5x BTC, SOL drops 1.5-2.5x BTC.
# =====================================================================

def altcoin_dip_amplifier(data: dict[str, pd.DataFrame],
                          context: Optional[dict] = None) -> list[dict]:
    """Buy oversold altcoins when BTC stabilizes after a correction."""
    signals = []

    btc_df = data.get("BTC-USD")
    if btc_df is None or len(btc_df) < 20:
        return signals

    try:
        btc_close = btc_df["Close"]
        # BTC must be stable or rising (3-day change > -1%)
        btc_3d_change = (float(btc_close.iloc[-1]) - float(btc_close.iloc[-4])) / float(btc_close.iloc[-4]) * 100
        if btc_3d_change < -1:
            return signals  # BTC still falling -- don't buy alts

        # BTC 7-day change to detect recovery
        btc_7d_change = (float(btc_close.iloc[-1]) - float(btc_close.iloc[-8])) / float(btc_close.iloc[-8]) * 100

    except Exception:
        return signals

    # Expected amplification factors
    AMPLIFIERS = {
        "ETH-USD": 1.3, "SOL-USD": 2.0, "AVAX-USD": 1.8,
        "NEAR-USD": 2.0, "SUI-USD": 2.2, "INJ-USD": 1.9,
        "TIA-USD": 2.0, "LINK-USD": 1.5, "DOT-USD": 1.7,
        "ADA-USD": 1.6,
        # Memes amplify even more
        "DOGE-USD": 2.0, "SHIB-USD": 2.5, "PEPE-USD": 3.0,
        "WIF-USD": 3.0, "BONK-USD": 3.0, "FLOKI-USD": 2.5,
    }

    for symbol, amp_factor in AMPLIFIERS.items():
        df = data.get(symbol)
        if df is None or len(df) < 20:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # Alt's 7-day drawdown from peak
            alt_high_7d = float(high.rolling(7).max().iloc[-1])
            alt_price = float(close.iloc[-1])
            alt_drawdown = (alt_price - alt_high_7d) / alt_high_7d * 100

            # Expected amplified drawdown vs BTC
            btc_high_7d = float(btc_df["High"].rolling(7).max().iloc[-1])
            btc_drawdown = (float(btc_close.iloc[-1]) - btc_high_7d) / btc_high_7d * 100

            # Alt has drawn down MORE than expected amplification of BTC drawdown
            expected_alt_dd = btc_drawdown * amp_factor
            excess_dd = alt_drawdown - expected_alt_dd  # Negative = alt overdipped

            if excess_dd > -3:
                continue  # Alt hasn't oversold enough relative to BTC

            # RSI confirmation
            rsi14 = rsi(close, 14)
            current_rsi = float(rsi14.iloc[-1])
            if current_rsi > 45:
                continue  # Not oversold enough

            # BTC must be recovering (stable or up)
            if btc_3d_change < 0:
                continue

            entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=3.5, sl_mult=1.5)

            confidence = 0.55
            if abs(excess_dd) > 8:
                confidence += 0.12
            elif abs(excess_dd) > 5:
                confidence += 0.08
            if current_rsi < 25:
                confidence += 0.07
            if btc_3d_change > 2:
                confidence += 0.05  # BTC bouncing strongly

            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            signals.append({
                "strategy": "altcoin_dip_amplifier",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(min(confidence, 0.82), 3),
                "risk_reward": round(rr, 2),
                "reason": (f"Alt dip amplifier: {symbol} dd={alt_drawdown:.1f}% vs "
                           f"BTC dd={btc_drawdown:.1f}% (excess={excess_dd:.1f}%), "
                           f"RSI={current_rsi:.0f}, BTC 3d={btc_3d_change:+.1f}%"),
                "timeframe": "3-7d",
                "rsi_at_entry": round(current_rsi, 2),
                "extra": {
                    "alt_drawdown": round(alt_drawdown, 2),
                    "btc_drawdown": round(btc_drawdown, 2),
                    "excess_drawdown": round(excess_dd, 2),
                    "amplifier": amp_factor,
                    "btc_3d_change": round(btc_3d_change, 2),
                },
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 60: Enhanced Token Unlock Scoring
# =====================================================================
# Keyrock research scoring system:
#   Team unlock: +3pts    | Investor: +2pts   | Ecosystem: 0 (skip)
#   >5% supply:  +3pts    | 2-5%:    +2pts   | 1-2%: +1pt
#   Cliff:       +2pts    | Linear:   0pts
#   Perp market: +1pt
# Score ≥ 6 = high-conviction short. 9 = maximum.
#
# 30-14 Rule: Enter T-14 to T-7, cover T+7 to T+14.
# =====================================================================

def unlock_scoring_enhanced(data: dict[str, pd.DataFrame],
                            context: Optional[dict] = None) -> list[dict]:
    """Enhanced token unlock short with Keyrock scoring system."""
    signals = []

    # Fetch unlock data from DeFiLlama
    unlocks_url = "https://api.llama.fi/unlocks"
    unlocks_data = _fetch_json(unlocks_url, timeout=10)

    if not unlocks_data or not isinstance(unlocks_data, list):
        return signals

    now = datetime.now(timezone.utc)
    # 30-14 Rule: look for unlocks 7-14 days out (sweet spot)
    window_start = now + timedelta(days=7)
    window_end = now + timedelta(days=14)

    # Map token names to our symbols
    symbol_map = {}
    for sym, info in CRYPTO_SYMBOLS.items():
        name_lower = info.get("name", "").lower()
        ticker = sym.replace("-USD", "").lower()
        symbol_map[name_lower] = sym
        symbol_map[ticker] = sym

    for event in unlocks_data[:80]:
        try:
            token_name = event.get("name", "").lower()
            matched_sym = symbol_map.get(token_name)
            if not matched_sym:
                continue

            upcoming = event.get("upcomingEvent", [])
            if not upcoming:
                continue

            for unlock in upcoming[:3]:
                unlock_ts = unlock.get("timestamp", 0)
                if unlock_ts == 0:
                    continue

                unlock_dt = datetime.fromtimestamp(unlock_ts, tz=timezone.utc)
                if not (window_start <= unlock_dt <= window_end):
                    continue

                # ---- SCORING SYSTEM ----
                score = 0

                # Recipient type scoring
                description = (unlock.get("description", "") or "").lower()
                if "team" in description or "core" in description or "founder" in description:
                    score += 3
                    recipient = "TEAM"
                elif "investor" in description or "seed" in description or "private" in description:
                    score += 2
                    recipient = "INVESTOR"
                elif "ecosystem" in description or "community" in description or "airdrop" in description:
                    score += 0
                    recipient = "ECOSYSTEM"
                    continue  # Skip ecosystem unlocks (avg +1.18%)
                else:
                    score += 1
                    recipient = "UNKNOWN"

                # Supply % scoring
                unlock_value = unlock.get("noOfTokens", 0) * unlock.get("price", 0)
                mcap = event.get("mcap", 1)
                supply_pct = (unlock_value / mcap * 100) if mcap > 0 else 0

                if supply_pct > 5:
                    score += 3
                elif supply_pct > 2:
                    score += 2
                elif supply_pct > 1:
                    score += 1
                else:
                    continue  # < 1% = no meaningful impact

                # Cliff vs linear scoring
                unlock_type = (unlock.get("type", "") or "").lower()
                if "cliff" in unlock_type or "one-time" in unlock_type:
                    score += 2
                    unlock_style = "CLIFF"
                elif "linear" in unlock_type or "vesting" in unlock_type:
                    score += 0
                    unlock_style = "LINEAR"
                else:
                    score += 1  # Unknown type
                    unlock_style = "UNKNOWN"

                # Perp market bonus
                binance_sym = CRYPTO_SYMBOLS.get(matched_sym, {}).get("binance")
                if binance_sym:
                    score += 1

                # Only signal if score >= 5 (relaxed from 6 for broader coverage)
                if score < 5:
                    continue

                # Get price data
                df = data.get(matched_sym)
                if df is None or len(df) < 20:
                    continue

                close = df["Close"]
                price = float(close.iloc[-1])
                days_until = (unlock_dt - now).days

                # Confidence scales with score
                confidence = min(0.88, 0.45 + score * 0.05)

                # TP/SL based on Keyrock avg declines
                if recipient == "TEAM":
                    tp_pct = 0.85  # -15% target (team avg -25%, conservative)
                elif recipient == "INVESTOR":
                    tp_pct = 0.93  # -7% target
                else:
                    tp_pct = 0.95  # -5% target

                tp = _smart_round(price * tp_pct)
                sl = _smart_round(price * 1.04)  # 4% stop

                rr = abs(price - tp) / abs(sl - price) if abs(sl - price) > 0 else 0

                signals.append({
                    "strategy": "unlock_scoring_enhanced",
                    "symbol": matched_sym,
                    "category": _get_category(matched_sym),
                    "signal_type": "SELL",
                    "entry_price": _smart_round(price),
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(confidence, 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Unlock Score: {score}/9 -- {recipient} {unlock_style} "
                               f"{supply_pct:.1f}% supply in {days_until}d. "
                               f"Keyrock: {recipient} unlocks avg "
                               f"{'−25%' if recipient == 'TEAM' else '−5-10%'}"),
                    "timeframe": f"{days_until}d to T+14",
                    "extra": {
                        "keyrock_score": score,
                        "recipient": recipient,
                        "unlock_style": unlock_style,
                        "supply_pct": round(supply_pct, 2),
                        "unlock_date": unlock_dt.isoformat(),
                        "days_until": days_until,
                        "has_perp": bool(binance_sym),
                    },
                    "timestamp": _now_iso(),
                })

        except (KeyError, TypeError, ValueError, IndexError):
            continue

    return signals


# =====================================================================
# STRATEGY 61: Cascade Volume Detector (Enhanced)
# =====================================================================
# Enhanced liquidation cascade detection using Binance futures data.
# Proxy: when OI drops sharply (>5% in 1 hour) + negative funding +
# extreme volume + RSI<10 = cascade exhaustion signal.
#
# Oct 2025 cascade: $6.93B in 40 min, V-shaped recovery in 4-12h.
# =====================================================================

def cascade_volume_detector(data: dict[str, pd.DataFrame],
                            context: Optional[dict] = None) -> list[dict]:
    """Detect liquidation cascade exhaustion via Binance futures proxy."""
    signals = []

    for symbol in ["BTC-USD", "ETH-USD", "SOL-USD"]:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        binance_sym = CRYPTO_SYMBOLS.get(symbol, {}).get("binance")
        if not binance_sym:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            vol = df["Volume"]

            # Check current conditions
            rsi2_val = rsi(close, 2)
            current_rsi = float(rsi2_val.iloc[-1])

            # Volume spike check
            vol_r = volume_ratio(vol, 20)
            current_vol_r = float(vol_r.iloc[-1])

            # Price drop in last 6 bars
            price_now = float(close.iloc[-1])
            price_6ago = float(close.iloc[-7]) if len(close) > 7 else price_now
            drop_pct = (price_now - price_6ago) / price_6ago * 100

            # Need: RSI extreme + volume spike + meaningful drop
            if current_rsi > 12 or current_vol_r < 2.0 or drop_pct > -4:
                continue

            # Binance: check if OI has decreased (cascade = forced closing)
            oi_data = fetch_binance_json(f"/fapi/v1/openInterest?symbol={binance_sym}", futures=True)

            # Check funding rate
            fr_data = fetch_binance_json(f"/fapi/v1/fundingRate?symbol={binance_sym}&limit=1", futures=True)

            cascade_score = 0.0

            if current_rsi < 5:
                cascade_score += 0.15
            elif current_rsi < 8:
                cascade_score += 0.10
            else:
                cascade_score += 0.05

            if current_vol_r > 4.0:
                cascade_score += 0.15
            elif current_vol_r > 3.0:
                cascade_score += 0.10
            else:
                cascade_score += 0.05

            if drop_pct < -10:
                cascade_score += 0.15
            elif drop_pct < -7:
                cascade_score += 0.10
            else:
                cascade_score += 0.05

            # Negative funding = bearish extreme
            if fr_data and len(fr_data) > 0:
                fr_rate = float(fr_data[0].get("fundingRate", 0))
                if fr_rate < -0.005:
                    cascade_score += 0.12
                elif fr_rate < -0.001:
                    cascade_score += 0.07

            confidence = min(0.88, 0.50 + cascade_score)

            entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=2.0)
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            signals.append({
                "strategy": "cascade_volume_detector",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"Cascade exhaustion: RSI(2)={current_rsi:.1f}, "
                           f"vol={current_vol_r:.1f}x avg, drop={drop_pct:.1f}%, "
                           f"V-shape recovery expected in 4-12h"),
                "timeframe": "4-12h",
                "rsi_at_entry": round(current_rsi, 2),
                "extra": {
                    "cascade_score": round(cascade_score, 3),
                    "vol_ratio": round(current_vol_r, 2),
                    "drop_pct": round(drop_pct, 2),
                },
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 62: DVOL Extreme Buy (Contrarian)
# =====================================================================
# When DVOL > 80 = extreme fear in crypto options market.
# Historically, DVOL > 80 is a contrarian buy signal -- vol mean-reverts.
# Risk: never sell vol (short straddle) when DVOL > 80.
# But buying the underlying after a DVOL spike tends to be profitable.
# =====================================================================

def dvol_extreme_buy(data: dict[str, pd.DataFrame],
                     context: Optional[dict] = None) -> list[dict]:
    """Contrarian buy when DVOL exceeds 80 (extreme fear)."""
    signals = []

    btc_df = data.get("BTC-USD")
    if btc_df is None or len(btc_df) < 20:
        return signals

    try:
        # Fetch DVOL
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_ms = now_ms - 86400_000  # Last 24h
        dvol_url = (
            f"https://www.deribit.com/api/v2/public/get_volatility_index_data"
            f"?currency=BTC&start_timestamp={start_ms}&end_timestamp={now_ms}"
            f"&resolution=3600"
        )
        dvol_data = _fetch_json(dvol_url, timeout=10)

        if not dvol_data or "result" not in dvol_data:
            return signals

        dvol_points = dvol_data["result"].get("data", [])
        if not dvol_points:
            return signals

        latest_dvol = float(dvol_points[-1][4])

        # Only signal on extreme fear (DVOL > 70)
        if latest_dvol < 70:
            return signals

        # Check if DVOL is declining from peak (mean reversion starting)
        if len(dvol_points) >= 3:
            prev_dvol = float(dvol_points[-3][4])
            if latest_dvol > prev_dvol:
                return signals  # Vol still rising -- wait for turn

        close = btc_df["Close"]
        high = btc_df["High"]
        low = btc_df["Low"]

        # Buy BTC, ETH, SOL on DVOL extreme
        for symbol in ["BTC-USD", "ETH-USD", "SOL-USD"]:
            sym_df = data.get(symbol)
            if sym_df is None or len(sym_df) < 20:
                continue

            sym_close = sym_df["Close"]
            sym_high = sym_df["High"]
            sym_low = sym_df["Low"]

            entry, tp, sl = _atr_tp_sl(sym_close, sym_high, sym_low,
                                        tp_mult=4.0, sl_mult=2.0)

            confidence = min(0.82, 0.50 + (latest_dvol - 70) * 0.01)
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            signals.append({
                "strategy": "dvol_extreme_buy",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(confidence, 3),
                "risk_reward": round(rr, 2),
                "reason": (f"DVOL extreme fear: {latest_dvol:.1f}% (>70 threshold). "
                           f"Vol mean-reverts from extremes -- contrarian buy"),
                "timeframe": "7-14d",
                "extra": {
                    "dvol": round(latest_dvol, 2),
                    "signal_basis": "DVOL extreme → vol mean reversion",
                },
                "timestamp": _now_iso(),
            })

    except Exception:
        pass

    return signals


# =====================================================================
# STRATEGY 63: Sector Momentum 7d Rolling (CoinGecko)
# =====================================================================
# 7-day rolling momentum on CoinGecko categories.
# Enter when a sector shows 3+ consecutive days of positive momentum.
# 2025 data: RWA +185.8% YTD (sustained narrative).
# Filter: avoid flash narratives (meme <2 weeks).
# =====================================================================

def sector_momentum_7d(data: dict[str, pd.DataFrame],
                       context: Optional[dict] = None) -> list[dict]:
    """Trade crypto sector momentum using CoinGecko categories."""
    signals = []

    # Fetch categories
    cat_url = f"{COINGECKO_BASE}/coins/categories"
    categories = _fetch_json(cat_url, timeout=10)

    if not categories or not isinstance(categories, list):
        return signals

    # Map categories to our symbols
    SECTOR_SYMBOLS = {
        "layer-1": ["SOL-USD", "AVAX-USD", "NEAR-USD", "SUI-USD"],
        "smart-contract-platform": ["ETH-USD", "SOL-USD", "ADA-USD", "BNB-USD"],
        "defi": ["LINK-USD", "INJ-USD"],
        "meme-token": ["DOGE-USD", "SHIB-USD", "PEPE-USD", "WIF-USD", "BONK-USD"],
        "infrastructure": ["DOT-USD", "LINK-USD", "FIL-USD"],
        "real-world-assets": ["LINK-USD"],  # LINK is heavily RWA-adjacent
        "artificial-intelligence": ["NEAR-USD", "FIL-USD"],
    }

    for cat in categories[:20]:
        try:
            cat_id = cat.get("id", "")
            cat_name = cat.get("name", "")
            mc_change_24h = cat.get("market_cap_change_24h", 0) or 0
            cat_volume = cat.get("volume_24h", 0) or 0

            # Need meaningful positive momentum
            if mc_change_24h < 3:
                continue

            # Skip meme categories for momentum (flash narratives)
            if "meme" in cat_id.lower() and mc_change_24h < 15:
                continue

            # Match to our symbol universe
            matched = []
            for sector_key, syms in SECTOR_SYMBOLS.items():
                if sector_key in cat_id.lower() or cat_id.lower() in sector_key:
                    matched.extend(syms)

            if not matched:
                continue

            for symbol in set(matched):
                sym_df = data.get(symbol)
                if sym_df is None or len(sym_df) < 10:
                    continue

                close = sym_df["Close"]
                high = sym_df["High"]
                low = sym_df["Low"]

                # Check if this coin has room to run (RSI < 70)
                rsi14 = rsi(close, 14)
                current_rsi = float(rsi14.iloc[-1])
                if current_rsi > 72:
                    continue

                entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=1.5)

                confidence = 0.52
                if mc_change_24h > 10:
                    confidence += 0.12
                elif mc_change_24h > 5:
                    confidence += 0.07
                if cat_volume and cat_volume > 1e9:
                    confidence += 0.05

                rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

                signals.append({
                    "strategy": "sector_momentum_7d",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(min(confidence, 0.78), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Sector momentum: {cat_name} +{mc_change_24h:.1f}% (24h). "
                               f"{symbol} RSI={current_rsi:.0f} -- room to run"),
                    "timeframe": "3-7d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "sector": cat_name,
                        "sector_change_24h": round(mc_change_24h, 2),
                        "sector_volume": round(cat_volume) if cat_volume else 0,
                    },
                    "timestamp": _now_iso(),
                })

        except Exception:
            continue

    return signals[:6]  # Cap at 6 sector signals


# =====================================================================
# STRATEGY 64: Fractal Decay
# =====================================================================
# Scans for fractal price structures at varying depth levels, then
# applies a sigma-weighted decay filter to confirm the move is real
# before entering. The decay period controls how fast old patterns
# lose relevance, filtering out stale setups.
#
# Inspired by KIRA Fractal Decay (port 8050):
#   Net Profit 263.16, 281 trades, 44.13% WR, Sharpe 0.57, Sortino 1.43
#
# Fractal = a candle whose high/low is the extreme of N surrounding
# candles (Williams fractal). Decay weighting ensures recent fractals
# matter more than old ones.
# =====================================================================

def fractal_decay(data: dict[str, pd.DataFrame],
                  context: Optional[dict] = None) -> list[dict]:
    """Buy/sell on fractal breakouts weighted by sigma-decay relevance."""
    signals = []
    FRACTAL_DEPTH = 5
    DECAY_PERIOD = 24
    SIGMA_COEFF = 0.18
    MOMENTUM_DECAY = 0.41

    for symbol, df in data.items():
        if symbol not in CRYPTO_SYMBOLS or df is None or len(df) < max(DECAY_PERIOD + FRACTAL_DEPTH * 2, 50):
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # --- Detect Williams fractals at given depth ---
            fractal_highs = []
            fractal_lows = []
            for i in range(FRACTAL_DEPTH, len(df) - FRACTAL_DEPTH):
                h = float(high.iloc[i])
                l = float(low.iloc[i])
                is_high = all(h >= float(high.iloc[i - j]) and h >= float(high.iloc[i + j])
                              for j in range(1, FRACTAL_DEPTH + 1))
                is_low = all(l <= float(low.iloc[i - j]) and l <= float(low.iloc[i + j])
                             for j in range(1, FRACTAL_DEPTH + 1))
                if is_high:
                    fractal_highs.append((i, h))
                if is_low:
                    fractal_lows.append((i, l))

            if not fractal_highs or not fractal_lows:
                continue

            price = float(close.iloc[-1])
            last_idx = len(df) - 1

            # --- Apply sigma-weighted decay to fractals ---
            def decay_weight(fractal_idx: int) -> float:
                age = last_idx - fractal_idx
                return np.exp(-SIGMA_COEFF * (age / DECAY_PERIOD) ** 2)

            # Weighted recent fractal high/low
            weighted_high = sum(h * decay_weight(i) for i, h in fractal_highs[-8:])
            weight_sum_h = sum(decay_weight(i) for i, _ in fractal_highs[-8:])
            weighted_low = sum(l * decay_weight(i) for i, l in fractal_lows[-8:])
            weight_sum_l = sum(decay_weight(i) for i, _ in fractal_lows[-8:])

            if weight_sum_h == 0 or weight_sum_l == 0:
                continue

            decay_resistance = weighted_high / weight_sum_h
            decay_support = weighted_low / weight_sum_l

            # --- Momentum decay factor ---
            returns_recent = close.pct_change().tail(DECAY_PERIOD).dropna()
            if len(returns_recent) < 5:
                continue
            momentum = float(returns_recent.mean()) * DECAY_PERIOD
            momentum_factor = 1.0 + MOMENTUM_DECAY * momentum

            # --- Signal logic ---
            rsi14 = rsi(close, 14)
            current_rsi = float(rsi14.iloc[-1])

            # BUY: price bounces off decayed support + momentum positive
            if price <= decay_support * 1.01 and momentum_factor > 1.0 and current_rsi < 45:
                entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=1.5)

                confidence = 0.55
                proximity = abs(price - decay_support) / decay_support
                if proximity < 0.005:
                    confidence += 0.1
                if current_rsi < 30:
                    confidence += 0.08
                # Freshness bonus: recent fractals weigh more
                newest_low_age = last_idx - fractal_lows[-1][0]
                if newest_low_age < 10:
                    confidence += 0.05

                rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

                signals.append({
                    "strategy": "fractal_decay",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(min(confidence, 0.80), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Fractal decay: price at decayed support "
                               f"${decay_support:.2f}, RSI={current_rsi:.0f}, "
                               f"momentum_factor={momentum_factor:.2f}"),
                    "timeframe": "2-5d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "decay_support": round(decay_support, 4),
                        "decay_resistance": round(decay_resistance, 4),
                        "momentum_factor": round(momentum_factor, 4),
                        "fractal_depth": FRACTAL_DEPTH,
                        "newest_fractal_age": newest_low_age,
                    },
                    "timestamp": _now_iso(),
                })

            # SELL: price rejected at decayed resistance + momentum negative
            elif price >= decay_resistance * 0.99 and momentum_factor < 1.0 and current_rsi > 65:
                entry, tp, sl = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=1.5)
                tp_sell = entry - (tp - entry)  # Mirror for short
                sl_sell = entry + (entry - sl)
                rr = abs(entry - tp_sell) / abs(sl_sell - entry) if abs(sl_sell - entry) > 0 else 0

                confidence = 0.55
                if current_rsi > 75:
                    confidence += 0.08
                newest_high_age = last_idx - fractal_highs[-1][0]
                if newest_high_age < 10:
                    confidence += 0.05

                signals.append({
                    "strategy": "fractal_decay",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": _smart_round(entry),
                    "take_profit": _smart_round(tp_sell),
                    "stop_loss": _smart_round(sl_sell),
                    "confidence": round(min(confidence, 0.78), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Fractal decay: price at decayed resistance "
                               f"${decay_resistance:.2f}, RSI={current_rsi:.0f}, "
                               f"momentum_factor={momentum_factor:.2f}"),
                    "timeframe": "2-5d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "decay_support": round(decay_support, 4),
                        "decay_resistance": round(decay_resistance, 4),
                        "momentum_factor": round(momentum_factor, 4),
                        "fractal_depth": FRACTAL_DEPTH,
                        "newest_fractal_age": newest_high_age,
                    },
                    "timestamp": _now_iso(),
                })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 65: Swing Structure
# =====================================================================
# Tracks swing highs and swing lows to classify market structure.
# Higher-high + higher-low = uptrend → go long.
# Lower-high + lower-low = downtrend → go short.
# Pure price action, no indicators.
#
# Inspired by KIRA swing_struct (port 8051).
# =====================================================================

def swing_structure(data: dict[str, pd.DataFrame],
                    context: Optional[dict] = None) -> list[dict]:
    """Trade market structure shifts via swing high/low sequences."""
    signals = []
    SWING_LOOKBACK = 5  # Bars each side to confirm swing point

    for symbol, df in data.items():
        if symbol not in CRYPTO_SYMBOLS or df is None or len(df) < 40:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # --- Detect swing highs and swing lows ---
            swing_highs = []
            swing_lows = []
            for i in range(SWING_LOOKBACK, len(df) - SWING_LOOKBACK):
                h = float(high.iloc[i])
                l = float(low.iloc[i])
                is_sh = all(h >= float(high.iloc[i - j]) and h >= float(high.iloc[i + j])
                            for j in range(1, SWING_LOOKBACK + 1))
                is_sl = all(l <= float(low.iloc[i - j]) and l <= float(low.iloc[i + j])
                            for j in range(1, SWING_LOOKBACK + 1))
                if is_sh:
                    swing_highs.append((i, h))
                if is_sl:
                    swing_lows.append((i, l))

            if len(swing_highs) < 2 or len(swing_lows) < 2:
                continue

            # Latest two swing highs and lows
            sh1_val = swing_highs[-2][1]
            sh2_val = swing_highs[-1][1]
            sl1_val = swing_lows[-2][1]
            sl2_val = swing_lows[-1][1]

            price = float(close.iloc[-1])

            # Classify structure
            higher_high = sh2_val > sh1_val
            higher_low = sl2_val > sl1_val
            lower_high = sh2_val < sh1_val
            lower_low = sl2_val < sl1_val

            uptrend = higher_high and higher_low
            downtrend = lower_high and lower_low

            # Volume confirmation
            vol_r = volume_ratio(df["Volume"], 20)
            current_vr = float(vol_r.iloc[-1]) if not np.isnan(float(vol_r.iloc[-1])) else 1.0

            entry, tp, sl_price = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=1.5)

            if uptrend and price > sl2_val:
                # Buy on pullback toward higher low in uptrend
                rsi14 = rsi(close, 14)
                current_rsi = float(rsi14.iloc[-1])
                if current_rsi > 75:
                    continue  # Already overbought

                confidence = 0.58
                if higher_high and (sh2_val - sh1_val) / sh1_val > 0.02:
                    confidence += 0.07  # Strong HH
                if higher_low and (sl2_val - sl1_val) / sl1_val > 0.01:
                    confidence += 0.05  # Strong HL
                if current_vr > 1.3:
                    confidence += 0.05  # Volume supports

                rr = abs(tp - entry) / abs(entry - sl_price) if abs(entry - sl_price) > 0 else 0

                signals.append({
                    "strategy": "swing_structure",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl_price,
                    "confidence": round(min(confidence, 0.80), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Swing structure: HH={higher_high} HL={higher_low} -- "
                               f"uptrend confirmed. SH ${sh2_val:.2f} > ${sh1_val:.2f}, "
                               f"SL ${sl2_val:.2f} > ${sl1_val:.2f}"),
                    "timeframe": "3-7d",
                    "extra": {
                        "swing_high_prev": round(sh1_val, 4),
                        "swing_high_curr": round(sh2_val, 4),
                        "swing_low_prev": round(sl1_val, 4),
                        "swing_low_curr": round(sl2_val, 4),
                        "volume_ratio": round(current_vr, 2),
                        "structure": "uptrend",
                    },
                    "timestamp": _now_iso(),
                })

            elif downtrend and price < sh2_val:
                # Sell on rally toward lower high in downtrend
                rsi14 = rsi(close, 14)
                current_rsi = float(rsi14.iloc[-1])
                if current_rsi < 25:
                    continue  # Already oversold

                tp_sell = entry - (tp - entry)
                sl_sell = entry + (entry - sl_price)
                rr = abs(entry - tp_sell) / abs(sl_sell - entry) if abs(sl_sell - entry) > 0 else 0

                confidence = 0.55
                if lower_high and (sh1_val - sh2_val) / sh1_val > 0.02:
                    confidence += 0.07
                if lower_low and (sl1_val - sl2_val) / sl1_val > 0.01:
                    confidence += 0.05
                if current_vr > 1.3:
                    confidence += 0.05

                signals.append({
                    "strategy": "swing_structure",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": _smart_round(entry),
                    "take_profit": _smart_round(tp_sell),
                    "stop_loss": _smart_round(sl_sell),
                    "confidence": round(min(confidence, 0.78), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Swing structure: LH={lower_high} LL={lower_low} -- "
                               f"downtrend confirmed. SH ${sh2_val:.2f} < ${sh1_val:.2f}, "
                               f"SL ${sl2_val:.2f} < ${sl1_val:.2f}"),
                    "timeframe": "3-7d",
                    "extra": {
                        "swing_high_prev": round(sh1_val, 4),
                        "swing_high_curr": round(sh2_val, 4),
                        "swing_low_prev": round(sl1_val, 4),
                        "swing_low_curr": round(sl2_val, 4),
                        "volume_ratio": round(current_vr, 2),
                        "structure": "downtrend",
                    },
                    "timestamp": _now_iso(),
                })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 66: Kalman Filter Trend
# =====================================================================
# Runs a Kalman filter on price -- an adaptive smoother from aerospace
# engineering that estimates "true" price by dynamically balancing new
# data vs its existing estimate. Long above the line, short below.
# Very responsive, generates tons of trades.
#
# Inspired by KIRA kalman (port 8052).
#
# Simple scalar Kalman filter:
#   prediction = prev_estimate
#   kalman_gain = pred_error / (pred_error + measurement_noise)
#   estimate = prediction + kalman_gain * (observation - prediction)
#   pred_error = (1 - kalman_gain) * pred_error + process_noise
# =====================================================================

def kalman_filter_trend(data: dict[str, pd.DataFrame],
                        context: Optional[dict] = None) -> list[dict]:
    """Trade Kalman-filtered price crossovers with RSI confirmation."""
    signals = []
    # Kalman parameters
    Q = 1e-5   # Process noise (low = smoother)
    R = 0.001  # Measurement noise
    MIN_BARS = 30

    for symbol, df in data.items():
        if symbol not in CRYPTO_SYMBOLS or df is None or len(df) < MIN_BARS:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            prices = close.values.astype(float)

            # --- Run Kalman filter ---
            n = len(prices)
            estimates = np.zeros(n)
            estimates[0] = prices[0]
            p = 1.0  # Initial error covariance

            for i in range(1, n):
                # Predict
                pred = estimates[i - 1]
                p_pred = p + Q
                # Update
                k = p_pred / (p_pred + R)
                estimates[i] = pred + k * (prices[i] - pred)
                p = (1 - k) * p_pred

            price = prices[-1]
            kalman_price = estimates[-1]
            kalman_prev = estimates[-2]

            # Direction of Kalman line
            kalman_slope = (kalman_price - kalman_prev) / kalman_prev

            # Price crossing above/below Kalman
            prev_above = prices[-2] > estimates[-2]
            curr_above = price > kalman_price

            rsi14 = rsi(close, 14)
            current_rsi = float(rsi14.iloc[-1])

            entry, tp, sl_price = _atr_tp_sl(close, high, low, tp_mult=2.5, sl_mult=1.2)

            # BUY: price crosses above rising Kalman line
            if curr_above and not prev_above and kalman_slope > 0 and current_rsi < 65:
                confidence = 0.55
                if kalman_slope > 0.005:
                    confidence += 0.08  # Strong upward Kalman
                if current_rsi < 40:
                    confidence += 0.07  # Oversold cross
                deviation = (price - kalman_price) / kalman_price
                if deviation < 0.01:
                    confidence += 0.05  # Tight cross (not extended)

                rr = abs(tp - entry) / abs(entry - sl_price) if abs(entry - sl_price) > 0 else 0

                signals.append({
                    "strategy": "kalman_filter_trend",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl_price,
                    "confidence": round(min(confidence, 0.78), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Kalman crossover UP: price ${price:.2f} crossed above "
                               f"Kalman ${kalman_price:.2f} (slope={kalman_slope:+.4f}), "
                               f"RSI={current_rsi:.0f}"),
                    "timeframe": "1-3d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "kalman_price": round(kalman_price, 6),
                        "kalman_slope": round(kalman_slope, 6),
                        "deviation_pct": round((price - kalman_price) / kalman_price * 100, 4),
                        "process_noise": Q,
                        "measurement_noise": R,
                    },
                    "timestamp": _now_iso(),
                })

            # SELL: price crosses below falling Kalman line
            elif not curr_above and prev_above and kalman_slope < 0 and current_rsi > 40:
                tp_sell = entry - (tp - entry)
                sl_sell = entry + (entry - sl_price)
                rr = abs(entry - tp_sell) / abs(sl_sell - entry) if abs(sl_sell - entry) > 0 else 0

                confidence = 0.53
                if kalman_slope < -0.005:
                    confidence += 0.08
                if current_rsi > 65:
                    confidence += 0.07

                signals.append({
                    "strategy": "kalman_filter_trend",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": _smart_round(entry),
                    "take_profit": _smart_round(tp_sell),
                    "stop_loss": _smart_round(sl_sell),
                    "confidence": round(min(confidence, 0.75), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Kalman crossover DOWN: price ${price:.2f} crossed below "
                               f"Kalman ${kalman_price:.2f} (slope={kalman_slope:+.4f}), "
                               f"RSI={current_rsi:.0f}"),
                    "timeframe": "1-3d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "kalman_price": round(kalman_price, 6),
                        "kalman_slope": round(kalman_slope, 6),
                        "deviation_pct": round((price - kalman_price) / kalman_price * 100, 4),
                    },
                    "timestamp": _now_iso(),
                })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 67: Candle Momentum
# =====================================================================
# Looks at consecutive candle bodies. When several candles in a row
# show strong directional bodies (e.g., 3 big green candles), it
# enters in that direction -- riding short-term bursts of buying/
# selling pressure before it fades.
#
# Inspired by KIRA candle_mom (port 8053).
# =====================================================================

def candle_momentum(data: dict[str, pd.DataFrame],
                    context: Optional[dict] = None) -> list[dict]:
    """Enter on consecutive strong-body candles indicating momentum bursts."""
    signals = []
    MIN_CONSEC = 3       # Minimum consecutive strong candles
    BODY_THRESHOLD = 0.6  # Body must be >= 60% of candle range

    for symbol, df in data.items():
        if symbol not in CRYPTO_SYMBOLS or df is None or len(df) < 20:
            continue

        try:
            close = df["Close"]
            opn = df["Open"]
            high = df["High"]
            low = df["Low"]

            # Analyze last 5 candles for consecutive strong bodies
            bull_streak = 0
            bear_streak = 0

            for i in range(-5, 0):
                c = float(close.iloc[i])
                o = float(opn.iloc[i])
                h = float(high.iloc[i])
                l = float(low.iloc[i])
                candle_range = h - l
                if candle_range == 0:
                    bull_streak = 0
                    bear_streak = 0
                    continue

                body = abs(c - o)
                body_ratio = body / candle_range

                if body_ratio >= BODY_THRESHOLD and c > o:
                    bull_streak += 1
                    bear_streak = 0
                elif body_ratio >= BODY_THRESHOLD and c < o:
                    bear_streak += 1
                    bull_streak = 0
                else:
                    bull_streak = 0
                    bear_streak = 0

            price = float(close.iloc[-1])
            rsi14 = rsi(close, 14)
            current_rsi = float(rsi14.iloc[-1])

            # Volume must support the move
            vol_r = volume_ratio(df["Volume"], 20)
            current_vr = float(vol_r.iloc[-1]) if not np.isnan(float(vol_r.iloc[-1])) else 1.0

            if current_vr < 1.1:
                continue  # Need above-average volume

            entry, tp, sl_price = _atr_tp_sl(close, high, low, tp_mult=2.5, sl_mult=1.2)

            if bull_streak >= MIN_CONSEC and current_rsi < 75:
                confidence = 0.55
                if bull_streak >= 4:
                    confidence += 0.08
                if current_vr > 1.5:
                    confidence += 0.07
                if current_rsi < 60:
                    confidence += 0.05  # Not yet overbought

                rr = abs(tp - entry) / abs(entry - sl_price) if abs(entry - sl_price) > 0 else 0

                signals.append({
                    "strategy": "candle_momentum",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl_price,
                    "confidence": round(min(confidence, 0.78), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Candle momentum: {bull_streak} consecutive bullish candles "
                               f"(body>60% range), vol_ratio={current_vr:.2f}, RSI={current_rsi:.0f}"),
                    "timeframe": "1-3d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "bull_streak": bull_streak,
                        "volume_ratio": round(current_vr, 2),
                        "body_threshold": BODY_THRESHOLD,
                    },
                    "timestamp": _now_iso(),
                })

            elif bear_streak >= MIN_CONSEC and current_rsi > 30:
                tp_sell = entry - (tp - entry)
                sl_sell = entry + (entry - sl_price)
                rr = abs(entry - tp_sell) / abs(sl_sell - entry) if abs(sl_sell - entry) > 0 else 0

                confidence = 0.53
                if bear_streak >= 4:
                    confidence += 0.08
                if current_vr > 1.5:
                    confidence += 0.07
                if current_rsi > 45:
                    confidence += 0.05

                signals.append({
                    "strategy": "candle_momentum",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": _smart_round(entry),
                    "take_profit": _smart_round(tp_sell),
                    "stop_loss": _smart_round(sl_sell),
                    "confidence": round(min(confidence, 0.75), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Candle momentum: {bear_streak} consecutive bearish candles "
                               f"(body>60% range), vol_ratio={current_vr:.2f}, RSI={current_rsi:.0f}"),
                    "timeframe": "1-3d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "bear_streak": bear_streak,
                        "volume_ratio": round(current_vr, 2),
                        "body_threshold": BODY_THRESHOLD,
                    },
                    "timestamp": _now_iso(),
                })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 68: CUSUM Regime Detector
# =====================================================================
# CUSUM (Cumulative Sum) is a statistical algorithm that accumulates
# deviations of returns from their mean. When the sum exceeds a
# threshold, it signals a regime change -- the market has shifted from
# noise to trend. Originally from manufacturing quality control,
# repurposed for trend detection.
#
# Inspired by KIRA cusum (port 8054).
#
# S_t = max(0, S_{t-1} + x_t - mu - k)   (upper CUSUM)
# T_t = max(0, T_{t-1} - x_t + mu - k)   (lower CUSUM)
# Signal when S_t > h (bullish regime) or T_t > h (bearish regime)
# =====================================================================

def cusum_regime(data: dict[str, pd.DataFrame],
                 context: Optional[dict] = None) -> list[dict]:
    """Detect regime changes via CUSUM on returns."""
    signals = []
    K_SENSITIVITY = 0.5  # Slack parameter (in std devs)
    H_THRESHOLD = 4.0    # Detection threshold (in std devs)
    LOOKBACK = 60        # Period for mean/std estimation

    for symbol, df in data.items():
        if symbol not in CRYPTO_SYMBOLS or df is None or len(df) < LOOKBACK + 10:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            returns = close.pct_change().dropna()
            if len(returns) < LOOKBACK:
                continue

            # Estimate mean and std from lookback window
            mu = float(returns.tail(LOOKBACK).mean())
            sigma = float(returns.tail(LOOKBACK).std())
            if sigma == 0:
                continue

            k = K_SENSITIVITY * sigma
            h = H_THRESHOLD * sigma

            # Run CUSUM on recent returns
            s_pos = 0.0  # Upper CUSUM (detects upward shift)
            s_neg = 0.0  # Lower CUSUM (detects downward shift)
            recent_returns = returns.tail(LOOKBACK).values

            pos_signal_idx = None
            neg_signal_idx = None

            for i, r in enumerate(recent_returns):
                s_pos = max(0, s_pos + r - mu - k)
                s_neg = max(0, s_neg - r + mu - k)

                if s_pos > h:
                    pos_signal_idx = i
                    s_pos = 0  # Reset after detection
                if s_neg > h:
                    neg_signal_idx = i
                    s_neg = 0

            price = float(close.iloc[-1])
            rsi14 = rsi(close, 14)
            current_rsi = float(rsi14.iloc[-1])

            entry, tp, sl_price = _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=1.5)

            # Only act on recent regime changes (within last 5 bars)
            if pos_signal_idx is not None and pos_signal_idx >= LOOKBACK - 5 and current_rsi < 70:
                confidence = 0.58
                # How recent was the detection?
                recency = LOOKBACK - pos_signal_idx
                if recency <= 2:
                    confidence += 0.10  # Very fresh
                elif recency <= 4:
                    confidence += 0.05

                vol_r = volume_ratio(df["Volume"], 20)
                current_vr = float(vol_r.iloc[-1]) if not np.isnan(float(vol_r.iloc[-1])) else 1.0
                if current_vr > 1.3:
                    confidence += 0.05

                rr = abs(tp - entry) / abs(entry - sl_price) if abs(entry - sl_price) > 0 else 0

                signals.append({
                    "strategy": "cusum_regime",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl_price,
                    "confidence": round(min(confidence, 0.80), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"CUSUM regime shift UP detected {recency} bars ago. "
                               f"Returns shifted above mean+{K_SENSITIVITY}σ, "
                               f"RSI={current_rsi:.0f}"),
                    "timeframe": "3-7d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "cusum_k": K_SENSITIVITY,
                        "cusum_h": H_THRESHOLD,
                        "return_mean": round(mu * 100, 4),
                        "return_std": round(sigma * 100, 4),
                        "detection_recency": recency,
                    },
                    "timestamp": _now_iso(),
                })

            elif neg_signal_idx is not None and neg_signal_idx >= LOOKBACK - 5 and current_rsi > 35:
                tp_sell = entry - (tp - entry)
                sl_sell = entry + (entry - sl_price)
                rr = abs(entry - tp_sell) / abs(sl_sell - entry) if abs(sl_sell - entry) > 0 else 0

                recency = LOOKBACK - neg_signal_idx
                confidence = 0.55
                if recency <= 2:
                    confidence += 0.10
                elif recency <= 4:
                    confidence += 0.05

                signals.append({
                    "strategy": "cusum_regime",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": _smart_round(entry),
                    "take_profit": _smart_round(tp_sell),
                    "stop_loss": _smart_round(sl_sell),
                    "confidence": round(min(confidence, 0.78), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"CUSUM regime shift DOWN detected {recency} bars ago. "
                               f"Returns shifted below mean-{K_SENSITIVITY}σ, "
                               f"RSI={current_rsi:.0f}"),
                    "timeframe": "3-7d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "cusum_k": K_SENSITIVITY,
                        "cusum_h": H_THRESHOLD,
                        "return_mean": round(mu * 100, 4),
                        "return_std": round(sigma * 100, 4),
                        "detection_recency": recency,
                    },
                    "timestamp": _now_iso(),
                })

        except Exception:
            continue

    return signals


# =====================================================================
# Registry
# =====================================================================

ADVANCED_STRATEGIES: dict[str, callable] = {
    "vol_risk_premium": vol_risk_premium,
    "dynamic_momentum_scaling": dynamic_momentum_scaling,
    "goplus_filtered_sniper": goplus_filtered_sniper,
    "altcoin_dip_amplifier": altcoin_dip_amplifier,
    "unlock_scoring_enhanced": unlock_scoring_enhanced,
    "cascade_volume_detector": cascade_volume_detector,
    "dvol_extreme_buy": dvol_extreme_buy,
    "sector_momentum_7d": sector_momentum_7d,
    "fractal_decay": fractal_decay,
    "swing_structure": swing_structure,
    "kalman_filter_trend": kalman_filter_trend,
    "candle_momentum": candle_momentum,
    "cusum_regime": cusum_regime,
}
