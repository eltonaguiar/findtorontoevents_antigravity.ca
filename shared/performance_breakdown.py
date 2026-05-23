#!/usr/bin/env python3
"""
Multi-Timeframe Performance Breakdown + Trend Analysis
========================================================
Calculates 1W, 1M, 3M, YTD, 1Y performance for any symbol.
Like the TradingView Performance tab — shows how a symbol performed
over multiple timeframes with trend grading and bullish entry detection.

Also provides multi-timeframe trend analysis (Bullish/Bearish/Neutral)
across 5m, 15m, 30m, 1H, 4H, 1D, 1W timeframes using EMA crossovers
and RSI — similar to TradingView's MTF Trend Analysis panel.

Usage:
    from shared.performance_breakdown import PerformanceBreakdown
    perf = PerformanceBreakdown()
    enriched = perf.enrich_picks(picks)
"""

import json
import math
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

# ── Configuration ─────────────────────────────────────────────────────────

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
COINCAP_API = "https://api.coincap.io/v2/assets"

CACHE_TTL_MINUTES = 60  # 1h cache for price data
MAX_SYMBOLS_PER_RUN = 50  # Safety limit

# Symbol mapping: common symbol → Binance pair
BINANCE_PAIRS = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "BNB": "BNBUSDT",
    "XRP": "XRPUSDT", "ADA": "ADAUSDT", "AVAX": "AVAXUSDT", "DOT": "DOTUSDT",
    "LINK": "LINKUSDT", "NEAR": "NEARUSDT", "ATOM": "ATOMUSDT", "LTC": "LTCUSDT",
    "DOGE": "DOGEUSDT", "SHIB": "SHIBUSDT", "MATIC": "MATICUSDT", "POL": "POLUSDT",
    "TRX": "TRXUSDT", "UNI": "UNIUSDT", "AAVE": "AAVEUSDT", "MKR": "MKRUSDT",
    "GRT": "GRTUSDT", "FIL": "FILUSDT", "ETC": "ETCUSDT", "BCH": "BCHUSDT",
    "ALGO": "ALGOUSDT", "ICP": "ICPUSDT", "APT": "APTUSDT", "SUI": "SUIUSDT",
    "SEI": "SEIUSDT", "TIA": "TIAUSDT", "INJ": "INJUSDT", "RUNE": "RUNEUSDT",
    "STX": "STXUSDT", "OP": "OPUSDT", "ARB": "ARBUSDT", "FTM": "FTMUSDT",
    "CRO": "CROUSDT", "HBAR": "HBARUSDT", "VET": "VETUSDT", "XLM": "XLMUSDT",
    "EOS": "EOSUSDT", "SAND": "SANDUSDT", "MANA": "MANAUSDT", "AXS": "AXSUSDT",
    "NEO": "NEOUSDT", "KAVA": "KAVAUSDT", "QNT": "QNTUSDT", "RENDER": "RENDERUSDT",
    "FET": "FETUSDT", "TAO": "TAOUSDT", "WLD": "WLDUSDT", "JUP": "JUPUSDT",
    "PYTH": "PYTHUSDT", "JTO": "JTOUSDT", "W": "WUSDT", "PEPE": "PEPEUSDT",
    "WIF": "WIFUSDT", "BONK": "BONKUSDT", "FLOKI": "FLOKIUSDT",
    "SIREN": "SIRENUSDT", "ENSO": "ENSOUSDT", "MORPHO": "MORPHOUSDT",
    "KITE": "KITEUSDT",
}

# Non-crypto symbols we can't fetch from Binance
NON_CRYPTO_SYMBOLS = {
    "SPY", "QQQ", "GLD", "TLT", "IWM", "DIA", "VTI", "VOO",
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF",
}


class PerformanceBreakdown:
    """Multi-timeframe performance calculator."""

    def __init__(self, cache_dir=None, cache_ttl_minutes=CACHE_TTL_MINUTES):
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "price_history_cache.json"
        self.cache = self._load_cache()
        self._call_count = 0

    # ── Public API ────────────────────────────────────────────────────────

    def compute(self, symbol, current_price=None):
        """
        Compute multi-timeframe performance for a symbol.

        Returns:
            {
                "1w": {"pct": 5.2, "direction": "up"},
                "1m": {"pct": -3.1, "direction": "down"},
                "3m": {"pct": 22.0, "direction": "up"},
                "ytd": {"pct": 45.0, "direction": "up"},
                "1y": {"pct": 120.0, "direction": "up"},
                "trend_grade": "A+",
                "super_bullish": true,
                "breakout_from_downtrend": false,
                "volatility_30d": 42.5,
                "computed_at": "2026-02-20T18:00:00Z"
            }
        """
        clean = self._clean_symbol(symbol)

        # Skip non-crypto (no free API for forex/equity historical)
        if clean in NON_CRYPTO_SYMBOLS or self._is_forex(symbol):
            return None

        # Fetch daily prices (up to 365 days)
        prices = self._fetch_daily_prices(clean)
        if not prices or len(prices) < 7:
            return None

        # Use provided current_price or latest close
        latest = current_price if current_price else prices[-1]["close"]

        # Calculate each period
        performance = {}
        now = datetime.now(timezone.utc)

        periods = [
            ("1w", 7),
            ("1m", 30),
            ("3m", 90),
            ("1y", 365),
        ]

        for label, days in periods:
            result = self._calc_period(prices, latest, days)
            if result:
                performance[label] = result

        # YTD special handling
        ytd = self._calc_ytd(prices, latest)
        if ytd:
            performance["ytd"] = ytd

        if not performance:
            return None

        # Trend grade
        trend_grade = self._grade_trend(performance)

        # Super bullish detection
        super_bullish = all(
            performance.get(p, {}).get("pct", 0) > 0
            for p in ["1w", "1m", "3m", "ytd", "1y"]
            if p in performance
        ) and len(performance) >= 3

        # Breakout detection: long-term negative but short-term positive
        breakout = self._detect_breakout(performance)

        # 30-day volatility
        vol = self._calc_volatility(prices, 30)

        return {
            **performance,
            "trend_grade": trend_grade,
            "super_bullish": super_bullish,
            "breakout_from_downtrend": breakout,
            "volatility_30d": round(vol, 1) if vol else None,
            "computed_at": now.isoformat(),
        }

    def enrich_picks(self, picks):
        """Add performance_breakdown, trend_grade, super_bullish to each pick."""
        if not requests:
            print("  [PERF] requests library not available, skipping performance breakdown")
            return picks

        computed = 0
        skipped = 0
        bullish = 0

        for pick in picks:
            if self._call_count >= MAX_SYMBOLS_PER_RUN:
                print(f"  [PERF] Hit {MAX_SYMBOLS_PER_RUN} symbol limit, stopping")
                break

            symbol = pick.get("symbol", "")
            current_price = pick.get("current_price") or pick.get("entry_price")

            result = self.compute(symbol, current_price=current_price)

            if result:
                # Store full breakdown under performance_breakdown key
                pick["performance_breakdown"] = {
                    k: v for k, v in result.items()
                    if k in ("1w", "1m", "3m", "ytd", "1y")
                }
                pick["trend_grade"] = result.get("trend_grade", "?")
                pick["super_bullish"] = result.get("super_bullish", False)
                pick["breakout_from_downtrend"] = result.get("breakout_from_downtrend", False)
                pick["volatility_30d"] = result.get("volatility_30d")
                computed += 1
                if result.get("super_bullish"):
                    bullish += 1
            else:
                skipped += 1

            # Multi-timeframe trend analysis (5m through 1W)
            try:
                mtf = self.compute_mtf_trend(symbol)
                if mtf:
                    pick["mtf_trend"] = mtf
            except Exception:
                pass

        self._save_cache()
        print(f"  [PERF] {computed} computed, {skipped} skipped, {bullish} super bullish")
        return picks

    # ── Price Fetching ────────────────────────────────────────────────────

    def _fetch_daily_prices(self, symbol):
        """Fetch up to 365 daily candles from Binance. Returns list of {date, open, high, low, close, volume}."""
        # Check cache
        cache_key = f"daily_{symbol}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        # Resolve Binance pair
        pair = BINANCE_PAIRS.get(symbol.upper())
        if not pair:
            # Try appending USDT
            pair = f"{symbol.upper()}USDT"

        prices = self._fetch_binance_klines(pair, "1d", 365)

        if not prices:
            # Fallback: try CoinCap
            prices = self._fetch_coincap_history(symbol)

        if prices:
            self._set_cached(cache_key, prices)
            self._call_count += 1

        return prices

    def _fetch_binance_klines(self, pair, interval, limit):
        """Fetch klines from Binance public API."""
        if not requests:
            return None

        try:
            params = {"symbol": pair, "interval": interval, "limit": limit}
            r = requests.get(BINANCE_KLINES, params=params, timeout=10)

            if r.status_code != 200:
                return None

            data = r.json()
            if not data or not isinstance(data, list):
                return None

            prices = []
            for k in data:
                try:
                    prices.append({
                        "date": datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc).isoformat(),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                    })
                except (IndexError, ValueError, TypeError):
                    continue

            return prices if prices else None

        except Exception:
            return None

    def _fetch_coincap_history(self, symbol):
        """Fallback: fetch from CoinCap API (close-only data)."""
        if not requests:
            return None

        # CoinCap uses full names or IDs
        coincap_map = {
            "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
            "BNB": "binance-coin", "XRP": "xrp", "ADA": "cardano",
            "DOGE": "dogecoin", "DOT": "polkadot", "LINK": "chainlink",
            "AVAX": "avalanche", "LTC": "litecoin",
        }

        asset_id = coincap_map.get(symbol.upper())
        if not asset_id:
            return None

        try:
            end = int(time.time() * 1000)
            start = end - (365 * 24 * 60 * 60 * 1000)
            url = f"{COINCAP_API}/{asset_id}/history?interval=d1&start={start}&end={end}"
            r = requests.get(url, timeout=10)

            if r.status_code != 200:
                return None

            data = r.json().get("data", [])
            prices = []
            for d in data:
                try:
                    prices.append({
                        "date": datetime.fromtimestamp(d["time"] / 1000, tz=timezone.utc).isoformat(),
                        "open": float(d["priceUsd"]),
                        "high": float(d["priceUsd"]),
                        "low": float(d["priceUsd"]),
                        "close": float(d["priceUsd"]),
                        "volume": 0,
                    })
                except (KeyError, ValueError, TypeError):
                    continue

            return prices if prices else None

        except Exception:
            return None

    # ── Calculations ──────────────────────────────────────────────────────

    def _calc_period(self, prices, latest_price, days_ago):
        """Calculate % change from N days ago to latest."""
        if len(prices) < days_ago:
            return None

        # Find the price closest to N days ago
        idx = max(0, len(prices) - days_ago)
        old_price = prices[idx]["close"]

        if old_price <= 0:
            return None

        pct = ((latest_price / old_price) - 1) * 100
        direction = "up" if pct > 0.5 else ("down" if pct < -0.5 else "flat")

        return {"pct": round(pct, 2), "direction": direction}

    def _calc_ytd(self, prices, latest_price):
        """Calculate YTD performance (from Jan 1 of current year)."""
        now = datetime.now(timezone.utc)
        jan1 = datetime(now.year, 1, 1, tzinfo=timezone.utc)

        # Find closest price to Jan 1
        best_price = None
        best_diff = float("inf")

        for p in prices:
            try:
                dt = datetime.fromisoformat(p["date"].replace("Z", "+00:00"))
                diff = abs((dt - jan1).total_seconds())
                if diff < best_diff:
                    best_diff = diff
                    best_price = p["close"]
            except (ValueError, TypeError):
                continue

        if not best_price or best_price <= 0:
            return None

        pct = ((latest_price / best_price) - 1) * 100
        direction = "up" if pct > 0.5 else ("down" if pct < -0.5 else "flat")
        return {"pct": round(pct, 2), "direction": direction}

    def _calc_volatility(self, prices, window=30):
        """Calculate annualized volatility from daily returns."""
        if len(prices) < window + 1:
            return None

        recent = prices[-window:]
        returns = []
        for i in range(1, len(recent)):
            prev = recent[i - 1]["close"]
            curr = recent[i]["close"]
            if prev > 0:
                returns.append(curr / prev - 1)

        if len(returns) < 5:
            return None

        mean_r = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        daily_vol = math.sqrt(variance)

        # Annualize: daily_vol * sqrt(365) for crypto (trades every day)
        annual_vol = daily_vol * math.sqrt(365) * 100
        return annual_vol

    def _grade_trend(self, performance):
        """Grade based on how many timeframes are positive."""
        periods = ["1w", "1m", "3m", "ytd", "1y"]
        green_count = sum(
            1 for p in periods
            if performance.get(p, {}).get("pct", 0) > 0
        )
        total = sum(1 for p in periods if p in performance)

        if total == 0:
            return "?"

        ratio = green_count / total
        if ratio >= 1.0:
            return "A+"
        elif ratio >= 0.8:
            return "A"
        elif ratio >= 0.6:
            return "B"
        elif ratio >= 0.4:
            return "C"
        elif ratio >= 0.2:
            return "D"
        else:
            return "F"

    def _detect_breakout(self, performance):
        """
        Detect breakout from downtrend:
        Short-term positive (1w, 1m) but long-term negative (3m or 1y).
        """
        short_pos = (
            performance.get("1w", {}).get("pct", 0) > 0 and
            performance.get("1m", {}).get("pct", 0) > 0
        )
        long_neg = (
            performance.get("3m", {}).get("pct", 0) < 0 or
            performance.get("1y", {}).get("pct", 0) < 0
        )
        return short_pos and long_neg

    # ── Helpers ───────────────────────────────────────────────────────────

    def _clean_symbol(self, symbol):
        """Normalize symbol: 'BTCUSDT' → 'BTC', 'DEX:PEPE' → 'PEPE'."""
        s = str(symbol).upper().strip()
        if ":" in s:
            s = s.split(":", 1)[1]
        for suffix in ("USDT", "USDC", "BUSD", "USD", "BTC", "ETH", "-USD",
                        "-USDT", "=X", "/USD", "/USDT"):
            if s.endswith(suffix) and len(s) > len(suffix):
                s = s[:-len(suffix)]
                break
        return s

    def _is_forex(self, symbol):
        """Check if symbol is a forex pair."""
        s = str(symbol).upper()
        return "=X" in s or any(
            s.startswith(p) and len(s) <= 10
            for p in ("EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD")
        )

    # ── Cache ─────────────────────────────────────────────────────────────

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                pass
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, default=str)
        except Exception:
            pass

    def _get_cached(self, key):
        if key not in self.cache:
            return None
        entry = self.cache[key]
        try:
            ts = datetime.fromisoformat(entry.get("fetched_at", "2000-01-01"))
            if datetime.now(timezone.utc) - ts < self.cache_ttl:
                return entry.get("data")
        except (ValueError, TypeError):
            pass
        return None

    def _set_cached(self, key, data):
        self.cache[key] = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

    # ── Multi-Timeframe Trend Analysis ─────────────────────────────────────
    # Bullish/Bearish/Neutral per timeframe using EMA(9) vs EMA(21) crossover
    # + RSI(14) confirmation. Timeframes: 5m, 15m, 30m, 1H, 4H, 1D, 1W

    MTF_TIMEFRAMES = [
        ("5m",  "5m",  50),   # label, Binance interval, bars to fetch
        ("15m", "15m", 50),
        ("30m", "30m", 50),
        ("1H",  "1h",  50),
        ("4H",  "4h",  50),
        ("1D",  "1d",  50),
        ("1W",  "1w",  50),
    ]

    def compute_mtf_trend(self, symbol):
        """
        Compute multi-timeframe trend analysis for a symbol.

        Returns dict like:
            {
                "5m":  {"trend": "Bullish",  "strength": 72},
                "15m": {"trend": "Bearish",  "strength": 35},
                "1H":  {"trend": "Neutral",  "strength": 50},
                ...
                "overall": "Bullish",   # majority vote
                "bullish_count": 5,
                "bearish_count": 1,
                "neutral_count": 1,
            }
        """
        clean = self._clean_symbol(symbol)
        if clean in NON_CRYPTO_SYMBOLS or self._is_forex(symbol):
            return None

        pair = BINANCE_PAIRS.get(clean.upper())
        if not pair:
            pair = f"{clean.upper()}USDT"

        results = {}
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0

        for label, interval, bars in self.MTF_TIMEFRAMES:
            cache_key = f"mtf_{clean}_{interval}"
            klines = self._get_cached(cache_key)
            if klines is None:
                klines = self._fetch_binance_klines(pair, interval, bars)
                if klines:
                    self._set_cached(cache_key, klines)
                    time.sleep(0.1)  # Light rate limiting

            if not klines or len(klines) < 22:
                results[label] = {"trend": "N/A", "strength": 0}
                continue

            closes = [k["close"] for k in klines]

            # EMA(9) vs EMA(21) for trend direction
            ema9 = self._ema(closes, 9)
            ema21 = self._ema(closes, 21)

            # RSI(14) for strength/confirmation
            rsi = self._rsi(closes, 14)

            if ema9 is None or ema21 is None:
                results[label] = {"trend": "N/A", "strength": 0}
                continue

            # Trend logic: EMA crossover + RSI confirmation
            if ema9 > ema21:
                if rsi and rsi > 50:
                    trend = "Bullish"
                    strength = min(round(50 + (rsi - 50) * 1.0), 100)
                elif rsi and rsi > 40:
                    trend = "Neutral"
                    strength = 50
                else:
                    trend = "Neutral"
                    strength = 45
            elif ema9 < ema21:
                if rsi and rsi < 50:
                    trend = "Bearish"
                    strength = max(round(50 - (50 - rsi) * 1.0), 0)
                elif rsi and rsi < 60:
                    trend = "Neutral"
                    strength = 50
                else:
                    trend = "Neutral"
                    strength = 55
            else:
                trend = "Neutral"
                strength = 50

            results[label] = {"trend": trend, "strength": strength}

            if trend == "Bullish":
                bullish_count += 1
            elif trend == "Bearish":
                bearish_count += 1
            else:
                neutral_count += 1

        # Overall trend = majority vote
        if bullish_count > bearish_count and bullish_count > neutral_count:
            overall = "Bullish"
        elif bearish_count > bullish_count and bearish_count > neutral_count:
            overall = "Bearish"
        else:
            overall = "Neutral"

        results["overall"] = overall
        results["bullish_count"] = bullish_count
        results["bearish_count"] = bearish_count
        results["neutral_count"] = neutral_count

        return results

    @staticmethod
    def _ema(closes, period):
        """Calculate EMA of the last value."""
        if len(closes) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(closes[:period]) / period  # SMA seed
        for price in closes[period:]:
            ema = (price - ema) * multiplier + ema
        return ema

    @staticmethod
    def _rsi(closes, period=14):
        """Calculate RSI(14) of the last value."""
        if len(closes) < period + 1:
            return None
        gains = []
        losses = []
        for i in range(1, len(closes)):
            delta = closes[i] - closes[i - 1]
            gains.append(max(delta, 0))
            losses.append(max(-delta, 0))

        if len(gains) < period:
            return None

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - 100 / (1 + rs), 1)


# ── Standalone test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Performance Breakdown — Multi-Timeframe Test")
    print("=" * 60)

    pb = PerformanceBreakdown()

    for sym in ["BTC", "ETH", "SOL", "DOGE", "PEPE"]:
        print(f"\n  {sym}:")
        result = pb.compute(sym)
        if result:
            for period in ["1w", "1m", "3m", "ytd", "1y"]:
                if period in result:
                    d = result[period]
                    sign = "+" if d["pct"] >= 0 else ""
                    color = "GREEN" if d["direction"] == "up" else "RED" if d["direction"] == "down" else "FLAT"
                    print(f"    {period:>4}: {sign}{d['pct']:.2f}% [{color}]")
            print(f"    Grade: {result.get('trend_grade', '?')}")
            print(f"    Super Bullish: {result.get('super_bullish', False)}")
            print(f"    Breakout: {result.get('breakout_from_downtrend', False)}")
            print(f"    Vol 30d: {result.get('volatility_30d', '?')}%")
        else:
            print("    No data available")

    print("\n  Done.")
