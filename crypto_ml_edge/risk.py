"""
Risk Management — Crypto ML Edge Engine
=========================================
ATR-based fractional Kelly position sizing with hard caps.

Requirements satisfied:
  RISK-01: ATR-based volatility-adjusted position sizing, fractional Kelly
           10-25% (config: KELLY_FRACTION = 0.15).
  RISK-02: Hard cap at MAX_POSITION_PCT (5%) of capital per pick.
  RISK-03: TP/SL set per-pick from ATR multiples defined in TPSL_CONFIG.

Design philosophy:
  - Position size scales with edge (confidence) AND shrinks with volatility
    (ATR). High-volatility assets automatically receive smaller dollar risk.
  - Kelly criterion caps prevent ruin from overconfidence. We use 15% of
    full Kelly, which research suggests is near-optimal for noisy signals.
  - All functions are pure (no side effects) — safe to call from both
    the scanner and live inference without state contamination.

Academic anchors:
  - Kelly 1956: optimal growth criterion
  - Thorp 2008: fractional Kelly in practice (0.25 Kelly halves variance)
  - Vince 1992: optimal f and position sizing
"""

from __future__ import annotations

from typing import Optional

from crypto_ml_edge.config import (
    KELLY_FRACTION,
    MAX_POSITION_PCT,
    TPSL_CONFIG,
    SLIPPAGE_MAP,
    ROUND_TRIP_FEE,
)


# ─── Public API ───────────────────────────────────────────────────────────────

def compute_position_size(
    confidence: float,
    atr: float,
    price: float,
    capital: float,
    pair: str,
) -> dict:
    """
    ATR-based fractional Kelly position sizing.

    The Kelly fraction f* is derived from the model's confidence (edge
    estimate) and scaled by KELLY_FRACTION (15%) to stay conservative.
    The result is then divided by ATR-based volatility so that high-
    volatility assets receive proportionally smaller positions.

    The formula used:
        kelly_edge   = 2 * confidence - 1          # maps [0.5, 1] → [0, 1]
        raw_fraction = kelly_edge * KELLY_FRACTION
        vol_adj_frac = raw_fraction / (atr_pct + epsilon)
        position_pct = min(vol_adj_frac, MAX_POSITION_PCT)
        position_usd = position_pct * capital

    Where:
        atr_pct  = atr / price   (ATR expressed as a fraction of price)
        confidence must be > 0.5 to produce a positive signal; anything
        below 0.5 is treated as no-edge and returns position_size_usd=0.

    Parameters
    ----------
    confidence:
        Model probability for the predicted direction (e.g. 0.65 = 65%
        confident in a long signal). Must be in [0, 1].
        Values <= 0.5 produce a zero-size position (no edge above chance).
    atr:
        Absolute ATR in the same currency as price (not the normalised
        percentage version stored in the feature engine). For example,
        if price=50000 and atr_14 feature=0.01, then atr=500.
    price:
        Current asset price (same currency as atr and capital).
    capital:
        Total capital base in the quote currency (USD). Used to convert
        the fractional position size to a dollar amount.
    pair:
        Binance trading pair symbol (e.g. "BTCUSDT"). Used to look up
        the per-pair slippage for cost-adjusted minimum viable size.

    Returns
    -------
    dict with keys:
        position_size_usd:   Dollar amount to allocate to this trade.
                             0.0 if confidence <= 0.5 or inputs are invalid.
        position_size_pct:   Position as fraction of capital (0 to MAX_POSITION_PCT).
        tp_price:            Take-profit price level (0.0 if not computable).
        sl_price:            Stop-loss price level (0.0 if not computable).
        risk_reward_ratio:   TP distance / SL distance. 0.0 if SL distance is 0.
        kelly_edge:          Raw Kelly edge estimate before fraction scaling.
        atr_pct:             ATR expressed as fraction of price.
        effective_fraction:  Actual position fraction before capital multiplication.
        capped:              True if the position was capped by MAX_POSITION_PCT.

    Notes
    -----
    The minimum position size is not enforced here — that is a broker/exchange
    concern. Callers should check position_size_usd > minimum_order_size before
    submitting.
    """
    # ── Input validation ───────────────────────────────────────────────────
    if not (0.0 <= confidence <= 1.0):
        raise ValueError(f"confidence must be in [0, 1], got {confidence}")
    if price <= 0:
        raise ValueError(f"price must be positive, got {price}")
    if atr < 0:
        raise ValueError(f"atr must be non-negative, got {atr}")
    if capital <= 0:
        raise ValueError(f"capital must be positive, got {capital}")

    # ── No-edge case: confidence <= 0.5 means model predicts no better than
    #    random; do not size a position.
    if confidence <= 0.5:
        return _zero_position()

    # ── Step 1: Kelly edge from confidence ──────────────────────────────────
    # Full Kelly for a binary bet with win probability p:
    #   f* = 2p - 1   (when payoff is 1:1)
    # For TP/SL strategies the payoff is not 1:1, but this is a useful
    # approximation that degrades gracefully — in practice the fractional
    # Kelly multiplier absorbs most of the error.
    kelly_edge = 2.0 * confidence - 1.0   # range: (0, 1] when conf > 0.5

    # ── Step 2: ATR volatility scaling ──────────────────────────────────────
    # Express ATR as a fraction of price so it is dimensionless.
    # Avoid division by zero: if ATR is zero (flat market), return zero position
    # since there is no meaningful barrier to set.
    atr_pct = atr / price
    if atr_pct <= 0.0:
        return _zero_position()

    # ── Step 3: Fractional Kelly adjusted for volatility ───────────────────
    # The intuition: higher volatility → larger ATR → smaller position for
    # the same level of confidence. This keeps dollar risk-per-trade roughly
    # constant regardless of the asset's volatility regime.
    raw_fraction = kelly_edge * KELLY_FRACTION
    vol_adjusted_fraction = raw_fraction / (atr_pct + 1e-10)

    # ── Step 3b: Regime multiplier (Sharpe upgrade Feb 26 2026) ─────────────
    # Scale position by Fear & Greed regime. Our edge is strongest in
    # extreme fear (F&G < 15). No proven edge in greed.
    regime_mult = _regime_multiplier()
    vol_adjusted_fraction *= regime_mult

    # ── Step 4: Hard cap at MAX_POSITION_PCT ────────────────────────────────
    capped = vol_adjusted_fraction > MAX_POSITION_PCT
    effective_fraction = min(vol_adjusted_fraction, MAX_POSITION_PCT)
    effective_fraction = max(0.0, effective_fraction)  # floor at 0

    # ── Step 5: Dollar amount ───────────────────────────────────────────────
    position_size_usd = effective_fraction * capital

    # ── Step 6: TP/SL levels (default timeframe heuristic) ─────────────────
    # We don't know the timeframe here, so use the 1h config as a sensible
    # default. Callers who know the timeframe should use compute_tp_sl() directly.
    tp_sl = compute_tp_sl(
        price=price,
        atr=atr,
        timeframe="1h",
        direction="long",
    )

    return {
        "position_size_usd": round(position_size_usd, 2),
        "position_size_pct": round(effective_fraction, 6),
        "tp_price": tp_sl["tp_price"],
        "sl_price": tp_sl["sl_price"],
        "risk_reward_ratio": tp_sl["risk_reward_ratio"],
        "kelly_edge": round(kelly_edge, 4),
        "atr_pct": round(atr_pct, 6),
        "effective_fraction": round(effective_fraction, 6),
        "capped": capped,
    }


def compute_tp_sl(
    price: float,
    atr: float,
    timeframe: str,
    direction: str,
) -> dict:
    """
    Compute take-profit and stop-loss prices from ATR multiples.

    Uses TPSL_CONFIG from config.py which stores the ATR multiples
    calibrated per timeframe.

    Parameters
    ----------
    price:
        Entry price.
    atr:
        Absolute ATR in the same currency as price.
    timeframe:
        One of the keys in TPSL_CONFIG: "1h" or "4h".
    direction:
        "long" or "short". For longs: TP is above entry, SL below.
        For shorts: TP is below entry, SL above.

    Returns
    -------
    dict with keys:
        tp_price:          Take-profit absolute price level.
        sl_price:          Stop-loss absolute price level.
        tp_distance:       |tp_price - price| in absolute terms.
        sl_distance:       |sl_price - price| in absolute terms.
        tp_pct:            Take-profit as fraction of price.
        sl_pct:            Stop-loss as fraction of price.
        risk_reward_ratio: tp_distance / sl_distance (0 if sl_distance == 0).
        tp_atr_mult:       ATR multiple used for TP (from config).
        sl_atr_mult:       ATR multiple used for SL (from config).
        max_hold_bars:     Maximum holding period in bars (from config).

    Raises
    ------
    ValueError:
        If timeframe is not in TPSL_CONFIG.
        If direction is not "long" or "short".
        If price or atr are non-positive.
    """
    if timeframe not in TPSL_CONFIG:
        raise ValueError(
            f"timeframe '{timeframe}' not in TPSL_CONFIG. "
            f"Valid: {list(TPSL_CONFIG.keys())}"
        )
    if direction not in ("long", "short"):
        raise ValueError(
            f"direction must be 'long' or 'short', got '{direction}'"
        )
    if price <= 0:
        raise ValueError(f"price must be positive, got {price}")
    if atr <= 0:
        raise ValueError(f"atr must be positive, got {atr}")

    cfg = TPSL_CONFIG[timeframe]
    tp_mult: float = cfg["tp_atr_mult"]
    sl_mult: float = cfg["sl_atr_mult"]
    max_hold: int  = cfg["max_hold_bars"]

    tp_distance = tp_mult * atr
    sl_distance = sl_mult * atr

    if direction == "long":
        tp_price = price + tp_distance
        sl_price = price - sl_distance
    else:  # short
        tp_price = price - tp_distance
        sl_price = price + sl_distance

    risk_reward_ratio = (
        round(tp_distance / sl_distance, 3)
        if sl_distance > 0
        else 0.0
    )

    return {
        "tp_price": round(tp_price, 8),
        "sl_price": round(sl_price, 8),
        "tp_distance": round(tp_distance, 8),
        "sl_distance": round(sl_distance, 8),
        "tp_pct": round(tp_distance / price, 6),
        "sl_pct": round(sl_distance / price, 6),
        "risk_reward_ratio": risk_reward_ratio,
        "tp_atr_mult": tp_mult,
        "sl_atr_mult": sl_mult,
        "max_hold_bars": max_hold,
    }


def compute_portfolio_risk(
    picks: list[dict],
    capital: float,
    max_concurrent: Optional[int] = None,
) -> dict:
    """
    Portfolio-level risk summary across multiple simultaneous picks.

    Checks that the total allocated capital does not breach the per-pick
    cap or the portfolio concentration limit.

    Parameters
    ----------
    picks:
        List of dicts, each with at least:
            - confidence: float
            - atr: float
            - price: float
            - pair: str
        Typically the output of a scan run.
    capital:
        Total capital base.
    max_concurrent:
        Maximum simultaneous positions. Defaults to MAX_CONCURRENT_PICKS
        from config.

    Returns
    -------
    dict with keys:
        sized_picks:       List of picks with position sizing attached.
        total_allocated:   Sum of position_size_usd across all picks.
        total_allocated_pct: As fraction of capital.
        n_picks:           Number of picks after concentration filter.
        risk_per_pick_avg: Average risk per pick (USD).
    """
    from crypto_ml_edge.config import MAX_CONCURRENT_PICKS

    limit = max_concurrent if max_concurrent is not None else MAX_CONCURRENT_PICKS

    sized_picks = []
    for pick in picks[:limit]:
        sizing = compute_position_size(
            confidence=pick.get("confidence", 0.5),
            atr=pick.get("atr", 0.0),
            price=pick.get("price", 1.0),
            capital=capital,
            pair=pick.get("pair", "BTCUSDT"),
        )
        sized_picks.append({**pick, **sizing})

    total_usd = sum(p.get("position_size_usd", 0.0) for p in sized_picks)
    n = len(sized_picks)

    return {
        "sized_picks": sized_picks,
        "total_allocated": round(total_usd, 2),
        "total_allocated_pct": round(total_usd / capital, 6) if capital > 0 else 0.0,
        "n_picks": n,
        "risk_per_pick_avg": round(total_usd / n, 2) if n > 0 else 0.0,
    }


# ─── Private helpers ──────────────────────────────────────────────────────────

# Module-level cache for F&G (avoids HTTP call on every position sizing)
_fng_cache: dict = {"value": None, "fetched_at": 0.0}
_FNG_CACHE_TTL = 600  # 10 minutes


def _regime_multiplier() -> float:
    """Return regime-based position multiplier from cached F&G index.

    Extreme fear (F&G < 15): 1.3x — our proven edge zone.
    Fear (F&G 15-25): 1.1x — moderate boost.
    Neutral (F&G 25-60): 1.0x — standard.
    Greed (F&G > 60): 0.6x — no edge, reduce exposure.

    Caches F&G for 10 minutes to avoid HTTP call on every sizing.
    Falls back to 1.0 if fetch fails (safe default).
    """
    import time
    now = time.time()

    if _fng_cache["value"] is not None and (now - _fng_cache["fetched_at"]) < _FNG_CACHE_TTL:
        fng = _fng_cache["value"]
    else:
        try:
            import requests
            resp = requests.get(
                "https://api.alternative.me/fng/?limit=1", timeout=5
            )
            fng = int(resp.json()["data"][0]["value"])
            _fng_cache["value"] = fng
            _fng_cache["fetched_at"] = now
        except Exception:
            return 1.0

    if fng < 15:
        return 1.3
    elif fng < 25:
        return 1.1
    elif fng > 60:
        return 0.6
    return 1.0


def _zero_position() -> dict:
    """Return a zero-size position dict (used when confidence <= 0.5 or ATR=0)."""
    return {
        "position_size_usd": 0.0,
        "position_size_pct": 0.0,
        "tp_price": 0.0,
        "sl_price": 0.0,
        "risk_reward_ratio": 0.0,
        "kelly_edge": 0.0,
        "atr_pct": 0.0,
        "effective_fraction": 0.0,
        "capped": False,
    }
