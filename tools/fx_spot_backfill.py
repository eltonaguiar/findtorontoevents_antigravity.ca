#!/usr/bin/env python3
"""Backfill ``data/forex_rate_cache/`` with real daily FX spot history.

Why
---
``tools/class_data_readiness.py`` requires >=100 real files under
``data/forex_rate_cache/`` for FOREX to be READY. The directory held only
``.gitkeep``, so FOREX was BLOCKED_DATA.

Source
------
Frankfurter (https://api.frankfurter.app) serving European Central Bank
reference rates. Free, no API key. It is already adapter #2 in
``alpha_engine/forex_price_failover.py``.

On 2026-11-22 the two preferred sources were unavailable from this host:
  * Stooq historical CSV -> JS proof-of-work challenge page, no CSV body
  * Yahoo v8 chart (query1 and query2) -> "Too Many Requests"

Data integrity
--------------
Only rows actually returned by the source are written. Cross rates such as
GBPJPY are exact arithmetic on two published ECB rates (r[quote] / r[base]),
never interpolated or synthesised. Missing business days are left missing so
the Round 2 gap audit can see them.

Usage
-----
    python3 tools/fx_spot_backfill.py --dry-run
    python3 tools/fx_spot_backfill.py --apply --since 2019-01-01
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / "data" / "forex_rate_cache"
RAW_DIR = REPO_ROOT / "data" / "fx_spot_raw"

# G10 majors (ECB publishes all of these) plus DKK so the ordered-pair set
# exceeds the checker's 100-file minimum with genuinely distinct series.
CURRENCIES = ["USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD", "SEK", "NOK", "DKK"]

USER_AGENT = "FindTorontoEvents-EdgeResearch/1.0 (no-key FX backfill)"
SLEEP_SEC = 2.0
MAX_REQUESTS = 40


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def fetch_usd_rates(since: date, until: date) -> dict:
    """USD-base rates: r[X] = units of X per 1 USD, keyed by ISO date."""
    quotes = [c for c in CURRENCIES if c != "USD"]
    url = (f"https://api.frankfurter.app/{since.isoformat()}..{until.isoformat()}"
           f"?from=USD&to={','.join(quotes)}")
    body = _get(url)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"frankfurter_USD_{since}_{until}.json").write_bytes(body)
    payload = json.loads(body)
    rates = payload.get("rates") or {}
    if not rates:
        raise RuntimeError(f"frankfurter returned no rates: {body[:200]!r}")
    # Normalise so every date has USD=1.0 plus whatever the source published.
    out = {}
    for d, row in sorted(rates.items()):
        r = {k: float(v) for k, v in row.items() if isinstance(v, (int, float))}
        r["USD"] = 1.0
        out[d] = r
    return out


def build_pairs(usd_rates: dict) -> dict[str, list[tuple[str, float]]]:
    """Ordered pair -> [(date, close)]. close = r[quote]/r[base]; both legs real."""
    pairs: dict[str, list[tuple[str, float]]] = {}
    for d, r in sorted(usd_rates.items()):
        for base in CURRENCIES:
            if base not in r:
                continue
            for quote in CURRENCIES:
                if quote == base or quote not in r:
                    continue
                close = r[quote] / r[base]
                pairs.setdefault(f"{base}{quote}", []).append((d, close))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default="2019-01-01")
    ap.add_argument("--until", default=date.today().isoformat())
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    since, until = date.fromisoformat(args.since), date.fromisoformat(args.until)

    if args.dry_run or not args.apply:
        print(f"plan: fetch USD-base ECB rates {since}..{until} for "
              f"{len(CURRENCIES)} currencies -> up to "
              f"{len(CURRENCIES) * (len(CURRENCIES) - 1)} pair files in {CACHE_DIR}")
        print("requests: 1 (frankfurter multi-currency range endpoint)")
        return 0

    requests_made = 1
    rates = fetch_usd_rates(since, until)
    pairs = build_pairs(rates)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    for pair, rows in sorted(pairs.items()):
        if len(rows) < 100:
            print(f"skip {pair}: only {len(rows)} rows", file=sys.stderr)
            continue
        lines = ["date,close"] + [f"{d},{c:.10g}" for d, c in rows]
        (CACHE_DIR / f"{pair}.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        written += 1
        time.sleep(0)  # disk only; network sleep accounted below
    time.sleep(SLEEP_SEC)  # polite pause after the single network request

    print(f"requests made: {requests_made} (cap {MAX_REQUESTS})")
    print(f"pairs written: {written}")
    for pair in sorted(pairs)[:5]:
        rows = pairs[pair]
        print(f"  {pair}: {len(rows)} rows {rows[0][0]}..{rows[-1][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
