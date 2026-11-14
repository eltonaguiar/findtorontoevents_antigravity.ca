#!/usr/bin/env python3
"""
Prediction-system data hygiene guardian.

Flags known data-quality defects in the audit dashboard payload:

  STALE_CRYPTO_PRICE      - 24/7 crypto pick whose current_price == entry_price
                            (pinned to entry, never re-quoted at generation
                            time). The dashboard may still print a fresh
                            signal-age banner ("1.9h ago") for these.
  FROZEN_CLOSED_PHANTOM   - closed pick resolved to 0% PnL with exit reason
                            UNKNOWN and exit_price == entry_price (resolver
                            never actually marked it; forced 0%).
  DATE_ONLY_SEED          - pick whose signal_time/entry_time is a bare
                            YYYY-MM-DD string (no time component), so the UI
                            renders "no date" for it.
  NULL_PRICE              - active pick with no current_price populated.
  PLACEHOLDER_ENTRY       - active pick with entry_price <= 0 (placeholder row,
                            e.g. consensus/prediction-market scaffolds).

The report also prints TRUE recency per asset class: the age of the newest
signal, and whether any live quote (current != entry) exists. This lets a
consumer tell signal age apart from price freshness instead of trusting the
banner.

Usage:
  python tools/pi_data_hygiene.py [--json PATH] [--asof ISO8601] [--show]
  python tools/pi_data_hygiene.py --json /tmp/kilo/dashboard_data_latest.json --show

Exit codes: 0 = no findings; 1 = findings present; 2 = input unreadable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

EPS = 1e-6
DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

KNOWN_CRYPTO = {
    "BTC", "ETH", "XRP", "NEAR", "SOL", "DOGE", "LINK", "DOT", "AVAX",
    "ADA", "MATIC", "BNB", "LTC", "SHIB", "PEPE", "WIF", "SUI", "INJ",
    "SEI", "ARB", "OP", "TIA",
}
CRYPTO_QUOTE_SUFFIXES = ("USDT", "USDC", "BUSD", "FDUSD", "TUSD", "DAI", "BTC", "ETH")


def _now(asof: str | None) -> datetime:
    if asof:
        return datetime.fromisoformat(asof.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def _num(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def _is_crypto(symbol) -> bool:
    if not symbol:
        return False
    s = str(symbol).upper().strip()
    base = s.split("=")[0].split("_")[0].split("-")[0]
    if base in KNOWN_CRYPTO:
        return True
    if s.endswith(CRYPTO_QUOTE_SUFFIXES) and not s.endswith("USD=X"):
        return True
    return False


def _date_only_str(v) -> bool:
    if not isinstance(v, str):
        return False
    return bool(DATE_ONLY_RE.match(v.strip()))


def _diff(a, b) -> float | None:
    if a is None or b is None:
        return None
    return abs(a - b)


def classify_active(pick: dict, asof: str | None):
    tags = []
    symbol = pick.get("symbol")
    entry = _num(pick.get("entry_price"))
    cur = _num(pick.get("current_price"))
    sig = pick.get("signal_time") or pick.get("timestamp") or pick.get("entry_time")

    if entry is None or entry <= 0:
        tags.append("PLACEHOLDER_ENTRY")
    if cur is None:
        tags.append("NULL_PRICE")
    if _date_only_str(sig):
        tags.append("DATE_ONLY_SEED")
    if _is_crypto(symbol) and cur is not None and entry is not None and entry > 0:
        d = _diff(cur, entry)
        if d is not None and d <= EPS:
            tags.append("STALE_CRYPTO_PRICE")
    return tags


def classify_closed(pick: dict):
    tags = []
    entry = _num(pick.get("entry_price"))
    exit_price = _num(pick.get("exit_price"))
    pnl = _num(pick.get("pnl_pct"))
    reason = str(pick.get("exit_reason") or "").upper()
    if pnl is not None and abs(pnl) <= EPS and reason == "UNKNOWN":
        if entry is not None and exit_price is not None and _diff(entry, exit_price) is not None:
            if _diff(entry, exit_price) <= EPS:
                tags.append("FROZEN_CLOSED_PHANTOM")
    return tags


def _asset_class(pick: dict, default="UNKNOWN") -> str:
    ac = pick.get("asset_class")
    if ac:
        return str(ac).upper()
    symbol = pick.get("symbol")
    if _is_crypto(symbol):
        return "CRYPTO"
    if symbol and "=" in str(symbol):
        return "FOREX"
    return default


def summarize_active(active: list, asof: str | None):
    now = _now(asof)
    by_class: dict[str, dict] = {}
    for p in active:
        ac = _asset_class(p)
        b = by_class.setdefault(ac, {"n": 0, "live_quotes": 0, "pinned": 0, "newest_signal": None})
        b["n"] += 1
        entry = _num(p.get("entry_price"))
        cur = _num(p.get("current_price"))
        if cur is not None and entry is not None and entry > 0:
            if _diff(cur, entry) is not None and _diff(cur, entry) > EPS:
                b["live_quotes"] += 1
            else:
                b["pinned"] += 1
        sig = p.get("signal_time") or p.get("timestamp") or p.get("entry_time")
        ts = _parse_ts(sig)
        if ts is not None:
            if b["newest_signal"] is None or ts > b["newest_signal"]:
                b["newest_signal"] = ts
    for ac, b in by_class.items():
        if b["newest_signal"] is not None:
            b["newest_signal_age_h"] = round((now - b["newest_signal"]).total_seconds() / 3600.0, 2)
        else:
            b["newest_signal_age_h"] = None
    return by_class


ZOMBIE_AGE_HOURS = 168  # 7 days


def summarize_zombies(raw: list, asof: str | None):
    """Scan the raw active feed for zombie rows per asset class.

    A zombie is a row that is old (signal older than ZOMBIE_AGE_HOURS) or
    that has no current_price (never quoted). The raw feed can contain
    long-dead rows that poison "active" counts.
    """
    now = _now(asof)
    by: dict[str, dict] = {}
    for p in raw:
        ac = _asset_class(p)
        b = by.setdefault(ac, {"n": 0, "older_7d": 0, "null_price": 0})
        b["n"] += 1
        cur = _num(p.get("current_price"))
        if cur is None:
            b["null_price"] += 1
        ts = _parse_ts(p.get("signal_time") or p.get("timestamp") or p.get("entry_time"))
        if ts is not None:
            age_h = (now - ts).total_seconds() / 3600.0
            if age_h > ZOMBIE_AGE_HOURS:
                b["older_7d"] += 1
    return by


def _parse_ts(v) -> datetime | None:
    if not v:
        return None
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(float(v), tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
    s = str(v)
    if _date_only_str(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    try:
        ts = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def run(payload: dict, asof: str | None, show: bool):
    findings = {"STALE_CRYPTO_PRICE": [], "FROZEN_CLOSED_PHANTOM": [],
                "DATE_ONLY_SEED": [], "NULL_PRICE": [], "PLACEHOLDER_ENTRY": []}
    picks = payload.get("picks") or {}
    active = picks.get("active") or []
    closed = picks.get("recent_closed") or []

    for p in active:
        for tag in classify_active(p, asof):
            findings[tag].append((p.get("symbol"), p.get("signal_time") or p.get("timestamp")))
    for p in closed:
        for tag in classify_closed(p):
            findings[tag].append((p.get("symbol"), p.get("closed_at") or p.get("timestamp")))

    total = sum(len(v) for v in findings.values())
    print(f"payload generated_at: {payload.get('generated_at')}")
    print(f"active picks scanned: {len(active)}; recent_closed scanned: {len(closed)}")
    print(f"TOTAL FINDINGS: {total}")
    print()
    for tag, rows in findings.items():
        print(f"{tag}: {len(rows)}")
        if show:
            for sym, ts in rows[:15]:
                print(f"    {sym}  {ts}")
    print()
    print("TRUE RECENCY per asset class (active picks):")
    print(f"{'CLASS':<14}{'N':>4}{'live_quotes':>13}{'cur_eq_entry':>12}{'newest_signal_age_h':>20}")
    for ac, b in sorted(summarize_active(active, asof).items()):
        print(f"{ac:<14}{b['n']:>4}{b['live_quotes']:>13}{b['pinned']:>12}"
              f"{str(b['newest_signal_age_h']):>20}")
    print()
    print(f"ACTIVE_RAW ZOMBIE SCAN (rows older than {ZOMBIE_AGE_HOURS}h or null price):")
    raw = picks.get("active_raw") or []
    if raw:
        print(f"{'CLASS':<14}{'n':>6}{'older_7d':>10}{'null_price':>11}")
        for ac, b in sorted(summarize_zombies(raw, asof).items()):
            print(f"{ac:<14}{b['n']:>6}{b['older_7d']:>10}{b['null_price']:>11}")
    else:
        print("    (no active_raw present)")
    return total


def main(argv=None):
    ap = argparse.ArgumentParser(description="Prediction-system data hygiene guardian")
    ap.add_argument("--json", default=None, help="path to dashboard payload JSON")
    ap.add_argument("--asof", default=None, help="reference time ISO8601")
    ap.add_argument("--show", action="store_true", help="list flagged items")
    args = ap.parse_args(argv)

    path = args.json
    if not path:
        candidates = [
            Path("/tmp/kilo/dashboard_data_latest.json"),
            Path("audit_dashboard/data/dashboard_data.json"),
            Path("alpha_engine/data/active_picks.json"),
        ]
        for c in candidates:
            if c.exists():
                path = str(c)
                break
    if not path:
        print("no payload found; pass --json PATH", file=sys.stderr)
        return 2
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"unable to read {path}: {exc}", file=sys.stderr)
        return 2

    total = run(payload, args.asof, args.show)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
