#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Force-Close Breached Picks
============================
Standalone script that loads active_picks.json, fetches live prices from
Binance (with 4+ mirror failover + CoinGecko + yfinance fallbacks), and
force-closes any pick whose TP or SL has been breached.

Also handles:
  - Stale pick cleanup (>7 days with no price update)
  - Backfill missing created_at timestamps
  - Backfill missing volume_ratio from Binance 24h ticker
  - Backfill missing htf_confirmation (default to "neutral")
  - Deduplicate picks by ID

Usage:
  python alpha_engine/force_close_breached.py          # standalone
  python alpha_engine/force_close_breached.py --dry-run # preview only

Can also be imported:
  from force_close_breached import force_close_all
  n_closed = force_close_all()
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone, timedelta
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
# API mirrors (per API failover rule: 3+ fallbacks always)
# ---------------------------------------------------------------------------
BINANCE_SPOT_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]

# In CI, prefer non-geo-blocked endpoints
if os.environ.get("GITHUB_ACTIONS"):
    BINANCE_SPOT_MIRRORS = [
        "https://data-api.binance.vision",
        "https://api.binance.us",
    ] + BINANCE_SPOT_MIRRORS

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
KUCOIN_BASE = "https://api.kucoin.com"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

HTTP_TIMEOUT = 12
STALE_DAYS_THRESHOLD = 7
FOREX_MAX_HOLD_HOURS = 48  # Force-close forex picks after 48h (they move 0.3-0.8%/day; if TP not hit by then, edge is gone)

# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _sanitize_for_json(obj):
    """Recursively replace NaN/Infinity with None for json.dump safety."""
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
    """Convert pick symbol to Binance ticker format. Returns None if not crypto."""
    if not symbol:
        return None
    s = symbol.upper().strip()

    if s.endswith("USDT") or s.endswith("BUSD") or s.endswith("USDC"):
        return s

    if s.endswith("-USD") or s.endswith("-USDT"):
        base = s.split("-")[0]
        return base + "USDT"

    if "=X" in s or "=F" in s or "^" in s:
        return None

    if len(s) <= 6 and s.isalpha():
        return s + "USDT"

    return s if s.endswith("USDT") else None


# ---------------------------------------------------------------------------
# Price fetching: Binance batch (with 4-mirror failover)
# ---------------------------------------------------------------------------

def _fetch_all_binance_prices() -> dict[str, float]:
    """Fetch ALL Binance spot prices in one call with mirror failover."""
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


def _fetch_binance_24h_tickers() -> dict[str, dict]:
    """Fetch Binance 24h ticker stats (volume, price change) for all symbols."""
    import requests

    for mirror in BINANCE_SPOT_MIRRORS:
        try:
            r = requests.get(
                f"{mirror}/api/v3/ticker/24hr",
                timeout=HTTP_TIMEOUT
            )
            if r.status_code in (451, 403):
                continue
            r.raise_for_status()
            data = r.json()
            result = {}
            for item in data:
                sym = item.get("symbol", "")
                try:
                    result[sym] = {
                        "price": float(item.get("lastPrice", 0)),
                        "high": float(item.get("highPrice", 0)),
                        "low": float(item.get("lowPrice", 0)),
                        "quoteVolume": float(item.get("quoteVolume", 0)),
                        "priceChangePercent": float(item.get("priceChangePercent", 0)),
                    }
                except (ValueError, TypeError):
                    pass
            return result
        except Exception:
            continue

    print("  [WARN] All Binance mirrors failed for 24h tickers")
    return {}


# ---------------------------------------------------------------------------
# Fallback: CoinGecko
# ---------------------------------------------------------------------------

def _fetch_coingecko_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch prices from CoinGecko as fallback (maps XXXUSDT -> xxx -> coingecko id)."""
    import requests

    # Simple mapping of base symbols to CoinGecko IDs
    KNOWN_IDS = {
        "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
        "SOL": "solana", "ADA": "cardano", "XRP": "ripple",
        "DOGE": "dogecoin", "DOT": "polkadot", "AVAX": "avalanche-2",
        "MATIC": "matic-network", "LINK": "chainlink", "NEAR": "near",
        "FET": "fetch-ai", "DUSK": "dusk-network", "ONT": "ontology",
        "DEGO": "dego-finance", "ENA": "ethena", "FIL": "filecoin",
        "ATOM": "cosmos", "UNI": "uniswap", "AAVE": "aave",
        "LTC": "litecoin", "SHIB": "shiba-inu", "ARB": "arbitrum",
        "OP": "optimism", "SUI": "sui", "APT": "aptos",
    }

    base_to_orig = {}
    cg_ids = []
    for sym in symbols:
        s = sym.upper()
        for suffix in ("USDT", "BUSD", "USDC", "USD"):
            if s.endswith(suffix):
                base = s[:-len(suffix)]
                break
        else:
            base = s
        cg_id = KNOWN_IDS.get(base)
        if cg_id:
            base_to_orig[cg_id] = sym
            cg_ids.append(cg_id)

    if not cg_ids:
        return {}

    prices = {}
    try:
        ids_str = ",".join(cg_ids[:50])
        r = requests.get(
            f"{COINGECKO_BASE}/simple/price",
            params={"ids": ids_str, "vs_currencies": "usd"},
            timeout=HTTP_TIMEOUT
        )
        r.raise_for_status()
        data = r.json()
        for cg_id, orig_sym in base_to_orig.items():
            if cg_id in data and "usd" in data[cg_id]:
                prices[orig_sym] = float(data[cg_id]["usd"])
    except Exception as e:
        print(f"  [CoinGecko] Failed: {e}")

    return prices


# ---------------------------------------------------------------------------
# Fallback: KuCoin
# ---------------------------------------------------------------------------

def _fetch_kucoin_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch prices from KuCoin as fallback."""
    import requests

    prices = {}
    try:
        r = requests.get(
            f"{KUCOIN_BASE}/api/v1/market/allTickers",
            timeout=HTTP_TIMEOUT
        )
        r.raise_for_status()
        data = r.json()
        tickers = data.get("data", {}).get("ticker", [])

        # Build KuCoin symbol map: BTC-USDT -> BTCUSDT
        kucoin_map = {}
        for t in tickers:
            kc_sym = t.get("symbol", "")
            price = float(t.get("last", 0))
            if price > 0 and "-USDT" in kc_sym:
                binance_equiv = kc_sym.replace("-", "")
                kucoin_map[binance_equiv] = price

        for sym in symbols:
            binance_sym = _normalize_to_binance(sym)
            if binance_sym and binance_sym in kucoin_map:
                prices[sym] = kucoin_map[binance_sym]
    except Exception as e:
        print(f"  [KuCoin] Failed: {e}")

    return prices


# ---------------------------------------------------------------------------
# Fallback: CryptoCompare
# ---------------------------------------------------------------------------

def _fetch_cryptocompare_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch prices from CryptoCompare as final fallback."""
    import requests

    prices = {}
    bases = set()
    sym_to_base = {}
    for sym in symbols:
        s = sym.upper()
        for suffix in ("USDT", "BUSD", "USDC", "USD"):
            if s.endswith(suffix):
                base = s[:-len(suffix)]
                break
        else:
            base = s
        bases.add(base)
        sym_to_base[sym] = base

    if not bases:
        return {}

    try:
        fsyms = ",".join(list(bases)[:50])
        r = requests.get(
            f"{CRYPTOCOMPARE_BASE}/pricemulti",
            params={"fsyms": fsyms, "tsyms": "USD"},
            timeout=HTTP_TIMEOUT
        )
        r.raise_for_status()
        data = r.json()
        for sym, base in sym_to_base.items():
            if base in data and "USD" in data[base]:
                prices[sym] = float(data[base]["USD"])
    except Exception as e:
        print(f"  [CryptoCompare] Failed: {e}")

    return prices


# ---------------------------------------------------------------------------
# Fetch prices with full failover chain
# ---------------------------------------------------------------------------

def fetch_prices_with_failover(symbols: list[str]) -> dict[str, float]:
    """Fetch prices using Binance (4 mirrors) -> CoinGecko -> KuCoin -> CryptoCompare."""
    # 1. Binance batch (gets all symbols in one call)
    all_binance = _fetch_all_binance_prices()
    prices = {}
    for sym in symbols:
        binance_sym = _normalize_to_binance(sym)
        if binance_sym and binance_sym in all_binance:
            prices[sym] = all_binance[binance_sym]
        elif sym in all_binance:
            prices[sym] = all_binance[sym]

    print(f"  [Binance] Got prices for {len(prices)}/{len(symbols)} symbols")

    missing = [s for s in symbols if s not in prices]
    if not missing:
        return prices

    # 2. CoinGecko fallback
    cg_prices = _fetch_coingecko_prices(missing)
    prices.update(cg_prices)
    if cg_prices:
        print(f"  [CoinGecko] Got {len(cg_prices)} more prices")

    missing = [s for s in symbols if s not in prices]
    if not missing:
        return prices

    # 3. KuCoin fallback
    kc_prices = _fetch_kucoin_prices(missing)
    prices.update(kc_prices)
    if kc_prices:
        print(f"  [KuCoin] Got {len(kc_prices)} more prices")

    missing = [s for s in symbols if s not in prices]
    if not missing:
        return prices

    # 4. CryptoCompare fallback
    cc_prices = _fetch_cryptocompare_prices(missing)
    prices.update(cc_prices)
    if cc_prices:
        print(f"  [CryptoCompare] Got {len(cc_prices)} more prices")

    final_missing = [s for s in symbols if s not in prices]
    if final_missing:
        print(f"  [WARN] No price for {len(final_missing)} symbols: "
              f"{', '.join(final_missing[:10])}")

    return prices


# ---------------------------------------------------------------------------
# yfinance fallback for non-crypto (stocks, forex)
# ---------------------------------------------------------------------------

def _fetch_yfinance_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch prices for non-Binance symbols using yfinance."""
    if not symbols:
        return {}
    prices = {}
    try:
        import yfinance as yf
        tickers = yf.Tickers(" ".join(symbols))
        for sym in symbols:
            try:
                ticker = tickers.tickers.get(sym)
                if ticker:
                    info = ticker.fast_info
                    price = getattr(info, "last_price", None)
                    if price and price > 0:
                        prices[sym] = float(price)
            except Exception:
                pass
    except ImportError:
        pass
    except Exception:
        pass
    return prices


# ---------------------------------------------------------------------------
# Core: force-close breached picks
# ---------------------------------------------------------------------------

def force_close_all(dry_run: bool = False) -> dict:
    """Force-close all picks that have breached TP/SL, are stale, or are duplicates.

    Also backfills missing data: created_at, volume_ratio, htf_confirmation.

    Returns summary dict with counts.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # Load data
    active = _load_json(ACTIVE_PICKS_FILE)
    if not isinstance(active, list):
        print("[FORCE CLOSE] No active picks found")
        return {"closed": 0, "active": 0}

    closed = _load_json(CLOSED_PICKS_FILE)
    if not isinstance(closed, list):
        closed = []

    total_before = len(active)
    print(f"[FORCE CLOSE] Loaded {total_before} active picks, {len(closed)} closed picks")

    # -----------------------------------------------------------------------
    # Step 0: Deduplicate picks by ID
    # -----------------------------------------------------------------------
    seen_ids = set()
    deduped = []
    dupes_removed = 0
    for pick in active:
        pid = pick.get("id", "")
        if pid and pid in seen_ids:
            dupes_removed += 1
            continue
        if pid:
            seen_ids.add(pid)
        deduped.append(pick)
    active = deduped
    if dupes_removed:
        print(f"  [DEDUP] Removed {dupes_removed} duplicate picks")

    # -----------------------------------------------------------------------
    # Step 1: Backfill missing created_at
    # -----------------------------------------------------------------------
    backfilled_created = 0
    for pick in active:
        if not pick.get("created_at"):
            # Try timestamp field first, then entry_date
            ts = pick.get("timestamp")
            if ts:
                pick["created_at"] = ts
            elif pick.get("entry_date"):
                pick["created_at"] = pick["entry_date"] + "T00:00:00+00:00"
            else:
                pick["created_at"] = now_iso
            backfilled_created += 1
    if backfilled_created:
        print(f"  [BACKFILL] Set created_at on {backfilled_created} picks")

    # -----------------------------------------------------------------------
    # Step 2: Collect symbols and fetch prices
    # -----------------------------------------------------------------------
    crypto_symbols = []
    yf_symbols = []
    for pick in active:
        sym = pick.get("symbol", "")
        cat = (pick.get("category") or "").lower()
        if not sym:
            continue
        if cat in ("forex", "stocks", "stock", "equity", "etf",
                    "commodity", "bond", "penny", "index"):
            yf_symbols.append(sym)
        elif "=X" in sym.upper() or "=F" in sym.upper() or "^" in sym.upper():
            yf_symbols.append(sym)
        else:
            crypto_symbols.append(sym)

    crypto_symbols = list(set(crypto_symbols))
    yf_symbols = list(set(yf_symbols))

    print(f"  Fetching prices for {len(crypto_symbols)} crypto + {len(yf_symbols)} non-crypto symbols...")

    # Fetch crypto prices with full failover
    price_map = fetch_prices_with_failover(crypto_symbols)

    # Fetch non-crypto prices via yfinance
    if yf_symbols:
        yf_prices = _fetch_yfinance_prices(yf_symbols)
        price_map.update(yf_prices)
        if yf_prices:
            print(f"  [yfinance] Got {len(yf_prices)} non-crypto prices")

    # -----------------------------------------------------------------------
    # Step 2b: Fetch 24h tickers for volume_ratio backfill
    # -----------------------------------------------------------------------
    ticker_24h = _fetch_binance_24h_tickers()
    vol_backfilled = 0

    # -----------------------------------------------------------------------
    # Step 3: Check TP/SL and close breached picks
    # -----------------------------------------------------------------------
    still_active = []
    newly_closed = []
    tp_closed = 0
    sl_closed = 0
    stale_closed = 0
    forex_expired = 0

    for pick in active:
        sym = pick.get("symbol", "")
        entry = pick.get("entry_price")
        if not entry or entry <= 0:
            still_active.append(pick)
            continue

        # Get live price
        live_price = price_map.get(sym)

        # Backfill volume_ratio if missing
        if not pick.get("volume_ratio"):
            binance_sym = _normalize_to_binance(sym)
            if binance_sym and binance_sym in ticker_24h:
                td = ticker_24h[binance_sym]
                qv = td.get("quoteVolume", 0)
                # Use quote volume / 1M as rough volume ratio
                # (proper avg would need historical data; this is a reasonable proxy)
                if qv > 0:
                    # Approximate: if quoteVolume > 10M USDT, it's high volume
                    pick["volume_ratio"] = round(qv / 5_000_000, 2)
                    vol_backfilled += 1

        # Backfill htf_confirmation if missing
        if not pick.get("htf_confirmation"):
            pick["htf_confirmation"] = "neutral"

        if live_price is None or live_price <= 0:
            # No price available -- check if stale
            _check_stale(pick, now, still_active, newly_closed)
            if pick not in newly_closed:
                # Still couldn't close -- check stale by age
                pass  # _check_stale already handled it
            continue

        # Update current price
        pick["current_price"] = live_price
        pick["last_checked"] = now_iso

        direction = (pick.get("direction") or pick.get("signal_type") or "LONG").upper()
        is_long = direction in ("BUY", "LONG")

        tp = pick.get("take_profit")
        sl = pick.get("stop_loss")

        # Calculate PnL
        if is_long:
            pnl_pct = (live_price - entry) / entry * 100
        else:
            pnl_pct = (entry - live_price) / entry * 100

        pick["pnl_pct"] = round(pnl_pct, 4)
        pick["unrealized_pnl_pct"] = round(pnl_pct / 100, 6)

        # Check TP hit
        tp_hit = False
        if tp and tp > 0:
            if is_long:
                tp_hit = live_price >= tp
            else:
                tp_hit = live_price <= tp

        # Check SL hit
        sl_hit = False
        if sl and sl > 0:
            if is_long:
                sl_hit = live_price <= sl
            else:
                sl_hit = live_price >= sl

        if tp_hit:
            pick["exit_reason"] = "TP_HIT"
            # Exit at TP level (not live_price which may have overshot)
            pick["exit_price"] = tp
            pick["exit_date"] = now_iso
            pick["status"] = "CLOSED"
            pick["closed_at"] = now_iso
            # Recalculate PnL at TP level for accurate accounting
            if is_long:
                tp_pnl = round((tp - entry) / entry, 4)
            else:
                tp_pnl = round((entry - tp) / entry, 4)
            pick["pnl_pct"] = tp_pnl
            pick["_actual_exit_price"] = live_price  # Record actual price for audit
            newly_closed.append(pick)
            tp_closed += 1
            print(f"  [TP HIT] {sym} entry={entry} tp={tp} cur={live_price} "
                  f"PnL={tp_pnl:+.2f}% [{pick.get('strategy', '?')}]")
        elif sl_hit:
            pick["exit_reason"] = "SL_HIT"
            # Exit at SL level (not live_price which may have gapped far beyond SL)
            # This prevents micro-cap gaps from causing 5-11x larger losses than intended
            pick["exit_price"] = sl
            pick["exit_date"] = now_iso
            pick["status"] = "CLOSED"
            pick["closed_at"] = now_iso
            # Recalculate PnL at SL level — this is the INTENDED max loss
            if is_long:
                sl_pnl = round((sl - entry) / entry, 4)
            else:
                sl_pnl = round((entry - sl) / entry, 4)
            pick["pnl_pct"] = sl_pnl
            pick["_actual_exit_price"] = live_price  # Record actual price for audit
            pick["_slippage_pct"] = round(abs(live_price - sl) / sl * 100, 2)
            newly_closed.append(pick)
            sl_closed += 1
            print(f"  [SL HIT] {sym} entry={entry} sl={sl} cur={live_price} "
                  f"PnL={sl_pnl:+.2f}% slippage={pick['_slippage_pct']:.1f}% [{pick.get('strategy', '?')}]")
        else:
            # --- Forex time-based expiry (48h max hold) ---
            # Forex moves 0.3-0.8%/day; if TP not hit in 48h, the edge is gone.
            # This fixes the 0% close rate where picks sat open for weeks.
            is_forex = (
                (pick.get("category") or "").lower() == "forex"
                or (pick.get("asset_class") or "").upper() == "FOREX"
                or "=X" in sym.upper()
            )
            if is_forex:
                created_str = pick.get("created_at") or pick.get("timestamp") or ""
                created_dt = None
                if created_str:
                    try:
                        if "T" in created_str:
                            created_dt = datetime.fromisoformat(
                                created_str.replace("Z", "+00:00"))
                        else:
                            created_dt = datetime.strptime(
                                created_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        pass
                if created_dt and (now - created_dt).total_seconds() > FOREX_MAX_HOLD_HOURS * 3600:
                    pick["exit_reason"] = "FOREX_TIME_EXIT"
                    pick["exit_price"] = live_price
                    pick["exit_date"] = now_iso
                    pick["status"] = "CLOSED"
                    pick["closed_at"] = now_iso
                    pick["pnl_pct"] = round(pnl_pct, 4)
                    hours_held = round((now - created_dt).total_seconds() / 3600, 1)
                    newly_closed.append(pick)
                    forex_expired += 1
                    print(f"  [FOREX EXPIRY] {sym} held {hours_held}h > {FOREX_MAX_HOLD_HOURS}h "
                          f"PnL={pnl_pct:+.2f}% [{pick.get('strategy', '?')}]")
                    continue

            # Check stale (>7 days without meaningful price movement or update)
            _check_stale(pick, now, still_active, newly_closed)
            if pick in newly_closed:
                stale_closed += 1
            # else it was added to still_active by _check_stale

    if vol_backfilled:
        print(f"  [BACKFILL] Set volume_ratio on {vol_backfilled} picks")

    htf_backfilled = sum(1 for p in still_active + newly_closed
                         if p.get("htf_confirmation") == "neutral")
    if htf_backfilled:
        print(f"  [BACKFILL] Set htf_confirmation='neutral' on picks missing it")

    # -----------------------------------------------------------------------
    # Step 4: Save results
    # -----------------------------------------------------------------------
    summary = {
        "total_before": total_before,
        "dupes_removed": dupes_removed,
        "tp_closed": tp_closed,
        "sl_closed": sl_closed,
        "stale_closed": stale_closed,
        "forex_expired": forex_expired,
        "total_closed": len(newly_closed),
        "still_active": len(still_active),
        "backfilled_created_at": backfilled_created,
        "backfilled_volume_ratio": vol_backfilled,
    }

    print(f"\n  SUMMARY: {len(newly_closed)} closed (TP={tp_closed}, SL={sl_closed}, "
          f"stale={stale_closed}, forex_expiry={forex_expired}), "
          f"{len(still_active)} still active, {dupes_removed} dupes removed")

    if dry_run:
        print("\n  [DRY RUN] No files written.")
        return summary

    # Save updated active picks
    _save_json(ACTIVE_PICKS_FILE, still_active)
    print(f"  Saved {len(still_active)} active picks")

    # Append closed picks
    if newly_closed:
        closed.extend(newly_closed)
        # Deduplicate closed by ID
        seen_closed_ids = set()
        deduped_closed = []
        for p in closed:
            pid = p.get("id", "")
            if pid and pid in seen_closed_ids:
                continue
            if pid:
                seen_closed_ids.add(pid)
            deduped_closed.append(p)
        _save_json(CLOSED_PICKS_FILE, deduped_closed)
        print(f"  Saved {len(deduped_closed)} total closed picks "
              f"(+{len(newly_closed)} new)")

    return summary


def _check_stale(pick: dict, now: datetime,
                 still_active: list, newly_closed: list):
    """Check if a pick is stale (>STALE_DAYS_THRESHOLD days old with no price data)."""
    entry_date_str = pick.get("entry_date") or pick.get("timestamp") or ""
    entry_dt = None
    if entry_date_str:
        try:
            if "T" in entry_date_str:
                entry_dt = datetime.fromisoformat(
                    entry_date_str.replace("Z", "+00:00"))
            else:
                entry_dt = datetime.strptime(
                    entry_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass

    is_old = entry_dt and (now - entry_dt).days >= STALE_DAYS_THRESHOLD
    has_no_price = not pick.get("current_price")

    if is_old and has_no_price:
        pick["exit_reason"] = "STALE_NO_DATA"
        pick["exit_date"] = now.isoformat()
        pick["exit_price"] = pick.get("entry_price", 0)
        pick["status"] = "CLOSED"
        pick["closed_at"] = now.isoformat()
        pick["pnl_pct"] = 0.0
        newly_closed.append(pick)
        sym = pick.get("symbol", "?")
        strat = pick.get("strategy", "?")
        print(f"  [STALE] Closing {sym} ({strat}): "
              f"open since {entry_date_str}, never price-checked, >{STALE_DAYS_THRESHOLD}d old")
    elif pick not in still_active and pick not in newly_closed:
        still_active.append(pick)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Force-close breached TP/SL picks")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only, don't write files")
    args = parser.parse_args()

    print("=" * 60)
    print("  Force-Close Breached Picks")
    print("=" * 60)
    start = time.time()

    summary = force_close_all(dry_run=args.dry_run)

    elapsed = time.time() - start
    print(f"\n  Completed in {elapsed:.1f}s")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    main()
