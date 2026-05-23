#!/usr/bin/env python3
"""
Backtest the proposed 9-gate High Conviction filter against closed trades.

Loads closed picks CSV, splits chronologically (70/30), applies gates,
reports WR/PnL on train vs test to detect overfitting.

Usage:
    python tools/backtest_hc_gates.py
    python tools/backtest_hc_gates.py --csv path/to/closed_picks.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Any

_SIGNAL_GROUPS: dict[str, list[str]] = {
    "ml_engine": [
        "alpha_engine", "alpha_engine_fast", "ml_crypto_pred",
        "ml_crypto_pred_v12", "mercury2", "predictions",
        "crypto_ml_edge", "dna_winner_picks",
    ],
    "technical": [
        "luxalgo_filters", "rapid_fire", "breakout_b_ml",
        "breakout_c_spike", "baby_strats_forward", "tsmom_strategy",
        "super_signals",
    ],
    "regime_group": [
        "regime_terminal", "battleground", "quan_engine",
        "fear_greed_contrarian",
    ],
    "prediction_market": [
        "pm_whale_signals", "pm_kalshi_signals",
        "prediction_market_consensus", "pm_momentum_signals",
    ],
    "copy_trader": [
        "copy_trader_highscore", "copy_trader_intel",
        "copy_trader_clones", "copy_trader_consensus",
    ],
    "ai_challenge": [
        "ai_challenge_antigravity", "ai_challenge_grok",
        "ai_challenge_mercury", "claude_gainer_st",
        "chatgpt_combined", "kimi_riseoftheclaw",
    ],
    "fundamentals": [
        "pead_earnings_drift", "quality_minus_junk",
        "quality_value", "earnings_drift",
    ],
}

_CORR_PAIRS: dict[str, list[str]] = {
    "ETHUSDT": ["SOLUSDT", "AVAXUSDT", "NEARUSDT"],
    "SOLUSDT": ["ETHUSDT", "AVAXUSDT", "NEARUSDT"],
    "BTCUSDT": ["ETHUSDT", "BNBUSDT"],
    "BNBUSDT": ["BTCUSDT"],
    "AVAXUSDT": ["ETHUSDT", "SOLUSDT"],
    "NEARUSDT": ["ETHUSDT", "SOLUSDT"],
}


def _num(v: Any, default: float = 0.0) -> float:
    try:
        s = str(v).strip().rstrip("%")
        return float(s)
    except (TypeError, ValueError):
        return default


def _norm_wr(v: float) -> float:
    if v > 1.5:
        return v / 100.0
    return v


def _norm_conf(v: float) -> float:
    if v > 1:
        return v / 100.0
    return v


def _parse_source_systems(row: dict) -> list[str]:
    """Extract source systems from CSV row."""
    raw = row.get("Consensus System Reasons", "") or ""
    systems: list[str] = []
    sys_field = (row.get("System") or "").strip()
    if sys_field:
        systems.append(sys_field)
    paren_match = re.search(r"\(([^)]+)\)", raw)
    if paren_match:
        for s in re.split(r"[,;]", paren_match.group(1)):
            s = s.strip()
            if s and s not in systems:
                systems.append(s)
    return systems


def _get_confluence_count(row: dict) -> int:
    """Get confluence count from CSV -- more reliable than parsing system names."""
    return int(_num(row.get("Confluence Count", 0)))


def _count_independent_groups(sources: list[str]) -> int:
    groups: set[str] = set()
    for src in sources:
        src_clean = re.sub(r"_(standalone|live_signals|signal_tracking)$", "", src)
        for gname, members in _SIGNAL_GROUPS.items():
            if src_clean in members:
                groups.add(gname)
                break
    return len(groups)


def passes_hc_v3(row: dict, passed_syms: dict[str, str] | None = None) -> bool:
    """Proposed 9-gate High Conviction filter."""
    sym = (row.get("Symbol") or "").upper()
    asset_class = (row.get("Asset Class") or "").upper()
    if asset_class in ("STOCKS", "PENNY_STOCK", "EQUITIES"):
        asset_class = "EQUITY"
    if asset_class == "COMMODITIES":
        asset_class = "COMMODITY"
    if not asset_class:
        asset_class = "CRYPTO"

    trust = _num(row.get("Trust Score (0-10)"))
    fwd_wr = _norm_wr(_num(row.get("Forward WR")))
    fwd_n = int(_num(row.get("Forward Trades")))
    conf_raw = row.get("Score Breakdown (English)") or ""
    conf_match = re.search(r"confidence=(\d+(?:\.\d+)?)%?", conf_raw)
    cf = _norm_conf(_num(conf_match.group(1)) if conf_match else 0.0)
    sc = _num(row.get("Score"))
    trust_tier = (row.get("Trust Tier") or "").upper()
    direction = (row.get("Direction") or "LONG").upper()
    direction_reason = (row.get("Direction Reason") or "").upper()

    regime = ""
    if "BEAR" in direction_reason or "TRENDING_DOWN" in direction_reason:
        regime = "BEAR"
    elif "BULL" in direction_reason or "TRENDING_UP" in direction_reason:
        regime = "BULL"
    elif "CHOPPY" in direction_reason or "RANGING" in direction_reason:
        regime = "CHOPPY"

    # GATE 1: Compound grade gate
    if sc < 40:
        return False
    if sc < 50 and trust < 8:
        return False

    # GATE 2: No SANDBOX/UNPROVEN/DEMOTED
    if trust_tier in ("SANDBOX", "UNPROVEN", "DEMOTED"):
        return False

    # GATE 3: Forward validation
    if fwd_n < 5:
        return False
    if fwd_wr < 0.45:
        return False

    # GATE 4: Trust score minimum
    trust_floor = 6.0 if asset_class == "CRYPTO" else 5.0
    if trust < trust_floor:
        return False

    # GATE 5: Overconfidence kill
    if cf > 0.95 and fwd_n < 30:
        return False
    if cf > 0.90 and fwd_n < 20:
        return False

    # GATE 6: Direction x regime
    if direction == "LONG" and regime == "BEAR":
        return False
    if direction == "SHORT" and regime == "BULL":
        if trust_tier != "PROVEN":
            return False

    # GATE 7: Walk-forward -- CSV doesn't have wf_verdict, skip in backtest

    # GATE 8: Confluence/consensus (>=3 systems agreed)
    cc = _get_confluence_count(row)
    if cc > 0 and cc < 3:
        return False

    # GATE 9: Correlated asset check
    if passed_syms is not None and sym in _CORR_PAIRS:
        for corr in _CORR_PAIRS[sym]:
            if passed_syms.get(corr) == direction:
                return False

    # All gates passed -- pick qualifies as HC
    return True


def passes_hc_old(row: dict) -> bool:
    """Current (broken) HC filter -- approximation for baseline comparison."""
    trust = _num(row.get("Trust Score (0-10)"))
    fwd_wr = _norm_wr(_num(row.get("Forward WR")))
    sc = _num(row.get("Score"))
    conf_raw = row.get("Score Breakdown (English)") or ""
    conf_match = re.search(r"confidence=(\d+(?:\.\d+)?)%?", conf_raw)
    cf = _norm_conf(_num(conf_match.group(1)) if conf_match else 0.0)

    if trust >= 6 and fwd_wr >= 0.55:
        return True
    if cf >= 0.75 and sc >= 60:
        return True
    return False


def _is_win(row: dict) -> bool:
    pnl = _num(row.get("PnL%"))
    return pnl > 0.01


def _pnl(row: dict) -> float:
    return _num(row.get("PnL%"))


def _report(label: str, rows: list[dict], filter_fn, use_corr: bool = False):
    passed = []
    rejected = []
    passed_syms: dict[str, str] = {}
    for r in rows:
        if filter_fn == passes_hc_v3:
            ok = filter_fn(r, passed_syms if use_corr else None)
        else:
            ok = filter_fn(r)
        if ok:
            passed.append(r)
            sym = (r.get("Symbol") or "").upper()
            direction = (r.get("Direction") or "LONG").upper()
            passed_syms[sym] = direction
        else:
            rejected.append(r)

    total = len(rows)
    n_pass = len(passed)
    n_rej = len(rejected)
    pass_rate = n_pass / total * 100 if total else 0

    pass_wins = sum(1 for r in passed if _is_win(r))
    pass_wr = pass_wins / n_pass * 100 if n_pass else 0
    pass_pnl = sum(_pnl(r) for r in passed) / n_pass if n_pass else 0

    rej_wins = sum(1 for r in rejected if _is_win(r))
    rej_wr = rej_wins / n_rej * 100 if n_rej else 0
    rej_pnl = sum(_pnl(r) for r in rejected) / n_rej if n_rej else 0

    all_wins = sum(1 for r in rows if _is_win(r))
    all_wr = all_wins / total * 100 if total else 0
    all_pnl = sum(_pnl(r) for r in rows) / total if total else 0

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Total trades:   {total}")
    print(f"  Passed filter:  {n_pass} ({pass_rate:.1f}%)")
    print(f"  Rejected:       {n_rej}")
    print(f"")
    print(f"  {'Category':<20} {'Count':>6} {'WR':>8} {'Avg PnL':>10}")
    print(f"  {'-'*20} {'-'*6} {'-'*8} {'-'*10}")
    print(f"  {'ALL (unfiltered)':<20} {total:>6} {all_wr:>7.1f}% {all_pnl:>9.2f}%")
    print(f"  {'PASSED (HC v3)':<20} {n_pass:>6} {pass_wr:>7.1f}% {pass_pnl:>9.2f}%")
    print(f"  {'REJECTED':<20} {n_rej:>6} {rej_wr:>7.1f}% {rej_pnl:>9.2f}%")

    if n_pass > 0:
        print(f"\n  WR improvement:  {pass_wr - all_wr:+.1f}pp")
        print(f"  PnL improvement: {pass_pnl - all_pnl:+.2f}pp")

    return {
        "total": total, "passed": n_pass, "pass_rate": pass_rate,
        "pass_wr": pass_wr, "pass_pnl": pass_pnl,
        "rej_wr": rej_wr, "rej_pnl": rej_pnl,
        "all_wr": all_wr, "all_pnl": all_pnl,
    }


def _gate_attribution(rows: list[dict]):
    """Show which gate blocks the most trades."""
    gate_kills: dict[str, int] = {
        "G1_score": 0, "G2_trust_tier": 0, "G3_fwd_validation": 0,
        "G4_trust_floor": 0, "G5_overconfidence": 0, "G6_regime": 0,
        "G8_consensus": 0, "passes_all": 0,
    }
    for r in rows:
        sym = (r.get("Symbol") or "").upper()
        asset_class = (r.get("Asset Class") or "").upper()
        if not asset_class:
            asset_class = "CRYPTO"
        trust = _num(r.get("Trust Score (0-10)"))
        fwd_wr = _norm_wr(_num(r.get("Forward WR")))
        fwd_n = int(_num(r.get("Forward Trades")))
        sc = _num(r.get("Score"))
        trust_tier = (r.get("Trust Tier") or "").upper()
        conf_raw = r.get("Score Breakdown (English)") or ""
        conf_match = re.search(r"confidence=(\d+(?:\.\d+)?)%?", conf_raw)
        cf = _norm_conf(_num(conf_match.group(1)) if conf_match else 0.0)
        direction = (r.get("Direction") or "LONG").upper()
        direction_reason = (r.get("Direction Reason") or "").upper()
        regime = ""
        if "BEAR" in direction_reason:
            regime = "BEAR"
        elif "BULL" in direction_reason:
            regime = "BULL"

        if sc < 40 or (sc < 50 and trust < 8):
            gate_kills["G1_score"] += 1; continue
        if trust_tier in ("SANDBOX", "UNPROVEN", "DEMOTED"):
            gate_kills["G2_trust_tier"] += 1; continue
        if fwd_n < 5 or fwd_wr < 0.45:
            gate_kills["G3_fwd_validation"] += 1; continue
        trust_floor = 6.0 if asset_class == "CRYPTO" else 5.0
        if trust < trust_floor:
            gate_kills["G4_trust_floor"] += 1; continue
        if (cf > 0.95 and fwd_n < 30) or (cf > 0.90 and fwd_n < 20):
            gate_kills["G5_overconfidence"] += 1; continue
        if direction == "LONG" and regime == "BEAR":
            gate_kills["G6_regime"] += 1; continue
        if direction == "SHORT" and regime == "BULL" and trust_tier != "PROVEN":
            gate_kills["G6_regime"] += 1; continue
        cc = _get_confluence_count(r)
        if cc > 0 and cc < 3:
            gate_kills["G8_consensus"] += 1; continue
        gate_kills["passes_all"] += 1

    print(f"\n  Gate Attribution (first gate that blocks each trade):")
    print(f"  {'Gate':<25} {'Blocked':>8} {'% of Total':>10}")
    print(f"  {'-'*25} {'-'*8} {'-'*10}")
    total = len(rows)
    for gate, count in sorted(gate_kills.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total else 0
        print(f"  {gate:<25} {count:>8} {pct:>9.1f}%")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="C:/Users/zerou/Downloads/antigravity_closed_picks_2026-04-09.csv")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: CSV not found at {csv_path}")
        sys.exit(1)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Loaded {len(rows)} closed trades from {csv_path.name}")

    split_idx = int(len(rows) * 0.70)
    train = rows[:split_idx]
    test = rows[split_idx:]
    print(f"Split: {len(train)} train / {len(test)} test (chronological 70/30)")

    print("\n" + "#" * 60)
    print("  BASELINE: Current (old) HC filter")
    print("#" * 60)
    _report("OLD FILTER — TRAIN SET", train, passes_hc_old)
    _report("OLD FILTER — TEST SET", test, passes_hc_old)

    print("\n" + "#" * 60)
    print("  PROPOSED: v3 9-gate HC filter")
    print("#" * 60)
    train_r = _report("v3 FILTER — TRAIN SET", train, passes_hc_v3)
    test_r = _report("v3 FILTER — TEST SET", test, passes_hc_v3)

    print("\n" + "#" * 60)
    print("  GATE ATTRIBUTION (which gate blocks the most)")
    print("#" * 60)
    _gate_attribution(rows)

    print("\n" + "=" * 60)
    print("  SUMMARY: Train vs Test comparison")
    print("=" * 60)
    print(f"  Train pass WR: {train_r['pass_wr']:.1f}%  |  Test pass WR: {test_r['pass_wr']:.1f}%")
    delta = abs(train_r["pass_wr"] - test_r["pass_wr"])
    if delta > 10:
        print(f"  WARNING: {delta:.1f}pp gap between train/test — possible overfitting")
    elif test_r["pass_wr"] < 60:
        print(f"  WARNING: Test WR {test_r['pass_wr']:.1f}% < 60% threshold — consider loosening gates")
    else:
        print(f"  OK: {delta:.1f}pp gap is within tolerance. Filter validated.")

    if test_r["passed"] < 10:
        print(f"  WARNING: Only {test_r['passed']} picks passed in test set — very selective")

    print()


if __name__ == "__main__":
    main()
