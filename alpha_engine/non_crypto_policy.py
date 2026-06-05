from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ── Fix B / C: re-entry cooldown + daily session cap ──────────────────────────
_DATA_DIR = Path(__file__).resolve().parent / "data"
_RECENT_EXITS_PATH = _DATA_DIR / "recent_exits.json"
_CLOSED_PICKS_PATH = _DATA_DIR / "closed_picks.json"
_ACTIVE_PICKS_PATH = _DATA_DIR / "active_picks.json"

_COOLDOWN_SL_MIN = 60
_COOLDOWN_TP_MIN = 15


def _load_json(path: Path) -> Any:
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_json_atomic(path: Path, data: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        tmp.replace(path)
    except Exception:
        pass


def record_recent_exit(symbol: str, exit_kind: str, exit_ts: Optional[str] = None) -> None:
    """Write/update recent_exits.json with the latest SL/TP/EXPIRED exit for a symbol.

    Called from the outcome resolver at resolution time. Safe on missing file.
    """
    if not symbol:
        return
    kind = (exit_kind or "").upper()
    if kind not in ("SL", "TP", "EXPIRED"):
        # Best-effort normalization from exit_reason strings
        if "SL" in kind:
            kind = "SL"
        elif "TP" in kind:
            kind = "TP"
        elif "TIME" in kind or "EXPIR" in kind:
            kind = "EXPIRED"
        else:
            return
    ts = exit_ts or datetime.now(timezone.utc).isoformat()
    data = _load_json(_RECENT_EXITS_PATH) or {}
    if not isinstance(data, dict):
        data = {}
    data[str(symbol).upper()] = {"last_exit_ts": ts, "last_exit_kind": kind}
    _write_json_atomic(_RECENT_EXITS_PATH, data)


def is_symbol_cooling_down(symbol: str, now: Optional[datetime] = None) -> dict[str, Any]:
    """Check whether a symbol is in a re-entry cooldown window.

    Returns a dict {"blocked": bool, "reason": str, "minutes_since": float|None}.
    SL cools for 60min; TP cools for 15min. EXPIRED does not cool.
    """
    if not symbol:
        return {"blocked": False, "reason": "", "minutes_since": None}
    data = _load_json(_RECENT_EXITS_PATH) or {}
    entry = data.get(str(symbol).upper()) if isinstance(data, dict) else None
    if not entry:
        return {"blocked": False, "reason": "", "minutes_since": None}
    try:
        last = datetime.fromisoformat(str(entry.get("last_exit_ts", "")).replace("Z", "+00:00"))
    except Exception:
        return {"blocked": False, "reason": "", "minutes_since": None}
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    _now = now or datetime.now(timezone.utc)
    if _now.tzinfo is None:
        _now = _now.replace(tzinfo=timezone.utc)
    delta_min = (_now - last).total_seconds() / 60.0
    kind = str(entry.get("last_exit_kind", "")).upper()
    if kind == "SL" and delta_min < _COOLDOWN_SL_MIN:
        return {"blocked": True, "reason": f"cooldown_sl_{int(_COOLDOWN_SL_MIN - delta_min)}min_left", "minutes_since": delta_min}
    if kind == "TP" and delta_min < _COOLDOWN_TP_MIN:
        return {"blocked": True, "reason": f"cooldown_tp_{int(_COOLDOWN_TP_MIN - delta_min)}min_left", "minutes_since": delta_min}
    return {"blocked": False, "reason": "", "minutes_since": delta_min}


def count_trades_today(now: Optional[datetime] = None) -> int:
    """Count picks entered today (UTC day) across active + closed ledgers."""
    _now = now or datetime.now(timezone.utc)
    if _now.tzinfo is None:
        _now = _now.replace(tzinfo=timezone.utc)
    today = _now.date().isoformat()
    count = 0
    for path in (_CLOSED_PICKS_PATH, _ACTIVE_PICKS_PATH):
        data = _load_json(path)
        picks = []
        if isinstance(data, list):
            picks = data
        elif isinstance(data, dict):
            picks = data.get("picks") or data.get("active") or []
        for p in picks:
            if not isinstance(p, dict):
                continue
            entry_ts = (
                p.get("entry_date")
                or p.get("entry_time")
                or p.get("created_at")
                or p.get("timestamp")
                or ""
            )
            if not entry_ts:
                continue
            if str(entry_ts)[:10] == today:
                count += 1
    return count


def is_daily_cap_reached(now: Optional[datetime] = None) -> dict[str, Any]:
    """Block when count_trades_today >= MAX_TRADES_PER_DAY (default 3)."""
    try:
        cap = int(os.environ.get("MAX_TRADES_PER_DAY", "3"))
    except Exception:
        cap = 3
    n = count_trades_today(now=now)
    if n >= cap:
        return {"blocked": True, "reason": "daily_cap_reached", "count": n, "cap": cap}
    return {"blocked": False, "reason": "", "count": n, "cap": cap}


def check_emission_gates(symbol: str, now: Optional[datetime] = None) -> dict[str, Any]:
    """Unified gate: cooldown + daily cap. Returns status dict.

    Callers at the pick-emission path should invoke this and, if blocked, tag
    the pick with status="cooldown_blocked" or status="daily_cap_reached".
    """
    cap = is_daily_cap_reached(now=now)
    if cap.get("blocked"):
        return {"blocked": True, "status": "daily_cap_reached", "reason": cap["reason"], "detail": cap}
    cool = is_symbol_cooling_down(symbol, now=now)
    if cool.get("blocked"):
        return {"blocked": True, "status": "cooldown_blocked", "reason": cool["reason"], "detail": cool}
    return {"blocked": False, "status": "ok", "reason": "", "detail": {"daily": cap, "cooldown": cool}}





COMMODITY_SYMBOLS = {
    "GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "ZC=F",
    "ZW=F", "ZS=F", "KC=F", "SB=F", "PL=F", "CT=F",
    # 2026-04-21: sync with alpha_engine/config.py COMMODITY_SYMBOLS so newly
    # emitted picks classify as asset_class=COMMODITY rather than falling back
    # to FUTURES via the sym.endswith("=F") branch below.
    "PA=F", "BZ=F", "RB=F", "HO=F", "ZM=F", "ZL=F",
    "CC=F", "OJ=F", "LE=F", "GF=F", "HE=F",
}

FUTURES_SYMBOLS = {
    "ES=F", "NQ=F", "YM=F", "ZN=F",
}

BOND_SYMBOLS = {
    "TLT", "IEF", "HYG", "ZN=F",
}

NON_CRYPTO_CATEGORIES = {"forex", "equity", "commodity", "futures", "bond"}


# Default stance: probation for all non-crypto unless a strategy explicitly earns
# the right to stay live. Thresholds reflect the current gap vs crypto.
NON_CRYPTO_STRATEGY_POLICY: dict[str, dict[str, Any]] = {
    "post-earnings-rev-scout": {
        "categories": {"equity"},
        "min_confidence": 0.68,
        "min_rr": 1.25,
        "min_elite_score": 55,
        "min_forward_trades": 2,
        "min_forward_wr": 0.40,
        "allow_without_forward": False,
    },
    "quality-momentum-scout": {
        "categories": {"equity"},
        "min_confidence": 0.68,
        "min_rr": 1.25,
        "min_elite_score": 55,
        "min_forward_trades": 2,
        "min_forward_wr": 0.50,
        "allow_without_forward": False,
    },
    # PR4 (2026-05-27): Promote equity_pead from shadow to probation.
    # Bernard & Thomas (1989) PEAD anomaly. 62.2% OOS WR on 2-day window.
    # Only WF-VERIFIED equity strategy. 30-day hold, 6% TP / 3% SL (2:1 R:R).
    "equity_pead": {
        "categories": {"equity"},
        "min_confidence": 0.58,
        "min_rr": 1.50,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.50,
        "allow_without_forward": True,  # Probation: build forward record
    },
    "cot_positioning": {
        "categories": {"forex", "commodity", "futures", "equity"},
        "min_confidence": 0.55,
        "min_rr": 1.25,
        "min_elite_score": 60,
        "min_forward_trades": 20,
        "min_forward_wr": 0.35,
        "allow_without_forward": False,
    },
    "cta_tsmom_blend": {
        "categories": {"forex", "commodity", "futures", "equity"},
        "min_confidence": 0.68,
        "min_rr": 1.20,
        "min_elite_score": 58,
        "min_forward_trades": 4,
        "min_forward_wr": 0.50,
        "allow_without_forward": False,
    },
    # PR #7 (2026-05-31): Restricted to futures-only — commodity sleeve retired
    # (class WR 11.9% / PF 0.29). Rebuild from non-COT signals before re-enabling.
    "cta_commodity_momentum_term": {
        "categories": {"futures"},
        "min_confidence": 0.67,
        "min_rr": 1.20,
        "min_elite_score": 58,
        "min_forward_trades": 2,
        "min_forward_wr": 0.50,
        "allow_without_forward": False,
    },
    # 2026-05-31 (tick30): DXY trend filter wire-up.
    # Already registered in multi_asset.forex_strategies.FOREX_STRATEGIES and
    # called via scanner.py FOREX_STRATEGIES.update(), but blocked by missing
    # policy entry ("strategy_on_probation"). Edge premise: EURUSD/GBPUSD/AUDUSD
    # have -0.95..-0.90 DXY correlation; entering aligned trades w/ DXY ADX>=20
    # trend confirmation is the textbook DXY macro overlay. Probationary until
    # forward record builds. Replaces cta_cross_asset_tsmom FOREX (0/86 WR, killed
    # via cap in cta_bridge.py same PR).
    "dxy_trend_filter": {
        "categories": {"forex"},
        "min_confidence": 0.55,
        "min_rr": 1.20,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.40,
        "allow_without_forward": True,  # Probation: build forward record
    },
    # INC FOREX P0 (2026-05-31): sole proven FOREX sleeve (57.6% WR SHORT, USDJPY-heavy).
    # Admission gate above restricts to SHORT only for forex category.
    "cta_cross_asset_tsmom": {
        "categories": {"forex", "commodity", "futures", "equity"},
        "min_confidence": 0.55,
        "min_rr": 1.20,
        "min_elite_score": 50,
        "min_forward_trades": 2,
        "min_forward_wr": 0.45,
        "allow_without_forward": True,
    },
    # INC FOREX P0/P1 (2026-05-31): probation allowlist for G10 carry (Lustig et al. 2011).
    # Losers (forex_rsi2, carry_trade_momentum, inverse_carry, forex_carry_ppp) moved to
    # BLACKLISTED_STRATEGIES in config.py.
    "forex_carry": {
        "categories": {"forex"},
        "min_confidence": 0.52,
        "min_rr": 1.20,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.40,
        "allow_without_forward": True,
    },
    # ── ETF strategies (new 2026-04-07) ──────────────────────────────────────
    # All start on probation (allow_without_forward=True) to build forward record.
    # Benchmarks: Antonacci dual-momentum 75%+ WR, Faber TAA ~65% WR in academic tests.
    "etf_dual_momentum": {
        "categories": {"etf"},
        "min_confidence": 0.50,
        "min_rr": 1.20,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.50,
        "allow_without_forward": True,
    },
    "etf_sector_momentum": {
        "categories": {"etf"},
        "min_confidence": 0.50,
        "min_rr": 1.20,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.50,
        "allow_without_forward": True,
    },
    "etf_risk_parity_rotation": {
        "categories": {"etf"},
        "min_confidence": 0.50,
        "min_rr": 1.20,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.50,
        "allow_without_forward": True,
    },
    "etf_trend_following": {
        "categories": {"etf"},
        "min_confidence": 0.50,
        "min_rr": 1.30,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.50,
        "allow_without_forward": True,
    },
    # Faber TAA (10-month / 200-day SMA) — Faber, JoWM 2007/2013/2020.
    # Published edge: Sharpe ~0.76, MaxDD ~-17%, avg-win/loss ~2.3, PF ~1.4,
    # per-trade WR ~45%. Baseline confidence 0.55 reflects moderate Sharpe;
    # min_rr 1.0 because exit is SMA-trail (no fixed TP), and forward gate
    # opens at 5 trades / 40% WR while we build a forward record.
    "etf_faber_tactical": {
        "categories": {"etf"},
        "min_confidence": 0.55,
        "min_rr": 1.0,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.50,
        "allow_without_forward": True,  # New strategy, build forward record
    },
    # ── Futures strategies (new 2026-04-07) ──────────────────────────────────
    # CL=F removed (3.8% WR on 26 trades). Only index/metal/bond futures here.
    # Benchmarks: TSMOM 55-60% WR (Moskowitz 2012), ConnorsRSI2 73-76% WR on proxies.
    "futures_tsmom": {
        "categories": {"futures"},
        "min_confidence": 0.50,
        "min_rr": 1.20,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.45,
        "allow_without_forward": True,
    },
    "futures_connors_rsi2": {
        "categories": {"futures"},
        "min_confidence": 0.55,
        "min_rr": 1.50,
        "min_elite_score": 55,
        "min_forward_trades": 5,
        "min_forward_wr": 0.55,
        "allow_without_forward": True,
    },
    "futures_cross_asset_momentum": {
        "categories": {"futures"},
        "min_confidence": 0.50,
        "min_rr": 1.20,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.45,
        "allow_without_forward": True,
    },
    "futures_vol_regime_breakout": {
        "categories": {"futures"},
        "min_confidence": 0.50,
        "min_rr": 1.20,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.45,
        "allow_without_forward": True,
    },
    # ── Bond strategies — KILLED 2026-05-31 (PR #7) ───────────────────────────
    # All bond strategies removed from allowlist. BOND class is hard-blocked at
    # the emission gate (0% WR / PF 0.00 / Sharpe -2.465). Re-enable path:
    #   1. Build viable yield-curve or duration strategy with backtest evidence
    #   2. Run 60-day forward test in shadow mode (n>=20, WR>=55%)
    #   3. Remove bond_class_kill_switch gate
    #   4. Add strategy back here with probation thresholds
    # Removed: bond_connors_rsi2, bond_duration_rotation, bond_ust_tsmom,
    #          bond_credit_spread_mean_reversion
    # ── Commodity TSMOM — RETIRED 2026-05-31 (PR #7) ──────────────────────────
    # commodity_tsmom_12m removed from allowlist (class WR 11.9% / PF 0.29).
    # Rebuild from non-COT signals: term structure, EIA inventory, weather overlay.
    # 2026-05-31 (tick33): Gold safe-haven policy entry — formalize probation.
    # Already registered in alpha_engine/commodities_strategies.py:1076 and
    # dispatched via scanner.py:2101 (COMMODITY_STRATEGIES.update on
    # strategy_filter in {"all","commodity"}), but had NO policy gate so
    # default-deny via _default_policy was the implicit behavior. Per PR #269
    # deep-dive: best wired commodity backtest (PF 1.98 / n=61) but
    # UNREPLICATED LIVE. Probationary gate gives it room to build a real
    # forward record without blanket admission. Floor matches commodity_tsmom_12m
    # (min_forward_wr 0.45) since they share the same vol-targeted long-only
    # commodity-future regime profile.
    "gold_safe_haven": {
        "categories": {"commodity"},
        "min_confidence": 0.55,
        "min_rr": 1.20,
        "min_elite_score": 50,
        "min_forward_trades": 5,
        "min_forward_wr": 0.45,
        "allow_without_forward": True,  # Probation: build forward record
    },
}


# ── TP/SL percentage caps by asset class ──────────────────────────────
# These are hard ceilings applied *after* strategy-level TP/SL calculation.
# Even if ATR or analyst targets suggest wider levels, these caps keep
# non-crypto picks in realistic swing-trade territory.
NON_CRYPTO_TP_SL_CAPS: dict[str, tuple[float, float]] = {
    # (max_tp_pct, max_sl_pct) relative to entry price
    # 2026-03-29: Tightened crypto caps based on SL distance analysis:
    #   SL < 1% = 60% WR, +0.48% avg | SL 2-3% = 37% WR, -5.05% avg
    #   SL > 5% = 45% WR, -16.88% avg — catastrophic tail losses
    "crypto":    (0.050, 0.020),   # 5.0% TP, 2.0% SL — data shows 2% is the quality cliff
    # 2026-04-25: WIDENED from (0.0075, 0.005) to (0.015, 0.008) — second
    # widening this month. The 2026-04-19 widening to 0.75%/0.5% wasn't enough:
    # realised FX class shows PF=0.26, expectancy=-$0.99/trade across 1,558
    # closed picks, with SL_HIT rate 44% vs TP_HIT 12% (3.7x more SLs than TPs).
    # 0.5% SL sits AT the median daily FX ATR (0.3-0.8% per code comment) —
    # essentially a noise filter, not a risk guard. Two-model Ollama Cloud
    # consensus (gpt-oss:120b + qwen3-coder:480b) recommends 0.8% SL (above
    # ATR ceiling) + 1.5% TP (1.875:1 R:R). All three forex cap locations
    # updated together: production_scanner.py TP_CAP_FOREX/SL_CAP_FOREX and
    # config.py CATEGORY_RISK forex. See updates/2026-04-25-forex-tpsl-review.md.
    #
    # PR3 (2026-05-27): WIDENED SL from 0.8% to 1.0%. Incident analysis shows
    # SL at 0.8% still sits at median daily FX ATR for volatile pairs (GBP, JPY).
    # 1.0% SL clears the ATR ceiling for all G10 pairs. TP unchanged at 1.5%.
    # Expected: SL_HIT rate drops from 44% to ~30%, R:R improves to 1.5:1.
    "forex":     (0.015, 0.010),   # 1.5% TP, 1.0% SL — PR3 ATR-clearing fix
    "equity":    (0.080, 0.050),   # 8.0% TP, 5.0% SL
    "etf":       (0.050, 0.030),   # 5.0% TP, 3.0% SL
    "commodity": (0.030, 0.020),   # 3.0% TP, 2.0% SL (commodities move 1-3%/day)
    "futures":   (0.030, 0.020),   # 3.0% TP, 2.0% SL (aligned with commodity)
    "bond":      (0.030, 0.020),   # 3.0% TP, 2.0% SL
}


def clamp_non_crypto_tp_sl(pick: dict[str, Any]) -> dict[str, Any]:
    """Enforce asset-class TP/SL percentage caps on a pick dict.

    Mutates and returns the pick.  Works for both LONG and SHORT directions.
    Fields expected: entry_price, take_profit, stop_loss, direction,
    and one of category / asset_class / symbol for classification.
    """
    entry = _to_float(pick.get("entry_price"))
    tp = _to_float(pick.get("take_profit"))
    sl = _to_float(pick.get("stop_loss"))
    if entry <= 0 or tp <= 0 or sl <= 0:
        return pick

    category = normalize_asset_category(
        pick.get("category"),
        pick.get("symbol"),
        pick.get("asset_class"),
    )
    caps = NON_CRYPTO_TP_SL_CAPS.get(category)
    if not caps:
        return pick

    max_tp_pct, max_sl_pct = caps
    direction = str(pick.get("direction", "LONG")).upper()

    if direction == "LONG":
        max_tp = entry * (1.0 + max_tp_pct)
        max_sl = entry * (1.0 - max_sl_pct)
        if tp > max_tp:
            pick["take_profit"] = round(max_tp, 6)
        if sl < max_sl:
            pick["stop_loss"] = round(max_sl, 6)
    else:  # SHORT
        max_tp = entry * (1.0 - max_tp_pct)
        max_sl = entry * (1.0 + max_sl_pct)
        if tp < max_tp:
            pick["take_profit"] = round(max_tp, 6)
        if sl > max_sl:
            pick["stop_loss"] = round(max_sl, 6)

    # Recalculate RR if present
    new_tp = _to_float(pick.get("take_profit"))
    new_sl = _to_float(pick.get("stop_loss"))
    risk = abs(entry - new_sl)
    if risk > 0:
        pick["rr"] = round(abs(new_tp - entry) / risk, 2)
        pick["risk_reward"] = pick["rr"]

    return pick


def _to_float(value: Any) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _normalize_wr(value: Any) -> float:
    wr = _to_float(value)
    return wr / 100.0 if wr > 1.0 else wr


def _normalize_strategy(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_asset_category(
    category: Any = None,
    symbol: Any = "",
    asset_class: Any = None,
) -> str:
    raw = str(category or asset_class or "").strip().lower()
    raw = {
        "stock": "equity",
        "stocks": "equity",
        # 2026-04-22 BUG FIX: "etf" was mapped to "equity" which caused ETF
        # picks to receive equity TP/SL caps (8%/5%) instead of ETF caps (5%/3%),
        # equity score floors instead of ETF floors, and equity-specific penalties
        # instead of ETF ones. ETF is a distinct asset class in NON_CRYPTO_TP_SL_CAPS
        # and quality_gates.py with its own calibrated thresholds.
        "index": "futures",  # Index symbols are futures-like; maps to futures TP/SL caps
        "fx": "forex",
    }.get(raw, raw)

    sym = str(symbol or "").upper().strip()
    if sym.endswith("=X"):
        return "forex"
    if sym in BOND_SYMBOLS:
        return "bond"
    if sym in COMMODITY_SYMBOLS:
        return "commodity"
    if raw in NON_CRYPTO_CATEGORIES:
        return raw
    if sym in FUTURES_SYMBOLS or sym.endswith("=F"):
        return "futures"
    if raw:
        return raw
    return "equity"


def is_non_crypto(
    category: Any = None,
    symbol: Any = "",
    asset_class: Any = None,
) -> bool:
    return normalize_asset_category(category, symbol, asset_class) in NON_CRYPTO_CATEGORIES


def evaluate_non_crypto_candidate(candidate: dict[str, Any], *, context: str = "live") -> dict[str, Any]:
    category = normalize_asset_category(
        candidate.get("category"),
        candidate.get("symbol"),
        candidate.get("asset_class"),
    )
    strategy = _normalize_strategy(candidate.get("strategy"))
    symbol = str(candidate.get("symbol") or "").upper()

    # Fix B + C: emission gates — re-entry cooldown + daily session cap.
    # Applied before strategy policy checks so any non-crypto pick is blocked
    # when the symbol just exited or the daily cap is reached.
    try:
        gate = check_emission_gates(symbol)
        if gate.get("blocked"):
            return {
                "allowed": False,
                "category": category,
                "strategy": strategy,
                "reason": gate.get("reason") or gate.get("status") or "emission_gate_blocked",
                "status": gate.get("status"),
            }
    except Exception:
        pass

    # INC FOREX P0 (2026-05-31): consolidate to proven sleeve + one probation carry leg.
    _FOREX_ALLOWED = frozenset({"cta_cross_asset_tsmom", "forex_carry", "forex_carry_g10"})
    if category == "forex":
        if strategy not in _FOREX_ALLOWED:
            return {
                "allowed": False,
                "category": category,
                "strategy": strategy,
                "reason": "forex_strategy_consolidation_blocked",
            }
        if strategy == "cta_cross_asset_tsmom":
            direction = str(candidate.get("direction", "LONG")).upper()
            if direction != "SHORT":
                return {
                    "allowed": False,
                    "category": category,
                    "strategy": strategy,
                    "reason": "cta_cross_asset_tsmom_short_only",
                }

    # PR #7 (2026-05-31): BOND Class Kill Switch
    # BOND class is 0% WR / PF 0.00 / Sharpe -2.465. All bond strategies are on
    # probation with zero verified forward trades. Re-enable only after a viable
    # yield-curve or duration strategy builds a forward record (n>=20, WR>=55%).
    if category == "bond":
        return {
            "allowed": False,
            "category": category,
            "strategy": strategy,
            "reason": "bond_class_kill_switch",
        }

    if category not in NON_CRYPTO_CATEGORIES:
        return {
            "allowed": True,
            "category": category,
            "strategy": strategy,
            "reason": "not_non_crypto",
        }

    if not strategy:
        return {
            "allowed": False,
            "category": category,
            "strategy": strategy,
            "reason": "missing_strategy",
        }

    policy = NON_CRYPTO_STRATEGY_POLICY.get(strategy)
    if not policy:
        return {
            "allowed": False,
            "category": category,
            "strategy": strategy,
            "reason": "strategy_on_probation",
        }

    if category not in policy["categories"]:
        return {
            "allowed": False,
            "category": category,
            "strategy": strategy,
            "reason": f"category_{category}_not_approved",
        }

    if candidate.get("paper_trade"):
        return {
            "allowed": False,
            "category": category,
            "strategy": strategy,
            "reason": "paper_trade_only",
        }

    if context == "smart_picks" and candidate.get("has_conflict"):
        return {
            "allowed": False,
            "category": category,
            "strategy": strategy,
            "reason": "conflicting_non_crypto_signal",
        }

    confidence = _to_float(candidate.get("confidence"))
    if confidence < policy["min_confidence"]:
        return {
            "allowed": False,
            "category": category,
            "strategy": strategy,
            "reason": f"confidence_below_{policy['min_confidence']:.2f}",
        }

    rr = max(
        _to_float(candidate.get("rr")),
        _to_float(candidate.get("rr_ratio")),
        _to_float(candidate.get("risk_reward")),
    )
    if rr and rr < policy["min_rr"]:
        return {
            "allowed": False,
            "category": category,
            "strategy": strategy,
            "reason": f"rr_below_{policy['min_rr']:.2f}",
        }

    elite_score = max(_to_float(candidate.get("elite_score")), _to_float(candidate.get("score")))
    if elite_score and elite_score < policy["min_elite_score"]:
        return {
            "allowed": False,
            "category": category,
            "strategy": strategy,
            "reason": f"elite_below_{policy['min_elite_score']:.0f}",
        }

    forward_trades = int(
        max(
            _to_float(candidate.get("strat_fwd_trades")),
            _to_float(candidate.get("forward_trades")),
            _to_float(candidate.get("history_trades")),
        )
    )
    forward_wr = max(
        _normalize_wr(candidate.get("strat_fwd_wr")),
        _normalize_wr(candidate.get("forward_wr")),
        _normalize_wr(candidate.get("history_wr")),
    )

    if forward_trades < policy["min_forward_trades"]:
        if not policy.get("allow_without_forward", False):
            return {
                "allowed": False,
                "category": category,
                "strategy": strategy,
                "reason": f"forward_sample_below_{policy['min_forward_trades']}",
            }
    elif forward_wr < policy["min_forward_wr"]:
        return {
            "allowed": False,
            "category": category,
            "strategy": strategy,
            "reason": f"forward_wr_below_{policy['min_forward_wr']:.2f}",
        }

    return {
        "allowed": True,
        "category": category,
        "strategy": strategy,
        "reason": "approved_non_crypto_strategy",
    }


# ── Pre-emission gates (Phase 1 rollout) ──────────────────────────────────────
# Audit on 3500 closed picks (2026-04-20) showed:
#   - 60% of forex picks force-close flat (TP/SL never hit) because they were
#     emitted outside the London/NY liquid window — sit dead until hold window
#     expires.
#   - 65% of commodity picks show the same pattern because TP distances
#     (avg 5.47%) vastly exceed realistic ATR-walk for the hold window
#     (avg max reach 0.72% at 24h).
#
# Shipped as two env-togglable gates so ops can flip them independently based
# on observed per-source rejection rates.

# Per-asset-class ATR fallback (percent of price) used when the pick dict does
# not carry an ATR estimate. These are rough daily-ATR averages based on 12mo
# history as of 2026-04-21; intentionally conservative.
_ATR_PCT_DEFAULTS: dict[str, float] = {
    "FOREX": 0.50,
    "COMMODITY": 1.20,
    "EQUITY": 1.80,
    "ETF": 1.20,
    "BOND": 0.40,
}


def passes_fx_session_gate(
    pick: dict[str, Any],
    now_utc: Optional[datetime] = None,
) -> tuple[bool, str]:
    """Block FOREX picks emitted outside the London/NY liquid window [07, 17] UTC.

    FOREX Rescue Operation (2026-05-08): Window widened to 07-17 UTC (extended London
    + NY morning overlap). Original 13-21 UTC study showed WR 58% vs 33% outside;
    07-17 UTC extends to London open to capture European session liquidity.
    Note: evidence base is for 13-21 UTC; 07-17 needs re-validation after FOREX re-enable.

    Uses current UTC hour at emission evaluation time. All FOREX strategies
    generate signals during 07-22 UTC via _session_guard in forex_strategies.py.
    At emission time (during 07-17 UTC London/NY overlap), carry_trade_momentum,
    london_session_breakout, and other overlap-session strategies emit correctly.
    asian_range_breakout (generates 21-07 UTC) emits at 14:00+ UTC but is blocked
    because 14 UTC is still within the gate range.

    Env: ``FX_SESSION_GATE`` (default ``"1"`` / ON). Set to ``"0"`` to disable.

    Returns ``(True, "")`` to emit, ``(False, reason)`` to block.
    """
    if os.environ.get("FX_SESSION_GATE", "1") != "1":
        return True, ""

    asset_class = str(pick.get("asset_class") or "").upper()
    if asset_class != "FOREX":
        return True, ""

    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    hour = now_utc.hour
    if 7 <= hour < 17:
        return True, ""

    return (
        False,
        f"fx_session_gate: outside London/NY overlap 07-17 UTC (hour={hour})",
    )


def passes_atr_reachability_gate(pick: dict[str, Any]) -> tuple[bool, str]:
    """Block non-crypto picks whose TP distance exceeds a heuristic ATR reach.

    Heuristic: ``max_reachable = 0.6 * atr_pct * sqrt(hold_hours / 24)``.
    If ``tp_dist_pct`` exceeds that, the TP is unlikely to be hit within the
    hold window and the pick will force-close flat at expiry.

    Env: ``ATR_REACH_GATE`` (default ``"0"`` / OFF). Set to ``"1"`` to enable.

    Shipped OFF initially because audit data (2026-04-21, 3500 closed picks)
    showed average commodity TP distance at 5.47% vs max reach 0.72% at the
    default 24h hold window — turning the gate ON at default would block
    roughly 80% of commodity picks before upstream strategies get a chance
    to tighten their TPs. Flip ON after observing per-source rejection-rate
    counters in a dry run and adjusting ``_ATR_PCT_DEFAULTS`` / the 0.6
    multiplier / strategy-side TP math.

    CRYPTO picks pass through unconditionally (this is a non-crypto gate).
    Missing fields fail-open: if entry/tp/hold/atr cannot be resolved, the
    pick emits.

    Returns ``(True, "")`` to emit, ``(False, reason)`` to block. The reason
    string starts with ``"atr_reachability_gate:"`` so rejections group cleanly
    in counters at call sites.
    """
    if os.environ.get("ATR_REACH_GATE", "0") != "1":
        return True, ""

    asset_class = str(pick.get("asset_class") or "").upper()
    if asset_class == "CRYPTO":
        return True, ""

    entry = _to_float(pick.get("entry_price"))
    tp = _to_float(pick.get("take_profit"))
    if tp <= 0:
        tp = _to_float(pick.get("tp_price"))
    sl = _to_float(pick.get("stop_loss"))
    if sl <= 0:
        sl = _to_float(pick.get("sl_price"))

    hold_hours = _to_float(pick.get("hold_window_hours"))
    if hold_hours <= 0:
        max_hold_days = _to_float(pick.get("max_hold_days"))
        if max_hold_days > 0:
            hold_hours = max_hold_days * 24.0

    if entry <= 0 or tp <= 0 or sl <= 0 or hold_hours <= 0:
        # Fail-open: no way to evaluate without all four inputs.
        return True, ""

    atr_pct = _to_float(pick.get("atr_pct"))
    if atr_pct <= 0:
        # Fall back to absolute-ATR fields, convert to percent of entry.
        for key in ("atr_14", "atr", "atr_at_entry"):
            raw = _to_float(pick.get(key))
            if raw > 0:
                # If the value is already small (< 5), assume it's absolute
                # price units and convert; if it's already in percent terms
                # (>= 5 on a forex pair is impossible → clearly percent), use
                # as-is.
                # Forex/bond/commodity raw ATRs are < 5 price units almost
                # always, so the heuristic below is safe.
                if raw < entry:
                    atr_pct = raw / entry * 100.0
                else:
                    atr_pct = raw
                break
    if atr_pct <= 0:
        atr_pct = _ATR_PCT_DEFAULTS.get(asset_class, 1.00)

    tp_dist_pct = abs(tp - entry) / entry * 100.0
    max_reachable = 0.6 * atr_pct * math.sqrt(hold_hours / 24.0)

    if tp_dist_pct > max_reachable:
        return (
            False,
            (
                f"atr_reachability_gate: tp_dist={tp_dist_pct:.2f}% "
                f"> max_reachable={max_reachable:.2f}% "
                f"given atr={atr_pct:.2f}% and hold={hold_hours:.0f}h"
            ),
        )

    return True, ""


def passes_non_crypto_policy(pick: dict[str, Any]) -> tuple[bool, str]:
    """Compose all pre-emission non-crypto gates. Returns first failure.

    Call sites should invoke this immediately before appending a pick to its
    output list. On ``(False, reason)``, skip emission and increment a counter
    keyed by the reason prefix (``fx_session_gate`` / ``atr_reachability_gate``)
    so rejection causes group cleanly in logs.
    """
    ok, reason = passes_fx_session_gate(pick)
    if not ok:
        return False, reason
    ok, reason = passes_atr_reachability_gate(pick)
    if not ok:
        return False, reason
    return True, ""
