"""
Shared normalization for AI-tournament picks.

One pass that both the JSON merge (merge_submissions_to_latest.py) and the DB
ingest (ingest_to_db.py) call, so the snapshot the dashboard reads and the
tournament_picks table stay consistent. Fixes the data-quality issues found in
the 2026-05-28 audit (TOURNYFIND_OPENCODE_DEEPSEEKV4FLASH.MD):

  - direction strings (SELL/BUY/etc.) collapsed to canonical LONG/SHORT
  - asset_class strings (STOCKS/STOCK) collapsed to canonical EQUITY
  - symbols that were in the wrong class bucket (e.g. XLI tagged CRYPTO) or
    split across two classes (IWM as EQUITY *and* ETF) pinned to one class
  - empty persona_id replaced with a sentinel so it stops polluting counts

normalize_pick() mutates and returns the dict. is_timestamp_anomaly() is a
read-only check used by the backfill to flag (not rewrite) picks whose
resolved_at predates submitted_at.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

# Canonical asset classes for /audit money-ready reporting.
CANONICAL_CLASSES = {"CRYPTO", "EQUITY", "COMMODITY", "ETF", "FOREX", "BOND"}

DIRECTION_MAP = {
    "LONG": "LONG", "BUY": "LONG", "LONG_BUY": "LONG",
    "SHORT": "SHORT", "SELL": "SHORT", "SHORT_SELL": "SHORT", "SELL_SHORT": "SHORT",
}

ASSET_CLASS_MAP = {
    "STOCKS": "EQUITY", "STOCK": "EQUITY", "EQUITIES": "EQUITY",
}

# Symbols observed in the wrong / inconsistent class. Each maps to the single
# canonical class it belongs in, so the same ticker never lands in two buckets.
#   XLI: industrial sector ETF that was tagged CRYPTO (clear bug)
#   IWM: Russell 2000 ETF (was split EQUITY/ETF)
#   TLT/BND/IEF/SHY: bond proxies the repo tracks under BOND (were split BOND/ETF)
#   *=F: commodity futures fold into the canonical COMMODITY class (were split
#        COMMODITY/FUTURES; FUTURES is not one of the canonical 6)
SYMBOL_CLASS_OVERRIDES = {
    "XLI": "ETF",
    "IWM": "ETF",
    "TLT": "BOND", "BND": "BOND", "IEF": "BOND", "SHY": "BOND",
    "CL=F": "COMMODITY", "NG=F": "COMMODITY", "GC=F": "COMMODITY",
    "SI=F": "COMMODITY", "HG=F": "COMMODITY", "ZS=F": "COMMODITY",
    "ZC=F": "COMMODITY",
}

PERSONA_FALLBACK = "unspecified"


def canon_direction(v: Any) -> str:
    s = str(v or "").strip().upper()
    return DIRECTION_MAP.get(s, s or "LONG")


def canon_asset_class(symbol: Any, asset_class: Any) -> str:
    sym = str(symbol or "").strip().upper()
    if sym in SYMBOL_CLASS_OVERRIDES:
        return SYMBOL_CLASS_OVERRIDES[sym]
    ac = str(asset_class or "").strip().upper()
    return ASSET_CLASS_MAP.get(ac, ac or "EQUITY")


def normalize_pick(p: dict) -> dict:
    """Canonicalize a pick in place and return it."""
    p["direction"] = canon_direction(p.get("direction"))
    p["asset_class"] = canon_asset_class(p.get("symbol"), p.get("asset_class"))
    if not str(p.get("persona_id", "")).strip():
        p["persona_id"] = PERSONA_FALLBACK
    return p


def _parse(ts: Any) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None


def is_timestamp_anomaly(p: dict) -> bool:
    """True when resolved_at predates submitted_at (impossible — corrupt seed row)."""
    sub = _parse(p.get("submitted_at"))
    res = _parse(p.get("resolved_at"))
    return bool(sub and res and res < sub)


def is_tpsl_violation(p: dict) -> bool:
    """True when TP/SL sit on the wrong side of entry for the pick's direction.
    LONG must have TP > entry > SL; SHORT must have TP < entry < SL. Such a pick
    can never resolve as intended, so its WIN/LOSS is meaningless."""
    try:
        e = float(p.get("entry_price"))
        tp = float(p.get("take_profit"))
        sl = float(p.get("stop_loss"))
    except (TypeError, ValueError):
        return False
    if not (e > 0 and tp > 0 and sl > 0):
        return False
    d = canon_direction(p.get("direction"))
    if d == "LONG":
        return not (tp > e > sl)
    if d == "SHORT":
        return not (tp < e < sl)
    return False


def is_resolution_trustworthy(p: dict) -> bool:
    """A resolved pick whose WIN/LOSS can be trusted for leaderboard stats.

    2026-06-04: Picks with status='MISPRICED_ENTRY' are excluded — these are
    picks whose entry_price drifted >25% from the actual market price at
    submission (corporate action / reverse split / contract roll / stale
    AI training data). 553 of 969 audited tournament picks (57.1%) on the
    top 15 models were mispriced this way. Including them produces the
    inflated 87-92% WR figures the audit page showed pre-cleanup. See
    reports/db_wide_mispriced_audit_2026-06-04/summary.json for the audit
    output.
    """
    status = str(p.get("status") or "").upper()
    if status == "MISPRICED_ENTRY":
        return False
    return not (is_timestamp_anomaly(p) or is_tpsl_violation(p))
