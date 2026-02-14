"""Top Picks Engine — Real-time status check"""
import json, sys
try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request

BASE = "https://findtorontoevents.ca/findcryptopairs/api/"

def fetch(ep):
    try:
        req = Request(BASE + ep, headers={"User-Agent": "WarRoom/1.0"})
        return json.loads(urlopen(req, timeout=60).read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}

def sign(v):
    return ("+" if v >= 0 else "") + "{:.2f}%".format(v)

sep = "=" * 64

# ── DERIVATIVES FEED ──
print(sep)
print("  DERIVATIVES INTELLIGENCE (Binance Futures)")
print(sep)
deriv = fetch("derivatives_feed.php?action=all")
if deriv.get("ok"):
    for asset in ["BTC", "ETH", "AVAX"]:
        rs = deriv.get("risk_scores", {}).get(asset, {})
        st = deriv.get("supertrend", {}).get(asset, {})
        fr = deriv.get("funding", {}).get(asset, {})
        ls = deriv.get("long_short_ratio", {}).get(asset, {})
        oi = deriv.get("open_interest", {}).get(asset, {})
        score = rs.get("risk_score", "?")
        assess = rs.get("assessment", "?")
        print("")
        print("  {}:".format(asset))
        print("    Risk Score  : {}/100 -> {}".format(score, assess))
        st_sig = st.get("signal", st.get("error", "?"))
        print("    Supertrend  : {}".format(st_sig))
        print("    Funding     : {} (rate={})".format(
            fr.get("extreme", fr.get("error", "?")),
            fr.get("current_rate", fr.get("error", "?"))))
        print("    L/S Ratio   : {} ({})".format(
            ls.get("ratio", ls.get("error", "?")),
            ls.get("positioning", ls.get("error", "?"))))
        oi_trend = oi.get("oi_trend_7d", oi.get("error", "?"))
        print("    Open Int    : {}".format(oi_trend))
        for f in rs.get("factors", []):
            print("    + {}".format(f))
        for w in rs.get("warnings", []):
            print("    ! WARNING: {}".format(w))
    print("\n  Latency: {}ms".format(deriv.get("latency_ms", "?")))
else:
    print("  ERROR: {}".format(deriv.get("error", "unknown")))

# ── SCAN ──
print("")
print(sep)
print("  CONSENSUS SCAN (Hybrid + Custom + Spike + Derivatives)")
print(sep)
scan = fetch("top_picks.php?action=scan&key=toppicks2026")
if scan.get("ok"):
    eo = scan.get("engines_online", 0)
    es = scan.get("engine_status", {})
    print("  Engines online: {}/4  |  Latency: {}ms".format(eo, scan.get("latency_ms", "?")))
    for eng, st in es.items():
        icon = "[OK]" if st == "ONLINE" else "[!!]"
        print("    {} {} : {}".format(icon, eng.upper(), st))
    picks = scan.get("picks", [])
    print("")
    for p in picks:
        grade = p.get("grade", "?")
        asset = p.get("asset", "?")
        price = float(p.get("price", 0))
        eng_a = p.get("engines_agree", 0)
        eng_t = p.get("engines_total", 0)
        regime = p.get("hybrid_regime", "")
        print("  {} | Grade: {} | Price: {:,.2f} | Consensus: {}/{} | Regime: {}".format(
            asset, grade, price, eng_a, eng_t, regime))
        if p.get("hybrid_signal") not in ("OFFLINE", None, ""):
            print("    Hybrid v2.0 : {} (conf {})".format(
                p.get("hybrid_signal"), p.get("hybrid_conf")))
        if p.get("custom_signal") not in ("OFFLINE", None, ""):
            print("    Custom      : {} (score {}/100)".format(
                p.get("custom_signal"), p.get("custom_score")))
        if p.get("spike_signal") not in ("OFFLINE", "", None):
            det = p.get("spike_detail", "")
            print("    Spike       : {} {}".format(p.get("spike_signal"),
                  "({})".format(det) if det else ""))
        thesis = p.get("thesis", "")
        if thesis:
            for s in thesis.split(". "):
                if s.strip():
                    print("    > {}".format(s.strip()))
        tp_p = p.get("tp_price", "")
        sl_p = p.get("sl_price", "")
        if tp_p:
            print("    TP: {} | SL: {}".format(tp_p, sl_p))
        print("")
else:
    print("  SCAN ERROR: {}".format(scan.get("error", "unknown")))

# ── STATS ──
print(sep)
print("  FORWARD-TEST TRACK RECORD")
print(sep)
stats = fetch("top_picks.php?action=stats")
if stats.get("ok"):
    s = stats.get("overall", {})
    print("  Total Picks   : {}".format(s.get("total_picks", 0)))
    print("  Open          : {}".format(s.get("open", 0)))
    print("  No-Trade Days : {}".format(s.get("no_trade_days", 0)))
    print("  Resolved      : {}".format(s.get("resolved", 0)))
    print("  Wins          : {}".format(s.get("wins", 0)))
    print("  Losses        : {}".format(s.get("losses", 0)))
    print("  Win Rate      : {}%".format(s.get("win_rate", 0)))
    avg = s.get("avg_pnl")
    if avg is not None:
        print("  Avg P&L       : {}".format(sign(avg)))
    else:
        print("  Avg P&L       : --")
    print("  Total P&L     : {}".format(sign(s.get("total_pnl", 0))))
    print("  Sharpe        : {}".format(s.get("sharpe", "--")))
    bg = stats.get("by_grade", [])
    if bg:
        print("")
        print("  By Grade:")
        for g in bg:
            print("    {} : {} picks | {}W {}L | WR {}%".format(
                g["grade"], g["total"], g["wins"], g["losses"], g.get("win_rate", 0)))
    ba = stats.get("by_asset", [])
    if ba:
        print("")
        print("  By Asset:")
        for a in ba:
            print("    {} : {} picks | {}W {}L | WR {}%".format(
                a["asset"], a["total"], a["wins"], a["losses"], a.get("win_rate", 0)))
else:
    print("  STATS ERROR: {}".format(stats.get("error", "unknown")))

# ── HISTORY ──
print("")
print(sep)
print("  ALL PICKS IN DATABASE")
print(sep)
hist = fetch("top_picks.php?action=history")
if hist.get("ok"):
    picks = hist.get("picks", [])
    print("  Total recorded: {}".format(len(picks)))
    for p in picks:
        pnl = float(p.get("pnl_pct") or 0)
        status = p.get("status", "?")
        entry = float(p.get("entry_price") or 0)
        current = float(p.get("current_price") or 0)
        grade = p.get("grade", "?")
        asset = p.get("asset", "?")
        date = p.get("pick_date", "?")[:10]
        peak = float(p.get("peak_pnl", 0))
        trough = float(p.get("trough_pnl", 0))
        thesis_short = (p.get("thesis", "") or "")[:80]
        print("")
        print("  {} {} {} [{}]".format(date, asset, grade, status))
        print("    Entry {:,.2f} -> Now {:,.2f} | P&L {} | Peak {} | Trough {}".format(
            entry, current, sign(pnl), sign(peak), sign(trough)))
        if thesis_short:
            print("    Thesis: {}...".format(thesis_short))
else:
    print("  HISTORY ERROR: {}".format(hist.get("error", "unknown")))

# ── VERDICT ──
print("")
print(sep)
print("  WAR VERDICT")
print(sep)
if scan.get("ok"):
    picks = scan.get("picks", [])
    actionable = [p for p in picks if p.get("grade") not in ("WAIT", None)]
    if actionable:
        print("  ACTIONABLE PICKS: {}".format(len(actionable)))
        for p in actionable:
            print("  >>> {} Grade {} at {:,.2f}".format(
                p["asset"], p["grade"], float(p["price"])))
    else:
        print("  NO ACTIONABLE PICKS — ALL ENGINES SAY WAIT")
        print("  This IS the system working. Discipline = Edge.")
print("")
print("  Dashboard : https://findtorontoevents.ca/findcryptopairs/top-picks.html")
print(sep)
