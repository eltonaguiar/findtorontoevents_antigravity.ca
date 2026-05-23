"""
ALPHA_ENGINE -- Execution Cost Stack
======================================
Computes net expected edge after all friction costs.

Formula:
    NetEdge_bps = AlphaGross_bps - Sum(CostLeg_bps) - TransferBorrow_bps
    Trade only if NetEdge > SafetyBuffer (default 5 bps).

Cost legs (one-way):
    1. Explicit fees       : 10 bps taker (Binance default)
    2. Spread half-cost    : ATR-estimated or 5 bps default
    3. Market impact       : 2 bps for retail-sized orders
    4. Latency drift       : 1 bps conservative
    5. Funding carry       : funding_rate * hold_hours / 8
Round-trip doubles legs 1-4.

References:
    - Kissell & Glantz (2003), Optimal Trading Strategies
    - Binance fee schedule (2026 Q1): 0.10% taker, 0.02% maker
"""

from __future__ import annotations

from typing import Optional


# ---------------------------------------------------------------------------
# Default cost parameters (in basis points)
# ---------------------------------------------------------------------------
DEFAULT_TAKER_FEE_BPS = 10.0        # 0.10% Binance taker
DEFAULT_SPREAD_BPS = 5.0             # 0.05% half-spread estimate
DEFAULT_IMPACT_BPS = 2.0             # 0.02% for small orders (<$50k)
DEFAULT_LATENCY_BPS = 1.0            # 0.01% conservative latency drift
DEFAULT_SAFETY_BUFFER_BPS = 5.0      # minimum edge to take the trade


def compute_net_edge(
    pick: dict,
    atr_pct: Optional[float] = None,
    taker_fee_bps: float = DEFAULT_TAKER_FEE_BPS,
    spread_bps: Optional[float] = None,
    impact_bps: float = DEFAULT_IMPACT_BPS,
    latency_bps: float = DEFAULT_LATENCY_BPS,
    funding_rate: Optional[float] = None,
    expected_hold_hours: Optional[float] = None,
    safety_buffer_bps: float = DEFAULT_SAFETY_BUFFER_BPS,
) -> dict:
    """Compute net expected edge after all execution costs.

    Args:
        pick: Signal dict with entry_price, take_profit, stop_loss, direction,
              optionally funding_rate and expected_hold_hours.
        atr_pct: ATR as fraction of price (e.g., 0.035 for 3.5%). If provided,
                 used to estimate spread cost (30% of ATR is a common proxy).
        taker_fee_bps: One-way taker fee in basis points.
        spread_bps: Half-spread in bps. If None, estimated from atr_pct or default.
        impact_bps: Market impact in bps.
        latency_bps: Latency drift in bps.
        funding_rate: Per-8h funding rate as decimal (e.g., 0.0001 for 0.01%).
                      Pulled from pick dict if not supplied.
        expected_hold_hours: Expected holding period in hours.
                             If None, estimated from TP/SL distance.
        safety_buffer_bps: Minimum net edge to consider trade profitable.

    Returns:
        dict with:
            gross_edge_bps: (tp - entry) / entry * 10000  (for longs)
            total_cost_bps: sum of all cost legs (round-trip)
            net_edge_bps: gross - costs
            is_profitable: net_edge > safety_buffer
            safety_buffer_bps: the buffer used
            cost_breakdown: dict of per-leg costs in bps
    """
    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    direction = pick.get("direction", "long")

    result = {
        "gross_edge_bps": 0.0,
        "total_cost_bps": 0.0,
        "net_edge_bps": 0.0,
        "is_profitable": False,
        "safety_buffer_bps": safety_buffer_bps,
        "cost_breakdown": {},
    }

    if not entry or entry <= 0 or not tp or tp <= 0:
        return result

    # --- Gross edge ---
    if direction == "short":
        gross_edge_pct = (entry - tp) / entry
    else:
        gross_edge_pct = (tp - entry) / entry
    gross_edge_bps = gross_edge_pct * 10_000
    result["gross_edge_bps"] = round(gross_edge_bps, 2)

    # --- Spread estimate ---
    if spread_bps is not None:
        effective_spread_bps = spread_bps
    elif atr_pct is not None and atr_pct > 0:
        # 30% of ATR is a common spread proxy for liquid crypto
        effective_spread_bps = atr_pct * 10_000 * 0.30
    else:
        # Fallback: try to get ATR from pick metadata
        pick_atr = pick.get("atr_at_entry", 0)
        if pick_atr and entry > 0:
            pick_atr_pct = pick_atr / entry
            effective_spread_bps = pick_atr_pct * 10_000 * 0.30
        else:
            effective_spread_bps = DEFAULT_SPREAD_BPS

    # Cap spread estimate to something reasonable (max 50 bps one-way)
    effective_spread_bps = min(effective_spread_bps, 50.0)

    # --- Funding carry ---
    fr = funding_rate if funding_rate is not None else pick.get("funding_rate", 0)
    fr = fr or 0

    if expected_hold_hours is None:
        # Estimate hold duration from TP/SL distance and typical crypto vol
        expected_hold_hours = pick.get("expected_hold_hours", 0)
        if not expected_hold_hours:
            # Rough estimate: 1% move per 8h for crypto
            if gross_edge_pct > 0:
                expected_hold_hours = min(max(gross_edge_pct / 0.00125, 4), 168)
            else:
                expected_hold_hours = 24

    funding_cost_bps = abs(fr) * (expected_hold_hours / 8.0) * 10_000

    # --- One-way costs ---
    one_way_bps = taker_fee_bps + effective_spread_bps + impact_bps + latency_bps

    # --- Round-trip (double one-way for legs 1-4) + funding ---
    total_cost_bps = (one_way_bps * 2) + funding_cost_bps

    # --- Net edge ---
    net_edge_bps = gross_edge_bps - total_cost_bps

    result["total_cost_bps"] = round(total_cost_bps, 2)
    result["net_edge_bps"] = round(net_edge_bps, 2)
    result["is_profitable"] = net_edge_bps > safety_buffer_bps
    result["cost_breakdown"] = {
        "taker_fee_bps_rt": round(taker_fee_bps * 2, 2),
        "spread_bps_rt": round(effective_spread_bps * 2, 2),
        "impact_bps_rt": round(impact_bps * 2, 2),
        "latency_bps_rt": round(latency_bps * 2, 2),
        "funding_carry_bps": round(funding_cost_bps, 2),
    }

    return result


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  Execution Cost Stack -- Self-Test")
    print("=" * 60)

    # Test 1: Typical crypto trade (2% TP, 1% SL)
    pick1 = {
        "symbol": "BTC-USD",
        "entry_price": 85000.0,
        "take_profit": 86700.0,   # +2%
        "stop_loss": 84150.0,     # -1%
        "direction": "long",
        "atr_at_entry": 2500.0,
    }
    r1 = compute_net_edge(pick1)
    print(f"\n  BTC +2% TP trade:")
    print(f"    Gross edge:  {r1['gross_edge_bps']:.1f} bps")
    print(f"    Total costs: {r1['total_cost_bps']:.1f} bps")
    print(f"    Net edge:    {r1['net_edge_bps']:.1f} bps")
    print(f"    Profitable:  {r1['is_profitable']}")
    print(f"    Breakdown:   {r1['cost_breakdown']}")
    assert r1["gross_edge_bps"] == 200.0, f"Expected 200 bps gross, got {r1['gross_edge_bps']}"
    assert r1["is_profitable"], "2% TP should be profitable after costs"

    # Test 2: Tiny edge trade (0.1% TP) -- should NOT be profitable
    pick2 = {
        "symbol": "ETH-USD",
        "entry_price": 3500.0,
        "take_profit": 3503.5,    # +0.1%
        "stop_loss": 3465.0,
        "direction": "long",
    }
    r2 = compute_net_edge(pick2)
    print(f"\n  ETH +0.1% TP trade:")
    print(f"    Gross edge:  {r2['gross_edge_bps']:.1f} bps")
    print(f"    Net edge:    {r2['net_edge_bps']:.1f} bps")
    print(f"    Profitable:  {r2['is_profitable']}")
    assert not r2["is_profitable"], "0.1% TP should NOT be profitable after costs"

    # Test 3: Short direction
    pick3 = {
        "symbol": "SOL-USD",
        "entry_price": 180.0,
        "take_profit": 172.0,     # -4.4% (short TP = lower)
        "stop_loss": 185.0,
        "direction": "short",
    }
    r3 = compute_net_edge(pick3)
    print(f"\n  SOL short trade:")
    print(f"    Gross edge:  {r3['gross_edge_bps']:.1f} bps")
    print(f"    Profitable:  {r3['is_profitable']}")
    assert r3["gross_edge_bps"] > 400, "4.4% short should have >400 bps gross"

    # Test 4: With explicit funding rate
    pick4 = {
        "symbol": "BTC-USD",
        "entry_price": 85000.0,
        "take_profit": 85850.0,   # +1%
        "stop_loss": 84150.0,
        "direction": "long",
    }
    r4 = compute_net_edge(pick4, funding_rate=0.0003, expected_hold_hours=48)
    print(f"\n  BTC +1% with high funding (0.03%/8h, 48h hold):")
    print(f"    Funding cost: {r4['cost_breakdown']['funding_carry_bps']:.1f} bps")
    print(f"    Net edge:     {r4['net_edge_bps']:.1f} bps")

    # Test 5: Missing data (should return zeros gracefully)
    r5 = compute_net_edge({})
    assert r5["net_edge_bps"] == 0.0
    print(f"\n  Empty pick: net_edge={r5['net_edge_bps']} (graceful zero)")

    print("\n  All execution cost tests passed.")
