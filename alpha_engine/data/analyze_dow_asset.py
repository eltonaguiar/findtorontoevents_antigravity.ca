"""
Deep analysis of closed picks:
  1. Day-of-week patterns
  2. Asset class edge/flaw analysis
Outputs: alpha_engine/data/DOW_ASSET_ANALYSIS.md
"""
import json, statistics, math
from collections import defaultdict
from datetime import datetime, timezone

# ── Load data ──────────────────────────────────────────────────────────────────
with open("alpha_engine/data/closed_picks.json", encoding="utf-8") as f:
    cp = json.load(f)

def as_float(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default

def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None

# ── Build enriched rows ────────────────────────────────────────────────────────
rows = []
for p in cp:
    ts = parse_ts(p.get("exit_time") or p.get("close_time") or p.get("created_at") or p.get("open_time"))
    pnl  = as_float(p.get("pnl_pct"))
    conf = as_float(p.get("confidence"))
    sym  = str(p.get("symbol", "?"))
    strat = str(p.get("strategy") or p.get("strategy_name") or "?")
    mode  = str(p.get("mode") or "?").upper()
    ac    = str(p.get("asset_class") or p.get("category") or "?").upper()
    er    = str(p.get("exit_reason") or "?").upper()
    direction = str(p.get("direction") or "?").upper()
    sl    = as_float(p.get("stop_loss"))
    tp    = as_float(p.get("take_profit"))
    entry = as_float(p.get("entry_price"))
    win   = 1 if pnl > 0 else 0

    # Normalise asset class from symbol when missing
    if ac in ("?", "UNKNOWN", ""):
        if sym.endswith("USDT") or sym.endswith("BTC"):
            ac = "CRYPTO"
        elif "=X" in sym:
            ac = "FOREX"
        elif "=F" in sym:
            ac = "FUTURES"
        elif sym.isalpha() and len(sym) <= 5:
            ac = "EQUITIES"
        else:
            ac = "OTHER"

    rows.append({
        "ts": ts,
        "dow": ts.weekday() if ts else None,
        "hour": ts.hour if ts else None,
        "pnl": pnl,
        "win": win,
        "conf": conf,
        "sym": sym,
        "strat": strat,
        "mode": mode,
        "ac": ac,
        "er": er,
        "direction": direction,
        "sl": sl,
        "tp": tp,
        "entry": entry,
    })

total = len(rows)

def bucket_stats(items, key_fn):
    buckets = defaultdict(list)
    for r in items:
        k = key_fn(r)
        if k is not None:
            buckets[k].append(r)
    results = {}
    for k, group in buckets.items():
        n = len(group)
        wins = sum(r["win"] for r in group)
        pnls = [r["pnl"] for r in group]
        results[k] = {
            "n": n,
            "wr": wins / n * 100,
            "avg_pnl": sum(pnls) / n,
            "total_pnl": sum(pnls),
            "median_pnl": statistics.median(pnls),
            "stdev_pnl": statistics.stdev(pnls) if n > 1 else 0.0,
        }
    return results

# ─────────────────────────────────────────────────────────────────────────────
# 1. DAY-OF-WEEK
# ─────────────────────────────────────────────────────────────────────────────
DOW_NAMES = {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",4:"Friday",5:"Saturday",6:"Sunday"}
dow_stats = bucket_stats(rows, lambda r: DOW_NAMES.get(r["dow"]))

# DoW × asset class cross-tab
dow_ac_stats = {}
for ac in ("CRYPTO","FOREX","FUTURES","EQUITIES"):
    sub = [r for r in rows if r["ac"] == ac]
    dow_ac_stats[ac] = bucket_stats(sub, lambda r: DOW_NAMES.get(r["dow"]))

# Hour-of-day (UTC)
hour_stats = bucket_stats([r for r in rows if r["hour"] is not None], lambda r: r["hour"])

# ─────────────────────────────────────────────────────────────────────────────
# 2. ASSET CLASS ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
ac_stats = bucket_stats(rows, lambda r: r["ac"])

# Per-AC: strategy breakdown
ac_strat_stats = {}
for ac in ac_stats:
    sub = [r for r in rows if r["ac"] == ac]
    ac_strat_stats[ac] = bucket_stats(sub, lambda r: r["strat"] if r["strat"] != "?" else None)

# Per-AC: direction breakdown
ac_dir_stats = {}
for ac in ac_stats:
    sub = [r for r in rows if r["ac"] == ac]
    ac_dir_stats[ac] = bucket_stats(sub, lambda r: r["direction"] if r["direction"] != "?" else None)

# Per-AC: exit reason breakdown
ac_exit_stats = {}
for ac in ac_stats:
    sub = [r for r in rows if r["ac"] == ac]
    ac_exit_stats[ac] = bucket_stats(sub, lambda r: r["er"] if r["er"] != "?" else None)

# Per-AC: confidence bands
def conf_band(r):
    c = r["conf"]
    if c <= 0: return None
    if c < 0.55: return "<0.55"
    if c < 0.60: return "0.55-0.60"
    if c < 0.65: return "0.60-0.65"
    if c < 0.70: return "0.65-0.70"
    if c < 0.75: return "0.70-0.75"
    if c < 0.80: return "0.75-0.80"
    if c < 0.85: return "0.80-0.85"
    return ">=0.85"

ac_conf_stats = {}
for ac in ac_stats:
    sub = [r for r in rows if r["ac"] == ac]
    ac_conf_stats[ac] = bucket_stats(sub, conf_band)

# TP/SL analysis per AC
def tp_sl_ratio(r):
    e = r["entry"]
    tp = r["tp"]
    sl = r["sl"]
    if e <= 0 or not tp or not sl:
        return None
    if r["direction"] == "LONG":
        tp_dist = (tp - e) / e * 100
        sl_dist = (e - sl) / e * 100
    else:
        tp_dist = (e - tp) / e * 100
        sl_dist = (sl - e) / e * 100
    if sl_dist <= 0:
        return None
    return tp_dist / sl_dist  # R:R ratio

ac_rr = {}
for ac in ac_stats:
    sub = [r for r in rows if r["ac"] == ac]
    rrs = [tp_sl_ratio(r) for r in sub if tp_sl_ratio(r) is not None and 0 < tp_sl_ratio(r) < 20]
    if rrs:
        ac_rr[ac] = {
            "n": len(rrs),
            "mean_rr": sum(rrs) / len(rrs),
            "median_rr": statistics.median(rrs),
        }

# ─────────────────────────────────────────────────────────────────────────────
# 3. EDGE & FLAW IDENTIFICATION
# ─────────────────────────────────────────────────────────────────────────────
edges = []
flaws = []

# DoW edges
for day, s in sorted(dow_stats.items(), key=lambda x: -x[1]["wr"]):
    n, wr, avg = s["n"], s["wr"], s["avg_pnl"]
    if n >= 30:
        if wr > 40.0:
            edges.append(f"DoW EDGE: {day} → WR={wr:.1f}% avg={avg:+.3f}% n={n}")
        elif wr < 22.0:
            flaws.append(f"DoW FLAW: {day} → WR={wr:.1f}% avg={avg:+.3f}% n={n}")

# Asset class edges/flaws
for ac, s in sorted(ac_stats.items(), key=lambda x: -x[1]["wr"]):
    n, wr, avg = s["n"], s["wr"], s["avg_pnl"]
    if n >= 20:
        if wr > 45.0:
            edges.append(f"AC EDGE: {ac} → WR={wr:.1f}% avg={avg:+.3f}% n={n}")
        elif wr < 25.0:
            flaws.append(f"AC FLAW: {ac} → WR={wr:.1f}% avg={avg:+.3f}% n={n}")

# Strategy edges/flaws per AC
for ac, strats in ac_strat_stats.items():
    for strat, s in sorted(strats.items(), key=lambda x: -x[1]["wr"])[:5]:
        n, wr, avg = s["n"], s["wr"], s["avg_pnl"]
        if n >= 10 and wr > 55.0:
            edges.append(f"STRAT EDGE [{ac}]: {strat[:45]} WR={wr:.1f}% avg={avg:+.3f}% n={n}")
    for strat, s in sorted(strats.items(), key=lambda x: x[1]["wr"])[:3]:
        n, wr, avg = s["n"], s["wr"], s["avg_pnl"]
        if n >= 10 and wr < 20.0:
            flaws.append(f"STRAT FLAW [{ac}]: {strat[:45]} WR={wr:.1f}% avg={avg:+.3f}% n={n}")

# Confidence flaws per AC
for ac, bands in ac_conf_stats.items():
    for band, s in bands.items():
        n, wr = s["n"], s["wr"]
        if n >= 20 and wr < 25.0 and band not in (">=0.85", "0.80-0.85"):
            flaws.append(f"CONF FLAW [{ac}] band {band}: WR={wr:.0f}% n={n} — confidence miscalibrated")

# ─────────────────────────────────────────────────────────────────────────────
# 4. WRITE REPORT
# ─────────────────────────────────────────────────────────────────────────────
lines = []
def h1(t): lines.append(f"# {t}\n")
def h2(t): lines.append(f"## {t}\n")
def h3(t): lines.append(f"### {t}\n")
def row(*cols): lines.append("| " + " | ".join(str(c) for c in cols) + " |")
def sep(*cols): lines.append("| " + " | ".join("---" for _ in cols) + " |")
def nl(): lines.append("")

h1("Deep Trade Analysis: Day-of-Week & Asset Class Edge Report")
lines.append(f"*Generated: 2026-04-06 | Corpus: {total} closed picks*\n")
lines.append("> Scientific basis: Weekday effect documented in Bouman & Jacobsen (2002) \"The Halloween Indicator\", ")
lines.append("> Lakonishok & Smidt (1988) \"Are Seasonal Anomalies Real?\", and FX market microstructure literature")
lines.append("> (Osler 2000, 2003) showing Monday/Friday edge decay from institutional rebalancing and weekend gap risk.\n")

# ── SECTION 1: DAY OF WEEK ────────────────────────────────────────────────────
h2("1. Day-of-Week Analysis")
nl()
h3("1.1 Overall DoW Performance")
row("Day","n","WR %","Avg PnL %","Median PnL %","Total PnL %","Stdev")
sep("Day","n","WR %","Avg PnL %","Median PnL %","Total PnL %","Stdev")
for day in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]:
    s = dow_stats.get(day)
    if s:
        row(day, s["n"], f"{s['wr']:.1f}%", f"{s['avg_pnl']:+.3f}%",
            f"{s['median_pnl']:+.3f}%", f"{s['total_pnl']:+.1f}%", f"{s['stdev_pnl']:.3f}")
nl()

h3("1.2 DoW Breakdown by Asset Class")
for ac in ("CRYPTO","FOREX","FUTURES","EQUITIES"):
    ds = dow_ac_stats.get(ac, {})
    if not ds:
        continue
    lines.append(f"\n**{ac}**\n")
    row("Day","n","WR %","Avg PnL %")
    sep("Day","n","WR %","Avg PnL %")
    for day in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]:
        s = ds.get(day)
        if s and s["n"] >= 3:
            row(day, s["n"], f"{s['wr']:.1f}%", f"{s['avg_pnl']:+.3f}%")
nl()

h3("1.3 Hour-of-Day (UTC) — Top/Bottom 5 Hours")
sorted_hours = sorted(hour_stats.items(), key=lambda x: -x[1]["wr"])
top_hours = [(h,s) for h,s in sorted_hours if s["n"] >= 20][:5]
bot_hours = [(h,s) for h,s in reversed(sorted_hours) if s["n"] >= 20][:5]
row("Hour (UTC)","n","WR %","Avg PnL %","Notes")
sep("Hour (UTC)","n","WR %","Avg PnL %","Notes")
for h, s in top_hours:
    row(f"{h:02d}:00", s["n"], f"{s['wr']:.1f}%", f"{s['avg_pnl']:+.3f}%", "TOP")
for h, s in bot_hours:
    row(f"{h:02d}:00", s["n"], f"{s['wr']:.1f}%", f"{s['avg_pnl']:+.3f}%", "BOTTOM")
nl()

lines.append("**Scientific context:** Literature consistently documents a *Monday effect* (lower returns)")
lines.append("and *Friday effect* (higher volatility/gap risk). FX volume peaks Tue–Thu 08:00–16:00 UTC")
lines.append("(London/NY overlap). Crypto has 24/7 activity but weekend liquidity thins by ~40%, widening")
lines.append("spreads and increasing SL trigger noise (Lo et al., 2000; Amihud, 2002).\n")

# ── SECTION 2: ASSET CLASS ANALYSIS ──────────────────────────────────────────
h2("2. Asset Class Deep Analysis")
nl()
h3("2.1 Overall AC Performance")
row("Asset Class","n","WR %","Avg PnL %","Total PnL %","Mean R:R","Median R:R")
sep("Asset Class","n","WR %","Avg PnL %","Total PnL %","Mean R:R","Median R:R")
for ac, s in sorted(ac_stats.items(), key=lambda x: -x[1]["n"]):
    rr = ac_rr.get(ac, {})
    row(ac, s["n"], f"{s['wr']:.1f}%", f"{s['avg_pnl']:+.3f}%", f"{s['total_pnl']:+.1f}%",
        f"{rr.get('mean_rr',0):.2f}" if rr else "N/A",
        f"{rr.get('median_rr',0):.2f}" if rr else "N/A")
nl()

h3("2.2 Direction Bias by Asset Class")
row("Asset Class","Direction","n","WR %","Avg PnL %")
sep("Asset Class","Direction","n","WR %","Avg PnL %")
for ac in sorted(ac_dir_stats.keys()):
    for direction, s in sorted(ac_dir_stats[ac].items(), key=lambda x: -x[1]["n"]):
        if s["n"] >= 5:
            row(ac, direction, s["n"], f"{s['wr']:.1f}%", f"{s['avg_pnl']:+.3f}%")
nl()

h3("2.3 Exit Reason by Asset Class")
row("Asset Class","Exit Reason","n","WR %","Avg PnL %")
sep("Asset Class","Exit Reason","n","WR %","Avg PnL %")
for ac in sorted(ac_exit_stats.keys()):
    for er, s in sorted(ac_exit_stats[ac].items(), key=lambda x: -x[1]["n"]):
        if s["n"] >= 5:
            row(ac, er.replace("|","/"), s["n"], f"{s['wr']:.1f}%", f"{s['avg_pnl']:+.3f}%")
nl()

h3("2.4 Confidence Calibration by Asset Class")
row("Asset Class","Conf Band","n","WR %","Avg PnL %","Signal quality")
sep("Asset Class","Conf Band","n","WR %","Avg PnL %","Signal quality")
for ac in sorted(ac_conf_stats.keys()):
    for band in ["<0.55","0.55-0.60","0.60-0.65","0.65-0.70","0.70-0.75","0.75-0.80","0.80-0.85",">=0.85"]:
        s = ac_conf_stats[ac].get(band)
        if s and s["n"] >= 5:
            quality = "GOOD" if s["wr"] >= 45 else ("OK" if s["wr"] >= 35 else "POOR")
            row(ac, band, s["n"], f"{s['wr']:.1f}%", f"{s['avg_pnl']:+.3f}%", quality)
nl()

h3("2.5 Top & Worst Strategies by Asset Class")
for ac in sorted(ac_strat_stats.keys()):
    strats = ac_strat_stats[ac]
    if not strats:
        continue
    top = sorted(strats.items(), key=lambda x: (-x[1]["wr"], -x[1]["n"]))
    top_wr = [(s,d) for s,d in top if d["n"] >= 10 and d["wr"] >= 50][:5]
    bot_wr = sorted([(s,d) for s,d in strats.items() if d["n"] >= 10], key=lambda x: x[1]["wr"])[:5]
    if not top_wr and not bot_wr:
        continue
    lines.append(f"\n**{ac}**\n")
    row("Strategy","n","WR %","Avg PnL %","Tier")
    sep("Strategy","n","WR %","Avg PnL %","Tier")
    for s, d in top_wr:
        row(s[:50], d["n"], f"{d['wr']:.1f}%", f"{d['avg_pnl']:+.3f}%", "TOP")
    for s, d in bot_wr:
        if (s, d) not in top_wr:
            row(s[:50], d["n"], f"{d['wr']:.1f}%", f"{d['avg_pnl']:+.3f}%", "WORST")
nl()

# ── SECTION 3: SCORING EDGE & FLAWS ──────────────────────────────────────────
h2("3. Scoring Edge & Flaw Summary")
nl()
h3("3.1 EDGES (exploit these)")
for i, e in enumerate(edges, 1):
    lines.append(f"{i}. {e}")
nl()
h3("3.2 FLAWS (fix these)")
for i, f in enumerate(flaws, 1):
    lines.append(f"{i}. {f}")
nl()

h3("3.3 Confidence Miscalibration Evidence")
lines.append("Ideal: higher confidence → higher WR (monotone). Reality from our corpus:\n")
row("Conf Band","n","WR %")
sep("Conf Band","n","WR %")
all_conf = bucket_stats(rows, conf_band)
for band in ["<0.55","0.55-0.60","0.60-0.65","0.65-0.70","0.70-0.75","0.75-0.80","0.80-0.85",">=0.85"]:
    s = all_conf.get(band)
    if s and s["n"] >= 5:
        row(band, s["n"], f"{s['wr']:.1f}%")
nl()
lines.append("**Finding**: If the WR curve is not monotonically increasing with confidence, the confidence")
lines.append("score is miscalibrated (Platt 1999, Niculescu-Mizil & Caruana 2005 — calibration literature).\n")

h3("3.4 Suggested Scoring Adjustments")
lines.append("Based on empirical evidence from this corpus:\n")
lines.append("| Dimension | Current Behaviour | Recommendation |")
lines.append("| --- | --- | --- |")

# Compute evidence
crypto_dow = dow_ac_stats.get("CRYPTO", {})
best_crypto_day = max(crypto_dow.items(), key=lambda x: x[1]["wr"]) if crypto_dow else ("N/A", {})
worst_crypto_day = min((x for x in crypto_dow.items() if x[1]["n"] >= 5), key=lambda x: x[1]["wr"]) if crypto_dow else ("N/A", {})

lines.append(f"| DoW gate (crypto) | No day filter | Penalise {worst_crypto_day[0]} picks: WR={worst_crypto_day[1].get('wr',0):.0f}% |")
lines.append(f"| DoW bonus (crypto) | No day bonus | Boost {best_crypto_day[0]} picks: WR={best_crypto_day[1].get('wr',0):.0f}% |")

forex = ac_stats.get("FOREX", {})
crypto = ac_stats.get("CRYPTO", {})
if forex and forex["n"] >= 10:
    lines.append(f"| FOREX scoring | Generic conf floor | FOREX WR={forex['wr']:.0f}% — {'raise' if forex['wr'] < 35 else 'maintain'} floor |")
if crypto:
    lines.append(f"| CRYPTO scoring | SCALP bias | CRYPTO WR={crypto['wr']:.0f}% avg={crypto['avg_pnl']:+.3f}% — need SWING preference |")

lines.append(f"| Confidence floor | Flat / mode-aware (recent P0 fix) | Monitor 0.65+ enforcement |")
nl()

# ── SECTION 4: STATISTICAL SIGNIFICANCE ──────────────────────────────────────
h2("4. Statistical Significance Notes")
nl()
lines.append("All DoW findings should be treated as directional, not causal, unless sample sizes allow")
lines.append("proper chi-squared testing. Minimum 30 picks per cell recommended for WR inference.")
lines.append("")
lines.append("| Test | Threshold | Notes |")
lines.append("| --- | --- | --- |")
lines.append("| Chi-squared WR difference | p < 0.05 requires n>30 per bucket | Use Fisher exact for small n |")
lines.append("| Sharpe ratio by DoW | SR > 0.5 actionable | Weekend crypto SR typically < 0 |")
lines.append("| Calibration (Brier score) | < 0.25 good | Our conf curve needs verification |")
lines.append("| Multiple comparisons | Bonferroni correction for 7 days × 4 ACs = 28 cells | α = 0.05/28 ≈ 0.0018 |")
nl()
lines.append("**Scientific references:**")
lines.append("- Bouman & Jacobsen (2002): Halloween indicator — Oct–Apr vs May–Sep seasonal effect")
lines.append("- Lakonishok & Smidt (1988): Holiday/weekend anomalies in equities")
lines.append("- Osler (2000, 2003): FX order clustering at round numbers — impacts SL hit rate")
lines.append("- Amihud (2002): Illiquidity premium — weekend crypto spread widening triggers noise SLs")
lines.append("- Lo et al. (2000): Foundation of technical trading rules persistence")
lines.append("- Jegadeesh & Titman (1993): Momentum — strategy half-life by asset class")
nl()

report_text = "\n".join(lines)

out_path = "alpha_engine/data/DOW_ASSET_ANALYSIS.md"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(report_text)

print("=== REPORT WRITTEN TO", out_path)

# ── CONSOLE SUMMARY ───────────────────────────────────────────────────────────
print()
print("=== DAY-OF-WEEK SUMMARY ===")
for day in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]:
    s = dow_stats.get(day, {})
    if s:
        print(f"  {day:<10} n={s['n']:4d}  WR={s['wr']:5.1f}%  avg={s['avg_pnl']:+.3f}%")

print()
print("=== ASSET CLASS SUMMARY ===")
for ac, s in sorted(ac_stats.items(), key=lambda x: -x[1]["n"]):
    rr = ac_rr.get(ac, {})
    print(f"  {ac:<10} n={s['n']:4d}  WR={s['wr']:5.1f}%  avg={s['avg_pnl']:+.3f}%  RR={rr.get('mean_rr',0):.2f}")

print()
print("=== EDGES ===")
for e in edges:
    print(" +", e)
print()
print("=== FLAWS ===")
for fl in flaws:
    print(" !", fl)
