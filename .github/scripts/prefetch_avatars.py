#!/usr/bin/env python3
"""
GitHub Actions script: Pre-fetch avatar URLs for all FavCreators.

Fetches the full creator list from the API, resolves avatar URLs from
multiple sources (Kick API, Twitch DecAPI, Unavatar, etc.), validates
them with HEAD requests, and POSTs the results to the avatar_cache
endpoint on the server.

Environment variables:
    FC_API_BASE         Base URL  (default: https://findtorontoevents.ca/fc)
    AVATAR_CACHE_TOKEN  Secret token for the POST endpoint
    AVATAR_MAX_CREATORS Max creators to process per run (default: 200)
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime

# ── Configuration ────────────────────────────────────────────────────────
API_BASE = os.environ.get("FC_API_BASE", "https://findtorontoevents.ca/fc")
CACHE_TOKEN = os.environ.get("AVATAR_CACHE_TOKEN", "")
MAX_CREATORS = int(os.environ.get("AVATAR_MAX_CREATORS", "200"))
REQUEST_TIMEOUT = 10  # seconds per HTTP request
BATCH_SIZE = 50       # POST this many avatars at a time
RATE_LIMIT_DELAY = 0.3  # seconds between external API calls

# User-Agent to avoid blocks
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def http_get(url, timeout=REQUEST_TIMEOUT):
    """GET request, returns (status, body_str | None)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        body = resp.read().decode("utf-8", errors="replace")
        return resp.getcode(), body
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def http_head(url, timeout=6):
    """HEAD request — returns True if the URL responds 200."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return 200 <= resp.getcode() < 400
    except Exception:
        return False


def http_post_json(url, data, timeout=30):
    """POST JSON, returns (status, body_str)."""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": UA,
            "X-Avatar-Token": CACHE_TOKEN,
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.getcode(), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace") if e.fp else ""
    except Exception as ex:
        return 0, str(ex)


# ── Avatar source resolvers ─────────────────────────────────────────────

def resolve_kick(username):
    """Kick API v1 → profile picture URL."""
    url = f"https://kick.com/api/v1/channels/{username}"
    status, body = http_get(url)
    if status == 200 and body:
        try:
            data = json.loads(body)
            pic = data.get("user", {}).get("profile_pic", "")
            if pic and pic.startswith("http"):
                return pic
        except Exception:
            pass
    return None


def resolve_twitch_decapi(username):
    """Twitch DecAPI → avatar URL (plain text response)."""
    url = f"https://decapi.me/twitch/avatar/{username}"
    status, body = http_get(url)
    if status == 200 and body and body.strip().startswith("http"):
        return body.strip()
    return None


def resolve_unavatar(platform, username):
    """unavatar.io → redirects to actual avatar."""
    platform_map = {
        "tiktok": "tiktok",
        "youtube": "youtube",
        "twitch": "twitch",
        "instagram": "instagram",
        "twitter": "twitter",
        "github": "github",
    }
    ua_platform = platform_map.get(platform)
    if not ua_platform:
        return None
    url = f"https://unavatar.io/{ua_platform}/{username}"
    # unavatar returns a redirect or image — just validate with HEAD
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        resp = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT)
        final_url = resp.geturl()
        code = resp.getcode()
        if 200 <= code < 400:
            # Skip if it redirected to a default/fallback image
            if "default" in final_url.lower() or "fallback" in final_url.lower():
                return None
            return final_url if final_url != url else url
    except Exception:
        pass
    return None


# ── Main logic ───────────────────────────────────────────────────────────

def fetch_all_creators():
    """Fetch the guest creator list (user_id=0) to get all creators + accounts."""
    url = f"{API_BASE}/api/get_my_creators.php?user_id=0"
    log(f"Fetching creators from {url}")
    status, body = http_get(url, timeout=30)
    if status != 200 or not body:
        log(f"Failed to fetch creators: HTTP {status}")
        return []
    try:
        data = json.loads(body)
        creators = data.get("creators", [])
        log(f"Got {len(creators)} creators from API")
        return creators
    except Exception as e:
        log(f"JSON parse error: {e}")
        return []


def resolve_avatars_for_creator(creator):
    """
    Try multiple sources for each account of a creator.
    Returns list of {creator_id, source, platform, username, avatar_url}.
    """
    cid = creator.get("id", "")
    name = creator.get("name", "")
    accounts = creator.get("accounts", [])
    if isinstance(accounts, str):
        try:
            accounts = json.loads(accounts)
        except Exception:
            accounts = []
    if not isinstance(accounts, list):
        accounts = []

    results = []
    seen_urls = set()

    def add(url, platform, source, username):
        if not url or not url.startswith("http"):
            return
        norm = url.split("?")[0]
        if norm in seen_urls:
            return
        # Skip generated/placeholder avatars
        for skip in ("dicebear.com", "ui-avatars.com", "default-avatar", "placeholder"):
            if skip in url.lower():
                return
        seen_urls.add(norm)
        results.append({
            "creator_id": cid,
            "source": source,
            "platform": platform,
            "username": username,
            "avatar_url": url,
        })

    for account in accounts:
        platform = account.get("platform", "").lower()
        username = account.get("username", "")
        if not username:
            continue

        # 1) Kick API
        if platform == "kick":
            try:
                url = resolve_kick(username)
                add(url, platform, "kick_api", username)
                time.sleep(RATE_LIMIT_DELAY)
            except Exception:
                pass

        # 2) Twitch DecAPI
        if platform == "twitch":
            try:
                url = resolve_twitch_decapi(username)
                add(url, platform, "twitch_decapi", username)
                time.sleep(RATE_LIMIT_DELAY)
            except Exception:
                pass

        # 3) Unavatar (works for most platforms)
        try:
            url = resolve_unavatar(platform, username)
            add(url, platform, f"unavatar_{platform}", username)
            time.sleep(RATE_LIMIT_DELAY)
        except Exception:
            pass

    return results


def validate_avatars(avatar_list):
    """HEAD-check each avatar URL and keep only valid ones."""
    valid = []
    for entry in avatar_list:
        url = entry["avatar_url"]
        if http_head(url):
            valid.append(entry)
        else:
            log(f"  Invalid (HEAD failed): {url}")
        time.sleep(0.1)
    return valid


def post_to_cache(avatars):
    """Send batch of avatars to the avatar_cache endpoint."""
    url = f"{API_BASE}/api/avatar_cache.php"

    for i in range(0, len(avatars), BATCH_SIZE):
        batch = avatars[i:i + BATCH_SIZE]
        payload = {"avatars": batch}
        if CACHE_TOKEN:
            payload["token"] = CACHE_TOKEN

        status, body = http_post_json(url, payload)
        try:
            resp = json.loads(body)
            saved = resp.get("saved", 0)
            errors = resp.get("errors", 0)
            log(f"  Batch {i // BATCH_SIZE + 1}: saved={saved}, errors={errors}")
        except Exception:
            log(f"  Batch {i // BATCH_SIZE + 1}: HTTP {status}, body: {body[:200]}")


def main():
    log("=" * 60)
    log("Avatar Prefetch — starting")
    log(f"API base: {API_BASE}")
    log(f"Max creators: {MAX_CREATORS}")
    log(f"Token configured: {'yes' if CACHE_TOKEN else 'no (open writes)'}")
    log("=" * 60)

    creators = fetch_all_creators()
    if not creators:
        log("No creators found — exiting.")
        sys.exit(1)

    # Limit to MAX_CREATORS
    creators = creators[:MAX_CREATORS]
    log(f"Processing {len(creators)} creators...")

    all_avatars = []
    stats = {"processed": 0, "avatars_found": 0, "avatars_valid": 0}

    for i, creator in enumerate(creators):
        name = creator.get("name", "?")
        cid = creator.get("id", "?")
        log(f"[{i + 1}/{len(creators)}] {name} ({cid})")

        found = resolve_avatars_for_creator(creator)
        if found:
            valid = validate_avatars(found)
            log(f"  Found {len(found)} avatars, {len(valid)} valid")
            all_avatars.extend(valid)
            stats["avatars_found"] += len(found)
            stats["avatars_valid"] += len(valid)
        else:
            log(f"  No avatars found")
        stats["processed"] += 1

    log("")
    log(f"Resolved {stats['avatars_valid']} valid avatars for {stats['processed']} creators")

    if all_avatars:
        log(f"Posting {len(all_avatars)} avatars to cache...")
        post_to_cache(all_avatars)
    else:
        log("No avatars to cache.")

    # Write summary for GitHub Actions artifact
    summary = {
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "creators_processed": stats["processed"],
        "avatars_found": stats["avatars_found"],
        "avatars_valid": stats["avatars_valid"],
        "avatars_cached": len(all_avatars),
    }
    with open("avatar_prefetch_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    log(f"Summary: {json.dumps(summary)}")
    log("Done.")


if __name__ == "__main__":
    main()
