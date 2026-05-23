#!/usr/bin/env python3
"""
Top Movies Scraper — Fetches live movie rankings from TMDB + The Numbers
Outputs: TORONTOEVENTS_ANTIGRAVITY/shared/top-movies.json

Sources:
  - TMDB: Now Playing, Trending, Top Rated, Popular (free API, no auth needed)
  - The Numbers: Weekend Box Office chart (web scraping)

Usage:
  python tools/scrapers/top_movies_scraper.py
  python tools/scrapers/top_movies_scraper.py --dry-run
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote
from html.parser import HTMLParser

# TMDB API key (same one used in MOVIESHOWS3)
TMDB_API_KEY = "b84ff7bfe35ffad8779b77bcbbda317f"
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p"

OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "TORONTOEVENTS_ANTIGRAVITY" / "shared" / "top-movies.json"

GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 10770: "TV Movie",
    53: "Thriller", 10752: "War", 37: "Western"
}


def fetch_json(url, retries=2):
    """Fetch JSON from URL with retries."""
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": "TopMoviesScraper/1.0"})
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except (URLError, HTTPError) as e:
            if attempt < retries:
                time.sleep(1)
                continue
            print(f"  [WARN] Failed to fetch {url}: {e}")
            return None


def fetch_html(url, retries=2):
    """Fetch HTML from URL with retries."""
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (URLError, HTTPError) as e:
            if attempt < retries:
                time.sleep(1)
                continue
            print(f"  [WARN] Failed to fetch {url}: {e}")
            return None


def get_trailer_id(tmdb_id):
    """Get YouTube trailer ID for a movie from TMDB videos endpoint."""
    data = fetch_json(f"{TMDB_BASE}/movie/{tmdb_id}/videos?api_key={TMDB_API_KEY}")
    if not data or not data.get("results"):
        return None

    # Priority: Official Trailer > Trailer > Teaser > any YouTube video
    videos = data["results"]
    for priority_type in ["Trailer", "Teaser", "Clip", "Featurette"]:
        for v in videos:
            if v.get("site") == "YouTube" and v.get("type") == priority_type:
                if priority_type == "Trailer" and "official" in v.get("name", "").lower():
                    return v["key"]
        for v in videos:
            if v.get("site") == "YouTube" and v.get("type") == priority_type:
                return v["key"]

    # Fallback: any YouTube video
    for v in videos:
        if v.get("site") == "YouTube":
            return v["key"]
    return None


def parse_movie(m, source, rank=None):
    """Parse a TMDB movie object into our format."""
    genres = [GENRE_MAP.get(gid, str(gid)) for gid in (m.get("genre_ids") or [])]
    year = (m.get("release_date") or "")[:4]
    return {
        "title": m.get("title", "Unknown"),
        "tmdb_id": m.get("id"),
        "year": year,
        "rating": round(m.get("vote_average", 0), 1),
        "poster": f"{TMDB_IMG}/w300{m['poster_path']}" if m.get("poster_path") else None,
        "backdrop": f"{TMDB_IMG}/w780{m['backdrop_path']}" if m.get("backdrop_path") else None,
        "overview": (m.get("overview") or "")[:200],
        "genres": genres,
        "source": source,
        "rank": rank,
        "trailer_id": None  # Filled in later
    }


def fetch_tmdb_list(endpoint, source, limit=20):
    """Fetch a list of movies from TMDB endpoint."""
    movies = []
    for page in [1, 2]:
        data = fetch_json(f"{TMDB_BASE}{endpoint}?api_key={TMDB_API_KEY}&language=en-US&page={page}&region=US")
        if not data or not data.get("results"):
            break
        for i, m in enumerate(data["results"]):
            if len(movies) >= limit:
                break
            rank = len(movies) + 1
            movies.append(parse_movie(m, source, rank))
    return movies[:limit]


class BoxOfficeParser(HTMLParser):
    """Parse The Numbers weekend box office chart HTML.

    The Numbers table has 11 columns (0-indexed):
      0: Rank (e.g. "1")
      1: Previous rank ("N" for new, "(1)" for returning)
      2: Title (inside <b><a>...</a></b>)
      3: Distributor
      4: Weekend gross (e.g. "$32,801,647")
      5: %LW change
      6: Theaters
      7: Theater change
      8: Per theater
      9: Total gross
     10: Weekends in release
    """

    def __init__(self):
        super().__init__()
        self.movies = []
        self._in_target_table = False
        self._in_row = False
        self._in_cell = False
        self._cells = []
        self._current_cell = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "table":
            # Target the specific box office table by id
            table_id = attrs_dict.get("id", "")
            if "box_office" in table_id or "weekend" in table_id:
                self._in_target_table = True
            # Fallback: also accept tables with DataTable classes
            elif "dataTable" in attrs_dict.get("class", ""):
                self._in_target_table = True
        if self._in_target_table and tag == "tr":
            self._in_row = True
            self._cells = []
        if self._in_row and tag == "td":
            self._in_cell = True
            self._current_cell = ""

    def handle_endtag(self, tag):
        if tag == "table":
            self._in_target_table = False
        if tag == "tr" and self._in_row:
            self._in_row = False
            if len(self._cells) >= 5:
                self._parse_row(self._cells)
        if tag == "td" and self._in_cell:
            self._in_cell = False
            self._cells.append(self._current_cell.strip())

    def handle_data(self, data):
        if self._in_cell:
            self._current_cell += data

    def _parse_row(self, cells):
        """Parse a table row using fixed column positions."""
        try:
            # Column 0: Rank
            rank_str = cells[0].strip()
            if not re.match(r'^\d+$', rank_str):
                return
            rank = int(rank_str)
            if rank > 20:
                return

            # Column 2: Title (text content from <b><a>title</a></b>)
            title = cells[2].strip().strip('"').strip()
            if not title or len(title) < 2:
                return

            # Column 4: Weekend gross
            weekend_gross = None
            if len(cells) > 4 and '$' in cells[4]:
                weekend_gross = cells[4].replace(',', '').strip()

            # Column 9: Total gross
            total_gross = None
            if len(cells) > 9 and '$' in cells[9]:
                total_gross = cells[9].replace(',', '').strip()

            self.movies.append({
                "rank": rank,
                "title": title,
                "weekend_gross": weekend_gross,
                "total_gross": total_gross
            })
        except (ValueError, IndexError):
            pass


def scrape_the_numbers():
    """Scrape weekend box office data from The Numbers."""
    print("  Fetching The Numbers weekend box office...")
    html = fetch_html("https://www.the-numbers.com/weekend-box-office-chart")
    if not html:
        print("  [WARN] Could not fetch The Numbers")
        return []

    parser = BoxOfficeParser()
    parser.feed(html)

    if not parser.movies:
        print("  [WARN] No box office data parsed from The Numbers")
        return []

    print(f"  Found {len(parser.movies)} box office entries")

    # Deduplicate by title (safety net)
    seen_titles = set()
    unique_movies = []
    for entry in parser.movies:
        t = entry["title"].lower().strip()
        if t not in seen_titles:
            seen_titles.add(t)
            unique_movies.append(entry)

    if len(unique_movies) < len(parser.movies):
        print(f"  Removed {len(parser.movies) - len(unique_movies)} duplicate entries")

    # Look up TMDB IDs and trailers for each title
    results = []
    for entry in unique_movies[:15]:
        title = entry["title"]
        # Search TMDB for this title (properly URL-encoded)
        search_data = fetch_json(
            f"{TMDB_BASE}/search/movie?api_key={TMDB_API_KEY}&query={quote(title)}&language=en-US&page=1&year=2026"
        )
        tmdb_movie = None
        # If year-filtered search returned nothing, retry without year
        if not search_data or not search_data.get("results"):
            search_data = fetch_json(
                f"{TMDB_BASE}/search/movie?api_key={TMDB_API_KEY}&query={quote(title)}&language=en-US&page=1"
            )
        if search_data and search_data.get("results"):
            # Find best match: exact title match with recent year preferred
            for m in search_data["results"]:
                yr = (m.get("release_date") or "")[:4]
                if m.get("title", "").lower() == title.lower() and yr in ("2025", "2026"):
                    tmdb_movie = m
                    break
            if not tmdb_movie:
                for m in search_data["results"]:
                    if m.get("title", "").lower() == title.lower():
                        tmdb_movie = m
                        break
            if not tmdb_movie:
                tmdb_movie = search_data["results"][0]

        movie = {
            "title": title,
            "rank": entry["rank"],
            "weekend_gross": entry.get("weekend_gross"),
            "total_gross": entry.get("total_gross"),
            "tmdb_id": tmdb_movie.get("id") if tmdb_movie else None,
            "year": (tmdb_movie.get("release_date") or "")[:4] if tmdb_movie else None,
            "rating": round(tmdb_movie.get("vote_average", 0), 1) if tmdb_movie else None,
            "poster": f"{TMDB_IMG}/w300{tmdb_movie['poster_path']}" if tmdb_movie and tmdb_movie.get("poster_path") else None,
            "overview": (tmdb_movie.get("overview") or "")[:200] if tmdb_movie else None,
            "genres": [GENRE_MAP.get(gid) for gid in (tmdb_movie.get("genre_ids") or []) if gid in GENRE_MAP] if tmdb_movie else [],
            "source": "Box Office",
            "trailer_id": None
        }
        results.append(movie)
        time.sleep(0.15)  # Rate limit

    return results


def resolve_trailers(movies, label=""):
    """Resolve YouTube trailer IDs for a list of movies."""
    resolved = 0
    for m in movies:
        if m.get("tmdb_id") and not m.get("trailer_id"):
            trailer_id = get_trailer_id(m["tmdb_id"])
            if trailer_id:
                m["trailer_id"] = trailer_id
                resolved += 1
            time.sleep(0.15)  # Rate limit
    print(f"  {label}: resolved {resolved}/{len(movies)} trailers")


def main():
    dry_run = "--dry-run" in sys.argv
    print(f"=== Top Movies Scraper {'(DRY RUN)' if dry_run else ''} ===")
    print(f"Output: {OUTPUT_PATH}")
    print()

    # 1. TMDB Now Playing
    print("[1/5] Fetching TMDB Now Playing...")
    now_playing = fetch_tmdb_list("/movie/now_playing", "In Theaters", limit=15)
    print(f"  Got {len(now_playing)} now playing movies")

    # 2. TMDB Trending This Week
    print("[2/5] Fetching TMDB Trending...")
    trending = fetch_tmdb_list("/trending/movie/week", "Trending", limit=15)
    print(f"  Got {len(trending)} trending movies")

    # 3. TMDB Top Rated
    print("[3/5] Fetching TMDB Top Rated...")
    top_rated = fetch_tmdb_list("/movie/top_rated", "Top Rated", limit=15)
    print(f"  Got {len(top_rated)} top rated movies")

    # 4. TMDB Popular
    print("[4/5] Fetching TMDB Popular...")
    popular = fetch_tmdb_list("/movie/popular", "Popular", limit=15)
    print(f"  Got {len(popular)} popular movies")

    # 5. The Numbers Weekend Box Office
    print("[5/5] Scraping The Numbers Weekend Box Office...")
    box_office = scrape_the_numbers()

    # Resolve trailers for all lists
    print("\nResolving YouTube trailers...")
    resolve_trailers(now_playing, "Now Playing")
    resolve_trailers(trending, "Trending")
    resolve_trailers(top_rated, "Top Rated")
    resolve_trailers(popular, "Popular")
    resolve_trailers(box_office, "Box Office")

    # Build output
    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "tmdb": "The Movie Database (TMDB) API v3",
            "box_office": "The Numbers (the-numbers.com)"
        },
        "now_playing": now_playing,
        "trending": trending,
        "top_rated": top_rated,
        "popular": popular,
        "box_office": box_office
    }

    # Stats
    all_movies = now_playing + trending + top_rated + popular + box_office
    with_trailers = sum(1 for m in all_movies if m.get("trailer_id"))
    print(f"\n=== Summary ===")
    print(f"  Now Playing:  {len(now_playing)} movies")
    print(f"  Trending:     {len(trending)} movies")
    print(f"  Top Rated:    {len(top_rated)} movies")
    print(f"  Popular:      {len(popular)} movies")
    print(f"  Box Office:   {len(box_office)} movies")
    print(f"  Total:        {len(all_movies)} movies, {with_trailers} with trailers")

    if dry_run:
        print("\n[DRY RUN] Would write to:", OUTPUT_PATH)
        print(json.dumps(output, indent=2)[:2000] + "...")
    else:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\nWrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
