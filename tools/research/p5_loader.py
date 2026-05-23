"""Load P5 SYNTHESIS swarm output → SynthesisRow list.

Aggregates votes across engines: majority verdict wins per candidate.
Engine weight from P1 (deepseek 0.5x means half a vote).
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import Counter

from .schemas import SynthesisRow

REPO_ROOT = Path(__file__).resolve().parents[2]
SWARM_RUNS = REPO_ROOT / "swarm_runs"


def _latest_p5_dir(asset_class: str) -> Path | None:
    pattern = f"research_{asset_class.lower()}_p5_*"
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


def load_p5_synthesis(
    asset_class: str,
    engine_weights: dict[str, float] | None = None,
    p5_dir: Path | None = None,
) -> dict:
    """Aggregate per-engine synthesis votes into deduped SynthesisRow list.

    Returns:
      {
        "rows": [SynthesisRow, ...],   # one per spec_id, majority-voted
        "run_verdict": str,             # majority of engine-level run_verdict
        "run_rationale": str,           # joined rationales
        "p5_dir": Path or None,
        "engines_seen": [...],
      }
    """
    p5_dir = p5_dir or _latest_p5_dir(asset_class)
    out: dict = {
        "rows": [],
        "run_verdict": "PENDING",
        "run_rationale": "",
        "p5_dir": p5_dir,
        "engines_seen": [],
    }
    if p5_dir is None or not p5_dir.exists():
        return out

    engine_weights = engine_weights or {}
    per_spec_votes: dict[str, list[tuple[str, float, str, str, str]]] = {}
    run_verdicts: list[tuple[str, float]] = []
    run_rationales: list[str] = []

    for engine_json in sorted(p5_dir.glob("*.json")):
        if engine_json.name == "_summary.json":
            continue
        engine_name = engine_json.stem
        weight = engine_weights.get(engine_name, 1.0)
        if weight <= 0:
            continue
        data = _parse_engine_json(engine_json)
        out["engines_seen"].append(engine_name)
        rv = data.get("run_verdict") or ""
        if rv:
            run_verdicts.append((rv, weight))
        rr = data.get("run_rationale") or ""
        if rr:
            run_rationales.append(f"[{engine_name}] {rr}")

        for s in data.get("synthesis") or []:
            if not isinstance(s, dict):
                continue
            spec_id = (s.get("spec_id") or "").strip()
            if not spec_id:
                continue
            verdict = (s.get("verdict") or "").upper().strip() or "MIXED"
            rationale = (s.get("rationale") or "").strip()
            wiring = (s.get("wiring_plan") or "").strip()
            per_spec_votes.setdefault(spec_id, []).append(
                (engine_name, weight, verdict, rationale, wiring)
            )

    # Weighted majority per spec
    for spec_id, votes in per_spec_votes.items():
        counter: Counter = Counter()
        for _eng, w, verdict, _r, _wp in votes:
            counter[verdict] += w
        winning_verdict = counter.most_common(1)[0][0]
        winning = [v for v in votes if v[2] == winning_verdict]
        # Pick highest-weight winner for rationale + wiring
        winning.sort(key=lambda x: -x[1])
        eng, _w, verdict, rationale, wiring = winning[0]
        engine_votes = {v[0]: v[2] for v in votes}
        out["rows"].append(
            SynthesisRow(
                spec_id=spec_id,
                verdict=verdict,
                rationale=rationale,
                wiring_plan=wiring,
                engine_votes=engine_votes,
            )
        )

    # Weighted majority for run-level verdict
    if run_verdicts:
        rc: Counter = Counter()
        for verdict, w in run_verdicts:
            rc[verdict] += w
        out["run_verdict"] = rc.most_common(1)[0][0]
    out["run_rationale"] = "\n\n".join(run_rationales)

    return out
