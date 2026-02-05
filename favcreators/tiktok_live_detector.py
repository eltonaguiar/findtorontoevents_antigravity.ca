import requests
import json
import os

def is_tiktok_live(username):
    """
    Checks if a TikTok user is currently live.
    Returns a tuple: (is_live: bool, details: dict)
    """
    url = f"https://www.tiktok.com/@{username}/live"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return False, {"error": f"HTTP {resp.status_code}"}
        html = resp.text
        # Stricter: require both a <video> element and a live badge, and no story/offline markers
        has_video = '<video' in html
        has_live_badge = 'data-e2e="live-badge"' in html or 'LIVE NOW' in html or 'isLive":true' in html
        is_story = 'story' in html.lower()
        is_offline = (
            'LIVE_UNAVAILABLE' in html
            or '"status":2' in html
            or 'This LIVE has ended' in html
            or 'currently unavailable' in html
        )
        is_live = has_video and has_live_badge and not is_story and not is_offline
        details = {
            "status_code": resp.status_code,
            "checked_url": url,
            "has_video": has_video,
            "has_live_badge": has_live_badge,
            "is_story": is_story,
            "is_offline": is_offline
        }
        return is_live, details
    except Exception as e:
        return False, {"error": str(e)}

def main():
    username = "starfireara"
    is_live, details = is_tiktok_live(username)
    output = {
        "username": username,
        "is_live": is_live,
        "details": details
    }
    out_dir = r"C:\Users\zerou\Documents\FAVCREATORS"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"tiktok_live_{username}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"Result written to {out_path}")

if __name__ == "__main__":
    main()
