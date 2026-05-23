#!/usr/bin/env python3
"""
Top-Gainer Capture Metric System
=================================
Measures how well our trading systems capture the market's top-performing assets.

Metrics:
  - Recall@Top-5%:  What fraction of the top 5% gainers did we have picks for?
  - Recall@Top-10%: What fraction of the top 10% gainers did we have picks for?
  - Average Rank:   Among all USDT pairs, what's the average rank of our picked symbols?
  - Coverage Rate:  What % of our picks landed in the top decile?

Data sources (with failover):
  Binance mirrors -> CoinGecko -> KuCoin
"""

import sys
import os
import io
import json
import ssl
import math
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── Windows UTF-8 fix ────────────────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Constants ─────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DASHBOARD_PAYLOAD = SCRIPT_DIR.parent / "audit_trail" / "data" / "dashboard_payload.json"
ACTIVE_PICKS_JSON = DATA_DIR / "active_picks.json"
OUTPUT_FILE = DATA_DIR / "top_gainer_capture.json"

# Stablecoins / wrapped tokens to exclude from gainer ranking
EXCLUDE_SYMBOLS = {
    "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "DAIUSDT", "FDUSDUSDT",
    "USDPUSDT", "EURUSDT", "GBPUSDT", "AEURUSDT", "USTCUSDT",
    "WBTCUSDT", "WBETHUSDT",
    # Extended stablecoin blocklist (Mar 2026)
    "UUSDT", "USD1USDT", "USDEUSDT", "XUSDUSDT", "STABLEUSDT",
    "RLUSDUSDT", "BFUSDUSDT", "PYUSDUSDT", "GUSDUSDT", "FRAXUSDT",
}


def _is_stablecoin_by_pattern(symbol: str, price: float | None = None) -> bool:
    """Detect stablecoins by naming pattern or price heuristic."""
    if symbol in EXCLUDE_SYMBOLS:
        return True
    if symbol.endswith("USDUSDT") or symbol.endswith("USDTUSDT"):
        return True
    if price is not None and 0.99 <= price <= 1.01:
        return True
    return False

TIMEOUT = 15  # seconds per API call

# ── SSL context (skip verification for CI environments) ───────────────────────
def _ssl_ctx():
    ctx = ssl.create_default_context()
    try:
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    except Exception:
        ctx = ssl._create_unverified_context()
    return ctx


def _fetch_json(url, timeout=TIMEOUT):
    """Fetch JSON from a URL using stdlib only."""
    ctx = _ssl_ctx()
    req = urllib.request.Request(url, headers={"User-Agent": "TopGainerCapture/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── Binance 24h ticker (failover chain) ──────────────────────────────────────
BINANCE_MIRRORS = [
    "https://data-api.binance.vision/api/v3/ticker/24hr",
    "https://api.binance.com/api/v3/ticker/24hr",
    "https://api1.binance.com/api/v3/ticker/24hr",
    "https://api2.binance.com/api/v3/ticker/24hr",
]


def fetch_binance_tickers():
    """Fetch all 24h tickers from Binance with mirror failover."""
    errors = []
    for url in BINANCE_MIRRORS:
        try:
            data = _fetch_json(url)
            # Filter to USDT pairs only, exclude stablecoins
            usdt_pairs = []
            for t in data:
                sym = t.get("symbol", "")
                if not sym.endswith("USDT"):
                    continue
                try:
                    last_price = float(t.get("lastPrice", 0))
                except (ValueError, TypeError):
                    last_price = 0
                if _is_stablecoin_by_pattern(sym, last_price):
                    continue
                try:
                    pct = float(t.get("priceChangePercent", 0))
                except (ValueError, TypeError):
                    continue
                usdt_pairs.append({
                    "symbol": sym,
                    "price_change_pct": pct,
                    "volume_usdt": float(t.get("quoteVolume", 0)),
                    "last_price": last_price,
                })
            if usdt_pairs:
                return usdt_pairs, "binance"
        except Exception as e:
            errors.append(f"Binance ({url}): {e}")
            continue

    # Fallback 1: CoinGecko
    try:
        return _fetch_coingecko(), "coingecko"
    except Exception as e:
        errors.append(f"CoinGecko: {e}")

    # Fallback 2: KuCoin
    try:
        return _fetch_kucoin(), "kucoin"
    except Exception as e:
        errors.append(f"KuCoin: {e}")

    raise RuntimeError(f"All API sources failed:\n" + "\n".join(errors))


def _fetch_coingecko():
    """CoinGecko fallback — top 250 coins by market cap."""
    all_coins = []
    for page in (1, 2):
        url = (
            f"https://api.coingecko.com/api/v3/coins/markets"
            f"?vs_currency=usd&order=market_cap_desc&per_page=250&page={page}"
            f"&price_change_percentage=24h"
        )
        data = _fetch_json(url)
        for c in data:
            sym = (c.get("symbol", "") + "USDT").upper()
            pct = c.get("price_change_percentage_24h")
            if pct is None:
                continue
            all_coins.append({
                "symbol": sym,
                "price_change_pct": float(pct),
                "volume_usdt": float(c.get("total_volume", 0)),
                "last_price": float(c.get("current_price", 0)),
            })
    return all_coins


def _fetch_kucoin():
    """KuCoin fallback."""
    url = "https://api.kucoin.com/api/v1/market/allTickers"
    data = _fetch_json(url)
    tickers = data.get("data", {}).get("ticker", [])
    pairs = []
    for t in tickers:
        sym_raw = t.get("symbol", "")
        if not sym_raw.endswith("-USDT"):
            continue
        sym = sym_raw.replace("-", "")
        try:
            pct = float(t.get("changeRate", 0)) * 100
        except (ValueError, TypeError):
            continue
        pairs.append({
            "symbol": sym,
            "price_change_pct": pct,
            "volume_usdt": float(t.get("volValue", 0)),
            "last_price": float(t.get("last", 0)),
        })
    return pairs


# ── Load our active picks ────────────────────────────────────────────────────
def load_our_symbols():
    """
    Load symbols we have active picks for from both:
      1. audit_trail/data/dashboard_payload.json -> picks.active[].symbol
      2. alpha_engine/data/active_picks.json -> [].symbol
    Returns a set of uppercased symbols (e.g. {'BTCUSDT', 'ETHUSDT'}).
    """
    symbols = set()

    # Source 1: dashboard_payload.json
    if DASHBOARD_PAYLOAD.exists():
        try:
            with open(DASHBOARD_PAYLOAD, "r", encoding="utf-8") as f:
                payload = json.load(f)
            picks = payload.get("picks", {})
            for pick in picks.get("active", []):
                sym = pick.get("symbol", "").upper()
                if sym and sym.endswith("USDT"):
                    symbols.add(sym)
        except Exception as e:
            print(f"  [WARN] Could not load dashboard_payload.json: {e}")

    # Source 2: active_picks.json
    if ACTIVE_PICKS_JSON.exists():
        try:
            with open(ACTIVE_PICKS_JSON, "r", encoding="utf-8") as f:
                picks = json.load(f)
            for pick in picks:
                sym = pick.get("symbol", "").upper()
                if sym and sym.endswith("USDT"):
                    symbols.add(sym)
        except Exception as e:
            print(f"  [WARN] Could not load active_picks.json: {e}")

    return symbols


# ── Core analysis ─────────────────────────────────────────────────────────────
def compute_capture_metrics(market_data, our_symbols):
    """
    Compute top-gainer capture metrics.

    Returns dict with:
      - recall_top_5pct: fraction of top 5% gainers we had picks for
      - recall_top_10pct: fraction of top 10% gainers we had picks for
      - avg_rank_of_picks: average rank of our picked symbols (1 = best)
      - avg_rank_percentile: average percentile of our picks (100 = top)
      - coverage_rate_top_decile: % of our picks that are in top 10%
      - top_gainers_we_caught: list of top gainers we had
      - top_gainers_we_missed: list of top gainers we missed
    """
    n = len(market_data)
    if n == 0:
        return {"error": "No market data available"}

    # Sort by 24h % change descending
    ranked = sorted(market_data, key=lambda x: x["price_change_pct"], reverse=True)

    # Assign ranks
    for i, item in enumerate(ranked):
        item["rank"] = i + 1
        item["percentile"] = 100.0 * (1.0 - i / n)

    # Build lookup
    rank_lookup = {item["symbol"]: item for item in ranked}

    # Top 5% and top 10% thresholds
    top_5pct_count = max(1, math.ceil(n * 0.05))
    top_10pct_count = max(1, math.ceil(n * 0.10))

    top_5pct_symbols = {ranked[i]["symbol"] for i in range(top_5pct_count)}
    top_10pct_symbols = {ranked[i]["symbol"] for i in range(top_10pct_count)}

    # Cross-reference with our picks (only those present in market data)
    our_in_market = our_symbols & set(rank_lookup.keys())

    # Recall = how many of the top gainers did we capture?
    caught_top5 = our_in_market & top_5pct_symbols
    caught_top10 = our_in_market & top_10pct_symbols

    recall_5 = len(caught_top5) / top_5pct_count if top_5pct_count else 0
    recall_10 = len(caught_top10) / top_10pct_count if top_10pct_count else 0

    # Average rank of our picks
    ranks_of_ours = [rank_lookup[s]["rank"] for s in our_in_market]
    avg_rank = sum(ranks_of_ours) / len(ranks_of_ours) if ranks_of_ours else n
    avg_percentile = sum(rank_lookup[s]["percentile"] for s in our_in_market) / len(our_in_market) if our_in_market else 0

    # Coverage rate: % of our picks that ended up in top decile
    in_top_decile = sum(1 for s in our_in_market if s in top_10pct_symbols)
    coverage_rate = (in_top_decile / len(our_in_market) * 100) if our_in_market else 0

    # Detail lists for reporting
    def _detail(sym):
        d = rank_lookup[sym]
        return {
            "symbol": sym,
            "rank": d["rank"],
            "percentile": round(d["percentile"], 1),
            "change_24h_pct": round(d["price_change_pct"], 2),
            "volume_usdt": round(d["volume_usdt"], 0),
        }

    caught_details = sorted(
        [_detail(s) for s in caught_top10],
        key=lambda x: x["rank"]
    )
    missed_top10 = top_10pct_symbols - our_in_market
    missed_details = sorted(
        [_detail(s) for s in list(missed_top10)[:20]],
        key=lambda x: x["rank"]
    )

    our_picks_details = sorted(
        [_detail(s) for s in our_in_market],
        key=lambda x: x["rank"]
    )

    return {
        "total_usdt_pairs": n,
        "our_active_symbols": len(our_symbols),
        "our_symbols_in_market": len(our_in_market),
        "top_5pct_count": top_5pct_count,
        "top_10pct_count": top_10pct_count,
        "recall_top_5pct": round(recall_5 * 100, 2),
        "recall_top_10pct": round(recall_10 * 100, 2),
        "caught_in_top_5pct": len(caught_top5),
        "caught_in_top_10pct": len(caught_top10),
        "avg_rank_of_picks": round(avg_rank, 1),
        "avg_rank_percentile": round(avg_percentile, 1),
        "coverage_rate_top_decile_pct": round(coverage_rate, 1),
        "top_gainer": _detail(ranked[0]["symbol"]) if ranked else None,
        "top_gainers_we_caught": caught_details,
        "top_gainers_we_missed": missed_details,
        "our_picks_ranked": our_picks_details,
    }


# ── Output ────────────────────────────────────────────────────────────────────
def print_summary(result, source):
    """Print a human-readable summary table."""
    print("\n" + "=" * 70)
    print("  TOP-GAINER CAPTURE REPORT")
    print("=" * 70)
    print(f"  Data source:           {source}")
    print(f"  Timestamp:             {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Total USDT pairs:      {result['total_usdt_pairs']}")
    print(f"  Our active symbols:    {result['our_active_symbols']}")
    print(f"  Matched in market:     {result['our_symbols_in_market']}")
    print("-" * 70)
    print(f"  Recall @ Top 5%:       {result['recall_top_5pct']:.1f}%  "
          f"({result['caught_in_top_5pct']}/{result['top_5pct_count']} golden trades)")
    print(f"  Recall @ Top 10%:      {result['recall_top_10pct']:.1f}%  "
          f"({result['caught_in_top_10pct']}/{result['top_10pct_count']} golden trades)")
    print(f"  Avg Rank of Picks:     {result['avg_rank_of_picks']} / {result['total_usdt_pairs']}")
    print(f"  Avg Rank Percentile:   {result['avg_rank_percentile']:.1f}%")
    print(f"  Top-Decile Coverage:   {result['coverage_rate_top_decile_pct']:.1f}% of our picks in top 10%")
    print("-" * 70)

    if result.get("top_gainer"):
        tg = result["top_gainer"]
        print(f"  Market top gainer:     {tg['symbol']} @ +{tg['change_24h_pct']}%")

    if result["top_gainers_we_caught"]:
        print(f"\n  TOP GAINERS WE CAUGHT ({len(result['top_gainers_we_caught'])}):")
        print(f"  {'Symbol':<14} {'Rank':>6} {'Pctl':>6} {'24h %':>8}")
        for g in result["top_gainers_we_caught"]:
            print(f"  {g['symbol']:<14} {g['rank']:>6} {g['percentile']:>5.1f}% {g['change_24h_pct']:>+7.2f}%")

    if result["top_gainers_we_missed"]:
        print(f"\n  TOP GAINERS WE MISSED (showing up to 20):")
        print(f"  {'Symbol':<14} {'Rank':>6} {'Pctl':>6} {'24h %':>8}")
        for g in result["top_gainers_we_missed"][:20]:
            print(f"  {g['symbol']:<14} {g['rank']:>6} {g['percentile']:>5.1f}% {g['change_24h_pct']:>+7.2f}%")

    print("\n" + "=" * 70)


# ── Main entry points ────────────────────────────────────────────────────────
def run():
    """Main entry point for workflow integration. Returns the result dict."""
    print("[TopGainerCapture] Fetching 24h market data...")
    market_data, source = fetch_binance_tickers()
    print(f"  -> {len(market_data)} USDT pairs from {source}")

    print("[TopGainerCapture] Loading our active picks...")
    our_symbols = load_our_symbols()
    print(f"  -> {len(our_symbols)} unique symbols across all systems")

    print("[TopGainerCapture] Computing capture metrics...")
    result = compute_capture_metrics(market_data, our_symbols)

    # Add metadata
    result["source"] = source
    result["generated_at"] = datetime.now(timezone.utc).isoformat()

    # Save to file
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"[TopGainerCapture] Results saved to {OUTPUT_FILE}")

    print_summary(result, source)
    return result


if __name__ == "__main__":
    run()
