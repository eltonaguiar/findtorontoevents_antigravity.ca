"""Entry-field contract for picks (2026-11-20).

Regime, hedge, path and time-in-market analysis all need to know WHEN a pick was
created and WHAT price it was taken at. 45.5% of resolved picks carried no
`entry_time`, which made half the book unusable for any of those questions.

This module owns the derivation so every producer and the dashboard ingest agree
on one priority order. It never invents a price: a missing entry_price stays
None and is reported as missing.
"""
from __future__ import annotations

from datetime import datetime, timezone

# Ordered by how close each field is to the moment the pick was created.
ENTRY_TS_KEYS = (
    "entry_time", "entryTime", "entry_date", "entryDate", "opened_at",
    "signal_time", "signalTime", "generated_at", "created_at", "createdAt",
    "at_issue", "first_seen", "detected_at", "timestamp",
)
ENTRY_PRICE_KEYS = (
    "entry_price", "entryPrice", "entry", "price_at_signal", "price",
    "signal_price", "fill_price", "open_price",
)


def _positive(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def to_utc_iso(value) -> str | None:
    """Parse a timestamp-ish value into ``YYYY-MM-DDTHH:MM:SSZ``.

    Naive datetimes are read as UTC (every producer here writes UTC); a bare date
    becomes midnight UTC.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if not raw:
            return None
        raw = raw.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
                try:
                    dt = datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    continue
            else:
                return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def derive_entry_time(pick: dict) -> tuple[str | None, str | None]:
    """Return ``(iso_utc, source_field)`` from the first usable field."""
    for key in ENTRY_TS_KEYS:
        iso = to_utc_iso(pick.get(key))
        if iso:
            return iso, key
    return None, None


def derive_entry_price(pick: dict) -> tuple[float | None, str | None]:
    for key in ENTRY_PRICE_KEYS:
        val = _positive(pick.get(key))
        if val is not None:
            return val, key
    return None, None


def ensure_entry_fields(pick: dict) -> dict:
    """Return ``pick`` with entry_time/entry_price filled where derivable.

    Adds ``entry_time_source``/``entry_price_source`` so a consumer can tell a
    native stamp from a derived one, and ``entry_fields_complete``.
    """
    out = dict(pick)
    ts, ts_src = derive_entry_time(out)
    price, price_src = derive_entry_price(out)
    out["entry_time"] = ts
    out["entry_price"] = price
    out["entry_time_source"] = ts_src
    out["entry_price_source"] = price_src
    out["entry_fields_complete"] = bool(ts and price)
    return out


def coverage(rows: list[dict]) -> dict:
    """Entry-field coverage, for reports and gates."""
    total = len(rows)
    if not total:
        return {"n": 0, "entry_time_pct": 0.0, "entry_price_pct": 0.0, "both_pct": 0.0}
    ts = sum(1 for r in rows if to_utc_iso(r.get("entry_time")))
    px = sum(1 for r in rows if _positive(r.get("entry_price")) is not None)
    both = sum(
        1 for r in rows
        if to_utc_iso(r.get("entry_time")) and _positive(r.get("entry_price")) is not None
    )
    return {
        "n": total,
        "entry_time_pct": round(ts / total * 100, 2),
        "entry_price_pct": round(px / total * 100, 2),
        "both_pct": round(both / total * 100, 2),
    }
