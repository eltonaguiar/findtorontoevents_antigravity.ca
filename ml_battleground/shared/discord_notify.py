"""
Discord notification module for ML Battleground — SUPERPOWERS branded.
Sends honest performance assessments via Discord webhook embeds.
Uses DISCORD_WEBHOOK_URL from environment (same as existing systems).
"""
import os
import json
import requests
from datetime import datetime, timezone
from typing import Optional


WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
USERNAME = "SUPERPOWERS \u2014 ML Battleground"


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
AVATAR_URL = ""  # Discord default

# Embed colors
COLOR_GREEN = 0x22C55E    # proven / winning
COLOR_YELLOW = 0xEAB308   # pending / warming up
COLOR_RED = 0xEF4444      # losing / needs work
COLOR_PURPLE = 0x8B5CF6   # no data yet
COLOR_BLUE = 0x3B82F6     # informational

# Pre-defined unicode strings (Python 3.11 disallows backslashes in f-string expressions)
_check = "\u2705"
_proven_check = "PROVEN \u2705"

# Dashboard URLs (GitHub Pages — always available)
_BASE = "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground"
DASHBOARD_URLS = {
    "system_a_filter": f"{_BASE}/a/",
    "system_b_regime": f"{_BASE}/b/",
    "system_c_deeplearn": f"{_BASE}/c/",
    "arena": f"{_BASE}/",
}


def send_system_status(
    system_name: str,
    system_label: str,
    version: str,
    active_picks: list[dict],
    closed_picks: list[dict],
    stats: dict,
    validation_gate: Optional[dict] = None,
    regime: Optional[str] = None,
    regime_confidence: Optional[float] = None,
    ml_filter_acceptance_rate: Optional[float] = None,
    **kwargs,  # catch legacy proven/proven_reason
):
    """
    Send honest status update for a single system.
    Follows the 'Forward Testing — Honest Assessment' pattern.
    Now uses institutional 8-check validation gate.
    """
    if not WEBHOOK_URL:
        print("[Discord] No DISCORD_WEBHOOK_URL set, skipping notification")
        return

    now = datetime.now(timezone.utc)
    trades = stats.get("trades", 0)
    wr = stats.get("win_rate", 0)
    sharpe = stats.get("sharpe", 0)
    max_dd = stats.get("max_dd", 0)
    total_pnl = stats.get("total_pnl_pct", 0)
    pf = stats.get("profit_factor", 0)

    # Extract validation gate info
    gate = validation_gate or {}
    gate_status = gate.get("status", "COLLECTING")
    checks_passed = gate.get("checks_passed", 0)
    proven = gate_status in ("PROVEN", "ELITE")

    # Status mapping from gate
    _STATUS_MAP = {
        "ELITE": (COLOR_GREEN, "\U0001f3c6", "ELITE"),
        "PROVEN": (COLOR_GREEN, "\u2705", "PROVEN"),
        "MARGINAL": (COLOR_YELLOW, "\u26a0\ufe0f", "MARGINAL"),
        "TESTING": (COLOR_YELLOW, "\U0001f52c", "TESTING"),
        "COLLECTING": (COLOR_PURPLE, "\U0001f4ca", "COLLECTING DATA"),
    }
    color, status_emoji, status_text = _STATUS_MAP.get(gate_status, (COLOR_PURPLE, "\U0001f195", "NO TRADES YET"))
    if trades == 0:
        color, status_emoji, status_text = COLOR_PURPLE, "\U0001f195", "NO TRADES YET"

    # Build honest performance text
    if trades == 0:
        perf_text = (
            f"{status_emoji} **{status_text}** \u2014 No closed trades yet.\n"
            f"System is scanning and will accumulate paper trades.\n"
            f"Need 30+ trades to begin institutional validation (8 checks)."
        )
    else:
        gate_line = f"**Gate:** {checks_passed}/8 checks passed \u2014 {gate_status}"
        if gate.get("recommendation"):
            gate_line += f"\n{gate['recommendation']}"
        perf_text = (
            f"{status_emoji} **{status_text}** \u2014 {trades} closed trades\n"
            f"```\n"
            f"Win Rate:       {wr:.1%} {'(>50%)' if not proven else _check}\n"
            f"Sharpe Ratio:   {sharpe:.2f} {'(>1.0)' if not proven else _check}\n"
            f"Max Drawdown:   {max_dd:.1%} {'(<15%)' if not proven else _check}\n"
            f"Profit Factor:  {pf:.2f} {'(>1.3)' if not proven else _check}\n"
            f"Total PnL:      {total_pnl:+.2f}%\n"
            f"```\n"
            f"{gate_line}"
        )

    # Direction breakdown from closed picks
    long_closed = [p for p in closed_picks if p.get("signal_type") == "BUY"]
    short_closed = [p for p in closed_picks if p.get("signal_type") == "SELL"]
    long_wins = sum(1 for p in long_closed if p.get("exit_reason") in ("tp", "trailing_tp") or p.get("net_pnl_pct", 0) > 0)
    short_wins = sum(1 for p in short_closed if p.get("exit_reason") in ("tp", "trailing_tp") or p.get("net_pnl_pct", 0) > 0)
    if long_closed or short_closed:
        dir_lines = []
        if long_closed:
            l_wr = long_wins / len(long_closed) * 100
            l_pnl = sum(p.get("net_pnl_pct", 0) for p in long_closed)
            dir_lines.append(f"LONG:  {l_wr:.0f}% WR ({long_wins}/{len(long_closed)})  {l_pnl:+.1f}%")
        if short_closed:
            s_wr = short_wins / len(short_closed) * 100
            s_pnl = sum(p.get("net_pnl_pct", 0) for p in short_closed)
            dir_lines.append(f"SHORT: {s_wr:.0f}% WR ({short_wins}/{len(short_closed)})  {s_pnl:+.1f}%")
        long_active = sum(1 for p in active_picks if p.get("signal_type") == "BUY")
        short_active = sum(1 for p in active_picks if p.get("signal_type") == "SELL")
        dir_lines.append(f"Active: {long_active} LONG / {short_active} SHORT")
        perf_text += f"\n**Direction Breakdown:**\n```\n" + "\n".join(dir_lines) + "\n```"

    # Build active picks text
    if active_picks:
        picks_lines = []
        for p in active_picks[:6]:  # max 6 shown (more detail per pick)
            sym = p.get("symbol", "?")
            sig = p.get("signal_type", "BUY")
            entry = p.get("entry_price", 0)
            tp = p.get("take_profit", 0)
            sl = p.get("stop_loss", 0)
            rr = p.get("risk_reward", 0)
            unrealized = p.get("unrealized_pnl_pct", 0)
            strat = p.get("strategy", "?")
            ml_score = p.get("ml_score", p.get("confidence", 0))
            issued = p.get("timestamp_est", "")
            pnl_emoji = "\U0001f7e2" if unrealized > 0 else ("\U0001f534" if unrealized < 0 else "\u26aa")
            pnl_label = f"P&L: {unrealized:+.2f}%" if unrealized != 0 else "P&L: new"
            picks_lines.append(
                f"{pnl_emoji} **{sym}** {sig} @ `{_fmt_price(entry)}`\n"
                f"   TP: `{_fmt_price(tp)}` | SL: `{_fmt_price(sl)}` | R:R: `{rr:.1f}` | ML: `{ml_score:.2f}`\n"
                f"   {pnl_label} | {strat} | {issued}"
            )
        picks_text = "\n".join(picks_lines)
        if len(active_picks) > 6:
            picks_text += f"\n+{len(active_picks) - 6} more active picks"
    else:
        picks_text = "_No active positions_"

    # Build training/readiness text
    readiness_parts = []
    if trades < 30:
        readiness_parts.append(f"\U0001f4ca Need {30 - trades} more trades for validation (8-check gate)")
    # Show individual check results if available
    check_details = gate.get("check_details", {})
    for check_name, detail in check_details.items():
        if isinstance(detail, dict) and not detail.get("passed", True):
            val = detail.get("value", "?")
            thresh = detail.get("threshold", "?")
            readiness_parts.append(f"\u26a0\ufe0f {check_name}: {val} (need {'>' if check_name != 'max_drawdown' else '<'}{thresh})")
    if gate_status == "ELITE":
        readiness_parts.append("\U0001f3c6 ELITE: 7+/8 institutional checks passed!")
    elif proven:
        readiness_parts.append("\u2705 PROVEN: 5+/8 checks passed \u2014 system validated")

    if ml_filter_acceptance_rate is not None:
        readiness_parts.append(f"\U0001f916 ML Filter accepting {ml_filter_acceptance_rate:.0%} of raw signals")
    if regime is not None:
        readiness_parts.append(f"\U0001f30d Regime: **{regime}** ({regime_confidence:.0%} confidence)" if regime_confidence else f"\U0001f30d Regime: **{regime}**")

    readiness_text = "\n".join(readiness_parts) if readiness_parts else "_Awaiting first trades_"

    # Build embeds
    embeds = [
        {
            "title": f"\u26a1 SUPERPOWERS: {system_label} v{version}",
            "description": f"Autonomous ML trading system \u2014 paper trading mode\n\U0001f517 [Open {system_label} Dashboard]({DASHBOARD_URLS.get(system_name, _BASE + '/')}) | [\U0001f3c6 Arena]({DASHBOARD_URLS['arena']})",
            "color": color,
            "timestamp": now.isoformat(),
            "fields": [
                {
                    "name": f"{status_emoji} Forward Testing \u2014 Honest Assessment",
                    "value": _truncate(perf_text),
                    "inline": False,
                },
                {
                    "name": f"\U0001f3af Active Picks ({len(active_picks)})",
                    "value": _truncate(picks_text),
                    "inline": False,
                },
                {
                    "name": "\U0001f9ea System Readiness",
                    "value": _truncate(readiness_text),
                    "inline": False,
                },
            ],
            "footer": {
                "text": (
                    f"SUPERPOWERS {system_label} v{version} | "
                    f"{gate_status} ({checks_passed}/8 checks) | "
                    f"Not financial advice | All metrics honest"
                ),
            },
        }
    ]

    _post(embeds)


def send_arena_comparison(
    systems: list[dict],
    consensus_pairs: list[str],
):
    """
    Send Arena comparison embed showing all 3 systems head-to-head.
    systems: list of {name, label, trades, wr, sharpe, max_dd, total_pnl, proven}
    """
    if not WEBHOOK_URL:
        return

    now = datetime.now(timezone.utc)

    # Build comparison table
    lines = ["```"]
    lines.append(f"{'System':<16} {'Trades':>6} {'WR':>7} {'Sharpe':>7} {'DD':>7} {'PnL':>8} {'L/S':>5}")
    lines.append("-" * 62)

    winner = None
    best_sharpe = -999

    for sys in systems:
        long_c = sys.get("long_closed", 0)
        short_c = sys.get("short_closed", 0)
        ls_str = f"{long_c}L/{short_c}S" if (long_c or short_c) else "..."
        lines.append(
            f"{sys['label']:<16} {sys['trades']:>6} "
            f"{sys['wr']:>6.1%} {sys['sharpe']:>7.2f} "
            f"{sys['max_dd']:>6.1%} {sys['total_pnl']:>+7.2f}% "
            f"{ls_str:>5}"
        )
        if sys.get("proven") and sys["sharpe"] > best_sharpe:
            best_sharpe = sys["sharpe"]
            winner = sys["label"]

    lines.append("```")
    table_text = "\n".join(lines)

    # Consensus
    if consensus_pairs:
        consensus_text = f"\U0001f91d **Consensus signals** (2+ systems agree): {', '.join(consensus_pairs[:5])}"
    else:
        consensus_text = "_No consensus signals right now_"

    # Winner
    if winner:
        winner_text = f"\U0001f3c6 **Current Winner: {winner}** (highest Sharpe among proven systems)"
    else:
        winner_text = "\u23f3 No system has earned PROVEN status yet. The race continues..."

    embeds = [
        {
            "title": "\u26a1 SUPERPOWERS ARENA \u2014 The Horse Race",
            "description": (
                "3 ML systems compete head-to-head. Honest, transparent metrics.\n"
                f"\U0001f517 [\U0001f3c6 Arena]({DASHBOARD_URLS['arena']}) | "
                f"[The Filter]({DASHBOARD_URLS['system_a_filter']}) | "
                f"[The Regime]({DASHBOARD_URLS['system_b_regime']}) | "
                f"[The Neural Net]({DASHBOARD_URLS['system_c_deeplearn']})"
            ),
            "color": COLOR_BLUE,
            "timestamp": now.isoformat(),
            "fields": [
                {"name": "\U0001f4ca Head-to-Head", "value": _truncate(table_text), "inline": False},
                {"name": "\U0001f3c6 Winner Status", "value": winner_text, "inline": False},
                {"name": "\U0001f91d Consensus", "value": consensus_text, "inline": False},
            ],
            "footer": {
                "text": "SUPERPOWERS Arena | 50+ trades per system for validation | Not financial advice",
            },
        }
    ]

    _post(embeds)


def send_pick_alert(
    system_label: str,
    pick: dict,
):
    """Send alert for a new high-confidence pick."""
    if not WEBHOOK_URL:
        return

    sym = pick.get("symbol", "?")
    sig = pick.get("signal_type", "BUY")
    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    rr = pick.get("risk_reward", 0)
    strat = pick.get("strategy", "?")
    confidence = pick.get("confidence", 0)
    ml_score = pick.get("ml_score", confidence)
    tp_sl_method = pick.get("tp_sl_method", "atr")
    issued_est = pick.get("timestamp_est", "")
    timeframe = pick.get("timeframe", "")

    color = COLOR_GREEN if sig == "BUY" else COLOR_RED

    # Asset class detection
    ac = pick.get("asset_class", "")
    if not ac:
        su = sym.upper().replace("-", "").replace("/", "")
        if any(su.endswith(sfx) for sfx in ("USDT", "BTC", "ETH", "BUSD", "USDC")):
            ac = "CRYPTO"
        elif len(su) == 6 and su[:3] in ("EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD"):
            ac = "FOREX"
        else:
            ac = "EQUITY"
    ac_tag = {"CRYPTO": "\U0001fa99 CRYPTO", "FOREX": "\U0001f4b1 FOREX", "EQUITY": "\U0001f4c8 EQUITY", "MEMECOIN": "\U0001f436 MEMECOIN"}.get(ac.upper(), ac.upper())

    embeds = [
        {
            "title": f"\u26a1 SUPERPOWERS: {system_label} \u2014 {'BUY' if sig == 'BUY' else 'SELL'} {sym} [{ac_tag}]",
            "description": f"\U0001f4c5 **Issued:** {issued_est}\n\U0001f517 [Open {system_label} Dashboard]({_dashboard_url_for_label(system_label)}) | [\U0001f3c6 Arena]({DASHBOARD_URLS['arena']})",
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fields": [
                {"name": "Entry", "value": f"`{_fmt_price(entry)}`", "inline": True},
                {"name": "Take Profit", "value": f"`{_fmt_price(tp)}`", "inline": True},
                {"name": "Stop Loss", "value": f"`{_fmt_price(sl)}`", "inline": True},
                {"name": "R:R", "value": f"`{rr:.1f}`", "inline": True},
                {"name": "ML Score", "value": f"`{ml_score:.2f}`", "inline": True},
                {"name": "Timeframe", "value": f"`{timeframe}`" if timeframe else "`--`", "inline": True},
                {"name": "Strategy", "value": strat, "inline": True},
                {"name": "TP/SL Method", "value": f"`{tp_sl_method}`", "inline": True},
                {"name": "Confidence", "value": f"{confidence:.0%}", "inline": True},
            ],
            "footer": {
                "text": f"SUPERPOWERS {system_label} | Paper trade | Not financial advice",
            },
        }
    ]

    _post(embeds)


def send_pick_exit(
    system_label: str,
    pick: dict,
):
    """Send alert when a pick closes (TP/SL/trailing/expiry)."""
    if not WEBHOOK_URL:
        return

    sym = pick.get("symbol", "?")
    reason = pick.get("exit_reason", "?")
    net_pnl = pick.get("net_pnl_pct", 0)
    entry = pick.get("entry_price", 0)
    exit_p = pick.get("exit_price", 0)
    strat = pick.get("strategy", "?")
    opened_est = pick.get("timestamp_est", "")
    closed_est = pick.get("closed_at_est", pick.get("closed_est", ""))

    color = COLOR_GREEN if net_pnl > 0 else COLOR_RED
    result_emoji = "\U0001f7e2" if net_pnl > 0 else "\U0001f534"

    # Asset class detection
    ac = pick.get("asset_class", "")
    if not ac:
        su = sym.upper().replace("-", "").replace("/", "")
        if any(su.endswith(sfx) for sfx in ("USDT", "BTC", "ETH", "BUSD", "USDC")):
            ac = "CRYPTO"
        elif len(su) == 6 and su[:3] in ("EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD"):
            ac = "FOREX"
        else:
            ac = "EQUITY"
    ac_tag = {"CRYPTO": "\U0001fa99 CRYPTO", "FOREX": "\U0001f4b1 FOREX", "EQUITY": "\U0001f4c8 EQUITY", "MEMECOIN": "\U0001f436 MEMECOIN"}.get(ac.upper(), ac.upper())

    embeds = [
        {
            "title": f"{result_emoji} SUPERPOWERS: {system_label} \u2014 {sym} CLOSED ({reason}) [{ac_tag}]",
            "description": f"\U0001f4c5 **Opened:** {opened_est} | **Closed:** {closed_est}\n\U0001f517 [Open {system_label} Dashboard]({_dashboard_url_for_label(system_label)}) | [\U0001f3c6 Arena]({DASHBOARD_URLS['arena']})",
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fields": [
                {"name": "Entry", "value": f"`{_fmt_price(entry)}`", "inline": True},
                {"name": "Exit", "value": f"`{_fmt_price(exit_p)}`", "inline": True},
                {"name": "Net PnL", "value": f"`{net_pnl:+.2f}%`", "inline": True},
                {"name": "Exit Reason", "value": reason, "inline": True},
                {"name": "Strategy", "value": strat, "inline": True},
            ],
            "footer": {
                "text": f"SUPERPOWERS {system_label} | Paper trade | All metrics honest",
            },
        }
    ]

    _post(embeds)


def _dashboard_url_for_label(label: str) -> str:
    """Get dashboard URL from system label (e.g. 'The Filter')."""
    label_map = {
        "The Filter": DASHBOARD_URLS["system_a_filter"],
        "The Regime": DASHBOARD_URLS["system_b_regime"],
        "The Neural Net": DASHBOARD_URLS["system_c_deeplearn"],
    }
    return label_map.get(label, DASHBOARD_URLS["arena"])


def _truncate(text: str, max_len: int = 1024) -> str:
    """Discord embed field value max is 1024 chars."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def _post(embeds: list[dict]):
    """Post embeds to Discord webhook with retry."""
    if not WEBHOOK_URL:
        return

    import time as _time
    payload = {
        "username": USERNAME,
        "embeds": embeds,
    }
    if AVATAR_URL:
        payload["avatar_url"] = AVATAR_URL

    for attempt in range(3):
        try:
            resp = requests.post(WEBHOOK_URL, json=payload, timeout=15)
            if resp.status_code in (200, 204):
                print(f"[Discord] Sent {len(embeds)} embed(s) OK")
                return
            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 3)
                _time.sleep(retry_after)
                continue
            print(f"[Discord] Failed: {resp.status_code} {resp.text[:200]}")
            if attempt < 2:
                _time.sleep(2 * (attempt + 1))
                continue
            return
        except Exception as e:
            if attempt == 2:
                print(f"[Discord] Error after 3 attempts: {e}")
            else:
                _time.sleep(2 * (attempt + 1))
