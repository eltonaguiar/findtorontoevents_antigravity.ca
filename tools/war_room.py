"""WAR ROOM: Real-time performance check across ALL engines."""
import json, urllib.request, ssl, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = "https://findtorontoevents.ca/findcryptopairs/api"

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WarRoom/1.0"})
        resp = urllib.request.urlopen(req, timeout=20, context=ctx)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def fmt_pnl(v):
    v = float(v or 0)
    sign = "+" if v > 0 else ""
    return sign + str(round(v, 2)) + "%"

def fmt_price(v):
    v = float(v or 0)
    if v >= 1000: return "$" + str(round(v, 2))
    if v >= 1: return "$" + str(round(v, 4))
    return "$" + str(round(v, 6))

print("=" * 80)
print("  WAR ROOM -- REAL-TIME PERFORMANCE CHECK")
print("  " + time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
print("=" * 80)

# 1. PROVEN PICKS
print("\n" + "=" * 80)
print("  1. PROVEN PICKS (Multi-Engine Consensus, Forward-Tested)")
print("=" * 80)
d = fetch(BASE + "/proven_picks.php?action=picks")
if "error" not in d:
    s = d.get("stats", {})
    print("  Total Resolved: {}  |  Wins: {}  |  Losses: {}".format(s.get("total_picks",0), s.get("wins",0), s.get("losses",0)))
    print("  Win Rate: {}%  |  Cumulative PnL: {}%  |  Sharpe: {}".format(s.get("win_rate",0), s.get("cumulative_pnl",0), s.get("sharpe",0)))
    print("  Profit Factor: {}  |  Max DD: {}%  |  Avg Win: +{}%  |  Avg Loss: -{}%".format(s.get("profit_factor",0), s.get("max_drawdown",0), s.get("avg_win",0), s.get("avg_loss",0)))
    print("  Streak: {}  |  Best Streak: {}  |  Active: {}".format(s.get("current_streak",0), s.get("best_streak",0), s.get("active_count",0)))
    print()
    active = d.get("active", [])
    if active:
        print("  ACTIVE PICKS:")
        for p in active:
            pnl = fmt_pnl(p.get("pnl_pct",0))
            pnl_a = fmt_pnl(p.get("pnl_after_slip",0))
            hrs = round(float(p.get("hours_held",0) or 0), 1)
            print("    {} {} Tier {} | Entry {} -> Now {} | PnL {} (slip-adj {}) | {}h".format(
                p["pair"], p["direction"], p.get("tier","?"),
                fmt_price(p["entry_price"]), fmt_price(p.get("current_price",0)),
                pnl, pnl_a, hrs))
            print("      Engines: {}".format(p.get("engines_agreeing","")))
    else:
        print("  No active picks.")
    hist = d.get("history", [])
    if hist:
        print("\n  RECENT RESOLVED:")
        for h in hist[:5]:
            print("    {} {} {} | PnL {} | {}".format(
                h["pair"], h["direction"], h.get("exit_reason",""),
                fmt_pnl(h.get("pnl_after_slip",0)), h.get("resolved_at","")))
else:
    print("  ERROR:", d["error"])

# 2. EXPERT CONSENSUS
print("\n" + "=" * 80)
print("  2. EXPERT CONSENSUS (10 Social + 10 Algo Communities + 5 Disciplines)")
print("=" * 80)
d = fetch(BASE + "/expert_consensus.php?action=signals")
if "error" not in d:
    s = d.get("stats", {})
    print("  Win Rate: {}%  |  PnL: {}%  |  Wins: {}  |  Losses: {}".format(
        s.get("win_rate",0), s.get("total_pnl",0), s.get("wins",0), s.get("losses",0)))
    active = d.get("active", [])
    print("  Active signals: {}".format(len(active)))
    for p in active:
        pnl = fmt_pnl(p.get("pnl_pct",0))
        print("    {} {} | Score {} | Conf {}% | State {} | PnL {}".format(
            p["pair"], p["direction"], p.get("expert_score","?"),
            p.get("confidence","?"), p.get("market_state","?"), pnl))
else:
    print("  ERROR:", d["error"])

# 3. KIMI-ENHANCED
print("\n" + "=" * 80)
print("  3. KIMI-ENHANCED (Asset-Specific Modules + Walk-Forward Backtested)")
print("=" * 80)
d = fetch(BASE + "/kimi_enhanced.php?action=signals")
if "error" not in d:
    s = d.get("stats", {})
    print("  Win Rate: {}%  |  PnL: {}%  |  Wins: {}  |  Losses: {}".format(
        s.get("wr",0), s.get("pnl",0), s.get("w",0), s.get("l",0)))
    active = d.get("active", [])
    print("  Active signals: {}".format(len(active)))
    for p in active:
        pnl = fmt_pnl(p.get("pnl_pct",0))
        print("    {} {} | Module {}/{} | Strat {} | Conf {}% | PnL {}".format(
            p["pair"], p["direction"],
            p.get("asset_module","?"), p.get("strategy_type","?"),
            p.get("strategy","?"), p.get("confidence","?"), pnl))
else:
    print("  ERROR:", d["error"])

# 4. KIMI BACKTEST LEADERBOARD
print("\n" + "=" * 80)
print("  4. BACKTEST LEADERBOARD (Walk-Forward Out-of-Sample Results)")
print("=" * 80)
d = fetch(BASE + "/kimi_enhanced.php?action=compare")
if "error" not in d:
    bt = d.get("backtest_leaderboard", [])
    print("  Top 10 strategies by out-of-sample Sharpe:")
    print("  {:<12} {:<22} {:<8} {:>8} {:>8} {:>8}".format("Pair","Strategy","WR%","PnL%","Sharpe","Overfit"))
    for b in bt[:10]:
        print("  {:<12} {:<22} {:>8} {:>8} {:>8} {:>8}".format(
            b["pair"], b["strategy"],
            b["test_win_rate"], b["test_pnl"], b["test_sharpe"], b["overfit_ratio"]))
else:
    print("  ERROR:", d["error"])

# 5. CURRENT MARKET PRICES
print("\n" + "=" * 80)
print("  5. CURRENT MARKET (Kraken Live Prices)")
print("=" * 80)
try:
    req = urllib.request.Request("https://api.kraken.com/0/public/Ticker?pair=XXBTZUSD,XETHZUSD,SOLUSD,XXRPZUSD,AVAXUSD", headers={"User-Agent":"WarRoom/1.0"})
    resp = urllib.request.urlopen(req, timeout=10, context=ctx)
    kdata = json.loads(resp.read().decode())
    if kdata.get("result"):
        for k, v in kdata["result"].items():
            last = float(v["c"][0])
            hi = float(v["h"][1])
            lo = float(v["l"][1])
            chg = ((last - float(v["o"])) / float(v["o"])) * 100 if float(v["o"]) > 0 else 0
            print("  {:<12} {} | 24h Hi {} | 24h Lo {} | 24h Chg {:+.2f}%".format(
                k, fmt_price(last), fmt_price(hi), fmt_price(lo), chg))
except Exception as e:
    print("  Kraken error:", e)

# 6. OTHER ENGINES (quick check)
print("\n" + "=" * 80)
print("  6. OTHER ENGINES (Quick Status)")
print("=" * 80)
engines = [
    ("Alpha Hunter", "/alpha_hunter.php?action=signals"),
    ("Hybrid Engine", "/hybrid_engine.php?action=signals"),
    ("Academic Edge", "/academic_edge.php?action=signals"),
    ("Spike Forensics", "/spike_forensics.php?action=signals"),
]
for name, url in engines:
    d = fetch(BASE + url)
    if "error" not in d:
        active = d.get("active", d.get("signals", []))
        if isinstance(active, list):
            print("  {:<20} Active: {}".format(name, len(active)))
        else:
            print("  {:<20} Response OK".format(name))
    else:
        print("  {:<20} {}".format(name, d["error"]))

print("\n" + "=" * 80)
print("  WAR ROOM COMPLETE")
print("=" * 80)
