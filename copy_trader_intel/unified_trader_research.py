#!/usr/bin/env python3
"""
Unified Trader Research Runner
===============================
Deploys ALL copy trader scrapers across 8+ platforms in parallel,
consolidates picks, detects cross-platform consensus, and saves results.

Platforms scanned:
  CEX: OKX, Hyperliquid, Bitget, Bybit, BingX, Gate.io
  DEX: Copin.io (50+ protocols), dYdX v4, GMX v2

Usage:
    python copy_trader_intel/unified_trader_research.py           # Single run
    python copy_trader_intel/unified_trader_research.py --loop    # Escalating loop
"""

import json
import logging
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Ensure imports work
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "copy_trader_intel"))
sys.path.insert(0, str(ROOT / "alpha_engine"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("unified_trader_research")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

ALPHA_DATA = ROOT / "alpha_engine" / "data"
ALPHA_DATA.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Individual scraper runners (each returns list of pick dicts)
# ---------------------------------------------------------------------------

def run_okx() -> list:
    """OKX copy trading - existing scraper."""
    try:
        from okx_scraper import scan_okx_traders, save_okx_results
        profiles, picks = scan_okx_traders(max_traders=10)
        save_okx_results(profiles, picks)
        logger.info("OKX: %d picks from %d traders", len(picks), len(profiles))
        return picks
    except Exception as e:
        logger.error("OKX failed: %s", e)
        return []


def run_hyperliquid() -> list:
    """Hyperliquid - existing scraper."""
    try:
        from hyperliquid_scraper import run_full_scan
        qualified, picks = run_full_scan()
        logger.info("Hyperliquid: %d picks", len(picks))
        return picks
    except Exception as e:
        logger.error("Hyperliquid failed: %s", e)
        return []


def run_bitget() -> list:
    """Bitget - new scraper (web API + HTML fallback)."""
    try:
        sys.path.insert(0, str(ROOT / "alpha_engine"))
        from bitget_scraper import scan_bitget_traders
        picks = scan_bitget_traders()
        logger.info("Bitget: %d picks", len(picks))
        return picks
    except Exception as e:
        logger.error("Bitget failed: %s", e)
        traceback.print_exc()
        return []


def run_bybit() -> list:
    """Bybit - new scraper (beehive API)."""
    try:
        sys.path.insert(0, str(ROOT / "alpha_engine"))
        from bybit_scraper import scan_bybit_traders
        picks = scan_bybit_traders()
        logger.info("Bybit: %d picks", len(picks))
        return picks
    except Exception as e:
        logger.error("Bybit failed: %s", e)
        traceback.print_exc()
        return []


def run_bingx() -> list:
    """BingX - new scraper (frontend API + Copin fallback)."""
    try:
        sys.path.insert(0, str(ROOT / "alpha_engine"))
        from bingx_gateio_scrapers import scan_bingx_traders
        picks = scan_bingx_traders()
        logger.info("BingX: %d picks", len(picks))
        return picks
    except Exception as e:
        logger.error("BingX failed: %s", e)
        traceback.print_exc()
        return []


def run_gateio() -> list:
    """Gate.io - new scraper (SSR JSON + Copin fallback)."""
    try:
        sys.path.insert(0, str(ROOT / "alpha_engine"))
        from bingx_gateio_scrapers import scan_gateio_traders
        picks = scan_gateio_traders()
        logger.info("Gate.io: %d picks", len(picks))
        return picks
    except Exception as e:
        logger.error("Gate.io failed: %s", e)
        traceback.print_exc()
        return []


def run_dex_whales() -> list:
    """DEX whales - Copin.io + dYdX v4 + GMX v2."""
    try:
        sys.path.insert(0, str(ROOT / "copy_trader_intel"))
        from dex_whale_scrapers import DexWhaleScanner
        scanner = DexWhaleScanner()
        save_path = str(DATA_DIR / "dex_whale_picks.json")
        picks = scanner.scan_all(save_path=save_path)
        logger.info("DEX Whales: %d picks (Copin+dYdX+GMX)", len(picks))
        return picks
    except Exception as e:
        logger.error("DEX Whales failed: %s", e)
        traceback.print_exc()
        return []


def run_alpha_copy_trader() -> list:
    """Alpha Engine copy trader analyzer (OKX consensus)."""
    try:
        sys.path.insert(0, str(ROOT / "alpha_engine"))
        from copy_trader_analyzer import scan_copy_traders
        picks = scan_copy_traders()
        logger.info("Alpha CopyTrader: %d picks", len(picks))
        return picks
    except Exception as e:
        logger.error("Alpha CopyTrader failed: %s", e)
        return []


def run_alpha_hyperliquid() -> list:
    """Alpha Engine Hyperliquid trader analyzer."""
    try:
        sys.path.insert(0, str(ROOT / "alpha_engine"))
        from hyperliquid_traders import scan_hyperliquid_traders
        picks = scan_hyperliquid_traders()
        logger.info("Alpha HL Traders: %d picks", len(picks))
        return picks
    except Exception as e:
        logger.error("Alpha HL Traders failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Parallel execution + consensus detection
# ---------------------------------------------------------------------------

ALL_SCRAPERS = {
    "OKX": run_okx,
    "Hyperliquid": run_hyperliquid,
    "Bitget": run_bitget,
    "Bybit": run_bybit,
    "BingX": run_bingx,
    "Gate.io": run_gateio,
    "DEX_Whales": run_dex_whales,
    "Alpha_CopyTrader": run_alpha_copy_trader,
    "Alpha_HL": run_alpha_hyperliquid,
}


def deduplicate_and_consensus(all_picks: list) -> list:
    """
    Deduplicate picks by (symbol, direction).
    When multiple platforms agree:
      - Boost confidence by 0.05 per additional source (cap 0.95)
      - Track all contributing sources
      - Mark as cross-platform consensus
    """
    groups = {}
    for pick in all_picks:
        if not isinstance(pick, dict):
            continue
        symbol = pick.get("symbol", "")
        direction = pick.get("direction", pick.get("signal_type", "BUY"))
        if not symbol:
            continue

        # Normalize symbol
        symbol = symbol.upper().replace("-", "").replace("_", "")
        if not symbol.endswith("USDT") and not symbol.endswith("USD"):
            symbol += "USDT"

        key = f"{symbol}__{direction}"
        if key not in groups:
            groups[key] = []
        groups[key].append(pick)

    deduped = []
    consensus_count = 0

    for key, picks in groups.items():
        picks.sort(key=lambda p: p.get("confidence", 0), reverse=True)
        best = picks[0].copy()

        if len(picks) > 1:
            # Cross-platform consensus!
            consensus_count += 1
            n = len(picks)
            boost = min(0.20, (n - 1) * 0.05)
            orig = best.get("confidence", 0.5)
            best["confidence"] = round(min(0.95, orig + boost), 3)

            sources = set()
            trader_ids = []
            for p in picks:
                src = p.get("source", p.get("source_system", "unknown"))
                sources.add(src)
                tid = p.get("trader_id", p.get("trader_name", ""))
                if tid:
                    trader_ids.append(f"{src}:{tid}")

            best["cross_platform_consensus"] = True
            best["consensus_count"] = n
            best["consensus_sources"] = list(sources)
            best["consensus_traders"] = trader_ids[:10]
            best["reason"] = (
                f"CROSS-PLATFORM CONSENSUS ({n} sources: {', '.join(sources)}) | "
                + best.get("reason", "")
            )

        deduped.append(best)

    # Sort by confidence descending
    deduped.sort(key=lambda p: p.get("confidence", 0), reverse=True)

    if consensus_count:
        logger.info(
            "CONSENSUS: %d symbols confirmed across multiple platforms!",
            consensus_count,
        )

    return deduped


def run_all_scrapers(max_workers: int = 5) -> dict:
    """
    Run all scrapers in parallel, return summary dict.
    """
    start = time.time()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    print("\n" + "=" * 75)
    print("  UNIFIED TRADER RESEARCH - FULL SCAN")
    print(f"  {now_str}")
    print(f"  Platforms: {len(ALL_SCRAPERS)} | Parallel workers: {max_workers}")
    print("=" * 75)

    all_picks = []
    source_stats = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for name, func in ALL_SCRAPERS.items():
            future = executor.submit(func)
            futures[future] = name

        for future in as_completed(futures):
            name = futures[future]
            try:
                picks = future.result(timeout=120)
                all_picks.extend(picks)
                source_stats[name] = len(picks)
                status = "OK" if picks else "EMPTY"
                print(f"  [{status}] {name}: {len(picks)} picks")
            except Exception as e:
                source_stats[name] = 0
                print(f"  [FAIL] {name}: {e}")

    elapsed = time.time() - start

    # Deduplicate with consensus detection
    print(f"\n--- Deduplication & Consensus ---")
    print(f"  Raw picks: {len(all_picks)}")
    deduped = deduplicate_and_consensus(all_picks)
    print(f"  After dedup: {len(deduped)}")

    consensus_picks = [p for p in deduped if p.get("cross_platform_consensus")]
    if consensus_picks:
        print(f"\n  CROSS-PLATFORM CONSENSUS PICKS:")
        for p in consensus_picks[:15]:
            print(f"    {p['symbol']:12s} {p.get('direction','?'):4s}  "
                  f"conf={p['confidence']:.2f}  "
                  f"sources={p.get('consensus_sources', [])}")

    # Save consolidated results
    output = {
        "generated_at": now_str,
        "scan_duration_s": round(elapsed, 1),
        "platforms_scanned": len(ALL_SCRAPERS),
        "source_stats": source_stats,
        "total_raw": len(all_picks),
        "total_deduped": len(deduped),
        "consensus_picks": len(consensus_picks),
        "picks": deduped,
    }

    # Save to both data dirs
    for out_dir in [DATA_DIR, ALPHA_DATA]:
        out_path = out_dir / "unified_trader_research.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)

    # Also update copy_trader_intel/data/active_picks.json
    active_path = DATA_DIR / "active_picks.json"
    with open(active_path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, default=str)

    print(f"\n{'=' * 75}")
    print(f"  SCAN COMPLETE in {elapsed:.1f}s")
    print(f"  Total picks: {len(deduped)} ({len(consensus_picks)} cross-platform consensus)")
    for name, count in sorted(source_stats.items(), key=lambda x: -x[1]):
        print(f"    {name}: {count}")
    print(f"  Saved to: {DATA_DIR / 'unified_trader_research.json'}")
    print(f"{'=' * 75}\n")

    return output


# ---------------------------------------------------------------------------
# Escalating interval loop
# ---------------------------------------------------------------------------

def escalating_loop():
    """
    Run the scanner on an escalating schedule:
      - First hour: every 3 minutes
      - Next period: every 5 minutes
      - Then: every 7 minutes
      - Then slowly increasing by 2 min each hour
    """
    start_time = time.time()
    run_count = 0
    current_interval = 3 * 60  # Start at 3 min (seconds)

    # Schedule: (duration_minutes, interval_minutes)
    SCHEDULE = [
        (60, 3),    # First 60 min: every 3 min
        (60, 5),    # Next 60 min: every 5 min
        (60, 7),    # Next 60 min: every 7 min
        (60, 9),    # Next 60 min: every 9 min
        (60, 11),   # Next 60 min: every 11 min
        (60, 13),   # Next 60 min: every 13 min
        (9999, 15), # After that: every 15 min forever
    ]

    def get_interval():
        elapsed_min = (time.time() - start_time) / 60
        cumulative = 0
        for duration, interval in SCHEDULE:
            cumulative += duration
            if elapsed_min < cumulative:
                return interval * 60  # Return seconds
        return 15 * 60  # Default 15 min

    print("\n" + "#" * 75)
    print("  UNIFIED TRADER RESEARCH - ESCALATING LOOP STARTED")
    print("  Schedule: 3min (1h) -> 5min (1h) -> 7min (1h) -> +2min/hour")
    print(f"  Started: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")
    print("#" * 75 + "\n")

    try:
        while True:
            run_count += 1
            elapsed = (time.time() - start_time) / 60
            interval_sec = get_interval()

            logger.info(
                "=== RUN #%d | Elapsed: %.0fmin | Next interval: %ds ===",
                run_count, elapsed, interval_sec,
            )

            try:
                result = run_all_scrapers(max_workers=5)
                total = result.get("total_deduped", 0)
                consensus = result.get("consensus_picks", 0)
                logger.info(
                    "Run #%d complete: %d picks (%d consensus)",
                    run_count, total, consensus,
                )
            except Exception as e:
                logger.error("Run #%d failed: %s", run_count, e)
                traceback.print_exc()

            logger.info("Sleeping %d seconds until next scan...", interval_sec)
            time.sleep(interval_sec)

    except KeyboardInterrupt:
        elapsed = (time.time() - start_time) / 60
        print(f"\n\nLoop stopped after {run_count} runs ({elapsed:.0f} min)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--loop" in sys.argv:
        escalating_loop()
    else:
        run_all_scrapers()
