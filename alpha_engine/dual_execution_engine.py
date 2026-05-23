#!/usr/bin/env python3
"""
ALPHA ENGINE -- Dual Execution Engine (Hedge Fund Sprint 2026-03-25)
=====================================================================
Separates incompatible alpha types into dedicated execution pipelines.

ROOT CAUSE: Blending ML scalp signals (short-horizon, tight SL 2-3%) with
whale copy signals (medium-horizon, needs wide SL 4-8%) was the single
biggest structural flaw. Wrong risk model per signal type → guaranteed losses.

PIPELINE A — ML Scalping Engine
  - Signals: ml_enhanced_* strategies (BNBUSDT, FETUSDT, RENDERUSDT 85-94% WR)
  - TP: 3-5%  |  SL: 2-3%
  - Time horizon: hours
  - Driven by ml_score (restored as primary weight)
  - Score gate: ≥65 (higher bar for scalping)

PIPELINE B — Whale Swing Engine
  - Signals: NMTD_25M (81% WR), whale_123M (100% WR)
  - TP: 8%  |  SL: 4%
  - Time horizon: hours-days
  - ONLY proven Hyperliquid traders
  - Score gate: ≥55

PIPELINE C — Experimental (paper-only, zero capital)
  - All other strategies awaiting promotion
  - No real capital until 20+ trades at 60%+ WR and PF > 1.8

Capital Allocation (Target):
  - ML top-3 pairs: 50% of total
  - NMTD_25M: 30%
  - whale_123M: 20%
  - Experimental: 0% LIVE (paper only)

Usage:
    from dual_execution_engine import route_pick, DualExecutionEngine
    routed = route_pick(pick)
    # routed['pipeline']: 'ML' | 'WHALE' | 'EXPERIMENTAL'
    # routed['tp_pct']:  float
    # routed['sl_pct']:  float
    # routed['allocated_pct']: float (portfolio allocation)
    # routed['live']: bool
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# ML Pipeline — proven strategies (85-94% WR)
# ---------------------------------------------------------------------------
ML_PIPELINE_STRATEGIES: frozenset = frozenset({
    "ml_enhanced_bnbusdt_15m_b_lightgbm",
    "ml_enhanced_fetusdt_1d_b_lightgbm",
    "ml_enhanced_renderusdt_1h_d_ensemble_stack",
    "ml_enhanced_renderusdt_4h_d_ensemble_stack",
    # Prefix match: any ml_enhanced_* on tier-1 crypto
})
ML_PIPELINE_SYMBOLS: frozenset = frozenset({
    "BNBUSDT", "FETUSDT", "RENDERUSDT",
})
ML_PIPELINE_PREFIX = "ml_enhanced_"

ML_TP_PCT = 0.04     # 4% take-profit (3-5% range, using midpoint)
ML_SL_PCT = 0.02     # 2% stop-loss (tight, short holding period)
ML_SCORE_GATE = 65   # Higher bar for scalp trades
ML_CAPITAL_PCT = 0.50  # 50% of total capital

# ---------------------------------------------------------------------------
# Whale Pipeline — proven Hyperliquid traders only
# ---------------------------------------------------------------------------
WHALE_PIPELINE_TRADERS: frozenset = frozenset({
    "nmtd_25m",
    "copy_hl_nmtd_25m",
    "nmtd",
    "whale_123m",
    "copy_hl_whale_123m",
    "whale_123m_87roi",
    "copy_hl_whale_123m_87roi",
})
WHALE_PIPELINE_PREFIXES: tuple = ("copy_hl_", "copy_hl_lb_")

WHALE_TP_PCT = 0.08    # 8% take-profit
WHALE_SL_PCT = 0.04    # 4% stop-loss
WHALE_SCORE_GATE = 55  # Standard quality gate
WHALE_CAPITAL_PCT = 0.50  # Split: NMTD 30% + whale_123m 20%

NMTD_CAPITAL_PCT = 0.30
WHALE_123M_CAPITAL_PCT = 0.20

# ---------------------------------------------------------------------------
# Global quality gate — no trade below this regardless of pipeline
# ---------------------------------------------------------------------------
GLOBAL_SCORE_GATE = 55  # Score 40-59 = 6.2% WR (inverted), 55+ is quality floor

# ---------------------------------------------------------------------------
# Concentration caps — prevent over-concentration in single symbol
# ---------------------------------------------------------------------------
MAX_SYMBOL_CONCENTRATION = 0.30  # FETUSDT capped at 30% (avoid over-concentration)


def _normalise(value: object) -> str:
    return str(value or "").strip().lower()


def _get_elite_score(pick: dict) -> float:
    """Extract best available score from the pick."""
    for key in ("elite_score", "pipeline_score", "score", "confidence"):
        val = pick.get(key)
        if val is not None:
            try:
                s = float(val)
                # Confidence is 0-1 scale; normalise to 0-100
                if s <= 1.0 and key == "confidence":
                    s = s * 100
                if s > 0:
                    return s
            except (ValueError, TypeError):
                continue
    return 0.0


def _apply_tp_sl(pick: dict, tp_pct: float, sl_pct: float) -> dict:
    """Return a pick copy with updated TP/SL based on entry_price and direction."""
    ep = pick.get("entry_price")
    if not ep:
        return pick
    try:
        ep = float(ep)
    except (ValueError, TypeError):
        return pick

    direction = _normalise(pick.get("direction") or pick.get("signal_type") or "LONG")
    p = dict(pick)
    if "long" in direction or "buy" in direction:
        p["take_profit"] = round(ep * (1 + tp_pct), 6)
        p["stop_loss"] = round(ep * (1 - sl_pct), 6)
    else:
        p["take_profit"] = round(ep * (1 - tp_pct), 6)
        p["stop_loss"] = round(ep * (1 + sl_pct), 6)
    p["_tp_pct"] = tp_pct
    p["_sl_pct"] = sl_pct
    return p


def route_pick(pick: dict) -> dict:
    """
    Route a pick to ML, WHALE, or EXPERIMENTAL pipeline.

    Returns a copy of the pick dict enriched with:
      - pipeline: 'ML' | 'WHALE' | 'EXPERIMENTAL'
      - pipeline_live: bool (False = paper only)
      - pipeline_capital_pct: float (target portfolio allocation)
      - pipeline_tp_pct: float
      - pipeline_sl_pct: float
      - pipeline_score_gate: int
      - (take_profit and stop_loss recalculated for ML and WHALE picks)
    """
    strategy = _normalise(pick.get("strategy", ""))
    symbol = str(pick.get("symbol", "") or "").upper().strip()
    score = _get_elite_score(pick)

    # -----------------------------------------------------------------------
    # Global quality gate — block regardless of pipeline assignment
    # -----------------------------------------------------------------------
    if score < GLOBAL_SCORE_GATE and score > 0:
        p = dict(pick)
        p["pipeline"] = "BLOCKED"
        p["pipeline_live"] = False
        p["pipeline_capital_pct"] = 0.0
        p["pipeline_blocked_reason"] = f"score {score:.0f} < global gate {GLOBAL_SCORE_GATE}"
        return p

    # -----------------------------------------------------------------------
    # Pipeline A — ML Scalping (ml_enhanced_* on proven symbols)
    # -----------------------------------------------------------------------
    is_ml = (
        strategy.startswith(ML_PIPELINE_PREFIX)
        or strategy in ML_PIPELINE_STRATEGIES
        or (symbol in ML_PIPELINE_SYMBOLS and "ml" in strategy)
    )
    if is_ml:
        if score < ML_SCORE_GATE and score > 0:
            p = dict(pick)
            p["pipeline"] = "BLOCKED"
            p["pipeline_live"] = False
            p["pipeline_capital_pct"] = 0.0
            p["pipeline_blocked_reason"] = f"score {score:.0f} < ML gate {ML_SCORE_GATE}"
            return p

        p = _apply_tp_sl(pick, ML_TP_PCT, ML_SL_PCT)
        # Symbol concentration cap
        cap = min(ML_CAPITAL_PCT, MAX_SYMBOL_CONCENTRATION) if symbol == "FETUSDT" else ML_CAPITAL_PCT
        p["pipeline"] = "ML"
        p["pipeline_live"] = True
        p["pipeline_capital_pct"] = cap
        p["pipeline_tp_pct"] = ML_TP_PCT
        p["pipeline_sl_pct"] = ML_SL_PCT
        p["pipeline_score_gate"] = ML_SCORE_GATE
        return p

    # -----------------------------------------------------------------------
    # Pipeline B — Whale Swing (NMTD + whale_123M only)
    # -----------------------------------------------------------------------
    # Normalise trader label for matching
    _trader_label = strategy
    for pfx in WHALE_PIPELINE_PREFIXES:
        if _trader_label.startswith(pfx):
            _trader_label = _trader_label[len(pfx):]
            break

    is_whale = _trader_label in WHALE_PIPELINE_TRADERS or strategy in WHALE_PIPELINE_TRADERS
    if is_whale:
        p = _apply_tp_sl(pick, WHALE_TP_PCT, WHALE_SL_PCT)
        # Sub-allocate within whale bucket
        if "nmtd" in strategy:
            alloc = NMTD_CAPITAL_PCT
        elif "whale_123m" in strategy or "whale_123" in strategy:
            alloc = WHALE_123M_CAPITAL_PCT
        else:
            alloc = 0.10  # Unknown proven whale — small allocation
        p["pipeline"] = "WHALE"
        p["pipeline_live"] = True
        p["pipeline_capital_pct"] = alloc
        p["pipeline_tp_pct"] = WHALE_TP_PCT
        p["pipeline_sl_pct"] = WHALE_SL_PCT
        p["pipeline_score_gate"] = WHALE_SCORE_GATE
        return p

    # -----------------------------------------------------------------------
    # Pipeline C — Experimental (paper-only, zero live capital)
    # -----------------------------------------------------------------------
    p = dict(pick)
    p["pipeline"] = "EXPERIMENTAL"
    p["pipeline_live"] = False
    p["pipeline_capital_pct"] = 0.0
    p["pipeline_tp_pct"] = 0.04   # Default 4% TP for paper tracking
    p["pipeline_sl_pct"] = 0.025  # Default 2.5% SL for paper tracking
    p["pipeline_score_gate"] = GLOBAL_SCORE_GATE
    return p


class DualExecutionEngine:
    """
    Stateful wrapper around route_pick() that tracks live vs paper splits
    and enforces portfolio-level capital constraints.
    """

    def __init__(self, total_capital_usd: float = 10_000.0):
        self.total_capital = total_capital_usd
        self._live_picks: list[dict] = []
        self._paper_picks: list[dict] = []

    def process_picks(self, picks: list[dict]) -> dict:
        """
        Route all picks and return a structured result.

        Returns:
            {
                'live': [... live picks with pipeline metadata ...],
                'paper': [... paper picks ...],
                'blocked': [... rejected picks ...],
                'summary': {ml_count, whale_count, experimental_count, blocked_count}
            }
        """
        live: list[dict] = []
        paper: list[dict] = []
        blocked: list[dict] = []

        for pick in picks:
            routed = route_pick(pick)
            pl = routed.get("pipeline", "EXPERIMENTAL")
            if pl == "BLOCKED":
                blocked.append(routed)
            elif routed.get("pipeline_live", False):
                live.append(routed)
            else:
                paper.append(routed)

        self._live_picks = live
        self._paper_picks = paper

        ml_live = [p for p in live if p.get("pipeline") == "ML"]
        whale_live = [p for p in live if p.get("pipeline") == "WHALE"]

        return {
            "live": live,
            "paper": paper,
            "blocked": blocked,
            "summary": {
                "ml_count": len(ml_live),
                "whale_count": len(whale_live),
                "experimental_count": len(paper),
                "blocked_count": len(blocked),
                "total_live": len(live),
                "ml_capital_pct": ML_CAPITAL_PCT,
                "whale_capital_pct": WHALE_CAPITAL_PCT,
            },
        }


if __name__ == "__main__":
    # Quick smoke test
    test_picks = [
        {"strategy": "ml_enhanced_FETUSDT_1d_B_lightgbm", "symbol": "FETUSDT",
         "direction": "LONG", "entry_price": 1.50, "elite_score": 72,
         "take_profit": 1.55, "stop_loss": 1.47},
        {"strategy": "copy_hl_NMTD_25M", "symbol": "BTCUSDT",
         "direction": "LONG", "entry_price": 85000, "elite_score": 68,
         "take_profit": 86700, "stop_loss": 82650},
        {"strategy": "binance_smart_money", "symbol": "DOGEUSDT",
         "direction": "LONG", "entry_price": 0.12, "elite_score": 42,
         "take_profit": 0.124, "stop_loss": 0.118},
        {"strategy": "some_random_strategy", "symbol": "XYZUSDT",
         "direction": "LONG", "entry_price": 10.0, "elite_score": 30,
         "take_profit": 10.4, "stop_loss": 9.8},
    ]
    engine = DualExecutionEngine()
    result = engine.process_picks(test_picks)
    print(f"\n=== DualExecutionEngine Smoke Test ===")
    print(f"Live: {result['summary']['total_live']} | Paper: {len(result['paper'])} | Blocked: {result['summary']['blocked_count']}")
    for p in result["live"]:
        print(f"  LIVE [{p['pipeline']}] {p['symbol']} TP={p.get('take_profit')} SL={p.get('stop_loss')} alloc={p['pipeline_capital_pct']*100:.0f}%")
    for p in result["blocked"]:
        print(f"  BLOCKED {p.get('symbol')} reason={p.get('pipeline_blocked_reason')}")
