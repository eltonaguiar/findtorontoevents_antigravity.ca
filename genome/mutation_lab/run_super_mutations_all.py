# run_super_mutations_all.py
"""
Extensive testing script for the Super Mutation Designer.
It fetches the full list of Binance USDT‑paired spot symbols and runs the
five super mutations across all of them, using the same backtester as
`run_super_mutations.py`. Results are written to `super_mutation_results_all.json`.
"""

from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

# Import mutation functions and backtester utilities
from .super_mutations import (
    keltner_rsi_confluence_v2,
    consensus_deep_value_hybrid,
    genesis_momentum_blend,
    ml_keltner_adaptive,
    multi_system_conviction_filter,
)
from .backtester import MutationGenes, backtest_on_all_symbols, fetch_klines

logger = logging.getLogger(__name__)


def _make_genes(func) -> MutationGenes:
    """Create a generic MutationGenes instance from a mutation function.
    The function is called with a minimal placeholder dict; the result is
    used only for naming – the actual parameters are the defaults defined in
    `MutationGenes`.
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


def _fetch_all_usdt_symbols() -> list[str]:
    """Return a list of all Binance spot symbols that end with 'USDT'."""
    _mirrors = [
        "https://api.binance.com", "https://api1.binance.com",
        "https://api2.binance.com", "https://api3.binance.com",
        "https://data-api.binance.vision",
    ]
    for _base in _mirrors:
        try:
            resp = requests.get(f"{_base}/api/v3/exchangeInfo", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            symbols = [s["symbol"] for s in data["symbols"] if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"]
            logger.info(f"Fetched {len(symbols)} USDT symbols from Binance ({_base})")
            return symbols
        except Exception as e:
            logger.warning(f"Mirror {_base} failed: {e}")
            continue
    logger.error("All Binance mirrors failed for exchangeInfo")
    return []


def run_extensive_test(output_path: str = "super_mutation_results_all.json") -> list[dict]:
    logger.info("Generating super mutation gene sets for extensive testing")
    mutation_funcs = [
        keltner_rsi_confluence_v2,
        consensus_deep_value_hybrid,
        genesis_momentum_blend,
        ml_keltner_adaptive,
        multi_system_conviction_filter,
    ]
    genes_list = [_make_genes(f) for f in mutation_funcs]

    symbols = _fetch_all_usdt_symbols()
    if not symbols:
        logger.warning("No symbols to test – aborting")
        return []

    # Prefetch market data for each symbol
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
        "mutation_type": "super_extensive",
        "total_mutations": len(results),
        "symbols_tested": len(symbols),
        "results": results,
    }
    Path(output_path).write_text(json.dumps(output, indent=2, default=str))
    logger.info(f"Extensive super mutation results written to {output_path}")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    run_extensive_test()
