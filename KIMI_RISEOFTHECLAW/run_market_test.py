#!/usr/bin/env python3
"""
KIMI v11 — Real-Time Market Test & Algorithm Performance Audit
Fetches live prices, validates all open picks, shows leaderboard,
runs elimination logic, and identifies best-performing algorithms.
"""
import json
import sqlite3
import requests
import warnings
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

BINANCE_BASE = "https://api.binance.com"
BINANCE_FUTURES = "https://fapi.binance.com"

YF_TO_BINANCE = {
    "BTC-USD":  "BTCUSDT",  "ETH-USD":  "ETHUSDT",  "SOL-USD":  "SOLUSDT",
    "BNB-USD":  "BNBUSDT",  "XRP-USD":  "XRPUSDT",  "DOGE-USD": "DOGEUSDT",
    "AVAX-USD": "AVAXUSDT", "LINK-USD": "LINKUSDT",  "DOT-USD":  "DOTUSDT",
    "NEAR-USD": "NEARUSDT", "LTC-USD":  "LTCUSDT",   "INJ-USD":  "INJUSDT",
    "OP-USD":   "OPUSDT",   "ARB11841-USD": "ARBUSDT", "SUI20947-USD": "SUIUSDT",
    "SEI-USD":  "SEIUSDT",  "FLOKI-USD":"FLOKIUSDT", "BONK-USD": "BONKUSDT",
    "WIF-USD":  "WIFUSDT",  "PEPE-USD": "PEPEUSDT",  "SHIB-USD": "SHIBUSDT",
    "ADA-USD":  "ADAUSDT",  "ATOM-USD": "ATOMUSDT",  "APT21794-USD": "APTUSDT",
    "BCH-USD":  "BCHUSDT",  "TIA-USD":  "TIAUSDT",
}

CATEGORY_RISK = {
    "crypto": (-0.12, 0.25, 7),
    "meme":   (-0.18, 0.40, 5),
    "penny":  (-0.12, 0.25, 7),
    "forex":  (-0.03, 0.06, 10),
    "stock":  (-0.08, 0.15, 10),
}

# ── helpers ────────────────────────────────────────────────────────────────

def binance_price(symbol):
    bn = YF_TO_BINANCE.get(symbol)
    if not bn:
        return None
    try:
        r = requests.get(f"{BINANCE_BASE}/api/v3/ticker/price",
                         params={"symbol": bn}, timeout=5)
        return float(r.json()["price"])
    except:
        return None

def binance_24h(symbol):
    """Returns (price, change_pct, volume_usd_M)."""
    bn = YF_TO_BINANCE.get(symbol)
    if not bn:
        return None, 0, 0
    try:
        r = requests.get(f"{BINANCE_BASE}/api/v3/ticker/24hr",
                         params={"symbol": bn}, timeout=5)
        d = r.json()
        return float(d["lastPrice"]), float(d["priceChangePercent"]), float(d["quoteVolume"]) / 1e6
    except:
        return None, 0, 0

def yf_price(symbol):
    try:
        import yfinance as yf
        tk = yf.Ticker(symbol)
        h = tk.history(period="1d", interval="5m")
        if not h.empty:
            return float(h["Close"].iloc[-1])
    except:
        pass
    return None

def get_price(symbol):
    p = binance_price(symbol)
    if p:
        return p
    return yf_price(symbol)


# ── SECTION 1: Live market snapshot ────────────────────────────────────────

def section_market_snapshot():
    print("\n" + "="*70)
    print("  LIVE CRYPTO MARKET  (Binance, real-time)")
    print("="*70)

    crypto_syms = [
        ("BTC-USD","Bitcoin"), ("ETH-USD","Ethereum"), ("SOL-USD","Solana"),
        ("XRP-USD","XRP"),     ("BNB-USD","BNB"),       ("DOGE-USD","Dogecoin"),
        ("AVAX-USD","Avalanche"),("LINK-USD","Chainlink"),("PEPE-USD","Pepe"),
        ("FLOKI-USD","Floki"), ("WIF-USD","WIF"),        ("SHIB-USD","Shiba"),
    ]
    print(f"  {'Pair':<10} {'Name':<14} {'Price':>14}  {'24h':>8}  {'Vol(M)':>8}")
    print("  " + "-"*60)
    for sym, name in crypto_syms:
        p, chg, vol = binance_24h(sym)
        if p:
            arrow = "+" if chg > 0 else ""
            print(f"  {sym.replace('-USD',''):<10} {name:<14} ${p:>13,.4f}  {arrow}{chg:.2f}%  ${vol:>6,.0f}M")

    print()
    print("  FOREX  (yfinance)")
    print("  " + "-"*45)
    try:
        import yfinance as yf
        for sym in ["EURUSD=X","GBPUSD=X","AUDUSD=X","NZDUSD=X","JPY=X","CHF=X"]:
            h = yf.Ticker(sym).history(period="2d", interval="1h")
            if not h.empty:
                cp = float(h["Close"].iloc[-1])
                prev = float(h["Close"].iloc[-24]) if len(h) >= 24 else float(h["Close"].iloc[0])
                chg = (cp - prev) / prev * 100
                print(f"  {sym:<12} {cp:>10.5f}  {chg:>+8.3f}%  (24h)")
    except Exception as e:
        print(f"  Forex error: {e}")


# ── SECTION 2: Active pick P&L audit ───────────────────────────────────────

def section_pick_audit():
    print("\n" + "="*70)
    print("  OPEN PICK P&L AUDIT  (live prices vs entry)")
    print("="*70)

    comp = json.load(open(DATA_DIR / "live_competition.json", encoding="utf-8"))
    algos = comp.get("algorithms", [])

    rows = []
    for a in algos:
        cat = a.get("category", "stock")
        sl_def, tp_def, mh_def = CATEGORY_RISK.get(cat, CATEGORY_RISK["stock"])
        for p in a.get("activePicks", []):
            sym = p.get("symbol", "")
            ep  = float(p.get("entryPrice") or 0)
            if ep <= 0:
                continue
            tp  = float(p.get("targetPrice") or ep * (1 + tp_def))
            sl  = float(p.get("stopPrice")   or ep * (1 + sl_def))
            cp  = get_price(sym) or ep
            pnl = (cp - ep) / ep * 100
            tp_dist = (tp - ep) / ep * 100
            sl_dist = (sl - ep) / ep * 100
            days_held = (datetime.now(timezone.utc) -
                         datetime.fromisoformat(p.get("entryDate", "2026-02-17T00:00:00+00:00").replace("Z","+00:00"))
                        ).days
            status = "OPEN"
            if cp >= tp:
                status = "HIT_TP"
            elif cp <= sl:
                status = "HIT_SL"
            rows.append({
                "algo": a["name"][:22],
                "cat": cat, "sym": sym,
                "ep": ep, "cp": cp, "tp": tp, "sl": sl,
                "pnl": pnl, "tp_dist": tp_dist, "sl_dist": sl_dist,
                "days": days_held, "status": status,
                "tier": a.get("tier", "SCOUT"),
            })

    rows.sort(key=lambda x: x["pnl"], reverse=True)
    wins  = [r for r in rows if r["status"] == "HIT_TP"]
    losses= [r for r in rows if r["status"] == "HIT_SL"]
    opens = [r for r in rows if r["status"] == "OPEN"]

    print(f"\n  Total open: {len(rows)}  |  TP Hit: {len(wins)}  |  SL Hit: {len(losses)}  |  Open: {len(opens)}")

    if wins:
        print(f"\n  --- TP HITS (WINNERS) ---")
        for r in wins:
            print(f"  [WIN] {r['sym']:<18} {r['pnl']:>+7.2f}%  [{r['cat']}]  {r['algo']}")

    if losses:
        print(f"\n  --- SL HITS (LOSERS) ---")
        for r in losses:
            print(f"  [LOSS] {r['sym']:<17} {r['pnl']:>+7.2f}%  [{r['cat']}]  {r['algo']}")

    print(f"\n  {'Status':<6} {'P&L':>7}  {'Symbol':<18}  {'Cat':>6}  {'TP':>6}  {'SL':>6}  {'Days':>4}  Algo")
    print("  " + "-"*75)
    for r in rows[:30]:
        flag = "**" if r["status"] != "OPEN" else "  "
        print(f"  {flag}{r['pnl']:>+7.2f}%  {r['sym']:<18}  {r['cat']:>6}  "
              f"{r['tp_dist']:>+5.1f}%  {r['sl_dist']:>+5.1f}%  {r['days']:>3}d  {r['algo']}")

    return rows


# ── SECTION 3: Algorithm leaderboard ───────────────────────────────────────

def section_leaderboard(pick_rows):
    print("\n" + "="*70)
    print("  ALGORITHM LEADERBOARD  (live competition)")
    print("="*70)

    comp = json.load(open(DATA_DIR / "live_competition.json", encoding="utf-8"))
    algos = comp.get("algorithms", [])

    # Build per-algo stats
    algo_pnl = {}
    for r in pick_rows:
        name = r["algo"]
        if name not in algo_pnl:
            algo_pnl[name] = []
        algo_pnl[name].append(r["pnl"])

    rows = []
    for a in algos:
        name = a["name"][:22]
        pnls = algo_pnl.get(name, [])
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0
        closed = len(a.get("closedPicks", []))
        active = len(a.get("activePicks", []))
        total_ret = float(a.get("totalReturn", 0))
        wr = a.get("winRate")
        wr_str = f"{float(wr)*100:.0f}%" if wr else "—"
        rows.append({
            "name": name, "cat": a.get("category","?"),
            "tier": a.get("tier","SCOUT"),
            "total_ret": total_ret, "avg_live_pnl": avg_pnl,
            "closed": closed, "active": active, "wr": wr_str,
        })

    rows.sort(key=lambda x: (x["avg_live_pnl"], x["total_ret"]), reverse=True)

    print(f"\n  {'Tier':<8} {'Algorithm':<24} {'Live P&L':>9} {'Tot Ret':>8} {'WR':>5} {'C':>4} {'A':>4}  Cat")
    print("  " + "-"*72)
    for r in rows:
        live_pnl_str = f"{r['avg_live_pnl']:>+.2f}%" if r["avg_live_pnl"] != 0 else "   —"
        print(f"  {r['tier']:<8} {r['name']:<24} {live_pnl_str:>9} "
              f"{r['total_ret']:>+7.2f}% {r['wr']:>5} {r['closed']:>4} {r['active']:>4}  {r['cat']}")

    # Danger zone
    danger = [r for r in rows if r["avg_live_pnl"] < -0.5 or r["total_ret"] < -0.5]
    if danger:
        print(f"\n  !! DANGER ZONE ({len(danger)} algos losing > 0.5%) !!")
        for r in danger:
            print(f"     {r['name']:<24}  live:{r['avg_live_pnl']:>+.2f}%  total:{r['total_ret']:>+.2f}%  [{r['cat']}]")

    return rows


# ── SECTION 4: Quick backtest (90 days yfinance OHLC) ──────────────────────

def section_quick_backtest():
    print("\n" + "="*70)
    print("  90-DAY BACKTEST  (RSI + MACD strategy, key symbols)")
    print("="*70)

    try:
        import yfinance as yf
        import numpy as np

        test_symbols = {
            "crypto": ["BTC-USD","ETH-USD","SOL-USD","XRP-USD","BNB-USD","DOGE-USD"],
            "forex":  ["EURUSD=X","GBPUSD=X","AUDUSD=X","NZDUSD=X"],
            "meme":   ["DOGE-USD","SHIB11052-USD"],  # Shiba via alternate
            "stock":  ["SPY","QQQ","NVDA","AAPL","META"],
        }

        results = []
        for cat, syms in test_symbols.items():
            for sym in syms:
                try:
                    df = yf.download(sym, period="90d", interval="1d",
                                     progress=False, auto_adjust=True)
                    if df.empty or len(df) < 30:
                        continue

                    closes = df["Close"].squeeze().values.astype(float)

                    # RSI-14
                    delta = np.diff(closes)
                    gain = np.where(delta > 0, delta, 0)
                    loss = np.where(delta < 0, -delta, 0)
                    avg_g = np.convolve(gain, np.ones(14)/14, mode="valid")
                    avg_l = np.convolve(loss, np.ones(14)/14, mode="valid")
                    rs = avg_g / (avg_l + 1e-9)
                    rsi = 100 - 100 / (1 + rs)

                    # MACD (12,26,9)
                    def ema(x, n):
                        e = np.zeros_like(x)
                        e[0] = x[0]
                        k = 2/(n+1)
                        for i in range(1, len(x)):
                            e[i] = x[i]*k + e[i-1]*(1-k)
                        return e
                    ema12 = ema(closes, 12)
                    ema26 = ema(closes, 26)
                    macd_line = ema12 - ema26
                    signal_line = ema(macd_line, 9)

                    # Simple strategy: BUY when RSI < 35 + MACD crossover up
                    min_len = min(len(rsi), len(macd_line)-1)
                    trades = []
                    in_trade = False
                    entry_price = 0
                    for i in range(1, min_len - 5):
                        idx = len(closes) - min_len + i
                        r = rsi[i]
                        macd_cross_up = (macd_line[idx-1] < signal_line[idx-1] and
                                         macd_line[idx] > signal_line[idx])
                        macd_cross_dn = (macd_line[idx-1] > signal_line[idx-1] and
                                         macd_line[idx] < signal_line[idx])

                        if not in_trade and r < 40 and macd_cross_up:
                            entry_price = closes[idx]
                            in_trade = True
                        elif in_trade and (macd_cross_dn or r > 65):
                            pnl = (closes[idx] - entry_price) / entry_price * 100
                            trades.append(pnl)
                            in_trade = False

                    if not trades:
                        continue

                    wins_t = [t for t in trades if t > 0]
                    wr = len(wins_t) / len(trades) * 100
                    avg_pnl = sum(trades) / len(trades)
                    total_pnl = sum(trades)

                    results.append({
                        "sym": sym, "cat": cat,
                        "trades": len(trades), "wr": wr,
                        "avg": avg_pnl, "total": total_pnl,
                    })
                except Exception as e:
                    continue

        results.sort(key=lambda x: x["total"], reverse=True)
        print(f"\n  {'Symbol':<16} {'Cat':>6}  {'Trades':>7}  {'WR':>6}  {'Avg P&L':>8}  {'Total':>8}")
        print("  " + "-"*60)
        for r in results:
            grade = "A" if r["wr"] >= 55 and r["avg"] > 0 else ("B" if r["wr"] >= 45 else "C")
            print(f"  [{grade}] {r['sym']:<14} {r['cat']:>6}  {r['trades']:>7}  "
                  f"{r['wr']:>5.0f}%  {r['avg']:>+7.2f}%  {r['total']:>+7.2f}%")

        winners = [r for r in results if r["wr"] >= 55 and r["avg"] > 0]
        print(f"\n  Backtest winners (WR >= 55%, avg P&L > 0): {len(winners)}/{len(results)}")
        for r in winners:
            print(f"    -> {r['sym']:<16} WR:{r['wr']:.0f}%  avg:{r['avg']:+.2f}%  [{r['cat']}]")

    except Exception as e:
        print(f"  Backtest error: {e}")
        import traceback; traceback.print_exc()


# ── SECTION 5: Elimination recommendation ──────────────────────────────────

def section_elimination(leaderboard_rows):
    print("\n" + "="*70)
    print("  ELIMINATION VERDICT")
    print("="*70)

    to_eliminate = []
    to_watch     = []
    strong       = []

    for r in leaderboard_rows:
        score = r["avg_live_pnl"] * 0.6 + r["total_ret"] * 0.4
        if score < -0.4 and r["active"] > 0:
            to_eliminate.append(r)
        elif score < 0 and r["active"] > 0:
            to_watch.append(r)
        elif score >= 0 and r["active"] > 0:
            strong.append(r)

    print(f"\n  STRONG (keep & promote)  — {len(strong)} algos")
    for r in strong:
        print(f"    [KEEP] {r['name']:<24}  live:{r['avg_live_pnl']:>+.2f}%  [{r['cat']}]")

    print(f"\n  WATCH LIST (marginal)    — {len(to_watch)} algos")
    for r in to_watch:
        print(f"    [WATCH] {r['name']:<23}  live:{r['avg_live_pnl']:>+.2f}%  [{r['cat']}]")

    print(f"\n  ELIMINATE (losing picks) — {len(to_eliminate)} algos")
    for r in to_eliminate:
        print(f"    [ELIM] {r['name']:<24}  live:{r['avg_live_pnl']:>+.2f}%  total:{r['total_ret']:>+.2f}%  [{r['cat']}]")

    # Best asset class
    cat_pnl = {}
    for r in leaderboard_rows:
        cat = r["cat"]
        cat_pnl.setdefault(cat, []).append(r["avg_live_pnl"])
    print(f"\n  BEST ASSET CLASS (avg live P&L):")
    cat_ranked = sorted(cat_pnl.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True)
    for cat, pnls in cat_ranked:
        avg = sum(pnls)/len(pnls)
        print(f"    {cat:<10}  avg live pnl: {avg:>+.3f}%  ({len(pnls)} algos)")


# ── MAIN ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "#"*70)
    print("  KIMI RISE OF THE CLAW — FULL MARKET AUDIT")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("#"*70)

    section_market_snapshot()
    pick_rows = section_pick_audit()
    lb_rows   = section_leaderboard(pick_rows)
    section_quick_backtest()
    section_elimination(lb_rows)

    print("\n" + "#"*70)
    print("  AUDIT COMPLETE")
    print("#"*70 + "\n")
