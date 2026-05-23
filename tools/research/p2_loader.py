"""Load P2 swarm output: candidates dicts → StrategySpec list.

Mirrors p1_loader. Each engine's `candidates[]` array gets normalized
into `StrategySpec` objects. Deduped by `spec_id`; ties resolved by
engine vote weight (higher P1 weight wins; same weight = lexicographic
on engine name).
"""

from __future__ import annotations

import json
from pathlib import Path

from .schemas import StrategySpec

REPO_ROOT = Path(__file__).resolve().parents[2]
SWARM_RUNS = REPO_ROOT / "swarm_runs"


def _latest_p2_dir(asset_class: str) -> Path | None:
    pattern = f"research_{asset_class.lower()}_p2_*"
    matches = sorted(SWARM_RUNS.glob(pattern), reverse=True)
    return matches[0] if matches else None


def _parse_engine_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict) and isinstance(data.get("response"), str):
        try:
            inner = json.loads(data["response"])
            if isinstance(inner, dict):
                return inner
        except json.JSONDecodeError:
            pass
    return data if isinstance(data, dict) else {}


def load_p2_specs(
    asset_class: str,
    engine_weights: dict[str, float] | None = None,
    p2_dir: Path | None = None,
) -> dict:
    """Aggregate candidates across engines into deduped StrategySpec list.

    engine_weights: from P1's verify_citations output. Engines with weight
    < 0.5 are EXCLUDED from P2 spec contribution to avoid laundering bad
    sources through new wrappers.
    """
    p2_dir = p2_dir or _latest_p2_dir(asset_class)
    out: dict = {
        "specs": [],
        "p2_dir": p2_dir,
        "engines_seen": [],
        "engine_attribution": {},
        "notes_to_p3": [],
    }
    if p2_dir is None or not p2_dir.exists():
        return out

    engine_weights = engine_weights or {}
    seen_ids: dict[str, tuple[StrategySpec, float, str]] = {}

    for engine_json in sorted(p2_dir.glob("*.json")):
        if engine_json.name == "_summary.json":
            continue
        engine_name = engine_json.stem
        # Exclude engines with weight < 0.5 (hallucinated >50% URLs in P1)
        weight = engine_weights.get(engine_name, 1.0)
        if weight < 0.5:
            continue
        data = _parse_engine_json(engine_json)
        out["engines_seen"].append(engine_name)
        note = data.get("notes_to_p3") or ""
        if isinstance(note, str) and note.strip():
            out["notes_to_p3"].append(f"[{engine_name}] {note.strip()}")

        for c in data.get("candidates") or []:
            if not isinstance(c, dict):
                continue
            spec_id = (c.get("spec_id") or "").strip()
            if not spec_id:
                continue
            spec = StrategySpec(
                spec_id=spec_id,
                asset_class=c.get("asset_class", asset_class.upper()),
                entry=str(c.get("entry") or "").strip(),
                exit=str(c.get("exit") or "").strip(),
                sizing=str(c.get("sizing") or "").strip(),
                universe=[str(u).upper() for u in (c.get("universe") or []) if u],
                regime_filter=str(c.get("regime_filter") or "").strip(),
                source_refs=[str(r) for r in (c.get("source_refs") or []) if r],
                proposed_by_engine=engine_name,
            )
            existing = seen_ids.get(spec_id)
            if existing is None or weight > existing[1] or (
                weight == existing[1] and engine_name < existing[2]
            ):
                seen_ids[spec_id] = (spec, weight, engine_name)
            out["engine_attribution"].setdefault(engine_name, []).append(spec_id)

    out["specs"] = [v[0] for v in seen_ids.values()]
    return out
