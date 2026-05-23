#!/usr/bin/env python3
"""
backfill_resolver_scale_mismatch.py — clean corrupt resolver rows from the
canonical closed-pick ledger (alpha_engine/data/closed_picks.json).

BACKGROUND
----------
M-112 (2026-05-18) fixed a price-scale-mismatch bug in
``alpha_engine/outcome_resolver.py``'s non-crypto bar-replay path
(``resolve_non_crypto_picks``, ~line 2523). Some upstream writers stored
``entry_price`` / ``take_profit`` / ``stop_loss`` on a normalized ~0-1 scale
while the resolver compared them against raw Yahoo OHLC bars. A gapped bar then
credited a raw bar price as the fill, exploding ``pnl_pct`` (e.g. HG=F entry
0.59035 vs exit 6.287 -> pnl_pct 9.649615 = +965%).

M-112 stops NEW corruption (it now skips rows whose exit/entry ratio > 10x and
stamps ``_pnl_scale_mismatch=True``), but rows written BEFORE the fix already
landed in closed_picks.json and pollute the FUTURES/COMMODITY/EQUITY aggregates
in audit_dashboard/data/pf_registry.json.

WHAT THIS SCRIPT DOES
---------------------
Detects already-landed corrupt rows and (with --apply) un-resolves them:
nulls the bad exit_price + pnl_pct so the resolver's own ``is_unresolved()``
guard re-picks them up on the next run. It does NOT delete rows and does NOT
invent status enum values.

Detection mirrors the two M-112 guards exactly:
  1. SCALE guard  — entry_price and a resolved exit price both > 0 and
                    max(exit/entry, entry/exit) > 10.0  (outcome_resolver.py:2535)
  2. PNL-CAP guard — resolved_by == "non_crypto_resolver" and |pnl_pct| exceeds
                    the per-asset-class sanity cap from
                    outcome_resolver._pnl_sanity_cap_for() (outcome_resolver.py:2553)

DEFAULT IS DRY-RUN. Pass --apply to write. Network-free.

USAGE
-----
  python tools/backfill_resolver_scale_mismatch.py              # dry-run (default)
  python tools/backfill_resolver_scale_mismatch.py --apply      # write (makes .bak first)
  python tools/backfill_resolver_scale_mismatch.py --file other.json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import shutil
import sys
from datetime import datetime, timezone

# --------------------------------------------------------------------------
# Constants — kept in lockstep with alpha_engine/outcome_resolver.py M-112.
# --------------------------------------------------------------------------
SCALE_RATIO_THRESHOLD = 10.0  # outcome_resolver.py:2535  (_scale_ratio > 10.0)

DEFAULT_FILE = os.path.join("alpha_engine", "data", "closed_picks.json")
MAX_INMEMORY_BYTES = 50 * 1024 * 1024  # 50MB — above this, stream instead.

# Status value the resolver treats as "still needs resolution". closed_picks.json
# rows are all already-closed; outcome_resolver.is_unresolved() (line 661-663)
# re-detects any row whose status is in {WON,LOST,CLOSED,EXPIRED} once its
# exit_price is None. We therefore DO NOT change `status` — we only null the
# bad exit_price + pnl_pct, which is the exact signal is_unresolved() keys on.
# This avoids inventing an enum value (per task constraint).
UNRESOLVED_STATUSES = {"WON", "LOST", "CLOSED", "EXPIRED"}

# Field names — confirmed against the live closed_picks.json schema
# (8463 rows, 2026-05-18): every row has entry_price, exit_price, pnl_pct,
# status, exit_reason; resolved_by present on resolver-touched rows.
F_ENTRY = "entry_price"
F_EXIT = "exit_price"
F_PNL = "pnl_pct"
F_STATUS = "status"
F_RESOLVED_BY = "resolved_by"
F_ASSET_CLASS = "asset_class"
F_SYMBOL = "symbol"

NON_CRYPTO_RESOLVER = "non_crypto_resolver"


# --------------------------------------------------------------------------
# Per-class PnL sanity cap. Prefer importing the canonical function from
# outcome_resolver.py so the two never drift; fall back to an inline mirror
# if the import fails (keeps this script network-free + standalone).
# --------------------------------------------------------------------------
def _load_pnl_sanity_cap():
    """Return _pnl_sanity_cap_for(asset_class)->float, importing if possible."""
    try:
        # repo-root-relative import
        sys.path.insert(0, os.getcwd())
        from alpha_engine.outcome_resolver import _pnl_sanity_cap_for  # type: ignore
        return _pnl_sanity_cap_for, "imported from alpha_engine.outcome_resolver"
    except Exception:
        # Inline mirror of outcome_resolver.py PNL_SANITY_CAP_BY_CLASS (M-111).
        _CAP_BY_CLASS = {
            "FOREX": 0.30, "EQUITY": 5.00, "ETF": 2.00, "CRYPTO": 5.00,
            "COMMODITY": 2.00, "BOND": 0.50, "FUTURES": 3.00,
            "STOCK": 5.00, "STOCKS": 5.00, "INDEX": 2.00,
        }
        _CAP_DEFAULT = 10.0

        def _fallback(asset_class):
            return _CAP_BY_CLASS.get(str(asset_class or "").upper(), _CAP_DEFAULT)

        return _fallback, "inline fallback (import failed)"


_PNL_SANITY_CAP_FOR, _CAP_SOURCE = _load_pnl_sanity_cap()


# --------------------------------------------------------------------------
# Pure helpers (testable, no I/O).
# --------------------------------------------------------------------------
def _num(x):
    """Coerce to float, or None if not a usable positive-able number."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    return v


def scale_ratio(row: dict):
    """Return max(exit/entry, entry/exit) if both prices > 0, else None.

    Mirrors outcome_resolver.py:2533-2534."""
    entry = _num(row.get(F_ENTRY))
    exit_p = _num(row.get(F_EXIT))
    if entry is None or exit_p is None or entry <= 0 or exit_p <= 0:
        return None
    return max(exit_p / entry, entry / exit_p)


def is_scale_corrupt(row: dict) -> bool:
    """True if `row` is a price-scale-mismatch corrupt resolver row.

    Two independent triggers, matching the two M-112 guards:
      (A) scale guard  — exit/entry (or inverse) ratio > 10x.
      (B) pnl-cap guard — resolved by non_crypto_resolver and |pnl_pct| exceeds
                          the per-asset-class sanity cap.
    Either trigger flags the row. Pure function — no I/O."""
    return _scale_trigger(row) or _pnl_cap_trigger(row)


def _scale_trigger(row: dict) -> bool:
    r = scale_ratio(row)
    return r is not None and r > SCALE_RATIO_THRESHOLD


def _pnl_cap_trigger(row: dict) -> bool:
    if str(row.get(F_RESOLVED_BY) or "") != NON_CRYPTO_RESOLVER:
        return False
    pnl = _num(row.get(F_PNL))
    if pnl is None:
        return False
    cap = _PNL_SANITY_CAP_FOR(row.get(F_ASSET_CLASS))
    return abs(pnl) > cap


def corrupt_reason(row: dict) -> str:
    """Human-readable reason a row tripped detection (for the report)."""
    parts = []
    if _scale_trigger(row):
        parts.append("scale>%gx" % SCALE_RATIO_THRESHOLD)
    if _pnl_cap_trigger(row):
        cap = _PNL_SANITY_CAP_FOR(row.get(F_ASSET_CLASS))
        parts.append("pnl>%g(cap)" % cap)
    return "+".join(parts) or "-"


def build_correction(row: dict) -> dict:
    """Return a NEW dict — `row` with the backfill correction applied.

    Does not mutate the input. Action:
      * pnl_pct  -> None
      * exit_price -> None  (the bad raw-scale price)
      * status   -> kept as-is (a valid closed-ledger enum; nulling exit_price
                    is what is_unresolved() keys on, so the resolver re-picks
                    the row up next run — no invented enum value)
      * _pnl_scale_mismatch -> True   (parity with M-112's live stamp)
      * _backfill_note -> diagnostic string with the original values + ratio
    Rows are never deleted."""
    out = dict(row)
    r = scale_ratio(row)
    orig_pnl = row.get(F_PNL)
    orig_exit = row.get(F_EXIT)
    orig_entry = row.get(F_ENTRY)
    out[F_PNL] = None
    out[F_EXIT] = None
    out["_pnl_scale_mismatch"] = True
    if r is not None:
        out["_pnl_scale_ratio"] = round(r, 2)
    note = (
        "backfill_resolver_scale_mismatch %s: reason=%s entry=%s "
        "bad_exit=%s bad_pnl_pct=%s ratio=%s — un-resolved (exit_price+pnl_pct "
        "nulled) so outcome_resolver.is_unresolved() re-picks it up."
    ) % (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        corrupt_reason(row),
        orig_entry, orig_exit, orig_pnl,
        ("%.2f" % r) if r is not None else "n/a",
    )
    out["_backfill_note"] = note
    return out


def find_corrupt(rows):
    """Yield (index, row) for every corrupt row. Pure (no I/O)."""
    for i, row in enumerate(rows):
        if isinstance(row, dict) and is_scale_corrupt(row):
            yield i, row


# --------------------------------------------------------------------------
# I/O + reporting.
# --------------------------------------------------------------------------
def _fmt(v, width=14):
    if v is None:
        return "-".ljust(width)
    if isinstance(v, float):
        return ("%.6g" % v).ljust(width)
    return str(v)[:width].ljust(width)


def print_dry_run(rows, path):
    corrupt = list(find_corrupt(rows))
    print("=" * 100)
    print("DRY-RUN  backfill_resolver_scale_mismatch.py")
    print("file              : %s" % path)
    print("total rows         : %d" % len(rows))
    print("scale threshold    : ratio > %g x  (outcome_resolver.py:2535)" % SCALE_RATIO_THRESHOLD)
    print("pnl cap source     : %s" % _CAP_SOURCE)
    print("corrupt rows found : %d" % len(corrupt))
    print("=" * 100)

    if not corrupt:
        print("No corrupt rows. Nothing would change.")
        return corrupt

    hdr = (
        _fmt("symbol", 12) + _fmt("asset_class", 12) + _fmt("entry", 14)
        + _fmt("exit", 16) + _fmt("ratio", 10) + _fmt("pnl_pct", 14)
        + _fmt("resolved_by", 20) + _fmt("status", 9) + "reason"
    )
    print(hdr)
    print("-" * 100)
    by_class = collections.Counter()
    by_reason = collections.Counter()
    for idx, row in corrupt:
        r = scale_ratio(row)
        ac = row.get(F_ASSET_CLASS)
        by_class[str(ac)] += 1
        by_reason[corrupt_reason(row)] += 1
        print(
            _fmt(row.get(F_SYMBOL), 12)
            + _fmt(ac, 12)
            + _fmt(_num(row.get(F_ENTRY)), 14)
            + _fmt(_num(row.get(F_EXIT)), 16)
            + _fmt(round(r, 4) if r is not None else None, 10)
            + _fmt(_num(row.get(F_PNL)), 14)
            + _fmt(row.get(F_RESOLVED_BY), 20)
            + _fmt(row.get(F_STATUS), 9)
            + corrupt_reason(row)
        )
    print("-" * 100)
    print("counts per asset class:")
    for ac, c in sorted(by_class.items(), key=lambda kv: -kv[1]):
        print("  %-14s %d" % (ac, c))
    print("counts per detection reason:")
    for reason, c in sorted(by_reason.items(), key=lambda kv: -kv[1]):
        print("  %-22s %d" % (reason, c))
    print("=" * 100)
    print("WOULD un-resolve %d row(s): pnl_pct->null, exit_price->null, "
          "status kept, _pnl_scale_mismatch=true stamped." % len(corrupt))
    print("No file written (dry-run). Re-run with --apply to write.")
    return corrupt


def apply_corrections(rows, path):
    corrupt = list(find_corrupt(rows))
    if not corrupt:
        print("No corrupt rows — nothing to apply.")
        return 0
    bak = path + ".bak"
    shutil.copy2(path, bak)
    print("backup written: %s" % bak)
    by_class = collections.Counter()
    for idx, row in corrupt:
        rows[idx] = build_correction(row)
        by_class[str(row.get(F_ASSET_CLASS))] += 1
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    print("APPLIED — %d row(s) un-resolved, file rewritten: %s" % (len(corrupt), path))
    for ac, c in sorted(by_class.items(), key=lambda kv: -kv[1]):
        print("  %-14s %d" % (ac, c))
    return len(corrupt)


def report_pf_registry_followup(corrupt_count):
    print()
    print("-" * 100)
    print("FOLLOW-UP — audit_dashboard/data/pf_registry.json")
    if corrupt_count == 0:
        print("  No rows changed; pf_registry.json regeneration NOT required.")
    else:
        print("  %d corrupt row(s) feed FUTURES/COMMODITY/EQUITY aggregates in" % corrupt_count)
        print("  audit_dashboard/data/pf_registry.json — it WILL need regeneration")
        print("  AFTER --apply for the canonical PF/WR to reflect the cleaned ledger.")
    print("  Generator       : tools/build_pf_registry.py")
    print("  Workflow        : .github/workflows/audit-dashboard.yml")
    print("  This script does NOT run that generator (CLAUDE.md: generators")
    print("  overwrite live JSON). Operator must run it as a separate step.")
    print("-" * 100)


# --------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Backfill: un-resolve price-scale-mismatch corrupt rows "
                    "in the closed-pick ledger. Dry-run by default."
    )
    ap.add_argument("--file", default=DEFAULT_FILE,
                    help="closed-pick ledger (default: %s)" % DEFAULT_FILE)
    ap.add_argument("--apply", action="store_true",
                    help="WRITE corrections (makes a .bak first). "
                         "Omit for dry-run (default).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Explicit dry-run (this is already the default; "
                         "accepted as a no-op for clarity). Ignored if --apply.")
    args = ap.parse_args(argv)
    if args.dry_run and args.apply:
        print("ERROR: --dry-run and --apply are mutually exclusive.", file=sys.stderr)
        return 5

    path = args.file
    if not os.path.isfile(path):
        print("ERROR: file not found: %s" % path, file=sys.stderr)
        return 2

    size = os.path.getsize(path)
    if size > MAX_INMEMORY_BYTES:
        print("ERROR: %s is %.1f MB (> %d MB cap). Streaming not implemented; "
              "increase MAX_INMEMORY_BYTES only after confirming RAM headroom."
              % (path, size / 1024 / 1024, MAX_INMEMORY_BYTES // 1024 // 1024),
              file=sys.stderr)
        return 3

    with open(path, "r", encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list):
        print("ERROR: expected a JSON list at top level, got %s" % type(rows).__name__,
              file=sys.stderr)
        return 4

    if args.apply:
        n = apply_corrections(rows, path)
    else:
        corrupt = print_dry_run(rows, path)
        n = len(corrupt)
    report_pf_registry_followup(n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
