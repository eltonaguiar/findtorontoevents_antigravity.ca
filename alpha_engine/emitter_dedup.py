#!/usr/bin/env python3
"""
emitter_dedup.py -- Action Item A9: emitter/resolver idempotency
================================================================

PROBLEM
-------
41% of the closed-pick ledger is duplicate re-emissions of the same signal
(proven retroactively by ``tools/build_pf_registry.py`` +
``reports/pf_registry_2026-05-17.md``). The existing closed-pick writers
deduplicate only by pick ``id``, but a re-emitted signal is assigned a FRESH
``id`` on every cycle -- so the id-dedup never catches it. Every downstream
PF/WR number is corrupted because winners get re-emitted more often than
losers, asymmetrically inflating profit factor.

SOLUTION
--------
Compute a DETERMINISTIC idempotency key at WRITE time and stamp it onto the
pick as ``pick['dedup_key']``. The key is a stable hash of the signal
identity -- ``(asset_class, strategy, symbol, direction, entry_bar,
entry_price_rounded)`` -- which matches the retroactive dedup logic in
``tools/build_pf_registry.py`` (``classify_rows``). Two emissions of the same
signal collapse to the same key even though their ``id`` differs.

The closed-pick writers then call :func:`dedup_closed_picks` before
persisting: any row whose ``dedup_key`` was already seen is dropped (the
first occurrence wins). This stops FUTURE duplicates from ever being written.

This module does NOT rewrite history and does NOT mutate any existing ledger
file -- existing duplicates are still cleaned at READ time by
``build_pf_registry.py``.

ENV GATE
--------
``EMITTER_DEDUP`` (default ``"1"`` -- ON). Set ``EMITTER_DEDUP=0`` to disable
the guard entirely (writers fall back to their previous id-only dedup).

FAIL-SOFT
---------
Every public function is wrapped so that any unexpected exception falls back
to the caller's prior behavior. The resolver must never crash because of the
de-dup guard.
"""
from __future__ import annotations

import hashlib
import os

# Entry prices are rounded to this many decimals when forming the key, so two
# emissions of the same signal with float jitter still collapse. Matches
# ENTRY_PRICE_ROUND in tools/build_pf_registry.py.
ENTRY_PRICE_ROUND = 2

# Fields tried, in order, to determine the entry bar / timestamp. Mirrors the
# _trade_date() fallback chain in tools/build_pf_registry.py but keeps the full
# value (not just the YYYY-MM-DD date) so two genuinely distinct same-day
# signals are not collapsed.
_ENTRY_TIME_FIELDS = (
    "entry_date", "entry_time", "opened_at", "scan_time",
    "timestamp", "created_at",
)
# Fields tried for entry price.
_ENTRY_PRICE_FIELDS = ("entry_price", "entry", "price")


def dedup_enabled() -> bool:
    """True unless EMITTER_DEDUP is explicitly set to a falsy value."""
    return os.environ.get("EMITTER_DEDUP", "1").strip().lower() not in (
        "0", "false", "no", "off", ""
    )


def _norm(val, default="UNKNOWN") -> str:
    if val is None:
        return default
    s = str(val).strip()
    return s if s else default


def _entry_time(pick: dict) -> str:
    for field in _ENTRY_TIME_FIELDS:
        v = pick.get(field)
        if v:
            return str(v)
    return "UNKNOWN"


def _entry_price_key(pick: dict) -> str:
    for field in _ENTRY_PRICE_FIELDS:
        v = pick.get(field)
        if v in (None, ""):
            continue
        try:
            return str(round(float(v), ENTRY_PRICE_ROUND))
        except (TypeError, ValueError):
            continue
    return "NA"


def compute_dedup_key(pick: dict) -> str:
    """Return a deterministic idempotency key for ``pick``.

    Stable hash of (asset_class | strategy | symbol | direction |
    entry_bar | entry_price_rounded). Returns a short hex digest.

    Strategy identity prefers ``source_system`` then ``strategy`` -- the same
    grouping the COT re-emission bug lives in, matching build_pf_registry.py.
    """
    asset_class = _norm(pick.get("asset_class"))
    strategy = _norm(pick.get("source_system") or pick.get("strategy"))
    symbol = _norm(pick.get("symbol"))
    direction = _norm(pick.get("direction") or pick.get("side"))
    entry_bar = _entry_time(pick)
    entry_price = _entry_price_key(pick)

    raw = "|".join([
        asset_class, strategy, symbol, direction, entry_bar, entry_price,
    ])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def ensure_dedup_key(pick: dict) -> str:
    """Stamp ``pick['dedup_key']`` if absent and return it.

    Fail-soft: on any error returns an empty string and leaves the pick alone.
    """
    try:
        existing = pick.get("dedup_key")
        if existing:
            return str(existing)
        key = compute_dedup_key(pick)
        pick["dedup_key"] = key
        return key
    except Exception:
        return ""


def dedup_closed_picks(picks: list, *, label: str = "closed_picks"):
    """Drop duplicate re-emissions from ``picks`` by deterministic dedup key.

    Stamps ``dedup_key`` on every pick (in place), then keeps only the FIRST
    occurrence of each key. Picks whose key cannot be computed are always
    kept (fail-open per row).

    Returns ``(deduped_list, blocked_count)``.

    When the EMITTER_DEDUP env gate is off, returns ``(picks, 0)`` unchanged.
    On any unexpected error the original list is returned untouched so the
    caller's prior behavior is preserved.
    """
    try:
        if not dedup_enabled():
            return picks, 0
        if not isinstance(picks, list):
            return picks, 0

        seen: set[str] = set()
        deduped: list = []
        blocked = 0
        for p in picks:
            if not isinstance(p, dict):
                deduped.append(p)
                continue
            key = ensure_dedup_key(p)
            if not key:
                # could not key this row -- keep it (fail-open per row)
                deduped.append(p)
                continue
            if key in seen:
                blocked += 1
                continue
            seen.add(key)
            deduped.append(p)

        if blocked:
            print(f"  [EMITTER_DEDUP] Blocked {blocked} duplicate "
                  f"re-emission(s) in {label} (key=dedup_key)")
        return deduped, blocked
    except Exception as exc:  # pragma: no cover - defensive
        print(f"  [EMITTER_DEDUP] WARNING: guard failed ({exc}); "
              f"falling back to no-dedup")
        return picks, 0


# ---------------------------------------------------------------------------
# Self-check -- run: python alpha_engine/emitter_dedup.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    failures = []

    def check(name, cond):
        if cond:
            print(f"  PASS  {name}")
        else:
            print(f"  FAIL  {name}")
            failures.append(name)

    base = {
        "asset_class": "CRYPTO", "strategy": "dna_winner", "symbol": "BTCUSDT",
        "direction": "LONG", "entry_time": "2026-05-17T00:00:00Z",
        "entry_price": 64000.01, "id": "id-A",
    }
    # (a) a fresh row writes
    os.environ["EMITTER_DEDUP"] = "1"
    out, blocked = dedup_closed_picks([dict(base)], label="test")
    check("(a) fresh row is written", len(out) == 1 and blocked == 0)
    check("(a) dedup_key was stamped", bool(out[0].get("dedup_key")))

    # (b) identical row written twice is blocked once.
    # Re-emission gets a FRESH id + float jitter on entry_price -- id-dedup
    # would miss it, dedup_key must still collapse it.
    reemit = dict(base)
    reemit["id"] = "id-B"               # fresh id (re-emission)
    reemit["entry_price"] = 64000.0103  # float jitter, same rounded price
    out, blocked = dedup_closed_picks([dict(base), reemit], label="test")
    check("(b) duplicate re-emission blocked once",
          len(out) == 1 and blocked == 1)

    # genuinely distinct signal is NOT blocked
    other = dict(base)
    other["symbol"] = "ETHUSDT"
    out, blocked = dedup_closed_picks([dict(base), other], label="test")
    check("    distinct signal is kept", len(out) == 2 and blocked == 0)

    # (c) EMITTER_DEDUP=0 disables the guard
    os.environ["EMITTER_DEDUP"] = "0"
    out, blocked = dedup_closed_picks([dict(base), dict(reemit)], label="test")
    check("(c) EMITTER_DEDUP=0 disables guard",
          len(out) == 2 and blocked == 0)
    os.environ["EMITTER_DEDUP"] = "1"

    # determinism: same pick -> same key across calls
    check("    compute_dedup_key is deterministic",
          compute_dedup_key(dict(base)) == compute_dedup_key(dict(base)))

    if failures:
        print(f"\nSELF-CHECK FAILED: {len(failures)} failure(s)")
        sys.exit(1)
    print("\nSELF-CHECK PASSED")
    sys.exit(0)
