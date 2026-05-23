#!/usr/bin/env python3
"""
Copy Trader Intelligence - Main Scanner (v2.1)
===============================================
Runs ALL exchange scrapers (OKX, Hyperliquid, Bitget, Bybit, BingX, DEX, Drift),
deduplicates picks by symbol (boosting confidence on consensus),
and saves consolidated active_picks.json.

Supported sources:
  - OKX copy trading (public API)
  - Hyperliquid on-chain (public API)
  - Bitget copy trading (public API)
  - Bybit copy trading (public/web API)
  - BingX copy trading (public/web API + REST)
  - Gate.io copy trading (web frontend API)
  - DEX on-chain (Copin.io, dYdX v4, GMX v2)
  - Drift Protocol (Solana perp DEX via DLOB)

Usage:
    python copy_trader_intel/main.py              # Run all scrapers
    python copy_trader_intel/main.py --okx-only   # OKX only
    python copy_trader_intel/main.py --hl-only    # Hyperliquid only
    python copy_trader_intel/main.py --cex-only   # All CEX (OKX+Bitget+Bybit+BingX)
    python copy_trader_intel/main.py --dex-only   # All DEX (Copin+dYdX+GMX+Drift)
    python copy_trader_intel/main.py --myfxbook-only  # Myfxbook only
    python copy_trader_intel/main.py --fast        # Quick scan (top 5 per source)
    python copy_trader_intel/main.py --learn       # Run strategy learning engine after scan
    python copy_trader_intel/main.py --variations  # Force variation forward tester (auto when not --fast)
"""

import json
import sys
import os
import time
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows charmap encoding — force UTF-8 stdout/stderr
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

# Ensure parent dir is on path for imports
sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

try:
    from alpha_engine.feed_hygiene import sanitize_active_picks
except ImportError:
    sanitize_active_picks = lambda picks, label="": picks  # graceful fallback


def run_okx_scraper() -> list:
    """Run OKX copy trader scraper, return list of picks."""
    try:
        from okx_scraper import scan_okx_traders, save_okx_results
        profiles, picks = scan_okx_traders(max_traders=10)
        save_okx_results(profiles, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] OKX scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_hyperliquid_scraper() -> list:
    """Run Hyperliquid copy trader scraper, return list of picks."""
    try:
        from hyperliquid_scraper import run_full_scan
        qualified, picks = run_full_scan()
        return picks
    except Exception as e:
        print(f"  [ERROR] Hyperliquid scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_polymarket_scraper() -> list:
    """Run Polymarket wallet-intel scraper, return list of picks."""
    try:
        from polymarket_scraper import scan_polymarket_traders, save_polymarket_results
        profiles, picks = scan_polymarket_traders()
        save_polymarket_results(profiles, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] Polymarket scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_bitget_scraper() -> list:
    """Run Bitget copy trader scraper, return list of picks."""
    try:
        from bitget_scraper import scan_bitget_traders, save_bitget_results
        profiles, picks = scan_bitget_traders(max_traders=10)
        save_bitget_results(profiles, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] Bitget scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_bybit_scraper() -> list:
    """Run Bybit copy trader scraper, return list of picks."""
    try:
        from bybit_scraper import scan_bybit_traders, save_bybit_results
        profiles, picks = scan_bybit_traders(max_traders=10)
        save_bybit_results(profiles, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] Bybit scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_bingx_scraper() -> list:
    """Run BingX copy trader scraper, return list of picks."""
    try:
        from bingx_scraper import scan_bingx_traders, save_bingx_results
        profiles, picks = scan_bingx_traders(max_traders=10)
        save_bingx_results(profiles, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] BingX scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_gate_scraper() -> list:
    """Run Gate.io copy trader scraper, return list of picks."""
    try:
        from gate_scraper import scan_gate_traders, save_gate_results
        profiles, picks = scan_gate_traders(max_traders=15)
        save_gate_results(profiles, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] Gate.io scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_dex_scraper() -> list:
    """Run DEX on-chain trader scraper (Copin, dYdX, GMX)."""
    try:
        from dex_scraper import scan_all_dex
        profiles, picks = scan_all_dex(max_per_source=10)
        return picks
    except Exception as e:
        print(f"  [ERROR] DEX scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_gmx_scraper() -> list:
    """Run GMX v2 standalone scraper (Subsquid GraphQL + REST)."""
    try:
        from gmx_scraper import scan_gmx, save_gmx_results
        profiles, picks = scan_gmx()
        save_gmx_results(profiles, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] GMX scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_drift_scraper() -> list:
    """Run Drift Protocol (Solana) DLOB scraper."""
    try:
        from drift_scraper import scan_drift_traders, save_drift_results
        profiles, picks = scan_drift_traders(max_traders=15)
        save_drift_results(profiles, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] Drift scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_binance_scraper() -> list:
    """Run Binance futures smart money scraper, return list of picks."""
    try:
        from binance_scraper import scan_binance_traders, save_binance_results
        profiles, picks = scan_binance_traders(max_symbols=30)
        save_binance_results(profiles, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] Binance scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_multi_asset_bridge() -> list:
    """Run Multi-Asset Bridge (Forex, CTA, DNA Clones, High-Quality institutional sources)."""
    try:
        # Avoid circular imports or missing files if not in correct dir
        from multi_asset_bridge import load_multi_asset_picks, load_cta_picks, load_dna_clone_picks
        picks = []
        picks.extend(load_multi_asset_picks() or [])
        picks.extend(load_cta_picks() or [])
        picks.extend(load_dna_clone_picks() or [])
        return picks
    except Exception as e:
        print(f"  [ERROR] Multi-asset bridge failed (check multi_asset_bridge.py): {e}")
        return []


def run_coinglass_scraper() -> list:
    """Run CoinGlass top trader sentiment scraper, return list of picks."""
    try:
        from coinglass_scraper import scan_coinglass, save_coinglass_results
        profiles, picks = scan_coinglass()
        save_coinglass_results(profiles, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] CoinGlass scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_okx_futures_scraper() -> list:
    """Run OKX Futures Leaderboard sentiment scraper, return list of picks."""
    try:
        from okx_futures_scraper import scan_okx_futures, save_okx_futures_results
        analyses, picks = scan_okx_futures()
        save_okx_futures_results(analyses, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] OKX Futures scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_htx_scraper() -> list:
    """Run HTX (Huobi) Elite Trader sentiment scraper, return list of picks."""
    try:
        from htx_scraper import scan_htx_elite, save_htx_results
        analyses, picks = scan_htx_elite()
        save_htx_results(analyses, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] HTX scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_dune_scraper() -> list:
    """Run Dune Analytics on-chain trader intelligence scraper, return list of picks."""
    try:
        from dune_scraper import scan_dune, save_dune_results
        data, picks = scan_dune()
        save_dune_results(data, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] Dune Analytics scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_nansen_scraper() -> list:
    """Run Nansen Smart Money token screener, return list of picks."""
    try:
        from nansen_scraper import scan_nansen, save_nansen_results
        profiles, picks = scan_nansen(max_tokens=50)
        save_nansen_results(profiles, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] Nansen scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_zulutrade_scraper() -> list:
    """Run ZuluTrade forex copy trading scraper, return list of picks."""
    try:
        from zulutrade_scraper import scan_zulutrade_traders, save_zulutrade_results
        profiles, picks = scan_zulutrade_traders(max_traders=20)
        save_zulutrade_results(profiles, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] ZuluTrade scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_etoro_scraper() -> list:
    """Run eToro Popular Investor scraper (forex + crypto), return list of picks."""
    try:
        from etoro_scraper import scan_etoro_traders, save_etoro_results
        profiles, picks = scan_etoro_traders(max_traders=20)
        save_etoro_results(profiles, picks)
        return picks
    except Exception as e:
        print(f"  [ERROR] eToro scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_myfxbook_scraper() -> list:
    """Run Myfxbook AutoTrade + community sentiment scraper, return list of picks."""
    try:
        from myfxbook_scraper import scan_myfxbook, save_myfxbook_results
        profiles, picks, status = scan_myfxbook(max_systems=15)
        save_myfxbook_results(profiles, picks, status)
        if status.get("diagnostic_code") != "ok":
            print(
                "  [INFO] Myfxbook status:"
                f" {status.get('diagnostic_code')} "
                f"(auth={status.get('auth_status')}, "
                f"outlook={status.get('outlook_source')})"
            )
        return picks
    except Exception as e:
        print(f"  [ERROR] Myfxbook scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def deduplicate_picks(all_picks: list) -> list:
    """
    Deduplicate picks by symbol+direction.
    When multiple traders have the same symbol+direction:
    - Boost confidence by 0.05 per additional trader (capped at 0.95)
    - Keep the pick with the highest original confidence
    - Track all contributing traders
    """
    # Group by symbol+direction
    groups = {}
    for pick in all_picks:
        if not isinstance(pick, dict):
            continue
        symbol = pick.get("symbol", "")
        direction = pick.get("direction", pick.get("signal_type", ""))
        key = f"{symbol}__{direction}"

        if key not in groups:
            groups[key] = []
        groups[key].append(pick)

    deduped = []
    consensus_boosts = 0

    for key, picks in groups.items():
        if len(picks) == 1:
            deduped.append(picks[0])
            continue

        # Multiple traders agree on this symbol+direction
        picks.sort(key=lambda p: p.get("confidence", 0), reverse=True)
        best = picks[0].copy()

        # Boost confidence for consensus
        num_traders = len(picks)
        boost = min(0.20, (num_traders - 1) * 0.05)
        original_conf = best.get("confidence", 0.5)
        best["confidence"] = round(min(0.95, original_conf + boost), 3)
        best["ml_score"] = None  # FIX: ml_score must come from real ML, not confidence

        # Track consensus info
        sources = []
        for p in picks:
            src = p.get("source_system", "unknown")
            name = p.get("trader_name", p.get("strategy", ""))
            sources.append(f"{src}:{name}")

        best["consensus_count"] = num_traders
        best["consensus_sources"] = sources
        best["cross_exchange_consensus"] = len(set(
            p.get("source_system", "").split("_")[-1] for p in picks
        )) > 1  # True if multiple exchanges agree
        best["reason"] = (f"CONSENSUS ({num_traders} traders, "
                          f"{len(set(p.get('source_system','') for p in picks))} sources) | " +
                          best.get("reason", ""))

        deduped.append(best)
        consensus_boosts += 1

    if consensus_boosts > 0:
        print(f"  Consensus: {consensus_boosts} symbols confirmed by multiple traders")

    return deduped


def save_consolidated_picks(picks: list):
    """Save final consolidated picks to active_picks.json."""
    now_iso = datetime.now(timezone.utc).isoformat()

    picks = sanitize_active_picks(picks, "copy_trader_consolidated")

    output_path = DATA_DIR / "active_picks.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)

    # Also save a metadata file
    meta_path = DATA_DIR / "scan_metadata.json"
    source_counts = {}
    for p in picks:
        src = p.get("source_system", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    consensus_picks = [p for p in picks if p.get("consensus_count", 1) > 1]
    cross_exchange = [p for p in picks if p.get("cross_exchange_consensus")]

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "total_picks": len(picks),
            "source_breakdown": source_counts,
            "consensus_picks": len(consensus_picks),
            "cross_exchange_consensus_picks": len(cross_exchange),
            "symbols": sorted(set(p.get("symbol", "") for p in picks)),
            "sources_active": sorted(source_counts.keys()),
        }, f, indent=2)

    print(f"  Saved {len(picks)} consolidated picks to {output_path}")
    return output_path


def main():
    """Run all scrapers, deduplicate, save consolidated picks."""
    print("=" * 70)
    print("  COPY TRADER INTELLIGENCE v2.1 - MULTI-EXCHANGE SCANNER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Sources: OKX | OKX-Futures | Hyperliquid | Polymarket | Bitget | Bybit | BingX | Gate.io | Binance | HTX | Nansen | DEX | GMX | Drift | CoinGlass | Dune | ZuluTrade | eToro | Myfxbook")
    print("=" * 70)

    # Parse flags
    args = set(sys.argv[1:])
    okx_only = "--okx-only" in args
    hl_only = "--hl-only" in args
    cex_only = "--cex-only" in args
    dex_only = "--dex-only" in args
    myfxbook_only = "--myfxbook-only" in args
    fast = "--fast" in args
    learn = "--learn" in args
    variations = "--variations" in args

    all_picks = []
    scraper_results = {}

    # -- CEX Scrapers --
    if not dex_only and not myfxbook_only:
        # OKX
        if not hl_only:
            print("\n--- OKX Copy Trading ---")
            okx_picks = run_okx_scraper()
            all_picks.extend(okx_picks)
            scraper_results["OKX"] = len(okx_picks)
            print(f"  OKX: {len(okx_picks)} picks")

        # Hyperliquid
        if not okx_only:
            print("\n--- Hyperliquid ---")
            hl_picks = run_hyperliquid_scraper()
            all_picks.extend(hl_picks)
            scraper_results["Hyperliquid"] = len(hl_picks)
            print(f"  Hyperliquid: {len(hl_picks)} picks")

        if not okx_only and not hl_only and not cex_only and not dex_only:
            print("\n--- Polymarket Wallet Intelligence ---")
            pm_picks = run_polymarket_scraper()
            all_picks.extend(pm_picks)
            scraper_results["Polymarket"] = len(pm_picks)
            print(f"  Polymarket: {len(pm_picks)} picks")

        # Bitget (new)
        if not okx_only and not hl_only:
            print("\n--- Bitget Copy Trading ---")
            bg_picks = run_bitget_scraper()
            all_picks.extend(bg_picks)
            scraper_results["Bitget"] = len(bg_picks)
            print(f"  Bitget: {len(bg_picks)} picks")

        # Bybit (new)
        if not okx_only and not hl_only:
            print("\n--- Bybit Copy Trading ---")
            bb_picks = run_bybit_scraper()
            all_picks.extend(bb_picks)
            scraper_results["Bybit"] = len(bb_picks)
            print(f"  Bybit: {len(bb_picks)} picks")

        # BingX (new)
        if not okx_only and not hl_only:
            print("\n--- BingX Copy Trading ---")
            bx_picks = run_bingx_scraper()
            all_picks.extend(bx_picks)
            scraper_results["BingX"] = len(bx_picks)
            print(f"  BingX: {len(bx_picks)} picks")

        # Gate.io (new)
        if not okx_only and not hl_only:
            print("\n--- Gate.io Copy Trading ---")
            gate_picks = run_gate_scraper()
            all_picks.extend(gate_picks)
            scraper_results["Gate.io"] = len(gate_picks)
            print(f"  Gate.io: {len(gate_picks)} picks")

        # Binance Futures Smart Money
        if not okx_only and not hl_only:
            print("\n--- Binance Futures Smart Money ---")
            bn_picks = run_binance_scraper()
            all_picks.extend(bn_picks)
            scraper_results["Binance"] = len(bn_picks)
            print(f"  Binance: {len(bn_picks)} picks")

    # -- DEX Scrapers --
    if not cex_only and not okx_only and not hl_only and not myfxbook_only:
        print("\n--- DEX On-Chain (Copin + dYdX + GMX) ---")
        dex_picks = run_dex_scraper()
        all_picks.extend(dex_picks)
        scraper_results["DEX"] = len(dex_picks)
        print(f"  DEX: {len(dex_picks)} picks")

    # -- GMX v2 Standalone (Subsquid GraphQL) --
    if not cex_only and not okx_only and not hl_only and not myfxbook_only:
        print("\n--- GMX v2 (Arbitrum) ---")
        gmx_picks = run_gmx_scraper()
        all_picks.extend(gmx_picks)
        scraper_results["GMX"] = len(gmx_picks)
        print(f"  GMX: {len(gmx_picks)} picks")

    # -- Drift Protocol (Solana) --
    if not cex_only and not okx_only and not hl_only and not myfxbook_only:
        print("\n--- Drift Protocol (Solana) ---")
        drift_picks = run_drift_scraper()
        all_picks.extend(drift_picks)
        scraper_results["Drift"] = len(drift_picks)
        print(f"  Drift: {len(drift_picks)} picks")

    # -- OKX Futures Leaderboard Sentiment --
    if not okx_only and not hl_only and not myfxbook_only:
        print("\n--- OKX Futures Leaderboard Sentiment ---")
        okxf_picks = run_okx_futures_scraper()
        all_picks.extend(okxf_picks)
        scraper_results["OKX-Futures"] = len(okxf_picks)
        print(f"  OKX-Futures: {len(okxf_picks)} picks")

    # -- HTX Elite Trader Sentiment --
    if not okx_only and not hl_only and not myfxbook_only:
        print("\n--- HTX (Huobi) Elite Sentiment ---")
        htx_picks = run_htx_scraper()
        all_picks.extend(htx_picks)
        scraper_results["HTX"] = len(htx_picks)
        print(f"  HTX: {len(htx_picks)} picks")

    # -- Nansen Smart Money --
    if not okx_only and not hl_only and not myfxbook_only:
        print("\n--- Nansen Smart Money ---")
        nansen_picks = run_nansen_scraper()
        all_picks.extend(nansen_picks)
        scraper_results["Nansen"] = len(nansen_picks)
        print(f"  Nansen: {len(nansen_picks)} picks")

    # -- CoinGlass Sentiment --
    if not okx_only and not hl_only and not myfxbook_only:
        print("\n--- CoinGlass Top Trader Sentiment ---")
        cg_picks = run_coinglass_scraper()
        all_picks.extend(cg_picks)
        scraper_results["CoinGlass"] = len(cg_picks)
        print(f"  CoinGlass: {len(cg_picks)} picks")

    # -- Dune Analytics On-Chain Intelligence --
    if not okx_only and not hl_only and not myfxbook_only:
        print("\n--- Dune Analytics On-Chain Intelligence ---")
        dune_picks = run_dune_scraper()
        all_picks.extend(dune_picks)
        scraper_results["Dune"] = len(dune_picks)
        print(f"  Dune: {len(dune_picks)} picks")

    # -- Forex: ZuluTrade copy traders --
    if not okx_only and not hl_only and not cex_only and not dex_only and not myfxbook_only:
        print("\n--- ZuluTrade Forex Copy Trading ---")
        zt_picks = run_zulutrade_scraper()
        all_picks.extend(zt_picks)
        scraper_results["ZuluTrade"] = len(zt_picks)
        print(f"  ZuluTrade: {len(zt_picks)} picks")

        # CME Futures Bridge: feed live futures-agent scanner output into the
        # non-crypto consensus engine (it reads futures_copytrader_picks.json).
        # Wrapped — a bridge failure must log but never abort the scan run.
        print("\n--- CME Futures Bridge (live scanner -> consensus) ---")
        try:
            from cme_futures_bridge import bridge_futures_picks
            _bridged_futures = bridge_futures_picks()
            scraper_results["CME-Futures-Bridge"] = len(_bridged_futures)
            print(f"  CME Futures Bridge: {len(_bridged_futures)} picks bridged")
        except Exception as e:
            print(f"  [WARN] CME Futures Bridge failed (continuing without): {e}")

        # Multi-Asset Bridge: Forex, Commodity, Equity from institutional-style models
        print("\n--- Multi-Asset Bridge (Forex/Futures) ---")
        mab_picks = run_multi_asset_bridge()
        all_picks.extend(mab_picks)
        scraper_results["MultiAsset-MAB"] = len(mab_picks)
        print(f"  Multi-Asset MAB: {len(mab_picks)} picks (ELITE tier)")

    # -- Forex/Crypto: eToro Popular Investors --
    if not okx_only and not hl_only and not cex_only and not dex_only and not myfxbook_only:
        print("\n--- eToro Popular Investors ---")
        et_picks = run_etoro_scraper()
        all_picks.extend(et_picks)
        scraper_results["eToro"] = len(et_picks)
        print(f"  eToro: {len(et_picks)} picks")
        
        # GP-9: Generate Myfxbook-compatible output for OlivierDanvel (eToro Elite PI)
        try:
            from olivierdanvel_wrapper import save_myfxbook_format_picks
            print("  [GP-9] Generating Myfxbook-compatible OlivierDanvel picks...")
            wrapper_result = save_myfxbook_format_picks()
            print(f"  [GP-9] OlivierDanvel wrapper: {wrapper_result['count']} picks (platform: {wrapper_result['actual_platform']})")
            # Load and append his picks explicitly as myfxbook proxy
            wrapper_file = Path(__file__).parent / "data" / "myfxbook_olivierdanvel_picks.json"
            if wrapper_file.exists():
                import json
                with open(wrapper_file, 'r', encoding='utf-8') as wf:
                    olivier_picks = json.load(wf)
                    all_picks.extend(olivier_picks)
                    print(f"  [GP-9] Merged {len(olivier_picks)} OlivierDanvel picks into all_picks pool")
        except Exception as e:
            print(f"  [GP-9] Wrapper failed (non-critical): {e}")

    # -- Forex: Myfxbook AutoTrade + sentiment --
    if myfxbook_only or (not okx_only and not hl_only and not cex_only and not dex_only):
        print("\n--- Myfxbook AutoTrade & Sentiment ---")
        mfx_picks = run_myfxbook_scraper()
        all_picks.extend(mfx_picks)
        scraper_results["Myfxbook"] = len(mfx_picks)
        print(f"  Myfxbook: {len(mfx_picks)} picks")

    # Lightweight fast-path for source-local refreshes.
    # Myfxbook picks already ship with complete TP/SL, confidence, and metadata,
    # so the generic copy-trader post-processing adds latency without improving
    # this feed. Save immediately so downstream consumers can refresh from disk.
    if myfxbook_only:
        if not all_picks:
            print("\n  [WARN] No Myfxbook picks generated")
            save_consolidated_picks([])
            return []
        deduped = deduplicate_picks(all_picks)
        save_consolidated_picks(deduped)
        print(f"  [MYFXBOOK-ONLY] Saved {len(deduped)} refreshed Myfxbook picks")
        return deduped

    if not all_picks:
        print("\n  [WARN] No picks generated from any scraper")
        # Fallback: merge from per-exchange picks files instead of overwriting with []
        # This preserves pick data when API failures (bans/credits/schema changes) cause
        # scrapers to return 0 but per-exchange files still hold recent valid picks.
        fallback_picks = []
        per_exchange_files = [
            "bitget_picks.json", "bybit_picks.json", "okx_picks.json",
            "binance_picks.json", "htx_picks.json", "coinglass_picks.json",
            "polymarket_picks.json", "dune_picks.json", "gmx_picks.json",
            "dex_picks.json", "forex_copytrader_picks.json",
            "commodity_copytrader_picks.json", "stocks_copytrader_picks.json",
            "okx_futures_picks.json",
        ]
        for fname in per_exchange_files:
            fpath = DATA_DIR / fname
            if fpath.exists():
                try:
                    with open(fpath, encoding="utf-8") as f:
                        fallback_picks.extend(json.load(f) or [])
                except Exception:
                    continue
        if fallback_picks:
            print(f"  [FALLBACK] Preserving {len(fallback_picks)} picks from per-exchange files")
            save_consolidated_picks(fallback_picks)
            return fallback_picks
        # Only write empty if literally no per-exchange files have data
        print("  [WARN] No per-exchange fallback available - writing empty")
        save_consolidated_picks([])
        return []

    # --- Fix -1: Record original_trader_entry on every copy pick ---
    # Enables drift analysis: how much did our entry differ from the trader's actual entry?
    # Some scrapers already set original_trader_entry (e.g., hyperliquid). For others,
    # entry_price IS the trader's entry (extracted from position openPrice/avgPx).
    _drift_tagged = 0
    for pick in all_picks:
        if not isinstance(pick, dict):
            continue
        # Skip if already set (e.g., by hyperliquid_scraper)
        if pick.get("original_trader_entry") is not None:
            _drift_tagged += 1
            continue
        # For most scrapers, entry_price comes from the trader's position (openPrice/avgPx/entryPrice)
        # Store it as original_trader_entry for consistency
        original_entry = pick.get("entry_price")
        if original_entry and float(original_entry) > 0:
            pick["original_trader_entry"] = float(original_entry)
            # trader_entry_time from open_time (set by most scrapers)
            pick["trader_entry_time"] = pick.get("open_time") or pick.get("created_at") or pick.get("timestamp")
            # entry_drift_pct will be meaningful after TP/SL filler re-prices entry
            # For now, drift is 0 since entry_price == original_trader_entry
            pick["entry_drift_pct"] = 0.0
            _drift_tagged += 1
    if _drift_tagged:
        print(f"  [DRIFT] Tagged {_drift_tagged}/{len(all_picks)} picks with original_trader_entry")

    # --- Fix -0.5: Replace entry_price with CURRENT market price ---
    # The trader's entry price is historical — by the time our 30-min scanner
    # detects the position, the price has already moved. Use the current Binance
    # spot price as our entry_price (the price we'd actually get if we copied now).
    # The trader's original entry is preserved as original_trader_entry.
    print(f"\n--- Market Price Entry Correction ---")
    try:
        from market_price import replace_entry_with_market_price
        _market_replaced = 0
        _market_failed = 0
        for pick in all_picks:
            if not isinstance(pick, dict):
                continue
            # Only replace for NEW picks (status=OPEN, no exit yet)
            if pick.get("status", "OPEN") != "OPEN":
                continue
            if pick.get("exit_price") is not None:
                continue
            # Only for crypto picks (forex/equity use different price sources)
            category = pick.get("category", "crypto").lower()
            if category not in ("crypto", "cryptocurrency"):
                continue
            old_entry = pick.get("entry_price", 0)
            replace_entry_with_market_price(pick)
            if pick.get("entry_price_source") == "market":
                _market_replaced += 1
                new_entry = pick.get("entry_price", 0)
                deviation = pick.get("trader_entry_deviation_pct", 0)
                if deviation > 1.0:
                    print(f"  [REPRICED] {pick.get('symbol','')}: "
                          f"trader ${old_entry:.4f} -> market ${new_entry:.4f} "
                          f"({deviation:.1f}% drift)")
            elif pick.get("entry_price_source") == "trader_fallback":
                _market_failed += 1
        print(f"  Market price applied to {_market_replaced} crypto picks "
              f"({_market_failed} fallbacks to trader entry)")
    except Exception as _mp_err:
        print(f"  [WARN] Market price correction failed (using trader entries): {_mp_err}")
        import traceback
        traceback.print_exc()

    # --- Fix 0: Propagate trader stats from qualified_traders.json + trader_profiles.json ---
    # Tag picks with median_hold_hours, avg_loss, win_rate, total_trades so MM filter works
    # v2.2: Also reject traders with median_hold < 4h at qualification stage
    try:
        trader_stats_map = {}
        _hft_traders_rejected = 0

        # Load from both qualified_traders.json AND trader_profiles.json
        # (some picks come from traders not in qualified list)
        for stats_file, key in [
            (DATA_DIR / "qualified_traders.json", "traders"),
            (DATA_DIR / "trader_profiles.json", "profiles"),
        ]:
            if stats_file.exists():
                with open(stats_file, encoding="utf-8") as _sf:
                    _sdata = json.load(_sf)
                _traders = _sdata.get(key, []) if isinstance(_sdata, dict) else _sdata
                for t in _traders:
                    addr = t.get("address", "")
                    label = t.get("label", "")

                    # v2.2: Reject HFT/scalper traders at qualification stage
                    # Traders with median hold < 4h cannot be replicated at our scan interval
                    _mhh = t.get("median_hold_hours")
                    if _mhh is not None and float(_mhh) < 4.0:
                        _hft_traders_rejected += 1
                        t["qualified"] = False
                        t["disqualify_reason"] = f"HFT/scalper: median_hold={float(_mhh):.2f}h < 4h minimum"
                        # Still add to stats map so the HFT filter can cross-reference
                        # and reject their picks downstream

                    stats = {
                        "median_hold_hours": t.get("median_hold_hours"),
                        "avg_loss": t.get("avg_loss"),
                        "win_rate": t.get("win_rate"),
                        "total_trades": t.get("total_trades"),
                    }
                    # Only add if we have at least one useful field
                    if any(v is not None for v in stats.values()):
                        if addr:
                            trader_stats_map.setdefault(addr.lower(), stats)
                        if label:
                            trader_stats_map.setdefault(label.lower(), stats)

        if _hft_traders_rejected:
            print(f"  [HFT-QUALIFY] Disqualified {_hft_traders_rejected} traders with median_hold < 4h")

            # Persist disqualification back to qualified_traders.json
            try:
                _qt_path = DATA_DIR / "qualified_traders.json"
                if _qt_path.exists():
                    with open(_qt_path, encoding="utf-8") as _qf:
                        _qt_data = json.load(_qf)
                    _qt_list = _qt_data.get("traders", []) if isinstance(_qt_data, dict) else _qt_data
                    _updated = False
                    for _t in _qt_list:
                        _mhh = _t.get("median_hold_hours")
                        if _mhh is not None and float(_mhh) < 4.0:
                            _t["qualified"] = False
                            _t["disqualify_reason"] = f"HFT/scalper: median_hold={float(_mhh):.2f}h < 4h minimum"
                            _updated = True
                    if _updated:
                        if isinstance(_qt_data, dict):
                            _qt_data["traders"] = _qt_list
                            _qt_data["hft_disqualified_count"] = sum(
                                1 for _t in _qt_list if not _t.get("qualified", True))
                        with open(_qt_path, "w", encoding="utf-8") as _qf:
                            json.dump(_qt_data, _qf, indent=2)
                        print(f"  [HFT-QUALIFY] Updated qualified_traders.json — HFT traders marked disqualified")
            except Exception as _persist_err:
                print(f"  [WARN] Could not persist disqualification to qualified_traders.json: {_persist_err}")
            # Tag picks with trader stats for the MM filter
            tagged_count = 0
            for pick in all_picks:
                if not isinstance(pick, dict):
                    continue
                trader_addr = (pick.get("trader_address", "") or "").lower()
                trader_nm = (pick.get("trader_name", "") or "").lower()
                # Also try extracting trader name from strategy field (e.g. "clone_hl_copy_whale_433roi")
                strategy = pick.get("strategy", "")
                strategy_trader = ""
                for prefix in ["clone_hl_copy_", "copy_hl_", "clone_"]:
                    if strategy.startswith(prefix):
                        strategy_trader = strategy[len(prefix):].lower()
                        break
                stats = (trader_stats_map.get(trader_addr) or
                         trader_stats_map.get(trader_nm) or
                         trader_stats_map.get(strategy_trader))
                if stats is None:
                    continue
                changed = False
                if pick.get("avg_hold_hours") is None and pick.get("trader_avg_hold_hours") is None:
                    mhh = stats.get("median_hold_hours")
                    if mhh is not None:
                        pick["avg_hold_hours"] = float(mhh)
                        changed = True
                if pick.get("trader_avg_loss") is None:
                    al = stats.get("avg_loss")
                    if al is not None:
                        pick["trader_avg_loss"] = float(al)
                        changed = True
                if pick.get("trader_win_rate") is None and pick.get("clone_expected_wr") is None:
                    wr = stats.get("win_rate")
                    if wr is not None:
                        pick["trader_win_rate"] = float(wr)
                        changed = True
                if pick.get("trader_total_trades") is None and pick.get("forward_trades") is None:
                    tt = stats.get("total_trades")
                    if tt is not None:
                        pick["trader_total_trades"] = int(tt)
                        changed = True
                if changed:
                    tagged_count += 1
            if tagged_count:
                print(f"  [STATS-TAG] Tagged {tagged_count} picks with trader stats from qualified_traders.json")
    except Exception as _qt_err:
        print(f"  [WARN] Could not load qualified_traders.json for trader stats tagging: {_qt_err}")

    # --- Fix 1: Filter out HFT / market-maker traders from directional cloning ---
    # Market makers profit from bid-ask spreads in sub-minute trades.
    # Their edge does NOT transfer to copy trading (we hold days, they hold seconds).
    # v2.2: Also cross-reference qualified_traders.json median_hold_hours for each
    # trader — the per-pick avg_hold_hours is often None (trader_entry_time missing),
    # so we must check the trader profile directly.
    print(f"\n--- Market-Maker / HFT Filter (v2.2 — trader profile cross-ref) ---")

    # Build trader hold-time lookup from qualified_traders.json
    _hft_hold_lookup = {}
    try:
        _qt_path = DATA_DIR / "qualified_traders.json"
        if _qt_path.exists():
            with open(_qt_path, encoding="utf-8") as _qf:
                _qt_data = json.load(_qf)
            _qt_traders = _qt_data.get("traders", []) if isinstance(_qt_data, dict) else _qt_data
            for _t in _qt_traders:
                _mhh = _t.get("median_hold_hours")
                if _mhh is not None:
                    _addr = (_t.get("address", "") or "").lower()
                    _label = (_t.get("label", "") or "").lower()
                    if _addr:
                        _hft_hold_lookup[_addr] = float(_mhh)
                    if _label:
                        _hft_hold_lookup[_label] = float(_mhh)
    except Exception as _hft_err:
        print(f"  [WARN] Could not load qualified_traders.json for HFT lookup: {_hft_err}")

    MIN_HOLD_HOURS = 4.0  # Minimum median hold time — our scan interval is 15-30 min

    pre_hft = len(all_picks)
    filtered_picks = []
    for pick in all_picks:
        if not isinstance(pick, dict):
            continue
        trader_wr = pick.get("trader_win_rate", pick.get("clone_expected_wr", 0))
        trader_trades = pick.get("trader_total_trades", pick.get("forward_trades", 0))
        avg_hold = pick.get("trader_avg_hold_hours", pick.get("avg_hold_hours", None))
        avg_loss = pick.get("trader_avg_loss", None)

        trader_name = pick.get('trader_name', pick.get('strategy', 'unknown'))
        trader_addr = (pick.get("trader_address", "") or "").lower()
        trader_nm = (pick.get("trader_name", "") or "").lower()

        # Cross-reference trader profile median_hold_hours if per-pick value is missing
        if avg_hold is None:
            # Try address, then name, then strategy-extracted name
            profile_hold = _hft_hold_lookup.get(trader_addr) or _hft_hold_lookup.get(trader_nm)
            if profile_hold is None:
                strategy = pick.get("strategy", "")
                for prefix in ["clone_hl_copy_", "copy_hl_", "clone_"]:
                    if strategy.startswith(prefix):
                        _strat_name = strategy[len(prefix):].lower()
                        profile_hold = _hft_hold_lookup.get(_strat_name)
                        break
            if profile_hold is not None:
                avg_hold = profile_hold
                pick["avg_hold_hours"] = profile_hold  # Tag for downstream filters

        # HARD REJECT 1: Median/avg hold time < 4 hours = HFT/scalper
        # (was < 1h — raised to 4h because our 15-30 min scan interval cannot
        #  replicate entries of traders who hold < 4 hours)
        if avg_hold is not None and avg_hold < MIN_HOLD_HOURS:
            print(f"  [HFT-REJECT] {pick.get('symbol','')} from {trader_name}: "
                  f"avg_hold={avg_hold:.2f}h < {MIN_HOLD_HOURS}h (HFT/scalper — unreplicable at our scan interval)")
            continue

        # HARD REJECT 2: WR >= 99% AND > 50 trades = market maker pattern
        if trader_wr is not None and trader_trades is not None:
            if float(trader_wr) >= 0.99 and int(trader_trades) > 50:
                print(f"  [MM-REJECT] {pick.get('symbol','')} from {trader_name}: "
                      f"WR={float(trader_wr):.1%} + {trader_trades} trades (market maker pattern)")
                continue

        # HARD REJECT 3: avg_loss == 0 AND > 20 trades = hiding unrealized losses
        if avg_loss is not None and trader_trades is not None:
            if float(avg_loss) == 0 and int(trader_trades) > 20:
                print(f"  [MM-REJECT] {pick.get('symbol','')} from {trader_name}: "
                      f"avg_loss=0 + {trader_trades} trades (never takes a loss = hiding unrealized)")
                continue

        filtered_picks.append(pick)
    all_picks = filtered_picks
    hft_removed = pre_hft - len(all_picks)
    if hft_removed:
        print(f"  MM/HFT filter: removed {hft_removed} picks from market-maker/HFT/scalper traders")
    else:
        print(f"  MM/HFT filter: all {len(all_picks)} picks passed")

    # --- PROVEN TRADER CAPITAL CONCENTRATION ---
    # After the fake trader purge, only 2 traders survive with verified track records.
    # Boost their picks' confidence to route ~90%+ of allocation to them,
    # while heavily penalizing (but not blocking) unproven traders.
    PROVEN_TRADERS = {
        "NMTD_25M": {
            "win_rate": 0.777,
            "total_trades": 1117,
            "median_hold_hours": 8.5,
            "address": "0xf517639a8872e756ac98d3c65507d2ebc25cc032",
            "boost": 1.3,
        },
        "whale_1225roi": {
            "win_rate": 0.655,
            "total_trades": 476,
            "median_hold_hours": 3.01,
            "address": "0xad8be12a452b5b8f9ad9883f6e8e67536627db4b",
            "boost": 1.3,
        },
        "OlivierDanvel": {
            "win_rate": 0.65,
            "total_trades": 500,
            "median_hold_hours": 24.0,
            "address": "",
            "boost": 1.4,
        },
    }
    # Build fast lookup sets (lowercase) for matching
    _proven_names = {name.lower() for name in PROVEN_TRADERS}
    _proven_addrs = {v["address"].lower() for v in PROVEN_TRADERS.values() if v.get("address")}

    def _is_proven_trader(pick: dict) -> str:
        """Return proven trader name if pick is from a proven trader, else empty string."""
        trader_name = (pick.get("trader_name", "") or "").lower()
        trader_addr = (pick.get("trader_address", "") or "").lower()
        strategy = (pick.get("strategy", "") or "").lower()
        # Direct name match
        for name in _proven_names:
            if name in trader_name or name in strategy:
                return name
        # Address match
        if trader_addr in _proven_addrs:
            for pname, pdata in PROVEN_TRADERS.items():
                if pdata.get("address", "").lower() == trader_addr:
                    return pname.lower()
        return ""

    print(f"\n--- Proven Trader Capital Concentration ---")
    PROVEN_BOOST = 1.3     # 30% confidence boost for proven traders (capped at 0.95)
    UNPROVEN_PENALTY = 0.5  # 50% confidence penalty for unproven traders
    _proven_boosted = 0
    _proven_names_seen = set()
    _unproven_penalized = 0

    for pick in all_picks:
        if not isinstance(pick, dict):
            continue
        proven_name = _is_proven_trader(pick)
        if proven_name:
            old_conf = pick.get("confidence", 0.5)
            new_conf = round(min(0.95, old_conf * PROVEN_BOOST), 4)
            pick["confidence"] = new_conf
            pick["proven_trader"] = True
            pick["proven_trader_name"] = proven_name
            pick["_conf_reason"] = (pick.get("_conf_reason", "") +
                                    f" | PROVEN_TRADER boost {old_conf:.3f} -> {new_conf:.3f}")
            _proven_boosted += 1
            _proven_names_seen.add(proven_name)
        else:
            cat = pick.get("category", pick.get("asset_class", "")).lower()
            if cat in ("forex", "fx"):
                old_conf = pick.get("confidence", 0.5)
                # Forex copy traders are verified by default in this domain
                new_conf = round(min(0.95, old_conf * 1.2), 4) # 20% boost
                pick["confidence"] = new_conf
                pick["proven_trader"] = True
                pick["_conf_reason"] = (pick.get("_conf_reason", "") +
                                        f" | FOREX_TRADER boost {old_conf:.3f} -> {new_conf:.3f}")
            else:
                # Penalize unproven traders — they still have a path to prove themselves
                old_conf = pick.get("confidence", 0.5)
                new_conf = round(old_conf * UNPROVEN_PENALTY, 4)
                pick["confidence"] = new_conf
                pick["proven_trader"] = False
                pick["_conf_reason"] = (pick.get("_conf_reason", "") +
                                        f" | UNPROVEN penalty {old_conf:.3f} -> {new_conf:.3f}")
                _unproven_penalized += 1

    print(f"  [PROVEN_TRADER] Boosted {_proven_boosted} picks from "
          f"{len(_proven_names_seen)} proven traders, "
          f"penalized {_unproven_penalized} from unproven")
    if _proven_names_seen:
        print(f"  [PROVEN_TRADER] Proven traders active: {', '.join(sorted(_proven_names_seen))}")

    # --- Fix 2: Score copy trader picks based on per-symbol performance ---
    print(f"\n--- Per-Symbol Confidence Scoring ---")
    rescored = 0
    for pick in all_picks:
        if not isinstance(pick, dict):
            continue
        # Only apply to copy trader picks that have flat 0.95 or near-max confidence
        source = pick.get("source_system", "")
        if "copy_trader" not in source and "clone_" not in pick.get("strategy", ""):
            continue

        trader_wr = pick.get("trader_win_rate", pick.get("clone_expected_wr", None))
        symbol_wr = pick.get("trader_symbol_wr", None)
        symbol_pnl = pick.get("trader_symbol_pnl", None)

        old_conf = pick.get("confidence", 0.5)

        if symbol_wr is not None:
            # Trader has history on this specific symbol
            if symbol_pnl is not None and symbol_pnl < 0:
                # Losing on this symbol -- cap at 0.55
                new_conf = min(0.55, old_conf)
                pick["confidence"] = round(new_conf, 3)
                pick["ml_score"] = None  # FIX: ml_score must come from real ML, not confidence
                pick["_conf_reason"] = f"trader losing on this symbol (WR={symbol_wr:.0%}, PnL={symbol_pnl:.2f})"
                rescored += 1
            else:
                # Profitable on this symbol -- use formula, allow up to 0.90
                new_conf = min(0.90, 0.60 + float(symbol_wr) * 0.30)
                pick["confidence"] = round(new_conf, 3)
                pick["ml_score"] = None  # FIX: ml_score must come from real ML, not confidence
                pick["_conf_reason"] = f"per-symbol scoring (WR={symbol_wr:.0%})"
                rescored += 1
        elif trader_wr is not None:
            # No per-symbol data -- cap at 0.70
            new_conf = min(0.70, old_conf)
            if new_conf != old_conf:
                pick["confidence"] = round(new_conf, 3)
                pick["ml_score"] = None  # FIX: ml_score must come from real ML, not confidence
                pick["_conf_reason"] = "no per-symbol history, capped at 0.70"
                rescored += 1
    # Safety net: cap copy trader picks by proven status.
    # Proven traders (NMTD_25M, whale_1225roi) get higher cap — they earned it.
    # Unproven traders get the original 0.60 cap (was already the rule).
    PROVEN_COPY_TRADER_CONF_CAP = 0.85   # Proven traders: higher cap to preserve boost
    UNPROVEN_COPY_TRADER_CONF_CAP = 0.60  # Unproven: original conservative cap
    safety_capped = 0
    for pick in all_picks:
        if not isinstance(pick, dict):
            continue
        source = pick.get("source_system", "")
        if "copy_trader" not in source and "clone_" not in pick.get("strategy", ""):
            continue
        is_proven = pick.get("proven_trader", False)
        cap = PROVEN_COPY_TRADER_CONF_CAP if is_proven else UNPROVEN_COPY_TRADER_CONF_CAP
        old_conf = pick.get("confidence", 0)
        if old_conf > cap:
            pick["confidence"] = cap
            pick["ml_score"] = None  # Must come from real ML
            pick["_conf_reason"] = (pick.get("_conf_reason", "") +
                                    f" | hard-capped from {old_conf:.3f} to {cap} "
                                    f"({'proven' if is_proven else 'unproven'})")
            safety_capped += 1
    if safety_capped:
        rescored += safety_capped
        print(f"  Safety net: capped {safety_capped} copy trader picks "
              f"(proven cap={PROVEN_COPY_TRADER_CONF_CAP}, unproven cap={UNPROVEN_COPY_TRADER_CONF_CAP})")

    if rescored:
        print(f"  Re-scored {rescored} copy trader picks based on per-symbol performance")
    else:
        print(f"  No copy trader picks needed re-scoring")

    # Deduplicate
    print(f"\n--- Deduplication ---")
    print(f"  Raw picks: {len(all_picks)}")
    deduped = deduplicate_picks(all_picks)
    print(f"  After dedup: {len(deduped)}")

    # Enrich with market context (funding, OI, fear/greed, DVOL, L/S ratios, RSI, volume)
    try:
        from enrichment_pipeline import run_enrichment
        print(f"\n--- Market Context Enrichment ---")
        deduped = run_enrichment(deduped)
    except Exception as e:
        print(f"  [WARN] Enrichment failed (picks saved without context): {e}")

    # --- Meta-Consensus Scorer: re-rank picks by ML meta-score ---
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "alpha_engine"))
        from meta_consensus_scorer import score_picks as meta_score_picks
        deduped = meta_score_picks(deduped, gate=0.55, retrain=True)
    except Exception as e:
        print(f"  [WARN] Meta-consensus scorer failed (continuing without): {e}")
        import traceback
        traceback.print_exc()

    # --- Fix 3: Block conflicting positions (LONG vs SHORT on same symbol) ---
    print(f"\n--- Conflict Resolution ---")
    sym_picks = {}
    for p in deduped:
        sym = p.get("symbol", "")
        sym_picks.setdefault(sym, []).append(p)

    resolved = []
    conflicts_found = 0
    for sym, group in sym_picks.items():
        if len(group) <= 1:
            resolved.extend(group)
            continue
        # Check for direction conflict
        directions = {}
        for p in group:
            d = (p.get("direction", p.get("signal_type", "LONG"))).upper()
            if d in ("SELL", "SHORT"):
                d = "SHORT"
            else:
                d = "LONG"
            directions.setdefault(d, []).append(p)

        if len(directions) > 1:
            # Conflict: LONG + SHORT on same symbol -- keep highest confidence
            all_conflicting = []
            for d_group in directions.values():
                all_conflicting.extend(d_group)
            all_conflicting.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            winner = all_conflicting[0]
            w_dir = (winner.get("direction", winner.get("signal_type", "LONG"))).upper()
            for loser in all_conflicting[1:]:
                l_dir = (loser.get("direction", loser.get("signal_type", "LONG"))).upper()
                l_strat = loser.get("strategy", loser.get("trader_name", "unknown"))
                w_strat = winner.get("strategy", winner.get("trader_name", "unknown"))
                if l_dir != w_dir:
                    print(f"  Conflict detected: {w_strat} {w_dir} vs {l_strat} {l_dir} on {sym} "
                          f"-- keeping {w_strat} (conf={winner.get('confidence', 0):.2f})")
                    conflicts_found += 1
            resolved.append(winner)
        else:
            resolved.extend(group)

    deduped = resolved
    if conflicts_found:
        print(f"  Resolved {conflicts_found} LONG/SHORT conflicts")
    else:
        print(f"  No directional conflicts found")

    # --- Fix 4: Reject stale position copies (entry price drift > 10%) ---
    # NOTE: entry_price is now the CURRENT MARKET price (our actual entry).
    # original_trader_entry is the trader's historical entry.
    # We reject picks where the trader's entry has drifted >10% from current
    # market price -- meaning the position has moved too far to safely copy.
    print(f"\n--- Stale Position Filter ---")
    pre_stale = len(deduped)
    fresh_picks = []
    for p in deduped:
        our_entry = p.get("entry_price", 0)
        trader_entry = p.get("original_trader_entry",
                        p.get("trader_entry_price",
                        p.get("original_entry_price", None)))

        # Handle position_is_stale boolean flag (from hyperliquid_scraper)
        if p.get("position_is_stale", False) and trader_entry:
            trader_entry_val = float(trader_entry)
            our_entry_val = float(our_entry) if our_entry else 0
            if trader_entry_val > 0 and our_entry_val > 0:
                drift = abs(our_entry_val - trader_entry_val) / trader_entry_val
                if drift > 0.10:
                    print(f"  Stale+drifted rejected: {p.get('symbol','')} flagged stale, "
                          f"market ${our_entry_val:.4f} vs trader ${trader_entry_val:.4f} "
                          f"(drift {drift * 100:.1f}%)")
                    continue

        # Reject if trader's entry has drifted >10% from current market price
        if our_entry and trader_entry and float(trader_entry) > 0:
            diff_pct = abs(float(our_entry) - float(trader_entry)) / float(trader_entry) * 100
            if diff_pct > 10.0:
                print(f"  Stale position rejected: {p.get('symbol','')} market ${float(our_entry):.4f} vs "
                      f"trader ${float(trader_entry):.4f} ({diff_pct:.1f}% drift -- too late to copy)")
                continue
        # Update entry_drift_pct now that we have both prices
        if our_entry and p.get("original_trader_entry"):
            orig = float(p["original_trader_entry"])
            if orig > 0:
                p["entry_drift_pct"] = round(abs(float(our_entry) - orig) / orig * 100, 3)
        fresh_picks.append(p)
    stale_removed = pre_stale - len(fresh_picks)
    deduped = fresh_picks
    if stale_removed:
        print(f"  Removed {stale_removed} stale position copies (entry drift > 10%)")
    else:
        print(f"  All picks are fresh (no stale positions)")

    # --- Fix 4b: Mark/reject stale active picks (>24h old) ---
    # Copy trader picks with timestamp > 24 hours old are stale — the trader
    # has likely already exited. Mark them and remove from active pool.
    STALE_HOURS = 24
    print(f"\n--- Stale Age Filter (>{STALE_HOURS}h old) ---")
    now_utc = datetime.now(timezone.utc)
    pre_stale_age = len(deduped)
    non_stale_picks = []
    stale_count = 0
    for p in deduped:
        if not isinstance(p, dict):
            continue
        ts_str = p.get("timestamp") or p.get("generated_at") or p.get("entry_date")
        if ts_str:
            try:
                pick_time = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
                age_hours = (now_utc - pick_time).total_seconds() / 3600
                if age_hours > STALE_HOURS:
                    p["status"] = "STALE"
                    p["stale_reason"] = f"pick is {age_hours:.1f}h old (>{STALE_HOURS}h limit)"
                    stale_count += 1
                    print(f"  [STALE] {p.get('symbol','')} from {p.get('source_system','')}: "
                          f"{age_hours:.1f}h old — removed from active pool")
                    continue
            except (ValueError, TypeError):
                pass  # Unparseable timestamp, keep the pick
        non_stale_picks.append(p)
    deduped = non_stale_picks
    if stale_count:
        print(f"  Stale age filter: removed {stale_count} picks older than {STALE_HOURS}h")
    else:
        print(f"  Stale age filter: all {len(deduped)} picks are fresh")

    # --- Whale TP/SL widening (Mercury sprint) ---
    # Whale positions on Hyperliquid use 10-40x leverage, 2-3% SL trips on noise.
    # Widen TP/SL to 8%/4% for copy_hl_* and clone_hl_* strategies.
    _whale_widened = 0
    for p in deduped:
        if not isinstance(p, dict):
            continue
        strategy = p.get("strategy", "")
        if "copy_hl" in strategy or "clone_hl" in strategy:
            entry = float(p.get("entry_price", 0) or 0)
            if entry <= 0:
                continue
            direction = str(p.get("direction", p.get("signal_type", "LONG"))).upper()
            tp_pct = 0.08  # 8% TP
            sl_pct = 0.04  # 4% SL
            if direction in ("LONG", "BUY"):
                p["take_profit"] = round(entry * (1 + tp_pct), 8)
                p["stop_loss"] = round(entry * (1 - sl_pct), 8)
            else:
                p["take_profit"] = round(entry * (1 - tp_pct), 8)
                p["stop_loss"] = round(entry * (1 + sl_pct), 8)
            _whale_widened += 1
    if _whale_widened:
        print(f"  [WHALE TP/SL] Widened TP/SL to 8%/4% for {_whale_widened} whale copy picks")

    # Quality gate: filter out picks with adjusted confidence < 0.55
    pre_gate_count = len(deduped)
    deduped = [p for p in deduped if p.get("confidence", 0.5) >= 0.55]
    removed = pre_gate_count - len(deduped)
    if removed > 0:
        print(f"  Quality gate: removed {removed} low-confidence picks (confidence < 0.55)")
    else:
        print(f"  Quality gate: all {len(deduped)} picks passed (confidence >= 0.55)")

    # --- DATA-DRIVEN QUALITY FILTERS (from 884 closed trade analysis) ---
    print(f"\n--- Data-Driven Quality Filters (884 trade analysis) ---")
    pre_quality = len(deduped)
    quality_filtered = []
    quality_reasons = {"low_score": 0, "weak_short": 0, "bad_hour": 0, "high_rsi": 0, "vol_spike": 0}

    current_hour_utc = datetime.now(timezone.utc).hour
    BAD_HOURS = {8, 9, 10, 11, 12, 13}  # 9-19% WR

    for p in deduped:
        if not isinstance(p, dict):
            continue

        # Compute score from various possible fields
        score = float(p.get("elite_score", p.get("score", p.get("confidence", 0) * 100)) or 0)
        direction = str(p.get("direction", p.get("signal_type", "LONG"))).upper()

        # Filter 1: Minimum score 60 for active_picks (portfolio tracker applies 80 gate)
        if score < 60:
            quality_reasons["low_score"] += 1
            continue

        # Filter 2: Shorts need higher score (shorts have 13.8% WR overall)
        if direction in ("SHORT", "SELL") and score < 75:
            quality_reasons["weak_short"] += 1
            continue

        # Filter 3: Bad hours — 08:00-13:00 UTC (9-19% WR)
        if current_hour_utc in BAD_HOURS:
            # Don't hard-block at this level (scrapers run on schedule),
            # but tag the pick so portfolio tracker can filter
            p["_bad_hour_entry"] = True

        # Filter 4: RSI > 70 for LONG entries (7.9% WR)
        enrichment = p.get("enrichment", {})
        rsi_data = enrichment.get("rsi", {})
        rsi = rsi_data.get("rsi_14_1h", None)
        if rsi is not None and direction in ("LONG", "BUY") and float(rsi) > 70:
            quality_reasons["high_rsi"] += 1
            continue

        # Filter 5: Volume spike > 5x (11% WR for extreme spikes)
        vol_ratio = enrichment.get("volume_ratio", enrichment.get("vol_ratio", None))
        if vol_ratio is not None and float(vol_ratio) > 5.0:
            quality_reasons["vol_spike"] += 1
            continue

        quality_filtered.append(p)

    quality_removed = pre_quality - len(quality_filtered)
    deduped = quality_filtered
    if quality_removed > 0:
        reason_str = ", ".join(f"{k}={v}" for k, v in quality_reasons.items() if v > 0)
        print(f"  [QUALITY] Removed {quality_removed} low-quality picks ({reason_str})")
        print(f"  [QUALITY] {len(deduped)} picks remaining after data-driven filters")
    else:
        print(f"  [QUALITY] All {len(deduped)} picks passed data-driven quality filters")

    # Record to audit trail SQLite DB for historical enrichment analysis + ML training
    try:
        _audit_root = str(Path(__file__).parent.parent)
        if _audit_root not in sys.path:
            sys.path.insert(0, _audit_root)
        from audit_trail.recorder import start_run, record_raw_pick as _record_pick, finish_run
        _run_id = start_run()
        _recorded = 0
        for _p in deduped:
            _src = _p.get("source_system") or _p.get("strategy") or "copy_trader"
            if _record_pick(_src, _p, _run_id):
                _recorded += 1
        _consensus_ct = sum(1 for _p in deduped if _p.get("consensus_count", 1) > 1)
        finish_run(_run_id, consensus_count=_consensus_ct, systems_loaded=len(scraper_results), raw_count=_recorded)
        print(f"  [AUDIT] {_recorded}/{len(deduped)} picks recorded to SQLite audit trail (run={_run_id[:8]})")
    except Exception as _e:
        print(f"  [WARN] Audit trail recording failed (non-fatal): {_e}")

    # Stamp regime_at_entry on all picks from HMM regime data
    try:
        _hmm_path = Path(__file__).parent.parent / "alpha_engine" / "data" / "hmm_regime.json"
        if _hmm_path.exists():
            with open(_hmm_path, encoding="utf-8") as _hf:
                _hmm = json.load(_hf)
            _regime_label = (_hmm.get("aggregate", {}).get("market_regime") or "UNKNOWN").upper()
            _regime_ts = _hmm.get("generated_at", "")
            for _p in deduped:
                if not _p.get("regime_at_entry"):
                    _p["regime_at_entry"] = _regime_label
                    _p["regime_timestamp"] = _regime_ts
            print(f"  [REGIME] Stamped {len(deduped)} picks with regime_at_entry={_regime_label}")
    except Exception as _re:
        print(f"  [WARN] Regime stamping failed: {_re}")

    # --- Fix 5: Velocity filter — reject picks where alpha already captured (chasing) ---
    try:
        import urllib.request
        import ssl

        print(f"\n--- Velocity Filter (anti-chase) ---")
        _ssl_ctx = ssl.create_default_context()
        _ssl_ctx.check_hostname = False
        _ssl_ctx.verify_mode = ssl.CERT_NONE

        _BINANCE_MIRRORS = [
            "https://data-api.binance.vision",
            "https://api.binance.com",
            "https://api1.binance.com",
            "https://api2.binance.com",
            "https://api3.binance.com",
        ]

        def _fetch_live_price(symbol: str) -> float:
            """Fetch live price from Binance with 5-mirror failover."""
            # Normalize symbol for Binance (e.g., BTC/USDT -> BTCUSDT)
            bn_sym = symbol.upper().replace("/", "").replace("-", "")
            if not bn_sym.endswith("USDT") and not bn_sym.endswith("BUSD"):
                bn_sym = bn_sym + "USDT" if "USD" not in bn_sym else bn_sym
            for mirror in _BINANCE_MIRRORS:
                try:
                    url = f"{mirror}/api/v3/ticker/price?symbol={bn_sym}"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=5, context=_ssl_ctx) as resp:
                        data = json.loads(resp.read().decode())
                        return float(data.get("price", 0))
                except Exception:
                    continue
            return 0.0

        # Batch fetch: collect unique symbols
        _symbols_needed = set()
        for _p in deduped:
            if isinstance(_p, dict) and _p.get("entry_price"):
                _symbols_needed.add(_p.get("symbol", ""))

        _live_prices = {}
        for _sym in _symbols_needed:
            if _sym:
                _price = _fetch_live_price(_sym)
                if _price > 0:
                    _live_prices[_sym] = _price

        _velocity_filtered = []
        _velocity_skipped = 0
        for _p in deduped:
            if not isinstance(_p, dict):
                _velocity_filtered.append(_p)
                continue
            _sym = _p.get("symbol", "")
            _entry = float(_p.get("entry_price", 0) or 0)
            _live = _live_prices.get(_sym, 0)
            if _entry > 0 and _live > 0:
                _gap = abs(_live - _entry) / _entry * 100
                if _gap > 3.0:
                    print(f"  [VELOCITY] Skipping {_sym} — entry {_entry:.6g} vs live {_live:.6g} = {_gap:.2f}% gap (chasing)")
                    _velocity_skipped += 1
                    continue
            _velocity_filtered.append(_p)

        if _velocity_skipped:
            print(f"  [VELOCITY] Removed {_velocity_skipped} picks where alpha already captured (>3% gap)")
        else:
            print(f"  [VELOCITY] All {len(deduped)} picks within 3% of live price")
        deduped = _velocity_filtered
    except Exception as _vel_err:
        print(f"  [WARN] Velocity filter failed (non-fatal, keeping all picks): {_vel_err}")

    # --- Fix 6: ATR-based TP/SL widening — prevent shakeout on tight stops ---
    try:
        print(f"\n--- ATR Stop Widening ---")

        def _fetch_klines(symbol: str, interval: str = "1h", limit: int = 50) -> list:
            """Fetch klines from Binance with 5-mirror failover."""
            bn_sym = symbol.upper().replace("/", "").replace("-", "")
            if not bn_sym.endswith("USDT") and not bn_sym.endswith("BUSD"):
                bn_sym = bn_sym + "USDT" if "USD" not in bn_sym else bn_sym
            for mirror in _BINANCE_MIRRORS:
                try:
                    url = f"{mirror}/api/v3/klines?symbol={bn_sym}&interval={interval}&limit={limit}"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=8, context=_ssl_ctx) as resp:
                        return json.loads(resp.read().decode())
                except Exception:
                    continue
            return []

        def _compute_atr_pct(klines: list, period: int = 14) -> float:
            """Compute ATR(14) as percentage of current price from klines."""
            if len(klines) < period + 1:
                return 0.0
            trs = []
            for i in range(1, len(klines)):
                high = float(klines[i][2])
                low = float(klines[i][3])
                prev_close = float(klines[i - 1][4])
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                trs.append(tr)
            if len(trs) < period:
                return 0.0
            # Simple moving average ATR
            atr = sum(trs[-period:]) / period
            current_price = float(klines[-1][4])
            if current_price <= 0:
                return 0.0
            return (atr / current_price) * 100  # as percentage

        _atr_widened = 0
        for _p in deduped:
            if not isinstance(_p, dict):
                continue
            _entry = float(_p.get("entry_price", 0) or 0)
            if _entry <= 0:
                continue
            _tp = float(_p.get("take_profit", 0) or 0)
            _sl = float(_p.get("stop_loss", 0) or 0)
            if _tp <= 0 or _sl <= 0:
                continue

            _direction = str(_p.get("direction", _p.get("signal_type", "LONG"))).upper()
            _is_long = _direction in ("LONG", "BUY")

            # Calculate current SL distance as percentage
            if _is_long:
                _sl_dist = (_entry - _sl) / _entry * 100
                _tp_dist = (_tp - _entry) / _entry * 100
            else:
                _sl_dist = (_sl - _entry) / _entry * 100
                _tp_dist = (_entry - _tp) / _entry * 100

            # Only widen if SL < 2%
            if _sl_dist >= 2.0:
                continue

            _sym = _p.get("symbol", "")
            _klines = _fetch_klines(_sym)
            _atr_pct = _compute_atr_pct(_klines) if _klines else 0.0

            _old_sl_dist = _sl_dist
            _old_tp_dist = _tp_dist

            _new_sl_dist = max(_sl_dist, 2.0 * _atr_pct, 2.5)
            _new_tp_dist = max(_tp_dist, 2.5 * _atr_pct, 3.5)

            # Recalculate prices
            if _is_long:
                _p["stop_loss"] = round(_entry * (1 - _new_sl_dist / 100), 8)
                _p["take_profit"] = round(_entry * (1 + _new_tp_dist / 100), 8)
            else:
                _p["stop_loss"] = round(_entry * (1 + _new_sl_dist / 100), 8)
                _p["take_profit"] = round(_entry * (1 - _new_tp_dist / 100), 8)

            print(f"  [ATR_STOPS] {_sym} SL widened from {_old_sl_dist:.2f}% to {_new_sl_dist:.2f}%, "
                  f"TP from {_old_tp_dist:.2f}% to {_new_tp_dist:.2f}% (ATR={_atr_pct:.2f}%)")
            _atr_widened += 1

        if _atr_widened:
            print(f"  [ATR_STOPS] Widened {_atr_widened} picks with SL < 2%")
        else:
            print(f"  [ATR_STOPS] No picks needed SL widening (all >= 2%)")
    except Exception as _atr_err:
        print(f"  [WARN] ATR stop widening failed (non-fatal, keeping original TP/SL): {_atr_err}")

    # --- Fix 7: Ensure copy trader pick metadata is correct for scoring ---
    print(f"\n--- Copy Trader Metadata Fix ---")
    _meta_fixed = 0
    for _p in deduped:
        if not isinstance(_p, dict):
            continue
        _strategy = _p.get("strategy", "")
        _source = _p.get("source_system", "")
        _is_ct = ("copy_hl" in _strategy or "clone_hl" in _strategy
                  or "copy_okx" in _strategy or "copy_trader" in _source
                  or "clone_" in _strategy)
        if not _is_ct:
            continue
        _changed = False
        # Ensure source_system is set
        if not _source:
            _p["source_system"] = "copy_trader_intel"
            _changed = True
        # Ensure asset_class is set
        if not _p.get("asset_class"):
            _p["asset_class"] = "CRYPTO"
            _changed = True
        # Cap confidence to prevent deflation bypass
        _conf = _p.get("confidence", 0.5)
        if _conf < 0.60:
            _p["confidence"] = min(0.60, _conf)  # floor at current if below 0.60
        # Ensure strategy prefix
        if _strategy and not _strategy.startswith(("copy_hl_", "clone_hl_", "copy_okx_", "copy_bg_",
                                                    "copy_bb_", "copy_bx_", "copy_gate_", "copy_bn_")):
            if "hyperliquid" in _source.lower() or "hl" in _source.lower():
                _p["strategy"] = f"copy_hl_{_strategy}"
            elif not _strategy.startswith("clone_"):
                _p["strategy"] = f"clone_hl_{_strategy}"
            _changed = True
        if _changed:
            _meta_fixed += 1
    if _meta_fixed:
        print(f"  [META] Fixed metadata on {_meta_fixed} copy trader picks (source_system, asset_class, strategy prefix)")
    else:
        print(f"  [META] All copy trader picks have correct metadata")

    # Save
    save_consolidated_picks(deduped)

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  SCAN COMPLETE - COPY TRADER INTELLIGENCE v2.0")
    print(f"  Total picks: {len(deduped)}")
    for src, count in sorted(scraper_results.items()):
        status = "OK" if count > 0 else "EMPTY"
        print(f"    {src}: {count} picks [{status}]")
    consensus = sum(1 for p in deduped if p.get("consensus_count", 1) > 1)
    cross_ex = sum(1 for p in deduped if p.get("cross_exchange_consensus"))
    if consensus:
        print(f"    Multi-trader consensus: {consensus} picks")
    if cross_ex:
        print(f"    Cross-exchange consensus: {cross_ex} picks (HIGHEST CONVICTION)")
    print(f"{'=' * 70}\n")

    # Generate dashboard-compatible data for funds.html
    try:
        from generate_dashboard_data import main as gen_dashboard
        gen_dashboard()
    except Exception as e:
        print(f"  [WARN] Dashboard data generation failed: {e}")

    # Trusted trader performance tracking + insights
    try:
        from trusted_trader_tracker import run as run_trusted_tracker
        run_trusted_tracker()
    except Exception as e:
        print(f"  [WARN] Trusted trader tracker failed: {e}")
        import traceback
        traceback.print_exc()

    # Merge copy trader picks into alpha engine active_picks.json
    try:
        ae_file = Path(__file__).parent.parent / "alpha_engine" / "data" / "active_picks.json"
        ct_file = Path(__file__).parent / "data" / "active_picks.json"
        clone_file = Path(__file__).parent / "data" / "clone_active_picks.json"
        hs_file = Path(__file__).parent / "data" / "highscore_active_picks.json"

        # Load all copy trader picks
        ct_all = []
        for src in [ct_file, clone_file, hs_file]:
            if src.exists():
                with open(src, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        ct_all.extend(data)

        if ct_all and ae_file.exists():
            with open(ae_file, encoding="utf-8") as f:
                ae_picks = json.load(f)
            # Remove old copy trader picks
            ae_picks = [p for p in ae_picks if isinstance(p, dict)
                        and not p.get("source_system", "").startswith("copy_trader")
                        and "copy_hl_" not in p.get("strategy", "")
                        and "copy_okx_" not in p.get("strategy", "")
                        and "clone_" not in p.get("strategy", "")]
            # Normalize confidence before merge (hs_* picks report raw scores 0-100)
            # Enforce caps: proven traders get 0.85 cap, unproven get 0.60
            for _p in ct_all:
                _conf = _p.get("confidence")
                _is_proven = _p.get("proven_trader", False)
                _merge_cap = 0.85 if _is_proven else 0.60
                if _conf is not None and _conf > 1.0:
                    _p["confidence"] = round(min(_conf / 100.0, _merge_cap), 4)
                elif _conf is not None and _conf > _merge_cap:
                    _p["confidence"] = _merge_cap
            ae_picks.extend(ct_all)

            # Post-merge: Apply hygiene checks (100x ratio floor etc)
            ae_picks = sanitize_active_picks(ae_picks, "alpha_engine_merge_gate")

            # Post-merge conflict resolution: resolve LONG vs SHORT on same symbol
            seen_symbols = {}
            final_merged = []
            merge_conflicts = 0
            for pick in ae_picks:
                if not isinstance(pick, dict):
                    continue
                key = pick.get("symbol", "")
                if not key:
                    final_merged.append(pick)
                    continue
                if key in seen_symbols:
                    existing = seen_symbols[key]
                    existing_dir = str(existing.get("direction", existing.get("signal_type", "LONG"))).upper()
                    pick_dir = str(pick.get("direction", pick.get("signal_type", "LONG"))).upper()
                    # Normalize directions
                    existing_dir = "SHORT" if existing_dir in ("SHORT", "SELL") else "LONG"
                    pick_dir = "SHORT" if pick_dir in ("SHORT", "SELL") else "LONG"
                    if existing_dir != pick_dir:
                        # Conflict! Keep higher confidence
                        if pick.get("confidence", 0) > existing.get("confidence", 0):
                            final_merged = [p for p in final_merged if p.get("symbol") != key]
                            final_merged.append(pick)
                            seen_symbols[key] = pick
                        merge_conflicts += 1
                        continue
                    # Same direction, same symbol — keep existing (first wins)
                    continue
                seen_symbols[key] = pick
                final_merged.append(pick)
            ae_picks = final_merged
            if merge_conflicts:
                print(f"  [MERGE-CONFLICT] Resolved {merge_conflicts} LONG/SHORT conflicts after merge")

            # Score all picks with elite_scorer (copy trader picks were unscored)
            try:
                import sys as _sys
                _ae_dir = str(Path(__file__).parent.parent / "alpha_engine")
                if _ae_dir not in _sys.path:
                    _sys.path.insert(0, _ae_dir)
                from elite_scorer import enrich_picks_with_elite_score
                _unscored = [p for p in ae_picks if p.get("elite_score") is None]
                if _unscored:
                    enrich_picks_with_elite_score(ae_picks, str(Path(ae_file).parent))
                    print(f"  [MERGE] Elite-scored {len(_unscored)} previously unscored picks")
            except Exception as _es_err:
                print(f"  [MERGE] Elite scoring failed (non-fatal): {_es_err}")

            # FINAL HYGIENE CHECK after scoring (just in case)
            ae_picks = sanitize_active_picks(ae_picks, "alpha_engine_final_safety")

            with open(ae_file, "w", encoding="utf-8") as f:
                json.dump(ae_picks, f, indent=2)
            print(f"  [MERGE] {len(ct_all)} copy trader picks merged into alpha engine ({len(ae_picks)} total)")
    except Exception as e:
        print(f"  [WARN] Alpha engine merge failed: {e}")

    # Optional: Strategy Learning Engine (slow — fetches fills for each trader)
    if learn:
        try:
            from strategy_learner import run as run_strategy_learner
            print(f"\n--- Strategy Learning Engine ---")
            run_strategy_learner()
        except Exception as e:
            print(f"  [WARN] Strategy learner failed: {e}")
            import traceback
            traceback.print_exc()

    # Strategy Variation Forward Tester (runs when --variations flag or not --fast)
    if variations or (not fast and not okx_only and not hl_only and not myfxbook_only):
        try:
            from strategy_variation_engine import generate_variations
            from variation_forward_tester import update_all_variations
            print(f"\n--- Strategy Variation Engine ---")
            generate_variations()
            print(f"\n--- Variation Forward Tester ---")
            update_all_variations(picks=deduped)
        except Exception as e:
            print(f"  [WARN] Variation forward tester failed: {e}")
            import traceback
            traceback.print_exc()

    return deduped


if __name__ == "__main__":
    main()
