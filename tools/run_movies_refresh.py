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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", choices=("both", "movie", "tv"), default="both")
    parser.add_argument("--pages", type=int, choices=range(1, 11), default=3)
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
            result = refresh_host(base, key, args.type, args.pages, args.mode)
        except RefreshError as error:
            print(f"ERROR: {base}: {error}", file=sys.stderr, flush=True)
            failed = True
        else:
            print(f"VERIFIED {base}: {json.dumps(result, sort_keys=True)}", flush=True)
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
