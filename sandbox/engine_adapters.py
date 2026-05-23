"""Engine adapters — normalize picks from 5 sources into NormalizedPick."""

import json
import logging
from pathlib import Path
from typing import List

from sandbox.config import ENGINE_SOURCES, EXCLUDED_SYMBOLS
from sandbox.core import (
    NormalizedPick,
    normalize_symbol,
    flip_direction,
    flip_tp_sl,
    default_tp_sl,
    make_pick_id,
    utc_now,
    expiration_from,
)

log = logging.getLogger(__name__)


def _read_json(path: Path):
    """Safely read a JSON file, return empty list/dict on error."""
    if not path.is_file():
        log.warning("Source file not found: %s", path)
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.error("Failed to read %s: %s", path, exc)
        return []


# ── Predictions Dashboard ───────────────────────────────────────────

def _adapt_predictions() -> List[NormalizedPick]:
    """Flip picks from predictions/data/active_predictions.json.

    Fields: symbol, direction (LONG/SHORT), entry_price, take_profit, stop_loss,
            id, scraped_at, predictor_id
    """
    data = _read_json(ENGINE_SOURCES["predictions"])
    if not isinstance(data, list):
        return []

    seen = set()
    picks = []
    for p in data:
        try:
            sym = normalize_symbol(p.get("symbol", ""))
            if sym in EXCLUDED_SYMBOLS:
                continue
            orig_dir = p.get("direction", "").upper()
            if not orig_dir or orig_dir not in ("LONG", "SHORT"):
                continue

            dedup_key = f"{sym}_{orig_dir}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            entry = float(p["entry_price"])
            tp = float(p.get("take_profit") or 0)
            sl = float(p.get("stop_loss") or 0)
            if tp == 0 or sl == 0:
                tp, sl = default_tp_sl(entry, orig_dir)

            opp_dir = flip_direction(orig_dir)
            opp_tp, opp_sl = flip_tp_sl(entry, tp, sl, orig_dir)
            ts = p.get("scraped_at", utc_now())
            pick_id = make_pick_id("predictions", sym, opp_dir, ts)

            picks.append(NormalizedPick(
                symbol=sym,
                original_direction=orig_dir,
                opposite_direction=opp_dir,
                entry_price=entry,
                original_tp=tp,
                original_sl=sl,
                opposite_tp=opp_tp,
                opposite_sl=opp_sl,
                source_engine="predictions",
                source_pick_id=pick_id,
                picked_at=ts,
                expiration_at=expiration_from(ts),
                confidence=float(p.get("sentiment_score", 0)),
            ))
        except Exception as exc:
            log.warning("Predictions adapter skip: %s", exc)
    return picks


# ── KIMI Rise of the Claw ──────────────────────────────────────────

def _adapt_kimi() -> List[NormalizedPick]:
    """Flip picks from KIMI_RISEOFTHECLAW/data/live_signals_now.json.

    Top-level: {crypto_signals: [{symbol, signal (BUY/SELL), entryPrice,
                targetPrice, stopPrice, confidence, algorithm, timestamp}]}
    """
    raw = _read_json(ENGINE_SOURCES["kimi"])
    if isinstance(raw, dict):
        data = raw.get("crypto_signals", [])
    else:
        data = raw

    seen = set()
    picks = []
    for p in data:
        try:
            sym = normalize_symbol(p.get("symbol", ""))
            if sym in EXCLUDED_SYMBOLS:
                continue
            signal = p.get("signal", "").upper()
            orig_dir = "LONG" if signal == "BUY" else "SHORT"

            dedup_key = f"{sym}_{orig_dir}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            entry = float(p.get("entryPrice") or p.get("price", 0))
            if entry <= 0:
                continue
            tp = float(p.get("targetPrice") or p.get("take_profit") or 0)
            sl = float(p.get("stopPrice") or p.get("stop_loss") or 0)
            if tp == 0 or sl == 0:
                tp, sl = default_tp_sl(entry, orig_dir)

            opp_dir = flip_direction(orig_dir)
            opp_tp, opp_sl = flip_tp_sl(entry, tp, sl, orig_dir)
            ts = p.get("timestamp", utc_now())
            pick_id = make_pick_id("kimi", sym, opp_dir, ts)

            conf_raw = float(p.get("confidence", 0))
            confidence = conf_raw / 100 if conf_raw > 1 else conf_raw

            picks.append(NormalizedPick(
                symbol=sym,
                original_direction=orig_dir,
                opposite_direction=opp_dir,
                entry_price=entry,
                original_tp=tp,
                original_sl=sl,
                opposite_tp=opp_tp,
                opposite_sl=opp_sl,
                source_engine="kimi",
                source_pick_id=pick_id,
                picked_at=ts,
                expiration_at=expiration_from(ts),
                confidence=confidence,
            ))
        except Exception as exc:
            log.warning("KIMI adapter skip: %s", exc)
    return picks


# ── Alpha Engine ────────────────────────────────────────────────────

def _adapt_alpha() -> List[NormalizedPick]:
    """Flip picks from alpha_engine/data/active_picks.json.

    Fields: id, symbol (BTC-USD), direction (LONG/SHORT), entry_price,
            take_profit, stop_loss, confidence, timestamp, strategy
    """
    data = _read_json(ENGINE_SOURCES["alpha"])
    if not isinstance(data, list):
        return []

    picks = []
    for p in data:
        try:
            sym = normalize_symbol(p.get("symbol", ""))
            if sym in EXCLUDED_SYMBOLS:
                continue
            orig_dir = p.get("direction", "").upper()
            if not orig_dir or orig_dir not in ("LONG", "SHORT"):
                continue

            entry = float(p["entry_price"])
            tp = float(p.get("take_profit") or 0)
            sl = float(p.get("stop_loss") or 0)
            if tp == 0 or sl == 0:
                tp, sl = default_tp_sl(entry, orig_dir)

            opp_dir = flip_direction(orig_dir)
            opp_tp, opp_sl = flip_tp_sl(entry, tp, sl, orig_dir)
            ts = p.get("timestamp", utc_now())
            source_id = p.get("id", make_pick_id("alpha", sym, opp_dir, ts))
            pick_id = f"opp::alpha::{source_id}"

            picks.append(NormalizedPick(
                symbol=sym,
                original_direction=orig_dir,
                opposite_direction=opp_dir,
                entry_price=entry,
                original_tp=tp,
                original_sl=sl,
                opposite_tp=opp_tp,
                opposite_sl=opp_sl,
                source_engine="alpha",
                source_pick_id=pick_id,
                picked_at=ts,
                expiration_at=expiration_from(ts),
                confidence=float(p.get("confidence", 0)),
            ))
        except Exception as exc:
            log.warning("Alpha adapter skip: %s", exc)
    return picks


# ── Signal Engine ───────────────────────────────────────────────────

def _adapt_signal_engine() -> List[NormalizedPick]:
    """Flip picks from crypto_signal_engine/data/active_picks.json.

    Fields: symbol (BTCUSDT), signal (LONG/SHORT), entry, tp, sl,
            confidence, timestamp
    """
    data = _read_json(ENGINE_SOURCES["signal_engine"])
    if not isinstance(data, list):
        return []

    picks = []
    for p in data:
        try:
            sym = normalize_symbol(p.get("symbol", ""))
            if sym in EXCLUDED_SYMBOLS:
                continue
            orig_dir = p.get("signal", "").upper()
            if orig_dir == "BUY":
                orig_dir = "LONG"
            elif orig_dir == "SELL":
                orig_dir = "SHORT"
            if orig_dir not in ("LONG", "SHORT"):
                continue

            entry = float(p.get("entry", 0))
            if entry <= 0:
                continue
            tp = float(p.get("tp") or 0)
            sl = float(p.get("sl") or 0)
            if tp == 0 or sl == 0:
                tp, sl = default_tp_sl(entry, orig_dir)

            opp_dir = flip_direction(orig_dir)
            opp_tp, opp_sl = flip_tp_sl(entry, tp, sl, orig_dir)
            ts = p.get("timestamp", utc_now())
            pick_id = make_pick_id("signal_engine", sym, opp_dir, ts)

            picks.append(NormalizedPick(
                symbol=sym,
                original_direction=orig_dir,
                opposite_direction=opp_dir,
                entry_price=entry,
                original_tp=tp,
                original_sl=sl,
                opposite_tp=opp_tp,
                opposite_sl=opp_sl,
                source_engine="signal_engine",
                source_pick_id=pick_id,
                picked_at=ts,
                expiration_at=expiration_from(ts),
                confidence=float(p.get("confidence", 0)),
            ))
        except Exception as exc:
            log.warning("Signal Engine adapter skip: %s", exc)
    return picks


# ── Cross-Aggregator ────────────────────────────────────────────────

def _adapt_cross_aggregator() -> List[NormalizedPick]:
    """Flip picks from cross_aggregation/data/super_signals.json.

    Top-level: {super_signals: [{symbol (BTCUSDT), direction (LONG/SHORT),
                entry_price, take_profit, stop_loss, confidence,
                agreeing_systems, agreement_count, signal_tier}]}
    """
    raw = _read_json(ENGINE_SOURCES["cross_aggregator"])
    if isinstance(raw, dict):
        data = raw.get("super_signals", [])
    else:
        data = raw

    picks = []
    for p in data:
        try:
            sym = normalize_symbol(p.get("symbol", ""))
            if sym in EXCLUDED_SYMBOLS:
                continue
            orig_dir = p.get("direction", "").upper()
            if orig_dir not in ("LONG", "SHORT"):
                continue

            entry = float(p["entry_price"])
            tp = float(p.get("take_profit") or 0)
            sl = float(p.get("stop_loss") or 0)
            if tp == 0 or sl == 0:
                tp, sl = default_tp_sl(entry, orig_dir)

            opp_dir = flip_direction(orig_dir)
            opp_tp, opp_sl = flip_tp_sl(entry, tp, sl, orig_dir)
            ts = utc_now()
            pick_id = make_pick_id("cross_aggregator", sym, opp_dir, ts)

            picks.append(NormalizedPick(
                symbol=sym,
                original_direction=orig_dir,
                opposite_direction=opp_dir,
                entry_price=entry,
                original_tp=tp,
                original_sl=sl,
                opposite_tp=opp_tp,
                opposite_sl=opp_sl,
                source_engine="cross_aggregator",
                source_pick_id=pick_id,
                picked_at=ts,
                expiration_at=expiration_from(ts),
                confidence=float(p.get("confidence", 0)),
            ))
        except Exception as exc:
            log.warning("Cross-Aggregator adapter skip: %s", exc)
    return picks


# ── Public API ──────────────────────────────────────────────────────

ADAPTERS = {
    "predictions": _adapt_predictions,
    "kimi": _adapt_kimi,
    "alpha": _adapt_alpha,
    "signal_engine": _adapt_signal_engine,
    "cross_aggregator": _adapt_cross_aggregator,
}


def fetch_all_opposite_picks() -> List[NormalizedPick]:
    """Run all adapters and return combined opposite picks."""
    all_picks = []
    for name, adapter_fn in ADAPTERS.items():
        try:
            picks = adapter_fn()
            log.info("  %s: %d opposite picks", name, len(picks))
            all_picks.extend(picks)
        except Exception as exc:
            log.error("Adapter %s failed entirely: %s", name, exc)
    return all_picks
