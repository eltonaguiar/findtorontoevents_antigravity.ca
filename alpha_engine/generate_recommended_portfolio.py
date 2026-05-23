#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Recommended Portfolio Generator
=================================================
Generates a balanced, ready-to-trade portfolio from current active picks.

Runs each scan cycle and outputs data/recommended_portfolio.json with:
  - Top 4-position diversified basket (via basket_generator)
  - Watchlist of next 5 best picks
  - Live PnL for each position
  - Conviction classification (HIGH/MEDIUM/LOW)
  - Market warnings

Usage:
  python -m alpha_engine.generate_recommended_portfolio
  python alpha_engine/generate_recommended_portfolio.py
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = _THIS_DIR / "data"


# ---------------------------------------------------------------------------
# Binance price fetcher with 3-mirror failover (API Failover Rule)
# ---------------------------------------------------------------------------
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api3.binance.com",
]
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"


def _http_get_json(url, timeout=10):
    """Fetch JSON from URL with timeout."""
    req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def fetch_live_prices(symbols):
    """
    Fetch live prices for a list of symbols.
    Uses Binance 3-mirror failover -> CoinGecko fallback.
    Returns dict: {symbol: price}
    """
    prices = {}
    remaining = list(symbols)

    # Try Binance mirrors first
    for mirror in BINANCE_MIRRORS:
        if not remaining:
            break
        for sym in list(remaining):
            url = f"{mirror}/api/v3/ticker/price?symbol={sym}"
            data = _http_get_json(url, timeout=8)
            if data and "price" in data:
                prices[sym] = float(data["price"])
                remaining.remove(sym)
        if not remaining:
            break
        time.sleep(0.3)

    # CoinGecko fallback for remaining symbols
    if remaining:
        for sym in list(remaining):
            base = sym.upper().replace("USDT", "").replace("USD", "").lower()
            url = f"{COINGECKO_URL}?ids={base}&vs_currencies=usd"
            data = _http_get_json(url, timeout=8)
            if data and base in data and "usd" in data[base]:
                prices[sym] = float(data[base]["usd"])
                remaining.remove(sym)

    return prices


def fetch_btc_price():
    """Fetch current BTC price."""
    prices = fetch_live_prices(["BTCUSDT"])
    return prices.get("BTCUSDT", 0.0)


def fetch_fear_greed():
    """Fetch Fear & Greed index from alternative.me."""
    url = "https://api.alternative.me/fng/?limit=1&format=json"
    data = _http_get_json(url, timeout=8)
    if data and "data" in data and len(data["data"]) > 0:
        return int(data["data"][0].get("value", 50))
    return 50  # neutral fallback


# ---------------------------------------------------------------------------
# Load active picks
# ---------------------------------------------------------------------------
def _load_active_picks():
    """Load picks from active_picks.json."""
    candidates = [
        DATA_DIR / "active_picks.json",
        Path("alpha_engine") / "data" / "active_picks.json",
        Path("data") / "active_picks.json",
    ]
    for path in candidates:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "picks" in data:
                return data["picks"]
            return []
    return []


# ---------------------------------------------------------------------------
# Load market regime
# ---------------------------------------------------------------------------
def _load_market_regime():
    """Load current regime from hmm_regime.json."""
    candidates = [
        DATA_DIR / "hmm_regime.json",
        Path("alpha_engine") / "data" / "hmm_regime.json",
        Path("data") / "hmm_regime.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                regime = (data.get("aggregate", {}).get("market_regime") or "UNKNOWN").upper()
                return regime
            except Exception:
                pass
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Score and enrich picks
# ---------------------------------------------------------------------------
def _score_picks(picks):
    """Score picks using elite_scorer."""
    try:
        try:
            from alpha_engine.elite_scorer import enrich_picks_with_elite_score
        except ImportError:
            from elite_scorer import enrich_picks_with_elite_score
        enrich_picks_with_elite_score(picks)
    except ImportError:
        pass  # elite_scorer not available, use existing scores
    return picks


# ---------------------------------------------------------------------------
# Conviction classification
# ---------------------------------------------------------------------------
def _classify_conviction(pick, regime):
    """
    Classify conviction level:
      HIGH:   score >= 70 AND direction matches regime AND R:R >= 1.5
      MEDIUM: score >= 50 AND R:R >= 1.0
      LOW:    otherwise
    """
    score = pick.get("elite_score", 0) or 0
    direction = (pick.get("direction") or "").upper()
    entry = float(pick.get("entry_price", 0) or 0)
    tp = float(pick.get("take_profit", 0) or 0)
    sl = float(pick.get("stop_loss", 0) or 0)

    # Compute R:R
    rr = 0.0
    if entry > 0 and sl > 0 and tp > 0:
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk > 0:
            rr = round(reward / risk, 2)

    # Check direction-regime alignment
    regime_upper = regime.upper()
    direction_matches = False
    if direction == "SHORT" and regime_upper in ("BEARISH", "TRENDING_DOWN", "CRISIS"):
        direction_matches = True
    elif direction == "LONG" and regime_upper in ("BULLISH", "TRENDING_UP"):
        direction_matches = True
    elif regime_upper in ("UNKNOWN", "MEAN_REVERTING", "NEUTRAL"):
        direction_matches = True  # neutral regimes match anything

    if score >= 70 and direction_matches and rr >= 1.5:
        return "HIGH", rr
    elif score >= 50 and rr >= 1.0:
        return "MEDIUM", rr
    else:
        return "LOW", rr


# ---------------------------------------------------------------------------
# Compute live PnL
# ---------------------------------------------------------------------------
def _compute_pnl(pick, live_price):
    """Compute PnL percentage for a pick given live price."""
    entry = float(pick.get("entry_price", 0) or 0)
    if entry <= 0 or live_price <= 0:
        return 0.0
    direction = (pick.get("direction") or "").upper()
    if direction == "SHORT":
        return round((entry - live_price) / entry * 100, 2)
    else:
        return round((live_price - entry) / entry * 100, 2)


# ---------------------------------------------------------------------------
# Generate warnings
# ---------------------------------------------------------------------------
def _generate_warnings(picks, regime, fear_greed, btc_price):
    """Generate market warnings list."""
    warnings = []

    if fear_greed < 20:
        warnings.append(f"F&G at Extreme Fear ({fear_greed})")
    elif fear_greed > 80:
        warnings.append(f"F&G at Extreme Greed ({fear_greed})")

    if regime in ("CRISIS", "TRENDING_DOWN", "BEARISH"):
        warnings.append(f"Market regime: {regime}")

    # Check directional concentration
    directions = [(p.get("direction") or "").upper() for p in picks if p.get("direction")]
    longs = sum(1 for d in directions if d == "LONG")
    shorts = sum(1 for d in directions if d == "SHORT")
    if longs > 0 and shorts == 0:
        warnings.append("All-LONG portfolio -- no hedges")
    elif shorts > 0 and longs == 0:
        warnings.append("All-SHORT portfolio -- risk of squeeze")

    # BTC EMA check from regime data
    try:
        hmm_path = DATA_DIR / "hmm_regime.json"
        if hmm_path.exists():
            with open(hmm_path, "r", encoding="utf-8") as f:
                hmm = json.load(f)
            metrics = hmm.get("aggregate", {}).get("metrics", {})
            roc_7d = metrics.get("roc_7d", 0)
            if roc_7d < -0.03:
                warnings.append("BTC 7d momentum negative")
    except Exception:
        pass

    return warnings


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------
def generate_recommended_portfolio():
    """
    Generates a balanced portfolio recommendation from current active picks.
    Uses basket_generator for correlation/hedge logic.
    Outputs to data/recommended_portfolio.json
    """
    print("=" * 60)
    print("  RECOMMENDED PORTFOLIO GENERATOR")
    print("=" * 60)

    # 1. Load active picks
    picks = _load_active_picks()
    open_picks = [p for p in picks if (p.get("status") or "").upper() == "OPEN"]
    print(f"  Loaded {len(open_picks)} open picks")

    if not open_picks:
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "market_regime": "UNKNOWN",
            "btc_price": 0,
            "fear_greed": 50,
            "portfolio": {
                "positions": [],
                "hedge": None,
                "diversification": "D",
                "correlation": 0.0,
                "long_pct": 0.0,
                "short_pct": 0.0,
            },
            "watchlist": [],
            "warnings": ["No open picks available"],
        }
        _save_result(result)
        return result

    # 2. Score all picks
    open_picks = _score_picks(open_picks)
    print(f"  Scored {len(open_picks)} picks")

    # 3. Fetch live prices (3-mirror failover)
    symbols = list(set(p["symbol"] for p in open_picks if p.get("symbol")))
    print(f"  Fetching live prices for {len(symbols)} symbols...")
    live_prices = fetch_live_prices(symbols)
    print(f"  Got prices for {len(live_prices)}/{len(symbols)} symbols")

    # 4. Filter: only picks where live price is within 2% of entry (fresh entries)
    fresh_picks = []
    for p in open_picks:
        sym = p.get("symbol", "")
        entry = float(p.get("entry_price", 0) or 0)
        live = live_prices.get(sym, 0)

        if entry <= 0:
            continue

        if live <= 0:
            # No live price available -- still include but mark
            fresh_picks.append(p)
            continue

        gap_pct = abs(live - entry) / entry * 100
        if gap_pct <= 2.0:
            fresh_picks.append(p)

    print(f"  {len(fresh_picks)} picks within 2% of entry (fresh)")

    # If no fresh picks, relax to 5% to avoid empty portfolio
    if not fresh_picks:
        print("  Relaxing freshness filter to 5%...")
        for p in open_picks:
            sym = p.get("symbol", "")
            entry = float(p.get("entry_price", 0) or 0)
            live = live_prices.get(sym, 0)
            if entry <= 0:
                continue
            if live <= 0:
                fresh_picks.append(p)
                continue
            gap_pct = abs(live - entry) / entry * 100
            if gap_pct <= 5.0:
                fresh_picks.append(p)
        print(f"  {len(fresh_picks)} picks within 5% of entry")

    # If still empty, use all scored picks (sorted by score)
    if not fresh_picks:
        print("  Using all open picks (no freshness filter)")
        fresh_picks = sorted(open_picks, key=lambda p: p.get("elite_score", 0), reverse=True)

    # 5. Use basket_generator for balanced basket
    try:
        try:
            from alpha_engine.basket_generator import generate_balanced_basket
        except ImportError:
            from basket_generator import generate_balanced_basket
    except ImportError:
        print("  [WARN] basket_generator not available, using top-4 by score")
        generate_balanced_basket = None

    if generate_balanced_basket:
        basket_result = generate_balanced_basket(
            fresh_picks, max_positions=4, require_hedge=True
        )
    else:
        # Fallback: top 4 by score
        top4 = sorted(fresh_picks, key=lambda p: p.get("elite_score", 0), reverse=True)[:4]
        basket_result = {
            "basket": [{"symbol": p["symbol"], "direction": (p.get("direction") or "LONG").upper(),
                        "score": p.get("elite_score", 0), "size_pct": round(100 / max(len(top4), 1), 1),
                        "group": "unknown", "reason": p.get("reason", "")[:80]} for p in top4],
            "hedge": None,
            "correlation_score": 0.5,
            "diversification_grade": "C",
            "long_pct": 0.0,
            "short_pct": 0.0,
        }

    # 6. Market context
    btc_price = fetch_btc_price()
    fear_greed = fetch_fear_greed()
    regime = _load_market_regime()
    print(f"  BTC: ${btc_price:,.0f}  |  F&G: {fear_greed}  |  Regime: {regime}")

    # 7. Build enriched positions with live PnL + conviction
    basket_symbols = set(b["symbol"] for b in basket_result.get("basket", []))
    positions = []
    for b in basket_result.get("basket", []):
        sym = b["symbol"]
        # Find the original pick for full data
        orig = next((p for p in fresh_picks if p["symbol"] == sym), {})
        live = live_prices.get(sym, 0)
        entry = float(orig.get("entry_price", 0) or 0)
        tp = float(orig.get("take_profit", 0) or 0)
        sl = float(orig.get("stop_loss", 0) or 0)
        pnl = _compute_pnl(orig, live) if live > 0 else 0.0
        conviction, rr = _classify_conviction(orig, regime)

        positions.append({
            "symbol": sym,
            "direction": b.get("direction", "LONG"),
            "score": b.get("score", 0),
            "grade": orig.get("elite_grade", "?"),
            "entry": entry,
            "live": live,
            "pnl_pct": pnl,
            "tp": tp,
            "sl": sl,
            "rr": rr,
            "size_pct": b.get("size_pct", 25),
            "conviction": conviction,
            "strategy": orig.get("strategy", "unknown"),
            "group": b.get("group", "unknown"),
            "reason": (orig.get("reason") or "")[:120],
        })

    # 8. Hedge info
    hedge = basket_result.get("hedge")
    if hedge:
        hedge_out = {
            "symbol": hedge.get("symbol", ""),
            "direction": hedge.get("direction", "SHORT"),
            "size_pct": hedge.get("size_pct", 20),
            "reason": hedge.get("reason", "Correlation hedge"),
        }
    else:
        hedge_out = None

    # 9. Watchlist: next 5 best picks not in basket
    watchlist_picks = [p for p in fresh_picks if p["symbol"] not in basket_symbols]
    watchlist_picks.sort(key=lambda p: p.get("elite_score", 0), reverse=True)
    watchlist = []
    for p in watchlist_picks[:5]:
        conv, rr = _classify_conviction(p, regime)
        watchlist.append({
            "symbol": p["symbol"],
            "score": p.get("elite_score", 0),
            "grade": p.get("elite_grade", "?"),
            "direction": (p.get("direction") or "LONG").upper(),
            "rr": rr,
            "conviction": conv,
            "reason": (p.get("reason") or "")[:100],
        })

    # 10. Warnings
    warnings = _generate_warnings(positions, regime, fear_greed, btc_price)

    # Build final result
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market_regime": regime,
        "btc_price": round(btc_price, 2),
        "fear_greed": fear_greed,
        "portfolio": {
            "positions": positions,
            "hedge": hedge_out,
            "diversification": basket_result.get("diversification_grade", "D"),
            "correlation": basket_result.get("correlation_score", 0.0),
            "long_pct": basket_result.get("long_pct", 0.0),
            "short_pct": basket_result.get("short_pct", 0.0),
        },
        "watchlist": watchlist,
        "warnings": warnings,
    }

    _save_result(result)
    _print_summary(result)
    return result


def _save_result(result):
    """Save result to data/recommended_portfolio.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "recommended_portfolio.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Saved to {out_path}")


def _print_summary(result):
    """Pretty-print portfolio summary."""
    portfolio = result.get("portfolio", {})
    positions = portfolio.get("positions", [])
    watchlist = result.get("watchlist", [])
    warnings = result.get("warnings", [])

    print()
    print("=" * 60)
    print("  RECOMMENDED PORTFOLIO")
    print(f"  Regime: {result.get('market_regime')}  |  "
          f"BTC: ${result.get('btc_price', 0):,.0f}  |  "
          f"F&G: {result.get('fear_greed', 0)}")
    print(f"  Diversification: {portfolio.get('diversification', '?')}  |  "
          f"Correlation: {portfolio.get('correlation', 0):.2f}  |  "
          f"Long: {portfolio.get('long_pct', 0):.0f}%  Short: {portfolio.get('short_pct', 0):.0f}%")
    print("-" * 60)

    if not positions:
        print("  (no positions)")
    else:
        for i, pos in enumerate(positions, 1):
            arrow = "^" if pos["direction"] == "LONG" else "v"
            conv_tag = f"[{pos['conviction']}]"
            pnl_str = f"{pos['pnl_pct']:+.2f}%" if pos.get("live") else "n/a"
            print(f"  {i}. {arrow} {pos['symbol']:<14} "
                  f"Score:{pos['score']:>3} {pos['grade']}  "
                  f"Size:{pos['size_pct']:>5.1f}%  "
                  f"PnL:{pnl_str:<8}  "
                  f"R:R {pos['rr']:.1f}  "
                  f"{conv_tag}")

    hedge = portfolio.get("hedge")
    if hedge:
        print(f"  H. {hedge['direction']:<6} {hedge['symbol']:<14} "
              f"Size:{hedge['size_pct']:>5.1f}%  "
              f"({hedge['reason']})")

    if watchlist:
        print("-" * 60)
        print("  WATCHLIST:")
        for w in watchlist:
            arrow = "^" if w["direction"] == "LONG" else "v"
            print(f"    {arrow} {w['symbol']:<14} Score:{w['score']:>3} {w['grade']}  "
                  f"R:R {w['rr']:.1f}  [{w['conviction']}]")

    if warnings:
        print("-" * 60)
        print("  WARNINGS:")
        for w in warnings:
            print(f"    ! {w}")

    print("=" * 60)


if __name__ == "__main__":
    result = generate_recommended_portfolio()
    print("\n--- JSON output ---")
    print(json.dumps(result, indent=2, default=str))
