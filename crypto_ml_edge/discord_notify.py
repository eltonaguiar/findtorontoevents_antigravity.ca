"""
Discord Webhook Notifications -- Crypto ML Edge Engine
======================================================
Sends formatted embeds to a Discord channel via webhook URL.
Includes active picks summary, recent performance, and an honest
forward-testing assessment.

Usage:
    from crypto_ml_edge.discord_notify import send_scan_notification

    send_scan_notification(picks_data)

Environment:
    DISCORD_WEBHOOK_URL -- Discord webhook URL (required)

The notification includes GSD branding per project requirements.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Config ─────────────────────────────────────────────────────────────────

DISCORD_WEBHOOK_URL_ENV = "DISCORD_WEBHOOK_URL"

# Embed colors (Discord uses decimal integers)
COLOR_GREEN = 0x22C55E   # Winning: WR > 55%
COLOR_YELLOW = 0xEAB308  # Early / inconclusive
COLOR_RED = 0xEF4444     # Losing: WR < 45%


# ─── Helpers ────────────────────────────────────────────────────────────────

def _get_webhook_url() -> Optional[str]:
    """Get Discord webhook URL from environment."""
    url = os.environ.get(DISCORD_WEBHOOK_URL_ENV, "").strip()
    if not url:
        return None
    return url


def _get_embed_color(performance: dict) -> int:
    """
    Determine embed color based on performance.
    Green if winning (WR > 55%), yellow if early/inconclusive, red if losing.
    """
    total = performance.get("total_picks", 0)
    win_rate = performance.get("win_rate", 0.0)

    # Need at least 10 picks to judge
    if total < 10:
        return COLOR_YELLOW

    if win_rate > 0.55:
        return COLOR_GREEN
    elif win_rate < 0.45:
        return COLOR_RED
    else:
        return COLOR_YELLOW


def _format_pick_line(pick: dict) -> str:
    """Format a single pick as a compact one-liner for Discord."""
    pair = pick.get("symbol_display") or pick.get("pair", "???")
    tf = pick.get("timeframe", "?")
    direction = pick.get("direction", "?")
    conf = pick.get("confidence", 0)
    size = pick.get("position_size_usd", 0)
    rr = pick.get("risk_reward_ratio", 0)
    tier = pick.get("tier", "")

    arrow = "LONG" if direction == "long" else "SHORT"
    tier_emoji = {"HIGH": "\U0001f7e2", "MEDIUM": "\U0001f7e1", "WATCH": "\u26aa"}.get(tier, "")

    # Strategy info from audit trail
    audit = pick.get("audit", {})
    strategy = audit.get("strategy_name", pick.get("source", "edge"))
    reasons = audit.get("reasons", [])
    first_reason = reasons[0][:80] if reasons else ""

    line = f"{tier_emoji} `{pair}` {tf} **{arrow}** | Conf: {conf:.1%} | Size: ${size:.0f} | RR: {rr:.1f}"
    if strategy:
        line += f"\n> *{strategy}*"
    if first_reason:
        line += f" -- {first_reason}"

    return line


def _build_honest_assessment(performance: dict, n_models: int) -> str:
    """
    Build an honest forward-testing assessment.
    No hype -- just facts about the system state.
    """
    total = performance.get("total_picks", 0)
    wins = performance.get("wins", 0)
    losses = performance.get("losses", 0)
    timeouts = performance.get("timeouts", 0)
    win_rate = performance.get("win_rate", 0.0)
    sharpe = performance.get("sharpe_estimate", 0.0)
    total_return = performance.get("total_return_pct", 0.0)

    lines = []

    # Training status
    if n_models == 0:
        lines.append("**Training:** No models trained yet. System is in setup phase.")
    elif n_models < 5:
        lines.append(f"**Training:** {n_models} models trained. Limited coverage.")
    else:
        lines.append(f"**Training:** {n_models} models trained and validated (DSR-gated).")

    # Performance assessment
    if total == 0:
        lines.append("**Performance:** No picks generated yet. Cannot assess.")
        lines.append("**Verdict:** Too early to evaluate.")
    elif total < 10:
        lines.append(f"**Performance:** {total} picks ({wins}W/{losses}L/{timeouts}T). "
                      "Sample too small.")
        lines.append("**Verdict:** Insufficient data. Need 10+ picks to assess.")
    elif total < 30:
        lines.append(f"**Performance:** {total} picks | WR: {win_rate:.1%} | "
                      f"Return: {total_return:+.1f}%")
        if win_rate > 0.55:
            lines.append("**Verdict:** Early positive signal, but not yet statistically "
                          "significant. Proceed with caution.")
        elif win_rate < 0.45:
            lines.append("**Verdict:** Early negative signal. May need model retraining "
                          "or market regime has shifted.")
        else:
            lines.append("**Verdict:** Inconclusive. Win rate near random. "
                          "More data needed.")
    else:
        lines.append(f"**Performance:** {total} picks | WR: {win_rate:.1%} | "
                      f"Sharpe: {sharpe:.2f} | Return: {total_return:+.1f}%")
        if win_rate > 0.55 and sharpe > 1.0:
            lines.append("**Verdict:** System showing edge above transaction costs. "
                          "Cautiously positive.")
        elif win_rate > 0.55:
            lines.append("**Verdict:** Win rate positive but Sharpe below target. "
                          "Edge may not survive costs.")
        elif win_rate < 0.45:
            lines.append("**Verdict:** System is losing money. Recommend pausing and "
                          "retraining on recent data.")
        else:
            lines.append("**Verdict:** No clear edge detected. System performing "
                          "near random after costs.")

    return "\n".join(lines)


# ─── Public API ─────────────────────────────────────────────────────────────

def send_scan_notification(
    picks_data: dict,
    n_models: int = 0,
    webhook_url: Optional[str] = None,
) -> bool:
    """
    Send a Discord embed notification with scan results.

    Parameters
    ----------
    picks_data : dict
        The active_picks.json structure (with picks, closed_picks, performance).
    n_models : int
        Number of trained models available.
    webhook_url : str, optional
        Override webhook URL. If None, reads from DISCORD_WEBHOOK_URL env var.

    Returns
    -------
    bool : True if notification sent successfully.
    """
    import requests

    url = webhook_url or _get_webhook_url()
    if not url:
        logger.warning(
            "Discord webhook URL not set. Set %s environment variable.",
            DISCORD_WEBHOOK_URL_ENV,
        )
        return False

    active_picks = picks_data.get("picks", [])
    performance = picks_data.get("performance", {})
    capital = picks_data.get("capital_base", 10000)

    color = _get_embed_color(performance)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Build fields
    fields = []

    # Active picks
    if active_picks:
        pick_lines = [_format_pick_line(p) for p in active_picks[:5]]
        if len(active_picks) > 5:
            pick_lines.append(f"*...and {len(active_picks) - 5} more*")
        fields.append({
            "name": "Active Picks",
            "value": "\n".join(pick_lines),
            "inline": False,
        })
    else:
        fields.append({
            "name": "Active Picks",
            "value": "No active picks this cycle.",
            "inline": False,
        })

    # Performance summary
    total = performance.get("total_picks", 0)
    if total > 0:
        perf_text = (
            f"**Win Rate:** {performance.get('win_rate', 0):.1%} "
            f"({performance.get('wins', 0)}W / "
            f"{performance.get('losses', 0)}L / "
            f"{performance.get('timeouts', 0)}T)\n"
            f"**Total Return:** {performance.get('total_return_pct', 0):+.1f}%\n"
            f"**Sharpe Est:** {performance.get('sharpe_estimate', 0):.2f}\n"
            f"**Total Picks:** {total}"
        )
    else:
        perf_text = "No closed picks yet. Performance tracking will begin after first TP/SL hit."

    fields.append({
        "name": "Performance",
        "value": perf_text,
        "inline": False,
    })

    # Honest assessment
    assessment = _build_honest_assessment(performance, n_models)
    fields.append({
        "name": "Forward Testing -- Honest Assessment",
        "value": assessment,
        "inline": False,
    })

    # System info
    engine_version = picks_data.get("engine_version", "1.0.0")
    fields.append({
        "name": "System",
        "value": (
            f"Engine: v{engine_version} | "
            f"Models: {n_models} | "
            f"Capital: ${capital:,.0f} (simulated)"
        ),
        "inline": False,
    })

    # Dashboard URL (GitHub Pages deployment)
    dashboard_url = "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/edge/"

    # Build embed
    embed = {
        "title": f"GSD Crypto ML Edge -- Scanner Report",
        "url": dashboard_url,
        "description": (
            f"Scan completed at {now_str}\n"
            f"**{len(active_picks)}** active picks | "
            f"**{total}** total closed\n"
            f"[View Dashboard]({dashboard_url})"
        ),
        "color": color,
        "fields": fields,
        "footer": {
            "text": (
                "GSD Crypto ML Edge Engine | Quick Engine + Research-driven | "
                "Not financial advice"
            ),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    payload = {
        "embeds": [embed],
    }

    # Send
    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=15,
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code in (200, 204):
            logger.info("Discord notification sent successfully.")
            return True
        else:
            logger.warning(
                "Discord webhook returned %d: %s",
                resp.status_code, resp.text[:200],
            )
            return False
    except Exception as e:
        logger.error("Failed to send Discord notification: %s", e)
        return False


def send_error_notification(
    error_message: str,
    context: str = "Scanner",
    webhook_url: Optional[str] = None,
) -> bool:
    """
    Send an error notification to Discord.

    Parameters
    ----------
    error_message : str
        Description of the error.
    context : str
        Where the error occurred (e.g., "Scanner", "Trainer").
    webhook_url : str, optional
        Override webhook URL.

    Returns
    -------
    bool : True if sent successfully.
    """
    import requests

    url = webhook_url or _get_webhook_url()
    if not url:
        return False

    embed = {
        "title": f"GSD Edge Engine -- {context} Error",
        "description": error_message[:2000],
        "color": COLOR_RED,
        "footer": {
            "text": "GSD Crypto ML Edge Engine | Error Notification",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        resp = requests.post(
            url,
            json={"embeds": [embed]},
            timeout=15,
            headers={"Content-Type": "application/json"},
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False
