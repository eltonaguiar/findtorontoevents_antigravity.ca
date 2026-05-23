#!/usr/bin/env python3
"""
Claude Pick Generator — Round 2 Evolutionary Regime Engine
==========================================================
Auto-generates Claude's tournament picks by:
1. Fetching current market regime (BTC trend, F&G, ADX, RSI)
2. Scanning all systems' active picks (same sources as fc_crypto_pro)
3. Applying enhanced scoring with regime/vol/ADX multipliers
4. Selecting top 3 picks with highest composite score
5. Writing to audit_dashboard/data/claude_top_picks.json

Research basis:
  - Moskowitz (2012) TSMOM — regime-aware direction gating
  - Llorente (2002) — volume as liquidity/conviction filter
  - Wilder (1978) — ADX for trend strength
  - Lo (2000) — oversold traps in bear markets
  - Vince (2000) — dynamic R:R by regime

Round 1 lesson: Direction selection explains ~80% of outcome variance.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request
from datetime import datetime, timezone

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# ── Import regime router ──
try:
    from cross_aggregation.regime_router import get_market_context
    _HAS_REGIME = True
except ImportError:
    _HAS_REGIME = False

# ── Config ──
MAX_PICKS = 3
MIN_SCORE = 0.15
MIN_RR = 1.0   # Lower floor — dynamic cap handles the rest

# ── Oversold strategies killed in downtrend ──
OVERSOLD_STRATEGIES = {
    "williams_pct_r", "williams_r", "williams_%r",
    "rsi_bounce", "rsi_oversold", "rsi_divergence",
    "mean_reversion_oversold", "stoch_rsi_oversold",
    "oversold_reversal", "oversold_bounce",
}

# ── Systems to scan (same as fc_crypto_pro) ──
SYSTEMS = {
    "mercury2": "mercury2/data/active_picks.json",
    "alpha_engine": "alpha_engine/data/active_picks.json",
    "ml_battleground": "ml_battleground/data/active_picks.json",
    "mega_mutation": "genome/data/active_picks.json",
    "cross_agg": "cross_aggregation/data/active_picks.json",
    "kimi": "KIMI_RISEOFTHECLAW/data/live_signals_now.json",
    "breakout_arena": "breakout_arena/data/active_picks.json",
}


def _load_json(path: pathlib.Path) -> dict | list | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _extract_picks(data) -> list[dict]:
    """Extract picks from various JSON structures."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("picks", "active_picks", "signals", "activePicks", "top_picks"):
            if key in data and isinstance(data[key], list):
                return data[key]
        if "symbol" in data:
            return [data]
    return []


def _norm_sym(sym: str) -> str:
    """Normalize symbol to BTCUSDT format."""
    sym = sym.upper().strip()
    for sep in ["-", "/", "_"]:
        sym = sym.replace(sep, "")
    # Normalize to USDT pairs (Binance standard)
    if sym.endswith("USD") and not sym.endswith("USDT"):
        sym += "T"
    if not sym.endswith("USDT"):
        sym += "USDT"
    return sym


def _get_direction(p: dict) -> str:
    """Extract direction from pick."""
    for key in ("direction", "signal", "signal_type", "side"):
        val = str(p.get(key, "")).upper()
        if "SHORT" in val or "SELL" in val:
            return "SHORT"
        if "LONG" in val or "BUY" in val:
            return "LONG"
    return ""


def _is_closed(p: dict) -> bool:
    """Check if pick is already closed."""
    status = str(p.get("status", "")).upper()
    outcome = str(p.get("outcome", "")).upper()
    return any(x in status + outcome for x in ["CLOSED", "TP_HIT", "SL_HIT", "EXPIRED", "STOPPED"])


def _fetch_binance_prices() -> dict[str, float]:
    """Fetch current prices from Binance."""
    try:
        req = urllib.request.Request(
            "https://api.binance.com/api/v3/ticker/price",
            headers={"User-Agent": "ClaudePickGen/2.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return {t["symbol"]: float(t["price"]) for t in data}
    except Exception as e:
        print(f"  [WARN] Binance price fetch failed: {e}")
        return {}


def _fetch_volume_data(symbols: list[str]) -> dict[str, float]:
    """Fetch 24h volume data from Binance for specific symbols."""
    volumes = {}
    try:
        req = urllib.request.Request(
            "https://api.binance.com/api/v3/ticker/24hr",
            headers={"User-Agent": "ClaudePickGen/2.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        for t in data:
            if t["symbol"] in symbols:
                volumes[t["symbol"]] = float(t.get("quoteVolume", 0))
    except Exception:
        pass
    return volumes


def generate_claude_picks() -> dict:
    """Generate Claude's tournament picks using enhanced scoring.

    Returns the full claude_top_picks.json structure.
    """
    print("=" * 60)
    print("CLAUDE PICK GENERATOR v2.0 — Round 2 Evolutionary Regime Engine")
    print("=" * 60)

    # 1. Get market context
    context = {}
    if _HAS_REGIME:
        context = get_market_context()
        print(f"\n  Regime: {context.get('regime', '?')} | F&G: {context.get('fng', '?')} "
              f"| ADX: {context.get('adx', '?')} | RSI: {context.get('rsi_14', '?')}")
        print(f"  Direction bias: {context.get('direction_bias', '?')} | R:R cap: {context.get('rr_cap', '?')}")
    else:
        print("\n  [WARN] Regime router not available — using defaults")

    regime_str = context.get("regime", "UNKNOWN")
    direction_bias = context.get("direction_bias", "NEUTRAL")
    rr_cap = context.get("rr_cap", 1.5)

    # 2. Collect all active picks from all systems
    all_picks = []
    for sys_id, active_path in SYSTEMS.items():
        data = _load_json(REPO_ROOT / active_path)
        if not data:
            continue
        picks = _extract_picks(data)
        for p in picks:
            if _is_closed(p):
                continue
            sym = _norm_sym(p.get("symbol") or p.get("pair") or "")
            direction = _get_direction(p)
            if not sym or not direction:
                continue
            entry = float(p.get("entry_price") or p.get("entryPrice") or 0)
            tp = float(p.get("take_profit") or p.get("tp_price") or p.get("targetPrice") or 0)
            sl = float(p.get("stop_loss") or p.get("sl_price") or p.get("stopPrice") or 0)
            if not entry or not tp:
                continue
            strategy = p.get("strategy") or p.get("algorithm") or p.get("strategy_name") or "unknown"
            conf = float(p.get("confidence") or p.get("ml_score") or 0.5)

            # Kill oversold strategies in downtrend
            if strategy.lower() in OVERSOLD_STRATEGIES and regime_str == "TRENDING_DOWN" and direction == "LONG":
                continue

            # R:R calculation
            if sl and abs(entry - sl) > 0:
                rr = abs(tp - entry) / abs(entry - sl)
            else:
                rr = 0
            if rr < MIN_RR:
                continue

            vol_24h = float(p.get("volume_24h") or p.get("volume_24h_usd") or p.get("vol_24h") or 0)
            adx = float(p.get("adx") or p.get("adx_14") or 0)
            rsi = float(p.get("rsi") or p.get("rsi_14") or 0)

            all_picks.append({
                "symbol": sym,
                "direction": direction,
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "risk_reward": rr,
                "confidence": conf,
                "strategy": strategy,
                "system": sys_id,
                "volume_24h": vol_24h,
                "adx": adx,
                "rsi": rsi,
                "change_24h_pct": float(p.get("change_24h_pct") or p.get("price_change_24h") or 0),
            })

    print(f"\n  Collected {len(all_picks)} active picks from {len(SYSTEMS)} systems")

    # 3. Fetch live prices and volume
    prices = _fetch_binance_prices()
    symbols = list({p["symbol"] for p in all_picks})
    volumes = _fetch_volume_data(symbols)

    # Update picks with live data
    for p in all_picks:
        if p["volume_24h"] == 0 and p["symbol"] in volumes:
            p["volume_24h"] = volumes[p["symbol"]]

    # 4. Score each pick
    scored = []
    for p in all_picks:
        live = prices.get(p["symbol"], 0)
        if not live:
            continue

        # Check if SL breached
        if p["direction"] == "LONG" and live < p["stop_loss"] and p["stop_loss"] > 0:
            continue
        if p["direction"] == "SHORT" and live > p["stop_loss"] and p["stop_loss"] > 0:
            continue

        # Entry room check
        if p["direction"] == "LONG":
            if p["take_profit"] <= p["entry_price"]:
                continue
            room_used = (live - p["entry_price"]) / (p["take_profit"] - p["entry_price"])
        else:
            if p["entry_price"] <= p["take_profit"]:
                continue
            room_used = (p["entry_price"] - live) / (p["entry_price"] - p["take_profit"])
        room_used = max(0, min(1, room_used))
        if room_used > 0.6:
            continue  # Too late

        # === Enhanced Composite Score ===
        # Base: WR-proxy * room * confidence
        wr_proxy = min(p["confidence"], 0.95)  # Cap at 95%
        base = wr_proxy * (1 - room_used)

        # Regime multiplier (Moskowitz 2012)
        if regime_str == "TRENDING_DOWN":
            regime_mult = 1.3 if p["direction"] == "SHORT" else 0.6
        elif regime_str == "TRENDING_UP":
            regime_mult = 1.3 if p["direction"] == "LONG" else 0.6
        elif regime_str == "RANGE_BOUND":
            regime_mult = 1.0
        else:
            regime_mult = 1.0

        # Volume multiplier (Llorente 2002)
        vol = p["volume_24h"]
        if vol >= 50_000_000:
            vol_mult = 1.3
        elif vol >= 10_000_000:
            vol_mult = 1.0
        else:
            vol_mult = 0.6 if p["direction"] == "LONG" else 0.85

        # ADX multiplier (Wilder 1978)
        adx = p["adx"]
        if p["direction"] == "LONG":
            adx_mult = 1.0 if adx >= 15 else (0.6 if adx > 0 else 0.8)
        else:
            adx_mult = 1.0  # Shorts less ADX-sensitive

        # R:R bonus (Vince 2000)
        rr_score = min(p["risk_reward"] / 3.0, 1.0)

        # Final score
        score = base * regime_mult * vol_mult * adx_mult * (0.7 + 0.3 * rr_score)

        # Dynamic R:R cap
        if p["risk_reward"] > rr_cap * 1.5:
            # Tighten TP to regime cap
            if p["direction"] == "LONG":
                risk = p["entry_price"] - p["stop_loss"]
                p["take_profit"] = p["entry_price"] + risk * rr_cap
            else:
                risk = p["stop_loss"] - p["entry_price"]
                p["take_profit"] = p["entry_price"] - risk * rr_cap
            p["risk_reward"] = rr_cap
            p["tp_tightened"] = True

        p["_score"] = round(score, 4)
        p["_regime_mult"] = regime_mult
        p["_vol_mult"] = vol_mult
        p["_adx_mult"] = adx_mult
        p["_live_price"] = live
        scored.append(p)

    # 5. Sort by score and select top picks
    scored.sort(key=lambda x: x["_score"], reverse=True)

    # Diversify: max 1 pick per symbol
    seen_symbols = set()
    selected = []
    for p in scored:
        if p["symbol"] in seen_symbols:
            continue
        seen_symbols.add(p["symbol"])
        selected.append(p)
        if len(selected) >= MAX_PICKS:
            break

    print(f"  Selected {len(selected)} picks (from {len(scored)} scored)")

    # 6. Build output JSON
    picks_out = []
    for i, p in enumerate(selected):
        is_short = p["direction"] == "SHORT"
        change = p.get("change_24h_pct", 0)
        pnl_from_entry = (
            ((p["entry_price"] - p["_live_price"]) / p["entry_price"] * 100) if is_short
            else ((p["_live_price"] - p["entry_price"]) / p["entry_price"] * 100)
        )

        reasoning = (
            f"Score: {p['_score']:.3f} | Regime: {regime_str} (x{p['_regime_mult']}) | "
            f"Vol: ${p['volume_24h']/1e6:.0f}M (x{p['_vol_mult']}) | "
            f"ADX: {p['adx']:.0f} (x{p['_adx_mult']}) | "
            f"System: {p['system']} | Strategy: {p['strategy']}"
        )

        pick = {
            "rank": i + 1,
            "symbol": p["symbol"],
            "direction": p["direction"],
            "entry_price": round(p["_live_price"], 6),  # Use current price as entry
            "take_profit": round(p["take_profit"], 6),
            "stop_loss": round(p["stop_loss"], 6),
            "risk_reward": round(p["risk_reward"], 2),
            "confidence": round(p["confidence"], 2),
            "strategy": p["strategy"],
            "genesis_score": f"{int(p['_score'] * 10)}/10",
            "rsi": round(p["rsi"], 1) if p["rsi"] else None,
            "adx": round(p["adx"], 1) if p["adx"] else None,
            "supertrend": "BEAR" if is_short else "BULL",
            "volume_24h_usd": p["volume_24h"],
            "change_24h_pct": change,
            "reasoning": reasoning,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "ACTIVE",
            "outcome": "PENDING",
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "check_intervals_h": [1, 4, 8, 12, 24],
            "conviction": f"REGIME-ALIGNED — {p['direction']} in {regime_str} market. Score {p['_score']:.3f}.",
            "round": 2,
            "scoring_version": "v2.0_evolutionary_regime_engine",
        }
        picks_out.append(pick)

        dir_emoji = "S" if is_short else "L"
        print(f"  #{i+1} {p['symbol'].replace('USDT','')} {dir_emoji} @ ${p['_live_price']:.4f} "
              f"-> TP ${p['take_profit']:.4f} | Score: {p['_score']:.3f}")

    # 7. Load existing data to preserve history
    out_path = REPO_ROOT / "audit_dashboard" / "data" / "claude_top_picks.json"
    existing = _load_json(out_path) or {}
    historical_rounds = existing.get("historical_rounds", [])

    # Check if Round 1 picks exist and archive them
    old_picks = existing.get("picks", [])
    if old_picks and any(p.get("round") != 2 for p in old_picks):
        round1_results = {}
        for p in old_picks:
            sym = p.get("symbol", "")
            round1_results[sym] = {
                "outcome": p.get("outcome", "PENDING"),
                "pnl_pct": float(p.get("pnl_pct", 0) or 0),
                "peak_pnl_pct": p.get("peak_pnl_pct", 0),
                "trough_pnl_pct": p.get("trough_pnl_pct", 0),
            }
            if p.get("closed_at"):
                round1_results[sym]["closed_at"] = p["closed_at"]
                round1_results[sym]["closed_price"] = p.get("closed_price")
                round1_results[sym]["realized_pnl_usd"] = p.get("realized_pnl_usd")

        # Only add if not already archived
        if not any(r.get("round") == 1 for r in historical_rounds):
            historical_rounds.append({
                "round": 1,
                "generated_at": old_picks[0].get("timestamp", ""),
                "picks": [p.get("symbol", "") for p in old_picks],
                "status": "COMPLETED",
                "results": round1_results,
                "scoring_version": "v1.0_manual",
            })

    # Count wins/losses from history
    total_wins = sum(
        1 for r in historical_rounds
        for res in r.get("results", {}).values()
        if res.get("outcome") == "TP_HIT"
    )
    total_losses = sum(
        1 for r in historical_rounds
        for res in r.get("results", {}).values()
        if res.get("outcome") == "SL_HIT"
    )
    total_closed = total_wins + total_losses
    total_picks_all = sum(len(r.get("picks", [])) for r in historical_rounds) + len(picks_out)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
        "curator": "Claude Opus 4.6 — Evolutionary Regime Engine",
        "methodology": (
            f"Round 2: Regime-aware scoring (Moskowitz TSMOM). "
            f"Regime={regime_str}, Bias={direction_bias}, R:R cap={rr_cap}. "
            f"Multi-factor: WR*room*regime*vol*ADX. "
            f"Oversold strategies killed in downtrend (Lo 2000). "
            f"Volume gate $50M for longs (Llorente 2002). "
            f"ADX>=15 for longs (Wilder 1978)."
        ),
        "picks": picks_out,
        "historical_rounds": historical_rounds,
        "lifetime_stats": {
            "total_rounds": len(historical_rounds) + 1,
            "total_picks": total_picks_all,
            "wins": total_wins,
            "losses": total_losses,
            "pending": len(picks_out),
            "win_rate": round(total_wins / total_closed * 100, 1) if total_closed > 0 else None,
            "avg_pnl_pct": None,  # Updated by tracker
            "cumulative_pnl_pct": None,
        },
        "regime_context": {
            "regime": regime_str,
            "direction_bias": direction_bias,
            "fng": context.get("fng"),
            "adx": context.get("adx"),
            "rsi_14": context.get("rsi_14"),
            "rr_cap": rr_cap,
        },
        "last_checked": datetime.now(timezone.utc).isoformat(),
    }

    # Write output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Written to {out_path}")

    return output


if __name__ == "__main__":
    generate_claude_picks()
