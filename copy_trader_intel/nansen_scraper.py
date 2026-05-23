#!/usr/bin/env python3
"""
Nansen Smart Money Scraper & Pick Generator
============================================
Uses the Nansen API token-screener endpoint with `only_smart_money: true`
to discover what tokens smart money wallets are buying and selling on-chain.

API Endpoint (confirmed working):
  POST https://api.nansen.ai/api/v1/token-screener
  Headers: Content-Type: application/json, apiKey: <NANSEN_API_KEY>
  Body: {
    "chains": ["ethereum", "solana", "base"],
    "timeframe": "24h",
    "filters": {"only_smart_money": true, "token_age_days": {"max": 365, "min": 1}},
    "order_by": [{"field": "buy_volume", "direction": "DESC"}],
    "pagination": {"page": 1, "per_page": 100}
  }

Response fields per token:
  chain, token_address, token_symbol, token_age_days, market_cap_usd,
  liquidity, price_usd, price_change, fdv, fdv_mc_ratio, nof_traders,
  buy_volume, sell_volume, volume, netflow, inflow_fdv_ratio, outflow_fdv_ratio

Rate limits (from response headers):
  - 20 req/sec, 300 req/min
  - Credit-based billing per endpoint call
  - x-ratelimit-remaining-credit-fails tracks failed credit deductions

Other endpoints tested (all 404 — not available on this API tier):
  - GET  /api/v1/chains
  - POST /api/v1/wallet-profiler
  - POST /api/v1/smart-money
  - GET  /api/v1/smart-money/transactions

Pick generation logic:
  - Positive netflow (buy > sell) → LONG signal
  - Negative netflow (sell > buy) → SHORT signal
  - Confidence based on: nof_traders, netflow magnitude, volume, market_cap
  - Filters: market_cap >= $100K, nof_traders >= 1, volume > $100
  - Maps token_symbol to USDT pairs for Binance price fetching
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# -- Windows UTF-8 fix --
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

NANSEN_API_URL = "https://api.nansen.ai/api/v1/token-screener"

# Supported chains (confirmed working: ethereum, solana; base sometimes empty)
CHAINS = ["ethereum", "solana", "base"]

# Rate limit: be conservative to preserve credits
RATE_LIMIT_SEC = 3.0

# Well-known token symbol → Binance USDT pair mapping
# Many DeFi/meme tokens won't be on Binance — those use Nansen's own price_usd
SYMBOL_TO_PAIR = {
    "BTC": "BTCUSDT", "WBTC": "BTCUSDT",
    "ETH": "ETHUSDT", "WETH": "ETHUSDT", "STETH": "ETHUSDT",
    "SOL": "SOLUSDT", "WSOL": "SOLUSDT",
    "BNB": "BNBUSDT", "WBNB": "BNBUSDT",
    "AVAX": "AVAXUSDT", "WAVAX": "AVAXUSDT",
    "MATIC": "MATICUSDT", "POL": "MATICUSDT",
    "ARB": "ARBUSDT",
    "OP": "OPUSDT",
    "DOGE": "DOGEUSDT",
    "SHIB": "SHIBUSDT",
    "PEPE": "PEPEUSDT",
    "LINK": "LINKUSDT",
    "UNI": "UNIUSDT",
    "AAVE": "AAVEUSDT",
    "MKR": "MKRUSDT",
    "CRV": "CRVUSDT",
    "LDO": "LDOUSDT",
    "APE": "APEUSDT",
    "NEAR": "NEARUSDT",
    "FTM": "FTMUSDT",
    "ATOM": "ATOMUSDT",
    "DOT": "DOTUSDT",
    "ADA": "ADAUSDT",
    "XRP": "XRPUSDT",
    "TRX": "TRXUSDT",
    "SUI": "SUIUSDT",
    "SEI": "SEIUSDT",
    "TIA": "TIAUSDT",
    "JUP": "JUPUSDT",
    "WIF": "WIFUSDT",
    "BONK": "BONKUSDT",
    "RENDER": "RENDERUSDT", "RNDR": "RENDERUSDT",
    "INJ": "INJUSDT",
    "FET": "FETUSDT",
    "PENDLE": "PENDLEUSDT",
    "ENA": "ENAUSDT",
    "W": "WUSDT",
    "ETHFI": "ETHFIUSDT",
    "EIGEN": "EIGENUSDT",
}

# Binance API mirrors (failover per project rules)
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api4.binance.com",
]


# ======================================================================
# API Key Loading
# ======================================================================

def _get_nansen_api_key() -> str:
    """
    Load Nansen API key from environment.
    Tries os.environ first, then Windows User-level env var via PowerShell.
    """
    key = os.environ.get("NANSEN_API_KEY", "")
    if key:
        return key

    # Windows fallback: read from User-level environment variable
    if sys.platform == "win32":
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[Environment]::GetEnvironmentVariable('NANSEN_API_KEY', 'User')"],
                capture_output=True, text=True, timeout=5
            )
            key = result.stdout.strip()
        except Exception:
            pass

    return key


# ======================================================================
# Nansen API Client
# ======================================================================

def _nansen_request(body: dict, retries: int = 3) -> dict:
    """
    POST to Nansen token-screener with retries and rate limit handling.
    Returns parsed JSON response or empty dict on failure.
    """
    api_key = _get_nansen_api_key()
    if not api_key:
        print("  [ERROR] No NANSEN_API_KEY found")
        return {}

    headers = {
        "Content-Type": "application/json",
        "apiKey": api_key,
    }

    for attempt in range(retries):
        try:
            resp = requests.post(
                NANSEN_API_URL, headers=headers, json=body, timeout=20
            )
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                # Rate limited — wait and retry
                wait = min(30, 5 * (attempt + 1))
                print(f"    [RATE LIMIT] 429 — waiting {wait}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
                continue
            elif resp.status_code == 403:
                # Credit exhaustion or auth issue
                try:
                    err = resp.json()
                    detail = err.get("detail", err.get("error", ""))
                except Exception:
                    detail = resp.text[:200]
                print(f"    [403] {detail}")
                if "credit" in str(detail).lower():
                    print("    Credits exhausted — cannot make more API calls this period")
                return {}
            else:
                print(f"    [HTTP {resp.status_code}] {resp.text[:200]}")
                if attempt < retries - 1:
                    time.sleep(2)
                continue
        except requests.exceptions.RequestException as e:
            print(f"    [NET ERROR] {e}")
            if attempt < retries - 1:
                time.sleep(2)
            continue

    return {}


def fetch_smart_money_tokens(
    order_field: str = "buy_volume",
    order_dir: str = "DESC",
    chains: list = None,
    timeframe: str = "24h",
    per_page: int = 100,
    page: int = 1,
) -> list:
    """
    Fetch tokens from Nansen token-screener with smart money filter.

    Args:
        order_field: buy_volume, sell_volume, volume, netflow, market_cap_usd
        order_dir: DESC or ASC
        chains: list of chains (default: ethereum, solana, base)
        timeframe: 24h (only confirmed working timeframe)
        per_page: results per page (max 100)
        page: page number

    Returns:
        List of token dicts with fields: chain, token_address, token_symbol,
        token_age_days, market_cap_usd, liquidity, price_usd, price_change,
        fdv, nof_traders, buy_volume, sell_volume, volume, netflow
    """
    body = {
        "chains": chains or CHAINS,
        "timeframe": timeframe,
        "filters": {
            "only_smart_money": True,
            "token_age_days": {"max": 365, "min": 1},
        },
        "order_by": [{"field": order_field, "direction": order_dir}],
        "pagination": {"page": page, "per_page": per_page},
    }

    data = _nansen_request(body)
    tokens = data.get("data", [])
    if isinstance(tokens, dict):
        tokens = tokens.get("items", tokens.get("tokens", []))
    return tokens if isinstance(tokens, list) else []


# ======================================================================
# Binance Price Fetching (with failover per project rules)
# ======================================================================

_price_cache = {}


def _fetch_binance_price(symbol: str) -> float:
    """Fetch live price from Binance with mirror failover. Uses cache."""
    if symbol in _price_cache:
        return _price_cache[symbol]

    for mirror in BINANCE_MIRRORS:
        try:
            resp = requests.get(
                f"{mirror}/api/v3/ticker/price",
                params={"symbol": symbol},
                timeout=5,
            )
            if resp.status_code == 200:
                price = float(resp.json().get("price", 0))
                if price > 0:
                    _price_cache[symbol] = price
                    return price
        except Exception:
            continue

    return 0.0


def _get_entry_price(token: dict) -> float:
    """
    Get entry price for a token. Tries Binance first (for tradeable pairs),
    falls back to Nansen's price_usd.
    """
    symbol_upper = token.get("token_symbol", "").upper()

    # Try mapping to Binance pair
    binance_pair = SYMBOL_TO_PAIR.get(symbol_upper, "")
    if not binance_pair and symbol_upper:
        # Try constructing pair directly
        binance_pair = f"{symbol_upper}USDT"

    if binance_pair:
        price = _fetch_binance_price(binance_pair)
        if price > 0:
            return price

    # Fallback: Nansen's own price
    return float(token.get("price_usd", 0))


def _map_to_usdt_pair(token_symbol: str) -> str:
    """Map a token symbol to its USDT trading pair."""
    upper = token_symbol.upper()
    if upper in SYMBOL_TO_PAIR:
        return SYMBOL_TO_PAIR[upper]
    return f"{upper}USDT"


# ======================================================================
# Pick Generation
# ======================================================================

def _calculate_confidence(token: dict, direction: str) -> float:
    """
    Calculate confidence score (0.50 - 0.95) based on smart money signals.

    Factors:
      - nof_traders: more smart money wallets = higher conviction
      - netflow magnitude relative to volume
      - market_cap: higher mcap = more reliable signal
      - buy/sell volume ratio
    """
    nof_traders = token.get("nof_traders", 1)
    buy_vol = token.get("buy_volume", 0)
    sell_vol = token.get("sell_volume", 0)
    volume = token.get("volume", 0)
    netflow = abs(token.get("netflow", 0))
    mcap = token.get("market_cap_usd", 0)

    # Base confidence
    conf = 0.55

    # +0.05 per additional smart money trader (up to +0.15)
    conf += min(0.15, (nof_traders - 1) * 0.05)

    # Netflow dominance: what % of volume is directional
    if volume > 0:
        flow_ratio = netflow / volume
        conf += min(0.10, flow_ratio * 0.15)

    # Market cap tier bonus
    if mcap >= 1_000_000_000:  # $1B+
        conf += 0.08
    elif mcap >= 100_000_000:  # $100M+
        conf += 0.05
    elif mcap >= 10_000_000:   # $10M+
        conf += 0.03

    # Buy/sell volume imbalance bonus
    if direction == "LONG" and buy_vol > 0 and sell_vol >= 0:
        ratio = buy_vol / max(sell_vol, 1)
        conf += min(0.07, (ratio - 1) * 0.02) if ratio > 1 else 0
    elif direction == "SHORT" and sell_vol > 0 and buy_vol >= 0:
        ratio = sell_vol / max(buy_vol, 1)
        conf += min(0.07, (ratio - 1) * 0.02) if ratio > 1 else 0

    return round(min(0.95, max(0.50, conf)), 3)


def token_to_pick(token: dict, direction: str, entry_price: float) -> dict:
    """Convert a Nansen smart money token into an active_picks.json compatible pick."""
    symbol = _map_to_usdt_pair(token.get("token_symbol", ""))
    if not symbol or entry_price <= 0:
        return None

    confidence = _calculate_confidence(token, direction)
    now = datetime.now(timezone.utc)

    # TP/SL calculation — wider for small-cap, tighter for large-cap
    mcap = token.get("market_cap_usd", 0)
    if mcap >= 1_000_000_000:
        tp_pct, sl_pct = 0.03, 0.02   # Large cap: 3% TP / 2% SL
    elif mcap >= 100_000_000:
        tp_pct, sl_pct = 0.05, 0.03   # Mid cap: 5% TP / 3% SL
    elif mcap >= 10_000_000:
        tp_pct, sl_pct = 0.08, 0.04   # Small cap: 8% TP / 4% SL
    else:
        tp_pct, sl_pct = 0.12, 0.06   # Micro cap: 12% TP / 6% SL

    if direction == "LONG":
        tp_price = round(entry_price * (1 + tp_pct), 8)
        sl_price = round(entry_price * (1 - sl_pct), 8)
    else:
        tp_price = round(entry_price * (1 - tp_pct), 8)
        sl_price = round(entry_price * (1 + sl_pct), 8)

    # Smart money metrics for the reason string
    nof_traders = token.get("nof_traders", 0)
    buy_vol = token.get("buy_volume", 0)
    sell_vol = token.get("sell_volume", 0)
    netflow = token.get("netflow", 0)
    chain = token.get("chain", "?")
    price_change = token.get("price_change", 0) * 100

    raw_symbol = token.get("token_symbol", "")
    safe_sym = raw_symbol.replace(" ", "_").replace("/", "_")[:20]
    pick_id = (f"nansen_sm_{safe_sym}::{symbol}::"
               f"{now.strftime('%Y-%m-%d_%H%M')}")

    return {
        "id": pick_id,
        "strategy": f"nansen_smart_money_{chain}",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": entry_price,
        "entry_date": now.strftime("%Y-%m-%d"),
        "take_profit": tp_price,
        "stop_loss": sl_price,
        "confidence": confidence,
        "ml_score": confidence,
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "pnl_pct": None,
        "pnl_dollar": None,
        "status": "OPEN",
        "hold_days": None,
        "allocation": 200.0,
        "position_sizing": "smart_money",
        "risk_per_trade_pct": 0.025,
        "max_safe_leverage": 3.0,
        "forward_trades": 0,
        "forward_wr": 0,
        "forward_validated": False,
        "elite_score": min(100, int(confidence * 100)),
        "elite_grade": "A" if confidence >= 0.80 else "B" if confidence >= 0.65 else "C",
        "reason": (
            f"Nansen Smart Money ({chain}) | {nof_traders} wallets | "
            f"Buy:${buy_vol:,.0f} Sell:${sell_vol:,.0f} Net:${netflow:,.0f} | "
            f"24h:{price_change:+.1f}%"
        ),
        "source_system": "nansen_smart_money",
        "nansen_chain": chain,
        "nansen_token_address": token.get("token_address", ""),
        "nansen_token_symbol": raw_symbol,
        "nansen_market_cap": token.get("market_cap_usd", 0),
        "nansen_liquidity": token.get("liquidity", 0),
        "nansen_fdv": token.get("fdv", 0),
        "nansen_nof_traders": nof_traders,
        "nansen_buy_volume": buy_vol,
        "nansen_sell_volume": sell_vol,
        "nansen_netflow": netflow,
        "nansen_price_change_24h": price_change,
        "nansen_token_age_days": token.get("token_age_days", 0),
        "timestamp": now.isoformat(),
    }


# ======================================================================
# Main Scanner
# ======================================================================

def scan_nansen(max_tokens: int = 50) -> tuple:
    """
    Main scan: fetch smart money token data from Nansen, generate picks.

    Strategy:
    1. Fetch tokens ordered by buy_volume DESC → LONG candidates
    2. Fetch tokens ordered by sell_volume DESC → SHORT candidates
    3. Also fetch by netflow DESC/ASC for strongest directional signals
    4. Deduplicate by token_address, keep strongest signal
    5. Filter: must have market_cap >= $100K, volume > $100
    6. Generate picks with confidence scores

    Returns (token_profiles, picks)
    """
    print("=" * 70)
    print("  NANSEN SMART MONEY SCRAPER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    api_key = _get_nansen_api_key()
    if not api_key:
        print("  [ERROR] NANSEN_API_KEY not set. Set it as a Windows User env var or in os.environ.")
        return [], []

    print(f"  API key: {api_key[:8]}...{api_key[-4:]}")
    print(f"  Chains: {', '.join(CHAINS)}")
    print(f"  Max tokens per query: {max_tokens}")

    # Collect all tokens from multiple queries
    all_tokens = {}  # keyed by token_address for dedup

    queries = [
        ("buy_volume", "DESC", "Smart money BUYING"),
        ("sell_volume", "DESC", "Smart money SELLING"),
        ("netflow", "DESC", "Strongest net INFLOW"),
        ("netflow", "ASC", "Strongest net OUTFLOW"),
    ]

    for field, direction, label in queries:
        print(f"\n  --- {label} (order: {field} {direction}) ---")
        tokens = fetch_smart_money_tokens(
            order_field=field,
            order_dir=direction,
            per_page=max_tokens,
        )

        if not tokens:
            print(f"    No data returned (rate limit or credits exhausted)")
            time.sleep(RATE_LIMIT_SEC)
            continue

        new_count = 0
        for t in tokens:
            addr = t.get("token_address", "")
            if addr and addr not in all_tokens:
                all_tokens[addr] = t
                new_count += 1
            elif addr in all_tokens:
                # Update with higher volume data if exists
                existing = all_tokens[addr]
                if t.get("volume", 0) > existing.get("volume", 0):
                    all_tokens[addr] = t

        print(f"    Fetched {len(tokens)} tokens, {new_count} new unique")
        for t in tokens[:5]:
            sym = t.get("token_symbol", "?")
            chain = t.get("chain", "?")
            buy = t.get("buy_volume", 0)
            sell = t.get("sell_volume", 0)
            net = t.get("netflow", 0)
            traders = t.get("nof_traders", 0)
            print(f"    {sym:12s} ({chain:8s}) "
                  f"buy=${buy:>10,.0f} sell=${sell:>10,.0f} "
                  f"net=${net:>10,.0f} traders={traders}")

        time.sleep(RATE_LIMIT_SEC)

    if not all_tokens:
        print("\n  [WARN] No tokens fetched — API may be rate-limited or credits exhausted")
        return [], []

    print(f"\n  Total unique tokens: {len(all_tokens)}")

    # -- Filter and classify tokens --
    long_candidates = []
    short_candidates = []

    for addr, token in all_tokens.items():
        mcap = token.get("market_cap_usd", 0)
        volume = token.get("volume", 0)
        netflow = token.get("netflow", 0)
        buy_vol = token.get("buy_volume", 0)
        sell_vol = token.get("sell_volume", 0)

        # Filter: minimum thresholds
        if volume < 100:
            continue  # Too low volume

        # Classify direction based on netflow
        if netflow > 0 and buy_vol > 0:
            long_candidates.append(token)
        elif netflow < 0 and sell_vol > 0:
            short_candidates.append(token)
        elif buy_vol > sell_vol:
            long_candidates.append(token)
        elif sell_vol > buy_vol:
            short_candidates.append(token)

    # Sort by absolute netflow (strongest signals first)
    long_candidates.sort(key=lambda t: t.get("netflow", 0), reverse=True)
    short_candidates.sort(key=lambda t: t.get("netflow", 0))  # Most negative first

    print(f"  LONG candidates: {len(long_candidates)}")
    print(f"  SHORT candidates: {len(short_candidates)}")

    # -- Generate picks --
    all_picks = []
    all_profiles = []

    # Process LONG candidates
    for token in long_candidates[:max_tokens]:
        entry_price = _get_entry_price(token)
        if entry_price <= 0:
            continue

        pick = token_to_pick(token, "LONG", entry_price)
        if pick:
            all_picks.append(pick)

        # Build profile
        all_profiles.append({
            "token_address": token.get("token_address", ""),
            "token_symbol": token.get("token_symbol", ""),
            "chain": token.get("chain", ""),
            "direction": "LONG",
            "market_cap_usd": token.get("market_cap_usd", 0),
            "liquidity": token.get("liquidity", 0),
            "buy_volume": token.get("buy_volume", 0),
            "sell_volume": token.get("sell_volume", 0),
            "netflow": token.get("netflow", 0),
            "nof_traders": token.get("nof_traders", 0),
            "price_usd": token.get("price_usd", 0),
            "price_change_24h": token.get("price_change", 0),
            "token_age_days": token.get("token_age_days", 0),
            "analysis_time": datetime.now(timezone.utc).isoformat(),
        })
        time.sleep(0.1)  # Gentle on Binance

    # Process SHORT candidates
    for token in short_candidates[:max_tokens]:
        entry_price = _get_entry_price(token)
        if entry_price <= 0:
            continue

        pick = token_to_pick(token, "SHORT", entry_price)
        if pick:
            all_picks.append(pick)

        all_profiles.append({
            "token_address": token.get("token_address", ""),
            "token_symbol": token.get("token_symbol", ""),
            "chain": token.get("chain", ""),
            "direction": "SHORT",
            "market_cap_usd": token.get("market_cap_usd", 0),
            "liquidity": token.get("liquidity", 0),
            "buy_volume": token.get("buy_volume", 0),
            "sell_volume": token.get("sell_volume", 0),
            "netflow": token.get("netflow", 0),
            "nof_traders": token.get("nof_traders", 0),
            "price_usd": token.get("price_usd", 0),
            "price_change_24h": token.get("price_change", 0),
            "token_age_days": token.get("token_age_days", 0),
            "analysis_time": datetime.now(timezone.utc).isoformat(),
        })
        time.sleep(0.1)

    print(f"\n  Generated {len(all_picks)} picks from {len(all_profiles)} tokens")
    longs = sum(1 for p in all_picks if p.get("direction") == "LONG")
    shorts = sum(1 for p in all_picks if p.get("direction") == "SHORT")
    print(f"  LONG: {longs} | SHORT: {shorts}")

    return all_profiles, all_picks


def save_nansen_results(profiles: list, picks: list):
    """Save Nansen results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    profiles_path = DATA_DIR / "nansen_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "nansen_smart_money",
            "token_count": len(profiles),
            "profiles": profiles,
        }, f, indent=2, default=str)
    print(f"  Saved {len(profiles)} token profiles to {profiles_path}")

    picks_path = DATA_DIR / "nansen_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return profiles_path, picks_path


# Alias for main.py compatibility
def run():
    """Run the Nansen smart money scanner (alias for scan_nansen)."""
    profiles, picks = scan_nansen(max_tokens=50)
    save_nansen_results(profiles, picks)
    return picks


if __name__ == "__main__":
    profiles, picks = scan_nansen(max_tokens=50)
    save_nansen_results(profiles, picks)
    print(f"\nDone. {len(picks)} Nansen smart money picks generated.")
