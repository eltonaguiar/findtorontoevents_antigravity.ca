#!/usr/bin/env python3
"""
ALPHA ENGINE -- Score Booster
================================
Fixes broken scoring by boosting picks from strategy families with PROVEN
performance track records. Runs every dashboard cycle, AFTER the dashboard
generator produces the payload, BEFORE the HTML template is built.

The elite_scorer intentionally deflates copy_trader scores (caps confidence,
zeros forward WR, gives minimal source system points). While that's correct
for untested strategies, it creates a huge blind spot: 95+ winning crypto
picks (+338% total PnL) are hidden because their scores sit below 50.

This module applies evidence-based score boosts to fix that.

Usage:
  python -m alpha_engine.score_booster           # standalone
  python alpha_engine/score_booster.py            # direct
"""
from __future__ import annotations

import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── Windows UTF-8 fix ──
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent

# ── MTF gate (optional import — must not crash pipeline) ──
try:
    from alpha_engine.mtf_gate import check_mtf_alignment as _check_mtf
    _HAS_MTF_GATE = True
except ImportError:
    try:
        from mtf_gate import check_mtf_alignment as _check_mtf
        _HAS_MTF_GATE = True
    except ImportError:
        _HAS_MTF_GATE = False

# ──────────────────────────────────────────────────────────────────────
# Binance circuit breaker (module-level)
# ──────────────────────────────────────────────────────────────────────
# Problem: mtf_gate and ensemble_gate make Binance API calls that bypass
# config.py's circuit breaker. In CI (geo-blocked) this wastes 3+ minutes.
# Solution: track failures here and disable all Binance-dependent gates
# after 3 consecutive failures or an immediate 451 geo-block response.
_BINANCE_FAIL_COUNT: int = 0
_BINANCE_DISABLED: bool = False
_BINANCE_FAIL_THRESHOLD: int = 3
_IN_CI: bool = os.environ.get("GITHUB_ACTIONS") == "true"


def _binance_gate_call(fn, *args, **kwargs):
    """Wrap a Binance-dependent gate call with circuit breaker logic.

    On success: resets the failure counter.
    On failure: increments counter; after 3 consecutive failures (or a
    single HTTP 451 in CI) disables ALL remaining Binance calls for this run.
    Returns the gate result dict on success, or None when the breaker is open.
    """
    global _BINANCE_FAIL_COUNT, _BINANCE_DISABLED

    if _BINANCE_DISABLED:
        return None

    try:
        result = fn(*args, **kwargs)
        # Success — reset counter
        _BINANCE_FAIL_COUNT = 0
        return result
    except Exception as exc:
        _BINANCE_FAIL_COUNT += 1

        # Immediate disable on 451 geo-block (especially in CI)
        exc_str = str(exc)
        if "451" in exc_str or "geo" in exc_str.lower():
            _BINANCE_DISABLED = True
            logging.getLogger("score_booster").warning(
                "Binance geo-blocked (451) — circuit breaker OPEN, skipping all remaining Binance calls"
            )
            return None

        # Immediate disable in CI on any HTTP error (Binance is always geo-blocked in GitHub Actions)
        if _IN_CI and ("HTTP" in exc_str or "URLError" in exc_str or "timeout" in exc_str.lower()):
            _BINANCE_DISABLED = True
            logging.getLogger("score_booster").warning(
                "Binance unreachable in CI — circuit breaker OPEN, skipping all remaining Binance calls"
            )
            return None

        if _BINANCE_FAIL_COUNT >= _BINANCE_FAIL_THRESHOLD:
            _BINANCE_DISABLED = True
            logging.getLogger("score_booster").warning(
                "Binance circuit breaker OPEN after %d consecutive failures — skipping all remaining calls",
                _BINANCE_FAIL_COUNT,
            )
        else:
            logging.getLogger("score_booster").debug(
                "Binance call failed (%d/%d): %s", _BINANCE_FAIL_COUNT, _BINANCE_FAIL_THRESHOLD, exc
            )
        return None


PAYLOAD_PATH = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
BOOST_LOG_PATH = ROOT / "alpha_engine" / "data" / "score_boost_log.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("score_booster")

# Systems with consistently low forward WR that drag elite scores down.
# Exported so safety_status.py can reference without re-defining.
WEAK_SYSTEMS_SET: frozenset[str] = frozenset({
    "luxalgo_filters", "crypto_winners", "baby_strats_forward", "claude_gainer_st",
})

# ──────────────────────────────────────────────────────────────────────
# Strategy family classification
# ──────────────────────────────────────────────────────────────────────
# Maps strategy/source_system substrings to a family name.
# Order matters: first match wins.
FAMILY_TAGS = [
    ("copy_trader_consensus", ["copy_trader_consensus", "ct_consensus_"]),
    ("copy_trader_highscore", ["copy_trader_highscore", "highscore", "hs_"]),
    ("copy_trader_clones", ["copy_trader_clones", "clone_hl_"]),
    ("copy_trader_intel", ["copy_trader_intel", "copy_hl_", "copy_trader"]),
    ("kimi_signal_tracking", ["kimi_signal_tracking"]),
    ("rapid_fire", ["rapid_fire", "macd_crossover", "stochrsi_", "stochrsi_macd"]),
    ("binance_smart_money", ["binance_smart_money"]),
]

# ──────────────────────────────────────────────────────────────────────
# Historical baseline boosts (from known track records).
# These are fallback values when there aren't enough live picks to
# compute a live boost. Format: (min_boost, max_boost, baseline_wr).
# ──────────────────────────────────────────────────────────────────────
BASELINE_BOOSTS = {
    # 2026-03-23: copy_trader_consensus boost reduced from 45 → 5.
    # consensus_accuracy.json (strong consensus 4-7 traders) shows 34.8% WR, -0.14% avg PnL.
    # Contradicts original 72% assumption. Formula: max(0, (wr - 0.35) * 100) = ~0.
    # Keeping +5 as a minor tip to preserve family classification benefits.
    "copy_trader_consensus": {"boost": 5,  "known_wr": 0.348, "known_pnl": -0.14},
    # 2026-03-24 AUDIT: All boosts verified against closed_picks.json (500 picks).
    # copy_trader_intel: 47 closed, 59.6% WR, +0.01% avg PnL. Boost kept (best source).
    "copy_trader_intel":     {"boost": 25, "known_wr": 0.596, "known_pnl": 0.01},
    # copy_trader_highscore: 1 closed trade only. Reduce boost until more data.
    "copy_trader_highscore": {"boost": 10, "known_wr": 0.50, "known_pnl": 0.03},
    # copy_trader_clones: 0% WR on 11 live picks, 0/1 closed. CRITICAL — was +40!
    "copy_trader_clones":    {"boost": -10, "known_wr": 0.00, "known_pnl": -0.16},
    # kimi_signal_tracking: 0 closed picks. No data to verify. Reduce from +35.
    "kimi_signal_tracking":  {"boost": 10, "known_wr": 0.50, "known_pnl": 0.0},
    "rapid_fire":            {"boost": -30, "known_wr": 0.25, "known_pnl": -429.0},  # 150 trades, 25% WR — biggest alpha destroyer
    # 2026-03-25 refresh: strategy_performance.json now shows 24 closed,
    # 45.8% WR, negative avg PnL, and a negative Sharpe. Penalize instead of
    # boosting so sentiment-only copy volume stops inheriting preferred rank.
    "binance_smart_money":   {"boost": -10, "known_wr": 0.4583, "known_pnl": -0.21},
}


def _classify_family(pick: dict) -> str | None:
    """Classify a pick into a strategy family based on its own source/strategy.

    Do not infer family ownership from agreeing_systems/source_systems. Those
    fields describe cross-system overlap and were causing unrelated battleground,
    coinglass, incubator, and other picks to inherit copy-trader boosts just
    because a copy-trader consensus system also agreed with the symbol.
    """
    strategy = (pick.get("strategy") or "").lower()
    source = (pick.get("source_system") or "").lower()
    combined = strategy + "|" + source

    for family, tags in FAMILY_TAGS:
        for tag in tags:
            if tag in combined:
                return family
    return None


def _float(v) -> float:
    """Safe float conversion."""
    try:
        return float(v or 0)
    except (ValueError, TypeError):
        return 0.0


def _verified_alpha_bonus(pick: dict) -> int:
    """Score bonus for verified PM / auditable pro-trader rows."""
    source = str(pick.get("source_system", "") or "").lower()
    strategy = str(pick.get("strategy", "") or "").lower()
    audited_wr = _float(
        pick.get("history_wr_bayes")
        or pick.get("profile_crypto_wr_bayes")
        or pick.get("history_wr")
        or pick.get("profile_crypto_wr")
        or 0
    )
    audited_trades = int(_float(pick.get("history_trades") or pick.get("forward_trades") or 0))
    audited_edge = audited_wr >= 0.60 and audited_trades >= 5

    if source == "prediction_market_consensus":
        return 22 if audited_edge else 16
    if source == "pm_kalshi_signals":
        return 6
    if source == "pm_whale_signals" and strategy.startswith("copy_pm_"):
        return 18 if audited_edge else 15
    if source == "pm_whale_signals":
        return 10
    if source == "polymarket_signals" and strategy.startswith("copy_pm_"):
        return 18 if audited_edge else 14
    if source == "polymarket_signals":
        return 12 if audited_edge else 8
    if strategy.startswith("copy_pm_"):
        return 14 if audited_edge else 12
    if source == "multi_asset_copytrader" and strategy in {
        "forex_rsi2_mean_reversion",
        "stocks_rsi2_pullback",
        "cftc_cot_commercial_signal",
    }:
        return 10
    return 0


def _verified_alpha_score_floor(pick: dict) -> int:
    """Late-stage display floor so audited PM edge is reflected in the visible score.

    These rows can survive active/smart gates on audited edge even after later
    Binance/ensemble penalties, which made excellent audited PM picks display as
    single-digit garbage. The floor keeps the published score aligned with the
    gating intent without giving them elite scores by default.
    """
    source = str(pick.get("source_system", "") or "").lower()
    strategy = str(pick.get("strategy", "") or "").lower()
    if _verified_alpha_bonus(pick) <= 0:
        return 0

    wr = _float(
        pick.get("history_wr_bayes")
        or pick.get("profile_crypto_wr_bayes")
        or pick.get("history_wr")
        or pick.get("profile_crypto_wr")
        or pick.get("forward_wr")
        or 0
    )
    trades = int(_float(pick.get("history_trades") or pick.get("forward_trades") or 0))
    if wr > 1.5:
        wr /= 100.0

    if trades >= 10 and wr >= 0.80:
        return 60
    if trades >= 5 and wr >= 0.70:
        return 55
    if trades >= 5 and wr >= 0.60:
        return 50
    if source == "prediction_market_consensus" and trades >= 2 and wr >= 0.60:
        return 50
    if source == "multi_asset_copytrader" and strategy in {
        "forex_rsi2_mean_reversion",
        "stocks_rsi2_pullback",
        "cftc_cot_commercial_signal",
    } and trades >= 5 and wr >= 0.55:
        return 50
    return 0


def _apply_verified_alpha_score_floor(active_picks: list[dict]) -> int:
    floored = 0
    for pick in active_picks:
        floor = _verified_alpha_score_floor(pick)
        if floor <= 0:
            continue
        old = _float(pick.get("score", 0))
        if old >= floor:
            continue
        pick["score"] = floor
        pick["_verified_alpha_floor"] = floor
        pick["_verified_alpha_floor_from"] = old
        floored += 1
    return floored


def _normalize_direction(pick: dict) -> str:
    direction = str(pick.get("direction", pick.get("signal_type", ""))).upper()
    if direction == "BUY":
        return "LONG"
    if direction == "SELL":
        return "SHORT"
    return direction


def _apply_symbol_hard_cap(
    active_picks: list[dict],
    max_per_symbol: int = 3,
    max_per_direction: int = 2,
) -> int:
    """Cap symbol crowding with per-direction + total limits.

    Per approved hedge-fund threshold B (docs/HEDGE_FUND_QUALITY_NEXT_STEPS.md):
    max 2 per direction-side, max 2 portfolios holding same symbol-direction.
    Total cap preserves opposite-side picks; per-direction cap prevents
    single-side concentration (e.g. ETH×3 LONG observed in 2026-04-04 audit).
    """
    symbol_groups: dict[str, list[dict]] = defaultdict(list)
    for pick in active_picks:
        sym = (pick.get("symbol") or "").upper().replace("-USD", "USDT")
        if sym:
            symbol_groups[sym].append(pick)

    symbol_capped_count = 0
    for sym, group in symbol_groups.items():
        # Apply per-direction cap first (threshold B enforcement).
        by_direction: dict[str, list[dict]] = defaultdict(list)
        for pick in group:
            by_direction[_normalize_direction(pick)].append(pick)

        kept_ids: set = set()
        for direction, dir_group in by_direction.items():
            dir_group.sort(key=lambda p: _float(p.get("score", 0)), reverse=True)
            for pick in dir_group[:max_per_direction]:
                kept_ids.add(id(pick))

        # Apply total cap (preserves best long + best short + fills by score).
        if len(kept_ids) > max_per_symbol:
            # Too many kept after per-direction cap — re-rank and trim to total cap.
            kept_picks = [p for p in group if id(p) in kept_ids]
            kept_picks.sort(key=lambda p: _float(p.get("score", 0)), reverse=True)
            # Guarantee best-of-each-direction first, then fill by score.
            final_ids: set = set()
            for direction in ("LONG", "SHORT"):
                for pick in kept_picks:
                    if _normalize_direction(pick) == direction:
                        final_ids.add(id(pick))
                        break
            for pick in kept_picks:
                if len(final_ids) >= max_per_symbol:
                    break
                final_ids.add(id(pick))
            kept_ids = final_ids

        for pick in group:
            if id(pick) in kept_ids:
                continue
            pick["symbol_capped"] = True
            pick["score"] = 0
            symbol_capped_count += 1

    return symbol_capped_count


def _compute_live_wr(picks: list[dict], family: str) -> dict:
    """Compute live win rate for a family from active picks with PnL."""
    family_picks = [p for p in picks if _classify_family(p) == family]
    if not family_picks:
        return {"count": 0, "winners": 0, "wr": 0.0, "total_pnl": 0.0, "avg_score": 0.0}

    winners = [p for p in family_picks if _float(p.get("pnl_pct", 0)) > 0]
    total_pnl = sum(_float(p.get("pnl_pct", 0)) for p in family_picks)
    avg_score = sum(_float(p.get("score", 0)) for p in family_picks) / len(family_picks) if family_picks else 0

    return {
        "count": len(family_picks),
        "winners": len(winners),
        "wr": len(winners) / len(family_picks) if family_picks else 0.0,
        "total_pnl": round(total_pnl, 2),
        "avg_score": round(avg_score, 1),
    }


def _compute_closed_wr(closed_picks: list[dict], family: str) -> dict:
    """Compute win rate from closed/resolved picks for a family."""
    family_picks = [p for p in closed_picks if _classify_family(p) == family]
    if not family_picks:
        return {"count": 0, "winners": 0, "wr": 0.0, "total_pnl": 0.0}

    winners = [p for p in family_picks if _float(p.get("pnl_pct", 0)) > 0]
    total_pnl = sum(_float(p.get("pnl_pct", 0)) for p in family_picks)

    return {
        "count": len(family_picks),
        "winners": len(winners),
        "wr": len(winners) / len(family_picks) if family_picks else 0.0,
        "total_pnl": round(total_pnl, 2),
    }


def compute_boost(family: str, live_stats: dict, closed_stats: dict) -> int:
    """
    Compute the score boost for a family based on LIVE + CLOSED performance.

    Logic:
    - If live WR > 55% on 5+ picks: use live data to scale boost
    - Else fall back to baseline (known historical performance)
    - Boost scales with WR: 55% = half boost, 65%+ = full boost
    - Extra boost if total PnL is strongly positive
    """
    baseline = BASELINE_BOOSTS.get(family)
    if not baseline:
        return 0

    base_boost = baseline["boost"]

    # Check live performance first (most reliable current signal)
    if live_stats["count"] >= 5 and live_stats["wr"] > 0.40:
        # Scale boost by actual live WR
        # 40% WR = 50% of baseline, 55% = 75%, 65%+ = 100%
        wr = live_stats["wr"]
        if wr >= 0.65:
            scale = 1.0
        elif wr >= 0.55:
            scale = 0.75
        elif wr >= 0.45:
            scale = 0.60
        else:
            scale = 0.50

        # PnL bonus: if total PnL is very positive, bump scale
        if live_stats["total_pnl"] > 50:
            scale = min(1.0, scale + 0.10)
        elif live_stats["total_pnl"] > 20:
            scale = min(1.0, scale + 0.05)

        boost = int(base_boost * scale)
        log.info("  %s: LIVE boost=%d (wr=%.0f%%, %d picks, pnl=%.1f%%)",
                 family, boost, wr * 100, live_stats["count"], live_stats["total_pnl"])
        return boost

    # Check closed performance (historical track record)
    if closed_stats["count"] >= 10 and closed_stats["wr"] > 0.40:
        wr = closed_stats["wr"]
        if wr >= 0.60:
            scale = 0.90  # Slightly less than live since these are historical
        elif wr >= 0.50:
            scale = 0.70
        else:
            scale = 0.50

        boost = int(base_boost * scale)
        log.info("  %s: CLOSED boost=%d (wr=%.0f%%, %d picks)",
                 family, boost, wr * 100, closed_stats["count"])
        return boost

    # Fall back to baseline — but scale by known WR so low-performing
    # families don't get an outsized boost.  Formula:
    #   scale = min(known_wr / 0.50, 1.5)
    # This means: 50% WR → 1.0x, 65% → 1.3x (capped at 1.5x),
    #             35% → 0.70x, 18% → 0.36x.
    # If known_wr is missing or zero, use conservative 0.5x multiplier.
    known_wr = baseline.get("known_wr", 0)
    if known_wr and known_wr > 0:
        scale = min(known_wr / 0.50, 1.5)
    else:
        scale = 0.5  # conservative default when no WR data

    scaled_boost = max(0, int(base_boost * scale))
    log.info("  %s: BASELINE boost=%d (base=%d, scale=%.2f, known wr=%.0f%%)",
             family, scaled_boost, base_boost, scale, (known_wr or 0) * 100)
    return scaled_boost


def _load_consensus_lessons() -> dict[str, dict]:
    """
    Load consensus lesson data from copytrader_lesson_extractor output.
    Returns dict keyed by "{symbol}_{direction}" → lesson data.
    """
    lessons_path = ROOT / "copy_trader_intel" / "data" / "copytrader_lessons.json"
    if not lessons_path.exists():
        return {}
    try:
        with open(lessons_path) as f:
            data = json.load(f)
        lessons = data.get("lessons", [])
        return {f"{l['symbol']}_{l['direction']}": l for l in lessons}
    except Exception as e:
        log.warning("Could not load consensus lessons: %s", e)
        return {}


def _position_health_adjustment(pick: dict, consensus_lessons: dict) -> int:
    """
    Returns a small score delta from the lesson extractor's evidence bundle.

    The old version only looked at large unrealized dollar PnL. The new lesson
    extractor emits realized trader-history stats plus mutation backtests, so
    we use those first and keep the live PnL signal small.
    """
    key = f"{pick.get('symbol', '')}_{pick.get('direction', '')}"
    lesson = consensus_lessons.get(key)
    if not lesson:
        return 0

    adjustment = int(lesson.get("score_boost_hint", 0) or 0)

    supporting = lesson.get("supporting_closed_history", {}) or {}
    trades = int(supporting.get("trades", 0) or 0)
    win_rate = float(supporting.get("win_rate", 0) or 0)
    avg_pnl = float(supporting.get("avg_pnl", 0) or 0)
    if trades >= 5 and win_rate >= 0.62 and avg_pnl > 0:
        adjustment += 2
    elif trades >= 5 and win_rate < 0.40 and avg_pnl < 0:
        adjustment -= 2

    best_mutation = lesson.get("best_mutation") or {}
    backtest = best_mutation.get("backtest", {}) if isinstance(best_mutation, dict) else {}
    m_trades = int(backtest.get("trades", 0) or 0)
    m_wr = float(backtest.get("win_rate", 0) or 0)
    m_avg_pnl = float(backtest.get("avg_pnl", 0) or 0)
    if m_trades >= 5 and m_wr >= 0.65 and m_avg_pnl > 0:
        adjustment += 2
    elif m_trades >= 5 and m_wr < 0.40 and m_avg_pnl < 0:
        adjustment -= 2

    active_support = lesson.get("active_support", {}) or {}
    active_avg_pnl = float(active_support.get("avg_pnl_pct", 0) or 0)
    if active_avg_pnl >= 1.0:
        adjustment += 1
    elif active_avg_pnl <= -1.0:
        adjustment -= 1

    return max(-6, min(8, adjustment))



def _apply_crypto_hour_filter(pick: dict) -> int:
    """UTC-hour death-zone filter for CRYPTO picks.

    Memory project_clean_data_symbol_wr: 22 UTC = 61.2% WR (n>1000),
    08-09 UTC is a death zone. Kill-switch: CRYPTO_HOUR_FILTER=0.

    BTC-specific symbols delegate to alpha_engine.btc_hour_filter for
    more targeted penalties (wired 2026-05-17, M-070).

    Returns score adjustment (negative = penalty, positive = boost).
    """
    import os as _os_chf
    if _os_chf.environ.get("CRYPTO_HOUR_FILTER", "1") in ("0", "false", "FALSE", "False"):
        return 0
    ac = str(pick.get("asset_class", "") or "").upper()
    if ac != "CRYPTO":
        return 0
    sym = str(pick.get("symbol") or "").upper()
    # Strip exchange prefix (e.g. "BINANCE:BTCUSDT" -> "BTCUSDT")
    if ":" in sym:
        sym = sym.split(":", 1)[1]
    is_btc = sym in ("BTCUSDT", "BTCUSD")

    if is_btc:
        # Delegate BTC symbols to the dedicated module for more targeted penalties.
        try:
            from alpha_engine.btc_hour_filter import btc_hour_score_adjustment
            return btc_hour_score_adjustment(pick)  # -12 death-zone, +5 boost, 0 neutral
        except ImportError:
            import logging as _log_chf
            _log_chf.getLogger(__name__).warning(
                "btc_hour_filter not importable; falling back to inline CRYPTO penalties for BTC"
            )
            # Fall through to inline below

    try:
        from datetime import datetime, timezone
        ts_raw = pick.get("created_at") or pick.get("timestamp") or ""
        if ts_raw:
            dt = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        else:
            dt = datetime.now(timezone.utc)
        hour = dt.hour
        if hour in (8, 9):          # death zone: -20 penalty
            return -20
        elif hour == 22:            # high-WR slot: +8 boost
            return 8
    except Exception:
        pass
    return 0


def _overconf_ab_key(pick: dict) -> str:
    """Stable identity key for the overconfidence-decay A/B bucket.

    Prefers pick['id']; falls back to symbol+timestamp so picks without an
    explicit id are still deterministically (and stably) bucketed instead of
    all collapsing into one arm. Returns '' only if nothing usable exists.
    """
    pid = pick.get("id")
    if pid:
        return str(pid)
    sym = str(pick.get("symbol", "") or "")
    ts = str(pick.get("created_at") or pick.get("timestamp") or "")
    return (sym + "|" + ts).strip("|")


def _overconf_ab_bucket(key: str) -> str:
    """Stable 50/50 hash bucket for the overconfidence-decay A/B test.

    Returns 'A' (control, no decay) or 'B' (treatment, decay applied).
    Deterministic on key: sha1(key) % 2 -> 0=A, 1=B. Empty/missing key
    falls to bucket 'A' (control) so an unidentifiable pick is never
    silently treated.
    """
    import hashlib as _hl_ocd
    if not key:
        return "A"
    h = int(_hl_ocd.sha1(str(key).encode("utf-8")).hexdigest(), 16)
    return "B" if (h % 2 == 1) else "A"


def _apply_overconfidence_decay(pick: dict) -> int:
    """Overconfidence-score decay for extreme aggregate scores (A/B harness).

    P2 from DAILY_IDEAS_LLMARENA_May162026.MD. The non-ergodic cumulative-PnL
    trap (memory: claude_gainer_st cumulative PF 6.80 -> real WR 26.5%) means
    extreme aggregate scores are the least trustworthy. This decays the score
    EXCESS above a high threshold, mimicking Gemini RAKO's `score *= 0.8`
    while staying in the additive-adjustment idiom of this module.

    Distinct axis from `_calibrate_confidence` (keys on `confidence`) and from
    `conviction_stack.compute_conviction_score` (keys on direction x regime) —
    this keys on the aggregate `score` magnitude, so no double-penalty.

    A2 A/B harness (2026-05-17): the decay is hash-bucketed so its effect is
    measurable against a control. Bucket on hash(id or symbol+timestamp) % 2.

    Mode (env OVERCONFIDENCE_DECAY, default '1'):
      '0' / 'false'  -> kill-switch: off everywhere, NO arm stamp, no decay.
      '1' (default)  -> A/B mode: stamp pick['_overconfidence_arm']='A'|'B'
                        on every pick; decay ONLY arm B (treatment). Arm A
                        is the control and receives no decay.

    When the flag is on, pick['_overconfidence_arm'] is always stamped so the
    attribution report (tools/overconfidence_ab_report.py) can compare arms.

    Kill-switch: OVERCONFIDENCE_DECAY=0. Returns a non-positive adjustment.
    """
    import os as _os_ocd
    mode = _os_ocd.environ.get("OVERCONFIDENCE_DECAY", "1")
    # Kill-switch: no stamp, no decay — pick is left entirely untouched.
    if mode in ("0", "false", "FALSE", "False", "off", "OFF"):
        return 0
    # A/B mode (default): stamp the arm on every pick so outcomes stay
    # attributable, then decay ONLY bucket B (treatment). Bucket A is control.
    arm = _overconf_ab_bucket(_overconf_ab_key(pick))
    pick["_overconfidence_arm"] = arm
    if arm != "B":
        return 0
    try:
        score = _float(pick.get("score", 0))
        # Decay only the excess above the high-conviction threshold.
        HIGH = 80.0
        if score <= HIGH:
            return 0
        # 0.2 * excess  ==  (1 - 0.8) * excess  -> same as RAKO score*0.8 on excess.
        adj = -int(round((score - HIGH) * 0.2))
        # Cap so a single adjustment cannot dominate the pipeline.
        return max(adj, -10)
    except Exception:
        return 0


def _calibrate_confidence(conf: float, asset_class: str) -> float:
    """Per-asset-class confidence recalibration.

    Addresses systematic confidence inversion discovered in the audit:
      CRYPTO: conf>=0.9 -> 14.4%% WR, conf 0.5-0.6 -> 60.3%% WR
      EQUITY: 0.85-0.90 -> 20%% WR (WORST), >0.90 -> 67%% WR
      FOREX: peak 0.75-0.80 (49%% WR), 0.70-0.75 = DANGER (25%% WR)
      COMMODITY: peak 0.70-0.75 (48%% WR)

    Returns score adjustment (can be negative to penalize overconfidence).
    """
    if conf <= 0 or conf > 1.0:
        return 0.0

    if asset_class == "CRYPTO":
        # Penalize high confidence strongly; reward moderate
        if conf > 0.85:
            return -12
        elif conf > 0.80:
            return -6
        elif conf >= 0.60:
            return 0
        elif conf >= 0.50:
            return 3
        else:
            return 2

    elif asset_class == "EQUITY":
        # Bipolar: 0.85-0.90 is worst, >0.90 recovers
        if 0.85 <= conf <= 0.90:
            return -15
        elif conf > 0.90:
            return 5
        elif conf >= 0.70:
            return 0
        elif conf >= 0.55:
            return 3
        else:
            return 1

    elif asset_class == "FOREX":
        # Low ceiling; trust moderate confidence only
        if conf >= 0.85:
            return -10
        elif conf >= 0.75:
            return 0
        elif conf >= 0.65:
            return 3
        elif conf >= 0.55:
            return 5  # Sweet spot shift lower for forex
        else:
            return 0

    elif asset_class == "COMMODITY":
        if conf >= 0.85:
            return -8
        elif conf >= 0.70:
            return 0
        elif conf >= 0.55:
            return 3
        else:
            return 1

    return 0


def run_score_booster(payload_path: Path | None = None) -> dict:
    """
    Main entry point. Loads dashboard payload, applies score boosts,
    saves the updated payload.

    Returns a summary dict with boost statistics.
    """
    if payload_path is None:
        payload_path = PAYLOAD_PATH

    if not payload_path.exists():
        log.error("Dashboard payload not found: %s", payload_path)
        return {"error": "payload_not_found"}

    log.info("=== Score Booster v1.0 ===")
    log.info("Loading payload: %s", payload_path)

    with open(payload_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    active_picks = payload.get("picks", {}).get("active", [])
    closed_picks = payload.get("picks", {}).get("recent_closed", [])

    # Load lesson data for consensus evidence adjustments
    consensus_lessons = _load_consensus_lessons()
    log.info("Loaded %d consensus lessons for evidence-aware adjustments", len(consensus_lessons))

    log.info("Active picks: %d, Closed picks: %d", len(active_picks), len(closed_picks))

    # ── Compute per-family stats ──
    family_stats = {}
    for family, _ in FAMILY_TAGS:
        live = _compute_live_wr(active_picks, family)
        closed = _compute_closed_wr(closed_picks, family)
        boost = compute_boost(family, live, closed)
        family_stats[family] = {
            "live": live,
            "closed": closed,
            "boost": boost,
        }

    # ── Apply boosts to active picks ──
    boosted_count = 0
    total_boost_pts = 0
    boost_details = []

    for pick in active_picks:
        family = _classify_family(pick)
        if not family:
            continue

        stats = family_stats.get(family)
        if not stats or stats["boost"] <= 0:
            continue

        old_score = _float(pick.get("score", 0))
        boost_amount = stats["boost"]

        # Small lesson-based adjustment from realized copytrader evidence
        health_adj = _position_health_adjustment(pick, consensus_lessons)
        boost_amount += health_adj

        # Don't boost picks that already have high scores
        if old_score >= 70:
            continue

        new_score = min(95, old_score + boost_amount)

        # Only boost if it actually changes the score
        if new_score <= old_score:
            continue

        pick["score"] = int(new_score)
        pick["_score_boosted"] = True
        pick["_boost_family"] = family
        pick["_boost_amount"] = int(new_score - old_score)
        pick["_original_score"] = int(old_score)

        # Update elite_grade based on new score
        if new_score >= 85:
            pick["elite_grade"] = "A"
        elif new_score >= 70:
            pick["elite_grade"] = "B"
        elif new_score >= 55:
            pick["elite_grade"] = "C"
        elif new_score >= 40:
            pick["elite_grade"] = "D"
        else:
            pick["elite_grade"] = "F"

        boosted_count += 1
        total_boost_pts += int(new_score - old_score)

        boost_details.append({
            "symbol": pick.get("symbol", "???"),
            "family": family,
            "old_score": int(old_score),
            "new_score": int(new_score),
            "pnl_pct": round(_float(pick.get("pnl_pct", 0)), 2),
        })

    # ── Proven Winner boost (2026-03-24 correlation fix) ──
    # Strategies with >55% WR on 20+ closed trades get +10 score.
    # This is the most reliable predictive signal per IC analysis (IC=+0.17).
    # Applied to ALL picks regardless of family classification.
    proven_winner_boosted = 0
    try:
        strat_perf_path = ROOT / "alpha_engine" / "data" / "strategy_performance.json"
        strat_perf_data = {}
        if strat_perf_path.exists():
            with open(strat_perf_path, "r", encoding="utf-8") as f:
                strat_perf_data = json.load(f)

        for pick in active_picks:
            strat_name = pick.get("strategy", "")
            if not strat_name or strat_name not in strat_perf_data:
                continue
            sp = strat_perf_data[strat_name]
            sp_closed = sp.get("closed_picks", 0)
            sp_wr = sp.get("win_rate", 0)
            if sp_closed >= 20 and sp_wr > 0.55:
                old_score = _float(pick.get("score", 0))
                bonus = 10
                new_score = min(95, old_score + bonus)
                if new_score > old_score:
                    pick["score"] = int(new_score)
                    pick["_proven_winner_boost"] = bonus
                    pick["_proven_winner_wr"] = round(sp_wr * 100, 1)
                    pick["_proven_winner_trades"] = sp_closed
                    proven_winner_boosted += 1
    except Exception as e:
        log.warning("Proven winner boost failed: %s", e)
    if proven_winner_boosted:
        log.info("Proven winner boost: %d picks boosted (+10 score, >55%% WR on 20+ trades)",
                 proven_winner_boosted)

    # ── Opposing-pick penalty: penalize when same symbol has LONG and SHORT ──
    # XRP at score 100 LONG + score 100 SHORT = contradiction = neither is trustworthy
    symbol_dirs = defaultdict(list)
    for pick in active_picks:
        sym = pick.get("symbol", "").upper().replace("-USD", "USDT")
        d = str(pick.get("direction", pick.get("signal_type", ""))).upper()
        if d in ("LONG", "BUY"):
            symbol_dirs[sym].append(("LONG", pick))
        elif d in ("SHORT", "SELL"):
            symbol_dirs[sym].append(("SHORT", pick))

    opposing_penalized = 0
    opposing_killed = 0
    for sym, entries in symbol_dirs.items():
        dirs = set(d for d, _ in entries)
        if len(dirs) > 1:  # Both LONG and SHORT exist
            # Find best score per direction, KILL the weaker direction entirely
            longs = [(d, p) for d, p in entries if d == "LONG"]
            shorts = [(d, p) for d, p in entries if d == "SHORT"]
            best_long = max((_float(p.get("score", 0)) for _, p in longs), default=0)
            best_short = max((_float(p.get("score", 0)) for _, p in shorts), default=0)
            # Kill the weaker direction (score=0), penalize the winner (-10%)
            kill_dir = "SHORT" if best_long >= best_short else "LONG"
            for d, pick in entries:
                if d == kill_dir:
                    pick["score"] = 0  # Kill weaker direction
                    pick["_opposing_killed"] = True
                    opposing_killed += 1
                else:
                    old = _float(pick.get("score", 0))
                    pick["score"] = max(0, int(old * 0.90))  # -10% for contested
                    pick["_opposing_penalty"] = True
                    opposing_penalized += 1
    if opposing_penalized:
        log.info("Opposing-pick penalty: %d picks penalized (-20%%) across %d contested symbols",
                 opposing_penalized, sum(1 for d in symbol_dirs.values() if len(set(x[0] for x in d)) > 1))

    # ── Age-decay penalty: stale picks lose score over time ──
    # Fresh picks (< 4h) = no penalty. 4-12h = -5. 12-24h = -10. 24-48h = -15. >48h = -20.
    # This prevents stale high-score picks from misleading traders after regime changes.
    age_decayed = 0
    for pick in active_picks:
        age = _float(pick.get("age_hours"))
        if age is None or age <= 0:
            continue
        if age <= 4:
            decay = 0
        elif age <= 12:
            decay = 5
        elif age <= 24:
            decay = 10
        elif age <= 48:
            decay = 15
        else:
            decay = 20
        if decay > 0:
            old = _float(pick.get("score", 0))
            pick["score"] = max(0, int(old - decay))
            pick["_age_decay"] = decay
            age_decayed += 1
    if age_decayed:
        log.info("Age-decay penalty: %d picks penalized (stale signals)", age_decayed)

    # ── CRYPTO UTC-hour filter (2026-05-15) ──
    # 22 UTC = 61.2% WR (n>1000 proven), 08-09 UTC = death zone.
    # Kill-switch: CRYPTO_HOUR_FILTER=0
    hour_filter_adjusted = 0
    for pick in active_picks:
        adj = _apply_crypto_hour_filter(pick)
        if adj != 0:
            old = _float(pick.get("score", 0))
            pick["score"] = max(0, int(old + adj))
            pick["_hour_filter_adj"] = adj
            hour_filter_adjusted += 1
    if hour_filter_adjusted:
        log.info("CRYPTO hour filter: %d picks adjusted (death-zone penalty or 22-UTC boost)",
                 hour_filter_adjusted)

    # ── COMMODITY DXY inverse booster (2026-05-17, M-074) ──
    # When USD is weakening (DXY below 20-day SMA and 5d change <-0.5%),
    # COMMODITY LONG picks get +6 score boost (Gorton/Rouwenhorst 2006).
    # When USD is strengthening, LONG picks get -3 and SHORT picks get +4.
    # State file: alpha_engine/data/dxy_state.json (updated daily by dxy_state_updater.py).
    # Kill-switch: DXY_BOOSTER_DISABLED=1
    dxy_adjusted = 0
    try:
        from alpha_engine.dxy_booster import dxy_score_adjustment
        for pick in active_picks:
            adj = dxy_score_adjustment(pick)
            if adj != 0:
                old = _float(pick.get("score", 0))
                pick["score"] = max(0, int(old + adj))
                pick.setdefault("_penalties", [])
                pick["_penalties"].append(f"dxy_inverse({adj:+d})")
                dxy_adjusted += 1
    except ImportError:
        log.warning("dxy_booster not importable — skipping COMMODITY DXY adjustment")
    if dxy_adjusted:
        log.info("COMMODITY DXY booster: %d picks adjusted", dxy_adjusted)

    # ── Overconfidence-score decay (P2, 2026-05-16; A/B harness A2, 2026-05-17) ──
    # Decays the score excess above 80 (non-ergodic cumulative-PnL trap).
    # Modes: OVERCONFIDENCE_DECAY=1 (A/B split, default) / 0 (kill-switch off).
    # When on, every pick gets pick['_overconfidence_arm']='A'|'B' stamped for
    # attribution; only arm B (treatment) is actually decayed, arm A is control.
    # Distinct axis from _calibrate_confidence / conviction_stack.
    overconf_decayed = 0
    for pick in active_picks:
        adj = _apply_overconfidence_decay(pick)
        if adj != 0:
            old = _float(pick.get("score", 0))
            pick["score"] = max(0, int(old + adj))
            pick["_overconfidence_decay"] = adj
            overconf_decayed += 1
    if overconf_decayed:
        log.info("Overconfidence decay: %d high-score picks decayed", overconf_decayed)

    # ── HF-grade scoring fixes (2026-04-21): PnL outlier cap, symbol WR gate,
    # non-crypto catastrophe penalty, per-system per-asset-class WR gate.
    pnl_capped_count = 0
    for pick in active_picks + closed_picks:
        pnl = _float(pick.get("pnl_pct", 0))
        if pnl > 100.0:
            pick["pnl_pct"] = 100.0
            pick["_pnl_capped"] = True
            pick["_pnl_original"] = pnl
            pnl_capped_count += 1
        elif pnl < -100.0:
            pick["pnl_pct"] = -100.0
            pick["_pnl_capped"] = True
            pick["_pnl_original"] = pnl
            pnl_capped_count += 1
    if pnl_capped_count:
        log.info("PnL outlier cap: %d picks clamped to [-100%%, +100%%]",
                 pnl_capped_count)

    symbol_wr_capped = 0
    symbol_wr_data: dict[str, dict] = defaultdict(lambda: {"wins": 0, "total": 0})
    try:
        for cp in closed_picks:
            sym = (cp.get("symbol") or "").upper()
            pnl = _float(cp.get("pnl_pct", 0))
            if not sym:
                continue
            symbol_wr_data[sym]["total"] += 1
            if pnl > 0:
                symbol_wr_data[sym]["wins"] += 1

        for pick in active_picks:
            sym = (pick.get("symbol") or "").upper()
            if sym not in symbol_wr_data:
                continue
            sdata = symbol_wr_data[sym]
            if sdata["total"] < 10:
                continue
            sym_wr = sdata["wins"] / sdata["total"]
            if sym_wr < 0.35:
                old = _float(pick.get("score", 0))
                if old > 50:
                    pick["score"] = 50
                    pick["_symbol_wr_capped"] = True
                    pick["_symbol_wr"] = round(sym_wr * 100, 1)
                    pick["_symbol_trades"] = sdata["total"]
                    symbol_wr_capped += 1
    except Exception as e:
        log.warning("Symbol WR gate error: %s", e)
    if symbol_wr_capped:
        log.info("Symbol WR gate: %d picks capped to 50 (symbol WR <35%% on 10+ trades)",
                 symbol_wr_capped)

    noncrypto_penalized = 0
    for pick in active_picks:
        asset_class = str(pick.get("asset_class", "")).upper()
        if asset_class not in ("FOREX", "COMMODITY"):
            continue
        sym = (pick.get("symbol") or "").upper()
        if sym in symbol_wr_data and symbol_wr_data[sym]["total"] >= 5:
            sym_wr = symbol_wr_data[sym]["wins"] / symbol_wr_data[sym]["total"]
            if sym_wr < 0.30:
                old = _float(pick.get("score", 0))
                pick["score"] = max(0, int(old - 15))
                pick["_noncrypto_catastrophe"] = True
                pick["_noncrypto_sym_wr"] = round(sym_wr * 100, 1)
                noncrypto_penalized += 1
    if noncrypto_penalized:
        log.info("Non-crypto catastrophe: %d picks penalized (-15, WR <30%% on 5+ trades)",
                 noncrypto_penalized)

    sys_ac_wr: dict[str, dict] = defaultdict(lambda: {"wins": 0, "total": 0})
    sys_ac_capped = 0
    try:
        for cp in closed_picks:
            src = str(cp.get("source_system", "") or "").lower()
            ac = str(cp.get("asset_class", "") or "").upper()
            pnl = _float(cp.get("pnl_pct", 0))
            if not src or not ac:
                continue
            key = f"{src}|{ac}"
            sys_ac_wr[key]["total"] += 1
            if pnl > 0:
                sys_ac_wr[key]["wins"] += 1

        for pick in active_picks:
            src = str(pick.get("source_system", "") or "").lower()
            ac = str(pick.get("asset_class", "") or "").upper()
            key = f"{src}|{ac}"
            if key not in sys_ac_wr:
                continue
            sdata = sys_ac_wr[key]
            if sdata["total"] < 15:
                continue
            wr = sdata["wins"] / sdata["total"]
            if wr < 0.35:
                old = _float(pick.get("score", 0))
                cap = max(10, int(wr * 100))
                if old > cap:
                    pick["score"] = cap
                    pick["_sys_ac_wr_capped"] = True
                    pick["_sys_ac_wr"] = round(wr * 100, 1)
                    pick["_sys_ac_key"] = key
                    sys_ac_capped += 1
    except Exception as e:
        log.warning("Per-system-per-asset WR gate error: %s", e)
    if sys_ac_capped:
        log.info("System-asset WR gate: %d picks capped (system WR <35%% on this asset class)",
                 sys_ac_capped)

    # ── Low WR System penalty: -10 for picks from systems with poor forward WR ──
    # Matches the "Low WR System" warning badge shown in the audit dashboard template.
    # Triggers on: forward_status starting with "low_wr", or source_system in WEAK_SYSTEMS.
    # 2026-03-24: Added baby_strats_forward (39.8% WR, 150 Q5 losers) and
    # claude_gainer_st (28.3% WR, 104 Q5 losers). These systems get high scores
    # but lose consistently, dragging Q5 performance below Q4.
    low_wr_penalized = 0
    for pick in active_picks:
        fwd_status = str(pick.get("forward_status", "")).lower()
        src_sys = str(pick.get("source_system", "")).lower()
        is_low_wr = fwd_status.startswith("low_wr") or src_sys in WEAK_SYSTEMS_SET
        if is_low_wr:
            old = _float(pick.get("score", 0))
            pick["score"] = max(0, int(old - 10))
            pick["_low_wr_penalty"] = True
            low_wr_penalized += 1
    if low_wr_penalized:
        log.info("Low WR System penalty: %d picks penalized (-10 score)", low_wr_penalized)

    # ── Verified-alpha bonus: prediction markets + auditable pro-trader rows ──
    # The product goal is not generic signal breadth. It is to surface the
    # PM / verified-copy cohort ahead of legacy broad-market feeds when the
    # symbol contest is close.
    verified_alpha_boosted = 0
    for pick in active_picks:
        bonus = _verified_alpha_bonus(pick)
        if bonus <= 0:
            continue
        old = _float(pick.get("score", 0))
        pick["score"] = min(100, int(old + bonus))
        pick["_verified_alpha_bonus"] = bonus
        verified_alpha_boosted += 1
    if verified_alpha_boosted:
        log.info("Verified-alpha bonus: %d picks boosted (+10 to +16)", verified_alpha_boosted)

    # ── Per-symbol deduplication: keep only best pick per symbol+direction ──
    # Prevents concentration risk (e.g. XRPUSDT x3, SUIUSDT x3 → Gini 0.51).
    # For each symbol+direction combo, the highest-scored pick is kept as-is.
    # Lower-scored duplicates get flagged and penalized -20 score.
    _sym_dir_best: dict[tuple, list] = defaultdict(list)
    for pick in active_picks:
        sym = (pick.get("symbol") or "").upper().replace("-USD", "USDT")
        d = str(pick.get("direction", pick.get("signal_type", ""))).upper()
        if d in ("BUY",):
            d = "LONG"
        elif d in ("SELL",):
            d = "SHORT"
        _sym_dir_best[(sym, d)].append(pick)

    dedup_penalized = 0
    for (sym, d), group in _sym_dir_best.items():
        if len(group) <= 1:
            continue
        # Sort by score descending — best pick first
        group.sort(key=lambda p: _float(p.get("score", 0)), reverse=True)
        for i, pick in enumerate(group):
            if i == 0:
                continue  # Keep the best pick untouched
            old = _float(pick.get("score", 0))
            pick["score"] = max(0, int(old - 20))
            pick["deduplicated"] = True
            pick["_dedup_kept_symbol"] = sym
            pick["_dedup_rank"] = i + 1  # 2nd, 3rd, etc.
            dedup_penalized += 1
    if dedup_penalized:
        log.info("Symbol dedup penalty: %d duplicate picks penalized (-20 score) across %d contested symbol+direction combos",
                 dedup_penalized, sum(1 for g in _sym_dir_best.values() if len(g) > 1))

    # ── Mercury 2: ATR-scaled TP/SL flagging ──
    # Loads optimal_tp_sl.json and flags picks with suboptimal TP/SL or low R:R
    optimal_tp_sl_path = ROOT / "alpha_engine" / "data" / "optimal_tp_sl.json"
    tp_sl_flagged = 0
    rr_penalized = 0
    if optimal_tp_sl_path.exists():
        try:
            with open(optimal_tp_sl_path, "r", encoding="utf-8") as f:
                tp_sl_data = json.load(f)
            by_asset = tp_sl_data.get("by_asset_class", {})
            by_dir = tp_sl_data.get("by_direction", {})

            for pick in active_picks:
                asset_class = str(pick.get("asset_class", "CRYPTO")).upper()
                direction = str(pick.get("direction", pick.get("signal_type", ""))).upper()
                if direction in ("BUY",):
                    direction = "LONG"
                elif direction in ("SELL",):
                    direction = "SHORT"

                # Look up optimal SL for this asset class (primary) and direction (secondary)
                optimal_info = None
                if asset_class in by_asset:
                    optimal_info = by_asset[asset_class].get("optimal")
                if not optimal_info and direction in by_dir:
                    optimal_info = by_dir[direction].get("optimal")
                if not optimal_info:
                    continue

                optimal_sl = _float(optimal_info.get("sl_recommended_pct", 0))
                pick_sl = _float(pick.get("stop_loss_pct", pick.get("sl_pct", 0)))
                pick_tp = _float(pick.get("take_profit_pct", pick.get("tp_pct", 0)))

                # Flag if SL is too tight (< 80% of optimal)
                if optimal_sl > 0 and pick_sl > 0 and pick_sl < optimal_sl * 0.8:
                    pick["tp_sl_suboptimal"] = True
                    tp_sl_flagged += 1

                # Penalize if R:R < 1.5
                if pick_sl > 0 and pick_tp > 0:
                    rr = pick_tp / pick_sl
                    if rr < 1.5:
                        old = _float(pick.get("score", 0))
                        pick["score"] = max(0, int(old - 5))
                        pick["_rr_penalty"] = True
                        rr_penalized += 1
        except Exception as e:
            log.warning("Could not load optimal_tp_sl.json: %s", e)
    if tp_sl_flagged or rr_penalized:
        log.info("TP/SL check: %d picks flagged suboptimal SL, %d picks penalized for R:R < 1.5",
                 tp_sl_flagged, rr_penalized)

    # ── Mercury 2: Symbol hard cap — max 3 total, max 2 per direction (threshold B) ──
    # Preserve the best long and best short first so one crowded side does not
    # erase the only valid opposite-direction pick on the symbol.
    # Per-direction cap (2) enforces approved HF threshold B; total cap (3) allows
    # one extra pick on the dominant side when consensus agrees.
    symbol_capped_count = _apply_symbol_hard_cap(
        active_picks, max_per_symbol=3, max_per_direction=2
    )
    if symbol_capped_count:
        log.info(
            "Symbol hard cap: %d excess picks zeroed (max 3/symbol, max 2/direction)",
            symbol_capped_count,
        )

    # ── Mercury 2: Liquidity-aware penalty ──
    # Penalizes picks on low-volume symbols to prevent high scores on illiquid micro-caps.
    # Top 50 symbols by Binance 24h volume (static list, updated periodically)
    TOP50_SYMBOLS = {
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
        "ADAUSDT", "AVAXUSDT", "DOTUSDT", "TRXUSDT", "LINKUSDT", "MATICUSDT",
        "SHIBUSDT", "LTCUSDT", "BCHUSDT", "NEARUSDT", "UNIUSDT", "APTUSDT",
        "ICPUSDT", "FILUSDT", "ETCUSDT", "ATOMUSDT", "STXUSDT", "IMXUSDT",
        "HBARUSDT", "MANAUSDT", "SANDUSDT", "AAVEUSDT", "GRTUSDT", "ALGOUSDT",
        "FTMUSDT", "THETAUSDT", "AXSUSDT", "EGLDUSDT", "FLOWUSDT", "CHZUSDT",
        "EOSUSDT", "MKRUSDT", "SNXUSDT", "CRVUSDT", "LDOUSDT", "RNDRUSDT",
        "INJUSDT", "SUIUSDT", "SEIUSDT", "TIAUSDT", "JUPUSDT", "WIFUSDT",
        "PENDLEUSDT", "ONDOUSDT",
    }
    liquidity_penalized = 0
    for pick in active_picks:
        sym = (pick.get("symbol") or "").upper().replace("-USD", "USDT")
        vol_ratio = _float(pick.get("volume_ratio", pick.get("volume_24h_ratio", 0)))
        penalty = 0

        # Low volume ratio penalty
        if vol_ratio > 0 and vol_ratio < 0.5:
            penalty += 5

        # Not in top 50 penalty (only for crypto)
        asset_class = str(pick.get("asset_class", "")).upper()
        if asset_class in ("CRYPTO", "") and sym and sym not in TOP50_SYMBOLS:
            # Only apply if we can confirm it's crypto or unknown
            if asset_class == "CRYPTO" or sym.endswith("USDT"):
                penalty += 3

        if penalty > 0:
            old = _float(pick.get("score", 0))
            pick["score"] = max(0, int(old - penalty))
            pick["_liquidity_penalty"] = penalty
            liquidity_penalized += 1
    if liquidity_penalized:
        log.info("Liquidity penalty: %d picks penalized (low volume / not top-50)",
                 liquidity_penalized)

    # M-001 UTC-hour filter applied earlier via _apply_crypto_hour_filter() at line ~829

    # ── MTF gate: multi-timeframe confirmation scoring (crypto only) ──
    mtf_boosted = 0
    mtf_penalized = 0
    if _HAS_MTF_GATE and not _BINANCE_DISABLED:
        for pick in active_picks:
            if _BINANCE_DISABLED:
                break  # Circuit breaker tripped mid-loop
            asset_class = str(pick.get("asset_class", "")).upper()
            if asset_class and asset_class != "CRYPTO":
                continue  # Only apply to crypto picks
            # Infer crypto if asset_class is empty and symbol ends with USDT
            sym = (pick.get("symbol") or "").upper()
            if not asset_class and not sym.endswith("USDT"):
                continue
            direction = str(pick.get("direction", pick.get("signal_type", ""))).upper()
            if direction in ("BUY", "LONG"):
                mtf_dir = "BULL"
            elif direction in ("SELL", "SHORT"):
                mtf_dir = "BEAR"
            else:
                continue
            mtf_result = _binance_gate_call(_check_mtf, sym, mtf_dir)
            if mtf_result is not None:
                adj = int(mtf_result.get("score_adjustment", 0))
                if _verified_alpha_bonus(pick) > 0 and adj < 0:
                    adj = max(adj, -5)
                old = _float(pick.get("score", 0))
                pick["score"] = max(0, int(old + adj))
                pick["mtf_aligned"] = bool(mtf_result.get("aligned", True))
                pick["mtf_agreement_ratio"] = mtf_result.get("agreement", "N/A")
                if adj > 0:
                    mtf_boosted += 1
                elif adj < 0:
                    mtf_penalized += 1
            else:
                pick["mtf_aligned"] = True  # Don't block on errors / circuit open
                pick["mtf_agreement_ratio"] = "SKIPPED" if _BINANCE_DISABLED else "ERROR"
        log.info("MTF gate: %d picks boosted, %d picks penalized (crypto only)%s",
                 mtf_boosted, mtf_penalized,
                 " [circuit breaker tripped]" if _BINANCE_DISABLED else "")
    else:
        reason = "Binance circuit breaker open" if _BINANCE_DISABLED else "mtf_gate module not available"
        log.info("MTF gate: skipped (%s)", reason)

    # ── Ensemble gate: 2-of-3 independent signal confirmation (crypto only) ──
    ens_boosted = 0
    ens_penalized = 0
    try:
        from alpha_engine.ensemble_gate import check_ensemble as _check_ensemble
        _HAS_ENSEMBLE_GATE = True
    except ImportError:
        try:
            from ensemble_gate import check_ensemble as _check_ensemble
            _HAS_ENSEMBLE_GATE = True
        except ImportError:
            _HAS_ENSEMBLE_GATE = False

    # Skip ensemble gate in CI or when Binance circuit breaker is open —
    # it makes 100+ Binance futures API calls per symbol that always fail
    # from GitHub Actions (geo-blocked), wasting 3+ minutes.
    if _HAS_ENSEMBLE_GATE and not _IN_CI and not _BINANCE_DISABLED:
        for pick in active_picks:
            if _BINANCE_DISABLED:
                break  # Circuit breaker tripped mid-loop
            asset_class = str(pick.get("asset_class", "")).upper()
            if asset_class and asset_class != "CRYPTO":
                continue  # Only apply to crypto picks
            sym = (pick.get("symbol") or "").upper()
            if not asset_class and not sym.endswith("USDT"):
                continue
            direction = str(pick.get("direction", pick.get("signal_type", ""))).upper()
            if direction in ("BUY", "LONG"):
                ens_dir = "LONG"
            elif direction in ("SELL", "SHORT"):
                ens_dir = "SHORT"
            else:
                continue
            ens_result = _binance_gate_call(_check_ensemble, sym, ens_dir)
            if ens_result is not None:
                aligned = ens_result.get("signals_aligned", 0)
                is_verified_alpha = _verified_alpha_bonus(pick) > 0
                old = _float(pick.get("score", 0))
                if aligned >= 3:
                    pick["score"] = int(old + 5)
                    ens_boosted += 1
                elif aligned == 1:
                    pick["score"] = max(0, int(old - (5 if is_verified_alpha else 10)))
                    ens_penalized += 1
                elif aligned == 0:
                    pick["score"] = max(0, int(old - (8 if is_verified_alpha else 20)))
                    ens_penalized += 1
                pick["ensemble_aligned"] = aligned
            else:
                pick["ensemble_aligned"] = -1  # Circuit breaker / error marker
        log.info("Ensemble gate: %d picks boosted (+5), %d picks penalized (crypto only)%s",
                 ens_boosted, ens_penalized,
                 " [circuit breaker tripped]" if _BINANCE_DISABLED else "")
    else:
        if _IN_CI:
            reason = "running in CI (Binance geo-blocked)"
        elif _BINANCE_DISABLED:
            reason = "Binance circuit breaker open"
        else:
            reason = "ensemble_gate module not available"
        log.info("Ensemble gate: skipped (%s)", reason)

    # ── SHORT direction edge bonus (2026-04-22) ──
    # Deep asset-class edge analysis found SHORT picks have 38.7% WR with
    # positive avg PnL vs 28.7% WR for BUYs (crypto, all-time n=9124).
    # The edge is strongest for high-score SHORTs (score>=70: 42% WR, +PnL).
    # Give a modest +3 bonus to SHORT direction picks that have score >= 40
    # to reflect this structural edge without over-tilting the book.
    short_edge_boosted = 0
    for pick in active_picks:
        direction = _normalize_direction(pick)
        if direction != "SHORT":
            continue
        old_score = _float(pick.get("score", 0))
        if old_score < 40:
            continue  # Only boost SHORTs with decent base scores
        bonus = 3
        new_score = min(100, int(old_score + bonus))
        if new_score > old_score:
            pick["score"] = new_score
            pick["_short_edge_bonus"] = bonus
            short_edge_boosted += 1
    if short_edge_boosted:
        log.info("SHORT direction edge bonus: %d picks boosted (+3 score, proven 38.7%% WR edge)",
                 short_edge_boosted)

    # ── P1: Persona_WR → confidence proxy (2026-05-24) ──
    # Picks with confidence ≤ 0.01 get persona_WR as confidence fallback.
    # Clamped 0.25-0.75, same as tools/ai_tournament/ingest_to_db.py enrichment.
    # Verifies: SELECT confidence FROM tournament_picks LIMIT 10 → non-zero.
    persona_wr_proxied = 0
    for pick in active_picks:
        raw_conf = _float(pick.get("confidence", 0))
        if raw_conf > 0.01:
            continue
        pw = _float(pick.get("persona_win_rate", 0))
        if pw > 0:
            pick["confidence"] = max(0.25, min(0.75, pw))
            pick["_persona_wr_proxy"] = True
            persona_wr_proxied += 1
    if persona_wr_proxied:
        log.info("Persona_WR confidence proxy: %d picks enriched (confidence was ≤0.01)", persona_wr_proxied)

    # ── Confidence recalibration per asset class (2026-05-14) ──
    # Per-system analysis shows confidence is INVERTED for some classes:
    #   CRYPTO: conf>=0.9 -> 14.4%% WR, conf 0.5-0.6 -> 60.3%% WR
    #   EQUITY: 0.85-0.90 -> 20%% WR (WORST band), >0.90 -> 67%% WR
    #   FOREX: peak 0.75-0.80 (49%% WR), 0.70-0.75 = DANGER (25%% WR)
    #   COMMODITY: peak 0.70-0.75 (48%% WR)
    recalibrated_count = 0
    for pick in active_picks:
        raw_conf = _float(pick.get("confidence", 0))
        asset_class = str(pick.get("asset_class", "CRYPTO")).upper()
        old_score = _float(pick.get("score", 0))
        cal = _calibrate_confidence(raw_conf, asset_class)
        if abs(cal) > 0.01:
            pick["_conf_calibration"] = round(cal, 3)
            new_score = max(0, min(100, int(old_score + cal)))
            if new_score != int(old_score):
                pick["score"] = new_score
                recalibrated_count += 1
    if recalibrated_count:
        log.info("Confidence recalibration: %d picks adjusted (per-class inversion fix)",
                 recalibrated_count)

    # ── Late verified-alpha floor ──
    # Apply after all major penalties so audited PM / pro-trader rows that still
    # pass the quality gates don't publish as deceptive single-digit scores.
    verified_alpha_floored = _apply_verified_alpha_score_floor(active_picks)
    if verified_alpha_floored:
        log.info("Verified-alpha score floor: %d picks lifted to the audited floor", verified_alpha_floored)

    # ── System-level score caps (prevent weak systems from reaching Q5) ──
    # IC analysis + Q5 investigation (2026-03-24): baby_strats_forward (39.8% WR)
    # and claude_gainer_st (28.3% WR) get inflated scores. Cap them to prevent
    # high-scoring losers from dragging Q5 below Q4.
    SYSTEM_SCORE_CAPS = {
        "baby_strats_forward": 52,   # 39.8% WR — keep in Q3-Q4
        "claude_gainer_st": 25,      # 23.8% WR, -463% PnL — LOWERED from 45 (HF-grade 2026-04-21)
        "rapid_fire": 10,            # 25% WR, -429% PnL — force to bottom quintile
        "aggregated_picks": 50,      # 14.3% WR per gap analysis
        # Catastrophic / weak systems (audit 2026-04-20 + HF-grade 2026-04-21)
        "mercury2_fast": 5,
        "myfxbook_retail_contrarian": 5,
        "multi_asset_copytrader": 40,
        "copy_trader_intel": 35,
        "mercury2": 20,
        "forex_copy_trader": 15,
        "goldmine_stocks": 10,
    }
    sys_capped = 0
    for pick in active_picks:
        src = str(pick.get("source_system", "") or "").lower()
        for sys_name, cap_val in SYSTEM_SCORE_CAPS.items():
            if sys_name in src:
                s = _float(pick.get("score", 0))
                if s > cap_val:
                    pick["score"] = cap_val
                    pick["_system_score_capped"] = True
                    pick["_system_cap_from"] = s
                    sys_capped += 1
                break
    if sys_capped:
        log.info("System score cap: %d picks capped to prevent Q5 inversion", sys_capped)

    # ── COMMODITY CT=F concentration guard (2026-05-15) ──
    # CT=F (Cotton) is ~73% of COMMODITY PnL — single-contract risk.
    # Penalty: -8 to elite_score (mapped to score field here) when symbol is
    # CT=F, to reduce its relative volume vs other commodities and diversify
    # class PnL share. Does NOT block — just de-prioritizes.
    # Lift this penalty when CT=F concentration drops below 30% of class PnL share.
    ctf_penalized = 0
    try:
        for pick in active_picks:
            try:
                if (str(pick.get("asset_class", "") or "").upper() == "COMMODITY"
                        and str(pick.get("symbol", "") or "").upper() in ("CT=F", "CT")):
                    _current_score = float(pick.get("score", 0) or 0)
                    pick["score"] = max(0, int(_current_score - 8))
                    pick["concentration_penalty"] = "CT=F -8 (single-contract >70% PnL share)"
                    ctf_penalized += 1
            except Exception:
                pass  # fail-open: never break admission for a single pick
    except Exception as _ctf_exc:
        log.warning("CT=F concentration guard failed (fail-open): %s", _ctf_exc)
    if ctf_penalized:
        log.info(
            "CT=F concentration guard: %d COMMODITY picks penalized (-8 score, "
            "single-contract >70%% PnL share)",
            ctf_penalized,
        )

    # ── EQUITY gap-risk de-prioritize (2026-05-15) ──
    # Symbols in GAP_RISK_EQUITY_SYMBOLS (NIO, LCID, RIVN, GME, AMC, PLTR, etc.)
    # drag EQUITY PF via low-float gap events. Penalty: -6 to score to de-prioritize
    # without hard-blocking. Does NOT apply to non-EQUITY asset classes.
    # Lift penalty when GAP_RISK names are removed from EQUITY_SYMBOLS entirely.
    gap_risk_penalized = 0
    try:
        from alpha_engine.config import is_gap_risk_equity
        for pick in active_picks:
            try:
                if (str(pick.get("asset_class", "") or "").upper() == "EQUITY"
                        and is_gap_risk_equity(str(pick.get("symbol", "") or ""))):
                    _current_score = float(pick.get("score", 0) or 0)
                    pick["score"] = max(0, int(_current_score - 6))
                    pick["gap_risk_penalty"] = "gap-risk de-prioritize -6"
                    gap_risk_penalized += 1
            except Exception:
                pass  # fail-open: never block admission for a single pick
    except Exception as _gr_exc:
        log.warning("EQUITY gap-risk penalty failed (fail-open): %s", _gr_exc)
    if gap_risk_penalized:
        log.info(
            "EQUITY gap-risk penalty: %d picks penalized (-6 score, low-float/meme symbols)",
            gap_risk_penalized,
        )

    # ── M-026: EQUITY day-of-week tilt (2026-05-15) ──
    # Tue/Wed historically show higher WR for EQUITY momentum picks.
    # Disabled by default (EQUITY_DOW_TILT=0). Set to "1" to activate.
    # Effect: +3 score on Tue/Wed, -2 score on Mon/Fri for EQUITY picks.
    # Keep as a score adjustment only — never a hard gate.
    try:
        import os as _os_dow
        if _os_dow.environ.get("EQUITY_DOW_TILT", "0") not in ("0", "false", "FALSE", "False"):
            import datetime as _dt_dow
            _dow_today = _dt_dow.datetime.utcnow().weekday()  # 0=Mon, 4=Fri
            _dow_tilt = {1: 3, 2: 3, 0: -2, 4: -2}.get(_dow_today, 0)
            if _dow_tilt != 0:
                _dow_penalized = _dow_boosted = 0
                for pick in active_picks:
                    try:
                        if str(pick.get("asset_class", "") or "").upper() == "EQUITY":
                            pick["score"] = max(0, min(100, int(float(pick.get("score", 0) or 0) + _dow_tilt)))
                            pick["_dow_tilt"] = _dow_tilt
                            if _dow_tilt > 0:
                                _dow_boosted += 1
                            else:
                                _dow_penalized += 1
                    except Exception:
                        pass
                if _dow_boosted or _dow_penalized:
                    log.info("M-026 DOW tilt: weekday=%d tilt=%+d equity_boosted=%d penalized=%d",
                             _dow_today, _dow_tilt, _dow_boosted, _dow_penalized)
    except Exception as _dow_exc:
        log.debug("M-026 DOW tilt skipped (fail-open): %s", _dow_exc)

    # ── M-027: FUTURES Thursday short momentum tilt (2026-05-15) ──
    # Thursdays show +2.56% avg edge on short momentum FUTURES picks (n=9 live).
    # Disabled by default (FUTURES_DOW_TILT=0). Requires n>30 before production use.
    # Short-bias: +3 score on SHORT direction on Thursdays; -2 on non-Thursday SHORT.
    try:
        import os as _os_fut_dow
        if _os_fut_dow.environ.get("FUTURES_DOW_TILT", "0") not in ("0", "false", "FALSE", "False"):
            import datetime as _dt_fut
            _fut_weekday = _dt_fut.datetime.utcnow().weekday()  # 3=Thursday
            _fut_boosted = _fut_penalized = 0
            for pick in active_picks:
                try:
                    if str(pick.get("asset_class", "") or "").upper() != "FUTURES":
                        continue
                    _is_short = str(pick.get("direction", "") or "").upper() == "SHORT"
                    if not _is_short:
                        continue
                    if _fut_weekday == 3:  # Thursday
                        pick["score"] = max(0, min(100, int(float(pick.get("score", 0) or 0) + 3)))
                        pick["_futures_dow_tilt"] = +3
                        _fut_boosted += 1
                    else:
                        pick["score"] = max(0, min(100, int(float(pick.get("score", 0) or 0) - 2)))
                        pick["_futures_dow_tilt"] = -2
                        _fut_penalized += 1
                except Exception:
                    pass
            if _fut_boosted or _fut_penalized:
                log.info("M-027 FUTURES DOW tilt: weekday=%d boosted=%d penalized=%d",
                         _fut_weekday, _fut_boosted, _fut_penalized)
    except Exception as _fut_dow_exc:
        log.debug("M-027 FUTURES DOW tilt skipped (fail-open): %s", _fut_dow_exc)

    # ── Final [0, 100] clamp (safety net) ──
    # Every boost/penalty above may push scores outside the valid range.
    # This MUST be the last scoring operation before the payload is saved.
    for pick in active_picks:
        s = _float(pick.get("score", 0))
        clamped = int(min(100, max(0, s)))
        if clamped != int(s):
            pick["score"] = clamped
            pick["_clamped_to_range"] = True

    # ── Save updated payload ──
    log.info("Boosted %d picks (total +%d score points)", boosted_count, total_boost_pts)

    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    log.info("Saved boosted payload to %s", payload_path)

    # ── Save boost log ──
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "boosted_picks": boosted_count,
        "total_boost_points": total_boost_pts,
        "family_stats": {
            fam: {
                "boost": s["boost"],
                "live_count": s["live"]["count"],
                "live_wr": round(s["live"]["wr"] * 100, 1),
                "live_pnl": s["live"]["total_pnl"],
                "live_avg_score": s["live"]["avg_score"],
                "closed_count": s["closed"]["count"],
                "closed_wr": round(s["closed"]["wr"] * 100, 1),
            }
            for fam, s in family_stats.items()
        },
        "top_boosts": sorted(boost_details, key=lambda x: x["pnl_pct"], reverse=True)[:20],
        "low_wr_penalized": low_wr_penalized,
        "dedup_penalized": dedup_penalized,
        "opposing_penalized": opposing_penalized,
        "tp_sl_flagged": tp_sl_flagged,
        "rr_penalized": rr_penalized,
        "symbol_capped": symbol_capped_count,
        "liquidity_penalized": liquidity_penalized,
        "mtf_boosted": mtf_boosted,
        "mtf_penalized": mtf_penalized,
        "ensemble_boosted": ens_boosted,
        "ensemble_penalized": ens_penalized,
        "proven_winner_boosted": proven_winner_boosted,
        "verified_alpha_floored": verified_alpha_floored,
        "pnl_outlier_capped": pnl_capped_count,
        "symbol_wr_capped": symbol_wr_capped,
        "noncrypto_catastrophe_penalized": noncrypto_penalized,
        "sys_ac_wr_capped": sys_ac_capped,
        "short_edge_boosted": short_edge_boosted,
        "ctf_concentration_penalized": ctf_penalized,
    }

    BOOST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BOOST_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    log.info("Saved boost log to %s", BOOST_LOG_PATH)

    return summary


if __name__ == "__main__":
    result = run_score_booster()
    if "error" in result:
        print(f"ERROR: {result['error']}")
        sys.exit(1)

    print(f"\n=== Score Booster Complete ===")
    print(f"Boosted picks: {result['boosted_picks']}")
    print(f"Total boost points: {result['total_boost_points']}")
    print(f"\nPer-family stats:")
    for fam, stats in result.get("family_stats", {}).items():
        if stats["boost"] > 0:
            print(f"  {fam}: boost=+{stats['boost']}, "
                  f"live={stats['live_count']} picks ({stats['live_wr']:.0f}% WR, +{stats['live_pnl']:.1f}% PnL), "
                  f"closed={stats['closed_count']} picks ({stats['closed_wr']:.0f}% WR)")
    if result.get("top_boosts"):
        print(f"\nTop boosted picks:")
        for b in result["top_boosts"][:10]:
            print(f"  {b['symbol']}: {b['old_score']} -> {b['new_score']} (+{b['new_score']-b['old_score']}) "
                  f"[{b['family']}] PnL: {b['pnl_pct']:+.2f}%")
