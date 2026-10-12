#!/usr/bin/env python3
"""Refresh the two movie databases through their authenticated production APIs."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


HOSTS = ("https://findtorontoevents.ca", "https://torontoevent.net")


class RefreshError(Exception):
    pass


def request_json(url, timeout):
    request = urllib.request.Request(url, headers={
        "User-Agent": "MovieShowsRefresh/1.0",
        "Cache-Control": "no-cache",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RefreshError(f"HTTP {error.code}") from None
    except urllib.error.URLError:
        raise RefreshError("Production endpoint transport failure") from None
    except (TimeoutError, OSError):
        raise RefreshError("Production endpoint connection failed or timed out") from None
    except (ValueError, UnicodeError):
        raise RefreshError("Production endpoint did not return valid JSON") from None


def successful_object(value, label):
    if not isinstance(value, dict) or value.get("success") is not True:
        raise RefreshError(f"{label} reported failure")
    return value


def count(value, key):
    number = value.get(key)
    if type(number) is not int or number < 0:
        raise RefreshError(f"Invalid or missing count: {key}")
    return number


def refresh_host(base, key, kind, pages, mode):
    endpoint = base + "/MOVIESHOWS3/"
    before = successful_object(request_json(endpoint + "log/api_status.php", 45), "Pre-refresh database")
    initial_count = count(before, "total_records")
    query = urllib.parse.urlencode({"key": key, "type": kind, "pages": pages, "mode": mode})
    result = successful_object(
        request_json(endpoint + "fetch_new_content.php?" + query, 360),
        "TMDB refresh",
    )
    summary = result.get("summary")
    if not isinstance(summary, dict):
        raise RefreshError("Refresh summary is missing")
    if count(summary, "errors") != 0:
        raise RefreshError("Refresh reported errors")
    fetched = count(summary, "fetched_from_tmdb")
    added = count(summary, "movies_added") + count(summary, "tv_added")
    skipped = count(summary, "skipped")
    if fetched == 0 or fetched != added + skipped:
        raise RefreshError("Refresh returned empty or inconsistent TMDB results")
    after = successful_object(request_json(endpoint + "log/api_status.php", 45), "Post-refresh database")
    final_count = count(after, "total_records")
    if final_count - initial_count != added:
        raise RefreshError("Post-refresh row count does not match added titles")
    logs = request_json(endpoint + "log/pull_log.json", 45)
    entry = result.get("log_entry")
    if (not isinstance(entry, dict) or entry.get("status") != "success" or
            not isinstance(entry.get("timestamp"), str) or not entry["timestamp"] or
            not isinstance(logs, list) or entry not in logs):
        raise RefreshError("Refresh persisted log is missing or does not match this run")
    return {"total_records": final_count, "added": added, "skipped": skipped, "fetched": fetched}

def refresh_ratings(base, key):
    query = urllib.parse.urlencode({"key": key, "mode": "ratings"})
    result = successful_object(request_json(
        base + "/MOVIESHOWS3/fetch_new_content.php?" + query, 600,
    ), "Existing-title rating refresh")
    if count(result, "errors") != 0:
        raise RefreshError("Rating refresh reported errors")
    ratings = result.get("ratings")
    if not isinstance(ratings, list) or count(result, "refreshed") != len(ratings):
        raise RefreshError("Rating refresh counts are inconsistent")
    if not ratings:
        return 0
    feed = successful_object(request_json(
        base + "/MOVIESHOWS3/api/get-movies.php", 45,
    ), "Rating verification feed")
    movies = feed.get("movies")
    if not isinstance(movies, list):
        raise RefreshError("Rating verification feed is invalid")
    by_id = {int(movie["id"]): movie for movie in movies}
    verified = 0
    for rating in ratings:
        movie = by_id.get(rating["id"])
        if movie is None:
            continue  # Titles without playable trailers are intentionally absent from the feed.
        if (float(movie.get("imdb_rating") or 0) != float(rating["rating"])
                or movie.get("rating_vote_count") != rating["vote_count"]
                or movie.get("rating_provisional") != rating["provisional"]
                or movie.get("rating_checked_at") != rating["checked_at"]):
            raise RefreshError("Persisted rating metadata does not match refresh results")
        verified += 1
    if verified == 0:
        raise RefreshError("No refreshed ratings could be verified in the production feed")
    return verified


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", choices=("both", "movie", "tv"), default="both")
    parser.add_argument("--pages", type=int, choices=range(1, 11), default=3)
    parser.add_argument("--ratings-only", action="store_true", help="Refresh the tracked rating cohort without importing titles")
    parser.add_argument("--mode", choices=(
        "trending", "upcoming", "popular", "top_rated", "now_playing", "on_the_air",
    ), default="trending")
    args = parser.parse_args(argv)
    key = os.environ.get("MS2_SYNC_KEY")
    if not key:
        print("ERROR: MS2_SYNC_KEY is required; no refresh was attempted", file=sys.stderr)
        return 1
    failed = False
    for base in HOSTS:
        print(f"Refreshing {base}: type={args.type}, pages={args.pages}, mode={args.mode}", flush=True)
        try:
            result = {} if args.ratings_only else refresh_host(base, key, args.type, args.pages, args.mode)
            result["ratings_verified"] = refresh_ratings(base, key)
        except RefreshError as error:
            print(f"ERROR: {base}: {error}", file=sys.stderr, flush=True)
            failed = True
        else:
            print(f"VERIFIED {base}: {json.dumps(result, sort_keys=True)}", flush=True)
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
