#!/usr/bin/env python3
"""
Refresh Toronto Event Resources
Scrapes real event data from the 50+ resource source websites and updates
resources/resources.json with fresh sample events for each source.

Runs daily via GitHub Actions (.github/workflows/refresh-resources.yml).

Usage:
    python tools/refresh_resources.py                # Scrape and update
    python tools/refresh_resources.py --dry-run      # Preview without writing
    python tools/refresh_resources.py --deploy       # Update + FTP deploy
"""
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Install dependencies: pip install requests beautifulsoup4 lxml")
    sys.exit(1)

# Fix Windows console encoding for emoji output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
RESOURCES_JSON = PROJECT_ROOT / "resources" / "resources.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8",
}

TODAY = datetime.now()
TODAY_STR = TODAY.strftime("%B %d").replace(" 0", " ")  # "February 15"
TODAY_SHORT = TODAY.strftime("%b %d").replace(" 0", " ")  # "Feb 15"


def fetch_page(url, timeout=15):
    """Fetch a page with error handling and rate limiting."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  [WARN] Failed to fetch {url}: {e}")
        return None


def parse_date_text(text):
    """Try to extract a human-readable date from various formats."""
    text = text.strip()
    # Already short enough
    if len(text) < 30:
        return text
    # Try to extract "Mon DD" or "Month DD"
    m = re.search(r'(\w{3,9}\s+\d{1,2})', text)
    if m:
        return m.group(1)
    return text[:25]


def fmt_price(text):
    """Normalize price text."""
    if not text:
        return "See Site"
    text = text.strip()
    if text.lower() in ("free", "$0", "$0.00", "0"):
        return "Free"
    if "$" in text:
        m = re.search(r'\$[\d,.]+', text)
        if m:
            return m.group(0) + "+"
    return text[:20] if len(text) > 20 else text


# ═══════════════════════════════════════════════════════
# SOURCE SCRAPERS — one per resource source
# Each returns a list of {"title": ..., "date": ..., "price": ...}
# ═══════════════════════════════════════════════════════

def scrape_eventbrite():
    """Scrape upcoming events from Eventbrite Toronto."""
    events = []
    html = fetch_page("https://www.eventbrite.ca/d/canada--toronto/events/")
    if not html:
        return events
    soup = BeautifulSoup(html, "lxml")

    # Try JSON-LD first
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            items = []
            if isinstance(data, dict) and data.get("@type") == "ItemList":
                items = data.get("itemListElement", [])
            elif isinstance(data, list):
                items = data
            for item in items:
                evt = item.get("item", item) if isinstance(item, dict) else {}
                if evt.get("@type") == "Event":
                    title = evt.get("name", "")
                    start = evt.get("startDate", "")
                    price = ""
                    offers = evt.get("offers", {})
                    if isinstance(offers, dict):
                        price = offers.get("lowPrice", offers.get("price", ""))
                    if title and start:
                        try:
                            dt = datetime.fromisoformat(start.replace("Z", "+00:00").split("+")[0])
                            date_str = dt.strftime("%b %d").replace(" 0", " ")
                        except Exception:
                            date_str = start[:10]
                        events.append({
                            "title": title[:60],
                            "date": date_str,
                            "price": fmt_price(str(price)) if price else "See Site"
                        })
        except (json.JSONDecodeError, Exception):
            continue

    # Fallback: parse HTML cards
    if not events:
        for card in soup.select("[data-testid='event-card'],.discover-search-desktop-card"):
            title_el = card.select_one("h2, h3, .event-card__title, [data-testid='event-card-title']")
            date_el = card.select_one("p, .event-card__date, [data-testid='event-card-date']")
            if title_el:
                title = title_el.get_text(strip=True)
                date = date_el.get_text(strip=True) if date_el else ""
                events.append({"title": title[:60], "date": parse_date_text(date), "price": "See Site"})

    return events[:3]


def scrape_meetup():
    """Scrape Meetup.com Toronto events."""
    events = []
    html = fetch_page("https://www.meetup.com/find/?source=EVENTS&location=ca--on--Toronto&eventType=inPerson")
    if not html:
        return events
    soup = BeautifulSoup(html, "lxml")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for evt in items:
                if evt.get("@type") == "Event":
                    title = evt.get("name", "")
                    start = evt.get("startDate", "")
                    free = evt.get("isAccessibleForFree", False)
                    if title:
                        try:
                            dt = datetime.fromisoformat(start.replace("Z", "+00:00").split("+")[0])
                            date_str = dt.strftime("%b %d").replace(" 0", " ")
                        except Exception:
                            date_str = ""
                        events.append({
                            "title": title[:60],
                            "date": date_str or "See Site",
                            "price": "Free" if free else "See Site"
                        })
        except Exception:
            continue

    if not events:
        for card in soup.select("[id*='event-card'], .eventCardHead--lg, .searchResult"):
            title_el = card.select_one("h2, h3, .text--bold, .eventCardHead--title")
            date_el = card.select_one("time, .eventTimeDisplay")
            if title_el:
                events.append({
                    "title": title_el.get_text(strip=True)[:60],
                    "date": date_el.get_text(strip=True)[:20] if date_el else "See Site",
                    "price": "Free-$"
                })

    return events[:3]


def scrape_ticketmaster():
    """Scrape Ticketmaster Toronto events via Discovery API if key available, else HTML."""
    events = []
    api_key = os.environ.get("TICKETMAST_CONSUMER_KEY", "")
    if api_key:
        try:
            url = (f"https://app.ticketmaster.com/discovery/v2/events.json"
                   f"?city=Toronto&stateCode=ON&countryCode=CA&size=5"
                   f"&sort=date,asc&apikey={api_key}")
            resp = requests.get(url, timeout=15)
            data = resp.json()
            for evt in data.get("_embedded", {}).get("events", []):
                title = evt.get("name", "")
                dates = evt.get("dates", {}).get("start", {})
                date_str = dates.get("localDate", "")
                price_ranges = evt.get("priceRanges", [{}])
                min_price = price_ranges[0].get("min", "") if price_ranges else ""
                if title and date_str:
                    try:
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                        date_str = dt.strftime("%b %d").replace(" 0", " ")
                    except Exception:
                        pass
                    events.append({
                        "title": title[:60],
                        "date": date_str,
                        "price": f"${min_price:.0f}+" if min_price else "See Site"
                    })
        except Exception as e:
            print(f"  [WARN] Ticketmaster API failed: {e}")

    if not events:
        html = fetch_page("https://www.ticketmaster.ca/search?q=toronto&tab=events")
        if html:
            soup = BeautifulSoup(html, "lxml")
            for card in soup.select(".event-listing__item, .search-results__item, .event-tile"):
                title_el = card.select_one("h3, .event-listing__title, .event-name")
                date_el = card.select_one(".event-listing__date, time, .event-date")
                if title_el:
                    events.append({
                        "title": title_el.get_text(strip=True)[:60],
                        "date": date_el.get_text(strip=True)[:20] if date_el else "See Site",
                        "price": "See Site"
                    })

    return events[:3]


def scrape_blogto():
    """Scrape BlogTO events page."""
    events = []
    html = fetch_page("https://www.blogto.com/events/")
    if not html:
        return events
    soup = BeautifulSoup(html, "lxml")

    for card in soup.select("article, .event-listing, .listing-item, .blogto-event"):
        title_el = card.select_one("h2, h3, .listing-title a, .event-title")
        date_el = card.select_one(".event-date, .listing-date, time, .date")
        if title_el:
            title = title_el.get_text(strip=True)
            date = date_el.get_text(strip=True) if date_el else ""
            events.append({"title": title[:60], "date": parse_date_text(date) or "See Site", "price": "Check Site"})

    return events[:3]


def scrape_generic_jsonld(url, max_events=3):
    """Generic scraper that looks for schema.org Event data in JSON-LD."""
    events = []
    html = fetch_page(url)
    if not html:
        return events
    soup = BeautifulSoup(html, "lxml")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "Event":
                    title = item.get("name", "")
                    start = item.get("startDate", "")
                    offers = item.get("offers", {})
                    price = ""
                    if isinstance(offers, dict):
                        price = offers.get("lowPrice", offers.get("price", ""))
                    elif isinstance(offers, list) and offers:
                        price = offers[0].get("price", "")
                    if title:
                        try:
                            dt = datetime.fromisoformat(start.replace("Z", "+00:00").split("+")[0])
                            date_str = dt.strftime("%b %d").replace(" 0", " ")
                        except Exception:
                            date_str = start[:10] if start else "See Site"
                        events.append({
                            "title": title[:60],
                            "date": date_str,
                            "price": fmt_price(str(price)) if price else "See Site"
                        })
                # ItemList with events
                if item.get("@type") == "ItemList":
                    for sub in item.get("itemListElement", []):
                        evt = sub.get("item", sub) if isinstance(sub, dict) else {}
                        if evt.get("@type") == "Event":
                            events.append({
                                "title": evt.get("name", "")[:60],
                                "date": evt.get("startDate", "")[:10],
                                "price": "See Site"
                            })
        except Exception:
            continue

    return events[:max_events]


def scrape_massey_hall():
    """Scrape Massey Hall events."""
    events = scrape_generic_jsonld("https://www.masseyhall.com/")
    if not events:
        html = fetch_page("https://www.masseyhall.com/")
        if html:
            soup = BeautifulSoup(html, "lxml")
            for card in soup.select(".event-card, .show-card, article"):
                title_el = card.select_one("h2, h3, .event-title, .show-title")
                date_el = card.select_one(".event-date, time, .show-date")
                price_el = card.select_one(".event-price, .price")
                if title_el:
                    events.append({
                        "title": title_el.get_text(strip=True)[:60],
                        "date": date_el.get_text(strip=True)[:20] if date_el else "See Site",
                        "price": fmt_price(price_el.get_text(strip=True)) if price_el else "See Site"
                    })
    return events[:3]


def scrape_tiff():
    """Scrape TIFF events."""
    events = scrape_generic_jsonld("https://www.tiff.net/calendar")
    if not events:
        html = fetch_page("https://www.tiff.net/calendar")
        if html:
            soup = BeautifulSoup(html, "lxml")
            for card in soup.select(".module-card, .event-card, article"):
                title_el = card.select_one("h2, h3, .card-title")
                date_el = card.select_one(".card-date, time")
                if title_el:
                    events.append({
                        "title": title_el.get_text(strip=True)[:60],
                        "date": date_el.get_text(strip=True)[:20] if date_el else "See Site",
                        "price": "See Site"
                    })
    return events[:3]


def scrape_comedy_bar():
    """Scrape Comedy Bar events."""
    events = scrape_generic_jsonld("https://comedybar.ca/")
    if not events:
        html = fetch_page("https://comedybar.ca/")
        if html:
            soup = BeautifulSoup(html, "lxml")
            for card in soup.select(".show-card, .event-listing, article"):
                title_el = card.select_one("h2, h3, .show-name, .event-name")
                date_el = card.select_one(".show-date, time, .event-date")
                price_el = card.select_one(".price, .show-price")
                if title_el:
                    events.append({
                        "title": title_el.get_text(strip=True)[:60],
                        "date": date_el.get_text(strip=True)[:20] if date_el else "See Site",
                        "price": fmt_price(price_el.get_text(strip=True)) if price_el else "See Site"
                    })
    return events[:3]


# Map source names to their scraper functions
SOURCE_SCRAPERS = {
    "Eventbrite.ca": scrape_eventbrite,
    "Meetup.com": scrape_meetup,
    "Ticketmaster": scrape_ticketmaster,
    "BlogTO Events": scrape_blogto,
    "BlogTO Food": scrape_blogto,
    "Massey Hall": scrape_massey_hall,
    "TIFF": scrape_tiff,
    "Comedy Bar": scrape_comedy_bar,
}

# Sources that get generic JSON-LD scraping via their URL
GENERIC_JSONLD_SOURCES = {
    "Roy Thomson Hall": "https://www.roythomsonhall.com/",
    "Scotiabank Arena": "https://www.scotiabankarena.com/events",
    "Danforth Music Hall": "https://www.thedanforth.com/",
    "Mirvish Productions": "https://www.mirvish.com/",
    "Second City Toronto": "https://www.secondcity.com/shows/toronto/",
    "Art Gallery of Ontario": "https://ago.ca/",
    "Royal Ontario Museum": "https://www.rom.on.ca/",
    "Destination Toronto Events": "https://www.destinationtoronto.com/events",
}


def fetch_own_events():
    """Fetch our own events.json for cross-referencing venue/source data."""
    try:
        resp = requests.get("https://findtorontoevents.ca/events.json", headers=HEADERS, timeout=15)
        events = resp.json()
        if isinstance(events, dict):
            events = events.get("events", [])
        print(f"  Loaded {len(events)} events from our own events.json")
        return events
    except Exception as e:
        print(f"  [WARN] Could not fetch own events.json: {e}")
        # Try local file
        local = PROJECT_ROOT / "next" / "events.json"
        if local.exists():
            try:
                with open(local, "r", encoding="utf-8") as f:
                    events = json.load(f)
                if isinstance(events, dict):
                    events = events.get("events", [])
                print(f"  Loaded {len(events)} events from local next/events.json")
                return events
            except Exception:
                pass
        return []


def match_events_to_source(own_events, source_name, source_url, max_events=3):
    """Match our scraped events to a specific resource source by venue/location/URL keywords."""
    # Build keyword sets for matching
    name_lower = source_name.lower()
    url_lower = source_url.lower()
    keywords = set()

    # Source name keywords
    for word in name_lower.split():
        if len(word) > 2:
            keywords.add(word)

    # Known venue/source mappings
    VENUE_MAP = {
        "massey hall": ["massey hall"],
        "roy thomson hall": ["roy thomson", "rth"],
        "scotiabank arena": ["scotiabank arena", "scotia arena"],
        "danforth music hall": ["danforth music", "the danforth"],
        "comedy bar": ["comedy bar"],
        "second city": ["second city"],
        "yuk yuk": ["yuk yuk", "yukyuks"],
        "mirvish": ["mirvish", "royal alexandra", "princess of wales", "ed mirvish"],
        "tiff": ["tiff", "toronto international film"],
        "art gallery of ontario": ["ago", "art gallery of ontario"],
        "royal ontario museum": ["rom", "royal ontario museum"],
        "blue jays": ["blue jays", "rogers centre", "jays"],
        "raptors": ["raptors", "scotiabank arena"],
        "maple leafs": ["maple leafs", "leafs game", "leafs at", "leafs vs"],
        "toronto fc": ["toronto fc", "tfc", "bmo field"],
        "argonauts": ["argonauts", "argos game", "argos at", "argos vs"],
        "marlies": ["marlies", "coca-cola coliseum"],
        "cne": ["cne", "canadian national exhibition", "exhibition place", "the ex"],
        "toronto pride": ["pride", "pride parade"],
        "eventbrite": ["eventbrite"],
        "budweiser stage": ["budweiser stage"],
        "the phoenix": ["phoenix concert"],
        "the drake": ["drake hotel"],
        "history toronto": ["history toronto"],
        "rogers centre": ["rogers centre"],
    }

    match_kw = []
    for key, vals in VENUE_MAP.items():
        if key in name_lower:
            match_kw.extend(vals)
            break

    matched = []
    for evt in own_events:
        title = (evt.get("title") or "").lower()
        location = (evt.get("location") or "").lower()
        source = (evt.get("source") or "").lower()
        link = (evt.get("link") or evt.get("url") or "").lower()
        combined = f"{title} {location} {source} {link}"

        # Check venue-specific keywords
        found = False
        for kw in match_kw:
            if kw in combined:
                found = True
                break

        # Check if event URL contains the source domain
        if not found and url_lower:
            domain = url_lower.split("//")[-1].split("/")[0].replace("www.", "")
            if domain in link:
                found = True

        if found:
            date_str = evt.get("date", "")
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00").split("+")[0])
                date_str = dt.strftime("%b %d").replace(" 0", " ")
            except Exception:
                date_str = date_str[:10] if date_str else "See Site"

            price = evt.get("price", "")
            matched.append({
                "title": (evt.get("title") or "Event")[:60],
                "date": date_str or "See Site",
                "price": fmt_price(price) if price else "See Site"
            })

    return matched[:max_events]


def refresh_resources(dry_run=False):
    """Main refresh logic: load resources.json, scrape each source, update events."""
    print(f"{'='*60}")
    print(f"Toronto Event Resources Refresh")
    print(f"Date: {TODAY.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"{'='*60}\n")

    if not RESOURCES_JSON.exists():
        print(f"ERROR: {RESOURCES_JSON} not found")
        sys.exit(1)

    with open(RESOURCES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Fetch our own events for fallback matching
    print("Step 1: Fetching own events.json for cross-reference...")
    own_events = fetch_own_events()

    total_scraped = 0
    total_fallback = 0
    total_kept = 0
    total_skipped = 0

    print("\nStep 2: Scraping resource sources...")

    for cat in data.get("categories", []):
        print(f"\n--- {cat['emoji']} {cat['name']} ---")
        for source in cat.get("sources", []):
            name = source["name"]
            url = source.get("url", "")

            # Check if we have a dedicated scraper
            scraper_fn = SOURCE_SCRAPERS.get(name)
            if not scraper_fn and name in GENERIC_JSONLD_SOURCES:
                target_url = GENERIC_JSONLD_SOURCES[name]
                scraper_fn = lambda u=target_url: scrape_generic_jsonld(u)

            new_events = []

            # Try dedicated/generic scraper first
            if scraper_fn:
                print(f"  Scraping {name}...", end=" ", flush=True)
                time.sleep(0.3)
                try:
                    new_events = scraper_fn()
                    if new_events:
                        source["events"] = new_events
                        total_scraped += 1
                        titles = [e["title"][:40] for e in new_events]
                        print(f"OK ({len(new_events)} events: {', '.join(titles)})")
                        continue
                except Exception as e:
                    print(f"scrape failed ({e})", end=" ")

            # Fallback: match from our own events.json
            if own_events:
                fallback_events = match_events_to_source(own_events, name, url)
                if fallback_events:
                    source["events"] = fallback_events
                    total_fallback += 1
                    if scraper_fn:
                        print(f"-> fallback OK ({len(fallback_events)} from events.json)")
                    else:
                        titles = [e["title"][:35] for e in fallback_events]
                        print(f"  {name}: fallback OK ({len(fallback_events)} events: {', '.join(titles)})")
                    continue

            # Neither worked — keep existing events
            if scraper_fn:
                print("keeping existing")
            total_kept += 1 if scraper_fn else 0
            total_skipped += 0 if scraper_fn else 1

    # Update metadata
    data["last_updated"] = TODAY.strftime("%Y-%m-%d")

    print(f"\n{'='*60}")
    print(f"Results: {total_scraped} scraped, {total_fallback} from events.json fallback, "
          f"{total_kept} kept existing, {total_skipped} skipped (no scraper)")
    print(f"Total refreshed: {total_scraped + total_fallback}")
    print(f"{'='*60}")

    if dry_run:
        print("\n[DRY RUN] Would write to:", RESOURCES_JSON)
        print(json.dumps(data["categories"][0]["sources"][0], indent=2))
        return data

    # Write updated file
    with open(RESOURCES_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nWrote updated resources to {RESOURCES_JSON}")

    # Also update the HTML page's "Last updated" date
    resources_html = PROJECT_ROOT / "resources" / "resources.html"
    if resources_html.exists():
        html_content = resources_html.read_text(encoding="utf-8")
        updated_html = re.sub(
            r'Last updated: \w+ \d{1,2}, \d{4}',
            f'Last updated: {TODAY.strftime("%B %d, %Y").replace(" 0", " ")}',
            html_content
        )
        if updated_html != html_content:
            resources_html.write_text(updated_html, encoding="utf-8")
            print(f"Updated last_updated date in {resources_html}")

    return data


def deploy_to_ftp():
    """Deploy updated resources files to live site via FTP."""
    ftp_host = os.environ.get("FTP_SERVER", os.environ.get("FTP_HOST", ""))
    ftp_user = os.environ.get("FTP_USER", "")
    ftp_pass = os.environ.get("FTP_PASS", "")

    if not all([ftp_host, ftp_user, ftp_pass]):
        print("[SKIP] FTP credentials not set, skipping deploy")
        return False

    try:
        from ftplib import FTP
        ftp = FTP(ftp_host)
        ftp.login(ftp_user, ftp_pass)

        remote_base = "/findtorontoevents.ca"

        # Upload resources.json
        remote_path = f"{remote_base}/resources/resources.json"
        try:
            ftp.cwd(f"{remote_base}/resources")
        except Exception:
            ftp.mkd(f"{remote_base}/resources")
            ftp.cwd(f"{remote_base}/resources")

        with open(RESOURCES_JSON, "rb") as f:
            ftp.storbinary(f"STOR resources.json", f)
        print(f"Uploaded resources.json to {remote_path}")

        # Upload resources.html if updated
        resources_html = PROJECT_ROOT / "resources" / "resources.html"
        if resources_html.exists():
            with open(resources_html, "rb") as f:
                ftp.storbinary(f"STOR resources.html", f)
            print(f"Uploaded resources.html")

        ftp.quit()
        print("FTP deploy complete")
        return True
    except Exception as e:
        print(f"FTP deploy failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Refresh Toronto Event Resources")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--deploy", action="store_true", help="Also deploy via FTP")
    args = parser.parse_args()

    data = refresh_resources(dry_run=args.dry_run)

    if args.deploy and not args.dry_run:
        deploy_to_ftp()
