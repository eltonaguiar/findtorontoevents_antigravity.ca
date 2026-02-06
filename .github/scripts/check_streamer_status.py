#!/usr/bin/env python3
"""
GitHub Actions script to check streamer live status automatically.
Fetches ALL creators from the database, prioritizing those not checked recently.
Updates the last_seen tracking database when streamers are found online.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any

# Configuration
API_BASE = os.environ.get('FC_API_BASE', 'https://findtorontoevents.ca/fc')
CHECKER_EMAIL = os.environ.get('FC_CHECKER_EMAIL', 'github-actions@findtorontoevents.ca')
MAX_RETRIES = 3
RETRY_DELAY = 2
# How many streamers to check per run (GitHub Actions has time limits)
MAX_STREAMERS_PER_RUN = int(os.environ.get('FC_MAX_STREAMERS', '50'))
# Only check streamers not checked in the last N minutes
MIN_AGE_MINUTES = int(os.environ.get('FC_MIN_AGE_MINUTES', '60'))

# Fallback streamers if API fails
DEFAULT_STREAMERS = [
    {
        "creator_id": "wtfpreston",
        "creator_name": "WTFPreston",
        "platform": "tiktok",
        "username": "wtfprestonlive",
        "url": "https://www.tiktok.com/@wtfprestonlive"
    },
    {
        "creator_id": "adinross",
        "creator_name": "Adin Ross",
        "platform": "kick",
        "username": "adinross",
        "url": "https://kick.com/adinross"
    },
    {
        "creator_id": "loltyler1",
        "creator_name": "loltyler1",
        "platform": "twitch",
        "username": "loltyler1",
        "url": "https://twitch.tv/loltyler1"
    }
]

def log_message(message: str, log_file=None):
    """Print and optionally log a message."""
    timestamp = datetime.now().isoformat()
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    if log_file:
        log_file.write(full_message + "\n")

def _http_get(url: str, timeout: int = 30) -> Dict[str, Any]:
    """Make an HTTP GET request using urllib (no external deps)."""
    req = urllib.request.Request(url, headers={"User-Agent": "FavCreators-GitHub-Actions/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    body = resp.read().decode("utf-8")
    return {"status": resp.status, "data": json.loads(body)}

def _http_post_json(url: str, payload: dict, timeout: int = 30) -> Dict[str, Any]:
    """Make an HTTP POST request with JSON body using urllib."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "User-Agent": "FavCreators-GitHub-Actions/1.0"
    })
    resp = urllib.request.urlopen(req, timeout=timeout)
    body = resp.read().decode("utf-8")
    return {"status": resp.status, "data": json.loads(body)}

def check_live_status(platform: str, username: str) -> Dict[str, Any]:
    """
    Check if a streamer is live using the TLC.php endpoint.
    """
    params = urllib.parse.urlencode({"platform": platform, "user": username})
    url = f"{API_BASE}/TLC.php?{params}"

    for attempt in range(MAX_RETRIES):
        try:
            result = _http_get(url)

            if result["status"] == 200:
                data = result["data"]
                return {
                    "is_live": data.get("live", False),
                    "method": data.get("method", "unknown"),
                    "account_status": data.get("account_status", "unknown"),
                    "stream_title": data.get("title", ""),
                    "viewer_count": data.get("viewers", 0),
                    "success": True
                }
            else:
                log_message(f"HTTP {result['status']} for {platform}/{username}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        except urllib.error.URLError as e:
            log_message(f"Timeout/network error checking {platform}/{username} (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
        except Exception as e:
            log_message(f"Error checking {platform}/{username}: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    return {
        "is_live": False,
        "method": "error",
        "account_status": "error",
        "stream_title": "",
        "viewer_count": 0,
        "success": False
    }

def update_last_seen(streamer: Dict[str, Any], status: Dict[str, Any]) -> bool:
    """
    Update the last_seen tracking database.
    """
    url = f"{API_BASE}/api/update_streamer_last_seen.php"
    
    payload = {
        "creator_id": streamer["creator_id"],
        "creator_name": streamer["creator_name"],
        "platform": streamer["platform"],
        "username": streamer["username"],
        "account_url": streamer["url"],
        "is_live": status["is_live"],
        "stream_title": status.get("stream_title", ""),
        "viewer_count": status.get("viewer_count", 0),
        "checked_by": CHECKER_EMAIL
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            result = _http_post_json(url, payload)

            if result["status"] == 200:
                data = result["data"]
                if data.get("ok"):
                    return True
                else:
                    log_message(f"API error: {data.get('error')}")
                    return False
            else:
                log_message(f"HTTP {result['status']} updating {streamer['creator_id']}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        except Exception as e:
            log_message(f"Error updating {streamer['creator_id']}: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    return False

def get_streamers_from_api() -> List[Dict[str, Any]]:
    """
    Fetch ALL streamers from the database that need checking.
    Uses the new endpoint that prioritizes accounts not checked recently.
    """
    # Use the new endpoint that fetches all streamers, prioritized by last check time
    url = f"{API_BASE}/api/get_all_streamers_to_check.php?limit={MAX_STREAMERS_PER_RUN}&min_age_minutes={MIN_AGE_MINUTES}"
    
    try:
        result = _http_get(url, timeout=30)
        
        if result["status"] == 200:
            data = result["data"]
            if data.get("ok") and "streamers" in data:
                streamers = data["streamers"]
                stats = data.get("stats", {})
                
                log_message(f"Database stats: {stats.get('total_tracked', 0)} total tracked, "
                           f"{stats.get('checked_last_hour', 0)} checked in last hour, "
                           f"{stats.get('currently_live', 0)} currently live")
                log_message(f"Fetched {len(streamers)} streamers to check (limit={MAX_STREAMERS_PER_RUN}, min_age={MIN_AGE_MINUTES}min)")
                
                if len(streamers) > 0:
                    # Log first few for debugging
                    for s in streamers[:3]:
                        last_check = s.get('last_checked', 'never')
                        log_message(f"  - {s['creator_name']} ({s['platform']}) - last checked: {last_check}")
                    if len(streamers) > 3:
                        log_message(f"  ... and {len(streamers) - 3} more")
                    
                    return streamers
            
            log_message("API returned no streamers, falling back to guest list")
            return get_streamers_from_guest_list()
            
        else:
            log_message(f"Failed to fetch streamers: HTTP {result['status']}, falling back to guest list")
            return get_streamers_from_guest_list()
            
    except Exception as e:
        log_message(f"Error fetching streamers: {str(e)}, falling back to guest list")
        return get_streamers_from_guest_list()


def get_streamers_from_guest_list() -> List[Dict[str, Any]]:
    """
    Fallback: Fetch streamers from guest list (user_id=0).
    """
    url = f"{API_BASE}/api/get_my_creators.php?user_id=0"
    
    try:
        result = _http_get(url, timeout=30)
        
        if result["status"] == 200:
            data = result["data"]
            if isinstance(data, dict) and "creators" in data:
                creators = data["creators"]
                streamers = []
                
                for creator in creators:
                    accounts = creator.get("accounts", [])
                    if isinstance(accounts, list):
                        for account in accounts:
                            platform = account.get("platform", "").lower()
                            if platform in ["tiktok", "twitch", "kick", "youtube"]:
                                streamers.append({
                                    "creator_id": creator.get("id", ""),
                                    "creator_name": creator.get("name", ""),
                                    "platform": platform,
                                    "username": account.get("username", ""),
                                    "url": account.get("url", "")
                                })
                
                log_message(f"Fallback: Got {len(streamers)} streamers from guest list")
                if len(streamers) > 0:
                    return streamers
        
        log_message("Fallback failed, using default list")
        return DEFAULT_STREAMERS
        
    except Exception as e:
        log_message(f"Fallback error: {str(e)}, using default list")
        return DEFAULT_STREAMERS

def main():
    log_file = open("streamer_check_log.txt", "w")
    
    log_message("=" * 60, log_file)
    log_message("Starting streamer status check", log_file)
    log_message(f"API Base: {API_BASE}", log_file)
    log_message(f"Checker: {CHECKER_EMAIL}", log_file)
    log_message("=" * 60, log_file)
    
    # Get streamers to check
    streamers = get_streamers_from_api()
    log_message(f"Checking {len(streamers)} streamers", log_file)
    
    results = {
        "checked_at": datetime.now().isoformat(),
        "checker": CHECKER_EMAIL,
        "streamers": [],
        "summary": {
            "total": len(streamers),
            "live": 0,
            "offline": 0,
            "errors": 0,
            "updated": 0
        }
    }
    
    # Check each streamer
    for i, streamer in enumerate(streamers):
        log_message(f"\n[{i+1}/{len(streamers)}] Checking {streamer['creator_name']} ({streamer['platform']})", log_file)
        
        status = check_live_status(streamer["platform"], streamer["username"])
        
        result = {
            "creator_id": streamer["creator_id"],
            "creator_name": streamer["creator_name"],
            "platform": streamer["platform"],
            "username": streamer["username"],
            "is_live": status["is_live"],
            "method": status["method"],
            "success": status["success"]
        }
        
        if status["success"]:
            log_message(f"  Status: {'LIVE' if status['is_live'] else 'offline'} (method: {status['method']})", log_file)
            
            if status["is_live"]:
                results["summary"]["live"] += 1
                if status.get("stream_title"):
                    log_message(f"  Title: {status['stream_title']}", log_file)
                if status.get("viewer_count"):
                    log_message(f"  Viewers: {status['viewer_count']}", log_file)
            else:
                results["summary"]["offline"] += 1
            
            # Update the tracking database
            updated = update_last_seen(streamer, status)
            if updated:
                results["summary"]["updated"] += 1
                result["updated"] = True
                log_message(f"  Database updated successfully", log_file)
            else:
                result["updated"] = False
                log_message(f"  Failed to update database", log_file)
        else:
            results["summary"]["errors"] += 1
            result["error"] = True
            log_message(f"  Error checking status", log_file)
        
        results["streamers"].append(result)
        
        # Small delay to be nice to the APIs
        time.sleep(1)
    
    # Save results
    with open("streamer_check_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    log_message("\n" + "=" * 60, log_file)
    log_message("Check complete!", log_file)
    log_message(f"Total: {results['summary']['total']}", log_file)
    log_message(f"Live: {results['summary']['live']}", log_file)
    log_message(f"Offline: {results['summary']['offline']}", log_file)
    log_message(f"Errors: {results['summary']['errors']}", log_file)
    log_message(f"Updated: {results['summary']['updated']}", log_file)
    log_message("=" * 60, log_file)
    
    log_file.close()
    
    # Exit with error if all checks failed
    if results["summary"]["errors"] == results["summary"]["total"]:
        print("\nERROR: All streamer checks failed")
        sys.exit(1)
    
    print(f"\nSuccess: Checked {results['summary']['total']} streamers, {results['summary']['live']} currently live")
    sys.exit(0)

if __name__ == "__main__":
    main()