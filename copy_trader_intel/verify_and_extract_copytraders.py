#!/usr/bin/env python3
"""
verify_and_extract_copytraders.py
==================================
Phase 1: Verify API sources by pulling real trade data
Phase 2: Extract trade history from working sources
Phase 3: Reverse-engineer strategy DNA from trade patterns
Phase 4: Create test portfolios per trader for monitoring

Run: python copy_trader_intel/verify_and_extract_copytraders.py
"""

import json, sys, os, time, math, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

import requests

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json,text/html,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================
# PHASE 1: Verify each source
# ============================================================

def verify_all_sources():
    """Test every data source and report which ones work."""
    print("=" * 70)
    print("  PHASE 1: VERIFY DATA SOURCES")
    print("=" * 70)

    results = {}

    # --- OKX Copy Trading API ---
    print("\n  [1] OKX Copy Trading API...")
    try:
        r = requests.get(
            "https://www.okx.com/api/v5/copytrading/public-lead-traders",
            headers=HEADERS, timeout=15
        )
        data = r.json()
        code = data.get("code", "?")
        traders = data.get("data", [])
        if code == "0" and traders:
            results["OKX"] = {"status": "VERIFIED", "traders": len(traders), "type": "REST_API", "asset": "CRYPTO"}
            print(f"    [OK] {len(traders)} traders, API code={code}")
            for t in traders[:3]:
                print(f"      {t.get('nickName','?')} | {float(t.get('pnlRatio',0))*100:.1f}% | {t.get('copyTraderNum',0)} copiers")
        else:
            results["OKX"] = {"status": "FAILED", "code": code, "msg": data.get("msg", "")}
            print(f"    [FAIL] code={code}, msg={data.get('msg','')}")
    except Exception as e:
        results["OKX"] = {"status": "ERROR", "error": str(e)}
        print(f"    [ERROR] {e}")

    # --- OKX Trade History (for a known trader) ---
    print("\n  [2] OKX Trade History API...")
    okx_test_code = "99FB5ECCC0C27A8A"  # CrowleyZhou
    try:
        r = requests.get(
            "https://www.okx.com/api/v5/copytrading/public-subpositions-history",
            params={"uniqueCode": okx_test_code, "limit": 10},
            headers=HEADERS, timeout=15
        )
        data = r.json()
        trades = data.get("data", [])
        if trades:
            results["OKX_HISTORY"] = {"status": "VERIFIED", "trades": len(trades), "type": "REST_API"}
            print(f"    [OK] {len(trades)} historical trades for CrowleyZhou")
            for t in trades[:3]:
                pnl = float(t.get("pnl", 0))
                inst = t.get("instId", "?")
                side = t.get("posSide", "?")
                lever = t.get("lever", "?")
                print(f"      {inst} {side} {lever}x | PnL: ${pnl:.2f}")
        else:
            results["OKX_HISTORY"] = {"status": "EMPTY", "code": data.get("code"), "msg": data.get("msg")}
            print(f"    [EMPTY] {data.get('msg','no trades')}")
    except Exception as e:
        results["OKX_HISTORY"] = {"status": "ERROR", "error": str(e)}
        print(f"    [ERROR] {e}")

    # --- Hyperliquid API ---
    print("\n  [3] Hyperliquid Leaderboard...")
    try:
        r = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "leaderboard"},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            n = len(data) if isinstance(data, list) else len(data.get("leaderboardRows", []))
            results["Hyperliquid"] = {"status": "VERIFIED", "traders": n, "type": "POST_API", "asset": "CRYPTO"}
            print(f"    [OK] {n} leaderboard entries")
        else:
            # Try alternate format
            r2 = requests.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "leaderboard", "timeWindow": "month"},
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            data2 = r2.json()
            rows = data2.get("leaderboardRows", []) if isinstance(data2, dict) else data2
            results["Hyperliquid"] = {"status": "PARTIAL", "response_code": r.status_code, "alt_code": r2.status_code, "rows": len(rows) if isinstance(rows, list) else 0}
            print(f"    [PARTIAL] Status {r.status_code}, alt: {r2.status_code}")
    except Exception as e:
        results["Hyperliquid"] = {"status": "ERROR", "error": str(e)}
        print(f"    [ERROR] {e}")

    # --- Hyperliquid User Fills (for a known whale) ---
    print("\n  [4] Hyperliquid User Fills...")
    hl_test_addr = "0x393d4562ff tried"
    try:
        r = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "userFills", "user": "0x393dbe8a31e94a0e5471d4baa1050469e842c109"},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        data = r.json()
        fills = data if isinstance(data, list) else data.get("fills", [])
        results["Hyperliquid_Fills"] = {"status": "VERIFIED" if fills else "EMPTY", "fills": len(fills)}
        print(f"    [{'OK' if fills else 'EMPTY'}] {len(fills)} fills")
        if fills:
            for f in fills[:3]:
                print(f"      {f.get('coin','?')} {f.get('side','?')} {f.get('sz','?')} @ {f.get('px','?')}")
    except Exception as e:
        results["Hyperliquid_Fills"] = {"status": "ERROR", "error": str(e)}
        print(f"    [ERROR] {e}")

    # --- Myfxbook Community ---
    print("\n  [5] Myfxbook Community Outlook...")
    try:
        r = requests.get(
            "https://www.myfxbook.com/api/get-community-outlook.json",
            headers=HEADERS, timeout=15
        )
        data = r.json()
        symbols = data.get("symbols", [])
        results["Myfxbook"] = {"status": "VERIFIED" if symbols else "EMPTY", "symbols": len(symbols), "type": "REST_API", "asset": "FOREX"}
        print(f"    [{'OK' if symbols else 'EMPTY'}] {len(symbols)} symbols")
        if symbols:
            for s in symbols[:3]:
                name = s.get("name", "?")
                long_pct = s.get("longPercentage", 0)
                print(f"      {name}: {long_pct}% long")
    except Exception as e:
        results["Myfxbook"] = {"status": "ERROR", "error": str(e)}
        print(f"    [ERROR] {e}")

    # --- Myfxbook Systems (AutoTrade) ---
    print("\n  [6] Myfxbook AutoTrade Systems...")
    try:
        r = requests.get(
            "https://www.myfxbook.com/systems",
            headers=HEADERS, timeout=15
        )
        # Parse system IDs from HTML
        system_ids = re.findall(r'/system/(\d+)', r.text)
        unique_ids = list(set(system_ids))
        results["Myfxbook_Systems"] = {"status": "VERIFIED" if unique_ids else "EMPTY", "systems": len(unique_ids), "type": "HTML_SCRAPE", "asset": "FOREX"}
        print(f"    [{'OK' if unique_ids else 'EMPTY'}] {len(unique_ids)} systems from HTML")
    except Exception as e:
        results["Myfxbook_Systems"] = {"status": "ERROR", "error": str(e)}
        print(f"    [ERROR] {e}")

    # --- Myfxbook Strategies Page ---
    print("\n  [7] Myfxbook Strategies...")
    try:
        r = requests.get(
            "https://www.myfxbook.com/strategies",
            headers=HEADERS, timeout=15
        )
        strat_ids = re.findall(r'data-strategy-id="(\d+)"', r.text)
        if not strat_ids:
            strat_ids = re.findall(r'/strategy/[^/]+/(\d+)', r.text)
        unique_strats = list(set(strat_ids))
        results["Myfxbook_Strategies"] = {"status": "VERIFIED" if unique_strats else "EMPTY", "strategies": len(unique_strats)}
        print(f"    [{'OK' if unique_strats else 'EMPTY'}] {len(unique_strats)} strategies")
    except Exception as e:
        results["Myfxbook_Strategies"] = {"status": "ERROR", "error": str(e)}
        print(f"    [ERROR] {e}")

    # --- Copin.io API ---
    print("\n  [8] Copin.io Aggregator...")
    try:
        r = requests.get(
            "https://api.copin.io/traders?protocol=HYPERLIQUID&sortBy=pnl&sortType=desc&limit=20",
            headers=HEADERS, timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", data) if isinstance(data, (dict, list)) else []
            if isinstance(items, dict):
                items = items.get("data", [])
            results["Copin"] = {"status": "VERIFIED", "traders": len(items) if isinstance(items, list) else 0, "type": "REST_API", "asset": "CRYPTO"}
            print(f"    [OK] {len(items) if isinstance(items, list) else '?'} traders")
        else:
            results["Copin"] = {"status": "FAILED", "http_code": r.status_code}
            print(f"    [FAIL] HTTP {r.status_code}")
    except Exception as e:
        results["Copin"] = {"status": "ERROR", "error": str(e)}
        print(f"    [ERROR] {e}")

    # --- BingX Copy Trading ---
    print("\n  [9] BingX Copy Trading...")
    try:
        r = requests.get(
            "https://bingx.com/api/copy-trade/v1/public/trader/list?page=1&pageSize=20",
            headers=HEADERS, timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", {}).get("list", []) if isinstance(data.get("data"), dict) else []
            results["BingX"] = {"status": "VERIFIED" if items else "EMPTY", "traders": len(items), "type": "REST_API", "asset": "CRYPTO"}
            print(f"    [{'OK' if items else 'EMPTY'}] {len(items)} traders")
        else:
            results["BingX"] = {"status": "FAILED", "http_code": r.status_code}
            print(f"    [FAIL] HTTP {r.status_code}")
    except Exception as e:
        results["BingX"] = {"status": "ERROR", "error": str(e)}
        print(f"    [ERROR] {e}")

    # --- SignalStart ---
    print("\n  [10] SignalStart Signal Providers...")
    try:
        r = requests.get(
            "https://www.signalstart.com/search-signal-providers",
            headers=HEADERS, timeout=15
        )
        provider_ids = re.findall(r'/paging/signal/(\d+)', r.text)
        unique_providers = list(set(provider_ids))
        results["SignalStart"] = {"status": "VERIFIED" if unique_providers else "EMPTY", "providers": len(unique_providers), "type": "HTML_SCRAPE", "asset": "FOREX"}
        print(f"    [{'OK' if unique_providers else 'EMPTY'}] {len(unique_providers)} providers from HTML")
    except Exception as e:
        results["SignalStart"] = {"status": "ERROR", "error": str(e)}
        print(f"    [ERROR] {e}")

    print("\n" + "=" * 70)
    print("  SOURCE VERIFICATION SUMMARY")
    print("=" * 70)
    verified = [k for k, v in results.items() if v.get("status") == "VERIFIED"]
    failed = [k for k, v in results.items() if v.get("status") in ("FAILED", "ERROR", "EMPTY")]
    print(f"  VERIFIED: {len(verified)} — {', '.join(verified)}")
    print(f"  FAILED:   {len(failed)} — {', '.join(failed)}")

    return results


# ============================================================
# PHASE 2: Extract trade history from verified sources
# ============================================================

def extract_okx_trade_history(unique_codes, max_per_trader=100):
    """Pull full trade history from OKX for given trader codes."""
    print("\n" + "=" * 70)
    print("  PHASE 2: EXTRACT OKX TRADE HISTORY")
    print("=" * 70)

    all_trades = {}
    for code in unique_codes:
        print(f"\n  Fetching {code}...")
        try:
            r = requests.get(
                "https://www.okx.com/api/v5/copytrading/public-subpositions-history",
                params={"uniqueCode": code, "limit": max_per_trader},
                headers=HEADERS, timeout=15
            )
            data = r.json()
            trades = data.get("data", [])
            print(f"    {len(trades)} trades")

            enriched = []
            for t in trades:
                hold_ms = int(t.get("closeTime", 0)) - int(t.get("openTime", 0))
                hold_hours = hold_ms / 3_600_000 if hold_ms > 0 else 0
                pnl = float(t.get("pnl", 0))
                pnl_ratio = float(t.get("pnlRatio", 0))

                enriched.append({
                    "inst": t.get("instId", ""),
                    "side": t.get("posSide", ""),
                    "leverage": float(t.get("lever", 0)),
                    "margin_mode": t.get("mgnMode", ""),
                    "entry_price": float(t.get("openAvgPx", 0)),
                    "exit_price": float(t.get("closeAvgPx", 0)),
                    "open_time": int(t.get("openTime", 0)),
                    "close_time": int(t.get("closeTime", 0)),
                    "hold_hours": round(hold_hours, 2),
                    "pnl_usd": round(pnl, 2),
                    "pnl_pct": round(pnl_ratio * 100, 4),
                    "size": float(t.get("subPos", 0)),
                    "trade_id": t.get("subPosId", ""),
                })

            all_trades[code] = enriched
            time.sleep(0.5)  # Rate limit
        except Exception as e:
            print(f"    [ERROR] {e}")
            all_trades[code] = []

    path = DATA_DIR / "okx_trade_history.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "traders": all_trades,
            "total_trades": sum(len(v) for v in all_trades.values()),
        }, f, indent=2)
    print(f"\n  [OK] Saved {sum(len(v) for v in all_trades.values())} trades -> {path}")
    return all_trades


def extract_hyperliquid_fills(addresses, max_per_trader=200):
    """Pull fill history from Hyperliquid for given addresses."""
    print("\n" + "=" * 70)
    print("  PHASE 2: EXTRACT HYPERLIQUID FILLS")
    print("=" * 70)

    all_fills = {}
    for addr in addresses:
        print(f"\n  Fetching {addr[:10]}...")
        try:
            r = requests.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "userFills", "user": addr},
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            fills = r.json() if r.status_code == 200 else []
            if isinstance(fills, list):
                enriched = []
                for f in fills[:max_per_trader]:
                    enriched.append({
                        "coin": f.get("coin", ""),
                        "side": f.get("side", ""),
                        "price": float(f.get("px", 0)),
                        "size": float(f.get("sz", 0)),
                        "time": f.get("time", 0),
                        "fee": float(f.get("fee", 0)),
                        "closed_pnl": float(f.get("closedPnl", 0)),
                        "hash": f.get("hash", ""),
                    })
                all_fills[addr] = enriched
                print(f"    {len(enriched)} fills")
            else:
                all_fills[addr] = []
                print(f"    [EMPTY/ERROR] {type(fills)}")
            time.sleep(0.3)
        except Exception as e:
            print(f"    [ERROR] {e}")
            all_fills[addr] = []

    path = DATA_DIR / "hyperliquid_fills.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "traders": all_fills,
            "total_fills": sum(len(v) for v in all_fills.values()),
        }, f, indent=2)
    print(f"\n  [OK] Saved {sum(len(v) for v in all_fills.values())} fills -> {path}")
    return all_fills


# ============================================================
# PHASE 3: Reverse-engineer strategy DNA
# ============================================================

def reverse_engineer_trader(trader_id, trades, platform="OKX"):
    """Analyze a trader's history and extract strategy DNA."""
    if not trades:
        return None

    # Basic metrics
    n = len(trades)
    pnls = [t.get("pnl_usd", t.get("closed_pnl", 0)) for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    win_rate = wins / n if n > 0 else 0

    # Hold time analysis
    hold_key = "hold_hours" if "hold_hours" in (trades[0] if trades else {}) else None
    if hold_key:
        holds = [t[hold_key] for t in trades if t.get(hold_key, 0) > 0]
    else:
        holds = []
    avg_hold = sum(holds) / len(holds) if holds else 0
    median_hold = sorted(holds)[len(holds)//2] if holds else 0

    # Leverage analysis
    leverages = [t.get("leverage", 0) for t in trades if t.get("leverage", 0) > 0]
    avg_leverage = sum(leverages) / len(leverages) if leverages else 0

    # Directional bias
    longs = sum(1 for t in trades if t.get("side", "").lower() in ("long", "buy", "b"))
    shorts = sum(1 for t in trades if t.get("side", "").lower() in ("short", "sell", "s"))
    long_pct = longs / n if n > 0 else 0.5

    # Instrument concentration
    inst_key = "inst" if "inst" in (trades[0] if trades else {}) else "coin"
    instruments = [t.get(inst_key, "UNKNOWN") for t in trades]
    inst_counts = defaultdict(int)
    for inst in instruments:
        inst_counts[inst] += 1
    top_instruments = sorted(inst_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    concentration = top_instruments[0][1] / n if top_instruments and n > 0 else 0

    # Session timing (UTC hour distribution)
    time_key = "open_time" if "open_time" in (trades[0] if trades else {}) else "time"
    hours = []
    for t in trades:
        ts = t.get(time_key, 0)
        if ts > 1e12:
            ts /= 1000  # Convert ms to s
        if ts > 0:
            try:
                h = datetime.fromtimestamp(ts, tz=timezone.utc).hour
                hours.append(h)
            except Exception:
                pass
    hour_dist = defaultdict(int)
    for h in hours:
        hour_dist[h] += 1
    peak_hour = max(hour_dist, key=hour_dist.get) if hour_dist else None
    # Map to session
    if peak_hour is not None:
        if 0 <= peak_hour < 8:
            session = "ASIA"
        elif 8 <= peak_hour < 16:
            session = "EUROPE"
        else:
            session = "US"
    else:
        session = "UNKNOWN"

    # PnL distribution
    avg_win = sum(p for p in pnls if p > 0) / wins if wins > 0 else 0
    avg_loss = abs(sum(p for p in pnls if p < 0) / losses) if losses > 0 else 0
    risk_reward = avg_win / avg_loss if avg_loss > 0 else 0
    profit_factor = sum(p for p in pnls if p > 0) / abs(sum(p for p in pnls if p < 0)) if sum(p for p in pnls if p < 0) != 0 else 99

    # Classify archetype
    if avg_hold < 2:
        archetype = "SCALPER"
    elif avg_hold < 24:
        archetype = "DAY_TRADER"
    elif avg_hold < 168:
        archetype = "SWING_TRADER"
    else:
        archetype = "POSITION_TRADER"

    if avg_leverage > 20:
        risk_profile = "HIGH_RISK"
    elif avg_leverage > 5:
        risk_profile = "MEDIUM_RISK"
    else:
        risk_profile = "LOW_RISK"

    # Strategy DNA
    dna = {
        "trader_id": trader_id,
        "platform": platform,
        "total_trades": n,
        "archetype": archetype,
        "risk_profile": risk_profile,
        "metrics": {
            "win_rate": round(win_rate * 100, 2),
            "profit_factor": round(profit_factor, 2),
            "risk_reward_ratio": round(risk_reward, 2),
            "avg_win_usd": round(avg_win, 2),
            "avg_loss_usd": round(avg_loss, 2),
            "total_pnl_usd": round(sum(pnls), 2),
        },
        "style": {
            "avg_hold_hours": round(avg_hold, 2),
            "median_hold_hours": round(median_hold, 2),
            "avg_leverage": round(avg_leverage, 1),
            "long_bias_pct": round(long_pct * 100, 1),
            "primary_session": session,
            "peak_hour_utc": peak_hour,
        },
        "instruments": {
            "top_5": [{"name": k, "trades": v, "pct": round(v/n*100, 1)} for k, v in top_instruments],
            "concentration_pct": round(concentration * 100, 1),
            "unique_count": len(inst_counts),
        },
        "clone_params": {
            "direction_bias": "LONG" if long_pct > 0.6 else ("SHORT" if long_pct < 0.4 else "NEUTRAL"),
            "hold_time_range": f"{min(holds):.1f}-{max(holds):.1f}h" if holds else "unknown",
            "leverage_range": f"{min(leverages):.0f}-{max(leverages):.0f}x" if leverages else "unknown",
            "preferred_instruments": [k for k, v in top_instruments[:3]],
            "preferred_session": session,
            "tp_estimate_pct": round(avg_win / (sum(abs(t.get("entry_price", t.get("price", 1))) for t in trades) / max(n, 1)) * 100, 4) if avg_win > 0 else 0,
            "sl_estimate_pct": round(avg_loss / (sum(abs(t.get("entry_price", t.get("price", 1))) for t in trades) / max(n, 1)) * 100, 4) if avg_loss > 0 else 0,
        },
    }

    return dna


def run_reverse_engineering(all_trade_data):
    """Run reverse engineering on all extracted trade data."""
    print("\n" + "=" * 70)
    print("  PHASE 3: REVERSE ENGINEER STRATEGY DNA")
    print("=" * 70)

    dna_profiles = {}
    for trader_id, trades in all_trade_data.items():
        if not trades:
            continue
        platform = "OKX" if "inst" in (trades[0] if trades else {}) else "Hyperliquid"
        dna = reverse_engineer_trader(trader_id, trades, platform)
        if dna:
            dna_profiles[trader_id] = dna
            print(f"\n  {trader_id[:16]}... ({platform})")
            print(f"    Archetype: {dna['archetype']} | Risk: {dna['risk_profile']}")
            print(f"    WR: {dna['metrics']['win_rate']}% | PF: {dna['metrics']['profit_factor']} | R:R: {dna['metrics']['risk_reward_ratio']}")
            print(f"    Hold: {dna['style']['avg_hold_hours']}h | Leverage: {dna['style']['avg_leverage']}x | Bias: {dna['clone_params']['direction_bias']}")
            print(f"    Session: {dna['style']['primary_session']} | Top: {', '.join(dna['clone_params']['preferred_instruments'][:3])}")

    path = DATA_DIR / "trader_dna_profiles.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_profiles": len(dna_profiles),
            "profiles": dna_profiles,
        }, f, indent=2)

    print(f"\n  [OK] {len(dna_profiles)} DNA profiles -> {path}")
    return dna_profiles


# ============================================================
# PHASE 4: Create test portfolios
# ============================================================

def create_test_portfolios(dna_profiles, trade_data):
    """Create test portfolios per trader to monitor performance."""
    print("\n" + "=" * 70)
    print("  PHASE 4: CREATE TEST PORTFOLIOS")
    print("=" * 70)

    portfolios = {}

    for trader_id, dna in dna_profiles.items():
        trades = trade_data.get(trader_id, [])
        if not trades or len(trades) < 5:
            continue

        # Use the most recent trades as "test" positions
        recent_trades = sorted(trades, key=lambda t: t.get("close_time", t.get("time", 0)), reverse=True)[:10]

        # Extract test portfolio params from DNA
        portfolio = {
            "trader_id": trader_id,
            "platform": dna["platform"],
            "archetype": dna["archetype"],
            "strategy_name": f"clone_{dna['archetype'].lower()}_{trader_id[:8]}",
            "clone_params": dna["clone_params"],
            "test_positions": [],
            "performance": {
                "total_trades": len(trades),
                "test_trades": len(recent_trades),
                "test_win_rate": 0,
                "test_pnl": 0,
            },
        }

        # Build test positions from recent trades
        test_wins = 0
        test_pnl = 0
        for t in recent_trades:
            pnl = t.get("pnl_usd", t.get("closed_pnl", 0))
            entry = t.get("entry_price", t.get("price", 0))
            inst = t.get("inst", t.get("coin", "UNKNOWN"))
            side = t.get("side", "unknown")
            hold = t.get("hold_hours", 0)

            if pnl > 0:
                test_wins += 1
            test_pnl += pnl

            portfolio["test_positions"].append({
                "instrument": inst,
                "direction": side,
                "entry_price": entry,
                "exit_price": t.get("exit_price", 0),
                "pnl_usd": round(pnl, 2),
                "hold_hours": hold,
                "status": "CLOSED",
            })

        portfolio["performance"]["test_win_rate"] = round(test_wins / len(recent_trades) * 100, 1) if recent_trades else 0
        portfolio["performance"]["test_pnl"] = round(test_pnl, 2)

        portfolios[trader_id] = portfolio

        print(f"\n  Portfolio: {portfolio['strategy_name']}")
        print(f"    {len(recent_trades)} test trades | WR: {portfolio['performance']['test_win_rate']}% | PnL: ${portfolio['performance']['test_pnl']:.2f}")

    # Save portfolios
    path = DATA_DIR / "copytrader_test_portfolios.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_portfolios": len(portfolios),
            "portfolios": portfolios,
        }, f, indent=2)

    print(f"\n  [OK] {len(portfolios)} test portfolios -> {path}")

    # Summary table
    print("\n  " + "=" * 70)
    print("  TEST PORTFOLIO SUMMARY")
    print("  " + "=" * 70)
    print(f"  {'Strategy':35s} {'Type':15s} {'WR%':>5s} {'PnL$':>8s} {'Trades':>6s}")
    print("  " + "-" * 70)
    for tid, p in sorted(portfolios.items(), key=lambda x: x[1]["performance"]["test_pnl"], reverse=True):
        print(f"  {p['strategy_name']:35s} {p['archetype']:15s} {p['performance']['test_win_rate']:4.1f}% {p['performance']['test_pnl']:+7.2f} {p['performance']['test_trades']:6d}")
    print("  " + "=" * 70)

    return portfolios


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 70)
    print("  COPYTRADER VERIFY → EXTRACT → REVERSE-ENGINEER → TEST")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Phase 1: Verify
    source_results = verify_all_sources()

    # Phase 2: Extract from verified sources
    # OKX — our best source
    okx_codes = [
        "1173EC858F15E04F",  # Expert-Ethash-Camel
        "849CAD818B573125",  # nightraid-
        "0C053614746975C0",  # Fair-Hash-Maverick
        "99FB5ECCC0C27A8A",  # CrowleyZhou
        "AD2B6E949E5E91EC",  # FJ Investment
        "D442CF34E4AEEAF1",  # Trader KS
    ]

    # Also pull leaderboard traders if verified
    if source_results.get("OKX", {}).get("status") == "VERIFIED":
        try:
            r = requests.get(
                "https://www.okx.com/api/v5/copytrading/public-lead-traders",
                headers=HEADERS, timeout=15
            )
            data = r.json()
            for t in data.get("data", []):
                code = t.get("uniqueCode", "")
                if code and code not in okx_codes:
                    okx_codes.append(code)
        except Exception:
            pass

    okx_trades = extract_okx_trade_history(okx_codes)

    # Hyperliquid fills
    hl_addresses = [
        "0x393dbe8a31e94a0e5471d4baa1050469e842c109",
        "0x488d2e08a7be65e6138df5c01f0e29b2b06f7fe08",
        "0xe44b004f02b4285e67fb2e40e1d3f7f06a3b9ea8",
        "0x05cac655fd4d4ab9fc4e1c0f5c7e39bd06f0c655",
    ]
    hl_fills = extract_hyperliquid_fills(hl_addresses)

    # Merge all trade data
    all_trades = {}
    all_trades.update(okx_trades)
    all_trades.update(hl_fills)

    # Phase 3: Reverse engineer
    dna_profiles = run_reverse_engineering(all_trades)

    # Phase 4: Test portfolios
    portfolios = create_test_portfolios(dna_profiles, all_trades)

    # Final summary
    print("\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)
    verified_sources = [k for k, v in source_results.items() if v.get("status") == "VERIFIED"]
    print(f"  Verified sources: {len(verified_sources)} — {', '.join(verified_sources)}")
    print(f"  Total trades extracted: {sum(len(v) for v in all_trades.values())}")
    print(f"  DNA profiles: {len(dna_profiles)}")
    print(f"  Test portfolios: {len(portfolios)}")
    print(f"\n  Next steps:")
    print(f"    1. Install crawl4ai for JS-rendered sources (Bitget, Bybit, eToro)")
    print(f"    2. Add Myfxbook system trader history extraction")
    print(f"    3. Set up cron for daily portfolio tracking")
    print(f"    4. Feed results to audit dashboard")
    print("=" * 70)


if __name__ == "__main__":
    main()
