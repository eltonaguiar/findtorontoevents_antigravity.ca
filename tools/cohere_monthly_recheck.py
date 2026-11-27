#!/usr/bin/env python3
"""Re-check the Cohere trial key after its monthly quota resets.

Cohere trial keys allow 1000 API calls per calendar month. When that is spent
every chat returns `429 You are using a Trial key, which is limited to 1000 API
calls / month`, even though `GET /v2/models` still answers 200 — so the key
looks alive while carrying no traffic. That is exactly the state we found it in
on 2026-11-27, and the deployments were removed from litellm_config.yaml.

This probe is meant to run on the 1st of each month (see the cron line in
updates/2026-11-27-provider-model-refresh-and-cleanup.md §15):

  * probe the key with one tiny chat call;
  * if it answers 200, put the two Cohere deployments back into `free-mode` and
    `free-mode-large`, restart the proxy and verify `free-mode` still answers;
  * if it is still 429, change nothing and record that;
  * always write reports/cohere_recheck_state.json so the next run (and a human)
    can see what happened without reading logs.

Usage:
    python3 tools/cohere_monthly_recheck.py --dry-run   # probe only
    python3 tools/cohere_monthly_recheck.py             # probe + wire + restart
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG = REPO_ROOT / "litellm_config.yaml"
STATE = REPO_ROOT / "reports" / "cohere_recheck_state.json"
PASSES_FILE = Path.home() / "dbpasses.txt"
PROXY = "http://127.0.0.1:4000"
MODEL = "command-r-plus-08-2024"

# The literal lines inserted when the quota is back. They match the shape of the
# rest of the file: `openai/`-less Cohere provider prefix, key from the launcher.
DEPLOYMENTS = (
    "  # Re-added automatically by tools/cohere_monthly_recheck.py once the monthly "
    "1000-call trial quota reset.\n"
    "  - {model_name: free-mode, litellm_params: {model: cohere/command-r-plus-08-2024, "
    "api_key: os.environ/COHERE_API_KEY}}\n"
)


def load_key() -> str | None:
    """Read the value that follows the COHERE_TRIAL_API_KEY label in ~/dbpasses.txt."""
    if not PASSES_FILE.is_file():
        return None
    lines = PASSES_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        if line.strip().upper().startswith("COHERE_TRIAL_API_KEY"):
            for candidate in lines[i + 1: i + 4]:
                value = candidate.strip()
                if value and not value.endswith(":") and not value.startswith("http"):
                    return value.split(" #")[0].strip()
    return None


def probe(key: str) -> tuple[int, str]:
    body = json.dumps(
        {"model": MODEL, "messages": [{"role": "user", "content": "Say OK"}], "max_tokens": 8}
    ).encode()
    request = urllib.request.Request(
        "https://api.cohere.com/v2/chat",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.getcode(), response.read().decode()[:400]
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()[:400]
    except Exception as error:  # network, DNS, timeout
        return 0, f"{type(error).__name__}: {error}"


def wire_deployments() -> bool:
    """Insert the Cohere deployments once. Returns True when the file changed."""
    text = CONFIG.read_text(encoding="utf-8")
    if "cohere/command-r-plus-08-2024" in text:
        return False

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    inserted = 0
    for line in lines:
        out.append(line)
        if inserted < 2 and re.search(r"model_name:\s*free-mode(-large)?,", line):
            out.append(DEPLOYMENTS)
            inserted += 1
    if inserted == 0:
        return False
    CONFIG.write_text("".join(out), encoding="utf-8")
    return True


def restart_proxy() -> bool:
    subprocess.run(["pkill", "-f", "[l]itellm --config"], check=False)
    time.sleep(2)
    subprocess.Popen(
        ["setsid", "bash", str(REPO_ROOT / "tools" / "start_litellm_proxy.sh"), "--background"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(30):
        time.sleep(2)
        try:
            with urllib.request.urlopen(f"{PROXY}/health/liveliness", timeout=5) as response:
                if response.getcode() == 200:
                    return True
        except Exception:
            continue
    return False


def free_mode_answers() -> tuple[int, str]:
    body = json.dumps(
        {"model": "free-mode", "messages": [{"role": "user", "content": "Reply with OK"}], "max_tokens": 16}
    ).encode()
    request = urllib.request.Request(
        f"{PROXY}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.getcode(), response.read().decode()[:200]
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()[:200]
    except Exception as error:
        return 0, f"{type(error).__name__}: {error}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="probe only, never edit config or restart")
    parser.add_argument("--no-restart", action="store_true", help="wire the deployments but do not restart")
    args = parser.parse_args()

    record: dict[str, object] = {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": MODEL,
        "dry_run": bool(args.dry_run),
    }

    key = load_key()
    if not key:
        record.update(status="no_key", detail="COHERE_TRIAL_API_KEY not found in ~/dbpasses.txt")
        write_state(record)
        print("no Cohere key found in ~/dbpasses.txt")
        return 0
    record["key_masked"] = key[:5] + "…" + ("*" * 6)

    code, body = probe(key)
    record["probe_http"] = code
    record["probe_body"] = body.replace("\n", " ")[:300]

    if code == 200:
        record["status"] = "quota_available"
    elif code == 429:
        record["status"] = "quota_exhausted"
        write_state(record)
        print("cohere still 429 (trial quota spent) — nothing changed")
        return 0
    elif code in (401, 403):
        record["status"] = "key_rejected"
        write_state(record)
        print(f"cohere key rejected ({code}) — needs a new key, nothing changed")
        return 0
    else:
        record["status"] = "probe_failed"
        write_state(record)
        print(f"cohere probe failed ({code}) — nothing changed")
        return 1

    if args.dry_run:
        record["wired"] = False
        write_state(record)
        print("cohere quota is back (dry run) — would wire free-mode + free-mode-large")
        return 0

    changed = wire_deployments()
    record["wired"] = changed
    if changed and not args.no_restart:
        record["proxy_restarted"] = restart_proxy()
        record["free_mode_http"] = free_mode_answers()[0]
    write_state(record)
    print(json.dumps({k: record[k] for k in ("status", "wired") if k in record}, indent=2))
    return 0


def write_state(record: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
