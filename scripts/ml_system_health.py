#!/usr/bin/env python3
"""ML System Health Monitor — checks all ML systems and reports to Discord."""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

REPO_ROOT = Path(__file__).resolve().parent.parent
EST = timezone(timedelta(hours=-5))

# Ensure stdout can handle Unicode (emojis) on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

GITHUB_PAGES_BASE = "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca"

ML_SYSTEMS = {
    "ML Crypto Predictor": {
        "model_dirs": ["ml_crypto_predictor/models", "ml_crypto_predictor/enhanced_models/models"],
        "picks_paths": ["ml_crypto_predictor/enhanced_models/live_picks/active_picks.json"],
        "model_exts": [".pkl", ".joblib"],
        "schedule": "Daily 00:00 UTC",
        "dashboard": f"{GITHUB_PAGES_BASE}/monitor/",
    },
    "Battleground A (XGBoost Filter)": {
        "model_dirs": ["ml_battleground/system_a_filter/models"],
        "picks_paths": ["ml_battleground/system_a_filter/data/active_picks.json"],
        "model_exts": [".joblib"],
        "schedule": "On-demand",
        "dashboard": f"{GITHUB_PAGES_BASE}/monitor/",
    },
    "Battleground B (Regime)": {
        "model_dirs": ["ml_battleground/system_b_regime/models"],
        "picks_paths": ["ml_battleground/system_b_regime/data/active_picks.json"],
        "model_exts": [".joblib"],
        "schedule": "On-demand",
        "dashboard": f"{GITHUB_PAGES_BASE}/monitor/",
    },
    "Battleground C (GRU-Attention)": {
        "model_dirs": ["ml_battleground/system_c_deeplearn/models"],
        "picks_paths": ["ml_battleground/system_c_deeplearn/data/active_picks.json"],
        "model_exts": [".pt", ".joblib"],
        "schedule": "On-demand",
        "dashboard": f"{GITHUB_PAGES_BASE}/monitor/",
    },
    "Crypto ML Edge": {
        "model_dirs": ["crypto_ml_edge/models"],
        "picks_paths": ["crypto_ml_edge/data/active_picks.json"],
        "model_exts": [".joblib"],
        "schedule": "Every 30 min",
        "dashboard": f"{GITHUB_PAGES_BASE}/monitor/",
    },
    "Mercury 2": {
        "model_dirs": ["mercury2/models"],
        "picks_paths": ["mercury2/data/active_picks.json"],
        "model_exts": [".joblib"],
        "schedule": "Every 30 min",
        "dashboard": f"{GITHUB_PAGES_BASE}/monitor/",
    },
    "Claude Gainer ML": {
        "model_dirs": ["claude_gainer_ml/models"],
        "picks_paths": ["claude_gainer_ml/tracker/claude_live_picks.json"],
        "model_exts": [".joblib"],
        "schedule": "Hourly",
        "dashboard": f"{GITHUB_PAGES_BASE}/monitor/",
    },
    "RL Agent (PPO)": {
        "model_dirs": ["rl_agent/models"],
        "picks_paths": ["rl_agent/data/active_picks.json"],
        "model_exts": [".npz"],
        "schedule": "Every 6h (train daily 3AM, predict 6h)",
        "dashboard": f"{GITHUB_PAGES_BASE}/alpha/",
    },
}

STATUS_EMOJI = {
    "HEALTHY": "\u2705",
    "WARNING": "\u26a0\ufe0f",
    "CRITICAL": "\ud83d\udd34",
    "OFFLINE": "\u2b1b",
}

EMBED_COLORS = {
    "HEALTHY": 0x2ECC71,
    "WARNING": 0xF39C12,
    "CRITICAL": 0xE74C3C,
    "OFFLINE": 0x95A5A6,
}


def find_newest_file(dirs, exts):
    """Find the newest file matching given extensions across directories."""
    newest_path = None
    newest_mtime = 0.0
    for d in dirs:
        full_dir = REPO_ROOT / d
        if not full_dir.is_dir():
            continue
        for ext in exts:
            for f in full_dir.rglob(f"*{ext}"):
                try:
                    mt = f.stat().st_mtime
                    if mt > newest_mtime:
                        newest_mtime = mt
                        newest_path = f
                except OSError:
                    continue
    if newest_path is None:
        return None, None
    return newest_path, datetime.fromtimestamp(newest_mtime, tz=timezone.utc)


def find_newest_picks(picks_paths):
    """Find newest picks file and count active picks."""
    newest_path = None
    newest_mtime = 0.0
    for p in picks_paths:
        full = REPO_ROOT / p
        if full.is_file():
            try:
                mt = full.stat().st_mtime
                if mt > newest_mtime:
                    newest_mtime = mt
                    newest_path = full
            except OSError:
                continue
    if newest_path is None:
        return None, None, 0

    picks_dt = datetime.fromtimestamp(newest_mtime, tz=timezone.utc)
    active_count = 0
    try:
        data = json.loads(newest_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            active_count = len(data)
        elif isinstance(data, dict):
            if "picks" in data and isinstance(data["picks"], list):
                active_count = len(data["picks"])
            elif "active_picks" in data and isinstance(data["active_picks"], list):
                active_count = len(data["active_picks"])
            else:
                active_count = len(data)
    except (json.JSONDecodeError, OSError):
        pass

    return newest_path, picks_dt, active_count


def relative_age(dt, now):
    """Return human-readable relative age string."""
    if dt is None:
        return "N/A"
    delta = now - dt
    hours = delta.total_seconds() / 3600
    if hours < 1:
        mins = int(delta.total_seconds() / 60)
        return f"{mins}m ago"
    if hours < 48:
        return f"{int(hours)}h ago"
    days = int(hours / 24)
    return f"{days}d ago"


def format_timestamp_est(dt):
    """Format a datetime as EST string."""
    if dt is None:
        return "N/A"
    est_dt = dt.astimezone(EST)
    return est_dt.strftime("%b %d %H:%M EST").replace(" 0", " ")


def determine_status(model_dt, picks_dt, now, has_picks_paths):
    """Determine system health status."""
    if model_dt is None:
        return "OFFLINE"

    model_age_h = (now - model_dt).total_seconds() / 3600

    if not has_picks_paths:
        # Systems with no picks paths (e.g., RL Agent) — judge by model only
        if model_age_h <= 48:
            return "HEALTHY"
        if model_age_h <= 72:
            return "WARNING"
        return "CRITICAL"

    if picks_dt is None:
        picks_age_h = float("inf")
    else:
        picks_age_h = (now - picks_dt).total_seconds() / 3600

    if model_age_h <= 48 and picks_age_h <= 24:
        return "HEALTHY"
    if model_age_h > 72 or picks_age_h > 72:
        return "CRITICAL"
    return "WARNING"


def check_all_systems():
    """Check all ML systems and return results."""
    now = datetime.now(timezone.utc)
    results = []

    for name, cfg in ML_SYSTEMS.items():
        _, model_dt = find_newest_file(cfg["model_dirs"], cfg["model_exts"])
        _, picks_dt, active_count = find_newest_picks(cfg["picks_paths"])
        has_picks = len(cfg["picks_paths"]) > 0
        status = determine_status(model_dt, picks_dt, now, has_picks)

        model_str = f"{format_timestamp_est(model_dt)} ({relative_age(model_dt, now)})" if model_dt else "No models found"
        if has_picks:
            picks_str = f"{format_timestamp_est(picks_dt)} ({relative_age(picks_dt, now)}) ({active_count} active)" if picks_dt else "No picks file"
        else:
            picks_str = "N/A"

        results.append({
            "name": name,
            "status": status,
            "model_str": model_str,
            "picks_str": picks_str,
            "schedule": cfg["schedule"],
            "dashboard": cfg.get("dashboard"),
        })

    return results, now


def build_embed(results, now):
    """Build Discord embed payload."""
    statuses = [r["status"] for r in results]
    if "CRITICAL" in statuses or "OFFLINE" in statuses:
        color = EMBED_COLORS["CRITICAL"]
    elif "WARNING" in statuses:
        color = EMBED_COLORS["WARNING"]
    else:
        color = EMBED_COLORS["HEALTHY"]

    fields = []
    for r in results:
        emoji = STATUS_EMOJI[r["status"]]
        value_parts = [f"Trained: {r['model_str']}"]
        if r["picks_str"] != "N/A":
            value_parts.append(f"Picks: {r['picks_str']}")
        value_parts.append(f"Schedule: {r['schedule']}")
        if r.get("dashboard"):
            value_parts.append(f"[Dashboard]({r['dashboard']})")

        fields.append({
            "name": f"{emoji} {r['name']}",
            "value": " | ".join(value_parts),
            "inline": False,
        })

    healthy = sum(1 for s in statuses if s == "HEALTHY")
    total = len(statuses)
    description = f"{healthy}/{total} systems healthy"

    return {
        "username": "ML Health Monitor",
        "embeds": [{
            "title": "ML Systems Health Report",
            "description": description,
            "color": color,
            "fields": fields,
            "footer": {"text": "ML Health Monitor"},
            "timestamp": now.isoformat(),
        }],
    }


def print_report(results, now):
    """Print a text report to stdout."""
    print(f"\n{'='*60}")
    print("ML Systems Health Report")
    print(f"Generated: {format_timestamp_est(now)}")
    print(f"{'='*60}\n")

    for r in results:
        emoji = STATUS_EMOJI[r["status"]]
        print(f"{emoji} {r['name']} [{r['status']}]")
        print(f"   Trained: {r['model_str']}")
        if r["picks_str"] != "N/A":
            print(f"   Picks:   {r['picks_str']}")
        print(f"   Schedule: {r['schedule']}")
        if r.get("dashboard"):
            print(f"   Dashboard: {r['dashboard']}")
        print()

    statuses = [r["status"] for r in results]
    healthy = sum(1 for s in statuses if s == "HEALTHY")
    print(f"Summary: {healthy}/{len(statuses)} systems healthy")
    print(f"{'='*60}\n")


def main():
    results, now = check_all_systems()
    payload = build_embed(results, now)

    webhook_url = os.environ.get("DISCORD_ML_CHANNEL")

    if webhook_url and requests:
        import time as _time
        sent = False
        for _attempt in range(3):
            try:
                resp = requests.post(webhook_url, json=payload, timeout=10)
                if resp.status_code in (200, 204):
                    print(f"Health report sent to Discord ({resp.status_code})")
                    sent = True
                    break
                if resp.status_code == 429:
                    _time.sleep(resp.json().get("retry_after", 3))
                    continue
                if _attempt < 2:
                    _time.sleep(2 * (_attempt + 1))
                    continue
                print(f"Discord webhook returned {resp.status_code}: {resp.text}", file=sys.stderr)
                break
            except Exception as e:
                if _attempt == 2:
                    print(f"Failed to send to Discord after 3 attempts: {e}", file=sys.stderr)
                else:
                    _time.sleep(2 * (_attempt + 1))
        if not sent:
            print_report(results, now)
    else:
        if not webhook_url:
            print("DISCORD_ML_CHANNEL not set, printing to stdout.")
        if not requests:
            print("requests library not available, printing to stdout.")
        print_report(results, now)


if __name__ == "__main__":
    main()
