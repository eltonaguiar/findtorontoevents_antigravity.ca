"""Load P1 swarm output from `swarm_runs/research_<class>_p1_*/` dirs and
aggregate citations across engines.

Each engine writes `<engine>.json` (the JSON-strict response) and
`<engine>.json.raw.txt` (raw stdout). This loader reads the parsed
`.json` files, deduplicates citations by URL, tracks per-engine
attribution for the verify_citations.py vote-weight calculation.
"""

from __future__ import annotations

import json
from pathlib import Path

from .schemas import Citation

REPO_ROOT = Path(__file__).resolve().parents[2]
SWARM_RUNS = REPO_ROOT / "swarm_runs"


def _latest_p1_dir(asset_class: str) -> Path | None:
    """Find the most-recent `research_<class>_p1_<ts>` dir."""
    pattern = f"research_{asset_class.lower()}_p1_*"
    matches = sorted(SWARM_RUNS.glob(pattern), reverse=True)
    return matches[0] if matches else None


def _parse_engine_json(path: Path) -> dict:
    """Tolerant parse: accepts wrapped JSON (`{"response": "...{json}..."}`)
    or raw JSON. Returns empty dict on parse failure."""
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    # Try direct JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    # If swarm_run.py wrapped the engine response, unwrap
    if isinstance(data, dict) and isinstance(data.get("response"), str):
        try:
            inner = json.loads(data["response"])
            if isinstance(inner, dict):
                return inner
        except json.JSONDecodeError:
            pass
    return data if isinstance(data, dict) else {}


def load_p1_citations(
    asset_class: str,
    p1_dir: Path | None = None,
) -> dict:
    """Load + dedupe citations from a P1 swarm run.

    Returns:
      {
        "citations": [Citation, ...],
        "engine_attribution": {engine: [url, url, ...]},
        "p1_dir": Path or None,
        "engines_seen": [engine_name, ...],
        "themes_observed": [str, ...],
      }
    """
    p1_dir = p1_dir or _latest_p1_dir(asset_class)
    out: dict = {
        "citations": [],
        "engine_attribution": {},
        "p1_dir": p1_dir,
        "engines_seen": [],
        "themes_observed": [],
    }
    if p1_dir is None or not p1_dir.exists():
        return out

    seen_urls: dict[str, Citation] = {}
    for engine_json in sorted(p1_dir.glob("*.json")):
        if engine_json.name == "_summary.json":
            continue
        engine_name = engine_json.stem
        data = _parse_engine_json(engine_json)
        out["engines_seen"].append(engine_name)
        themes = data.get("themes_observed") or []
        if isinstance(themes, list):
            for t in themes:
                if isinstance(t, str):
                    out["themes_observed"].append(f"[{engine_name}] {t}")
        for c in data.get("citations") or []:
            if not isinstance(c, dict):
                continue
            url = (c.get("url") or "").strip()
            if not url:
                continue
            cit = seen_urls.get(url)
            if cit is None:
                cit = Citation(
                    url=url,
                    access_date=str(c.get("access_date") or "").strip(),
                    title=str(c.get("title") or "").strip(),
                    author=str(c.get("author") or "").strip(),
                    year=str(c.get("year") or "").strip(),
                    claim=str(c.get("claim") or "").strip(),
                    evidence_strength=str(c.get("evidence_strength") or "anec").strip(),
                    asset_class=asset_class.upper(),
                )
                seen_urls[url] = cit
            out["engine_attribution"].setdefault(engine_name, []).append(url)
    out["citations"] = list(seen_urls.values())
    return out
