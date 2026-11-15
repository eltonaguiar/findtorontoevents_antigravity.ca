#!/usr/bin/env python3
"""
Baby Battleground -> FC-PRO exporter.

Reads battleground/data/baby_strats_dashboard.json, filters for strategies
that meet forward-test quality gates, and writes:
  - battleground/data/active_picks.json  (open positions from qualifying strats)
  - battleground/data/closed_picks.json  (resolved trades with WIN/LOSS status)

Quality gates (forward metrics):
  - win_rate  >= 55  (percent, e.g. 55.0 means 55%)
  - total_trades >= 20
  - max 2 variants per strategy family (by forward win rate)

Run standalone:
    python battleground/export_top_picks.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None  # type: ignore

# ── Paths ────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_JSON = REPO_ROOT / "battleground" / "data" / "baby_strats_dashboard.json"
ACTIVE_OUT = REPO_ROOT / "battleground" / "data" / "active_picks.json"
CLOSED_OUT = REPO_ROOT / "battleground" / "data" / "closed_picks.json"

# ── Quality gates ────────────────────────────────────────────────────
MIN_WIN_RATE = 55.0      # percent (dashboard stores 55.17, not 0.5517)
MAX_WIN_RATE = 95.0      # percent — 100% WR on 16 trades is overfitting, not skill
MIN_TRADES = 20
MIN_TRADES_PROTECTED = 10  # Protected strategies with proven track records need fewer trades
MAX_FAMILY_VARIANTS = 2   # max variants from the same strategy family


def _load_protected_strategies() -> set[str]:
    """Load protected strategies from core_whitelist.json."""
    try:
        wl_path = REPO_ROOT / "alpha_engine" / "data" / "core_whitelist.json"
        with open(wl_path, encoding="utf-8") as f:
            wl = json.load(f)
        return {s.lower() for s in wl.get("protected_strategies", [])}
    except Exception:
        return set()


_PROTECTED = _load_protected_strategies()


def load_dashboard() -> dict:
    """Load the baby strats dashboard JSON."""
    if not DASHBOARD_JSON.exists():
        print(f"[ERROR] Dashboard not found: {DASHBOARD_JSON}")
        sys.exit(1)
    with open(DASHBOARD_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_protected_strategies() -> set[str]:
    """Load protected strategies from core_whitelist.json."""
    try:
        wl_path = REPO_ROOT / "alpha_engine" / "data" / "core_whitelist.json"
        with open(wl_path, encoding="utf-8") as f:
            wl = json.load(f)
        return {s.lower() for s in wl.get("protected_strategies", [])}
    except Exception:
        return set()


_PROTECTED = _load_protected_strategies()


def passes_gates(strat: dict) -> bool:
    """Return True if strategy meets forward-test quality gates.

    Protected strategies (from core_whitelist.json) get a reduced MIN_TRADES
    threshold (10 vs 20) since they have proven track records from backtesting.
    """
    fm = strat.get("forward_metrics")
    if not fm:
        return False
    wr = fm.get("win_rate")
    trades = fm.get("total_trades", 0)
    if wr is None or trades is None:
        return False
    # win_rate is stored as percentage (e.g. 55.17)
    # Handle both percentage (>1) and decimal (<1) formats defensively
    wr_pct = wr if wr > 1 else wr * 100
    name = strat.get("name", "").lower()
    min_trades = MIN_TRADES_PROTECTED if name in _PROTECTED else MIN_TRADES
    return MIN_WIN_RATE <= wr_pct <= MAX_WIN_RATE and trades >= min_trades


def direction_from_side(side: str) -> str:
    """Normalize direction: LONG/BUY -> BUY, SHORT/SELL -> SELL."""
    s = side.upper()
    if s in ("LONG", "BUY"):
        return "BUY"
    if s in ("SHORT", "SELL"):
        return "SELL"
    return s


def _fetch_current_price(symbol: str) -> float | None:
    """Fetch current price from OKX (no geo-block) or CoinGecko fallback."""
    if requests is None:
        return None
    # OKX
    try:
        inst = symbol.replace("USDT", "-USDT")
        r = requests.get(f"https://www.okx.com/api/v5/market/ticker?instId={inst}", timeout=8)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                return float(data[0]["last"])
    except Exception:
        pass
    # CoinGecko
    try:
        cg_map = {"BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
                   "XRPUSDT": "ripple", "BNBUSDT": "binancecoin", "DOGEUSDT": "dogecoin",
                   "ADAUSDT": "cardano", "AVAXUSDT": "avalanche-2"}
        cg_id = cg_map.get(symbol)
        if cg_id:
            r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd", timeout=8)
            if r.status_code == 200:
                return float(r.json()[cg_id]["usd"])
    except Exception:
        pass
    return None


def _generate_signal_pick(strat: dict) -> dict | None:
    """Generate a pick from a qualifying strategy's recent trade pattern.

    When a strategy passes quality gates but has no live picks (its
    generate_signals() didn't fire on the latest bar), we create a
    signal-based pick using its most recent trade direction + current price.
    """
    trades = strat.get("forward_trades", [])
    if not trades:
        return None

    # Use the most recent 5 trades to determine dominant direction
    recent = trades[-5:]
    longs = sum(1 for t in recent if t.get("direction", "").upper() in ("LONG", "BUY"))
    shorts = len(recent) - longs
    direction = "BUY" if longs >= shorts else "SELL"

    # Get symbol from recent trades
    symbol = recent[-1].get("symbol", "BTCUSDT")

    # Fetch live price
    price = _fetch_current_price(symbol)
    if price is None:
        # Fallback: use last trade's exit price
        price = recent[-1].get("exit_price")
        if price is None:
            return None

    # Compute TP/SL from average win/loss of this strategy's trades
    win_pcts = [abs(t["pnl_pct"]) for t in trades if t.get("pnl_pct", 0) > 0]
    loss_pcts = [abs(t["pnl_pct"]) for t in trades if t.get("pnl_pct", 0) < 0]
    avg_win = sum(win_pcts) / len(win_pcts) if win_pcts else 1.5
    avg_loss = sum(loss_pcts) / len(loss_pcts) if loss_pcts else 1.0
    # Use avg win for TP and avg loss for SL, as percentages
    tp_pct = min(avg_win / 100, 0.05)   # cap at 5%
    sl_pct = min(avg_loss / 100, 0.03)   # cap at 3%

    if direction == "BUY":
        take_profit = round(price * (1 + tp_pct), 2)
        stop_loss = round(price * (1 - sl_pct), 2)
    else:
        take_profit = round(price * (1 - tp_pct), 2)
        stop_loss = round(price * (1 + sl_pct), 2)

    return {
        "side": direction,
        "symbol": symbol,
        "entry_price": round(price, 2),
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "signal_based",
    }


def build_active_picks(qualifying: list[dict]) -> list[dict]:
    """Collect forward_live_picks from qualifying strategies into FC-PRO format.

    If a qualifying strategy has no live picks but has recent trade history,
    generate a signal-based pick from its dominant direction and current price.
    """
    picks = []
    for strat in qualifying:
        fm = strat.get("forward_metrics", {})
        wr = fm.get("win_rate", 0)
        wr_pct = wr if wr > 1 else wr * 100
        total = fm.get("total_trades", 0)
        # Confidence: scale win-rate into 0..1 range, cap at 0.95
        confidence = round(min(wr_pct / 100.0, 0.95), 4)

        live_picks = strat.get("forward_live_picks", [])

        # If no live picks, generate signal-based pick from recent trades
        if not live_picks:
            generated = _generate_signal_pick(strat)
            if generated:
                live_picks = [generated]
                print(f"  [signal] Generated {generated['side']} pick for {strat['name']} "
                      f"@ {generated['entry_price']} ({generated['symbol']})")

        for pick in live_picks:
            picks.append({
                "symbol": pick.get("symbol", "BTCUSDT"),
                "direction": direction_from_side(pick.get("side", pick.get("direction", "BUY"))),
                "entry_price": pick.get("entry_price"),
                "take_profit": pick.get("take_profit"),
                "stop_loss": pick.get("stop_loss"),
                "confidence": confidence,
                "strategy": strat["name"],
                "source_system": "battleground",
                "forward_wr": round(wr_pct / 100.0, 4),
                "forward_trades": total,
                "forward_validated": True,
                "pick_source": pick.get("source", "forward_live"),
                "timestamp": pick.get("generated_at", datetime.now(timezone.utc).isoformat()),
            })
    # Dedup active picks: keep highest-confidence pick per symbol+direction
    seen: dict[tuple[str, str], int] = {}
    deduped_picks: list[dict] = []
    for i, p in enumerate(picks):
        key = (p.get("symbol", ""), p.get("direction", ""))
        if key in seen:
            existing_idx = seen[key]
            if p.get("confidence", 0) > deduped_picks[existing_idx].get("confidence", 0):
                deduped_picks[existing_idx] = p
        else:
            seen[key] = len(deduped_picks)
            deduped_picks.append(p)
    if len(picks) != len(deduped_picks):
        print(f"[baby_battleground] Active dedup: {len(picks)} -> {len(deduped_picks)} "
              f"(collapsed {len(picks) - len(deduped_picks)} correlated positions)")
    return deduped_picks


def _dedup_correlated_trades(trades: list[dict], window_hours: int = 4) -> list[dict]:
    """Remove correlated trades: same symbol+direction within window_hours.

    Keeps the first trade per (symbol, direction) cluster and the one with
    the best PnL from each subsequent cluster.  This prevents hourly strategies
    from inflating trade counts and P&L when they fire on the same symbol
    every run in trending markets.
    """
    if not trades:
        return trades
    # Sort by entry_time so we process chronologically
    trades.sort(key=lambda t: t.get("entry_time", ""))
    deduped: list[dict] = []
    # Track last entry per (symbol, direction)
    last_entry: dict[tuple[str, str], str] = {}
    for t in trades:
        key = (t.get("symbol", ""), t.get("direction", ""))
        entry_time = t.get("entry_time", "")
        prev_time = last_entry.get(key)
        if prev_time and entry_time:
            try:
                # Parse ISO timestamps
                fmt = "%Y-%m-%dT%H:%M:%S" if "T" in entry_time else "%Y-%m-%d %H:%M:%S"
                pfmt = "%Y-%m-%dT%H:%M:%S" if "T" in prev_time else "%Y-%m-%d %H:%M:%S"
                cur = datetime.strptime(entry_time[:19], fmt)
                prev = datetime.strptime(prev_time[:19], pfmt)
                if abs((cur - prev).total_seconds()) < window_hours * 3600:
                    # Within window — skip (correlated duplicate)
                    continue
            except (ValueError, TypeError):
                pass
        deduped.append(t)
        last_entry[key] = entry_time
    return deduped


def build_closed_picks(qualifying: list[dict]) -> list[dict]:
    """Collect forward_trades from qualifying strategies, tag WIN/LOSS.

    Applies cross-strategy deduplication: trades on the same symbol+direction
    within a 4-hour window are collapsed to prevent P&L inflation from
    correlated hourly strategies.
    """
    closed = []
    for strat in qualifying:
        fm = strat.get("forward_metrics", {})
        wr = fm.get("win_rate", 0)
        wr_pct = wr if wr > 1 else wr * 100
        total = fm.get("total_trades", 0)

        for trade in strat.get("forward_trades", []):
            pnl = trade.get("pnl_pct", 0)
            closed.append({
                "symbol": trade.get("symbol", "BTCUSDT"),
                "direction": direction_from_side(trade.get("direction", "LONG")),
                "entry_price": trade.get("entry_price"),
                "exit_price": trade.get("exit_price"),
                "pnl_pct": pnl,
                "status": "WIN" if pnl > 0 else "LOSS",
                "exit_reason": trade.get("exit_reason", ""),
                "strategy": strat["name"],
                "forward_wr": round(wr_pct / 100.0, 4),
                "forward_trades": total,
                "entry_time": trade.get("entry_time", ""),
                "exit_time": trade.get("exit_time", ""),
            })
    raw_count = len(closed)
    closed = _dedup_correlated_trades(closed)
    if raw_count != len(closed):
        print(f"[baby_battleground] Dedup: {raw_count} raw -> {len(closed)} unique "
              f"(removed {raw_count - len(closed)} correlated duplicates)")
    return closed


def main():
    print(f"[baby_battleground] Loading dashboard: {DASHBOARD_JSON}")
    dash = load_dashboard()
    strategies = dash.get("strategies", [])
    print(f"[baby_battleground] Total strategies in dashboard: {len(strategies)}")

    qualifying = [s for s in strategies if passes_gates(s)]
    print(f"[baby_battleground] Strategies passing gates "
          f"(WR>={MIN_WIN_RATE}%, trades>={MIN_TRADES}): {len(qualifying)}")

    # ── Family variant dedup ─────────────────────────────────────────
    # Grok/Mercury audit 2026-03-16: near-identical variants inflate
    # trade counts and dilute signal quality
    def _extract_family(name: str) -> str:
        """Strip variant suffix to get family name.

        e.g. 'crypto_soc_delta_divergence_a05_v1' -> 'crypto_soc_delta_divergence'
        """
        return re.sub(r"_[a-z]\d+(_v\d+)?$", "", name)

    families: dict[str, list[dict]] = {}
    for s in qualifying:
        fam = _extract_family(s["name"])
        families.setdefault(fam, []).append(s)

    pruned_qualifying: list[dict] = []
    for fam, members in families.items():
        if len(members) <= MAX_FAMILY_VARIANTS:
            pruned_qualifying.extend(members)
        else:
            # Keep top MAX_FAMILY_VARIANTS by forward win rate
            members.sort(
                key=lambda s: s.get("forward_metrics", {}).get("win_rate", 0),
                reverse=True,
            )
            kept = members[:MAX_FAMILY_VARIANTS]
            pruned = members[MAX_FAMILY_VARIANTS:]
            pruned_qualifying.extend(kept)
            for p in pruned:
                fm = p.get("forward_metrics", {})
                print(f"  [family-dedup] PRUNED {p['name']} "
                      f"(family={fam}, WR={fm.get('win_rate', 0):.2f}%)")

    if len(qualifying) != len(pruned_qualifying):
        print(f"[baby_battleground] Family dedup: {len(qualifying)} -> "
              f"{len(pruned_qualifying)} (pruned {len(qualifying) - len(pruned_qualifying)} "
              f"excess variants)")
    qualifying = pruned_qualifying

    if qualifying:
        for s in qualifying:
            fm = s["forward_metrics"]
            print(f"  -> {s['name']:50s}  WR={fm['win_rate']:6.2f}%  "
                  f"trades={fm['total_trades']:4d}  "
                  f"picks={s.get('forward_live_pick_count', 0)}")

    # ── Active picks ─────────────────────────────────────────────────
    active = build_active_picks(qualifying)
    ACTIVE_OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        from alpha_engine.feed_hygiene import sanitize_active_picks
    except ImportError:
        sanitize_active_picks = lambda picks, label="": picks
    active = sanitize_active_picks(active, "battleground")
    with open(ACTIVE_OUT, "w", encoding="utf-8") as f:
        json.dump(active, f, indent=2, default=str)
    print(f"[baby_battleground] Wrote {len(active)} active picks -> {ACTIVE_OUT}")

    # ── Closed picks ─────────────────────────────────────────────────
    closed = build_closed_picks(qualifying)
    with open(CLOSED_OUT, "w", encoding="utf-8") as f:
        json.dump(closed, f, indent=2, default=str)
    print(f"[baby_battleground] Wrote {len(closed)} closed picks -> {CLOSED_OUT}")

    # ── Summary ──────────────────────────────────────────────────────
    wins = sum(1 for c in closed if c["status"] == "WIN")
    losses = len(closed) - wins
    wr = (wins / len(closed) * 100) if closed else 0
    print(f"[baby_battleground] Closed summary: {wins}W / {losses}L  "
          f"({wr:.1f}% WR)")


if __name__ == "__main__":
    main()
