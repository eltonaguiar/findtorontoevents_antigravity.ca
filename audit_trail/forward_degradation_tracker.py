"""
Forward Degradation Tracker
===========================

Measures the gap between a strategy's upstream SOURCE win rate (reported by
the strategy itself via strat_fwd_wr) and its REALIZED forward win rate
(actual P&L of closed picks from that strategy).

A large negative delta means the strategy's reported edge doesn't hold up in
live forward trading — classic forward degradation / overfit signal.

Context (live data 2026-04-04T16:41Z):
  Source WR 59.2% vs Realized WR 49.7% = 9.5pp aggregate degradation
  Per-strategy analysis found catastrophic degradation:
    st_fear_greed_contrarian       -21.9pp, -19.39% PnL (17 trades)
    crypto_keltner_compression_v*  -38.2pp, -2.40% PnL (4 trades)
    crypto_bayesian_regime_trans   -25.2pp, -0.90% PnL (7 trades)
    quality-minus-junk             -23.8pp, -3.86% PnL (7 trades)

Usage
-----
    from audit_trail.forward_degradation_tracker import (
        compute_degradation_stats,
        flag_degraded_picks,
    )

    # Compute per-strategy degradation from closed picks
    stats = compute_degradation_stats(resolved_closed)

    # Apply degradation score penalty to active picks
    flagged = flag_degraded_picks(active_picks, stats)

Degradation Thresholds
----------------------
- SEVERE (-20pp or worse):  -30 score penalty, tag _degraded=SEVERE
- HIGH   (-15 to -20pp):    -20 score penalty, tag _degraded=HIGH
- MODERATE (-10 to -15pp):  -10 score penalty, tag _degraded=MODERATE
- OK (< -10pp):             no penalty
- LIFTING (+5pp or more):   +5 score bonus (strategy outperforming its history)

**Rehab parents** (see REHAB_CONFLUENCE_PARENT_STRATEGIES): penalties are **scaled down** when the
pick has MTF / elite / agreement confluence; child strategies matching ``_is_rehab_variant_strategy``
skip parent penalty. See docs/STRATEGY_REHAB_CONFLUENCE_2026-04-04.md .

Min trade requirement: 5 forward-realized trades before flagging.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable


MIN_TRADES_FOR_FLAG = 5
SEVERE_DELTA = -20.0
HIGH_DELTA = -15.0
MODERATE_DELTA = -10.0
LIFTING_DELTA = 5.0

PENALTY_SEVERE = -30
PENALTY_HIGH = -20
PENALTY_MODERATE = -10
BONUS_LIFTING = 5

# Strategies with large source-vs-realized gaps — do not hard-kill; prefer confluence
# variants (RSI2, MTF, regime) per docs/STRATEGY_REHAB_CONFLUENCE_2026-04-04.md
REHAB_CONFLUENCE_PARENT_STRATEGIES = frozenset({
    "claude_gainer_1h",
    "enhanced_ml_A_xgboost",
    "st_fear_greed_contrarian",
    "quality-minus-junk",
    "crypto_bayesian_regime_transition_momentum_v1",
})


def _float(v) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _int(v) -> int:
    try:
        return int(v) if v is not None else 0
    except (TypeError, ValueError):
        return 0


def _strategy_key(pick: dict) -> str:
    """Identify strategy for grouping."""
    s = pick.get("strategy") or pick.get("signal_type") or "unknown"
    return str(s).strip()


def _source_key(pick: dict) -> str:
    s = pick.get("source_system") or pick.get("source") or "unknown"
    return str(s).strip()


def compute_degradation_stats(closed_picks: Iterable[dict]) -> dict:
    """
    Aggregate source-vs-realized WR per (strategy, source) pair across all
    closed picks. Only includes picks with valid strat_fwd_wr.

    Returns
    -------
    dict with keys:
        by_strategy: dict[strategy_name, stats_dict]
        by_source:   dict[source_name, stats_dict]
        by_strategy_source: dict[(strategy, source), stats_dict]
        aggregate:   overall stats_dict

    Each stats_dict contains:
        trades, wins, losses, flat, resolved,
        source_wr (avg of strat_fwd_wr), realized_wr (wins/resolved*100),
        delta_pp (realized - source),
        total_pnl_pct, severity (SEVERE|HIGH|MODERATE|OK|LIFTING|NONE),
        penalty (int score adjustment to apply)
    """
    def _new_bucket() -> dict:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "flat": 0,
            "source_wr_sum": 0.0,
            "source_wr_count": 0,
            "total_pnl_pct": 0.0,
        }

    by_strategy: dict[str, dict] = defaultdict(_new_bucket)
    by_source: dict[str, dict] = defaultdict(_new_bucket)
    by_pair: dict[tuple, dict] = defaultdict(_new_bucket)
    overall = _new_bucket()

    for p in closed_picks or []:
        fwd_wr = p.get("strat_fwd_wr")
        if fwd_wr is None and p.get("forward_wr") is None:
            continue  # no source WR to compare against
        source_wr = _float(fwd_wr if fwd_wr is not None else p.get("forward_wr"))
        if source_wr <= 0:
            continue
        pnl = _float(p.get("pnl_pct") or p.get("net_pnl_pct"))
        strat = _strategy_key(p)
        src = _source_key(p)
        pair = (strat, src)

        for bucket in (by_strategy[strat], by_source[src], by_pair[pair], overall):
            bucket["trades"] += 1
            bucket["source_wr_sum"] += source_wr
            bucket["source_wr_count"] += 1
            bucket["total_pnl_pct"] += pnl
            if pnl > 0:
                bucket["wins"] += 1
            elif pnl < 0:
                bucket["losses"] += 1
            else:
                bucket["flat"] += 1

    def _finalize(bucket: dict) -> dict:
        resolved = bucket["wins"] + bucket["losses"] + bucket["flat"]
        bucket["resolved"] = resolved
        bucket["source_wr"] = round(
            bucket["source_wr_sum"] / max(1, bucket["source_wr_count"]), 1
        )
        bucket["realized_wr"] = round(bucket["wins"] / resolved * 100, 1) if resolved else None
        if bucket["realized_wr"] is None:
            bucket["delta_pp"] = None
            bucket["severity"] = "NONE"
            bucket["penalty"] = 0
        else:
            bucket["delta_pp"] = round(bucket["realized_wr"] - bucket["source_wr"], 1)
            delta = bucket["delta_pp"]
            if resolved < MIN_TRADES_FOR_FLAG:
                bucket["severity"] = "NONE"  # insufficient data
                bucket["penalty"] = 0
            elif delta <= SEVERE_DELTA:
                bucket["severity"] = "SEVERE"
                bucket["penalty"] = PENALTY_SEVERE
            elif delta <= HIGH_DELTA:
                bucket["severity"] = "HIGH"
                bucket["penalty"] = PENALTY_HIGH
            elif delta <= MODERATE_DELTA:
                bucket["severity"] = "MODERATE"
                bucket["penalty"] = PENALTY_MODERATE
            elif delta >= LIFTING_DELTA:
                bucket["severity"] = "LIFTING"
                bucket["penalty"] = BONUS_LIFTING
            else:
                bucket["severity"] = "OK"
                bucket["penalty"] = 0
        bucket["total_pnl_pct"] = round(bucket["total_pnl_pct"], 2)
        # Clean up internal accumulators
        bucket.pop("source_wr_sum", None)
        bucket.pop("source_wr_count", None)
        return bucket

    return {
        "by_strategy": {k: _finalize(v) for k, v in by_strategy.items()},
        "by_source": {k: _finalize(v) for k, v in by_source.items()},
        "by_strategy_source": {
            f"{k[0]}|{k[1]}": _finalize(v) for k, v in by_pair.items()
        },
        "aggregate": _finalize(overall),
    }


def compute_rehabilitation_hints(
    closed_picks: Iterable[dict],
    strategy_name: str,
    min_combo_trades: int = 3,
    winner_wr_threshold: float = 60.0,
) -> dict:
    """
    Per project policy 'Mutate Before Kill' — find profitable subsets of a
    degraded strategy BEFORE recommending a kill. Returns rehabilitation
    hints (winning symbol/direction combos, profitable asset classes,
    winning-side directions, inverse-candidate signals).

    Args:
        closed_picks: full closed picks list
        strategy_name: the strategy to analyze
        min_combo_trades: minimum trades for a (sym, dir) combo to count
        winner_wr_threshold: WR% to qualify as a "winner" subset

    Returns:
        dict with keys: winning_combos, winning_directions,
        winning_asset_classes, inverse_candidate, recommendations
    """
    candidates = [
        p for p in (closed_picks or [])
        if (p.get("strategy") or p.get("signal_type") or "") == strategy_name
    ]
    if not candidates:
        return {"recommendations": [], "winning_combos": [], "winning_directions": [],
                "winning_asset_classes": [], "inverse_candidate": False}

    by_sym_dir: dict[tuple, dict] = defaultdict(lambda: {"w": 0, "l": 0, "pnl": 0.0})
    by_dir: dict[str, dict] = defaultdict(lambda: {"w": 0, "l": 0, "pnl": 0.0})
    by_ac: dict[str, dict] = defaultdict(lambda: {"w": 0, "l": 0, "pnl": 0.0})
    for p in candidates:
        pnl = _float(p.get("pnl_pct") or p.get("net_pnl_pct"))
        sym = str(p.get("symbol") or "?")
        d = str(p.get("direction") or "?").upper()
        ac = str(p.get("asset_class") or "CRYPTO").upper()
        for bucket in (by_sym_dir[(sym, d)], by_dir[d], by_ac[ac]):
            bucket["pnl"] += pnl
            if pnl > 0:
                bucket["w"] += 1
            elif pnl < 0:
                bucket["l"] += 1

    winning_combos = []
    for (sym, d), s in by_sym_dir.items():
        total = s["w"] + s["l"]
        if total >= min_combo_trades:
            wr = s["w"] / total * 100
            if wr >= winner_wr_threshold:
                winning_combos.append({
                    "symbol": sym, "direction": d, "trades": total,
                    "win_rate": round(wr, 1), "pnl_pct": round(s["pnl"], 2),
                })
    winning_combos.sort(key=lambda x: (-x["win_rate"], -x["trades"]))

    winning_directions = []
    for d, s in by_dir.items():
        total = s["w"] + s["l"]
        if total >= 5:
            wr = s["w"] / total * 100
            if wr >= 55:
                winning_directions.append({
                    "direction": d, "trades": total,
                    "win_rate": round(wr, 1), "pnl_pct": round(s["pnl"], 2),
                })

    winning_asset_classes = []
    for ac, s in by_ac.items():
        total = s["w"] + s["l"]
        if total >= 5:
            wr = s["w"] / total * 100
            if wr >= 55:
                winning_asset_classes.append({
                    "asset_class": ac, "trades": total,
                    "win_rate": round(wr, 1), "pnl_pct": round(s["pnl"], 2),
                })

    # Inverse candidate: if overall WR < 40% on 10+ trades, inverse is worth testing
    all_resolved = sum((by_dir[d]["w"] + by_dir[d]["l"]) for d in by_dir)
    all_wins = sum(by_dir[d]["w"] for d in by_dir)
    inverse_candidate = bool(all_resolved >= 10 and (all_wins / all_resolved) < 0.40)

    recs = []
    if winning_combos:
        top = winning_combos[0]
        recs.append(
            f"SYMBOL_WHITELIST: restrict to {top['symbol']} {top['direction']} "
            f"({top['win_rate']}% WR on {top['trades']} trades, {top['pnl_pct']:+.2f}% PnL)"
        )
    if winning_directions:
        d = winning_directions[0]
        recs.append(
            f"DIRECTION_RESTRICT: {d['direction']}-only "
            f"({d['win_rate']}% WR on {d['trades']} trades)"
        )
    if winning_asset_classes:
        ac = winning_asset_classes[0]
        if ac["asset_class"] != "CRYPTO":
            recs.append(
                f"ASSET_ROTATION: {ac['asset_class']}-only "
                f"({ac['win_rate']}% WR on {ac['trades']} trades)"
            )
    if inverse_candidate:
        recs.append(
            f"INVERSE_CANDIDATE: overall WR {all_wins/all_resolved*100:.1f}% "
            f"< 40% — test inverse_{strategy_name}"
        )
    if not recs:
        recs.append(
            "DNA_MUTATION: no clear subset winner — crossover with proven strategy "
            "parameters or forward-test with tighter TP/SL"
        )

    return {
        "recommendations": recs,
        "winning_combos": winning_combos[:5],
        "winning_directions": winning_directions,
        "winning_asset_classes": winning_asset_classes,
        "inverse_candidate": inverse_candidate,
    }


def _degradation_penalty_relief(pick: dict, base_penalty: int) -> tuple[int, float]:
    """
    Reduce |penalty| when pick shows technical confluence / quality — mutate-before-kill
    for REHAB_CONFLUENCE_PARENT_STRATEGIES only. Always retains >= 15% of magnitude.
    Returns (adjusted_penalty, relief_factor 0.15-1.0).
    """
    if base_penalty >= 0:
        return base_penalty, 1.0
    mult = 1.0
    direction = str(pick.get("direction") or "").upper()
    tech_long = _int(pick.get("technical_buy_tfs", 0))
    tech_short = _int(pick.get("technical_sell_tfs", 0))
    supporting = tech_long if direction in ("LONG", "BUY") else tech_short
    if supporting >= 3:
        mult *= 0.38
    elif supporting >= 2:
        mult *= 0.58
    elite = _float(pick.get("elite_score", 0))
    if elite >= 62:
        mult *= 0.72
    elif elite >= 55:
        mult *= 0.85
    try:
        ac = _int(pick.get("agreement_count", 0))
        if ac >= 2:
            mult *= 0.72
    except (TypeError, ValueError):
        pass
    mult = max(0.15, min(1.0, mult))
    adj = int(round(base_penalty * mult))
    if adj > 0 and base_penalty < 0:
        adj = int(round(base_penalty * 0.15))
    return adj, mult


def _is_rehab_variant_strategy(strategy_name: str) -> bool:
    """Child strategies (suffix) exempt from parent degradation bucket."""
    s = str(strategy_name or "").lower().strip()
    for parent in REHAB_CONFLUENCE_PARENT_STRATEGIES:
        p = parent.lower()
        if s == p or not s.startswith(p + "_"):
            continue
        tail = s[len(p) + 1 :]
        if any(
            k in tail
            for k in (
                "rehab",
                "confluence",
                "rsi2",
                "rsi_2",
                "mtf",
                "multi_tf",
                "regime",
                "filter",
            )
        ):
            return True
    return False


def flag_degraded_picks(
    active_picks: list[dict],
    stats: dict,
    apply_penalty: bool = True,
) -> list[dict]:
    """
    Tag active picks with their strategy's degradation severity and optionally
    apply a score penalty. Uses by_strategy stats (looser than by_pair).

    Tags added to each pick:
        _degraded: severity string (SEVERE|HIGH|MODERATE|OK|LIFTING|NONE)
        _degradation_delta_pp: float
        _degradation_penalty: int (score adjustment applied)

    If apply_penalty=True, pick["score"] is adjusted by the penalty
    (floor 0, no cap).
    """
    by_strat = stats.get("by_strategy", {})
    for p in active_picks or []:
        strat = _strategy_key(p)
        if _is_rehab_variant_strategy(strat):
            p["_degraded"] = "REHAB_VARIANT"
            p["_degradation_delta_pp"] = None
            p["_degradation_penalty"] = 0
            p["_degradation_note"] = "exempt_parent_penalty_rehab_child"
            continue
        s = by_strat.get(strat)
        if not s or s.get("resolved", 0) < MIN_TRADES_FOR_FLAG:
            p["_degraded"] = "UNRATED"
            p["_degradation_delta_pp"] = None
            p["_degradation_penalty"] = 0
            continue
        p["_degraded"] = s["severity"]
        p["_degradation_delta_pp"] = s["delta_pp"]
        base_pen = s["penalty"]
        relief = 1.0
        if (
            strat in REHAB_CONFLUENCE_PARENT_STRATEGIES
            and base_pen < 0
        ):
            base_pen, relief = _degradation_penalty_relief(p, base_pen)
            p["_degradation_relief_factor"] = relief
        p["_degradation_penalty"] = base_pen
        if apply_penalty and base_pen != 0:
            cur = _float(p.get("score"))
            p["score"] = max(0, cur + base_pen)
            p["_original_score"] = cur
    return active_picks


def summarize_degradation(stats: dict, top_n: int = 10) -> str:
    """Return human-readable summary of worst decayed strategies."""
    by_strat = stats.get("by_strategy", {})
    # Sort by delta_pp ascending (most negative first)
    ranked = sorted(
        (
            (v["delta_pp"], k, v)
            for k, v in by_strat.items()
            if v.get("delta_pp") is not None
            and v.get("resolved", 0) >= MIN_TRADES_FOR_FLAG
        )
    )
    if not ranked:
        return "No strategies with enough forward data to evaluate degradation."
    lines = [f"Top {top_n} decayed strategies (delta <= {HIGH_DELTA}pp = HIGH/SEVERE):"]
    for delta, strat, s in ranked[:top_n]:
        marker = ""
        if s["severity"] in ("SEVERE", "HIGH"):
            marker = " [KILL CANDIDATE]"
        lines.append(
            f"  {strat[:50]:<50} "
            f"n={s['resolved']:>3} "
            f"src_wr={s['source_wr']:>5.1f}% "
            f"real_wr={s['realized_wr']:>5.1f}% "
            f"delta={delta:>+6.1f}pp "
            f"pnl={s['total_pnl_pct']:>+7.2f}%"
            f" [{s['severity']}]{marker}"
        )
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# P0 #3 Extensions: ALL sources coverage + dashboard alerts
# Added 2026-04-05 per docs/HEDGE_FUND_QUALITY_NEXT_STEPS.md
# ═══════════════════════════════════════════════════════════════════════════

# Known source systems that should be tracked for degradation
ALL_PUBLISHED_SOURCES = frozenset({
    # ML / Prediction systems
    "ml_crypto_predictor",
    "ml_strategy_reviver",
    "ml_strategy_reviver_inverse",
    "ml_enhanced_crypto",
    "claude_gainer_ml",
    "regime_transition",
    # Copy trader systems
    "multi_asset_copytrader",
    "copy_trader_consensus",
    "binance_copy",
    "bybit_copy",
    # Technical systems
    "luxalgo",
    "system_f_claws",
    "keltner_compression",
    "supertrend_confluence",
    "super_signal",
    # KOL / Social
    "kol_consensus",
    "social_momentum",
    # Prediction markets
    "prediction_market_consensus",
    "kalshi",
    "polymarket",
    # Aggregators
    "intelligent_unified_signal_aggregator",
    "battleground",
    "quant_signal_system",
})


def compute_source_coverage(stats: dict) -> dict:
    """
    Check which sources have degradation data vs which are expected.

    Returns:
        dict with keys:
            tracked_sources: set of sources with degradation data
            missing_sources: set of expected sources with no data
            unexpected_sources: set of sources with data but not in expected list
            coverage_pct: percentage of expected sources tracked
    """
    by_source = stats.get("by_source", {})
    tracked = set(by_source.keys())

    missing = ALL_PUBLISHED_SOURCES - tracked
    unexpected = tracked - ALL_PUBLISHED_SOURCES
    expected_count = len(ALL_PUBLISHED_SOURCES)
    tracked_expected = len(ALL_PUBLISHED_SOURCES & tracked)
    coverage_pct = (tracked_expected / expected_count * 100) if expected_count > 0 else 0

    return {
        "tracked_sources": sorted(tracked),
        "missing_sources": sorted(missing),
        "unexpected_sources": sorted(unexpected),
        "coverage_pct": round(coverage_pct, 1),
        "tracked_count": len(tracked),
        "expected_count": expected_count,
    }


def generate_degradation_alerts(
    stats: dict,
    min_trades: int = MIN_TRADES_FOR_FLAG,
    include_high: bool = True,
) -> list[dict]:
    """
    Generate user-facing alerts for strategies/sources with SEVERE or HIGH degradation.

    Each alert includes:
        - level: "CRITICAL" (SEVERE) or "WARNING" (HIGH)
        - type: "STRATEGY_DEGRADATION" or "SOURCE_DEGRADATION"
        - entity: strategy or source name
        - message: human-readable description
        - metrics: dict with delta_pp, source_wr, realized_wr, trades, pnl_pct
        - action: recommended action (KILL, INVESTIGATE, MUTATE)

    Returns:
        List of alert dicts, sorted by severity (CRITICAL first) then by delta_pp
    """
    alerts = []

    # Strategy-level alerts
    by_strategy = stats.get("by_strategy", {})
    for strat, s in by_strategy.items():
        if s.get("resolved", 0) < min_trades:
            continue
        severity = s.get("severity")
        if severity == "SEVERE" or (include_high and severity == "HIGH"):
            delta = s.get("delta_pp", 0)
            level = "CRITICAL" if severity == "SEVERE" else "WARNING"
            action = "KILL_CANDIDATE" if delta <= -20 else "INVESTIGATE_MUTATE"

            alerts.append({
                "level": level,
                "type": "STRATEGY_DEGRADATION",
                "entity": strat,
                "message": (
                    f"Strategy '{strat}' forward performance degraded {abs(delta):.1f}pp "
                    f"below reported WR ({s.get('source_wr', 0):.1f}% → {s.get('realized_wr', 0):.1f}%) "
                    f"across {s.get('resolved', 0)} trades"
                ),
                "metrics": {
                    "delta_pp": delta,
                    "source_wr": s.get("source_wr"),
                    "realized_wr": s.get("realized_wr"),
                    "trades": s.get("resolved"),
                    "pnl_pct": s.get("total_pnl_pct"),
                },
                "action": action,
                "severity_score": 0 if severity == "SEVERE" else 1,  # for sorting
            })

    # Source-level alerts
    by_source = stats.get("by_source", {})
    for src, s in by_source.items():
        if s.get("resolved", 0) < min_trades:
            continue
        severity = s.get("severity")
        if severity == "SEVERE" or (include_high and severity == "HIGH"):
            delta = s.get("delta_pp", 0)
            level = "CRITICAL" if severity == "SEVERE" else "WARNING"

            alerts.append({
                "level": level,
                "type": "SOURCE_DEGRADATION",
                "entity": src,
                "message": (
                    f"Source '{src}' aggregate forward performance degraded {abs(delta):.1f}pp "
                    f"({s.get('source_wr', 0):.1f}% → {s.get('realized_wr', 0):.1f}%) "
                    f"across {s.get('resolved', 0)} trades"
                ),
                "metrics": {
                    "delta_pp": delta,
                    "source_wr": s.get("source_wr"),
                    "realized_wr": s.get("realized_wr"),
                    "trades": s.get("resolved"),
                    "pnl_pct": s.get("total_pnl_pct"),
                },
                "action": "INVESTIGATE_SOURCE",
                "severity_score": 0 if severity == "SEVERE" else 1,
            })

    # Sort by severity (CRITICAL first) then by delta_pp (most negative first)
    alerts.sort(key=lambda a: (a["severity_score"], a["metrics"].get("delta_pp", 0)))

    # Remove internal sorting key
    for a in alerts:
        a.pop("severity_score", None)

    return alerts


def compute_dashboard_degradation_payload(
    stats: dict,
    top_n: int = 10,
) -> dict:
    """
    Generate structured payload for dashboard rendering of degradation data.

    Suitable for inclusion in dashboard_data.json as 'degradation_alerts' or
    'forward_degradation_panel'.

    Returns:
        dict with keys:
            alerts: list of alert dicts
            coverage: source coverage report
            summary: aggregate degradation stats
            worst_strategies: top N worst strategies by delta
            worst_sources: top N worst sources by delta
            policy_note: explanation of thresholds
            disclaimer: NFA disclaimer
    """
    alerts = generate_degradation_alerts(stats)
    coverage = compute_source_coverage(stats)

    # Worst strategies
    by_strat = stats.get("by_strategy", {})
    worst_strats = sorted(
        (
            {"name": k, **{kk: vv for kk, vv in v.items()}}
            for k, v in by_strat.items()
            if v.get("delta_pp") is not None and v.get("resolved", 0) >= MIN_TRADES_FOR_FLAG
        ),
        key=lambda x: x.get("delta_pp") or 0,
    )[:top_n]

    # Worst sources
    by_src = stats.get("by_source", {})
    worst_sources = sorted(
        (
            {"name": k, **{kk: vv for kk, vv in v.items()}}
            for k, v in by_src.items()
            if v.get("delta_pp") is not None and v.get("resolved", 0) >= MIN_TRADES_FOR_FLAG
        ),
        key=lambda x: x.get("delta_pp") or 0,
    )[:top_n]

    return {
        "alerts": alerts,
        "alert_count": len(alerts),
        "critical_count": sum(1 for a in alerts if a["level"] == "CRITICAL"),
        "warning_count": sum(1 for a in alerts if a["level"] == "WARNING"),
        "coverage": coverage,
        "summary": stats.get("aggregate", {}),
        "worst_strategies": worst_strats,
        "worst_sources": worst_sources,
        "thresholds": {
            "severe_delta_pp": SEVERE_DELTA,
            "high_delta_pp": HIGH_DELTA,
            "moderate_delta_pp": MODERATE_DELTA,
            "lifting_delta_pp": LIFTING_DELTA,
            "min_trades": MIN_TRADES_FOR_FLAG,
        },
        "policy_note": (
            "Thresholds: SEVERE ≤ -20pp, HIGH ≤ -15pp, MODERATE ≤ -10pp. "
            "LIFTING ≥ +5pp (outperforming). Minimum 5 trades for rating. "
            "Actions: KILL_CANDIDATE (extreme decay), INVESTIGATE_MUTATE (try DNA mutation), "
            "INVESTIGATE_SOURCE (source-wide issue)."
        ),
        "disclaimer": "NOT FINANCIAL ADVICE — historical research for ops visibility only.",
    }

