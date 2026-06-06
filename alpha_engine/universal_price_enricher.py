#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Price Enricher
========================
Fetches current prices for ALL active picks regardless of source system.

Problem: forward_validator and enrich_picks() only update crypto picks that
exist in CRYPTO_SYMBOLS config. Picks from copy_trader_intel, multi_asset_copytrader,
cta_replicator, yahoo_analyst_consensus, etc. never get price updates — 175 of 191
picks show "—" on the dashboard.

Solution: This module loads ALL active picks, fetches prices from:
  1. Binance batch endpoint (covers ~80% of crypto symbols in ONE call)
  2. yfinance fallback (stocks, forex, commodities, ETFs)
Then updates current_price, last_checked, pnl_pct, and checks TP/SL hits.

Usage:
  python alpha_engine/universal_price_enricher.py
  # Or import and call: from universal_price_enricher import enrich_all_picks
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR = ENGINE_DIR / "data"
ACTIVE_PICKS_FILE = DATA_DIR / "active_picks.json"
CLOSED_PICKS_FILE = DATA_DIR / "closed_picks.json"

# ---------------------------------------------------------------------------
# Binance mirrors (4-mirror failover per API failover rule)
# ---------------------------------------------------------------------------
BINANCE_SPOT_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]

# In CI, prefer non-geo-blocked endpoints first
if os.environ.get("GITHUB_ACTIONS"):
    BINANCE_SPOT_MIRRORS = [
        "https://data-api.binance.vision",
        "https://api.binance.us",
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ]

HTTP_TIMEOUT = 12


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_for_json(obj):
    """Recursively replace NaN/Infinity with None so json.dump never emits invalid tokens."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj


def _load_json(path: Path) -> list | dict | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] Failed to load {path}: {e}")
        return None


def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_sanitize_for_json(data), f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Symbol normalization
# ---------------------------------------------------------------------------

def _normalize_to_binance(symbol: str) -> str | None:
    """Try to convert a pick symbol to Binance ticker format.

    Returns None if symbol is clearly not a Binance-tradeable crypto.
    """
    if not symbol:
        return None
    s = symbol.upper().strip()

    # Already Binance format (e.g. BTCUSDT, ETHUSDT)
    if s.endswith("USDT") or s.endswith("BUSD") or s.endswith("USDC"):
        return s

    # Yahoo-style crypto: BTC-USD -> BTCUSDT
    if s.endswith("-USD") or s.endswith("-USDT"):
        base = s.split("-")[0]
        return base + "USDT"

    # Forex (EURUSD=X), commodities (CL=F, GC=F), stocks (AAPL) -- not Binance
    if "=X" in s or "=F" in s or "^" in s:
        return None

    # Pure base symbols that are likely crypto: add USDT
    # Skip if it looks like a stock ticker (2-4 uppercase letters, no numbers)
    # We'll try it on Binance and the lookup will just miss if it's not there
    if len(s) <= 6 and s.isalpha():
        # Could be crypto (BTC, ETH) or stock (AAPL, NVDA)
        # We'll try USDT suffix and let Binance lookup handle it
        return s + "USDT"

    return s if s.endswith("USDT") else None


def _needs_yfinance(symbol: str, category: str | None) -> bool:
    """Check if a symbol needs yfinance instead of Binance."""
    if not symbol:
        return False
    s = symbol.upper()
    cat = (category or "").lower()

    # Explicit non-crypto categories
    if cat in ("forex", "stocks", "stock", "equity", "etf", "futures",
               "commodity", "bond", "penny", "index"):
        return True

    # Yahoo-format symbols
    if "=X" in s or "=F" in s or "^" in s:
        return True

    return False


# ---------------------------------------------------------------------------
# Price fetching: Binance batch
# ---------------------------------------------------------------------------

def _fetch_all_binance_prices() -> dict[str, float]:
    """Fetch ALL Binance spot prices in one call with mirror failover.

    Returns dict of {symbol: price}, e.g. {"BTCUSDT": 84000.5, "ETHUSDT": 1900.2}
    """
    import requests

    for mirror in BINANCE_SPOT_MIRRORS:
        try:
            r = requests.get(
                f"{mirror}/api/v3/ticker/price",
                timeout=HTTP_TIMEOUT
            )
            if r.status_code in (451, 403):
                continue
            r.raise_for_status()
            data = r.json()
            return {item["symbol"]: float(item["price"]) for item in data}
        except Exception:
            continue

    print("  [WARN] All Binance mirrors failed for batch prices")
    return {}


# ---------------------------------------------------------------------------
# Price fetching: yfinance fallback
# ---------------------------------------------------------------------------

# Side-channel: records {symbol: {source, asof, is_proxy}} for the most recent
# forex/commodity failover fetch. Lets callers attribute price provenance and
# exclude proxy-priced closures from /audit WR/PF without changing the
# price_map return shape. Safe to ignore if unused.
LAST_PRICE_META: dict[str, dict] = {}


def _fetch_yfinance_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch prices for non-Binance symbols using yfinance.

    Returns dict of {symbol: price}.

    For =X (forex) and =F (commodity futures) symbols, the dedicated failover
    modules are tried first — they use stdlib urllib only and work on GHA runners
    where yfinance fails with 401.
    """
    if not symbols:
        return {}

    price_map = {}

    # ── Try dedicated failover chains for forex and commodity first ──
    try:
        from alpha_engine.forex_price_failover import fetch_forex_rate
        from alpha_engine.commodity_price_failover import fetch_commodity_price
        _failover_available = True
    except ImportError:
        _failover_available = False

    if _failover_available:
        for sym in list(symbols):
            if "=X" in sym.upper():
                result = fetch_forex_rate(sym)
                if result and result.get("price", 0) > 0:
                    price_map[sym] = result["price"]
                    LAST_PRICE_META[sym] = {"source": result.get("source"),
                                            "asof": result.get("asof"),
                                            "is_proxy": bool(result.get("is_proxy"))}
                    print(f"    [fx-failover] {sym} = {result['price']} [{result['source']}]")
            elif "=F" in sym.upper():
                result = fetch_commodity_price(sym)
                # Skip is_proxy (FRED spot/cash) results: a macro spot price is
                # NOT the front-month futures contract price and would create
                # phantom basis PnL / false TP-SL closures. Let it fall through
                # to yfinance instead of filling a wrong price.
                if result and result.get("price", 0) > 0 and not result.get("is_proxy"):
                    price_map[sym] = result["price"]
                    LAST_PRICE_META[sym] = {"source": result.get("source"),
                                            "asof": result.get("asof"),
                                            "is_proxy": False}
                    print(f"    [cmd-failover] {sym} = {result['price']} [{result['source']}]")
                elif result and result.get("is_proxy"):
                    print(f"    [cmd-failover] {sym}: skipped proxy/spot price from "
                          f"{result.get('source')} (not the futures contract)")

    try:
        import yfinance as yf
    except ImportError:
        print("  [WARN] yfinance not installed, skipping stock/forex/commodity prices")
        return price_map

    # ── Priority: fetch forex/commodity =X/=F symbols individually first ──
    # These often fail in batch mode (fast_info returns None for forex).
    # Use history(period="5d") to handle weekends/holidays where "1d" is empty.
    # Only try yfinance for symbols the failover chain didn't already cover.
    priority_syms = [s for s in symbols if ("=X" in s or "=F" in s) and s not in price_map]
    regular_syms = [s for s in symbols if s not in set(priority_syms)]

    for sym in priority_syms:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d")
            if not hist.empty:
                price_map[sym] = float(hist["Close"].iloc[-1])
                print(f"    [yf] {sym} = {price_map[sym]}")
            else:
                print(f"    [yf] {sym}: empty history (5d)")
        except Exception as e:
            print(f"    [yf] {sym}: error: {e}")

    # ── Batch fetch remaining symbols using Tickers ──
    if regular_syms:
        try:
            tickers = yf.Tickers(" ".join(regular_syms))
            for sym in regular_syms:
                try:
                    # yfinance may normalize keys — try both original and uppercase
                    ticker = (tickers.tickers.get(sym)
                              or tickers.tickers.get(sym.upper()))
                    if ticker:
                        info = ticker.fast_info
                        price = getattr(info, "last_price", None)
                        if price and price > 0:
                            price_map[sym] = float(price)
                except Exception:
                    pass
        except Exception as e:
            print(f"  [WARN] yfinance batch fetch failed: {e}")

    # ── Fallback: individual fetches for missed regular symbols ──
    missed = [s for s in regular_syms if s not in price_map]
    if missed:
        print(f"    [yf] Individual fallback for {len(missed)} missed symbols...")
    for sym in missed[:30]:  # Cap at 30 to avoid timeout
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d")
            if not hist.empty:
                price_map[sym] = float(hist["Close"].iloc[-1])
        except Exception:
            pass

    return price_map


# ---------------------------------------------------------------------------
# Core enrichment
# ---------------------------------------------------------------------------

def enrich_all_picks(picks: list[dict] | None = None,
                     save: bool = True) -> tuple[list[dict], dict]:
    """Enrich ALL active picks with current prices, PnL, and TP/SL checks.

    Args:
        picks: List of pick dicts. If None, loads from active_picks.json.
        save: If True, saves updated picks back to active_picks.json.

    Returns:
        (updated_picks, summary_dict)
    """
    # Load picks if not provided
    if picks is None:
        picks = _load_json(ACTIVE_PICKS_FILE)
        if not isinstance(picks, list):
            print("[ENRICHER] No active picks found")
            return [], {"updated": 0, "total": 0, "tp_hit": 0, "sl_hit": 0}

    if not picks:
        return picks, {"updated": 0, "total": 0, "tp_hit": 0, "sl_hit": 0}

    total = len(picks)
    now_iso = datetime.now(timezone.utc).isoformat()

    # -----------------------------------------------------------------------
    # Step 1: Collect all unique symbols and classify them
    # -----------------------------------------------------------------------
    binance_candidates = {}  # pick_symbol -> binance_symbol
    yfinance_symbols = set()

    for pick in picks:
        sym = pick.get("symbol", "")
        cat = pick.get("category", "")
        if not sym:
            continue

        if _needs_yfinance(sym, cat):
            yfinance_symbols.add(sym)
        else:
            binance_sym = _normalize_to_binance(sym)
            if binance_sym:
                binance_candidates[sym] = binance_sym
            else:
                # Unknown format — try yfinance as last resort
                yfinance_symbols.add(sym)

    # -----------------------------------------------------------------------
    # Step 2: Fetch Binance prices (one batch call)
    # -----------------------------------------------------------------------
    print(f"[ENRICHER] Fetching prices for {len(binance_candidates)} crypto + "
          f"{len(yfinance_symbols)} non-crypto symbols...")

    binance_prices = _fetch_all_binance_prices()  # {BTCUSDT: 84000.5, ...}

    # Build price map: original_symbol -> price
    price_map = {}
    binance_hits = 0
    for orig_sym, binance_sym in binance_candidates.items():
        if binance_sym in binance_prices:
            price_map[orig_sym] = binance_prices[binance_sym]
            binance_hits += 1

    # Also check if the original symbol is directly in Binance (copy_trader picks)
    for pick in picks:
        sym = pick.get("symbol", "")
        if sym and sym not in price_map and sym in binance_prices:
            price_map[sym] = binance_prices[sym]
            binance_hits += 1

    print(f"  Binance: {binance_hits} symbols matched")

    # -----------------------------------------------------------------------
    # Step 3: yfinance for non-crypto symbols
    # -----------------------------------------------------------------------
    # Also add crypto symbols that Binance missed (HL-only, exotic pairs)
    missed_crypto = [
        sym for sym in binance_candidates
        if sym not in price_map
    ]
    # Don't send raw crypto symbols (like HYPEUSDT) to yfinance — it won't know them
    # Only send symbols that look like stocks/forex
    yf_worth_trying = list(yfinance_symbols)
    for sym in missed_crypto:
        if not sym.endswith("USDT") and not sym.endswith("BUSD"):
            yf_worth_trying.append(sym)

    if yf_worth_trying:
        yf_prices = _fetch_yfinance_prices(yf_worth_trying)
        yf_hits = 0
        for sym, price in yf_prices.items():
            if sym not in price_map:
                price_map[sym] = price
                yf_hits += 1
        print(f"  yfinance: {yf_hits} symbols matched")

    # -----------------------------------------------------------------------
    # Step 4: Update each pick
    # -----------------------------------------------------------------------
    updated = 0
    tp_hit = 0
    sl_hit = 0
    picks_to_close = []

    for pick in picks:
        sym = pick.get("symbol", "")
        if sym not in price_map:
            continue

        live_price = price_map[sym]
        entry = pick.get("entry_price")
        if not entry or entry <= 0:
            # Backfill entry_price for informational picks
            pick["entry_price"] = live_price
            entry = live_price

        pick["current_price"] = live_price
        pick["last_checked"] = now_iso

        # Direction detection
        direction = (pick.get("direction") or pick.get("signal_type") or "LONG").upper()
        is_short = direction in ("SELL", "SHORT")

        # PnL calculation
        if is_short:
            pnl_pct = (entry - live_price) / entry * 100
        else:
            pnl_pct = (live_price - entry) / entry * 100
        pick["pnl_pct"] = round(pnl_pct, 4)
        pick["unrealized_pnl_pct"] = round(pnl_pct / 100, 6)  # Compat with existing format

        # TP progress
        tp = pick.get("take_profit")
        if tp and tp != entry and tp > 0:
            try:
                if is_short:
                    pick["tp_progress_pct"] = round(
                        max(0, (entry - live_price) / (entry - tp) * 100), 2
                    )
                else:
                    pick["tp_progress_pct"] = round(
                        max(0, (live_price - entry) / (tp - entry) * 100), 2
                    )
            except ZeroDivisionError:
                pick["tp_progress_pct"] = 0.0
        else:
            pick["tp_progress_pct"] = 0.0

        # SL progress
        sl = pick.get("stop_loss")
        if sl and sl != entry and sl > 0:
            try:
                if is_short:
                    pick["sl_progress_pct"] = round(
                        max(0, (live_price - entry) / (sl - entry) * 100), 2
                    )
                else:
                    pick["sl_progress_pct"] = round(
                        max(0, (entry - live_price) / (entry - sl) * 100), 2
                    )
            except ZeroDivisionError:
                pick["sl_progress_pct"] = 0.0
        else:
            pick["sl_progress_pct"] = 0.0

        # High-water mark tracking
        hwm = pick.get("high_water_mark") or live_price
        if is_short:
            pick["high_water_mark"] = min(hwm, live_price) if hwm else live_price
        else:
            pick["high_water_mark"] = max(hwm, live_price) if hwm else live_price

        # TP/SL hit detection
        if tp and tp > 0:
            tp_reached = (live_price <= tp if is_short else live_price >= tp)
            if tp_reached:
                tp_hit += 1
                pick["_tp_hit"] = True
                picks_to_close.append((pick, "TP_HIT"))

        if sl and sl > 0:
            sl_reached = (live_price >= sl if is_short else live_price <= sl)
            if sl_reached:
                sl_hit += 1
                pick["_sl_hit"] = True
                # Only mark for closure if not already marked as TP hit
                if not pick.get("_tp_hit"):
                    picks_to_close.append((pick, "SL_HIT"))

        updated += 1

    # -----------------------------------------------------------------------
    # Step 5: Close TP/SL hits
    # -----------------------------------------------------------------------
    closed_picks = []
    if picks_to_close:
        for pick, reason in picks_to_close:
            pick["status"] = "CLOSED"
            pick["exit_price"] = pick.get("current_price")
            pick["exit_date"] = now_iso
            pick["exit_reason"] = reason
            closed_picks.append(pick)

        # Remove closed picks from active list
        closed_ids = {id(p) for p, _ in picks_to_close}
        picks = [p for p in picks if id(p) not in closed_ids]

        # Append to closed_picks.json
        try:
            existing_closed = _load_json(CLOSED_PICKS_FILE) or []
            # Clean temporary flags
            for cp in closed_picks:
                cp.pop("_tp_hit", None)
                cp.pop("_sl_hit", None)
            existing_closed.extend(closed_picks)
            _save_json(CLOSED_PICKS_FILE, existing_closed)
            print(f"  Closed {len(closed_picks)} picks (TP: {tp_hit}, SL: {sl_hit}) -> closed_picks.json")
        except Exception as e:
            print(f"  [WARN] Failed to save closed picks: {e}")

    # Clean temporary flags from remaining picks
    for p in picks:
        p.pop("_tp_hit", None)
        p.pop("_sl_hit", None)

    # -----------------------------------------------------------------------
    # Step 6: Save
    # -----------------------------------------------------------------------
    if save:
        _save_json(ACTIVE_PICKS_FILE, picks)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    not_updated = total - updated - len(closed_picks)
    summary = {
        "updated": updated,
        "total": total,
        "tp_hit": tp_hit,
        "sl_hit": sl_hit,
        "closed": len(closed_picks),
        "no_price": not_updated,
    }
    print(f"\n  Updated {updated} of {total} picks with live prices. "
          f"{tp_hit} TP hit, {sl_hit} SL hit.")
    if not_updated > 0:
        print(f"  {not_updated} picks had no price source (exotic/HL-only symbols)")

    return picks, summary


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Universal Price Enricher")
    print("=" * 60)
    start = time.time()

    picks, summary = enrich_all_picks()

    elapsed = time.time() - start
    print(f"\n  Done in {elapsed:.1f}s")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    main()
