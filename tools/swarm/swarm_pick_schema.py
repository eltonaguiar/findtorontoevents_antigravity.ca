"""Schema + validator for swarm-pick tracking store.

Single durable JSON store at `audit_dashboard/data/swarm_picks.json` — array
of pick records. See `docs/SWARM_PICK_TRACKING_DESIGN.md` for design.

Q3 decided YES (2026-05-12): `models_consulted[].underlying_model` is REQUIRED
so leaderboard can roll up by both persona-role and underlying-model identity.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_ACCOUNTS = {
    "theswarm", "V4", "HIGHFWWRABV55_SCOREABOVE50_V4", "Leap", "The Leap Crypto",
    "zerounderscore", "BROKIE", "SCALPER", "TESTER", "TRUSTOURSCORE",
}
VALID_DIRECTIONS = {"LONG", "SHORT"}
VALID_VOTES = {"LONG", "SHORT", "SKIP"}
VALID_QTY_UNITS = {"asset_units", "pct_balance", "contracts"}
VALID_TIMEFRAMES = {"5m", "15m", "30m", "1H", "4H", "1D", "1W", "1M", "3M", "6M", "1Y"}
VALID_ASSET_CLASSES = {"CRYPTO", "EQUITY", "ETF", "FOREX", "BOND", "COMMODITY", "FUTURES", "SPORTS"}
VALID_TIERS = {"unanimous", "strong", "moderate", "single", "control"}
VALID_EXIT_REASONS = {"TP_HIT", "SL_HIT", "TIME_CAP", "MANUAL", "EXPIRED", None}

REQUIRED_PICK_FIELDS = {
    "pick_id", "created_at", "session_id", "account", "symbol",
    "direction", "entry", "tp", "sl", "qty", "qty_unit",
    "timeframe", "asset_class", "consensus_tier",
    "models_consulted", "models_agreed", "models_voted",
    "consensus_score", "regime_at_entry", "outcome", "pattern_tags",
}

REQUIRED_MODEL_VOTE_FIELDS = {
    "name", "role", "underlying_model", "vote", "confidence_0_100",
    "timeframe", "justification_summary",
}


class SchemaError(ValueError):
    pass


def _err(field: str, msg: str, idx: int | None = None) -> None:
    loc = f"pick[{idx}]." if idx is not None else ""
    raise SchemaError(f"{loc}{field}: {msg}")


def validate_model_vote(v: dict, pick_idx: int, vote_idx: int) -> None:
    missing = REQUIRED_MODEL_VOTE_FIELDS - set(v.keys())
    if missing:
        _err(f"models_consulted[{vote_idx}]", f"missing fields {missing}", pick_idx)
    if v["vote"] not in VALID_VOTES:
        _err(f"models_consulted[{vote_idx}].vote", f"not in {VALID_VOTES}", pick_idx)
    c = v["confidence_0_100"]
    if not (isinstance(c, (int, float)) and 0 <= c <= 100):
        _err(f"models_consulted[{vote_idx}].confidence_0_100", "must be 0-100", pick_idx)
    if v["timeframe"] not in VALID_TIMEFRAMES:
        _err(f"models_consulted[{vote_idx}].timeframe", f"not in {VALID_TIMEFRAMES}", pick_idx)


def validate_pick(p: dict, idx: int | None = None) -> None:
    missing = REQUIRED_PICK_FIELDS - set(p.keys())
    if missing:
        _err("root", f"missing fields {missing}", idx)
    if p["account"] not in VALID_ACCOUNTS:
        _err("account", f"not in {VALID_ACCOUNTS}", idx)
    if p["direction"] not in VALID_DIRECTIONS:
        _err("direction", f"not in {VALID_DIRECTIONS}", idx)
    if p["qty_unit"] not in VALID_QTY_UNITS:
        _err("qty_unit", f"not in {VALID_QTY_UNITS}", idx)
    if p["timeframe"] not in VALID_TIMEFRAMES:
        _err("timeframe", f"not in {VALID_TIMEFRAMES}", idx)
    if p["asset_class"] not in VALID_ASSET_CLASSES:
        _err("asset_class", f"not in {VALID_ASSET_CLASSES}", idx)
    if p["consensus_tier"] not in VALID_TIERS:
        _err("consensus_tier", f"not in {VALID_TIERS}", idx)

    entry, tp, sl = float(p["entry"]), float(p["tp"]), float(p["sl"])
    if p["direction"] == "LONG" and not (tp > entry > sl):
        _err("side-sanity", f"LONG requires tp>entry>sl; got tp={tp} entry={entry} sl={sl}", idx)
    if p["direction"] == "SHORT" and not (sl > entry > tp):
        _err("side-sanity", f"SHORT requires sl>entry>tp; got sl={sl} entry={entry} tp={tp}", idx)

    if not isinstance(p["models_consulted"], list) or not p["models_consulted"]:
        _err("models_consulted", "must be non-empty list", idx)
    for vi, v in enumerate(p["models_consulted"]):
        validate_model_vote(v, idx if idx is not None else 0, vi)

    score = p["consensus_score"]
    if not (isinstance(score, (int, float)) and 0 <= score <= 1):
        _err("consensus_score", "must be 0..1", idx)

    if p["outcome"] is not None:
        o = p["outcome"]
        if "exit_reason" in o and o["exit_reason"] not in VALID_EXIT_REASONS:
            _err("outcome.exit_reason", f"not in {VALID_EXIT_REASONS}", idx)


def validate_store(picks: list[dict]) -> None:
    if not isinstance(picks, list):
        raise SchemaError("root must be a list")
    seen_ids: set[str] = set()
    for i, p in enumerate(picks):
        validate_pick(p, i)
        if p["pick_id"] in seen_ids:
            raise SchemaError(f"pick[{i}].pick_id: duplicate {p['pick_id']}")
        seen_ids.add(p["pick_id"])


def derive_consensus_tier(consensus_score: float, models_voted: int) -> str:
    if consensus_score >= 0.95 and models_voted >= 3:
        return "unanimous"
    if consensus_score >= 0.66 and models_voted >= 3:
        return "strong"
    if consensus_score >= 0.50 and models_voted >= 2:
        return "moderate"
    if consensus_score > 0:
        return "single"
    return "control"


def passes_tier_gate(pick: dict, min_tier: str = "strong") -> bool:
    """M-010: Tier gate for tv-paper-trade execution filter.

    Returns True when the pick's consensus_tier is at or above min_tier.
    Tier order (ascending): control < single < moderate < strong < unanimous.

    Override: SWARM_TIER_GATE_ENABLED=0 → always pass (fail-open for testing).
    """
    if os.environ.get("SWARM_TIER_GATE_ENABLED", "1") not in ("1", "true", "TRUE"):
        return True
    tier_order = ["control", "single", "moderate", "strong", "unanimous"]
    pick_tier = str(pick.get("consensus_tier", "control")).lower()
    try:
        pick_rank = tier_order.index(pick_tier)
        min_rank = tier_order.index(min_tier.lower())
        return pick_rank >= min_rank
    except ValueError:
        return False  # unknown tier → block


def new_pick_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_store(path: Path, picks: list[dict]) -> None:
    validate_store(picks)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(picks, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def load_store(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def append_picks(path: Path, new_picks: list[dict]) -> dict:
    """Append picks to the store, preserving existing records + outcomes.

    Idempotent on `pick_id` — re-appending a pick with the same id is a no-op
    (returns it in `skipped` rather than overwriting). Caller must mint fresh
    `pick_id` (via `new_pick_id()`) for genuinely-new picks.

    Returns: {"added": int, "skipped": int, "total": int}
    """
    existing = load_store(path)
    seen = {p["pick_id"] for p in existing}
    added = 0
    skipped = 0
    for p in new_picks:
        if p.get("pick_id") in seen:
            skipped += 1
            continue
        validate_pick(p)
        existing.append(p)
        seen.add(p["pick_id"])
        added += 1
    if added > 0:
        atomic_write_store(path, existing)
    return {"added": added, "skipped": skipped, "total": len(existing)}


def update_pattern_tags(path: Path, pattern_tags_path: Path) -> dict:
    """Backfill `pattern_tags` on every pick from current miner output.

    Each pick gets tags derived from `(consensus_tier, asset_class, regime)`
    membership in winning/losing/sparse cells. Existing tags are REPLACED
    (idempotent, miner is the source of truth).

    Returns: {"tagged": int, "winning": int, "losing": int, "sparse": int}
    """
    picks = load_store(path)
    if not picks:
        return {"tagged": 0, "winning": 0, "losing": 0, "sparse": 0}
    if not pattern_tags_path.exists():
        return {"tagged": 0, "winning": 0, "losing": 0, "sparse": 0,
                "error": "pattern_tags_path missing — run pattern_miner first"}
    patterns = json.loads(pattern_tags_path.read_text(encoding="utf-8"))

    def _cell_key(cell: dict) -> tuple[str, str, str]:
        return (cell["tier"], cell["class"], cell["regime"])

    winning_cells = {_cell_key(c) for c in patterns.get("winning", [])}
    losing_cells = {_cell_key(c) for c in patterns.get("losing", [])}
    sparse_cells = {_cell_key(c) for c in patterns.get("sparse", [])}

    tagged = 0
    w_count = l_count = s_count = 0
    for p in picks:
        regime = p.get("regime_at_entry", {}).get("btc_regime", "UNK")
        key = (p["consensus_tier"], p["asset_class"], regime)
        new_tags = []
        if key in winning_cells:
            new_tags.append("winning_cell")
            w_count += 1
        if key in losing_cells:
            new_tags.append("losing_cell")
            l_count += 1
        if key in sparse_cells:
            new_tags.append("sparse_cell")
            s_count += 1
        if p.get("pattern_tags") != new_tags:
            p["pattern_tags"] = new_tags
            tagged += 1
    if tagged > 0:
        atomic_write_store(path, picks)
    return {"tagged": tagged, "winning": w_count, "losing": l_count, "sparse": s_count}


if __name__ == "__main__":
    import sys
    store_path = Path(sys.argv[1] if len(sys.argv) > 1 else "audit_dashboard/data/swarm_picks.json")
    picks = load_store(store_path)
    try:
        validate_store(picks)
        print(f"OK: {len(picks)} picks pass schema")
    except SchemaError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
