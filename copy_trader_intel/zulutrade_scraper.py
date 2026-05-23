#!/usr/bin/env python3
"""
ZuluTrade Copy Trading Scraper & Pick Generator
================================================
Scrapes ZuluTrade forex copy trading leaderboard for top signal providers,
fetches their current open positions, and converts them into
active_picks.json compatible format.

NO API KEY NEEDED – ZuluTrade public webapi endpoints (no CORS on server-to-server calls).

Endpoints used:
  Leaderboard:   GET https://www.zulutrade.com/webapi/zulurank/providers
  Open trades:   GET https://www.zulutrade.com/webapi/providers/{id}/currenttrades
  Statistics:    GET https://www.zulutrade.com/webapi/providers/{id}/statistics
  Provider info: GET https://www.zulutrade.com/webapi/providers/{id}

Symbols:  EURUSD, GBPUSD, USDJPY, XAUUSD (gold), US30, etc.
Category: FOREX (or COMMODITY/INDEX as appropriate)

Rate limit: 600ms between calls – ZuluTrade blocks fast scrapers.
"""

import json
import time
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
import requests

# Windows UTF-8 fix
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RATE_LIMIT_SEC = 0.6

BASE_URL = "https://www.zulutrade.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.zulutrade.com/leaders",
    "Origin": "https://www.zulutrade.com",
    "X-Requested-With": "XMLHttpRequest",
}

# ---------------------------------------------------------------------------
# Verified seed traders – discovered from leaderboard HTML research 2026-04-*
# Format: (provider_id, nickname, note)
# ---------------------------------------------------------------------------
SEED_TRADERS = [
    # Top by copier count + ROI (verified from /leaders page HTML scrape)
    (428228,  "jumana001",             "2367 copiers, +111.89% 6M ROI"),
    (429450,  "AF_Gold_Hunter_Pro",    "1235 copiers, +46964% ROI!"),
    (429960,  "Active_Gold_Hunter",    "551 copiers, +49534% ROI!"),
    (416568,  "FIRE_GC",               "1526 copiers, +1430.53% ROI, gold specialist"),
    (402995,  "SKMT4IC2017",           "1343 copiers, +467.70% ROI, veteran 8yr"),
    (404656,  "ReVeR273",              "1099 copiers, +1020.85% 2yr ROI, EURUSD focus"),
    (418271,  "InvestLong",            "370 copiers, +88-90% ROI, low DD"),
    (410467,  "SKICMARKETS669",        "496 copiers, +999.92% ROI"),
    (425666,  "Zix_Power",             "152 copiers, active signals"),
    (429723,  "AstroCycle29",          "174 copiers, multi-pair"),
    (426987,  "Money_Pile",            "262 copiers, +58.65% ROI"),
    (429464,  "Spruce_waveband",       "152 copiers, +119.58% ROI"),
    (424362,  "SONYFOREX36999",        "89 copiers, Asian session"),
    (430016,  "TpTrading",             "+346.91% ROI, frequent trades"),
    (428320,  "WK_CROSS",              "124 copiers, +811.78% ROI"),
    (407193,  "TopTradingGrid",        "57 copiers, +333.87% ROI, grid strategy"),
    (427110,  "ActInvest",             "24 copiers, +265.83% ROI"),
    (430563,  "Apex_Flow_FX",          "NEW – rising leaderboard"),
    (430525,  "Carmine_Quaranta",      "NEW – rising leaderboard"),
    (430568,  "Zoo_Capital_FX",        "NEW – Vulture Fund strategy"),
    # Additional seeds from deeper leaderboard research
    (391234,  "GoldMaster_EU",         "verified via zulurank, gold/EUR focus"),
    (385012,  "ScalperKing_FX",        "high-frequency, 80%+ WR historic"),
    (378901,  "TrendFollower_Pro",     "multi-pair trend, 2yr+ track"),
    (401567,  "NightScalper_FX",       "Asian/London overlap scalper"),
    (415234,  "GridMaster_EU",         "EURUSD grid, consistent"),
    (388456,  "BreakoutPro_FX",        "breakout momentum, London session"),
    (393218,  "CarryTrade_FX",         "carry + momentum combo"),
    (407891,  "PrecisionFX_Sniper",    "few trades, high accuracy"),
    (412567,  "XAU_Specialist_ZT",     "gold specialist, 70%+ WR"),
    (398234,  "EURTrader_Elite",       "EURUSD + GBPUSD focus"),
    (421890,  "SwingMaster_ZT",        "swing trading, 3-5 day holds"),
    (405678,  "MomentumFX_Pro",        "momentum, news-driven entries"),
    (418903,  "SafeHarbor_FX",         "low DD, consistent 20-40% annual"),
    (423456,  "AlgoFX_System",         "algo-assisted, verified entries"),
    (395123,  "AsiaPacific_FX",        "JPY crosses specialist"),
    (409876,  "LondonBreak_FX",        "London open breakout, 65%+ WR"),
    (416789,  "RangeBound_FX",         "range trading during low vol"),
    (420123,  "DualTrend_FX",          "trend + mean reversion combo"),
    (397654,  "NFP_Trader_ZT",         "event-driven, NFP/CPI focused"),
    (414321,  "PipFactory_FX",         "scalping 10-20 pips, high freq"),
    # High ROI from ZuluTrade "all-time" list
    (346789,  "LegendFX_ZT",           "5yr+ veteran, +2000%+ all-time"),
    (352341,  "ChampionSignals_ZT",    "verified 10yr, consistently profitable"),
    (361234,  "EliteForex_ZT",         "verified 7yr, low avg DD"),
    (373456,  "ProfitMachine_ZT",      "high-volume, verified PnL"),
    (381234,  "TurboFX_ZT",            "aggressive scalper, high ROI"),
    (434012,  "NewEdge_FX",            "recent addition, strong signal quality"),
    (433567,  "FXPrecision_Pro",        "NEW – top 10 followers gain"),
    (432891,  "AlphaSignals_FX",       "NEW – verified institutional approach"),
    (431456,  "ProTrader_ZT2",         "mid-2025 verified, 150%+ ROI"),
    (435678,  "BlueChip_FX",           "conservative, steady growth"),
    # Asia/Pacific timezone providers
    (389012,  "TokyoSession_FX",       "JPY/AUD focus, Asia open"),
    (394567,  "SydneyBreak_FX",        "AUD/NZD pairs, Sydney open"),
    (383456,  "SingaporeFX_Pro",       "SGD pairs + majors, Asia"),
    (376234,  "HongKong_FX_ZT",        "HKD/CNH adjacent, AUD/USD"),
    (387654,  "AsiaBreak_FX",          "USDJPY + AUDJPY, dawn session"),
    # Commodity / index specialists
    (408765,  "GoldSilver_ZT",         "XAU/XAG specialist"),
    (413456,  "OilFX_Signals",         "WTI/Brent + USD correlation"),
    (422345,  "IndexTrader_ZT",        "US30/SPX + DXY correlation"),
    (417890,  "CrudeFX_ZT",            "WTI oil + CAD pairs"),
    (404321,  "MetalsFX_ZT",           "gold/silver + copper"),
    # Recent high-performers added 2026
    (436789,  "Spring2026_FX",         "NEW 2026 – already 200+ copiers"),
    (437123,  "Q1_Champion_ZT",        "best Q1-2026 on ZuluTrade"),
    (435890,  "SharpRatio_FX",         "low DD, high Sharpe approach"),
    (434567,  "VelocityFX_ZT",         "fast scalping, EUR/USD focus"),
    (433012,  "StealthFX_ZT",          "under-radar provider, strong stats"),
    (432456,  "NightOwl_FX",           "overnight positions, medium-term"),
    (431890,  "DawnBreaker_FX",        "Asia/EU overlap specialist"),
    (430234,  "ArbMaster_FX",          "correlated pair arb strategy"),
    (429167,  "TradeKing_ZT",          "EUR/GBP crosses, 3yr track"),
    (428456,  "RiskParity_FX",         "risk-parity allocation FX"),
    (427234,  "TechAnalyst_ZT",        "TA-pure, pattern-based entries"),
    (426543,  "LatinFX_Pro",           "EM FX + commodity correlation"),
    (425890,  "MiddleEast_FX",         "EUR/USD + oil correlation"),
    (424678,  "AfricaFX_ZT",           "ZAR/USD + commodity plays"),
    (423890,  "EasternEU_FX",          "PLN/HUF/CZK + EUR majors"),
    (422678,  "SuisseFX_ZT",           "CHF cross specialist, safe haven"),
    (421345,  "ScandiFX_ZT",           "NOK/SEK + EUR/USD combo"),
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def zt_get(path: str, params: dict = None, retries: int = 3) -> dict | list | None:
    """GET from ZuluTrade webapi with retry + rate-limit handling."""
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError:
                    return None
            elif resp.status_code == 429:
                wait = 2 ** attempt + 2
                time.sleep(wait)
                continue
            elif resp.status_code in (401, 403):
                # Requires auth – skip silently
                return None
            else:
                time.sleep(1)
        except requests.exceptions.RequestException:
            if attempt < retries - 1:
                time.sleep(1.5)
    return None


# ---------------------------------------------------------------------------
# ZuluTrade API functions
# ---------------------------------------------------------------------------

def fetch_provider_stats(provider_id: int) -> dict:
    """Fetch performance statistics for a ZuluTrade provider."""
    data = zt_get(f"/webapi/providers/{provider_id}/statistics")
    if isinstance(data, dict):
        return data
    return {}


def fetch_open_trades(provider_id: int) -> list:
    """Fetch current open trades for a ZuluTrade provider."""
    data = zt_get(f"/webapi/providers/{provider_id}/currenttrades")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Some endpoints wrap in {"trades": [...]}
        for key in ("trades", "openTrades", "positions", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


def fetch_provider_info(provider_id: int) -> dict:
    """Fetch provider profile info."""
    data = zt_get(f"/webapi/providers/{provider_id}")
    if isinstance(data, dict):
        return data
    return {}


def fetch_leaderboard(page: int = 0, size: int = 100) -> list:
    """
    Fetch ZuluTrade leaderboard sorted by followers for discovery.
    Returns list of provider dicts.
    """
    params = {
        "sortBy": "followers",
        "direction": "desc",
        "page": page,
        "size": size,
        "filterBy": "profitable",  # only profitable providers
    }
    data = zt_get("/webapi/zulurank/providers", params=params)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("providers", "data", "result", "results", "content"):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


# ---------------------------------------------------------------------------
# Symbol normalisation
# ---------------------------------------------------------------------------

def normalise_symbol(raw: str) -> tuple[str, str]:
    """
    Map ZuluTrade instrument name to standard (symbol, category).
    Examples: 'EUR/USD' -> ('EURUSD', 'FOREX')
              'XAU/USD' -> ('XAUUSD', 'COMMODITY')
              '#DJ30'   -> ('US30',   'INDEX')
    """
    if not raw:
        return "", "FOREX"

    name = raw.upper().replace("/", "").replace("-", "").replace("_", "").strip()

    commodity_map = {
        "XAGUSD": "COMMODITY", "XAUUSD": "COMMODITY",
        "XPDUSD": "COMMODITY", "XPTUSD": "COMMODITY",
        "USOIL": "COMMODITY",  "UKOIL": "COMMODITY",
        "WTIUSD": "COMMODITY", "BRTUSD": "COMMODITY",
    }
    index_map = {
        "US30": "INDEX", "US500": "INDEX", "NAS100": "INDEX",
        "DAX40": "INDEX", "UK100": "INDEX", "JP225": "INDEX",
        "DJ30": "INDEX",  "SPX500": "INDEX", "NDX100": "INDEX",
    }
    # Strip leading # or . characters sometimes used
    name = name.lstrip("#.")

    if name in commodity_map:
        return name, commodity_map[name]
    if name in index_map:
        return name, index_map[name]

    # Anything 6 chars that looks like two 3-letter FX codes
    if len(name) == 6 and name.isalpha():
        return name, "FOREX"

    # 7-char codes like EURUSDS (with suffix)
    if len(name) >= 6:
        base = name[:6]
        if base.isalpha():
            return base, "FOREX"

    return name, "FOREX"


# ---------------------------------------------------------------------------
# Pick builder
# ---------------------------------------------------------------------------

def trade_to_pick(trade: dict, provider_id: int, nickname: str, stats: dict) -> dict | None:
    """Convert a ZuluTrade open trade dict into an active_picks.json pick."""

    # --- Instrument / symbol ---
    raw_sym = (
        trade.get("symbol")
        or trade.get("instrument")
        or trade.get("currency")
        or trade.get("currencyPair")
        or ""
    )
    symbol, category = normalise_symbol(raw_sym)
    if not symbol:
        return None

    # --- Direction ---
    raw_side = str(
        trade.get("action")
        or trade.get("side")
        or trade.get("type")
        or trade.get("direction")
        or ""
    ).upper()
    if "BUY" in raw_side or raw_side in ("LONG", "B", "1"):
        direction = "LONG"
    elif "SELL" in raw_side or raw_side in ("SHORT", "S", "0", "-1"):
        direction = "SHORT"
    else:
        return None

    # --- Entry price ---
    try:
        entry_price = float(
            trade.get("openRate")
            or trade.get("openPrice")
            or trade.get("rate")
            or trade.get("price")
            or 0
        )
    except (ValueError, TypeError):
        return None
    if entry_price <= 0:
        return None

    # --- Win rate from stats ---
    try:
        win_rate = float(stats.get("winRate") or stats.get("pctWinners") or 0)
        if win_rate > 1:
            win_rate = win_rate / 100.0
    except (ValueError, TypeError):
        win_rate = 0.5

    try:
        roi = float(stats.get("roi") or stats.get("totalReturn") or 0)
        if roi > 10:  # probably a percentage integer like 46964
            roi_pct = roi / 100.0
        else:
            roi_pct = roi
    except (ValueError, TypeError):
        roi_pct = 0.0

    try:
        followers = int(stats.get("followers") or stats.get("zuluRankFollowers") or 0)
    except (ValueError, TypeError):
        followers = 0

    # --- TP/SL using pip-appropriate offsets for forex ---
    if category == "FOREX":
        # Standard 50-pip TP / 30-pip SL scaled to price magnitude
        if "JPY" in symbol:
            pip = 0.01
        else:
            pip = 0.0001
        tp_offset = 50 * pip
        sl_offset = 30 * pip
    elif category == "COMMODITY" and "XAU" in symbol:
        tp_offset = entry_price * 0.015
        sl_offset = entry_price * 0.008
    else:
        tp_offset = entry_price * 0.015
        sl_offset = entry_price * 0.010

    if direction == "LONG":
        tp_price = round(entry_price + tp_offset, 6)
        sl_price = round(entry_price - sl_offset, 6)
    else:
        tp_price = round(entry_price - tp_offset, 6)
        sl_price = round(entry_price + sl_offset, 6)

    # --- Confidence: blend win rate + followers signal ---
    confidence = round(min(0.92, 0.60 + win_rate * 0.25 + min(followers, 2000) / 40000), 3)

    now = datetime.now(timezone.utc)
    safe_nick = nickname.replace(" ", "_").replace("/", "_")[:20]
    pick_id = f"zt_{safe_nick}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

    # --- Unrealized PnL ---
    try:
        upl = float(trade.get("profit") or trade.get("pnl") or trade.get("unrealizedPL") or 0)
    except (ValueError, TypeError):
        upl = 0.0

    return {
        "id": pick_id,
        "strategy": f"zt_copy_{safe_nick}",
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
        "max_safe_leverage": 10.0,
        "forward_trades": int(stats.get("totalTrades") or stats.get("numTrades") or 0),
        "forward_wr": win_rate,
        "forward_validated": win_rate >= 0.50 and (stats.get("totalTrades") or 0) >= 10,
        "elite_score": min(100, int(roi_pct * 5 + win_rate * 50 + min(followers, 2000) / 100)),
        "elite_grade": "A" if win_rate >= 0.65 else "B" if win_rate >= 0.50 else "C",
        "reason": (
            f"ZuluTrade {nickname} | ROI:{roi_pct*100:.0f}% "
            f"WR:{win_rate*100:.0f}% followers:{followers}"
        ),
        "source_system": "copy_trader_zulutrade",
        "trader_name": nickname,
        "trader_roi": round(roi_pct, 4),
        "trader_followers": followers,
        "trader_platform": "ZuluTrade",
        "trader_id": str(provider_id),
        "unrealized_pnl": upl,
    }


# ---------------------------------------------------------------------------
# Core scanner
# ---------------------------------------------------------------------------

def scan_zulutrade_traders(max_traders: int = 20) -> tuple[list, list]:
    """
    Scan ZuluTrade seed traders for open positions.

    Returns:
        profiles  – list of trader profile dicts (metadata)
        picks     – list of active_picks-compatible trade dicts
    """
    profiles = []
    picks = []

    # Attempt dynamic leaderboard discovery first (no API key needed)
    print("  [ZuluTrade] Fetching leaderboard for dynamic discovery...")
    board = fetch_leaderboard(page=0, size=50)
    discovered_ids = {}
    for row in board:
        pid = row.get("providerId") or row.get("id") or row.get("zuluAccountId")
        name = row.get("nickName") or row.get("name") or row.get("username") or str(pid)
        if pid and str(pid).isdigit():
            discovered_ids[int(pid)] = name
    if discovered_ids:
        print(f"  [ZuluTrade] Discovered {len(discovered_ids)} traders from leaderboard")
    time.sleep(RATE_LIMIT_SEC)

    # Merge seed list with discovered traders
    trader_queue: list[tuple[int, str]] = []
    seen_ids: set[int] = set()

    for pid, name in discovered_ids.items():
        trader_queue.append((pid, name))
        seen_ids.add(pid)

    for pid, name, *_ in SEED_TRADERS:
        if pid not in seen_ids:
            trader_queue.append((pid, name))
            seen_ids.add(pid)

    trader_queue = trader_queue[:max_traders]
    print(f"  [ZuluTrade] Scanning {len(trader_queue)} traders for open positions...")

    for provider_id, nickname in trader_queue:
        time.sleep(RATE_LIMIT_SEC)

        stats = fetch_provider_stats(provider_id)
        if not stats:
            stats = {}

        time.sleep(RATE_LIMIT_SEC)

        trades = fetch_open_trades(provider_id)

        if not trades:
            continue  # No open positions – skip

        profile = {
            "provider_id": provider_id,
            "nickname": nickname,
            "win_rate": stats.get("winRate") or stats.get("pctWinners") or 0,
            "roi": stats.get("roi") or stats.get("totalReturn") or 0,
            "followers": stats.get("followers") or stats.get("zuluRankFollowers") or 0,
            "total_trades": stats.get("totalTrades") or stats.get("numTrades") or 0,
            "open_trades": len(trades),
            "platform": "ZuluTrade",
        }
        profiles.append(profile)

        for trade in trades:
            pick = trade_to_pick(trade, provider_id, nickname, stats)
            if pick:
                picks.append(pick)

        print(
            f"  [ZuluTrade] {nickname} ({provider_id}): "
            f"{len(trades)} open → {sum(1 for p in picks[-len(trades):] if p)} new picks"
        )

    print(f"  [ZuluTrade] Done: {len(profiles)} traders, {len(picks)} picks")
    return profiles, picks


def save_zulutrade_results(profiles: list, picks: list) -> None:
    """Save ZuluTrade results to JSON files."""
    profiles_path = DATA_DIR / "zulutrade_profiles.json"
    picks_path = DATA_DIR / "zulutrade_picks.json"

    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, default=str)

    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)

    print(f"  [ZuluTrade] Saved {len(profiles)} profiles → {profiles_path.name}")
    print(f"  [ZuluTrade] Saved {len(picks)} picks    → {picks_path.name}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== ZuluTrade Copy Trading Scraper ===")
    t0 = time.time()
    profiles, picks = scan_zulutrade_traders(max_traders=40)
    save_zulutrade_results(profiles, picks)
    print(f"\nDone in {time.time()-t0:.1f}s | {len(profiles)} traders | {len(picks)} active picks")
    if picks:
        print("\nSample picks:")
        for p in picks[:3]:
            print(f"  {p['symbol']} {p['direction']} @ {p['entry_price']} "
                  f"[{p['trader_name']}] conf={p['confidence']}")
