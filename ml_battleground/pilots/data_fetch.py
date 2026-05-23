"""
Shared data fetcher for pilot projects with Binance → CoinGecko → Yahoo fallback.
GitHub Actions runners in the US get 451 from Binance, so we need alternatives.
"""
import requests
import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta


def fetch_crypto_daily(symbol="BTCUSDT", days=365):
    """Fetch daily crypto OHLCV. Tries Binance, then CoinGecko, then Yahoo."""
    # Map symbol to CoinGecko/Yahoo IDs
    COIN_MAP = {
        "BTCUSDT": ("bitcoin", "BTC-USD"),
        "ETHUSDT": ("ethereum", "ETH-USD"),
        "SOLUSDT": ("solana", "SOL-USD"),
        "BNBUSDT": ("binancecoin", "BNB-USD"),
        "XRPUSDT": ("ripple", "XRP-USD"),
        "DOGEUSDT": ("dogecoin", "DOGE-USD"),
        "ADAUSDT": ("cardano", "ADA-USD"),
        "AVAXUSDT": ("avalanche-2", "AVAX-USD"),
        "LINKUSDT": ("chainlink", "LINK-USD"),
        "TAOUSDT": ("bittensor", "TAO-USD"),
        "NEARUSDT": ("near", "NEAR-USD"),
        "RENDERUSDT": ("render-token", "RNDR-USD"),
    }

    # Try 1: Binance
    df = _try_binance_klines(symbol, "1d", min(days, 1000))
    if df is not None and len(df) >= 30:
        return df

    cg_id, yahoo_id = COIN_MAP.get(symbol, (None, None))

    # Try 2: CoinGecko (no API key needed for /market_chart)
    if cg_id:
        df = _try_coingecko_daily(cg_id, days)
        if df is not None and len(df) >= 30:
            return df

    # Try 3: Yahoo Finance
    if yahoo_id:
        df = _try_yahoo_daily(yahoo_id, days)
        if df is not None and len(df) >= 30:
            return df

    print(f"  [ERROR] All data sources failed for {symbol}")
    return None


def fetch_crypto_hourly(symbol="BTCUSDT", hours=500):
    """Fetch hourly crypto OHLCV. Tries Binance, then Yahoo (1h)."""
    YAHOO_MAP = {
        "BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD", "SOLUSDT": "SOL-USD",
        "BNBUSDT": "BNB-USD", "XRPUSDT": "XRP-USD", "DOGEUSDT": "DOGE-USD",
        "ADAUSDT": "ADA-USD", "AVAXUSDT": "AVAX-USD", "LINKUSDT": "LINK-USD",
        "TAOUSDT": "TAO-USD", "NEARUSDT": "NEAR-USD", "RENDERUSDT": "RNDR-USD",
    }

    # Try 1: Binance
    df = _try_binance_klines(symbol, "1h", min(hours, 1000))
    if df is not None and len(df) >= 50:
        return df

    # Try 2: Yahoo Finance (hourly, max ~7 days)
    yahoo_id = YAHOO_MAP.get(symbol)
    if yahoo_id:
        df = _try_yahoo_hourly(yahoo_id, min(hours, 168))  # Yahoo max ~7d hourly
        if df is not None and len(df) >= 20:
            return df

    print(f"  [ERROR] All hourly sources failed for {symbol}")
    return None


def fetch_funding_rates(symbol, limit=100):
    """Fetch funding rates from Binance Futures. Falls back to synthetic estimate."""
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    params = {"symbol": symbol, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return [{"time": r["fundingTime"], "rate": float(r["fundingRate"])} for r in data]
    except Exception:
        pass

    # Fallback: estimate funding from spot price momentum
    # High momentum → likely positive funding (longs paying shorts)
    df = fetch_crypto_daily(symbol, days=60)
    if df is None or len(df) < 14:
        return []

    print(f"  [INFO] Using synthetic funding estimate for {symbol}")
    rates = []
    returns_7d = df["Close"].pct_change(7).dropna()
    for i, (ts, ret) in enumerate(returns_7d.items()):
        # Approximate: strong uptrend → positive funding, downtrend → negative
        synthetic_rate = float(ret) * 0.002  # Scale down heavily
        synthetic_rate = max(-0.001, min(0.003, synthetic_rate))  # Cap at realistic range
        rates.append({
            "time": int(ts.timestamp() * 1000) if hasattr(ts, 'timestamp') else int(time.time() * 1000),
            "rate": synthetic_rate
        })
    return rates


def _try_binance_klines(symbol, interval, limit):
    """Try Binance klines API."""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data, columns=[
            "timestamp", "Open", "High", "Low", "Close", "Volume",
            "close_time", "qav", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = df[col].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception as e:
        print(f"  [WARN] Binance {symbol} {interval}: {e}")
        return None


def _try_coingecko_daily(coin_id, days):
    """Try CoinGecko /market_chart (no API key needed)."""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        prices = data.get("prices", [])
        volumes = data.get("total_volumes", [])
        if not prices:
            return None

        df = pd.DataFrame(prices, columns=["timestamp", "Close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        # CoinGecko doesn't give OHLC on market_chart, approximate
        df["Open"] = df["Close"].shift(1).fillna(df["Close"])
        df["High"] = df["Close"] * 1.01  # Approximate
        df["Low"] = df["Close"] * 0.99
        if volumes:
            vol_df = pd.DataFrame(volumes, columns=["timestamp", "Volume"])
            vol_df["timestamp"] = pd.to_datetime(vol_df["timestamp"], unit="ms")
            vol_df.set_index("timestamp", inplace=True)
            df = df.join(vol_df, how="left")
        else:
            df["Volume"] = 0

        print(f"  [INFO] Using CoinGecko data for {coin_id} ({len(df)} days)")
        return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception as e:
        print(f"  [WARN] CoinGecko {coin_id}: {e}")
        return None


def _try_yahoo_daily(ticker, days):
    """Try Yahoo Finance daily data (no API key needed)."""
    end = int(time.time())
    start = end - (days * 86400)
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={start}&period2={end}&interval=1d")
    return _parse_yahoo(url, ticker)


def _try_yahoo_hourly(ticker, hours):
    """Try Yahoo Finance hourly data."""
    end = int(time.time())
    start = end - (hours * 3600)
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={start}&period2={end}&interval=1h")
    return _parse_yahoo(url, ticker)


def _parse_yahoo(url, ticker):
    """Parse Yahoo Finance API response into DataFrame."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]

        df = pd.DataFrame({
            "timestamp": pd.to_datetime(timestamps, unit="s"),
            "Open": quotes["open"],
            "High": quotes["high"],
            "Low": quotes["low"],
            "Close": quotes["close"],
            "Volume": quotes["volume"],
        })
        df.set_index("timestamp", inplace=True)
        df = df.dropna(subset=["Close"])
        print(f"  [INFO] Using Yahoo Finance data for {ticker} ({len(df)} bars)")
        return df
    except Exception as e:
        print(f"  [WARN] Yahoo {ticker}: {e}")
        return None
