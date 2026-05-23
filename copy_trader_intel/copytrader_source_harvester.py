#!/usr/bin/env python3
"""
Copytrader Source Harvester v2.0
============================
Harvests copy traders from multiple platforms to build a database of
300+ crypto and 300+ forex traders with verifiable performance data.

v2.0 CHANGES:
  - Merges REAL data from qualified_traders.json, trader_profiles.json,
    okx/bitget/bybit_trader_profiles.json into crypto traders
  - Replaces placeholder forex traders (FXL-Signal-N, FF-System-N) with
    REAL verified data from forex_trader_database.json and research_verified_traders.json
  - Adds verify_trader_quality() scoring function
  - Removes all wr=? / pf=? placeholder stubs

CRYPTO SOURCES:
  1. OKX Copy Trading API (public, no auth) -- leaderboard + trade history
  2. Bitget Copy Trading (HTML scrape) -- leaderboard + profiles
  3. Hyperliquid DEX API (public, no auth) -- on-chain leaderboard
  4. Bybit Copy Trading (CDN-protected) -- master traders
  5. BingX Copy Trading API -- leaderboard
  6. Gate.io Copy Trading -- leaderboard
  7. Copin.io Aggregator -- 2M+ traders across 14 protocols
  8. Qualified traders from Hyperliquid analysis (qualified_traders.json)

FOREX SOURCES:
  1. Myfxbook AutoTrade API (v1.38) -- verified EAs and systems
  2. ZuluTrade REST API -- leaders with ZuluRank
  3. eToro Public API -- Pro Investors
  4. Darwinex Darwin Info API -- DARWIN strategies
  5. cTrader Copy (Spotware) -- strategy providers
  6. forex_trader_database.json -- 311 verified traders from 8 platforms
  7. research_verified_traders.json -- Myfxbook/Darwinex verified systems

Run: python copy_trader_intel/copytrader_source_harvester.py
"""

import json
import sys
import os
import time
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

try:
    import requests
except ImportError:
    print("[ERROR] pip install requests")
    sys.exit(1)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def _safe_get(url, **kwargs):
    """GET with timeout and error handling."""
    try:
        kwargs.setdefault("timeout", 20)
        kwargs.setdefault("headers", HEADERS)
        r = requests.get(url, **kwargs)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"    [WARN] {url[:80]}... -- {e}")
        return None


def _safe_post(url, json_body=None, **kwargs):
    """POST with timeout and error handling."""
    try:
        kwargs.setdefault("timeout", 20)
        kwargs.setdefault("headers", {**HEADERS, "Content-Type": "application/json"})
        r = requests.post(url, json=json_body, **kwargs)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"    [WARN] POST {url[:80]}... -- {e}")
        return None


def _trader_id(platform, identifier):
    """Generate a unique trader ID."""
    raw = f"{platform}::{identifier}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _load_json(filename):
    """Load a JSON file from DATA_DIR, return None on error."""
    path = DATA_DIR / filename
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"    [WARN] Could not load {filename}: {e}")
        return None


# ============================================================
# TRADER QUALITY VERIFICATION
# ============================================================

def verify_trader_quality(trader):
    """
    Score a trader 0-100 based on data quality and completeness.

    Checks:
    - Has name (not placeholder pattern like FXL-Signal-N, FF-System-N, HL-Whale-N)
    - Has platform
    - Has win_rate as a real number (not "?" or None)
    - Has trades_count >= 10
    - Flags suspicious WR < 30% or > 95%

    Returns:
        dict with keys: score (0-100), issues (list), is_placeholder (bool), is_suspicious (bool)
    """
    issues = []
    score = 0
    is_placeholder = False
    is_suspicious = False

    name = trader.get("name", "")
    platform = trader.get("platform", "")

    # Check for placeholder patterns
    placeholder_patterns = [
        r'^FXL-Signal-\d+$',
        r'^FF-System-\d+$',
        r'^HL-Whale-\d+$',
        r'^SS-Provider-\d+$',
        r'^ZT-\d+$',
        r'^CT-Strategy-\d+$',
        r'^MFX-\d+$',
        r'^BX-\w+$',
        r'^Gate-\w+$',
        r'^OKX-\w+$',
        r'^BG-\w+$',
        r'^HL-0x\w+$',
    ]

    for pat in placeholder_patterns:
        if re.match(pat, name):
            is_placeholder = True
            issues.append(f"Placeholder name: {name}")
            break

    # Name check (+15)
    if name and not is_placeholder:
        score += 15
    elif name:
        score += 5  # has a name but it is placeholder

    # Platform check (+10)
    if platform:
        score += 10
    else:
        issues.append("Missing platform")

    # Win rate check (+20)
    wr = trader.get("win_rate")
    if wr is None:
        wr = trader.get("win_rate_pct")
    if wr is not None and wr != "?" and wr != "":
        try:
            wr_val = float(wr)
            # Normalize: if <= 1, treat as ratio
            if 0 < wr_val <= 1:
                wr_val = wr_val * 100
            if 30 <= wr_val <= 95:
                score += 20
            elif wr_val < 30:
                score += 10
                is_suspicious = True
                issues.append(f"Low win rate: {wr_val:.1f}%")
            elif wr_val > 95:
                score += 10
                is_suspicious = True
                issues.append(f"Suspiciously high win rate: {wr_val:.1f}%")
            else:
                score += 15
        except (ValueError, TypeError):
            issues.append(f"Invalid win_rate: {wr}")
    else:
        issues.append("Missing win_rate")

    # Trades count check (+15)
    trades = trader.get("total_trades", trader.get("trades_count", 0))
    if trades and int(trades) >= 100:
        score += 15
    elif trades and int(trades) >= 10:
        score += 10
    elif trades and int(trades) > 0:
        score += 5
        issues.append(f"Low trade count: {trades}")
    else:
        issues.append("Missing or zero trades_count")

    # Profile URL check (+10)
    if trader.get("profile_url"):
        score += 10

    # Profit factor or PnL data (+10)
    has_pf = trader.get("profit_factor") not in (None, 0, "?", "")
    has_pnl = trader.get("total_pnl_usd", trader.get("pnl_90d_pct", trader.get("total_realized_pnl"))) not in (None, 0)
    if has_pf or has_pnl:
        score += 10
    else:
        issues.append("No profit factor or PnL data")

    # Drawdown data (+5)
    dd = trader.get("max_drawdown_pct", trader.get("drawdown"))
    if dd is not None and dd != "?" and dd != "":
        score += 5
    else:
        issues.append("No drawdown data")

    # Copiers/followers (+5)
    copiers = trader.get("copiers", trader.get("followers", trader.get("follower_count", 0)))
    if copiers and int(copiers) > 0:
        score += 5

    # Data quality bonus (+5)
    dq = trader.get("data_quality", "")
    if dq == "excellent":
        score += 5
    elif dq == "good":
        score += 3

    # Verified flag bonus (+5)
    if trader.get("verified") or trader.get("source") == "verified_research":
        score += 5

    return {
        "score": min(score, 100),
        "issues": issues,
        "is_placeholder": is_placeholder,
        "is_suspicious": is_suspicious,
    }


# ============================================================
# CRYPTO SOURCES
# ============================================================

def harvest_okx_traders():
    """OKX Copy Trading -- public API, no auth required.
    Endpoint returns ~20 traders per page, can paginate.
    """
    print("\n  [CRYPTO] Harvesting OKX Copy Trading...")
    traders = []

    # Main leaderboard
    url = "https://www.okx.com/api/v5/copytrading/public-lead-traders"
    r = _safe_get(url)
    if not r:
        return traders

    try:
        data = r.json()
        raw_traders = data.get("data", [])
        print(f"    Raw leaderboard: {len(raw_traders)} traders")

        for t in raw_traders:
            code = t.get("uniqueCode", "")
            if not code:
                continue

            pnl_ratio = float(t.get("pnlRatio", 0))
            win_ratio = float(t.get("winRatio", 0)) if t.get("winRatio") else None
            copiers = int(t.get("copyTraderNum", 0))
            max_copiers = int(t.get("accCopyTraderNum", 0))
            aum = float(t.get("aum", 0))
            lead_days = int(t.get("leadDays", 0))

            traders.append({
                "platform": "OKX",
                "asset_class": "CRYPTO",
                "trader_id": code,
                "name": t.get("nickName", f"OKX-{code[:8]}"),
                "pnl_90d_pct": round(pnl_ratio * 100, 2),
                "win_rate": round(win_ratio * 100, 2) if win_ratio else None,
                "copiers": copiers,
                "max_copiers": max_copiers,
                "aum_usd": aum,
                "days_active": lead_days,
                "api_endpoint": f"https://www.okx.com/api/v5/copytrading/public-subpositions-history?uniqueCode={code}&limit=100",
                "profile_url": f"https://www.okx.com/copy-trading/account/{code}",
                "has_trade_history": True,
                "data_quality": "excellent",
            })

        # Try pagination with different sort orders to get more traders
        for sort_type in ["pnl", "copiers", "aum"]:
            time.sleep(0.5)
            r2_url = f"{url}?sortType={sort_type}"
            r2 = _safe_get(r2_url)
            if r2:
                try:
                    more = r2.json().get("data", [])
                    existing_codes = {t["trader_id"] for t in traders}
                    for t in more:
                        code = t.get("uniqueCode", "")
                        if code and code not in existing_codes:
                            pnl_ratio = float(t.get("pnlRatio", 0))
                            traders.append({
                                "platform": "OKX",
                                "asset_class": "CRYPTO",
                                "trader_id": code,
                                "name": t.get("nickName", f"OKX-{code[:8]}"),
                                "pnl_90d_pct": round(pnl_ratio * 100, 2),
                                "win_rate": round(float(t.get("winRatio", 0)) * 100, 2) if t.get("winRatio") else None,
                                "copiers": int(t.get("copyTraderNum", 0)),
                                "aum_usd": float(t.get("aum", 0)),
                                "days_active": int(t.get("leadDays", 0)),
                                "has_trade_history": True,
                                "data_quality": "excellent",
                                "profile_url": f"https://www.okx.com/copy-trading/account/{code}",
                            })
                            existing_codes.add(code)
                except Exception:
                    pass

    except Exception as e:
        print(f"    [ERROR] OKX parse: {e}")

    print(f"    [OK] OKX: {len(traders)} traders harvested")
    return traders


def harvest_hyperliquid_traders():
    """Hyperliquid DEX -- fully on-chain, public POST API."""
    print("\n  [CRYPTO] Harvesting Hyperliquid leaderboard...")
    traders = []

    r = _safe_post("https://api.hyperliquid.xyz/info", json_body={"type": "leaderboard"})
    if not r:
        return traders

    try:
        data = r.json()
        # The leaderboard returns a list of entries
        entries = data if isinstance(data, list) else data.get("leaderboard", [])
        print(f"    Raw leaderboard: {len(entries)} entries")

        for entry in entries:
            if isinstance(entry, dict):
                addr = entry.get("ethAddress", entry.get("address", ""))
                pnl = entry.get("windowPerformances", {})
                account_value = float(entry.get("accountValue", 0))
            elif isinstance(entry, list) and len(entry) >= 2:
                # Alternative format: [address, {stats}]
                addr = entry[0] if isinstance(entry[0], str) else ""
                stats = entry[1] if len(entry) > 1 and isinstance(entry[1], dict) else {}
                pnl = stats
                account_value = float(stats.get("accountValue", 0))
            else:
                continue

            if not addr:
                continue

            traders.append({
                "platform": "Hyperliquid",
                "asset_class": "CRYPTO",
                "trader_id": addr,
                "name": f"HL-{addr[:6]}...{addr[-4:]}",
                "account_value_usd": account_value,
                "api_endpoint": f"https://api.hyperliquid.xyz/info (POST: userFills, user: {addr})",
                "profile_url": f"https://app.hyperliquid.xyz/@{addr}",
                "has_trade_history": True,
                "data_quality": "excellent",
                "on_chain": True,
            })

    except Exception as e:
        print(f"    [ERROR] Hyperliquid: {e}")

    print(f"    [OK] Hyperliquid: {len(traders)} traders")
    return traders


def harvest_bitget_traders():
    """Bitget Copy Trading -- try internal API first, then HTML scrape fallback."""
    print("\n  [CRYPTO] Harvesting Bitget Copy Trading...")
    traders = []

    # Try internal API endpoints (discovered through browser inspection)
    api_urls = [
        "https://www.bitget.com/v1/copy/mix/follower/querySurTraderList",
        "https://www.bitget.com/v1/copy/mix/public/traderRanking",
    ]

    for api_url in api_urls:
        r = _safe_post(api_url, json_body={
            "pageNo": 1, "pageSize": 50,
            "timeRange": "THIRTY_DAYS",
            "orderBy": "ROI",
        })
        if r:
            try:
                data = r.json()
                items = data.get("data", {}).get("traderList", [])
                if not items:
                    items = data.get("data", {}).get("list", [])
                if not items and isinstance(data.get("data"), list):
                    items = data["data"]

                for item in items:
                    tid = item.get("traderUid", item.get("uid", item.get("traderId", "")))
                    if not tid:
                        continue
                    traders.append({
                        "platform": "Bitget",
                        "asset_class": "CRYPTO",
                        "trader_id": str(tid),
                        "name": item.get("nickName", item.get("traderName", f"BG-{str(tid)[:8]}")),
                        "roi_30d_pct": float(item.get("roiRate", item.get("roi", 0))) * 100 if item.get("roiRate") or item.get("roi") else None,
                        "win_rate": float(item.get("winRate", 0)) * 100 if item.get("winRate") else None,
                        "copiers": int(item.get("followerCount", item.get("copyCount", 0))),
                        "max_drawdown_pct": float(item.get("maxDrawdown", 0)) * 100 if item.get("maxDrawdown") else None,
                        "profile_url": f"https://www.bitget.com/copy-trading/trader/{tid}/futures",
                        "has_trade_history": True,
                        "data_quality": "good",
                    })
                if traders:
                    break
            except Exception as e:
                print(f"    [WARN] Bitget API parse: {e}")

    # Fallback: add known verified traders from our research
    known_bitget = [
        {"trader_id": "b1b5467f8bb73f53ac97", "name": "hale", "roi_30d_pct": 61.04, "win_rate": 57.1, "copiers": 750, "max_drawdown_pct": 15.5, "days_active": 1605},
        {"trader_id": "b0bd4a7e86bb3956a49c", "name": "Bg-ATM", "roi_30d_pct": 57.48, "win_rate": 90.3, "copiers": 450, "max_drawdown_pct": 14.7, "days_active": 86},
        {"trader_id": "ICHIZENCapital", "name": "ICHIZENCapital", "roi_30d_pct": 4302, "win_rate": 34.6, "copiers": 0, "max_drawdown_pct": 21.6},
        {"trader_id": "btctangying", "name": "btctangying", "roi_30d_pct": 3.1, "win_rate": 100, "copiers": 13, "max_drawdown_pct": 9.6},
        {"trader_id": "BGUSER-X15KWVSN", "name": "WIN-2026", "roi_30d_pct": 19396, "win_rate": 89.5, "copiers": 354, "max_drawdown_pct": 70.6},
        {"trader_id": "BGUSER-YLCSRYTY", "name": "DeepSeek-V4", "roi_30d_pct": 12017, "win_rate": 100, "copiers": 437, "max_drawdown_pct": 83.4},
        {"trader_id": "BGUSER-57E4J14D", "name": "LaiFaCai", "roi_30d_pct": 12731, "win_rate": 92.9, "copiers": 214, "max_drawdown_pct": 93.2},
        {"trader_id": "BGUSER-9G3FB5CG", "name": "Rich", "roi_30d_pct": 64.69, "win_rate": 100, "copiers": 373, "max_drawdown_pct": 36.9},
        {"trader_id": "BGUSER-437X4N8S", "name": "FaGe", "roi_30d_pct": 58.8, "win_rate": 92.1, "copiers": 174, "max_drawdown_pct": 40.4},
        {"trader_id": "woshiguaizi", "name": "woshiguaizi", "roi_30d_pct": 0.47, "win_rate": 84.6, "copiers": 297, "max_drawdown_pct": 11.7},
    ]
    existing_ids = {t["trader_id"] for t in traders}
    for kt in known_bitget:
        if kt["trader_id"] not in existing_ids:
            kt["platform"] = "Bitget"
            kt["asset_class"] = "CRYPTO"
            kt["profile_url"] = f"https://www.bitget.com/copy-trading/trader/{kt['trader_id']}/futures"
            kt["has_trade_history"] = True
            kt["data_quality"] = "good"
            kt["source"] = "verified_research"
            traders.append(kt)

    print(f"    [OK] Bitget: {len(traders)} traders")
    return traders


def harvest_bingx_traders():
    """BingX Copy Trading -- public leaderboard API."""
    print("\n  [CRYPTO] Harvesting BingX Copy Trading...")
    traders = []

    urls = [
        "https://bingx.com/api/v1/copy-trading/leaderboard?page=1&pageSize=50",
        "https://open-api.bingx.com/openApi/copyTrading/v1/traderList",
    ]

    for url in urls:
        r = _safe_get(url)
        if r:
            try:
                data = r.json()
                items = data.get("data", {}).get("list", [])
                if not items:
                    items = data.get("data", []) if isinstance(data.get("data"), list) else []
                for item in items:
                    tid = item.get("uid", item.get("traderId", ""))
                    if not tid:
                        continue
                    traders.append({
                        "platform": "BingX",
                        "asset_class": "CRYPTO",
                        "trader_id": str(tid),
                        "name": item.get("nickName", f"BX-{str(tid)[:8]}"),
                        "roi_30d_pct": float(item.get("roi", 0)) * 100 if item.get("roi") else None,
                        "win_rate": float(item.get("winRate", 0)) * 100 if item.get("winRate") else None,
                        "copiers": int(item.get("followerCount", 0)),
                        "profile_url": f"https://bingx.com/en/copyTrading/trader/{tid}/",
                        "has_trade_history": True,
                        "data_quality": "good",
                    })
                if traders:
                    break
            except Exception:
                pass

    print(f"    [OK] BingX: {len(traders)} traders")
    return traders


def harvest_copin_traders():
    """Copin.io -- multi-protocol aggregator with 2M+ trader profiles."""
    print("\n  [CRYPTO] Harvesting Copin.io aggregator...")
    traders = []

    protocols = ["HYPERLIQUID", "GMX_V2", "KWENTA", "GNS_V8"]
    for protocol in protocols:
        url = f"https://api.copin.io/traders?protocol={protocol}&sort=pnl&order=desc&limit=100"
        r = _safe_get(url)
        if r:
            try:
                data = r.json()
                items = data.get("data", []) if isinstance(data.get("data"), list) else data if isinstance(data, list) else []
                for item in items:
                    addr = item.get("address", item.get("account", ""))
                    if not addr:
                        continue
                    traders.append({
                        "platform": f"Copin.io ({protocol})",
                        "asset_class": "CRYPTO",
                        "trader_id": addr,
                        "name": f"{protocol[:3]}-{addr[:6]}...{addr[-4:]}",
                        "total_pnl_usd": float(item.get("pnl", 0)),
                        "win_rate": float(item.get("winRate", 0)) * 100 if item.get("winRate") else None,
                        "total_trades": int(item.get("totalTrade", 0)),
                        "profile_url": f"https://app.copin.io/trader/{addr}?protocol={protocol}",
                        "has_trade_history": True,
                        "data_quality": "good",
                        "protocol": protocol,
                    })
            except Exception:
                pass
        time.sleep(0.3)

    print(f"    [OK] Copin.io: {len(traders)} traders across {len(protocols)} protocols")
    return traders


def harvest_gate_traders():
    """Gate.io Copy Trading leaderboard."""
    print("\n  [CRYPTO] Harvesting Gate.io Copy Trading...")
    traders = []

    urls = [
        "https://www.gate.io/api/v4/copy-trading/leaderboard?limit=50",
        "https://www.gate.io/api2/1/copy-trading/ranking",
    ]

    for url in urls:
        r = _safe_get(url)
        if r:
            try:
                data = r.json()
                items = data if isinstance(data, list) else data.get("data", [])
                for item in items:
                    tid = item.get("user_id", item.get("uid", ""))
                    if tid:
                        traders.append({
                            "platform": "Gate.io",
                            "asset_class": "CRYPTO",
                            "trader_id": str(tid),
                            "name": item.get("name", f"Gate-{str(tid)[:8]}"),
                            "roi_30d_pct": float(item.get("pnl_ratio", 0)) * 100 if item.get("pnl_ratio") else None,
                            "profile_url": f"https://www.gate.io/copy_trading/share/{tid}",
                            "has_trade_history": True,
                            "data_quality": "medium",
                        })
                if traders:
                    break
            except Exception:
                pass

    print(f"    [OK] Gate.io: {len(traders)} traders")
    return traders


# ============================================================
# ENRICH CRYPTO FROM LOCAL DATA FILES
# ============================================================

def enrich_from_qualified_traders():
    """Load qualified_traders.json -- real Hyperliquid whales with verified metrics."""
    print("\n  [CRYPTO] Enriching from qualified_traders.json...")
    traders = []

    data = _load_json("qualified_traders.json")
    if not data:
        print("    [WARN] qualified_traders.json not found")
        return traders

    raw = data.get("traders", [])
    for t in raw:
        if not t.get("qualified"):
            continue
        addr = t.get("address", "")
        if not addr:
            continue

        wr = t.get("win_rate", 0)
        if isinstance(wr, (int, float)) and 0 < wr <= 1:
            wr = round(wr * 100, 2)

        traders.append({
            "platform": "Hyperliquid",
            "asset_class": "CRYPTO",
            "trader_id": addr,
            "name": t.get("label", f"HL-{addr[:6]}...{addr[-4:]}"),
            "account_value_usd": t.get("account_value", 0),
            "total_realized_pnl": t.get("total_realized_pnl", 0),
            "win_rate": wr,
            "total_trades": t.get("total_trades", 0),
            "wins": t.get("wins", 0),
            "losses": t.get("losses", 0),
            "profit_factor": t.get("profit_factor", 0),
            "avg_win": t.get("avg_win", 0),
            "avg_loss": t.get("avg_loss", 0),
            "max_drawdown_pct": t.get("max_drawdown_pct", 0),
            "edge_score": t.get("edge_score", 0),
            "coins_traded": t.get("coins_traded", []),
            "profile_url": f"https://app.hyperliquid.xyz/@{addr}",
            "has_trade_history": True,
            "data_quality": "excellent",
            "on_chain": True,
            "source": "qualified_traders_analysis",
        })

    print(f"    [OK] Qualified traders: {len(traders)} verified Hyperliquid traders")
    return traders


def enrich_from_okx_profiles():
    """Load okx_trader_profiles.json -- enriches OKX traders with WR/PF/trades."""
    print("\n  [CRYPTO] Enriching from okx_trader_profiles.json...")
    data = _load_json("okx_trader_profiles.json")
    if not data:
        print("    [WARN] okx_trader_profiles.json not found")
        return {}

    enrichment = {}
    for p in data.get("profiles", []):
        code = p.get("uniqueCode", "")
        if not code:
            continue
        wr = p.get("win_rate", 0)
        if isinstance(wr, (int, float)) and 0 < wr <= 1:
            wr = round(wr * 100, 2)
        enrichment[code] = {
            "win_rate": wr,
            "profit_factor": p.get("profit_factor", 0),
            "avg_hold_hours": p.get("avg_hold_hours", 0),
            "total_trades": p.get("total_trades", 0),
            "open_positions_count": p.get("open_positions_count", 0),
        }

    print(f"    [OK] OKX profiles: {len(enrichment)} trader enrichments loaded")
    return enrichment


def enrich_from_bitget_profiles():
    """Load bitget_trader_profiles.json -- enriches Bitget traders."""
    print("\n  [CRYPTO] Enriching from bitget_trader_profiles.json...")
    data = _load_json("bitget_trader_profiles.json")
    if not data:
        print("    [WARN] bitget_trader_profiles.json not found")
        return {}

    enrichment = {}
    for p in data.get("profiles", []):
        uid = p.get("traderUid", "")
        if not uid:
            continue
        wr = p.get("win_rate", 0)
        if isinstance(wr, (int, float)) and 0 < wr <= 1:
            wr = round(wr * 100, 2)
        enrichment[uid] = {
            "win_rate": wr,
            "profit_factor": p.get("profit_factor", 0),
            "total_trades": p.get("total_trades", 0),
            "total_pnl": p.get("total_pnl", 0),
            "follower_count": p.get("follower_count", 0),
            "max_drawdown": p.get("max_drawdown", 0),
            "copy_trade_days": p.get("copy_trade_days", 0),
        }

    print(f"    [OK] Bitget profiles: {len(enrichment)} trader enrichments loaded")
    return enrichment


def enrich_from_bybit_profiles():
    """Load bybit_trader_profiles.json -- enriches Bybit traders."""
    print("\n  [CRYPTO] Enriching from bybit_trader_profiles.json...")
    traders = []
    data = _load_json("bybit_trader_profiles.json")
    if not data:
        print("    [WARN] bybit_trader_profiles.json not found")
        return traders

    for p in data.get("profiles", []):
        mark = p.get("leaderMark", "")
        if not mark:
            continue
        wr = p.get("win_rate", 0)
        if isinstance(wr, (int, float)) and 0 < wr <= 1:
            wr = round(wr * 100, 2)

        traders.append({
            "platform": "Bybit",
            "asset_class": "CRYPTO",
            "trader_id": mark,
            "name": p.get("nickName", f"Bybit-{mark[:8]}"),
            "win_rate": wr,
            "roi_pct": round(float(p.get("roi", 0)) * 100, 2) if p.get("roi") else None,
            "drawdown": round(float(p.get("drawdown", 0)) * 100, 2) if p.get("drawdown") else None,
            "sharpe_ratio": p.get("sharpe_ratio", 0),
            "copiers": p.get("currentFollowerCount", 0),
            "max_copiers": p.get("maxFollowerCount", 0),
            "followers_profit": p.get("followers_profit", 0),
            "user_tags": p.get("userTags", []),
            "profile_url": f"https://www.bybit.com/copyTrade/trade-center/detail?leaderMark={mark}",
            "has_trade_history": True,
            "data_quality": "good",
            "source": "bybit_api",
        })

    print(f"    [OK] Bybit profiles: {len(traders)} traders loaded")
    return traders


def enrich_from_okx_trade_history():
    """Compute actual WR/PF from okx_trade_history.json (221 trades)."""
    print("\n  [CRYPTO] Computing metrics from okx_trade_history.json...")
    data = _load_json("okx_trade_history.json")
    if not data:
        print("    [WARN] okx_trade_history.json not found")
        return {}

    enrichment = {}
    for trader_id, trades in data.get("traders", {}).items():
        if not trades:
            continue
        wins = sum(1 for t in trades if t.get("pnl_usd", 0) > 0)
        losses = sum(1 for t in trades if t.get("pnl_usd", 0) <= 0)
        total = wins + losses
        if total == 0:
            continue

        total_profit = sum(t["pnl_usd"] for t in trades if t.get("pnl_usd", 0) > 0)
        total_loss = abs(sum(t["pnl_usd"] for t in trades if t.get("pnl_usd", 0) < 0))
        pf = round(total_profit / total_loss, 2) if total_loss > 0 else 99.99

        enrichment[trader_id] = {
            "computed_win_rate": round(wins / total * 100, 2),
            "computed_profit_factor": pf,
            "computed_total_trades": total,
            "computed_total_pnl": round(sum(t.get("pnl_usd", 0) for t in trades), 2),
            "computed_wins": wins,
            "computed_losses": losses,
        }

    print(f"    [OK] OKX trade history: {len(enrichment)} traders with computed metrics")
    return enrichment


# ============================================================
# KNOWN CRYPTO TRADERS DATABASE (from our verified research)
# ============================================================

def add_known_crypto_traders():
    """Add manually verified crypto traders from our research."""
    print("\n  [CRYPTO] Adding verified research traders...")
    known = [
        # OKX verified
        {"platform": "OKX", "trader_id": "1173EC858F15E04F", "name": "Expert-Ethash-Camel", "pnl_90d_pct": 1053.34, "copiers": 301, "aum_usd": 164000, "days_active": 821},
        {"platform": "OKX", "trader_id": "849CAD818B573125", "name": "nightraid-", "pnl_90d_pct": 255.31, "copiers": 372, "aum_usd": 164000, "days_active": 405},
        {"platform": "OKX", "trader_id": "0C053614746975C0", "name": "Fair-Hash-Maverick", "pnl_90d_pct": 238.32, "copiers": 300, "aum_usd": 77000, "days_active": 404},
        {"platform": "OKX", "trader_id": "99FB5ECCC0C27A8A", "name": "CrowleyZhou", "pnl_90d_pct": 215.74, "copiers": 580, "aum_usd": 439000, "days_active": 147},
        {"platform": "OKX", "trader_id": "AD2B6E949E5E91EC", "name": "FJ Investment", "pnl_90d_pct": 125.68, "win_rate": 54.22, "copiers": 86, "aum_usd": 520000, "days_active": 724},
        {"platform": "OKX", "trader_id": "D442CF34E4AEEAF1", "name": "Trader KS", "pnl_90d_pct": 99.93, "win_rate": 61.9, "copiers": 78, "aum_usd": 52000, "days_active": 504},
    ]
    for k in known:
        k["asset_class"] = "CRYPTO"
        k["has_trade_history"] = True
        k["data_quality"] = "excellent"
        k["source"] = "verified_research"
    print(f"    [OK] Known: {len(known)} verified crypto traders")
    return known


# ============================================================
# FOREX SOURCES
# ============================================================

def harvest_myfxbook_traders():
    """Myfxbook -- AutoTrade signal providers (90K+ members).
    The public community page lists popular trading systems.
    """
    print("\n  [FOREX] Harvesting Myfxbook AutoTrade systems...")
    traders = []

    # Community outlook / popular systems
    urls = [
        "https://www.myfxbook.com/api/get-community-outlook.json",
        "https://www.myfxbook.com/api/get-top-providers.json",
    ]

    for url in urls:
        r = _safe_get(url)
        if r:
            try:
                data = r.json()
                # Community outlook gives us sentiment data, not individual traders
                if "symbols" in data:
                    print(f"    Community sentiment data available ({len(data.get('symbols', []))} symbols)")
            except Exception:
                pass

    # Scrape AutoTrade providers page
    at_url = "https://www.myfxbook.com/autotrade"
    r = _safe_get(at_url)
    if r:
        text = r.text
        # Parse provider IDs from HTML
        # Pattern: /autotrade/provider/{id}
        provider_ids = re.findall(r'/autotrade/provider/(\d+)', text)
        names = re.findall(r'class="traderName[^"]*"[^>]*>([^<]+)<', text)
        print(f"    AutoTrade page: found {len(set(provider_ids))} provider IDs")

        for i, pid in enumerate(set(provider_ids)):
            traders.append({
                "platform": "Myfxbook",
                "asset_class": "FOREX",
                "trader_id": pid,
                "name": names[i] if i < len(names) else f"MFX-{pid}",
                "profile_url": f"https://www.myfxbook.com/autotrade/provider/{pid}",
                "has_trade_history": True,
                "data_quality": "excellent",
                "verified_by": "Myfxbook",
            })

    # SignalStart (Myfxbook-powered)
    ss_url = "https://www.signalstart.com/search-signal-providers"
    r = _safe_get(ss_url)
    if r:
        text = r.text
        sp_ids = re.findall(r'/paging/signal/(\d+)', text)
        print(f"    SignalStart page: found {len(set(sp_ids))} signal provider IDs")
        for pid in set(sp_ids):
            traders.append({
                "platform": "SignalStart",
                "asset_class": "FOREX",
                "trader_id": f"SS-{pid}",
                "name": f"SS-Provider-{pid}",
                "profile_url": f"https://www.signalstart.com/paging/signal/{pid}",
                "has_trade_history": True,
                "data_quality": "good",
                "verified_by": "Myfxbook",
            })

    print(f"    [OK] Myfxbook + SignalStart: {len(traders)} forex traders")
    return traders


def harvest_zulutrade_traders():
    """ZuluTrade REST API -- forex leaders with ZuluRank."""
    print("\n  [FOREX] Harvesting ZuluTrade leaders...")
    traders = []

    # Try the public performance page
    urls = [
        "https://www.zulutrade.com/api/traders?page=1&pageSize=100&sort=performance",
        "https://www.zulutrade.com/api/providers?page=1&limit=100",
        "https://api.zulutrade.com/api/traders/top?limit=100",
    ]

    for url in urls:
        r = _safe_get(url)
        if r:
            try:
                data = r.json()
                items = data.get("data", data.get("traders", data.get("providers", [])))
                if isinstance(items, list):
                    for item in items:
                        tid = item.get("id", item.get("providerId", ""))
                        if tid:
                            traders.append({
                                "platform": "ZuluTrade",
                                "asset_class": "FOREX",
                                "trader_id": str(tid),
                                "name": item.get("name", item.get("nickName", f"ZT-{tid}")),
                                "roi_pct": float(item.get("performance", 0)),
                                "copiers": int(item.get("followers", 0)),
                                "profile_url": f"https://www.zulutrade.com/trader/{tid}",
                                "has_trade_history": True,
                                "data_quality": "excellent",
                                "zulu_rank": item.get("rank"),
                            })
                    if traders:
                        break
            except Exception:
                pass

    # Fallback: scrape the public leaderboard page
    if not traders:
        zl_url = "https://www.zulutrade.com/traders"
        r = _safe_get(zl_url)
        if r:
            text = r.text
            trader_ids = re.findall(r'/trader/(\d+)', text)
            print(f"    ZuluTrade page: found {len(set(trader_ids))} trader IDs from HTML")
            for tid in set(trader_ids):
                traders.append({
                    "platform": "ZuluTrade",
                    "asset_class": "FOREX",
                    "trader_id": tid,
                    "name": f"ZT-{tid}",
                    "profile_url": f"https://www.zulutrade.com/trader/{tid}",
                    "has_trade_history": True,
                    "data_quality": "good",
                })

    print(f"    [OK] ZuluTrade: {len(traders)} forex traders")
    return traders


def harvest_etoro_traders():
    """eToro -- public API launched Feb 2026, Pro Investors."""
    print("\n  [FOREX] Harvesting eToro public data...")
    traders = []

    # Try the public API (launched Oct 2025, broader Feb 2026)
    urls = [
        "https://www.etoro.com/sapi/rankings/rankings?blocked=false&rankingtype=TopPerformers&period=SixMonthsAgo&pageSize=50",
        "https://api.etoro.com/sapi/rankings/rankings?period=SixMonthsAgo&pageSize=50",
    ]

    for url in urls:
        r = _safe_get(url)
        if r:
            try:
                data = r.json()
                items = data.get("Items", data.get("data", []))
                for item in items:
                    username = item.get("UserName", item.get("username", ""))
                    if username:
                        traders.append({
                            "platform": "eToro",
                            "asset_class": "FOREX",
                            "trader_id": username,
                            "name": item.get("FullName", item.get("DisplayName", username)),
                            "gain_pct": float(item.get("Gain", 0)),
                            "risk_score": item.get("RiskScore"),
                            "copiers": int(item.get("Copiers", 0)),
                            "profile_url": f"https://www.etoro.com/people/{username}/portfolio",
                            "has_trade_history": True,
                            "data_quality": "excellent",
                        })
                if traders:
                    break
            except Exception:
                pass

    print(f"    [OK] eToro: {len(traders)} forex/multi-asset traders")
    return traders


def harvest_darwinex_traders():
    """Darwinex -- DARWIN strategies via Darwin Info API."""
    print("\n  [FOREX] Harvesting Darwinex DARWINs...")
    traders = []

    # Try public endpoints
    urls = [
        "https://api.darwinex.com/darwininfo/1.1/products?productName=*&status=ACTIVE&page=0&per_page=100",
        "https://api.darwinex.com/darwininfo/1.0/products?page=0&per_page=50",
    ]

    for url in urls:
        r = _safe_get(url)
        if r:
            try:
                data = r.json()
                items = data if isinstance(data, list) else data.get("content", data.get("data", []))
                for item in items:
                    darwin_id = item.get("productName", item.get("darwinId", ""))
                    if darwin_id:
                        traders.append({
                            "platform": "Darwinex",
                            "asset_class": "FOREX",
                            "trader_id": darwin_id,
                            "name": f"DARWIN-{darwin_id}",
                            "profile_url": f"https://www.darwinex.com/darwin/{darwin_id}",
                            "has_trade_history": True,
                            "data_quality": "excellent",
                            "darwin_type": "strategy",
                        })
                if traders:
                    break
            except Exception:
                pass

    print(f"    [OK] Darwinex: {len(traders)} DARWIN strategies")
    return traders


def harvest_ctrader_traders():
    """cTrader Copy -- Spotware strategy providers."""
    print("\n  [FOREX] Harvesting cTrader Copy providers...")
    traders = []

    url = "https://ct.spotware.com/copy/strategy/list"
    r = _safe_get(url)
    if r:
        try:
            data = r.json()
            items = data.get("data", []) if isinstance(data.get("data"), list) else data if isinstance(data, list) else []
            for item in items:
                sid = item.get("strategyId", item.get("id", ""))
                if sid:
                    traders.append({
                        "platform": "cTrader",
                        "asset_class": "FOREX",
                        "trader_id": str(sid),
                        "name": item.get("strategyName", f"CT-{sid}"),
                        "roi_pct": float(item.get("roi", 0)) if item.get("roi") else None,
                        "copiers": int(item.get("copiers", 0)),
                        "profile_url": f"https://ct.spotware.com/copy/strategy/{sid}",
                        "has_trade_history": True,
                        "data_quality": "good",
                    })
        except Exception:
            pass

    # Fallback: scrape HTML
    if not traders:
        html_url = "https://ctrader.com/copy/"
        r = _safe_get(html_url)
        if r:
            text = r.text
            strategy_ids = re.findall(r'/copy/strategy/(\d+)', text)
            for sid in set(strategy_ids):
                traders.append({
                    "platform": "cTrader",
                    "asset_class": "FOREX",
                    "trader_id": sid,
                    "name": f"CT-Strategy-{sid}",
                    "profile_url": f"https://ctrader.com/copy/strategy/{sid}",
                    "has_trade_history": True,
                    "data_quality": "medium",
                })

    print(f"    [OK] cTrader: {len(traders)} strategy providers")
    return traders


# ============================================================
# REAL FOREX DATA FROM LOCAL FILES (replaces placeholders)
# ============================================================

def load_forex_trader_database():
    """Load forex_trader_database.json -- 311 verified traders from 8 platforms.
    This REPLACES the old placeholder FXL-Signal-N / FF-System-N stubs.
    """
    print("\n  [FOREX] Loading forex_trader_database.json (verified traders)...")
    traders = []

    data = _load_json("forex_trader_database.json")
    if not data:
        print("    [WARN] forex_trader_database.json not found")
        return traders

    raw = data.get("traders", [])
    for t in raw:
        name = t.get("name", t.get("username", ""))
        platform = t.get("platform", "Unknown")
        if not name:
            continue

        wr = t.get("win_rate", 0)
        if isinstance(wr, (int, float)) and 0 < wr <= 1:
            wr = round(wr * 100, 2)

        trader = {
            "platform": platform,
            "asset_class": "FOREX",
            "trader_id": t.get("id", t.get("username", _trader_id(platform, name))),
            "name": name,
            "win_rate": wr,
            "strategy_type": t.get("strategy_type", ""),
            "has_trade_history": True,
            "source": "forex_trader_database",
        }

        # Add optional fields if present
        if t.get("monthly_return_pct"):
            trader["monthly_return_pct"] = t["monthly_return_pct"]
        if t.get("annual_return_pct"):
            trader["annual_return_pct"] = t["annual_return_pct"]
        if t.get("max_drawdown_pct"):
            trader["max_drawdown_pct"] = t["max_drawdown_pct"]
        if t.get("copiers") or t.get("followers"):
            trader["copiers"] = t.get("copiers", t.get("followers", 0))
        if t.get("profit_factor"):
            trader["profit_factor"] = t["profit_factor"]
        if t.get("total_trades"):
            trader["total_trades"] = t["total_trades"]
        if t.get("pips_profit"):
            trader["pips_profit"] = t["pips_profit"]
        if t.get("risk_score"):
            trader["risk_score"] = t["risk_score"]
        if t.get("pairs_traded"):
            trader["pairs_traded"] = t["pairs_traded"]
        if t.get("experience_years") or t.get("experience_weeks"):
            trader["experience_weeks"] = t.get("experience_weeks", (t.get("experience_years", 0) * 52))
        if t.get("notes"):
            trader["notes"] = t["notes"]
        if t.get("verified"):
            trader["verified"] = True
            trader["data_quality"] = "excellent"
        else:
            trader["data_quality"] = "good"

        # Build profile URL based on platform
        if t.get("username"):
            if platform == "eToro":
                trader["profile_url"] = f"https://www.etoro.com/people/{t['username']}/portfolio"
            elif platform == "ZuluTrade":
                trader["profile_url"] = f"https://www.zulutrade.com/trader/{t['username']}"

        traders.append(trader)

    print(f"    [OK] Forex trader database: {len(traders)} verified traders loaded")
    return traders


def load_research_verified_systems():
    """Load research_verified_traders.json -- Myfxbook verified EAs, Darwinex DARWINs."""
    print("\n  [FOREX] Loading research_verified_traders.json (Myfxbook EAs, Darwinex DARWINs)...")
    traders = []

    data = _load_json("research_verified_traders.json")
    if not data:
        print("    [WARN] research_verified_traders.json not found")
        return traders

    platforms = data.get("platforms", {})

    # Myfxbook verified systems
    mfxbook = platforms.get("myfxbook", {})
    for system in mfxbook.get("top_verified_systems", []):
        name = system.get("name", "")
        if not name:
            continue

        wr = system.get("win_rate_pct")
        if wr and isinstance(wr, (int, float)) and wr > 0:
            pass  # already pct
        else:
            wr = None

        trader = {
            "platform": "Myfxbook",
            "asset_class": "FOREX",
            "trader_id": _trader_id("Myfxbook", name),
            "name": name,
            "type": system.get("type", "EA/Robot"),
            "total_gain_pct": system.get("total_gain_pct"),
            "monthly_return_pct": system.get("monthly_return_pct"),
            "max_drawdown_pct": system.get("max_drawdown_pct"),
            "profit_factor": system.get("profit_factor"),
            "total_trades": system.get("total_trades"),
            "trading_days": system.get("trading_days"),
            "strategy_type": system.get("strategy_type", ""),
            "instruments": system.get("instruments"),
            "verified": True,
            "verified_by": "Myfxbook",
            "has_trade_history": True,
            "data_quality": "excellent",
            "source": "research_verified",
        }
        if wr:
            trader["win_rate"] = wr
        traders.append(trader)

    # Darwinex DARWINs (Silver competition winners)
    darwinex = platforms.get("darwinex", {})
    for darwin in darwinex.get("top_darwins_silver_jan2026", []):
        ticker = darwin.get("ticker", "")
        if not ticker:
            continue
        traders.append({
            "platform": "Darwinex",
            "asset_class": "FOREX",
            "trader_id": f"DARWIN-{ticker}",
            "name": f"DARWIN {ticker}",
            "monthly_return_pct": darwin.get("monthly_return_pct"),
            "six_month_return_pct": darwin.get("six_month_return_pct"),
            "max_drawdown_pct": abs(darwin.get("six_month_max_drawdown_pct", 0)),
            "allocation_eur": darwin.get("latest_allocation_eur", 0),
            "profile_url": f"https://www.darwinex.com/darwin/{ticker}",
            "verified": True,
            "verified_by": "Darwinex (FCA/CNMV regulated)",
            "has_trade_history": True,
            "data_quality": "excellent",
            "source": "research_verified",
        })

    print(f"    [OK] Research verified: {len(traders)} systems (Myfxbook EAs + Darwinex DARWINs)")
    return traders


# ============================================================
# Main Harvester
# ============================================================

def run_harvest():
    """Run all harvesters and build combined database."""
    print("=" * 70)
    print("  COPYTRADER SOURCE HARVESTER v2.0")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    all_traders = []

    # ---- CRYPTO SOURCES ----
    print("\n" + "=" * 40)
    print("  CRYPTO SOURCES")
    print("=" * 40)

    # Load enrichment data first
    okx_enrichment = enrich_from_okx_profiles()
    bitget_enrichment = enrich_from_bitget_profiles()
    okx_trade_enrichment = enrich_from_okx_trade_history()

    crypto_sources = [
        ("OKX", harvest_okx_traders),
        ("Hyperliquid", harvest_hyperliquid_traders),
        ("Bitget", harvest_bitget_traders),
        ("BingX", harvest_bingx_traders),
        ("Copin.io", harvest_copin_traders),
        ("Gate.io", harvest_gate_traders),
        ("Known/Verified", add_known_crypto_traders),
        ("Qualified Traders", enrich_from_qualified_traders),
        ("Bybit Profiles", enrich_from_bybit_profiles),
    ]

    crypto_count = 0
    for name, fn in crypto_sources:
        try:
            traders = fn()
            all_traders.extend(traders)
            crypto_count += len(traders)
        except Exception as e:
            print(f"    [ERROR] {name}: {e}")

    # Apply enrichment to OKX traders
    enriched_okx = 0
    for t in all_traders:
        if t.get("platform") == "OKX":
            tid = t.get("trader_id", "")
            # Enrich from profiles
            if tid in okx_enrichment:
                enr = okx_enrichment[tid]
                if enr.get("win_rate") and not t.get("win_rate"):
                    t["win_rate"] = enr["win_rate"]
                if enr.get("profit_factor") and not t.get("profit_factor"):
                    t["profit_factor"] = enr["profit_factor"]
                if enr.get("total_trades") and not t.get("total_trades"):
                    t["total_trades"] = enr["total_trades"]
                if enr.get("avg_hold_hours"):
                    t["avg_hold_hours"] = enr["avg_hold_hours"]
                enriched_okx += 1
            # Enrich from trade history (computed metrics)
            if tid in okx_trade_enrichment:
                comp = okx_trade_enrichment[tid]
                if not t.get("win_rate") and comp.get("computed_win_rate"):
                    t["win_rate"] = comp["computed_win_rate"]
                if not t.get("profit_factor") and comp.get("computed_profit_factor"):
                    t["profit_factor"] = comp["computed_profit_factor"]
                if not t.get("total_trades") and comp.get("computed_total_trades"):
                    t["total_trades"] = comp["computed_total_trades"]
                t["computed_pnl"] = comp.get("computed_total_pnl")
                enriched_okx += 1

    # Apply enrichment to Bitget traders
    enriched_bitget = 0
    for t in all_traders:
        if t.get("platform") == "Bitget":
            tid = t.get("trader_id", "")
            if tid in bitget_enrichment:
                enr = bitget_enrichment[tid]
                if enr.get("win_rate") and not t.get("win_rate"):
                    t["win_rate"] = enr["win_rate"]
                if enr.get("profit_factor") and not t.get("profit_factor"):
                    t["profit_factor"] = enr["profit_factor"]
                if enr.get("total_trades") and not t.get("total_trades"):
                    t["total_trades"] = enr["total_trades"]
                if enr.get("copy_trade_days"):
                    t["days_active"] = enr["copy_trade_days"]
                enriched_bitget += 1

    print(f"\n    [ENRICHED] OKX: {enriched_okx} traders, Bitget: {enriched_bitget} traders")

    # ---- FOREX SOURCES ----
    print("\n" + "=" * 40)
    print("  FOREX SOURCES")
    print("=" * 40)

    forex_sources = [
        ("Myfxbook", harvest_myfxbook_traders),
        ("ZuluTrade", harvest_zulutrade_traders),
        ("eToro", harvest_etoro_traders),
        ("Darwinex", harvest_darwinex_traders),
        ("cTrader", harvest_ctrader_traders),
        # REAL data from local files (replaces old placeholders)
        ("Forex Trader DB", load_forex_trader_database),
        ("Research Verified", load_research_verified_systems),
    ]

    forex_count = 0
    for name, fn in forex_sources:
        try:
            traders = fn()
            all_traders.extend(traders)
            forex_count += len(traders)
        except Exception as e:
            print(f"    [ERROR] {name}: {e}")

    # NOTE: We NO LONGER call add_known_forex_sources() which generated
    # 150 placeholder stubs (FXL-Signal-N, FF-System-N). Those are dead.

    # Deduplicate by (platform, trader_id)
    seen = set()
    unique_traders = []
    for t in all_traders:
        key = (t.get("platform", ""), t.get("trader_id", ""))
        if key not in seen:
            seen.add(key)
            unique_traders.append(t)

    # Run quality verification on all traders
    print("\n" + "=" * 40)
    print("  QUALITY VERIFICATION")
    print("=" * 40)

    verified_traders = []
    removed_placeholder = 0
    removed_low_quality = 0
    suspicious_count = 0

    for t in unique_traders:
        quality = verify_trader_quality(t)
        t["quality_score"] = quality["score"]
        t["quality_issues"] = quality["issues"]

        if quality["is_placeholder"] and quality["score"] < 30:
            removed_placeholder += 1
            continue

        if quality["score"] < 15:
            removed_low_quality += 1
            continue

        if quality["is_suspicious"]:
            t["flagged_suspicious"] = True
            suspicious_count += 1

        verified_traders.append(t)

    print(f"    Removed {removed_placeholder} placeholder stubs")
    print(f"    Removed {removed_low_quality} low-quality entries (score < 15)")
    print(f"    Flagged {suspicious_count} suspicious traders")
    print(f"    Kept {len(verified_traders)} verified traders")

    # Sort by quality score (descending), then platform
    verified_traders.sort(key=lambda x: (
        -x.get("quality_score", 0),
        {"excellent": 0, "good": 1, "medium": 2}.get(x.get("data_quality", "medium"), 3),
        x.get("platform", ""),
    ))

    # Separate by asset class
    crypto_traders = [t for t in verified_traders if t.get("asset_class") == "CRYPTO"]
    forex_traders = [t for t in verified_traders if t.get("asset_class") == "FOREX"]

    # By platform summary
    by_platform = defaultdict(lambda: {"count": 0, "crypto": 0, "forex": 0})
    for t in verified_traders:
        p = t.get("platform", "Unknown")
        by_platform[p]["count"] += 1
        if t.get("asset_class") == "CRYPTO":
            by_platform[p]["crypto"] += 1
        elif t.get("asset_class") == "FOREX":
            by_platform[p]["forex"] += 1

    # Quality score distribution
    score_buckets = {"90-100": 0, "70-89": 0, "50-69": 0, "30-49": 0, "15-29": 0}
    for t in verified_traders:
        s = t.get("quality_score", 0)
        if s >= 90:
            score_buckets["90-100"] += 1
        elif s >= 70:
            score_buckets["70-89"] += 1
        elif s >= 50:
            score_buckets["50-69"] += 1
        elif s >= 30:
            score_buckets["30-49"] += 1
        else:
            score_buckets["15-29"] += 1

    # Remove internal quality_issues from output (too verbose for JSON)
    for t in verified_traders:
        t.pop("quality_issues", None)

    # Save full database
    now_iso = datetime.now(timezone.utc).isoformat()
    output = {
        "generated_at": now_iso,
        "version": "2.0",
        "total_unique": len(verified_traders),
        "crypto_total": len(crypto_traders),
        "forex_total": len(forex_traders),
        "quality_distribution": score_buckets,
        "placeholders_removed": removed_placeholder,
        "suspicious_flagged": suspicious_count,
        "new_from_stealth": 0,
        "by_platform": {k: v for k, v in sorted(by_platform.items(), key=lambda x: x[1]["count"], reverse=True)},
        "crypto_traders": crypto_traders,
        "forex_traders": forex_traders,
    }

    path = DATA_DIR / "copytrader_database.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 70)
    print("  HARVEST SUMMARY v2.0")
    print("=" * 70)
    print(f"  Total verified traders: {len(verified_traders)}")
    print(f"    Crypto: {len(crypto_traders)}")
    print(f"    Forex: {len(forex_traders)}")
    print(f"    Removed: {removed_placeholder} placeholders + {removed_low_quality} low-quality")
    print()
    print(f"  {'Platform':25s} {'Total':>6s} {'Crypto':>7s} {'Forex':>6s}")
    print("  " + "-" * 50)
    for p, stats in sorted(by_platform.items(), key=lambda x: x[1]["count"], reverse=True):
        print(f"  {p:25s} {stats['count']:6d} {stats['crypto']:7d} {stats['forex']:6d}")

    # Quality breakdown
    by_quality = defaultdict(int)
    for t in verified_traders:
        by_quality[t.get("data_quality", "unknown")] += 1
    print(f"\n  Data Quality: {dict(by_quality)}")
    print(f"  Score Distribution: {score_buckets}")

    target_crypto = 300
    target_forex = 300
    crypto_gap = max(0, target_crypto - len(crypto_traders))
    forex_gap = max(0, target_forex - len(forex_traders))

    print(f"\n  Target: {target_crypto} crypto / {target_forex} forex")
    print(f"  Gap: {crypto_gap} crypto / {forex_gap} forex remaining")

    if crypto_gap > 0 or forex_gap > 0:
        print("\n  [INFO] Additional sources to reach targets:")
        if crypto_gap > 0:
            print(f"    Crypto ({crypto_gap} needed):")
            print(f"      - Bybit leaderboard (browser scrape needed)")
            print(f"      - Copin.io additional protocols (DYDX, APEX, etc)")
            print(f"      - Binance Copy Trading (JS-rendered, Playwright needed)")
            print(f"      - Dune Analytics top wallets")
        if forex_gap > 0:
            print(f"    Forex ({forex_gap} needed):")
            print(f"      - Myfxbook AutoTrade full pagination (50 per page, 90K+ total)")
            print(f"      - ZuluTrade full API pagination")
            print(f"      - eToro Pro Investors (API pagination)")
            print(f"      - NAGA social traders")
            print(f"      - FxStat community")

    print(f"\n  [OK] Database saved -> {path}")
    print("=" * 70)

    return output


if __name__ == "__main__":
    run_harvest()
