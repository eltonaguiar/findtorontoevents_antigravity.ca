"""
ALPHA_ENGINE -- Wave 4/5/6 Supplemental Strategies
====================================================
12 new signal providers using free APIs that fill critical data gaps.

WAVE 4 (activate dormant data):
  W4-1. coinlore_btc_dominance_rotation  -- BTC dominance regime → alt season timing
  W4-2. coinpaprika_mcap_ath_distance    -- Total market cap vs ATH → macro cycle position
  W4-3. blockchain_miner_revenue_diverge -- Miner revenue vs price divergence → 2-7d leading

WAVE 5 (new free APIs):
  W5-1. solana_tps_momentum              -- Solana TPS spikes → SOL ecosystem rally predictor
  W5-2. gemini_premium_tracker           -- Gemini/Binance price spread → institutional flow proxy
  W5-3. blockchain_fee_volatility        -- BTC fee volatility → price volatility predictor
  W5-4. blockchain_tx_volume_divergence  -- On-chain tx volume vs exchange vol divergence

WAVE 6 (cross-exchange + stablecoin):
  W6-1. funding_spread_arbitrage         -- Binance vs Bybit funding rate divergence
  W6-2. stablecoin_supply_momentum       -- DefiLlama stablecoin supply growth → liquidity signal
  W6-3. defi_tvl_momentum               -- DefiLlama chain TVL momentum → ecosystem rotation
  W6-4. multi_exchange_premium           -- Cross-exchange BTC price spread → flow direction
  W6-5. coinlore_altseason_breadth       -- Market breadth (% of top 100 green) → alt season

Data sources (ALL FREE, no key):
  - api.coinlore.net/api/               (global stats, top coins, no key)
  - api.coinpaprika.com/v1/             (global, tickers, OHLCV, no key)
  - api.blockchain.info/                (BTC on-chain charts, stats, no key)
  - api.mainnet-beta.solana.com         (Solana RPC, no key)
  - api.gemini.com/v1/                  (Gemini exchange, no key)
  - api.binance.com + api.bybit.com     (funding rates, tickers, no key)
  - stablecoins.llama.fi/               (DefiLlama stablecoins, no key)
  - api.llama.fi/                       (DefiLlama TVL, no key)

References:
  - BTC Dominance: Bouri et al. (2021) -- crypto herding & rotation
  - Miner Revenue: Cong & He (2019) -- mining economics & price
  - Exchange Premium: Makarov & Schoar (2020) -- cross-exchange price gaps
  - Stablecoin Flows: Lyons & Viswanath-Natraj (2023) -- stablecoin demand
  - Solana TPS: DeFi composability → price feedback (empirical)
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


# -- Helpers (shared with supplemental_data_strategies.py) -----------------

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
               direction: str = "BUY",
               tp_mult: float = 3.0, sl_mult: float = 2.25,
               atr_period: int = 14) -> tuple[float, float, float]:
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    if direction == "BUY":
        tp = price + tp_mult * current_atr
        sl = price - sl_mult * current_atr
    else:
        tp = price - tp_mult * current_atr
        sl = price + sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


def _fetch_json(url: str, timeout: int = 10, headers: Optional[dict] = None,
                method: str = "GET", body: Optional[bytes] = None) -> Optional[dict | list]:
    """Fetch JSON with timeout and optional custom headers."""
    try:
        hdrs = {"User-Agent": "ALPHA_ENGINE/3.0"}
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, headers=hdrs, method=method, data=body)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


# =========================================================================
# WAVE 4: MACRO REGIME STRATEGIES
# =========================================================================

# -- W4-1: BTC Dominance Rotation (Coinlore) -----------------------------

COINLORE_GLOBAL = "https://api.coinlore.net/api/global/"
COINLORE_TICKERS = "https://api.coinlore.net/api/tickers/"

# Solana ecosystem tokens that rally with SOL
_SOL_ECOSYSTEM = {"SOL-USD", "JUP-USD", "ORCA-USD", "RAY-USD", "PYTH-USD",
                  "BONK-USD", "WIF-USD", "JITO-USD"}

# Top altcoins that benefit from alt season rotation
_ALT_SEASON_TOKENS = {
    "ETH-USD", "SOL-USD", "BNB-USD", "ADA-USD", "AVAX-USD", "LINK-USD",
    "DOT-USD", "ATOM-USD", "UNI-USD", "NEAR-USD", "ARB-USD", "OP-USD",
    "SUI-USD", "APT-USD", "INJ-USD", "TIA-USD",
}


def coinlore_btc_dominance_rotation(data: dict[str, pd.DataFrame],
                                     context: Optional[dict] = None) -> list[dict]:
    """Trade alt season rotation based on BTC dominance shifts.

    When BTC dominance drops >2% in 7d → alt season (BUY alts with momentum).
    When BTC dominance rises >2% in 7d → flight to quality (BUY BTC on dips).
    Reference: Bouri et al. (2021) -- herding in crypto markets.
    """
    signals: list[dict] = []

    global_data = _fetch_json(COINLORE_GLOBAL, timeout=8)
    if not global_data or not isinstance(global_data, list) or len(global_data) == 0:
        return signals

    g = global_data[0]
    btc_dom = float(g.get("btc_d", 0))
    total_mcap = float(g.get("total_mcap", 0))
    total_vol = float(g.get("total_volume", 0))

    if btc_dom == 0:
        return signals

    # Also fetch top coins for 7d change context
    tickers = _fetch_json(f"{COINLORE_TICKERS}?start=0&limit=50", timeout=8)
    btc_7d_change = 0.0
    alt_avg_7d = 0.0
    if tickers and isinstance(tickers, dict):
        coins = tickers.get("data", [])
        for c in coins:
            if c.get("symbol") == "BTC":
                btc_7d_change = float(c.get("percent_change_7d", 0))
            elif c.get("symbol") in ("ETH", "SOL", "BNB", "ADA", "AVAX",
                                      "LINK", "DOT", "ATOM", "UNI"):
                alt_avg_7d += float(c.get("percent_change_7d", 0))
        alt_avg_7d /= max(1, 9)  # Avg of 9 alts

    # Alt rotation divergence
    alt_vs_btc = alt_avg_7d - btc_7d_change

    # Regime A: BTC dominance falling + alts outperforming → ALT SEASON
    if btc_dom < 48 and alt_vs_btc > 3:
        for symbol in _ALT_SEASON_TOKENS:
            if symbol not in data:
                continue
            try:
                df = data[symbol]
                if len(df) < 30:
                    continue
                close, high, low = df["Close"], df["High"], df["Low"]
                rsi_val = float(rsi(close, 14).iloc[-1])

                # Buy alts that are consolidating (not already overbought)
                if rsi_val > 70 or rsi_val < 25:
                    continue

                # Momentum confirmation: 7d return positive
                ret_7d = (float(close.iloc[-1]) - float(close.iloc[-7])) / float(close.iloc[-7])
                if ret_7d < 0:
                    continue

                entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 3.0, 2.0)
                rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
                if rr < 1.5:
                    continue

                conf = min(0.78, 0.50 + (48 - btc_dom) / 30 + alt_vs_btc / 40)
                signals.append({
                    "strategy": "coinlore_btc_dominance_rotation",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Alt season: BTC dom={btc_dom:.1f}% (low), "
                               f"alts outperform BTC by {alt_vs_btc:+.1f}% (7d)"),
                    "timeframe": "1d",
                    "extra": {
                        "btc_dominance": btc_dom,
                        "alt_vs_btc_7d": round(alt_vs_btc, 2),
                        "total_mcap_usd": total_mcap,
                        "source": "Coinlore global -- Bouri et al. (2021)",
                    },
                    "timestamp": _now_iso(),
                })
            except Exception:
                continue

    # Regime B: BTC dominance rising + BTC dip → BUY BTC (flight to quality)
    elif btc_dom > 55 and "BTC-USD" in data:
        try:
            df = data["BTC-USD"]
            if len(df) >= 30:
                close, high, low = df["Close"], df["High"], df["Low"]
                rsi_val = float(rsi(close, 14).iloc[-1])
                if rsi_val < 45:  # BTC dip in dominance-rising regime
                    entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 3.5, 2.0)
                    rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
                    if rr >= 1.5:
                        conf = min(0.80, 0.55 + (btc_dom - 55) / 30)
                        signals.append({
                            "strategy": "coinlore_btc_dominance_rotation",
                            "symbol": "BTC-USD",
                            "category": "crypto",
                            "signal_type": "BUY",
                            "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                            "confidence": round(conf, 2),
                            "risk_reward": round(rr, 2),
                            "reason": (f"Flight to quality: BTC dom={btc_dom:.1f}% (high), "
                                       f"RSI={rsi_val:.0f} dip in BTC-dominant regime"),
                            "timeframe": "1d",
                            "extra": {
                                "btc_dominance": btc_dom,
                                "total_mcap_usd": total_mcap,
                                "source": "Coinlore global -- BTC dominance regime",
                            },
                            "timestamp": _now_iso(),
                        })
        except Exception:
            pass

    return signals


# -- W4-2: Market Cap ATH Distance (Coinpaprika) -------------------------

COINPAPRIKA_GLOBAL = "https://api.coinpaprika.com/v1/global"


def coinpaprika_mcap_ath_distance(data: dict[str, pd.DataFrame],
                                   context: Optional[dict] = None) -> list[dict]:
    """Macro accumulation/distribution signal based on total crypto market cap vs ATH.

    >40% below ATH → macro accumulation zone → BUY dips with high confidence.
    <10% from ATH → topping risk → reduce exposure, tighten stops.
    Currently 47% below ATH ($2.54T vs $4.82T).
    """
    signals: list[dict] = []

    g = _fetch_json(COINPAPRIKA_GLOBAL, timeout=8)
    if not g:
        return signals

    current_mcap = g.get("market_cap_usd", 0)
    ath_mcap = g.get("market_cap_ath_value", 0)
    mcap_change_24h = g.get("market_cap_change_24h", 0)
    vol_change_24h = g.get("volume_24h_change_24h", 0)

    if not current_mcap or not ath_mcap:
        return signals

    distance_pct = ((current_mcap / ath_mcap) - 1) * 100  # Negative = below ATH

    # Deep accumulation zone: >40% below ATH
    if distance_pct < -40:
        # BUY large-cap crypto on RSI dips
        for symbol in ("BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"):
            if symbol not in data:
                continue
            try:
                df = data[symbol]
                if len(df) < 30:
                    continue
                close, high, low = df["Close"], df["High"], df["Low"]
                rsi_val = float(rsi(close, 14).iloc[-1])

                if rsi_val > 50:
                    continue  # Only buy dips in accumulation zone

                entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 3.5, 2.0)
                rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
                if rr < 1.5:
                    continue

                # Deeper below ATH = higher confidence
                depth_bonus = min(0.15, abs(distance_pct + 40) / 100)
                conf = min(0.82, 0.55 + depth_bonus + (50 - rsi_val) / 200)

                signals.append({
                    "strategy": "coinpaprika_mcap_ath_distance",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Macro accumulation: market {abs(distance_pct):.0f}% below ATH "
                               f"(${current_mcap/1e12:.2f}T vs ${ath_mcap/1e12:.2f}T ATH). "
                               f"RSI={rsi_val:.0f}"),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "mcap_usd": current_mcap,
                        "ath_mcap_usd": ath_mcap,
                        "distance_from_ath_pct": round(distance_pct, 2),
                        "mcap_change_24h_pct": round(mcap_change_24h, 2),
                        "vol_change_24h_pct": round(vol_change_24h, 2),
                        "source": "Coinpaprika global -- macro cycle position",
                    },
                    "timestamp": _now_iso(),
                })
            except Exception:
                continue

    # Topping zone: within 10% of ATH → SELL overbought
    elif distance_pct > -10:
        for symbol in ("BTC-USD", "ETH-USD", "SOL-USD"):
            if symbol not in data:
                continue
            try:
                df = data[symbol]
                if len(df) < 30:
                    continue
                close, high, low = df["Close"], df["High"], df["Low"]
                rsi_val = float(rsi(close, 14).iloc[-1])
                if rsi_val < 70:
                    continue
                entry, tp, sl = _atr_tp_sl(close, high, low, "SELL", 2.5, 1.5)
                rr = abs(entry - tp) / max(abs(sl - entry), 0.01)
                if rr < 1.5:
                    continue
                conf = min(0.72, 0.48 + (rsi_val - 70) / 100 + (distance_pct + 10) / 30)
                signals.append({
                    "strategy": "coinpaprika_mcap_ath_distance",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Topping risk: market only {abs(distance_pct):.0f}% below ATH, "
                               f"RSI={rsi_val:.0f} overbought"),
                    "timeframe": "1d",
                    "extra": {
                        "distance_from_ath_pct": round(distance_pct, 2),
                        "source": "Coinpaprika global -- topping risk",
                    },
                    "timestamp": _now_iso(),
                })
            except Exception:
                continue

    return signals


# -- W4-3: BTC Miner Revenue Divergence (Blockchain.info) ----------------

BLOCKCHAIN_CHARTS = "https://api.blockchain.info/charts"


def blockchain_miner_revenue_diverge(data: dict[str, pd.DataFrame],
                                      context: Optional[dict] = None) -> list[dict]:
    """Trade BTC based on miner revenue vs price divergence.

    Miner revenue dropping while price rising → miners selling into strength → bearish 2-7d.
    Miner revenue rising while price dropping → miners accumulating → bullish 2-7d.
    Reference: Cong & He (2019) -- mining economics and price dynamics.
    """
    signals: list[dict] = []

    if "BTC-USD" not in data:
        return signals

    # Fetch 14-day miner revenue from Blockchain.info
    rev_data = _fetch_json(f"{BLOCKCHAIN_CHARTS}/miners-revenue?timespan=14days&format=json", timeout=10)
    if not rev_data or "values" not in rev_data:
        return signals

    rev_values = rev_data["values"]
    if len(rev_values) < 7:
        return signals

    # Recent vs older revenue comparison
    recent_rev = [v["y"] for v in rev_values[-3:]]
    older_rev = [v["y"] for v in rev_values[-7:-3]]
    avg_recent = sum(recent_rev) / len(recent_rev) if recent_rev else 0
    avg_older = sum(older_rev) / len(older_rev) if older_rev else 1
    rev_trend = (avg_recent / max(avg_older, 1)) - 1  # Positive = revenue rising

    try:
        df = data["BTC-USD"]
        if len(df) < 14:
            return signals

        close, high, low = df["Close"], df["High"], df["Low"]
        price = float(close.iloc[-1])
        rsi_val = float(rsi(close, 14).iloc[-1])

        # Price trend (7d)
        price_7d_ago = float(close.iloc[-7]) if len(close) >= 7 else price
        price_trend = (price - price_7d_ago) / price_7d_ago

        # Divergence detection
        # Bearish divergence: revenue falling, price rising
        if rev_trend < -0.05 and price_trend > 0.03 and rsi_val > 60:
            entry, tp, sl = _atr_tp_sl(close, high, low, "SELL", 2.5, 1.5)
            rr = abs(entry - tp) / max(abs(sl - entry), 0.01)
            if rr >= 1.5:
                div_strength = min(1.0, abs(rev_trend) * 5 + price_trend * 5)
                conf = min(0.75, 0.48 + div_strength * 0.25)
                signals.append({
                    "strategy": "blockchain_miner_revenue_diverge",
                    "symbol": "BTC-USD", "category": "crypto",
                    "signal_type": "SELL",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Miner revenue divergence: rev {rev_trend*100:+.1f}% but "
                               f"price {price_trend*100:+.1f}% (7d). Miners selling. RSI={rsi_val:.0f}"),
                    "timeframe": "1d",
                    "extra": {
                        "miner_rev_trend_pct": round(rev_trend * 100, 2),
                        "price_trend_7d_pct": round(price_trend * 100, 2),
                        "avg_daily_rev_usd": round(avg_recent, 0),
                        "source": "Blockchain.info miners-revenue -- Cong & He (2019)",
                    },
                    "timestamp": _now_iso(),
                })

        # Bullish divergence: revenue rising, price falling
        elif rev_trend > 0.05 and price_trend < -0.03 and rsi_val < 40:
            entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 3.0, 2.0)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr >= 1.5:
                div_strength = min(1.0, abs(rev_trend) * 5 + abs(price_trend) * 5)
                conf = min(0.78, 0.52 + div_strength * 0.25)
                signals.append({
                    "strategy": "blockchain_miner_revenue_diverge",
                    "symbol": "BTC-USD", "category": "crypto",
                    "signal_type": "BUY",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Miner accumulation: rev {rev_trend*100:+.1f}% while "
                               f"price {price_trend*100:+.1f}% (7d). RSI={rsi_val:.0f}"),
                    "timeframe": "1d",
                    "extra": {
                        "miner_rev_trend_pct": round(rev_trend * 100, 2),
                        "price_trend_7d_pct": round(price_trend * 100, 2),
                        "source": "Blockchain.info miners-revenue -- bullish divergence",
                    },
                    "timestamp": _now_iso(),
                })
    except Exception:
        pass

    return signals


# =========================================================================
# WAVE 5: NEW FREE API STRATEGIES
# =========================================================================

# -- W5-1: Solana TPS Momentum -------------------------------------------

SOLANA_RPC = "https://api.mainnet-beta.solana.com"


def solana_tps_momentum(data: dict[str, pd.DataFrame],
                         context: Optional[dict] = None) -> list[dict]:
    """Trade SOL ecosystem based on Solana TPS momentum.

    TPS spike >50% above baseline → network usage surge → SOL rally 24-48h.
    TPS drop >30% below baseline → congestion risk → avoid SOL longs.
    """
    signals: list[dict] = []

    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": "getRecentPerformanceSamples",
        "params": [20]  # ~20 minutes of samples
    }).encode()

    rpc_data = _fetch_json(SOLANA_RPC, timeout=10,
                           headers={"Content-Type": "application/json"},
                           method="POST", body=payload)

    if not rpc_data or "result" not in rpc_data:
        return signals

    samples = rpc_data["result"]
    if len(samples) < 10:
        return signals

    # Calculate TPS for each sample
    tps_list = [s["numTransactions"] / max(s["samplePeriodSecs"], 1) for s in samples]
    recent_tps = sum(tps_list[:5]) / 5  # Most recent 5 samples
    baseline_tps = sum(tps_list[5:]) / max(len(tps_list) - 5, 1)

    if baseline_tps == 0:
        return signals

    momentum = (recent_tps / baseline_tps) - 1  # Positive = TPS rising

    # SOL ecosystem tokens
    sol_tokens = [s for s in _SOL_ECOSYSTEM if s in data]

    # TPS spike → BUY SOL ecosystem
    if momentum > 0.50:  # >50% above baseline
        for symbol in sol_tokens:
            try:
                df = data[symbol]
                if len(df) < 20:
                    continue
                close, high, low = df["Close"], df["High"], df["Low"]
                rsi_val = float(rsi(close, 14).iloc[-1])

                if rsi_val > 75:
                    continue  # Already overbought

                entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 3.0, 2.0)
                rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
                if rr < 1.5:
                    continue

                conf = min(0.75, 0.50 + momentum * 0.15)
                signals.append({
                    "strategy": "solana_tps_momentum",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Solana TPS surge: {recent_tps:.0f} TPS "
                               f"({momentum*100:+.0f}% vs baseline {baseline_tps:.0f}). "
                               f"Ecosystem demand rising"),
                    "timeframe": "4h",
                    "extra": {
                        "recent_tps": round(recent_tps, 0),
                        "baseline_tps": round(baseline_tps, 0),
                        "tps_momentum_pct": round(momentum * 100, 1),
                        "source": "Solana RPC getRecentPerformanceSamples",
                    },
                    "timestamp": _now_iso(),
                })
            except Exception:
                continue

    return signals


# -- W5-2: Gemini Premium Tracker ----------------------------------------

GEMINI_TICKER = "https://api.gemini.com/v1/pubticker"
BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/price"


def gemini_premium_tracker(data: dict[str, pd.DataFrame],
                            context: Optional[dict] = None) -> list[dict]:
    """Track Gemini/Binance BTC price spread as institutional flow proxy.

    Gemini premium >0.3% → institutional buying → bullish.
    Gemini discount <-0.3% → institutional selling → bearish.
    Reference: Makarov & Schoar (2020) -- cross-exchange price gaps.
    """
    signals: list[dict] = []

    if "BTC-USD" not in data:
        return signals

    gem = _fetch_json(f"{GEMINI_TICKER}/btcusd", timeout=8)
    bin_data = _fetch_json(f"{BINANCE_TICKER}?symbol=BTCUSDT", timeout=8)

    if not gem or not bin_data:
        return signals

    try:
        gem_price = (float(gem.get("bid", 0)) + float(gem.get("ask", 0))) / 2
        bin_price = float(bin_data.get("price", 0))

        if gem_price == 0 or bin_price == 0:
            return signals

        premium_pct = ((gem_price / bin_price) - 1) * 100

        df = data["BTC-USD"]
        if len(df) < 30:
            return signals

        close, high, low = df["Close"], df["High"], df["Low"]
        rsi_val = float(rsi(close, 14).iloc[-1])

        # Institutional buying: Gemini premium + BTC not overbought
        if premium_pct > 0.3 and rsi_val < 65:
            entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 3.0, 2.0)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr >= 1.5:
                conf = min(0.75, 0.50 + premium_pct * 0.10)
                signals.append({
                    "strategy": "gemini_premium_tracker",
                    "symbol": "BTC-USD", "category": "crypto",
                    "signal_type": "BUY",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Institutional buying: Gemini premium "
                               f"{premium_pct:+.3f}% vs Binance. RSI={rsi_val:.0f}"),
                    "timeframe": "4h",
                    "extra": {
                        "gemini_price": round(gem_price, 2),
                        "binance_price": round(bin_price, 2),
                        "premium_pct": round(premium_pct, 4),
                        "source": "Gemini vs Binance -- Makarov & Schoar (2020)",
                    },
                    "timestamp": _now_iso(),
                })

        # Institutional selling: Gemini discount + BTC overbought
        elif premium_pct < -0.3 and rsi_val > 65:
            entry, tp, sl = _atr_tp_sl(close, high, low, "SELL", 2.5, 1.5)
            rr = abs(entry - tp) / max(abs(sl - entry), 0.01)
            if rr >= 1.5:
                conf = min(0.72, 0.48 + abs(premium_pct) * 0.10)
                signals.append({
                    "strategy": "gemini_premium_tracker",
                    "symbol": "BTC-USD", "category": "crypto",
                    "signal_type": "SELL",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Institutional selling: Gemini discount "
                               f"{premium_pct:+.3f}% vs Binance. RSI={rsi_val:.0f}"),
                    "timeframe": "4h",
                    "extra": {
                        "premium_pct": round(premium_pct, 4),
                        "source": "Gemini vs Binance -- institutional flow proxy",
                    },
                    "timestamp": _now_iso(),
                })
    except Exception:
        pass

    return signals


# -- W5-3: BTC Fee Volatility Predictor (Blockchain.info) ----------------

def blockchain_fee_volatility(data: dict[str, pd.DataFrame],
                               context: Optional[dict] = None) -> list[dict]:
    """BTC transaction fee spikes predict price volatility 4-24h ahead.

    Fee spike >3x 7d average → expect volatility → trade with momentum.
    Complements mempool_fee_spike_reversal (different timeframe and logic).
    """
    signals: list[dict] = []

    if "BTC-USD" not in data:
        return signals

    fee_data = _fetch_json(
        f"{BLOCKCHAIN_CHARTS}/transaction-fees-usd?timespan=14days&format=json",
        timeout=10
    )
    if not fee_data or "values" not in fee_data:
        return signals

    fees = [v["y"] for v in fee_data["values"]]
    if len(fees) < 7:
        return signals

    latest_fee = fees[-1]
    avg_7d = sum(fees[-7:]) / 7
    fee_ratio = latest_fee / max(avg_7d, 0.01)

    # Only trigger on fee spikes
    if fee_ratio < 3.0:
        return signals

    try:
        df = data["BTC-USD"]
        if len(df) < 20:
            return signals

        close, high, low = df["Close"], df["High"], df["Low"]
        rsi_val = float(rsi(close, 14).iloc[-1])

        # Fee spike + RSI directional bias
        if rsi_val > 60:  # Momentum up → ride the wave
            entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 2.5, 1.5)
            direction = "BUY"
        elif rsi_val < 40:  # Momentum down → vol spike = acceleration
            entry, tp, sl = _atr_tp_sl(close, high, low, "SELL", 2.5, 1.5)
            direction = "SELL"
        else:
            return signals  # No directional bias

        rr = abs(tp - entry) / max(abs(sl - entry) if direction == "SELL" else abs(entry - sl), 0.01)
        if rr < 1.5:
            return signals

        conf = min(0.72, 0.48 + (fee_ratio - 3) * 0.05)
        signals.append({
            "strategy": "blockchain_fee_volatility",
            "symbol": "BTC-USD", "category": "crypto",
            "signal_type": direction,
            "entry_price": entry, "take_profit": tp, "stop_loss": sl,
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (f"Fee volatility spike: ${latest_fee/1e3:.1f}K/day "
                       f"({fee_ratio:.1f}x 7d avg). Vol expansion expected. RSI={rsi_val:.0f}"),
            "timeframe": "4h",
            "extra": {
                "daily_fee_usd": round(latest_fee, 0),
                "avg_7d_fee_usd": round(avg_7d, 0),
                "fee_ratio": round(fee_ratio, 2),
                "source": "Blockchain.info transaction-fees-usd",
            },
            "timestamp": _now_iso(),
        })
    except Exception:
        pass

    return signals


# -- W5-4: Blockchain TX Volume Divergence --------------------------------

def blockchain_tx_volume_divergence(data: dict[str, pd.DataFrame],
                                     context: Optional[dict] = None) -> list[dict]:
    """On-chain TX volume diverging from exchange volume → institutional OTC activity.

    Rising on-chain volume + flat exchange volume → OTC accumulation → bullish.
    Falling on-chain volume + rising exchange volume → retail panic → bearish.
    """
    signals: list[dict] = []

    if "BTC-USD" not in data:
        return signals

    tx_data = _fetch_json(
        f"{BLOCKCHAIN_CHARTS}/estimated-transaction-volume-usd?timespan=14days&format=json",
        timeout=10
    )
    if not tx_data or "values" not in tx_data:
        return signals

    tx_vals = [v["y"] for v in tx_data["values"]]
    if len(tx_vals) < 7:
        return signals

    recent_tx = sum(tx_vals[-3:]) / 3
    older_tx = sum(tx_vals[-7:-3]) / max(len(tx_vals[-7:-3]), 1)
    tx_trend = (recent_tx / max(older_tx, 1)) - 1

    try:
        df = data["BTC-USD"]
        if len(df) < 14:
            return signals

        close, high, low, volume = df["Close"], df["High"], df["Low"], df["Volume"]

        # Exchange volume trend (from OHLCV)
        recent_vol = float(volume.tail(3).mean())
        older_vol = float(volume.iloc[-7:-3].mean()) if len(volume) >= 7 else recent_vol
        exch_vol_trend = (recent_vol / max(older_vol, 1)) - 1

        rsi_val = float(rsi(close, 14).iloc[-1])

        # Bullish: on-chain rising + exchange flat/falling → OTC accumulation
        if tx_trend > 0.10 and exch_vol_trend < 0.05 and rsi_val < 55:
            entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 3.0, 2.0)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr >= 1.5:
                conf = min(0.75, 0.50 + tx_trend * 0.5)
                signals.append({
                    "strategy": "blockchain_tx_volume_divergence",
                    "symbol": "BTC-USD", "category": "crypto",
                    "signal_type": "BUY",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"OTC accumulation: on-chain vol {tx_trend*100:+.1f}% but "
                               f"exchange vol {exch_vol_trend*100:+.1f}%. "
                               f"TX vol=${recent_tx/1e9:.1f}B/day"),
                    "timeframe": "1d",
                    "extra": {
                        "onchain_vol_trend_pct": round(tx_trend * 100, 2),
                        "exchange_vol_trend_pct": round(exch_vol_trend * 100, 2),
                        "daily_onchain_vol_usd": round(recent_tx, 0),
                        "source": "Blockchain.info estimated-transaction-volume-usd",
                    },
                    "timestamp": _now_iso(),
                })
    except Exception:
        pass

    return signals


# =========================================================================
# WAVE 6: CROSS-EXCHANGE + STABLECOIN STRATEGIES
# =========================================================================

# -- W6-1: Funding Spread Arbitrage (Binance vs Bybit) -------------------

BINANCE_FUNDING = "https://fapi.binance.com/fapi/v1/premiumIndex"
BYBIT_TICKERS = "https://api.bybit.com/v5/market/tickers"


def funding_spread_arbitrage(data: dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> list[dict]:
    """Trade funding rate divergence between Binance and Bybit.

    When Binance funding is much higher than Bybit → Binance crowd overleveraged long →
    expect mean reversion (SHORT). Vice versa for shorts.
    """
    signals: list[dict] = []

    # Fetch Binance funding for BTCUSDT
    bin_fund = _fetch_json(f"{BINANCE_FUNDING}?symbol=BTCUSDT", timeout=8)
    bybit_data = _fetch_json(
        f"{BYBIT_TICKERS}?category=linear&symbol=BTCUSDT", timeout=8
    )

    if not bin_fund or not bybit_data:
        return signals

    try:
        bin_rate = float(bin_fund.get("lastFundingRate", 0))
        bybit_list = bybit_data.get("result", {}).get("list", [])
        bybit_rate = float(bybit_list[0].get("fundingRate", 0)) if bybit_list else 0

        spread = bin_rate - bybit_rate  # Positive = Binance more bullish

        # Only trade significant spread (>0.02% = 2 bps)
        if abs(spread) < 0.0002:
            return signals

        if "BTC-USD" not in data:
            return signals

        df = data["BTC-USD"]
        if len(df) < 20:
            return signals

        close, high, low = df["Close"], df["High"], df["Low"]
        rsi_val = float(rsi(close, 14).iloc[-1])

        # Binance much higher funding → crowd overleveraged long → SHORT
        if spread > 0.0005 and rsi_val > 55:
            entry, tp, sl = _atr_tp_sl(close, high, low, "SELL", 2.5, 1.5)
            rr = abs(entry - tp) / max(abs(sl - entry), 0.01)
            if rr >= 1.5:
                conf = min(0.72, 0.48 + abs(spread) * 200)
                signals.append({
                    "strategy": "funding_spread_arbitrage",
                    "symbol": "BTC-USD", "category": "crypto",
                    "signal_type": "SELL",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Funding spread: Binance {bin_rate*100:.4f}% vs "
                               f"Bybit {bybit_rate*100:.4f}% (spread={spread*100:.4f}%). "
                               f"Binance crowd overleveraged long"),
                    "timeframe": "4h",
                    "extra": {
                        "binance_funding": round(bin_rate * 100, 4),
                        "bybit_funding": round(bybit_rate * 100, 4),
                        "spread_bps": round(spread * 10000, 2),
                        "source": "Binance vs Bybit funding rate divergence",
                    },
                    "timestamp": _now_iso(),
                })

        # Bybit much higher → SHORT on Bybit crowd overleveraged
        elif spread < -0.0005 and rsi_val < 45:
            entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 3.0, 2.0)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr >= 1.5:
                conf = min(0.72, 0.48 + abs(spread) * 200)
                signals.append({
                    "strategy": "funding_spread_arbitrage",
                    "symbol": "BTC-USD", "category": "crypto",
                    "signal_type": "BUY",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Funding spread: Bybit {bybit_rate*100:.4f}% > "
                               f"Binance {bin_rate*100:.4f}% (spread={spread*100:.4f}%). "
                               f"Bybit crowd overleveraged short"),
                    "timeframe": "4h",
                    "extra": {
                        "binance_funding": round(bin_rate * 100, 4),
                        "bybit_funding": round(bybit_rate * 100, 4),
                        "spread_bps": round(spread * 10000, 2),
                        "source": "Binance vs Bybit funding rate divergence",
                    },
                    "timestamp": _now_iso(),
                })
    except Exception:
        pass

    return signals


# -- W6-2: Stablecoin Supply Momentum (DefiLlama) ------------------------

DEFILLAMA_STABLES = "https://stablecoins.llama.fi/stablecoins?includePrices=true"


def stablecoin_supply_momentum(data: dict[str, pd.DataFrame],
                                context: Optional[dict] = None) -> list[dict]:
    """Track stablecoin supply growth as a crypto liquidity signal.

    Rising stablecoin supply → capital entering crypto → bullish for all assets.
    Falling supply → capital leaving → bearish macro signal.
    Reference: Lyons & Viswanath-Natraj (2023) -- stablecoin demand drives crypto.
    """
    signals: list[dict] = []

    stable_data = _fetch_json(DEFILLAMA_STABLES, timeout=10)
    if not stable_data or "peggedAssets" not in stable_data:
        return signals

    # Sum USDT + USDC supply (top 2 = >90% of stablecoin market)
    total_supply = 0
    for asset in stable_data["peggedAssets"]:
        symbol = asset.get("symbol", "")
        if symbol in ("USDT", "USDC"):
            circ = asset.get("circulating", {})
            total_supply += circ.get("peggedUSD", 0)

    if total_supply == 0:
        return signals

    # We need historical comparison — use the circulatingPrevDay fields
    prev_supply = 0
    for asset in stable_data["peggedAssets"]:
        symbol = asset.get("symbol", "")
        if symbol in ("USDT", "USDC"):
            circ_prev = asset.get("circulatingPrevDay", {})
            prev_supply += circ_prev.get("peggedUSD", 0)

    if prev_supply == 0:
        return signals

    supply_change = (total_supply - prev_supply) / prev_supply

    # Only act on significant supply changes (>0.1% daily = meaningful)
    if abs(supply_change) < 0.001:
        return signals

    # Bullish: stablecoin supply growing → capital entering
    if supply_change > 0.002:  # >0.2% daily growth
        for symbol in ("BTC-USD", "ETH-USD", "SOL-USD"):
            if symbol not in data:
                continue
            try:
                df = data[symbol]
                if len(df) < 20:
                    continue
                close, high, low = df["Close"], df["High"], df["Low"]
                rsi_val = float(rsi(close, 14).iloc[-1])
                if rsi_val > 70:
                    continue

                entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 3.0, 2.0)
                rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
                if rr < 1.5:
                    continue

                conf = min(0.75, 0.50 + supply_change * 50)
                signals.append({
                    "strategy": "stablecoin_supply_momentum",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Stablecoin inflow: USDT+USDC supply "
                               f"{supply_change*100:+.3f}%/day "
                               f"(${total_supply/1e9:.0f}B total). Capital entering crypto"),
                    "timeframe": "1d",
                    "extra": {
                        "usdt_usdc_supply_usd": round(total_supply, 0),
                        "supply_change_pct": round(supply_change * 100, 4),
                        "source": "DefiLlama stablecoins -- Lyons & Viswanath-Natraj (2023)",
                    },
                    "timestamp": _now_iso(),
                })
            except Exception:
                continue

    return signals


# -- W6-3: DeFi TVL Momentum (DefiLlama) ---------------------------------

DEFILLAMA_CHAINS = "https://api.llama.fi/v2/chains"


def defi_tvl_momentum(data: dict[str, pd.DataFrame],
                       context: Optional[dict] = None) -> list[dict]:
    """Track DeFi TVL by chain as ecosystem rotation signal.

    Rising Ethereum TVL → ETH and DeFi tokens rally.
    Rising Solana TVL → SOL ecosystem rally.
    Falling TVL everywhere → risk-off, reduce exposure.
    """
    signals: list[dict] = []

    chains = _fetch_json(DEFILLAMA_CHAINS, timeout=10)
    if not chains or not isinstance(chains, list):
        return signals

    # Map chains to tokens
    chain_map = {
        "Ethereum": "ETH-USD",
        "Solana": "SOL-USD",
        "BSC": "BNB-USD",
        "Avalanche": "AVAX-USD",
        "Arbitrum": "ARB-USD",
        "Optimism": "OP-USD",
    }

    for chain_info in chains:
        chain_name = chain_info.get("name", "")
        if chain_name not in chain_map:
            continue

        symbol = chain_map[chain_name]
        if symbol not in data:
            continue

        tvl = chain_info.get("tvl", 0)
        # DefiLlama includes tokenSymbol for some chains
        if tvl <= 0:
            continue

        try:
            df = data[symbol]
            if len(df) < 30:
                continue

            close, high, low = df["Close"], df["High"], df["Low"]
            rsi_val = float(rsi(close, 14).iloc[-1])

            # Use price momentum as TVL-change proxy (TVL history needs separate call)
            sma_20_val = float(sma(close, 20).iloc[-1])
            sma_50_val = float(sma(close, 50).iloc[-1])

            # BUY: high TVL chain + price above 20/50 SMA + not overbought
            if tvl > 1e9 and sma_20_val > sma_50_val and rsi_val < 65:
                entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 3.0, 2.0)
                rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
                if rr < 1.5:
                    continue

                # Higher TVL = higher base confidence
                tvl_score = min(0.15, (tvl / 1e11) * 0.15)
                conf = min(0.75, 0.50 + tvl_score + (65 - rsi_val) / 200)

                signals.append({
                    "strategy": "defi_tvl_momentum",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"{chain_name} DeFi TVL ${tvl/1e9:.1f}B, "
                               f"SMA20>SMA50 uptrend, RSI={rsi_val:.0f}"),
                    "timeframe": "1d",
                    "extra": {
                        "chain": chain_name,
                        "tvl_usd": round(tvl, 0),
                        "sma_20_above_50": True,
                        "source": "DefiLlama v2/chains -- ecosystem rotation",
                    },
                    "timestamp": _now_iso(),
                })
        except Exception:
            continue

    return signals


# -- W6-4: Multi-Exchange Premium ----------------------------------------

_EXCHANGE_TICKERS = {
    "gemini": "https://api.gemini.com/v1/pubticker/btcusd",
    "kraken": "https://api.kraken.com/0/public/Ticker?pair=XBTUSD",
    "binance": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
}


def multi_exchange_premium(data: dict[str, pd.DataFrame],
                            context: Optional[dict] = None) -> list[dict]:
    """Track BTC price across 3 exchanges for flow direction signals.

    Large spread (>0.5%) between any two → flow imbalance → trade direction.
    """
    signals: list[dict] = []

    if "BTC-USD" not in data:
        return signals

    prices = {}
    # Gemini
    gem = _fetch_json(_EXCHANGE_TICKERS["gemini"], timeout=8)
    if gem:
        prices["gemini"] = (float(gem.get("bid", 0)) + float(gem.get("ask", 0))) / 2

    # Kraken
    kr = _fetch_json(_EXCHANGE_TICKERS["kraken"], timeout=8)
    if kr and "result" in kr:
        for pair_data in kr["result"].values():
            if isinstance(pair_data, dict) and "a" in pair_data:
                prices["kraken"] = float(pair_data["a"][0])
                break

    # Binance
    bn = _fetch_json(_EXCHANGE_TICKERS["binance"], timeout=8)
    if bn:
        prices["binance"] = float(bn.get("price", 0))

    if len(prices) < 2:
        return signals

    # Find max spread
    price_list = list(prices.values())
    avg_price = sum(price_list) / len(price_list)
    max_price = max(price_list)
    min_price = min(price_list)
    spread_pct = ((max_price / min_price) - 1) * 100

    if spread_pct < 0.5:
        return signals  # Normal range

    # Determine direction from which exchange has premium
    max_exchange = [k for k, v in prices.items() if v == max_price][0]

    try:
        df = data["BTC-USD"]
        if len(df) < 20:
            return signals

        close, high, low = df["Close"], df["High"], df["Low"]
        rsi_val = float(rsi(close, 14).iloc[-1])

        # Premium on institutional exchange (Gemini/Kraken) → BUY
        if max_exchange in ("gemini", "kraken") and rsi_val < 65:
            entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 3.0, 2.0)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr >= 1.5:
                conf = min(0.72, 0.48 + spread_pct * 0.08)
                signals.append({
                    "strategy": "multi_exchange_premium",
                    "symbol": "BTC-USD", "category": "crypto",
                    "signal_type": "BUY",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Institutional premium: {max_exchange} "
                               f"+{spread_pct:.2f}% vs market. Prices: "
                               f"{', '.join(f'{k}=${v:,.0f}' for k,v in prices.items())}"),
                    "timeframe": "4h",
                    "extra": {
                        "prices": {k: round(v, 2) for k, v in prices.items()},
                        "spread_pct": round(spread_pct, 3),
                        "premium_exchange": max_exchange,
                        "source": "Multi-exchange BTC premium -- flow detection",
                    },
                    "timestamp": _now_iso(),
                })
    except Exception:
        pass

    return signals


# -- W6-5: Coinlore Altseason Breadth ------------------------------------

def coinlore_altseason_breadth(data: dict[str, pd.DataFrame],
                                context: Optional[dict] = None) -> list[dict]:
    """Market breadth: % of top 100 coins positive (7d) as alt season indicator.

    >70% green → strong alt season → BUY alts with momentum.
    <30% green → capitulation → contrarian BUY on oversold dips.
    """
    signals: list[dict] = []

    tickers = _fetch_json(f"{COINLORE_TICKERS}?start=0&limit=100", timeout=10)
    if not tickers or "data" not in tickers:
        return signals

    coins = tickers["data"]
    positive_7d = sum(1 for c in coins if float(c.get("percent_change_7d", 0)) > 0)
    breadth = positive_7d / max(len(coins), 1)

    # Strong breadth → alt season → BUY alts with momentum
    if breadth > 0.70:
        for symbol in _ALT_SEASON_TOKENS:
            if symbol not in data:
                continue
            try:
                df = data[symbol]
                if len(df) < 20:
                    continue
                close, high, low = df["Close"], df["High"], df["Low"]
                rsi_val = float(rsi(close, 14).iloc[-1])
                if rsi_val > 75 or rsi_val < 30:
                    continue

                ret_7d = (float(close.iloc[-1]) - float(close.iloc[-7])) / float(close.iloc[-7])
                if ret_7d < 0:
                    continue  # Only buy green alts

                entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 3.0, 2.0)
                rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
                if rr < 1.5:
                    continue

                conf = min(0.75, 0.50 + (breadth - 0.70) * 2)
                signals.append({
                    "strategy": "coinlore_altseason_breadth",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Alt season breadth: {positive_7d}/{len(coins)} coins "
                               f"green ({breadth*100:.0f}%). Strong market breadth"),
                    "timeframe": "1d",
                    "extra": {
                        "breadth_pct": round(breadth * 100, 1),
                        "positive_coins": positive_7d,
                        "total_coins": len(coins),
                        "source": "Coinlore top 100 -- market breadth",
                    },
                    "timestamp": _now_iso(),
                })
            except Exception:
                continue

    # Capitulation → contrarian BUY on oversold large caps
    elif breadth < 0.30:
        for symbol in ("BTC-USD", "ETH-USD", "SOL-USD"):
            if symbol not in data:
                continue
            try:
                df = data[symbol]
                if len(df) < 20:
                    continue
                close, high, low = df["Close"], df["High"], df["Low"]
                rsi_val = float(rsi(close, 14).iloc[-1])
                if rsi_val > 35:
                    continue  # Only buy deep oversold

                entry, tp, sl = _atr_tp_sl(close, high, low, "BUY", 3.5, 2.0)
                rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
                if rr < 1.5:
                    continue

                conf = min(0.78, 0.52 + (0.30 - breadth) * 2)
                signals.append({
                    "strategy": "coinlore_altseason_breadth",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry, "take_profit": tp, "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Capitulation: only {positive_7d}/{len(coins)} coins "
                               f"green ({breadth*100:.0f}%). Contrarian oversold buy. "
                               f"RSI={rsi_val:.0f}"),
                    "timeframe": "1d",
                    "extra": {
                        "breadth_pct": round(breadth * 100, 1),
                        "source": "Coinlore top 100 -- contrarian capitulation",
                    },
                    "timestamp": _now_iso(),
                })
            except Exception:
                continue

    return signals


# =========================================================================
# Registry -- all Wave 4/5/6 strategies
# =========================================================================

WAVE456_STRATEGIES = {
    # Wave 4: Macro regime
    "coinlore_btc_dominance_rotation":   coinlore_btc_dominance_rotation,
    "coinpaprika_mcap_ath_distance":     coinpaprika_mcap_ath_distance,
    "blockchain_miner_revenue_diverge":  blockchain_miner_revenue_diverge,
    # Wave 5: New free APIs
    "solana_tps_momentum":               solana_tps_momentum,
    "gemini_premium_tracker":            gemini_premium_tracker,
    "blockchain_fee_volatility":         blockchain_fee_volatility,
    "blockchain_tx_volume_divergence":   blockchain_tx_volume_divergence,
    # Wave 6: Cross-exchange + stablecoin
    "funding_spread_arbitrage":          funding_spread_arbitrage,
    "stablecoin_supply_momentum":        stablecoin_supply_momentum,
    "defi_tvl_momentum":                 defi_tvl_momentum,
    "multi_exchange_premium":            multi_exchange_premium,
    "coinlore_altseason_breadth":        coinlore_altseason_breadth,
}
