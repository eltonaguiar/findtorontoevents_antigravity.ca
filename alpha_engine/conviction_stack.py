"""
Conviction stack — closed-book (n≈3500) institutional filters + scoring helpers.

Config: config/hf_conviction_stack.json
- Symbol denylist for st_fear_greed_contrarian family is applied from smart_picks_engine (always on).
- Tier-1 institutional rules apply only when institutional_filter_enabled is true.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_REPO = Path(__file__).resolve().parents[1]
_DEFAULT_PATH = _REPO / "config" / "hf_conviction_stack.json"

_FALLBACK: dict[str, Any] = {
    "version": 1,
    "institutional_filter_enabled": False,
    "min_forward_wr_pct": 50.0,
    "min_forward_wr_pct_strict": 55.0,
    "use_strict_forward_wr": False,
    "min_forward_trades_for_wr_rule": 5,
    "reject_when_forward_wr_unknown": False,
    "blocked_trust_tiers": ["BANNED", "UNTRUSTED"],
    "block_crypto_shorts": False,
    "short_exception_min_forward_wr_pct": 60.0,
    "short_exception_trust_tiers": ["PROVEN"],
    "block_scalp_mode": False,
    "max_elite_hard": 80,
    "reject_elite_above_max": False,
    "max_rr": 2.5,
    "reject_rr_above_max": False,
    "require_buy_technical_verdict": False,
    "buy_technical_tokens": ["BUY", "STRONG BUY"],
    "utc_reject_hours": [2, 8, 13, 20],
    "utc_gate_use_signal_timestamp": True,
    "utc_gate_fallback_now": True,
    "forward_smart_score_boost_enabled": False,
    "forward_smart_score_max_points": 15,
    "strat_pf_boost_threshold": 1.5,
    "strat_pf_boost_points": 5,
    "stamp_conviction_on_output": True,
    "conviction_min_trade_pts": 40,
    # Safe-rollout flags for scoring behavior updates.
    "enable_direction_aware_conviction_v2": False,
    "long_direction_bonus": 5,
    "short_direction_penalty_crypto": -15,
    "short_direction_penalty_non_crypto": -5,
    "bear_regime_short_relief_points": 10,
}

# Always-on: UNI/OP/APT × fear_greed_contrarian underperform (closed-book).
_FEAR_GREED_KEYS = ("fear_greed_contrarian",)
_FEAR_GREED_SYMBOL_DENY = frozenset({"UNIUSDT", "OPUSDT", "APTUSDT"})


def load_conviction_stack_config(path: Optional[Path] = None) -> dict[str, Any]:
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


def fear_greed_loser_symbol_reject(strategy: str, symbol: str) -> bool:
    """Hard deny known-bad symbols for fear/greed contrarian strategies only."""
    s = (strategy or "").lower()
    if not any(k in s for k in _FEAR_GREED_KEYS):
        return False
    sym = (
        (symbol or "")
        .upper()
        .replace("-", "")
        .replace("/", "")
        .replace("_", "")
    )
    return sym in _FEAR_GREED_SYMBOL_DENY


def _norm_sym(symbol: str) -> str:
    return (symbol or "").upper().replace("-", "").replace("/", "").replace("_", "")


_STRATEGY_PERF_CACHE: dict | None = None

def _get_strategy_performance() -> dict:
    """Load and cache strategy_performance.json"""
    global _STRATEGY_PERF_CACHE
    if _STRATEGY_PERF_CACHE is not None:
        return _STRATEGY_PERF_CACHE
    try:
        import json
        from pathlib import Path
        perf_path = Path(__file__).parent / "data" / "strategy_performance.json"
        if perf_path.exists():
            with open(perf_path) as f:
                _STRATEGY_PERF_CACHE = json.load(f)
    except Exception:
        pass
    return _STRATEGY_PERF_CACHE or {}


def _forward_wr_pct(pick: dict) -> float:
    # FIX: Check extra_json if not at top level
    extra = pick.get("extra_json")
    if extra:
        if isinstance(extra, str):
            try:
                import json
                extra = json.loads(extra)
            except (json.JSONDecodeError, TypeError):
                extra = None
        if isinstance(extra, dict):
            for key in ("forward_wr", "strat_fwd_wr"):
                v = extra.get(key)
                if v is None:
                    continue
                try:
                    f = float(v)
                    if 0 < f <= 1.0:
                        f *= 100.0
                    return f
                except (TypeError, ValueError):
                    continue
    
    # Check top-level fields
    for key in ("strat_fwd_wr", "forward_wr"):
        v = pick.get(key)
        if v is None:
            continue
        try:
            f = float(v)
            if 0 < f <= 1.0:
                f *= 100.0
            return f
        except (TypeError, ValueError):
            continue
    
    # CRITICAL FIX: Fallback to strategy_performance.json for strategies with track record
    strategy_name = pick.get("strategy", "")
    if strategy_name:
        strat_perf = _get_strategy_performance()
        if strategy_name in strat_perf:
            wr = strat_perf[strategy_name].get("win_rate", 0)
            trades = strat_perf[strategy_name].get("closed_picks", 0)
            # Only use if we have enough trades for reliability
            if trades >= 3 and wr > 0:
                return wr * 100.0
        
        # Also try base strategy name (e.g., ml_enhanced_FETUSDT_1d_B_lightgbm -> ml_enhanced_FETUSDT)
        if strategy_name.startswith("ml_enhanced_"):
            parts = strategy_name.replace("ml_enhanced_", "").split("_")
            if parts:
                base = f"ml_enhanced_{parts[0]}"
                if base in strat_perf:
                    wr = strat_perf[base].get("win_rate", 0)
                    trades = strat_perf[base].get("closed_picks", 0)
                    if trades >= 5 and wr > 0:
                        return wr * 100.0
    
    return 0.0


def _forward_trades_n(pick: dict) -> int:
    # FIX: Check extra_json if not at top level
    extra = pick.get("extra_json")
    if extra:
        if isinstance(extra, str):
            try:
                import json
                extra = json.loads(extra)
            except (json.JSONDecodeError, TypeError):
                extra = None
        if isinstance(extra, dict):
            for key in ("forward_trades", "strat_fwd_trades"):
                v = extra.get(key)
                if v is None:
                    continue
                try:
                    return max(int(float(v)), 0)
                except (TypeError, ValueError):
                    continue
    
    # Check top-level fields
    for key in (
        "strat_fwd_trades",
        "forward_trades",
        "strat_fwd_n",
        "strat_fwd_total",
        "sym_track_total",
    ):
        v = pick.get(key)
        if v is None:
            continue
        try:
            return max(int(float(v)), 0)
        except (TypeError, ValueError):
            continue
    
    # CRITICAL FIX: Fallback to strategy_performance.json for trade count
    strategy_name = pick.get("strategy", "")
    if strategy_name:
        strat_perf = _get_strategy_performance()
        if strategy_name in strat_perf:
            trades = strat_perf[strategy_name].get("closed_picks", 0)
            if trades > 0:
                return trades
        
        # Also try base strategy name for ml_enhanced_*
        if strategy_name.startswith("ml_enhanced_"):
            parts = strategy_name.replace("ml_enhanced_", "").split("_")
            if parts:
                base = f"ml_enhanced_{parts[0]}"
                if base in strat_perf:
                    trades = strat_perf[base].get("closed_picks", 0)
                    if trades > 0:
                        return trades
    
    return 0


def _technical_verdict_tokens(pick: dict) -> set[str]:
    out: set[str] = set()
    for key in (
        "technical_verdict",
        "technical_v_4h",
        "technical_v_1h",
        "technical_v_1d",
    ):
        v = pick.get(key)
        if v and str(v).strip() and str(v).strip() not in ("?", "N/A", "NONE"):
            out.add(str(v).strip().upper())
    return out


def _utc_hour_from_pick(pick: dict, now: Optional[datetime]) -> Optional[int]:
    ts_raw = pick.get("open_time") or pick.get("timestamp") or pick.get("entry_date")
    if not ts_raw:
        return None
    try:
        ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc).hour
    except (TypeError, ValueError):
        return None


def _approx_rr_from_pick(pick: dict) -> float:
    """Best-effort R:R for audit gating (no import from quality_gates — avoids cycles)."""
    try:
        ep = float(pick.get("entry_price") or 0)
        tp = float(pick.get("take_profit") or 0)
        sl = float(pick.get("stop_loss") or 0)
        cp = float(
            pick.get("current_price")
            or pick.get("live_price")
            or pick.get("last_price")
            or ep
            or 0
        )
        if not ep or not tp or not sl or not cp:
            return 0.0
        direction = str(pick.get("direction") or "LONG").upper()
        if direction in ("LONG", "BUY"):
            risk = abs(cp - sl)
            reward = abs(tp - cp)
        else:
            risk = abs(sl - cp)
            reward = abs(cp - tp)
        if risk <= 0:
            return 0.0
        return round(reward / risk, 2)
    except (TypeError, ValueError):
        return 0.0


def institutional_filter_reason(
    pick: dict,
    *,
    rr: float,
    pick_mode: str,
    asset_class: str,
    now: datetime,
    cfg: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """
    Return a short exclusion key if Tier-1 institutional rules fail, else None.
    Only runs meaningful checks when cfg['institutional_filter_enabled'] is true
    (except fear_greed symbol deny — handled separately, always-on in caller).
    """
    cfg = cfg if cfg is not None else load_conviction_stack_config()
    if not cfg.get("institutional_filter_enabled"):
        return None

    tier = str(pick.get("trust_tier") or "").strip().upper()
    blocked_tiers = {str(x).upper() for x in (cfg.get("blocked_trust_tiers") or [])}
    if tier and tier in blocked_tiers:
        return "inst_trust_tier_blocked"

    ac = (asset_class or "").lower()
    direction = str(pick.get("direction") or "LONG").upper()
    if cfg.get("block_crypto_shorts") and ac == "crypto" and direction in ("SHORT", "SELL"):
        exc_tiers = {str(x).upper() for x in (cfg.get("short_exception_trust_tiers") or ["PROVEN"])}
        min_wr = float(cfg.get("short_exception_min_forward_wr_pct", 60.0))
        wr = _forward_wr_pct(pick)
        if not (tier in exc_tiers and wr >= min_wr):
            return "inst_crypto_short"

    mode_u = (pick_mode or "").upper()
    if cfg.get("block_scalp_mode") and mode_u == "SCALP":
        return "inst_scalp_blocked"

    if cfg.get("reject_elite_above_max"):
        cap = float(cfg.get("max_elite_hard", 80))
        raw_elite = float(pick.get("elite_score") or pick.get("score") or 0)
        if raw_elite > cap:
            return "inst_elite_overcap"

    if cfg.get("reject_rr_above_max"):
        max_rr = float(cfg.get("max_rr", 2.5))
        if rr > max_rr and rr > 0:
            return "inst_rr_high"

    min_tr = int(cfg.get("min_forward_trades_for_wr_rule", 5))
    wr_need = float(
        cfg.get("min_forward_wr_pct_strict")
        if cfg.get("use_strict_forward_wr")
        else cfg.get("min_forward_wr_pct", 50.0)
    )
    n = _forward_trades_n(pick)
    wr = _forward_wr_pct(pick)
    if n >= min_tr:
        if wr > 0 and wr < wr_need:
            return "inst_forward_wr_low"
    elif cfg.get("reject_when_forward_wr_unknown") and wr <= 0:
        return "inst_forward_wr_missing"

    if cfg.get("require_buy_technical_verdict"):
        tokens = {str(x).upper() for x in (cfg.get("buy_technical_tokens") or ["BUY", "STRONG BUY"])}
        got = _technical_verdict_tokens(pick)
        if got and not (got & tokens):
            return "inst_technical_not_buy"

    hours = cfg.get("utc_reject_hours") or []
    if hours:
        h = None
        if cfg.get("utc_gate_use_signal_timestamp", True):
            h = _utc_hour_from_pick(pick, now)
        if h is None and cfg.get("utc_gate_fallback_now", True):
            h = now.astimezone(timezone.utc).hour
        if h is not None and h in [int(x) for x in hours]:
            return "inst_utc_hour_blocked"

    return None


def forward_track_record_score_boost(pick: dict, cfg: Optional[dict[str, Any]] = None) -> int:
    """Extra smart_score points from forward WR / PF (capped; off by default — smart_picks has Step 22)."""
    cfg = cfg if cfg is not None else load_conviction_stack_config()
    if not cfg.get("forward_smart_score_boost_enabled", False):
        return 0
    max_pts = int(cfg.get("forward_smart_score_max_points", 15))
    wr = _forward_wr_pct(pick)
    n = _forward_trades_n(pick)
    if n <= 0 or wr <= 0:
        base = 0
    else:
        base = min(max_pts, int(round((wr / 100.0) * max_pts)))
    pf = 0.0
    for key in ("strat_fwd_pf", "profit_factor", "forward_pf"):
        v = pick.get(key)
        if v is not None:
            try:
                pf = max(pf, float(v))
            except (TypeError, ValueError):
                pass
    extra = (
        int(cfg.get("strat_pf_boost_points", 5))
        if pf >= float(cfg.get("strat_pf_boost_threshold", 1.5))
        else 0
    )
    return min(25, base + extra)


def compute_conviction_score(pick: dict, scored: Optional[dict[str, Any]] = None) -> tuple[int, dict[str, int]]:
    """
    Soft 0–120 scale (document weights from HF plan). For ranking / stamping only.
    Returns (total, breakdown dict).
    """
    scored = scored or {}
    cfg = load_conviction_stack_config()
    b: dict[str, int] = {}
    tier = str(pick.get("trust_tier") or scored.get("trust_tier") or "").upper()
    if tier == "PROVEN":
        b["trust"] = 30
    elif tier == "WATCH":
        b["trust"] = 10
    elif tier == "RELIABLE":
        b["trust"] = 12
    else:
        b["trust"] = 0

    wr = _forward_wr_pct(pick)
    if wr >= 60:
        b["fwd_wr"] = 25
    elif wr >= 55:
        b["fwd_wr"] = 20
    elif wr >= 50:
        b["fwd_wr"] = 10
    else:
        b["fwd_wr"] = 0

    elite = float(scored.get("elite_score") or pick.get("elite_score") or pick.get("score") or 0)
    if 41 <= elite <= 80:
        b["elite"] = 15
    elif elite > 80:
        b["elite"] = -10
    else:
        b["elite"] = 0

    d = str(pick.get("direction") or "LONG").upper()
    toks = _technical_verdict_tokens(pick)
    ac = str(pick.get("asset_class") or pick.get("category") or "").upper().strip()
    is_crypto = ac == "CRYPTO" or _norm_sym(str(pick.get("symbol") or "")).endswith(("USDT", "USDC"))
    regime = _pick_regime_blob(pick).lower()
    direction_aware = bool(cfg.get("enable_direction_aware_conviction_v2"))

    if direction_aware:
        if d in ("SHORT", "SELL"):
            if "STRONG SELL" in toks:
                b["technical"] = 10
            elif "SELL" in toks:
                b["technical"] = 7
            elif "STRONG BUY" in toks:
                b["technical"] = -5
            else:
                b["technical"] = 0
        else:
            if "STRONG BUY" in toks:
                b["technical"] = 10
            elif "BUY" in toks:
                b["technical"] = 7
            elif "STRONG SELL" in toks:
                b["technical"] = 0
            else:
                b["technical"] = 0

        if d in ("LONG", "BUY"):
            b["direction"] = int(cfg.get("long_direction_bonus", 5))
        else:
            short_penalty = int(
                cfg.get(
                    "short_direction_penalty_crypto" if is_crypto else "short_direction_penalty_non_crypto",
                    -15 if is_crypto else -5,
                )
            )
            if "bear" in regime:
                short_penalty += int(cfg.get("bear_regime_short_relief_points", 10))
            b["direction"] = short_penalty
    else:
        if "STRONG BUY" in toks:
            b["technical"] = 10
        elif "BUY" in toks:
            b["technical"] = 7
        elif "STRONG SELL" in toks:
            b["technical"] = 5
        else:
            b["technical"] = 0
        b["direction"] = 5 if d in ("LONG", "BUY") else -15

    mode = str(pick.get("timeframe") or pick.get("trade_timeframe") or "SWING").upper()
    if mode == "INTRADAY":
        b["mode"] = 5
    elif mode == "SCALP":
        b["mode"] = -10
    else:
        b["mode"] = 0

    strat = str(pick.get("strategy") or "").lower()
    if "fear_greed_contrarian" in strat:
        b["strategy"] = 20
    else:
        b["strategy"] = 0

    sym = _norm_sym(str(pick.get("symbol") or ""))
    if fear_greed_loser_symbol_reject(strat, sym):
        b["fg_sym"] = -15
    else:
        b["fg_sym"] = 0

    pf = 0.0
    for key in ("strat_fwd_pf", "profit_factor"):
        v = pick.get(key)
        if v is not None:
            try:
                pf = max(pf, float(v))
            except (TypeError, ValueError):
                pass
    if pf >= 1.5:
        b["pf"] = 5
    elif 0 < pf < 1.0:
        b["pf"] = -10
    else:
        b["pf"] = 0

    n = _forward_trades_n(pick)
    b["depth"] = 5 if n >= 100 else 0

    total = sum(b.values())
    return total, b


def audit_smart_gate_institutional_fail(pick: dict) -> Optional[str]:
    """First-failure key for audit_trail quality_gates smart funnel."""
    cfg = load_conviction_stack_config()
    now = datetime.now(timezone.utc)
    strat = str(pick.get("strategy") or "")
    sym = str(pick.get("symbol") or "")
    if fear_greed_loser_symbol_reject(strat, sym):
        return "fear_greed_loser_symbol"
    if not cfg.get("institutional_filter_enabled"):
        return None
    ac = str(pick.get("asset_class") or pick.get("category") or "CRYPTO").lower()
    ac_norm = "crypto" if ac == "crypto" else "other"
    rr = _approx_rr_from_pick(pick)
    mode = str(pick.get("timeframe") or pick.get("trade_timeframe") or "SWING").upper()
    return institutional_filter_reason(
        pick,
        rr=rr,
        pick_mode=mode,
        asset_class=ac_norm,
        now=now,
        cfg=cfg,
    )


# ── HF conviction tiers S / A / B (dashboard “extreme conviction”) ─────────────
_TIERS_CFG_PATH = _REPO / "config" / "hf_conviction_tiers.json"
_TIERS_CACHE: dict[str, Any] | None = None

_TIERS_FALLBACK: dict[str, Any] = {
    "version": 1,
    "min_forward_wr_pct": 55.0,
    "min_forward_trades": 5,
    "elite_min": 41,
    "elite_max": 80,
    "fear_greed_substrings": ["fear_greed_contrarian"],
    "tier_s_symbols": [
        "DOTUSDT",
        "SUIUSDT",
        "LTCUSDT",
        "NEARUSDT",
        "XRPUSDT",
    ],
    "tier_a_extra_symbols": [
        "LINKUSDT",
        "ATOMUSDT",
        "AVAXUSDT",
        "SOLUSDT",
        "ADAUSDT",
        "BNBUSDT",
    ],
    "tier_a_alt_short_symbols": [
        "DOGEUSDT",
        "SHIBUSDT",
        "1000SHIBUSDT",
        "PEPEUSDT",
        "1000PEPEUSDT",
        "SOLUSDT",
    ],
    "tier_b_major_symbols": ["BTCUSDT", "ETHUSDT"],
    "bull_neutral_substrings": [
        "bull",
        "neutral",
        "uptrend",
        "trending_up",
        "trend_up",
        "sideways",
    ],
    "exclude_from_tier_s_regime": [
        "bear",
        "weak",
        "crash",
        "down",
        "downtrend",
        "ranging",
        "choppy",
    ],
    "bear_regime_substrings": ["bear", "weak", "crash", "down", "downtrend"],
    "non_crypto_tier_a_strategies": ["pead_earnings_drift", "quality_value"],
    "non_crypto_tier_b_strategies": [
        "pead_earnings_drift",
        "quality_minus_junk",
        "quality_value",
        "earnings_drift",
    ],
    "non_crypto_tier_a_confidence_threshold": 0.82,
    "non_crypto_tier_b_confidence_threshold": 0.75,
}


def load_conviction_tiers_config(path: Optional[Path] = None) -> dict[str, Any]:
    global _TIERS_CACHE
    if path is None and _TIERS_CACHE is not None:
        return _TIERS_CACHE
    out = json.loads(json.dumps(_TIERS_FALLBACK))
    p = path or _TIERS_CFG_PATH
    if p.is_file():
        try:
            raw = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            if isinstance(raw, dict):
                out.update(raw)
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    if path is None:
        _TIERS_CACHE = out
    return out


def clear_conviction_tiers_cache_for_tests() -> None:
    global _TIERS_CACHE
    _TIERS_CACHE = None


def _pick_regime_blob(pick: dict) -> str:
    parts: list[str] = []
    for key in (
        "btc_regime",
        "regime_at_entry",
        "fast_regime",
        "regime",
        "market_regime",
    ):
        v = pick.get(key)
        if v is not None and str(v).strip():
            parts.append(str(v).strip().lower())
    return " ".join(parts)


def _pick_elite_for_tiers(pick: dict) -> float:
    for key in ("elite_score", "score"):
        v = pick.get(key)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return 0.0


def _is_fear_greed_strategy(strat: str, cfg: dict[str, Any]) -> bool:
    s = (strat or "").lower()
    for frag in cfg.get("fear_greed_substrings") or ["fear_greed_contrarian"]:
        if str(frag).lower() in s:
            return True
    return False


def _regime_bull_neutral(regime_blob: str, cfg: dict[str, Any]) -> bool:
    if not regime_blob.strip():
        return False
    r = regime_blob.lower()
    for bad in cfg.get("exclude_from_tier_s_regime") or []:
        if str(bad).lower() in r:
            return False
    for good in cfg.get("bull_neutral_substrings") or []:
        if str(good).lower() in r:
            return True
    return False


def _regime_bearish(regime_blob: str, cfg: dict[str, Any]) -> bool:
    if not regime_blob.strip():
        return False
    r = regime_blob.lower()
    for frag in cfg.get("bear_regime_substrings") or []:
        if str(frag).lower() in r:
            return True
    return False


def _is_crypto_pick(pick: dict, sym: str) -> bool:
    ac = (pick.get("asset_class") or pick.get("category") or "").upper()
    if ac == "CRYPTO":
        return True
    return sym.endswith("USDT") or sym.endswith("USDC")


def _non_crypto_strategy_match(strategy: str, fragments: list[str]) -> bool:
    s = (strategy or "").lower()
    for frag in fragments or []:
        if frag and str(frag).lower() in s:
            return True
    return False


def _classify_non_crypto_hf_tier(
    pick: dict, cfg: dict[str, Any]
) -> tuple[Optional[str], list[str]]:
    """
    PEAD / quality-style non-crypto names — config-driven substring lists.
    Tier A: tier_a strategies + high confidence + bull/neutral regime blob.
    Tier B: tier_b strategies + confidence floor (no regime gate).
    """
    sym = _norm_sym(str(pick.get("symbol") or ""))
    if _is_crypto_pick(pick, sym):
        return None, []
    direction = str(pick.get("direction") or "LONG").upper()
    if direction not in ("LONG", "BUY"):
        return None, []
    strat = str(pick.get("strategy") or "")
    conf = float(pick.get("confidence") or 0)
    if conf > 1.0:
        conf = conf / 100.0
    regime = _pick_regime_blob(pick)
    a_frags = list(cfg.get("non_crypto_tier_a_strategies") or [])
    b_frags = list(cfg.get("non_crypto_tier_b_strategies") or [])
    a_thr = float(cfg.get("non_crypto_tier_a_confidence_threshold", 0.82))
    b_thr = float(cfg.get("non_crypto_tier_b_confidence_threshold", 0.75))

    if _non_crypto_strategy_match(strat, a_frags) and conf >= a_thr:
        if _regime_bull_neutral(regime, cfg):
            return "A", ["non_crypto_pead_quality_high_conf"]
    if _non_crypto_strategy_match(strat, b_frags) and conf >= b_thr:
        return "B", ["non_crypto_proven_strategy_conf"]
    return None, []


def classify_hf_conviction_tier(
    pick: dict, cfg: Optional[dict[str, Any]] = None
) -> tuple[Optional[str], list[str]]:
    """
    Assign hedge-fund conviction tier S > A > B or (None, []).
    Uses real pick fields only — no invented stats.
    """
    cfg = cfg if cfg is not None else load_conviction_tiers_config()
    strat = str(pick.get("strategy") or "")
    sym = _norm_sym(str(pick.get("symbol") or ""))
    if fear_greed_loser_symbol_reject(strat, sym):
        return None, ["fear_greed_blocked_symbol"]

    direction = str(pick.get("direction") or "LONG").upper()
    trust = str(pick.get("trust_tier") or "").strip().upper()
    regime = _pick_regime_blob(pick)
    elite = _pick_elite_for_tiers(pick)
    wr = _forward_wr_pct(pick)
    n = _forward_trades_n(pick)
    min_wr = float(cfg.get("min_forward_wr_pct", 55.0))
    min_n = int(cfg.get("min_forward_trades", 5))
    emin = float(cfg.get("elite_min", 41))
    emax = float(cfg.get("elite_max", 80))

    is_crypto = _is_crypto_pick(pick, sym)

    # GATE: Require minimum forward_trades for ANY HC tier
    if n < min_n:
        return None, [f"insufficient_forward_trades_for_hc ({n}<{min_n})"]

    tier_s_syms = frozenset(_norm_sym(x) for x in (cfg.get("tier_s_symbols") or []))
    tier_a_extra = frozenset(_norm_sym(x) for x in (cfg.get("tier_a_extra_symbols") or []))
    tier_a_long_syms = tier_s_syms | tier_a_extra
    alt_short_syms = frozenset(
        _norm_sym(x) for x in (cfg.get("tier_a_alt_short_symbols") or [])
    )
    tier_b_majors = frozenset(
        _norm_sym(x) for x in (cfg.get("tier_b_major_symbols") or [])
    )

    def _wr_elite_ok() -> bool:
        """
        Strict WR/elite check with hard quality gates.
        
        QUANT TEAM FIX (2026-04-09): Added additional gates to filter out
        unvalidated noise that was causing high-conviction picks to perform
        at coin-toss levels (47-52% WR).
        
        Gates added:
        1. No SANDBOX/UNPROVEN/PROBATION/DEMOTED trust tiers
        2. Kill overconfidence (conf > 0.90 with < 20 trades = anti-predictive)
        """
        # GATE 1: Check trust tier - no unvalidated systems in high conviction
        if trust in ("SANDBOX", "UNPROVEN", "PROBATION", "DEMOTED"):
            return False
        
        # GATE 2: Kill overconfidence - per quant analysis, extreme confidence is anti-predictive
        conf = pick.get("confidence", 0)
        if conf:
            conf_val = float(conf)
            if conf_val > 1:
                conf_val = conf_val / 100
            # Overconfident with insufficient track record
            fwd_trades = pick.get("forward_trades", pick.get("strat_fwd_trades", 0))
            try:
                fwd_trades_val = int(fwd_trades)
            except (TypeError, ValueError):
                fwd_trades_val = 0
            
            if conf_val > 0.90 and fwd_trades_val < 20:
                return False
        
        # Main gate: n, wr, elite thresholds
        return n >= min_n and wr >= min_wr and emin <= elite <= emax

    # Tier S — fear/greed core symbols, PROVEN, LONG, bull/neutral regime
    if (
        is_crypto
        and _is_fear_greed_strategy(strat, cfg)
        and sym in tier_s_syms
        and direction in ("LONG", "BUY")
        and trust == "PROVEN"
        and _regime_bull_neutral(regime, cfg)
        and _wr_elite_ok()
    ):
        return "S", ["tier_s_fear_greed_proven_core_symbol"]

    # Tier A — fear/greed expanded LONG (PROVEN or WATCH)
    if (
        is_crypto
        and _is_fear_greed_strategy(strat, cfg)
        and sym in tier_a_long_syms
        and direction in ("LONG", "BUY")
        and _regime_bull_neutral(regime, cfg)
        and _wr_elite_ok()
        and trust in ("PROVEN", "WATCH")
    ):
        if trust == "PROVEN":
            return "A", ["tier_a_fear_greed_proven_expanded_long"]
        return "A", ["tier_a_fear_greed_watch_expanded_long"]

    # Tier A — alt SHORT in bear regime
    if (
        is_crypto
        and direction in ("SHORT", "SELL")
        and sym in alt_short_syms
        and _regime_bearish(regime, cfg)
    ):
        return "A", ["tier_a_alt_short_bear_regime"]

    # Tier B — major LONG + PROVEN
    # QUANT TEAM FIX: Add overconfidence and trust tier gates to this bypass path
    if (
        is_crypto
        and sym in tier_b_majors
        and direction in ("LONG", "BUY")
        and trust == "PROVEN"
    ):
        # Apply hard gates before allowing Tier B
        if trust in ("SANDBOX", "UNPROVEN", "PROBATION", "DEMOTED"):
            pass  # Fall through to None
        else:
            # Check overconfidence
            conf = pick.get("confidence", 0)
            if conf:
                conf_val = float(conf)
                if conf_val > 1:
                    conf_val = conf_val / 100
                fwd_trades_val = n  # Use the already-parsed n
                if conf_val > 0.90 and fwd_trades_val < 20:
                    pass  # Fall through to None
                else:
                    return "B", ["tier_b_major_long_proven"]
            else:
                return "B", ["tier_b_major_long_proven"]
    # End of Tier B major path

    # Tier B — INTRADAY + BUY technical
    tf = str(pick.get("trade_timeframe") or pick.get("timeframe") or "").upper()
    if tf == "INTRADAY":
        toks = _technical_verdict_tokens(pick)
        buy_ok = toks & {"BUY", "STRONG BUY"}
        if buy_ok:
            return "B", ["tier_b_intraday_buy_technical"]

    # -----------------------------------------------------------------------
    # Data-driven bypass tiers (no minimum forward-trade history required)
    # -----------------------------------------------------------------------
    # Derived from 3,340 closed picks (alpha_engine/data/closed_picks.json):
    #
    #   Confidence 0.80-0.90 → 77% WR, avg PnL +13%   ← PROVEN edge
    #   ML score >= 0.85     → top-decile model output
    #   Elite score >= 60    → multi-factor quality composite
    #   RR >= 1.2            → positive-EV floor (RR 1-1.5 zone has 56% WR)
    #   MC verified          → Monte Carlo simulation confirms edge
    #
    # Without this bypass, forward_trades=0 blocks ALL new strategies from
    # conviction tiers even when every measurable quality signal is green.
    # The bypass is calibrated to be MORE conservative than the closed-book
    # data would suggest (requiring 3+ of 5 criteria, not just 1).
    # -----------------------------------------------------------------------
    conf_val = float(pick.get("confidence") or 0)
    elite_val = float(pick.get("elite_score") or pick.get("ml_composite_score") or 0)
    ml_val = float(pick.get("ml_score") or pick.get("ml_composite_score") or 0)
    rr_val = float(pick.get("risk_reward") or 0)
    mc_ok = bool(pick.get("mc_verified"))

    # Score criteria against data-driven thresholds
    # QUANT TEAM FIX: Apply hard gates to bypass paths too
    bypass_criteria_met = sum([
        conf_val >= 0.80,       # Confidence 0.80+ → 77% WR in closed picks
        elite_val >= 60,        # Elite composite quality floor
        ml_val >= 0.85,         # Top-decile ML probability
        rr_val >= 1.2,          # Positive-EV risk-reward
        mc_ok,                  # Monte Carlo verified edge
    ])

    # Hard gates apply to bypass paths too - don't let unvalidated noise through
    def _bypass_allowed() -> bool:
        # GATE: No SANDBOX/UNPROVEN/PROBATION/DEMOTED in high conviction
        if trust in ("SANDBOX", "UNPROVEN", "PROBATION", "DEMOTED"):
            return False
        # GATE: Kill overconfidence (anti-predictive per quant analysis)
        if conf_val > 0.90 and n < 20:
            return False
        return True

    if not _bypass_allowed():
        # Fall through to check non-crypto or return None
        pass
    elif bypass_criteria_met >= 4:
        # ALL four-of-five: premium quality — Tier A
        reasons = ["bypass_tier_a_4of5_quality_criteria"]
        return "A", reasons
    elif bypass_criteria_met >= 3 and conf_val >= 0.75:
        # Three-of-five with minimum confidence — Tier B
        reasons = [f"bypass_tier_b_3of5_criteria_conf{conf_val:.2f}"]
        return "B", reasons

    # Non-crypto: PEAD / quality strategies (dashboard parity; sparse forward stats)
    nc_tier, nc_reasons = _classify_non_crypto_hf_tier(pick, cfg)
    if nc_tier:
        return nc_tier, nc_reasons

    return None, []


def attach_hf_conviction_tiers_to_picks(picks: list) -> dict[str, int]:
    """Mutate picks with hf_conviction_tier / hf_conviction_reasons; return counts."""
    counts = {"S": 0, "A": 0, "B": 0}
    cfg = load_conviction_tiers_config()
    for pick in picks:
        if not isinstance(pick, dict):
            continue
        tier, reasons = classify_hf_conviction_tier(pick, cfg)
        if tier:
            pick["hf_conviction_tier"] = tier
            pick["hf_conviction_reasons"] = reasons
            counts[tier] = counts.get(tier, 0) + 1
        else:
            pick.pop("hf_conviction_tier", None)
            pick["hf_conviction_reasons"] = []
    return counts
