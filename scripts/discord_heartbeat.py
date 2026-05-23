#!/usr/bin/env python3
"""Discord heartbeat — posts a status check to quiet channels every 4 hours.

Targets: #ml-picks (DISCORD_ML_CHANNEL) and #conviction-picks (DISCORD_WEBHOOK_CONVICTION).
Shows system health, recent activity summary, and next scan times so channels
always show signs of life even when no picks are generated.
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("[heartbeat] requests not installed, exiting")
    sys.exit(0)

REPO_ROOT = Path(__file__).resolve().parent.parent
EST = timezone(timedelta(hours=-5))

# ── Channel config ──────────────────────────────────────────────
CHANNELS = {
    "ml_picks": {
        "webhook_env": "DISCORD_ML_CHANNEL",
        "name": "#ml-picks",
        "username": "ML Picks Bot",
        "color": 0x3B82F6,
    },
    "conviction_picks": {
        "webhook_env": "DISCORD_WEBHOOK_CONVICTION",
        "name": "#conviction-picks",
        "username": "Conviction Picks Bot",
        "color": 0xF59E0B,
    },
}


def _load_json(path: Path):
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _count_active_picks(data) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("signals", "picks", "active_picks", "super_signals"):
            if key in data and isinstance(data[key], list):
                return len(data[key])
    return 0


def _file_age_hours(path: Path) -> float:
    if not path.is_file():
        return -1
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return (datetime.now(timezone.utc) - mtime).total_seconds() / 3600


def build_ml_status() -> dict:
    """Build ML system status embed for #ml-picks."""
    now = datetime.now(timezone.utc)
    now_est = datetime.now(EST)

    # Check enhanced ML predictions
    ml_picks_path = REPO_ROOT / "updates" / "data" / "antigravity_ml_live_picks.json"
    ml_data = _load_json(ml_picks_path)
    ml_count = _count_active_picks(ml_data) if ml_data else 0
    ml_age = _file_age_hours(ml_picks_path)

    # Check enhanced ML models
    model_dir = REPO_ROOT / "ml_crypto_predictor" / "enhanced_models" / "models"
    model_count = len(list(model_dir.glob("*.pkl"))) if model_dir.is_dir() else 0

    # Check ML battleground
    bg_picks = REPO_ROOT / "ml_battleground" / "shared" / "data" / "consensus_picks.json"
    bg_data = _load_json(bg_picks)
    bg_count = _count_active_picks(bg_data) if bg_data else 0
    bg_age = _file_age_hours(bg_picks)

    # Determine health
    if ml_age > 0 and ml_age < 6:
        health = "\U0001f7e2 Healthy"
        health_color = 0x22C55E
    elif ml_age > 0 and ml_age < 12:
        health = "\U0001f7e1 Stale"
        health_color = 0xF59E0B
    else:
        health = "\U0001f534 No recent data"
        health_color = 0xEF4444

    # Active signals summary
    active_text = f"ML Predictions: **{ml_count}** active"
    if ml_age > 0:
        active_text += f" (updated {ml_age:.1f}h ago)"
    active_text += f"\nBattleground Consensus: **{bg_count}** active"
    if bg_age > 0:
        active_text += f" (updated {bg_age:.1f}h ago)"
    active_text += f"\nTrained Models: **{model_count}**"

    # Next scan times
    next_4h = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=4 - now.hour % 4)
    next_scan = next_4h.strftime("%H:%M UTC")

    fields = [
        {"name": "\U0001f4e1 System Health", "value": health, "inline": True},
        {"name": "\U0001f552 Next Scan", "value": next_scan, "inline": True},
        {"name": "\U0001f4ca Active Signals", "value": active_text, "inline": False},
    ]

    # If there are picks, show top one
    if ml_data and isinstance(ml_data, list) and ml_data:
        top = max(ml_data, key=lambda x: x.get("pump_probability", 0))
        sym = top.get("symbol", "?")
        prob = top.get("pump_probability", 0)
        conf = top.get("confidence", "?")
        # Derive direction from TP vs entry price, or signals list
        tp = top.get("tp_price", 0)
        entry = top.get("entry_price", 0)
        signals = top.get("signals", [])
        if any("BEARISH" in s for s in signals):
            direction = "BEARISH \U0001f534"
        elif any("BULLISH" in s for s in signals):
            direction = "BULLISH \U0001f7e2"
        elif tp and entry and tp > entry:
            direction = "BULLISH \U0001f7e2"
        elif tp and entry and tp < entry:
            direction = "BEARISH \U0001f534"
        else:
            direction = "NEUTRAL \U0001f7e1"
        fields.append({
            "name": "\U0001f3af Top Signal",
            "value": f"**{sym}** — {direction} {conf} ({prob:.1%} signal strength, not historical WR)",
            "inline": False,
        })
    else:
        fields.append({
            "name": "\U0001f4ad Status",
            "value": "No ML picks active — model waiting for entry conditions.\n"
                     "This is normal; strict filters prevent low-quality signals.",
            "inline": False,
        })

    return {
        "embeds": [{
            "title": f"\u2699\ufe0f ML System Status — {now_est.strftime('%b %d, %I:%M %p EST')}",
            "color": health_color,
            "fields": fields,
            "footer": {"text": "Status check every 4h | Paper Trade Only"},
            "timestamp": now.isoformat(),
        }],
    }


def build_conviction_status() -> dict:
    """Build conviction picks status embed for #conviction-picks."""
    now = datetime.now(timezone.utc)
    now_est = datetime.now(EST)

    # Load conviction picks data
    conviction_path = REPO_ROOT / "cross_aggregation" / "data" / "conviction_picks.json"
    conviction_data = _load_json(conviction_path)
    conv_age = _file_age_hours(conviction_path)

    # Load sent history
    sent_path = REPO_ROOT / "cross_aggregation" / "data" / "conviction_sent.json"
    sent_data = _load_json(sent_path) or {}
    total_sent = len(sent_data) if isinstance(sent_data, dict) else 0

    # Load super signals for context
    super_path = REPO_ROOT / "cross_aggregation" / "data" / "super_signals.json"
    super_data = _load_json(super_path)
    super_count = 0
    if super_data and isinstance(super_data, dict):
        super_count = len(super_data.get("super_signals", []))

    # Active conviction picks
    active_picks = []
    if conviction_data and isinstance(conviction_data, list):
        active_picks = [p for p in conviction_data if p.get("status") == "ACTIVE"]

    # Quality gates summary
    gates_text = (
        "1. System WR \u2265 55% (15+ trades)\n"
        "2. Strategy WR \u2265 50% (10+ trades)\n"
        "3. R:R \u2265 2.0\n"
        "4. \u2265 2 systems agree\n"
        "5. Entry room \u2265 50%\n"
        "6. Regime-aligned (F&G + BTC)\n"
        "7. Max 3 picks per run"
    )

    fields = [
        {"name": "\U0001f4e1 Scanner Status",
         "value": f"\U0001f7e2 Running every 30 min\nLast scan: {conv_age:.1f}h ago" if conv_age > 0
                  else "\U0001f7e1 Waiting for first scan",
         "inline": True},
        {"name": "\U0001f4ca Pipeline",
         "value": f"Cross-system signals: **{super_count}**\nConviction qualified: **{len(active_picks)}**\nTotal sent (all time): **{total_sent}**",
         "inline": True},
    ]

    if active_picks:
        pick_lines = []
        for p in active_picks[:3]:
            sym = p.get("symbol", "?")
            direction = p.get("direction", "?")
            emoji = "\U0001f7e2" if direction == "LONG" else "\U0001f534"
            pick_lines.append(f"{emoji} **{sym}** {direction} — R:R {p.get('risk_reward', 0):.1f}:1")
        fields.append({
            "name": "\U0001f3af Active Conviction Picks",
            "value": "\n".join(pick_lines),
            "inline": False,
        })
    else:
        fields.append({
            "name": "\U0001f4ad Status",
            "value": "No conviction picks active — **this is by design**.\n"
                     "Conviction picks require 9 quality gates to pass simultaneously.\n"
                     "\"Better to miss 10 good trades than take 1 bad one.\"",
            "inline": False,
        })

    fields.append({
        "name": "\U0001f512 Quality Gates (all must pass)",
        "value": gates_text,
        "inline": False,
    })

    return {
        "embeds": [{
            "title": f"\U0001f3af Conviction Picks Status — {now_est.strftime('%b %d, %I:%M %p EST')}",
            "color": 0xF59E0B,
            "fields": fields,
            "footer": {"text": "Status check every 4h | Ultra-selective | Paper Trade Only"},
            "timestamp": now.isoformat(),
        }],
    }


def post_heartbeat(channel_key: str, payload: dict):
    """Post a heartbeat to a Discord channel."""
    cfg = CHANNELS[channel_key]
    webhook_url = os.environ.get(cfg["webhook_env"], "")
    if not webhook_url:
        print(f"[heartbeat] No {cfg['webhook_env']} set — skipping {cfg['name']}")
        return

    payload["username"] = cfg["username"]
    import time as _time
    for _attempt in range(3):
        try:
            r = requests.post(webhook_url, json=payload, timeout=15)
            if r.status_code in (200, 204):
                print(f"[heartbeat] {cfg['name']}: posted successfully")
                break
            elif r.status_code == 429:
                retry = r.json().get("retry_after", 5)
                _time.sleep(retry)
                continue
            else:
                print(f"[heartbeat] {cfg['name']}: Discord returned {r.status_code}")
                if _attempt < 2:
                    _time.sleep(2 * (_attempt + 1))
                    continue
                break
        except Exception as e:
            if _attempt == 2:
                print(f"[heartbeat] {cfg['name']}: failed after 3 attempts — {e}")
            else:
                _time.sleep(2 * (_attempt + 1))


def main():
    print(f"[heartbeat] Running at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    # Post to #ml-picks
    ml_payload = build_ml_status()
    post_heartbeat("ml_picks", ml_payload)

    # Post to #conviction-picks
    conv_payload = build_conviction_status()
    post_heartbeat("conviction_picks", conv_payload)

    print("[heartbeat] Done")


if __name__ == "__main__":
    main()
