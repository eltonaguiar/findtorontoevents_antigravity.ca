"""
Optional hedge-fund-grade post-score filters for Smart Picks.

Thresholds live in config/hf_quality_gates.json. **Default: enabled=false**
so production behaviour is unchanged until you opt in.

See docs/HF_MERGED_EXECUTION_PLAN_2026-04-02.md and HEDGE_FUND_QUALITY_ROADMAP.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_PATH = _REPO_ROOT / "config" / "hf_quality_gates.json"

_FALLBACK: dict[str, Any] = {
    "version": 1,
    "enabled": False,
    "min_elite_score": 80,
    "min_risk_reward": 0.8,
    "max_risk_reward": 2.0,
    "max_signal_age_hours": 4,
    "max_signal_age_hours_copy_trader": 24,
    "min_mtf_agree_numerator": 2,
    "min_mtf_agree_denominator": 3,
    "trust_tier_order": [
        "UNKNOWN",
        "",
        "PROBATION",
        "SANDBOX",
        "WATCH",
        "VALIDATING",
        "RELIABLE",
        "PROVEN",
    ],
    "min_trust_tier": "WATCH",
    "require_macro_overlay_when_snapshot_present": True,
    "kelly_cap_fraction": 0.25,
}


def load_hf_quality_gates(path: Optional[Path] = None) -> dict[str, Any]:
    """Merge JSON over fallback; never raises."""
    out = json.loads(json.dumps(_FALLBACK))
    p = path or _DEFAULT_PATH
    if not p.is_file():
        return out
    try:
        raw = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        if isinstance(raw, dict):
            out.update(raw)
    except (json.JSONDecodeError, OSError, TypeError):
        pass
    return out


def _tier_index(order: list[str], tier: str) -> int:
    t = (tier or "").strip().upper()
    if t in order:
        return order.index(t)
    return 0


def _parse_mtf_ratio(s: Any) -> Optional[tuple[int, int]]:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return None
    text = str(s).strip()
    m = re.match(r"^(\d+)\s*/\s*(\d+)$", text)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _is_copy_trader_pick(source: Optional[dict]) -> bool:
    if not source or not isinstance(source, dict):
        return False
    strat = str(source.get("strategy", "") or "").lower()
    return "copy" in strat or "whale" in strat


def hf_smart_pick_post_score_reason(
    scored: dict[str, Any],
    source_pick: Optional[dict] = None,
    cfg: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """
    Return None if pick passes optional HF gates, else a short exclusion key
    for smart_picks_engine excluded_reasons.
    """
    cfg = cfg if cfg is not None else load_hf_quality_gates()
    if not cfg.get("enabled"):
        return None

    elite = float(scored.get("elite_score") or scored.get("score") or 0)
    if elite < float(cfg.get("min_elite_score", 80)):
        return "hf_gate_elite"

    rr = float(scored.get("rr_ratio") or scored.get("risk_reward") or scored.get("rr") or 0)
    min_rr = cfg.get("min_risk_reward", 0.8)
    max_rr = cfg.get("max_risk_reward")
    if rr > 0 and float(min_rr) > 0 and rr < float(min_rr):
        return "hf_gate_rr_low"
    if max_rr is not None and rr > float(max_rr) > 0:
        return "hf_gate_rr_high"

    age = float(scored.get("age_hours") or 999)
    max_age = float(
        cfg.get("max_signal_age_hours_copy_trader", 24)
        if _is_copy_trader_pick(source_pick)
        else cfg.get("max_signal_age_hours", 4)
    )
    if age > max_age:
        return "hf_gate_stale"

    order = list(cfg.get("trust_tier_order") or _FALLBACK["trust_tier_order"])
    min_tier = str(cfg.get("min_trust_tier") or "WATCH").strip().upper()
    pick_tier = str(scored.get("trust_tier") or (source_pick or {}).get("trust_tier") or "").strip().upper()
    if _tier_index(order, pick_tier) < _tier_index(order, min_tier):
        return "hf_gate_trust_tier"

    num_need = int(cfg.get("min_mtf_agree_numerator", 2))
    den_need = int(cfg.get("min_mtf_agree_denominator", 3))
    parsed = _parse_mtf_ratio(scored.get("mtf_agreement_ratio"))
    if parsed is not None:
        num, den = parsed
        if den > 0 and den == den_need and num < num_need:
            return "hf_gate_mtf"
    elif str(scored.get("asset_class", "")).upper() == "CRYPTO":
        rec = str(scored.get("mtf_recommendation") or "")
        if rec == "BLOCKED":
            return "hf_gate_mtf"
        strict = bool(cfg.get("mtf_strict_if_no_ratio"))
        if strict and scored.get("mtf_aligned") is False:
            return "hf_gate_mtf"

    if cfg.get("require_macro_overlay_when_snapshot_present"):
        snap_path = _REPO_ROOT / "alpha_engine" / "data" / "macro_factors_snapshot.json"
        if snap_path.is_file():
            try:
                snap = json.loads(snap_path.read_text(encoding="utf-8", errors="replace"))
            except (json.JSONDecodeError, OSError):
                snap = {}
            if isinstance(snap, dict) and snap.get("series"):
                ms = scored.get("macro_score")
                if ms is None:
                    return "hf_gate_macro_missing"
                try:
                    if float(ms) == 0.0 and snap.get("require_nonzero_macro_score"):
                        return "hf_gate_macro_zero"
                except (TypeError, ValueError):
                    return "hf_gate_macro_missing"

    return None


def suggested_kelly_notional_fraction(scored: dict[str, Any], cfg: Optional[dict[str, Any]] = None) -> float:
    """Conservative fractional Kelly cap (no fake edge); uses forward_wr if present."""
    cfg = cfg if cfg is not None else load_hf_quality_gates()
    cap = float(cfg.get("kelly_cap_fraction", 0.25))
    fwd = scored.get("strat_fwd_wr")
    if fwd is None:
        fwd = scored.get("forward_wr")
    try:
        p = float(fwd)
        if p > 1.0:
            p = p / 100.0
        if p <= 0 or p >= 1:
            return min(cap, 0.05)
        edge = max(p - 0.5, 0.0)
        k = min(edge * 2.0, cap)
        return max(0.01, min(k, cap))
    except (TypeError, ValueError):
        return min(cap, 0.05)
