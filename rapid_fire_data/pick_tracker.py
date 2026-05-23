#!/usr/bin/env python3
"""Rapid Fire pick lifecycle tracker — checks TP/SL/time exits with multi-source failover.

# ATR Trailing Stop (added 2026-03-16):
# Activation: +1.5% unrealized PnL
# Trail distance: 1.5x ATR (or 2% fallback)
# Purpose: Capture 15-30% more profit in trends per Kimi research
"""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
ACTIVE_FILE = os.path.join(DIR, "active_picks.json")
CLOSED_FILE = os.path.join(DIR, "closed_picks.json")
MAX_HOLD_HOURS = 24
STABLECOIN_SYMBOLS = {"USDCUSDT", "USDTUSDC", "USD1USDT", "USDTUSD1", "USDCUSD1"}
_UA = {"User-Agent": "pick-tracker/1.0"}

# ATR trailing stop constants
TRAIL_ACTIVATION_PCT = 1.5   # Activate trailing stop at +1.5% unrealized PnL
TRAIL_ATR_MULT = 1.5         # Trail distance = 1.5x ATR
TRAIL_FALLBACK_PCT = 0.02    # 2% of price if ATR unavailable

# CoinGecko ID mapping for symbols without direct exchange API support
_CG_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin", "SOL": "solana",
    "XRP": "ripple", "ADA": "cardano", "AVAX": "avalanche-2", "DOT": "polkadot",
    "LINK": "chainlink", "MATIC": "matic-network", "LTC": "litecoin", "DOGE": "dogecoin",
    "SHIB": "shiba-inu", "UNI": "uniswap", "AAVE": "aave", "ATOM": "cosmos",
    "NEAR": "near", "FIL": "filecoin", "ICP": "internet-computer", "TRX": "tron",
    "ETC": "ethereum-classic", "BCH": "bitcoin-cash", "ALGO": "algorand",
    "HBAR": "hedera-hashgraph", "VET": "vechain", "PEPE": "pepe", "ZEC": "zcash",
    "APT": "aptos", "OP": "optimism", "ARB": "arbitrum", "SUI": "sui",
    "SEI": "sei-network", "INJ": "injective-protocol", "FTM": "fantom",
    "RUNE": "thorchain", "GRT": "the-graph", "MKR": "maker", "STX": "blockstack",
    "FLOKI": "floki", "BONK": "bonk", "WIF": "dogwifcoin", "FET": "fetch-ai",
    "RNDR": "render-token", "IMX": "immutable-x", "TIA": "celestia",
    "CRV": "curve-dao-token", "LDO": "lido-dao", "SAND": "the-sandbox",
    "MANA": "decentraland", "DASH": "dash", "THETA": "theta-token", "CHZ": "chiliz",
}

def _http_json(url, timeout=10, headers=None):
    """GET JSON with error handling. Returns None on any failure."""
    hdrs = dict(_UA)
    if headers:
        hdrs.update(headers)
    try:
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Price source 1: Binance (4 mirrors)
# ---------------------------------------------------------------------------
def _fetch_binance_prices():
    """Try all 4 Binance endpoints. Returns {symbol: price} or None."""
    for host in ("api.binance.com", "api1.binance.com", "api2.binance.com", "api.binance.us"):
        data = _http_json(f"https://{host}/api/v3/ticker/price")
        if data and isinstance(data, list) and len(data) > 10:
            print(f"  [price] Binance ({host}) OK — {len(data)} tickers")
            return {t["symbol"]: float(t["price"]) for t in data if "symbol" in t and "price" in t}
    return None

# ---------------------------------------------------------------------------
# Price source 2: Bybit
# ---------------------------------------------------------------------------
def _fetch_bybit_prices():
    """Fetch spot tickers from Bybit. Returns {symbol: price} or None."""
    data = _http_json("https://api.bybit.com/v5/market/tickers?category=spot", timeout=10)
    if not data or data.get("retCode") != 0:
        return None
    items = data.get("result", {}).get("list", [])
    if not items:
        return None
    prices = {}
    for t in items:
        sym = t.get("symbol", "")
        last = t.get("lastPrice", "")
        if sym and last:
            try:
                prices[sym] = float(last)
            except ValueError:
                pass
    if prices:
        print(f"  [price] Bybit OK — {len(prices)} tickers")
    return prices if prices else None

# ---------------------------------------------------------------------------
# Price source 3: CoinGecko (per-symbol, batched)
# ---------------------------------------------------------------------------
def _fetch_coingecko_prices(symbols):
    """Fetch prices from CoinGecko for known symbols. Returns {symbol: price} or None."""
    # Build reverse map: coingecko_id -> [BTCUSDT, ...]
    needed = {}
    for sym in symbols:
        base = sym.replace("USDT", "").replace("BUSD", "")
        cg_id = _CG_MAP.get(base)
        if cg_id:
            needed.setdefault(cg_id, []).append(sym)
    if not needed:
        return None
    # CoinGecko accepts comma-separated IDs (batch up to 250)
    ids_str = ",".join(needed.keys())
    headers = {}
    cg_key = os.environ.get("COINGECKO_API_KEY", "")
    if cg_key:
        headers["x-cg-demo-api-key"] = cg_key
    data = _http_json(
        f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd",
        timeout=15, headers=headers if headers else None,
    )
    if not data or not isinstance(data, dict):
        return None
    prices = {}
    for cg_id, syms in needed.items():
        usd = data.get(cg_id, {}).get("usd")
        if usd:
            for sym in syms:
                prices[sym] = float(usd)
    if prices:
        print(f"  [price] CoinGecko OK — {len(prices)} prices")
    return prices if prices else None

# ---------------------------------------------------------------------------
# Price source 4: Yahoo Finance (for equities/forex, crypto fallback)
# ---------------------------------------------------------------------------
def _fetch_yahoo_price(symbol):
    """Fetch a single price from Yahoo Finance. Returns float or None."""
    base = symbol.replace("USDT", "").replace("BUSD", "")
    yf_sym = f"{base}-USD"
    data = _http_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_sym}?interval=1d&range=1d")
    if not data:
        return None
    try:
        meta = data["chart"]["result"][0]["meta"]
        return float(meta["regularMarketPrice"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None

# ---------------------------------------------------------------------------
# Confidence-weighted consensus price fetcher
# ---------------------------------------------------------------------------
OUTLIER_THRESHOLD = 0.005  # 0.5% deviation from median = outlier

def _compute_consensus(prices_by_source):
    """Compute weighted consensus from multiple source prices.

    Args:
        prices_by_source: dict of {source_name: price}

    Returns:
        dict with 'price', 'confidence', 'sources', 'outliers'
    """
    if not prices_by_source:
        return None
    if len(prices_by_source) == 1:
        source, price = next(iter(prices_by_source.items()))
        return {'price': price, 'confidence': 0.33, 'sources': 1, 'outliers': []}

    vals = list(prices_by_source.values())
    sorted_vals = sorted(vals)
    median_price = sorted_vals[len(sorted_vals) // 2]

    # Flag outliers (>0.5% from median)
    clean = {s: p for s, p in prices_by_source.items()
             if abs(p - median_price) / median_price <= OUTLIER_THRESHOLD}
    outliers = [s for s in prices_by_source if s not in clean]

    if not clean:
        # All flagged as outliers — fall back to median
        clean = prices_by_source

    consensus_price = sum(clean.values()) / len(clean)
    confidence = round(len(clean) / 3, 2)  # 0.33 to 1.0 (3 bulk sources)

    return {
        'price': consensus_price,
        'confidence': confidence,
        'sources': len(clean),
        'outliers': outliers,
    }


def fetch_prices_with_confidence(symbols):
    """Fetch from all bulk sources, compute weighted consensus price.

    Returns:
        dict of {symbol: {'price': float, 'confidence': float,
                          'sources': int, 'outliers': list}}
    """
    # Fetch from all bulk sources in parallel (they each return full ticker lists)
    binance = _fetch_binance_prices() or {}
    bybit = _fetch_bybit_prices() or {}
    coingecko = _fetch_coingecko_prices(symbols) or {}

    source_counts = {'binance': len(binance), 'bybit': len(bybit), 'coingecko': len(coingecko)}
    active_sources = sum(1 for v in source_counts.values() if v > 0)
    print(f"  [price] Sources responding: {active_sources}/3 — "
          f"Binance={source_counts['binance']}, Bybit={source_counts['bybit']}, "
          f"CoinGecko={source_counts['coingecko']}")

    all_prices = {}
    for sym in symbols:
        prices_for_sym = {}
        if sym in binance:
            prices_for_sym['binance'] = binance[sym]
        if sym in bybit:
            prices_for_sym['bybit'] = bybit[sym]
        if sym in coingecko:
            prices_for_sym['coingecko'] = coingecko[sym]

        if prices_for_sym:
            result = _compute_consensus(prices_for_sym)
            if result:
                all_prices[sym] = result
                if result['outliers']:
                    print(f"  [price] OUTLIER {sym}: {', '.join(result['outliers'])} "
                          f"deviated >{OUTLIER_THRESHOLD*100}% from median")

    # Yahoo fallback for symbols with no data from bulk sources
    missing = [s for s in symbols if s not in all_prices]
    if missing:
        print(f"  [price] {len(missing)} symbols missing from bulk sources, trying Yahoo...")
        for sym in missing:
            p = _fetch_yahoo_price(sym)
            if p:
                all_prices[sym] = {'price': p, 'confidence': 0.33, 'sources': 1, 'outliers': []}

    if not all_prices:
        print("  [price] ALL SOURCES FAILED")
    else:
        low_conf = sum(1 for v in all_prices.values() if v['confidence'] < 0.5)
        if low_conf:
            print(f"  [price] {low_conf}/{len(all_prices)} symbols have low confidence (single source)")

    return all_prices


def fetch_all_prices(symbols):
    """Backward-compatible wrapper: returns {symbol: price} using consensus.

    Also prints confidence warnings for low-confidence prices.
    """
    consensus = fetch_prices_with_confidence(symbols)
    return {sym: data['price'] for sym, data in consensus.items()}

# ---------------------------------------------------------------------------
# Core logic (unchanged)
# ---------------------------------------------------------------------------
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def parse_time(ts_str):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(ts_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc)

def _fetch_atr(symbol, period=14):
    """Fetch ATR from Binance hourly klines. Returns absolute ATR value or None."""
    for host in ("api.binance.com", "api1.binance.com", "data-api.binance.vision", "api.binance.us"):
        try:
            url = f"https://{host}/api/v3/klines?symbol={symbol}&interval=1h&limit={period + 1}"
            data = _http_json(url, timeout=5)
            if not data or len(data) < period + 1:
                continue
            trs = []
            for i in range(1, len(data)):
                high, low, prev_close = float(data[i][2]), float(data[i][3]), float(data[i - 1][4])
                trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
            return sum(trs[-period:]) / period
        except Exception:
            continue
    return None


def update_trailing_stop(pick, current_price):
    """Update ATR trailing stop for a pick. Modifies pick in-place.

    Returns 'TRAIL_SL' if trailing SL was hit, else None.
    """
    direction = pick.get("direction", "LONG").upper()
    entry = pick.get("entry_price", 0)
    if not entry:
        return None

    # Calculate unrealized PnL
    if direction == "LONG":
        pnl_pct = (current_price - entry) / entry * 100
    else:
        pnl_pct = (entry - current_price) / entry * 100

    # Track peak price
    peak = pick.get("_trail_peak_price", current_price)
    if direction == "LONG":
        peak = max(peak, current_price)
    else:
        peak = min(peak, current_price)
    pick["_trail_peak_price"] = peak

    # Check activation threshold
    if pnl_pct < TRAIL_ACTIVATION_PCT and not pick.get("_trail_active"):
        return None

    # Activate trailing stop if not already active
    if not pick.get("_trail_active"):
        symbol = pick.get("symbol", "")
        atr = _fetch_atr(symbol)
        if atr and atr > 0:
            trail_dist = TRAIL_ATR_MULT * atr
            method = "ATR_1.5x_dynamic"
        else:
            trail_dist = TRAIL_FALLBACK_PCT * current_price
            method = "pct_2_fallback"
        pick["_trail_active"] = True
        pick["_trail_dist"] = trail_dist
        pick["_trail_metadata"] = {
            "method": method,
            "atr": round(atr, 6) if atr else 0,
            "trail_dist": round(trail_dist, 6),
            "activation_pnl_pct": round(pnl_pct, 2),
        }
        print(f"  TRAIL_ACTIVATED {pick.get('symbol')} dist={trail_dist:.6f} method={method}")

    trail_dist = pick.get("_trail_dist", TRAIL_FALLBACK_PCT * current_price)
    orig_sl = pick.get("sl_price") or pick.get("stop_loss")

    # Compute new trailing SL
    if direction == "LONG":
        trail_sl = peak - trail_dist
        if orig_sl:
            trail_sl = max(trail_sl, orig_sl)
        # Check if trail SL hit
        if current_price <= trail_sl:
            pick["_trail_exit_peak_pnl"] = round((peak - entry) / entry * 100, 2)
            pick["_trail_exit_actual_pnl"] = round((current_price - entry) / entry * 100, 2)
            return "TRAIL_SL"
        # Ratchet SL upward
        pick["sl_price"] = round(trail_sl, 8)
    else:  # SHORT
        trail_sl = peak + trail_dist
        if orig_sl:
            trail_sl = min(trail_sl, orig_sl)
        # Check if trail SL hit
        if current_price >= trail_sl:
            pick["_trail_exit_peak_pnl"] = round((entry - peak) / entry * 100, 2)
            pick["_trail_exit_actual_pnl"] = round((entry - current_price) / entry * 100, 2)
            return "TRAIL_SL"
        # Ratchet SL downward
        pick["sl_price"] = round(trail_sl, 8)

    pick["peak_pnl_pct"] = round(max(pnl_pct, pick.get("peak_pnl_pct", 0)), 2)
    return None


def check_tp_sl(pick, current_price):
    direction = pick.get("direction", "LONG").upper()
    entry = pick.get("entry_price", 0)
    tp = pick.get("tp_price_1_5") or pick.get("take_profit")
    sl = pick.get("sl_price") or pick.get("stop_loss")
    if not entry or (not tp and not sl):
        return None
    if direction == "LONG":
        if tp and current_price >= tp:
            return "TP_HIT", tp, round((tp - entry) / entry * 100, 2)
        if sl and current_price <= sl:
            return "SL_HIT", sl, round((sl - entry) / entry * 100, 2)
    else:
        if tp and current_price <= tp:
            return "TP_HIT", tp, round((entry - tp) / entry * 100, 2)
        if sl and current_price >= sl:
            return "SL_HIT", sl, round((entry - sl) / entry * 100, 2)
    return None

def make_closed_record(pick, exit_reason, exit_price, pnl_pct):
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "symbol": pick.get("symbol", ""),
        "direction": pick.get("direction", "LONG").upper(),
        "strategy": pick.get("strategy", "unknown"),
        "entry_price": pick.get("entry_price", 0),
        "take_profit": pick.get("tp_price_1_5") or pick.get("take_profit", 0),
        "stop_loss": pick.get("sl_price") or pick.get("stop_loss", 0),
        "exit_price": exit_price, "pnl_pct": pnl_pct,
        "exit_reason": exit_reason, "status": "CLOSED",
        "opened_at": pick.get("scan_time", pick.get("opened_at", now_iso)),
        "closed_at": now_iso, "source_system": "rapid_fire",
    }

def resolve_duplicates(picks):
    by_symbol, to_close = {}, []
    for p in picks:
        sym = p.get("symbol", "")
        direction = p.get("direction", "LONG").upper()
        if sym in by_symbol:
            prev = by_symbol[sym]
            if prev.get("direction", "").upper() != direction:
                older = prev if parse_time(prev.get("scan_time", "")) <= parse_time(p.get("scan_time", "")) else p
                to_close.append(older)
                by_symbol[sym] = p if older is prev else prev
            else:
                by_symbol[sym] = p
        else:
            by_symbol[sym] = p
    closed_ids = set(id(x) for x in to_close)
    return [p for p in picks if id(p) not in closed_ids], to_close

def main():
    now = datetime.now(timezone.utc)
    active = load_json(ACTIVE_FILE)
    closed = load_json(CLOSED_FILE)
    active = [p for p in active if p.get("symbol", "") not in STABLECOIN_SYMBOLS]
    active, dupes = resolve_duplicates(active)
    for dupe in dupes:
        closed.append(make_closed_record(dupe, "TIME_EXIT", dupe.get("entry_price", 0), 0.0))
        print(f"  DUPE_CLOSE {dupe.get('symbol')} {dupe.get('direction')} (contradictory direction)")
    # Fetch prices with confidence-weighted consensus
    symbols = list({p.get("symbol", "") for p in active if p.get("symbol")})
    price_data = fetch_prices_with_confidence(symbols)
    if not price_data:
        print("WARNING: No prices available from any source. Saving duplicate resolutions only.")
    still_active, newly_closed = [], 0
    for pick in active:
        symbol = pick.get("symbol", "")
        sym_data = price_data.get(symbol)
        if sym_data is None:
            still_active.append(pick)
            continue
        current_price = sym_data['price']
        # Annotate pick with price confidence metadata
        pick['_price_confidence'] = sym_data['confidence']
        pick['_price_sources'] = sym_data['sources']
        if sym_data['outliers']:
            pick['_price_outliers'] = sym_data['outliers']
        if sym_data['confidence'] < 0.5:
            pick['_low_confidence_note'] = 'low price confidence — single source only'
            print(f"  [confidence] {symbol}: LOW ({sym_data['confidence']}) — single source")
        if current_price is None:
            still_active.append(pick)
            continue
        # ATR trailing stop check (before fixed TP/SL)
        trail_result = update_trailing_stop(pick, current_price)
        if trail_result == "TRAIL_SL":
            entry = pick.get("entry_price", 0)
            d = pick.get("direction", "LONG").upper()
            pnl = round(((current_price - entry) / entry * 100) * (1 if d == "LONG" else -1), 2) if entry else 0.0
            rec = make_closed_record(pick, "TRAIL_SL", current_price, pnl)
            rec["peak_pnl_pct"] = pick.get("_trail_exit_peak_pnl", 0)
            rec["trail_metadata"] = pick.get("_trail_metadata", {})
            closed.append(rec)
            newly_closed += 1
            peak_pnl = pick.get("_trail_exit_peak_pnl", 0)
            print(f"  TRAIL_SL {symbol} {pick.get('direction')} pnl={pnl:+.2f}% (peak={peak_pnl:+.2f}%)")
            continue
        result = check_tp_sl(pick, current_price)
        if result:
            reason, exit_px, pnl = result
            closed.append(make_closed_record(pick, reason, exit_px, pnl))
            newly_closed += 1
            print(f"  {reason} {symbol} {pick.get('direction')} pnl={pnl:+.2f}%")
            continue
        opened = parse_time(pick.get("scan_time", pick.get("opened_at", "")))
        if (now - opened).total_seconds() > MAX_HOLD_HOURS * 3600:
            entry = pick.get("entry_price", 0)
            d = pick.get("direction", "LONG").upper()
            pnl = round(((current_price - entry) / entry * 100) * (1 if d == "LONG" else -1), 2) if entry else 0.0
            closed.append(make_closed_record(pick, "TIME_EXIT", current_price, pnl))
            newly_closed += 1
            print(f"  TIME_EXIT {symbol} {pick.get('direction')} pnl={pnl:+.2f}%")
            continue
        still_active.append(pick)
    save_json(ACTIVE_FILE, still_active)
    save_json(CLOSED_FILE, closed)
    print(f"\nPick Tracker Summary:")
    print(f"  Active: {len(still_active)} | Newly closed: {newly_closed} | Total closed: {len(closed)}")

if __name__ == "__main__":
    main()
