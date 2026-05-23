"""
PCG-5 Portfolio Gate System — Shadow Mode

Five institutional-grade portfolio gates that monitor live picks for
quality signals without blocking production (shadow mode = always True, but logs).

Wire to production by:
1. Setting PCG5_SHADOW_MODE=0 in env after 30-day observation period
2. Calling passes_pcg5_gate() from audit_trail/quality_gates.py::passes_active_gate()

## Gates
G1 - Max Correlation: reject picks from strategies already >0.6 correlated to open positions
G2 - Regime Alignment: reject LONG picks entering bear regime, SHORT picks in bull
G3 - Max Drawdown Circuit: reject new picks when system MDD > 15% in rolling 30d window
G4 - Score Percentile Floor: reject picks below 30th percentile of last-30d scores
G5 - Asset Concentration: reject new picks adding >40% weight to one asset class

Kill-switch: PCG5_SHADOW_MODE=1 (default=1 → shadow/observe only, never blocks)
PCG5_GATE_LOG: path to pcg5_log.json (default: audit_dashboard/data/pcg5_log.json)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

SHADOW_MODE: bool = os.environ.get("PCG5_SHADOW_MODE", "1") not in ("0", "false", "FALSE", "False")
# PCG5_ENFORCE=1 → failed picks are actually rejected (returns False). Default 0 = shadow only.
ENFORCE_MODE: bool = os.environ.get("PCG5_ENFORCE", "0") not in ("0", "false", "FALSE", "False")

_DEFAULT_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "audit_dashboard", "data", "pcg5_log.json",
)

# Gate parameters (tune before going live)
MAX_CORRELATION_THRESHOLD = 0.60       # G1
BEAR_REGIMES = {"bear", "trending_down", "crash", "distribution"}
BULL_REGIMES = {"bull", "trending_up", "strong_bull"}           # G2
MAX_DRAWDOWN_THRESHOLD_PCT = 15.0      # G3 — 15% MDD triggers circuit
SCORE_PERCENTILE_FLOOR = 30            # G4 — 30th percentile
ASSET_CONCENTRATION_MAX_PCT = 40.0     # G5 — max single class weight


# ── Gate implementations ───────────────────────────────────────────────────────


def g1_max_correlation(
    pick: Dict[str, Any],
    open_picks: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[bool, str]:
    """G1: Reject if strategy is >0.6 correlated to open positions.

    In shadow mode: always returns (True, reason) but logs.
    In live mode: returns (False, reason) to block pick.
    """
    open_picks = open_picks or []
    if not open_picks:
        return True, "G1_PASS: no open picks to correlate"

    strategy = str(pick.get("strategy", "") or "").strip()
    asset_class = str(pick.get("asset_class", "") or "").upper()
    symbol = str(pick.get("symbol", "") or "").upper()

    # Count strategy overlap (proxy for correlation without full return series)
    same_strategy_count = sum(
        1 for p in open_picks
        if str(p.get("strategy", "")) == strategy
        and str(p.get("asset_class", "")).upper() == asset_class
    )
    # Rough correlation proxy: same strategy + same class = high correlation
    if len(open_picks) > 0:
        correlation_proxy = same_strategy_count / len(open_picks)
    else:
        correlation_proxy = 0.0

    passed = correlation_proxy <= MAX_CORRELATION_THRESHOLD
    reason = (
        f"G1_{'PASS' if passed else 'FAIL'}: strategy={strategy} "
        f"same_strat_count={same_strategy_count} corr_proxy={correlation_proxy:.2f}"
    )
    if not passed:
        log.info("PCG5 G1 FAIL (shadow=%s): %s", SHADOW_MODE, reason)
    return True if SHADOW_MODE else passed, reason


def g2_regime_alignment(
    pick: Dict[str, Any],
) -> Tuple[bool, str]:
    """G2: Reject LONG in bear regime, SHORT in bull regime."""
    direction = str(pick.get("direction", pick.get("signal_type", "LONG")) or "LONG").upper()
    regime = str(pick.get("regime_at_entry", pick.get("market_regime", pick.get("regime", ""))) or "").lower()

    if direction == "LONG" and any(b in regime for b in BEAR_REGIMES):
        reason = f"G2_FAIL: LONG pick in bear regime ({regime})"
        log.info("PCG5 G2 FAIL (shadow=%s): %s", SHADOW_MODE, reason)
        return True if SHADOW_MODE else False, reason

    if direction == "SHORT" and any(b in regime for b in BULL_REGIMES):
        reason = f"G2_FAIL: SHORT pick in bull regime ({regime})"
        log.info("PCG5 G2 FAIL (shadow=%s): %s", SHADOW_MODE, reason)
        return True if SHADOW_MODE else False, reason

    return True, f"G2_PASS: direction={direction} regime={regime}"


def g3_drawdown_circuit(
    system_mdd_pct: float = 0.0,
) -> Tuple[bool, str]:
    """G3: Block new picks when 30d system MDD exceeds threshold.

    Args:
        system_mdd_pct: current 30-day max drawdown % (positive number).
    """
    if system_mdd_pct >= MAX_DRAWDOWN_THRESHOLD_PCT:
        reason = (
            f"G3_FAIL: system 30d MDD={system_mdd_pct:.1f}% >= "
            f"circuit threshold {MAX_DRAWDOWN_THRESHOLD_PCT:.1f}%"
        )
        log.info("PCG5 G3 FAIL (shadow=%s): %s", SHADOW_MODE, reason)
        return True if SHADOW_MODE else False, reason

    return True, f"G3_PASS: MDD={system_mdd_pct:.1f}%"


def g4_score_percentile_floor(
    pick: Dict[str, Any],
    recent_scores: Optional[List[float]] = None,
) -> Tuple[bool, str]:
    """G4: Reject picks below 30th percentile of last-30d scores."""
    if not recent_scores:
        return True, "G4_PASS: no score history (warm-up)"

    pick_score = float(pick.get("score", 0) or 0)

    # Compute 30th percentile
    sorted_scores = sorted(recent_scores)
    n = len(sorted_scores)
    idx = int(SCORE_PERCENTILE_FLOOR / 100.0 * n)
    idx = max(0, min(idx, n - 1))
    p30 = sorted_scores[idx]

    if pick_score < p30:
        reason = f"G4_FAIL: score={pick_score:.0f} < p30={p30:.0f} (n={n})"
        log.info("PCG5 G4 FAIL (shadow=%s): %s", SHADOW_MODE, reason)
        return True if SHADOW_MODE else False, reason

    return True, f"G4_PASS: score={pick_score:.0f} >= p30={p30:.0f}"


def g5_asset_concentration(
    pick: Dict[str, Any],
    open_picks: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[bool, str]:
    """G5: Reject if new pick would push single asset class above 40% of portfolio."""
    open_picks = open_picks or []
    if not open_picks:
        return True, "G5_PASS: empty portfolio"

    pick_class = str(pick.get("asset_class", "") or "").upper()
    if not pick_class:
        return True, "G5_PASS: no asset_class on pick"

    total = len(open_picks) + 1  # including the new pick
    same_class = sum(
        1 for p in open_picks
        if str(p.get("asset_class", "")).upper() == pick_class
    ) + 1  # + the new pick

    concentration_pct = (same_class / total) * 100.0
    if concentration_pct > ASSET_CONCENTRATION_MAX_PCT:
        reason = (
            f"G5_FAIL: {pick_class} concentration={concentration_pct:.1f}% > "
            f"{ASSET_CONCENTRATION_MAX_PCT:.1f}% (n_same={same_class}/{total})"
        )
        log.info("PCG5 G5 FAIL (shadow=%s): %s", SHADOW_MODE, reason)
        return True if SHADOW_MODE else False, reason

    return True, f"G5_PASS: {pick_class}={concentration_pct:.1f}%"


# ── Aggregated gate (single entry point) ──────────────────────────────────────


def passes_pcg5_gate(
    pick: Dict[str, Any],
    open_picks: Optional[List[Dict[str, Any]]] = None,
    system_mdd_pct: float = 0.0,
    recent_scores: Optional[List[float]] = None,
    log_path: Optional[str] = None,
) -> Tuple[bool, str]:
    """Run all 5 PCG gates. In shadow mode, always returns True but logs all failures.

    Args:
        pick: pick dict (same schema as production picks)
        open_picks: current open portfolio picks (for correlation + concentration)
        system_mdd_pct: current 30d max drawdown % (for circuit breaker)
        recent_scores: last 30d pick scores (for percentile floor)
        log_path: path for pcg5_log.json (default from PCG5_GATE_LOG env or default path)

    Returns:
        (passed: bool, combined_reason: str)
        In shadow mode, passed is always True.
    """
    gates = [
        ("G1", lambda: g1_max_correlation(pick, open_picks)),
        ("G2", lambda: g2_regime_alignment(pick)),
        ("G3", lambda: g3_drawdown_circuit(system_mdd_pct)),
        ("G4", lambda: g4_score_percentile_floor(pick, recent_scores)),
        ("G5", lambda: g5_asset_concentration(pick, open_picks)),
    ]

    all_passed = True
    reasons: List[str] = []
    gate_log: List[Dict[str, Any]] = []

    for gate_id, gate_fn in gates:
        try:
            passed, reason = gate_fn()
        except Exception as exc:
            passed, reason = True, f"{gate_id}_ERROR (fail-open): {exc}"
            log.warning("PCG5 %s error: %s", gate_id, exc)

        reasons.append(reason)
        gate_log.append({"gate": gate_id, "passed": passed, "reason": reason})
        if not passed:
            all_passed = False

    combined_reason = " | ".join(reasons)
    final_passed = True if SHADOW_MODE else all_passed

    # PCG5_ENFORCE=1: even in shadow-mode-off OR when ENFORCE_MODE is set,
    # actually block picks that failed gates. Fail-open: any exception → pass.
    if ENFORCE_MODE and not all_passed:
        failed_gates = [entry["gate"] for entry in gate_log if not entry["passed"]]
        log.info("PCG-5 ENFORCE: pick blocked by gates %s | %s", failed_gates, combined_reason)
        final_passed = False

    # Append to log
    _append_log(pick, gate_log, final_passed, log_path)

    return final_passed, combined_reason


def _append_log(
    pick: Dict[str, Any],
    gate_log: List[Dict[str, Any]],
    final_passed: bool,
    log_path: Optional[str] = None,
) -> None:
    """Append gate evaluation to pcg5_log.json."""
    if log_path is None:
        log_path = os.environ.get("PCG5_GATE_LOG", _DEFAULT_LOG_PATH)

    entry = {
        "symbol": pick.get("symbol", ""),
        "strategy": pick.get("strategy", ""),
        "asset_class": pick.get("asset_class", ""),
        "shadow_mode": SHADOW_MODE,
        "enforce_mode": ENFORCE_MODE,
        "final_passed": final_passed,
        "gates": gate_log,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        existing: List[Dict[str, Any]] = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    existing = data
                elif isinstance(data, dict):
                    existing = data.get("entries", [])
        existing.append(entry)
        # Keep last 500 entries to avoid unbounded growth
        existing = existing[-500:]
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({"shadow_mode": SHADOW_MODE, "entries": existing}, f, indent=2, default=str)
    except Exception as exc:
        log.debug("PCG5 log write failed (non-critical): %s", exc)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log.info("PCG-5 gates loaded. shadow_mode=%s enforce_mode=%s", SHADOW_MODE, ENFORCE_MODE)
    log.info("To activate live mode: PCG5_SHADOW_MODE=0")
    log.info("To enforce blocking (reject failing picks): PCG5_ENFORCE=1")
    log.info("Wire to production: call passes_pcg5_gate() from quality_gates.py::passes_active_gate()")
    log.info("Thresholds: corr=%.2f, MDD=%.1f%%, score_p=%d, concentration=%.0f%%",
             MAX_CORRELATION_THRESHOLD,
             MAX_DRAWDOWN_THRESHOLD_PCT,
             SCORE_PERCENTILE_FLOOR,
             ASSET_CONCENTRATION_MAX_PCT)
