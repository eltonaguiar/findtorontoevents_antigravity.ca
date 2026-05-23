"""Shared no-picks heartbeat for all Discord channels."""
import json
import pathlib
import time
import requests
from datetime import datetime, timezone, timedelta

EST = timezone(timedelta(hours=-5))

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_COOLDOWN_FILE = _REPO_ROOT / "data" / "heartbeat_last_sent.json"
_DEFAULT_COOLDOWN_SEC = 30 * 60  # 30 minutes


def _load_cooldowns() -> dict:
    if _COOLDOWN_FILE.exists():
        try:
            return json.loads(_COOLDOWN_FILE.read_text())
        except (json.JSONDecodeError, ValueError):
            pass
    return {}


def _save_cooldowns(data: dict):
    _COOLDOWN_FILE.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    pruned = {k: v for k, v in data.items() if now - v < 86400}
    _COOLDOWN_FILE.write_text(json.dumps(pruned))


def send_no_picks_heartbeat(
    webhook_url: str,
    channel_name: str,
    scan_info: dict,
    cooldown_sec: int = _DEFAULT_COOLDOWN_SEC,
) -> bool:
    """Send a 'scan complete, no picks' embed to a Discord channel.

    Includes per-channel throttling to avoid spam.

    Args:
        webhook_url: Discord webhook URL
        channel_name: Identifier for throttle key (e.g., 'paper-trade')
        scan_info: Dict with keys:
            - symbols_scanned (int): how many symbols were checked
            - systems_checked (int, optional): how many systems contributed
            - filter_reason (str): why no picks qualified
            - active_positions (int, optional): currently tracked positions
        cooldown_sec: Minimum seconds between heartbeats per channel

    Returns:
        True if sent, False if throttled or failed.
    """
    if not webhook_url:
        return False

    cooldowns = _load_cooldowns()
    last_sent = cooldowns.get(channel_name, 0)
    if time.time() - last_sent < cooldown_sec:
        return False

    now_est = datetime.now(EST).strftime("%Y-%m-%d %I:%M %p EST")
    symbols = scan_info.get("symbols_scanned", 0)
    systems = scan_info.get("systems_checked", 0)
    reason = scan_info.get("filter_reason", "No signals met quality criteria")
    active = scan_info.get("active_positions", 0)

    desc_lines = [
        f"**{now_est}**",
        f"\U0001f4ca Scanned: **{symbols}** symbols"
        + (f" across **{systems}** systems" if systems else ""),
        f"\U0001f6ab Result: {reason}",
    ]
    if active > 0:
        desc_lines.append(
            f"\U0001f4c8 Active positions: **{active}** being tracked"
        )
    desc_lines.append(
        "This is normal \u2014 the quality gate ensures only high-conviction signals are sent."
    )

    embed = {
        "title": "\U0001f50d Scan Complete \u2014 No New Picks",
        "description": "\n".join(desc_lines),
        "color": 0x6B7280,
        "footer": {"text": f"{channel_name} | {now_est} | System healthy"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        r = requests.post(
            webhook_url,
            json={"username": channel_name, "embeds": [embed]},
            timeout=15,
        )
        if r.status_code in (200, 204):
            cooldowns[channel_name] = time.time()
            _save_cooldowns(cooldowns)
            print(f"[Heartbeat] Sent no-picks to {channel_name}")
            return True
        elif r.status_code == 429:
            retry = r.json().get("retry_after", 5)
            time.sleep(retry)
            r2 = requests.post(
                webhook_url,
                json={"username": channel_name, "embeds": [embed]},
                timeout=15,
            )
            if r2.status_code in (200, 204):
                cooldowns[channel_name] = time.time()
                _save_cooldowns(cooldowns)
                return True
        print(f"[Heartbeat] Failed for {channel_name}: {r.status_code}")
    except Exception as e:
        print(f"[Heartbeat] Error for {channel_name}: {e}")
    return False
