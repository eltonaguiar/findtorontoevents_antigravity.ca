"""Strategy B + C2: Loser Inversion + Pure Flip — 30% budget (15 mutations).

B (Pure Flip, 5 mutations): Direct signal inversion of worst losers (WR<30%).
  If a strategy consistently loses, its inverse should consistently win.
  No parameter changes — just flip BUY↔SELL.

C2 (Loser Invert, 10 mutations): Flip signals AND adjust parameters.
  Invert direction + optimize TP/SL for the new direction.

Usage:
    python -m genome.mutation_lab.mutator_invert --targets mutation_targets.json --output results_b.json [--symbol BTCUSDT]
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

NUM_PURE_FLIP = 5
NUM_LOSER_INVERT = 10


def _infer_genes_from_loser(loser: dict, invert: bool = True) -> MutationGenes:
    """Infer gene parameters from a losing strategy."""
    name = loser.get("name", "unknown")
    wr = loser.get("win_rate", 0.3)
    if wr > 1:
        wr /= 100

    # Losers often have bad TP/SL ratios — fix when inverting
    if wr < 0.30:
        tp_mult, sl_mult = 2.5, 1.0  # aggressive TP, tight SL
    elif wr < 0.40:
        tp_mult, sl_mult = 2.2, 1.2
    else:
        tp_mult, sl_mult = 2.0, 1.5

    name_lower = name.lower()
    rsi_period = 14
    if "rsi" in name_lower:
        rsi_oversold, rsi_overbought = 30, 70
    elif "macd" in name_lower:
        rsi_oversold, rsi_overbought = 35, 65
    else:
        rsi_oversold, rsi_overbought = 30, 70

    return MutationGenes(
        name=f"{'B_flip' if not invert else 'C2_inv'}_{name[:25]}",
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
        confidence_base=0.40,
        invert_signals=True,  # KEY: flip the direction
    )


def generate_pure_flips(losers: list[dict]) -> list[MutationGenes]:
    """B: Direct signal inversion — no parameter changes, just flip direction.
    Target the absolute worst performers (WR < 30%)."""
    worst = sorted(losers, key=lambda x: x.get("win_rate", 100))
    mutations = []
    seen = set()

    for loser in worst[:NUM_PURE_FLIP * 2]:  # over-sample in case of duplicates
        if len(mutations) >= NUM_PURE_FLIP:
            break

        genes = MutationGenes(
            name=f"B_flip_{loser.get('name', 'unk')[:30]}",
            invert_signals=True,
            confidence_base=0.40,
            tp_atr_mult=2.0,
            sl_atr_mult=1.5,
        )

        if genes.dna_hash not in seen and genes.params_valid():
            seen.add(genes.dna_hash)
            mutations.append(genes)

    return mutations


def generate_loser_inversions(losers: list[dict]) -> list[MutationGenes]:
    """C2: Invert signals AND optimize parameters for the new direction."""
    mutations = []
    seen = set()

    for loser in losers[:NUM_LOSER_INVERT * 2]:
        if len(mutations) >= NUM_LOSER_INVERT:
            break

        base = _infer_genes_from_loser(loser, invert=True)

        # Apply moderate parameter mutations to find optimal inverted config
        variants = [
            # Variant 1: Tighter risk
            MutationGenes(
                name=f"C2_inv_tight_{loser.get('name', 'unk')[:20]}",
                rsi_period=base.rsi_period,
                rsi_oversold=25, rsi_overbought=75,
                ema_fast=8, ema_slow=21, ema_trend=50,
                macd_fast=12, macd_slow=26, macd_signal=9,
                bb_period=20, bb_std=2.0, atr_period=14,
                tp_atr_mult=1.8, sl_atr_mult=1.0,
                vol_threshold=1.5, confidence_base=0.42,
                invert_signals=True,
            ),
            # Variant 2: Wider net
            MutationGenes(
                name=f"C2_inv_wide_{loser.get('name', 'unk')[:20]}",
                rsi_period=10, rsi_oversold=35, rsi_overbought=65,
                ema_fast=7, ema_slow=18, ema_trend=45,
                macd_fast=10, macd_slow=22, macd_signal=7,
                bb_period=18, bb_std=1.8, atr_period=12,
                tp_atr_mult=2.5, sl_atr_mult=1.2,
                vol_threshold=1.2, confidence_base=0.38,
                invert_signals=True,
            ),
            # Variant 3: Momentum-focused inversion
            MutationGenes(
                name=f"C2_inv_mom_{loser.get('name', 'unk')[:20]}",
                rsi_period=7, rsi_oversold=30, rsi_overbought=70,
                ema_fast=5, ema_slow=13, ema_trend=34,
                macd_fast=8, macd_slow=17, macd_signal=6,
                bb_period=15, bb_std=2.2, atr_period=10,
                tp_atr_mult=2.2, sl_atr_mult=1.3,
                vol_threshold=1.4, confidence_base=0.43,
                invert_signals=True,
            ),
        ]

        for v in variants:
            if len(mutations) >= NUM_LOSER_INVERT:
                break
            if v.dna_hash not in seen and v.params_valid():
                seen.add(v.dna_hash)
                mutations.append(v)

    return mutations


def run_invert(targets_path: str, output_path: str,
               symbol: str | None = None) -> list[dict]:
    """Main entry point for inversion mutations."""
    targets = json.loads(Path(targets_path).read_text())
    losers = targets.get("losers", [])

    if not losers:
        logger.warning("No losers found in targets")
        return []

    logger.info(f"Generating inversions from {len(losers)} losers")

    # Generate both types
    pure_flips = generate_pure_flips(losers)
    loser_inverts = generate_loser_inversions(losers)
    all_mutations = pure_flips + loser_inverts
    logger.info(f"Generated {len(pure_flips)} pure flips + {len(loser_inverts)} inversions = {len(all_mutations)} total")

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

        # Find parent
        loser_idx = min(i, len(losers) - 1)
        mutation_type = "pure_flip" if i < len(pure_flips) else "loser_invert"

        results.append({
            "strategy_name": genes.name,
            "mutation_type": mutation_type,
            "parent_strategy": losers[loser_idx].get("name", "unknown"),
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
        "mutation_type": "invert",
        "total_mutations": len(results),
        "passed": sum(1 for r in results if r["backtest_results"].get("passed")),
        "pure_flips": len(pure_flips),
        "loser_inverts": len(loser_inverts),
        "results": results,
    }

    Path(output_path).write_text(json.dumps(output, indent=2, default=str))
    logger.info(f"Invert results written to {output_path}: {output['passed']}/{output['total_mutations']} passed")
    return results


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Mutation Lab: Loser Inversion + Pure Flip")
    parser.add_argument("--targets", default="mutation_targets.json")
    parser.add_argument("--output", default="mutation_results_b.json")
    parser.add_argument("--symbol", default=None)
    args = parser.parse_args()

    results = run_invert(args.targets, args.output, args.symbol)
    passed = sum(1 for r in results if r["backtest_results"].get("passed"))
    print(f"Invert complete: {passed}/{len(results)} passed quality gates")


if __name__ == "__main__":
    main()
