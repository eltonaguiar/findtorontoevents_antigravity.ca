#!/usr/bin/env python3
"""
KIMI Emergency Triage — force-close losing picks, ban bad symbols,
run proper per-symbol 90-day backtest, print final verdict.
"""
import json, requests, sys
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR   = SCRIPT_DIR / "data"

CATEGORY_RISK = {
    "crypto": (-0.12, 0.25, 7),
    "meme":   (-0.18, 0.40, 5),
    "penny":  (-0.12, 0.25, 7),
    "forex":  (-0.03, 0.06, 10),
    "stock":  (-0.08, 0.15, 10),
}

# Symbols permanently banned after live validation
BANNED_SYMBOLS = {
    "RIVN",    # gap-chased, -7% on multiple algos
    "LCID",    # meme EV, zero volume
    "APT-USD", # delisted crypto
}

# Algos to immediately suppress (close all picks, flag danger)
ELIMINATE_NOW = {
    "meme-velocity-pump-detector-scout",
    "penny-stock-momentum-scout",
    "gap-and-go-breakout-scout",
    "williams-r-reversal-scout",
    "adx-trend-confirmation-scout",
    "pairs-trading-cointegration-tier1",
    "crypto-rsi-momentum-scout",
    "sector-rotation-momentum-tier1",
    "quality-minus-junk-tier1",
    "betting-against-beta-tier1",
}

YF_TO_BINANCE = {
    "BTC-USD": "BTCUSDT", "ETH-USD": "ETHUSDT", "SOL-USD": "SOLUSDT",
    "BNB-USD": "BNBUSDT", "XRP-USD": "XRPUSDT", "DOGE-USD": "DOGEUSDT",
    "AVAX-USD": "AVAXUSDT","LINK-USD": "LINKUSDT","DOT-USD": "DOTUSDT",
    "NEAR-USD": "NEARUSDT","LTC-USD": "LTCUSDT",  "INJ-USD": "INJUSDT",
    "OP-USD": "OPUSDT",   "ARB11841-USD": "ARBUSDT","SUI20947-USD": "SUIUSDT",
    "SEI-USD": "SEIUSDT", "FLOKI-USD": "FLOKIUSDT","BONK-USD": "BONKUSDT",
    "WIF-USD": "WIFUSDT", "PEPE-USD": "PEPEUSDT",  "SHIB-USD": "SHIBUSDT",
    "ADA-USD": "ADAUSDT", "ATOM-USD": "ATOMUSDT",  "APT21794-USD": "APTUSDT",
    "BCH-USD": "BCHUSDT", "TIA-USD": "TIAUSDT",
}

def get_live_price(symbol):
    bn = YF_TO_BINANCE.get(symbol)
    if bn:
        _mirrors = [
            "https://api.binance.com", "https://api1.binance.com",
            "https://api2.binance.com", "https://api3.binance.com",
            "https://data-api.binance.vision",
        ]
        for _base in _mirrors:
            try:
                r = requests.get(f"{_base}/api/v3/ticker/price",
                                 params={"symbol": bn}, timeout=5)
                return float(r.json()["price"])
            except Exception:
                continue
    try:
        import yfinance as yf
        h = yf.Ticker(symbol).history(period="1d", interval="5m")
        if not h.empty:
            return float(h["Close"].iloc[-1])
    except: pass
    return None


# ── 90-day backtest (per-symbol, RSI+MACD) ─────────────────────────────────

def backtest_symbol(symbol, period="90d"):
    try:
        import yfinance as yf
        import numpy as np
        df = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
        if df.empty or len(df) < 30:
            return None
        closes = df["Close"].values.astype(float)

        def ema(x, n):
            e = np.zeros(len(x)); e[0] = x[0]; k = 2/(n+1)
            for i in range(1, len(x)):
                e[i] = x[i]*k + e[i-1]*(1-k)
            return e

        # RSI-14
        d = np.diff(closes)
        gain = np.where(d>0,d,0); loss = np.where(d<0,-d,0)
        avg_g = np.zeros(len(gain)); avg_l = np.zeros(len(loss))
        avg_g[13] = np.mean(gain[:14]); avg_l[13] = np.mean(loss[:14])
        for i in range(14, len(gain)):
            avg_g[i] = (avg_g[i-1]*13 + gain[i]) / 14
            avg_l[i] = (avg_l[i-1]*13 + loss[i]) / 14
        rsi = 100 - 100 / (1 + avg_g/(avg_l+1e-9))
        rsi = np.concatenate([[50], rsi])   # align with closes

        # MACD 12/26/9
        e12 = ema(closes, 12); e26 = ema(closes, 26)
        macd = e12 - e26; sig = ema(macd, 9)

        trades = []
        in_trade = False; ep = 0; entry_idx = 0
        for i in range(26, len(closes)-1):
            cross_up = macd[i-1] < sig[i-1] and macd[i] >= sig[i]
            cross_dn = macd[i-1] > sig[i-1] and macd[i] <= sig[i]
            if not in_trade and rsi[i] < 42 and cross_up:
                ep = closes[i]; in_trade = True; entry_idx = i
            elif in_trade:
                hold = i - entry_idx
                pnl_pct = (closes[i] - ep) / ep * 100
                if cross_dn or rsi[i] > 68 or hold >= 14 or pnl_pct <= -8:
                    trades.append(pnl_pct)
                    in_trade = False

        if not trades:
            return None
        wins = [t for t in trades if t > 0]
        return {
            "symbol": symbol,
            "trades": len(trades),
            "wr": len(wins)/len(trades)*100,
            "avg_pnl": sum(trades)/len(trades),
            "total_pnl": sum(trades),
            "max_win": max(trades),
            "max_loss": min(trades),
        }
    except Exception as e:
        return None


def run_backtest_suite():
    print("\n" + "="*65)
    print("  90-DAY BACKTEST SUITE  (RSI+MACD, per-symbol)")
    print("="*65)

    universe = {
        "crypto": ["BTC-USD","ETH-USD","SOL-USD","XRP-USD","BNB-USD",
                   "DOGE-USD","AVAX-USD","LINK-USD","PEPE-USD","FLOKI-USD",
                   "WIF-USD","SUI20947-USD"],
        "forex":  ["EURUSD=X","GBPUSD=X","AUDUSD=X","NZDUSD=X","JPY=X","CHF=X"],
        "stock":  ["SPY","QQQ","NVDA","AAPL","META","MSFT","TSLA","AMD","COIN","MARA"],
        "penny":  ["AMC","BBBY","SNDL","CLOV","WKHS"],
        "meme":   ["DOGE-USD","SHIB-USD","PEPE-USD","FLOKI-USD","WIF-USD"],
    }

    results = []
    for cat, syms in universe.items():
        print(f"  Testing {cat} ({len(syms)} symbols)...", end=" ", flush=True)
        cat_results = []
        for sym in syms:
            r = backtest_symbol(sym)
            if r:
                r["cat"] = cat
                cat_results.append(r)
        results.extend(cat_results)
        wins = [r for r in cat_results if r["wr"] >= 55 and r["avg_pnl"] > 0]
        print(f"{len(cat_results)} tested, {len(wins)} winners")

    results.sort(key=lambda x: (x["wr"], x["avg_pnl"]), reverse=True)

    print(f"\n  {'Grade':<5} {'Symbol':<16} {'Cat':>6}  {'N':>4}  {'WR':>6}  {'Avg':>7}  {'Total':>7}  {'MaxW':>6}  {'MaxL':>7}")
    print("  " + "-"*72)
    for r in results:
        if r["wr"] >= 55 and r["avg_pnl"] > 0:   grade = "A+"
        elif r["wr"] >= 50 and r["avg_pnl"] > 0:  grade = "A"
        elif r["wr"] >= 45:                        grade = "B"
        else:                                       grade = "C"
        print(f"  [{grade:<2}]  {r['symbol']:<16} {r['cat']:>6}  {r['trades']:>4}  "
              f"{r['wr']:>5.0f}%  {r['avg_pnl']:>+6.2f}%  {r['total_pnl']:>+6.2f}%  "
              f"{r['max_win']:>+5.2f}%  {r['max_loss']:>+6.2f}%")

    grade_a = [r for r in results if r["wr"] >= 50 and r["avg_pnl"] > 0]
    print(f"\n  Grade A+ / A symbols (deploy these): {len(grade_a)}")
    for r in grade_a:
        print(f"    -> {r['symbol']:<16}  WR:{r['wr']:.0f}%  avg:{r['avg_pnl']:>+.2f}%  [{r['cat']}]")
    return results


# ── Force-close losing picks & apply bans ──────────────────────────────────

def apply_triage():
    print("\n" + "="*65)
    print("  TRIAGE: Force-close losers, ban bad symbols")
    print("="*65)

    comp_path = DATA_DIR / "live_competition.json"
    comp = json.load(open(comp_path, encoding="utf-8"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    forced_exits = 0
    banned_exits = 0

    for algo in comp["algorithms"]:
        algo_id = algo.get("id", "")
        surviving = []
        closed = algo.setdefault("closedPicks", [])

        for p in algo.get("activePicks", []):
            sym = p.get("symbol", "")
            ep  = float(p.get("entryPrice") or 0)
            cp  = get_live_price(sym) or ep
            pnl_pct = ((cp - ep) / ep * 100) if ep > 0 else 0

            reason = None
            # Ban check
            base_sym = sym.replace("-USD","").replace("=X","").upper()
            if base_sym in BANNED_SYMBOLS or sym.replace("-USD","") in BANNED_SYMBOLS:
                reason = f"BANNED_SYMBOL ({base_sym} flagged after live validation)"
                banned_exits += 1
            # Algo elimination check
            elif algo_id in ELIMINATE_NOW:
                reason = f"ALGO_ELIMINATED (live loss: {pnl_pct:+.2f}%)"
                forced_exits += 1
            # Hard stop: any pick down more than 8% immediately
            elif pnl_pct <= -8.0:
                reason = f"EMERGENCY_STOP ({pnl_pct:+.2f}% exceeds -8% hard floor)"
                forced_exits += 1

            if reason:
                closed.append({
                    **p,
                    "exitPrice": round(cp, 6),
                    "exitDate": now,
                    "exitReason": reason,
                    "pnlPct": round(pnl_pct, 4),
                    "status": "LOSS" if pnl_pct < 0 else "WIN",
                })
                # Update algo cash
                alloc = float(p.get("allocation", 2000))
                algo["cash"] = round(float(algo.get("cash", 10000)) + alloc * (1 + pnl_pct/100), 2)
                print(f"  [{reason[:25]:<25}] {sym:<18} {pnl_pct:>+7.2f}%  {algo['name'][:22]}")
            else:
                surviving.append(p)

        algo["activePicks"] = surviving

        # Recompute totalReturn
        start = 10000.0
        total_val = float(algo.get("cash", start))
        for p in algo.get("activePicks", []):
            ep = float(p.get("entryPrice") or 0)
            cp = get_live_price(p.get("symbol","")) or ep
            alloc = float(p.get("allocation", 2000))
            if ep > 0:
                total_val += alloc * (cp / ep)
        algo["currentValue"] = round(total_val, 2)
        algo["totalReturn"]  = round((total_val - start) / start * 100, 4)

    print(f"\n  Banned exits: {banned_exits} | Algo-eliminated: {forced_exits}")
    comp["competition"]["lastUpdated"] = now

    with open(comp_path, "w", encoding="utf-8") as f:
        json.dump(comp, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {comp_path}")
    return forced_exits + banned_exits


# ── Final leaderboard after triage ─────────────────────────────────────────

def final_leaderboard():
    print("\n" + "="*65)
    print("  POST-TRIAGE LEADERBOARD")
    print("="*65)
    comp = json.load(open(DATA_DIR / "live_competition.json", encoding="utf-8"))
    algos = sorted(comp["algorithms"],
                   key=lambda a: float(a.get("totalReturn", 0)), reverse=True)
    print(f"\n  {'Algo':<32} {'Return':>8}  {'Cash':>10}  {'Active':>7}  {'Closed':>7}  Cat")
    print("  " + "-"*75)
    for a in algos:
        ret  = float(a.get("totalReturn", 0))
        cash = float(a.get("cash", 10000))
        act  = len(a.get("activePicks", []))
        cl   = len(a.get("closedPicks", []))
        flag = " **" if ret > 0 else ("  !" if ret < -1 else "   ")
        print(f"  {flag}{a['name'][:32]:<32} {ret:>+8.4f}%  ${cash:>9,.2f}  {act:>7}  {cl:>7}  {a.get('category','?')}")

    # Category summary
    cat_rets = {}
    for a in algos:
        c = a.get("category", "?")
        cat_rets.setdefault(c, []).append(float(a.get("totalReturn", 0)))
    print("\n  CATEGORY SUMMARY:")
    for cat, rets in sorted(cat_rets.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True):
        avg = sum(rets)/len(rets)
        best = max(rets)
        print(f"    {cat:<8}  avg:{avg:>+.3f}%  best:{best:>+.3f}%  ({len(rets)} algos)")


# ── MAIN ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "#"*65)
    print("  KIMI EMERGENCY TRIAGE + BACKTEST")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("#"*65)

    # 1. Force-close losers
    n = apply_triage()
    print(f"\n  Total positions force-closed: {n}")

    # 2. 90-day backtest
    bt_results = run_backtest_suite()

    # 3. Post-triage leaderboard
    final_leaderboard()

    print("\n" + "#"*65)
    print("  TRIAGE COMPLETE")
    print("#"*65 + "\n")
