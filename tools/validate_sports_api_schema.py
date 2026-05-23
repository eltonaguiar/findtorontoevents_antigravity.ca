#!/usr/bin/env python3
"""
CI guard: fetch live-monitor sports JSON and assert required keys exist.
Usage: python tools/validate_sports_api_schema.py [API_BASE]
  API_BASE default: https://findtorontoevents.ca/live-monitor/api/
Exit 0 on success, 1 on failure.
"""
from __future__ import print_function

import json
import sys

try:
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError
except ImportError:
    Request = None
    urlopen = None


def main():
    base = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://findtorontoevents.ca/live-monitor/api/"
    ).rstrip("/") + "/"

    def fetch(path):
        url = base + path
        try:
            req = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; sports-schema-ci/1.0)",
                    "Accept": "application/json,text/plain,*/*",
                },
            )
            r = urlopen(req, timeout=90)
            body = r.read().decode("utf-8", errors="replace")
            return json.loads(body)
        except HTTPError as e:
            print("HTTPError", url, e.code)
            return None
        except URLError as e:
            print("URLError", url, e.reason)
            return None
        except ValueError as e:
            print("JSON parse error", url, e)
            return None

    if urlopen is None or Request is None:
        print("urllib not available")
        return 1

    d = fetch("sports_bets.php?action=dashboard")
    if not d or not d.get("ok"):
        print("dashboard: missing or not ok")
        return 1
    for k in (
        "clv_quadrants",
        "by_market",
        "pending_exposure_by_sport",
        "risk_budget",
        "by_sport",
    ):
        if k not in d:
            print("dashboard missing key:", k)
            return 1
    cq = d.get("clv_quadrants") or {}
    for k in ("plus_clv_win", "minus_clv_loss"):
        if k not in cq:
            print("clv_quadrants missing", k)
            return 1

    for k in (
        "pending_stale_14d_count",
        "pending_stale_14d_stake",
        "oldest_stale_pending_commence",
        "stale_pending_hint",
    ):
        if k not in d:
            print("dashboard missing stale-pending key:", k)
            return 1
    try:
        int(d.get("pending_stale_14d_count", -1))
        float(d.get("pending_stale_14d_stake", -1.0))
    except (TypeError, ValueError):
        print("dashboard stale-pending fields not numeric")
        return 1

    wq = d.get("win_rate_quality") or {}
    for k in ("wilson_95_low_pct", "wilson_95_high_pct", "directional_n", "small_sample"):
        if k not in wq:
            print("dashboard missing win_rate_quality key:", k)
            return 1
    cg = d.get("cohort_guardrail_v1") or {}
    for k in (
        "cohort",
        "algorithm",
        "directional_n",
        "wins",
        "losses",
        "pushes",
        "voids",
        "win_rate_pct",
        "wilson_95_low_pct",
        "wilson_95_high_pct",
        "total_pnl",
        "roi_pct",
    ):
        if k not in cg:
            print("dashboard missing cohort_guardrail_v1 key:", k)
            return 1

    spf = d.get("since_policy_fix") or {}
    for k in (
        "cohort",
        "settled_tickets",
        "wins",
        "losses",
        "pushes",
        "voids",
        "directional_n",
        "win_rate_pct",
        "total_pnl",
        "roi_pct",
        "win_rate_quality",
        "caption",
    ):
        if k not in spf:
            print("dashboard missing since_policy_fix key:", k)
            return 1
    wrq = spf.get("win_rate_quality") or {}
    for k in ("wilson_95_low_pct", "wilson_95_high_pct", "directional_n", "small_sample"):
        if k not in wrq:
            print("since_policy_fix.win_rate_quality missing", k)
            return 1

    f = fetch("sports_forensics.php?action=segments&include_ci=1")
    if not f or not f.get("ok"):
        print("forensics segments: missing or not ok")
        return 1
    segs = f.get("segments") or []
    for s in segs:
        wl = int(s.get("wins") or 0) + int(s.get("losses") or 0)
        if wl >= 1:
            if "win_rate_ci_low_pct" not in s or "win_rate_ci_high_pct" not in s:
                print("segment missing Wilson CI (include_ci=1):", s.get("sport"), s.get("market"))
                return 1

    p = fetch("sports_forensics.php?action=pre_game_status")
    if not p or not p.get("ok"):
        print("pre_game_status: missing or not ok")
        return 1
    if "table_exists" not in p:
        print("pre_game_status missing table_exists")
        return 1

    print("validate_sports_api_schema: OK", base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
