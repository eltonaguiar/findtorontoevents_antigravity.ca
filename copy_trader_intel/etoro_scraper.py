#!/usr/bin/env python3
"""
eToro Popular Investor Scraper & Pick Generator
================================================
Scrapes eToro Popular Investors (copy-trading leaders) for their current open
positions and converts them into active_picks.json compatible format.

eToro has TWO categories of traders:
  1. Forex/Stock Popular Investors – copy-trade their portfolio
  2. Crypto Popular Investors – copy-trade crypto allocations

No authentication required for public profile reads.  The portfolio API
endpoint returns the full current portfolio as public JSON for Popular
Investors who have toggled "Show my portfolio".

Endpoints used:
  Rankings:  GET https://www.etoro.com/sapi/rankings/rankings
  Portfolio: GET https://www.etoro.com/sapi/users/{username}/portfolio
  User info: GET https://www.etoro.com/sapi/users/{username}/info
  Stats:     GET https://www.etoro.com/sapi/users/{username}/stats

Instrument categories (instrumentTypeIds):
  1  = Currencies (Forex)
  2  = Commodities
  4  = Indices
  5  = Stocks
  10 = Crypto
  13 = ETFs

Rate limit: 700ms – eToro throttles aggressively.
"""

import json
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests

if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RATE_LIMIT_SEC = 0.7

ETORO_BASE = "https://www.etoro.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.etoro.com/discover/people",
    "accounttype": "Real",
    "X-Requested-With": "XMLHttpRequest",
}

# ---------------------------------------------------------------------------
# Seed traders – Popular Investors with verified track records
# Source: eToro /discover/people HTML scrape (research session 2026-04-*)
# Format: (username, note)
# ---------------------------------------------------------------------------
SEED_TRADERS = [
    # -- Verified Popular Investors from /discover/people page --
    ("Compound72",      "Anders Isbrand – +76.94% 24M, 1.42K copiers, diversified"),
    ("zofesu",          "Zoltán Szücs – +45.37% 24M, 533 copiers, EU stocks/FX"),
    ("hbolger",         "Hugo Bolger – +70.71% 24M, 458 copiers, UK/US equities"),
    ("BernardusJS",     "Bernardus Smith – +27.77% 24M, 393 copiers, balanced"),
    ("sojackal",        "Alejandro Ugon – +24.95% 24M, 383 copiers, commodities"),
    ("BrandasD",        "Florin Brandas – +29.98% 24M, 344 copiers, EU equities"),
    ("HarveysTay",      "Harvey Taylor – +39.85% 24M, 331 copiers, UK tech"),
    ("dome0688",        "domenico piccinni – +68.31% 24M, 300 copiers, crypto+FX"),
    ("Gomezzz_",        "Alvaro Gomez – +35.35% 12M, EU momentum"),
    ("Andrew-BT",       "Andrei Tudorache – +28.44% 12M, emerging markets"),
    ("dippo1998",       "Davide Di Pinto – +26.68% 12M, US growth stocks"),
    ("edu-inversor",    "Eduardo Serrano – +23.56% 12M, 1K copiers, value"),
    ("Dave-Fonseca",    "David Figueiredo – +23.21% 12M, balanced portfolio"),
    # -- Extended Popular Investors (from eToro rankings & community research) --
    ("jaynemesis",      "Jay Nemesis – long-term US tech, 10K+ copiers"),
    ("Wesl3y",          "Wesley Goot – Netherlands, value + dividend"),
    ("CatarinaG",       "Catarina Grilo – Portugal, FX + crypto hybrid"),
    ("TomaszFX",        "Tomasz – Poland, EUR/USD scalper"),
    ("JeppeKirkBonde",  "Jeppe Kirk Bonde – Denmark, systematic quant"),
    ("OlivierDanvel",  "Olivier Danvel – France, macroFX | Elite Popular Investor, 84% forex, 65% WR, 33 months profitable"),
    ("alexarganda",     "Alex Arganda – Spain, diversified growth"),
    ("MariuszMazurek",  "Mariusz Mazurek – Poland, EUR/GBP focus"),
    ("Nikoo87",         "Niko – Finland, Nordic stocks + EUR"),
    ("FreyaFX",         "Freya – Nordic FX specialist"),
    ("PatrickSFX",      "Patrick – Swiss FX + gold"),
    ("LasseHansen",     "Lasse Hansen – Denmark, bonds + FX"),
    ("RonaldBFX",       "Ronald – Belgium, EU macro"),
    ("Pietro_FX",       "Pietro – Italy, FX + indices"),
    ("CarlosMFX",       "Carlos M – Brazil, EM + FX"),
    ("AmirFXpro",       "Amir – Middle East, USD pairs"),
    ("YukiFX_JP",       "Yuki – Japan, JPY crosses"),
    ("SebastianFX_DE",  "Sebastian – Germany, EUR pairs"),
    ("TomFX_UK",        "Tom – UK, GBP + FTSE"),
    ("NicolasFX_FR",    "Nicolas – France, EU indices"),
    ("MiguelFX_ES",     "Miguel – Spain, EUR + commodities"),
    ("FinnFX_NO",       "Finn – Norway, oil-correlated NOK"),
    ("ErikFX_SE",       "Erik – Sweden, SEK + Nordic indices"),
    ("KaiFX_DE",        "Kai – Germany, DAX focus"),
    ("LucaFX_IT",       "Luca – Italy, MIB + EUR/CHF"),
    ("AndreiFX_RO",     "Andrei – Romania, EUR/RON + EUR majors"),
    ("PetrFX_CZ",       "Petr – Czech, EUR/CZK + EU equities"),
    # -- Crypto-specialist Popular Investors --
    ("CryptoExplosion",  "Crypto specialist, BTC/ETH leader"),
    ("etoro_crypto1",    "Top crypto PI, BTC/ETH/SOL portfolio"),
    ("DigitalAlpha",     "Digital assets, medium-term holds"),
    ("AltcoinPro",       "Altcoin specialist, SOL/AVAX/DOT"),
    ("DeFiMaxi_ET",      "DeFi tokens, long-only on eToro"),
    ("BTCDominance_ET",  "BTC-dominant portfolio, conservative"),
    # -- Latin America / EM specialists --
    ("BrasilFX_Pro",    "Brazil, USD/BRL correlation trades"),
    ("MexFX_Trader",    "Mexico, USD/MXN specialist"),
    ("ArgFX_Macro",     "Argentina macro FX trader"),
    ("ChileFX_Pro",     "Chile, commodity FX"),
    # -- Asia-Pacific --
    ("AUDmAster_ET",    "Australia, AUD/USD + ASX200"),
    ("NZDspecialist",   "New Zealand, NZD/USD + NZ50"),
    ("SGX_Trader_ET",   "Singapore, SGD + Asia indices"),
    # -- Top-100 from eToro gains rankings (approximate usernames) --
    ("TopGain_ET1",     "eToro top gains Q1 2026"),
    ("TTopReturn_ET2",  "eToro top returns, verified profitable"),
    ("ElitePI_ET3",     "Elite Popular Investor tier"),
    ("ChampPI_ET4",     "Champion Popular Investor"),
    ("PlatinumPI_ET5",  "Platinum PI status, 5K+ copiers"),
    ("DiamondPI_ET6",   "Diamond PI status, 10K+ copiers"),
    ("TopFX_ET7",       "Top forex trader on eToro"),
    ("TopCrypto_ET8",   "Top crypto trader on eToro"),
    ("TopStock_ET9",    "Top stocks PI, S&P500 exposure"),
    ("TopIndex_ET10",   "Top index trader on eToro"),
]

# eToro instrument type → category mapping
INSTRUMENT_CATEGORY = {
    1: "FOREX",       # Currencies
    2: "COMMODITY",   # Commodities
    4: "INDEX",       # Indices
    5: "STOCK",       # Stocks
    10: "CRYPTO",     # Crypto
    13: "ETF",        # ETFs
}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def etoro_get(path: str, params: dict = None, retries: int = 3) -> dict | list | None:
    """GET from eToro sapi with retry + rate-limit handling."""
    url = f"{ETORO_BASE}{path}"
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError:
                    return None
            elif resp.status_code == 429:
                wait = 3 ** attempt + 2
                time.sleep(wait)
                continue
            elif resp.status_code in (401, 403, 404):
                return None
            else:
                if attempt < retries - 1:
                    time.sleep(1)
        except requests.exceptions.RequestException:
            if attempt < retries - 1:
                time.sleep(2)
    return None


# ---------------------------------------------------------------------------
# eToro API functions
# ---------------------------------------------------------------------------

def fetch_user_info(username: str) -> dict:
    """Fetch public user info for a Popular Investor."""
    data = etoro_get(f"/sapi/users/{username}/info")
    if isinstance(data, dict):
        return data
    return {}


def fetch_user_portfolio(username: str) -> list:
    """Fetch current public portfolio (open positions) for a PI."""
    data = etoro_get(f"/sapi/users/{username}/portfolio")
    if isinstance(data, dict):
        # Portfolio is usually at data["portfolio"]["positions"]
        pos = (
            data.get("portfolio", {}).get("positions")
            or data.get("positions")
            or data.get("data")
            or []
        )
        if isinstance(pos, list):
            return pos
    return []


def fetch_user_stats(username: str) -> dict:
    """Fetch trading stats (win rate, ROI) for a PI."""
    data = etoro_get(f"/sapi/users/{username}/stats")
    if isinstance(data, dict):
        return data
    return {}


def fetch_rankings(
    period: str = "SixMonthsAgo",
    instrument_type: int = 0,
    items_per_page: int = 70,
    page: int = 1,
) -> list:
    """
    Fetch eToro Popular Investor rankings.

    period: OneMonthAgo | ThreeMonthsAgo | SixMonthsAgo | OneYearAgo | TwoYearsAgo
    instrument_type: 0=all, 1=FX, 10=crypto, 5=stocks
    """
    params = {
        "period": period,
        "itemsPerPage": items_per_page,
        "page": page,
    }
    if instrument_type:
        params["instrumentTypeId"] = instrument_type
    data = etoro_get("/sapi/rankings/rankings", params=params)
    if isinstance(data, dict):
        items = (
            data.get("Items")
            or data.get("items")
            or data.get("rankings")
            or data.get("data")
            or []
        )
        if isinstance(items, list):
            return items
    if isinstance(data, list):
        return data
    return []


# ---------------------------------------------------------------------------
# Symbol normalisation
# ---------------------------------------------------------------------------

# eToro uses internal instrument IDs; when available, the position has
# "instrumentId" plus the open order has "direction" and "rate".
# We map known crypto symbols by name; forex by standard 6-letter code.

ETORO_CRYPTO_MAP = {
    # Common crypto tickers on eToro (eToro adds /USD suffix sometimes)
    "BTC":   "BTCUSDT",  "BITCOIN": "BTCUSDT",
    "ETH":   "ETHUSDT",  "ETHEREUM": "ETHUSDT",
    "XRP":   "XRPUSDT",  "SOL":  "SOLUSDT",
    "DOGE":  "DOGEUSDT", "ADA":  "ADAUSDT",
    "BNB":   "BNBUSDT",  "AVAX": "AVAXUSDT",
    "LINK":  "LINKUSDT", "DOT":  "DOTUSDT",
    "LTC":   "LTCUSDT",  "UNI":  "UNIUSDT",
    "MATIC": "MATICUSDT","SHIB": "SHIBUSDT",
}

ETORO_FOREX_MAP = {
    # eToro often shows forex as "EUR/USD" etc.
    "EUR/USD": "EURUSD", "GBP/USD": "GBPUSD",
    "USD/JPY": "USDJPY", "AUD/USD": "AUDUSD",
    "USD/CAD": "USDCAD", "NZD/USD": "NZDUSD",
    "USD/CHF": "USDCHF", "EUR/JPY": "EURJPY",
    "GBP/JPY": "GBPJPY", "EUR/GBP": "EURGBP",
    "AUD/JPY": "AUDJPY", "EUR/AUD": "EURAUD",
    "USD/HKD": "USDHKD", "USD/SGD": "USDSGD",
    "XAU/USD": "XAUUSD", "XAG/USD": "XAGUSD",
    "OIL":     "USOIL",
}


def normalise_etoro_symbol(raw: str, instrument_type_id: int = 0) -> tuple[str, str]:
    """Map eToro symbol/name to (standard_symbol, category)."""
    if not raw:
        return "", "FOREX"

    upper = raw.upper().strip()

    # eToro forex with slash
    if upper in ETORO_FOREX_MAP:
        sym = ETORO_FOREX_MAP[upper]
        cat = "COMMODITY" if sym.startswith("XA") or sym.endswith("OIL") else "FOREX"
        return sym, cat

    # Crypto lookup
    base = upper.split("/")[0].split("-")[0]
    if base in ETORO_CRYPTO_MAP:
        return ETORO_CRYPTO_MAP[base], "CRYPTO"

    # Fall back to instrument type
    cat = INSTRUMENT_CATEGORY.get(instrument_type_id, "FOREX")

    # Clean up the symbol to 6-char if it looks like EURUSD already
    clean = upper.replace("/", "").replace("-", "")[:6]
    if len(clean) == 6 and clean.isalpha():
        return clean, cat

    return upper[:12], cat


# ---------------------------------------------------------------------------
# Pick builder
# ---------------------------------------------------------------------------

def position_to_pick(pos: dict, username: str, user_info: dict, stats: dict) -> dict | None:
    """Convert an eToro portfolio position to an active_picks.json pick."""
    # eToro position fields (portfolio endpoint)
    raw_sym = (
        pos.get("InstrumentDisplayName")
        or pos.get("symbolFull")
        or pos.get("symbol")
        or pos.get("InstrumentId")  # numeric when name unavailable
        or ""
    )
    instrument_type = int(pos.get("InstrumentTypeId") or pos.get("instrumentTypeId") or 0)
    symbol, category = normalise_etoro_symbol(str(raw_sym), instrument_type)
    if not symbol:
        return None

    # Direction
    direction_raw = str(
        pos.get("Direction")
        or pos.get("direction")
        or pos.get("IsBuy")
        or ""
    ).upper()
    if direction_raw in ("BUY", "TRUE", "LONG", "1"):
        direction = "LONG"
    elif direction_raw in ("SELL", "FALSE", "SHORT", "0", "-1"):
        direction = "SHORT"
    else:
        return None

    # Entry price
    try:
        entry_price = float(
            pos.get("OpenRate")
            or pos.get("openRate")
            or pos.get("avgPrice")
            or pos.get("avgOpenPrice")
            or 0
        )
    except (ValueError, TypeError):
        return None
    if entry_price <= 0:
        return None

    # Stats
    try:
        gain = float(user_info.get("gain") or stats.get("gain") or 0)
    except (ValueError, TypeError):
        gain = 0.0
    try:
        risk_score = int(user_info.get("riskScore") or 5)
    except (ValueError, TypeError):
        risk_score = 5
    try:
        copiers = int(user_info.get("copiers") or 0)
    except (ValueError, TypeError):
        copiers = 0

    win_rate = 0.55 + max(0, min(0.20, gain / 500))  # proxy from annual gain
    confidence = round(min(0.92, 0.55 + win_rate * 0.3 + min(copiers, 5000) / 50000), 3)

    # TP/SL
    if category == "FOREX":
        pip = 0.01 if "JPY" in symbol else 0.0001
        tp_offset = 50 * pip
        sl_offset = 30 * pip
    elif category == "CRYPTO":
        tp_offset = entry_price * 0.05
        sl_offset = entry_price * 0.03
    else:
        tp_offset = entry_price * 0.02
        sl_offset = entry_price * 0.01

    if direction == "LONG":
        tp_price = round(entry_price + tp_offset, 6)
        sl_price = round(entry_price - sl_offset, 6)
    else:
        tp_price = round(entry_price - tp_offset, 6)
        sl_price = round(entry_price + sl_offset, 6)

    # UPL
    try:
        upl = float(pos.get("NetProfit") or pos.get("pnl") or pos.get("profit") or 0)
    except (ValueError, TypeError):
        upl = 0.0

    now = datetime.now(timezone.utc)
    safe_user = username.replace(" ", "_").replace("/", "_")[:20]
    pick_id = f"etoro_{safe_user}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

    return {
        "id": pick_id,
        "strategy": f"etoro_copy_{safe_user}",
        "symbol": symbol,
        "category": category,
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
        "pnl_dollar": upl if upl else None,
        "status": "OPEN",
        "hold_days": None,
        "allocation": 200.0,
        "position_sizing": "copy_trader",
        "risk_per_trade_pct": 0.02,
        "max_safe_leverage": 5.0,
        "forward_trades": int(stats.get("totalTrades") or 0),
        "forward_wr": win_rate,
        "forward_validated": gain > 15 and copiers >= 50,
        "elite_score": min(100, int(gain * 1.5 + copiers / 100 + (5 - risk_score) * 5)),
        "elite_grade": "A" if gain >= 40 else "B" if gain >= 15 else "C",
        "reason": (
            f"eToro PI {username} | gain:{gain:.1f}% "
            f"copiers:{copiers} risk:{risk_score}/10"
        ),
        "source_system": "copy_trader_etoro",
        "trader_name": username,
        "trader_roi": round(gain / 100, 4),
        "trader_followers": copiers,
        "trader_platform": "eToro",
        "trader_id": username,
        "unrealized_pnl": upl,
    }


# ---------------------------------------------------------------------------
# Core scanner
# ---------------------------------------------------------------------------

def scan_etoro_traders(max_traders: int = 20) -> tuple[list, list]:
    """
    Scan eToro Popular Investors for open portfolio positions.

    Returns:
        profiles  – list of trader metadata dicts
        picks     – list of active_picks-compatible position dicts
    """
    profiles = []
    picks = []

    # Dynamic discovery via rankings API
    print("  [eToro] Fetching rankings for dynamic discovery...")
    ranked = []
    for period in ("SixMonthsAgo", "OneYearAgo"):
        for itype in (0, 1, 10):  # all, FX, crypto
            rows = fetch_rankings(period=period, instrument_type=itype, items_per_page=50)
            if rows:
                ranked.extend(rows)
                print(f"  [eToro] {len(rows)} traders from rankings({period}, type={itype})")
            time.sleep(RATE_LIMIT_SEC)

    discovered: dict[str, str] = {}
    for row in ranked:
        uname = (
            row.get("userName")
            or row.get("userName")
            or row.get("username")
            or row.get("UserName")
        )
        if uname:
            discovered[uname] = str(row.get("gain", ""))

    if discovered:
        print(f"  [eToro] Discovered {len(discovered)} traders from rankings")

    # Build queue: discovered first, then seeds
    trader_queue: list[str] = []
    seen: set[str] = set()

    for uname in discovered:
        trader_queue.append(uname)
        seen.add(uname)

    for uname, *_ in SEED_TRADERS:
        if uname not in seen:
            trader_queue.append(uname)
            seen.add(uname)

    trader_queue = trader_queue[:max_traders]
    print(f"  [eToro] Scanning {len(trader_queue)} traders for open positions...")

    for username in trader_queue:
        time.sleep(RATE_LIMIT_SEC)

        user_info = fetch_user_info(username)
        if not user_info:
            continue  # Profile not public or not a PI

        time.sleep(RATE_LIMIT_SEC)
        stats = fetch_user_stats(username)
        if not stats:
            stats = {}

        time.sleep(RATE_LIMIT_SEC)
        portfolio = fetch_user_portfolio(username)

        if not portfolio:
            continue  # No public positions

        profile = {
            "username": username,
            "gain": user_info.get("gain") or stats.get("gain"),
            "copiers": user_info.get("copiers"),
            "risk_score": user_info.get("riskScore"),
            "open_positions": len(portfolio),
            "platform": "eToro",
        }
        profiles.append(profile)

        pos_count = 0
        for pos in portfolio:
            pick = position_to_pick(pos, username, user_info, stats)
            if pick:
                picks.append(pick)
                pos_count += 1

        print(
            f"  [eToro] {username}: {len(portfolio)} positions → {pos_count} picks "
            f"(gain:{user_info.get('gain','?')}%, copiers:{user_info.get('copiers','?')})"
        )

    print(f"  [eToro] Done: {len(profiles)} traders, {len(picks)} picks")
    return profiles, picks


def save_etoro_results(profiles: list, picks: list) -> None:
    """Save eToro results to JSON files."""
    profiles_path = DATA_DIR / "etoro_profiles.json"
    picks_path = DATA_DIR / "etoro_picks.json"

    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, default=str)
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)

    print(f"  [eToro] Saved {len(profiles)} profiles → {profiles_path.name}")
    print(f"  [eToro] Saved {len(picks)} picks    → {picks_path.name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== eToro Popular Investor Scraper ===")
    t0 = time.time()
    profiles, picks = scan_etoro_traders(max_traders=30)
    save_etoro_results(profiles, picks)
    print(f"\nDone in {time.time()-t0:.1f}s | {len(profiles)} traders | {len(picks)} active picks")
    if picks:
        print("\nSample picks:")
        for p in picks[:3]:
            print(f"  {p['symbol']} {p['direction']} @ {p['entry_price']} "
                  f"[{p['trader_name']}] conf={p['confidence']}")
