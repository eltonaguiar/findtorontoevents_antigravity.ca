"""Strategy A: Winner Amplification — 20% budget (10 mutations).

Takes top-performing strategies and makes small perturbations (±10-15%)
to find nearby parameter spaces that might perform even better.
Tightens risk management and optimizes TP/SL ratios.

Usage:
    python -m genome.mutation_lab.mutator_amplify --targets mutation_targets.json --output results_a.json [--symbol BTCUSDT]
"""

from __future__ import annotations
import argparse
import json
import logging
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from genome.mutation_lab.backtester import (
    MutationGenes, backtest_on_all_symbols, fetch_klines, BACKTEST_SYMBOLS,
)
from genome.mutation_lab.schemas import validate_mutation_results

logger = logging.getLogger(__name__)

NUM_MUTATIONS = 10
PERTURBATION_RANGE = 0.15  # ±15%


def _perturb(value: float, pct: float = PERTURBATION_RANGE) -> float:
    """Small random perturbation within ±pct range."""
    factor = 1.0 + random.uniform(-pct, pct)
    return value * factor


def _perturb_int(value: int, pct: float = PERTURBATION_RANGE) -> int:
    return max(1, round(_perturb(value, pct)))


def _infer_genes_from_winner(winner: dict) -> MutationGenes:
    """Infer gene parameters from a winning strategy's name and metrics."""
    name = winner.get("name", "unknown")
    wr = winner.get("win_rate", 0.5)
    if wr > 1:
        wr /= 100

    # Risk profile from win rate
    if wr >= 0.65:
        tp_mult, sl_mult = 1.8, 1.2  # tight risk, winners don't need big TP
    elif wr >= 0.55:
        tp_mult, sl_mult = 2.0, 1.5
    else:
        tp_mult, sl_mult = 2.5, 1.5  # needs bigger TP to compensate

    # Detect strategy type from name for better defaults
    name_lower = name.lower()
    if "rsi" in name_lower:
        rsi_period = 14
        rsi_oversold, rsi_overbought = 30, 70
    elif "macd" in name_lower:
        rsi_period = 14
        rsi_oversold, rsi_overbought = 35, 65
    elif "bb" in name_lower or "bollinger" in name_lower:
        rsi_period = 14
        rsi_oversold, rsi_overbought = 25, 75
    else:
        rsi_period = 14
        rsi_oversold, rsi_overbought = 30, 70

    return MutationGenes(
        name=f"A_amp_{name[:30]}",
        rsi_period=rsi_period,
        rsi_oversold=rsi_oversold,
        rsi_overbought=rsi_overbought,
        ema_fast=9,
        ema_slow=21,
        ema_trend=50,
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        bb_period=20,
        bb_std=2.0,
        atr_period=14,
        tp_atr_mult=tp_mult,
        sl_atr_mult=sl_mult,
        vol_threshold=1.3,
        confidence_base=0.45,
    )


def generate_amplified_mutations(winners: list[dict]) -> list[MutationGenes]:
    """Create NUM_MUTATIONS small perturbations of winning strategies."""
    mutations = []
    seen_hashes = set()

    # Distribute mutations across top winners
    per_winner = max(1, NUM_MUTATIONS // min(len(winners), NUM_MUTATIONS))

    for winner in winners[:NUM_MUTATIONS]:
        parent = _infer_genes_from_winner(winner)

        for variant in range(per_winner):
            if len(mutations) >= NUM_MUTATIONS:
                break

            mutant = MutationGenes(
                name=f"A_amp_{winner.get('name', 'unk')[:25]}_v{variant}",
                rsi_period=_perturb_int(parent.rsi_period, 0.10),
                rsi_oversold=round(_perturb(parent.rsi_oversold, 0.10), 1),
                rsi_overbought=round(_perturb(parent.rsi_overbought, 0.10), 1),
                ema_fast=_perturb_int(parent.ema_fast, 0.10),
                ema_slow=_perturb_int(parent.ema_slow, 0.10),
                ema_trend=_perturb_int(parent.ema_trend, 0.10),
                macd_fast=_perturb_int(parent.macd_fast, 0.10),
                macd_slow=_perturb_int(parent.macd_slow, 0.10),
                macd_signal=_perturb_int(parent.macd_signal, 0.10),
                bb_period=_perturb_int(parent.bb_period, 0.10),
                bb_std=round(_perturb(parent.bb_std, 0.10), 2),
                atr_period=_perturb_int(parent.atr_period, 0.10),
                tp_atr_mult=round(_perturb(parent.tp_atr_mult, 0.12), 2),
                sl_atr_mult=round(_perturb(parent.sl_atr_mult, 0.08), 2),  # tighter SL perturbation
                vol_threshold=round(_perturb(parent.vol_threshold, 0.10), 2),
                confidence_base=round(max(0.35, min(0.55, _perturb(parent.confidence_base, 0.10))), 2),
            )

            # Ensure EMA ordering
            if mutant.ema_fast >= mutant.ema_slow:
                mutant.ema_slow = mutant.ema_fast + 5
            if mutant.macd_fast >= mutant.macd_slow:
                mutant.macd_slow = mutant.macd_fast + 5

            # Pre-filter
            if not mutant.params_valid():
                continue
            if mutant.dna_hash in seen_hashes:
                continue
            seen_hashes.add(mutant.dna_hash)

            mutations.append(mutant)

    return mutations


def run_amplify(targets_path: str, output_path: str,
                symbol: str | None = None) -> list[dict]:
    """Main entry point for winner amplification."""
    targets = json.loads(Path(targets_path).read_text())
    winners = targets.get("winners", [])

    if not winners:
        logger.warning("No winners found in targets")
        return []

    logger.info(f"Generating {NUM_MUTATIONS} amplified mutations from {len(winners)} winners")
    mutations = generate_amplified_mutations(winners)
    logger.info(f"Generated {len(mutations)} valid mutations (after pre-filter)")

    # Prefetch market data
    symbols = [symbol] if symbol else BACKTEST_SYMBOLS
    market_data = {}
    for sym in symbols:
        df = fetch_klines(sym)
        if df is not None:
            market_data[sym] = df

    # Backtest each mutation
    results = []
    for i, genes in enumerate(mutations):
        logger.info(f"Backtesting mutation {i + 1}/{len(mutations)}: {genes.name}")
        bt = backtest_on_all_symbols(genes, symbols=symbols, market_data=market_data)

        parent_name = winners[min(i, len(winners) - 1)].get("name", "unknown")
        results.append({
            "strategy_name": genes.name,
            "mutation_type": "winner_amplify",
            "parent_strategy": parent_name,
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

    # Validate and write
    errors = validate_mutation_results(results)
    if errors:
        logger.warning(f"Validation warnings: {errors}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mutation_type": "winner_amplify",
        "total_mutations": len(results),
        "passed": sum(1 for r in results if r["backtest_results"].get("passed")),
        "results": results,
    }

    Path(output_path).write_text(json.dumps(output, indent=2, default=str))
    logger.info(f"Amplify results written to {output_path}: {output['passed']}/{output['total_mutations']} passed")
    return results


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Mutation Lab: Winner Amplification")
    parser.add_argument("--targets", default="mutation_targets.json")
    parser.add_argument("--output", default="mutation_results_a.json")
    parser.add_argument("--symbol", default=None, help="Single symbol to backtest")
    args = parser.parse_args()

    results = run_amplify(args.targets, args.output, args.symbol)
    passed = sum(1 for r in results if r["backtest_results"].get("passed"))
    print(f"Winner Amplify complete: {passed}/{len(results)} passed quality gates")


if __name__ == "__main__":
    main()
