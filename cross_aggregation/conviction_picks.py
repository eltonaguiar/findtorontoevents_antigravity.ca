#!/usr/bin/env python3
"""
Conviction Picks — Ultra-Selective Discord Alert
=================================================
Only fires for signals that pass ALL quality gates simultaneously.
Designed for picks "actually worth putting money into."

Philosophy: Better to miss 10 good trades than take 1 bad one.

Requirements for a Conviction Pick:
  1. System WR >= 55% with >= 15 closed trades (proven edge)
  2. Strategy WR >= 50% with >= 10 trades (strategy-level proof)
  3. R:R >= 2.0 (asymmetric payoff)
  4. >= 2 independent systems agree on symbol + direction
  5. Entry room >= 50% remaining (not too late)
  6. Regime-aligned (F&G + BTC momentum gate)
  7. Not in kill-list or stale (> 30 min)
  8. DSR gate passes (statistical significance)
  9. Max 3 picks per run (concentration = conviction)

Runs every 30 min alongside fc_crypto_pro.
Posts to DISCORD_WEBHOOK_CONVICTION (new channel #conviction-picks).
"""
from __future__ import annotations

import json
import math
import os
import pathlib
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Any

# ── Config ──────────────────────────────────────────────────────
MIN_SYSTEM_WR = 0.55          # System must have >= 55% WR
MIN_SYSTEM_TRADES = 15        # System must have >= 15 closed trades
MIN_STRATEGY_WR = 0.50        # Strategy must have >= 50% WR
MIN_STRATEGY_TRADES = 10      # Strategy must have >= 10 closed trades
MIN_RISK_REWARD = 2.0         # R:R must be >= 2.0 (asymmetric payoff)
MIN_ENTRY_ROOM = 0.50         # At least 50% room to TP remaining
MAX_SIGNAL_AGE_MIN = 30       # Max 30 min signal age
MIN_CONSENSUS_SYSTEMS = 2     # >= 2 systems must agree
MAX_PICKS_PER_RUN = 3         # Max 3 per run — concentration = conviction (quant audit 2026-04-07)
MIN_CONFIDENCE = 0.60         # Minimum raw confidence
MAX_CRYPTO_SAME_DIR = 2       # Max 2 same-direction crypto picks (portfolio diversification)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Reuse system registry from fc_crypto_pro
try:
    from cross_aggregation.fc_crypto_pro import (
        SYSTEMS, STRATEGY_KILL_LIST, _load_json, _extract_picks,
        _norm_sym, _get_direction, _is_closed, _is_win,
        _is_crypto_symbol, _fetch_fear_greed, _fetch_btc_momentum,
        _fetch_current_prices, _regime_direction_gate,
        _compute_rolling_wr, ROLLING_WR_SUSPEND,
    )
except ImportError:
    print("[FATAL] Cannot import fc_crypto_pro — conviction_picks requires it", file=sys.stderr)
    sys.exit(1)

# DSR gate
try:
    from cross_aggregation.dsr_gate import passes_dsr_gate, compute_system_avg_gains
    _HAS_DSR = True
except ImportError:
    _HAS_DSR = False

# Regime router
try:
    from cross_aggregation.regime_router import get_current_regime, should_generate_signal as _regime_check
    _HAS_REGIME = True
except ImportError:
    _HAS_REGIME = False

# Institutional overlay (Bayesian scoring)
try:
    from trading.institutional_overlay import BayesianEdgeScorer
    _HAS_BAYESIAN = True
except ImportError:
    _HAS_BAYESIAN = False


# ── Discord ─────────────────────────────────────────────────────

WEBHOOK_CONVICTION = os.environ.get("DISCORD_WEBHOOK_CONVICTION", "")
WEBHOOK_FALLBACK = os.environ.get("DISCORD_WEBHOOK_PROPICKS", "")

# Dedup state
DEDUP_FILE = REPO_ROOT / "cross_aggregation" / "data" / "conviction_sent.json"
DEDUP_COOLDOWN_HOURS = 4  # Don't re-alert same symbol+direction within 4 hours


def _load_dedup() -> dict:
    try:
        with open(DEDUP_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_dedup(state: dict):
    DEDUP_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DEDUP_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _is_duplicate(sym: str, direction: str, dedup: dict) -> bool:
    key = f"{sym}_{direction}"
    last = dedup.get(key)
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - last_dt).total_seconds() < DEDUP_COOLDOWN_HOURS * 3600
    except Exception:
        return False


def _mark_sent(sym: str, direction: str, dedup: dict):
    key = f"{sym}_{direction}"
    dedup[key] = datetime.now(timezone.utc).isoformat()


# ── Core Logic ──────────────────────────────────────────────────

def compute_strategy_stats() -> dict[str, dict]:
    """Compute per-strategy win/loss/WR across ALL closed picks from ALL systems."""
    stats: dict[str, dict] = {}
    for sys_id, sys_info in SYSTEMS.items():
        closed_path = sys_info.get("closed")
        if not closed_path:
            continue
        try:
            with open(REPO_ROOT / closed_path, "r", encoding="utf-8") as f:
                closed = json.load(f)
            if not isinstance(closed, list):
                closed = _extract_picks(closed)
            for p in closed:
                strat = (p.get("strategy") or p.get("algorithm")
                         or p.get("strategy_name") or "unknown").lower()
                if strat not in stats:
                    stats[strat] = {"wins": 0, "losses": 0, "total": 0}
                w = _is_win(p)
                if w is True:
                    stats[strat]["wins"] += 1
                    stats[strat]["total"] += 1
                elif w is False:
                    stats[strat]["losses"] += 1
                    stats[strat]["total"] += 1
        except Exception:
            continue
    for s in stats.values():
        s["wr"] = s["wins"] / s["total"] if s["total"] > 0 else 0.0
    return stats


def compute_system_wrs() -> dict[str, dict]:
    """Compute system-level WR from closed picks."""
    results = {}
    for sys_id, sys_info in SYSTEMS.items():
        wins, losses = 0, 0
        if sys_info.get("closed"):
            closed_data = _load_json(REPO_ROOT / sys_info["closed"])
            if closed_data:
                for p in (_extract_picks(closed_data) if isinstance(closed_data, dict) else closed_data):
                    w = _is_win(p)
                    if w is True:
                        wins += 1
                    elif w is False:
                        losses += 1
        total = wins + losses
        wr = wins / total if total > 0 else 0.0
        results[sys_id] = {
            "name": sys_info["name"], "wins": wins, "losses": losses,
            "total": total, "wr": wr,
            "qualified": total >= MIN_SYSTEM_TRADES and wr >= MIN_SYSTEM_WR,
        }
    return results


def collect_conviction_picks(
    system_wrs: dict,
    strategy_stats: dict,
    current_prices: dict,
    fear_greed: int | None = None,
    btc_momentum: dict | None = None,
    regime: dict | None = None,
) -> list[dict]:
    """Collect picks that pass ALL conviction gates."""
    candidates: list[dict] = []
    btc_momentum = btc_momentum or {"pct_24h": 0, "regime": "neutral"}

    for sys_id, sys_info in SYSTEMS.items():
        tier = sys_info.get("tier", "watch")
        if tier in ("demoted", "retired"):
            continue

        wr_data = system_wrs.get(sys_id, {})

        # Gate 1: System WR >= 55% with >= 15 trades
        if not wr_data.get("qualified", False):
            continue

        # Gate: Rolling WR guard
        rolling = _compute_rolling_wr(sys_id)
        if rolling is not None and rolling < ROLLING_WR_SUSPEND:
            print(f"  [CONVICTION] {sys_info['name']} rolling WR {rolling*100:.0f}% — suppressed")
            continue

        # Gate: DSR (statistical significance)
        if _HAS_DSR and wr_data.get("total", 0) >= 20:
            closed_path = sys_info.get("closed")
            if closed_path:
                closed_data = _load_json(REPO_ROOT / closed_path)
                if closed_data:
                    closed_list = _extract_picks(closed_data) if isinstance(closed_data, dict) else closed_data
                    avg_gain, avg_loss = compute_system_avg_gains(closed_list)
                    dsr_pass, dsr_reason = passes_dsr_gate(
                        sys_id, wr_data["wins"], wr_data["losses"], avg_gain, avg_loss
                    )
                    if not dsr_pass:
                        print(f"  [CONVICTION-DSR] {sys_info['name']} BLOCKED: {dsr_reason}")
                        continue

        # Load active picks
        active_data = _load_json(REPO_ROOT / sys_info["active"])
        if not active_data:
            continue

        for p in _extract_picks(active_data):
            if _is_closed(p):
                continue

            entry = float(p.get("entry_price") or p.get("entryPrice") or 0)
            tp = float(p.get("take_profit") or p.get("tp_price") or p.get("targetPrice") or p.get("tp1_price") or 0)
            sl = float(p.get("stop_loss") or p.get("sl_price") or p.get("stopPrice") or 0)
            if not entry or not tp:
                continue

            sym = _norm_sym(p.get("symbol") or p.get("pair") or "")
            direction = _get_direction(p)
            if not sym or not direction or not _is_crypto_symbol(sym):
                continue

            strategy = (p.get("strategy") or p.get("algorithm") or p.get("strategy_name") or "default").lower()

            # Gate: Kill-list
            if strategy in STRATEGY_KILL_LIST:
                continue

            # Gate: Signal freshness (30 min for conviction)
            pick_ts = p.get("timestamp") or p.get("generated_at") or p.get("time") or ""
            if pick_ts:
                try:
                    pick_dt = datetime.fromisoformat(str(pick_ts).replace("Z", "+00:00"))
                    if pick_dt.tzinfo is None:
                        pick_dt = pick_dt.replace(tzinfo=timezone.utc)
                    age_min = (datetime.now(timezone.utc) - pick_dt).total_seconds() / 60
                    if age_min > MAX_SIGNAL_AGE_MIN:
                        continue
                except (ValueError, TypeError):
                    pass

            # Gate: Strategy WR >= 50% with >= 10 trades
            strat_stats = strategy_stats.get(strategy, {})
            if strat_stats.get("total", 0) < MIN_STRATEGY_TRADES:
                continue
            if strat_stats.get("wr", 0) < MIN_STRATEGY_WR:
                continue

            # Gate: R:R >= 2.0
            if sl and sl > 0:
                if direction == "LONG":
                    reward = tp - entry
                    risk = entry - sl
                elif direction == "SHORT":
                    reward = entry - tp
                    risk = sl - entry
                else:
                    continue
                if risk <= 0:
                    continue
                rr = reward / risk
                if rr < MIN_RISK_REWARD:
                    continue
            else:
                continue  # No SL = no conviction pick

            # Gate: Entry room >= 50%
            cur_price = current_prices.get(sym, 0)
            if cur_price > 0:
                if direction == "LONG":
                    total_move = tp - entry
                    price_moved = cur_price - entry
                elif direction == "SHORT":
                    total_move = entry - tp
                    price_moved = entry - cur_price
                else:
                    continue
                if total_move > 0:
                    room_used = max(0, price_moved / total_move)
                    if room_used > (1.0 - MIN_ENTRY_ROOM):
                        continue
                    # Check if SL already breached
                    if direction == "LONG" and cur_price < sl:
                        continue
                    if direction == "SHORT" and cur_price > sl:
                        continue

            # Gate: Regime-direction alignment
            if _HAS_REGIME and regime:
                if not _regime_check(direction, regime.get("fng"), regime.get("regime", "UNKNOWN"),
                                     regime.get("btc_dom_trend", "NEUTRAL"), regime.get("rsi_14")):
                    continue
            elif btc_momentum:
                if not _regime_direction_gate(direction, fear_greed, btc_momentum):
                    continue

            # Gate: Minimum confidence
            conf = float(p.get("confidence") or p.get("signal_confidence") or 0.5)
            if conf < MIN_CONFIDENCE:
                continue

            # Bayesian edge score (if available)
            bayesian_prob = None
            if _HAS_BAYESIAN:
                try:
                    scorer = BayesianEdgeScorer()
                    bayesian_prob = scorer.probability_above_threshold(
                        wins=strat_stats.get("wins", 0),
                        total=strat_stats.get("total", 0),
                        threshold=0.50
                    )
                except Exception:
                    pass

            # Score: system_wr * strategy_wr * rr_normalized * confidence
            score = wr_data["wr"] * strat_stats["wr"] * min(rr / 4.0, 1.0) * conf
            if bayesian_prob and bayesian_prob > 0.5:
                score *= (0.5 + 0.5 * bayesian_prob)  # Bayesian boost

            # ── Round 2: Regime multiplier (Moskowitz 2012) ──
            if regime:
                r_str = regime.get("regime", "UNKNOWN")
                if r_str == "TRENDING_DOWN":
                    score *= 1.2 if direction == "SHORT" else 0.7
                elif r_str == "TRENDING_UP":
                    score *= 1.2 if direction == "LONG" else 0.7

            # ── Round 2: Volume gate for LONGs (Llorente 2002) ──
            vol_24h = float(p.get("volume_24h") or p.get("volume_24h_usd") or 0)
            if direction == "LONG" and vol_24h > 0 and vol_24h < 50_000_000:
                score *= 0.7  # Low-vol longs penalized

            # ── Round 2: ADX gate for LONGs (Wilder 1978) ──
            pick_adx = float(p.get("adx") or p.get("adx_14") or 0)
            if direction == "LONG" and pick_adx > 0 and pick_adx < 15:
                score *= 0.7  # Low-ADX longs penalized

            candidates.append({
                "symbol": sym,
                "direction": direction,
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "risk_reward": round(rr, 2),
                "confidence": round(conf, 3),
                "strategy": strategy,
                "system_id": sys_id,
                "system_name": sys_info["name"],
                "system_wr": round(wr_data["wr"] * 100, 1),
                "system_trades": wr_data["total"],
                "strategy_wr": round(strat_stats["wr"] * 100, 1),
                "strategy_trades": strat_stats["total"],
                "score": round(score, 4),
                "bayesian_prob": round(bayesian_prob, 3) if bayesian_prob else None,
                "room_used": round(room_used * 100, 1) if cur_price > 0 else None,
                "current_price": cur_price if cur_price > 0 else None,
            })

    # Sort by score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Consensus filter: require >= 2 systems on same symbol+direction
    symbol_systems: dict[str, set] = {}
    for c in candidates:
        key = f"{c['symbol']}_{c['direction']}"
        if key not in symbol_systems:
            symbol_systems[key] = set()
        symbol_systems[key].add(c["system_id"])

    consensus_picks = []
    for c in candidates:
        key = f"{c['symbol']}_{c['direction']}"
        systems_agreeing = symbol_systems.get(key, set())
        if len(systems_agreeing) >= MIN_CONSENSUS_SYSTEMS:
            c["consensus_count"] = len(systems_agreeing)
            c["consensus_systems"] = sorted(systems_agreeing)
            consensus_picks.append(c)

    # Correlation cap: max N same-direction
    long_count, short_count = 0, 0
    final_picks = []
    seen_symbols = set()

    for pick in consensus_picks:
        if pick["symbol"] in seen_symbols:
            continue  # One pick per symbol
        if pick["direction"] == "LONG":
            if long_count >= MAX_CRYPTO_SAME_DIR:
                continue
            long_count += 1
        else:
            if short_count >= MAX_CRYPTO_SAME_DIR:
                continue
            short_count += 1
        seen_symbols.add(pick["symbol"])
        final_picks.append(pick)
        if len(final_picks) >= MAX_PICKS_PER_RUN:
            break

    return final_picks


# ── Discord Embed ──────────────────────────────────────────────

def _build_conviction_embed(pick: dict) -> dict:
    """Build a rich Discord embed for a conviction pick."""
    is_long = pick["direction"] == "LONG"
    color = 0x22C55E if is_long else 0xEF4444  # Green / Red

    # Direction emoji and text
    dir_text = "LONG" if is_long else "SHORT"
    dir_emoji = "🟢" if is_long else "🔴"

    # Star rating based on score
    score = pick["score"]
    if score >= 0.25:
        stars = "⭐⭐⭐"
    elif score >= 0.15:
        stars = "⭐⭐"
    else:
        stars = "⭐"

    title = f"🎯 CONVICTION PICK: {pick['symbol']} {dir_emoji} {dir_text}"

    # Build description
    desc_parts = [
        f"**{pick['consensus_count']} systems agree** on this trade.",
        f"System WR: **{pick['system_wr']}%** ({pick['system_trades']} trades)",
        f"Strategy WR: **{pick['strategy_wr']}%** ({pick['strategy_trades']} trades)",
    ]
    if pick.get("bayesian_prob"):
        desc_parts.append(f"Bayesian P(edge>50%): **{pick['bayesian_prob']*100:.0f}%**")
    desc_parts.append(f"Score: **{score:.4f}** {stars}")

    fields = [
        {"name": "Entry", "value": f"`${pick['entry_price']:,.4f}`" if pick['entry_price'] < 1 else f"`${pick['entry_price']:,.2f}`", "inline": True},
        {"name": "Target", "value": f"`${pick['take_profit']:,.4f}`" if pick['take_profit'] < 1 else f"`${pick['take_profit']:,.2f}`", "inline": True},
        {"name": "Stop Loss", "value": f"`${pick['stop_loss']:,.4f}`" if pick['stop_loss'] < 1 else f"`${pick['stop_loss']:,.2f}`", "inline": True},
        {"name": "R:R", "value": f"`{pick['risk_reward']}:1`", "inline": True},
        {"name": "Confidence", "value": f"`{pick['confidence']*100:.0f}%`", "inline": True},
        {"name": "Strategy", "value": f"`{pick['strategy']}`", "inline": True},
    ]

    if pick.get("current_price"):
        cp = pick["current_price"]
        fields.append({
            "name": "Current Price",
            "value": f"`${cp:,.4f}`" if cp < 1 else f"`${cp:,.2f}`",
            "inline": True,
        })
    if pick.get("room_used") is not None:
        room_left = 100 - pick["room_used"]
        fields.append({
            "name": "Entry Room Left",
            "value": f"`{room_left:.0f}%`",
            "inline": True,
        })
        # Entry window verdict
        if room_left >= 80:
            window_line = "\U0001f7e2 **Ideal entry** — price near original level"
        elif room_left >= 60:
            window_line = "\U0001f7e2 **Good entry** — confirmed direction, plenty of room"
        elif room_left >= 40:
            window_line = "\U0001f7e1 **OK entry** — halfway to target"
        else:
            window_line = "\U0001f534 **Late entry** — most of the move already happened"
        fields.append({
            "name": "Entry Window",
            "value": window_line,
            "inline": False,
        })

    fields.append({
        "name": "Agreeing Systems",
        "value": ", ".join(f"`{s}`" for s in pick.get("consensus_systems", [])),
        "inline": False,
    })

    return {
        "title": title,
        "description": "\n".join(desc_parts),
        "color": color,
        "fields": fields,
        "footer": {
            "text": f"Conviction Picks | {pick['system_name']} | Min WR 55% | Min R:R 2.0 | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        },
    }


def send_conviction_picks(picks: list[dict]) -> int:
    """Send conviction picks to Discord. Returns number sent."""
    webhook = WEBHOOK_CONVICTION or WEBHOOK_FALLBACK
    if not webhook:
        print("[CONVICTION] No webhook configured (set DISCORD_WEBHOOK_CONVICTION)")
        return 0

    dedup = _load_dedup()
    sent = 0

    for pick in picks:
        if _is_duplicate(pick["symbol"], pick["direction"], dedup):
            print(f"  [DEDUP] {pick['symbol']} {pick['direction']} — already sent within {DEDUP_COOLDOWN_HOURS}h")
            continue

        embed = _build_conviction_embed(pick)
        payload = {
            "username": "Conviction Picks",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
            "embeds": [embed],
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook,
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": "ConvictionPicks/1.0"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 204):
                    _mark_sent(pick["symbol"], pick["direction"], dedup)
                    sent += 1
                    print(f"  [SENT] {pick['symbol']} {pick['direction']} R:R={pick['risk_reward']} Score={pick['score']}")
                else:
                    print(f"  [WARN] Discord returned {resp.status} for {pick['symbol']}")
        except Exception as e:
            print(f"  [ERROR] Failed to send {pick['symbol']}: {e}", file=sys.stderr)

        time.sleep(1)  # Rate limit

    _save_dedup(dedup)
    return sent


def _send_no_picks_summary(system_wrs: dict, strategy_stats: dict):
    """Send a brief summary when no conviction picks found (for transparency)."""
    webhook = WEBHOOK_CONVICTION or WEBHOOK_FALLBACK
    if not webhook:
        return

    # Count qualified systems
    qualified = [s for s, d in system_wrs.items() if d.get("qualified")]
    top_strategies = sorted(
        [(k, v) for k, v in strategy_stats.items() if v["total"] >= MIN_STRATEGY_TRADES and v["wr"] >= MIN_STRATEGY_WR],
        key=lambda x: x[1]["wr"], reverse=True
    )[:5]

    desc = (
        "All 9 conviction gates must pass simultaneously for a pick to fire. "
        "Common reasons no picks qualify:\n"
        f"• **System WR gate:** Need ≥{MIN_SYSTEM_WR*100:.0f}% WR with {MIN_SYSTEM_TRADES}+ trades\n"
        f"• **Consensus gate:** Need ≥{MIN_CONSENSUS_SYSTEMS} independent systems agreeing\n"
        f"• **R:R gate:** Need ≥{MIN_RISK_REWARD}x risk:reward\n"
        "• **Regime/freshness/entry room gates**\n\n"
    )
    desc += f"**{len(qualified)} systems** currently meet min WR threshold:\n"
    if qualified:
        for sys_id in qualified:
            d = system_wrs[sys_id]
            desc += f"  • {d['name']}: {d['wr']*100:.1f}% WR ({d['total']} trades)\n"
    else:
        desc += "  None — no system currently meets conviction thresholds.\n"

    if top_strategies:
        desc += f"\n**Top strategies** (≥{MIN_STRATEGY_TRADES} trades, ≥{MIN_STRATEGY_WR*100:.0f}% WR):\n"
        for name, s in top_strategies[:3]:
            desc += f"  • `{name}`: {s['wr']*100:.1f}% WR ({s['total']} trades)\n"

    payload = {
        "username": "Conviction Picks",
        "embeds": [{
            "title": "📊 Conviction Scan — No Qualifying Picks",
            "description": desc,
            "color": 0x6B7280,
            "footer": {"text": f"Conviction Picks | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"},
        }],
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(webhook, data=data, headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


# ── Main ────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("CONVICTION PICKS — Ultra-Selective Discord Alert")
    print(f"  Min System WR: {MIN_SYSTEM_WR*100:.0f}% | Min Trades: {MIN_SYSTEM_TRADES}")
    print(f"  Min Strategy WR: {MIN_STRATEGY_WR*100:.0f}% | Min Trades: {MIN_STRATEGY_TRADES}")
    print(f"  Min R:R: {MIN_RISK_REWARD} | Min Consensus: {MIN_CONSENSUS_SYSTEMS} systems")
    print(f"  Max Age: {MAX_SIGNAL_AGE_MIN} min | Max Picks: {MAX_PICKS_PER_RUN}")
    print("=" * 60)

    # Compute system and strategy stats
    print("\n[1/6] Computing system WRs...")
    system_wrs = compute_system_wrs()
    qualified_count = sum(1 for d in system_wrs.values() if d.get("qualified"))
    print(f"  {qualified_count}/{len(system_wrs)} systems qualified (>= {MIN_SYSTEM_WR*100:.0f}% WR, >= {MIN_SYSTEM_TRADES} trades)")
    for sys_id, d in sorted(system_wrs.items(), key=lambda x: x[1]["wr"], reverse=True):
        if d["total"] > 0:
            q = "✅" if d["qualified"] else "❌"
            print(f"    {q} {d['name']}: {d['wr']*100:.1f}% WR ({d['total']} trades)")

    print("\n[2/6] Computing strategy stats...")
    strategy_stats = compute_strategy_stats()
    qualified_strats = {k: v for k, v in strategy_stats.items()
                        if v["total"] >= MIN_STRATEGY_TRADES and v["wr"] >= MIN_STRATEGY_WR}
    print(f"  {len(qualified_strats)}/{len(strategy_stats)} strategies qualified")
    for name, s in sorted(qualified_strats.items(), key=lambda x: x[1]["wr"], reverse=True)[:10]:
        print(f"    ✅ {name}: {s['wr']*100:.1f}% WR ({s['total']} trades)")

    print("\n[3/6] Fetching market data...")
    fear_greed = _fetch_fear_greed()
    btc_momentum = _fetch_btc_momentum()
    print(f"  Fear & Greed: {fear_greed}")
    print(f"  BTC 24h: {btc_momentum.get('pct_24h', 0):+.2f}% ({btc_momentum.get('regime', 'unknown')})")

    regime = None
    if _HAS_REGIME:
        try:
            regime = get_current_regime()
            print(f"  Regime: {regime}")
        except Exception:
            pass

    print("\n[4/6] Fetching current prices...")
    # Collect all symbols from active picks
    all_symbols = set()
    for sys_info in SYSTEMS.values():
        active = _load_json(REPO_ROOT / sys_info["active"])
        if active:
            for p in _extract_picks(active):
                sym = _norm_sym(p.get("symbol") or p.get("pair") or "")
                if sym:
                    all_symbols.add(sym)
    current_prices = _fetch_current_prices(list(all_symbols))
    print(f"  Got prices for {len(current_prices)} symbols")

    print("\n[5/6] Scanning for conviction picks...")
    picks = collect_conviction_picks(
        system_wrs, strategy_stats, current_prices,
        fear_greed, btc_momentum, regime
    )
    print(f"  Found {len(picks)} conviction picks")

    if picks:
        print("\n[6/6] Sending to Discord...")
        for i, pick in enumerate(picks, 1):
            print(f"\n  Pick #{i}:")
            print(f"    {pick['symbol']} {pick['direction']}")
            print(f"    Entry: ${pick['entry_price']} → TP: ${pick['take_profit']} | SL: ${pick['stop_loss']}")
            print(f"    R:R: {pick['risk_reward']} | Score: {pick['score']}")
            print(f"    System: {pick['system_name']} ({pick['system_wr']}% WR)")
            print(f"    Strategy: {pick['strategy']} ({pick['strategy_wr']}% WR)")
            print(f"    Consensus: {pick['consensus_count']} systems ({', '.join(pick['consensus_systems'])})")
            if pick.get("bayesian_prob"):
                print(f"    Bayesian P(edge): {pick['bayesian_prob']*100:.0f}%")

        sent = send_conviction_picks(picks)
        print(f"\n  Sent {sent}/{len(picks)} conviction picks to Discord")
    else:
        print("\n[6/6] No conviction picks — sending scan summary")
        _send_no_picks_summary(system_wrs, strategy_stats)
        print("  Sent summary to Discord")

    # Save results
    output_path = REPO_ROOT / "cross_aggregation" / "data" / "conviction_picks.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "picks": picks,
        "system_summary": {
            sys_id: {"wr": d["wr"], "trades": d["total"], "qualified": d["qualified"]}
            for sys_id, d in system_wrs.items() if d["total"] > 0
        },
        "qualified_strategies": len(qualified_strats),
        "fear_greed": fear_greed,
        "btc_momentum": btc_momentum,
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to {output_path}")

    print("\n" + "=" * 60)
    print(f"CONVICTION SCAN COMPLETE — {len(picks)} picks")
    print("=" * 60)

    return picks


if __name__ == "__main__":
    main()
