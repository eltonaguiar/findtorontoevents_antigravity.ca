#!/usr/bin/env python3
"""
Regime feed adapters for verified external crypto signal sources.

Sources:
  - EtherSignals (https://ethersignals.com/api/signals) - ETHUSDT trend/regime, MIT
  - AA Signals (https://signals.brobotapp.com/v1/signal/{SYMBOL}) - 8 crypto symbols, MIT

Both publish UTC timestamps. This module normalises their payloads and flags
any record whose timestamp is in the future relative to the source server
clock or the local fetch time (future-bias guard).

Run:
  python copy_trader_intel/regime_feed_adapters.py --source all
  python copy_trader_intel/regime_feed_adapters.py --source ether --limit 200
  python copy_trader_intel/regime_feed_adapters.py --source aa --symbol ETH
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERROR] pip install requests")
    sys.exit(1)

DATA_DIR = Path(__file__).parent / "data" / "regime_feeds"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, */*",
}

ETHER_URL = "https://ethersignals.com/api/signals"
AA_URL = "https://signals.brobotapp.com/v1/signal/{symbol}"
AA_SYMBOLS = ("BTC", "ETH", "TAO", "QNT", "ZEC", "DOGE", "DOG", "VVV")
FUTURE_TOLERANCE_SECONDS = 10.0


def _get(url, params=None, timeout=25):
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"[ERROR] GET {url} failed: {exc}")
        return None


def _parse_ts(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def fetch_ethersignals(limit=200):
    params = {"limit": limit} if limit else None
    payload = _get(ETHER_URL, params=params)
    if not payload:
        return []
    server_time = _parse_ts((payload.get("stats") or {}).get("serverTime"))
    records = []
    for item in payload.get("signals") or []:
        records.append({
            "source": "ethersignals",
            "signal_id": item.get("id"),
            "symbol": item.get("symbol"),
            "market_type": item.get("marketType"),
            "price": item.get("price"),
            "timeframe": item.get("timeframe"),
            "regime": item.get("regime"),
            "score": item.get("score"),
            "received_at": item.get("receivedAt"),
            "pushed_at": item.get("pushedAt"),
            "server_time": (payload.get("stats") or {}).get("serverTime"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    return records


def fetch_aa_signals(symbol="BTC"):
    payload = _get(AA_URL.format(symbol=symbol))
    if not payload:
        return []
    record = {
        "source": "aa_signals",
        "symbol": payload.get("symbol"),
        "action": payload.get("action"),
        "confidence": payload.get("confidence"),
        "composite_score": payload.get("composite_score"),
        "regime": payload.get("regime"),
        "generated_at": payload.get("generated_at"),
        "source_detail": payload.get("source"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    return [record]


def check_future_bias(records):
    now = datetime.now(timezone.utc)
    violations = []
    for record in records:
        ts = _parse_ts(record.get("received_at") or record.get("generated_at"))
        if ts is None:
            violations.append({"record": record, "reason": "missing_or_unparseable_timestamp"})
            continue
        server_time = _parse_ts(record.get("server_time"))
        reference = server_time or now
        skew = (ts - reference).total_seconds()
        if skew > FUTURE_TOLERANCE_SECONDS:
            violations.append({
                "record": record,
                "reason": "timestamp_ahead_of_reference",
                "skew_seconds": skew,
                "timestamp": ts.isoformat(),
                "reference": reference.isoformat(),
            })
    return violations


def _write(records, source):
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ")
    path = DATA_DIR / f"{source}_{stamp}.json"
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fetch and bias-check verified regime feeds")
    parser.add_argument("--source", choices=("ether", "aa", "all"), default="all")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--symbol", default="BTC", help="AA Signals symbol")
    args = parser.parse_args(argv)

    all_records = []
    if args.source in ("ether", "all"):
        records = fetch_ethersignals(limit=args.limit)
        violations = check_future_bias(records)
        path = _write(records, "ethersignals") if records else None
        print(f"[ethersignals] fetched={len(records)} future_bias_violations={len(violations)} out={path}")
        all_records.extend(records)
    if args.source in ("aa", "all"):
        records = fetch_aa_signals(symbol=args.symbol)
        violations = check_future_bias(records)
        path = _write(records, "aa_signals") if records else None
        print(f"[aa_signals:{args.symbol}] fetched={len(records)} future_bias_violations={len(violations)} out={path}")
        all_records.extend(records)

    violations = check_future_bias(all_records)
    if violations:
        print(f"[WARN] {len(violations)} future-bias violation(s)")
        for violation in violations[:5]:
            print(json.dumps(violation)[:400])
        return 1
    print(f"[OK] {len(all_records)} record(s), no future-bias violations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
