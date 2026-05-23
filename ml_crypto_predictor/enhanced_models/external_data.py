"""
External Market Data Fetchers — Free API Sources
=================================================
Fetches data NOT available in Binance OHLCV for ML feature enrichment.
All sources are free. Returns scalars or small DataFrames.
Every function returns a safe fallback value on failure.
"""
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from pathlib import Path
import json, time

CACHE_DIR = Path(__file__).resolve().parent / "data" / "external_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _cached(key: str, max_age_hours: float = 1.0):
    """Read from cache if fresh enough."""
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if age_h < max_age_hours:
            with open(path) as f:
                return json.load(f)
    return None

def _save_cache(key: str, data):
    with open(CACHE_DIR / f"{key}.json", "w") as f:
        json.dump(data, f, default=str)


# === 1. Futures Open Interest (multi-exchange failover) ===

# Binance fapi mirrors + Bybit fallback for OI data
_BINANCE_FAPI_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]
_BYBIT_BASE = "https://api.bybit.com"


def fetch_open_interest(symbol: str = "BTCUSDT") -> Dict[str, float]:
    """Fetch open interest with failover: Binance fapi mirrors -> Bybit v5."""
    cache_key = f"oi_{symbol}"
    cached = _cached(cache_key, 0.25)  # 15 min cache
    if cached:
        return cached

    # Try Binance fapi mirrors
    for base in _BINANCE_FAPI_BASES:
        try:
            r = requests.get(f"{base}/fapi/v1/openInterest",
                             params={"symbol": symbol}, timeout=10)
            r.raise_for_status()
            data = r.json()
            result = {"oi_value": float(data.get("openInterest", 0)),
                      "symbol": symbol, "time": data.get("time", 0)}
            _save_cache(cache_key, result)
            return result
        except Exception:
            continue

    # Fallback: Bybit v5
    try:
        r = requests.get(f"{_BYBIT_BASE}/v5/market/tickers",
                         params={"category": "linear", "symbol": symbol}, timeout=10)
        r.raise_for_status()
        data = r.json()
        tickers = data.get("result", {}).get("list", [])
        if tickers:
            oi = float(tickers[0].get("openInterest", 0))
            result = {"oi_value": oi, "symbol": symbol, "time": int(time.time() * 1000)}
            _save_cache(cache_key, result)
            return result
    except Exception as e:
        print(f"[external] OI fetch failed for {symbol} (all sources): {e}")

    return {"oi_value": 0.0, "symbol": symbol, "time": 0}


def fetch_open_interest_history(symbol: str = "BTCUSDT", period: str = "1h",
                                 limit: int = 48) -> pd.DataFrame:
    """Fetch OI history with failover: Binance fapi mirrors -> Bybit v5."""
    cache_key = f"oi_hist_{symbol}_{period}_{limit}"
    cached = _cached(cache_key, 0.5)
    if cached:
        return pd.DataFrame(cached)

    # Try Binance fapi mirrors
    for base in _BINANCE_FAPI_BASES:
        try:
            r = requests.get(f"{base}/futures/data/openInterestHist",
                             params={"symbol": symbol, "period": period, "limit": limit},
                             timeout=10)
            r.raise_for_status()
            data = r.json()
            rows = [{"timestamp": pd.Timestamp(d["timestamp"], unit="ms", tz="UTC"),
                     "oi": float(d.get("sumOpenInterest", 0)),
                     "oi_value": float(d.get("sumOpenInterestValue", 0))}
                    for d in data]
            df = pd.DataFrame(rows)
            if not df.empty:
                df.set_index("timestamp", inplace=True)
                _save_cache(cache_key, df.reset_index().to_dict("records"))
            return df
        except Exception:
            continue

    # Bybit doesn't have historical OI in free API, return empty
    print(f"[external] OI history failed for {symbol} (all Binance mirrors)")
    return pd.DataFrame()


# === 2. Deribit DVOL (Bitcoin Implied Volatility Index) ===
def fetch_deribit_dvol(currency: str = "BTC", resolution: int = 3600,
                        hours: int = 48) -> Dict[str, float]:
    """
    Fetch DVOL (Deribit Volatility Index) — free public API.
    Returns {dvol_current, dvol_24h_ago, dvol_change, dvol_percentile}.
    """
    cache_key = f"dvol_{currency}"
    cached = _cached(cache_key, 0.5)
    if cached:
        return cached
    try:
        end = int(datetime.now(timezone.utc).timestamp() * 1000)
        start = end - hours * 3600 * 1000
        r = requests.get("https://www.deribit.com/api/v2/public/get_volatility_index_data",
                         params={"currency": currency, "start_timestamp": start,
                                 "end_timestamp": end, "resolution": resolution},
                         timeout=10)
        r.raise_for_status()
        data = r.json().get("result", {}).get("data", [])
        if not data:
            return {"dvol_current": 50.0, "dvol_24h_ago": 50.0,
                    "dvol_change": 0.0, "dvol_percentile": 0.5}
        # data is [[timestamp, open, high, low, close], ...]
        current = data[-1][4]
        ago_24h = data[max(0, len(data) - 25)][4] if len(data) > 24 else data[0][4]
        all_vals = [d[4] for d in data]
        percentile = sum(1 for v in all_vals if v < current) / max(len(all_vals), 1)
        result = {"dvol_current": current, "dvol_24h_ago": ago_24h,
                  "dvol_change": (current - ago_24h) / max(ago_24h, 1),
                  "dvol_percentile": percentile}
        _save_cache(cache_key, result)
        return result
    except Exception as e:
        print(f"[external] Deribit DVOL failed: {e}")
        return {"dvol_current": 50.0, "dvol_24h_ago": 50.0,
                "dvol_change": 0.0, "dvol_percentile": 0.5}


# === 3. SPX / VIX via yfinance ===
def fetch_spx_vix(days: int = 60) -> Dict[str, float]:
    """
    Fetch S&P 500 and VIX data via yfinance for macro correlation features.
    Returns {spx_return_1d, spx_return_5d, vix_current, vix_percentile,
             vix_5d_change, spx_vix_regime}.
    """
    cache_key = f"spx_vix_{days}"
    cached = _cached(cache_key, 1.0)
    if cached:
        return cached
    try:
        import yfinance as yf
        spy = yf.download("SPY", period=f"{days}d", interval="1d", progress=False)
        vix = yf.download("^VIX", period=f"{days}d", interval="1d", progress=False)

        spx_close = spy["Close"].iloc[:, 0] if isinstance(spy["Close"], pd.DataFrame) else spy["Close"]
        vix_close = vix["Close"].iloc[:, 0] if isinstance(vix["Close"], pd.DataFrame) else vix["Close"]

        spx_ret_1d = float(spx_close.pct_change().iloc[-1]) if len(spx_close) > 1 else 0.0
        spx_ret_5d = float((spx_close.iloc[-1] / spx_close.iloc[-6] - 1)) if len(spx_close) > 5 else 0.0

        vix_current = float(vix_close.iloc[-1]) if len(vix_close) > 0 else 20.0
        vix_hist = vix_close.dropna().values
        vix_pctile = float(np.sum(vix_hist < vix_current) / max(len(vix_hist), 1))
        vix_5d = float(vix_current - vix_close.iloc[-6]) if len(vix_close) > 5 else 0.0

        # Regime: 0=low vol, 1=normal, 2=high, 3=extreme
        if vix_current < 15: regime = 0
        elif vix_current < 25: regime = 1
        elif vix_current < 35: regime = 2
        else: regime = 3

        result = {"spx_return_1d": spx_ret_1d, "spx_return_5d": spx_ret_5d,
                  "vix_current": vix_current, "vix_percentile": vix_pctile,
                  "vix_5d_change": vix_5d, "spx_vix_regime": regime}
        _save_cache(cache_key, result)
        return result
    except Exception as e:
        print(f"[external] SPX/VIX fetch failed: {e}")
        return {"spx_return_1d": 0.0, "spx_return_5d": 0.0,
                "vix_current": 20.0, "vix_percentile": 0.5,
                "vix_5d_change": 0.0, "spx_vix_regime": 1}


# === 4. Coinbase Premium Index ===
def fetch_coinbase_premium() -> Dict[str, float]:
    """
    Coinbase BTC-USD vs Binance BTCUSDT premium.
    Positive = US institutional buying pressure (bullish).
    """
    cache_key = "coinbase_premium"
    cached = _cached(cache_key, 0.25)
    if cached:
        return cached
    try:
        # Binance price
        r_bn = requests.get("https://api.binance.com/api/v3/ticker/price",
                            params={"symbol": "BTCUSDT"}, timeout=5)
        binance_price = float(r_bn.json()["price"])

        # Coinbase price via public ticker
        r_cb = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=5)
        coinbase_price = float(r_cb.json()["data"]["amount"])

        premium = (coinbase_price - binance_price) / binance_price
        result = {"coinbase_premium": premium, "coinbase_price": coinbase_price,
                  "binance_price": binance_price}
        _save_cache(cache_key, result)
        return result
    except Exception as e:
        print(f"[external] Coinbase premium failed: {e}")
        return {"coinbase_premium": 0.0, "coinbase_price": 0.0, "binance_price": 0.0}


# === 5. Binance Long/Short Ratio ===
def fetch_long_short_ratio(symbol: str = "BTCUSDT", period: str = "1h",
                            limit: int = 24) -> Dict[str, float]:
    """
    Fetch Binance top trader long/short ratio.
    Returns {ls_ratio_current, ls_ratio_change_24h, ls_extreme}.
    """
    cache_key = f"ls_ratio_{symbol}"
    cached = _cached(cache_key, 0.25)
    if cached:
        return cached
    try:
        r = requests.get("https://fapi.binance.com/futures/data/topLongShortPositionRatio",
                         params={"symbol": symbol, "period": period, "limit": limit},
                         timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            return {"ls_ratio_current": 1.0, "ls_ratio_change_24h": 0.0, "ls_extreme": 0}
        current = float(data[-1].get("longShortRatio", 1.0))
        oldest = float(data[0].get("longShortRatio", 1.0))
        change = (current - oldest) / max(oldest, 0.01)
        extreme = 1 if current > 2.5 or current < 0.4 else 0
        result = {"ls_ratio_current": current, "ls_ratio_change_24h": change,
                  "ls_extreme": extreme}
        _save_cache(cache_key, result)
        return result
    except Exception as e:
        print(f"[external] Long/short ratio failed for {symbol}: {e}")
        return {"ls_ratio_current": 1.0, "ls_ratio_change_24h": 0.0, "ls_extreme": 0}


# === 6. Funding Rate History (for momentum, not just current level) ===
def fetch_funding_rate_history(symbol: str = "BTCUSDT", limit: int = 30) -> Dict[str, float]:
    """
    Fetch funding rate history for rate-of-change features.
    Returns {fr_current, fr_8h_ago, fr_24h_ago, fr_roc_8h, fr_roc_24h,
             fr_cumulative_24h, fr_extreme}.
    """
    cache_key = f"fr_hist_{symbol}"
    cached = _cached(cache_key, 0.5)
    if cached:
        return cached
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate",
                         params={"symbol": symbol, "limit": limit}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            return {"fr_current": 0.0, "fr_8h_ago": 0.0, "fr_24h_ago": 0.0,
                    "fr_roc_8h": 0.0, "fr_roc_24h": 0.0,
                    "fr_cumulative_24h": 0.0, "fr_extreme": 0}
        rates = [float(d.get("fundingRate", 0)) for d in data]
        current = rates[-1] if rates else 0.0
        ago_8h = rates[-2] if len(rates) > 1 else current
        ago_24h = rates[-4] if len(rates) > 3 else rates[0]
        roc_8h = current - ago_8h
        roc_24h = current - ago_24h
        cum_24h = sum(rates[-3:])  # last 3 periods = 24h
        extreme = 1 if abs(current) > 0.001 else 0  # >0.1% is extreme
        result = {"fr_current": current, "fr_8h_ago": ago_8h, "fr_24h_ago": ago_24h,
                  "fr_roc_8h": roc_8h, "fr_roc_24h": roc_24h,
                  "fr_cumulative_24h": cum_24h, "fr_extreme": extreme}
        _save_cache(cache_key, result)
        return result
    except Exception as e:
        print(f"[external] Funding rate history failed for {symbol}: {e}")
        return {"fr_current": 0.0, "fr_8h_ago": 0.0, "fr_24h_ago": 0.0,
                "fr_roc_8h": 0.0, "fr_roc_24h": 0.0,
                "fr_cumulative_24h": 0.0, "fr_extreme": 0}


# === 7. Alpha Engine Signal Confluence ===
def fetch_alpha_engine_confluence(symbol: str) -> Dict[str, float]:
    """
    Read Alpha Engine active picks to count how many strategies agree on this symbol.
    This is our UNIQUE edge — nobody else has this cross-system signal.
    """
    try:
        repo_root = Path(__file__).resolve().parent.parent.parent
        picks_path = repo_root / "alpha_engine" / "data" / "active_picks.json"
        perf_path = repo_root / "alpha_engine" / "data" / "strategy_performance.json"

        confluence_buy = 0
        confluence_sell = 0
        avg_confidence = 0.0
        proven_strategy_active = 0

        # Count active picks for this symbol
        if picks_path.exists():
            with open(picks_path) as f:
                picks = json.load(f)
            # Normalize symbol: "BTC-USD" → "BTCUSDT", etc.
            symbol_variants = [symbol, symbol.replace("USDT", "-USD"),
                              symbol.replace("USDT", "USD")]
            matching = [p for p in picks if p.get("symbol", "") in symbol_variants
                       or symbol in p.get("symbol", "")]
            for p in matching:
                if p.get("signal_type") == "BUY":
                    confluence_buy += 1
                else:
                    confluence_sell += 1
                avg_confidence += p.get("confidence", 0.5)
            if matching:
                avg_confidence /= len(matching)

            # Check if proven strategy (Connors RSI-2, etc.) is active
            proven_strategies = {"connors_rsi2_crypto", "connors_rsi2_scanner",
                                "vix_spike_reversal_scanner", "triple_rsi_scanner"}
            for p in matching:
                if p.get("strategy") in proven_strategies:
                    proven_strategy_active = 1

        # Get strategy performance for this symbol
        best_strategy_wr = 0.0
        if perf_path.exists():
            with open(perf_path) as f:
                perf = json.load(f)
            for strat_name, strat_data in perf.items():
                by_sym = strat_data.get("by_symbol", {})
                for sym_key, sym_data in by_sym.items():
                    if symbol in sym_key or sym_key.replace("-", "") in symbol:
                        total = sym_data.get("wins", 0) + sym_data.get("losses", 0)
                        if total > 0:
                            wr = sym_data["wins"] / total
                            best_strategy_wr = max(best_strategy_wr, wr)

        return {"alpha_confluence_buy": confluence_buy,
                "alpha_confluence_sell": confluence_sell,
                "alpha_confluence_total": confluence_buy + confluence_sell,
                "alpha_avg_confidence": avg_confidence,
                "alpha_proven_strategy_active": proven_strategy_active,
                "alpha_best_strategy_wr": best_strategy_wr}
    except Exception as e:
        print(f"[external] Alpha Engine confluence failed: {e}")
        return {"alpha_confluence_buy": 0, "alpha_confluence_sell": 0,
                "alpha_confluence_total": 0, "alpha_avg_confidence": 0.0,
                "alpha_proven_strategy_active": 0, "alpha_best_strategy_wr": 0.0}


# === 8. BTC Dominance ===
def fetch_btc_dominance() -> Dict[str, float]:
    """Fetch BTC dominance from CoinGecko free API."""
    cache_key = "btc_dominance"
    cached = _cached(cache_key, 0.5)
    if cached:
        return cached
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
        r.raise_for_status()
        data = r.json().get("data", {})
        btc_dom = data.get("market_cap_percentage", {}).get("btc", 50.0)
        eth_dom = data.get("market_cap_percentage", {}).get("eth", 15.0)
        total_mcap = data.get("total_market_cap", {}).get("usd", 0)
        result = {"btc_dominance": btc_dom, "eth_dominance": eth_dom,
                  "altcoin_dominance": 100 - btc_dom - eth_dom,
                  "total_market_cap_usd": total_mcap}
        _save_cache(cache_key, result)
        return result
    except Exception as e:
        print(f"[external] BTC dominance fetch failed: {e}")
        return {"btc_dominance": 50.0, "eth_dominance": 15.0,
                "altcoin_dominance": 35.0, "total_market_cap_usd": 0}


# === Master fetcher: get all external features for a symbol ===
def fetch_all_external_features(symbol: str = "BTCUSDT") -> Dict[str, float]:
    """
    Fetch ALL external features for a given symbol.
    Returns flat dict ready to merge into feature DataFrame.
    """
    features = {}

    # 1. Open Interest
    oi = fetch_open_interest(symbol)
    features["ext_oi_value"] = oi["oi_value"]

    # OI history for rate of change
    oi_hist = fetch_open_interest_history(symbol, "1h", 48)
    if not oi_hist.empty and len(oi_hist) > 1:
        features["ext_oi_roc_4h"] = (oi_hist["oi"].iloc[-1] / max(oi_hist["oi"].iloc[-5], 1e-10)) - 1 if len(oi_hist) > 4 else 0.0
        features["ext_oi_roc_24h"] = (oi_hist["oi"].iloc[-1] / max(oi_hist["oi"].iloc[0], 1e-10)) - 1
    else:
        features["ext_oi_roc_4h"] = 0.0
        features["ext_oi_roc_24h"] = 0.0

    # 2. Deribit DVOL (BTC only, use as macro signal for all pairs)
    dvol = fetch_deribit_dvol("BTC")
    features["ext_dvol"] = dvol["dvol_current"]
    features["ext_dvol_change"] = dvol["dvol_change"]
    features["ext_dvol_percentile"] = dvol["dvol_percentile"]

    # 3. SPX/VIX
    spx = fetch_spx_vix()
    features["ext_spx_return_1d"] = spx["spx_return_1d"]
    features["ext_spx_return_5d"] = spx["spx_return_5d"]
    features["ext_vix"] = spx["vix_current"]
    features["ext_vix_percentile"] = spx["vix_percentile"]
    features["ext_vix_5d_change"] = spx["vix_5d_change"]
    features["ext_macro_regime"] = spx["spx_vix_regime"]

    # 4. Coinbase Premium
    prem = fetch_coinbase_premium()
    features["ext_coinbase_premium"] = prem["coinbase_premium"]

    # 5. Long/Short Ratio
    ls = fetch_long_short_ratio(symbol)
    features["ext_ls_ratio"] = ls["ls_ratio_current"]
    features["ext_ls_ratio_change"] = ls["ls_ratio_change_24h"]
    features["ext_ls_extreme"] = ls["ls_extreme"]

    # 6. Funding Rate Momentum
    fr = fetch_funding_rate_history(symbol)
    features["ext_fr_roc_8h"] = fr["fr_roc_8h"]
    features["ext_fr_roc_24h"] = fr["fr_roc_24h"]
    features["ext_fr_cumulative_24h"] = fr["fr_cumulative_24h"]
    features["ext_fr_extreme"] = fr["fr_extreme"]

    # 7. Alpha Engine Confluence (our unique edge)
    alpha = fetch_alpha_engine_confluence(symbol)
    features["ext_alpha_confluence_buy"] = alpha["alpha_confluence_buy"]
    features["ext_alpha_confluence_sell"] = alpha["alpha_confluence_sell"]
    features["ext_alpha_proven_active"] = alpha["alpha_proven_strategy_active"]
    features["ext_alpha_best_wr"] = alpha["alpha_best_strategy_wr"]

    # 8. BTC Dominance
    dom = fetch_btc_dominance()
    features["ext_btc_dominance"] = dom["btc_dominance"]
    features["ext_altcoin_dominance"] = dom["altcoin_dominance"]

    return features
