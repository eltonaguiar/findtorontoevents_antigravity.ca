#!/usr/bin/env python3
"""
merge_top_gainers.py — Merge top-gainers scanner picks into the audit dashboard.

Loads STOCKS/scanners/data/top_gainers_picks.json, stamps hf_conviction_tier,
skips already-closed picks, then upserts into
audit_dashboard/data/top_gainers_active_picks.json.

Run as a step in audit-dashboard.yml before stamp-pick-quality.
Non-fatal: exits cleanly even if source file is missing or empty.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
SRC = ROOT / "STOCKS" / "scanners" / "data" / "top_gainers_picks.json"
DEST = ROOT / "audit_dashboard" / "data" / "top_gainers_active_picks.json"
FORWARD_PICKS = ROOT / "STOCKS" / "competition" / "forward_picks.json"

SOURCE_SYSTEM = "top_gainers_scanner"


def _load_json(path: Path) -> dict | list | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _conviction_tier(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    return None


def _closed_symbols() -> set[str]:
    """Return set of ticker symbols that are already closed in forward_picks."""
    data = _load_json(FORWARD_PICKS)
    if not data:
        return set()
    picks = data.get("picks", []) if isinstance(data, dict) else data
    closed = set()
    for p in picks:
        status = str(p.get("status", "") or "").upper()
        outcome = str(p.get("outcome", "") or "").upper()
        if status == "CLOSED" or outcome in ("TP_HIT", "SL_HIT", "CLOSED", "EXPIRED"):
            sym = p.get("ticker") or p.get("symbol") or ""
            if sym:
                closed.add(str(sym).upper())
    return closed


def _normalize_pick(raw: dict, closed_syms: set[str]) -> dict | None:
    symbol = str(raw.get("symbol") or raw.get("ticker") or "").upper()
    if not symbol:
        return None
    if symbol in closed_syms:
        return None

    score = raw.get("score") or raw.get("ml_score") or raw.get("confidence")
    if score is not None:
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = None

    # Normalise confidence: score may be 0-100 or 0-1
    confidence = score
    if confidence is not None and confidence > 1.0:
        confidence = confidence / 100.0

    now_iso = datetime.now(timezone.utc).isoformat()

    return {
        "symbol": symbol,
        "ticker": symbol,
        "direction": str(raw.get("direction") or raw.get("signal_type") or "LONG").upper(),
        "signal_type": str(raw.get("signal_type") or ("BUY" if (raw.get("direction", "LONG") or "LONG").upper() == "LONG" else "SELL")),
        "entry_price": float(raw.get("entry_price") or raw.get("price") or 0),
        "take_profit": float(raw.get("take_profit") or raw.get("tp_price") or 0),
        "stop_loss": float(raw.get("stop_loss") or raw.get("sl_price") or 0),
        "confidence": round(confidence, 4) if confidence is not None else 0.5,
        "score": score,
        "ml_score": score,
        "hf_conviction_tier": _conviction_tier(score),
        "strategy": str(raw.get("strategy") or raw.get("algorithm") or "top_gainers"),
        "source_system": SOURCE_SYSTEM,
        "asset_class": str(raw.get("asset_class") or "stocks"),
        "category": str(raw.get("category") or "stocks"),
        "status": "OPEN",
        "outcome": "PENDING",
        "pnl_pct": 0.0,
        "rationale": str(raw.get("rationale") or raw.get("reason") or ""),
        "generated_at": str(raw.get("generated_at") or now_iso),
        "ingested_at": now_iso,
    }


def main() -> int:
    raw_data = _load_json(SRC)
    if not raw_data:
        print(f"[merge_top_gainers] Source file missing or empty: {SRC} — skipping.")
        return 0

    raw_picks = raw_data.get("picks", []) if isinstance(raw_data, dict) else raw_data
    if not raw_picks:
        print("[merge_top_gainers] No picks in source file — skipping.")
        return 0

    closed_syms = _closed_symbols()
    print(f"[merge_top_gainers] Closed symbols to skip: {len(closed_syms)}")

    new_picks: list[dict] = []
    skipped = 0
    for raw in raw_picks:
        pick = _normalize_pick(raw, closed_syms)
        if pick is None:
            skipped += 1
            continue
        new_picks.append(pick)

    print(f"[merge_top_gainers] Processed {len(raw_picks)} picks → {len(new_picks)} valid, {skipped} skipped.")

    # Load existing dest file and upsert by symbol+direction
    existing: list[dict] = []
    if DEST.exists():
        existing_data = _load_json(DEST)
        if isinstance(existing_data, list):
            existing = existing_data
        elif isinstance(existing_data, dict):
            existing = existing_data.get("picks", [])

    # Build lookup by symbol+direction for upsert
    key_map: dict[str, int] = {}
    for i, p in enumerate(existing):
        k = f"{p.get('symbol','').upper()}|{p.get('direction','LONG').upper()}"
        key_map[k] = i

    added = updated = 0
    for pick in new_picks:
        k = f"{pick['symbol']}|{pick['direction']}"
        if k in key_map:
            existing[key_map[k]] = pick
            updated += 1
        else:
            existing.append(pick)
            key_map[k] = len(existing) - 1
            added += 1

    DEST.parent.mkdir(parents=True, exist_ok=True)
    with open(DEST, "w", encoding="utf-8") as fh:
        json.dump(existing, fh, indent=2)

    print(f"[merge_top_gainers] Saved {len(existing)} picks to {DEST} (+{added} new, {updated} updated).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
