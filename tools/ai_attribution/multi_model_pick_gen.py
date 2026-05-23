#!/usr/bin/env python3
"""M-051 — multi-model swarm pick-candidate generator.

For each symbol in a watchlist, asks genuinely different LLM engines to
vote (via ``multi_model_vote.gather_votes``), takes the consensus, and
emits a *candidate* pick record carrying real per-engine attribution in
``models_consulted[]``.

Output goes to a **sidecar** — ``audit_dashboard/data/ai_leaderboard/
swarm_pick_candidates.json`` — NOT the live ``swarm_picks.json`` book.
Candidates have no entry/tp/sl and ``status="CANDIDATE"``; an operator
(or a follow-up wire-up) reviews them and promotes the chosen ones.

This is the piece that makes the AI Leaderboard genuinely multi-engine:
once promoted + resolved, each candidate's ``models_consulted`` engines
appear on the realized-performance board.

## Wiring Plan
Target caller: a follow-up that, at swarm decision time, calls
`generate_candidates()` and feeds promoted candidates through
`swarm_pick_schema.append_picks()`. Until then this is an opt-in
sidecar — it changes no production behaviour, only writes the
review-only candidates file.

Usage:
    python tools/ai_attribution/multi_model_pick_gen.py \\
        --symbols BTCUSDT,ETHUSDT --asset-class CRYPTO --timeframe 4H
"""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUT = (REPO_ROOT / "audit_dashboard" / "data" / "ai_leaderboard"
               / "swarm_pick_candidates.json")

# Minimum vote agreement to emit a candidate (else the swarm is too split).
MIN_AGREEMENT = 2

try:
    from tools.ai_attribution.multi_model_vote import (
        consensus as _consensus, gather_votes as _gather_votes,
    )
except ImportError:  # pragma: no cover - direct-script fallback
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from tools.ai_attribution.multi_model_vote import (  # type: ignore
        consensus as _consensus, gather_votes as _gather_votes,
    )


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_candidates(
    symbols: list[str],
    asset_class: str = "CRYPTO",
    timeframe: str = "4H",
    context: str = "",
    min_agreement: int = MIN_AGREEMENT,
    vote_fn: Callable[..., list[dict]] | None = None,
) -> list[dict[str, Any]]:
    """Generate candidate picks for *symbols* via a multi-model vote.

    A candidate is emitted only when the consensus direction is not PASS
    and at least *min_agreement* engines agreed. ``vote_fn`` is an
    injection seam for tests (defaults to the real ``gather_votes``).
    """
    vote_fn = vote_fn or _gather_votes
    candidates: list[dict[str, Any]] = []
    for symbol in symbols:
        votes = vote_fn(symbol, asset_class, timeframe, context)
        if not votes:
            continue
        summary = _consensus(votes)
        if summary["direction"] == "PASS":
            continue
        if summary["models_agreed"] < min_agreement:
            continue
        candidates.append({
            "pick_id": f"mmcand-{uuid.uuid4().hex[:12]}",
            "created_at": _utc(),
            "status": "CANDIDATE",
            "symbol": symbol,
            "asset_class": asset_class,
            "direction": summary["direction"],
            "timeframe": timeframe,
            "consensus_tier": "multi_model",
            "models_consulted": votes,
            "models_agreed": summary["models_agreed"],
            "models_voted": summary["models_voted"],
            "consensus_score": summary["consensus_score"],
            "_source": "multi_model_pick_gen",
        })
    return candidates


def write_candidates(candidates: list[dict[str, Any]],
                      out_path: Path = DEFAULT_OUT) -> Path:
    """Write the candidates sidecar (review-only — never the live book)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "v1",
        "as_of": _utc(),
        "note": ("Review-only candidates. NOT the live swarm_picks.json. "
                 "Promote chosen candidates via swarm_pick_schema.append_picks()."),
        "count": len(candidates),
        "candidates": candidates,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="M-051 multi-model pick generator.")
    ap.add_argument("--symbols", required=True,
                    help="Comma-separated symbols, e.g. BTCUSDT,ETHUSDT.")
    ap.add_argument("--asset-class", default="CRYPTO")
    ap.add_argument("--timeframe", default="4H")
    ap.add_argument("--context", default="")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    cands = generate_candidates(symbols, args.asset_class, args.timeframe,
                                args.context)
    path = write_candidates(cands, args.out)
    print(f"[m051-pickgen] {len(cands)}/{len(symbols)} candidate(s) -> {path}")
    for c in cands:
        engines = sorted({v["underlying_model"] for v in c["models_consulted"]})
        print(f"  {c['symbol']} {c['direction']} "
              f"(agree {c['models_agreed']}/{c['models_voted']}, "
              f"engines: {', '.join(engines)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
