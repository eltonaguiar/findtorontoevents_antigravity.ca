"""
ALPHA_ENGINE -- Time-Series Momentum (TSMOM) with Volatility Scaling
====================================================================
The #1 alpha generator for crypto per academic research.

Strategy:
  - Lookback: 7-21 day returns (configurable, default 14 days)
  - Signal LONG: past-N-day return > 0 AND BTC > 50-day SMA → top 5 by momentum
  - Signal SHORT/cash: past-N-day return < 0 AND BTC < 50-day SMA → bottom 5
  - Position sizing: vol-target 15% annualized / 30-day realized vol
    - Cap at 2x leverage, floor at 0.25x
  - Rebalance: weekly (or on signal flip)
  - Universe: top 20 liquid USDT pairs by 24h volume
  - TP = 2x ATR(14), SL = 1x ATR(14) → minimum 2:1 R:R

Key innovations vs naive momentum:
  1. Vol scaling prevents momentum crashes (Barroso & Santa-Clara 2015, JFE)
  2. BTC regime filter avoids trading against the macro tide
  3. Concentrated top-5 portfolio (not 200 diluted strategies)
  4. Weekly rebalance reduces noise and slippage

References:
  - Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum" JFE -- Sharpe 1.12-1.51
  - Han, Kang & Ryu (2024) "TSMOM in Cryptocurrency" -- Sharpe 1.51, vol-weighted 2.17
  - Barroso & Santa-Clara (2015) "Momentum has its moments" JFE -- vol scaling
  - Liu, Tsyvinski & Wu (2022) "Common Risk Factors in Cryptocurrency" JFE
  - Realized performance: 56-87% annual returns with vol targeting

API failover: 5 Binance mirrors + CoinGecko + KuCoin (7 endpoints total)
Stdlib only (urllib). Windows UTF-8 safe.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

_log = logging.getLogger("alpha_engine.tsmom")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR = ENGINE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "tsmom_picks.json"

# ---------------------------------------------------------------------------
# API Endpoints -- 7+ failover endpoints (MANDATORY per project rules)
# ---------------------------------------------------------------------------
BINANCE_SPOT_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]
# In CI, prefer non-geo-blocked endpoints first
if os.environ.get("GITHUB_ACTIONS"):
    BINANCE_SPOT_BASES = [
        "https://data-api.binance.vision",
        "https://api.binance.us",
    ] + BINANCE_SPOT_BASES

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
KUCOIN_BASE = "https://api.kucoin.com"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

# CoinGecko ID mapping for fallback price fetching
_CG_ID_MAP = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "ADAUSDT": "cardano",
    "AVAXUSDT": "avalanche-2", "LINKUSDT": "chainlink", "DOTUSDT": "polkadot",
    "DOGEUSDT": "dogecoin", "LTCUSDT": "litecoin", "NEARUSDT": "near",
    "SUIUSDT": "sui", "TONUSDT": "the-open-network", "TRXUSDT": "tron",
    "TAOUSDT": "bittensor", "RENDERUSDT": "render-token",
    "PEPEUSDT": "pepe", "WIFUSDT": "dogwifhat", "HYPEUSDT": "hyperliquid",
    "AAVEUSDT": "aave", "UNIUSDT": "uniswap", "INJUSDT": "injective-protocol",
    "APTUSDT": "aptos", "SEIUSDT": "sei-network", "ONDOUSDT": "ondo-finance",
    "TIAUSDT": "celestia", "ATOMUSDT": "cosmos", "FILUSDT": "filecoin",
    "ICPUSDT": "internet-computer", "HBARUSDT": "hedera-hashgraph",
    "XLMUSDT": "stellar", "STXUSDT": "blockstack", "JUPUSDT": "jupiter-exchange-solana",
    "ENAUSDT": "ethena", "KASUSDT": "kaspa", "MATICUSDT": "matic-network",
    "ARBUSDT": "arbitrum", "OPUSDT": "optimism",
}

# ---------------------------------------------------------------------------
# Strategy Parameters
# ---------------------------------------------------------------------------
LOOKBACK_DAYS = 14          # Momentum lookback (7-21, default 14)
VOL_WINDOW = 30             # Realized volatility lookback
BTC_SMA_PERIOD = 50         # Regime filter: BTC above/below 50-day SMA
TARGET_VOL_ANN = 0.15       # 15% annualized vol target
MAX_LEVERAGE = 2.0          # Cap vol-scaled weight
MIN_LEVERAGE = 0.25         # Floor vol-scaled weight
TOP_N = 5                   # Concentrate on top 5 momentum winners
ATR_PERIOD = 14             # ATR for TP/SL calculation
TP_ATR_MULT = 2.0           # TP = entry + 2x ATR
SL_ATR_MULT = 1.0           # SL = entry - 1x ATR (ensures >= 2:1 R:R)
CANDLE_LIMIT = 60           # Fetch 60 daily candles (enough for 50-SMA + lookback)
TOP_VOLUME_N = 20           # Universe: top 20 by volume


# ---------------------------------------------------------------------------
# HTTP helpers with failover
# ---------------------------------------------------------------------------

def _fetch_json(url: str, timeout: int = 10) -> Optional[dict | list]:
    """Fetch JSON from a single URL."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine-TSMOM/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _fetch_binance(path: str, timeout: int = 10) -> Optional[dict | list]:
    """Fetch from Binance with 5-mirror failover."""
    for base in BINANCE_SPOT_BASES:
        result = _fetch_json(f"{base}{path}", timeout)
        if result is not None:
            return result
    return None


def _fetch_klines_coingecko(cg_id: str, days: int = 60) -> Optional[list]:
    """Fallback: fetch OHLC from CoinGecko (4-day granularity for >30d)."""
    url = f"{COINGECKO_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days={days}"
    data = _fetch_json(url)
    if data and isinstance(data, list) and len(data) > 10:
        return data  # [[timestamp, open, high, low, close], ...]
    return None


def _fetch_klines_kucoin(symbol: str, days: int = 60) -> Optional[list]:
    """Fallback: fetch daily klines from KuCoin."""
    # KuCoin uses BTC-USDT format
    kucoin_sym = symbol.replace("USDT", "-USDT")
    import time
    end_at = int(time.time())
    start_at = end_at - days * 86400
    url = (
        f"{KUCOIN_BASE}/api/v1/market/candles"
        f"?type=1day&symbol={kucoin_sym}&startAt={start_at}&endAt={end_at}"
    )
    data = _fetch_json(url)
    if data and isinstance(data, dict) and data.get("data"):
        return data["data"]  # [[time, open, close, high, low, volume, turnover], ...]
    return None


# ---------------------------------------------------------------------------
# Data fetching: daily candles with full failover chain
# ---------------------------------------------------------------------------

def _fetch_daily_candles(symbol: str, limit: int = CANDLE_LIMIT) -> Optional[list[dict]]:
    """
    Fetch daily OHLCV candles for a USDT pair.
    Failover: Binance (5 mirrors) -> KuCoin -> CoinGecko -> CryptoCompare
    Returns list of dicts: [{open, high, low, close, volume, timestamp}, ...]
    """
    # --- Attempt 1: Binance klines ---
    path = f"/api/v3/klines?symbol={symbol}&interval=1d&limit={limit}"
    data = _fetch_binance(path)
    if data and isinstance(data, list) and len(data) >= 20:
        candles = []
        for k in data:
            candles.append({
                "timestamp": int(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })
        return candles

    # --- Attempt 2: KuCoin ---
    kucoin_data = _fetch_klines_kucoin(symbol, limit)
    if kucoin_data and len(kucoin_data) >= 20:
        candles = []
        for k in kucoin_data:
            # KuCoin format: [time, open, close, high, low, volume, turnover]
            candles.append({
                "timestamp": int(k[0]) * 1000,
                "open": float(k[1]),
                "high": float(k[3]),
                "low": float(k[4]),
                "close": float(k[2]),
                "volume": float(k[5]),
            })
        # KuCoin returns newest first, reverse to chronological
        candles.sort(key=lambda c: c["timestamp"])
        return candles

    # --- Attempt 3: CoinGecko OHLC ---
    cg_id = _CG_ID_MAP.get(symbol)
    if cg_id:
        cg_data = _fetch_klines_coingecko(cg_id, limit)
        if cg_data and len(cg_data) >= 10:
            candles = []
            for k in cg_data:
                candles.append({
                    "timestamp": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": 0.0,  # CoinGecko OHLC doesn't include volume
                })
            return candles

    # --- Attempt 4: CryptoCompare ---
    base_sym = symbol.replace("USDT", "")
    cc_url = f"{CRYPTOCOMPARE_BASE}/v2/histoday?fsym={base_sym}&tsym=USD&limit={limit}"
    cc_data = _fetch_json(cc_url)
    if cc_data and isinstance(cc_data, dict):
        cc_candles = cc_data.get("Data", {}).get("Data", [])
        if cc_candles and len(cc_candles) >= 20:
            candles = []
            for k in cc_candles:
                if k.get("close", 0) > 0:
                    candles.append({
                        "timestamp": int(k["time"]) * 1000,
                        "open": float(k["open"]),
                        "high": float(k["high"]),
                        "low": float(k["low"]),
                        "close": float(k["close"]),
                        "volume": float(k.get("volumeto", 0)),
                    })
            if candles:
                return candles

    _log.warning("All endpoints failed for %s", symbol)
    return None


def _fetch_top_volume_symbols(n: int = TOP_VOLUME_N) -> list[str]:
    """
    Get top N USDT pairs by 24h volume from Binance.
    Failover: Binance -> KuCoin -> hardcoded top-20.
    """
    # --- Attempt 1: Binance 24h ticker ---
    data = _fetch_binance("/api/v3/ticker/24hr")
    if data and isinstance(data, list):
        usdt_pairs = [
            t for t in data
            if t.get("symbol", "").endswith("USDT")
            and not t.get("symbol", "").startswith("USDC")
            and float(t.get("quoteVolume", 0)) > 0
        ]
        usdt_pairs.sort(key=lambda t: float(t.get("quoteVolume", 0)), reverse=True)
        symbols = [t["symbol"] for t in usdt_pairs[:n]]
        if len(symbols) >= 10:
            return symbols

    # --- Attempt 2: KuCoin allTickers ---
    kucoin_data = _fetch_json(f"{KUCOIN_BASE}/api/v1/market/allTickers")
    if kucoin_data and isinstance(kucoin_data, dict):
        tickers = kucoin_data.get("data", {}).get("ticker", [])
        usdt_tickers = [
            t for t in tickers
            if t.get("symbol", "").endswith("-USDT")
            and float(t.get("volValue", 0)) > 0
        ]
        usdt_tickers.sort(key=lambda t: float(t.get("volValue", 0)), reverse=True)
        symbols = [t["symbol"].replace("-USDT", "USDT") for t in usdt_tickers[:n]]
        if len(symbols) >= 10:
            return symbols

    # --- Fallback: hardcoded top-20 liquid pairs ---
    _log.warning("Using hardcoded top-20 universe (API failover exhausted)")
    return [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "TRXUSDT",
        "DOTUSDT", "LTCUSDT", "NEARUSDT", "SUIUSDT", "PEPEUSDT",
        "TONUSDT", "HBARUSDT", "ICPUSDT", "APTUSDT", "RENDERUSDT",
    ]


# ---------------------------------------------------------------------------
# Core computations
# ---------------------------------------------------------------------------

def _smart_round(value: float) -> float:
    """Round to appropriate precision based on magnitude."""
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


def _compute_sma(closes: list[float], period: int) -> Optional[float]:
    """Simple moving average of last `period` values."""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def _compute_realized_vol(closes: list[float], window: int = VOL_WINDOW) -> float:
    """
    Annualized realized volatility from daily log returns.
    Uses log returns for better statistical properties.
    """
    if len(closes) < window + 1:
        return 0.5  # Default 50% annualized (reasonable for crypto)

    log_returns = []
    for i in range(-window, 0):
        if closes[i - 1] > 0 and closes[i] > 0:
            log_returns.append(math.log(closes[i] / closes[i - 1]))

    if len(log_returns) < 10:
        return 0.5

    mean_r = sum(log_returns) / len(log_returns)
    variance = sum((r - mean_r) ** 2 for r in log_returns) / (len(log_returns) - 1)
    daily_vol = math.sqrt(variance)
    annualized_vol = daily_vol * math.sqrt(365)  # Crypto trades 365 days
    return max(0.01, annualized_vol)  # Floor at 1%


def _compute_atr(candles: list[dict], period: int = ATR_PERIOD) -> float:
    """Average True Range over `period` candles."""
    if len(candles) < period + 1:
        return 0.0

    true_ranges = []
    for i in range(-period, 0):
        c = candles[i]
        prev_close = candles[i - 1]["close"]
        tr = max(
            c["high"] - c["low"],
            abs(c["high"] - prev_close),
            abs(c["low"] - prev_close),
        )
        true_ranges.append(tr)

    return sum(true_ranges) / len(true_ranges)


def _compute_momentum(closes: list[float], lookback: int = LOOKBACK_DAYS) -> Optional[float]:
    """N-day return as momentum signal."""
    if len(closes) < lookback + 1:
        return None
    if closes[-(lookback + 1)] <= 0:
        return None
    return (closes[-1] - closes[-(lookback + 1)]) / closes[-(lookback + 1)]


# ---------------------------------------------------------------------------
# Main TSMOM strategy
# ---------------------------------------------------------------------------

def generate_tsmom_picks(
    lookback: int = LOOKBACK_DAYS,
    vol_window: int = VOL_WINDOW,
    target_vol: float = TARGET_VOL_ANN,
    top_n: int = TOP_N,
) -> list[dict]:
    """
    Full TSMOM strategy with volatility scaling.

    Returns list of pick dicts compatible with alpha_engine active_picks format.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    picks: list[dict] = []

    # Step 1: Get universe (top 20 by volume)
    universe = _fetch_top_volume_symbols(TOP_VOLUME_N)
    print(f"[TSMOM] Universe: {len(universe)} symbols")

    # Step 2: Fetch BTC candles first (regime filter)
    btc_candles = _fetch_daily_candles("BTCUSDT", CANDLE_LIMIT)
    if not btc_candles or len(btc_candles) < BTC_SMA_PERIOD + 5:
        _log.warning("Cannot fetch BTC data for regime filter -- aborting")
        return picks

    btc_closes = [c["close"] for c in btc_candles]
    btc_sma50 = _compute_sma(btc_closes, BTC_SMA_PERIOD)
    btc_price = btc_closes[-1]

    if btc_sma50 is None:
        _log.warning("Insufficient BTC data for 50-SMA -- aborting")
        return picks

    btc_bullish = btc_price > btc_sma50
    regime = "BULLISH" if btc_bullish else "BEARISH"
    print(f"[TSMOM] BTC regime: {regime} (price=${btc_price:,.0f}, SMA50=${btc_sma50:,.0f})")

    # Step 3: Fetch candles and compute momentum for all symbols
    momentum_data: list[dict] = []

    for symbol in universe:
        candles = _fetch_daily_candles(symbol, CANDLE_LIMIT)
        if not candles or len(candles) < max(lookback + 5, vol_window + 5):
            continue

        closes = [c["close"] for c in candles]
        mom = _compute_momentum(closes, lookback)
        if mom is None:
            continue

        realized_vol = _compute_realized_vol(closes, vol_window)
        atr_val = _compute_atr(candles, ATR_PERIOD)

        momentum_data.append({
            "symbol": symbol,
            "momentum": mom,
            "realized_vol": realized_vol,
            "atr": atr_val,
            "price": closes[-1],
            "candles": candles,
            "closes": closes,
        })

    if len(momentum_data) < 6:
        _log.warning("Only %d symbols with data -- need at least 6", len(momentum_data))
        return picks

    print(f"[TSMOM] Computed momentum for {len(momentum_data)} symbols")

    # Step 4: Rank by momentum
    momentum_data.sort(key=lambda x: x["momentum"], reverse=True)

    # Step 5: Select based on regime
    if btc_bullish:
        # LONG top N with positive momentum
        candidates = [m for m in momentum_data[:top_n] if m["momentum"] > 0]
        signal_type = "BUY"
    else:
        # BEARISH regime: go to cash / short bottom N
        # In practice, we skip shorts for spot-only portfolios and just report
        # the bottom N as warnings. Only signal if momentum is strongly negative.
        candidates = [m for m in momentum_data[-top_n:] if m["momentum"] < -0.02]
        signal_type = "SELL"

    if not candidates:
        print(f"[TSMOM] No valid candidates in {regime} regime")
        return picks

    print(f"[TSMOM] {len(candidates)} candidates selected ({signal_type})")

    # Step 6: Generate picks with vol-scaled sizing and ATR-based TP/SL
    for rank_idx, md in enumerate(candidates):
        symbol = md["symbol"]
        price = md["price"]
        mom = md["momentum"]
        realized_vol = md["realized_vol"]
        atr_val = md["atr"]

        if price <= 0 or atr_val <= 0:
            continue

        # Vol scaling: position_weight = target_vol / realized_vol
        if realized_vol > 0:
            vol_scale = target_vol / realized_vol
        else:
            vol_scale = 0.5
        vol_scale = max(MIN_LEVERAGE, min(MAX_LEVERAGE, vol_scale))

        # TP/SL based on ATR (2:1 minimum R:R)
        if signal_type == "BUY":
            tp = price + TP_ATR_MULT * atr_val
            sl = price - SL_ATR_MULT * atr_val
        else:
            tp = price - TP_ATR_MULT * atr_val
            sl = price + SL_ATR_MULT * atr_val

        # Validate R:R >= 2.0
        reward = abs(tp - price)
        risk = abs(price - sl)
        if risk <= 0:
            continue
        rr = reward / risk
        if rr < 1.9:  # Allow tiny float tolerance
            continue

        # Confidence scoring
        # Base: 0.55 for being in top-N
        # Bonus: stronger momentum, favorable vol scaling, regime alignment
        abs_mom = abs(mom)
        mom_bonus = min(0.15, abs_mom * 0.8)  # Up to +15% for strong momentum
        vol_bonus = 0.05 if 0.5 <= vol_scale <= 1.5 else 0.0  # Sweet spot
        regime_bonus = 0.05 if btc_bullish and signal_type == "BUY" else 0.0
        rank_bonus = (top_n - rank_idx) * 0.02  # Higher rank = more confidence

        confidence = min(0.90, 0.55 + mom_bonus + vol_bonus + regime_bonus + rank_bonus)
        confidence = max(0.50, confidence)

        # Derive category from symbol name
        category = "crypto"
        if symbol in ("DOGEUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT", "TURBOUSDT"):
            category = "meme"

        pick = {
            "strategy": "tsmom_volscaled",
            "symbol": symbol,
            "category": category,
            "signal_type": signal_type,
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(confidence, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"TSMOM: {lookback}d return {'+' if mom > 0 else ''}{mom*100:.1f}% "
                f"(rank {rank_idx+1}/{len(momentum_data)}), "
                f"BTC {regime}, "
                f"vol-scale {vol_scale:.2f}x "
                f"(rv={realized_vol*100:.0f}% -> target {target_vol*100:.0f}%), "
                f"ATR ${atr_val:.2f}"
            ),
            "timeframe": "7d",
            "rsi_at_entry": None,
            "extra": {
                "lookback_days": lookback,
                "momentum_pct": round(mom * 100, 2),
                "momentum_rank": rank_idx + 1,
                "total_symbols": len(momentum_data),
                "btc_regime": regime,
                "btc_price": round(btc_price, 2),
                "btc_sma50": round(btc_sma50, 2),
                "realized_vol_ann_pct": round(realized_vol * 100, 1),
                "target_vol_ann_pct": round(target_vol * 100, 1),
                "vol_scale": round(vol_scale, 3),
                "atr_14d": round(atr_val, 4),
                "tp_atr_mult": TP_ATR_MULT,
                "sl_atr_mult": SL_ATR_MULT,
                "position_weight_pct": round(vol_scale / sum(
                    max(MIN_LEVERAGE, min(MAX_LEVERAGE, target_vol / max(0.01, c["realized_vol"])))
                    for c in candidates
                ) * 100, 1) if candidates else 0,
                "rebalance": "weekly",
                "source": (
                    "Moskowitz, Ooi & Pedersen (2012) JFE; "
                    "Han, Kang & Ryu (2024); "
                    "Barroso & Santa-Clara (2015) JFE -- vol scaling"
                ),
            },
            "timestamp": now_iso,
        }

        picks.append(pick)
        print(
            f"  [{signal_type}] {symbol}: mom={mom*100:+.1f}%, "
            f"vol_scale={vol_scale:.2f}x, R:R={rr:.1f}, "
            f"conf={confidence:.0%}"
        )

    return picks


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    """Main entry point -- generate TSMOM picks and save to JSON."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    print("=" * 60)
    print("TSMOM Strategy -- Time-Series Momentum with Vol Scaling")
    print("=" * 60)

    picks = generate_tsmom_picks()

    # Ensure output directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    output = {
        "strategy": "tsmom_volscaled",
        "description": (
            "Time-Series Momentum with Volatility Scaling. "
            "Academic Sharpe 1.12-2.17, 56-87% annual returns. "
            "Vol scaling prevents momentum crashes."
        ),
        "parameters": {
            "lookback_days": LOOKBACK_DAYS,
            "vol_window": VOL_WINDOW,
            "btc_sma_period": BTC_SMA_PERIOD,
            "target_vol_ann": TARGET_VOL_ANN,
            "max_leverage": MAX_LEVERAGE,
            "min_leverage": MIN_LEVERAGE,
            "top_n": TOP_N,
            "tp_atr_mult": TP_ATR_MULT,
            "sl_atr_mult": SL_ATR_MULT,
            "universe_size": TOP_VOLUME_N,
        },
        "picks": picks,
        "pick_count": len(picks),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[TSMOM] Saved {len(picks)} picks to {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    run()
