"""
edge_concentrator.py
--------------------
Post-scoring gate for findtorontoevents_antigravity.ca smart picks.
Designed to be inserted between AgreementAlpha and FinalGate in the pipeline.

Activation: set env var EDGE_CONCENTRATOR_ENABLED=1  (off by default — opt-in sidecar).
            Or set policy flag {"enable_edge_concentrator": true} in risk_policy.json.

Integration point: called from smart_picks_engine.score_pick() just before the
final return dict, AFTER all scoring is complete.  score_pick() passes the
already-computed score + regime so no re-computation is needed here.

Five-layer gate (system → capacity → regime → family IC → strategy tier):
  1. Auto-pause    : 7-day rolling PF < 1.0 on 20+ concentrator-accepted trades → 48h halt
  2. Capacity      : max 3 concurrent open positions (TTL-based, not counter-based)
  3. Regime router : CHOPPY ≤5/week, BULL ≤12/week, BEAR ≤8/week (SHORTs only in BEAR)
  4. Family IC     : Spearman(score, pnl_pct) ≥ 0.05 over 20-day window (10 trade min)
  5. Strategy tier : n ≥ 20 in 90 days, WR > 50%, PF > 1.30

Production field names (match pick schema exactly):
  score, source_system, strategy, direction, entry_price, stop_loss, pnl_pct,
  closed_at | timestamp, id

State persistence: alpha_engine/data/edge_concentrator_state.json
Closed-trade data : alpha_engine/data/closed_picks.json  (loaded once, cached)
No external deps  : numpy only (no scipy).

Bugs fixed vs the original sketch (2026-05-16 review):
  - active_positions: was bare int, never decremented → TTL dict keyed by pick ID
  - auto_pause uses only concentrator-accepted trades, NOT the upstream raw history
  - MIN_TIER_TRADES: 50 → 20 (50 was filtering everything; 11/193 strats had n≥50)
  - IC burn-in: <10 trades → WARN+pass by default (IC_BURN_STRICT=1 to hard-block)
  - Regime tokens mapped from smart_picks_engine vocab (bull/bear/neutral → BULL/BEAR/CHOPPY)
  - scipy removed → pure-numpy Spearman
  - State persisted to disk so weekly caps survive cron restarts
  - ATR uses (entry - existing_sl) proxy — ATR not in pick schema
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

log = logging.getLogger("EdgeConcentrator")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CFG: dict = {
    "min_ic": 0.05,
    "ic_window_days": 20,
    "ic_min_trades": 10,           # warn/block threshold; see ic_burn_strict
    "ic_burn_strict": os.getenv("IC_BURN_STRICT", "0") == "1",  # False=WARN+pass, True=BLOCK
    "tier_window_days": 90,
    "min_tier_trades": 20,         # charter floor (was 50 — too strict for real data)
    "min_tier_wr": 0.50,
    "min_tier_pf": 1.30,
    "pause_window_days": 7,
    "pause_min_trades": 20,
    "pause_threshold_pf": 1.0,
    "pause_duration_hours": 48,
    "max_concurrent": 3,
    "position_ttl_hours": 48,      # assume trade closed after 48h if no explicit close
    "atr_multiplier": 2.0,
    "weekly_caps": {"CHOPPY": 5, "BULL": 12, "BEAR": 8},
}

_STATE_PATH = Path(__file__).resolve().parent / "data" / "edge_concentrator_state.json"
_CLOSED_PATH = Path(__file__).resolve().parent / "data" / "closed_picks.json"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _spearman_r(scores: list, pnls: list) -> float:
    """Spearman rank correlation — no scipy. Returns 0.0 on degenerate input."""
    if len(scores) < 3:
        return 0.0
    a = np.array(scores, dtype=float)
    b = np.array(pnls, dtype=float)
    if np.std(a) == 0 or np.std(b) == 0:
        return 0.0

    def _rank(v: np.ndarray) -> np.ndarray:
        order = np.argsort(v)
        r = np.empty_like(order, dtype=float)
        r[order] = np.arange(1, len(v) + 1, dtype=float)
        return r

    d = _rank(a) - _rank(b)
    n = len(d)
    denom = n * (n ** 2 - 1)
    return float(1.0 - 6.0 * float(np.sum(d ** 2)) / denom) if denom else 0.0


def _parse_ts(ts_str: str) -> datetime:
    """Parse ISO timestamp string → UTC datetime. Returns epoch on failure."""
    try:
        dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _week_key(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]}"


def _normalize_regime(regime: str) -> str:
    """Map smart_picks_engine regime tokens to concentrator tokens."""
    r = str(regime).lower().strip()
    if r in ("bull", "bullish"):
        return "BULL"
    if r in ("bear", "bearish"):
        return "BEAR"
    return "CHOPPY"


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    try:
        if _STATE_PATH.exists():
            return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"paused_until": None, "positions": {}, "weekly": {}, "accepted_log": []}


def _save_state(state: dict) -> None:
    try:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STATE_PATH.write_text(json.dumps(state, default=str), encoding="utf-8")
    except Exception as exc:
        log.warning("edge_concentrator: could not save state: %s", exc)


# ---------------------------------------------------------------------------
# Closed-trade cache (loaded once per process)
# ---------------------------------------------------------------------------

_CLOSED_CACHE: Optional[List[dict]] = None


def _load_closed_trades() -> List[dict]:
    global _CLOSED_CACHE
    if _CLOSED_CACHE is not None:
        return _CLOSED_CACHE
    try:
        raw = json.loads(_CLOSED_PATH.read_text(encoding="utf-8"))
        _CLOSED_CACHE = raw if isinstance(raw, list) else []
    except Exception as exc:
        log.warning("edge_concentrator: could not load closed_picks.json: %s", exc)
        _CLOSED_CACHE = []
    return _CLOSED_CACHE


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------

class EdgeConcentrator:
    """
    Stateful post-scoring gate.  Obtain via get_concentrator() — do not instantiate
    directly unless you need a fresh isolated instance for testing.
    """

    def __init__(self) -> None:
        self._state = _load_state()
        # In-memory accepted log for this process invocation (used by auto-pause
        # in addition to the persisted accepted_log in _state).
        self._in_memory_accepted: List[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        pick: dict,
        asset_class: str,
        direction: str,
        regime_raw: str,
        score: float,
    ) -> dict:
        """
        Evaluate a scored pick through the five-layer gate.

        Parameters
        ----------
        pick        : production pick dict with fields: id, symbol, score,
                      source_system, strategy, direction, entry_price,
                      stop_loss, pnl_pct, closed_at | timestamp, confidence
        asset_class : normalised asset class string (e.g. "crypto")
        direction   : "LONG" | "SHORT"
        regime_raw  : regime token from smart_picks_engine._regime_for_symbol()
        score       : smart_score (0–100) already computed by score_pick()

        Returns
        -------
        dict
            accepted   : bool
            reason     : str  ("ACCEPTED" or rejection code)
            dynamic_sl : float | None  (widened stop if accepted)
        """
        now = _now_utc()
        regime = _normalize_regime(regime_raw)
        source_system = str(pick.get("source_system") or "unknown").lower().strip()
        strategy = str(pick.get("strategy") or "unknown").lower().strip()
        is_short = direction.upper() in ("SHORT", "SELL")
        closed_trades = _load_closed_trades()

        # Gate 1 — auto-pause (own accepted log only)
        paused, pause_reason = self._check_auto_pause(now)
        if paused:
            return {"accepted": False, "reason": pause_reason, "dynamic_sl": None}

        # Gate 2 — concurrent position cap (TTL-based)
        self._expire_positions(now)
        if len(self._state.get("positions", {})) >= _CFG["max_concurrent"]:
            return {"accepted": False, "reason": "MAX_CONCURRENT_REACHED", "dynamic_sl": None}

        # Gate 3 — regime capacity + direction
        ok, reason = self._check_regime(now, regime, is_short)
        if not ok:
            return {"accepted": False, "reason": reason, "dynamic_sl": None}

        # Gate 4 — source_system IC (family-level Spearman rho)
        if not self._check_ic(now, source_system, closed_trades):
            return {"accepted": False, "reason": "POOR_FAMILY_IC", "dynamic_sl": None}

        # Gate 5 — strategy tier (n≥20, WR>50%, PF>1.3 in 90 days)
        if not self._check_tier(now, strategy, closed_trades):
            return {"accepted": False, "reason": "FAILS_TIER_FILTER", "dynamic_sl": None}

        # All gates passed
        dynamic_sl = self._compute_dynamic_sl(pick, is_short)

        # Register position (TTL keyed by pick ID)
        pick_id = str(
            pick.get("id")
            or f"{pick.get('symbol')}:{direction}:{pick.get('timestamp', now.isoformat())}"
        )
        expiry = (now + timedelta(hours=_CFG["position_ttl_hours"])).isoformat()
        self._state.setdefault("positions", {})[pick_id] = expiry

        # Update weekly cap counter
        wk = _week_key(now)
        self._state.setdefault("weekly", {})[wk] = self._state["weekly"].get(wk, 0) + 1

        # Append to accepted log (persisted for future auto-pause checks)
        entry = {
            "ts": now.isoformat(),
            "source_system": source_system,
            "strategy": strategy,
            "score": float(score),
            "pnl_pct": None,  # updated on close; None means still open
        }
        self._state.setdefault("accepted_log", []).append(entry)
        self._in_memory_accepted.append(entry)
        # Keep log bounded to 500 entries
        self._state["accepted_log"] = self._state["accepted_log"][-500:]

        _save_state(self._state)
        return {"accepted": True, "reason": "ACCEPTED", "dynamic_sl": dynamic_sl}

    # ------------------------------------------------------------------
    # Gate implementations
    # ------------------------------------------------------------------

    def _check_auto_pause(self, now: datetime) -> Tuple[bool, str]:
        paused_until_str = self._state.get("paused_until")
        if paused_until_str:
            try:
                pu = _parse_ts(paused_until_str)
                if now < pu:
                    return True, f"AUTO_PAUSE_UNTIL_{pu.strftime('%Y%m%dT%H%MZ')}"
            except Exception:
                pass

        # Evaluate only concentrator-accepted trades (NOT upstream raw history)
        cutoff = now - timedelta(days=_CFG["pause_window_days"])
        accepted_log = self._state.get("accepted_log", []) + self._in_memory_accepted
        recent = [
            t for t in accepted_log
            if _parse_ts(t.get("ts", "")) >= cutoff
            and t.get("pnl_pct") is not None
        ]
        if len(recent) >= _CFG["pause_min_trades"]:
            gross_p = sum(t["pnl_pct"] for t in recent if t["pnl_pct"] > 0)
            gross_l = abs(sum(t["pnl_pct"] for t in recent if t["pnl_pct"] < 0))
            pf = gross_p / gross_l if gross_l > 0 else 999.0
            if pf < _CFG["pause_threshold_pf"]:
                until = now + timedelta(hours=_CFG["pause_duration_hours"])
                self._state["paused_until"] = until.isoformat()
                log.warning(
                    "edge_concentrator: AUTO-PAUSE triggered. 7-day PF=%.2f. Pausing until %s",
                    pf, until.strftime("%Y-%m-%dT%H:%MZ"),
                )
                return True, "AUTO_PAUSE_PF_BELOW_1"
        return False, ""

    def _expire_positions(self, now: datetime) -> None:
        positions = self._state.get("positions", {})
        expired = [k for k, exp in positions.items() if _parse_ts(exp) <= now]
        for k in expired:
            del positions[k]

    def _check_regime(self, now: datetime, regime: str, is_short: bool) -> Tuple[bool, str]:
        if regime == "BEAR" and not is_short:
            return False, "BEAR_REGIME_LONGS_BLOCKED"
        cap = _CFG["weekly_caps"].get(regime, 12)
        wk = _week_key(now)
        count = self._state.get("weekly", {}).get(wk, 0)
        if count >= cap:
            return False, f"WEEKLY_CAP_{regime}_{cap}"
        return True, ""

    def _check_ic(self, now: datetime, source_system: str, closed_trades: List[dict]) -> bool:
        cutoff = now - timedelta(days=_CFG["ic_window_days"])
        family = [
            t for t in closed_trades
            if str(t.get("source_system") or "").lower().strip() == source_system
            and _parse_ts(t.get("closed_at") or t.get("timestamp") or "") >= cutoff
            and t.get("pnl_pct") is not None
            and t.get("score") is not None
        ]
        if len(family) < _CFG["ic_min_trades"]:
            if _CFG["ic_burn_strict"]:
                log.debug("edge_concentrator: %s only %d trades in IC window — BLOCK (strict)", source_system, len(family))
                return False
            log.info("edge_concentrator: %s only %d trades in IC window — WARN (pass-through; set IC_BURN_STRICT=1 to block)", source_system, len(family))
            return True

        scores = [float(t["score"]) for t in family]
        pnls = [float(t["pnl_pct"]) for t in family]
        ic = _spearman_r(scores, pnls)
        log.debug("edge_concentrator: %s IC=%.3f (n=%d)", source_system, ic, len(family))
        return ic >= _CFG["min_ic"]

    def _check_tier(self, now: datetime, strategy: str, closed_trades: List[dict]) -> bool:
        cutoff = now - timedelta(days=_CFG["tier_window_days"])
        strat = [
            t for t in closed_trades
            if str(t.get("strategy") or "").lower().strip() == strategy
            and _parse_ts(t.get("closed_at") or t.get("timestamp") or "") >= cutoff
            and t.get("pnl_pct") is not None
        ]
        n = len(strat)
        if n < _CFG["min_tier_trades"]:
            return False
        wins = [t for t in strat if float(t["pnl_pct"]) > 0]
        losses = [t for t in strat if float(t["pnl_pct"]) <= 0]
        wr = len(wins) / n
        gross_p = sum(float(t["pnl_pct"]) for t in wins)
        gross_l = abs(sum(float(t["pnl_pct"]) for t in losses))
        pf = gross_p / gross_l if gross_l > 0 else 999.0
        return wr > _CFG["min_tier_wr"] and pf > _CFG["min_tier_pf"]

    def _compute_dynamic_sl(self, pick: dict, is_short: bool) -> Optional[float]:
        """Widen SL to 2× ATR proxy (ATR proxy = |entry - existing_sl|). Fail-open."""
        try:
            entry = float(pick.get("entry_price") or 0)
            sl = float(pick.get("stop_loss") or 0)
            if entry <= 0 or sl <= 0:
                return None
            atr_proxy = abs(entry - sl)
            if is_short:
                return round(entry + _CFG["atr_multiplier"] * atr_proxy, 8)
            return round(entry - _CFG["atr_multiplier"] * atr_proxy, 8)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------------

_CONCENTRATOR: Optional[EdgeConcentrator] = None


def get_concentrator() -> EdgeConcentrator:
    """Return (or create) the process-wide singleton. Cron is single-threaded — no lock needed."""
    global _CONCENTRATOR
    if _CONCENTRATOR is None:
        _CONCENTRATOR = EdgeConcentrator()
    return _CONCENTRATOR


def reset_concentrator() -> None:
    """Force a fresh instance on next get_concentrator() call. For testing only."""
    global _CONCENTRATOR, _CLOSED_CACHE
    _CONCENTRATOR = None
    _CLOSED_CACHE = None
