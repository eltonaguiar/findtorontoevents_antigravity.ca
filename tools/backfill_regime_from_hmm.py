#!/usr/bin/env python3
"""Regime backfill — tag closed_picks.json with per-symbol regime from hmm_regime.json.

Reads ``alpha_engine/data/hmm_regime.json`` (43 symbols, per-symbol regime labels
from the regime_terminal Gaussian HMM) and stamps the ``regime`` field on every
closed pick whose symbol maps to a known HMM-regime symbol.

Symbol mapping:
  - Crypto:   ``BTC-USD`` <-> ``BTCUSDT``  (strip dash, replace USD->USDT)
  - Forex:    ``EURUSD=X`` <-> ``EURUSD``  (strip =X suffix)
  - Stocks:   ``AAPL`` <-> ``AAPL``       (identical)

The regime assigned is the HMM's *current* regime for that symbol — an
approximation for the resolve-date regime. Not perfect, but it unblocks the
``evaluate_by_regime()`` gate in ``edge_stability_harness.py`` so the
regime-conditional harness can produce its first real verdict.

Usage:
    python tools/backfill_regime_from_hmm.py [--dry-run]
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HMM_REGIME = ROOT / "alpha_engine" / "data" / "hmm_regime.json"
CLOSED = ROOT / "alpha_engine" / "data" / "closed_picks.json"
ACTIVE = ROOT / "alpha_engine" / "data" / "active_picks.json"
BACKUP_SUFFIX = ".bak.hmm_regime_backfill"


def _load_hmm() -> dict[str, dict]:
    """Load hmm_regime.json and return {normalized_symbol: regime_info}."""
    if not HMM_REGIME.exists():
        print(f"ERROR: {HMM_REGIME} not found — run regime_terminal first")
        sys.exit(1)

    with open(HMM_REGIME, "r", encoding="utf-8") as f:
        doc = json.load(f)

    per_symbol = doc.get("per_symbol", {})
    mapped: dict[str, dict] = {}
    for hmm_sym, info in per_symbol.items():
        norm = _normalize_hmm_symbol(hmm_sym)
        mapped[norm] = {
            "regime": info.get("regime", "Chop/Neutral"),
            "alpha_regime": info.get("alpha_regime", "ranging"),
            "confidence": info.get("confidence", 0.5),
            "signal": info.get("signal", "FLAT"),
            "hmm_symbol": hmm_sym,
        }
    return mapped


def _normalize_hmm_symbol(hmm_sym: str) -> str:
    """Convert hmm_regime symbol to closed_picks symbol format.

    "BTC-USD"   -> "BTCUSDT"
    "EURUSD=X"  -> "EURUSD"
    "AAPL"      -> "AAPL"
    """
    s = hmm_sym.upper().strip()
    # Forex: "EURUSD=X" -> "EURUSD"
    if s.endswith("=X"):
        return s[:-2]
    # Crypto: "BTC-USD" -> "BTCUSDT"
    if "-USD" in s:
        return s.replace("-USD", "USDT")
    return s


def _normalize_pick_symbol(pick_sym: str) -> str:
    """Normalize closed_picks symbol for matching.

    "BTCUSDT" -> "BTCUSDT" (already normalized)
    Some picks may have suffixes like "USDT.P" or ".P" — strip those.
    """
    s = pick_sym.upper().strip()
    # Remove common suffixes
    for suffix in (".P", ".OQ", "_P", "-P"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s


LEVERAGED_TOKENS = {"DOWN", "UP", "BEAR", "BULL"}


def _is_leveraged(sym: str) -> bool:
    """Heuristic: detect leveraged token suffixes in a symbol."""
    for suffix in ("3L", "3S", "2L", "2S", "5L", "5S"):
        if sym.endswith(suffix):
            return True
    return any(tag in sym for tag in LEVERAGED_TOKENS)


def backfill_closed(hmm_map: dict, dry_run: bool = False) -> dict:
    """Tag closed_picks.json with per-symbol regime labels."""
    if not CLOSED.exists():
        print(f"SKIP: {CLOSED} not found")
        return {"total": 0, "tagged": 0, "skipped": 0, "unmatched": 0}

    with open(CLOSED, "r", encoding="utf-8") as f:
        picks = json.load(f)

    tagged = 0
    skipped = 0
    unmatched = 0
    uses_fallback = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for p in picks:
        # Skip if already has a regime
        existing = p.get("regime") or p.get("_regime") or p.get("regime_label")
        if existing:
            skipped += 1
            continue

        sym = _normalize_pick_symbol(p.get("symbol", ""))
        if not sym:
            unmatched += 1
            continue

        hmm_info = hmm_map.get(sym)
        if hmm_info:
            p["regime"] = hmm_info["regime"]
            p["alpha_regime"] = hmm_info["alpha_regime"]
            p["regime_confidence"] = hmm_info["confidence"]
            p["regime_source"] = f"hmm_backfill_{today}"
            p["hmm_symbol"] = hmm_info["hmm_symbol"]
            tagged += 1
        else:
            # Try partial match: only if hmm_norm is >=4 chars and the
            # symbol is not a leveraged token (e.g., BTCDOWNUSDT != BTC)
            if _is_leveraged(sym):
                unmatched += 1
                continue
            matched = False
            for hmm_norm, info in hmm_map.items():
                if len(hmm_norm) >= 4 and (hmm_norm in sym or sym in hmm_norm):
                    p["regime"] = info["regime"]
                    p["alpha_regime"] = info["alpha_regime"]
                    p["regime_confidence"] = info["confidence"]
                    p["regime_source"] = f"hmm_partial_match_{today}"
                    p["hmm_symbol"] = info["hmm_symbol"]
                    tagged += 1
                    uses_fallback += 1
                    matched = True
                    break
            if not matched:
                unmatched += 1

    print(
        f"[closed_picks.json] Tagged: {tagged}"
        f" (partial: {uses_fallback})"
        f" | Already had: {skipped}"
        f" | Unmatched: {unmatched}"
        f" | Total: {len(picks)}"
    )

    if dry_run:
        print("  [dry-run] No changes written.")
        return {
            "total": len(picks), "tagged": tagged,
            "skipped": skipped, "unmatched": unmatched,
        }

    # Atomic write
    backup = CLOSED.with_suffix(CLOSED.suffix + BACKUP_SUFFIX)
    shutil.copy2(CLOSED, backup)
    print(f"  Backup: {backup}")

    tmp = CLOSED.with_suffix(".tmp.hmm_regime_backfill.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, ensure_ascii=False)
    shutil.move(str(tmp), str(CLOSED))
    print(f"  Written: {CLOSED}")

    return {
        "total": len(picks), "tagged": tagged,
        "skipped": skipped, "unmatched": unmatched,
    }


def backfill_active(hmm_map: dict, dry_run: bool = False) -> dict:
    """Tag active_picks.json with per-symbol regime labels (same logic)."""
    if not ACTIVE.exists():
        print(f"SKIP: {ACTIVE} not found")
        return {"total": 0, "tagged": 0, "skipped": 0, "unmatched": 0}

    with open(ACTIVE, "r", encoding="utf-8") as f:
        picks = json.load(f)

    tagged = 0
    skipped = 0
    unmatched = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for p in picks:
        existing = p.get("regime") or p.get("_regime") or p.get("regime_label")
        if existing:
            skipped += 1
            continue

        sym = _normalize_pick_symbol(p.get("symbol", ""))
        if not sym:
            unmatched += 1
            continue
        hmm_info = hmm_map.get(sym)
        if hmm_info:
            p["regime"] = hmm_info["regime"]
            p["alpha_regime"] = hmm_info["alpha_regime"]
            p["regime_source"] = f"hmm_backfill_{today}"
            tagged += 1
        elif not _is_leveraged(sym):
            # Partial match for active picks too (consistent with closed)
            matched = False
            for hmm_norm, info in hmm_map.items():
                if len(hmm_norm) >= 4 and (hmm_norm in sym or sym in hmm_norm):
                    p["regime"] = info["regime"]
                    p["alpha_regime"] = info["alpha_regime"]
                    p["regime_source"] = f"hmm_partial_match_{today}"
                    tagged += 1
                    matched = True
                    break
            if not matched:
                unmatched += 1
        else:
            unmatched += 1

    print(
        f"[active_picks.json] Tagged: {tagged}"
        f" | Already had: {skipped}"
        f" | Unmatched: {unmatched}"
        f" | Total: {len(picks)}"
    )

    if dry_run:
        print("  [dry-run] No changes written.")
        return {
            "total": len(picks), "tagged": tagged,
            "skipped": skipped, "unmatched": unmatched,
        }

    backup = ACTIVE.with_suffix(ACTIVE.suffix + BACKUP_SUFFIX)
    shutil.copy2(ACTIVE, backup)
    tmp = ACTIVE.with_suffix(".tmp.hmm_regime_backfill.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, ensure_ascii=False)
    shutil.move(str(tmp), str(ACTIVE))
    print(f"  Written: {ACTIVE}")

    return {
        "total": len(picks), "tagged": tagged,
        "skipped": skipped, "unmatched": unmatched,
    }


def main():
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    print("=" * 60)
    print("  REGIME BACKFILL — hmm_regime.json -> closed/active picks")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    if dry_run:
        print("  MODE: DRY RUN (no writes)")
    print("=" * 60)

    hmm_map = _load_hmm()
    hmm_regimes = set(v["regime"] for v in hmm_map.values())
    print(f"\nLoaded {len(hmm_map)} symbols from hmm_regime.json")
    print(f"  Regimes present: {sorted(hmm_regimes)}")

    print("\n[1/2] Closed picks...")
    closed_stats = backfill_closed(hmm_map, dry_run)

    print("\n[2/2] Active picks...")
    active_stats = backfill_active(hmm_map, dry_run)

    print("\n" + "=" * 60)
    print(f"  BACKFILL COMPLETE{' (dry run)' if dry_run else ''}")
    print(f"  Closed: {closed_stats}")
    print(f"  Active: {active_stats}")
    print("=" * 60)


if __name__ == "__main__":
    main()
