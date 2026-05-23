"""
Daily Feed Summary Generator
Aggregates weather, deals, financial picks, news into a single JSON file.
Runs via GitHub Actions at 6:00 AM EST daily.
"""
import json
import os
import sys
import hashlib
from datetime import datetime, timezone, timedelta

import requests

# ModSecurity blocks python-requests User-Agent
API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

# Toronto coordinates for Open-Meteo
TORONTO_LAT = 43.6532
TORONTO_LON = -79.3832

# Base URLs
FC_API = "https://findtorontoevents.ca/fc/api"
LM_API = "https://findtorontoevents.ca/live-monitor/api"

# Motivational quotes pool
QUOTES = [
    {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
    {"text": "Success is not final, failure is not fatal: it is the courage to continue that counts.", "author": "Winston Churchill"},
    {"text": "Believe you can and you're halfway there.", "author": "Theodore Roosevelt"},
    {"text": "The best time to plant a tree was 20 years ago. The second best time is now.", "author": "Chinese Proverb"},
    {"text": "It does not matter how slowly you go as long as you do not stop.", "author": "Confucius"},
    {"text": "In the middle of difficulty lies opportunity.", "author": "Albert Einstein"},
    {"text": "The future belongs to those who believe in the beauty of their dreams.", "author": "Eleanor Roosevelt"},
    {"text": "Do what you can, with what you have, where you are.", "author": "Theodore Roosevelt"},
    {"text": "Every morning brings new potential, but if you dwell on the misfortunes of the day before, you tend to overlook tremendous opportunities.", "author": "Harvey Mackay"},
    {"text": "The secret of getting ahead is getting started.", "author": "Mark Twain"},
    {"text": "What you get by achieving your goals is not as important as what you become by achieving your goals.", "author": "Zig Ziglar"},
    {"text": "Don't watch the clock; do what it does. Keep going.", "author": "Sam Levenson"},
    {"text": "You miss 100% of the shots you don't take.", "author": "Wayne Gretzky"},
    {"text": "Opportunities don't happen. You create them.", "author": "Chris Grosser"},
    {"text": "The harder you work for something, the greater you'll feel when you achieve it.", "author": "Unknown"},
    {"text": "Dream big and dare to fail.", "author": "Norman Vaughan"},
    {"text": "Act as if what you do makes a difference. It does.", "author": "William James"},
    {"text": "Success usually comes to those who are too busy to be looking for it.", "author": "Henry David Thoreau"},
    {"text": "The way to get started is to quit talking and begin doing.", "author": "Walt Disney"},
    {"text": "If you are working on something that you really care about, you don't have to be pushed. The vision pulls you.", "author": "Steve Jobs"},
    {"text": "People who are crazy enough to think they can change the world are the ones who do.", "author": "Rob Siltanen"},
    {"text": "Failure will never overtake me if my determination to succeed is strong enough.", "author": "Og Mandino"},
    {"text": "We may encounter many defeats but we must not be defeated.", "author": "Maya Angelou"},
    {"text": "Knowing is not enough; we must apply. Wishing is not enough; we must do.", "author": "Johann Wolfgang Von Goethe"},
    {"text": "Whether you think you can or you think you can't, you're right.", "author": "Henry Ford"},
    {"text": "To be the best, you must be able to handle the worst.", "author": "Wilson Kanadi"},
    {"text": "I find that the harder I work, the more luck I seem to have.", "author": "Thomas Jefferson"},
    {"text": "A year from now you may wish you had started today.", "author": "Karen Lamb"},
    {"text": "Money is only a tool. It will take you wherever you wish, but it will not replace you as the driver.", "author": "Ayn Rand"},
    {"text": "Toronto is a city that works. It's like New York run by the Swiss.", "author": "Peter Ustinov"},
    {"text": "The stock market is a device for transferring money from the impatient to the patient.", "author": "Warren Buffett"},
]

# WMO weather codes
WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
    82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


def get_quote_of_day(date_str):
    """Deterministic quote based on date."""
    seed = int(hashlib.md5(date_str.encode()).hexdigest(), 16)
    return QUOTES[seed % len(QUOTES)]


def get_jacket_recommendation(temp_feels_like, precipitation_mm, weather_code):
    """Generate jacket/clothing recommendation based on weather."""
    if temp_feels_like <= -15:
        return {"needed": "yes", "message": "Extreme cold! Heavy winter coat, layers, and warm accessories are a must."}
    elif temp_feels_like <= -5:
        return {"needed": "yes", "message": "Very cold! Bundle up with a heavy coat, scarf, and gloves."}
    elif temp_feels_like <= 5:
        return {"needed": "yes", "message": "Cold out there. A warm jacket is definitely needed."}
    elif temp_feels_like <= 12:
        if precipitation_mm > 0 or weather_code in (61, 63, 65, 80, 81, 82):
            return {"needed": "yes", "message": "Cool and wet. Grab a waterproof jacket."}
        return {"needed": "yes", "message": "A bit chilly. A light jacket should do."}
    elif temp_feels_like <= 18:
        if precipitation_mm > 0:
            return {"needed": "maybe", "message": "Mild but rainy. A light rain jacket would be smart."}
        return {"needed": "maybe", "message": "Pleasant weather. A light layer just in case."}
    else:
        if precipitation_mm > 5:
            return {"needed": "maybe", "message": "Warm but rainy. Consider an umbrella or rain jacket."}
        return {"needed": "no", "message": "Warm and nice! No jacket needed. Enjoy the weather!"}


def fetch_weather():
    """Fetch Toronto weather from Open-Meteo (free, no key)."""
    print("  Fetching weather from Open-Meteo...")
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={TORONTO_LAT}&longitude={TORONTO_LON}"
            f"&current=temperature_2m,apparent_temperature,precipitation,weather_code"
            f"&daily=temperature_2m_max,temperature_2m_min"
            f"&timezone=America/Toronto&forecast_days=1"
        )
        resp = requests.get(url, headers=API_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current", {})
        daily = data.get("daily", {})

        temp = current.get("temperature_2m", 0)
        feels_like = current.get("apparent_temperature", 0)
        precip = current.get("precipitation", 0)
        code = current.get("weather_code", 0)
        high = daily.get("temperature_2m_max", [None])[0]
        low = daily.get("temperature_2m_min", [None])[0]

        jacket = get_jacket_recommendation(feels_like, precip, code)

        return {
            "current_temp": round(temp, 1),
            "feels_like": round(feels_like, 1),
            "high": round(high, 1) if high is not None else None,
            "low": round(low, 1) if low is not None else None,
            "precipitation_mm": round(precip, 1),
            "weather_code": code,
            "weather_desc": WMO_CODES.get(code, "Unknown"),
            "jacket_needed": jacket["needed"],
            "jacket_message": jacket["message"],
        }
    except Exception as e:
        print(f"  Weather error: {e}")
        return {"error": str(e)}


def fetch_freebies():
    """Fetch today's free deals."""
    print("  Fetching freebies...")
    try:
        resp = requests.get(
            f"{FC_API}/deals.php?action=free_today",
            headers=API_HEADERS, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        # API returns free_today (array of free items for today)
        items = data.get("free_today", data.get("deals", data.get("freebies", [])))
        if isinstance(items, list):
            return {
                "count": len(items),
                "top_5": items[:5],
                "all_items": items[:15],
                "today_day": data.get("today_day", ""),
                "link": f"{FC_API}/deals.php",
            }
        return {"count": 0, "top_5": [], "all_items": [], "link": f"{FC_API}/deals.php"}
    except Exception as e:
        print(f"  Freebies error: {e}")
        return {"count": 0, "top_5": [], "error": str(e), "link": f"{FC_API}/deals.php"}


def fetch_daily_picks():
    """Fetch daily picks (all, momentum, wins)."""
    result = {
        "stocks": {"count": 0, "top_3": []},
        "crypto": {"count": 0, "top_3": []},
        "forex": {"count": 0, "top_3": []},
        "momentum": {"top_3": []},
        "recent_wins": {"count": 0, "trades": []},
        "sports": {"available": False, "message": "Coming soon"},
        "ml_status": {
            "stocks": "active",
            "crypto": "active",
            "forex": "active",
            "penny_stocks": "screener_only",
            "sports": "wip",
        },
    }

    # All picks
    print("  Fetching daily picks (all)...")
    try:
        resp = requests.get(
            f"{LM_API}/daily_picks.php?action=all",
            headers=API_HEADERS, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()

        for category in ("stocks", "crypto", "forex"):
            items = data.get(category, [])
            if isinstance(items, list):
                result[category]["count"] = len(items)
                result[category]["top_3"] = items[:3]
    except Exception as e:
        print(f"  Daily picks (all) error: {e}")
        result["stocks"]["error"] = str(e)

    # Momentum
    print("  Fetching momentum picks...")
    try:
        resp = requests.get(
            f"{LM_API}/daily_picks.php?action=momentum",
            headers=API_HEADERS, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        picks = data.get("picks", data.get("momentum", []))
        if isinstance(picks, list):
            result["momentum"]["top_3"] = picks[:3]
    except Exception as e:
        print(f"  Momentum error: {e}")

    # Recent wins
    print("  Fetching recent wins...")
    try:
        resp = requests.get(
            f"{LM_API}/daily_picks.php?action=wins",
            headers=API_HEADERS, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        wins = data.get("wins", data.get("trades", []))
        if isinstance(wins, list):
            result["recent_wins"]["count"] = len(wins)
            result["recent_wins"]["trades"] = wins[:5]
    except Exception as e:
        print(f"  Wins error: {e}")

    # Sports picks (allow failure)
    print("  Fetching sports picks...")
    try:
        resp = requests.get(
            f"{LM_API}/sports_picks.php?action=today",
            headers=API_HEADERS, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok") and data.get("picks"):
            result["sports"] = {
                "available": True,
                "picks": data["picks"][:3],
                "count": len(data.get("picks", [])),
            }
    except Exception as e:
        print(f"  Sports picks error (non-fatal): {e}")

    return result


def fetch_news():
    """Fetch latest Toronto news."""
    print("  Fetching news...")
    try:
        resp = requests.get(
            f"{FC_API}/news_feed.php?action=get&category=toronto&per_page=10",
            headers=API_HEADERS, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("articles", data.get("stories", data.get("news", [])))
        if isinstance(articles, list):
            stories = []
            for a in articles[:10]:
                stories.append({
                    "title": a.get("title", ""),
                    "source": a.get("source", a.get("feed_name", "")),
                    "url": a.get("url", a.get("link", "")),
                    "published": a.get("published", a.get("pub_date", "")),
                })
            return {"count": len(stories), "stories": stories}
        return {"count": 0, "stories": []}
    except Exception as e:
        print(f"  News error: {e}")
        return {"count": 0, "stories": [], "error": str(e)}


def main():
    print("=== Daily Feed Summary Generator ===")

    est = timezone(timedelta(hours=-5))
    now_utc = datetime.now(timezone.utc)
    now_est = now_utc.astimezone(est)
    date_str = now_est.strftime("%Y-%m-%d")
    date_display = now_est.strftime("%A, %B %d, %Y")

    print(f"Date: {date_display}")
    print()

    # Build summary
    summary = {
        "generated_at": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date_display": date_display,
        "quote": get_quote_of_day(date_str),
        "weather": fetch_weather(),
        "freebies": fetch_freebies(),
        "financial": fetch_daily_picks(),
        "news": fetch_news(),
    }

    # Ensure output directory exists
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daily-feed", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "summary.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print()
    print(f"Summary written to: {out_path}")
    print(f"  Weather: {summary['weather'].get('weather_desc', 'N/A')} {summary['weather'].get('current_temp', '?')}C")
    print(f"  Freebies: {summary['freebies'].get('count', 0)}")
    print(f"  Stocks: {summary['financial']['stocks']['count']} | Crypto: {summary['financial']['crypto']['count']} | Forex: {summary['financial']['forex']['count']}")
    print(f"  News: {summary['news']['count']} stories")
    print(f"  Quote: \"{summary['quote']['text'][:60]}...\"")
    print()
    print("Done!")


if __name__ == "__main__":
    main()
