"""
ALPHA_ENGINE -- Winner Pattern Precursor Strategy
=================================================
Uses HISTORICAL WINNER PATTERNS to predict the next winners.

Concept: Every hour, some crypto pumps. These pumps have precursor signals
(volume spike, RSI recovery, BB squeeze). We scan for these precursors in
REAL-TIME to catch the NEXT pump before it happens.

The Precursor Checklist (from research of 8,457 closed picks):
1. Volume acceleration 3h (current 3h vol > 2x previous 3h)  -- strongest predictor
2. RSI between 30-45 (oversold but recovering)                -- sweet spot for entry
3. Price compressed (BB width in bottom 30th pctl of 100 bars) -- coiling before expansion
4. Price above VWAP or reclaiming it                          -- institutional support
5. At least 3 of last 5 candles green                         -- momentum building
6. NOT overbought (RSI < 70)                                  -- room to run

Scoring: 1 point per precursor met (0-6). Score >= 4 => "pre-pump" candidate.
TP: 6% (average ideal TP from reverse engineering)
SL: 2.5% (tight SL -- momentum plays)
R:R: 2.4

References:
- Internal backtest of 8,457 closed picks (2024-2026)
- Bollinger (1992) "Using Bollinger Bands"
- Wilder (1978) RSI original paper
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("winner_pattern")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR = ENGINE_DIR / "data"
PRECURSOR_PICKS_PATH = DATA_DIR / "precursor_picks.json"
PRECURSOR_HISTORY_PATH = DATA_DIR / "precursor_history.json"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"

# ---------------------------------------------------------------------------
# API failover (mirrors CLAUDE.md rule: always 3+ fallback chain)
# ---------------------------------------------------------------------------
BINANCE_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]
# In CI, prefer non-geo-blocked endpoints first
if os.environ.get("GITHUB_ACTIONS"):
    _preferred = ["https://data-api.binance.vision", "https://api.binance.us"]
    BINANCE_BASES = _preferred + [u for u in BINANCE_BASES if u not in _preferred]

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
KUCOIN_BASE = "https://api.kucoin.com"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

# Rate limiting
_RATE_LIMIT_DELAY = 0.15  # seconds between API calls


def _fetch_json(url: str, timeout: int = 10) -> dict | list | None:
    """Fetch JSON with User-Agent header."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 24) -> list[dict] | None:
    """Fetch klines from Binance with full failover chain.

    Falls back to CoinGecko -> KuCoin -> CryptoCompare if all Binance mirrors fail.
    Returns list of dicts with keys: open, high, low, close, volume, timestamp.
    """
    # Try all Binance mirrors
    for base in BINANCE_BASES:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 0:
            return [
                {
                    "timestamp": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                for k in data
            ]
        time.sleep(_RATE_LIMIT_DELAY)

    # Fallback: CoinGecko (hourly OHLC for last 24h)
    cg_id = _binance_to_coingecko(symbol)
    if cg_id:
        url = f"{COINGECKO_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days=1"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) >= 10:
            return [
                {
                    "timestamp": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": 0.0,  # CoinGecko OHLC doesn't include volume
                }
                for k in data[-limit:]
            ]

    # Fallback: CryptoCompare
    base_sym = symbol.replace("USDT", "")
    url = f"{CRYPTOCOMPARE_BASE}/histohour?fsym={base_sym}&tsym=USD&limit={limit}"
    data = _fetch_json(url)
    if data and isinstance(data, dict) and data.get("Data"):
        return [
            {
                "timestamp": int(k["time"]) * 1000,
                "open": float(k["open"]),
                "high": float(k["high"]),
                "low": float(k["low"]),
                "close": float(k["close"]),
                "volume": float(k.get("volumefrom", 0)),
            }
            for k in data["Data"]
        ]

    log.warning("All API sources failed for %s", symbol)
    return None


def _fetch_top_symbols(n: int = 50) -> list[str]:
    """Get top N crypto symbols by 24h volume from Binance ticker endpoint.

    Falls back through the full chain if Binance is blocked.
    Returns list of USDT pair symbols like ['BTCUSDT', 'ETHUSDT', ...].
    """
    # Try Binance ticker/24hr
    for base in BINANCE_BASES:
        url = f"{base}/api/v3/ticker/24hr"
        data = _fetch_json(url, timeout=15)
        if data and isinstance(data, list):
            # Filter to USDT pairs, sort by quote volume
            usdt_pairs = [
                t for t in data
                if t.get("symbol", "").endswith("USDT")
                and not t.get("symbol", "").endswith("DOWNUSDT")
                and not t.get("symbol", "").endswith("UPUSDT")
                and "BUSD" not in t.get("symbol", "")
            ]
            usdt_pairs.sort(key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
            return [t["symbol"] for t in usdt_pairs[:n]]
        time.sleep(_RATE_LIMIT_DELAY)

    # Fallback: KuCoin allTickers
    url = f"{KUCOIN_BASE}/api/v1/market/allTickers"
    data = _fetch_json(url, timeout=15)
    if data and isinstance(data, dict) and data.get("data", {}).get("ticker"):
        tickers = data["data"]["ticker"]
        usdt = [t for t in tickers if t.get("symbol", "").endswith("-USDT")]
        usdt.sort(key=lambda x: float(x.get("volValue", 0)), reverse=True)
        # Convert KuCoin format (BTC-USDT) to Binance format (BTCUSDT)
        return [t["symbol"].replace("-", "") for t in usdt[:n]]

    # Fallback: CoinGecko top coins
    url = f"{COINGECKO_BASE}/coins/markets?vs_currency=usd&order=volume_desc&per_page={n}&page=1"
    data = _fetch_json(url, timeout=15)
    if data and isinstance(data, list):
        return [f"{c['symbol'].upper()}USDT" for c in data if c.get("symbol")]

    # Last resort: hardcoded majors
    log.warning("All ticker sources failed, using hardcoded top symbols")
    return [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "LINKUSDT",
        "DOTUSDT", "MATICUSDT", "SHIBUSDT", "LTCUSDT", "BCHUSDT",
        "NEARUSDT", "UNIUSDT", "APTUSDT", "FILUSDT", "ARBUSDT",
        "OPUSDT", "AAVEUSDT", "MKRUSDT", "ATOMUSDT", "ALGOUSDT",
    ]


# ---------------------------------------------------------------------------
# CoinGecko symbol mapping (for fallback)
# ---------------------------------------------------------------------------
_CG_MAP = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "BNBUSDT": "binancecoin",
    "SOLUSDT": "solana", "XRPUSDT": "ripple", "DOGEUSDT": "dogecoin",
    "ADAUSDT": "cardano", "AVAXUSDT": "avalanche-2", "TRXUSDT": "tron",
    "LINKUSDT": "chainlink", "DOTUSDT": "polkadot", "MATICUSDT": "matic-network",
    "SHIBUSDT": "shiba-inu", "LTCUSDT": "litecoin", "BCHUSDT": "bitcoin-cash",
    "NEARUSDT": "near", "UNIUSDT": "uniswap", "APTUSDT": "aptos",
    "FILUSDT": "filecoin", "ARBUSDT": "arbitrum", "OPUSDT": "optimism",
    "ATOMUSDT": "cosmos", "AAVEUSDT": "aave", "MKRUSDT": "maker",
    "TAOUSDT": "bittensor", "TONUSDT": "the-open-network",
}


def _binance_to_coingecko(symbol: str) -> str | None:
    return _CG_MAP.get(symbol)


# ---------------------------------------------------------------------------
# Pure-Python indicators (no numpy needed for 24 data points)
# ---------------------------------------------------------------------------

def _compute_rsi(closes: list[float], period: int = 14) -> float | None:
    """Compute RSI using Wilder's smoothing method."""
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

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
    return 100.0 - (100.0 / (1.0 + rs))


def _compute_bollinger(closes: list[float], period: int = 20, num_std: float = 2.0) -> dict | None:
    """Compute Bollinger Bands (SMA +/- N*stddev). Returns current width and percentile."""
    if len(closes) < period:
        return None

    # Compute BB width for last (len - period + 1) bars
    widths = []
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1 : i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = math.sqrt(variance) if variance > 0 else 0.0001
        width = (2 * num_std * std) / mean if mean > 0 else 0
        widths.append(width)

    if not widths:
        return None

    current_width = widths[-1]
    # Percentile rank of current width among recent widths (up to 100 bars)
    recent = widths[-100:] if len(widths) >= 100 else widths
    rank = sum(1 for w in recent if w <= current_width) / len(recent)

    return {"width": current_width, "percentile": rank}


def _compute_vwap(candles: list[dict]) -> float | None:
    """Compute VWAP from candle data (typical price * volume / cumulative volume)."""
    cum_tpv = 0.0
    cum_vol = 0.0
    for c in candles:
        tp = (c["high"] + c["low"] + c["close"]) / 3.0
        vol = c["volume"]
        cum_tpv += tp * vol
        cum_vol += vol
    if cum_vol == 0:
        return None
    return cum_tpv / cum_vol


# ---------------------------------------------------------------------------
# Core scanning logic
# ---------------------------------------------------------------------------

def _fetch_btc_4h_regime() -> tuple[str, float]:
    """Fetch BTC 4h regime using Binance klines with failover.

    Returns (regime, change_pct):
      "bearish" if < -1%, "bullish" if > +1%, else "neutral".
    """
    for base in BINANCE_BASES:
        try:
            url = f"{base}/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=5"
            data = _fetch_json(url)
            if data and isinstance(data, list) and len(data) >= 4:
                open_4h = float(data[0][1])
                close_now = float(data[-1][4])
                if open_4h > 0:
                    change = (close_now - open_4h) / open_4h * 100
                    if change < -1.0:
                        return "bearish", round(change, 2)
                    elif change > 1.0:
                        return "bullish", round(change, 2)
                    return "neutral", round(change, 2)
        except Exception:
            continue
        time.sleep(_RATE_LIMIT_DELAY)

    # CoinGecko fallback
    try:
        url = f"{COINGECKO_BASE}/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        data = _fetch_json(url)
        if data and "bitcoin" in data:
            approx_4h = data["bitcoin"].get("usd_24h_change", 0) / 6.0
            if approx_4h < -1.0:
                return "bearish", round(approx_4h, 2)
            elif approx_4h > 1.0:
                return "bullish", round(approx_4h, 2)
            return "neutral", round(approx_4h, 2)
    except Exception:
        pass
    return "neutral", 0.0


def scan_for_precursors(symbols: list[str] | None = None, top_n: int = 50) -> list[dict]:
    """Scan top crypto for precursor patterns that predict pumps.

    For each symbol, computes 6 precursors and assigns a score (0-6).
    Returns sorted list of candidates with score >= 4.
    """
    if symbols is None:
        log.info("Fetching top %d symbols by volume...", top_n)
        symbols = _fetch_top_symbols(top_n)
        log.info("Got %d symbols to scan", len(symbols))

    candidates = []
    scanned = 0
    failed = 0

    for symbol in symbols:
        time.sleep(_RATE_LIMIT_DELAY)
        candles = _fetch_binance_klines(symbol, interval="1h", limit=24)
        if not candles or len(candles) < 20:
            failed += 1
            continue

        scanned += 1
        closes = [c["close"] for c in candles]
        volumes = [c["volume"] for c in candles]
        current_price = closes[-1]

        # --- Precursor 1: Volume acceleration 3h ---
        # Current 3h volume > 2x previous 3h volume
        if len(volumes) >= 6:
            vol_current_3h = sum(volumes[-3:])
            vol_prev_3h = sum(volumes[-6:-3])
            vol_accel = vol_current_3h > 2.0 * vol_prev_3h if vol_prev_3h > 0 else False
            vol_ratio = (vol_current_3h / vol_prev_3h) if vol_prev_3h > 0 else 0
        else:
            vol_accel = False
            vol_ratio = 0

        # --- Precursor 2: RSI between 30-45 (oversold but recovering) ---
        rsi_val = _compute_rsi(closes, period=14)
        rsi_sweet_spot = rsi_val is not None and 30 <= rsi_val <= 45

        # --- Precursor 3: Price compressed (BB width in bottom 30th percentile) ---
        bb = _compute_bollinger(closes, period=20, num_std=2.0)
        bb_compressed = bb is not None and bb["percentile"] <= 0.30

        # --- Precursor 4: Price above VWAP or reclaiming it ---
        vwap = _compute_vwap(candles)
        above_vwap = vwap is not None and current_price >= vwap * 0.998  # within 0.2% counts as reclaiming

        # --- Precursor 5: At least 3 of last 5 candles green ---
        if len(candles) >= 5:
            green_count = sum(1 for c in candles[-5:] if c["close"] >= c["open"])
            momentum_building = green_count >= 3
        else:
            green_count = 0
            momentum_building = False

        # --- Precursor 6: NOT overbought (RSI < 70) ---
        not_overbought = rsi_val is not None and rsi_val < 70

        # --- Score ---
        precursors = {
            "volume_accel_3h": vol_accel,
            "rsi_sweet_spot": rsi_sweet_spot,
            "bb_compressed": bb_compressed,
            "above_vwap": above_vwap,
            "momentum_building": momentum_building,
            "not_overbought": not_overbought,
        }
        score = sum(1 for v in precursors.values() if v)

        # Collect feature values for transparency
        features = {
            "vol_ratio_3h": round(vol_ratio, 2),
            "rsi": round(rsi_val, 2) if rsi_val else None,
            "bb_width_pctl": round(bb["percentile"], 2) if bb else None,
            "bb_width": round(bb["width"], 4) if bb else None,
            "vwap": round(vwap, 4) if vwap else None,
            "price": round(current_price, 6),
            "green_candles_5": green_count,
        }

        if score >= 4:
            fired = [k for k, v in precursors.items() if v]
            candidates.append({
                "symbol": symbol,
                "score": score,
                "precursors": precursors,
                "fired": fired,
                "features": features,
                "current_price": current_price,
            })

    candidates.sort(key=lambda x: (-x["score"], -x["features"]["vol_ratio_3h"]))
    log.info("Scanned %d symbols (%d failed). Found %d candidates (score >= 4).",
             scanned, failed, len(candidates))
    return candidates


def generate_picks(candidates: list[dict]) -> list[dict]:
    """Generate actionable picks from precursor candidates.

    - entry_price = current close
    - take_profit = entry * 1.025 (2.5% -- calibrated to avg_mfe=2.8% from 84 closed picks)
    - stop_loss = entry * 0.985 (1.5% -- tight SL for momentum plays)
    - R:R = 1.67
    NOTE: Original TP=6%/SL=2.5% was unrealistic -- avg_mfe=2.8% meant only 8%
    of picks ever reached 6% TP, causing 64% TIME_EXPIRY exits.

    Regime awareness: In bearish regime, only emit SHORT picks or skip entirely.
    In bullish regime, emit normal BUY picks.
    """
    # Check BTC 4h regime before generating any picks
    btc_regime, btc_4h_change = _fetch_btc_4h_regime()
    if btc_regime == "bearish":
        log.warning("REGIME GATE: bearish regime detected (BTC 4h: %+.2f%%) -- skipping all LONG/BUY picks", btc_4h_change)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Load existing active picks to avoid duplicates
    existing_ids = set()
    if ACTIVE_PICKS_PATH.exists():
        try:
            active = json.loads(ACTIVE_PICKS_PATH.read_text(encoding="utf-8"))
            existing_ids = {p.get("id", "") for p in active}
        except Exception:
            pass

    picks = []
    for cand in candidates:
        # In bearish regime: skip BUY picks entirely (this strategy is LONG-only)
        if btc_regime == "bearish":
            log.info("  REGIME GATE: skipping %s BUY in bearish regime", cand["symbol"])
            continue

        entry = cand["current_price"]
        # FIX: TP=6% was unreachable (avg_mfe=2.8%, only 8% of picks hit TP).
        # Calibrated to 2.5% TP / 1.5% SL based on 84 closed picks.
        tp = round(entry * 1.025, 6)
        sl = round(entry * 0.985, 6)
        confidence = round(cand["score"] / 6.0, 3)

        # Quality gate: require 6/6 precursors (perfect score)
        # Data: 84 closed picks at 5/6 threshold had only 20% WR (-$708 PnL).
        # Raising to 6/6 to drastically reduce pick volume until WR improves.
        if cand["score"] < 6:
            log.info("  QUALITY GATE: skipping %s (score %d/6 < 6)", cand["symbol"], cand["score"])
            continue

        # Unique ID: strategy::symbol::date
        pick_id = f"winner_pattern_precursor::{cand['symbol']}::{now_str}"
        if pick_id in existing_ids:
            log.info("Skipping duplicate: %s", pick_id)
            continue

        reason = f"Precursors fired ({cand['score']}/6): {', '.join(cand['fired'])}"

        pick = {
            "id": pick_id,
            "strategy": "winner_pattern_precursor",
            "symbol": cand["symbol"],
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": round(entry, 6),
            "entry_date": now_str,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": confidence,
            "ml_score": None,
            "exit_price": None,
            "exit_date": None,
            "exit_reason": None,
            "pnl_pct": None,
            "pnl_dollar": None,
            "high_water_mark": None,
            "status": "OPEN",
            "regime_at_entry": None,
            "atr_at_entry": None,
            "rsi_at_entry": cand["features"].get("rsi"),
            "volume_ratio": cand["features"].get("vol_ratio_3h"),
            "hold_days": None,
            "allocation": 1500.0,
            "gross_tp": tp,
            "net_tp": round(tp * (1 - 0.001), 6),  # 0.1% trading fee
            "transaction_cost_pct": 0.001,
            "cost_model": 0.001,
            "position_sizing": "risk_based",
            "risk_per_trade_pct": 0.02,
            "regime_compatible": True,
            "regime_adx": None,
            "regime_volatility": None,
            "regime_trend_direction": None,
            "regime_warning": None,
            "hmm_regime": None,
            "hmm_confidence": None,
            "hmm_signal": None,
            "hmm_leverage": None,
            # Extra fields for this strategy
            "precursor_score": cand["score"],
            "precursor_reason": reason,
            "precursor_features": cand["features"],
            "scan_timestamp": now_iso,
            "regime_at_signal": btc_regime,
            "btc_4h_change_at_signal": btc_4h_change,
        }
        picks.append(pick)

    log.info("Generated %d new picks from %d candidates", len(picks), len(candidates))
    return picks


def _save_precursor_picks(picks: list[dict]) -> None:
    """Save current precursor picks to precursor_picks.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PRECURSOR_PICKS_PATH.write_text(
        json.dumps(picks, indent=2, default=str), encoding="utf-8"
    )
    log.info("Saved %d picks to %s", len(picks), PRECURSOR_PICKS_PATH)


def _append_to_history(picks: list[dict]) -> None:
    """Append picks to precursor_history.json for tracking accuracy over time."""
    history = []
    if PRECURSOR_HISTORY_PATH.exists():
        try:
            history = json.loads(PRECURSOR_HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            history = []

    history.extend(picks)

    # Keep last 2000 entries to avoid unbounded growth
    if len(history) > 2000:
        history = history[-2000:]

    PRECURSOR_HISTORY_PATH.write_text(
        json.dumps(history, indent=2, default=str), encoding="utf-8"
    )
    log.info("Appended %d picks to history (total: %d)", len(picks), len(history))


def merge_into_active_picks(picks: list[dict]) -> int:
    """Merge qualifying picks into the active_picks pipeline.

    Returns number of picks added.
    """
    if not picks:
        return 0

    active = []
    if ACTIVE_PICKS_PATH.exists():
        try:
            active = json.loads(ACTIVE_PICKS_PATH.read_text(encoding="utf-8"))
        except Exception:
            active = []

    # --- Inline quality gates ---
    STABLES = {"USDCUSDT", "USDTUSDT", "BUSDUSDT", "DAIUSDT", "FDUSDUSDT", "TUSDUSDT"}
    MIN_CONF = 0.70
    kill_list: set[str] = set()
    try:
        kl_path = DATA_DIR / "core_whitelist.json"
        if kl_path.exists():
            wl = json.loads(kl_path.read_text(encoding="utf-8"))
            _safe = set()
            for _sg in ("protected_strategies", "core_strategies", "incubator_strategies"):
                _safe.update(s.lower() for s in wl.get(_sg, []) if isinstance(s, str))
            for _ks in wl.get("kill_list", []):
                _kb = _ks.split("::", 1)[1].lower() if "::" in _ks else _ks.lower()
                if _kb not in _safe:
                    kill_list.add(_ks.lower())
                    if "::" in _ks:
                        kill_list.add(_kb)
    except Exception:
        pass

    existing_ids = {p.get("id", "") for p in active}
    added = 0
    for pick in picks:
        sym = pick.get("symbol", "")
        strat = (pick.get("strategy") or "").lower()
        conf = float(pick.get("confidence", 0) or 0)
        if conf < MIN_CONF:
            log.info("  [QUALITY GATE] Rejected %s: conf=%.2f < %.2f", sym, conf, MIN_CONF)
            continue
        if sym in STABLES:
            log.info("  [QUALITY GATE] Rejected %s: stablecoin", sym)
            continue
        if strat in kill_list:
            log.info("  [QUALITY GATE] Rejected %s: strategy '%s' in kill list", sym, strat)
            continue
        if pick["id"] not in existing_ids:
            active.append(pick)
            existing_ids.add(pick["id"])
            added += 1

    if added > 0:
        ACTIVE_PICKS_PATH.write_text(
            json.dumps(active, indent=2, default=str), encoding="utf-8"
        )
        log.info("Merged %d new picks into active_picks.json (total: %d)", added, len(active))

    return added


def main():
    """Run the winner pattern precursor scan."""
    log.info("=" * 60)
    log.info("WINNER PATTERN PRECURSOR SCANNER")
    log.info("Scanning top 50 crypto for pre-pump precursor patterns")
    log.info("=" * 60)

    # 1. Scan for precursors
    candidates = scan_for_precursors(top_n=50)

    if not candidates:
        log.info("No candidates found with score >= 4. Market may be quiet.")
        # Still save empty results
        _save_precursor_picks([])
        return

    # 2. Generate picks
    picks = generate_picks(candidates)

    # 3. Save results
    _save_precursor_picks(picks)
    _append_to_history(picks)

    # 4. Merge into active picks pipeline
    added = merge_into_active_picks(picks)

    # 5. Print summary
    log.info("")
    log.info("=" * 60)
    log.info("SCAN RESULTS")
    log.info("=" * 60)
    for p in picks:
        log.info(
            "  %s | Score %d/6 | Entry $%.4f | TP $%.4f (+6%%) | SL $%.4f (-2.5%%) | R:R 2.4",
            p["symbol"], p["precursor_score"], p["entry_price"],
            p["take_profit"], p["stop_loss"],
        )
        log.info("    Reason: %s", p["precursor_reason"])
    log.info("")
    log.info("Total candidates: %d | New picks: %d | Merged to active: %d",
             len(candidates), len(picks), added)


if __name__ == "__main__":
    main()
