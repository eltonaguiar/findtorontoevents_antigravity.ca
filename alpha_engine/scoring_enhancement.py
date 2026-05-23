"""
Supplementary boost-based ranking scores for audit dashboard picks.

Adds ``enhanced_score`` (0–100), ``enhanced_score_breakdown``, and ``quality_tier_label``
to picks without removing or replacing ``passes_active_gate`` / ``passes_smart_gate``.

Config: ``config/scoring_enhancement.json`` (provenance in ``source_note``).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parents[1]
_CFG_PATH = _REPO / "config" / "scoring_enhancement.json"


def _load_cfg() -> Dict[str, Any]:
    if not _CFG_PATH.is_file():
        return {}
    try:
        return json.loads(_CFG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("scoring_enhancement config unreadable: %s", e)
        return {}


def forward_wr_score(
    fwd_wr: Optional[float],
    fwd_trades: int,
    historical_wr: Optional[float],
    shrinkage_k: int,
    universe_prior: float,
) -> float:
    """Map shrunken forward/history WR to 0–30 (boost-only; no rejection)."""
    if fwd_wr is not None and fwd_wr > 0:
        wr = fwd_wr if fwd_wr <= 1.0 else fwd_wr / 100.0
        n = max(0, int(fwd_trades))
        if n >= shrinkage_k:
            shrunken = wr
        else:
            shrunken = (wr * n + universe_prior * shrinkage_k) / (n + shrinkage_k)
    elif historical_wr is not None and historical_wr > 0:
        hw = historical_wr if historical_wr <= 1.0 else historical_wr / 100.0
        shrunken = hw * 0.3 + universe_prior * 0.7
    else:
        shrunken = universe_prior

    if shrunken >= 0.70:
        return 30.0
    if shrunken >= 0.65:
        return 25.0 + (shrunken - 0.65) * 100.0
    if shrunken >= 0.55:
        return 18.0 + (shrunken - 0.55) * 70.0
    if shrunken >= 0.50:
        return 10.0 + (shrunken - 0.50) * 160.0
    if shrunken >= 0.40:
        return 3.0 + (shrunken - 0.40) * 70.0
    return max(0.0, shrunken * 7.5)


def confidence_score(confidence: float) -> float:
    """Parabolic 0–15 peak ~0.67 (humble sweet spot vs extreme confidence)."""
    if confidence <= 0:
        return 0.0
    deviation = (confidence - 0.67) / 0.67
    raw = 1.0 - deviation * deviation
    return max(0.0, min(15.0, raw * 15.0))


def _strategy_prior(strategy_name: str, priors: Dict[str, Any]) -> float:
    sl = strategy_name.lower().strip()
    best = float(priors.get("default", 0.45))
    for key, val in priors.items():
        if key == "default":
            continue
        if key.lower() in sl:
            try:
                best = float(val)
            except (TypeError, ValueError):
                pass
    return best


def track_record_score(
    strategy_name: str,
    historical_wr: Optional[float],
    historical_trades: int,
    priors: Dict[str, Any],
    shrinkage_k: int,
) -> float:
    prior = _strategy_prior(strategy_name, priors)
    if historical_wr is not None and historical_trades > 0:
        wr = historical_wr if historical_wr <= 1.0 else historical_wr / 100.0
        n = max(0, int(historical_trades))
        if n >= shrinkage_k:
            shrunken = wr
        else:
            shrunken = (wr * n + prior * shrinkage_k) / (n + shrinkage_k)
    else:
        shrunken = prior
    return max(0.0, min(15.0, (shrunken - 0.30) * 60.0))


def strat_symbol_affinity_boost(
    strategy: str, symbol: str, rows: List[Dict[str, Any]]
) -> float:
    sl = strategy.lower()
    su = symbol.upper().strip()
    best = 0.0
    for row in rows:
        sub = str(row.get("strategy_substring", "") or "").lower()
        sym = str(row.get("symbol", "") or "").upper().strip()
        if not sub or sub not in sl:
            continue
        if sym and sym != su:
            continue
        try:
            best = max(best, float(row.get("boost", 0)))
        except (TypeError, ValueError):
            pass
    return best


def regime_alignment_score(direction: str, regime: str) -> float:
    du = (direction or "LONG").upper()
    rl = (regime or "neutral").lower()
    if rl in ("bull", "trending_up", "strong_bull", "uptrend"):
        return 20.0 if du in ("LONG", "BUY") else 5.0
    if rl in ("bear", "trending_down", "strong_bear", "downtrend"):
        return 20.0 if du in ("SHORT", "SELL") else 5.0
    if rl in ("neutral", "ranging", "chop", "sideways"):
        return 10.0
    return 8.0


def time_of_day_score(hour_utc: int, best: List[int], worst: List[int]) -> float:
    if hour_utc in best:
        return 5.0
    if hour_utc in worst:
        return -3.0
    return 1.0


def freshness_score(age_hours: Optional[float]) -> float:
    if age_hours is None:
        return 3.0
    ah = float(age_hours)
    if ah < 1:
        return 10.0
    if ah < 4:
        return 8.0
    if ah < 12:
        return 6.0
    if ah < 24:
        return 4.0
    if ah < 48:
        return 2.0
    return 1.0


def consensus_score(agreement_count: int) -> float:
    ac = int(agreement_count)
    if ac <= 1:
        return 0.0
    if 2 <= ac <= 3:
        return 5.0
    if 4 <= ac <= 6:
        return 3.0
    return 1.0


def _pick_regime(pick: Dict[str, Any]) -> str:
    for key in ("regime", "btc_regime", "market_regime"):
        v = pick.get(key)
        if v:
            return str(v)
    extra = pick.get("extra") or {}
    if isinstance(extra, dict):
        for key in ("regime", "fast_regime", "btc_regime"):
            v = extra.get(key)
            if v:
                return str(v)
    return "neutral"


def _pick_age_hours(pick: Dict[str, Any]) -> Optional[float]:
    if pick.get("age_hours") is not None:
        try:
            return float(pick["age_hours"])
        except (TypeError, ValueError):
            pass
    return None


def compute_enhanced_score(
    pick: Dict[str, Any],
    cfg: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> Tuple[float, Dict[str, Any], str]:
    """Return (enhanced_score_0_100, breakdown, quality_tier_label)."""
    cfg = cfg if cfg is not None else _load_cfg()
    if not cfg:
        return 0.0, {}, "unconfigured"

    k_fwd = int(cfg.get("shrinkage_forward_k", 20))
    k_tr = int(cfg.get("shrinkage_track_k", 15))
    prior_u = float(cfg.get("universe_prior_wr", 0.45))
    best_h = [int(x) for x in cfg.get("best_hours_utc", [22, 23, 0, 1, 5, 6])]
    worst_h = [int(x) for x in cfg.get("worst_hours_utc", [2, 8, 13, 20])]
    affinity_rows = cfg.get("strat_symbol_affinity") or []
    priors = cfg.get("strategy_priors") or {"default": 0.45}

    strategy = str(pick.get("strategy") or "")
    symbol = str(pick.get("symbol") or "")
    direction = str(pick.get("direction") or "LONG")
    regime = _pick_regime(pick)
    try:
        confidence = float(pick.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0

    fwd_wr = pick.get("strat_fwd_wr")
    if fwd_wr is None:
        fwd_wr = pick.get("forward_wr")
    if fwd_wr is not None:
        try:
            fwd_wr = float(fwd_wr)
        except (TypeError, ValueError):
            fwd_wr = None

    fwd_trades = int(
        float(pick.get("strat_fwd_trades") or pick.get("forward_trades") or 0)
    )

    hist_wr = pick.get("history_wr_bayes", pick.get("history_wr"))
    if hist_wr is not None:
        try:
            hist_wr = float(hist_wr)
        except (TypeError, ValueError):
            hist_wr = None
    hist_trades = int(float(pick.get("history_trades") or 0))

    agreement = pick.get("agreement_count", pick.get("agreeing_systems_count"))
    if agreement is None:
        agreement = pick.get("source_count")
    try:
        agreement_n = int(float(agreement)) if agreement is not None else 1
    except (TypeError, ValueError):
        agreement_n = 1

    dt = now or datetime.now(timezone.utc)
    hour_utc = dt.hour

    fw_s = forward_wr_score(fwd_wr, fwd_trades, hist_wr, k_fwd, prior_u)
    aff_s = strat_symbol_affinity_boost(strategy, symbol, affinity_rows)
    reg_s = regime_alignment_score(direction, regime)
    tr_s = track_record_score(strategy, hist_wr, hist_trades, priors, k_tr)
    conf_s = confidence_score(confidence)
    fresh_s = freshness_score(_pick_age_hours(pick))
    cons_s = consensus_score(agreement_n)
    tod_s = time_of_day_score(hour_utc, best_h, worst_h)

    raw_total = fw_s + aff_s + reg_s + tr_s + conf_s + fresh_s + cons_s + tod_s
    enhanced = min(100.0, max(0.0, raw_total))

    try:
        elite = float(pick.get("elite_score") or 0)
    except (TypeError, ValueError):
        elite = 0.0
    if elite > 0:
        enhanced = enhanced * 0.9 + min(100.0, elite) * 0.1

    enhanced = round(enhanced, 1)

    if enhanced >= 80:
        tier = "ELITE"
    elif enhanced >= 65:
        tier = "HIGH"
    elif enhanced >= 45:
        tier = "STANDARD"
    elif enhanced >= 25:
        tier = "LOW"
    else:
        tier = "SPECULATIVE"

    breakdown = {
        "forward_wr": round(fw_s, 1),
        "strat_symbol_affinity": round(aff_s, 1),
        "regime_alignment": round(reg_s, 1),
        "track_record": round(tr_s, 1),
        "confidence_sweet_spot": round(conf_s, 1),
        "freshness": round(fresh_s, 1),
        "consensus": round(cons_s, 1),
        "time_of_day_utc": round(tod_s, 1),
        "raw_total_pre_cap": round(raw_total, 1),
        "elite_blend_applied": elite > 0,
    }
    return enhanced, breakdown, tier


def enrich_pick_with_enhanced_score(
    pick: Dict[str, Any],
    cfg: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> None:
    score, breakdown, tier = compute_enhanced_score(pick, cfg=cfg, now=now)
    pick["enhanced_score"] = score
    pick["enhanced_score_breakdown"] = breakdown
    pick["quality_tier_label"] = tier


def apply_enhanced_scoring_to_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Mutate pick dicts with enhanced fields; add ``picks.enhanced_ranked`` slice."""
    cfg = _load_cfg()
    if not cfg:
        logger.info("scoring_enhancement: no config, skipping")
        return payload

    picks = payload.get("picks") or {}
    now = datetime.now(timezone.utc)
    for key in ("active", "smart_picks", "recent_closed", "active_raw"):
        lst = picks.get(key)
        if isinstance(lst, list):
            for p in lst:
                if isinstance(p, dict):
                    enrich_pick_with_enhanced_score(p, cfg=cfg, now=now)

    active = picks.get("active") or []
    if isinstance(active, list) and active:
        ranked = sorted(
            [p for p in active if isinstance(p, dict)],
            key=lambda x: float(x.get("enhanced_score") or 0),
            reverse=True,
        )[:50]
        picks["enhanced_ranked"] = ranked

    summary = payload.setdefault("summary", {})
    summary["enhanced_scoring"] = {
        "version": cfg.get("version", 1),
        "config_path": str(_CFG_PATH.relative_to(_REPO)).replace("\\", "/"),
        "active_count": len(active) if isinstance(active, list) else 0,
    }
    return payload


__all__ = [
    "apply_enhanced_scoring_to_payload",
    "compute_enhanced_score",
    "enrich_pick_with_enhanced_score",
    "forward_wr_score",
]
