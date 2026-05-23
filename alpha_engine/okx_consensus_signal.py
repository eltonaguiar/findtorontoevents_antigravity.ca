"""
OKX Top-Trader Consensus + Binance Crowd Contrarian signals.

1. okx_top_trader_consensus  — 3+ of top-10 OKX lead traders hold same direction
2. binance_crowd_contrarian  — fade extreme global long/short ratio
"""

import time
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    requests = None  # type: ignore

# ---------------------------------------------------------------------------
# Cache layer (30-min TTL, in-memory + optional disk)
# ---------------------------------------------------------------------------
_CACHE: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 1800  # 30 minutes

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _cache_key(url: str, params: dict | None = None) -> str:
    raw = url + json.dumps(params or {}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def _get_cached(key: str):
    if key in _CACHE:
        ts, data = _CACHE[key]
        if time.time() - ts < _CACHE_TTL:
            return data
    # Try disk cache
    path = os.path.join(_CACHE_DIR, f"_okx_cache_{key}.json")
    try:
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            if time.time() - mtime < _CACHE_TTL:
                with open(path, "r") as f:
                    data = json.load(f)
                _CACHE[key] = (mtime, data)
                return data
    except Exception:
        pass
    return None


def _set_cached(key: str, data):
    _CACHE[key] = (time.time(), data)
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        path = os.path.join(_CACHE_DIR, f"_okx_cache_{key}.json")
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _api_get(url: str, params: dict | None = None):
    """GET with cache, timeout, and error handling."""
    if requests is None:
        return None
    key = _cache_key(url, params)
    cached = _get_cached(key)
    if cached is not None:
        return cached
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _set_cached(key, data)
        return data
    except Exception as e:
        print(f"    [okx_consensus] API error {url}: {e}")
        return None


# ---------------------------------------------------------------------------
# Pick builder helper
# ---------------------------------------------------------------------------
def _make_pick(
    strategy: str,
    symbol: str,
    signal_type: str,
    entry_price: float,
    confidence: float,
    tp_pct: float,
    sl_pct: float,
    extra: dict | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    tp_mult = 1 + tp_pct if signal_type == "BUY" else 1 - tp_pct
    sl_mult = 1 - sl_pct if signal_type == "BUY" else 1 + sl_pct
    pick_id = f"{strategy}_{symbol}_{now.strftime('%Y%m%d%H%M')}"
    return {
        "id": pick_id,
        "strategy": strategy,
        "symbol": symbol,
        "category": "crypto",
        "signal_type": signal_type,
        "entry_price": round(entry_price, 6),
        "entry_date": now.strftime("%Y-%m-%d"),
        "take_profit": round(entry_price * tp_mult, 6),
        "stop_loss": round(entry_price * sl_mult, 6),
        "confidence": round(confidence, 3),
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
        "rsi_at_entry": None,
        "volume_ratio": None,
        "hold_days": None,
        "allocation": 1500.0,
        "gross_tp": round(entry_price * tp_mult, 6),
        "net_tp": round(entry_price * tp_mult * (1 - 0.001), 6),
        "transaction_cost_pct": 0.001,
        "cost_model": 0.001,
        "position_sizing": "fixed",
        "risk_per_trade_pct": sl_pct,
        "regime_compatible": True,
        "regime_adx": None,
        "regime_volatility": None,
        "regime_trend_direction": None,
        "regime_warning": None,
        "hmm_regime": None,
        "hmm_confidence": None,
        "hmm_signal": None,
        "hmm_leverage": None,
        "source_system": "alpha_engine",
        "created_at": now.isoformat(),
        "forward_validated": False,
        "forward_status": None,
        "extra": extra or {},
    }


# ---------------------------------------------------------------------------
# Normalize OKX instId → unified symbol  e.g. BTC-USDT-SWAP → BTCUSDT
# ---------------------------------------------------------------------------
def _normalize_symbol(inst_id: str) -> str:
    parts = inst_id.replace("-SWAP", "").replace("-FUTURES", "").split("-")
    return "".join(parts).upper()


# ---------------------------------------------------------------------------
# Strategy 1: OKX Top Trader Consensus
# ---------------------------------------------------------------------------
MIN_TRADERS_CONSENSUS = 3
MAX_CONSENSUS_PICKS = 5


def okx_top_trader_consensus(data=None, **kwargs) -> list[dict]:
    """
    Query OKX public copy-trading API for top lead traders and find
    consensus positions (3+ traders same direction on same symbol).
    """
    picks: list[dict] = []

    # Step 1: Get top lead traders
    traders_resp = _api_get(
        "https://www.okx.com/api/v5/copytrading/public-lead-traders",
        params={"instType": "SWAP"},
    )
    if not traders_resp or traders_resp.get("code") != "0":
        print("    [okx_consensus] Could not fetch lead traders")
        return []

    traders = (traders_resp.get("data") or [])[:10]
    if not traders:
        print("    [okx_consensus] No traders returned")
        return []

    # Step 2: Get current positions for each trader
    # Aggregate: symbol -> { "LONG": [(trader_name, leverage)], "SHORT": [...] }
    consensus_map: dict[str, dict[str, list[tuple[str, float, float]]]] = {}

    for trader in traders:
        unique_code = trader.get("uniqueCode", "")
        trader_name = trader.get("nickName", unique_code[:8])
        if not unique_code:
            continue

        time.sleep(1)  # Rate-limit: 1s between trader queries

        pos_resp = _api_get(
            "https://www.okx.com/api/v5/copytrading/public-current-subpositions",
            params={"instType": "SWAP", "uniqueCode": unique_code},
        )
        if not pos_resp or pos_resp.get("code") != "0":
            continue

        positions = pos_resp.get("data") or []
        for pos in positions:
            inst_id = pos.get("instId", "")
            direction = pos.get("posSide", "").upper()
            if direction not in ("LONG", "SHORT"):
                # Try subPos direction
                sub_pos = pos.get("subPos", "")
                if sub_pos:
                    direction = "LONG" if float(sub_pos) > 0 else "SHORT"
                else:
                    continue

            symbol = _normalize_symbol(inst_id)
            leverage = float(pos.get("lever", 1) or 1)
            avg_px = float(pos.get("openAvgPx", 0) or pos.get("avgPx", 0) or 0)

            if symbol not in consensus_map:
                consensus_map[symbol] = {"LONG": [], "SHORT": []}
            consensus_map[symbol][direction].append((trader_name, leverage, avg_px))

    # Step 3: Find consensus (3+ traders same direction)
    consensus_candidates = []
    for symbol, dirs in consensus_map.items():
        for direction, entries in dirs.items():
            if len(entries) >= MIN_TRADERS_CONSENSUS:
                consensus_candidates.append((symbol, direction, entries))

    # Sort by number of agreeing traders (descending)
    consensus_candidates.sort(key=lambda x: len(x[2]), reverse=True)

    for symbol, direction, entries in consensus_candidates[:MAX_CONSENSUS_PICKS]:
        num_traders = len(entries)
        trader_names = [e[0] for e in entries]
        avg_leverage = round(sum(e[1] for e in entries) / num_traders, 2)
        avg_entry = sum(e[2] for e in entries if e[2] > 0)
        count_with_price = sum(1 for e in entries if e[2] > 0)
        entry_price = (avg_entry / count_with_price) if count_with_price > 0 else 0

        if entry_price <= 0:
            # Try to get current price from data dict
            if data and symbol in data:
                try:
                    entry_price = float(data[symbol]["close"].iloc[-1])
                except Exception:
                    pass
            if entry_price <= 0:
                continue

        # Confidence: 0.65 + 0.05 * (n - 3), capped at 0.85
        confidence = min(0.85, 0.65 + 0.05 * (num_traders - 3))
        signal_type = "BUY" if direction == "LONG" else "SELL"

        pick = _make_pick(
            strategy="okx_top_trader_consensus",
            symbol=symbol,
            signal_type=signal_type,
            entry_price=entry_price,
            confidence=confidence,
            tp_pct=0.06,
            sl_pct=0.03,
            extra={
                "num_traders": num_traders,
                "trader_names": trader_names,
                "avg_leverage": avg_leverage,
                "consensus_direction": direction,
            },
        )
        picks.append(pick)

    if picks:
        print(f"    [okx_consensus] {len(picks)} consensus pick(s)")
    return picks


# ---------------------------------------------------------------------------
# Strategy 2: Binance Crowd Contrarian
# ---------------------------------------------------------------------------
_CONTRARIAN_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT"]
_LS_EXTREME_LONG = 2.0   # crowd too long → SHORT (relaxed from 2.5)
_LS_EXTREME_SHORT = 0.6  # crowd too short → LONG (relaxed from 0.5)


def binance_crowd_contrarian(data=None, **kwargs) -> list[dict]:
    """
    Fade extreme Binance global long/short account ratio.
    L/S > 2.5 → SHORT contrarian signal
    L/S < 0.5 → LONG contrarian signal
    """
    picks: list[dict] = []

    for symbol in _CONTRARIAN_SYMBOLS:
        # Binance API failover chain per project rules
        ls_data = None
        urls = [
            f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio",
            f"https://fapi1.binance.com/futures/data/globalLongShortAccountRatio",
            f"https://fapi2.binance.com/futures/data/globalLongShortAccountRatio",
        ]
        for url in urls:
            ls_data = _api_get(url, params={
                "symbol": symbol,
                "period": "1d",
                "limit": "1",
            })
            if ls_data and isinstance(ls_data, list) and len(ls_data) > 0:
                break

        if not ls_data or not isinstance(ls_data, list) or len(ls_data) == 0:
            continue

        try:
            ratio = float(ls_data[0].get("longShortRatio", 1.0))
        except (ValueError, KeyError, TypeError):
            continue

        signal_type = None
        if ratio > _LS_EXTREME_LONG:
            signal_type = "SELL"  # Crowd too long, fade it
        elif ratio < _LS_EXTREME_SHORT:
            signal_type = "BUY"  # Crowd too short, fade it
        else:
            continue

        # Get current price
        entry_price = 0.0
        if data and symbol in data:
            try:
                entry_price = float(data[symbol]["close"].iloc[-1])
            except Exception:
                pass
        if entry_price <= 0:
            # Fallback: fetch from Binance
            ticker = _api_get(
                "https://fapi.binance.com/fapi/v1/ticker/price",
                params={"symbol": symbol},
            )
            if ticker and "price" in ticker:
                try:
                    entry_price = float(ticker["price"])
                except (ValueError, TypeError):
                    pass
        if entry_price <= 0:
            continue

        # Confidence: scale 0.66-0.77 by how extreme the ratio is (lowered due to relaxed thresholds)
        if signal_type == "SELL":
            # ratio > 2.0: more extreme = higher confidence
            conf = min(0.77, 0.66 + 0.02 * (ratio - _LS_EXTREME_LONG))
        else:
            # ratio < 0.6: smaller = more extreme
            conf = min(0.77, 0.66 + 0.02 * (_LS_EXTREME_SHORT - ratio))
        conf = max(0.66, conf)

        pick = _make_pick(
            strategy="binance_crowd_contrarian",
            symbol=symbol,
            signal_type=signal_type,
            entry_price=entry_price,
            confidence=round(conf, 3),
            tp_pct=0.05,
            sl_pct=0.03,
            extra={
                "long_short_ratio": round(ratio, 4),
                "extreme_type": "crowd_too_long" if signal_type == "SELL" else "crowd_too_short",
                "period": "1d",
            },
        )
        picks.append(pick)

    if picks:
        print(f"    [binance_contrarian] {len(picks)} contrarian pick(s)")
    return picks


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------
def run_okx_binance_signals(data=None, **kwargs) -> list[dict]:
    """Run both OKX consensus and Binance contrarian strategies."""
    all_picks: list[dict] = []
    try:
        all_picks.extend(okx_top_trader_consensus(data=data, **kwargs))
    except Exception as e:
        print(f"    [okx_consensus] error: {e}")
    try:
        all_picks.extend(binance_crowd_contrarian(data=data, **kwargs))
    except Exception as e:
        print(f"    [binance_contrarian] error: {e}")
    return all_picks


if __name__ == "__main__":
    picks = run_okx_binance_signals()
    print(f"\nTotal picks: {len(picks)}")
    for p in picks:
        print(f"  {p['strategy']} | {p['symbol']} | {p['signal_type']} | conf={p['confidence']}")
