"""
ALPHA ENGINE -- 2-of-3 Ensemble Confirmation Gate
=====================================================
Requires at least 2 of 3 independent signal categories to agree on
direction before a trade is accepted.

Signal categories:
  1. Price Action Signal  -- baseline (always True for active picks)
  2. Whale / Copy Trader  -- checks if any whale has an open position
     in the same symbol + direction (from copy_trader_intel data)
  3. Market Structure     -- funding rate, OI change, or volume spike
     confirms direction via Binance fapi

Usage:
    from ensemble_gate import check_ensemble

    result = check_ensemble("BTCUSDT", "LONG")
    # result['passes']           -> True/False
    # result['signals_aligned']  -> 0-3
    # result['confidence_boost'] -> 0.0 or 0.05
    # result['details']          -> per-signal breakdown

Stdlib only.  5-mirror Binance failover.  10-min cache.
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
COPY_TRADER_DIR = os.path.join(REPO_ROOT, "copy_trader_intel", "data")

# ---------------------------------------------------------------------------
# Binance mirror failover (5 mirrors -- spot + futures)
# ---------------------------------------------------------------------------
BINANCE_SPOT_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

BINANCE_FAPI_MIRRORS = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
    "https://fapi.binance.com",   # retry primary
    "https://fapi1.binance.com",  # retry secondary
]

# ---------------------------------------------------------------------------
# Bybit v5 fallback endpoints (no geo-block, public, no auth)
# ---------------------------------------------------------------------------
BYBIT_V5_BASE = "https://api.bybit.com"
_BYBIT_INTERVAL_MAP = {
    "1h": "60", "4h": "240", "1d": "D", "5m": "5", "15m": "15",
}

# ---------------------------------------------------------------------------
# Cache (10-min TTL)
# ---------------------------------------------------------------------------
_cache: Dict[str, Tuple[float, Any]] = {}
_CACHE_TTL = 600  # 10 minutes

# Rate-limit tracker
_last_api_call = 0.0
_RATE_LIMIT_DELAY = 0.12  # 120 ms between calls

# ---------------------------------------------------------------------------
# SSL context
# ---------------------------------------------------------------------------
def _make_ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    try:
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    except Exception:
        ctx = ssl._create_unverified_context()
    return ctx


_SSL_CTX = _make_ssl_ctx()


# ---------------------------------------------------------------------------
# HTTP helpers with failover
# ---------------------------------------------------------------------------
def _rate_limit() -> None:
    global _last_api_call
    now = time.time()
    elapsed = now - _last_api_call
    if elapsed < _RATE_LIMIT_DELAY:
        time.sleep(_RATE_LIMIT_DELAY - elapsed)
    _last_api_call = time.time()


def _fetch_json(mirrors: List[str], path: str, params: str = "",
                cache_key: Optional[str] = None) -> Any:
    """
    Fetch JSON from first responding mirror.  Uses 10-min cache.
    Returns parsed JSON or None on total failure.
    """
    if cache_key:
        now = time.time()
        if cache_key in _cache:
            ts, data = _cache[cache_key]
            if now - ts < _CACHE_TTL:
                return data

    # Circuit breaker: after 3 consecutive failures for same endpoint, skip all future calls
    _ep = path.split("?")[0]
    if not hasattr(_fetch_json, '_cb'):
        _fetch_json._cb = {}
    if _fetch_json._cb.get(_ep, 0) >= 3:
        return None  # Circuit open — endpoint confirmed dead

    last_err = None
    for mirror in mirrors:
        url = f"{mirror}{path}"
        if params:
            url += f"?{params}"
        try:
            _rate_limit()
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
            with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
            if data is not None:
                if cache_key:
                    _cache[cache_key] = (time.time(), data)
                _fetch_json._cb[_ep] = 0  # Reset on success
                return data
        except Exception as exc:
            last_err = exc
            logger.debug("Mirror %s%s failed: %s", mirror, path, exc)
            continue

    _fetch_json._cb[_ep] = _fetch_json._cb.get(_ep, 0) + 1
    if _fetch_json._cb[_ep] == 3:
        logger.warning("CIRCUIT BREAKER: %s failed 3 times — skipping all future calls", _ep)
    else:
        logger.warning("All mirrors failed for %s: %s", path, last_err)
    return None


# ===================================================================
# SIGNAL 1: Price Action (baseline -- always True for active picks)
# ===================================================================
def _check_price_action(symbol: str, direction: str) -> Dict[str, Any]:
    """
    Baseline signal: the strategy already generated a pick in this
    direction, so price action agrees by definition.  Always returns
    True for active picks.
    """
    return {
        "name": "price_action",
        "agrees": True,
        "reason": f"Strategy produced active {direction} signal for {symbol}",
    }


# ===================================================================
# SIGNAL 2: Whale / Copy Trader confirmation
# ===================================================================
def _load_copy_trader_picks() -> List[Dict[str, Any]]:
    """
    Load open positions from copy trader intel data files.
    Merges active_picks.json and consensus_active_picks.json.
    """
    all_picks: List[Dict[str, Any]] = []

    # --- active_picks.json (flat list) ---
    ap_path = os.path.join(COPY_TRADER_DIR, "active_picks.json")
    try:
        with open(ap_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            all_picks.extend(data)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.debug("Could not load active_picks.json: %s", exc)

    # --- consensus_active_picks.json (has 'picks' key) ---
    cap_path = os.path.join(COPY_TRADER_DIR, "consensus_active_picks.json")
    try:
        with open(cap_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        picks = data.get("picks", []) if isinstance(data, dict) else data
        if isinstance(picks, list):
            all_picks.extend(picks)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.debug("Could not load consensus_active_picks.json: %s", exc)

    return all_picks


def _normalize_symbol(sym: str) -> str:
    """Normalize symbol: uppercase, strip common suffixes for matching."""
    s = sym.upper().strip()
    # BTC-USD -> BTCUSD, BTC/USDT -> BTCUSDT
    s = s.replace("-", "").replace("/", "")
    return s


def _check_whale_signal(symbol: str, direction: str) -> Dict[str, Any]:
    """
    Check if any copy trader whale has an open position in the same
    symbol + direction.
    """
    norm_sym = _normalize_symbol(symbol)
    direction_up = direction.upper()
    picks = _load_copy_trader_picks()

    matching_traders: List[str] = []
    for pick in picks:
        pick_sym = _normalize_symbol(pick.get("symbol", ""))
        pick_dir = (pick.get("direction", "") or "").upper()
        pick_status = (pick.get("status", "") or "").upper()

        # Only consider open positions
        if pick_status not in ("OPEN", "ACTIVE", ""):
            continue

        if pick_sym == norm_sym and pick_dir == direction_up:
            trader = pick.get("strategy", pick.get("trader_address", "unknown"))
            matching_traders.append(trader)

    agrees = len(matching_traders) > 0
    if agrees:
        reason = (f"{len(matching_traders)} whale(s) confirm {direction_up} on "
                  f"{symbol}: {', '.join(matching_traders[:3])}")
        if len(matching_traders) > 3:
            reason += f" (+{len(matching_traders) - 3} more)"
    else:
        reason = f"No whale/copy-trader positions found for {symbol} {direction_up}"

    return {
        "name": "whale_copy_trader",
        "agrees": agrees,
        "reason": reason,
        "matching_count": len(matching_traders),
    }


# ===================================================================
# SIGNAL 3: Market Structure (funding rate + OI + volume)
# ===================================================================
def _fetch_bybit_funding(symbol: str) -> Optional[dict]:
    """Fallback: fetch funding rate from Bybit v5 when Binance fapi is geo-blocked."""
    try:
        url = f"{BYBIT_V5_BASE}/v5/market/tickers?category=linear&symbol={symbol.upper()}"
        _rate_limit()
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("retCode") == 0:
            return payload["result"]["list"][0] if payload["result"]["list"] else None
    except Exception as exc:
        logger.debug("Bybit funding fallback failed for %s: %s", symbol, exc)
    return None


def _fetch_bybit_oi(symbol: str) -> Optional[dict]:
    """Fallback: fetch open interest from Bybit v5 when Binance fapi is geo-blocked."""
    try:
        url = f"{BYBIT_V5_BASE}/v5/market/open-interest?category=linear&symbol={symbol.upper()}&intervalTime=5min&limit=3"
        _rate_limit()
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("retCode") == 0:
            return payload["result"]
    except Exception as exc:
        logger.debug("Bybit OI fallback failed for %s: %s", symbol, exc)
    return None


def _fetch_bybit_klines(symbol: str, interval: str = "1h", limit: int = 3) -> Optional[list]:
    """Fallback: fetch klines from Bybit v5 when Binance spot is geo-blocked."""
    bybit_interval = _BYBIT_INTERVAL_MAP.get(interval, "60")
    try:
        url = f"{BYBIT_V5_BASE}/v5/market/kline?category=spot&symbol={symbol.upper()}&interval={bybit_interval}&limit={limit}"
        _rate_limit()
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("retCode") == 0:
            # Bybit kline format: [[startTime, open, high, low, close, volume, turnover], ...]
            # Convert to Binance-compatible: [[startTime, open, high, low, close, volume, ...], ...]
            rows = []
            for item in payload["result"]["list"]:
                rows.append([int(item[0]), item[1], item[2], item[3], item[4], item[5]])
            return rows
    except Exception as exc:
        logger.debug("Bybit kline fallback failed for %s: %s", symbol, exc)
    return None


def _check_funding_rate(symbol: str, direction: str) -> Optional[bool]:
    """
    Positive funding = SHORT bias (longs pay shorts -> overheated longs).
    Negative funding = LONG bias (shorts pay longs -> overheated shorts).
    Returns True if funding confirms direction, False if contradicts,
    None if data unavailable.
    """
    data = _fetch_json(
        BINANCE_FAPI_MIRRORS,
        "/fapi/v1/premiumIndex",
        f"symbol={symbol.upper()}",
        cache_key=f"funding_{symbol}",
    )
    if not data or not isinstance(data, dict):
        # Bybit fallback: funding rate from linear tickers
        bybit_data = _fetch_bybit_funding(symbol)
        if bybit_data and isinstance(bybit_data, dict):
            try:
                rate = float(bybit_data.get("fundingRate", 0))
            except (TypeError, ValueError):
                return None
            if abs(rate) < 0.00005:
                return None
            direction_up = direction.upper()
            if direction_up == "LONG":
                return rate < 0
            elif direction_up == "SHORT":
                return rate > 0
        return None

    try:
        rate = float(data.get("lastFundingRate", 0))
    except (TypeError, ValueError):
        return None

    # Threshold: ignore near-zero rates (noise)
    if abs(rate) < 0.00005:
        return None

    direction_up = direction.upper()
    if direction_up == "LONG":
        # Negative funding = shorts paying = LONG-friendly
        return rate < 0
    elif direction_up == "SHORT":
        # Positive funding = longs paying = SHORT-friendly
        return rate > 0
    return None


def _check_oi_change(symbol: str, direction: str) -> Optional[bool]:
    """
    Rising OI + rising price = genuine trend (LONG confirmed).
    Rising OI + falling price = genuine trend (SHORT confirmed).
    Falling OI = position unwinding, not confirmed.
    Returns True/False/None.
    """
    # Fetch recent OI snapshots (last 2 periods, 5min interval)
    data = _fetch_json(
        BINANCE_FAPI_MIRRORS,
        "/fapi/v1/openInterest",
        f"symbol={symbol.upper()}",
        cache_key=f"oi_{symbol}",
    )
    if not data or not isinstance(data, dict):
        # Bybit fallback: OI from linear open-interest endpoint
        bybit_oi = _fetch_bybit_oi(symbol)
        if bybit_oi and isinstance(bybit_oi, dict):
            try:
                current_oi = float(bybit_oi.get("openInterest", 0))
            except (TypeError, ValueError):
                return None
            if current_oi <= 0:
                return None
            # Fall through to price/kline check below with Bybit data
        else:
            return None
    else:
        try:
            current_oi = float(data.get("openInterest", 0))
        except (TypeError, ValueError):
            return None

        if current_oi <= 0:
            return None

    # Get recent price action to check if price is rising or falling
    klines = _fetch_json(
        BINANCE_SPOT_MIRRORS,
        "/api/v3/klines",
        f"symbol={symbol.upper()}&interval=1h&limit=3",
        cache_key=f"klines_1h_{symbol}",
    )
    if not klines or not isinstance(klines, list) or len(klines) < 2:
        # Bybit fallback for klines
        klines = _fetch_bybit_klines(symbol, "1h", 3)
    if not klines or not isinstance(klines, list) or len(klines) < 2:
        return None

    try:
        prev_close = float(klines[-2][4])
        curr_close = float(klines[-1][4])
    except (IndexError, TypeError, ValueError):
        return None

    price_rising = curr_close > prev_close
    direction_up = direction.upper()

    # We can't directly compare OI change from a single snapshot,
    # so we use the OI history endpoint instead
    oi_hist = _fetch_json(
        BINANCE_FAPI_MIRRORS,
        "/futures/data/openInterestHist",
        f"symbol={symbol.upper()}&period=5m&limit=3",
        cache_key=f"oi_hist_{symbol}",
    )
    if not oi_hist or not isinstance(oi_hist, list) or len(oi_hist) < 2:
        # Bybit fallback: use OI history from v5 open-interest with interval
        try:
            url = f"{BYBIT_V5_BASE}/v5/market/open-interest?category=linear&symbol={symbol.upper()}&intervalTime=5min&limit=3"
            _rate_limit()
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
            with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
                bybit_payload = json.loads(resp.read().decode("utf-8"))
            if bybit_payload.get("retCode") == 0:
                bybit_list = bybit_payload["result"]["list"]
                if bybit_list and len(bybit_list) >= 2:
                    oi_hist = [{"sumOpenInterest": item.get("openInterest", 0)} for item in bybit_list]
        except Exception:
            pass
    if oi_hist and isinstance(oi_hist, list) and len(oi_hist) >= 2:
        try:
            prev_oi = float(oi_hist[-2].get("sumOpenInterest", 0))
            curr_oi_val = float(oi_hist[-1].get("sumOpenInterest", 0))
            oi_rising = curr_oi_val > prev_oi * 1.005  # >0.5% increase
        except (TypeError, ValueError):
            return None
    else:
        # Fallback: cannot determine OI change
        return None

    if not oi_rising:
        return None  # Unwinding, no confirmation

    if direction_up == "LONG" and price_rising and oi_rising:
        return True
    elif direction_up == "SHORT" and not price_rising and oi_rising:
        return True

    return False


def _check_volume_spike(symbol: str, direction: str) -> Optional[bool]:
    """
    Check if the latest candle's volume is >= 1.5x the 20-bar average.
    Uses 1H klines.  Direction-agnostic (volume confirms momentum).
    Returns True/False/None.
    """
    klines = _fetch_json(
        BINANCE_SPOT_MIRRORS,
        "/api/v3/klines",
        f"symbol={symbol.upper()}&interval=1h&limit=21",
        cache_key=f"klines_1h_vol_{symbol}",
    )
    if not klines or not isinstance(klines, list) or len(klines) < 5:
        # Bybit fallback for volume spike klines
        klines = _fetch_bybit_klines(symbol, "1h", 21)
    if not klines or not isinstance(klines, list) or len(klines) < 5:
        return None

    try:
        volumes = [float(k[5]) for k in klines]  # index 5 = volume
    except (IndexError, TypeError, ValueError):
        return None

    if len(volumes) < 2:
        return None

    latest_vol = volumes[-1]
    avg_vol = sum(volumes[:-1]) / len(volumes[:-1])

    if avg_vol <= 0:
        return None

    return latest_vol >= avg_vol * 1.5


def _check_spot_proxy(symbol: str, direction: str) -> Optional[bool]:
    """Fallback proxy when Binance fapi funding/OI are unavailable."""
    data = _fetch_json(
        BINANCE_SPOT_MIRRORS,
        "/api/v3/ticker/24hr",
        f"symbol={symbol.upper()}",
        cache_key=f"spot_proxy_{symbol}",
    )
    if not data or not isinstance(data, dict):
        return None
    try:
        pct = float(data.get("priceChangePercent", 0))
        quote_vol = float(data.get("quoteVolume", 0))
    except (TypeError, ValueError):
        return None
    if quote_vol <= 0:
        return None
    dir_up = direction.upper()
    if abs(pct) < 0.2:
        return None
    if dir_up == "LONG":
        return pct > 0
    if dir_up == "SHORT":
        return pct < 0
    return None


def _check_market_structure(symbol: str, direction: str) -> Dict[str, Any]:
    """
    Market structure signal passes if at least ONE sub-signal confirms:
      - Funding rate confirms direction
      - OI change aligns with direction
      - Volume is >= 1.5x average
    """
    sub_signals = {}
    agrees = False

    # 1. Funding rate
    fr_result = _check_funding_rate(symbol, direction)
    sub_signals["funding_rate"] = fr_result
    if fr_result is True:
        agrees = True

    # 2. Open Interest change
    oi_result = _check_oi_change(symbol, direction)
    sub_signals["oi_change"] = oi_result
    if oi_result is True:
        agrees = True

    # 3. Volume spike
    vol_result = _check_volume_spike(symbol, direction)
    sub_signals["volume_spike"] = vol_result
    if vol_result is True:
        agrees = True
    # Fallback proxy for regions where Binance futures endpoints are blocked.
    if fr_result is None and oi_result is None:
        proxy_result = _check_spot_proxy(symbol, direction)
        sub_signals["spot_proxy"] = proxy_result
        if proxy_result is True:
            agrees = True

    # Build reason
    confirmed = [k for k, v in sub_signals.items() if v is True]
    denied = [k for k, v in sub_signals.items() if v is False]
    unavailable = [k for k, v in sub_signals.items() if v is None]

    if agrees:
        reason = f"Market structure confirmed by: {', '.join(confirmed)}"
    elif denied:
        reason = f"Market structure contradicted by: {', '.join(denied)}"
    else:
        reason = f"Market structure data unavailable: {', '.join(unavailable)}"

    return {
        "name": "market_structure",
        "agrees": agrees,
        "reason": reason,
        "sub_signals": sub_signals,
        "confirmed_by": confirmed,
    }


# ===================================================================
# Main ensemble gate
# ===================================================================
def check_ensemble(symbol: str, direction: str) -> Dict[str, Any]:
    """
    2-of-3 ensemble confirmation gate.

    Requires at least 2 of 3 independent signal categories to agree
    on direction before a trade is accepted.

    Args:
        symbol:    Trading pair (e.g. "BTCUSDT")
        direction: "LONG" or "SHORT"

    Returns:
        dict with keys:
          - signals_aligned: int (0-3)
          - passes: bool (True if >= 2)
          - details: dict with per-signal results
          - confidence_boost: float (0.0 if 2/3, +0.05 if 3/3)
    """
    symbol = symbol.upper().strip()
    direction = direction.upper().strip()

    # Collect all 3 signals
    sig_price = _check_price_action(symbol, direction)
    sig_whale = _check_whale_signal(symbol, direction)
    sig_market = _check_market_structure(symbol, direction)

    signals = [sig_price, sig_whale, sig_market]
    signals_aligned = sum(1 for s in signals if s["agrees"])

    passes = signals_aligned >= 2
    confidence_boost = 0.05 if signals_aligned == 3 else 0.0

    return {
        "signals_aligned": signals_aligned,
        "passes": passes,
        "confidence_boost": confidence_boost,
        "details": {
            "price_action": sig_price,
            "whale_copy_trader": sig_whale,
            "market_structure": sig_market,
        },
    }


def check_ensemble_batch(picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Run ensemble gate on a list of picks.  Each pick must have
    'symbol' and 'direction' keys.  Returns the picks with
    'ensemble_result' added.
    """
    results = []
    for pick in picks:
        symbol = pick.get("symbol", "")
        direction = pick.get("direction", "")
        if not symbol or not direction:
            pick["ensemble_result"] = {
                "signals_aligned": 0,
                "passes": False,
                "confidence_boost": 0.0,
                "details": {},
                "error": "Missing symbol or direction",
            }
        else:
            pick["ensemble_result"] = check_ensemble(symbol, direction)
        results.append(pick)
    return results


# ===================================================================
# run() -- test with BTCUSDT, ETHUSDT, SOLUSDT
# ===================================================================
def run() -> None:
    """Test the ensemble gate with major symbols."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    test_cases = [
        ("BTCUSDT", "LONG"),
        ("BTCUSDT", "SHORT"),
        ("ETHUSDT", "LONG"),
        ("ETHUSDT", "SHORT"),
        ("SOLUSDT", "LONG"),
        ("SOLUSDT", "SHORT"),
    ]

    print("=" * 70)
    print("ALPHA ENGINE -- 2-of-3 Ensemble Confirmation Gate")
    print("=" * 70)

    for symbol, direction in test_cases:
        result = check_ensemble(symbol, direction)
        status = "PASS" if result["passes"] else "FAIL"
        boost = result["confidence_boost"]

        print(f"\n{'~' * 60}")
        print(f"  {symbol} {direction} -> {status}  "
              f"({result['signals_aligned']}/3 aligned"
              f"{f', +{boost:.0%} boost' if boost > 0 else ''})")
        print(f"{'~' * 60}")

        for sig_name, sig_data in result["details"].items():
            icon = "[+]" if sig_data["agrees"] else "[-]"
            print(f"  {icon} {sig_name}: {sig_data['reason']}")
            if "sub_signals" in sig_data:
                for sub_k, sub_v in sig_data["sub_signals"].items():
                    label = ("confirmed" if sub_v is True
                             else "denied" if sub_v is False
                             else "n/a")
                    print(f"      {sub_k}: {label}")

    print(f"\n{'=' * 70}")
    print("Ensemble gate test complete.")


if __name__ == "__main__":
    run()
