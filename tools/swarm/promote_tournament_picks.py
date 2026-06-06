#!/usr/bin/env python3
"""M-052 — promote AI tournament consensus picks into swarm_picks.json.

Reads ``data/ai_tournament/submissions/*.json``, groups picks by (symbol,
direction), and promotes picks that appear in >=2 submissions with the
same direction into the live ``swarm_picks.json`` store.

This revives the Swarm Picks tab — instead of calling expensive multi-model
LLM APIs in CI, it reuses the AI tournament submissions that are already
generated daily by multiple models.

Usage (standalone):
    python tools/swarm/promote_tournament_picks.py

Usage (in CI — swarm-pick-review.yml):
    The script is idempotent (skip existing pick_ids). Safe to run daily.

Design:
    - Reads submissions from the last 3 days to catch weekend gaps
    - Minimum 2-model consensus to promote (configurable via MIN_CONSENSUS)
    - Idempotent: duplicate pick_ids are skipped by swarm_pick_schema.append_picks()
    - Entry price / TP / SL derived from tournament metadata or left as None
      for operator review; resolved by outcome_resolver_swarm.py nightly
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
SUBMISSIONS_DIR = ROOT / "data" / "ai_tournament" / "submissions"
SWARM_STORE = ROOT / "audit_dashboard" / "data" / "swarm_picks.json"

MIN_CONSENSUS = 2  # minimum models agreeing on same (symbol, direction)
MAX_AGE_DAYS = 3    # only consider submissions from the last N days

# Tournament submissions use horizon labels (7d, 14d, equity_default) that are
# not in swarm_pick_schema.VALID_TIMEFRAMES — map them before append.
_TOURNEY_TF_MAP = {
    "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1H", "1H": "1H", "4h": "4H", "4H": "4H",
    "1d": "1D", "1D": "1D", "1w": "1W", "1W": "1W",
    "1m": "1M", "1M": "1M", "3m": "3M", "3M": "3M",
    "6m": "6M", "6M": "6M", "1y": "1Y", "1Y": "1Y",
    "7d": "1W", "14d": "1M", "28d": "1M", "30d": "1M", "60d": "3M",
    "equity_default": "1D",
}


def normalize_timeframe(raw: Any) -> str:
    """Map tournament horizon labels to swarm_pick_schema timeframes."""
    key = str(raw or "").strip()
    if not key:
        return "4H"
    mapped = _TOURNEY_TF_MAP.get(key) or _TOURNEY_TF_MAP.get(key.lower())
    if mapped:
        return mapped
    # Fallback: day-count horizons → weekly/monthly buckets
    if key.endswith("d") and key[:-1].isdigit():
        days = int(key[:-1])
        if days <= 7:
            return "1W"
        if days <= 30:
            return "1M"
        return "3M"
    return "4H"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cutoff_date() -> str:
    """Return ISO date string for MAX_AGE_DAYS days ago."""
    dt = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    return dt.strftime("%Y%m%d")


def load_recent_submissions() -> list[dict[str, Any]]:
    """Load tournament submissions from the last MAX_AGE_DAYS days.

    Each submission is a dict with keys: model_id, provider, submitted_at,
    picks (list of {symbol, direction, entry, tp, sl, ...}).
    """
    if not SUBMISSIONS_DIR.exists():
        return []

    cutoff = _cutoff_date()
    submissions: list[dict[str, Any]] = []
    for fpath in sorted(SUBMISSIONS_DIR.glob("*.json")):
        # Filenames like: alpha_engine_20260523.json, grok3_20260525.json
        stem = fpath.stem
        # Extract date suffix (last 8 digits if present)
        date_part = stem[-8:] if len(stem) >= 8 and stem[-8:].isdigit() else ""
        if date_part and date_part >= cutoff:
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                submissions.append(data)
            except (json.JSONDecodeError, OSError):
                continue
    return submissions


def derive_asset_class(symbol: str) -> str:
    """Derive asset class from symbol suffix pattern."""
    s = symbol.upper()
    if s.endswith("USDT") or s.endswith("USD") or s.endswith("BTC"):
        return "CRYPTO"
    if "=X" in s or any(s.startswith(p) for p in ("EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF")):
        return "FOREX"
    if s in ("GC=F", "CL=F", "NG=F", "SI=F", "HG=F", "ZC=F", "ZS=F", "ZW=F", "CT=F"):
        return "COMMODITY"
    if s in ("SPY", "QQQ", "IWM", "DIA", "TLT", "GLD", "SLV", "VIX"):
        return "ETF"
    return "EQUITY"


def promote_consensus_picks(
    submissions: list[dict[str, Any]],
    min_consensus: int = MIN_CONSENSUS,
    store_path: Path = SWARM_STORE,
) -> dict[str, int]:
    """Promote picks with >=min_consensus model agreement into swarm_picks.json.

    Returns: {"promoted": int, "skipped": int, "total_promoted": int}
    """
    from tools.swarm.swarm_pick_schema import append_picks  # noqa: E402

    # ── Phase 1: Group picks by (symbol, direction) across submissions ──
    consensus: dict[tuple[str, str], dict[str, Any]] = {}
    for sub in submissions:
        model_id = sub.get("model_id", sub.get("provider", "unknown"))
        picks = sub.get("picks", [])
        if not isinstance(picks, list):
            continue
        for pick in picks:
            sym = str(pick.get("symbol", "")).strip().upper()
            d = str(pick.get("direction", "LONG")).strip().upper()
            if not sym or d not in ("LONG", "SHORT"):
                continue
            key = (sym, d)
            if key not in consensus:
                consensus[key] = {
                    "symbol": sym,
                    "direction": d,
                    "models": set(),
                    "providers": set(),
                    "entry_prices": [],
                    "tps": [],
                    "sls": [],
                    "timeframes": [],
                    "rationales": [],
                }
            entry = consensus[key]
            entry["models"].add(model_id)
            entry["providers"].add(sub.get("provider", model_id))
            if pick.get("entry") or pick.get("entry_price"):
                entry["entry_prices"].append(float(pick.get("entry") or pick.get("entry_price")))
            if pick.get("tp") or pick.get("take_profit"):
                entry["tps"].append(float(pick.get("tp") or pick.get("take_profit")))
            if pick.get("sl") or pick.get("stop_loss"):
                entry["sls"].append(float(pick.get("sl") or pick.get("stop_loss")))
            if pick.get("timeframe"):
                entry["timeframes"].append(normalize_timeframe(pick["timeframe"]))
            if sub.get("strategy_rationale"):
                entry["rationales"].append(str(sub["strategy_rationale"])[:200])

    # ── Phase 2: Build swarm pick records for consensus entries ──
    new_picks: list[dict[str, Any]] = []
    for (sym, d), entry in consensus.items():
        if len(entry["models"]) < min_consensus:
            continue

        # Compute median entry/TP/SL from collected values
        def _median(vals: list[float]) -> float | None:
            if not vals:
                return None
            svals = sorted(vals)
            mid = len(svals) // 2
            return svals[mid] if len(svals) % 2 else (svals[mid - 1] + svals[mid]) / 2

        entry_price = _median(entry["entry_prices"])

        # Skip picks without valid entry prices — swarm_pick_schema requires
        # tp > entry > sl (strict inequality), and entry=0 triggers SchemaError.
        if not entry_price or entry_price <= 0:
            continue

        tp = _median(entry["tps"]) if entry["tps"] else None
        sl = _median(entry["sls"]) if entry["sls"] else None
        asset_class = derive_asset_class(sym)
        timeframe = (
            max(set(entry["timeframes"]), key=entry["timeframes"].count)
            if entry["timeframes"] else "4H"
        )
        timeframe = normalize_timeframe(timeframe)

        models_list = sorted(entry["models"])
        n_models = len(models_list)

        # Build models_consulted (lightweight — no full vote metadata since
        # tournament submissions don't carry per-engine confidence)
        models_consulted = []
        for m in models_list:
            models_consulted.append({
                "name": m,
                "role": "tournament",
                "underlying_model": m,
                "vote": d,
                "confidence_0_100": 60,  # consensus default
                "timeframe": timeframe,
                "justification_summary": f"AI tournament consensus: {n_models} models agree on {d}",
            })

        consensus_score = n_models / max(n_models + 1, 2)

        # Derive tier
        if n_models >= 4:
            tier = "strong"
        elif n_models >= 3:
            tier = "moderate"
        elif n_models >= 2:
            tier = "moderate"
        else:
            tier = "single"

        pick_id = f"tourney-{uuid.uuid4().hex[:12]}"
        new_picks.append({
            "pick_id": pick_id,
            "created_at": _utc_now(),
            "session_id": f"tournament-consensus-{_utc_now()[:10]}",
            "account": "theswarm",
            "symbol": sym,
            "direction": d,
            "entry": entry_price or 0,
            "tp": tp or (entry_price * 1.05 if entry_price and d == "LONG" else entry_price * 0.95 if entry_price else 0),
            "sl": sl or (entry_price * 0.95 if entry_price and d == "LONG" else entry_price * 1.05 if entry_price else 0),
            "qty": 1,
            "qty_unit": "asset_units",
            "timeframe": timeframe,
            "asset_class": asset_class,
            "consensus_tier": tier,
            "models_consulted": models_consulted,
            "models_agreed": n_models,
            "models_voted": n_models,
            "consensus_score": round(consensus_score, 4),
            "regime_at_entry": {"btc_regime": "UNK", "source": "tournament_consensus"},
            "outcome": None,
            "pattern_tags": [],
            "_source": "promote_tournament_picks",
            "_rationale": "; ".join(entry["rationales"][:3]) if entry["rationales"] else "",
        })

    # ── Phase 3: Append to swarm_picks.json ──
    if not new_picks:
        print("[promote_tournament] No consensus picks found (threshold >= "
              f"{min_consensus} models)")
        return {"promoted": 0, "skipped": 0, "total_promoted": 0}

    result = append_picks(store_path, new_picks)
    promoted = result["added"]
    skipped = result["skipped"]
    total = result["total"]

    print(f"[promote_tournament] Promoted {promoted} new picks, "
          f"skipped {skipped} duplicates, store now has {total} total")

    for p in new_picks[:10]:
        if promoted > 0:
            models = [m['name'] for m in p['models_consulted']]
            print(f"  {p['symbol']} {p['direction']} "
                  f"({p['models_agreed']} models: {', '.join(sorted(models))}) "
                  f"tier={p['consensus_tier']}")

    return {"promoted": promoted, "skipped": skipped, "total_promoted": total}


def main() -> int:
    submissions = load_recent_submissions()
    if not submissions:
        print("[promote_tournament] No recent tournament submissions found "
              f"(last {MAX_AGE_DAYS}d). Nothing to promote.")
        return 0

    print(f"[promote_tournament] Loaded {len(submissions)} submissions "
          f"from last {MAX_AGE_DAYS}d")
    for s in submissions:
        model = s.get("model_id", "?")
        picks = s.get("picks", [])
        print(f"  {model}: {len(picks) if isinstance(picks, list) else 'N/A'} picks")

    result = promote_consensus_picks(submissions)
    return 0 if result["promoted"] >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
