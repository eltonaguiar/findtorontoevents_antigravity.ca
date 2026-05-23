#!/usr/bin/env python3
import json
import pathlib
import requests
import sys
from datetime import datetime

# Paths
MANIFEST_PATH = pathlib.Path("e:/findtorontoevents_antigravity.ca/hub/data/systems_manifest.json")
# In a real environment, this would be a real webhook
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/mock_webhook" 

def load_manifest():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def ping(url):
    """Check if a URL is reachable and returns 200."""
    try:
        # Some endpoints might be local files or relative paths in a real scenario
        # but for this audit we assume they are the 'active' URLs in manifest.
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error pinging {url}: {e}")
        return False

def alert(message):
    """Send alert to Discord/Slack."""
    print(f"ALERT: {message}")
    # payload = {"content": message}
    # requests.post(DISCORD_WEBHOOK, json=payload)

def main():
    try:
        data = load_manifest()
    except Exception as e:
        alert(f"Failed to load manifest: {e}")
        sys.exit(1)

    failures = []
    active_systems = [s for s in data["systems"] if s.get("status") == "active"]
    
    print(f"Checking {len(active_systems)} active systems...")

    for system in active_systems:
        sys_id = system["id"]
        endpoints = system.get("data_endpoints", {})
        
        # Check 'active' picks endpoint
        active_url = endpoints.get("active")
        if active_url:
            if not ping(active_url):
                failures.append(f"{sys_id} (active)")
        
        # Check 'closed' picks endpoint
        closed_url = endpoints.get("closed")
        if closed_url:
            if not ping(closed_url):
                failures.append(f"{sys_id} (closed)")

    if failures:
        ts = datetime.utcnow().isoformat()
        alert(f"⚠️ Audit Feed Health Failure at {ts}Z\nMissing: {', '.join(failures)}")
        sys.exit(1)
    else:
        print("✅ All active feeds are healthy.")
        sys.exit(0)

if __name__ == "__main__":
    main()
