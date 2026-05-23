"""
Forward-test gates: lightweight pick check + full GateFilter (Downloads-aligned).

`forward_pick_passes_gates` — minimal geometry + optional ml/strategy blocks (tracker ingest).

`GateFilter` — Layer 2.5-style gates from TESTING_PROTOCOL.MD + Downloads/forward_test_gates.py
(net R:R, TP remaining, age, direction conflict, high-risk strategy stats).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

BLOCKED_STRATEGIES = frozenset(
    {
        "vol_spike_backfill",
        "winner_pattern",
        "ml_crypto_predictor",
        "unknown",
        "ema_stack_momentum",
        "futures_ema_stack_momentum",  # 0/4=0% WR, 7 zombie picks — killed 2026-04-02
    }
)

HIGH_RISK_SYSTEMS = frozenset(
    {
        "crypto_drawdown_convexity_recovery_v1",
        "MomentumEMA",
        "extreme_fear",
    }
)

MIN_RR = 1.2
MIN_ML_SCORE = 0.50


def _f(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def forward_pick_passes_gates(pick: dict) -> tuple[bool, str]:
    """
    Normalized forward-test dict: entry_price, tp_price, sl_price, direction.
    """
    entry = _f(pick.get("entry_price"))
    tp = _f(pick.get("tp_price"))
    sl = _f(pick.get("sl_price"))
    direction = str(pick.get("direction") or "").upper()
    if entry <= 0 or tp <= 0 or sl <= 0:
        return False, "missing_levels"

    if direction in ("LONG", "BUY"):
        risk = entry - sl
        reward = tp - entry
    elif direction in ("SHORT", "SELL"):
        risk = sl - entry
        reward = entry - tp
    else:
        return False, "bad_direction"

    if risk <= 0 or reward <= 0:
        return False, "invalid_risk_reward_geometry"

    rr = reward / risk
    if rr < MIN_RR:
        return False, "rr_below_%.1f" % MIN_RR

    strat = str(pick.get("strategy") or "").strip()
    if strat and strat in BLOCKED_STRATEGIES:
        return False, "blocked_strategy"

    ml = pick.get("ml_score")
    if ml is not None and str(ml).strip() != "":
        if _f(ml) < MIN_ML_SCORE:
            return False, "ml_below_%.2f" % MIN_ML_SCORE

    sc = pick.get("score")
    if sc is not None and _f(sc) > 85:
        n = pick.get("strat_closed_n")
        if n is not None:
            try:
                if int(n) < 10:
                    return False, "high_score_low_sample"
            except (TypeError, ValueError):
                pass

    return True, "ok"


class GateFilter:
    """Full gate stack for paper/forward simulation (requires closed + active context)."""

    MIN_ML_SCORE = 0.50
    MIN_RR = 1.2
    MIN_TP_REMAINING_PCT = 0.10
    MAX_AGE_HOURS = 48.0
    MAX_AGE_HOURS_COPY_TRADER = 168.0
    MIN_SCORE_DIRECTION_CONFLICT = 70
    MIN_SYS_WR = 45.0
    MIN_SYS_PF = 1.0
    MIN_SYS_CLOSED = 5

    COMMISSION_CRYPTO_RT = 0.0030
    COMMISSION_EQUITY_RT = 0.0070
    COMMISSION_FOREX_RT = 0.0002

    def __init__(self, closed_history: list[dict], active_picks: Optional[list[dict]] = None):
        self.closed = [x for x in (closed_history or []) if isinstance(x, dict)]
        self.active = [x for x in (active_picks or []) if isinstance(x, dict)]
        self._strat_stats = self._build_strategy_stats()
        self._active_by_symbol = self._index_active_by_symbol()

    def _build_strategy_stats(self) -> dict[str, dict[str, Any]]:
        by_strat: dict[str, list[dict]] = defaultdict(list)
        for t in self.closed:
            by_strat[str(t.get("strategy") or "unknown")].append(t)
        stats: dict[str, dict[str, Any]] = {}
        for strat, trades in by_strat.items():
            wins = [t for t in trades if _f(t.get("pnl_pct", t.get("pnl", 0))) > 0]
            losses = [t for t in trades if _f(t.get("pnl_pct", t.get("pnl", 0))) <= 0]
            n = len(trades)
            wr = (len(wins) / n * 100.0) if n > 0 else 0.0
            gp = sum(_f(t.get("pnl_pct", t.get("pnl", 0))) for t in wins)
            gl = abs(sum(_f(t.get("pnl_pct", t.get("pnl", 0))) for t in losses))
            pf = gp / gl if gl > 0 else 999.0
            stats[strat] = {"n": n, "wr": wr, "pf": pf, "wins": len(wins), "losses": len(losses)}
        return stats

    def _index_active_by_symbol(self) -> dict[str, list[dict]]:
        by_symbol: dict[str, list[dict]] = defaultdict(list)
        for p in self.active:
            by_symbol[str(p.get("symbol") or "")].append(p)
        return by_symbol

    def should_take_trade(self, pick: dict) -> tuple[bool, str]:
        strategy = str(pick.get("strategy") or "unknown")
        symbol = str(pick.get("symbol") or "")
        direction = str(pick.get("direction") or "LONG").upper()
        score = _f(pick.get("score", 50))
        ml_score = pick.get("ml_score", pick.get("ml_composite_score"))
        if ml_score is None or str(ml_score).strip() == "":
            ml_f = 0.5
        else:
            ml_f = _f(ml_score)

        if strategy in BLOCKED_STRATEGIES:
            return False, "blocked_system:%s" % strategy
        if ml_f < self.MIN_ML_SCORE:
            return False, "kill_zone:ml_score=%.2f" % ml_f

        entry = _f(pick.get("entry", pick.get("entry_price", 0)))
        tp = _f(pick.get("tp", pick.get("take_profit", 0)))
        sl = _f(pick.get("sl", pick.get("stop_loss", 0)))
        if entry and tp and sl and entry != sl:
            if direction in ("LONG", "BUY"):
                risk = abs(entry - sl)
                reward = abs(tp - entry)
            else:
                risk = abs(sl - entry)
                reward = abs(entry - tp)
            rr = reward / risk if risk > 0 else 0.0
            ac = str(pick.get("asset_class", "CRYPTO")).upper()
            if ac == "EQUITY":
                commission = self.COMMISSION_EQUITY_RT
            elif ac in ("FOREX", "FX"):
                commission = self.COMMISSION_FOREX_RT
            else:
                commission = self.COMMISSION_CRYPTO_RT
            net_risk = risk + (entry * commission)
            net_reward = reward - (entry * commission)
            net_rr = net_reward / net_risk if net_risk > 0 else 0.0
            if net_rr < self.MIN_RR:
                return False, "rr_too_low:net_rr=%.2f" % net_rr

        if tp and entry:
            current = _f(pick.get("current_price", entry)) or entry
            if direction in ("LONG", "BUY") and tp > entry:
                tp_remaining = (tp - current) / (tp - entry)
            elif direction in ("SHORT", "SELL") and tp < entry:
                tp_remaining = (current - tp) / (entry - tp)
            else:
                tp_remaining = 0.5
            if tp_remaining < self.MIN_TP_REMAINING_PCT:
                return False, "tp_exhausted:%.1f%%" % (tp_remaining * 100)

        age_h = _f(pick.get("age_hours", 0))
        is_ct = bool(pick.get("is_copy_trader", False))
        max_age = self.MAX_AGE_HOURS_COPY_TRADER if is_ct else self.MAX_AGE_HOURS
        if age_h > max_age:
            return False, "stale_pick:%.0fh" % age_h

        if pick.get("tp_hit") or pick.get("sl_hit"):
            return False, "already_resolved"

        meme = {"DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "FLOKIUSDT", "BONKUSDT"}
        regime = str(pick.get("regime", "") or "")
        if symbol in meme and direction in ("LONG", "BUY") and regime in ("BEAR", "STORM", "HURRICANE"):
            return False, "meme_long_in_bear"

        if strategy in HIGH_RISK_SYSTEMS:
            st = self._strat_stats.get(strategy, {})
            if int(st.get("n", 0)) >= self.MIN_SYS_CLOSED:
                if float(st.get("pf", 0)) < self.MIN_SYS_PF:
                    return False, "pf_below_1"
                if float(st.get("wr", 0)) < self.MIN_SYS_WR:
                    return False, "wr_too_low"

        same = self._active_by_symbol.get(symbol, [])
        conflict = any(str(p.get("direction")).upper() != direction for p in same)
        if conflict and score < self.MIN_SCORE_DIRECTION_CONFLICT:
            return False, "direction_conflict"

        st2 = self._strat_stats.get(strategy, {})
        if score > 85 and int(st2.get("n", 0)) < 10:
            pick["score"] = 60.0

        ac2 = str(pick.get("asset_class", "CRYPTO")).upper()
        if ac2 == "CRYPTO":
            last = self._get_last_trade(strategy, symbol)
            if last is not None:
                last_pnl = _f(last.get("pnl_pct", last.get("pnl", 0)))
                if last_pnl < 0 and score < 65:
                    return False, "post_loss_penalty"

        return True, "passed_all_gates"

    def _get_last_trade(self, strategy: str, symbol: str) -> Optional[dict]:
        rel = [
            t
            for t in self.closed
            if str(t.get("strategy")) == strategy and str(t.get("symbol")) == symbol
        ]
        if not rel:
            return None
        return max(rel, key=lambda t: str(t.get("closed_at", t.get("timestamp", ""))))

    def filter_batch(self, picks: list[dict]) -> tuple[list[dict], list[dict]]:
        passed, rejected = [], []
        for p in picks:
            ok, reason = self.should_take_trade(dict(p))
            if ok:
                passed.append(p)
            else:
                rejected.append({**p, "_reject_reason": reason})
        return passed, rejected


def closed_pick_to_forward_shape(p: dict) -> dict[str, Any]:
    """Map dashboard closed pick to forward_gate / GateFilter field names."""
    entry = _f(p.get("entry_price", p.get("entry", 0)))
    tp = _f(p.get("take_profit", p.get("tp", 0)))
    sl = _f(p.get("stop_loss", p.get("sl", 0)))
    return {
        "symbol": p.get("symbol"),
        "direction": p.get("direction", "LONG"),
        "strategy": p.get("strategy", ""),
        "entry_price": entry,
        "entry": entry,
        "tp_price": tp,
        "take_profit": tp,
        "sl_price": sl,
        "stop_loss": sl,
        "score": p.get("score"),
        "ml_score": p.get("ml_score"),
        "asset_class": p.get("asset_class", "CRYPTO"),
        "age_hours": _f(p.get("age_hours", 0)),
    }
