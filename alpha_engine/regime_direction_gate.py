"""
Regime × direction gates — config/regime_direction_gates.json

Default enabled=false so aggregate-dashboard behaviour is unchanged until you
validate regime labels on actives (often missing / neutral).
"""

from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Mapping
from typing import Any, Optional, Set

_REPO = Path(__file__).resolve().parents[1]
_CFG = _REPO / "config" / "regime_direction_gates.json"
_LONG_DANGER = _REPO / "config" / "symbol_danger_long.json"

_CALIB_CACHE: dict[str, Any] | None = None
_LONG_DANGER_SYMS: frozenset[str] | None = None


def _load_regime_cfg() -> dict[str, Any]:
    global _CALIB_CACHE
    if _CALIB_CACHE is not None:
        return _CALIB_CACHE
    default: dict[str, Any] = {
        "enabled": False,
        "weak_regime_substrings": [],
        "major_symbols": [],
        "block_midcap_long_in_weak_regime": True,
        "exempt_if_strategy_symbol_affinity_positive": True,
        "exempt_if_strategy_in_proven_winners": True,
    }
    out = dict(default)
    if _CFG.is_file():
        try:
            raw = json.loads(_CFG.read_text(encoding="utf-8", errors="replace"))
            if isinstance(raw, dict):
                out.update(raw)
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    _CALIB_CACHE = out
    return out


def _load_long_danger() -> frozenset[str]:
    global _LONG_DANGER_SYMS
    if _LONG_DANGER_SYMS is not None:
        return _LONG_DANGER_SYMS
    syms: set[str] = set()
    if _LONG_DANGER.is_file():
        try:
            raw = json.loads(_LONG_DANGER.read_text(encoding="utf-8", errors="replace"))
            if isinstance(raw, dict) and raw.get("enabled", True):
                for s in raw.get("symbols") or []:
                    syms.add(str(s).upper().replace("-", "").replace("/", ""))
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    _LONG_DANGER_SYMS = frozenset(syms)
    return _LONG_DANGER_SYMS


def clear_caches_for_tests() -> None:
    global _CALIB_CACHE, _LONG_DANGER_SYMS
    _CALIB_CACHE = None
    _LONG_DANGER_SYMS = None


def _norm_sym(s: str) -> str:
    return (s or "").upper().replace("-", "").replace("/", "").replace("_", "")


def is_bull_regime(regime: str, cfg: Optional[dict[str, Any]] = None) -> bool:
    cfg = cfg if cfg is not None else _load_regime_cfg()
    r = (regime or "").lower().strip()
    for frag in cfg.get("bull_regime_substrings") or []:
        if str(frag).lower() in r:
            return True
    return False


def is_weak_regime(regime: str, cfg: Optional[dict[str, Any]] = None) -> bool:
    cfg = cfg if cfg is not None else _load_regime_cfg()
    r = (regime or "").lower().strip()
    for frag in cfg.get("weak_regime_substrings") or []:
        if str(frag).lower() in r:
            return True
    return False


def is_major_symbol(symbol: str, cfg: Optional[dict[str, Any]] = None) -> bool:
    cfg = cfg if cfg is not None else _load_regime_cfg()
    s = _norm_sym(symbol)
    majors = {_norm_sym(x) for x in (cfg.get("major_symbols") or [])}
    return s in majors


def midcap_long_blocked_in_weak_regime(
    pick: dict,
    symbol: str,
    direction: str,
    regime: str,
    *,
    proven_winners: Optional[Set[str] | Mapping[str, Any]] = None,
    strat_symbol_affinity: Optional[dict[str, dict[str, int]]] = None,
) -> Optional[str]:
    """
    Return rejection reason key, or None if allowed.
    proven_winners / strat_symbol_affinity: optional refs from smart_picks_engine.
    """
    cfg = _load_regime_cfg()
    if not cfg.get("enabled"):
        return None
    d = (direction or "").upper()
    if d not in ("LONG", "BUY"):
        return None
    if not cfg.get("block_midcap_long_in_weak_regime", True):
        return None
    if not is_weak_regime(regime, cfg):
        return None
    if is_major_symbol(symbol, cfg):
        return None

    strat = str(pick.get("strategy") or "")
    if cfg.get("exempt_if_strategy_in_proven_winners") and proven_winners:
        _keys = (
            proven_winners.keys()
            if isinstance(proven_winners, Mapping)
            else proven_winners
        )
        if strat in _keys:
            return None
    if cfg.get("exempt_if_strategy_symbol_affinity_positive") and strat_symbol_affinity:
        boost = strat_symbol_affinity.get(strat, {}).get(symbol, 0)
        if isinstance(boost, (int, float)) and boost > 0:
            return None

    return "regime_midcap_long_weak"


def long_danger_symbol_block(symbol: str, direction: str) -> Optional[str]:
    """Hard block LONG on symbols in symbol_danger_long.json."""
    d = (direction or "").upper()
    if d not in ("LONG", "BUY"):
        return None
    s = _norm_sym(symbol)
    if s in _load_long_danger():
        return "symbol_danger_long"
    return None


def cross_book_position_multiplier(pick: dict) -> float:
    """
    When the same symbol+direction is duplicated across books, scale size down.
    Requires upstream to set e.g. pick['correlated_book_count'] (int >=1).
    """
    n = pick.get("correlated_book_count")
    if n is None:
        n = pick.get("duplicate_book_exposure")
    try:
        c = int(n)
    except (TypeError, ValueError):
        return 1.0
    if c <= 1:
        return 1.0
    return 1.0 / float(c)


def weak_regime_short_bonus_points(
    symbol: str, direction: str, regime: str
) -> int:
    """Optional score bonus for alt SHORT in weak regime (0 unless configured)."""
    cfg = _load_regime_cfg()
    if not cfg.get("enabled"):
        return 0
    bonus = int(cfg.get("weak_regime_short_score_bonus", 0) or 0)
    if bonus <= 0:
        return 0
    if (direction or "").upper() not in ("SHORT", "SELL"):
        return 0
    if not is_weak_regime(regime, cfg):
        return 0
    s = _norm_sym(symbol)
    alts = {_norm_sym(x) for x in (cfg.get("alt_short_boost_symbols") or [])}
    if s not in alts:
        return 0
    return bonus


def bull_regime_short_penalty_points(direction: str, regime: str) -> int:
    """Negative score delta for SHORT in bull regime (0 unless configured)."""
    cfg = _load_regime_cfg()
    if not cfg.get("enabled"):
        return 0
    pen = int(cfg.get("bull_regime_short_score_penalty", 0) or 0)
    if pen <= 0:
        return 0
    if (direction or "").upper() not in ("SHORT", "SELL"):
        return 0
    if not is_bull_regime(regime, cfg):
        return 0
    return -pen


def regime_direction_score_delta(symbol: str, direction: str, regime: str) -> int:
    return weak_regime_short_bonus_points(symbol, direction, regime) + bull_regime_short_penalty_points(
        direction, regime
    )
