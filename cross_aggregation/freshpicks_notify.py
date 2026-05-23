# -*- coding: utf-8 -*-
"""
FreshPicks Discord Notifications — Forward Performance Only
=============================================================
Sends new buy/sell signals to the dedicated #fresh-picks channel.
Each pick includes entry/TP/SL, confidence, strategy, AND forward
performance stats (live TP/SL tracking — NEVER backtested numbers).

IMPORTANT: All stats passed to send_fresh_pick() MUST come from
forward-tracked closed picks validated against live exchange prices.
Never pass backtested, simulated, or estimated performance data.

Uses DISCORD_WEBHOOK_FRESHPICKS from environment.

Usage:
    from cross_aggregation.freshpicks_notify import send_fresh_pick, send_fresh_picks_batch
    send_fresh_pick(
        system="Mercury 2",
        pick={...},
        dashboard_url="https://...",
        stats={"total": 16, "active": 2, "wins": 15, "losses": 1,
               "tracking_since": "Feb 23", ...},
    )
"""

import json
import os
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_FRESHPICKS", "")
WEBHOOK_SANDBOX = os.environ.get("DISCORD_WEBHOOK_SANDBOX", "")

# Pick classification for routing
try:
    from cross_aggregation.pick_classifier import classify_system, get_system_trust_badge, get_system_stats_line
    _HAS_CLASSIFIER = True
except ImportError:
    _HAS_CLASSIFIER = False

# Centralized quality gate (G1-G7)
try:
    from cross_aggregation.freshpicks_gate import FreshPicksGate
    _gate = FreshPicksGate()
    _HAS_GATE = True
except ImportError:
    _gate = None
    _HAS_GATE = False

# EST timezone (UTC-5)
EST = timezone(timedelta(hours=-5))

# Embed colors by direction
COLORS = {
    "LONG": 0x22C55E,   # green
    "SHORT": 0xEF4444,  # red
    "CARRY": 0xEAB308,  # yellow
    "BUY": 0x22C55E,
    "SELL": 0xEF4444,
}


def _fmt_price(val) -> str:
    """Format price without scientific notation."""
    if val is None or val == 0:
        return "$0"
    val = float(val)
    if val >= 1000:
        return f"${val:,.2f}"
    elif val >= 1:
        return f"${val:.4f}"
    elif val >= 0.001:
        return f"${val:.6f}"
    else:
        return f"${val:.10f}"


def _now_est() -> str:
    """Current time in EST as formatted string."""
    return datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST")


def _post(payload: dict) -> bool:
    """Post to FreshPicks webhook with retry. Returns True on success."""
    if not WEBHOOK_URL:
        print("  [FreshPicks] No DISCORD_WEBHOOK_FRESHPICKS set, skipping")
        return False
    import time as _time
    for attempt in range(3):
        try:
            r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
            if r.status_code in (200, 204):
                print(f"  [FreshPicks] Sent ({r.status_code})")
                return True
            if r.status_code == 429:
                retry_after = r.json().get("retry_after", 3)
                _time.sleep(retry_after)
                continue
            print(f"  [FreshPicks] Failed ({r.status_code})")
            if attempt < 2:
                _time.sleep(2 * (attempt + 1))
                continue
            return False
        except Exception as e:
            if attempt == 2:
                print(f"  [FreshPicks] Failed after 3 attempts: {e}")
                return False
            _time.sleep(2 * (attempt + 1))
    return False


def _format_stats_block(stats: Dict) -> str:
    """Format forward-only performance stats as a compact text block.

    IMPORTANT: Stats MUST come from forward-tracked picks (real TP/SL hits
    validated against live exchange prices). Never pass backtested numbers.
    """
    if not stats:
        return ""

    total = stats.get("total", 0)
    active = stats.get("active", 0)
    wins = stats.get("wins", 0)
    losses = stats.get("losses", 0)
    wr = stats.get("win_rate", 0)
    realized = stats.get("realized_pnl_pct", 0)
    unrealized = stats.get("unrealized_pnl_pct", 0)
    tracking_since = stats.get("tracking_since", "")
    max_dd = stats.get("max_drawdown_pct", 0)
    rolling_wr = stats.get("rolling_wr_20", 0)

    # Trust indicator — conservative thresholds requiring meaningful sample
    if total < 5:
        trust = "\u26a0\ufe0f Too Early"
    elif total < 20:
        trust = "\u26a0\ufe0f Small Sample"
    elif wr >= 60:
        trust = "\u2705 Solid"
    elif wr >= 50:
        trust = "\U0001f7e1 Moderate"
    else:
        trust = "\U0001f534 Weak"

    # Build lines — always label as FORWARD (live-tracked)
    since_str = f" | Since {tracking_since}" if tracking_since else ""
    lines = [
        f"**{trust}** | WR: **{wr:.1f}%** ({wins}W/{losses}L) | {total} closed picks{since_str}",
        f"Realized P/L: **{realized:+.2f}%** | Unrealized: **{unrealized:+.2f}%** | {active} active",
    ]

    # Rolling WR (last 20 picks) — shows recent momentum vs all-time
    if rolling_wr and total >= 20:
        trend = "\u2197\ufe0f" if rolling_wr > wr else "\u2198\ufe0f"
        lines.append(f"Recent WR (last 20): **{rolling_wr:.1f}%** {trend} | Max DD: **{max_dd:.1f}%**")
    elif max_dd:
        lines.append(f"Max Drawdown: **{max_dd:.1f}%**")

    lines.append("*Forward performance only (live TP/SL tracking)*")
    return "\n".join(lines)


def _format_recent_closed(recent: List[Dict]) -> str:
    """Format last N closed picks as a compact list."""
    if not recent:
        return ""

    lines = []
    for p in recent[:5]:
        sym = p.get("symbol", "?")
        pnl = float(p.get("pnl_pct", 0) or 0)
        status = p.get("status", "?")
        strategy = p.get("strategy", "")

        # Normalize status display
        if status in ("WON", "WIN", "CLOSED_TP"):
            icon = "\u2705"
        elif status in ("LOST", "LOSS", "CLOSED_SL"):
            icon = "\u274c"
        else:
            icon = "\u2796"

        # Format PnL
        if isinstance(pnl, (int, float)):
            pnl_str = f"{pnl * 100:+.2f}%" if abs(pnl) < 1 else f"{pnl:+.2f}%"
        else:
            pnl_str = str(pnl)

        strat_str = f" [{strategy}]" if strategy else ""
        lines.append(f"{icon} `{sym:12s}` {pnl_str}{strat_str}")

    return "\n".join(lines)


def send_fresh_pick(
    system: str,
    pick: Dict,
    dashboard_url: str = "",
    extra_fields: Optional[List[Dict]] = None,
    stats: Optional[Dict] = None,
) -> bool:
    """
    Send a single new pick to the #fresh-picks channel with system performance.

    Args:
        system: System name (e.g., "Mercury 2", "Claws of Doom", "KIMI")
        pick: Dict with keys: symbol, direction, entry_price, tp_price/take_profit,
              sl_price/stop_loss, confidence, strategy/strategy_name, reason
        dashboard_url: Link to the system's dashboard
        extra_fields: Optional additional embed fields
        stats: Optional dict with FORWARD-ONLY performance (live TP/SL tracking).
            NEVER pass backtested or simulated numbers here.
            total: total closed picks (forward-tracked only)
            active: active picks count
            wins: win count (TP hits validated against live prices)
            losses: loss count (SL hits validated against live prices)
            win_rate: win rate percentage (0-100)
            realized_pnl_pct: total realized P/L %
            unrealized_pnl_pct: unrealized P/L on active picks %
            tracking_since: date string when forward tracking started (e.g. "Feb 23")
            max_drawdown_pct: max drawdown % from equity peak (negative number)
            rolling_wr_20: win rate over last 20 closed picks (0-100)
            recent_closed: list of last 5 closed picks [{symbol, pnl_pct, status, strategy}]
    """
    # --- Centralized quality gate (all 7 gates) ---
    if _HAS_GATE and _gate is not None:
        gate_result = _gate.check(system, pick)
        if not gate_result.allowed:
            print(f"  [FreshPicks GATE] Blocked {pick.get('symbol', '?')} from {system}: {gate_result.reason}")
            return False
        pick = gate_result.pick  # use enriched pick (dynamic TP/SL, sizing, expiry)

    symbol = pick.get("symbol", "???")
    direction = pick.get("direction", pick.get("signal", "LONG")).upper()
    strategy = pick.get("strategy_name", pick.get("strategy", pick.get("algorithm", "unknown")))
    entry = pick.get("entry_price", pick.get("price", 0))
    tp = pick.get("tp_price", pick.get("take_profit", pick.get("target_price", 0)))
    sl = pick.get("sl_price", pick.get("stop_loss", pick.get("stop_price", 0)))
    confidence = pick.get("confidence", 0)
    reason = pick.get("reason", pick.get("reasons", ""))
    if isinstance(reason, list):
        reason = "; ".join(reason)

    # Format confidence (handle both 0-1 and 0-100 scales)
    conf_display = f"{confidence * 100:.0f}%" if confidence <= 1 else f"{confidence:.0f}%"

    # TP/SL percentages
    tp_pct = ((tp / entry - 1) * 100) if entry and tp else 0
    sl_pct = ((1 - sl / entry) * 100) if entry and sl else 0

    color = COLORS.get(direction, 0x888888)
    dir_emoji = "\U0001f7e2" if direction in ("LONG", "BUY") else "\U0001f534" if direction in ("SHORT", "SELL") else "\U0001f7e1"

    # System trust badge (WINNER/LOSER/UNDETERMINED)
    sys_key = system.lower().replace(" ", "_").replace("-", "_")
    trust_line = ""
    sys_classification = "PROVEN"
    if _HAS_CLASSIFIER:
        badge_emoji, badge_text = get_system_trust_badge(sys_key)
        trust_line = f" {badge_emoji} {badge_text}"
        sys_classification = classify_system(sys_key)

    fields = [
        {"name": "Entry", "value": _fmt_price(entry), "inline": True},
        {"name": f"Target (+{tp_pct:.1f}%)", "value": _fmt_price(tp), "inline": True},
        {"name": f"Stop (-{sl_pct:.1f}%)", "value": _fmt_price(sl), "inline": True},
        {"name": "Confidence", "value": conf_display, "inline": True},
        {"name": "Strategy", "value": strategy, "inline": True},
        {"name": "System", "value": f"{system}{trust_line}", "inline": True},
    ]

    # Gate-enriched fields: sizing, R:R, expiry
    if pick.get("size_frac"):
        fields.append({"name": "Size", "value": f"{pick['size_frac'] * 100:.1f}% of portfolio", "inline": True})
    if pick.get("rr"):
        fields.append({"name": "R:R", "value": f"1:{pick['rr']:.2f}", "inline": True})
    if pick.get("expires_at"):
        try:
            exp_dt = datetime.fromisoformat(pick["expires_at"])
            exp_ts = int(exp_dt.timestamp())
            fields.append({"name": "Expires", "value": f"<t:{exp_ts}:R>", "inline": True})
        except Exception:
            pass

    # Entry window analysis — show if current price is still near entry
    cur_price = pick.get("current_price", 0)
    if cur_price and entry and tp:
        dir_up = direction in ("LONG", "BUY")
        if dir_up:
            pnl_from_entry = (cur_price - entry) / entry * 100
            room_to_tp = max(0, (tp - cur_price) / (tp - entry) * 100) if tp != entry else 0
        else:
            pnl_from_entry = (entry - cur_price) / entry * 100
            room_to_tp = max(0, (cur_price - tp) / (entry - tp) * 100) if tp != entry else 0

        if pnl_from_entry < -1:
            window_emoji, window_text = "\U0001f7e1", f"Dipped {pnl_from_entry:+.1f}% (better entry!)"
        elif abs(pnl_from_entry) <= 1:
            window_emoji, window_text = "\U0001f7e2", f"At entry ({pnl_from_entry:+.1f}%) — ideal!"
        elif pnl_from_entry <= 3:
            window_emoji, window_text = "\U0001f7e2", f"Confirmed {pnl_from_entry:+.1f}% — still OK"
        elif pnl_from_entry <= 5:
            window_emoji, window_text = "\U0001f7e1", f"Running {pnl_from_entry:+.1f}% — late entry"
        else:
            window_emoji, window_text = "\U0001f534", f"Moved {pnl_from_entry:+.1f}% — consider waiting"
        fields.append({
            "name": f"{window_emoji} Entry Window",
            "value": f"{window_text} | Room to TP: **{room_to_tp:.0f}%**",
            "inline": False,
        })

    # Gate-enriched fields: regime context + agreement
    if pick.get("fear_greed") is not None:
        fng = pick["fear_greed"]
        regime = pick.get("regime_label", "")
        regime_emoji = {
            "Extreme Fear": "\U0001f630", "Fear": "\U0001f628",
            "Neutral": "\U0001f610", "Greed": "\U0001f911",
            "Extreme Greed": "\U0001f525",
        }.get(regime, "\U0001f4ca")
        fields.append({"name": "Market Regime", "value": f"{regime_emoji} {regime} (F&G: {fng})", "inline": True})
    if pick.get("regime_warning"):
        fields.append({"name": "\u26a0\ufe0f Regime Warning", "value": pick["regime_warning"], "inline": False})
    agreement = pick.get("agreement_count", 0)
    total_sys = pick.get("total_systems", 0)
    if agreement:
        agree_emoji = "\u2705" if agreement >= 2 else "\u26a0\ufe0f"
        fields.append({"name": "System Agreement", "value": f"{agree_emoji} {agreement}/{total_sys} systems", "inline": True})

    # Add forward performance stats (NEVER backtested)
    if stats:
        total_trades = stats.get("wins", 0) + stats.get("losses", 0)
        stats_block = _format_stats_block(stats)
        if stats_block:
            fields.append({"name": f"\U0001f4ca Forward Performance ({total_trades} trades)", "value": stats_block, "inline": False})

        recent = stats.get("recent_closed", [])
        if recent:
            recent_block = _format_recent_closed(recent)
            if recent_block:
                fields.append({"name": "\U0001f4cb Last 5 Closed (Forward)", "value": recent_block, "inline": False})
    else:
        fields.append({"name": "\u26a0\ufe0f Forward Trades", "value": "No forward-tracked trades yet — treat with caution", "inline": False})

    if extra_fields:
        fields.extend(extra_fields)

    description = reason[:200] if reason else ""
    if dashboard_url:
        description += f"\n[View Dashboard]({dashboard_url})"

    embed = {
        "title": f"{dir_emoji} {direction}: {symbol}",
        "color": color,
        "fields": fields,
        "description": description,
        "footer": {"text": f"{system} | {_now_est()}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Route experimental/unproven system picks to sandbox
    if sys_classification == "EXPERIMENTAL" and WEBHOOK_SANDBOX:
        embed["footer"]["text"] = f"EXPERIMENTAL | {system} | {_now_est()}"
        import time as _retry_time
        for _attempt in range(3):
            try:
                r = requests.post(WEBHOOK_SANDBOX, json={"embeds": [embed]}, timeout=10)
                if r.status_code in (200, 204):
                    print(f"  [FreshPicks→Sandbox] Sent ({r.status_code}): {system} → {symbol}")
                    if _HAS_GATE and _gate is not None:
                        _gate.mark_sent(pick)
                    return True
                if r.status_code == 429:
                    _retry_time.sleep(r.json().get("retry_after", 3))
                    continue
                if _attempt < 2:
                    _retry_time.sleep(2 * (_attempt + 1))
                    continue
                return False
            except Exception as e:
                if _attempt == 2:
                    print(f"  [FreshPicks→Sandbox] Failed after 3 attempts: {e}")
                    return False
                _retry_time.sleep(2 * (_attempt + 1))
        return False

    success = _post({"embeds": [embed]})
    if success and _HAS_GATE and _gate is not None:
        _gate.mark_sent(pick)
    return success


def send_no_picks_status(reason: str = "quality_gate", total_scanned: int = 0, blocked_count: int = 0) -> bool:
    """
    Send a status message to #fresh-picks when no picks pass quality gates.
    Includes a 60-min cooldown to avoid spamming.
    """
    import pathlib
    cooldown_path = pathlib.Path(__file__).resolve().parent.parent / "data" / "freshpicks_nopicks_last.txt"
    now = datetime.now(timezone.utc)

    # Cooldown: max once per 60 min
    if cooldown_path.exists():
        try:
            last_sent = datetime.fromisoformat(cooldown_path.read_text().strip())
            if (now - last_sent).total_seconds() < 3600:
                return False
        except Exception:
            pass

    reasons_map = {
        "quality_gate": "All signals were filtered by the 7-gate quality system (confidence, R:R, dedup, rate cap, etc.).",
        "no_consensus": "No consensus picks found — fewer than 2 systems agree on any symbol + direction.",
        "all_sent": "All qualifying picks were already sent recently (dedup cooldown active).",
        "no_signals": "No active signals from any system this scan cycle.",
    }
    reason_text = reasons_map.get(reason, reason)

    detail = ""
    if total_scanned > 0:
        detail = f"\n{total_scanned} signal(s) scanned, {blocked_count} blocked by quality gates."

    embed = {
        "title": "FreshPicks Scan — No New Picks",
        "description": (
            f"{reason_text}{detail}\n\n"
            "This is normal — the quality gate ensures only high-conviction, "
            "non-duplicate signals reach this channel."
        ),
        "color": 0x6B7280,
        "footer": {"text": f"FreshPicks Gate | {_now_est()}"},
        "timestamp": now.isoformat(),
    }

    success = _post({"embeds": [embed]})
    if success:
        cooldown_path.parent.mkdir(parents=True, exist_ok=True)
        cooldown_path.write_text(now.isoformat())
    return success


def send_fresh_picks_batch(
    system: str,
    picks: List[Dict],
    dashboard_url: str = "",
    stats: Optional[Dict] = None,
) -> int:
    """
    Send multiple picks. Returns count of successfully sent.
    Discord allows max 10 embeds per message, so we batch.
    """
    if not picks:
        return 0
    sent = 0
    for pick in picks:
        if send_fresh_pick(system, pick, dashboard_url, stats=stats):
            sent += 1
    return sent


# --- Standalone mode: scan all system data dirs for new picks ---
if __name__ == "__main__":
    import pathlib

    REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

    SYSTEMS = {
        "Mercury 2": {
            "data": REPO_ROOT / "mercury2" / "data",
            "picks_file": "active_picks.json",
            "dashboard": "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/mercury2/",
        },
        "Claws of Doom": {
            "data": REPO_ROOT / "ml_battleground" / "system_f_clawsofdoom" / "data",
            "picks_file": "picks.json",
            "picks_key": "picks",
            "dashboard": "https://eltonaguiar.github.io/CLAWSOFDOOM/",
        },
    }

    total = 0
    for name, cfg in SYSTEMS.items():
        picks_path = cfg["data"] / cfg["picks_file"]
        if not picks_path.exists():
            continue
        try:
            data = json.load(open(picks_path))
            if isinstance(data, list):
                picks = data
            elif isinstance(data, dict):
                picks = data.get(cfg.get("picks_key", "picks"), [])
            else:
                picks = []
            if picks:
                sent = send_fresh_picks_batch(name, picks, cfg["dashboard"])
                total += sent
                print(f"  {name}: {sent}/{len(picks)} picks sent")
        except Exception as e:
            print(f"  {name}: error — {e}")

    print(f"  Total fresh picks sent: {total}")
