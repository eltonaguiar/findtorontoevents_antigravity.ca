#!/usr/bin/env python3
"""
Universal Evolution Runner
============================
Orchestrates ALL evolution engines in one unified pipeline:
  1. GP (genetic_programmer.py) — expression tree evolution
  2. MAP-Elites (mape_evolver.py) — quality-diversity
  3. Audit Ensemble (audit_ensemble_evolver.py) — weight meta-evolution
  4. Ensemble Coevolution (ensemble_evolver.py) — team evolution

Collects picks from all engines, finds consensus, outputs unified JSON.

Run:
  python genome/universal_evolver.py --mode all --quick
  python genome/universal_evolver.py --crypto BTCUSDT,ETHUSDT --mode gp,mape
"""

import argparse
import importlib.util
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
GENOME_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = GENOME_DIR.parent
DATA_DIR = GENOME_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = DATA_DIR / "universal_picks.json"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_log_dir = GENOME_DIR / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(str(_log_dir / "universal_evolver.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("UniversalEvolver")

# ---------------------------------------------------------------------------
# Direct module imports (bypass genome/__init__.py pandas issue)
# ---------------------------------------------------------------------------

def _load_module(name: str) -> Any:
    """Import a sibling module by filename, avoiding __init__.py."""
    path = str(GENOME_DIR / f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _try_load_module(name: str) -> Optional[Any]:
    try:
        return _load_module(name)
    except Exception as exc:
        logger.warning("Failed to import %s: %s", name, exc)
        return None


# ---------------------------------------------------------------------------
# Engine runners — each returns a list of pick dicts
# ---------------------------------------------------------------------------

def _run_gp(mod, symbols: List[str], quick: bool) -> List[Dict]:
    """Run Genetic Programming evolution and read back its picks file."""
    pop = 40 if quick else 60
    gens = 10 if quick else 15
    logger.info("GP: pop=%d gens=%d symbols=%s", pop, gens, symbols)
    mod.run_gp_evolution(symbols=symbols, population_size=pop, generations=gens)
    return _read_picks(PROJECT_ROOT / "genome" / "data" / "gp_active_picks.json", "gp")


def _run_mape(mod, symbols: List[str], quick: bool) -> List[Dict]:
    """Run MAP-Elites evolution and read back its picks file."""
    iters = 500 if quick else 3000
    initial = 50 if quick else 150
    logger.info("MAP-Elites: iterations=%d initial=%d symbols=%s", iters, initial, symbols)
    mod.run_mape_evolution(symbols=symbols, iterations=iters, initial_random=initial)
    return _read_picks(PROJECT_ROOT / "genome" / "data" / "mape_active_picks.json", "mape")


def _run_audit(mod, symbols: List[str], quick: bool) -> List[Dict]:
    """Run Audit Ensemble meta-evolution and read back its picks file."""
    pop = 30 if quick else 50
    gens = 10 if quick else 20
    logger.info("Audit Ensemble: pop=%d gens=%d symbols=%s", pop, gens, symbols)
    evolver = mod.AuditEnsembleEvolver(pop, gens, symbols)
    evolver.evolve()
    return _read_picks(PROJECT_ROOT / "genome" / "data" / "ae_active_picks.json", "audit_ensemble")


def _run_ensemble(mod, symbols: List[str], quick: bool) -> List[Dict]:
    """Run Ensemble Coevolution and read back its picks file."""
    pop = 20 if quick else 40
    gens = 8 if quick else 25
    logger.info("Ensemble Coevolution: pop=%d gens=%d symbols=%s", pop, gens, symbols)
    mod.run_ensemble_evolution(symbols=symbols, population_size=pop, generations=gens)
    return _read_picks(PROJECT_ROOT / "genome" / "data" / "ensemble_active_picks.json", "ensemble_coevolution")


def _read_picks(path: Path, engine_tag: str) -> List[Dict]:
    """Read a picks JSON file and tag each pick with its engine origin."""
    try:
        if not path.exists():
            logger.warning("Picks file not found: %s", path)
            return []
        data = json.loads(path.read_text())
        picks = data.get("picks", [])
        for p in picks:
            p.setdefault("engine", engine_tag)
        logger.info("Read %d picks from %s", len(picks), path.name)
        return picks
    except Exception as exc:
        logger.error("Error reading %s: %s", path, exc)
        return []


# ---------------------------------------------------------------------------
# Consensus detection
# ---------------------------------------------------------------------------

def _find_consensus(all_picks: List[Dict], min_engines: int = 2) -> List[Dict]:
    """
    Find symbols+directions agreed upon by >= min_engines different engines.
    Returns synthetic consensus picks with aggregated confidence.
    """
    # Group by (symbol, direction)
    groups: Dict[tuple, List[Dict]] = defaultdict(list)
    for p in all_picks:
        sym = p.get("symbol", "").upper()
        direction = p.get("direction", "LONG").upper()
        if sym:
            groups[(sym, direction)].append(p)

    consensus = []
    for (sym, direction), picks in groups.items():
        engines = set(p.get("engine", "unknown") for p in picks)
        if len(engines) >= min_engines:
            confidences = [float(p.get("confidence", 0.5)) for p in picks]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.5
            consensus.append({
                "symbol": sym,
                "direction": direction,
                "confidence": round(min(avg_conf * 1.1, 1.0), 4),
                "engines_agreeing": sorted(engines),
                "engine_count": len(engines),
                "strategy": f"Consensus_{len(engines)}x_{direction}",
                "source_system": "universal_evolver",
                "individual_picks": len(picks),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    consensus.sort(key=lambda c: (c["engine_count"], c["confidence"]), reverse=True)
    return consensus


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

ENGINE_REGISTRY = {
    "gp": ("genetic_programmer", _run_gp),
    "mape": ("mape_evolver", _run_mape),
    "audit": ("audit_ensemble_evolver", _run_audit),
    "ensemble": ("ensemble_evolver", _run_ensemble),
}


def run_universal_evolution(
    crypto: Optional[List[str]] = None,
    stocks: Optional[List[str]] = None,
    forex: Optional[List[str]] = None,
    mode: str = "all",
    quick: bool = False,
) -> Dict:
    """
    Run all (or selected) evolution engines and merge results.

    Returns unified picks dict saved to genome/data/universal_picks.json.
    """
    t0 = time.time()
    now = datetime.now(timezone.utc).isoformat()

    # Default crypto symbols
    symbols = crypto or ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOGEUSDT"]

    # Determine which engines to run
    if mode == "all":
        engines_to_run = list(ENGINE_REGISTRY.keys())
    else:
        engines_to_run = [e.strip() for e in mode.split(",")]

    logger.info("=" * 70)
    logger.info("UNIVERSAL EVOLUTION RUNNER")
    logger.info("Symbols : %s", symbols)
    logger.info("Engines : %s", engines_to_run)
    logger.info("Quick   : %s", quick)
    logger.info("=" * 70)

    # Extra asset classes (future expansion — warn if unavailable)
    if stocks:
        logger.info("Stocks requested: %s (future expansion — skipping for now)", stocks)
    if forex:
        logger.info("Forex requested: %s (future expansion — skipping for now)", forex)

    # Run each engine, collecting picks
    picks_by_engine: Dict[str, List[Dict]] = {}
    engines_run: List[str] = []
    engine_timings: Dict[str, float] = {}

    for engine_key in engines_to_run:
        if engine_key not in ENGINE_REGISTRY:
            logger.warning("Unknown engine '%s' — skipping", engine_key)
            continue

        module_name, runner_fn = ENGINE_REGISTRY[engine_key]
        logger.info("-" * 50)
        logger.info("Starting engine: %s", engine_key)
        et0 = time.time()

        try:
            mod = _try_load_module(module_name)
            if mod is None:
                logger.error("Could not load module for %s — skipping", engine_key)
                picks_by_engine[engine_key] = []
                continue

            picks = runner_fn(mod, symbols, quick)
            picks_by_engine[engine_key] = picks
            engines_run.append(engine_key)
            elapsed = time.time() - et0
            engine_timings[engine_key] = round(elapsed, 2)
            logger.info("Engine %s finished: %d picks in %.1fs", engine_key, len(picks), elapsed)

        except Exception as exc:
            elapsed = time.time() - et0
            engine_timings[engine_key] = round(elapsed, 2)
            logger.error("Engine %s FAILED after %.1fs: %s", engine_key, elapsed, exc, exc_info=True)
            picks_by_engine[engine_key] = []

    # Merge all picks
    all_picks = []
    for engine_key, picks in picks_by_engine.items():
        all_picks.extend(picks)

    # Find consensus
    consensus = _find_consensus(all_picks, min_engines=2)

    total_elapsed = round(time.time() - t0, 2)

    # Build output
    output = {
        "generated_at": now,
        "system": "universal_evolver",
        "version": "1.0.0",
        "elapsed_seconds": total_elapsed,
        "symbols": symbols,
        "quick_mode": quick,
        "engines_run": engines_run,
        "engine_timings": engine_timings,
        "total_picks": len(all_picks),
        "consensus_count": len(consensus),
        "picks_by_engine": {k: v for k, v in picks_by_engine.items()},
        "consensus_picks": consensus,
        "picks": all_picks,
    }

    # Feed hygiene: strip resolved/zero-entry picks before persisting
    try:
        import sys as _sys
        _sys.path.insert(0, str(PROJECT_ROOT))
        from alpha_engine.feed_hygiene import sanitize_active_picks
        raw_count = len(all_picks)
        all_picks = sanitize_active_picks(all_picks)
        consensus = sanitize_active_picks(consensus)
        output["picks"] = all_picks
        output["consensus_picks"] = consensus
        output["total_picks"] = len(all_picks)
        output["consensus_count"] = len(consensus)
        if raw_count != len(all_picks):
            logger.info("Feed hygiene: removed %d invalid picks", raw_count - len(all_picks))
    except Exception as _fh_exc:
        logger.warning("Feed hygiene unavailable: %s", _fh_exc)

    # Save
    with open(str(OUTPUT_PATH), "w") as f:
        json.dump(output, f, indent=2, default=str)

    logger.info("=" * 70)
    logger.info("UNIVERSAL EVOLUTION COMPLETE")
    logger.info("  Engines run    : %s", engines_run)
    logger.info("  Total picks    : %d", len(all_picks))
    logger.info("  Consensus picks: %d", len(consensus))
    logger.info("  Elapsed        : %.1fs", total_elapsed)
    logger.info("  Output         : %s", OUTPUT_PATH)
    logger.info("=" * 70)

    # Print consensus summary
    if consensus:
        print("\nCONSENSUS PICKS (2+ engines agree):")
        print("-" * 60)
        for c in consensus:
            print(f"  {c['symbol']:>10s} {c['direction']:>5s}  "
                  f"conf={c['confidence']:.3f}  "
                  f"engines={c['engine_count']}  "
                  f"({', '.join(c['engines_agreeing'])})")
        print("-" * 60)
    else:
        print("\nNo consensus picks found (no symbol+direction agreed by 2+ engines)")

    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Universal Evolution Runner — orchestrates all genome engines"
    )
    parser.add_argument(
        "--crypto", type=str,
        default="BTCUSDT,ETHUSDT,SOLUSDT,AVAXUSDT,DOGEUSDT",
        help="Comma-separated crypto symbols (default: BTC,ETH,SOL,AVAX,DOGE)",
    )
    parser.add_argument(
        "--stocks", type=str, default=None,
        help="Comma-separated stock symbols (future expansion, e.g. SPY,QQQ,AAPL)",
    )
    parser.add_argument(
        "--forex", type=str, default=None,
        help="Comma-separated forex pairs (future expansion, e.g. EURUSD,GBPUSD)",
    )
    parser.add_argument(
        "--mode", type=str, default="all",
        help="Engines to run: all | gp | mape | audit | ensemble | gp,mape (default: all)",
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Reduced iterations for fast testing",
    )
    args = parser.parse_args()

    crypto = [s.strip() for s in args.crypto.split(",")]
    stocks = [s.strip() for s in args.stocks.split(",")] if args.stocks else None
    forex = [s.strip() for s in args.forex.split(",")] if args.forex else None

    result = run_universal_evolution(
        crypto=crypto, stocks=stocks, forex=forex,
        mode=args.mode, quick=args.quick,
    )

    print(f"\nTotal picks: {result['total_picks']} | "
          f"Consensus: {result['consensus_count']} | "
          f"Time: {result['elapsed_seconds']}s")


if __name__ == "__main__":
    main()
