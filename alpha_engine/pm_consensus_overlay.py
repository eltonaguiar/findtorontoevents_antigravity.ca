"""
PM Consensus Overlay — Kalshi + Polymarket Strict Pairwise Agreement
=====================================================================

Purpose
-------
Augment `st_fear_greed_contrarian` (and other sentiment strategies) with a
real-money cross-platform overlay: emit a NEW pick only when BOTH Kalshi and
Polymarket agree on (symbol, direction). This is intentionally distinct from
`alpha_engine/prediction_market_consensus.py`, which is a 3-source weighted
voting aggregator (wallet copy + polymarket + kalshi) with a min-2-categories
gate and a continuous score-gap rule.

Differences vs prediction_market_consensus.py
---------------------------------------------
- Strict pairwise: requires BOTH platforms (no wallet-copy substitute).
- Alignment boost: 1.2x multiplier when both sides report >0.7 confidence.
- Disagreement tracking: emits NEUTRAL/zero-signal when sides disagree on a
  symbol (logged to `_pm_disagreement_history` for later analysis).
- Stale guard: 4h freshness check on each source's `updated_at`.
- Rollback: env `PM_CONSENSUS_OVERLAY_DISABLED=1` returns [].

Wire-in plan (opt-in sidecar — NOT wired this PR)
-------------------------------------------------
Target: register in `audit_trail/dashboard_generator.py` JSON_PICK_SOURCES,
inserted after the existing tradingagents/skyrocket entries:

    JSON_PICK_SOURCES = [
        ...
        ("pm_consensus_overlay", "alpha_engine/data/pm_consensus_overlay_picks.json"),
        ...
    ]

The overlay should write its emitted picks to that path via `_dump_overlay()`
once the registration is opened in a follow-up PR. Until then, this is a pure
sidecar — no production caller. Per CLAUDE.md Wire-Up Rule.

Schema of emitted pick
----------------------
    {
      "id":            "pm_overlay_<SYMBOL>_<L|S>_<YYYYMMDDHHMM>",
      "strategy":      "pm_consensus_overlay",
      "source_system": "pm_consensus",
      "symbol":        "<SYMBOL>",
      "category":      "<crypto|equity|commodity|forex|macro>",
      "direction":     "LONG" | "SHORT",
      "signal_type":   "BUY" | "SELL",
      "confidence":    float (0..0.95),
      "entry_price":   float | None,
      "take_profit":   float | None,
      "stop_loss":     float | None,
      "status":        "OPEN" | "SIGNAL",
      "type_label":    "🔮 PM Overlay",
      "created_at":    ISO8601 UTC,
      "pm_consensus_data": {
        "kalshi_pick_id":      str,
        "polymarket_pick_id":  str,
        "kalshi_confidence":   float,
        "polymarket_confidence": float,
        "alignment_boost":     1.0 | 1.2,
        "consensus_confidence": float,
        "kalshi_updated_at":   str,
        "polymarket_updated_at": str,
      },
      "reason": "Kalshi+Polymarket agree LONG BTCUSDT (k=0.62, p=0.90)",
    }
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
POLYMARKET_FILE = DATA_DIR / "polymarket_signals.json"
KALSHI_FILE = DATA_DIR / "kalshi_signals.json"

STALE_HOURS = 4
ALIGNMENT_HIGH_CONF_THRESHOLD = 0.70
ALIGNMENT_BOOST = 1.20
MAX_CONFIDENCE = 0.95
ROLLBACK_ENV = "PM_CONSENSUS_OVERLAY_DISABLED"

# Module-level disagreement log (in-memory ring; bounded to last 256 events).
_pm_disagreement_history: list[dict[str, Any]] = []
_DISAGREEMENT_MAX = 256


def _normalize_direction(pick: dict[str, Any]) -> str | None:
    raw = str(pick.get("direction", pick.get("signal_type", ""))).upper()
    if raw in ("BUY", "LONG"):
        return "LONG"
    if raw in ("SELL", "SHORT"):
        return "SHORT"
    return None


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_iso(ts: Any) -> datetime | None:
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    s = str(ts).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _is_stale(updated_at: Any, *, now: datetime, max_hours: int = STALE_HOURS) -> bool:
    dt = _parse_iso(updated_at)
    if dt is None:
        # No timestamp = treat as stale to be safe.
        return True
    return (now - dt) > timedelta(hours=max_hours)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return None
    if not isinstance(data, dict):
        return None
    return data


def _index_picks(
    payload: dict[str, Any] | None,
    *,
    now: datetime,
    label: str,
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, set[str]], bool]:
    """Return (by_symbol_dir, dirs_by_symbol, source_fresh) for one platform.

    by_symbol_dir: (symbol, direction) -> single best pick (highest confidence)
    dirs_by_symbol: symbol -> set of directions present (used for disagreement)
    source_fresh:  True if the file's top-level `updated_at` is within window
    """
    by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    dirs_by_symbol: dict[str, set[str]] = {}
    if not payload:
        return by_pair, dirs_by_symbol, False

    top_updated = payload.get("updated_at")
    source_fresh = not _is_stale(top_updated, now=now)
    if not source_fresh:
        logger.info(
            "[pm_overlay] %s source stale (updated_at=%s, >%dh) — skipping",
            label,
            top_updated,
            STALE_HOURS,
        )
        return by_pair, dirs_by_symbol, False

    picks = payload.get("picks") if isinstance(payload.get("picks"), list) else []
    for pick in picks:
        if not isinstance(pick, dict):
            continue
        symbol = str(pick.get("symbol", "")).strip().upper()
        direction = _normalize_direction(pick)
        confidence = _to_float(pick.get("confidence"))
        if not symbol or not direction or confidence <= 0:
            continue

        dirs_by_symbol.setdefault(symbol, set()).add(direction)
        key = (symbol, direction)
        existing = by_pair.get(key)
        if existing is None or confidence > _to_float(existing.get("confidence")):
            by_pair[key] = pick

    return by_pair, dirs_by_symbol, True


def _record_disagreement(
    symbol: str,
    *,
    kalshi_dir: str,
    polymarket_dir: str,
    kalshi_conf: float,
    polymarket_conf: float,
    now: datetime,
) -> None:
    event = {
        "ts": now.isoformat(),
        "symbol": symbol,
        "kalshi_direction": kalshi_dir,
        "polymarket_direction": polymarket_dir,
        "kalshi_confidence": round(kalshi_conf, 4),
        "polymarket_confidence": round(polymarket_conf, 4),
        "verdict": "NEUTRAL_NO_TRADE",
    }
    _pm_disagreement_history.append(event)
    if len(_pm_disagreement_history) > _DISAGREEMENT_MAX:
        del _pm_disagreement_history[: len(_pm_disagreement_history) - _DISAGREEMENT_MAX]
    logger.info(
        "[pm_overlay] disagreement %s: kalshi=%s(%.2f) polymarket=%s(%.2f) → NEUTRAL",
        symbol,
        kalshi_dir,
        kalshi_conf,
        polymarket_dir,
        polymarket_conf,
    )


def _build_overlay_pick(
    symbol: str,
    direction: str,
    kalshi_pick: dict[str, Any],
    polymarket_pick: dict[str, Any],
    *,
    now: datetime,
    kalshi_updated_at: Any,
    polymarket_updated_at: Any,
) -> dict[str, Any]:
    k_conf = _to_float(kalshi_pick.get("confidence"))
    p_conf = _to_float(polymarket_pick.get("confidence"))
    base = (k_conf + p_conf) / 2.0
    boost = ALIGNMENT_BOOST if (k_conf > ALIGNMENT_HIGH_CONF_THRESHOLD and p_conf > ALIGNMENT_HIGH_CONF_THRESHOLD) else 1.0
    consensus = min(MAX_CONFIDENCE, round(base * boost, 4))

    # Prefer the pick with a real entry_price (Polymarket usually has one for crypto).
    entry_pick = polymarket_pick if _to_float(polymarket_pick.get("entry_price")) > 0 else kalshi_pick
    entry_price = _to_float(entry_pick.get("entry_price")) or None
    take_profit = _to_float(entry_pick.get("take_profit")) or None
    stop_loss = _to_float(entry_pick.get("stop_loss")) or None

    category = (
        polymarket_pick.get("category")
        or kalshi_pick.get("category")
        or "crypto"
    )

    pid = f"pm_overlay_{symbol}_{direction[0]}_{now.strftime('%Y%m%d%H%M')}"
    status = "OPEN" if entry_price else "SIGNAL"

    return {
        "id": pid,
        "strategy": "pm_consensus_overlay",
        "source_system": "pm_consensus",
        "symbol": symbol,
        "category": category,
        "direction": direction,
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "confidence": consensus,
        "entry_price": entry_price,
        "entry_date": now.strftime("%Y-%m-%d"),
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "status": status,
        "type_label": "🔮 PM Overlay",
        "created_at": now.isoformat(),
        "pm_consensus_data": {
            "kalshi_pick_id": str(kalshi_pick.get("id", "")),
            "polymarket_pick_id": str(polymarket_pick.get("id", "")),
            "kalshi_confidence": round(k_conf, 4),
            "polymarket_confidence": round(p_conf, 4),
            "alignment_boost": boost,
            "consensus_confidence": consensus,
            "kalshi_updated_at": str(kalshi_updated_at) if kalshi_updated_at else None,
            "polymarket_updated_at": str(polymarket_updated_at) if polymarket_updated_at else None,
        },
        "reason": (
            f"Kalshi+Polymarket agree {direction} {symbol} "
            f"(k={k_conf:.2f}, p={p_conf:.2f}, boost={boost:.2f})"
        ),
    }


def pm_consensus_overlay() -> list[dict[str, Any]]:
    """Build pairwise Kalshi+Polymarket consensus overlay picks.

    Returns: list of emitted pick dicts. Empty on rollback, missing files, or
    fully stale sources. Disagreements are NOT emitted as picks — they go to
    the in-memory `_pm_disagreement_history` ring.
    """
    if os.environ.get(ROLLBACK_ENV, "").strip() == "1":
        logger.info("[pm_overlay] disabled via %s=1", ROLLBACK_ENV)
        return []

    now = datetime.now(timezone.utc)

    poly_payload = _load_json(POLYMARKET_FILE)
    kalshi_payload = _load_json(KALSHI_FILE)

    if poly_payload is None:
        logger.info("[pm_overlay] polymarket file missing — empty result")
        return []
    if kalshi_payload is None:
        logger.info("[pm_overlay] kalshi file missing — empty result")
        return []

    poly_by_pair, poly_dirs, poly_fresh = _index_picks(poly_payload, now=now, label="polymarket")
    kalshi_by_pair, kalshi_dirs, kalshi_fresh = _index_picks(kalshi_payload, now=now, label="kalshi")

    if not poly_fresh or not kalshi_fresh:
        return []

    poly_updated_at = poly_payload.get("updated_at")
    kalshi_updated_at = kalshi_payload.get("updated_at")

    overlay: list[dict[str, Any]] = []
    seen_disagreement: set[str] = set()

    common_symbols = set(poly_dirs) & set(kalshi_dirs)
    for symbol in sorted(common_symbols):
        p_dirs = poly_dirs.get(symbol, set())
        k_dirs = kalshi_dirs.get(symbol, set())

        agreed = p_dirs & k_dirs
        if agreed:
            for direction in sorted(agreed):
                kalshi_pick = kalshi_by_pair.get((symbol, direction))
                poly_pick = poly_by_pair.get((symbol, direction))
                if not kalshi_pick or not poly_pick:
                    continue
                overlay.append(
                    _build_overlay_pick(
                        symbol,
                        direction,
                        kalshi_pick,
                        poly_pick,
                        now=now,
                        kalshi_updated_at=kalshi_updated_at,
                        polymarket_updated_at=poly_updated_at,
                    )
                )

        # Disagreement detection: at least one direction in each but no overlap.
        elif p_dirs and k_dirs and symbol not in seen_disagreement:
            seen_disagreement.add(symbol)
            # Pick the highest-confidence entry from each side for the log.
            k_dir = sorted(k_dirs)[0]
            p_dir = sorted(p_dirs)[0]
            k_pick = kalshi_by_pair.get((symbol, k_dir), {})
            p_pick = poly_by_pair.get((symbol, p_dir), {})
            _record_disagreement(
                symbol,
                kalshi_dir=k_dir,
                polymarket_dir=p_dir,
                kalshi_conf=_to_float(k_pick.get("confidence")),
                polymarket_conf=_to_float(p_pick.get("confidence")),
                now=now,
            )

    overlay.sort(key=lambda p: float(p.get("confidence", 0) or 0), reverse=True)
    logger.info(
        "[pm_overlay] emitted %d consensus picks, %d disagreements logged",
        len(overlay),
        len(seen_disagreement),
    )
    return overlay


def get_disagreement_history() -> list[dict[str, Any]]:
    """Return a copy of the in-memory disagreement log."""
    return list(_pm_disagreement_history)


def clear_disagreement_history() -> None:
    """Reset the disagreement log (used by tests)."""
    _pm_disagreement_history.clear()


def _summarize_confidences(picks: Iterable[dict[str, Any]]) -> dict[str, float]:
    confs = [float(p.get("confidence", 0) or 0) for p in picks]
    if not confs:
        return {"n": 0, "min": 0.0, "max": 0.0, "mean": 0.0}
    return {
        "n": len(confs),
        "min": round(min(confs), 4),
        "max": round(max(confs), 4),
        "mean": round(sum(confs) / len(confs), 4),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 70)
    print("  PM Consensus Overlay — Kalshi + Polymarket Pairwise Agreement")
    print("=" * 70)

    picks = pm_consensus_overlay()
    dist = _summarize_confidences(picks)
    disagreements = get_disagreement_history()

    print(f"\nn_consensus_picks:   {len(picks)}")
    print(f"n_disagreements:     {len(disagreements)}")
    print(
        f"confidence_dist:     n={dist['n']} min={dist['min']} "
        f"max={dist['max']} mean={dist['mean']}"
    )

    print("\n--- Sample emitted picks (top 5) ---")
    for pick in picks[:5]:
        d = pick.get("pm_consensus_data", {})
        print(
            f"  {pick['direction']:<5s} {pick['symbol']:<10s} "
            f"conf={pick['confidence']:.3f}  "
            f"k={d.get('kalshi_confidence')}  p={d.get('polymarket_confidence')}  "
            f"boost={d.get('alignment_boost')}"
        )
        print(f"    reason: {pick['reason']}")

    print("\n--- Disagreement log ---")
    for ev in disagreements:
        print(
            f"  {ev['symbol']:<10s} kalshi={ev['kalshi_direction']}({ev['kalshi_confidence']}) "
            f"polymarket={ev['polymarket_direction']}({ev['polymarket_confidence']})"
        )
