# run_super_mutations.py
"""
Entry script for the Super Mutation Designer.
It loads the five blended strategy mutation functions from `super_mutations.py`,
instantiates them with sample market data, and runs a backtest across the
standard symbols (BTCUSDT, ETHUSDT, SOLUSDT) using the existing backtester.
Results are written to `genome/mutation_lab/super_mutation_results.json`.
"""

from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

# Import the mutation functions
from .super_mutations import (
    keltner_rsi_confluence_v2,
    consensus_deep_value_hybrid,
    genesis_momentum_blend,
    ml_keltner_adaptive,
    multi_system_conviction_filter,
)

from .backtester import MutationGenes, backtest_on_all_symbols, fetch_klines, BACKTEST_SYMBOLS

logger = logging.getLogger(__name__)


def _make_genes(func) -> MutationGenes:
    """Run the mutation function with a minimal placeholder data dict and
    convert the returned dict into a MutationGenes instance.
    The mutation functions expect a dict with keys used internally; we provide
    a generic placeholder that satisfies the most common keys.
    """
    placeholder = {
        "price": 100.0,
        "keltner_upper": 105.0,
        "keltner_lower": 95.0,
        "rsi": 50,
        "consensus_score": 0.5,
        "rsi_cap": 50,
        "genesis_momentum": 0,
        "ma_fast": 100.0,
        "ma_slow": 100.0,
        "ml_score": 0.0,
        "keltner_range": 1.0,
        "subsystem_signals": [True, False, True, True],
    }
    result = func(placeholder)
    # The mutation functions already return a dict with name and signal.
    # We map that to a MutationGenes instance using sensible defaults.
    # For a full implementation you would translate the signal into concrete
    # parameter values; here we generate a generic gene set.
    return MutationGenes(
        name=result.get("strategy", "unknown"),
        rsi_period=14,
        rsi_oversold=30,
        rsi_overbought=70,
        ema_fast=9,
        ema_slow=21,
        ema_trend=50,
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        bb_period=20,
        bb_std=2.0,
        atr_period=14,
        tp_atr_mult=2.0,
        sl_atr_mult=1.5,
        vol_threshold=1.3,
        confidence_base=0.42,
        invert_signals=False,
    )


def run_super_mutations(output_path: str = "super_mutation_results.json") -> list[dict]:
    logger.info("Generating super mutation gene sets")
    mutation_funcs = [
        keltner_rsi_confluence_v2,
        consensus_deep_value_hybrid,
        genesis_momentum_blend,
        ml_keltner_adaptive,
        multi_system_conviction_filter,
    ]
    genes_list = [_make_genes(f) for f in mutation_funcs]

    # Prefetch market data
    symbols = BACKTEST_SYMBOLS
    market_data = {}
    for sym in symbols:
        df = fetch_klines(sym)
        if df is not None:
            market_data[sym] = df

    results = []
    for i, genes in enumerate(genes_list):
        logger.info(f"Backtesting super mutation {i+1}/{len(genes_list)}: {genes.name}")
        bt = backtest_on_all_symbols(genes, symbols=symbols, market_data=market_data)
        results.append({
            "strategy_name": genes.name,
            "dna_hash": genes.dna_hash,
            "backtest_results": bt,
        })

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mutation_type": "super",
        "total_mutations": len(results),
        "results": results,
    }
    Path(output_path).write_text(json.dumps(output, indent=2, default=str))
    logger.info(f"Super mutation results written to {output_path}")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    run_super_mutations()
