#!/usr/bin/env python3
"""Recommended Portfolio Tracker — tracks basket-generated portfolio performance.
Reads ONLY from data/recommended_portfolio.json. Auto-tunes via conviction/regime analysis."""
import json, os, sys, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio_recommended.json")
RECOMMENDED_PICKS_FILE = os.path.join(DATA_DIR, "recommended_portfolio.json")
INSIGHTS_FILE = os.path.join(DATA_DIR, "recommended_portfolio_insights.json")

STARTING_BALANCE = 10000
MAX_POSITIONS = 5
OPTIMAL_HOLD_HOURS = 72
MAX_HOLD_HOURS = 168
TRAILING_STOP_ACTIVATION = 0.02
TRAILING_STOP_DISTANCE = 0.015
BASE_POSITION_SIZE = 200
AUTOTUNE_INTERVAL = 10
AUTOTUNE_WARN_THRESHOLD = 20

def normalize_symbol(sym):
    sym = sym.upper().replace("-USD", "USDT").replace("/", "")
    if not sym.endswith("USDT") and "USD" in sym and "=" not in sym:
        sym += "T"
    return sym

def fetch_prices():
    """Fetch live prices with 3+ API failover chain."""
    apis = [
        ("https://api.binance.com/api/v3/ticker/price", "binance"),
        ("https://api1.binance.com/api/v3/ticker/price", "binance_mirror"),
        ("https://api2.binance.com/api/v3/ticker/price", "binance_mirror2"),
        ("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,dogecoin,ripple,cardano,avalanche-2,chainlink,polkadot,near,shiba-inu,filecoin,bnb,fetch-ai,render-token&vs_currencies=usd", "coingecko"),
    ]
    for url, source in apis:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=10).read())
            if source.startswith("binance"):
                return {t["symbol"]: float(t["price"]) for t in data}
            cg_map = {"bitcoin": "BTCUSDT", "ethereum": "ETHUSDT", "solana": "SOLUSDT",
                      "dogecoin": "DOGEUSDT", "ripple": "XRPUSDT", "cardano": "ADAUSDT",
                      "avalanche-2": "AVAXUSDT", "chainlink": "LINKUSDT", "polkadot": "DOTUSDT",
                      "near": "NEARUSDT", "shiba-inu": "SHIBUSDT", "filecoin": "FILUSDT",
                      "bnb": "BNBUSDT", "fetch-ai": "FETUSDT", "render-token": "RENDERUSDT"}
            return {sym: float(data[cid]["usd"]) for cid, sym in cg_map.items()
                    if cid in data and "usd" in data[cid]}
        except Exception:
            continue
    return {}

def fetch_btc_4h_regime():
    for base in ["https://api1.binance.com", "https://api2.binance.com",
                  "https://api3.binance.com", "https://api.binance.com"]:
        try:
            url = f"{base}/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=5"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            klines = json.loads(urllib.request.urlopen(req, timeout=10).read())
            if klines and len(klines) >= 4:
                pct = (float(klines[-1][4]) - float(klines[0][1])) / float(klines[0][1]) * 100
                regime = "bearish" if pct < -1 else ("bullish" if pct > 1 else "neutral")
                return regime, round(pct, 2)
        except Exception:
            continue
    return "neutral", 0.0

def _default_stats():
    return {
        "total_trades": 0, "wins": 0, "losses": 0, "tp_hits": 0, "sl_hits": 0,
        "trailing_stops": 0, "total_pnl_usdt": 0, "best_trade_pnl": 0, "worst_trade_pnl": 0,
        "conviction_stats": {k: {"trades": 0, "wins": 0, "pnl": 0} for k in ("HIGH", "MEDIUM", "LOW")},
        "regime_stats": {k: {"longs": 0, "long_wins": 0, "shorts": 0, "short_wins": 0}
                         for k in ("bullish", "bearish", "neutral")},
    }

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            pf = json.load(f)
        ds = _default_stats()
        for k, v in ds.items():
            pf.setdefault("stats", {}).setdefault(k, v)
        return pf
    return {"created_at": datetime.now(timezone.utc).isoformat(),
            "starting_balance": STARTING_BALANCE, "current_balance": STARTING_BALANCE,
            "tracker_type": "recommended_portfolio_forward_test",
            "positions": {}, "closed_positions": [], "stats": _default_stats()}

def save_portfolio(pf):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(pf, f, indent=2, default=str)

def load_recommended_picks():
    if not os.path.exists(RECOMMENDED_PICKS_FILE):
        return []
    try:
        with open(RECOMMENDED_PICKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return data.get("positions", data.get("basket", []))
    except Exception:
        return []

def classify_conviction(pick):
    score = float(pick.get("elite_score", pick.get("score", pick.get("confidence", 0))) or 0)
    return "HIGH" if score >= 75 else ("MEDIUM" if score >= 55 else "LOW")

def _is_long(d):
    return d in ("LONG", "BUY")

def _pnl(direction, entry, current):
    return (current - entry) / entry if _is_long(direction) else (entry - current) / entry

def compute_insights(closed):
    """Compute conviction/regime/hold-time insights from closed trades."""
    if not closed:
        return {}
    conv_pnls = {"HIGH": [], "MEDIUM": [], "LOW": []}
    regime_pnls = {r: {"LONG": [], "SHORT": []} for r in ("bullish", "bearish", "neutral")}
    w_hours, l_hours = [], []
    for pos in closed:
        pnl = pos.get("pnl_usdt", 0) or 0
        conv = pos.get("conviction", "MEDIUM")
        conv_pnls.setdefault(conv, []).append(pnl)
        r = pos.get("regime_at_entry", "neutral").lower()
        if r not in regime_pnls:
            r = "neutral"
        d = "LONG" if _is_long(pos.get("direction", "LONG").upper()) else "SHORT"
        regime_pnls[r][d].append(pnl)
        h = pos.get("hours_held", 0) or 0
        if h > 0:
            (w_hours if pnl > 0 else l_hours).append(h)

    def _wr(t): return round(sum(1 for x in t if x > 0) / len(t) * 100, 1) if t else 0.0
    def _avg(t): return round(sum(t) / len(t), 1) if t else 0.0

    insights = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "total_closed": len(closed),
        "conviction_wr": {k: {"trades": len(v), "wr": _wr(v), "avg_pnl": _avg(v)}
                          for k, v in conv_pnls.items()},
        "regime_wr": {r: {"long_trades": len(d["LONG"]), "long_wr": _wr(d["LONG"]),
                          "short_trades": len(d["SHORT"]), "short_wr": _wr(d["SHORT"])}
                      for r, d in regime_pnls.items()},
        "hold_time": {"avg_winner_hours": _avg(w_hours), "avg_loser_hours": _avg(l_hours)},
        "warnings": [],
    }
    # Auto-tune warnings (after 20+ closed)
    if len(closed) >= AUTOTUNE_WARN_THRESHOLD:
        h_wr = insights["conviction_wr"]["HIGH"]["wr"]
        m_wr = insights["conviction_wr"]["MEDIUM"]["wr"]
        if h_wr < 50 and insights["conviction_wr"]["HIGH"]["trades"] >= 5:
            insights["warnings"].append(f"WARNING: HIGH conviction WR only {h_wr}% — tighten criteria")
        if m_wr > h_wr and insights["conviction_wr"]["MEDIUM"]["trades"] >= 5:
            insights["warnings"].append(f"SCORING INVERSION DETECTED: MEDIUM WR ({m_wr}%) > HIGH WR ({h_wr}%)")
        all_l = sum((d["LONG"] for d in regime_pnls.values()), [])
        all_s = sum((d["SHORT"] for d in regime_pnls.values()), [])
        if _wr(all_s) > _wr(all_l) + 10 and len(all_s) >= 3:
            insights["warnings"].append(f"REGIME FAVORS SHORTS — SHORT WR {_wr(all_s)}% vs LONG WR {_wr(all_l)}%")
    for w in insights["warnings"]:
        print(f"  {w}")
    return insights

def save_insights(ins):
    with open(INSIGHTS_FILE, "w", encoding="utf-8") as f:
        json.dump(ins, f, indent=2, default=str)

def _close_pos(pos, reason, current, pnl_pct, pnl_usdt, now, hours=None):
    pos.update(close_reason=reason, close_price=current, close_time=now.isoformat(),
               pnl_pct=pnl_pct * 100, pnl_usdt=pnl_usdt)
    if hours is not None:
        pos["hours_held"] = round(hours, 1)

def run_check():
    """Main portfolio check cycle."""
    pf = load_portfolio()
    prices = fetch_prices()
    if not prices:
        print("[REC TRACKER] Failed to fetch prices"); return pf
    now = datetime.now(timezone.utc)
    regime, regime_pct = fetch_btc_4h_regime()
    print(f"[REC TRACKER] Regime: {regime} ({regime_pct:+.2f}%) | "
          f"Open: {len(pf['positions'])} | Closed: {len(pf['closed_positions'])}")

    to_close = []
    for pid, pos in list(pf["positions"].items()):
        sym, entry, d = normalize_symbol(pos["symbol"]), pos["entry_price"], pos["direction"]
        cur = prices.get(sym, 0)
        if cur <= 0:
            continue
        if entry > 0 and abs(cur - entry) / entry > 0.50:
            cur = entry * (1.20 if cur > entry else 0.80)
        pp = _pnl(d, entry, cur)
        sz = pos.get("position_size", BASE_POSITION_SIZE)
        if abs(pp) > 0.50:
            pp = 0.50 if pp > 0 else -0.50
        pu = sz * pp
        # TP
        tp = pos.get("take_profit", 0)
        if tp > 0 and ((_is_long(d) and cur >= tp) or (not _is_long(d) and cur <= tp)):
            _close_pos(pos, "TP_HIT", cur, pp, pu, now)
            to_close.append(pid); pf["stats"]["tp_hits"] += 1; pf["stats"]["wins"] += 1
            print(f"  TP HIT: {pos['symbol']} {d} pnl={pu:+.2f}"); continue
        # SL
        sl = pos.get("stop_loss", 0)
        if sl > 0 and ((_is_long(d) and cur <= sl) or (not _is_long(d) and cur >= sl)):
            _close_pos(pos, "SL_HIT", cur, pp, pu, now)
            to_close.append(pid); pf["stats"]["sl_hits"] += 1; pf["stats"]["losses"] += 1
            print(f"  SL HIT: {pos['symbol']} {d} pnl={pu:+.2f}"); continue
        # Trailing stop
        hwm_key = "hwm_price"
        if _is_long(d):
            pos[hwm_key] = max(pos.get(hwm_key, 0), cur)
        else:
            pos[hwm_key] = min(pos.get(hwm_key, float("inf")), cur)
        if pp >= TRAILING_STOP_ACTIVATION:
            hwm = pos[hwm_key]
            if _is_long(d):
                pos["trailing_stop"] = max(pos.get("trailing_stop", 0), hwm * (1 - TRAILING_STOP_DISTANCE))
            else:
                pos["trailing_stop"] = min(pos.get("trailing_stop", float("inf")), hwm * (1 + TRAILING_STOP_DISTANCE))
        tr = pos.get("trailing_stop", 0)
        if tr > 0 and ((_is_long(d) and cur <= tr) or (not _is_long(d) and tr < float("inf") and cur >= tr)):
            tpp = _pnl(d, entry, cur)
            _close_pos(pos, "TRAILING_STOP", cur, tpp, sz * tpp, now)
            to_close.append(pid); pf["stats"]["trailing_stops"] += 1
            pf["stats"]["wins" if tpp > 0 else "losses"] += 1
            print(f"  TRAILING STOP: {pos['symbol']} {d} pnl=${pos['pnl_usdt']:+.2f}"); continue
        # Time exit
        try:
            hrs = (now - datetime.fromisoformat(pos.get("opened_at", now.isoformat()))).total_seconds() / 3600
        except Exception:
            hrs = 0
        if (hrs > OPTIMAL_HOLD_HOURS and pp > 0) or hrs > MAX_HOLD_HOURS:
            reason = "TIME_EXIT_PROFIT" if pp > 0 and hrs <= MAX_HOLD_HOURS else "TIME_EXIT_MAX_HOLD"
            _close_pos(pos, reason, cur, pp, pu, now, hrs)
            to_close.append(pid); pf["stats"]["wins" if pp > 0 else "losses"] += 1
            print(f"  TIME EXIT: {pos['symbol']} {d} {hrs:.0f}h pnl={pu:+.2f}"); continue
        pos.update(current_pnl_pct=pp*100, current_pnl_usdt=pu, current_price=cur, last_checked=now.isoformat())

    # Close positions and update stats
    closed_n = 0
    for pid in to_close:
        pos = pf["positions"].pop(pid)
        pf["closed_positions"].append(pos)
        pf["stats"]["total_pnl_usdt"] += pos["pnl_usdt"]
        pf["current_balance"] += pos["pnl_usdt"]
        pf["stats"]["total_trades"] += 1
        pf["stats"]["best_trade_pnl"] = max(pf["stats"]["best_trade_pnl"], pos["pnl_usdt"])
        pf["stats"]["worst_trade_pnl"] = min(pf["stats"]["worst_trade_pnl"], pos["pnl_usdt"])
        conv = pos.get("conviction", "MEDIUM")
        cs = pf["stats"]["conviction_stats"].setdefault(conv, {"trades": 0, "wins": 0, "pnl": 0})
        cs["trades"] += 1
        if pos["pnl_usdt"] > 0: cs["wins"] += 1
        cs["pnl"] = round(cs["pnl"] + pos["pnl_usdt"], 2)
        r = pos.get("regime_at_entry", "neutral").lower()
        if r not in pf["stats"]["regime_stats"]: r = "neutral"
        rs = pf["stats"]["regime_stats"][r]
        dk = "longs" if _is_long(pos.get("direction", "LONG").upper()) else "shorts"
        wk = "long_wins" if dk == "longs" else "short_wins"
        rs[dk] = rs.get(dk, 0) + 1
        if pos["pnl_usdt"] > 0: rs[wk] = rs.get(wk, 0) + 1
        closed_n += 1

    # Add new positions from recommended portfolio
    picks = load_recommended_picks()
    added = 0
    for pick in picks:
        if not isinstance(pick, dict) or len(pf["positions"]) >= MAX_POSITIONS:
            break
        sym = pick.get("symbol", "")
        if not sym:
            continue
        d = str(pick.get("direction", "LONG")).upper()
        ep = float(pick.get("entry_price", 0) or 0)
        if ep <= 0:
            ep = prices.get(normalize_symbol(sym), 0)
        if ep <= 0:
            continue
        pk = f"{sym}_{d}"
        if pk in pf["positions"]:
            continue
        if any(normalize_symbol(p.get("symbol", "")) == normalize_symbol(sym) for p in pf["positions"].values()):
            continue
        tp = float(pick.get("take_profit", pick.get("target_price", 0)) or 0)
        sl = float(pick.get("stop_loss", 0) or 0)
        if tp <= 0:
            tp = ep * (1.04 if _is_long(d) else 0.96)
        if sl <= 0:
            sl = ep * (0.97 if _is_long(d) else 1.03)
        conv = pick.get("conviction", classify_conviction(pick))
        pf["positions"][pk] = {
            "symbol": sym, "direction": d, "entry_price": ep, "take_profit": tp, "stop_loss": sl,
            "position_size": float(pick.get("size_usd", BASE_POSITION_SIZE) or BASE_POSITION_SIZE),
            "conviction": conv, "regime_at_entry": regime, "regime_pct": regime_pct,
            "strategy": pick.get("strategy", pick.get("reason", "basket")),
            "score": float(pick.get("elite_score", pick.get("score", 0)) or 0),
            "opened_at": now.isoformat(), "group": pick.get("group", "unknown"),
        }
        added += 1
        print(f"  NEW: {sym} {d} entry={ep:.4f} tp={tp:.4f} sl={sl:.4f} conv={conv} regime={regime}")

    # Auto-tune insights every AUTOTUNE_INTERVAL closed trades
    tc = len(pf["closed_positions"])
    if tc > 0 and tc % AUTOTUNE_INTERVAL == 0:
        print(f"\n  === AUTO-TUNE ({tc} closed trades) ===")
        ins = compute_insights(pf["closed_positions"])
        save_insights(ins)
        for lv in ("HIGH", "MEDIUM", "LOW"):
            info = ins["conviction_wr"].get(lv, {})
            if info.get("trades", 0) > 0:
                print(f"  INSIGHT: {lv} conviction picks have {info['wr']}% WR "
                      f"({info['trades']} trades, avg pnl ${info['avg_pnl']:.2f})")
        ht = ins["hold_time"]
        if ht["avg_winner_hours"] > 0 or ht["avg_loser_hours"] > 0:
            print(f"  INSIGHT: Winners held avg {ht['avg_winner_hours']}h, losers held avg {ht['avg_loser_hours']}h")

    s = pf["stats"]
    wr = s["wins"] / (s["wins"] + s["losses"]) * 100 if s["wins"] + s["losses"] > 0 else 0
    print(f"\n[REC TRACKER] Balance: ${pf['current_balance']:.2f} | PnL: ${s['total_pnl_usdt']:+.2f} | "
          f"WR: {wr:.1f}% ({s['wins']}W/{s['losses']}L) | Open: {len(pf['positions'])} | +{added} -{closed_n}")
    save_portfolio(pf)
    return pf

if __name__ == "__main__":
    run_check()
