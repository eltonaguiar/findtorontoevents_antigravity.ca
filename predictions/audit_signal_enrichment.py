"""
Cross-enrich social/analyst predictions using unified audit active picks.

Uses audit_trail/data/dashboard_payload.json (when present) to compute
per-(symbol, direction) alignment with the rest of the fleet, then blends
that with predictor tier from the predictions DB.

Outputs extra fields on each exported row (non-destructive to SQLite):
  - audit_alignment_score: -1..1 (fleet agrees / disagrees with direction)
  - predictor_tier: ELITE | PROVEN | MIXED | LOSING | UNRANKED
  - enhanced_conviction: 0..1 (ranking hint for dashboard / sorting)
  - enrichment_generated_at: ISO timestamp
  - enrichment_source: constant string for debugging

See CHATWITHIT.MD 2026-03-29 (dormant winners / consensus analysis).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_PAYLOAD = REPO_ROOT / "audit_trail" / "data" / "dashboard_payload.json"

TIER_WEIGHT: dict[str, float] = {
    "ELITE": 1.0,
    "PROVEN": 0.88,
    "MIXED": 0.65,
    "LOSING": 0.32,
    "UNRANKED": 0.55,
}

ENRICHMENT_VERSION = "audit_cross_signal_v1"


def _norm_direction(d: Any) -> str:
    u = str(d or "").strip().upper()
    if u in ("BUY", "LONG", "BULL", "CALL"):
        return "LONG"
    if u in ("SELL", "SHORT", "BEAR", "PUT"):
        return "SHORT"
    return u or "LONG"


def _norm_symbol(sym: Any) -> str:
    s = str(sym or "").upper().replace("/", "").replace("-", "").strip()
    if "=" in s:
        s = s.split("=")[0]
    return s


def _load_audit_alignment(
    payload_path: Path | None = None,
) -> dict[str, dict[str, int]]:
    """symbol_base -> {'LONG': n, 'SHORT': n} from payload picks.active (crypto-ish only)."""
    path = payload_path or DEFAULT_AUDIT_PAYLOAD
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    actives = (doc.get("picks") or {}).get("active") or []
    counts: dict[str, dict[str, int]] = {}
    for p in actives:
        if not isinstance(p, dict):
            continue
        sym = _norm_symbol(p.get("symbol"))
        if not sym or len(sym) < 3:
            continue
        # Skip obvious non-crypto equity symbols for alignment (optional heuristic)
        if sym.isalpha() and len(sym) <= 5 and not sym.endswith("USDT") and "USD" not in sym:
            if "." not in sym and sym not in ("BTC", "ETH", "SOL"):
                continue
        d = _norm_direction(p.get("direction"))
        if d not in ("LONG", "SHORT"):
            continue
        bucket = counts.setdefault(sym, {"LONG": 0, "SHORT": 0})
        bucket[d] = bucket.get(d, 0) + 1
    return counts


def _alignment_for_symbol_direction(
    sym_counts: dict[str, dict[str, int]],
    symbol: Any,
    direction: Any,
) -> float:
    """-1 = fleet disagrees, +1 = fleet agrees, 0 = unknown / empty."""
    sym = _norm_symbol(symbol)
    if not sym:
        return 0.0
    # Try exact, then strip USDT suffix variants
    candidates = [sym]
    if sym.endswith("USDT"):
        candidates.append(sym[:-4])
    elif len(sym) >= 3 and not sym.endswith("USDT"):
        candidates.append(sym + "USDT")
    block: dict[str, int] | None = None
    for c in candidates:
        if c in sym_counts:
            block = sym_counts[c]
            break
    if not block:
        return 0.0
    d = _norm_direction(direction)
    long_n = int(block.get("LONG", 0))
    short_n = int(block.get("SHORT", 0))
    total = long_n + short_n
    if total == 0:
        return 0.0
    if d == "LONG":
        return (long_n - short_n) / float(total)
    if d == "SHORT":
        return (short_n - long_n) / float(total)
    return 0.0


def _predictor_tier(conn: sqlite3.Connection, predictor_id: str) -> str:
    row = conn.execute(
        "SELECT tier FROM predictors WHERE predictor_id = ? LIMIT 1",
        (predictor_id,),
    ).fetchone()
    if not row:
        return "UNRANKED"
    t = row["tier"] if isinstance(row, sqlite3.Row) else row[0]
    return str(t or "UNRANKED")


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def enrich_prediction_row(
    row: dict[str, Any],
    conn: sqlite3.Connection,
    sym_counts: dict[str, dict[str, int]],
) -> dict[str, Any]:
    out = dict(row)
    pid = str(out.get("predictor_id") or "")
    tier = _predictor_tier(conn, pid)
    align = _alignment_for_symbol_direction(sym_counts, out.get("symbol"), out.get("direction"))
    tw = TIER_WEIGHT.get(tier, TIER_WEIGHT["UNRANKED"])
    # Blend: half tier strength, half fleet alignment mapped to 0..1
    align_01 = 0.5 + 0.5 * _clamp(align, -1.0, 1.0)
    enhanced = _clamp(0.5 * tw + 0.5 * align_01, 0.0, 1.0)
    # Penalize LOSING + strong disagreement
    if tier == "LOSING" and align < -0.25:
        enhanced = _clamp(enhanced * 0.75, 0.0, 1.0)
        out["low_conviction_flag"] = True
    elif tier == "ELITE" and align > 0.2:
        enhanced = _clamp(enhanced * 1.05, 0.0, 1.0)

    out["audit_alignment_score"] = round(float(align), 4)
    out["predictor_tier"] = tier
    out["enhanced_conviction"] = round(float(enhanced), 4)
    out["enrichment_generated_at"] = datetime.now(timezone.utc).isoformat()
    out["enrichment_source"] = ENRICHMENT_VERSION
    return out


def enrich_prediction_rows(
    rows: list[dict[str, Any]],
    conn: sqlite3.Connection,
    audit_payload_path: Path | None = None,
) -> list[dict[str, Any]]:
    sym_counts = _load_audit_alignment(audit_payload_path)
    return [enrich_prediction_row(r, conn, sym_counts) for r in rows]
