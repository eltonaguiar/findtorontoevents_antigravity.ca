"""
Phase 1: deterministic regex router.

Reads `tools/swarm/agent_personas/_registry.yaml`, takes a problem description
as input, returns a ranked list of (persona_name, confidence, matched_keywords)
for matches with confidence >= the persona's `confidence_floor_for_match`
(default 0.65).

This is LOGGING-ONLY in Phase 1 — it does not change the behavior of
swarm_run.py or swarm_dispatch.ps1. It just logs what it WOULD have selected,
so we can validate routing accuracy against actual swarm runs.

Usage:
    python tools/swarm/persona_router.py --problem-file <md>
    python tools/swarm/persona_router.py --query "user clicks Next Month and..."
    python tools/swarm/persona_router.py --query "..." --json   # machine-readable

Spec: tools/swarm/agent_personas/ROUTER_ARCHITECTURE.md
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Paths

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "tools" / "swarm" / "agent_personas" / "_registry.yaml"
DEFAULT_LOG_DIR = REPO_ROOT / "swarm_runs"
DEFAULT_LOG_PATH = DEFAULT_LOG_DIR / "_routing_log.jsonl"

# ---------------------------------------------------------------------------
# Constants from ROUTER_ARCHITECTURE consensus addendum (§1)

GLOBAL_CONFIDENCE_FLOOR = 0.60       # below this -> fallback
HIGH_CONFIDENCE_THRESHOLD = 0.75     # >= this -> route directly
DEFAULT_PER_PERSONA_FLOOR = 0.65
TOP_K = 3


# ---------------------------------------------------------------------------
# Registry loading

def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Load and validate the persona registry YAML."""
    if not path.exists():
        raise FileNotFoundError(f"Registry not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "personas" not in data:
        raise ValueError(f"Registry malformed (no 'personas' key): {path}")
    return data


# ---------------------------------------------------------------------------
# Matching

_WORD_BOUNDARY_SAFE = re.compile(r"^[A-Za-z0-9_]+$")


def _compile_keyword_pattern(keyword: str) -> re.Pattern[str]:
    """
    Compile a keyword to a case-insensitive regex.

    Single bare-word keywords get \b boundaries. Multi-word / punctuated
    keywords are matched as substrings (case-insensitive) since \b is
    unreliable for tokens like "EUR/USD" or "applyFilters".
    """
    if _WORD_BOUNDARY_SAFE.match(keyword):
        return re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
    return re.compile(re.escape(keyword), re.IGNORECASE)


# Saturating denominator: 3 keyword hits = full confidence. This makes the
# per-persona floor of 0.65 reachable (~2 hits) and the global 0.60 fallback
# threshold meaningful, regardless of how many trigger_keywords a persona
# declares. Without saturation, a persona with 13 keywords would need 9 hits
# to reach 0.65 — which never happens in practice.
SATURATION_HITS = 3.0


def _score_persona(text: str, persona: dict[str, Any]) -> tuple[float, list[str]]:
    """
    Return (confidence, matched_keywords) for one persona.

    confidence = min(1.0, matches / SATURATION_HITS). The generalist
    (empty keywords) always scores 0.0 — it's surfaced separately when no
    other persona clears the global floor.
    """
    keywords: list[str] = persona.get("trigger_keywords") or []
    if not keywords:
        return 0.0, []
    matched: list[str] = []
    for kw in keywords:
        pattern = _compile_keyword_pattern(kw)
        if pattern.search(text):
            matched.append(kw)
    confidence = min(1.0, len(matched) / SATURATION_HITS)
    return confidence, matched


def route(
    text: str,
    registry: dict[str, Any] | None = None,
    top_k: int = TOP_K,
) -> dict[str, Any]:
    """
    Run regex routing over the registry.

    Returns:
        {
          "matches": [
            {"persona": str, "confidence": float, "matched_keywords": [str]},
            ...
          ],
          "fallback_used": bool,
          "method": "regex",
          "global_floor": GLOBAL_CONFIDENCE_FLOOR,
        }

    Top-K matches are filtered to those with confidence >= the persona's
    own confidence_floor_for_match (default 0.65). If the max confidence
    across the registry is < GLOBAL_CONFIDENCE_FLOOR (0.60), `matches`
    becomes [{"persona": "generalist-fallback", "confidence": 0.0,
    "matched_keywords": []}] and `fallback_used` = True.
    """
    if registry is None:
        registry = load_registry()
    personas = registry.get("personas", [])

    scored: list[dict[str, Any]] = []
    max_conf = 0.0
    for p in personas:
        conf, matched = _score_persona(text, p)
        scored.append(
            {
                "persona": p["name"],
                "confidence": conf,
                "matched_keywords": matched,
                "floor": float(
                    p.get("confidence_floor_for_match", DEFAULT_PER_PERSONA_FLOOR)
                ),
            }
        )
        if conf > max_conf and p["name"] != "generalist-fallback":
            max_conf = conf

    # Global fallback: nothing cleared 0.60 -> route to generalist.
    if max_conf < GLOBAL_CONFIDENCE_FLOOR:
        return {
            "matches": [
                {
                    "persona": "generalist-fallback",
                    "confidence": 0.0,
                    "matched_keywords": [],
                }
            ],
            "fallback_used": True,
            "method": "regex",
            "global_floor": GLOBAL_CONFIDENCE_FLOOR,
        }

    # Filter by per-persona floor; sort by confidence desc; take top K.
    qualifying = [
        s for s in scored
        if s["persona"] != "generalist-fallback" and s["confidence"] >= s["floor"]
    ]
    qualifying.sort(key=lambda s: s["confidence"], reverse=True)
    top = qualifying[:top_k]

    # If qualifying is empty (max conf >= 0.60 but below per-persona floor),
    # surface the strongest below-floor candidate so the caller still gets a
    # signal, but mark fallback_used=True.
    if not top:
        below_floor = [s for s in scored if s["persona"] != "generalist-fallback"]
        below_floor.sort(key=lambda s: s["confidence"], reverse=True)
        return {
            "matches": [
                {
                    "persona": "generalist-fallback",
                    "confidence": 0.0,
                    "matched_keywords": [],
                }
            ],
            "fallback_used": True,
            "method": "regex",
            "global_floor": GLOBAL_CONFIDENCE_FLOOR,
            "below_floor_top": [
                {k: v for k, v in s.items() if k != "floor"} for s in below_floor[:3]
            ],
        }

    return {
        "matches": [
            {k: v for k, v in m.items() if k != "floor"} for m in top
        ],
        "fallback_used": False,
        "method": "regex",
        "global_floor": GLOBAL_CONFIDENCE_FLOOR,
    }


# ---------------------------------------------------------------------------
# Logging

def _query_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def log_routing_decision(
    text: str,
    result: dict[str, Any],
    log_path: Path = DEFAULT_LOG_PATH,
) -> None:
    """Append a JSONL record describing this routing decision."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query_hash": _query_hash(text),
        "matched": result["matches"],
        "method": result["method"],
        "fallback_used": result["fallback_used"],
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# CLI

def _format_human(text: str, result: dict[str, Any]) -> str:
    lines = []
    lines.append("# Persona router (Phase 1, regex, logging-only)")
    lines.append("")
    lines.append(f"- query_hash: `{_query_hash(text)}`")
    lines.append(f"- method: {result['method']}")
    lines.append(f"- fallback_used: {result['fallback_used']}")
    lines.append(f"- global_floor: {result['global_floor']}")
    lines.append("")
    lines.append("| Rank | Persona | Confidence | Matched keywords |")
    lines.append("|---|---|---|---|")
    for i, m in enumerate(result["matches"], 1):
        kws = ", ".join(f"`{k}`" for k in m["matched_keywords"]) or "(none)"
        lines.append(f"| {i} | {m['persona']} | {m['confidence']:.2f} | {kws} |")
    if result.get("below_floor_top"):
        lines.append("")
        lines.append("Below-floor candidates (no qualifying match):")
        for m in result["below_floor_top"]:
            kws = ", ".join(f"`{k}`" for k in m["matched_keywords"]) or "(none)"
            lines.append(f"- {m['persona']} ({m['confidence']:.2f}) — {kws}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--problem-file", type=Path, help="Path to a problem description (text/md)")
    src.add_argument("--query", type=str, help="Inline problem description")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of markdown table")
    ap.add_argument("--no-log", action="store_true", help="Skip writing to _routing_log.jsonl")
    ap.add_argument(
        "--log-path",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help=f"Override log path (default {DEFAULT_LOG_PATH})",
    )
    ap.add_argument("--top-k", type=int, default=TOP_K, help="Max number of matches to return")
    args = ap.parse_args(argv)

    if args.problem_file:
        text = args.problem_file.read_text(encoding="utf-8", errors="replace")
    else:
        text = args.query or ""

    registry = load_registry()
    result = route(text, registry, top_k=args.top_k)

    if not args.no_log:
        log_routing_decision(text, result, log_path=args.log_path)

    if args.json:
        sys.stdout.write(json.dumps(result, indent=2) + "\n")
    else:
        sys.stdout.write(_format_human(text, result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
