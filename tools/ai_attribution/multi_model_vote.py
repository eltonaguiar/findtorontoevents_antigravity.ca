#!/usr/bin/env python3
"""M-051 — multi-model swarm vote primitive.

Asks several *genuinely different* LLM providers to vote LONG / SHORT / PASS
on a candidate trade, and assembles a ``models_consulted[]`` array in the
swarm-pick schema shape (``tools/swarm/swarm_pick_schema.py``).

Why: today every record in ``audit_dashboard/data/swarm_picks.json`` carries
``underlying_model = "claude-opus-4-7"`` — one model wearing every persona —
so the AI Leaderboard (``audit_dashboard/ai_leaderboard.html``) is
single-engine. This module is the core primitive that lets swarm picks be
voted by real different models (deepseek / groq / cerebras / openrouter),
making per-AI attribution meaningful.

Status: opt-in sidecar. Not yet wired into live pick generation.

## Wiring Plan
Target caller: the swarm pick-generation path that today writes single-model
picks. `gather_votes()` output is dropped straight into a pick's
`models_consulted` field before `append_picks()` (`swarm_pick_schema.py`).
Wire-up PR: a follow-up that calls `gather_votes()` at swarm decision time.

Uses the swarm_v2 LLM client (`tools/swarm_v2/swarms/core/llm_client.py`) —
real providers, graceful skip when a provider key is absent.

Usage:
    python tools/ai_attribution/multi_model_vote.py --symbol BTCUSDT \\
        --asset-class CRYPTO --timeframe 4H
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# swarm_v2 is a standalone package under tools/swarm_v2/.
sys.path.insert(0, str(REPO_ROOT / "tools" / "swarm_v2"))

try:
    from swarms.core.llm_client import LLMClient, detect_providers
    _HAS_LLM = True
except ImportError:  # pragma: no cover - swarm_v2 absent
    LLMClient = None  # type: ignore
    detect_providers = lambda: []  # noqa: E731
    _HAS_LLM = False

# Default provider roster — the four verified-working engines (2026-05-15).
DEFAULT_PROVIDERS = ("deepseek", "groq", "cerebras", "openrouter")

_VALID_VOTES = {"LONG", "SHORT", "PASS"}

_SYSTEM = (
    "You are a disciplined trading analyst. Vote on ONE candidate trade. "
    "Reply with ONLY a compact JSON object, no prose, no code fence:\n"
    '{"vote":"LONG|SHORT|PASS","confidence":0-100,'
    '"rationale":"<= 30 words"}'
)


def _build_prompt(symbol: str, asset_class: str, timeframe: str,
                  context: str) -> str:
    ctx = f"\nContext:\n{context}" if context else ""
    return (
        f"Candidate: {symbol} ({asset_class}), intended timeframe {timeframe}."
        f"{ctx}\n\nShould we go LONG, SHORT, or PASS? Vote now."
    )


def _parse_vote(text: str | None) -> dict[str, Any] | None:
    """Parse a model reply into {vote, confidence, rationale}. None on junk."""
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except (json.JSONDecodeError, ValueError):
        return None
    vote = str(obj.get("vote", "")).strip().upper()
    if vote not in _VALID_VOTES:
        return None
    try:
        conf = int(float(obj.get("confidence", 0)))
    except (TypeError, ValueError):
        conf = 0
    conf = max(0, min(100, conf))
    rationale = str(obj.get("rationale", "")).strip()[:200]
    return {"vote": vote, "confidence": conf, "rationale": rationale}


def gather_votes(
    symbol: str,
    asset_class: str,
    timeframe: str = "4H",
    context: str = "",
    providers: tuple[str, ...] = DEFAULT_PROVIDERS,
    llm_factory: Any = None,
) -> list[dict[str, Any]]:
    """Fan a vote request to each provider; return a ``models_consulted[]``.

    Each entry matches the swarm-pick schema: name, role, underlying_model,
    vote, confidence_0_100, timeframe, justification_summary.

    A provider with no key, or that errors / returns junk, is skipped — the
    returned list only contains genuine votes. ``llm_factory`` is an
    injection seam for tests (defaults to the real ``LLMClient``).
    """
    if llm_factory is None:
        if not _HAS_LLM:
            return []
        llm_factory = LLMClient
    prompt = _build_prompt(symbol, asset_class, timeframe, context)
    votes: list[dict[str, Any]] = []
    for provider in providers:
        try:
            client = llm_factory(provider=provider)
        except Exception:  # noqa: BLE001 - unknown provider name
            continue
        if not getattr(client, "available", False):
            continue
        reply = client.complete(prompt, system=_SYSTEM, max_tokens=300)
        parsed = _parse_vote(reply)
        if parsed is None:
            continue
        votes.append({
            "name": f"{provider}_analyst",
            "role": "trade_voter",
            "underlying_model": client.model or provider,
            "vote": parsed["vote"],
            "confidence_0_100": parsed["confidence"],
            "timeframe": timeframe,
            "justification_summary": parsed["rationale"],
        })
    return votes


def consensus(votes: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarise votes: majority direction, agreement count, mean confidence."""
    if not votes:
        return {"direction": "PASS", "models_agreed": 0,
                "models_voted": 0, "consensus_score": 0.0}
    tally: dict[str, int] = {}
    for v in votes:
        tally[v["vote"]] = tally.get(v["vote"], 0) + 1
    direction = max(tally, key=lambda k: tally[k])
    agreed = tally[direction]
    mean_conf = sum(v["confidence_0_100"] for v in votes) / len(votes)
    return {
        "direction": direction,
        "models_agreed": agreed,
        "models_voted": len(votes),
        "consensus_score": round(agreed / len(votes) * (mean_conf / 100.0), 3),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="M-051 multi-model trade vote.")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--asset-class", default="CRYPTO")
    ap.add_argument("--timeframe", default="4H")
    ap.add_argument("--context", default="")
    ap.add_argument("--providers", default=",".join(DEFAULT_PROVIDERS),
                    help="Comma-separated provider names.")
    args = ap.parse_args(argv)

    provs = tuple(p.strip() for p in args.providers.split(",") if p.strip())
    print(f"[m051] keyed providers available: {detect_providers()}")
    votes = gather_votes(args.symbol, args.asset_class, args.timeframe,
                         args.context, providers=provs)
    summary = consensus(votes)
    print(json.dumps({"symbol": args.symbol,
                       "models_consulted": votes,
                       "consensus": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
