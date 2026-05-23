#!/usr/bin/env python3
"""Local real-time scanner -- validates scoring + live prices for buy guide."""

import json
import os
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "local_scan_history.json")

CORR_GROUPS = {
    "large_cap": ["BTC", "ETH"],
    "alt_l1": ["SOL", "AVAX", "NEAR", "DOT"],
    "defi": ["LINK", "UNI", "AAVE"],
    "meme": ["DOGE", "SHIB"],
    "exchange": ["BNB"],
    "infra": ["RENDER", "FIL", "FET"],
}

BLACKLIST = {
    "BTCUSDT", "ADAUSDT", "ADA-USD", "WIF-USD", "WIFUSDT", "SOL-USD",
    "AVAX-USD", "DOT-USD", "TIA-USD", "ETC-USD", "SPY", "QQQ",
    "BONK-USD", "FLOKI-USD", "STRKUSDT", "INJUSDT", "POLUSDT",
}


def norm_sym(s):
    return s.upper().replace("-USD", "USDT").replace("=X", "").replace(" ", "")


def get_group(sym):
    base = sym.upper().replace("-USD", "").replace("USDT", "")
    for g, syms in CORR_GROUPS.items():
        if base in syms:
            return g
    return "other"


def fetch_prices():
    try:
        req = urllib.request.Request(
            "https://api.binance.com/api/v3/ticker/price",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return {t["symbol"]: float(t["price"]) for t in data}
    except Exception:
        try:
            cg_url = (
                "https://api.coingecko.com/api/v3/simple/price?"
                "ids=bitcoin,ethereum,solana,dogecoin,ripple,cardano,"
                "avalanche-2,chainlink,polkadot,near,shiba-inu,filecoin,"
                "bnb,fetch-ai,render-token,atom,cake,tron&vs_currencies=usd"
            )
            req = urllib.request.Request(cg_url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            cg = json.loads(resp.read())
            mapping = {
                "bitcoin": "BTCUSDT", "ethereum": "ETHUSDT", "solana": "SOLUSDT",
                "dogecoin": "DOGEUSDT", "ripple": "XRPUSDT", "cardano": "ADAUSDT",
                "chainlink": "LINKUSDT", "near": "NEARUSDT", "bnb": "BNBUSDT",
                "fetch-ai": "FETUSDT", "render-token": "RENDERUSDT", "tron": "TRXUSDT",
            }
            prices = {}
            for cg_id, sym in mapping.items():
                if cg_id in cg and "usd" in cg[cg_id]:
                    prices[sym] = float(cg[cg_id]["usd"])
            return prices
        except Exception:
            return {}


def run_scan():
    from elite_scorer import compute_elite_score

    now = datetime.now(timezone.utc)
    prices = fetch_prices()
    print(f"Prices: {len(prices)} symbols from Binance")

    # Load picks
    ap_file = os.path.join(DATA_DIR, "active_picks.json")
    with open(ap_file, encoding="utf-8") as f:
        raw = json.load(f)
    picks = raw.get("picks", []) if isinstance(raw, dict) else raw if isinstance(raw, list) else []
    picks = [p for p in picks if isinstance(p, dict)]

    # Re-score and enrich
    for p in picks:
        sym = p.get("symbol", "")
        result = compute_elite_score(p)
        p["fresh_score"] = result["elite_score"]
        p["fresh_grade"] = result["elite_grade"]
        p["fresh_bd"] = result["elite_breakdown"]

        nsym = norm_sym(sym)
        live = prices.get(nsym, 0)
        entry = float(p.get("entry_price", 0) or 0)
        tp = float(p.get("take_profit", 0) or 0)
        sl = float(p.get("stop_loss", 0) or 0)
        direction = str(p.get("direction", p.get("signal_type", "LONG"))).upper()

        if live > 0 and entry > 0:
            spot = ((live - entry) / entry * 100) if direction in ("LONG", "BUY") else ((entry - live) / entry * 100)
            tp_prog = 0
            if direction in ("LONG", "BUY") and tp > entry:
                tp_prog = (live - entry) / (tp - entry) * 100
            elif direction in ("SHORT", "SELL") and tp < entry:
                tp_prog = (entry - live) / (entry - tp) * 100
            p["live"] = live
            p["spot_pnl"] = round(spot, 4)
            p["tp_prog"] = round(min(100, max(0, tp_prog)), 1)
            p["lev_pnl"] = round(spot * 20, 2)
            p["risk_pct"] = round(abs(entry - sl) / entry * 100, 2) if sl > 0 else 0
        else:
            p["live"] = 0
            p["spot_pnl"] = 0
            p["tp_prog"] = 0
            p["lev_pnl"] = 0
            p["risk_pct"] = 0

    picks.sort(key=lambda x: x["fresh_score"], reverse=True)

    # -- Output --
    print()
    print("=" * 80)
    print(f"  REAL-TIME LOCAL SCAN -- {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 80)

    # Categorize
    lev, spot, watch = [], [], []
    for p in picks:
        sym = p.get("symbol", "")
        score = p["fresh_score"]
        d = str(p.get("direction", p.get("signal_type", ""))).upper()
        if score >= 50 and d not in ("SHORT", "SELL"):
            spot.append(p)
        if score >= 55 and sym not in BLACKLIST and d not in ("SHORT", "SELL"):
            lev.append(p)
        elif score >= 35:
            watch.append(p)

    # 20x section
    print(f"\n--- 20x LEVERAGE CANDIDATES ({len([p for p in lev if p['fresh_score'] >= 68])}) ---")
    print(f"    [Score >= 68 required | Blackout: {now.hour in {0,6,8,17,20,21,22,23}} | UTC {now.hour}:{now.minute:02d}]")
    for p in lev:
        if p["fresh_score"] < 68:
            continue
        sym = p.get("symbol", "")
        print(f"  [{p['fresh_grade']}] {sym:14} score={p['fresh_score']:>3} | ${p['live']:.4f} | Spot:{p['spot_pnl']:+.2f}% @20x:{p['lev_pnl']:+.1f}% | TP:{p['tp_prog']:.0f}% | Risk:{p['risk_pct']:.1f}% | {get_group(sym)} | {p.get('strategy','')[:25]}")

    corr = Counter(get_group(p.get("symbol", "")) for p in lev if p["fresh_score"] >= 68)
    warns = [f"{g}({c})" for g, c in corr.items() if g != "other" and c > 1]
    if warns:
        print(f"  CORRELATION WARNING: {' '.join(warns)}")

    # Spot section
    print(f"\n--- SPOT (1x) TOP PICKS ({len(spot)}) ---")
    for p in spot[:12]:
        sym = p.get("symbol", "")
        d = str(p.get("direction", p.get("signal_type", "LONG"))).upper()
        print(f"  [{p['fresh_grade']}] {sym:14} {d:5} score={p['fresh_score']:>3} | ${p['live']:.4f} | PnL:{p['spot_pnl']:+.2f}% | TP:{p['tp_prog']:.0f}% | {get_group(sym)} | {p.get('strategy','')[:25]}")

    corr_s = Counter(get_group(p.get("symbol", "")) for p in spot)
    warns_s = [f"{g}({c})" for g, c in corr_s.items() if g != "other" and c > 1]
    if warns_s:
        print(f"  CORRELATION: {' '.join(warns_s)}")

    # Watch
    print(f"\n--- WATCH LIST ({len(watch)} picks, score 35-49) ---")

    # Market snapshot
    btc = prices.get("BTCUSDT", 0)
    eth = prices.get("ETHUSDT", 0)
    all_live = [p for p in picks if p["live"] > 0]
    winning = len([p for p in all_live if p["spot_pnl"] > 0])
    losing = len([p for p in all_live if p["spot_pnl"] < 0])
    avg_pnl = sum(p["spot_pnl"] for p in all_live) / len(all_live) if all_live else 0

    print(f"\n=== MARKET ===")
    print(f"BTC: ${btc:,.2f} | ETH: ${eth:,.2f}")
    print(f"Picks w/ live prices: {len(all_live)} | Win: {winning} | Lose: {losing} | Avg: {avg_pnl:+.2f}%")

    # 20x portfolio status
    pf_file = os.path.join(DATA_DIR, "portfolio_20x.json")
    if os.path.exists(pf_file):
        with open(pf_file, encoding="utf-8") as f:
            pf = json.load(f)
        pos = pf.get("positions", {})
        bal = pf.get("current_balance", 10000)
        unr = sum(p.get("current_pnl_usdt", 0) for p in pos.values())
        print(f"\n=== 20x PORTFOLIO ===")
        print(f"Equity: ${bal + unr:,.2f} | {len(pos)} open")
        for pid, p in pos.items():
            print(f"  {p.get('symbol',''):14} {p.get('direction',''):5} pnl={p.get('current_pnl_pct',0):+.1f}% hwm={p.get('high_water_mark_pnl',0):+.1f}%")

    # Save to history
    scan_result = {
        "timestamp": now.isoformat(),
        "btc": btc, "eth": eth,
        "total": len(picks), "lev_elig": len([p for p in lev if p["fresh_score"] >= 68]),
        "spot_elig": len(spot), "winning": winning, "losing": losing,
        "avg_pnl": round(avg_pnl, 4),
        "top": [{"sym": p.get("symbol", ""), "score": p["fresh_score"],
                 "pnl": p["spot_pnl"], "strat": p.get("strategy", "")}
                for p in picks[:10]],
    }
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, encoding="utf-8") as f:
            history = json.load(f)
    history.append(scan_result)
    history = history[-500:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
    print(f"\nScan #{len(history)} saved to local_scan_history.json")


if __name__ == "__main__":
    run_scan()
