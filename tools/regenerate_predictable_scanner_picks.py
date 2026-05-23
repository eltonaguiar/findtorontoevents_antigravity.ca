"""Auto-regenerate `ai_challenge_predictable` and `ai_challenge_scanner` curator picks.

Context (2026-04-18)
--------------------
The seven "AI Challenge" tournament curators went stale on 2026-04-12 because
Round 6 never shipped a generator. Of the seven, only two are purely data-driven
(not LLM-curated): **predictable** (highest ML score) and **scanner** (alpha
engine ML-ranked signals). Those two can be mechanically regenerated from the
live `alpha_engine/data/active_picks.json`, so this script does exactly that.

The five LLM curators (claude, grok, kimi_moonshot, antigravity, mercury) are
not regenerable here and are being retired separately in
`audit_trail/dashboard_generator.py::_HIDDEN_SYSTEMS`.

Output schema mirrors the existing stale files verbatim (top-level JSON array
of pick dicts) — no invented fields.

CLI
---
    python tools/regenerate_predictable_scanner_picks.py              # dry-run
    python tools/regenerate_predictable_scanner_picks.py --write      # commit
    python tools/regenerate_predictable_scanner_picks.py --verbose    # debug
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "alpha_engine" / "data" / "active_picks.json"
OUT_PREDICTABLE = REPO / "audit_dashboard" / "data" / "ai_challenge_predictable_active_picks.json"
OUT_SCANNER = REPO / "audit_dashboard" / "data" / "ai_challenge_scanner_active_picks.json"

# Strategy families produced by alpha_engine-ranked ML signals (the "scanner"
# curator's historical picks were all drawn from these families).
SCANNER_STRATEGY_PREFIXES = (
    "bollinger_keltner_squeeze",
    "kalman_filter",
    "mvrv_contrarian",
    "swing_structure",
    "entropy_regime",
    "ml_momentum",
    "cross_sectional_reversal",
)

PREDICTABLE_CURATOR = (
    "Most Predictable \u2014 Highest ML Score (auto-regenerated Round 6+)"
)
PREDICTABLE_METHODOLOGY = (
    "Auto-regenerated from alpha_engine active_picks.json. Simple ranking: "
    "top 3 crypto picks by raw ML confidence score, any direction. No human "
    "curation, no regime narrative. Round 6+ auto-pipeline after LLM tournament "
    "ended Apr 12 2026."
)

SCANNER_CURATOR = (
    "Alpha Engine Scanner \u2014 ML-Ranked Live Signals (auto-regenerated Round 6+)"
)
SCANNER_METHODOLOGY = (
    "Auto-regenerated from alpha_engine active_picks.json. Top 3 crypto picks "
    "from alpha_engine's ranked ML strategies (Bollinger-Keltner squeeze, "
    "Kalman filter, MVRV contrarian, swing structure, entropy regime, ML "
    "momentum composite). Round 6+ auto-pipeline."
)


def _load_source() -> list[dict[str, Any]]:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing source: {SOURCE}")
    with SOURCE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Source {SOURCE} is not a JSON array")
    return data


def _crypto_only(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for p in picks:
        if not isinstance(p, dict):
            continue
        cat = str(p.get("category", "")).lower()
        if cat and cat != "crypto":
            continue
        sym = str(p.get("symbol", ""))
        # Fallback: USDT-suffixed symbols are almost always crypto
        if not cat and not sym.endswith(("USDT", "USD", "BTC", "ETH")):
            continue
        out.append(p)
    return out


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x) if x is not None and x != "" else default
    except Exception:
        return default


def _rank_by_ml_score(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        picks,
        key=lambda p: (
            _as_float(p.get("ml_score")),
            _as_float(p.get("confidence")),
        ),
        reverse=True,
    )


def _shape_pick(p: dict[str, Any], *, rank: int, curator: str, methodology: str,
                now_iso: str) -> dict[str, Any]:
    """Project a live alpha_engine pick into the ai_challenge stale-file schema."""
    direction = str(p.get("direction") or ("LONG" if str(p.get("signal_type", "BUY")).upper() == "BUY" else "SHORT"))
    sig_type = str(p.get("signal_type") or ("BUY" if direction.upper() == "LONG" else "SELL"))
    rationale_bits = []
    if p.get("reason"):
        rationale_bits.append(str(p["reason"]))
    if p.get("confluence_reason"):
        rationale_bits.append(str(p["confluence_reason"]))
    return {
        "symbol": p.get("symbol"),
        "direction": direction.upper(),
        "signal_type": sig_type.upper(),
        "entry_price": _as_float(p.get("entry_price")),
        "take_profit": _as_float(p.get("take_profit")),
        "stop_loss": _as_float(p.get("stop_loss")),
        "confidence": _as_float(p.get("confidence")),
        "strategy": p.get("strategy", ""),
        "status": "OPEN",
        "outcome": "PENDING",
        "pnl_pct": 0.0,
        "round": 6,
        "rank": rank,
        "curator": curator,
        "methodology": methodology,
        "rationale": " | ".join(rationale_bits) or f"Auto-selected rank {rank} by ML score.",
        "statistical_basis": "",
        "risk_reward": _as_float(p.get("risk_reward")),
        "generated_at": now_iso,
        "ml_score": _as_float(p.get("ml_score")),
    }


def build_predictable(source: list[dict[str, Any]], now_iso: str) -> list[dict[str, Any]]:
    crypto = _crypto_only(source)
    ranked = _rank_by_ml_score(crypto)
    top = ranked[:3]
    return [_shape_pick(p, rank=i + 1, curator=PREDICTABLE_CURATOR,
                        methodology=PREDICTABLE_METHODOLOGY, now_iso=now_iso)
            for i, p in enumerate(top)]


def build_scanner(source: list[dict[str, Any]], now_iso: str) -> list[dict[str, Any]]:
    crypto = _crypto_only(source)
    filtered = [
        p for p in crypto
        if any(str(p.get("strategy", "")).lower().startswith(pref)
               for pref in SCANNER_STRATEGY_PREFIXES)
    ]
    # If no strategy-family matches, fall back to highest ML score crypto
    # (so the file is never empty when source has data).
    pool = filtered if filtered else crypto
    ranked = _rank_by_ml_score(pool)
    top = ranked[:3]
    return [_shape_pick(p, rank=i + 1, curator=SCANNER_CURATOR,
                        methodology=SCANNER_METHODOLOGY, now_iso=now_iso)
            for i, p in enumerate(top)]


def _write(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="Write output files (default: dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="Print what would be written (default)")
    ap.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = ap.parse_args(argv)

    write_mode = args.write and not args.dry_run

    try:
        source = _load_source()
    except Exception as e:
        print(f"[ERROR] Could not load source picks: {e}", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"[INFO] Loaded {len(source)} picks from {SOURCE}")

    now_iso = datetime.now(timezone.utc).isoformat()
    predictable = build_predictable(source, now_iso)
    scanner = build_scanner(source, now_iso)

    if args.verbose or not write_mode:
        print(f"[predictable] {len(predictable)} picks "
              f"({', '.join(p['symbol'] for p in predictable) if predictable else 'none'})")
        print(f"[scanner]     {len(scanner)} picks "
              f"({', '.join(p['symbol'] for p in scanner) if scanner else 'none'})")

    if not write_mode:
        print("[DRY-RUN] No files written. Pass --write to commit.")
        if args.verbose:
            print(json.dumps({"predictable": predictable, "scanner": scanner}, indent=2))
        return 0

    if not predictable and not scanner:
        print("[WARN] No picks derived from source — refusing to overwrite existing files.",
              file=sys.stderr)
        return 2

    if predictable:
        _write(OUT_PREDICTABLE, predictable)
        print(f"[OK] Wrote {len(predictable)} picks -> {OUT_PREDICTABLE}")
    if scanner:
        _write(OUT_SCANNER, scanner)
        print(f"[OK] Wrote {len(scanner)} picks -> {OUT_SCANNER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
