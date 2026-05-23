#!/usr/bin/env python3
"""
Validate news video live streams.
Checks YouTube channels for active live streams using oEmbed API.
Reports dead/unavailable streams so they can be fixed.
"""
import json
import sys
import urllib.request
import urllib.error

API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

# Mirror of VIDEO_CHANNELS from news/index.html
CHANNELS = [
    {"id": "cbc",     "name": "CBC News",     "channelId": "UCuFFtHWoLl5fauMMD5Ww2jA", "live": False},
    {"id": "global",  "name": "Global News",  "channelId": "UChLtXXpo4Ge1ReTEboVvTDg", "live": False},
    {"id": "cp24",    "name": "CP24",         "external": True, "url": "https://www.cp24.com/video/live", "live": True},
    {"id": "abc",     "name": "ABC News",     "external": True, "url": "https://abcnews.go.com/live", "live": True},
    {"id": "nbc",     "name": "NBC News",     "channelId": "UCeY0bbntWzzVIaj2z3QigXg", "live": False},
    {"id": "cnn",     "name": "CNN",          "channelId": "UCupvZG-5ko_eiXAupbDfxWw", "live": False},
    {"id": "sky",     "name": "Sky News",     "channelId": "UCoMdktPbSTixAyNGwb-UYkQ", "live": True, "ytHandle": "@SkyNews"},
    {"id": "aje",     "name": "Al Jazeera",   "channelId": "UCNye-wNBqNL5ZzHSJj3l8Bg", "live": True, "ytHandle": "@AlJazeeraEnglish"},
    {"id": "f24",     "name": "France 24",    "channelId": "UCQfwfsi5VrQ8yKZ-UWmAEFg", "live": True, "ytHandle": "@FRANCE24English"},
    {"id": "dw",      "name": "DW News",      "channelId": "UCknLrEdhRCp1aegoMqRaCZg", "live": True, "ytHandle": "@DWNews"},
    {"id": "nhk",     "name": "NHK World",    "channelId": "UCSPEjw8F2nQDtmUKPFNF7_A", "live": True, "ytHandle": "@NHKWORLDJAPAN"},
    {"id": "euro",    "name": "Euronews",     "channelId": "UCSrZ3UV4jOidv8ppoVuvW9Q", "live": True, "ytHandle": "@euronews"},
    {"id": "trt",     "name": "TRT World",    "channelId": "UC7fWeaHhqgM4Ry-RMpM2YYw", "live": True, "ytHandle": "@taborttrtworld"},
    {"id": "wion",    "name": "WION",         "channelId": "UC_gUM8rL-Lrg6O3adPW9K1g", "live": True, "ytHandle": "@WIONews"},
    {"id": "intoday", "name": "India Today",  "channelId": "UCYPvAwZP8pZhSMW8qs7cVCw", "live": True, "ytHandle": "@IndiaToday"},
    {"id": "bloom",   "name": "Bloomberg",    "channelId": "UChirEOpgFCupRAk5etXqPaA", "live": False},
    {"id": "cnbc",    "name": "CNBC",         "channelId": "UCvJJ_dzjViJCoLf5uKUTwoA", "live": False},
]


def check_external_url(url):
    """Check if an external URL is reachable (HTTP 200)."""
    try:
        req = urllib.request.Request(url, headers=API_HEADERS, method="HEAD")
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status == 200
    except Exception:
        # Try GET as fallback (some servers reject HEAD)
        try:
            req = urllib.request.Request(url, headers=API_HEADERS)
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.status == 200
        except Exception as e:
            return False


def check_youtube_live(channel_id):
    """Check if a YouTube channel has an embeddable live stream using oEmbed."""
    embed_url = "https://www.youtube.com/embed/live_stream?channel=" + channel_id
    oembed_url = "https://www.youtube.com/oembed?url=" + urllib.request.quote(embed_url, safe="") + "&format=json"
    try:
        req = urllib.request.Request(oembed_url, headers=API_HEADERS)
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode("utf-8"))
        return True, data.get("title", "")
    except urllib.error.HTTPError as e:
        return False, "HTTP " + str(e.code)
    except Exception as e:
        return False, str(e)


def check_youtube_uploads(channel_id):
    """Check if a YouTube channel's uploads playlist is accessible."""
    playlist_id = "UU" + channel_id[2:]
    embed_url = "https://www.youtube.com/embed/videoseries?list=" + playlist_id
    oembed_url = "https://www.youtube.com/oembed?url=" + urllib.request.quote(embed_url, safe="") + "&format=json"
    try:
        req = urllib.request.Request(oembed_url, headers=API_HEADERS)
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode("utf-8"))
        return True, data.get("title", "")
    except urllib.error.HTTPError as e:
        return False, "HTTP " + str(e.code)
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 60)
    print("  News Video Live Stream Health Check")
    print("=" * 60)

    ok_count = 0
    warn_count = 0
    fail_count = 0
    results = []

    for ch in CHANNELS:
        name = ch["name"]
        is_external = ch.get("external", False)

        if is_external:
            url = ch.get("url", "")
            reachable = check_external_url(url)
            status = "OK" if reachable else "FAIL"
            detail = url
            if reachable:
                ok_count += 1
            else:
                fail_count += 1
            results.append({"id": ch["id"], "name": name, "status": status, "detail": detail})
            icon = "[OK]" if reachable else "[FAIL]"
            print("  {} {} (external: {})".format(icon, name, url))

        elif ch.get("live", False):
            live_ok, live_detail = check_youtube_live(ch["channelId"])
            status = "OK" if live_ok else "WARN"
            detail = live_detail
            if live_ok:
                ok_count += 1
            else:
                warn_count += 1
            results.append({"id": ch["id"], "name": name, "status": status, "detail": detail})
            icon = "[OK]" if live_ok else "[WARN]"
            print("  {} {} live stream: {}".format(icon, name, live_detail))

        else:
            uploads_ok, uploads_detail = check_youtube_uploads(ch["channelId"])
            status = "OK" if uploads_ok else "WARN"
            detail = uploads_detail
            if uploads_ok:
                ok_count += 1
            else:
                warn_count += 1
            results.append({"id": ch["id"], "name": name, "status": status, "detail": detail})
            icon = "[OK]" if uploads_ok else "[WARN]"
            print("  {} {} uploads: {}".format(icon, name, uploads_detail))

    print()
    print("-" * 60)
    print("  Results: {} OK, {} warnings, {} failures".format(ok_count, warn_count, fail_count))
    print("-" * 60)

    if fail_count > 0:
        print()
        print("FAILED channels:")
        for r in results:
            if r["status"] == "FAIL":
                print("  - {} ({}): {}".format(r["name"], r["id"], r["detail"]))
        sys.exit(1)

    if warn_count > 0:
        print()
        print("Channels with warnings (may be temporarily offline):")
        for r in results:
            if r["status"] == "WARN":
                print("  - {} ({}): {}".format(r["name"], r["id"], r["detail"]))

    print()
    print("Health check complete.")


if __name__ == "__main__":
    main()
