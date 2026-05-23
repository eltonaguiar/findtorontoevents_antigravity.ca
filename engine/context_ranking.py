#!/usr/bin/env python3
"""
Context Ranking Engine — hierarchical decision policy for live picks.

For each new pick, this engine:
  1. Detects context (asset_class, setup_type, symbol, direction, etc.)
  2. Pulls blended historical stats from context_rankings.json
  3. Computes expected_edge = blended_wr * avg_win - blended_lr * avg_loss
  4. Decides: emit_live | low_priority | paper_trade_only | suppress

Designed to be imported by the scoring pipeline or called standalone for testing.

Usage (standalone):
  python engine/context_ranking.py                    # rank all active picks
  python engine/context_ranking.py --pick '{"symbol":"BTCUSDT","asset_class":"CRYPTO","strategy":"breakout","direction":"LONG","score":62}'

Usage (as library):
  from engine.context_ranking import ContextRanker
  ranker = ContextRanker("data/context_rankings.json")
  decision = ranker.rank_pick(pick_dict)
  # decision = {"action": "promote", "expected_edge": 0.34, "adjusted_score": 68.2, ...}
"""

import argparse
import json
import os
import sys
from pathlib import Path

_WORKSPACE = Path(__file__).resolve().parent.parent
_DEFAULT_RANKINGS = _WORKSPACE / "data" / "context_rankings.json"
_DEFAULT_PAYLOAD = _WORKSPACE / "audit_dashboard" / "data" / "dashboard_data.json"

PRIOR_WEIGHT = 20
MIN_SAMPLE_FOR_CONFIDENCE = 10


def _classify_strategy(strategy: str) -> str:
    s = (strategy or "unknown").lower().strip()
    if not s or s == "unknown":
        return "unknown"
    families = {
        "breakout": ["breakout", "squeeze", "volume_spike", "bollinger"],
        "mean_reversion": ["mean_rev", "rsi_bounce", "rsi2", "williams_r", "vwap_rev", "reversion"],
        "momentum": ["momentum", "macd", "ema_stack", "trend", "hma", "triple_confirm"],
        "scalp": ["scalp", "quick", "rapid"],
        "fear_greed": ["fear_greed", "contrarian", "sentiment"],
        "copy_trader": ["copy_", "copytrader", "copy_hl", "consensus"],
        "ml_model": ["ml_", "xgboost", "lightgbm", "gainer", "predictor"],
        "prop_firm": ["irb_", "prop_", "hoffman"],
    }
    for family, patterns in families.items():
        for pat in patterns:
            if pat in s:
                return family
    return "other"


def _shrink(child_val: float, child_n: int, parent_val: float,
            prior_weight: int = PRIOR_WEIGHT) -> float:
    return (child_n * child_val + prior_weight * parent_val) / (child_n + prior_weight)


class ContextRanker:
    """Hierarchical context-aware pick ranker."""

    def __init__(self, rankings_path: str = None):
        path = rankings_path or str(_DEFAULT_RANKINGS)
        if not os.path.isfile(path):
            self.data = None
            return
        with open(path, encoding="utf-8") as f:
            self.data = json.load(f)

    @property
    def loaded(self) -> bool:
        return self.data is not None

    def _get_global(self) -> dict:
        return self.data.get("global", {}) if self.data else {}

    def _get_asset_class(self, ac: str) -> dict:
        if not self.data:
            return {}
        return self.data.get("asset_classes", {}).get(ac, {})

    def _get_context(self, ac: str, setup_type: str) -> dict | None:
        ac_data = self._get_asset_class(ac)
        for ctx in ac_data.get("contexts", []):
            if ctx.get("setup_type") == setup_type:
                return ctx
        return None

    def _get_symbol(self, symbol: str) -> dict | None:
        if not self.data:
            return None
        for sr in self.data.get("symbol_rankings", []):
            if sr.get("symbol") == symbol:
                return sr
        return None

    def rank_pick(self, pick: dict) -> dict:
        """Compute context-aware ranking for a single pick.

        Returns dict with:
          action: emit_live | low_priority | paper_trade_only | suppress
          expected_edge: float (positive = profitable context)
          adjusted_score: float (base score * context multiplier)
          confidence: low | medium | high
          context_key: str
          explanation: str
        """
        if not self.loaded:
            return {
                "action": "neutral",
                "expected_edge": 0,
                "adjusted_score": pick.get("score", 50),
                "confidence": "low",
                "context_key": "no_rankings_loaded",
                "explanation": "No context rankings file loaded; using base score only.",
            }

        ac = (pick.get("asset_class") or "UNKNOWN").upper()
        symbol = pick.get("symbol", "UNKNOWN")
        strategy = pick.get("strategy", "unknown")
        setup_type = _classify_strategy(strategy)
        direction = (pick.get("direction") or "LONG").upper()
        base_score = float(pick.get("score") or 50)

        # Gather stats at each hierarchy level
        global_stats = self._get_global()
        ac_stats = self._get_asset_class(ac)
        ctx_stats = self._get_context(ac, setup_type)
        sym_stats = self._get_symbol(symbol)

        # Direction-specific stats
        dir_stats = ac_stats.get("by_direction", {}).get(direction)

        # Build blended expected edge using hierarchical shrinkage
        # Start with global, blend upward through specificity levels
        g_exp = global_stats.get("expectancy", 0)
        g_pf = global_stats.get("profit_factor", 1.0)
        g_wr = global_stats.get("win_rate", 50)
        g_n = global_stats.get("sample_size", 0)

        ac_exp = ac_stats.get("expectancy", g_exp)
        ac_pf = ac_stats.get("profit_factor", g_pf)
        ac_wr = ac_stats.get("win_rate", g_wr)
        ac_n = ac_stats.get("sample_size", 0)

        # Blend asset class toward global
        blended_exp = _shrink(ac_exp, ac_n, g_exp) if ac_n > 0 else g_exp
        blended_pf = _shrink(min(ac_pf, 50), ac_n, min(g_pf, 50)) if ac_n > 0 else g_pf
        blended_wr = _shrink(ac_wr, ac_n, g_wr) if ac_n > 0 else g_wr

        explanation_parts = [f"global(n={g_n})", f"ac={ac}(n={ac_n})"]

        # Blend context (setup_type) toward asset class
        if ctx_stats and ctx_stats.get("sample_size", 0) >= 5:
            ctx_n = ctx_stats["sample_size"]
            blended_exp = _shrink(ctx_stats.get("expectancy", blended_exp), ctx_n, blended_exp)
            blended_pf = _shrink(min(ctx_stats.get("profit_factor", blended_pf), 50), ctx_n, blended_pf)
            blended_wr = _shrink(ctx_stats.get("win_rate", blended_wr), ctx_n, blended_wr)
            explanation_parts.append(f"setup={setup_type}(n={ctx_n})")

        # Blend symbol toward current blended
        if sym_stats and sym_stats.get("sample_size", 0) >= MIN_SAMPLE_FOR_CONFIDENCE:
            sym_n = sym_stats["sample_size"]
            blended_exp = _shrink(sym_stats.get("blended_expectancy", blended_exp), sym_n, blended_exp)
            blended_pf = _shrink(sym_stats.get("blended_pf", blended_pf), sym_n, blended_pf)
            blended_wr = _shrink(sym_stats.get("blended_win_rate", blended_wr), sym_n, blended_wr)
            explanation_parts.append(f"sym={symbol}(n={sym_n})")

        # Direction adjustment
        if dir_stats and dir_stats.get("sample_size", 0) >= 10:
            dir_pf = dir_stats.get("profit_factor", blended_pf)
            if dir_pf < 0.7:
                blended_exp *= 0.7
                explanation_parts.append(f"dir_penalty({direction} PF={dir_pf:.2f})")
            elif dir_pf > 1.5:
                blended_exp *= 1.15
                explanation_parts.append(f"dir_boost({direction} PF={dir_pf:.2f})")

        # Compute adjusted score: base_score * context_multiplier
        if blended_pf > 0 and blended_pf < 999:
            multiplier = 0.7 + 0.3 * min(blended_pf / 2.0, 1.0)  # 0.7-1.0 range
        else:
            multiplier = 1.0 if blended_pf >= 999 else 0.7

        adjusted_score = round(base_score * multiplier, 1)

        # Determine confidence from effective sample size
        total_effective_n = ac_n + (ctx_stats.get("sample_size", 0) if ctx_stats else 0)
        if total_effective_n >= 100:
            confidence = "high"
        elif total_effective_n >= 30:
            confidence = "medium"
        else:
            confidence = "low"

        # Decision policy
        if total_effective_n < MIN_SAMPLE_FOR_CONFIDENCE:
            action = "paper_trade_only"
        elif blended_pf < 0.5:
            action = "suppress"
        elif blended_pf < 0.8 or blended_exp < -0.1:
            action = "suppress" if confidence == "high" else "low_priority"
        elif blended_pf >= 1.3 and blended_exp > 0.05 and confidence in ("medium", "high"):
            action = "emit_live"
        elif blended_pf >= 1.0 and blended_exp >= 0:
            action = "emit_live" if confidence != "low" else "low_priority"
        else:
            action = "low_priority"

        context_key = f"{ac}|{setup_type}|{symbol}"

        return {
            "action": action,
            "expected_edge": round(blended_exp, 4),
            "blended_pf": round(min(blended_pf, 999), 2),
            "blended_wr": round(blended_wr, 1),
            "adjusted_score": adjusted_score,
            "base_score": base_score,
            "context_multiplier": round(multiplier, 3),
            "confidence": confidence,
            "context_key": context_key,
            "setup_type": setup_type,
            "explanation": " → ".join(explanation_parts),
        }


def main():
    parser = argparse.ArgumentParser(description="Context ranking engine")
    parser.add_argument("--rankings", default=str(_DEFAULT_RANKINGS))
    parser.add_argument("--payload", default=str(_DEFAULT_PAYLOAD))
    parser.add_argument("--pick", type=str, default=None, help="Single pick JSON to rank")
    args = parser.parse_args()

    ranker = ContextRanker(args.rankings)
    if not ranker.loaded:
        print(f"ERROR: Rankings not found at {args.rankings}")
        print("Run 'python analysis/score_calibration.py' first to generate context_rankings.json")
        sys.exit(1)

    if args.pick:
        pick = json.loads(args.pick)
        result = ranker.rank_pick(pick)
        print(json.dumps(result, indent=2))
        return

    # Rank all active picks from dashboard payload
    if not os.path.isfile(args.payload):
        print(f"ERROR: Payload not found at {args.payload}")
        sys.exit(1)

    with open(args.payload, encoding="utf-8") as f:
        data = json.load(f)
    active = data.get("picks", data).get("active", [])
    print(f"Ranking {len(active)} active picks...\n")

    results = []
    for pick in active:
        result = ranker.rank_pick(pick)
        result["symbol"] = pick.get("symbol", "?")
        result["direction"] = pick.get("direction", "?")
        results.append(result)

    results.sort(key=lambda x: -x["expected_edge"])

    # Print summary
    actions = {"emit_live": 0, "low_priority": 0, "paper_trade_only": 0, "suppress": 0}
    for r in results:
        a = r["action"]
        actions[a] = actions.get(a, 0) + 1

    print(f"=== Decision Summary ===")
    for a, n in sorted(actions.items(), key=lambda x: -x[1]):
        print(f"  {a:>20s}: {n}")

    print(f"\n=== Top Picks (by expected edge) ===")
    for r in results[:15]:
        print(f"  {r['symbol']:>15s} {r['direction']:>5s}: "
              f"edge={r['expected_edge']:+.4f}, adj_score={r['adjusted_score']:5.1f}, "
              f"PF={r['blended_pf']:5.2f}, [{r['action']}] "
              f"({r['confidence']}) {r['setup_type']}")

    print(f"\n=== Suppressed Picks ===")
    suppressed = [r for r in results if r["action"] == "suppress"]
    for r in suppressed[:10]:
        print(f"  {r['symbol']:>15s} {r['direction']:>5s}: "
              f"edge={r['expected_edge']:+.4f}, PF={r['blended_pf']:5.2f}, "
              f"reason: {r['explanation']}")


if __name__ == "__main__":
    main()
