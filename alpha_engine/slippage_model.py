#!/usr/bin/env python3
"""
Liquidity-Adjusted Slippage Model & Volatility-Targeted Position Sizing
========================================================================
Estimates realistic trading costs (spread + market impact + fees) and adjusts
position sizes to target a fixed portfolio volatility.

Wired into production_scanner.py after Kelly sizing (step 6h).

Components:
  1. Slippage estimation: base_spread + k * sqrt(order_size / adv)
  2. Net edge after costs: expected_pnl - slippage - fees
  3. Volatility-targeted sizing: target_vol / (forecasted_vol * sqrt(252))
  4. Realistic Sharpe: recompute Sharpe on cost-adjusted closed trades
"""

from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parent / "data"
_REALISTIC_SHARPE_PATH = _DATA_DIR / "realistic_sharpe.json"
_SLIPPAGE_CALIBRATION_PATH = _DATA_DIR / "slippage_calibration.json"
_CLOSED_PICKS_PATH = _DATA_DIR / "closed_picks.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Top-20 altcoins by market cap (approximate, updated periodically)
TOP20_ALTS = {
    "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOTUSDT",
    "AVAXUSDT", "LINKUSDT", "MATICUSDT", "TRXUSDT", "SHIBUSDT", "LTCUSDT",
    "NEARUSDT", "ATOMUSDT", "UNIUSDT", "APTUSDT", "ARBUSDT", "OPUSDT",
    "SUIUSDT", "INJUSDT",
}

MAJORS = {"BTCUSDT", "ETHUSDT"}

# Base spreads (one-way, in decimal)
BASE_SPREAD_BTC_ETH = 0.0005      # 0.05%
BASE_SPREAD_TOP20 = 0.0010        # 0.10%
BASE_SPREAD_SMALLCAP = 0.0020     # 0.20%
BASE_SPREAD_FOREX = 0.0002        # 0.02%

# Trading fees (round-trip, taker)
FEE_CRYPTO = 0.0010   # 0.10% round-trip
FEE_FOREX = 0.0004    # 0.04% round-trip

# Market impact constant (calibrated starting value)
DEFAULT_K = 0.5

# Volatility target (annualized)
DEFAULT_TARGET_VOL = 0.15  # 15%

# Position size multiplier clamps
VOL_SIZE_MIN = 0.25
VOL_SIZE_MAX = 2.0


# ---------------------------------------------------------------------------
# 1. Slippage Estimation
# ---------------------------------------------------------------------------

def _get_base_spread(symbol: str, category: str = "crypto") -> float:
    """Return base spread for the given symbol/category."""
    if category in ("forex",):
        return BASE_SPREAD_FOREX
    if symbol in MAJORS:
        return BASE_SPREAD_BTC_ETH
    if symbol in TOP20_ALTS:
        return BASE_SPREAD_TOP20
    return BASE_SPREAD_SMALLCAP


def _get_trading_fee(category: str = "crypto") -> float:
    """Return round-trip trading fee for the asset category."""
    if category in ("forex",):
        return FEE_FOREX
    return FEE_CRYPTO


def _load_calibrated_k() -> float:
    """Load self-calibrated k constant from disk, or return default."""
    if _SLIPPAGE_CALIBRATION_PATH.exists():
        try:
            with open(_SLIPPAGE_CALIBRATION_PATH) as f:
                data = json.load(f)
            k = data.get("k", DEFAULT_K)
            if 0.01 <= k <= 5.0:
                return k
        except Exception:
            pass
    return DEFAULT_K


def estimate_slippage(symbol: str, order_size_usd: float,
                      avg_daily_volume_usd: float,
                      category: str = "crypto") -> float:
    """Estimate one-way slippage in decimal (e.g., 0.003 = 0.3%).

    Formula: base_spread + k * sqrt(order_size / adv)
    """
    base = _get_base_spread(symbol, category)

    if avg_daily_volume_usd <= 0:
        # No volume data -- assume worst case small-cap spread
        return base * 3

    k = _load_calibrated_k()
    market_impact = k * math.sqrt(max(order_size_usd, 0) / avg_daily_volume_usd)

    return base + market_impact


# ---------------------------------------------------------------------------
# 2. Net Edge After Costs
# ---------------------------------------------------------------------------

def compute_net_edge(expected_pnl_pct: float, slippage: float,
                     category: str = "crypto") -> float:
    """Compute net expected edge after slippage and trading fees.

    Args:
        expected_pnl_pct: Expected PnL in decimal (e.g., 0.02 = 2%)
        slippage: One-way estimated slippage in decimal
        category: Asset category for fee lookup

    Returns:
        Net edge in decimal. Negative means the trade loses money after costs.
    """
    fee = _get_trading_fee(category)
    # Slippage is one-way but we enter AND exit, so double it
    total_cost = (slippage * 2) + fee
    return expected_pnl_pct - total_cost


# ---------------------------------------------------------------------------
# 3. Volume Fetching (Binance with 4-mirror failover)
# ---------------------------------------------------------------------------

def _fetch_24h_volumes() -> dict[str, float]:
    """Fetch 24h quote volumes from Binance ticker with mirror failover.

    Returns dict of {symbol: volume_in_usd}.
    Uses the fetch_binance_json helper from config.py which already has
    4-mirror failover + non-Binance fallbacks.
    """
    try:
        from config import fetch_binance_json
    except ImportError:
        try:
            from alpha_engine.config import fetch_binance_json
        except ImportError:
            return {}

    data = fetch_binance_json("/api/v3/ticker/24hr")
    if not data or not isinstance(data, list):
        return {}

    volumes = {}
    for item in data:
        sym = item.get("symbol", "")
        try:
            vol = float(item.get("quoteVolume", 0))
            if vol > 0:
                volumes[sym] = vol
        except (ValueError, TypeError):
            continue
    return volumes


def _fetch_klines_for_vol(symbol: str, days: int = 20) -> list[float]:
    """Fetch daily close prices from Binance klines for volatility calculation.

    Returns list of daily close prices (most recent last).
    """
    try:
        from config import fetch_binance_json
    except ImportError:
        try:
            from alpha_engine.config import fetch_binance_json
        except ImportError:
            return []

    data = fetch_binance_json(
        f"/api/v3/klines?symbol={symbol}&interval=1d&limit={days + 1}"
    )
    if not data or not isinstance(data, list):
        return []

    closes = []
    for candle in data:
        try:
            closes.append(float(candle[4]))  # close price is index 4
        except (IndexError, ValueError, TypeError):
            continue
    return closes


def _realized_vol_from_closes(closes: list[float]) -> float:
    """Compute realized volatility (daily) from a list of close prices.

    Returns daily volatility as decimal (e.g., 0.03 = 3% daily).
    """
    if len(closes) < 3:
        return 0.0

    log_returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0 and closes[i] > 0:
            log_returns.append(math.log(closes[i] / closes[i - 1]))

    if len(log_returns) < 2:
        return 0.0

    mean_ret = sum(log_returns) / len(log_returns)
    variance = sum((r - mean_ret) ** 2 for r in log_returns) / (len(log_returns) - 1)
    return math.sqrt(variance)


# ---------------------------------------------------------------------------
# 4. Volatility-Targeted Position Sizing
# ---------------------------------------------------------------------------

def vol_targeted_multiplier(symbol: str, target_vol: float = None,
                            daily_vol: float = None) -> float:
    """Compute position size multiplier to target portfolio volatility.

    target_vol / (forecasted_vol * sqrt(252))

    Args:
        symbol: Trading symbol (used to fetch klines if daily_vol not given)
        target_vol: Annualized target volatility (default from env or 15%)
        daily_vol: Pre-computed daily realized vol (optional)

    Returns:
        Multiplier on base Kelly size, clamped to [0.25, 2.0]
    """
    if target_vol is None:
        target_vol = float(os.environ.get("ALPHA_TARGET_VOL", str(DEFAULT_TARGET_VOL)))

    if daily_vol is None:
        closes = _fetch_klines_for_vol(symbol, days=20)
        daily_vol = _realized_vol_from_closes(closes)

    if daily_vol <= 0:
        return 1.0  # no data, no adjustment

    # Annualize: daily_vol * sqrt(252) for equities/forex, sqrt(365) for crypto
    is_crypto = symbol.endswith("USDT") or symbol.endswith("USD")
    annualized_vol = daily_vol * math.sqrt(365 if is_crypto else 252)

    if annualized_vol <= 0:
        return 1.0

    multiplier = target_vol / annualized_vol
    return max(VOL_SIZE_MIN, min(VOL_SIZE_MAX, multiplier))


# ---------------------------------------------------------------------------
# 5. Realistic Sharpe Computation
# ---------------------------------------------------------------------------

def _load_closed_picks() -> list[dict]:
    """Load closed picks for Sharpe calculation."""
    if not _CLOSED_PICKS_PATH.exists():
        return []
    try:
        with open(_CLOSED_PICKS_PATH) as f:
            return json.load(f)
    except Exception:
        return []


def compute_realistic_sharpe() -> dict:
    """Compute Sharpe ratio on cost-adjusted returns from closed picks.

    Subtracts estimated slippage + fees from each trade's PnL,
    then computes annualized Sharpe.

    Returns:
        Dict with raw_sharpe, realistic_sharpe, total_cost_drag_bps, n_trades
    """
    closed = _load_closed_picks()
    if len(closed) < 5:
        return {"raw_sharpe": 0.0, "realistic_sharpe": 0.0,
                "total_cost_drag_bps": 0, "n_trades": len(closed),
                "note": "insufficient_data"}

    raw_returns = []
    adjusted_returns = []

    for pick in closed:
        pnl_pct = pick.get("pnl_pct")
        if pnl_pct is None:
            pnl_raw = pick.get("pnl")
            entry = pick.get("entry_price") or pick.get("entryPrice")
            if pnl_raw is not None and entry and float(entry) > 0:
                pnl_pct = float(pnl_raw) / float(entry)
            else:
                continue
        else:
            pnl_pct = float(pnl_pct)
            # Normalize: if stored as percentage (e.g., 2.5 meaning 2.5%)
            if abs(pnl_pct) > 1:
                pnl_pct = pnl_pct / 100.0

        symbol = pick.get("symbol", "UNKNOWN")
        category = pick.get("category", "crypto")

        # Estimate slippage for this trade (assume $500 order size as proxy)
        # Volume data not available for historical trades, use base spread * 2
        base = _get_base_spread(symbol, category)
        slippage_both_ways = base * 2
        fee = _get_trading_fee(category)
        total_cost = slippage_both_ways + fee

        raw_returns.append(pnl_pct)
        adjusted_returns.append(pnl_pct - total_cost)

    if len(raw_returns) < 2:
        return {"raw_sharpe": 0.0, "realistic_sharpe": 0.0,
                "total_cost_drag_bps": 0, "n_trades": 0,
                "note": "insufficient_valid_data"}

    def _sharpe(returns: list[float]) -> float:
        n = len(returns)
        mean_r = sum(returns) / n
        var_r = sum((r - mean_r) ** 2 for r in returns) / max(n - 1, 1)
        std_r = math.sqrt(var_r) if var_r > 0 else 1e-9
        # Annualize assuming ~250 trades/year
        trades_per_year = min(n * (365 / max(30, 1)), 500)
        return (mean_r / std_r) * math.sqrt(trades_per_year)

    raw_sharpe = _sharpe(raw_returns)
    realistic_sharpe = _sharpe(adjusted_returns)

    mean_raw = sum(raw_returns) / len(raw_returns)
    mean_adj = sum(adjusted_returns) / len(adjusted_returns)
    cost_drag_bps = round((mean_raw - mean_adj) * 10000)

    result = {
        "raw_sharpe": round(raw_sharpe, 3),
        "realistic_sharpe": round(realistic_sharpe, 3),
        "total_cost_drag_bps": cost_drag_bps,
        "n_trades": len(raw_returns),
        "mean_raw_pnl_pct": round(mean_raw * 100, 3),
        "mean_adj_pnl_pct": round(mean_adj * 100, 3),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Persist
    try:
        _REALISTIC_SHARPE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_REALISTIC_SHARPE_PATH, "w") as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# 6. Self-Calibration of k from Historical Fills
# ---------------------------------------------------------------------------

def calibrate_k_from_history() -> float:
    """Self-calibrate the market impact constant k from closed picks
    that have both entry_price and fill_price (actual execution).

    Stores calibrated value to disk for future use.
    """
    closed = _load_closed_picks()

    observations = []
    for pick in closed:
        entry = pick.get("entry_price") or pick.get("entryPrice")
        fill = pick.get("fill_price") or pick.get("actual_fill")
        volume_usd = pick.get("volume_24h") or (pick.get("extra", {}) or {}).get("volume_24h")

        if not all([entry, fill, volume_usd]):
            continue

        try:
            entry_f = float(entry)
            fill_f = float(fill)
            vol_f = float(volume_usd)
            if entry_f <= 0 or vol_f <= 0:
                continue
        except (ValueError, TypeError):
            continue

        observed_slippage = abs(fill_f - entry_f) / entry_f
        symbol = pick.get("symbol", "")
        category = pick.get("category", "crypto")
        base = _get_base_spread(symbol, category)

        # market_impact = observed_slippage - base_spread
        market_impact = max(observed_slippage - base, 0)

        # order_size approximation (use position_size if available, else $500)
        order_size = float(pick.get("position_size_usd", 500))
        ratio = order_size / vol_f

        if ratio > 0 and market_impact > 0:
            # k = market_impact / sqrt(ratio)
            k_obs = market_impact / math.sqrt(ratio)
            if 0.01 <= k_obs <= 10.0:
                observations.append(k_obs)

    if len(observations) < 3:
        return DEFAULT_K

    # Use median for robustness
    observations.sort()
    mid = len(observations) // 2
    if len(observations) % 2 == 0:
        k_calibrated = (observations[mid - 1] + observations[mid]) / 2
    else:
        k_calibrated = observations[mid]

    # Clamp to reasonable range
    k_calibrated = max(0.1, min(3.0, k_calibrated))

    # Persist
    try:
        cal_data = {
            "k": round(k_calibrated, 4),
            "n_observations": len(observations),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _SLIPPAGE_CALIBRATION_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_SLIPPAGE_CALIBRATION_PATH, "w") as f:
            json.dump(cal_data, f, indent=2)
    except Exception:
        pass

    return k_calibrated


# ---------------------------------------------------------------------------
# 7. Main Integration: apply_slippage_and_vol_sizing
# ---------------------------------------------------------------------------

def apply_slippage_and_vol_sizing(active_picks: list[dict],
                                  portfolio_value: float = 10000) -> list[dict]:
    """Apply slippage model and volatility-targeted sizing to active picks.

    This is the main entry point, called from production_scanner.py after Kelly sizing.

    For each pick:
      - Estimates slippage from symbol liquidity
      - Computes net edge (expected PnL - costs)
      - Blocks picks with negative edge (NEGATIVE_EDGE)
      - Adjusts position size by volatility-targeted multiplier
      - Adds net_edge_bps and slippage_bps to pick's extra dict

    Args:
        active_picks: List of pick dicts (already Kelly-sized)
        portfolio_value: Total portfolio value in USD

    Returns:
        Filtered + adjusted list of picks
    """
    if not active_picks:
        return active_picks

    # Fetch 24h volumes in bulk (single API call)
    volumes = _fetch_24h_volumes()

    # Attempt k calibration (non-blocking, uses cached value if no fill data)
    try:
        calibrate_k_from_history()
    except Exception:
        pass

    target_vol = float(os.environ.get("ALPHA_TARGET_VOL", str(DEFAULT_TARGET_VOL)))

    result = []
    blocked_count = 0

    for pick in active_picks:
        symbol = pick.get("symbol", "")
        category = pick.get("category", "crypto")

        # Get order size from Kelly sizing or default
        kelly_pct = pick.get("kelly_size_pct", 0.02)
        order_size_usd = portfolio_value * kelly_pct

        # Get 24h volume
        adv = volumes.get(symbol, 0)

        # Estimate slippage
        slippage = estimate_slippage(symbol, order_size_usd, adv, category)

        # Expected PnL: use tp_distance or score-based estimate
        extra = pick.get("extra", {}) or {}
        tp_dist = pick.get("tp_distance") or extra.get("tp_distance")
        if tp_dist is not None:
            expected_pnl = abs(float(tp_dist))
        else:
            # Fallback: use score as a proxy (higher score -> higher expected edge)
            score = pick.get("score", 50) or 50
            expected_pnl = max(0.005, (float(score) - 40) * 0.0005)

        # Net edge
        net_edge = compute_net_edge(expected_pnl, slippage, category)
        net_edge_bps = round(net_edge * 10000)

        # Slippage in bps for logging
        slippage_bps = round(slippage * 10000)

        # Store in extra dict
        if extra is None:
            extra = {}
        extra["net_edge_bps"] = net_edge_bps
        extra["slippage_bps"] = slippage_bps
        extra["est_slippage_pct"] = round(slippage * 100, 4)
        extra["est_round_trip_cost_pct"] = round((slippage * 2 + _get_trading_fee(category)) * 100, 4)
        pick["extra"] = extra

        # Block negative edge picks
        if net_edge < 0:
            pick["blocked"] = True
            pick["block_reason"] = "NEGATIVE_EDGE"
            extra["negative_edge_detail"] = (
                f"expected={expected_pnl*100:.2f}% < costs={((slippage*2)+_get_trading_fee(category))*100:.2f}%"
            )
            blocked_count += 1
            print(f"  [SLIPPAGE] BLOCKED {symbol}: net_edge={net_edge_bps}bps "
                  f"(slippage={slippage_bps}bps, expected_pnl={expected_pnl*10000:.0f}bps)")
            continue  # Do not include in result

        # Volatility-targeted sizing
        vol_mult = vol_targeted_multiplier(symbol, target_vol=target_vol)
        extra["vol_size_multiplier"] = round(vol_mult, 3)

        # Apply vol multiplier to Kelly size
        if "kelly_size_pct" in pick:
            original = pick["kelly_size_pct"]
            pick["kelly_size_pct"] = round(original * vol_mult, 6)
            extra["kelly_pre_vol"] = original
        if "position_size_usd" in pick:
            original_usd = pick["position_size_usd"]
            pick["position_size_usd"] = round(float(original_usd) * vol_mult, 2)
            extra["position_usd_pre_vol"] = original_usd

        result.append(pick)

    if blocked_count > 0:
        print(f"  [SLIPPAGE] Blocked {blocked_count} picks with negative edge")
    print(f"  [SLIPPAGE] Passed {len(result)}/{len(active_picks)} picks "
          f"(target_vol={target_vol*100:.0f}%)")

    # Compute realistic Sharpe in background (non-blocking)
    try:
        sharpe_data = compute_realistic_sharpe()
        if sharpe_data.get("n_trades", 0) >= 5:
            print(f"  [SHARPE] Raw={sharpe_data['raw_sharpe']:.2f} -> "
                  f"Realistic={sharpe_data['realistic_sharpe']:.2f} "
                  f"(cost drag: {sharpe_data['total_cost_drag_bps']}bps, "
                  f"n={sharpe_data['n_trades']})")
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Slippage Model Self-Test ===\n")

    # Test slippage estimation
    for sym, cat, adv in [
        ("BTCUSDT", "crypto", 5_000_000_000),
        ("ETHUSDT", "crypto", 2_000_000_000),
        ("SOLUSDT", "crypto", 500_000_000),
        ("PEPEUSDT", "crypto", 50_000_000),
        ("EURUSD", "forex", 1_000_000_000),
    ]:
        slip = estimate_slippage(sym, 500, adv, cat)
        fee = _get_trading_fee(cat)
        total = slip * 2 + fee
        print(f"  {sym:12s}: slippage={slip*10000:.1f}bps, "
              f"round-trip cost={total*10000:.1f}bps")

    # Test vol multiplier (offline, no API)
    print("\n--- Vol multiplier (synthetic) ---")
    for vol in [0.01, 0.03, 0.05, 0.10, 0.15]:
        ann = vol * math.sqrt(365)
        mult = DEFAULT_TARGET_VOL / ann if ann > 0 else 1.0
        mult = max(VOL_SIZE_MIN, min(VOL_SIZE_MAX, mult))
        print(f"  daily_vol={vol*100:.0f}%: annualized={ann*100:.1f}%, mult={mult:.2f}")

    # Test realistic Sharpe
    print("\n--- Realistic Sharpe ---")
    sharpe = compute_realistic_sharpe()
    print(f"  {json.dumps(sharpe, indent=2)}")
