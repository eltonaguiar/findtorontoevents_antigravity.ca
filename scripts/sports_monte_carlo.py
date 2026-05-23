#!/usr/bin/env python3
"""
Bootstrap Monte Carlo on daily PnL by sport (optional paper risk UI input).
Fetches sports_forensics.php?action=daily_returns and simulates correlated-ish
simple draws per sport (independent bootstrap — upgrade with real copula later).
"""
from __future__ import print_function

import json
import random
import sys

try:
    from urllib.request import Request, urlopen
except ImportError:
    Request = None
    urlopen = None


def main():
    base = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://findtorontoevents.ca/live-monitor/api/"
    ).rstrip("/") + "/"
    n_sims = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    if urlopen is None or Request is None:
        print("urllib required")
        return 1
    url = base + "sports_forensics.php?action=daily_returns"
    try:
        req = Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; sports-monte-carlo/1.0)"},
        )
        raw = urlopen(req, timeout=60).read().decode("utf-8", errors="replace")
        d = json.loads(raw)
    except Exception as e:
        print("fetch failed", e)
        return 1
    if not d.get("ok"):
        print("API not ok")
        return 1
    rows = d.get("daily_rows") or []
    by_sport = {}
    for r in rows:
        sp = r.get("sport_short") or r.get("sport") or "?"
        by_sport.setdefault(sp, []).append(float(r.get("pnl") or 0))
    if not by_sport:
        print("No daily_rows; nothing to simulate.")
        return 0
    outcomes = []
    random.seed(42)
    for _ in range(n_sims):
        total = 0.0
        for _, pnl_list in by_sport.items():
            if pnl_list:
                total += random.choice(pnl_list)
        outcomes.append(total)
    outcomes.sort()
    q5 = outcomes[int(0.05 * (len(outcomes) - 1))]
    q50 = outcomes[int(0.50 * (len(outcomes) - 1))]
    q95 = outcomes[int(0.95 * (len(outcomes) - 1))]
    print(
        "Monte Carlo (independent bootstrap by sport), n=%d sims, %d sports with history"
        % (n_sims, len(by_sport))
    )
    print(" 5th pct daily PnL ~ %.2f | median ~ %.2f | 95th ~ %.2f" % (q5, q50, q95))
    return 0


if __name__ == "__main__":
    sys.exit(main())
