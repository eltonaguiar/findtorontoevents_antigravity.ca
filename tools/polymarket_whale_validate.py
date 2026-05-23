#!/usr/bin/env python3
"""
Polymarket whale-position validator.

Takes a list of wallet addresses (Polygon hex 0x...) and pulls each
wallet's current open positions + recent trade activity from the
public Polymarket data-api. Outputs JSON suitable for seeding
`lm_polymarket_wallets` / `lm_polymarket_positions` (Copilot Phase 2.10).

USAGE
    python tools/polymarket_whale_validate.py --addresses 0xabc...,0xdef...
    python tools/polymarket_whale_validate.py --seed-file data/polymarket_whale_seed.json

The seed file is JSON: [{"label": "Swiss Tony", "address": "0x...", "focus": "soccer underdog"}, ...].

API SURFACE NOTES (probed 2026-04-26)
- `https://data-api.polymarket.com/positions?user=<address>` — works,
  returns array of open positions with marketId, side, shares, entry price.
  Empty array for unknown addresses (graceful).
- `https://data-api.polymarket.com/trades?user=<address>&limit=100` — works,
  recent trade history.
- `https://lb-api.polymarket.com/profit?window=...` — rejects every
  param shape we tried. Cannot use to discover top traders by username.
- `https://gamma-api.polymarket.com/users?username=...` — returns
  "invalid token/cookies"; not public.

CONSEQUENCE: discovering which addresses correspond to display names
("Swiss Tony", "HyperLiquid0xb", etc. from the Kimi research) requires
either (a) clicking through each profile on polymarket.com and copying
the address from the URL, or (b) using a third-party leaderboard
mirror. Operator must seed the address list manually for v1.

Read-only. Stdlib + standard urllib only. Does not commit anything.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_API = "https://data-api.polymarket.com"
UA = "FindTorontoEvents-Whale-Validate/1.0"


def http_get_json(url: str, timeout: float = 30.0):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_positions(address: str) -> list[dict]:
    url = f"{DATA_API}/positions?user={address}"
    try:
        data = http_get_json(url)
    except urllib.error.HTTPError as e:
        print(f"[positions] {address[:10]}…: HTTP {e.code}", file=sys.stderr)
        return []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"[positions] {address[:10]}…: {e}", file=sys.stderr)
        return []
    return data if isinstance(data, list) else []


def fetch_trades(address: str, limit: int = 100) -> list[dict]:
    url = f"{DATA_API}/trades?user={address}&limit={limit}"
    try:
        data = http_get_json(url)
    except urllib.error.HTTPError as e:
        print(f"[trades] {address[:10]}…: HTTP {e.code}", file=sys.stderr)
        return []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"[trades] {address[:10]}…: {e}", file=sys.stderr)
        return []
    return data if isinstance(data, list) else []


def summarize_wallet(addr_entry: dict) -> dict:
    address = addr_entry["address"].strip().lower()
    label = addr_entry.get("label") or address[:10]
    focus = addr_entry.get("focus") or "unknown"
    positions = fetch_positions(address)
    trades = fetch_trades(address)

    open_n = len(positions)
    total_open_value = 0.0
    for p in positions:
        try:
            total_open_value += float(p.get("currentValue") or p.get("size") or 0)
        except (TypeError, ValueError):
            continue
    last_trade_at = None
    for t in trades[:1]:
        last_trade_at = t.get("timestamp") or t.get("time")
        break

    return {
        "label": label,
        "address": address,
        "focus": focus,
        "open_positions": open_n,
        "open_value_usd": round(total_open_value, 2),
        "recent_trades_n": len(trades),
        "last_trade_at": last_trade_at,
        "active": open_n > 0 or len(trades) > 0,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def load_seed(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[seed] parse failed: {e}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        return []
    out = []
    for entry in data:
        if isinstance(entry, dict) and "address" in entry:
            out.append(entry)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--addresses", help="Comma-separated 0x... addresses")
    ap.add_argument("--seed-file", default=str(REPO / "data" / "polymarket_whale_seed.json"))
    ap.add_argument("--out", default=str(REPO / "data" / "polymarket_whale_validation.json"))
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    entries: list[dict] = []
    if args.addresses:
        for a in args.addresses.split(","):
            a = a.strip()
            if a:
                entries.append({"label": a[:10], "address": a, "focus": "cli"})
    else:
        seed_path = Path(args.seed_file)
        entries = load_seed(seed_path)
        if not entries:
            print(f"No seed at {seed_path} and no --addresses given. "
                  "Create the seed file with [{label, address, focus}, ...] "
                  "(see polymarket.com/profile/<address> URLs to discover addresses).",
                  file=sys.stderr)
            return 2

    rows = []
    for i, entry in enumerate(entries):
        if i:
            time.sleep(0.5)  # courtesy
        rows.append(summarize_wallet(entry))

    payload = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "wallets": rows,
        "summary": {
            "n_wallets": len(rows),
            "n_active": sum(1 for r in rows if r["active"]),
        },
    }
    text = json.dumps(payload, indent=2)
    if args.stdout:
        sys.stdout.write(text)
        return 0
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"Wrote {out_path}  wallets={len(rows)}  active={payload['summary']['n_active']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
