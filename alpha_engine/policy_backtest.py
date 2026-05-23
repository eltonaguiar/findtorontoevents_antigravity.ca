#!/usr/bin/env python3
"""
Policy Backtester — Re-evaluate closed picks under alternative policy rules.

Usage:
    python policy_backtest.py                          # baseline only
    python policy_backtest.py --policy new_policy.json # compare with custom policy

Policy JSON format (all fields optional, defaults shown):
{
    "goldmine_floor": {
        "min_score": 25,
        "min_confidence": 0.60
    },
    "non_crypto_cap": {
        "max_picks": null,          // null = no cap
        "window_size": 50           // sliding window size
    },
    "direction_penalty": {
        "CHOPPY":   {"LONG": 0.90, "SHORT": 0.85},
        "TRENDING": {"LONG": 1.00, "SHORT": 0.80},
        "RANGING":  {"LONG": 0.95, "SHORT": 0.95}
    },
    "kill_gates": {
        "min_trades": 20,
        "max_pf": 0.70,
        "max_wr": 35.0
    },
    "symbol_blocklist": {
        "CRM": ["all"],
        "ADBE": ["all"],
        "ACN": ["all"],
        "PG": ["all"],
        "PLTR": ["all"],
        "RIVN": ["all"],
        "PATH": ["all"]
    },
    "strategy_quarantine": {
        "strategies": ["value_quality", "dividend_aristocrats", "earnings_drift"],
        "sizing_multiplier": 0.10
    }
}

Output: impl/output/policy_backtest_result.json
"""

import csv
import re
import json
import math
import copy
import argparse
import os
from collections import defaultdict


# ─── Default policy ───────────────────────────────────────────────────────────

DEFAULT_POLICY = {
    "goldmine_floor": {
        "min_score": 25,
        "min_confidence": 0.60,
    },
    "non_crypto_cap": {
        "max_picks": None,        # None = no cap
        "window_size": 50,
    },
    "direction_penalty": {
        "CHOPPY":   {"LONG": 0.90, "SHORT": 0.85},
        "TRENDING": {"LONG": 1.00, "SHORT": 0.80},
        "RANGING":  {"LONG": 0.95, "SHORT": 0.95},
    },
    "kill_gates": {
        "min_trades": 20,
        "max_pf": 0.70,
        "max_wr": 35.0,
    },
    "symbol_blocklist": {
        "CRM":  ["all"],
        "ADBE": ["all"],
        "ACN":  ["all"],
        "PG":   ["all"],
        "PLTR": ["all"],
        "RIVN": ["all"],
        "PATH": ["all"],
    },
    "strategy_quarantine": {
        "strategies": [
            "value_quality",
            "dividend_aristocrats",
            "earnings_drift",
        ],
        "sizing_multiplier": 0.10,
    },
}

# Baseline = no filtering, no penalties, full sizing
BASELINE_POLICY = {
    "goldmine_floor": {"min_score": 0, "min_confidence": 0.0},
    "non_crypto_cap": {"max_picks": None, "window_size": 0},
    "direction_penalty": {},
    "kill_gates": {"min_trades": 0, "max_pf": 0.0, "max_wr": 0.0},
    "symbol_blocklist": {},
    "strategy_quarantine": {"strategies": [], "sizing_multiplier": 1.0},
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_float(v, default=0.0):
    """Parse a string to float, returning *default* on failure."""
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _extract_confidence(score_breakdown: str) -> float:
    """Pull confidence=XX% from the score breakdown text."""
    m = re.search(r"confidence=(\d+(?:\.\d+)?)%", score_breakdown)
    if m:
        return float(m.group(1)) / 100.0
    return 0.0


def _extract_forward_pf(entry_reason_full: str) -> float:
    """Try to extract PF from audit text like 'PF=0.87' or 'PF 0.73'."""
    m = re.search(r"PF\s*=?\s*([\d.]+)", entry_reason_full)
    if m:
        return float(m.group(1))
    return 1.0


def _extract_forward_wr_pct(entry_reason_full: str) -> float:
    """Try to extract WR% from audit text."""
    m = re.search(r"(\d+(?:\.\d+)?)%\s*WR", entry_reason_full)
    if m:
        return float(m.group(1))
    return 50.0


def _extract_forward_trades(entry_reason_full: str) -> int:
    """Try to extract trade count from audit text."""
    m = re.search(r"(\d+)\s*(?:closed\s+)?trades", entry_reason_full)
    if m:
        return int(m.group(1))
    return 0


def _strategy_matches_blocklist(strategy_name: str, blocklist: dict) -> bool:
    """Check if strategy_name fuzzy-matches any blocklist entry."""
    s_lower = strategy_name.lower().replace("_", " ")
    for blocked_key in blocklist:
        b_lower = blocked_key.lower().replace("_", " ")
        if b_lower in s_lower or s_lower in b_lower:
            return True
    return False


def _strategy_matches_quarantine(strategy_name: str, quarantine_list: list) -> bool:
    """Check if strategy_name fuzzy-matches any quarantine strategy."""
    s_lower = strategy_name.lower().replace("_", " ").replace("-", " ")
    for q in quarantine_list:
        q_lower = q.lower().replace("_", " ").replace("-", " ")
        # Check word-level overlap
        q_words = set(q_lower.split())
        s_words = set(s_lower.split())
        if q_words & s_words:
            return True
        if q_lower in s_lower or s_lower in q_lower:
            return True
    return False


def _is_goldmine(strategy_name: str) -> bool:
    """Check if 'goldmine' appears in the strategy name."""
    return "goldmine" in strategy_name.lower()


def _is_crypto(asset_class: str) -> bool:
    return asset_class.upper() == "CRYPTO"


# ─── Core metrics ─────────────────────────────────────────────────────────────

def _compute_metrics(pnl_list: list) -> dict:
    """Compute aggregate metrics from a list of PnL% floats."""
    n = len(pnl_list)
    if n == 0:
        return {
            "n": 0, "wr_pct": 0.0, "pf": 0.0,
            "expectancy": 0.0, "median_pnl": 0.0,
            "var_95": 0.0, "var_99": 0.0,
            "max_dd": 0.0, "total_pnl": 0.0,
        }

    wins = [p for p in pnl_list if p > 0]
    losses = [p for p in pnl_list if p <= 0]

    wr = (len(wins) / n) * 100.0

    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    pf = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    expectancy = sum(pnl_list) / n

    sorted_pnl = sorted(pnl_list)
    mid = n // 2
    if n % 2 == 1:
        median_pnl = sorted_pnl[mid]
    else:
        median_pnl = (sorted_pnl[mid - 1] + sorted_pnl[mid]) / 2.0

    # VaR (historical): the loss at the given percentile
    def _var(pnl_sorted, alpha):
        """VaR at alpha confidence — the alpha-th percentile loss (positive number)."""
        idx = max(0, int(math.floor((1.0 - alpha) * len(pnl_sorted))))
        return -pnl_sorted[idx] if pnl_sorted[idx] < 0 else 0.0

    var_95 = _var(sorted_pnl, 0.95)
    var_99 = _var(sorted_pnl, 0.99)

    # Max drawdown on cumulative equity curve
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnl_list:
        cum += p
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd

    return {
        "n": n,
        "wr_pct": round(wr, 2),
        "pf": round(pf, 4) if pf != float("inf") else 999.99,
        "expectancy": round(expectancy, 4),
        "median_pnl": round(median_pnl, 4),
        "var_95": round(var_95, 4),
        "var_99": round(var_99, 4),
        "max_dd": round(max_dd, 4),
        "total_pnl": round(sum(pnl_list), 4),
    }


# ─── PolicyBacktester ─────────────────────────────────────────────────────────

class PolicyBacktester:
    """Re-evaluate every closed pick under a configurable policy."""

    def __init__(self, closed_picks_path: str, active_picks_path: str | None = None):
        self.closed_picks = self._load_csv(closed_picks_path)
        self.active_picks = self._load_csv(active_picks_path) if active_picks_path else []
        self.policy = copy.deepcopy(BASELINE_POLICY)

    # ── CSV loading ───────────────────────────────────────────────────────

    @staticmethod
    def _load_csv(path: str) -> list[dict]:
        if not path or not os.path.isfile(path):
            return []
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return list(reader)

    # ── Policy configuration ──────────────────────────────────────────────

    def set_policy(self, config: dict) -> None:
        """Merge *config* into the current policy (deep update)."""
        self.policy = self._deep_merge(copy.deepcopy(DEFAULT_POLICY), config)

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        result = copy.deepcopy(base)
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = PolicyBacktester._deep_merge(result[k], v)
            else:
                result[k] = copy.deepcopy(v)
        return result

    # ── Pick evaluation under policy ──────────────────────────────────────

    def _evaluate_picks(self, policy: dict) -> list[dict]:
        """
        Walk every closed pick and apply policy gates.

        Returns a list of dicts:
            {symbol, strategy, asset_class, direction, regime,
             raw_pnl, effective_pnl, accepted, rejection_reason}
        """
        results = []
        quarantine_strats = policy.get("strategy_quarantine", {}).get("strategies", [])
        quarantine_mult = policy.get("strategy_quarantine", {}).get("sizing_multiplier", 1.0)
        blocklist = policy.get("symbol_blocklist", {})
        gf = policy.get("goldmine_floor", {})
        dp = policy.get("direction_penalty", {})
        kill = policy.get("kill_gates", {})

        # Per-strategy running stats for kill gates
        strat_stats = defaultdict(lambda: {"trades": 0, "wins": 0, "gross_profit": 0.0, "gross_loss": 0.0})

        # Non-crypto sliding window tracker
        nc_cap = policy.get("non_crypto_cap", {})
        nc_max = nc_cap.get("max_picks")
        nc_window = nc_cap.get("window_size", 50)
        nc_window_queue = []  # list of booleans: was this pick non-crypto?

        for row in self.closed_picks:
            symbol = row.get("Symbol", "").strip().upper()
            strategy = row.get("Strategy", "").strip()
            asset_class = row.get("Asset Class", "").strip().upper()
            direction = row.get("Direction", "").strip().upper()
            raw_pnl = _safe_float(row.get("PnL%", 0))
            score = _safe_float(row.get("Score", 0))
            score_breakdown = row.get("Score Breakdown (English)", "")
            confidence = _extract_confidence(score_breakdown)
            entry_audit = row.get("Entry Reason (Full Audit)", "")

            # Extract regime from direction reason or audit
            regime = "UNKNOWN"
            dir_reason = row.get("Direction Reason", "")
            for r in ["CHOPPY", "TRENDING", "RANGING"]:
                if r in dir_reason.upper() or r in entry_audit.upper():
                    regime = r
                    break

            accepted = True
            rejection_reason = None
            sizing_mult = 1.0

            # ── 1. Goldmine floor ──────────────────────────────────────────
            if accepted and _is_goldmine(strategy):
                gf_min_score = gf.get("min_score", 0)
                gf_min_conf = gf.get("min_confidence", 0.0)
                if score < gf_min_score or confidence < gf_min_conf:
                    accepted = False
                    rejection_reason = (
                        f"goldmine_floor(score={score}<{gf_min_score} or "
                        f"confidence={confidence:.2f}<{gf_min_conf})"
                    )

            # ── 2. Symbol blocklist ────────────────────────────────────────
            if accepted and symbol in blocklist:
                blocked_strats = blocklist[symbol]
                if "all" in blocked_strats or _strategy_matches_blocklist(strategy, {symbol: blocked_strats}):
                    accepted = False
                    rejection_reason = f"symbol_blocklist({symbol})"

            # ── 3. Non-crypto cap (sliding window) ────────────────────────
            if accepted and nc_max is not None and not _is_crypto(asset_class):
                # Count non-crypto in current window
                nc_count = sum(1 for x in nc_window_queue if x)
                if nc_count >= nc_max:
                    accepted = False
                    rejection_reason = f"non_crypto_cap(window_full:{nc_count}/{nc_max})"

            # Update sliding window
            if nc_window > 0:
                nc_window_queue.append(not _is_crypto(asset_class))
                if len(nc_window_queue) > nc_window:
                    nc_window_queue.pop(0)

            # ── 4. Kill gates (per-strategy cumulative) ────────────────────
            if accepted:
                ss = strat_stats[strategy]
                ss["trades"] += 1
                if raw_pnl > 0:
                    ss["wins"] += 1
                    ss["gross_profit"] += raw_pnl
                else:
                    ss["gross_loss"] += abs(raw_pnl)

                kg_min_trades = kill.get("min_trades", 0)
                kg_max_pf = kill.get("max_pf", 0.0)
                kg_max_wr = kill.get("max_wr", 0.0)

                if ss["trades"] >= kg_min_trades and kg_min_trades > 0:
                    strat_pf = (
                        ss["gross_profit"] / ss["gross_loss"]
                        if ss["gross_loss"] > 0
                        else (999.0 if ss["gross_profit"] > 0 else 0.0)
                    )
                    strat_wr = (ss["wins"] / ss["trades"]) * 100.0
                    if strat_pf < kg_max_pf and strat_wr < kg_max_wr:
                        accepted = False
                        rejection_reason = (
                            f"kill_gate(PF={strat_pf:.2f}<{kg_max_pf}, "
                            f"WR={strat_wr:.1f}%<{kg_max_wr}%)"
                        )

            # ── 5. Direction penalty (sizing) ──────────────────────────────
            if accepted and regime in dp:
                regime_penalties = dp[regime]
                if direction in regime_penalties:
                    sizing_mult *= regime_penalties[direction]

            # ── 6. Strategy quarantine (sizing) ────────────────────────────
            if accepted and _strategy_matches_quarantine(strategy, quarantine_strats):
                sizing_mult *= quarantine_mult

            effective_pnl = raw_pnl * sizing_mult

            results.append({
                "symbol": symbol,
                "strategy": strategy,
                "asset_class": asset_class,
                "direction": direction,
                "regime": regime,
                "raw_pnl": raw_pnl,
                "effective_pnl": effective_pnl,
                "sizing_mult": sizing_mult,
                "accepted": accepted,
                "rejection_reason": rejection_reason,
            })

        return results

    # ── Run single policy ─────────────────────────────────────────────────

    def run(self, policy: dict | None = None) -> dict:
        """Evaluate all closed picks under *policy* (or current self.policy)."""
        if policy is None:
            policy = self.policy

        evaluated = self._evaluate_picks(policy)

        accepted = [e for e in evaluated if e["accepted"]]
        rejected = [e for e in evaluated if not e["accepted"]]

        all_pnl = [e["effective_pnl"] for e in accepted]

        # Global metrics
        overall = _compute_metrics(all_pnl)

        # By asset class
        by_asset = defaultdict(list)
        for e in accepted:
            by_asset[e["asset_class"]].append(e["effective_pnl"])
        by_asset_metrics = {k: _compute_metrics(v) for k, v in sorted(by_asset.items())}

        # By strategy
        by_strategy = defaultdict(list)
        for e in accepted:
            by_strategy[e["strategy"]].append(e["effective_pnl"])
        by_strategy_metrics = {k: _compute_metrics(v) for k, v in sorted(by_strategy.items())}

        # Rejection summary
        rej_by_reason = defaultdict(int)
        for e in rejected:
            # Group by gate type
            reason = e["rejection_reason"] or "unknown"
            gate = reason.split("(")[0]
            rej_by_reason[gate] += 1

        return {
            "overall": overall,
            "by_asset_class": by_asset_metrics,
            "by_strategy": by_strategy_metrics,
            "total_closed": len(evaluated),
            "accepted": len(accepted),
            "rejected": len(rejected),
            "rejections_by_gate": dict(rej_by_reason),
        }

    # ── Compare two policies ──────────────────────────────────────────────

    def compare(self, baseline_policy: dict, new_policy: dict) -> dict:
        """Side-by-side comparison of two policies."""
        base_result = self.run(baseline_policy)
        new_result = self.run(new_policy)

        def _diff(base_m: dict, new_m: dict) -> dict:
            diff = {}
            for key in base_m:
                b = base_m[key]
                n = new_m.get(key, 0)
                if isinstance(b, (int, float)) and isinstance(n, (int, float)):
                    diff[key] = {
                        "baseline": b,
                        "new": n,
                        "delta": round(n - b, 4),
                    }
            return diff

        overall_diff = _diff(base_result["overall"], new_result["overall"])

        # By asset class
        all_assets = sorted(
            set(list(base_result["by_asset_class"].keys()) + list(new_result["by_asset_class"].keys()))
        )
        by_asset_diff = {}
        for a in all_assets:
            b = base_result["by_asset_class"].get(a, _compute_metrics([]))
            n = new_result["by_asset_class"].get(a, _compute_metrics([]))
            by_asset_diff[a] = _diff(b, n)

        # By strategy
        all_strats = sorted(
            set(list(base_result["by_strategy"].keys()) + list(new_result["by_strategy"].keys()))
        )
        by_strat_diff = {}
        for s in all_strats:
            b = base_result["by_strategy"].get(s, _compute_metrics([]))
            n = new_result["by_strategy"].get(s, _compute_metrics([]))
            by_strat_diff[s] = _diff(b, n)

        return {
            "overall": overall_diff,
            "by_asset_class": by_asset_diff,
            "by_strategy": by_strat_diff,
            "baseline_summary": {
                "total": base_result["total_closed"],
                "accepted": base_result["accepted"],
                "rejected": base_result["rejected"],
            },
            "new_summary": {
                "total": new_result["total_closed"],
                "accepted": new_result["accepted"],
                "rejected": new_result["rejected"],
                "rejections_by_gate": new_result["rejections_by_gate"],
            },
            "baseline_full": base_result,
            "new_full": new_result,
        }


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Policy backtester for closed picks")
    parser.add_argument(
        "--policy", type=str, default=None,
        help="Path to policy JSON file (merged with defaults)",
    )
    parser.add_argument(
        "--closed", type=str,
        default=os.path.join(os.path.dirname(__file__), "..", "..", "closed_picks.csv"),
        help="Path to closed_picks.csv",
    )
    parser.add_argument(
        "--active", type=str,
        default=os.path.join(os.path.dirname(__file__), "..", "..", "active_picks.csv"),
        help="Path to active_picks.csv",
    )
    parser.add_argument(
        "--output", type=str,
        default=os.path.join(os.path.dirname(__file__), "..", "output", "policy_backtest_result.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()

    bt = PolicyBacktester(args.closed, args.active)

    # Build new policy
    new_policy_cfg = {}
    if args.policy and os.path.isfile(args.policy):
        with open(args.policy) as f:
            new_policy_cfg = json.load(f)

    # Compare baseline (no filters) vs new policy
    comparison = bt.compare(BASELINE_POLICY, new_policy_cfg if new_policy_cfg else copy.deepcopy(BASELINE_POLICY))

    # Ensure output dir exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    with open(args.output, "w") as f:
        json.dump(comparison, f, indent=2, default=str)

    # Print summary
    ov = comparison["overall"]
    print("=" * 70)
    print("POLICY BACKTEST RESULTS")
    print("=" * 70)
    print(f"\n{'Metric':<20} {'Baseline':>12} {'New Policy':>12} {'Delta':>12}")
    print("-" * 56)
    for key in ["n", "wr_pct", "pf", "expectancy", "median_pnl", "var_95", "var_99", "max_dd", "total_pnl"]:
        d = ov[key]
        print(f"{key:<20} {d['baseline']:>12.4f} {d['new']:>12.4f} {d['delta']:>+12.4f}")

    bs = comparison["baseline_summary"]
    ns = comparison["new_summary"]
    print(f"\nPicks: {bs['accepted']} baseline → {ns['accepted']} new ({ns['rejected']} rejected)")

    if ns["rejections_by_gate"]:
        print("\nRejections by gate:")
        for gate, count in sorted(ns["rejections_by_gate"].items(), key=lambda x: -x[1]):
            print(f"  {gate}: {count}")

    print(f"\nFull results → {args.output}")


if __name__ == "__main__":
    main()
