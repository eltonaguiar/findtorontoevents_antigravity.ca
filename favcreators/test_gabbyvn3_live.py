
import asyncio
import json
import os
from playwright.async_api import async_playwright

def get_output_path(username):
    # Save to both Documents (legacy) and the project public folder (for web access)
    base_dirs = [
        r"C:\Users\zerou\Documents\FAVCREATORS",
        os.path.join(os.path.dirname(__file__), "public")
    ]
    
    paths = []
    for base in base_dirs:
        os.makedirs(base, exist_ok=True)
        paths.append(os.path.join(base, f"tiktok_live_{username}_playwright.json"))
    
    return paths

async def is_tiktok_live_playwright(username):
    url = f"https://www.tiktok.com/@{username}/live"
    async with async_playwright() as p:
        # Use non-headless for more reliability
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US"
        )
        page = await context.new_page()
        # Set extra headers to mimic a real browser
        await page.set_extra_http_headers({
            "accept-language": "en-US,en;q=0.9",
            "sec-ch-ua": '"Chromium";v="120", "Not:A-Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        })
        await page.goto(url, timeout=30000)
        # Wait for the main content to load
        await page.wait_for_selector('body', timeout=15000)
        is_live = False
        details = {}
        try:
            badge = await page.query_selector('span[data-e2e="live-badge"]')
            badge_text = (await badge.inner_text()) if badge else ""
            video = await page.query_selector('video')
            content = await page.content()
            has_live_badge = badge and "LIVE" in badge_text.upper()
            has_video = video is not None
            is_story = "story" in content.lower()
            is_offline = (
                "LIVE_UNAVAILABLE" in content
                or '"status":2' in content
                or "This LIVE has ended" in content
                or "currently unavailable" in content
            )
            # Only mark as live if both video and live badge, and not a story or offline
            if has_video and has_live_badge and not is_story and not is_offline:
                is_live = True
                details['badge_text'] = badge_text
                details['video_found'] = True
            else:
                is_live = False
                if is_offline:
                    details['offline_reason'] = 'offline marker found'
                if is_story:
                    details['story_detected'] = True
            # For debugging, add all checks
            details['has_video'] = has_video
            details['has_live_badge'] = has_live_badge
            details['is_story'] = is_story
            details['is_offline'] = is_offline
        except Exception as e:
            details['exception'] = str(e)
        await browser.close()
        return is_live, details

def main():
    username = "gabbyvn3"
    is_live = False
    details = {}
    try:
        is_live, details = asyncio.run(is_tiktok_live_playwright(username))
    except Exception as e:
        details['error'] = str(e)
    output = {
        "username": username,
        "is_live": is_live,
        "details": details
    }
    out_paths = get_output_path(username)
    for path in out_paths:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2)
            print(f"Result written to {path}")
        except Exception as e:
            print(f"Failed to write to {path}: {e}")

if __name__ == "__main__":
    main()
