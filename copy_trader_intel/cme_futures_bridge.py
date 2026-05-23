#!/usr/bin/env python3
"""
CME Futures Bridge
==================
Thin bridge between the live futures scanner and the non-crypto consensus engine.

PROBLEM IT SOLVES
-----------------
The futures-agent GitHub workflow (.github/workflows/futures-agent.yml) writes its
output to ``non_crypto_agent/data/futures_picks.json``, but the consensus engine
(copy_trader_intel/non_crypto_consensus.py, source 6) reads a DIFFERENT file:
``copy_trader_intel/data/futures_copytrader_picks.json`` — historically a stale
empty ``[]``. The two files never met, so FUTURES emitted 0 active picks.

This module is NOT a scanner. It reads the live scanner output, normalizes each
pick to the schema ``non_crypto_consensus.py`` expects (symbol / signal_type /
direction / confidence / asset_class / strategy / source_system), and writes the
file the consensus engine actually loads — atomically.

STALE-GUARD: if the source file is >48h old, an empty list is written instead of
propagating dead data.
"""

import json
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[cme_futures_bridge] %(message)s")

# Source: live futures scanner output (written by .github/workflows/futures-agent.yml)
SOURCE_PATH = (
    Path(__file__).resolve().parent.parent
    / "non_crypto_agent" / "data" / "futures_picks.json"
)
# Destination: file the non-crypto consensus engine reads (source 6, line ~294)
DEST_PATH = Path(__file__).resolve().parent / "data" / "futures_copytrader_picks.json"

# Pick is considered dead if the source file's mtime is older than this.
STALE_AFTER_SECONDS = 48 * 3600


def _atomic_write_json(path: Path, payload) -> None:
    """Write JSON atomically: temp file in the SAME directory + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2, default=str)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _extract_picks(data) -> list:
    """Accept both shapes: a top-level list OR {"picks": [...]}."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        picks = data.get("picks", [])
        return picks if isinstance(picks, list) else []
    return []


def _normalize(pick: dict) -> dict | None:
    """
    Normalize a scanner pick to the consensus schema.

    Required: symbol, direction (signal_type/direction), confidence — else drop.
    Defaults: asset_class -> "FUTURES", source_system -> "futures_tsmom_elite".
    """
    if not isinstance(pick, dict):
        logger.warning("Dropping non-dict pick: %r", pick)
        return None

    symbol = str(pick.get("symbol", "")).strip()
    direction = str(
        pick.get("signal_type", pick.get("direction", ""))
    ).strip().upper()
    confidence = pick.get("confidence", None)

    if not symbol:
        logger.warning("Dropping pick missing symbol: %r", pick)
        return None
    if direction not in ("BUY", "SELL", "LONG", "SHORT"):
        logger.warning("Dropping pick %s with invalid direction: %r", symbol, direction)
        return None
    if confidence is None:
        logger.warning("Dropping pick %s missing confidence", symbol)
        return None
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        logger.warning("Dropping pick %s with non-numeric confidence: %r", symbol, confidence)
        return None

    # Normalize direction to the BUY/SELL vocabulary consensus_vote() votes on.
    signal_type = "BUY" if direction in ("BUY", "LONG") else "SELL"

    normalized = dict(pick)
    normalized["symbol"] = symbol
    normalized["signal_type"] = signal_type
    normalized["direction"] = "LONG" if signal_type == "BUY" else "SHORT"
    normalized["confidence"] = confidence
    normalized["asset_class"] = str(pick.get("asset_class") or "FUTURES").upper()
    normalized.setdefault("category", "futures")
    normalized["source_system"] = "futures_tsmom_elite"
    normalized.setdefault("strategy", pick.get("strategy", "futures_tsmom_elite"))
    return normalized


def bridge_futures_picks(
    source_path: Path = SOURCE_PATH,
    dest_path: Path = DEST_PATH,
) -> list:
    """
    Read live futures scanner output, normalize, and write the consensus-side file
    atomically. Returns the list of normalized picks (possibly empty).

    Never raises on bad/missing/stale input — writes an empty list and warns.
    """
    source_path = Path(source_path)
    dest_path = Path(dest_path)
    generated_at = datetime.now(timezone.utc).isoformat()

    def _emit(picks: list) -> list:
        _atomic_write_json(
            dest_path,
            {"generated_at": generated_at, "source": str(source_path), "picks": picks},
        )
        return picks

    # Missing source — emit [] and warn, do not raise.
    if not source_path.exists():
        logger.warning("Source file missing (%s) — emitting empty picks", source_path)
        return _emit([])

    # Stale-guard — do not propagate dead data.
    try:
        age = time.time() - source_path.stat().st_mtime
    except OSError as e:
        logger.warning("Cannot stat source file (%s): %s — emitting empty picks", source_path, e)
        return _emit([])
    if age > STALE_AFTER_SECONDS:
        logger.warning(
            "Source file is stale (%.1fh old > 48h) — emitting empty picks",
            age / 3600.0,
        )
        return _emit([])

    # Parse — malformed JSON emits [] and warns.
    try:
        with open(source_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Malformed JSON in source file (%s): %s — emitting empty picks", source_path, e)
        return _emit([])
    except OSError as e:
        logger.warning("Cannot read source file (%s): %s — emitting empty picks", source_path, e)
        return _emit([])

    raw_picks = _extract_picks(data)
    normalized = []
    for p in raw_picks:
        n = _normalize(p)
        if n is not None:
            normalized.append(n)

    logger.info(
        "Bridged %d/%d futures picks -> %s", len(normalized), len(raw_picks), dest_path
    )
    return _emit(normalized)


# Convenience alias per spec.
def run(*args, **kwargs) -> list:
    """Alias for bridge_futures_picks()."""
    return bridge_futures_picks(*args, **kwargs)


if __name__ == "__main__":
    result = run()
    print(f"cme_futures_bridge: wrote {len(result)} picks to {DEST_PATH}")
