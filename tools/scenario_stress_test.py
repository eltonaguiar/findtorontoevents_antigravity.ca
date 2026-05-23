#!/usr/bin/env python3
"""Scenario Stress Test Engine — 3 vectors from HEDGE_FUND_ENHANCEMENT_PLAN v2.

Vectors:
  1. 30% BTC crash  (alt-coin beta amplification)
  2. 24h exchange outage  (all positions drift to stop-loss)
  3. Stablecoin regulatory ban  (USDT/USDC depeg + market panic)

Reads active portfolio from audit_dashboard/data/dashboard_data.json,
writes results to tools/stress_test_results.json.
"""

import json, os, sys, math, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "audit_dashboard", "data", "dashboard_data.json")
OUT_PATH = os.path.join(ROOT, "tools", "stress_test_results.json")

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _load_active():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        d = json.load(f)
    return d["picks"]["active"]


def _is_crypto(p):
    return (p.get("asset_class") or "").upper() == "CRYPTO"


def _is_btc(p):
    return "BTC" in (p.get("symbol") or "").upper()


def _sl_pct(p):
    """Return stop-loss distance as a positive fraction (e.g. 0.05 = 5%)."""
    entry = p.get("entry_price") or 0
    sl = p.get("stop_loss") or 0
    if not entry or not sl:
        return 0.15  # default assumption
    dist = abs(sl - entry) / entry
    return dist if dist > 0 else 0.15


def _direction_sign(p):
    return -1 if (p.get("direction") or "").upper() == "SHORT" else 1


def _pnl_from_move(p, move_pct):
    """Given a market move (negative = crash), return PnL % for this position.
    LONGs lose on negative moves, SHORTs gain."""
    return _direction_sign(p) * move_pct


def _stopped_out(p, move_pct):
    """Would this position hit its SL given a market move?"""
    pnl = _pnl_from_move(p, move_pct)
    sl_dist = _sl_pct(p)
    return pnl < -sl_dist


# ---------------------------------------------------------------------------
# BTC beta estimation
# ---------------------------------------------------------------------------

def _btc_beta(p):
    """Estimate how much this asset moves relative to BTC.
    BTC=1.0, major alts 1.2-1.4, small-caps 1.5-1.8, non-crypto ~0.3."""
    sym = (p.get("symbol") or "").upper()
    if not _is_crypto(p):
        # equities / forex have mild BTC correlation
        if p.get("asset_class", "").upper() == "EQUITY":
            return 0.25  # tech-heavy equities have some correlation
        return 0.10  # forex / sports minimal
    if "BTC" in sym:
        return 1.0
    if "ETH" in sym:
        return 1.25
    # major alts
    majors = {"BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "MATIC", "LINK", "ATOM"}
    for m in majors:
        if m in sym:
            return 1.35
    # everything else: small-cap alt
    return 1.6


# ---------------------------------------------------------------------------
# Scenario 1: 30% BTC crash
# ---------------------------------------------------------------------------

def scenario_btc_crash(picks, btc_drop=-0.30):
    results = []
    for p in picks:
        beta = _btc_beta(p)
        asset_move = btc_drop * beta  # e.g. -0.30 * 1.6 = -0.48
        pnl = _pnl_from_move(p, asset_move)
        stopped = _stopped_out(p, asset_move)
        results.append({
            "symbol": p.get("symbol"),
            "strategy": p.get("strategy"),
            "direction": p.get("direction"),
            "beta": beta,
            "implied_move_pct": round(asset_move * 100, 2),
            "pnl_pct": round(pnl * 100, 2),
            "stopped_out": stopped,
        })
    total_loss = sum(r["pnl_pct"] for r in results) / len(results) if results else 0
    stopped_count = sum(1 for r in results if r["stopped_out"])
    worst = min(results, key=lambda r: r["pnl_pct"]) if results else {}
    return {
        "name": "30% BTC Crash",
        "description": "BTC drops 30%; alts amplified by beta (1.2-1.8x). Non-crypto mildly correlated.",
        "avg_portfolio_loss_pct": round(total_loss, 2),
        "positions_stopped_out": stopped_count,
        "total_positions": len(results),
        "worst_symbol": worst.get("symbol"),
        "worst_strategy": worst.get("strategy"),
        "worst_pnl_pct": worst.get("pnl_pct"),
        "details": sorted(results, key=lambda r: r["pnl_pct"]),
    }


# ---------------------------------------------------------------------------
# Scenario 2: 24h exchange outage (drift to SL)
# ---------------------------------------------------------------------------

def scenario_exchange_outage(picks):
    results = []
    for p in picks:
        sl_dist = _sl_pct(p)
        # Worst case: every position drifts to its SL
        pnl = -sl_dist * 100  # always a loss
        results.append({
            "symbol": p.get("symbol"),
            "strategy": p.get("strategy"),
            "direction": p.get("direction"),
            "sl_distance_pct": round(sl_dist * 100, 2),
            "pnl_pct": round(pnl, 2),
            "stopped_out": True,  # by definition
        })
    total_loss = sum(r["pnl_pct"] for r in results) / len(results) if results else 0
    worst = min(results, key=lambda r: r["pnl_pct"]) if results else {}
    return {
        "name": "24h Exchange Outage",
        "description": "Zero liquidity for 24h. All positions drift to stop-loss. No SL = assume -15%.",
        "avg_portfolio_loss_pct": round(total_loss, 2),
        "positions_stopped_out": len(results),
        "total_positions": len(results),
        "worst_symbol": worst.get("symbol"),
        "worst_strategy": worst.get("strategy"),
        "worst_pnl_pct": worst.get("pnl_pct"),
        "details": sorted(results, key=lambda r: r["pnl_pct"]),
    }


# ---------------------------------------------------------------------------
# Scenario 3: Stablecoin regulatory ban
# ---------------------------------------------------------------------------

def scenario_stablecoin_ban(picks, depeg_pct=-0.075, panic_pct=-0.20):
    """USDT/USDC depeg 5-10% (avg 7.5%). Market panic -20% across the board.
    Crypto positions get both depeg + panic. Non-crypto get only panic spillover (dampened)."""
    results = []
    for p in picks:
        sym = (p.get("symbol") or "").upper()
        is_usdt = "USDT" in sym
        is_usdc = "USDC" in sym
        is_stablecoin_denom = is_usdt or is_usdc

        if _is_crypto(p):
            # Crypto: full panic + depeg on USDT/USDC denominated pairs
            market_move = panic_pct + (depeg_pct if is_stablecoin_denom else 0)
        else:
            # Non-crypto: dampened panic spillover
            market_move = panic_pct * 0.30  # 30% spillover to traditional markets
        pnl = _pnl_from_move(p, market_move)
        stopped = _stopped_out(p, market_move)
        results.append({
            "symbol": p.get("symbol"),
            "strategy": p.get("strategy"),
            "direction": p.get("direction"),
            "is_stablecoin_denom": is_stablecoin_denom,
            "implied_move_pct": round(market_move * 100, 2),
            "pnl_pct": round(pnl * 100, 2),
            "stopped_out": stopped,
        })
    total_loss = sum(r["pnl_pct"] for r in results) / len(results) if results else 0
    stopped_count = sum(1 for r in results if r["stopped_out"])
    worst = min(results, key=lambda r: r["pnl_pct"]) if results else {}
    return {
        "name": "Stablecoin Regulatory Ban",
        "description": "USDT/USDC depeg 7.5%. Market panic -20% crypto, -6% equities. Combined impact on USDT pairs.",
        "avg_portfolio_loss_pct": round(total_loss, 2),
        "positions_stopped_out": stopped_count,
        "total_positions": len(results),
        "worst_symbol": worst.get("symbol"),
        "worst_strategy": worst.get("strategy"),
        "worst_pnl_pct": worst.get("pnl_pct"),
        "details": sorted(results, key=lambda r: r["pnl_pct"]),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(scenarios):
    w = 32
    print("=" * (w * 3 + 4))
    print("SCENARIO STRESS TEST REPORT".center(w * 3 + 4))
    print(f"Generated: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * (w * 3 + 4))

    # Header row
    headers = [s["name"] for s in scenarios]
    print("  ".join(h.center(w) for h in headers))
    print("-" * (w * 3 + 4))

    rows = [
        ("Avg Portfolio Loss", "avg_portfolio_loss_pct", "%"),
        ("Positions Stopped Out", "positions_stopped_out", ""),
        ("Total Positions", "total_positions", ""),
        ("Worst Symbol", "worst_symbol", ""),
        ("Worst Strategy", "worst_strategy", ""),
        ("Worst Position PnL", "worst_pnl_pct", "%"),
    ]
    for label, key, suffix in rows:
        cells = []
        for s in scenarios:
            val = s.get(key, "N/A")
            if isinstance(val, float):
                cell = f"{val:+.2f}{suffix}"
            elif isinstance(val, int):
                cell = f"{val}{suffix}"
            elif isinstance(val, str) and len(val) > w - 2:
                cell = val[: w - 5] + "..."
            else:
                cell = str(val) + suffix
            cells.append(cell.center(w))
        print(f"{'  '.join(cells)}  {label}")
    print("=" * (w * 3 + 4))

    # Per-scenario top-5 worst
    for s in scenarios:
        print(f"\n--- {s['name']}: Top 5 Worst Positions ---")
        for r in s["details"][:5]:
            sym = r.get("symbol", "?")
            strat = (r.get("strategy") or "?")[:30]
            pnl = r.get("pnl_pct", 0)
            d = r.get("direction", "?")
            so = "STOPPED" if r.get("stopped_out") else "open"
            print(f"  {sym:<16} {d:<6} {pnl:+7.2f}%  [{so}]  {strat}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    picks = _load_active()
    if not picks:
        print("ERROR: No active picks found.")
        sys.exit(1)

    print(f"Loaded {len(picks)} active positions from dashboard_data.json\n")

    s1 = scenario_btc_crash(picks)
    s2 = scenario_exchange_outage(picks)
    s3 = scenario_stablecoin_ban(picks)
    scenarios = [s1, s2, s3]

    print_report(scenarios)

    # Write results (without bulky details for the JSON)
    output = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "portfolio_size": len(picks),
        "scenarios": [],
    }
    for s in scenarios:
        summary = {k: v for k, v in s.items() if k != "details"}
        summary["top5_worst"] = s["details"][:5]
        output["scenarios"].append(summary)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults written to {OUT_PATH}")


if __name__ == "__main__":
    main()
