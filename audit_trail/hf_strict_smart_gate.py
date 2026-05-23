"""
Optional strict Smart Picks rules for /audit (dashboard JSON).

Loads ``config/hf_audit_smart_strict.json`` (default ``enabled``: false).
Mirrors HF action plan §2: elite, R:R, freshness, trust WATCH+, MTF 2/3, macro when snapshot populated.

Stdlib only. Used from ``quality_gates._smart_gate_fail_after_active``.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_REPO = Path(__file__).resolve().parents[1]
_CONFIG = _REPO / "config" / "hf_audit_smart_strict.json"
_MACRO_SNAP = _REPO / "alpha_engine" / "data" / "macro_factors_snapshot.json"

_FALLBACK: dict[str, Any] = {
    "version": 1,
    "enabled": False,
    "apply_asset_classes": ["CRYPTO"],
    "min_elite_score": 80,
    "min_risk_reward": 1.2,  # Data: RR 1.0-1.5 = 56% WR (was 2.5 = 25% WR)
    "max_signal_age_hours": 4,
    "max_signal_age_hours_copy_trader": 24,
    "min_trust_tier": "WATCH",
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
    "require_mtf_two_of_three": True,
    "mtf_strict_if_no_ratio": False,
    "require_macro_score_when_snapshot_present": True,
}


def load_hf_audit_smart_strict(path: Optional[Path] = None) -> dict[str, Any]:
    out = json.loads(json.dumps(_FALLBACK))
    p = path or _CONFIG
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
    if s is None or isinstance(s, (int, float)):
        return None
    m = re.match(r"^(\d+)\s*/\s*(\d+)$", str(s).strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _is_copy_trader_pick(pick: dict[str, Any]) -> bool:
    strat = str(pick.get("strategy", "") or "").lower()
    return "copy" in strat or "whale" in strat


def _pick_rr(pick: dict[str, Any]) -> float:
    for k in ("rr", "rr_ratio", "risk_reward"):
        v = pick.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return 0.0


def _pick_age_hours(pick: dict[str, Any], now: datetime) -> Optional[float]:
    for key in ("open_time", "timestamp", "created_at", "entry_date"):
        raw = pick.get(key)
        if not raw:
            continue
        try:
            s = str(raw).replace("Z", "+00:00")
            if "T" not in s and len(s) >= 10:
                s = s[:10] + "T00:00:00+00:00"
            ts = datetime.fromisoformat(s)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return max(0.0, (now - ts).total_seconds() / 3600.0)
        except (ValueError, TypeError, OSError):
            continue
    return None


def strict_smart_gate_fail_reason(
    pick: dict[str, Any],
    cfg: Optional[dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> Optional[str]:
    """
    Return a short failure code for Smart funnel, or None if strict mode off / pass.
    """
    cfg = cfg if cfg is not None else load_hf_audit_smart_strict()
    if not cfg.get("enabled"):
        return None

    ac = str(pick.get("asset_class", "CRYPTO") or "CRYPTO").upper()
    apply_ac = [str(x).upper() for x in (cfg.get("apply_asset_classes") or ["CRYPTO"])]
    if ac not in apply_ac:
        return None

    now = now or datetime.now(timezone.utc)

    elite = float(pick.get("elite_score") or pick.get("score") or 0)
    if elite < float(cfg.get("min_elite_score", 80)):
        return "audit_strict_elite"

    rr = _pick_rr(pick)
    if rr > 0 and rr < float(cfg.get("min_risk_reward", 2.5)):
        return "audit_strict_rr"

    age = _pick_age_hours(pick, now)
    if age is not None:
        max_age = float(
            cfg.get("max_signal_age_hours_copy_trader", 24)
            if _is_copy_trader_pick(pick)
            else cfg.get("max_signal_age_hours", 4)
        )
        if age > max_age:
            return "audit_strict_stale"

    order = list(cfg.get("trust_tier_order") or _FALLBACK["trust_tier_order"])
    min_tier = str(cfg.get("min_trust_tier") or "WATCH").strip().upper()
    pick_tier = str(pick.get("trust_tier") or "").strip().upper()
    if _tier_index(order, pick_tier) < _tier_index(order, min_tier):
        return "audit_strict_trust"

    if cfg.get("require_mtf_two_of_three"):
        num_need, den_need = 2, 3
        parsed = _parse_mtf_ratio(pick.get("mtf_agreement_ratio"))
        if parsed is not None:
            num, den = parsed
            if den == den_need and num < num_need:
                return "audit_strict_mtf"
        else:
            rec = str(pick.get("mtf_recommendation") or "")
            if rec == "BLOCKED":
                return "audit_strict_mtf"
            if cfg.get("mtf_strict_if_no_ratio") and pick.get("mtf_aligned") is False:
                return "audit_strict_mtf"
            bt = pick.get("technical_buy_tfs")
            st = pick.get("technical_sell_tfs")
            if isinstance(bt, (int, float)) and isinstance(st, (int, float)):
                direction = str(pick.get("direction", "")).upper()
                if direction in ("LONG", "BUY") and int(bt) < 2:
                    return "audit_strict_mtf"
                if direction in ("SHORT", "SELL") and int(st) < 2:
                    return "audit_strict_mtf"

    if cfg.get("require_macro_score_when_snapshot_present") and _MACRO_SNAP.is_file():
        try:
            snap = json.loads(_MACRO_SNAP.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            snap = {}
        if isinstance(snap, dict) and snap.get("series"):
            ms = pick.get("macro_score")
            if ms is None:
                return "audit_strict_macro"
            try:
                float(ms)
            except (TypeError, ValueError):
                return "audit_strict_macro"

    return None
