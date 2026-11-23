"""One place that records picks into the provenance ledger at EMIT time.

WHY THIS MODULE EXISTS
    `alpha_engine/production_scanner.py` had the emit hook inline in section 6y.
    That made the ledger structurally blind to every pick that does not pass through
    the production scanner -- a survivorship hole in the very instrument built to
    close one. Measured 2026-11-22: 3,500 of 3,500 closed dashboard picks were
    `dashboard_only`, i.e. never emitted (`reports/provenance/reconciliation.json`).

    So the mapping logic lives here once, and every pick-producing path calls it.

THE CONTRACT
    `emit_picks(picks, default_source=...) -> (written, rejected)`

    - `created_at` is NOT accepted from the caller. `provenance_ledger.emit()` stamps
      it. That is the entire point: a pick that can carry its own timestamp can be
      backfilled, and a backfillable ledger proves nothing.
    - A pick without a usable entry, TP **and** SL is rejected rather than emitted
      with zeros, because a pick with no levels has no resolvable outcome.
    - FAIL-SAFE, ALWAYS. Any exception is caught, logged once, and `([], [])`
      returned. A provenance write must never be able to stop picks being produced:
      the ledger exists to observe the trading system, not to gate it.

NOT A GATE
    This records. It never blocks, never filters, never reorders. If you are looking
    for the thing that decides whether a pick is good, it is not here.
"""
from __future__ import annotations

import sys
from pathlib import Path

_TOOLS = str(Path(__file__).resolve().parent.parent / "tools")
if _TOOLS not in sys.path:          # guard: do not accumulate sys.path entries
    sys.path.insert(0, _TOOLS)

# Field names observed across the pick-producing paths. First present wins.
_SYMBOL = ("symbol", "ticker", "pair", "instrument")
_SIDE = ("direction", "side", "position")
_ENTRY = ("entry_price", "entry", "entry_ref", "price_open")
_TP = ("take_profit", "tp", "target")
_SL = ("stop_loss", "sl", "stop")
_STRATEGY = ("strategy", "strategy_family", "strategy_name", "strat")
_SOURCE = ("source_system", "source", "system", "origin")


def _first(pick: dict, names: tuple[str, ...]):
    for n in names:
        v = pick.get(n)
        if v not in (None, "", 0, 0.0):
            return v
    return None


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def to_ledger_pick(pick: dict, default_source: str | None = None) -> dict | None:
    """Map a pick from any producer onto the ledger schema. None if unusable.

    Returns None rather than a zero-filled record: a pick with no TP/SL has no
    resolvable outcome, so emitting it would create a permanently OPEN row that
    silently drags down `pct_forward` later.
    """
    entry = _num(_first(pick, _ENTRY))
    tp = _num(_first(pick, _TP))
    sl = _num(_first(pick, _SL))
    if not (entry and tp and sl):
        return None
    side = (_first(pick, _SIDE) or "").strip().upper()
    if side not in ("LONG", "SHORT"):
        return None
    return {
        "symbol": _first(pick, _SYMBOL),
        "side": side,
        "entry_ref": entry,
        "tp": tp,
        "sl": sl,
        "strategy": _first(pick, _STRATEGY) or "unknown",
        "source_system": _first(pick, _SOURCE) or default_source or "unknown",
        "horizon_hours": pick.get("horizon_hours"),
        "signal_ts": pick.get("signal_ts") or pick.get("as_of"),
    }


def emit_picks(picks, default_source: str | None = None,
               label: str = "PROVENANCE", quiet: bool = False, path=None):
    """Record `picks` into the ledger. Never raises.

    `path` exists so a test can point at a temporary ledger instead of the real one;
    it is None in production and lets `provenance_ledger.emit` use its own default.

    Returns (written, rejected) exactly as `provenance_ledger.emit()` does, or
    ([], []) on any failure.
    """
    try:
        from provenance_ledger import emit  # noqa: PLC0415  (late, keeps import cheap)

        rows, dropped, n_in = [], 0, 0
        for p in (picks or []):
            n_in += 1
            mapped = to_ledger_pick(p, default_source)
            if mapped is None:
                dropped += 1
                continue
            rows.append(mapped)
        if not rows:
            if not quiet:
                print(f"  [{label}] nothing to record "
                      f"({n_in} input, {dropped} unusable)")
            return [], []
        written, rejected = (emit(rows, path) if path is not None else emit(rows))
        if not quiet:
            print(f"  [{label}] recorded {len(written)} pick(s), rejected "
                  f"{len(rejected)} at validation ({dropped} unusable before it)")
            if written:
                print(f"  [{label}] chain head seq={written[-1]['seq']} "
                      f"sha={written[-1]['sha256'][:16]}...")
        return written, rejected
    except Exception as e:  # noqa: BLE001
        if not quiet:
            print(f"  [{label}] skipped (non-fatal): {e}")
        return [], []
