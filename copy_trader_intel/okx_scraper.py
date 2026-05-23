#!/usr/bin/env python3
"""
OKX Copy Trading Scraper & Pick Generator
==========================================
Scrapes the OKX copy trading leaderboard for top traders,
fetches their current open positions, and converts them into
active_picks.json compatible format.

NO API KEY NEEDED - OKX copy trading API is fully public.

Confirmed endpoints (from CRYPTO_COPY_TRADERS_RESEARCH.md):
  - Leaderboard: GET /api/v5/copytrading/public-lead-traders
  - Positions:   GET /api/v5/copytrading/public-current-subpositions?uniqueCode={CODE}
  - History:     GET /api/v5/copytrading/public-subpositions-history?uniqueCode={CODE}

API Failover Rule: 3+ mirrors (OKX primary, OKX AWS, OKX fallback).
Rate limit: 500ms between calls.
"""

import json
import time
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests

# -- API Mirrors (failover chain per project rules) --
OKX_API_MIRRORS = [
    "https://www.okx.com",
    "https://aws.okx.com",
    "https://okx.com",
]

# Endpoints (appended to mirror base)
LEADERBOARD_PATH = "/api/v5/copytrading/public-lead-traders"
POSITIONS_PATH = "/api/v5/copytrading/public-current-subpositions"
HISTORY_PATH = "/api/v5/copytrading/public-subpositions-history"

# Known top traders from research (uniqueCode verified via OKX public API)
# Sources: OKX public-lead-traders API, CRYPTO_COPY_TRADERS_RESEARCH.md
# Last verified: 2026-03-19
SEED_TRADERS = [
    # -- Original verified traders --
    {"uniqueCode": "1173EC858F15E04F", "nickName": "Expert-Ethash-Camel",
     "note": "+1071% ROI, 67.9% WR, 821 days, $180K AUM, 301 copiers"},
    {"uniqueCode": "849CAD818B573125", "nickName": "nightraid-",
     "note": "+281% ROI, 58.9% WR, 405 days, $180K AUM, 434 copiers"},
    {"uniqueCode": "0C053614746975C0", "nickName": "Fair-Hash-Maverick",
     "note": "+238% ROI, 82.9% WR, 404 days, $80K AUM, 300 copiers"},
    {"uniqueCode": "99FB5ECCC0C27A8A", "nickName": "CrowleyZhou",
     "note": "+225% ROI, 52.2% WR, 147 days, $479K AUM, 600 copiers"},
    {"uniqueCode": "AD2B6E949E5E91EC", "nickName": "FJ Investment",
     "note": "+125% 90d, 724 days active"},
    {"uniqueCode": "D442CF34E4AEEAF1", "nickName": "Trader KS",
     "note": "+103% ROI, 61.9% WR, 505 days, $54K AUM, 81 copiers"},
    # -- New traders added 2026-03-19 (verified via OKX public API) --
    {"uniqueCode": "35F888C7BB441B2B", "nickName": "Shallow-Pair-Frog",
     "note": "+48.7% ROI, 57.8% WR, 854 days, $94K AUM, 410 copiers -- veteran"},
    {"uniqueCode": "983AC67F2C0E41B5", "nickName": "xiao-wen-mj",
     "note": "+27.6% ROI, 66.2% WR, 114 days, $189K AUM, 586 copiers -- high WR"},
    {"uniqueCode": "4A8AB04BF304EBD8", "nickName": "Eeeeeex",
     "note": "+23.6% ROI, 51.8% WR, 215 days, $24K AUM"},
    {"uniqueCode": "8DADD51A63B6D30F", "nickName": "DL-Trading",
     "note": "+104% ROI, 72.7% WR, 723 days, veteran with strong WR"},
    {"uniqueCode": "2A892FFDB4E2E841", "nickName": "Yfhkfg",
     "note": "+22.3% ROI, 63.1% WR, 124 days, $4K AUM"},
    # -- New traders added 2026-03-20 (fresh live OKX leaderboard scan) --
    {"uniqueCode": "097F20F08F8BEB70", "nickName": "pikawenjiatouzi",
     "note": "+55% ROI, 58.9% WR, 124d, $68K AUM, 142 copiers"},
    {"uniqueCode": "609DDBB0C0532E3D", "nickName": "old leeks",
     "note": "+54% ROI, 60.9% WR, 374d, $69K AUM, 73 copiers -- veteran"},
    {"uniqueCode": "FA400F0E91664A05", "nickName": "TradingNotes",
     "note": "+30% ROI, 51.9% WR, 408d, $83K AUM -- solid veteran"},
    {"uniqueCode": "B7DF7A52C9C227F6", "nickName": "YMY2020",
     "note": "+19% ROI, 71.4% WR, 95d -- exceptional win rate"},
    {"uniqueCode": "823664FB73B79E41", "nickName": "Junglelaw",
     "note": "+8% ROI, 63.1% WR, 590d, $5.37M AUM, 16868 lifetime copiers -- stability king"},
]

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Rate limit
RATE_LIMIT_SEC = 0.5

# Headers to mimic browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


def okx_get(path: str, params: dict = None, retries: int = 3) -> dict:
    """
    GET request to OKX API with mirror failover.
    Tries each mirror in order. Returns parsed JSON or empty dict.
    """
    for mirror in OKX_API_MIRRORS:
        url = f"{mirror}{path}"
        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "0" or data.get("data"):
                        return data
                    # Some endpoints return data directly
                    if isinstance(data, list):
                        return {"data": data, "code": "0"}
                elif resp.status_code == 429:
                    # Rate limited - wait and retry
                    time.sleep(2)
                    continue
                else:
                    break  # Try next mirror
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    time.sleep(1)
                continue
        # Move to next mirror
    print(f"  [WARN] All OKX mirrors failed for {path}")
    return {}


def fetch_leaderboard(max_traders: int = 20) -> list:
    """
    Fetch top traders from OKX copy trading leaderboard.
    Returns list of trader dicts with uniqueCode, nickName, pnlRatio, etc.
    """
    print("  Fetching OKX leaderboard...")
    data = okx_get(LEADERBOARD_PATH)

    traders = data.get("data", [])
    if not traders:
        print("  [WARN] Leaderboard returned no data, using seed traders")
        return SEED_TRADERS

    print(f"  Found {len(traders)} traders on leaderboard")

    # Sort by pnlRatio (ROI) descending
    for t in traders:
        try:
            t["_pnlRatio"] = float(t.get("pnlRatio", 0))
        except (ValueError, TypeError):
            t["_pnlRatio"] = 0

    traders.sort(key=lambda x: x["_pnlRatio"], reverse=True)

    # Take top N
    result = traders[:max_traders]

    # Merge seed traders if not already present
    existing_codes = {t.get("uniqueCode", "").upper() for t in result}
    for seed in SEED_TRADERS:
        if seed["uniqueCode"].upper() not in existing_codes:
            result.append(seed)

    return result


def fetch_positions(unique_code: str) -> list:
    """
    Fetch a trader's current open positions.
    Returns list of position dicts.
    """
    data = okx_get(POSITIONS_PATH, params={"uniqueCode": unique_code})
    return data.get("data", [])


def fetch_history(unique_code: str, limit: int = 50) -> list:
    """
    Fetch a trader's historical trades for win rate calculation.
    Returns list of closed trade dicts.
    """
    data = okx_get(HISTORY_PATH, params={"uniqueCode": unique_code, "limit": limit})
    return data.get("data", [])


def calculate_trader_stats(history: list) -> dict:
    """Calculate win rate, profit factor, avg hold time from trade history."""
    if not history:
        return {"win_rate": 0, "profit_factor": 0, "avg_hold_hours": 0, "total_trades": 0}

    wins = 0
    losses = 0
    gross_profit = 0
    gross_loss = 0
    hold_times = []

    for trade in history:
        try:
            pnl = float(trade.get("pnl", 0))
        except (ValueError, TypeError):
            continue

        if pnl > 0:
            wins += 1
            gross_profit += pnl
        elif pnl < 0:
            losses += 1
            gross_loss += abs(pnl)

        # Calculate hold time
        try:
            open_t = int(trade.get("openTime", 0))
            close_t = int(trade.get("closeTime", 0))
            if open_t > 0 and close_t > open_t:
                hold_h = (close_t - open_t) / 3_600_000
                hold_times.append(hold_h)
        except (ValueError, TypeError):
            pass

    total = wins + losses
    win_rate = wins / total if total > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.99

    avg_hold = sum(hold_times) / len(hold_times) if hold_times else 0

    return {
        "win_rate": round(win_rate, 4),
        "profit_factor": round(min(profit_factor, 99.99), 2),
        "avg_hold_hours": round(avg_hold, 2),
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
    }


def convert_inst_id(inst_id: str) -> str:
    """
    Convert OKX instrument ID to standard symbol format.
    BTC-USDT-SWAP -> BTCUSDT
    ETH-USDT-SWAP -> ETHUSDT
    """
    if not inst_id:
        return ""
    parts = inst_id.split("-")
    if len(parts) >= 2:
        return f"{parts[0]}{parts[1]}"
    return inst_id.replace("-", "")


def position_to_pick(position: dict, trader: dict, stats: dict) -> dict:
    """
    Convert a single OKX position into an active_picks.json compatible pick.
    """
    inst_id = position.get("instId", "")
    symbol = convert_inst_id(inst_id)
    if not symbol:
        return None

    # Direction from posSide
    pos_side = position.get("posSide", position.get("subPosside", "")).lower()
    direction = "LONG" if pos_side == "long" else "SHORT"

    # Entry price
    try:
        entry_price = float(position.get("openAvgPx", position.get("avgPx", 0)))
    except (ValueError, TypeError):
        return None
    if entry_price <= 0:
        return None

    # Leverage
    try:
        leverage = float(position.get("lever", 1))
    except (ValueError, TypeError):
        leverage = 1.0
    leverage = min(leverage, 50)  # Cap at 50x

    # Trader stats
    win_ratio = stats.get("win_rate", 0)
    try:
        pnl_ratio = float(trader.get("pnlRatio", trader.get("_pnlRatio", 0)))
    except (ValueError, TypeError):
        pnl_ratio = 0

    try:
        aum = float(trader.get("aum", 0))
    except (ValueError, TypeError):
        aum = 0

    nick = trader.get("nickName", trader.get("uniqueCode", "unknown"))

    # Confidence: based on win ratio (0.7 + winRatio * 0.2) capped at 0.95
    confidence = round(min(0.95, 0.7 + win_ratio * 0.2), 3)

    # TP/SL: 5% TP, 3% SL for LONG; inverse for SHORT
    if direction == "LONG":
        tp_price = round(entry_price * 1.05, 8)
        sl_price = round(entry_price * 0.97, 8)
    else:
        tp_price = round(entry_price * 0.95, 8)
        sl_price = round(entry_price * 1.03, 8)

    # Unrealized PnL
    try:
        upl = float(position.get("upl", position.get("pnl", 0)))
    except (ValueError, TypeError):
        upl = 0

    # Open time
    try:
        open_time_ms = int(position.get("openTime", position.get("cTime", 0)))
        open_time_str = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc).isoformat() if open_time_ms > 0 else None
    except (ValueError, TypeError):
        open_time_str = None

    now = datetime.now(timezone.utc)
    safe_nick = nick.replace(" ", "_").replace("/", "_")[:20]
    pick_id = f"okx_copy_{safe_nick}::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

    return {
        "id": pick_id,
        "strategy": f"okx_copy_{safe_nick}",
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
        "position_sizing": "copy_trader",
        "risk_per_trade_pct": 0.03,
        "max_safe_leverage": leverage,
        "forward_trades": stats.get("total_trades", 0),
        "forward_wr": win_ratio,
        "forward_validated": win_ratio >= 0.50 and stats.get("total_trades", 0) >= 10,
        "elite_score": min(100, int(pnl_ratio * 20 + win_ratio * 50)),
        "elite_grade": "A" if win_ratio >= 0.60 else "B" if win_ratio >= 0.50 else "C",
        "reason": (f"OKX copy trader {nick} | ROI:{pnl_ratio*100:.0f}% "
                   f"WR:{win_ratio*100:.0f}% AUM:${aum:,.0f}"),
        "source_system": "copy_trader_okx",
        "trader_name": nick,
        "trader_roi": round(pnl_ratio, 4),
        "trader_aum": round(aum, 2),
        "trader_win_rate": round(win_ratio, 4),
        "leverage": leverage,
        "unrealized_pnl": round(upl, 2),
        "open_time": open_time_str,
        "margin_mode": position.get("mgnMode", ""),
        "inst_id_raw": inst_id,
        "timestamp": now.isoformat(),
    }


def scan_okx_traders(max_traders: int = 15) -> tuple:
    """
    Main OKX scan: fetch leaderboard, get positions for top traders, generate picks.
    Returns (trader_profiles, picks).
    """
    print("=" * 70)
    print("  OKX COPY TRADER SCRAPER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Step 1: Fetch leaderboard
    traders = fetch_leaderboard(max_traders=20)
    print(f"  Leaderboard: {len(traders)} traders loaded")

    # Step 2: Analyze top traders
    all_profiles = []
    all_picks = []

    # Sort by ROI, take top N
    for t in traders:
        try:
            t["_sort_key"] = float(t.get("pnlRatio", t.get("_pnlRatio", 0)))
        except (ValueError, TypeError):
            t["_sort_key"] = 0

    traders.sort(key=lambda x: x.get("_sort_key", 0), reverse=True)
    top_traders = traders[:max_traders]

    for i, trader in enumerate(top_traders):
        code = trader.get("uniqueCode", "")
        nick = trader.get("nickName", code[:8] if code else f"trader_{i}")
        if not code:
            print(f"  [{i+1}] {nick}: no uniqueCode, skipping")
            continue

        print(f"  [{i+1}/{len(top_traders)}] {nick} (code: {code[:8]}...) ", end="", flush=True)
        time.sleep(RATE_LIMIT_SEC)

        # Fetch trade history for stats
        history = fetch_history(code, limit=50)
        stats = calculate_trader_stats(history)
        time.sleep(RATE_LIMIT_SEC)

        # Fetch current positions
        positions = fetch_positions(code)
        time.sleep(RATE_LIMIT_SEC)

        pnl_ratio = trader.get("_sort_key", 0)
        try:
            aum = float(trader.get("aum", 0))
        except (ValueError, TypeError):
            aum = 0
        try:
            copiers = int(trader.get("copyTraderNum", 0))
        except (ValueError, TypeError):
            copiers = 0

        profile = {
            "uniqueCode": code,
            "nickName": nick,
            "pnlRatio": round(pnl_ratio, 4),
            "aum": round(aum, 2),
            "copyTraderNum": copiers,
            "win_rate": stats["win_rate"],
            "profit_factor": stats["profit_factor"],
            "avg_hold_hours": stats["avg_hold_hours"],
            "total_trades": stats["total_trades"],
            "open_positions_count": len(positions),
            "analysis_time": datetime.now(timezone.utc).isoformat(),
        }
        all_profiles.append(profile)

        if not positions:
            print(f"ROI:{pnl_ratio*100:.0f}% WR:{stats['win_rate']*100:.0f}% -- no open positions")
            continue

        # Convert positions to picks
        picks_for_trader = []
        for pos in positions:
            pick = position_to_pick(pos, trader, stats)
            if pick:
                picks_for_trader.append(pick)

        all_picks.extend(picks_for_trader)
        print(f"ROI:{pnl_ratio*100:.0f}% WR:{stats['win_rate']*100:.0f}% "
              f"Trades:{stats['total_trades']} Positions:{len(positions)} "
              f"Picks:{len(picks_for_trader)}")

    print(f"\n  OKX scan complete: {len(all_profiles)} traders, {len(all_picks)} picks")
    return all_profiles, all_picks


def save_okx_results(profiles: list, picks: list):
    """Save OKX results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # Save trader profiles
    profiles_path = DATA_DIR / "okx_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "okx_copy_trading",
            "trader_count": len(profiles),
            "profiles": profiles,
        }, f, indent=2, default=str)
    print(f"  Saved {len(profiles)} trader profiles to {profiles_path}")

    # Save picks
    picks_path = DATA_DIR / "okx_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return profiles_path, picks_path


if __name__ == "__main__":
    profiles, picks = scan_okx_traders(max_traders=15)
    save_okx_results(profiles, picks)
    print(f"\nDone. {len(picks)} OKX copy trader picks generated.")
