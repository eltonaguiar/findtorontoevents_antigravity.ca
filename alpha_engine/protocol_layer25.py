"""Layer 2.5 pick-level gates (TESTING_PROTOCOL) — normalize + enforce floors.

Applies score/trust/confidence rules before paper-pilot or forward-test emission.
Does not hard-block score<40 when score is missing (Finding 9 phased rollout).
"""
from __future__ import annotations

from typing import Any


def _clamp_confidence(conf: float, direction: str) -> float:
    """Avoid toxic LONG+Conf>=0.90; cap production ceiling."""
    c = max(0.0, min(0.85, float(conf)))
    if direction.upper() in ("LONG", "BUY", "YES") and c >= 0.90:
        c = 0.85
    return round(c, 4)


def compute_score(confidence: float, trust: int, direction: str) -> int:
    """Map confidence + trust to audit score (40–85), Layer 2.5 aligned."""
    base = int(confidence * 100)
    if direction.upper() in ("SHORT", "SELL", "NO"):
        base += 5  # SHORT base +5 per protocol
    if 0.75 <= confidence <= 0.79:
        base += 18  # sweet spot
    elif 0.60 <= confidence <= 0.69:
        base -= 12
    if confidence >= 0.90:
        base -= 20
    if 6 <= trust <= 7:
        base += 15
    return max(40, min(85, base))


def compute_trust(confidence: float, volume_confirmed: bool = False) -> int:
    """Trust 4–7 for LONGs; default 5."""
    t = 5
    if volume_confirmed:
        t = 6
    if confidence >= 0.72:
        t = min(7, t + 1)
    return max(4, min(7, t))


def normalize_pick_for_emitter(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Enrich raw strategy pick with entry/TP/SL, score, trust; drop toxic combos."""
    direction = str(raw.get("direction", "LONG")).upper()
    conf = _clamp_confidence(float(raw.get("confidence", 0.55)), direction)

    extra = raw.get("extra") or {}
    sym = str(raw.get("symbol", ""))
    entry = raw.get("entry_price")
    if entry is None:
        entry = extra.get("entry_price") or extra.get("price")
    if entry is None and "SI" in sym.upper():
        entry = extra.get("si_price")
    if entry is None and "GC" in sym.upper():
        entry = extra.get("gc_price")
    if entry is None:
        return None

    entry_f = float(entry)
    tp = raw.get("take_profit")
    sl = raw.get("stop_loss")
    fr = raw.get("forced_resolution") or {}
    tp_pct = float(fr.get("tp_pct", 2.0)) / 100.0 if fr.get("tp_pct", 0) > 1 else float(fr.get("tp_pct", 0.02))
    sl_pct = float(fr.get("sl_pct", 1.5)) / 100.0 if fr.get("sl_pct", 0) > 1 else float(fr.get("sl_pct", 0.015))

    if tp is None:
        if direction in ("LONG", "BUY", "YES"):
            tp = round(entry_f * (1 + tp_pct), 6)
        else:
            tp = round(entry_f * (1 - tp_pct), 6)
    if sl is None:
        if direction in ("LONG", "BUY", "YES"):
            sl = round(entry_f * (1 - sl_pct), 6)
        else:
            sl = round(entry_f * (1 + sl_pct), 6)

    vol_ok = bool(extra.get("volume_ratio", 0) >= 1.5 or extra.get("vol_ratio", 0) >= 1.5)
    trust = int(raw.get("trust") or compute_trust(conf, vol_ok))
    if direction in ("LONG", "BUY", "YES") and trust < 4:
        trust = 4

    score = int(raw.get("score") or compute_score(conf, trust, direction))
    if score < 40:
        return None
    if direction in ("LONG", "BUY", "YES") and conf >= 0.90:
        return None

    out = dict(raw)
    out["entry_price"] = entry_f
    out["take_profit"] = float(tp)
    out["stop_loss"] = float(sl)
    out["confidence"] = conf
    out["trust"] = trust
    out["score"] = score
    out.setdefault("forced_resolution", fr)
    out.setdefault(
        "methodology_v2_extensions",
        {
            "expected_slippage_bps": extra.get("expected_slippage_bps", 5),
            "regime_kill_switch": extra.get("regime_kill_switch", "regime_flip"),
            "max_reasonable_aum_usd": extra.get("max_reasonable_aum_usd", 500000),
            "cross_strategy_corr_risk": extra.get("cross_strategy_corr_risk", "medium"),
            "live_vs_paper_slippage_delta_bps": "to_be_tracked",
            "reward_to_risk_floor": extra.get("reward_to_risk_floor", 1.2),
            "next_bar_open_fill": True,
        },
    )
    return out
