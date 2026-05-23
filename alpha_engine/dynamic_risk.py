"""
ALPHA_ENGINE -- Dynamic Risk Sizing (Phase 2.3)
================================================
ATR-based TP/SL adjustments and half-Kelly position sizing for active picks.

Computes:
  1. ATR(14) levels for dynamic TP/SL (2.5x ATR reward, 1.5x ATR risk)
  2. Half-Kelly fraction from strategy performance (capped 1-25%)
  3. Volatility-adjusted position sizing (scale down in high-vol, up in low-vol)

Designed to enrich picks in-place after elite scoring and before writing
premium_signals.json. All operations are try/except wrapped so failures
never break the production pipeline.

References:
  - Wilder (1978): ATR
  - Kelly (1956): Optimal bet sizing
  - Thorp (2006): Half-Kelly as conservative practical variant
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import requests

# Ensure alpha_engine is on path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CRYPTO_SYMBOLS

# Binance endpoints with failover (same pattern as production_scanner.py)
try:
    from config import BINANCE_BASE, BINANCE_FALLBACK_URLS
    _SPOT_BASES = [BINANCE_BASE] + BINANCE_FALLBACK_URLS
except ImportError:
    _SPOT_BASES = ["https://api.binance.com"]

HTTP_TIMEOUT = 10


# ---------------------------------------------------------------------------
# Internal: Fetch OHLCV from Binance klines (for picks missing atr_at_entry)
# ---------------------------------------------------------------------------

def _yf_to_binance_map() -> dict[str, str]:
    """Build yfinance ticker -> Binance symbol map from config."""
    return {
        yf_ticker: meta["binance"]
        for yf_ticker, meta in CRYPTO_SYMBOLS.items()
        if "binance" in meta
    }


def _fetch_binance_klines(binance_symbol: str, interval: str = "1d",
                          limit: int = 20) -> list[dict] | None:
    """Fetch recent klines from Binance for ATR computation.

    Returns list of dicts with keys: high, low, close -- or None on failure.
    """
    for base in _SPOT_BASES:
        try:
            r = requests.get(
                f"{base}/api/v3/klines",
                params={"symbol": binance_symbol, "interval": interval, "limit": limit},
                timeout=HTTP_TIMEOUT,
            )
            if r.status_code in (451, 403):
                continue
            r.raise_for_status()
            rows = r.json()
            return [
                {"high": float(row[2]), "low": float(row[3]), "close": float(row[4])}
                for row in rows
            ]
        except Exception:
            continue
    return None


def _compute_atr_from_klines(klines: list[dict], period: int = 14) -> float | None:
    """Compute ATR(period) from kline dicts using Wilder smoothing.

    Each kline dict must have keys: high, low, close.
    Returns the latest ATR value, or None if insufficient data.
    """
    if not klines or len(klines) < period + 1:
        return None

    # Compute true ranges
    true_ranges = []
    for i in range(1, len(klines)):
        h = klines[i]["high"]
        l = klines[i]["low"]
        prev_c = klines[i - 1]["close"]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    # Wilder smoothing: first ATR is simple average, then EMA with alpha=1/period
    atr_val = sum(true_ranges[:period]) / period
    alpha = 1.0 / period
    for tr in true_ranges[period:]:
        atr_val = atr_val * (1 - alpha) + tr * alpha

    return atr_val


def _get_atr_for_pick(pick: dict, _binance_map: dict[str, str] | None = None,
                      _kline_cache: dict[str, list[dict]] | None = None) -> float | None:
    """Get ATR(14) for a pick -- from pick field, or by fetching Binance klines.

    Priority:
      1. pick["atr_at_entry"] if present and > 0
      2. Fetch Binance klines and compute inline
    """
    # 1. Already on the pick
    atr_val = pick.get("atr_at_entry")
    if atr_val and float(atr_val) > 0:
        return float(atr_val)

    # 2. Fetch from Binance
    if _binance_map is None:
        _binance_map = _yf_to_binance_map()
    symbol = pick.get("symbol", "")
    binance_sym = _binance_map.get(symbol)
    if not binance_sym:
        return None

    # Use cache to avoid duplicate API calls for same symbol
    if _kline_cache is not None and binance_sym in _kline_cache:
        klines = _kline_cache[binance_sym]
    else:
        klines = _fetch_binance_klines(binance_sym, interval="1d", limit=20)
        if _kline_cache is not None and klines:
            _kline_cache[binance_sym] = klines

    if not klines:
        return None

    return _compute_atr_from_klines(klines, period=14)


# ---------------------------------------------------------------------------
# 1. ATR-based TP/SL levels
# ---------------------------------------------------------------------------

def compute_atr_levels(symbol: str, pick: dict, entry_price: float,
                       direction: str = "LONG",
                       atr_tp_mult: float = 2.5,
                       atr_sl_mult: float = 1.5,
                       atr_value: float | None = None) -> dict | None:
    """Compute ATR-based TP/SL for a pick.

    Args:
        symbol: Trading symbol (e.g. "BTC-USD")
        pick: The pick dict (used to extract atr_at_entry)
        entry_price: Entry price
        direction: "LONG" or "SHORT"
        atr_tp_mult: ATR multiplier for take-profit (default 2.5)
        atr_sl_mult: ATR multiplier for stop-loss (default 1.5)
        atr_value: Pre-computed ATR value (if None, extracted from pick)

    Returns:
        Dict with atr, atr_tp, atr_sl, atr_rr -- or None if ATR unavailable.
    """
    atr_val = atr_value if atr_value and atr_value > 0 else None
    if atr_val is None:
        atr_val = pick.get("atr_at_entry")
        if atr_val:
            atr_val = float(atr_val)
    if not atr_val or atr_val <= 0:
        return None

    if direction.upper() == "SHORT":
        tp = entry_price - atr_tp_mult * atr_val
        sl = entry_price + atr_sl_mult * atr_val
    else:
        tp = entry_price + atr_tp_mult * atr_val
        sl = entry_price - atr_sl_mult * atr_val

    return {
        "atr": round(atr_val, 8),
        "atr_tp": round(tp, 8),
        "atr_sl": round(sl, 8),
        "atr_rr": round(atr_tp_mult / atr_sl_mult, 4),
    }


# ---------------------------------------------------------------------------
# 2. Half-Kelly position sizing
# ---------------------------------------------------------------------------

def compute_half_kelly(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Compute half-Kelly fraction for conservative position sizing.

    Kelly fraction = (WR * avg_win - (1 - WR) * avg_loss) / avg_win
    Half-Kelly = Kelly / 2

    Args:
        win_rate: Win rate (0-1)
        avg_win: Average winning trade magnitude (positive, e.g. 2.5 for 2.5%)
        avg_loss: Average losing trade magnitude (positive, e.g. 1.5 for 1.5%)

    Returns:
        Fraction between 0.01 (1%) and 0.25 (25%).
    """
    avg_win = abs(avg_win)
    avg_loss = abs(avg_loss)

    if avg_win <= 0:
        return 0.01  # Floor

    kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    half_kelly = kelly / 2.0

    # Clamp to [0.01, 0.25]
    return max(0.01, min(0.25, half_kelly))


# ---------------------------------------------------------------------------
# 3. Volatility-adjusted position size
# ---------------------------------------------------------------------------

def compute_vol_adjusted_size(atr: float, price: float,
                              base_risk_pct: float = 0.02) -> float:
    """Compute volatility-adjusted risk fraction.

    Scales position size inversely with volatility:
      ATR% > 5%  (very volatile): 0.5x base
      ATR% 3-5%  (volatile):      0.75x base
      ATR% 1-3%  (normal):        1.0x base
      ATR% < 1%  (quiet):         1.25x base

    Args:
        atr: ATR(14) value in price units
        price: Current/entry price
        base_risk_pct: Base risk as fraction of equity (default 2%)

    Returns:
        Adjusted risk fraction (e.g. 0.01 to 0.025).
    """
    if price <= 0 or atr <= 0:
        return base_risk_pct

    atr_pct = atr / price * 100  # Convert to percentage

    if atr_pct > 5.0:
        multiplier = 0.50
    elif atr_pct > 3.0:
        multiplier = 0.75
    elif atr_pct > 1.0:
        multiplier = 1.00
    else:
        multiplier = 1.25

    return round(base_risk_pct * multiplier, 6)


# ---------------------------------------------------------------------------
# 4. Main enrichment function
# ---------------------------------------------------------------------------

def enrich_picks_with_dynamic_risk(
    picks: list[dict],
    strategy_perf: dict | None = None,
) -> list[dict]:
    """Enrich active picks with ATR-based dynamic TP/SL and half-Kelly sizing.

    For each pick:
      - Compute ATR levels (dynamic TP/SL)
      - Compute half-Kelly fraction if strategy has performance data
      - Compute volatility-adjusted position size
      - Add fields: dynamic_tp, dynamic_sl, dynamic_rr, kelly_fraction,
        vol_adj_size, atr_pct

    All errors are caught per-pick so one failure doesn't block others.

    Args:
        picks: List of active pick dicts (mutated in-place)
        strategy_perf: Strategy performance dict (strategy_name -> stats)
            Each strategy stats dict should have: win_rate, avg_win_pct,
            avg_loss_pct, closed_picks

    Returns:
        The same picks list (mutated in-place for convenience).
    """
    if not picks:
        return picks

    strategy_perf = strategy_perf or {}
    enriched = 0
    errors = 0

    # Build Binance symbol map and kline cache once
    binance_map = _yf_to_binance_map()
    kline_cache: dict[str, list[dict]] = {}

    for pick in picks:
        try:
            entry_price = pick.get("entry_price") or 0
            if not entry_price or entry_price <= 0:
                continue

            symbol = pick.get("symbol", "")
            direction = pick.get("direction") or (
                "SHORT" if pick.get("signal_type", "BUY").upper() in ("SELL", "SHORT")
                else "LONG"
            )
            strategy = pick.get("strategy", "")

            # --- Get ATR ---
            atr_val = _get_atr_for_pick(pick, binance_map, kline_cache)
            if not atr_val or atr_val <= 0:
                continue

            # --- ATR levels ---
            levels = compute_atr_levels(
                symbol=symbol,
                pick=pick,
                entry_price=entry_price,
                direction=direction,
                atr_value=atr_val,
            )
            if levels:
                pick["dynamic_tp"] = levels["atr_tp"]
                pick["dynamic_sl"] = levels["atr_sl"]
                pick["dynamic_rr"] = levels["atr_rr"]

            # --- ATR as % of price ---
            atr_pct = round(atr_val / entry_price * 100, 4)
            pick["atr_pct"] = atr_pct

            # --- Half-Kelly from strategy performance ---
            strat_stats = strategy_perf.get(strategy, {})
            closed_picks = strat_stats.get("closed_picks", 0)
            if closed_picks >= 5:
                wr = strat_stats.get("win_rate", 0.5)
                avg_win = abs(strat_stats.get("avg_win_pct", 2.0))
                avg_loss = abs(strat_stats.get("avg_loss_pct", 2.0))
                kelly_frac = compute_half_kelly(wr, avg_win, avg_loss)
            else:
                # Not enough data -- use conservative default
                kelly_frac = 0.01
            pick["kelly_fraction"] = round(kelly_frac, 4)

            # --- Vol-adjusted sizing ---
            vol_adj = compute_vol_adjusted_size(atr_val, entry_price)
            pick["vol_adj_size"] = round(vol_adj, 6)

            # Backfill atr_at_entry if missing
            if not pick.get("atr_at_entry"):
                pick["atr_at_entry"] = round(atr_val, 8)

            enriched += 1

        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  [RISK] Error enriching {pick.get('symbol', '?')}: {e}")

    print(f"  [RISK] Dynamic risk: enriched {enriched}/{len(picks)} picks"
          f"{f' ({errors} errors)' if errors else ''}")
    return picks


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  Dynamic Risk Sizing -- Self-Test")
    print("=" * 60)

    # Test 1: ATR levels (LONG)
    mock_pick = {"atr_at_entry": 2500.0}
    levels = compute_atr_levels("BTC-USD", mock_pick, entry_price=85000.0,
                                direction="LONG")
    assert levels is not None
    assert levels["atr_tp"] == 85000.0 + 2.5 * 2500.0  # 91250
    assert levels["atr_sl"] == 85000.0 - 1.5 * 2500.0  # 81250
    assert abs(levels["atr_rr"] - 1.6667) < 0.001
    print(f"\n  LONG BTC: TP=${levels['atr_tp']:,.0f}  SL=${levels['atr_sl']:,.0f}  "
          f"RR={levels['atr_rr']:.4f}")

    # Test 2: ATR levels (SHORT)
    levels_s = compute_atr_levels("BTC-USD", mock_pick, entry_price=85000.0,
                                  direction="SHORT")
    assert levels_s is not None
    assert levels_s["atr_tp"] == 85000.0 - 2.5 * 2500.0  # 78750
    assert levels_s["atr_sl"] == 85000.0 + 1.5 * 2500.0  # 88750
    print(f"  SHORT BTC: TP=${levels_s['atr_tp']:,.0f}  SL=${levels_s['atr_sl']:,.0f}")

    # Test 3: Half-Kelly
    k1 = compute_half_kelly(0.729, 1.985, 1.289)
    print(f"\n  Half-Kelly (72.9% WR, 1.985/1.289): {k1:.4f}")
    assert 0.01 <= k1 <= 0.25

    # Test 4: Negative edge clamps to floor
    k2 = compute_half_kelly(0.30, 1.0, 2.0)
    print(f"  Half-Kelly (30% WR, negative edge): {k2:.4f} (expected 0.01)")
    assert k2 == 0.01

    # Test 5: High edge caps at 0.25
    k3 = compute_half_kelly(0.95, 10.0, 0.5)
    print(f"  Half-Kelly (95% WR, extreme edge): {k3:.4f} (expected 0.25)")
    assert k3 == 0.25

    # Test 6: Vol-adjusted sizing
    v1 = compute_vol_adjusted_size(atr=4500, price=85000)  # 5.3% = very volatile
    v2 = compute_vol_adjusted_size(atr=3000, price=85000)  # 3.5% = volatile
    v3 = compute_vol_adjusted_size(atr=1500, price=85000)  # 1.8% = normal
    v4 = compute_vol_adjusted_size(atr=500, price=85000)   # 0.6% = quiet
    print(f"\n  Vol-adjusted (5.3% ATR): {v1:.4f} (0.5x)")
    print(f"  Vol-adjusted (3.5% ATR): {v2:.4f} (0.75x)")
    print(f"  Vol-adjusted (1.8% ATR): {v3:.4f} (1.0x)")
    print(f"  Vol-adjusted (0.6% ATR): {v4:.4f} (1.25x)")
    assert v1 == 0.01
    assert v2 == 0.015
    assert v3 == 0.02
    assert v4 == 0.025

    # Test 7: Full enrichment (mock picks)
    mock_picks = [
        {
            "symbol": "BTC-USD", "entry_price": 85000.0, "strategy": "keltner_btc",
            "signal_type": "BUY", "direction": "LONG", "atr_at_entry": 2500.0,
        },
        {
            "symbol": "ETH-USD", "entry_price": 3200.0, "strategy": "macd_eth",
            "signal_type": "BUY", "direction": "LONG", "atr_at_entry": 120.0,
        },
        {
            "symbol": "UNKNOWN-USD", "entry_price": 0,  # Should be skipped
            "strategy": "test", "signal_type": "BUY",
        },
    ]
    mock_perf = {
        "keltner_btc": {
            "win_rate": 0.729, "avg_win_pct": 1.985, "avg_loss_pct": 1.289,
            "closed_picks": 50,
        },
        "macd_eth": {
            "win_rate": 0.60, "avg_win_pct": 3.0, "avg_loss_pct": 2.0,
            "closed_picks": 3,  # Too few -- should use default kelly
        },
    }
    result = enrich_picks_with_dynamic_risk(mock_picks, mock_perf)
    assert result[0].get("dynamic_tp") is not None
    assert result[0].get("kelly_fraction") is not None
    assert result[0].get("vol_adj_size") is not None
    assert result[0].get("atr_pct") is not None
    assert result[1].get("kelly_fraction") == 0.01  # cold start
    print(f"\n  BTC pick: dynamic_tp={result[0]['dynamic_tp']}, "
          f"kelly={result[0]['kelly_fraction']}, vol_adj={result[0]['vol_adj_size']}")
    print(f"  ETH pick: dynamic_tp={result[1]['dynamic_tp']}, "
          f"kelly={result[1]['kelly_fraction']} (cold start)")

    print("\n  All tests passed.")
