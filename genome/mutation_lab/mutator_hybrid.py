"""Strategy C1 + X: Loser Fix + Crossbreed — 40% budget (20 mutations).

C1 (Loser Fix, 15 mutations): Perturb losing strategy parameters ±20-40%
  hoping to find a nearby profitable variant. Keep direction, fix parameters.

X (Crossbreed, 5 mutations): Take a winner's entry logic + a loser's
  inverted exit logic. Hybrid offspring from opposite parents.

Usage:
    python -m genome.mutation_lab.mutator_hybrid --targets mutation_targets.json --output results_c.json [--symbol BTCUSDT]
"""

from __future__ import annotations
import argparse
import json
import logging
import random
from datetime import datetime, timezone
from pathlib import Path

from genome.mutation_lab.backtester import (
    MutationGenes, backtest_on_all_symbols, fetch_klines, BACKTEST_SYMBOLS,
)
from genome.mutation_lab.schemas import validate_mutation_results

logger = logging.getLogger(__name__)

NUM_LOSER_FIX = 15
NUM_CROSSBREED = 5
FIX_PERTURBATION = 0.35  # ±35% for loser fix (aggressive)


def _perturb(value: float, pct: float = FIX_PERTURBATION) -> float:
    return value * (1.0 + random.uniform(-pct, pct))


def _perturb_int(value: int, pct: float = FIX_PERTURBATION) -> int:
    return max(1, round(_perturb(value, pct)))


def _base_genes_from_strategy(strategy: dict) -> MutationGenes:
    """Create base genes from strategy metadata."""
    name = strategy.get("name", "unknown")
    name_lower = name.lower()

    # Infer defaults from strategy type
    if "rsi" in name_lower:
        rsi_p, ema_f, ema_s = 14, 9, 21
    elif "macd" in name_lower:
        rsi_p, ema_f, ema_s = 14, 12, 26
    elif "ema" in name_lower or "momentum" in name_lower:
        rsi_p, ema_f, ema_s = 14, 8, 21
    elif "bb" in name_lower or "bollinger" in name_lower:
        rsi_p, ema_f, ema_s = 14, 9, 21
    else:
        rsi_p, ema_f, ema_s = 14, 9, 21

    return MutationGenes(
        name=name,
        rsi_period=rsi_p,
        rsi_oversold=30, rsi_overbought=70,
        ema_fast=ema_f, ema_slow=ema_s, ema_trend=50,
        macd_fast=12, macd_slow=26, macd_signal=9,
        bb_period=20, bb_std=2.0, atr_period=14,
        tp_atr_mult=2.0, sl_atr_mult=1.5,
        vol_threshold=1.3, confidence_base=0.42,
    )


def generate_loser_fixes(losers: list[dict]) -> list[MutationGenes]:
    """C1: Aggressively perturb loser parameters to find profitable variants."""
    mutations = []
    seen = set()

    # 3 fix variants per loser
    for loser in losers[:NUM_LOSER_FIX]:
        base = _base_genes_from_strategy(loser)

        fix_templates = [
            # Fix 1: Tighten everything (reduce noise)
            {
                "suffix": "tight",
                "rsi_oversold": 25, "rsi_overbought": 75,
                "tp_mult_range": (1.5, 2.5), "sl_mult_range": (0.8, 1.2),
                "vol_range": (1.5, 2.0), "conf_range": (0.45, 0.55),
            },
            # Fix 2: Widen entry, tighten exit
            {
                "suffix": "wide_entry",
                "rsi_oversold": 35, "rsi_overbought": 65,
                "tp_mult_range": (1.8, 3.0), "sl_mult_range": (1.0, 1.5),
                "vol_range": (1.0, 1.5), "conf_range": (0.35, 0.45),
            },
            # Fix 3: Faster indicators
            {
                "suffix": "fast",
                "rsi_oversold": 30, "rsi_overbought": 70,
                "tp_mult_range": (2.0, 3.0), "sl_mult_range": (1.0, 1.5),
                "vol_range": (1.2, 1.8), "conf_range": (0.40, 0.50),
            },
        ]

        for template in fix_templates:
            if len(mutations) >= NUM_LOSER_FIX:
                break

            genes = MutationGenes(
                name=f"C1_fix_{template['suffix']}_{loser.get('name', 'unk')[:20]}",
                rsi_period=_perturb_int(base.rsi_period, 0.25),
                rsi_oversold=template["rsi_oversold"] + random.uniform(-5, 5),
                rsi_overbought=template["rsi_overbought"] + random.uniform(-5, 5),
                ema_fast=_perturb_int(base.ema_fast, 0.30),
                ema_slow=_perturb_int(base.ema_slow, 0.30),
                ema_trend=_perturb_int(base.ema_trend, 0.25),
                macd_fast=_perturb_int(base.macd_fast, 0.25),
                macd_slow=_perturb_int(base.macd_slow, 0.25),
                macd_signal=_perturb_int(base.macd_signal, 0.25),
                bb_period=_perturb_int(base.bb_period, 0.20),
                bb_std=round(_perturb(base.bb_std, 0.20), 2),
                atr_period=_perturb_int(base.atr_period, 0.20),
                tp_atr_mult=round(random.uniform(*template["tp_mult_range"]), 2),
                sl_atr_mult=round(random.uniform(*template["sl_mult_range"]), 2),
                vol_threshold=round(random.uniform(*template["vol_range"]), 2),
                confidence_base=round(random.uniform(*template["conf_range"]), 2),
                invert_signals=False,  # Keep original direction
            )

            # Fix EMA ordering
            if genes.ema_fast >= genes.ema_slow:
                genes.ema_slow = genes.ema_fast + 5
            if genes.macd_fast >= genes.macd_slow:
                genes.macd_slow = genes.macd_fast + 5

            if genes.params_valid() and genes.dna_hash not in seen:
                seen.add(genes.dna_hash)
                mutations.append(genes)

    return mutations


def generate_crossbreeds(winners: list[dict], losers: list[dict]) -> list[MutationGenes]:
    """X: Combine winner entry logic with loser inverted exit logic."""
    mutations = []
    seen = set()

    for i in range(min(NUM_CROSSBREED, len(winners), len(losers))):
        winner = winners[i]
        loser = losers[-(i + 1)]  # pair from opposite ends

        winner_genes = _base_genes_from_strategy(winner)
        loser_genes = _base_genes_from_strategy(loser)

        # Take winner's entry parameters + loser's (inverted) risk parameters
        hybrid = MutationGenes(
            name=f"X_cross_{winner.get('name', 'w')[:12]}x{loser.get('name', 'l')[:12]}",
            # Entry from winner (momentum/trend detection)
            rsi_period=winner_genes.rsi_period,
            rsi_oversold=winner_genes.rsi_oversold,
            rsi_overbought=winner_genes.rsi_overbought,
            ema_fast=winner_genes.ema_fast,
            ema_slow=winner_genes.ema_slow,
            ema_trend=winner_genes.ema_trend,
            macd_fast=winner_genes.macd_fast,
            macd_slow=winner_genes.macd_slow,
            macd_signal=winner_genes.macd_signal,
            # BB from mix
            bb_period=round((winner_genes.bb_period + loser_genes.bb_period) / 2),
            bb_std=round((winner_genes.bb_std + loser_genes.bb_std) / 2, 2),
            atr_period=winner_genes.atr_period,
            # Risk management: use inverted loser's TP/SL (if loser loses at 1:1, try 2:1)
            tp_atr_mult=round(max(1.5, loser_genes.sl_atr_mult * 1.5), 2),  # loser's SL becomes our TP distance
            sl_atr_mult=round(max(0.5, loser_genes.tp_atr_mult * 0.6), 2),  # loser's TP becomes our SL
            vol_threshold=round((winner_genes.vol_threshold + loser_genes.vol_threshold) / 2, 2),
            confidence_base=round(max(0.35, (winner_genes.confidence_base + 0.45) / 2), 2),
            invert_signals=False,
        )

        # Ensure valid ratios
        if hybrid.tp_atr_mult <= hybrid.sl_atr_mult * 1.2:
            hybrid.tp_atr_mult = round(hybrid.sl_atr_mult * 1.5, 2)
        if hybrid.ema_fast >= hybrid.ema_slow:
            hybrid.ema_slow = hybrid.ema_fast + 5

        if hybrid.params_valid() and hybrid.dna_hash not in seen:
            seen.add(hybrid.dna_hash)
            mutations.append(hybrid)

    return mutations


def run_hybrid(targets_path: str, output_path: str,
               symbol: str | None = None) -> list[dict]:
    """Main entry point for loser fix + crossbreed mutations."""
    targets = json.loads(Path(targets_path).read_text())
    winners = targets.get("winners", [])
    losers = targets.get("losers", [])

    if not losers:
        logger.warning("No losers found in targets")
        return []

    logger.info(f"Generating fixes from {len(losers)} losers + crossbreeds from {len(winners)} winners")

    loser_fixes = generate_loser_fixes(losers)
    crossbreeds = generate_crossbreeds(winners, losers)
    all_mutations = loser_fixes + crossbreeds
    logger.info(f"Generated {len(loser_fixes)} fixes + {len(crossbreeds)} crossbreeds = {len(all_mutations)} total")

    # Prefetch market data
    symbols = [symbol] if symbol else BACKTEST_SYMBOLS
    market_data = {}
    for sym in symbols:
        df = fetch_klines(sym)
        if df is not None:
            market_data[sym] = df

    # Backtest
    results = []
    for i, genes in enumerate(all_mutations):
        logger.info(f"Backtesting {i + 1}/{len(all_mutations)}: {genes.name}")
        bt = backtest_on_all_symbols(genes, symbols=symbols, market_data=market_data)

        mutation_type = "loser_fix" if i < len(loser_fixes) else "crossbreed"
        if mutation_type == "loser_fix":
            parent = losers[min(i // 3, len(losers) - 1)].get("name", "unknown")
        else:
            cross_idx = i - len(loser_fixes)
            w_name = winners[min(cross_idx, len(winners) - 1)].get("name", "w")
            l_name = losers[min(cross_idx, len(losers) - 1)].get("name", "l")
            parent = f"{w_name} × {l_name}"

        results.append({
            "strategy_name": genes.name,
            "mutation_type": mutation_type,
            "parent_strategy": parent,
            "dna_hash": genes.dna_hash,
            "genes": {
                "rsi_period": genes.rsi_period,
                "ema_fast": genes.ema_fast,
                "ema_slow": genes.ema_slow,
                "macd_fast": genes.macd_fast,
                "macd_slow": genes.macd_slow,
                "tp_atr_mult": genes.tp_atr_mult,
                "sl_atr_mult": genes.sl_atr_mult,
                "vol_threshold": genes.vol_threshold,
                "confidence_base": genes.confidence_base,
                "invert_signals": genes.invert_signals,
            },
            "backtest_results": bt,
        })

    # Write
    errors = validate_mutation_results(results)
    if errors:
        logger.warning(f"Validation warnings: {errors}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mutation_type": "hybrid",
        "total_mutations": len(results),
        "passed": sum(1 for r in results if r["backtest_results"].get("passed")),
        "loser_fixes": len(loser_fixes),
        "crossbreeds": len(crossbreeds),
        "results": results,
    }

    Path(output_path).write_text(json.dumps(output, indent=2, default=str))
    logger.info(f"Hybrid results written to {output_path}: {output['passed']}/{output['total_mutations']} passed")
    return results


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Mutation Lab: Loser Fix + Crossbreed")
    parser.add_argument("--targets", default="mutation_targets.json")
    parser.add_argument("--output", default="mutation_results_c.json")
    parser.add_argument("--symbol", default=None)
    args = parser.parse_args()

    results = run_hybrid(args.targets, args.output, args.symbol)
    passed = sum(1 for r in results if r["backtest_results"].get("passed"))
    print(f"Hybrid complete: {passed}/{len(results)} passed quality gates")


if __name__ == "__main__":
    main()
