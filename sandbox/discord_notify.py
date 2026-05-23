"""Discord embed builder and webhook sender for Opposite Day."""

import logging
import os
import time
from typing import Dict, List

import requests

from sandbox.config import (
    WEBHOOK_ENV_VAR, MAX_PICKS_PER_EMBED,
)

log = logging.getLogger(__name__)

ENGINE_NAMES = {
    "predictions": "Predictions Dashboard",
    "kimi": "KIMI Rise of the Claw",
    "alpha": "Alpha Engine",
    "signal_engine": "Signal Engine",
    "cross_aggregator": "Cross-Aggregator",
}

ENGINE_COLORS = {
    "predictions": 0x3498DB,
    "kimi": 0xE74C3C,
    "alpha": 0x2ECC71,
    "signal_engine": 0xF39C12,
    "cross_aggregator": 0x9B59B6,
}


def _post_webhook(embeds: list, webhook_url: str) -> bool:
    """Post embeds to Discord with retry on rate-limit."""
    for attempt in range(3):
        try:
            resp = requests.post(webhook_url, json={"embeds": embeds[:10]}, timeout=10)
            if resp.status_code == 204:
                return True
            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 2)
                log.warning("Rate limited, retrying in %.1fs", retry_after)
                time.sleep(retry_after)
                continue
            log.error("Discord error %d: %s", resp.status_code, resp.text[:200])
            return False
        except Exception as exc:
            log.error("Discord post failed: %s", exc)
            return False
    return False


def _fmt_price(price: float) -> str:
    if price >= 1000:
        return f"${price:,.2f}"
    if price >= 1:
        return f"${price:.4f}"
    return f"${price:.6f}"


def _pnl_emoji(pnl: float) -> str:
    return "\U0001f7e2" if pnl > 0 else "\U0001f534" if pnl < 0 else "\u26aa"


def build_engine_embed(
    engine: str,
    stats: dict,
    timeline_avg: Dict[str, dict],
    new_picks: List[dict],
    closed_picks: List[dict],
) -> dict:
    """Build a Discord embed for one engine portfolio."""
    name = ENGINE_NAMES.get(engine, engine)
    color = ENGINE_COLORS.get(engine, 0x95A5A6)

    fields = []

    # Scorecard
    wr = stats.get("win_rate", 0)
    pf = stats.get("profit_factor", "\u221e")
    fields.append({
        "name": "\U0001f4ca Scorecard",
        "value": f"**{stats['wins']}W / {stats['losses']}L** ({wr}% WR) | PF: {pf}",
        "inline": False,
    })

    # New picks
    if new_picks:
        lines = []
        for p in new_picks[:MAX_PICKS_PER_EMBED]:
            lines.append(
                f"**{p['opposite_direction']}** {p['symbol']} @ {_fmt_price(p['entry_price'])} "
                f"(flipped from {p['original_direction']})\n"
                f"TP: {_fmt_price(p['opposite_tp'])} | SL: {_fmt_price(p['opposite_sl'])}"
            )
        if len(new_picks) > MAX_PICKS_PER_EMBED:
            lines.append(f"*+ {len(new_picks) - MAX_PICKS_PER_EMBED} more*")
        fields.append({
            "name": "\U0001f195 New Opposite Picks",
            "value": "\n".join(lines),
            "inline": False,
        })

    # Timeline performance
    if timeline_avg:
        cp_order = ["1h", "4h", "12h", "24h"]
        lines = []
        for cp in cp_order:
            if cp in timeline_avg:
                avg = timeline_avg[cp]
                opp = avg["avg_opposite_pnl"]
                orig = avg["avg_original_pnl"]
                lines.append(
                    f"`{cp:>3}:` {opp:+.2f}% {_pnl_emoji(opp)}  (original: {orig:+.2f}%)"
                )
        if lines:
            fields.append({
                "name": "\U0001f4c8 Timeline Performance (avg PnL)",
                "value": "\n".join(lines),
                "inline": False,
            })

    # Closed picks
    if closed_picks:
        lines = []
        for p in closed_picks[:MAX_PICKS_PER_EMBED]:
            emoji = "\u2705" if p["status"] == "TP_HIT" else "\u274c" if p["status"] == "SL_HIT" else "\u23f0"
            pnl = float(p.get("pnl_pct", 0) or 0) or 0
            lines.append(
                f"{emoji} {p['symbol']} {p['opposite_direction']} \u2192 "
                f"{p['status']} {pnl:+.2f}%"
            )
        if len(closed_picks) > MAX_PICKS_PER_EMBED:
            lines.append(f"*+ {len(closed_picks) - MAX_PICKS_PER_EMBED} more*")
        fields.append({
            "name": "\U0001f4cb Recently Closed",
            "value": "\n".join(lines),
            "inline": False,
        })

    return {
        "title": f"\U0001f504 Opposite Day \u2014 {name}",
        "color": color,
        "fields": fields,
        "footer": {"text": "Paper Trading | Not financial advice \u2014 DYOR!"},
    }


def build_summary_embed(all_stats: Dict[str, dict], all_timelines: Dict[str, dict]) -> dict:
    """Build the all-portfolios summary embed."""
    lines = ["```"]
    lines.append(f"{'Engine':<15} | {'Trades':>6} | {'W/L':>7} | {'WR':>5} | {'PF':>5} | Best")
    lines.append("-" * 62)
    total_w, total_l = 0, 0
    for eng in ["predictions", "kimi", "alpha", "signal_engine", "cross_aggregator"]:
        s = all_stats.get(eng, {})
        name = ENGINE_NAMES.get(eng, eng)[:15]
        wins = s.get("wins", 0)
        losses = s.get("losses", 0)
        trades = wins + losses
        wr = s.get("win_rate", 0)
        pf = s.get("profit_factor", "\u221e")
        best = "N/A"
        if eng in all_timelines and all_timelines[eng]:
            tl = all_timelines[eng]
            best_cp = max(tl.items(), key=lambda x: x[1].get("avg_opposite_pnl", -999))
            best = best_cp[0]
        wl = f"{wins}W/{losses}L"
        lines.append(f"{name:<15} | {trades:>6} | {wl:>7} | {wr:>4.1f}% | {str(pf):>5} | {best}")
        total_w += wins
        total_l += losses
    lines.append("```")

    total = total_w + total_l
    overall_wr = (total_w / total * 100) if total else 0
    total_pf_desc = ""
    # Compute overall profit factor from per-engine data
    all_win_pnl = sum(s.get("win_pnl", 0) for s in all_stats.values())
    all_loss_pnl = sum(s.get("loss_pnl", 0) for s in all_stats.values())
    if all_loss_pnl > 0:
        total_pf_desc = f" | PF: {all_win_pnl / all_loss_pnl:.2f}"

    return {
        "title": "\U0001f3c6 Opposite Day \u2014 All Portfolios Summary",
        "description": "\n".join(lines),
        "color": 0xF1C40F,
        "fields": [{
            "name": "\U0001f4ca Totals",
            "value": f"**{total} trades** | {total_w}W / {total_l}L | Overall WR: {overall_wr:.1f}%{total_pf_desc}",
            "inline": False,
        }],
        "footer": {"text": "Paper Trading | Not financial advice \u2014 DYOR!"},
    }


def send_notifications(tracker) -> bool:
    """Build and send all Discord embeds for this run."""
    webhook_url = os.getenv(WEBHOOK_ENV_VAR, "")
    if not webhook_url:
        log.warning("No %s env var set \u2014 skipping Discord", WEBHOOK_ENV_VAR)
        return False

    engines = ["predictions", "kimi", "alpha", "signal_engine", "cross_aggregator"]
    all_stats = {}
    all_timelines = {}
    embeds = []

    new_picks = tracker.get_recently_opened()
    closed_picks = tracker.get_recently_closed()

    for eng in engines:
        stats = tracker.get_engine_stats(eng)
        timeline = tracker.get_timeline_avg(eng)
        all_stats[eng] = stats
        all_timelines[eng] = timeline

        eng_new = [p for p in new_picks if p["source_engine"] == eng]
        eng_closed = [p for p in closed_picks if p["source_engine"] == eng]

        if eng_new or eng_closed or stats.get("total", 0) > 0:
            embeds.append(build_engine_embed(eng, stats, timeline, eng_new, eng_closed))

    embeds.append(build_summary_embed(all_stats, all_timelines))

    success = True
    for i in range(0, len(embeds), 10):
        batch = embeds[i : i + 10]
        if not _post_webhook(batch, webhook_url):
            success = False

    return success
