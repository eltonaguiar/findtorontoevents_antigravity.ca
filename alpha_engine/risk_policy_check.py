"""
Risk policy observability (HF §2.5).

Consumer of config/risk_policy.json. Given a list of sized picks plus the
portfolio value, aggregate exposure per-symbol and per-direction and emit
WARNING logs when caps are exceeded. Non-invasive: does not mutate picks.

Safe defaults (if risk_policy.json missing or loader fails):
  - per-symbol:    10% of equity
  - per-direction: 40% of equity  (v1 JSON currently ships 20 for crypto;
                                   40% used only as absolute fallback)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

_FALLBACK_PER_SYMBOL_PCT = 5.0   # 2026-05-09 v2: tightened 10 → 5 per swarm 4/4
_FALLBACK_PER_DIRECTION_PCT = 40.0

# PR-D (2026-05-12): explicit FOREX hard-cap sizing gate.
# Per CLAUDE.md FOREX directive + docs/MUTATION_THREE_AXIS_PROTOCOL.md:
# FOREX is genuinely sub-floor (PF 0.27 / WR 46.4% / n=1169 post-noise filter).
# Apply explicit per-class block (NOT BLOCKED_SOURCE_SYSTEMS extension) until
# the class earns its way back via mutate-before-kill protocol.
# Floor: PF >= 0.8 (mid-point between current ~0.28 and Tier-2 PF=1.5).
FOREX_SIZING_PF_FLOOR = 0.8


def is_forex_sizing_allowed(asset_class_health: dict) -> tuple[bool, str]:
    """Explicit FOREX sizing gate (PR-D, 2026-05-12).

    Returns (allowed, reason_str). ``reason_str`` is auditable on /audit when
    sizing is blocked. Empty string when allowed.

    Per CLAUDE.md: do NOT silently kill FOREX. Surface the block reason so
    the FOREX tile + downstream audit trail show *why* sizing is off.

    Decision tree:
      - asset_class_health missing FOREX entry        -> allowed (no data, no gate)
      - FOREX profit_factor is None / missing         -> allowed (no signal)
      - FOREX profit_factor < FOREX_SIZING_PF_FLOOR   -> BLOCKED with reason
      - FOREX profit_factor >= FOREX_SIZING_PF_FLOOR  -> allowed (recovered)
    """
    if not isinstance(asset_class_health, dict):
        return True, ""
    forex = asset_class_health.get("FOREX")
    if not isinstance(forex, dict):
        return True, ""
    pf_raw = forex.get("profit_factor")
    if pf_raw is None:
        return True, ""
    try:
        pf = float(pf_raw)
    except (TypeError, ValueError):
        return True, ""
    if pf < FOREX_SIZING_PF_FLOOR:
        reason = (
            f"FOREX hard-cap: PF {pf:.2f} < {FOREX_SIZING_PF_FLOOR} floor "
            "(PR-D mutate-before-kill)"
        )
        return False, reason
    return True, ""


def _norm_direction(raw: Any) -> str:
    s = str(raw or "").strip().upper()
    if s in ("BUY", "LONG"):
        return "LONG"
    if s in ("SELL", "SHORT"):
        return "SHORT"
    return s or "UNKNOWN"


def check_risk_policy(
    picks: Iterable[dict],
    portfolio_value: float,
    *,
    log_fn=print,
) -> dict[str, Any]:
    """Emit WARNING logs when picks breach risk_policy caps.

    Returns a summary dict: {version, breaches: [...], per_symbol_pct: {...},
    per_direction_pct: {...}}. Does NOT mutate picks.
    """
    try:
        from alpha_engine.risk_policy_loader import load_risk_policy
        policy = load_risk_policy()
    except Exception:
        policy = {"version": 1, "crypto": {}}

    version = policy.get("version", 1)
    crypto = policy.get("crypto") or {}
    per_symbol_cap = float(
        crypto.get("max_equity_pct_per_symbol", _FALLBACK_PER_SYMBOL_PCT)
    )
    per_direction_cap = float(
        crypto.get("max_equity_pct_per_direction", _FALLBACK_PER_DIRECTION_PCT)
    )

    pv = float(portfolio_value or 0.0)
    if pv <= 0:
        return {
            "version": version, "breaches": [],
            "per_symbol_pct": {}, "per_direction_pct": {},
        }

    per_symbol: dict[str, float] = defaultdict(float)
    per_direction: dict[str, float] = defaultdict(float)

    for pick in picks or []:
        try:
            size = float(pick.get("position_size", 0) or 0)
        except (TypeError, ValueError):
            size = 0.0
        if size <= 0:
            continue
        pct = size / pv * 100.0
        symbol = str(pick.get("symbol") or "?")
        direction = _norm_direction(
            pick.get("direction") or pick.get("signal_type")
        )
        per_symbol[symbol] += pct
        per_direction[direction] += pct

    breaches: list[dict[str, Any]] = []

    for symbol, pct in per_symbol.items():
        if pct > per_symbol_cap:
            msg = (
                f"[RISK_POLICY] WARNING: symbol {symbol} aggregate "
                f"{pct:.2f}% exceeds per-symbol cap {per_symbol_cap:.2f}% "
                f"(risk_policy v{version})"
            )
            log_fn(msg)
            breaches.append({
                "kind": "per_symbol", "symbol": symbol,
                "pct": round(pct, 2), "cap_pct": per_symbol_cap,
            })

    for direction, pct in per_direction.items():
        if direction == "UNKNOWN":
            continue
        if pct > per_direction_cap:
            msg = (
                f"[RISK_POLICY] WARNING: direction {direction} aggregate "
                f"{pct:.2f}% exceeds per-direction cap "
                f"{per_direction_cap:.2f}% (risk_policy v{version})"
            )
            log_fn(msg)
            breaches.append({
                "kind": "per_direction", "direction": direction,
                "pct": round(pct, 2), "cap_pct": per_direction_cap,
            })

    return {
        "version": version,
        "breaches": breaches,
        "per_symbol_pct": {k: round(v, 2) for k, v in per_symbol.items()},
        "per_direction_pct": {k: round(v, 2) for k, v in per_direction.items()},
    }
