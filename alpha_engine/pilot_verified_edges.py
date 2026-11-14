#!/usr/bin/env python3
"""
Pilot Verified Edges Pipeline

Emits picks from 3 verified profitable edges that are currently blocked
by outdated kill lists. Runs in SHADOW MODE by default (logs only, no
live emission). Set PILOT_LIVE=1 to emit to dashboard.

Verified edges (audit 2026-11-14):
  1. quan_engine: 95.8% WR, +669% PnL, 284 trades
  2. st_rsi_momentum_confluence: 65.1% WR, PF 2.53, 258 trades
  3. SHORT direction bias: 72.0% WR vs LONG 20.3%

Usage:
    python3 alpha_engine/pilot_verified_edges.py           # shadow mode
    PILOT_LIVE=1 python3 alpha_engine/pilot_verified_edges.py  # live emit
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("pilot_verified_edges")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PILOT_LIVE = os.environ.get("PILOT_LIVE", "").strip().lower() in ("1", "true", "yes")
SHADOW_TAG = "pilot_verified_edge"

# Verified edges — source_system or strategy names
VERIFIED_SOURCES = {"quan_engine", "st_rsi_momentum_confluence"}
VERIFIED_STRATEGIES = {"quan_engine", "st_rsi_momentum_confluence", "st_rsi_momentum_confluence_symbol_locked"}

# Position sizing: 1% per trade (TradingView real-money standard)
POSITION_SIZE_PCT = 1.0

# Score bucket gate: only emit 40-59 (proven positive expectancy)
SCORE_BUCKET_MIN = 40
SCORE_BUCKET_MAX = 59

# Direction bias: boost SHORT, penalize LONG for CRYPTO
SHORT_BOOST = 1.20
LONG_PENALTY = 0.80

# Output paths
SHADOW_LOG = REPO / "audit_dashboard" / "data" / "pilot_verified_edges_shadow.json"
LIVE_OUTPUT = REPO / "audit_dashboard" / "data" / "pilot_verified_edges.json"


def _load_all_signals() -> list[dict]:
    """Collect signals from all source JSONs."""
    signals = []
    signal_dirs = [
        REPO / "quan_engine" / "data",
        REPO / "predictions" / "data",
        REPO / "alpha_engine" / "data",
    ]
    for d in signal_dirs:
        if not d.exists():
            continue
        for f in d.glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                items = data if isinstance(data, list) else data.get("signals", data.get("active_picks", data.get("picks", [])))
                for item in items:
                    if isinstance(item, dict):
                        item["_source_file"] = str(f.relative_to(REPO))
                        signals.append(item)
            except Exception as exc:
                log.debug("Skip %s: %s", f, exc)
    return signals


def _is_verified_edge(signal: dict) -> bool:
    """Check if signal matches one of the 3 verified edges."""
    source = str(signal.get("source_system", signal.get("source", ""))).lower()
    strategy = str(signal.get("strategy", "")).lower()
    direction = str(signal.get("direction", "LONG")).upper()

    # Edge 1 & 2: verified source/strategy
    if source in VERIFIED_SOURCES or strategy in VERIFIED_STRATEGIES:
        return True

    # Edge 3: SHORT direction bias (any source, but CRYPTO only)
    asset_class = str(signal.get("asset_class", signal.get("category", "CRYPTO"))).upper()
    if direction in ("SHORT", "SELL") and asset_class == "CRYPTO":
        return True

    return False


def _apply_score_bucket_gate(signal: dict) -> dict | None:
    """Only allow score 40-59. Returns modified signal or None."""
    score = signal.get("score", signal.get("elite_score", 0))
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0

    if score < SCORE_BUCKET_MIN or score > SCORE_BUCKET_MAX:
        return None

    signal["_pilot_score_original"] = score
    signal["score"] = score  # keep within bucket
    return signal


def _apply_direction_bias(signal: dict) -> dict:
    """Boost SHORT, penalize LONG for CRYPTO."""
    direction = str(signal.get("direction", "LONG")).upper()
    asset_class = str(signal.get("asset_class", signal.get("category", "CRYPTO"))).upper()

    if asset_class != "CRYPTO":
        return signal

    original_score = float(signal.get("score", 0))
    if direction in ("SHORT", "SELL"):
        signal["score"] = round(original_score * SHORT_BOOST, 2)
        signal["_pilot_direction_boost"] = SHORT_BOOST
    elif direction in ("LONG", "BUY"):
        signal["score"] = round(original_score * LONG_PENALTY, 2)
        signal["_pilot_direction_penalty"] = LONG_PENALTY

    return signal


def _apply_position_sizing(signal: dict) -> dict:
    """Set position size to 1% with ATR-based stop."""
    signal["position_size_pct"] = POSITION_SIZE_PCT
    signal["_pilot_sizing"] = "1pct_atr_based"

    entry = float(signal.get("entry_price", 0) or 0)
    atr = float(signal.get("atr", signal.get("atr_pct", 0)) or 0)

    if entry > 0 and atr > 0:
        # ATR-based stop: 2x ATR for swing trades
        sl_distance = entry * (atr / 100) * 2
        direction = str(signal.get("direction", "LONG")).upper()
        if direction in ("SHORT", "SELL"):
            signal["stop_loss"] = round(entry + sl_distance, 8)
            signal["take_profit"] = round(entry - sl_distance * 1.5, 8)  # 1.5:1 R:R
        else:
            signal["stop_loss"] = round(entry - sl_distance, 8)
            signal["take_profit"] = round(entry + sl_distance * 1.5, 8)
        signal["_pilot_sl_basis"] = "2x_atr"
    else:
        # Fallback: fixed 2% stop, 3% target (1.5:1 R:R)
        if entry > 0:
            direction = str(signal.get("direction", "LONG")).upper()
            if direction in ("SHORT", "SELL"):
                signal["stop_loss"] = round(entry * 1.02, 8)
                signal["take_profit"] = round(entry * 0.97, 8)
            else:
                signal["stop_loss"] = round(entry * 0.98, 8)
                signal["take_profit"] = round(entry * 1.03, 8)
        signal["_pilot_sl_basis"] = "fixed_2pct_fallback"

    return signal


def _tag_pilot(signal: dict) -> dict:
    """Add pilot metadata tags."""
    signal["_pilot_tag"] = SHADOW_TAG
    signal["_pilot_generated_at"] = datetime.now(timezone.utc).isoformat()
    signal["_pilot_version"] = "2026-11-14-v1"
    return signal


def _save_output(picks: list[dict], live: bool = False) -> None:
    """Save picks to shadow or live output."""
    path = LIVE_OUTPUT if live else SHADOW_LOG
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if live else "shadow",
        "pilot_version": "2026-11-14-v1",
        "count": len(picks),
        "edges": list(VERIFIED_SOURCES),
        "picks": picks,
    }

    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    log.info("Saved %d picks to %s (mode=%s)", len(picks), path, payload["mode"])


def main() -> int:
    log.info("Pilot Verified Edges Pipeline starting (live=%s)", PILOT_LIVE)

    signals = _load_all_signals()
    log.info("Loaded %d total signals from all sources", len(signals))

    pilot_picks = []
    stats = {"verified_edge": 0, "score_bucket_rejected": 0, "direction_boosted": 0, "direction_penalized": 0}

    for sig in signals:
        if not _is_verified_edge(sig):
            continue
        stats["verified_edge"] += 1

        sig = _apply_score_bucket_gate(sig)
        if sig is None:
            stats["score_bucket_rejected"] += 1
            continue

        sig = _apply_direction_bias(sig)
        if "_pilot_direction_boost" in sig:
            stats["direction_boosted"] += 1
        elif "_pilot_direction_penalty" in sig:
            stats["direction_penalized"] += 1

        sig = _apply_position_sizing(sig)
        sig = _tag_pilot(sig)
        pilot_picks.append(sig)

    log.info(
        "Pilot stats: verified=%d, score_rejected=%d, boosted=%d, penalized=%d, final=%d",
        stats["verified_edge"],
        stats["score_bucket_rejected"],
        stats["direction_boosted"],
        stats["direction_penalized"],
        len(pilot_picks),
    )

    _save_output(pilot_picks, live=PILOT_LIVE)

    if not PILOT_LIVE:
        log.info("SHADOW MODE — no live emission. Set PILOT_LIVE=1 to emit.")
    else:
        log.info("LIVE MODE — %d picks emitted to dashboard", len(pilot_picks))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
