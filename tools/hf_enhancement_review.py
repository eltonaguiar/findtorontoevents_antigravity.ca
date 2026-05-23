#!/usr/bin/env python3
"""
Hedge-fund review metrics for Antigravity picks exports.

Produces:
- closed performance by asset class / trust tier
- system x asset-class sleeve matrix with action states
- active inventory risk concentration
- score tier efficacy

Example:
  python tools/hf_enhancement_review.py ^
    --closed "C:\\Users\\you\\Downloads\\antigravity_closed_picks.csv" ^
    --active "C:\\Users\\you\\Downloads\\antigravity_active_picks.csv" ^
    --all-picks "C:\\Users\\you\\Downloads\\antigravity_all_picks.csv" ^
    --json-out audit_trail/data/hf_enhancement_review.json
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

_REPO = Path(__file__).resolve().parents[1]


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        s = str(v).strip().replace("%", "").replace(",", "")
        if not s:
            return None
        return float(s)
    except (TypeError, ValueError):
        return None


def _norm_asset_class(v: Any) -> str:
    ac = str(v or "").strip().upper()
    alias = {
        "STOCKS": "EQUITY",
        "EQUITIES": "EQUITY",
        "PENNY_STOCK": "EQUITY",
        "COMMODITIES": "COMMODITY",
    }
    return alias.get(ac, ac or "UNKNOWN")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))
    if rows and "\ufeffSymbol" in rows[0]:
        for r in rows:
            r["Symbol"] = r.pop("\ufeffSymbol")
    if rows and "\ufeffType" in rows[0]:
        for r in rows:
            r["Type"] = r.pop("\ufeffType")
    return rows


def _wr(pnls: list[float]) -> float:
    if not pnls:
        return 0.0
    return round(100.0 * sum(1 for p in pnls if p > 0) / len(pnls), 1)


def _pf(pnls: list[float]) -> float | None:
    if not pnls:
        return None
    gp = sum(p for p in pnls if p > 0)
    gl = abs(sum(p for p in pnls if p < 0))
    if gl <= 1e-12:
        return None
    return round(gp / gl, 3)


def _avg(nums: list[float]) -> float:
    return round(sum(nums) / len(nums), 3) if nums else 0.0


def _score_bucket(score: float) -> str:
    if score < 30:
        return "<30"
    if score < 50:
        return "30-49"
    if score < 70:
        return "50-69"
    return "70+"


def _system_name(r: dict[str, str]) -> str:
    return str(
        r.get("System")
        or r.get("system")
        or r.get("source_system")
        or r.get("Strategy")
        or r.get("strategy")
        or "UNKNOWN"
    ).strip()


def _strategy_name(r: dict[str, str]) -> str:
    return str(r.get("Strategy") or r.get("strategy") or "").strip()


def _ratio(v: Any) -> float:
    n = _num(v)
    if n is None:
        return 0.0
    if n > 1.0:
        n /= 100.0
    return float(n)


def _passes_enhanced_profile(r: dict[str, str]) -> bool:
    score = _num(r.get("Score")) or 0.0
    trust_score = _num(r.get("Trust Score (0-10)") or r.get("trust_score")) or 0.0
    tier = str(r.get("Trust Tier") or r.get("trust_tier") or "").upper()
    fwd_wr = _ratio(r.get("Forward WR") or r.get("forward_wr"))
    fwd_n = int(_num(r.get("Forward Trades") or r.get("forward_trades")) or 0)
    conf = _ratio(r.get("Confidence") or r.get("confidence"))
    asset = _norm_asset_class(r.get("Asset Class") or r.get("asset_class"))

    if score < 40:
        return False
    if score < 50 and trust_score < 8:
        return False
    if tier in {"SANDBOX", "UNPROVEN", "PROBATION", "DEMOTED"}:
        return False
    if fwd_n < 5 or fwd_wr < 0.45:
        return False
    if asset != "CRYPTO" and trust_score < 5:
        return False
    if asset == "CRYPTO" and trust_score < 6:
        return False
    if conf > 0.90 and fwd_n < 20:
        return False
    if conf > 0.95 and fwd_n < 30:
        return False
    return True


def _sleeve_state(n: int, wr: float, pf: float | None, avg_pnl: float) -> str:
    # Conservative, manager-friendly defaults.
    if n < 20:
        return "probationary"
    if pf is not None and pf >= 1.25 and wr >= 55.0 and avg_pnl > 0:
        return "scale_up"
    if pf is not None and pf >= 1.0 and wr >= 50.0 and avg_pnl >= 0:
        return "hold"
    if pf is not None and pf < 0.9 and wr < 45.0 and avg_pnl < 0:
        return "suspend"
    return "de_risk"


def build_review(
    closed_rows: list[dict[str, str]],
    active_rows: list[dict[str, str]],
    all_rows: list[dict[str, str]],
) -> dict[str, Any]:
    # CLOSED aggregate
    by_ac: dict[str, list[float]] = defaultdict(list)
    by_tier: dict[str, list[float]] = defaultdict(list)
    by_sleeve: dict[tuple[str, str], list[float]] = defaultdict(list)
    score_buckets: dict[str, list[float]] = defaultdict(list)

    for r in closed_rows:
        pnl = _num(r.get("PnL%"))
        if pnl is None:
            continue
        ac = _norm_asset_class(r.get("Asset Class"))
        tier = str(r.get("Trust Tier") or "UNKNOWN").upper()
        system = _system_name(r)
        score = _num(r.get("Score")) or 0.0
        by_ac[ac].append(pnl)
        by_tier[tier].append(pnl)
        by_sleeve[(system, ac)].append(pnl)
        score_buckets[_score_bucket(score)].append(pnl)

    closed_by_ac = {
        ac: {
            "n": len(pnls),
            "wr_pct": _wr(pnls),
            "avg_pnl_pct": _avg(pnls),
            "median_pnl_pct": round(median(pnls), 3) if pnls else 0.0,
            "sum_pnl_pct": round(sum(pnls), 2),
            "profit_factor": _pf(pnls),
        }
        for ac, pnls in sorted(by_ac.items(), key=lambda kv: -len(kv[1]))
    }

    closed_by_tier = {
        tier: {
            "n": len(pnls),
            "wr_pct": _wr(pnls),
            "avg_pnl_pct": _avg(pnls),
            "sum_pnl_pct": round(sum(pnls), 2),
        }
        for tier, pnls in sorted(by_tier.items(), key=lambda kv: -len(kv[1]))
    }

    sleeve_matrix = []
    for (system, ac), pnls in sorted(by_sleeve.items(), key=lambda kv: -len(kv[1])):
        wr = _wr(pnls)
        pf = _pf(pnls)
        avg = _avg(pnls)
        sleeve_matrix.append(
            {
                "system": system,
                "asset_class": ac,
                "n": len(pnls),
                "wr_pct": wr,
                "avg_pnl_pct": avg,
                "sum_pnl_pct": round(sum(pnls), 2),
                "profit_factor": pf,
                "state": _sleeve_state(len(pnls), wr, pf, avg),
            }
        )

    top_bottom = {
        "top_10": sorted(
            [s for s in sleeve_matrix if s["n"] >= 20 and s["state"] in ("scale_up", "hold")],
            key=lambda x: (x["profit_factor"] or 0, x["avg_pnl_pct"], x["wr_pct"]),
            reverse=True,
        )[:10],
        "bottom_10": sorted(
            [s for s in sleeve_matrix if s["n"] >= 20],
            key=lambda x: (x["profit_factor"] if x["profit_factor"] is not None else 9e9, x["avg_pnl_pct"], x["wr_pct"]),
        )[:10],
    }

    # ACTIVE risk inventory
    active_by_ac = defaultdict(list)
    active_tier_mix: dict[str, Counter[str]] = defaultdict(Counter)
    active_symbols = Counter()
    active_systems = Counter()
    for r in active_rows:
        ac = _norm_asset_class(r.get("Asset Class"))
        active_by_ac[ac].append(r)
        tt = str(r.get("Trust Tier") or "UNKNOWN").upper()
        active_tier_mix[ac][tt] += 1
        active_symbols[str(r.get("Symbol") or "UNKNOWN")] += 1
        active_systems[str(r.get("System") or "UNKNOWN")] += 1

    active_inventory = {}
    for ac, rows in sorted(active_by_ac.items(), key=lambda kv: -len(kv[1])):
        fwr = [_num(r.get("Forward WR")) for r in rows if _num(r.get("Forward WR")) is not None]
        sc = [_num(r.get("Score")) for r in rows if _num(r.get("Score")) is not None]
        active_inventory[ac] = {
            "n_active": len(rows),
            "avg_forward_wr": _avg(fwr) if fwr else 0.0,
            "avg_score": _avg(sc) if sc else 0.0,
            "trust_tier_mix": dict(active_tier_mix[ac]),
        }

    total_active = len(active_rows)
    top_symbol, top_symbol_n = ("", 0)
    if active_symbols:
        top_symbol, top_symbol_n = active_symbols.most_common(1)[0]
    top_system, top_system_n = ("", 0)
    if active_systems:
        top_system, top_system_n = active_systems.most_common(1)[0]

    score_tier_perf = {
        bucket: {
            "n": len(pnls),
            "wr_pct": _wr(pnls),
            "avg_pnl_pct": _avg(pnls),
        }
        for bucket, pnls in sorted(score_buckets.items(), key=lambda kv: kv[0])
    }
    _score_order = ["<30", "30-49", "50-69", "70+"]
    _bucket_avgs = [score_tier_perf.get(k, {}).get("avg_pnl_pct", 0.0) for k in _score_order]
    _bucket_wrs = [score_tier_perf.get(k, {}).get("wr_pct", 0.0) for k in _score_order]
    score_tier_validation = {
        "bucket_order": _score_order,
        "avg_pnl_pct": _bucket_avgs,
        "wr_pct": _bucket_wrs,
        "avg_pnl_monotonic_non_decreasing": all(
            _bucket_avgs[i] <= _bucket_avgs[i + 1] for i in range(len(_bucket_avgs) - 1)
        ),
        "wr_monotonic_non_decreasing": all(
            _bucket_wrs[i] <= _bucket_wrs[i + 1] for i in range(len(_bucket_wrs) - 1)
        ),
    }

    # Enhanced-profile active pass watchlist + concentration guardrails.
    active_pass = [r for r in active_rows if _passes_enhanced_profile(r)]
    active_pass_symbol = Counter(str(r.get("Symbol") or "UNKNOWN").strip() for r in active_pass)
    active_pass_system = Counter(_system_name(r) for r in active_pass)
    active_pass_ac = Counter(_norm_asset_class(r.get("Asset Class") or r.get("asset_class")) for r in active_pass)
    _top_pass_symbol, _top_pass_symbol_n = ("", 0)
    _top_pass_system, _top_pass_system_n = ("", 0)
    _top_pass_ac, _top_pass_ac_n = ("", 0)
    if active_pass_symbol:
        _top_pass_symbol, _top_pass_symbol_n = active_pass_symbol.most_common(1)[0]
    if active_pass_system:
        _top_pass_system, _top_pass_system_n = active_pass_system.most_common(1)[0]
    if active_pass_ac:
        _top_pass_ac, _top_pass_ac_n = active_pass_ac.most_common(1)[0]
    active_pass_watch = {
        "active_total": len(active_rows),
        "active_pass_count": len(active_pass),
        "pass_rate_pct": round(100.0 * len(active_pass) / max(1, len(active_rows)), 2),
        "top_symbol": _top_pass_symbol,
        "top_symbol_share_pct": round(100.0 * _top_pass_symbol_n / max(1, len(active_pass)), 2),
        "top_system": _top_pass_system,
        "top_system_share_pct": round(100.0 * _top_pass_system_n / max(1, len(active_pass)), 2),
        "top_asset_class": _top_pass_ac,
        "top_asset_class_share_pct": round(100.0 * _top_pass_ac_n / max(1, len(active_pass)), 2),
        "guardrails": {
            "pass_rate_band_6_15": 6.0 <= (100.0 * len(active_pass) / max(1, len(active_rows))) <= 15.0,
            "symbol_lt_30": (100.0 * _top_pass_symbol_n / max(1, len(active_pass))) <= 30.0,
        },
    }

    # Strategy-specific diagnostics.
    def _contains(hay: str, needle: str) -> bool:
        return needle in hay.lower()

    claude_rows = [
        r for r in closed_rows
        if _contains(_system_name(r), "claude_gainer") or _contains(_strategy_name(r), "claude_gainer")
    ]
    claude_pnls = [_num(r.get("PnL%")) for r in claude_rows]
    claude_pnls = [p for p in claude_pnls if p is not None]
    claude_fixed_tp_n = sum(1 for p in claude_pnls if abs(p - 3.0) <= 0.05)
    claude_audit = {
        "n_closed": len(claude_pnls),
        "fixed_tp_around_3pct_n": claude_fixed_tp_n,
        "fixed_tp_share_pct": round(100.0 * claude_fixed_tp_n / max(1, len(claude_pnls)), 2),
        "wr_pct": _wr(claude_pnls),
        "avg_pnl_pct": _avg(claude_pnls),
        "score_discount_recommended": (100.0 * claude_fixed_tp_n / max(1, len(claude_pnls))) >= 40.0,
    }

    fast_rows = [
        r for r in closed_rows
        if _contains(_system_name(r), "fast_stocks_competition")
        or _contains(_strategy_name(r), "fast_stocks_competition")
    ]
    fast_pnls = [_num(r.get("PnL%")) for r in fast_rows]
    fast_pnls = [p for p in fast_pnls if p is not None]
    fast_decision = {
        "n_closed": len(fast_pnls),
        "wr_pct": _wr(fast_pnls),
        "avg_pnl_pct": _avg(fast_pnls),
        "sum_pnl_pct": round(sum(fast_pnls), 2) if fast_pnls else 0.0,
        "state": (
            "retire"
            if len(fast_pnls) >= 20 and (_wr(fast_pnls) < 35.0 or _avg(fast_pnls) < -0.5)
            else "de_risk"
        ),
        "stop_criteria": {"min_n": 20, "min_wr_pct": 35.0, "min_avg_pnl_pct": -0.5},
    }

    rapid_rows = [
        r for r in closed_rows
        if _contains(_system_name(r), "rapid_fire") or _contains(_strategy_name(r), "rapid_fire")
    ]
    rapid_pnls = [_num(r.get("PnL%")) for r in rapid_rows]
    rapid_pnls = [p for p in rapid_pnls if p is not None]
    rapid_study = {
        "n_closed": len(rapid_pnls),
        "wr_pct": _wr(rapid_pnls),
        "avg_pnl_pct": _avg(rapid_pnls),
        "profit_factor": _pf(rapid_pnls),
        "proven_bonus_candidate": len(rapid_pnls) >= 10 and _wr(rapid_pnls) >= 60.0 and _avg(rapid_pnls) > 1.0,
    }

    kimi_rows = [
        r for r in closed_rows
        if _contains(_system_name(r), "kimi_riseoftheclaw") or _contains(_strategy_name(r), "kimi_riseoftheclaw")
    ]
    kimi_conditions: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in kimi_rows:
        p = _num(r.get("PnL%"))
        if p is None:
            continue
        ac = _norm_asset_class(r.get("Asset Class"))
        direction = str(r.get("Direction") or "UNKNOWN").upper()
        kimi_conditions[(ac, direction)].append(p)
    kimi_condition_report = sorted(
        [
            {
                "asset_class": ac,
                "direction": d,
                "n": len(pnls),
                "wr_pct": _wr(pnls),
                "avg_pnl_pct": _avg(pnls),
            }
            for (ac, d), pnls in kimi_conditions.items()
        ],
        key=lambda x: (x["wr_pct"], x["avg_pnl_pct"], x["n"]),
        reverse=True,
    )

    # Cross-check all-picks file consistency.
    closed_from_all = sum(1 for r in all_rows if str(r.get("Type", "")).strip().lower() == "closed")
    active_from_all = sum(1 for r in all_rows if str(r.get("Type", "")).strip().lower() == "active")

    non_crypto_rollup_pnls: list[float] = []
    for _ac, _row in closed_by_ac.items():
        if _ac != "CRYPTO":
            non_crypto_rollup_pnls.extend(by_ac.get(_ac, []))
    non_crypto_rollup = {
        "n": len(non_crypto_rollup_pnls),
        "wr_pct": _wr(non_crypto_rollup_pnls),
        "avg_pnl_pct": _avg(non_crypto_rollup_pnls),
        "total_pnl": round(sum(non_crypto_rollup_pnls), 2) if non_crypto_rollup_pnls else 0.0,
        "profit_factor": _pf(non_crypto_rollup_pnls),
    }

    breadth_recovery = {
        "step_1_pass": active_pass_watch["guardrails"]["pass_rate_band_6_15"],
        "step_2_unlock_non_crypto_pilot": (
            active_pass_watch["guardrails"]["pass_rate_band_6_15"]
            and non_crypto_rollup["profit_factor"] is not None
            and float(non_crypto_rollup["profit_factor"] or 0) >= 1.0
        ),
        "rollback_trigger": (
            non_crypto_rollup["wr_pct"] < 50.0
            or (non_crypto_rollup["profit_factor"] is not None and float(non_crypto_rollup["profit_factor"] or 0) < 1.0)
        ),
    }

    return {
        "counts": {
            "all_rows": len(all_rows),
            "closed_rows": len(closed_rows),
            "active_rows": len(active_rows),
            "closed_rows_from_all": closed_from_all,
            "active_rows_from_all": active_from_all,
        },
        "closed_by_asset_class": closed_by_ac,
        "closed_by_trust_tier": closed_by_tier,
        "score_tier_performance": score_tier_perf,
        "score_tier_validation": score_tier_validation,
        "sleeve_matrix": sleeve_matrix,
        "sleeve_top_bottom": top_bottom,
        "active_inventory": active_inventory,
        "active_pass_watchlist": active_pass_watch,
        "non_crypto_closed_rollup": non_crypto_rollup,
        "breadth_recovery": breadth_recovery,
        "strategy_diagnostics": {
            "claude_gainer_audit": claude_audit,
            "fast_stocks_decision": fast_decision,
            "rapid_fire_upweight_study": rapid_study,
            "kimi_condition_mining": kimi_condition_report[:8],
        },
        "active_concentration": {
            "top_symbol": top_symbol,
            "top_symbol_count": top_symbol_n,
            "top_symbol_share_pct": round(100.0 * top_symbol_n / max(total_active, 1), 2),
            "top_system": top_system,
            "top_system_count": top_system_n,
            "top_system_share_pct": round(100.0 * top_system_n / max(total_active, 1), 2),
        },
        "manager_actions": {
            "de_risk_asset_classes": [
                ac
                for ac, row in closed_by_ac.items()
                if ac != "CRYPTO" and (row["profit_factor"] is None or row["profit_factor"] < 0.9)
            ],
            "scale_asset_classes": [
                ac
                for ac, row in closed_by_ac.items()
                if row["profit_factor"] is not None and row["profit_factor"] >= 1.25 and row["avg_pnl_pct"] > 0
            ],
            "monitor_flags": [
                "high_active_concentration" if (100.0 * top_system_n / max(total_active, 1)) > 30.0 else "",
                "sandbox_mix_high"
                if any(v.get("trust_tier_mix", {}).get("SANDBOX", 0) > max(1, int(v["n_active"] * 0.4)) for v in active_inventory.values())
                else "",
                "pass_set_symbol_concentration"
                if not active_pass_watch["guardrails"]["symbol_lt_30"]
                else "",
                "score_tier_non_monotonic"
                if not (score_tier_validation["avg_pnl_monotonic_non_decreasing"] and score_tier_validation["wr_monotonic_non_decreasing"])
                else "",
            ],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Hedge-fund review for Antigravity CSV exports.")
    ap.add_argument("--closed", type=Path, required=True, help="closed picks CSV")
    ap.add_argument("--active", type=Path, required=True, help="active picks CSV")
    ap.add_argument("--all-picks", type=Path, required=True, dest="all_picks", help="all picks CSV")
    ap.add_argument(
        "--json-out",
        type=Path,
        default=_REPO / "audit_trail" / "data" / "hf_enhancement_review.json",
        help="output JSON path",
    )
    args = ap.parse_args()

    for p in (args.closed, args.active, args.all_picks):
        if not p.is_file():
            print("Missing input:", p)
            return 1

    review = build_review(_read_csv(args.closed), _read_csv(args.active), _read_csv(args.all_picks))
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(review, indent=2), encoding="utf-8")

    print("Wrote", args.json_out)
    print(
        "Closed rows:",
        review["counts"]["closed_rows"],
        "| Active rows:",
        review["counts"]["active_rows"],
        "| Top system share:",
        f"{review['active_concentration']['top_system_share_pct']:.2f}%",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

